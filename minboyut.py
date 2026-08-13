"""Minimum takip boyutu deneyi: cekirdekleri kucuk hedef rejiminde kiyaslar.

test3 (irtifa 35 -> 470 m ustel rampa) birden fazla gurultu tohumuyla kosulur,
sonuclar hedef genisligine gore kovalanir. Cikti: her cekirdegin UCURUMU.

    python3 minboyut.py
"""
from functools import partial
from multiprocessing import Pool

import numpy as np

from calistir import kos
from kiyasla import boyut_egrisi, hukum
from sim.senaryolar import test3_cok_kucuk
from takip.izleyici import HedefTakip

TOHUMLAR = (7, 21, 99)
CEKIRDEKLER = ["mosse", "renk_dcf", "ncc"]


def _is(arg):
    cekirdek, tohum = arg
    m = kos(test3_cok_kucuk(seed=tohum), sessiz=True,
            yap_takipci=partial(HedefTakip, cekirdek=cekirdek))
    return cekirdek, m["_kayit"], m["fps"]


def main():
    isler = [(c, t) for c in CEKIRDEKLER for t in TOHUMLAR]
    with Pool(min(9, len(isler))) as p:
        ham = p.map(_is, isler)

    birles = {c: [] for c in CEKIRDEKLER}
    fpsler = {c: [] for c in CEKIRDEKLER}
    for c, kayit, fps in ham:
        birles[c] += kayit
        fpsler[c].append(fps)

    print("=" * 92)
    print("MINIMUM TAKIP BOYUTU - CEKIRDEK KARSILASTIRMASI")
    print(f"(test3 irtifa rampasi, {len(TOHUMLAR)} gurultu tohumu, kova basina ~150 kare)")
    print("=" * 92)
    ucurum = {}
    for c in CEKIRDEKLER:
        egri = boyut_egrisi(birles[c])
        print(f"\n--- {c} ---")
        print(f"{'hedef px':>16s} {'kare':>6s} {'IoU':>6s} {'hassasiyet':>11s} "
              f"{'merkez hata':>12s}   hukum")
        son_iyi = None
        for s in egri:
            h = hukum(s)
            if h == "BASARILI":
                son_iyi = s
            print(f"{s['ort_px']:7.1f}x{s['ort_py']:<8.1f} {s['n']:6d} {s['iou']:6.3f} "
                  f"{s['hassasiyet']:11.1%} {s['merkez_hata']:10.2f}px   {h}")
        ucurum[c] = son_iyi

    print("\n" + "=" * 92)
    print("SONUC - her cekirdegin takip edebildigi EN KUCUK hedef")
    print("=" * 92)
    for c in CEKIRDEKLER:
        s = ucurum[c]
        if s is None:
            print(f"  {c:10s} -> hicbir kovada basarili degil")
        else:
            print(f"  {c:10s} -> {s['ort_px']:.1f} x {s['ort_py']:.1f} px  "
                  f"(IoU {s['iou']:.2f}, merkez hata {s['merkez_hata']:.2f} px)  "
                  f"| {np.mean(fpsler[c]):.0f} FPS")


if __name__ == "__main__":
    main()
