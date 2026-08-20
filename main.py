"""Kaynak-bagimsiz calistirici: simulator / video / kamera -> ayni takip hatti.

    python3 main.py --source sim    --scenario test6
    python3 main.py --source video  --input data/test.mp4
    python3 main.py --source camera --camera-id 0

Takip tarafi (takip/izleyici.py) goruntunun nereden geldigini BILMEZ; bu dosyada
da `if video: ... if sim: ...` gibi bir dallanma yoktur. Tek fark, simulator
kaynagi yaninda ground-truth kutusu da tasidigi icin ekranda yesil GT cizilir.

Olcum ve kiyaslama icin `kiyasla.py` / `calistir.py` kullanilmaya devam edilir;
bu dosya onlarin yerini ALMAZ, yaninda durur.
"""
import argparse
import os
import sys
import time
from collections import deque

import cv2
import numpy as np

from calistir import RENK, _kutu_ciz, iou     # cizim ve olcum ilkelerini yeniden kullan
from kaynak import KaynakHatasi, kaynak_olustur
from takip.izleyici import ARAMA, KAYIP, KILITLI, HedefTakip

ISINMA = 6          # hareket tespiti icin gecmis gerekiyor (ilk kareler bos doner)
PENCERE_KUTUSU = (960, 540)     # baslangic penceresi bu kutuya sigar


def pencere_boyutu(genislik, yukseklik, kutu=PENCERE_KUTUSU):
    """Baslangic pencere boyutu: en-boy orani korunarak `kutu` icine sigdirilir.

    Ekrani kaplamasin diye; kullanici sonrasinda fareyle serbestce
    boyutlandirabilir (WINDOW_NORMAL). Kaynak cozunurlugu ne olursa olsun
    (sim 640x480, VisDrone 960x540 ya da 3840x2160) pencere ayni boyda acilir.
    """
    if genislik <= 0 or yukseklik <= 0:
        return kutu
    k = min(kutu[0] / genislik, kutu[1] / yukseklik)
    return max(160, int(round(genislik * k))), max(120, int(round(yukseklik * k)))


def gt_hedef_sec(adaylar, kare):
    """Ground-truth ile hedef secimi: GT kutusu varsa onu baslangic kutusu yap.

    Yalnizca KILIT ANINDA kullanilir; sonraki karelerde takipci kendi tahminiyle
    ilerler, GT'ye bir daha bakilmaz. Gercek veri kumelerinde adil SOT olcumu
    icin sart: aksi halde takipci rastgele bir nesneye kilitlenir ve IoU
    anlamsiz olur.
    """
    if kare.gt is None:
        return None
    kutu = np.asarray(kare.gt, np.float32)
    return {"kutu": kutu, "merkez": kutu[:2] + kutu[2:] / 2.0,
            "alan": float(kutu[2] * kutu[3])}


def otomatik_hedef_sec(adaylar, kare):
    """Varsayilan secici: GT varsa GT kutusu, yoksa merkeze yakin buyuk aday.

    Dallanma kaynak TIPINE degil, VERININ varligina bakar - bu yuzden dongu
    kaynak-bagimsiz kalir.

    HEDEF SECIMI TAKILIP CIKARILABILIR: `kos(..., hedef_secici=...)` ile
    baska bir secici verilebilir. Sozlesme:

        secici(adaylar, kare) -> aday sozlugu | None

    Fare ile secim (Asama 5) ayni imzayi uygulayacak; dongude tek satir bile
    degismeyecek. Kaynaktan bagimsiz olmasi icin burada GT kullanilmaz
    (calistir.py'deki GT tabanli secim yalnizca olcum icindir).
    """
    if kare.gt is not None:
        return gt_hedef_sec(adaylar, kare)
    if not adaylar:
        return None
    merkez = np.array([kare.genislik / 2.0, kare.yukseklik / 2.0], np.float32)
    kosegen = float(np.hypot(kare.genislik, kare.yukseklik))
    en_iyi, en_skor = None, -1.0
    for a in adaylar:
        d = float(np.linalg.norm(a["merkez"] - merkez))
        skor = a["alan"] / (1.0 + 2.0 * d / kosegen)
        if skor > en_skor:
            en_iyi, en_skor = a, skor
    return en_iyi


