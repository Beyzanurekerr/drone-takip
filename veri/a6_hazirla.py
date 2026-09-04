"""A6 veri hazirlama - UAVDT on-egitim + VisDrone fine-tuning havuzlari.

TAM BELIRLENIMCI: rastgelelik yok, tohum yok, sirali gezinme. Ayni kaynaklardan
ayni cikti uretilir.

KAYNAKLARA YAZILMAZ:
  - UAVDT tar'i yalnizca AKIS modunda (`tarfile "r|"`) OKUNUR; tar'a yazilmaz.
  - data/datasets/visdrone_det/ yalnizca okunur; tasima/silme yok.
  - Tum cikti data/a6/ altina YENI dosya olarak yazilir.

ASAMA A (on-egitim): UAVDT M alt kumesi, her 5. kare, TEK SINIF 'vehicle'.
    S alt kumesi (S####, jenerik 'vehicle', kare basina 1 kutu) ILK TURDA YOK.
ASAMA B (fine-tune): VisDrone DET, 4 sinif (car/van/truck/bus).
    A5 benchmark sizintisi nedeniyle 0000117_* ve 0000086_* gruplari HARIC.

SINIF ESLEMESI - A5'in COCO haritasi BURAYA TASINMAZ:
    A5.1 `veri/yolo_secici.py` COCO id'leriyle filtreler (2,3,5,7). A6 modelleri
    COCO id'i URETMEZ. Asama A tek sinif (0=vehicle); Asama B 0=car 1=van
    2=truck 3=bus (VisDrone 4,5,6,9 -> 0,1,2,3). Iki harita da burada TANIMLIDIR
    ve `data.yaml`'a yazilir; secici tarafi ayri bir turda guncellenecek.
"""
import json
import os
import re
import shutil
import sys
import tarfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veri.etiket import det_oku                                   # noqa: E402

TAR = "/mnt/c/Users/Casper/Downloads/uavdt-DatasetNinja.tar"
VD_KOK = "data/datasets/visdrone_det"
CIKTI = "data/a6"
ADIM = 5                                    # UAVDT: her 5. kare
HARIC_GRUP = ("0000117", "0000086")         # A5 sizintisi (A6 planinda kanitlandi)
VD_HARITA = {4: 0, 5: 1, 6: 2, 9: 3}        # car, van, truck, bus
VD_ADLAR = ["car", "van", "truck", "bus"]
UAVDT_ARAC = {"car", "truck", "bus"}        # -> tek sinif 0 'vehicle'


def yolo_satir(sinif, x, y, w, h, W, H):
    """Sol-ust (x,y,w,h) -> normalize 'cls cx cy w h'. Kadraja kirpilir."""
    x1, y1 = max(0.0, float(x)), max(0.0, float(y))
    x2, y2 = min(float(W), float(x) + float(w)), min(float(H), float(y) + float(h))
    ww, hh = x2 - x1, y2 - y1
    if ww <= 0.0 or hh <= 0.0:
        return None, None
    cx, cy = (x1 + ww / 2.0) / W, (y1 + hh / 2.0) / H
    return (f"{sinif} {cx:.6f} {cy:.6f} {ww / W:.6f} {hh / H:.6f}",
            (x1, y1, ww, hh))


def klasorler(kok, bolumler=("train", "val", "test")):
    for b in bolumler:
        os.makedirs(f"{kok}/images/{b}", exist_ok=True)
        os.makedirs(f"{kok}/labels/{b}", exist_ok=True)


def dengeli_ata(gruplar, agirlik, paylar=(0.70, 0.15, 0.15)):
    """Grup-bazli belirlenimci split: gruplar agirliga gore azalan sirada
    gezilir, her grup o an hedef payinin EN ALTINDA kalan bolume verilir.
    Rastgelelik yok; beraberlikte 'train' > 'val' > 'test' sirasi."""
    bolum = {b: 0.0 for b in ("train", "val", "test")}
    hedef = dict(zip(("train", "val", "test"), paylar))
    toplam = float(sum(agirlik.values())) or 1.0
    atama = {}
    for g in sorted(gruplar, key=lambda g: (-agirlik.get(g, 0), g)):
        b = min(("train", "val", "test"),
                key=lambda b: (bolum[b] / toplam - hedef[b], b))
        atama[g] = b
        bolum[b] += agirlik.get(g, 0)
    return atama, {b: bolum[b] for b in bolum}


