"""VisDrone gercek hava goruntusu uzerinde degerlendirme.

Simulasyon benchmark'indan (kiyasla.py) TAMAMEN AYRIDIR: farkli dosya, farkli
rapor, farkli sayilar. Ikisi birbirine karistirilmamalidir -
  * kiyasla.py       -> kontrollu sentetik ortam, hedef boyutu supurmesi
  * visdrone_kiyasla -> gercek goruntu, gercek kamera hareketi, gercek gurultu

    python3 visdrone_kiyasla.py                       # varsayilan dizi
    python3 visdrone_kiyasla.py --sequence uav0000305_00000_v --track-id 30
    python3 visdrone_kiyasla.py --hepsi               # 7 dizi, otomatik hedef
    python3 visdrone_kiyasla.py --hepsi --rapor       # RAPOR_VISDRONE.md yaz

ID switch olculmez: sistemde henuz gercek MOT yok (tek hedef takip ediliyor).
BoT-SORT / ByteTrack entegrasyonundan sonra eklenecek.
"""
import argparse
import time

import numpy as np

import main
from kaynak import KaynakHatasi, kaynak_olustur
from veri.visdrone import diziler

VARSAYILAN_KOK = "data/datasets/visdrone_vid"
VARSAYILAN_GENISLIK = 960


def kos_dizi(kok, dizi, track_id=None, hedef_genislik=VARSAYILAN_GENISLIK,
             max_kare=0, cekirdek="renk_dcf", kaydet=None, sessiz=False):
    kaynak = kaynak_olustur("visdrone", veri_kok=kok, dizi=dizi,
                            track_id=track_id, hedef_genislik=hedef_genislik)
    if not sessiz:
        print(f"  {kaynak.bilgi()}")
    m = main.kos(kaynak, cekirdek=cekirdek, pencere=False, kaydet=kaydet,
                 max_kare=max_kare)
    m["dizi"] = dizi
    m["track_id"] = kaynak.track_id
    m["ham"] = f"{kaynak.ham_genislik}x{kaynak.ham_yukseklik}"
    m["olcek"] = kaynak.olcek
    m["cozunurluk"] = f"{kaynak.genislik}x{kaynak.yukseklik}"
    return m


BASLIK = (f"{'dizi':22s} {'trk':>4s} {'kare':>5s} {'IoU':>6s} {'@0.5':>7s} "
          f"{'@0.3':>7s} {'hassas':>7s} {'mrkz.px':>8s} {'kilit':>7s} "
          f"{'p50':>6s} {'p95':>6s} {'FPS':>6s}")


def satir(m):
    return (f"{m['dizi']:22s} {m['track_id']:4d} {m['gt_kare']:5d} "
            f"{m.get('ort_iou', 0):6.3f} {m.get('basari@0.5', 0):7.1%} "
            f"{m.get('basari@0.3', 0):7.1%} {m.get('hassasiyet', 0):7.1%} "
            f"{m.get('merkez_hata', 0):8.2f} {m.get('kilit_orani', 0):7.1%} "
            f"{m['gecikme_p50']:6.2f} {m['gecikme_p95']:6.2f} {m['fps']:6.0f}")


