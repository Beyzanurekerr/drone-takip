"""A11.1/Y1 - renk_dcf doku-kaymasi Y1'in GERCEK yatakta hala var mi?
(A11_1_ONKAYIT.md, Y1 ek talebi.)

Kosum: python3 -m gazebo.tani_a11_1_dcf_kayma
Kapali cevrim, hakem=None, SAF DCF (A11 KOL0'daki H0 ile AYNI protokol):
kilit ilk karede GT'den alinir, sonrasi tamamen takipcinin kendi kararidir.

Cikti: cikti/a11_1_dcf_kayma_500k.json + IoU zaman serisi.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from calistir import iou                                    # noqa: E402
from gazebo.a11_ortak import kareleri_topla                  # noqa: E402
from gazebo.y1_ortak import yama_ici_mi                      # noqa: E402
from takip.izleyici import KILITLI, HedefTakip                # noqa: E402

SENARYO = "Y1_A1_taban_500k"
YANLIS_IOU = 0.2


def main():
    print(f"=== A11.1/Y1 renk_dcf doku-kaymasi: {SENARYO} ===")
    kareler, W, H, fx, fy, cx, cy = kareleri_topla(SENARYO)
    print(f"  {len(kareler)} kare yuklendi")

    ici_bayrak = [yama_ici_mi(satir["kam_x"], satir["kam_y"], satir["kam_z"], W, H, fx)
                 for _, _, satir in kareler]
    tumu_ici = all(ici_bayrak)
    print(f"  tamami yama-ici mi: {tumu_ici} ({sum(ici_bayrak)}/{len(ici_bayrak)})")

    tak = HedefTakip(hakem=None)
    img0, gt0, _ = kareler[0]
    tak.kilitle(img0, gt0.copy())

    seri = []
    for t in range(1, len(kareler)):
        img, gt, satir = kareler[t]
        s = tak.guncelle(img, None)          # KAPALI CEVRIM - GT verilmiyor
        o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
        seri.append({"t": t, "iou": round(o, 4), "durum": s["durum"],
                    "psr": round(float(s["psr"]), 3), "yama_ici": ici_bayrak[t]})

    kopus_karesi = None
    for x in seri:
        if x["durum"] == KILITLI and x["iou"] < YANLIS_IOU:
            kopus_karesi = x["t"]
            break

    kilitli_ve_yanlis = sum(1 for x in seri if x["durum"] == KILITLI and x["iou"] < YANLIS_IOU)
    kilitli_toplam = sum(1 for x in seri if x["durum"] == KILITLI)
    print(f"  ilk kopus karesi (KILITLI ama IoU<{YANLIS_IOU}): {kopus_karesi}")
    print(f"  KILITLI iken yanlis-kilit orani: {kilitli_ve_yanlis}/{kilitli_toplam} "
         f"({round(kilitli_ve_yanlis/max(kilitli_toplam,1),4)})")
    print(f"  IoU p50={round(float(np.percentile([x['iou'] for x in seri],50)),3)} "
         f"p95_dusuk={round(float(np.percentile([x['iou'] for x in seri],5)),3)}")

    sonuc = {"senaryo": SENARYO, "kare_sayisi": len(kareler),
            "tamami_yama_ici": tumu_ici, "yama_ici_kare": sum(ici_bayrak),
            "ilk_kopus_karesi": kopus_karesi,
            "kilitli_ve_yanlis_orani": round(kilitli_ve_yanlis / max(kilitli_toplam, 1), 4),
            "kilitli_toplam": kilitli_toplam, "kilitli_ve_yanlis": kilitli_ve_yanlis,
            "iou_zaman_serisi": seri}
    os.makedirs("cikti", exist_ok=True)
    with open("cikti/a11_1_dcf_kayma_500k.json", "w") as f:
        json.dump(sonuc, f, indent=2, ensure_ascii=False)
    print("yazildi: cikti/a11_1_dcf_kayma_500k.json")
    return sonuc


if __name__ == "__main__":
    main()