# ============================================================ ASAMA A: UAVDT
def uavdt_gecis1():
    """Tar'i bir kez akitip M alt kumesinin dizi/kare envanterini cikarir.

    Yalnizca tar BASLIKLARI okunur; dosya icerigi acilmaz, hicbir sey yazilmaz.
    """
    dizi = {}
    with tarfile.open(TAR, "r|") as tf:
        for m in tf:
            p = m.name.lstrip("./")
            if not (m.isfile() and "/img/" in p and p.endswith(".jpg")):
                continue
            ad = p.split("/")[-1]
            g = re.match(r"(M\d+)_img(\d+)\.jpg$", ad)
            if not g:                        # S alt kumesi: ILK TURDA DISARIDA
                continue
            dz, idx = g.group(1), int(g.group(2))
            if (idx - 1) % ADIM != 0:        # her 5. kare: 1, 6, 11, ...
                continue
            dizi.setdefault(dz, []).append(ad)
    return {k: sorted(v) for k, v in sorted(dizi.items())}


def uavdt_gecis2(secim, atama, kok):
    """Secilen kareleri ve JSON'lari tar'dan okuyup YOLO formatinda yazar."""
    gerekli = {}
    for dz, adlar in secim.items():
        for ad in adlar:
            gerekli[ad] = atama[dz]
    say = {"goruntu": 0, "kutu": 0, "atlanan_kutu": 0, "sinif": {}}
    rt = {"n": 0, "max_hata": 0.0}
    bekleyen = {}                            # ann JSON'lari img'den once gelebilir
    with tarfile.open(TAR, "r|") as tf:
        for m in tf:
            p = m.name.lstrip("./")
            if not m.isfile():
                continue
            ad = p.split("/")[-1]
            if "/ann/" in p and ad.endswith(".jpg.json"):
                jpg = ad[:-5]
                if jpg in gerekli:
                    bekleyen[jpg] = json.loads(tf.extractfile(m).read())
            elif "/img/" in p and ad.endswith(".jpg") and ad in gerekli:
                b = gerekli[ad]
                with open(f"{kok}/images/{b}/{ad}", "wb") as f:
                    f.write(tf.extractfile(m).read())
                d = bekleyen.pop(ad, None)
                if d is None:
                    raise RuntimeError(f"annotation bulunamadi: {ad}")
                W, H = d["size"]["width"], d["size"]["height"]
                satirlar = []
                for o in d.get("objects", []):
                    c = o["classTitle"]
                    say["sinif"][c] = say["sinif"].get(c, 0) + 1
                    if c not in UAVDT_ARAC:          # 'vehicle' yalnizca S'te
                        say["atlanan_kutu"] += 1
                        continue
                    (x1, y1), (x2, y2) = o["points"]["exterior"][:2]
                    x, y = min(x1, x2), min(y1, y2)
                    w, h = abs(x2 - x1), abs(y2 - y1)
                    s, kutu = yolo_satir(0, x, y, w, h, W, H)   # 0 = vehicle
                    if s is None:
                        say["atlanan_kutu"] += 1
                        continue
                    satirlar.append(s)
                    # round-trip: yazilan normalize deger geri cozulunce ayni mi
                    pr = [float(v) for v in s.split()[1:]]
                    gx = (pr[0] - pr[2] / 2) * W
                    gy = (pr[1] - pr[3] / 2) * H
                    hata = max(abs(gx - kutu[0]), abs(gy - kutu[1]),
                               abs(pr[2] * W - kutu[2]), abs(pr[3] * H - kutu[3]))
                    rt["n"] += 1
                    rt["max_hata"] = max(rt["max_hata"], hata)
                with open(f"{kok}/labels/{b}/{ad[:-4]}.txt", "w") as f:
                    f.write("\n".join(satirlar) + ("\n" if satirlar else ""))
                say["goruntu"] += 1
                say["kutu"] += len(satirlar)
    return say, rt


