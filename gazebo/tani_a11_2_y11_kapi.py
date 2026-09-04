"""A11.2/Y1.1 - kapi YENIDEN ON-KAYITLI: "Gazebo recall, A6'nin GERCEK VERI
recall'unun +-0.10 icinde" (40px tam kare+ROI, 20px ROI). A6 TEK model
(COCO dustu - Y1'de tam kor cikmisti, gercek veride de degerlendirilecek
bir dedektor degil).

ESKI 0.80 KAPISI NEDEN HATALIYDI (belgede de var, burada da olculdu):
A6_KUCUK_HEDEF_FINAL_BENCHMARK.md'nin GERCEK VisDrone recall@IoU>=0.5
tablosu (uav0000117_02622_v/23 ve uav0000137_00458_v/12, A6 UAVDT+VisDrone
suutunu):
    40x15 px : 0.900 (117/23) / 0.600 (137/12) -> ortalama 0.750
    20x10 px : 0.050 (117/23) / 0.375 (137/12) -> ortalama 0.2125
Yani modelin KENDI GERCEK EGITIM/DOGRULAMA VERISINDE bile 20px'te recall
0.05-0.375 araliginda - "Gazebo'da 20px'te >=0.80 olsun" sabit kapisi
gercek dunyada model bunu HICBIR ZAMAN basaramadigi icin ULASILAMAZ bir
bardi. Dogru soru "simulasyon gercek veriyle TUTARLI mi", "simulasyon
gercek veriden daha mi iyi/kotu" degil.

Kosum: python3 -m gazebo.tani_a11_2_y11_kapi
Cikti: cikti/a11_2_y11_kapi.json
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

from gazebo.tani_a11_1_y1 import pencere_recall, veri_topla            # noqa: E402
from gazebo.y1_ortak import (MODELLER, esle, recall_tablosu,           # noqa: E402
                             roi_dortx_tespit, tam_kare_tespit, yolo_yukle)

GATE_40, GATE_20, GATE_PAY = 40.0, 20.0, 5.0
# A6_KUCUK_HEDEF_FINAL_BENCHMARK.md SS2 tablosu, UAVDT+VisDrone sutunu,
# iki birincil dizinin (117/23, 137/12) ortalamasi:
GERCEK_REF_40PX = (0.900 + 0.600) / 2.0          # 0.750
GERCEK_REF_20PX = (0.050 + 0.375) / 2.0          # 0.2125
TOLERANS = 0.10


def degerlendir(recall, referans):
    if recall is None:
        return {"referans": referans, "fark": None, "gecti": False,
               "not": "orneklem yok"}
    fark = round(recall - referans, 4)
    return {"referans": referans, "fark": fark, "gecti": abs(fark) <= TOLERANS}


def main():
    print("=== A11.2/Y1.1 kapi YENIDEN OLCUMU (A6 tek model, genisletilmis yama) ===")
    kayit, ic_toplam, tasma_toplam = veri_topla()
    toplam = ic_toplam + tasma_toplam
    print(f"  toplam kare: {toplam} | yama-ici: {ic_toplam} "
         f"({round(ic_toplam/toplam,3) if toplam else None}) | tasma: {tasma_toplam}")
    print(f"  GT gorunur + yama-ici orneklem: {len(kayit)}")

    agirlik = yolo_yukle(MODELLER["A6"]["agirlik"])
    siniflar = MODELLER["A6"]["siniflar"]
    tam_LD, roi_LD = [], []
    for i, (ad, img, gt, L) in enumerate(kayit):
        kutular, _, _ = tam_kare_tespit(agirlik, img, siniflar)
        d, _ = esle(kutular, gt)
        tam_LD.append((L, d))

        merkez = (gt[0] + gt[2] / 2.0, gt[1] + gt[3] / 2.0)
        kutular_r, _, _ = roi_dortx_tespit(agirlik, img, merkez, siniflar)
        d_r, _ = esle(kutular_r, gt)
        roi_LD.append((L, d_r))
        if (i + 1) % 300 == 0:
            print(f"    {i+1}/{len(kayit)}")

    g40_tam = pencere_recall(tam_LD, GATE_40, GATE_PAY)
    g40_roi = pencere_recall(roi_LD, GATE_40, GATE_PAY)
    g20_roi = pencere_recall(roi_LD, GATE_20, GATE_PAY)

    sonuc = {
        "tasma": {"toplam_kare": toplam, "yama_ici": ic_toplam,
                 "tasma": tasma_toplam,
                 "tasma_orani": round(tasma_toplam/toplam, 4) if toplam else None},
        "gercek_referans": {"40px": GERCEK_REF_40PX, "20px": GERCEK_REF_20PX,
                            "tolerans": TOLERANS,
                            "kaynak": "A6_KUCUK_HEDEF_FINAL_BENCHMARK.md, "
                                     "117/23 + 137/12 ortalamasi"},
        "tam_kare_tablo": recall_tablosu(tam_LD),
        "roi_4x_tablo": recall_tablosu(roi_LD),
        "kapi": {
            "tam_kare_40px": {**g40_tam, **degerlendir(g40_tam["recall"], GERCEK_REF_40PX)},
            "roi_40px": {**g40_roi, **degerlendir(g40_roi["recall"], GERCEK_REF_40PX)},
            "roi_20px": {**g20_roi, **degerlendir(g20_roi["recall"], GERCEK_REF_20PX)},
        },
    }
    for ad, k in sonuc["kapi"].items():
        print(f"  {ad}: n={k['n']} recall={k['recall']} referans={k['referans']} "
             f"fark={k.get('fark')} -> {'GECTI' if k['gecti'] else 'KALDI'}")

    genel = all(v["gecti"] for v in sonuc["kapi"].values())
    sonuc["genel_kapi_gecti"] = genel
    print(f"\n=== GENEL KAPI (Y1.1, A6, +-0.10): {'GECTI' if genel else 'KALDI'} ===")

    os.makedirs("cikti", exist_ok=True)
    with open("cikti/a11_2_y11_kapi.json", "w") as f:
        json.dump(sonuc, f, indent=2, ensure_ascii=False)
    print("yazildi: cikti/a11_2_y11_kapi.json")
    return sonuc


if __name__ == "__main__":
    main()
