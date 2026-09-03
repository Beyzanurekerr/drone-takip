"""A5.2 — Kucuk hedef benchmark'i (SALT OKUNUR; takip/ ve A5.1 kodu degismez).

METODOLOJI GEREKCESI (ikisi de OLCULDU, varsayilmadi)
-----------------------------------------------------
M0. Tum kareyi kucultmek ISE YARAMAZ. Ultralytics letterbox'i uzun kenari
    imgsz=640'a normalize eder; kareyi s ile kucultmek ag girdisinde birebir
    geri buyutulur. 117/23 kare 1'de olculdu (olcek 1.0/0.5/0.25/0.125):
    tespit 8/7/6/5, ort guven 0.539/0.572/0.611/0.612 — dedektorun gordugu
    sey degismiyor. Tum-kare olcekleme "yeniden ornekleme kaybini" olcer,
    "hedef boyutunu" DEGIL. REDDEDILDI.

M1. Gercek arkaplanli FOV kirpma YETMIYOR. 146x154 px'lik gercek hedefi
    640x360 tuvalde 5 px uzun kenara indirmek 19193x10796 px'lik bir pencere
    ister; kaynak kare 2720x1530. En buyuk seviye (57) bile 2774x1560 istiyor.
    Hicbir seviye gercek arkaplanla ulasilamiyor. REDDEDILDI.

M2. UYGULANAN: gercek arkaplan uzerine gercek hedef yamasi (chip-composite).
    - Tuval 640x360, HER seviyede sabit. 640x360 -> letterbox 640x384,
      olcek 1.000 (yalnizca dolgu). Yani NOMINAL PIKSEL BOYUTU = AGIN GORDUGU
      BOYUT; letterbox hicbir yeniden olcekleme yapmaz. (Dogrulanir.)
    - Hedef yamasi: GT kutusunun native cozunurluktu kirpimi, IZOTROPIK
      (INTER_AREA) olceklenir; kontrol edilen degisken UZUN KENAR'dir.
      Bu hedeflerin gercek en-boy orani ~1:1, nominal etiketlerinki ~2.7:1;
      ikisini birden zorlamak hedefi BOZARDI. Ulasilan w x h raporlanir.
    - Arkaplan: ayni kareden, native cozunurlukte, ANNOTATION ICERMEYEN
      640x360 hucre (satir-oncelikli ilk bos hucre; deterministik).
    - Yapistirma dikdortgeni GT'dir.
    - Sabit: model, conf, imgsz, siniflar, cihaz, thread sayisi. Rastgelelik yok.

    Gecerlilik kontrolu: "native" seviyesi = yama olcek 1.0. Yapistirilmis
    native yama, dokunulmamis karedeki ayni hedef kadar tespit ediliyorsa
    kompozitin kendisi tespiti bozmuyor demektir.

IKI OLCUM AYRI TUTULUR
    1) TESPIT : YOLO hedefi buluyor mu? (kare basina, yama tuval merkezinde)
    2) TAKIP  : alinan baslangic kutusu takibi ne kadar surduruyor?
                Hedefin tuvaldeki hareketi GT hareketinin s katidir; boylece
                "kendi boyutunun kac kati/kare" her seviyede AYNI kalir
                (projenin olcek degismezligi: doluluk = v/(fps*L)).
                Arkaplan penceresi SABIT -> kamera ego-hareketi yok; takip
                kolu bu yuzden IYIMSER bir ust siniridir, boyut etkisi izole olur.
                Iki kol: YOLO-tohumlu (dedektor kutusu) ve GT-tohumlu
                (takipcinin kendi siniri, dedektorden bagimsiz).
"""
import json
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calistir import iou                                  # noqa: E402
from takip.izleyici import KILITLI, HedefTakip            # noqa: E402
from veri.visdrone import VisDroneVidKaynak               # noqa: E402