# --- HUD -------------------------------------------------------------------
# Yazi KAYNAK piksellerine cizilir, pencere ise `pencere_boyutu` ile 960x540
# kutusuna sigdirilir. Sabit font kullanilirsa 3840x2160 bir VisDrone dizisinde
# yazi ekranda 4 kat kucuk gorunur ve okunmaz. Bu yuzden font olcegi ve
# kalinlik cozunurlukle birlikte buyutulur: HUD her kaynakta AYNI boyda
# gorunur. Buradaki hicbir sey olcume girmez - sadece gorsellestirme.
FONT = cv2.FONT_HERSHEY_SIMPLEX
HUD_TABAN = 0.62         # 960x540 penceresinde govde yazisinin font olcegi
HUD_ALT_SINIR = 0.75     # kucuk kaynakta yaziyi bundan fazla kucultme
GT_RENK = (0, 220, 0)    # GT hep yesil; takip kutusu durum rengini kullanir
ADAY_RENK = (255, 120, 0)
BILGI_RENK = (235, 235, 235)


def hud_olcek(genislik, yukseklik, kutu=PENCERE_KUTUSU):
    """Cozunurluge gore font/kalinlik carpani.

    Pencere `kutu` icine k = min(kutu_w/W, kutu_h/H) orani ile sigdiriliyor;
    yazi da ayni kuculmeye ugruyor. 1/k ile carparak telafi edilir:
    960x540 -> 1.00 · 1904x1071 -> 1.98 · 3840x2160 -> 4.00 ·
    640x480 (4:3) -> 0.89 · 320x240 -> alt sinir 0.75.
    """
    if genislik <= 0 or yukseklik <= 0:
        return 1.0
    return max(HUD_ALT_SINIR, genislik / kutu[0], yukseklik / kutu[1])


