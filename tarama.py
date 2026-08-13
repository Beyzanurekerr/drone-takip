"""Cekirdek ve parametre karsilastirmasi - 7 test uzerinde, paralel.

    python3 tarama.py                 -> cekirdek karsilastirmasi
    python3 tarama.py --izgara        -> parametre izgarasi (secili cekirdekle)
"""
import argparse
import itertools
from functools import partial
from multiprocessing import Pool

import numpy as np

from calistir import kos
from sim.senaryolar import TUM_TESTLER
from takip.izleyici import HedefTakip


def skor(m):
    return 0.5 * m["basari@0.5"] + 0.5 * m["kilit_orani"] - 0.03 * m["id_switch"]


def _tek(is_, ):
    ad, konf = is_
    sen = TUM_TESTLER[ad]()
    m = kos(sen, video=None, sessiz=True, yap_takipci=partial(HedefTakip, **konf))
    m.pop("_kayit", None)
    return ad, m


def kos_konfigler(konfigler, isci=8):
    """konfigler: {etiket: kwargs}. Doner: {etiket: {test: metrik}}."""
    isler = [(etiket, ad, konf) for etiket, konf in konfigler.items() for ad in TUM_TESTLER]
    with Pool(isci) as p:
        sonuclar = p.map(_tek, [(ad, konf) for _, ad, konf in isler])
    out = {e: {} for e in konfigler}
    for (etiket, ad, _), (_, m) in zip(isler, sonuclar):
        out[etiket][ad] = m
    return out


def ozet(baslik, sonuclar):
    print(f"\n=== {baslik} ===")
    print(f"{'konfig':30s} {'skor':>6s} {'IoU':>6s} {'@0.5':>6s} {'@0.3':>6s} {'kilit':>6s} "
          f"{'IDsw':>5s} {'FPS':>6s}")
    sira = sorted(sonuclar.items(), key=lambda kv: -np.mean([skor(m) for m in kv[1].values()]))
    for etiket, s in sira:
        print(f"{etiket:30s} {np.mean([skor(m) for m in s.values()]):6.3f} "
              f"{np.mean([m['ort_iou'] for m in s.values()]):6.3f} "
              f"{np.mean([m['basari@0.5'] for m in s.values()]):6.1%} "
              f"{np.mean([m['basari@0.3'] for m in s.values()]):6.1%} "
              f"{np.mean([m['kilit_orani'] for m in s.values()]):6.1%} "
              f"{sum(m['id_switch'] for m in s.values()):5d} "
              f"{np.mean([m['fps'] for m in s.values()]):6.0f}")
    return sira[0]


def detay(etiket, s):
    print(f"\n--- {etiket} test bazinda ---")
    for ad, m in s.items():
        print(f"  {ad:8s} IoU {m['ort_iou']:.3f}  @0.5 {m['basari@0.5']:6.1%}  "
              f"@0.3 {m['basari@0.3']:6.1%}  kilit {m['kilit_orani']:6.1%}  "
              f"IDsw {m['id_switch']}  kurtarma {m['kurtarma_ort']:.0f}k  {m['fps']:.0f} FPS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--izgara", action="store_true")
    ap.add_argument("--cekirdek", default="mosse")
    ap.add_argument("--isci", type=int, default=8)
    a = ap.parse_args()

    if a.izgara:
        konfigler = {}
        for dg, pk in itertools.product([0, 3, 6, 12], [None]):
            konfigler[f"{a.cekirdek} dogr={dg}"] = dict(cekirdek=a.cekirdek,
                                                        dogrulama_araligi=dg)
        for cst in [4, 8, 16]:
            konfigler[f"{a.cekirdek} coast={cst}"] = dict(cekirdek=a.cekirdek, coast_kare=cst)
    else:
        konfigler = {c: dict(cekirdek=c) for c in ["mosse", "renk_dcf", "ncc", "akis"]}

    s = kos_konfigler(konfigler, a.isci)
    en_iyi = ozet("karsilastirma", s)
    detay(en_iyi[0], en_iyi[1])


if __name__ == "__main__":
    main()