KOK = "data/datasets/visdrone_vid"
AGIRLIK = "weights/yolov8n.pt"
CONF, IMGSZ, SINIFLAR = 0.25, 640, [2, 3, 5, 7]           # A5.1 ile AYNI, degismez
TUVAL = (640, 360)
SEVIYELER = [("native", None), ("57x21", 57), ("40x15", 40), ("30x12", 30),
             ("20x10", 20), ("15x7", 15), ("10x5", 10), ("8x5", 8), ("5x5", 5)]
N_TESPIT, N_TAKIP = 40, 60
DIZILER = [("uav0000117_02622_v", 23, "birincil"),
           ("uav0000137_00458_v", 12, "birincil"),
           ("uav0000305_00000_v", 5, "destek")]


# ---------------------------------------------------------------- yardimcilar
class YatakHatasi(Exception):
    """Kompozit yatak kurulamadi (A10.1/D1)."""


def arkaplan_hucresi(kareler, W, H, cw, ch):
    """Arkaplan hucresi: hedefe EN YAKIN, hedefi HIC icermeyen 640x360 hucre.

    Neden yakinlik: yama hedefin gercekte bulundugu yolun hemen yanina konur;
    ayni yol dokusu, ayni isik, ayni olcek. Baglam gercekci kalir.

    Neden "dedektore gore en bos hucre" DEGIL: o olcut denendi ve geri alindi.
    Dedektorun hic tespit uretmedigi hucre, tanimi geregi yola en az benzeyen
    bolgedir; 117/23'te oraya yapistirilan NATIVE boyutlu gercek arac bile
    20 karede yalnizca 3 kez bulundu - yani olcut, olcmek istedigimiz seyi
    (boyut etkisini) arkaplan uyusmazligiyla karistiriyordu.

    Arkaplanin KENDI urettigi tespitler ayrica olculur (`arkaplan_taban`) ve
    'ekstra tespit' bunun yaninda raporlanir; gizlenmez.
    """
    mc = np.mean([[g[0] + g[2] / 2.0, g[1] + g[3] / 2.0]
                  for _i, g, _e, _W, _H in kareler], axis=0)
    en_iyi, en_uzak = None, float("inf")
    for y in range(0, max(1, H - ch + 1), ch // 2):
        for x in range(0, max(1, W - cw + 1), cw // 2):
            if y + ch > H or x + cw > W:
                continue
            if any(not (g[0] + g[2] < x or g[0] > x + cw or
                        g[1] + g[3] < y or g[1] > y + ch)
                   for _i, g, _e, _W, _H in kareler):
                continue                       # hedef bu hucrede goruyor
            d = float(np.hypot(x + cw / 2.0 - mc[0], y + ch / 2.0 - mc[1]))
            if d < en_uzak:
                en_iyi, en_uzak = (x, y), d
    # A10.1/D1: (0,0) DUSUSU KALDIRILDI. Eskiden gecerli hucre bulunamayinca
    # sessizce (0,0) donuyordu; o hucre hedefi ICERDIGI icin kompozit arkaplan
    # gercek hedefi native boyutuyla tasiyordu (A10 EK-1 bulgusu, 3 dizi).
    # Artik HATA verir; yatak kurulamayan dizi tabandan DUSER.
    if en_iyi is None:
        raise YatakHatasi(
            f"gecerli arkaplan hucresi yok: {cw}x{ch} hucrelerinin hepsi 60 karenin "
            f"en az birinde hedefi iceriyor (kare {W}x{H}). Bu dizide kompozit "
            f"yatak KURULAMAZ; taban disi birakilmalidir.")
    return en_iyi, round(en_uzak, 1)


def arkaplan_taban(model, kareler, hucre, cw, ch):
    """Arkaplanin YAMASIZ hali kare basina kac tespit uretiyor (FP tabani)."""
    n, k = 0, 0
    for img, _g, _e, _W, _H in kareler:
        parca = img[hucre[1]:hucre[1] + ch, hucre[0]:hucre[0] + cw]
        if parca.shape[:2] != (ch, cw):
            continue
        kutular, _gv, _ms = yolo_calistir(model, parca)
        n += len(kutular)
        k += 1
    return round(n / float(k), 2) if k else None


def yama_olcekle(chip, uzun_kenar):
    """Izotropik olcekleme; kontrol edilen degisken uzun kenardir."""
    h, w = chip.shape[:2]
    if uzun_kenar is None:
        return chip.copy(), 1.0
    s = float(uzun_kenar) / float(max(w, h))
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR
    return cv2.resize(chip, (nw, nh), interpolation=interp), s


def yapistir(arka, chip, cx, cy):
    """chip'i (cx,cy) merkezine yapistir; GT = yapistirma dikdortgeni."""
    tuval = arka.copy()
    h, w = chip.shape[:2]
    x0, y0 = int(round(cx - w / 2.0)), int(round(cy - h / 2.0))
    H, W = tuval.shape[:2]
    if x0 < 0 or y0 < 0 or x0 + w > W or y0 + h > H:
        return None, None
    tuval[y0:y0 + h, x0:x0 + w] = chip
    return tuval, np.array([x0, y0, w, h], np.float32)


def yolo_calistir(model, img):
    t0 = time.perf_counter()
    r = model.predict(img, conf=CONF, imgsz=IMGSZ, classes=SINIFLAR,
                      verbose=False, device="cpu")[0]
    ms = (time.perf_counter() - t0) * 1e3
    kutular, guvenler = [], []
    if r.boxes is not None and len(r.boxes):
        for (x1, y1, x2, y2), g in zip(r.boxes.xyxy.cpu().numpy(),
                                       r.boxes.conf.cpu().numpy()):
            kutular.append(np.array([x1, y1, x2 - x1, y2 - y1], np.float32))
            guvenler.append(float(g))
    return kutular, guvenler, ms


def kareleri_topla(dizi, tid, n):
    """GT'si gorunur ilk n kareyi (goruntu, gt, tum etiketler) olarak dondur."""
    k = VisDroneVidKaynak(KOK, dizi, track_id=tid)
    cikti = []
    for kare in k:
        if kare.gt is not None and kare.gorunur:
            et = k.etiketler.get(kare.indeks + 1, [])
            cikti.append((kare.goruntu, np.asarray(kare.gt, np.float32), et,
                          kare.genislik, kare.yukseklik))
        if len(cikti) >= n:
            break
    return cikti


# ------------------------------------------------------------------- TESPIT
def tespit_olc(model, kareler, W, H):
    """1) TESPIT: YOLO hedefi buluyor mu? Yama tuval merkezinde, kare basina."""
    cw, ch = TUVAL
    hucre, uzaklik = arkaplan_hucresi(kareler, W, H, cw, ch)
    taban = arkaplan_taban(model, kareler, hucre, cw, ch)
    sonuc = {"arkaplan_hucre": list(hucre), "hedeften_uzaklik_px": uzaklik,
             "arkaplan_taban_tespit_kare_basina": taban, "seviyeler": {}}
    for ad, uzun in SEVIYELER:
        vur05 = vur0 = 0
        iou_l, guv_l, ms_l, boy_l, ekstra = [], [], [], [], 0
        kullanilan = 0
        for img, gt, _et, _W, _H in kareler:
            x, y, w, h = [int(round(v)) for v in gt]
            chip = img[max(0, y):y + h, max(0, x):x + w]
            if chip.size == 0 or chip.shape[0] < 2 or chip.shape[1] < 2:
                continue
            chip, _s = yama_olcekle(chip, uzun)
            arka = img[hucre[1]:hucre[1] + ch, hucre[0]:hucre[0] + cw]
            if arka.shape[:2] != (ch, cw):
                continue
            tuval, gt_yeni = yapistir(arka, chip, cw / 2.0, ch / 2.0)
            if tuval is None:
                continue
            kullanilan += 1
            boy_l.append((float(gt_yeni[2]), float(gt_yeni[3])))
            kutular, guvenler, ms = yolo_calistir(model, tuval)
            ms_l.append(ms)
            en_iyi, en_iyi_g = 0.0, 0.0
            for kb, g in zip(kutular, guvenler):
                o = float(iou(kb, gt_yeni))
                if o > en_iyi:
                    en_iyi, en_iyi_g = o, g
                if o <= 0.0:
                    ekstra += 1
            if en_iyi >= 0.5:
                vur05 += 1
            if en_iyi > 0.0:
                vur0 += 1
                iou_l.append(en_iyi)
                guv_l.append(en_iyi_g)
        bl = np.array(boy_l) if boy_l else np.zeros((1, 2))
        sonuc["seviyeler"][ad] = {
            "nominal_uzun_kenar": uzun,
            "ulasilan_w": round(float(bl[:, 0].mean()), 1),
            "ulasilan_h": round(float(bl[:, 1].mean()), 1),
            "ag_girdisi_w": round(float(bl[:, 0].mean()), 1),   # letterbox 1.000
            "kare": kullanilan,
            "recall_iou50": round(vur05 / kullanilan, 4) if kullanilan else None,
            "recall_iou0": round(vur0 / kullanilan, 4) if kullanilan else None,
            "fn": kullanilan - vur0,
            "ort_iou": round(float(np.mean(iou_l)), 4) if iou_l else None,
            "ort_guven": round(float(np.mean(guv_l)), 4) if guv_l else None,
            "ekstra_tespit": ekstra,
            "gecikme_ort_ms": round(float(np.mean(ms_l)), 2) if ms_l else None,
            "gecikme_p50_ms": round(float(np.percentile(ms_l, 50)), 2) if ms_l else None,
            "gecikme_p95_ms": round(float(np.percentile(ms_l, 95)), 2) if ms_l else None,
            "esdeger_fps": round(1000.0 / float(np.mean(ms_l)), 1) if ms_l else None,
        }
    return sonuc


# -------------------------------------------------------------------- TAKIP
def takip_dizisi(kareler, hucre, uzun):
    """Seviye icin sentetik dizi: (tuval, gt) listesi.

    Hedefin tuvaldeki yer degistirmesi GT'nin s katidir -> "kendi boyutunun
    kac kati/kare" her seviyede AYNI kalir.
    """
    cw, ch = TUVAL
    g0 = kareler[0][1]
    L0 = max(float(g0[2]), float(g0[3]))
    s = 1.0 if uzun is None else float(uzun) / L0
    c0 = g0[:2] + g0[2:] / 2.0
    dizi = []
    for img, gt, _et, _W, _H in kareler:
        x, y, w, h = [int(round(v)) for v in gt]
        chip = img[max(0, y):y + h, max(0, x):x + w]
        if chip.size == 0 or chip.shape[0] < 2 or chip.shape[1] < 2:
            break
        nw = max(1, int(round(chip.shape[1] * s)))
        nh = max(1, int(round(chip.shape[0] * s)))
        interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR
        chip = cv2.resize(chip, (nw, nh), interpolation=interp)
        arka = img[hucre[1]:hucre[1] + ch, hucre[0]:hucre[0] + cw]
        if arka.shape[:2] != (ch, cw):
            break
        c = gt[:2] + gt[2:] / 2.0
        p = np.array([cw / 2.0, ch / 2.0]) + (c - c0) * s
        tuval, gt_yeni = yapistir(arka, chip, p[0], p[1])
        if tuval is None:                     # hedef tuvalden cikti
            break
        dizi.append((tuval, gt_yeni))
    return dizi, s


def takip_olc(model, dizi, tohum):
    """2) TAKIP: alinan baslangic kutusu takibi ne kadar surduruyor?

    tohum: "gt"   -> baslangic kutusu yapistirma dikdortgeni (takipcinin sinirı)
           "yolo" -> baslangic kutusu A5.1 dedektorunden (ortusme sartiyla)
    """
    tak = HedefTakip()
    kilitli, kilit_kare, yolo_ms = False, None, []
    iou_l, mh_l, psr_l, kilit_l = [], [], [], []
    drift, ard = None, 0
    for k, (img, gt) in enumerate(dizi):
        if not kilitli:
            if tohum == "gt":
                kutu = gt.copy()
            else:
                kutular, guvenler, ms = yolo_calistir(model, img)
                yolo_ms.append(ms)
                aday = None
                for kb, g in zip(kutular, guvenler):
                    if float(iou(kb, gt)) > 0.0:     # A5.1 ortusme sarti
                        if aday is None or g > aday[1]:
                            aday = (kb, g)
                if aday is None:
                    continue
                kutu = aday[0].copy()
                # A5.1/A4 ile ayni 2 px on-telafi: kos() satir 491-492
                kutu[2:] = np.maximum(kutu[2:] - 2.0, 4.0)
                kutu[:2] = (aday[0][:2] + aday[0][2:] / 2.0) - kutu[2:] / 2.0
            tak.kilitle(img, kutu)
            kilitli, kilit_kare = True, k
            continue
        s = tak.guncelle(img)
        o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
        iou_l.append(o)
        psr_l.append(float(s["psr"]))
        if s["kutu"] is not None:
            tk = s["kutu"]
            mh_l.append(float(np.hypot(tk[0] + tk[2] / 2 - (gt[0] + gt[2] / 2),
                                       tk[1] + tk[3] / 2 - (gt[1] + gt[3] / 2))))
        kilit_l.append(1 if (s["durum"] == KILITLI and o > 0.2) else 0)
        if o < 0.3:
            ard += 1
            if ard >= 5 and drift is None:
                drift = k - 4
        else:
            ard = 0
    return {
        "kilit": bool(kilitli), "kilit_karesi": kilit_kare,
        "takip_karesi": len(iou_l),
        "kilit_orani": round(float(np.mean(kilit_l)), 4) if kilit_l else None,
        "ort_iou": round(float(np.mean(iou_l)), 4) if iou_l else None,
        "ort_merkez_hata_px": round(float(np.mean(mh_l)), 2) if mh_l else None,
        "ort_psr": round(float(np.mean(psr_l)), 2) if psr_l else None,
        "drift_karesi": drift,
        "yolo_cagrisi": len(yolo_ms),
    }


# --------------------------------------------------------------------- main
def letterbox_dogrula(model):
    """640x360 tuvalin ag girdisinde YENIDEN OLCEKLENMEDIGINI dogrula."""
    from ultralytics.data.augment import LetterBox
    lb = LetterBox((IMGSZ, IMGSZ), auto=True, stride=32)
    im = np.zeros((TUVAL[1], TUVAL[0], 3), np.uint8)
    cikti = lb(image=im)
    r = min(IMGSZ / TUVAL[1], IMGSZ / TUVAL[0])
    return {"tuval": list(TUVAL), "ag_girdisi": [cikti.shape[1], cikti.shape[0]],
            "letterbox_olcegi": round(float(r), 4)}


def kompozit_kontrolu(model, kareler, hucre):
    """Kompozit gecerliligi: dokunulmamis kare vs native yama."""
    ham_bul = yam_bul = 0
    cw, ch = TUVAL
    for img, gt, _e, _W, _H in kareler[:20]:
        kutular, _g, _m = yolo_calistir(model, img)
        if any(float(iou(kb, gt)) > 0.0 for kb in kutular):
            ham_bul += 1
        x, y, w, h = [int(round(v)) for v in gt]
        chip = img[max(0, y):y + h, max(0, x):x + w]
        arka = img[hucre[1]:hucre[1] + ch, hucre[0]:hucre[0] + cw]
        if chip.size == 0 or arka.shape[:2] != (ch, cw):
            continue
        tuval, gy = yapistir(arka, chip, cw / 2.0, ch / 2.0)
        if tuval is None:
            continue
        kutular, _g, _m = yolo_calistir(model, tuval)
        if any(float(iou(kb, gy)) > 0.0 for kb in kutular):
            yam_bul += 1
    return {"kare": 20, "dokunulmamis_karede_bulundu": ham_bul,
            "native_yamada_bulundu": yam_bul}


def main():
    import torch
    torch.set_num_threads(8)                 # sabit; belirlenimcilik icin
    from ultralytics import YOLO
    model = YOLO(AGIRLIK)
    yolo_calistir(model, np.zeros((TUVAL[1], TUVAL[0], 3), np.uint8))   # isinma

    cikti = {
        "asama": "A5.2 - kucuk hedef benchmark'i (COCO pretrained YOLOv8n taban)",
        "sabitler": {"agirlik": AGIRLIK, "conf": CONF, "imgsz": IMGSZ,
                     "siniflar_coco": SINIFLAR, "tuval": list(TUVAL),
                     "cihaz": "cpu", "thread": 8,
                     "degisken": "YALNIZCA hedef yamasinin uzun kenari"},
        "letterbox": letterbox_dogrula(model),
        "diziler": {},
    }
    for dizi, tid, rol in DIZILER:
        ad = f"{dizi}/{tid}"
        print(f"\n=== {ad} ({rol}) ===", flush=True)
        kareler = kareleri_topla(dizi, tid, max(N_TESPIT, N_TAKIP))
        W, H = kareler[0][3], kareler[0][4]
        g0 = kareler[0][1]
        d = {"rol": rol, "kare_boyutu": [W, H],
             "native_gt": [float(g0[2]), float(g0[3])],
             "native_uzun_kenar": float(max(g0[2], g0[3]))}

        t = tespit_olc(model, kareler[:N_TESPIT], W, H)
        d["arkaplan_hucre"] = t["arkaplan_hucre"]
        d["hedeften_uzaklik_px"] = t["hedeften_uzaklik_px"]
        d["arkaplan_taban_tespit_kare_basina"] = t["arkaplan_taban_tespit_kare_basina"]
        d["tespit"] = t["seviyeler"]
        for k, v in t["seviyeler"].items():
            print(f"  TESPIT {k:8s} {v['ulasilan_w']:5.1f}x{v['ulasilan_h']:<5.1f} "
                  f"recall@.5={v['recall_iou50']} hit={v['recall_iou0']} "
                  f"IoU={v['ort_iou']} guven={v['ort_guven']} ekstra={v['ekstra_tespit']}",
                  flush=True)

        d["kompozit_kontrolu"] = kompozit_kontrolu(model, kareler,
                                                   tuple(t["arkaplan_hucre"]))
        print(f"  KOMPOZIT KONTROL: {d['kompozit_kontrolu']}", flush=True)

        d["takip"] = {}
        for sad, uzun in SEVIYELER:
            dizi_k, s = takip_dizisi(kareler[:N_TAKIP], tuple(t["arkaplan_hucre"]), uzun)
            r = {"olcek_s": round(s, 4), "sentetik_kare": len(dizi_k)}
            if len(dizi_k) >= 10:
                r["gt_tohumlu"] = takip_olc(model, dizi_k, "gt")
                r["yolo_tohumlu"] = takip_olc(model, dizi_k, "yolo")
            else:
                r["not"] = "hedef tuvalden cikti; dizi 10 kareden kisa"
            d["takip"][sad] = r
            g = r.get("gt_tohumlu", {}); y = r.get("yolo_tohumlu", {})
            print(f"  TAKIP  {sad:8s} kare={r['sentetik_kare']:3d}  "
                  f"GT-tohum: IoU={g.get('ort_iou')} kilit={g.get('kilit_orani')} "
                  f"drift={g.get('drift_karesi')} PSR={g.get('ort_psr')} | "
                  f"YOLO-tohum: kilit={y.get('kilit')} IoU={y.get('ort_iou')}",
                  flush=True)
        cikti["diziler"][ad] = d

    os.makedirs("cikti", exist_ok=True)
    yol = "cikti/a5_kucuk_hedef.json"
    if len(sys.argv) > 1:
        yol = sys.argv[1]
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print(f"\nyazildi: {yol}")


if __name__ == "__main__":
    main()