def _yaz(img, metin, konum, olcek, renk, kalinlik):
    """Siyah kontur + renkli govde: acik asfaltta da koyu golgede de okunur."""
    cv2.putText(img, metin, konum, FONT, olcek, (0, 0, 0),
                kalinlik + 2 * max(1, kalinlik // 2), cv2.LINE_AA)
    cv2.putText(img, metin, konum, FONT, olcek, renk, kalinlik, cv2.LINE_AA)


def _panel(img, x0, y0, x1, y1, alfa=0.55):
    """Yazi blogunun arkasini karart - konturun tek basina yetmedigi zemine."""
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(img.shape[1], int(x1)), min(img.shape[0], int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    roi = img[y0:y1, x0:x1]
    roi[:] = (roi * (1.0 - alfa)).astype(img.dtype)


def _etiket(img, metin, x, y, renk, olcek, kalinlik, ped, ust=True):
    """Kutu kosesine dolu renkli rozet + siyah yazi.

    GT ile takip kutusu iki eksende birden ayrilir: RENK (yesil / durum rengi)
    ve KONUM (GT ustte, TAKIP altta). Tek eksen kucuk hedefte yetmiyor.
    """
    (tw, th), _ = cv2.getTextSize(metin, FONT, olcek, kalinlik)
    kw, kh = tw + 2 * ped, th + 2 * ped
    x0 = int(min(max(0, x), max(0, img.shape[1] - kw)))
    y0 = int(y - kh) if ust else int(y)
    y0 = int(min(max(0, y0), max(0, img.shape[0] - kh)))
    cv2.rectangle(img, (x0, y0), (x0 + kw, y0 + kh), renk, -1)
    cv2.putText(img, metin, (x0 + ped, y0 + kh - ped), FONT, olcek,
                (0, 0, 0), kalinlik, cv2.LINE_AA)


def ciz(img, kare, sonuc, adaylar, fps, kilitli, gecikme_ms=0.0,
        tur="kaynak", toplam=0, hedef_id=None):
    """Ekran ustu bilgi. Kaynak ne olursa olsun ayni; GT varsa ek olarak cizilir.

    Yalnizca gorsellestirme: hicbir metrik burada hesaplanmaz, `sonuc` sozlugu
    degistirilmez.
    """
    durum = sonuc["durum"]
    h, w = img.shape[:2]
    s = hud_olcek(w, h)
    f_govde = HUD_TABAN * s
    f_baslik = 0.92 * s
    f_etiket = 0.55 * s
    kal = max(1, int(round(2 * s)))
    ped = max(3, int(round(5 * s)))
    renk = RENK.get(durum, (255, 160, 0))

    # --- kutular ---
    if kare.gt is not None and kare.gorunur:
        _kutu_ciz(img, kare.gt, GT_RENK, max(1, int(round(1.5 * s))))
        _etiket(img, "GT", int(kare.gt[0]), int(kare.gt[1]), GT_RENK,
                f_etiket, kal, max(2, ped // 2), ust=True)
    if (not kilitli) or durum in (ARAMA, KAYIP):
        for a in (adaylar or []):
            _kutu_ciz(img, a["kutu"], ADAY_RENK, max(1, int(round(s))))
    if kilitli and sonuc["kutu"] is not None:
        _kutu_ciz(img, sonuc["kutu"], renk, max(2, int(round(2.5 * s))))
        tk = sonuc["kutu"]
        _etiket(img, "TAKIP", int(tk[0]), int(tk[1] + tk[3]), renk,
                f_etiket, kal, max(2, ped // 2), ust=False)

    # --- sol ust bilgi blogu ---
    baslik = durum if kilitli else "TARAMA"
    takip_ms = sonuc.get("sure", {}).get("toplam", 0.0)
    sayac = f"{kare.indeks}/{toplam}" if toplam > 0 else str(kare.indeks)
    ikinci = f"kare {sayac}"
    if hedef_id is not None:
        ikinci += f"   hedef #{hedef_id}"
    ikinci += (f"   PSR {sonuc['psr']:.1f}" if kilitli
               else f"   aday {len(adaylar or [])}")
    satirlar = [
        (f"FPS {fps:.1f}   gecikme {gecikme_ms:.1f} ms   takip {takip_ms:.1f} ms",
         BILGI_RENK),
        (ikinci, BILGI_RENK),
    ]
    if sonuc.get("iou") is not None:          # GT'den gelen olcu -> GT rengi
        satirlar.append((f"IoU {sonuc['iou']:.2f}   "
                         f"merkez hata {sonuc['merkez_hata']:.1f} px", GT_RENK))

    (bw, bh), _ = cv2.getTextSize(baslik, FONT, f_baslik, kal + 1)
    olcu = [cv2.getTextSize(t, FONT, f_govde, kal)[0] for t, _ in satirlar]
    genis = max([bw] + [m[0] for m in olcu])
    satir_h = int(round(max(m[1] for m in olcu) * 2.0))
    x_metin = ped + ped // 2
    y = ped + bh
    _panel(img, 0, 0, genis + 3 * ped, y + len(satirlar) * satir_h + ped)
    _yaz(img, baslik, (x_metin, y), f_baslik, renk, kal + 1)
    for metin, c in satirlar:
        y += satir_h
        _yaz(img, metin, (x_metin, y), f_govde, c, kal)

    # --- sol alt kaynak satiri ---
    alt = (f"[{tur}]  {kare.kaynak_adi}  "
           f"{kare.genislik}x{kare.yukseklik} @ {kare.fps:.0f} fps")
    (aw, ah), _ = cv2.getTextSize(alt, FONT, f_govde, kal)
    _panel(img, 0, h - ah - 2 * ped, aw + 3 * ped, h)
    _yaz(img, alt, (x_metin, h - ped), f_govde, BILGI_RENK, kal)


def goster(pencere, img, bekleme_ms, duraklat):
    """Doner: "devam" | "duraklat" | "cik".  Bosluk duraklat, n tek kare, q cik."""
    cv2.imshow(pencere, img)
    while True:
        tus = cv2.waitKey(0 if duraklat else bekleme_ms) & 0xFF
        if tus in (27, ord("q")):
            return "cik"
        if tus == ord(" "):
            duraklat = not duraklat
            if not duraklat:
                return "devam"
            continue
        if duraklat and tus in (ord("n"), 83):
            return "duraklat"
        if not duraklat:
            return "devam"


def kos(kaynak, cekirdek="renk_dcf", pencere=True, kaydet=None, max_kare=0,
        hedef_secici=None):
    """Kaynak-bagimsiz calisma dongusu.

    `hedef_secici`: None ise `otomatik_hedef_sec` kullanilir. Fare ile secim
    geldiginde buraya baska bir fonksiyon verilecek; dongu degismeyecek.
    """
    secici = hedef_secici or otomatik_hedef_sec
    tak = HedefTakip(cekirdek=cekirdek)
    kilitli = False
    yaz = None
    duraklat = False
    sureler = deque(maxlen=30)      # anlik FPS icin kayan pencere
    gecikmeler = []                 # tum kareler: p50 / p95 icin
    olcum = []                      # GT varsa kare kare: iou, merkez hata, durum
    kayip_basi, kurtarmalar = None, []
    bekleme = max(1, int(1000.0 / kaynak.fps)) if kaynak.fps > 0 else 1
    hedef_id = getattr(kaynak, "track_id", None)   # VisDrone track; yoksa None

    if pencere:
        # WINDOW_NORMAL  : kullanici fareyle boyutlandirabilsin
        # WINDOW_KEEPRATIO: elle boyutlandirirken en-boy orani korunsun
        cv2.namedWindow(kaynak.ad, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        cv2.resizeWindow(kaynak.ad, *pencere_boyutu(kaynak.genislik,
                                                    kaynak.yukseklik))

    try:
        for kare in kaynak:
            t0 = time.perf_counter()
            adaylar = []
            if not kilitli:
                adaylar = tak.tarama(kare.goruntu)
                if kare.indeks >= ISINMA:
                    secili = secici(adaylar, kare)
                    if secili is not None:
                        kutu = secili["kutu"].copy()
                        kutu[2:] = np.maximum(kutu[2:] - 2.0, 4.0)   # dilate telafisi
                        kutu[:2] = secili["merkez"] - kutu[2:] / 2
                        tak.kilitle(kare.goruntu, kutu)
                        kilitli = True
                sonuc = {"kutu": tak.kutu, "durum": tak.durum, "psr": 0.0, "sure": {}}
            else:
                sonuc = tak.guncelle(kare.goruntu)
                adaylar = tak.son_adaylar
            gecikme = time.perf_counter() - t0          # islem: takip (cizim haric)

            # --- GT varsa olcum (kaynaktan bagimsiz) ---
            sonuc["iou"] = sonuc["merkez_hata"] = None
            if kilitli and kare.gt is not None and kare.gorunur:
                sonuc["iou"] = iou(sonuc["kutu"], kare.gt)
                tk, gt = sonuc["kutu"], kare.gt
                sonuc["merkez_hata"] = float(np.hypot(
                    tk[0] + tk[2] / 2 - (gt[0] + gt[2] / 2),
                    tk[1] + tk[3] / 2 - (gt[1] + gt[3] / 2)))
                kilit = sonuc["durum"] == KILITLI and sonuc["iou"] > 0.2
                if not kilit and kayip_basi is None:
                    kayip_basi = kare.indeks
                elif kilit and kayip_basi is not None:
                    kurtarmalar.append(kare.indeks - kayip_basi)
                    kayip_basi = None
                olcum.append({
                    "kare": kare.indeks, "iou": sonuc["iou"],
                    "merkez_hata": sonuc["merkez_hata"],
                    "durum": sonuc["durum"],
                    "gt_w": float(gt[2]), "gt_h": float(gt[3])})

            sureler.append(gecikme)
            gecikmeler.append(gecikme * 1e3)
            fps = len(sureler) / max(1e-6, sum(sureler))

            if pencere or kaydet:
                ciz(kare.goruntu, kare, sonuc, adaylar, fps, kilitli,
                    gecikme * 1e3, kaynak.tur, kaynak.kare_sayisi,
                    hedef_id=hedef_id)
                if kaydet:
                    if yaz is None:
                        os.makedirs(os.path.dirname(kaydet) or ".", exist_ok=True)
                        yaz = cv2.VideoWriter(
                            kaydet, cv2.VideoWriter_fourcc(*"mp4v"),
                            kaynak.fps if kaynak.fps > 0 else 30.0,
                            (kare.genislik, kare.yukseklik))
                    yaz.write(kare.goruntu)
                if pencere:
                    cevap = goster(kaynak.ad, kare.goruntu, bekleme, duraklat)
                    if cevap == "cik":
                        break
                    duraklat = (cevap == "duraklat")

            if max_kare and kare.indeks + 1 >= max_kare:
                break
    finally:
        kaynak.kapat()
        if yaz is not None:
            yaz.release()
        if pencere:
            cv2.destroyWindow(kaynak.ad)

    g = np.array(gecikmeler, np.float64) if gecikmeler else np.zeros(1)
    m = {
        "kaynak": kaynak.ad,
        "tur": kaynak.tur,
        "kare": len(gecikmeler),
        "kilitli": kilitli,
        "fps": float(1000.0 / g.mean()) if gecikmeler else 0.0,
        "gecikme_ort": float(g.mean()),
        "gecikme_p50": float(np.percentile(g, 50)),
        "gecikme_p95": float(np.percentile(g, 95)),
        "gecikme_max": float(g.max()),
        "gt_kare": len(olcum),
    }
    if olcum:
        io = np.array([r["iou"] for r in olcum], np.float64)
        mh = np.array([r["merkez_hata"] for r in olcum], np.float64)
        kos = np.array([np.hypot(r["gt_w"], r["gt_h"]) for r in olcum], np.float64)
        m.update({
            "ort_iou": float(io.mean()),
            "basari@0.5": float((io > 0.5).mean()),
            "basari@0.3": float((io > 0.3).mean()),
            "merkez_hata": float(np.median(mh)),
            "hassasiyet": float((mh < np.maximum(4.0, 0.5 * kos)).mean()),
            "kilit_orani": float(np.mean([r["durum"] == KILITLI for r in olcum])),
            "hedef_kayip": float(np.mean([r["durum"] != KILITLI for r in olcum])),
            "kesinti": len(kurtarmalar),
            "kurtarma_ort": float(np.mean(kurtarmalar)) if kurtarmalar else 0.0,
            "kurtarma_max": int(max(kurtarmalar)) if kurtarmalar else 0,
            "gt_boyut": (float(np.mean([r["gt_w"] for r in olcum])),
                         float(np.mean([r["gt_h"] for r in olcum]))),
            "_olcum": olcum,
        })
    return m


def main():
    ap = argparse.ArgumentParser(
        description="Drone hedef takip - simulator / video / kamera",
        epilog="ornek: python3 main.py --source data/videos/drone_traffic_01.mp4")
    ap.add_argument("--source", default="sim",
                    help="sim | sim:test6 | camera | camera:1 | <video dosyasi yolu>")
    ap.add_argument("--input", default=None,
                    help="video dosyasi yolu (eski bicim: --source video ile)")
    ap.add_argument("--camera-id", type=int, default=0, dest="camera_id")
    ap.add_argument("--scenario", default="test1", help="sim senaryosu (test1..test7)")
    ap.add_argument("--dataset", default=None,
                    help="veri kumesi kok klasoru (varsayilan: data/datasets/visdrone_vid)")
    ap.add_argument("--sequence", default=None, help="VisDrone dizi adi")
    ap.add_argument("--track-id", type=int, default=None, dest="track_id",
                    help="hedef track id (verilmezse en uzun arac track'i)")
    ap.add_argument("--olcek", type=float, default=1.0, help="downscale carpani")
    ap.add_argument("--hedef-genislik", type=int, default=0, dest="hedef_genislik",
                    help="kareyi bu genislige indir (olcek'ten oncelikli)")
    ap.add_argument("--cekirdek", default="renk_dcf", help="renk_dcf | mosse | ncc | akis")
    ap.add_argument("--kaydet", default=None, help="cikti videosu yolu")
    ap.add_argument("--max-kare", type=int, default=0, dest="max_kare")
    ap.add_argument("--penceresiz", action="store_true", help="ekranda pencere acma")
    a = ap.parse_args()

    try:
        kaynak = kaynak_olustur(a.source, girdi=a.input,
                                kamera_id=a.camera_id, senaryo=a.scenario,
                                veri_kok=a.dataset, dizi=a.sequence,
                                track_id=a.track_id, olcek=a.olcek,
                                hedef_genislik=a.hedef_genislik)
    except KaynakHatasi as e:
        print(f"HATA: {e}")
        sys.exit(1)

    print(kaynak.bilgi())
    try:
        m = kos(kaynak, cekirdek=a.cekirdek, pencere=not a.penceresiz,
                kaydet=a.kaydet, max_kare=a.max_kare)
    except KaynakHatasi as e:
        print(f"HATA: {e}")
        sys.exit(1)
    print("-" * 58)
    print(f"  kaynak      : {m['kaynak']}  ({m['tur']})")
    print(f"  islenen kare: {m['kare']}")
    print(f"  hedef       : {'KILITLENDI' if m['kilitli'] else 'kilitlenmedi'}")
    print(f"  FPS         : {m['fps']:.1f}")
    print(f"  gecikme     : ort {m['gecikme_ort']:.2f} ms | "
          f"p50 {m['gecikme_p50']:.2f} | p95 {m['gecikme_p95']:.2f} | "
          f"max {m['gecikme_max']:.2f}")
    if m.get("gt_kare"):
        print(f"  --- GT ile olcum ({m['gt_kare']} kare) ---")
        print(f"  IoU         : {m['ort_iou']:.3f}  "
              f"(@0.5 {m['basari@0.5']:.1%} | @0.3 {m['basari@0.3']:.1%})")
        print(f"  merkez hata : {m['merkez_hata']:.2f} px  "
              f"(hassasiyet {m['hassasiyet']:.1%})")
        print(f"  kilit orani : {m['kilit_orani']:.1%}  "
              f"(hedef kayip {m['hedef_kayip']:.1%})")
        print(f"  kurtarma    : {m['kesinti']} kesinti, "
              f"ort {m['kurtarma_ort']:.0f} kare, max {m['kurtarma_max']} kare")
        print(f"  hedef boyut : {m['gt_boyut'][0]:.1f} x {m['gt_boyut'][1]:.1f} px")
    if a.kaydet:
        print(f"  kayit       : {a.kaydet}")


if __name__ == "__main__":
    main()
