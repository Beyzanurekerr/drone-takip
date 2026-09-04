"""A11.1/Y1 - yatak kapisi olcumu.

Kosum: python3 -m gazebo.tani_a11_1_y1
Cikti: cikti/a11_1_y1_kapi.json + ekrana ozet.

ON-KAYIT: docs/architecture/A11_1_ONKAYIT.md.
  - Kapi: dedektor tam kare recall @40px(+-5) >=0.8, ROI(4x,R=160) @20px(+-5)
    >=0.8, IKI modelde de (COCO, A6) AYRI AYRI raporlanir.
  - Yalnizca YAMA-ICI kareler (feather HARIC) kapiya girer; tasma orani ayri.
  - renk_dcf doku-kaymasi: Y1_A1_taban_500k'nin TAMAMI yama-ici mi dogrulanir,
    sonra H0-esdeger kapali cevrim (hakem=None, saf DCF) IoU zaman serisi
    cikarilir.
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

from calistir import iou                                              # noqa: E402
from gazebo.a11_ortak import kareleri_topla                            # noqa: E402
from gazebo.y1_ortak import (MODELLER, esle, recall_tablosu,           # noqa: E402
                             roi_dortx_tespit, tam_kare_tespit, yama_ici_mi,
                             yolo_yukle)

SENARYOLAR = ["Y1_A1_taban", "Y1_A2_kucul", "Y1_A3_yaw", "Y1_A4_irtifa",
             "Y1_A5_kucul_yaw", "Y1_A6_celdirici"]
GATE_40, GATE_20, GATE_PAY = 40.0, 20.0, 5.0     # +-5 px pencere
KAPI_ESIK = 0.80


def veri_topla():
    """Tum senaryolardan (img, gt, yama_ici, L) - yalnizca gt gorunur olan."""
    kayit = []
    tasma_toplam, ic_toplam = 0, 0
    for ad in SENARYOLAR:
        kareler, W, H, fx, fy, cx, cy = kareleri_topla(ad)
        for img, gt, satir in kareler:
            ici = yama_ici_mi(satir["kam_x"], satir["kam_y"], satir["kam_z"], W, H, fx)
            if ici:
                ic_toplam += 1
            else:
                tasma_toplam += 1
            if gt is None or not ici:
                continue          # kapi + recall SADECE yama-ici, gt gorunur
            kayit.append((ad, img, gt, float(np.max(gt[2:]))))
    return kayit, ic_toplam, tasma_toplam


def pencere_recall(kayit_LD, merkez, pay):
    """[merkez-pay, merkez+pay] penceresindeki (L, dogru) ciftlerinden recall."""
    alt = [d for L, d in kayit_LD if merkez - pay <= L <= merkez + pay]
    if not alt:
        return {"n": 0, "recall": None}
    r = sum(alt) / len(alt)
    return {"n": len(alt), "recall": round(r, 4)}


def main():
    print("=== A11.1/Y1 kapi olcumu ===")
    print("Veri toplaniyor (6 senaryo, sadece yama-ici + GT gorunur kareler)...")
    kayit, ic_toplam, tasma_toplam = veri_topla()
    toplam = ic_toplam + tasma_toplam
    tasma_orani = round(tasma_toplam / toplam, 4) if toplam else None
    print(f"  toplam kare: {toplam} | yama-ici: {ic_toplam} | tasma: {tasma_toplam} "
         f"(oran {tasma_orani})")
    print(f"  GT gorunur + yama-ici orneklem: {len(kayit)}")

    sonuc = {"tasma": {"toplam_kare": toplam, "yama_ici": ic_toplam,
                       "tasma": tasma_toplam, "tasma_orani": tasma_orani},
             "modeller": {}, "kapi": {}}

    for model_ad in MODELLER:
        print(f"\n--- {model_ad} ---")
        agirlik = yolo_yukle(MODELLER[model_ad]["agirlik"])
        siniflar = MODELLER[model_ad]["siniflar"]
        tam_LD, roi_LD = [], []
        ms_tam, ms_roi = [], []
        for i, (ad, img, gt, L) in enumerate(kayit):
            kutular, _, ms = tam_kare_tespit(agirlik, img, siniflar)
            d, _ = esle(kutular, gt)
            tam_LD.append((L, d)); ms_tam.append(ms)

            merkez = (gt[0] + gt[2] / 2.0, gt[1] + gt[3] / 2.0)
            kutular_r, _, ms_r = roi_dortx_tespit(agirlik, img, merkez, siniflar)
            d_r, _ = esle(kutular_r, gt)
            roi_LD.append((L, d_r)); ms_roi.append(ms_r)
            if (i + 1) % 200 == 0:
                print(f"    {i+1}/{len(kayit)}")

        g40 = pencere_recall(tam_LD, GATE_40, GATE_PAY)
        g20 = pencere_recall(roi_LD, GATE_20, GATE_PAY)
        gecti_40 = g40["recall"] is not None and g40["recall"] >= KAPI_ESIK
        gecti_20 = g20["recall"] is not None and g20["recall"] >= KAPI_ESIK
        print(f"  tam-kare @40px+-5: n={g40['n']} recall={g40['recall']} "
             f"-> {'GECTI' if gecti_40 else 'KALDI'}")
        print(f"  ROI4x    @20px+-5: n={g20['n']} recall={g20['recall']} "
             f"-> {'GECTI' if gecti_20 else 'KALDI'}")

        sonuc["modeller"][model_ad] = {
            "tam_kare_tablo": recall_tablosu(tam_LD),
            "roi_4x_tablo": recall_tablosu(roi_LD),
            "tam_kare_ms_p50": round(float(np.percentile(ms_tam, 50)), 2),
            "roi_4x_ms_p50": round(float(np.percentile(ms_roi, 50)), 2),
        }
        sonuc["kapi"][model_ad] = {
            "tam_kare_40px": {**g40, "gecti": gecti_40},
            "roi_20px": {**g20, "gecti": gecti_20},
            "gecti": gecti_40 and gecti_20,
        }

    genel_gecti = all(v["gecti"] for v in sonuc["kapi"].values())
    sonuc["genel_kapi_gecti"] = genel_gecti
    print(f"\n=== GENEL KAPI: {'GECTI' if genel_gecti else 'KALDI'} ===")

    os.makedirs("cikti", exist_ok=True)
    with open("cikti/a11_1_y1_kapi.json", "w") as f:
        json.dump(sonuc, f, indent=2, ensure_ascii=False)
    print("yazildi: cikti/a11_1_y1_kapi.json")
    return sonuc


if __name__ == "__main__":
    main()