# ======================================================== ASAMA B: VisDrone
def visdrone_hazirla(kok):
    """VisDrone DET -> YOLO (4 sinif). Sizintili gruplar tamamen disarida."""
    import cv2
    adlar = sorted(os.path.splitext(f)[0]
                   for f in os.listdir(f"{VD_KOK}/images") if f.endswith(".jpg"))
    haric = [a for a in adlar if a.split("_")[0] in HARIC_GRUP]
    temiz = [a for a in adlar if a.split("_")[0] not in HARIC_GRUP]

    # BIREBIR AYNI GORUNTULERI AYNI GRUBA BAGLA.
    # VisDrone DET'te md5'i ayni bir cift var (0000022_00000_d_0000004 ve
    # 0000023_00000_d_0000008) ve videoID'leri FARKLI. Yalnizca videoID'ye
    # gore bolununce bu cift train ile test'e dagildi -> birebir train/test
    # sizintisi. Ayni hash'i paylasan videoID'ler once birlestirilir.
    import hashlib
    hh = {}
    for a in temiz:
        with open(f"{VD_KOK}/images/{a}.jpg", "rb") as f:
            hh.setdefault(hashlib.md5(f.read()).hexdigest(), []).append(a)
    kok_g = {a.split("_")[0]: a.split("_")[0] for a in temiz}

    def bul(g):
        while kok_g[g] != g:
            g = kok_g[g]
        return g

    birlesen = []
    for _h, adlar in sorted(hh.items()):
        if len(adlar) < 2:
            continue
        gs = sorted({x.split("_")[0] for x in adlar})
        birlesen.append(gs)
        for g in gs[1:]:
            kok_g[bul(g)] = bul(gs[0])

    # grup agirligi = arac kutusu sayisi (split dengesi bunun uzerinden)
    grup = {}
    kutu_say = {}
    for a in temiz:
        g = bul(a.split("_")[0])
        n = sum(1 for e in det_oku(f"{VD_KOK}/annotations/{a}.txt")
                if e.sinif in VD_HARITA and not e.yoksayilan)
        kutu_say[a] = n
        grup.setdefault(g, []).append(a)
    agirlik = {g: sum(kutu_say[a] for a in v) for g, v in grup.items()}
    atama, dagilim = dengeli_ata(list(grup), agirlik)

    say = {"goruntu": 0, "kutu": 0, "atlanan_kutu": 0, "sinif": {}}
    rt = {"n": 0, "max_hata": 0.0}
    for g, dosyalar in sorted(grup.items()):
        b = atama[g]
        for a in dosyalar:
            im = cv2.imread(f"{VD_KOK}/images/{a}.jpg")
            H, W = im.shape[:2]
            shutil.copy2(f"{VD_KOK}/images/{a}.jpg", f"{kok}/images/{b}/{a}.jpg")
            satirlar = []
            for e in det_oku(f"{VD_KOK}/annotations/{a}.txt"):
                if e.yoksayilan or e.sinif not in VD_HARITA:
                    say["atlanan_kutu"] += 1
                    continue
                c = VD_HARITA[e.sinif]
                say["sinif"][VD_ADLAR[c]] = say["sinif"].get(VD_ADLAR[c], 0) + 1
                s, kutu = yolo_satir(c, *[float(v) for v in e.kutu], W, H)
                if s is None:
                    say["atlanan_kutu"] += 1
                    continue
                satirlar.append(s)
                pr = [float(v) for v in s.split()[1:]]
                hata = max(abs((pr[0] - pr[2] / 2) * W - kutu[0]),
                           abs((pr[1] - pr[3] / 2) * H - kutu[1]),
                           abs(pr[2] * W - kutu[2]), abs(pr[3] * H - kutu[3]))
                rt["n"] += 1
                rt["max_hata"] = max(rt["max_hata"], hata)
            with open(f"{kok}/labels/{b}/{a}.txt", "w") as f:
                f.write("\n".join(satirlar) + ("\n" if satirlar else ""))
            say["goruntu"] += 1
            say["kutu"] += len(satirlar)
    return say, rt, atama, agirlik, haric, temiz, birlesen