def rapor_yaz(sonuclar, hedef_genislik, yol="RAPOR_VISDRONE.md"):
    L = ["# VisDrone Gercek Hava Goruntusu - Sonuc Raporu", "",
         "Bu rapor SIMULASYON baseline'indan bagimsizdir; `RAPOR.md` ile",
         "karistirilmamalidir. Olculen sistem ayni klasik takip hattidir",
         "(ego-motion + renk_dcf + Kalman + durum makinesi); tek fark girdi.", "",
         f"- Veri kumesi: VisDrone2019-VID-val",
         f"- Kareler {hedef_genislik} px genislige indirildi, GT kutulari ayni oranda olceklendi",
         "- Hedef, track'in ilk karesindeki GT kutusuyla kilitlenir; sonraki",
         "  karelerde GT yalnizca OLCUM icin kullanilir, takipciye beslenmez",
         "- Hedef track otomatik secilir: en uzun sure gorunen ve HAREKET EDEN arac",
         "- ID switch olculmez (sistemde henuz MOT yok)", "",
         "## Sonuclar", "",
         "| dizi | track | kare | IoU | @0.5 | @0.3 | hassasiyet | merkez hata | kilit | p50 ms | p95 ms | FPS |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in sonuclar:
        L.append(
            f"| {m['dizi']} | {m['track_id']} | {m['gt_kare']} | "
            f"{m.get('ort_iou', 0):.3f} | {m.get('basari@0.5', 0):.0%} | "
            f"{m.get('basari@0.3', 0):.0%} | {m.get('hassasiyet', 0):.0%} | "
            f"{m.get('merkez_hata', 0):.2f} px | {m.get('kilit_orani', 0):.0%} | "
            f"{m['gecikme_p50']:.2f} | {m['gecikme_p95']:.2f} | {m['fps']:.0f} |")
    if len(sonuclar) > 1:
        ort = {k: float(np.mean([m.get(k, 0) for m in sonuclar]))
               for k in ("ort_iou", "basari@0.5", "hassasiyet", "kilit_orani", "fps")}
        L += ["", f"**Ortalama:** IoU {ort['ort_iou']:.3f} | "
                  f"@0.5 {ort['basari@0.5']:.0%} | "
                  f"hassasiyet {ort['hassasiyet']:.0%} | "
                  f"kilit {ort['kilit_orani']:.0%} | {ort['fps']:.0f} FPS"]
    L += ["", "## Hedef boyutlari ve kurtarma", "",
          "| dizi | ham cozunurluk | islenen | hedef boyut (px) | kesinti | ort kurtarma |",
          "|---|---|---|---|---|---|"]
    for m in sonuclar:
        b = m.get("gt_boyut", (0, 0))
        L.append(f"| {m['dizi']} | {m['ham']} | {m['cozunurluk']} | "
                 f"{b[0]:.1f} x {b[1]:.1f} | {m.get('kesinti', 0)} | "
                 f"{m.get('kurtarma_ort', 0):.0f} kare |")
    L += ["", "hassasiyet = merkez hatasinin hedef kosegeninin yarisindan kucuk",
          "oldugu kare orani.", ""]
    with open(yol, "w") as f:
        f.write("\n".join(L) + "\n")
    return yol


def main_cli():
    ap = argparse.ArgumentParser(description="VisDrone gercek veri degerlendirmesi")
    ap.add_argument("--dataset", default=VARSAYILAN_KOK)
    ap.add_argument("--sequence", default="uav0000305_00000_v")
    ap.add_argument("--track-id", type=int, default=None, dest="track_id")
    ap.add_argument("--hedef-genislik", type=int, default=VARSAYILAN_GENISLIK,
                    dest="hedef_genislik")
    ap.add_argument("--max-kare", type=int, default=0, dest="max_kare")
    ap.add_argument("--cekirdek", default="renk_dcf")
    ap.add_argument("--kaydet", default=None, help="cikti videosu yolu")
    ap.add_argument("--hepsi", action="store_true", help="tum dizileri kos")
    ap.add_argument("--rapor", action="store_true", help="RAPOR_VISDRONE.md yaz")
    a = ap.parse_args()

    try:
        hedefler = diziler(a.dataset) if a.hepsi else [a.sequence]
    except KaynakHatasi as e:
        print(f"HATA: {e}")
        raise SystemExit(1)

    print("=" * len(BASLIK))
    print("VISDRONE GERCEK VERI DEGERLENDIRMESI  (sim baseline'dan bagimsiz)")
    print("=" * len(BASLIK))
    t0 = time.time()
    sonuclar = []
    for d in hedefler:
        try:
            m = kos_dizi(a.dataset, d, track_id=a.track_id,
                         hedef_genislik=a.hedef_genislik, max_kare=a.max_kare,
                         cekirdek=a.cekirdek, kaydet=a.kaydet)
        except KaynakHatasi as e:
            print(f"  {d}: ATLANDI - {e}")
            continue
        if not m.get("gt_kare"):
            print(f"  {d}: ATLANDI - hedef hic kilitlenemedi")
            continue
        sonuclar.append(m)

    if not sonuclar:
        print("hicbir dizi olculemedi")
        raise SystemExit(1)

    print("\n" + BASLIK)
    print("-" * len(BASLIK))
    for m in sonuclar:
        print(satir(m))
    if len(sonuclar) > 1:
        print("-" * len(BASLIK))
        ort = {k: float(np.mean([m.get(k, 0) for m in sonuclar]))
               for k in ("ort_iou", "basari@0.5", "basari@0.3", "hassasiyet",
                         "merkez_hata", "kilit_orani", "gecikme_p50",
                         "gecikme_p95", "fps")}
        print(f"{'ORTALAMA':22s} {'':>4s} {sum(m['gt_kare'] for m in sonuclar):5d} "
              f"{ort['ort_iou']:6.3f} {ort['basari@0.5']:7.1%} "
              f"{ort['basari@0.3']:7.1%} {ort['hassasiyet']:7.1%} "
              f"{ort['merkez_hata']:8.2f} {ort['kilit_orani']:7.1%} "
              f"{ort['gecikme_p50']:6.2f} {ort['gecikme_p95']:6.2f} {ort['fps']:6.0f}")
    print(f"\ntoplam sure {time.time() - t0:.1f} s")

    if a.rapor:
        yol = rapor_yaz(sonuclar, a.hedef_genislik)
        print(f"-> {yol} yazildi")


if __name__ == "__main__":
    main_cli()
