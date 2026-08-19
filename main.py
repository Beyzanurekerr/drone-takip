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

from calistir import RENK, _kutu_ciz          # cizim ilkelerini yeniden kullan
from kaynak import KaynakHatasi, kaynak_olustur
from takip.izleyici import ARAMA, KAYIP, KILITLI, HedefTakip

ISINMA = 6          # hareket tespiti icin gecmis gerekiyor (ilk kareler bos doner)


def otomatik_hedef_sec(adaylar, kare):
    """Gecici otomatik hedef secimi: merkeze yakin ve buyuk olan aday.

    HEDEF SECIMI TAKILIP CIKARILABILIR: `kos(..., hedef_secici=...)` ile
    baska bir secici verilebilir. Sozlesme:

        secici(adaylar, kare) -> aday sozlugu | None

    Fare ile secim (Asama 5) ayni imzayi uygulayacak; dongude tek satir bile
    degismeyecek. Kaynaktan bagimsiz olmasi icin burada GT kullanilmaz
    (calistir.py'deki GT tabanli secim yalnizca olcum icindir).
    """
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


def ciz(img, kare, sonuc, adaylar, fps, kilitli, gecikme_ms=0.0,
        tur="kaynak", toplam=0):
    """Ekran ustu bilgi. Kaynak ne olursa olsun ayni; GT varsa ek olarak cizilir."""
    durum = sonuc["durum"]
    if kare.gt is not None and kare.gorunur:
        _kutu_ciz(img, kare.gt, (0, 255, 0), 1)                    # yesil: GT
    if (not kilitli) or durum in (ARAMA, KAYIP):
        for a in (adaylar or []):
            _kutu_ciz(img, a["kutu"], (255, 120, 0), 1)            # turuncu: aday
    if kilitli:
        _kutu_ciz(img, sonuc["kutu"], RENK.get(durum, (0, 0, 255)), 2)

    renk = RENK.get(durum, (255, 160, 0))
    if kilitli:
        ust = f"{durum}   PSR {sonuc['psr']:.1f}"
    else:
        ust = f"TARAMA   aday: {len(adaylar or [])}"
    cv2.putText(img, ust, (8, 18), 0, 0.5, renk, 1)

    takip_ms = sonuc.get("sure", {}).get("toplam", 0.0)
    cv2.putText(img, f"{fps:5.1f} FPS   islem {gecikme_ms:5.1f} ms   "
                     f"takip {takip_ms:4.1f} ms", (8, 36), 0, 0.45,
                (200, 200, 200), 1)
    sayac = f"{kare.indeks}/{toplam}" if toplam > 0 else str(kare.indeks)
    alt = (f"[{tur}]  {kare.kaynak_adi}  kare {sayac}  "
           f"{kare.genislik}x{kare.yukseklik} @ {kare.fps:.0f} fps")
    cv2.putText(img, alt, (8, img.shape[0] - 10), 0, 0.45, (255, 255, 255), 1)


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
    bekleme = max(1, int(1000.0 / kaynak.fps)) if kaynak.fps > 0 else 1

    if pencere:
        cv2.namedWindow(kaynak.ad, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(kaynak.ad, kaynak.genislik * 2, kaynak.yukseklik * 2)

    try:
        for kare in kaynak:
            t0 = time.perf_counter()
            adaylar = []
            if not kilitli:
                adaylar = tak.tarama(kare.goruntu)
                if kare.indeks >= ISINMA and adaylar:
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
            sureler.append(gecikme)
            gecikmeler.append(gecikme * 1e3)
            fps = len(sureler) / max(1e-6, sum(sureler))

            if pencere or kaydet:
                ciz(kare.goruntu, kare, sonuc, adaylar, fps, kilitli,
                    gecikme * 1e3, kaynak.tur, kaynak.kare_sayisi)
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
    return {
        "kaynak": kaynak.ad,
        "tur": kaynak.tur,
        "kare": len(gecikmeler),
        "kilitli": kilitli,
        "fps": float(1000.0 / g.mean()) if gecikmeler else 0.0,
        "gecikme_ort": float(g.mean()),
        "gecikme_p50": float(np.percentile(g, 50)),
        "gecikme_p95": float(np.percentile(g, 95)),
        "gecikme_max": float(g.max()),
    }


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
    ap.add_argument("--cekirdek", default="renk_dcf", help="renk_dcf | mosse | ncc | akis")
    ap.add_argument("--kaydet", default=None, help="cikti videosu yolu")
    ap.add_argument("--max-kare", type=int, default=0, dest="max_kare")
    ap.add_argument("--penceresiz", action="store_true", help="ekranda pencere acma")
    a = ap.parse_args()

    try:
        kaynak = kaynak_olustur(a.source, girdi=a.input,
                                kamera_id=a.camera_id, senaryo=a.scenario)
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
    if a.kaydet:
        print(f"  kayit       : {a.kaydet}")


if __name__ == "__main__":
    main()