def yaz_yaml(kok, adlar, baslik):
    yol = f"{kok}/data.yaml"
    with open(yol, "w") as f:
        f.write(f"# {baslik}\n# veri/a6_hazirla.py tarafindan uretildi - elle duzenlemeyin\n")
        f.write(f"path: {os.path.abspath(kok)}\n")
        f.write("train: images/train\nval: images/val\ntest: images/test\n")
        f.write(f"nc: {len(adlar)}\nnames:\n")
        for i, a in enumerate(adlar):
            f.write(f"  {i}: {a}\n")
    return yol


def main():
    ozet = {"kaynaklar": {"uavdt_tar": TAR, "visdrone_det": os.path.abspath(VD_KOK)},
            "adim": ADIM, "haric_gruplar": list(HARIC_GRUP)}

    # ---------------- ASAMA A ----------------
    kokA = f"{CIKTI}/uavdt_pretrain"
    klasorler(kokA)
    print("ASAMA A: UAVDT gecis 1 (envanter)...", flush=True)
    secim = uavdt_gecis1()
    agirlik = {d: len(v) for d, v in secim.items()}
    atamaA, dagA = dengeli_ata(list(secim), agirlik)
    print(f"  {len(secim)} M dizisi, {sum(agirlik.values())} secilen kare", flush=True)
    print("ASAMA A: gecis 2 (cikarma + donusum)...", flush=True)
    sayA, rtA = uavdt_gecis2(secim, atamaA, kokA)
    ozet["asama_A"] = {
        "kok": os.path.abspath(kokA), "dizi": len(secim),
        "secilen_kare": sum(agirlik.values()), "yazilan_goruntu": sayA["goruntu"],
        "kutu": sayA["kutu"], "atlanan_kutu": sayA["atlanan_kutu"],
        "kaynak_sinif_sayimi": sayA["sinif"], "sinif_haritasi": {"0": "vehicle"},
        "split_dizi": atamaA, "split_kare": dagA,
        "split_sayilari": {b: len(os.listdir(f"{kokA}/images/{b}"))
                           for b in ("train", "val", "test")},
        "round_trip": rtA,
        "yaml": yaz_yaml(kokA, ["vehicle"], "A6 Asama A - UAVDT on-egitim (tek sinif)")}

    # ---------------- ASAMA B ----------------
    kokB = f"{CIKTI}/visdrone_finetune"
    klasorler(kokB)
    print("ASAMA B: VisDrone DET donusumu...", flush=True)
    sayB, rtB, atamaB, agB, haric, temiz, birlesen = visdrone_hazirla(kokB)
    ozet["asama_B"] = {
        "kok": os.path.abspath(kokB), "kaynak_goruntu": len(temiz) + len(haric),
        "haric_goruntu": sorted(haric), "temiz_havuz": len(temiz),
        "yazilan_goruntu": sayB["goruntu"], "kutu": sayB["kutu"],
        "atlanan_kutu": sayB["atlanan_kutu"], "sinif_sayimi": sayB["sinif"],
        "sinif_haritasi": {"VisDrone 4 car": 0, "VisDrone 5 van": 1,
                           "VisDrone 6 truck": 2, "VisDrone 9 bus": 3},
        "split_grup": atamaB, "grup_agirligi": agB,
        "hash_ile_birlestirilen_gruplar": birlesen,
        "split_sayilari": {b: len(os.listdir(f"{kokB}/images/{b}"))
                           for b in ("train", "val", "test")},
        "round_trip": rtB,
        "yaml": yaz_yaml(kokB, VD_ADLAR, "A6 Asama B - VisDrone DET fine-tuning")}

    os.makedirs(f"{CIKTI}/manifest", exist_ok=True)
    json.dump(ozet, open(f"{CIKTI}/manifest/a6_hazirlik.json", "w"),
              indent=2, ensure_ascii=False)
    print("\nyazildi:", f"{CIKTI}/manifest/a6_hazirlik.json")
    for k in ("asama_A", "asama_B"):
        v = ozet[k]
        print(f"  {k}: {v['yazilan_goruntu']} goruntu, {v['kutu']} kutu, "
              f"split {v['split_sayilari']}, round-trip max hata "
              f"{v['round_trip']['max_hata']:.4f} px")


if __name__ == "__main__":
    main()
