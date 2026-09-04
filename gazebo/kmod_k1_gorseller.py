"""K-MOD/K1 gorsel ciktilari - gazebo/gorsel_uret.py'yi cagirir (kendi cizim
kodunu yazmaz). tani_kmod_k1.py'nin olcum mantigini (S1/S2/S3, rafine,
d_norm) BIREBIR tekrar eder ama bu sefer gorsel_uret'in bekledigi zengin
kare-kaydini da tutar.

Kosum: python3 -m gazebo.kmod_k1_gorseller
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from calistir import iou                                    # noqa: E402
from gazebo.a11_ortak import kareleri_topla                  # noqa: E402
from gazebo.gorsel_uret import (kare_izgara_uret, ozet_tablo_uret,  # noqa: E402
                                video_uret, zaman_serisi_uret)
from gazebo.tani_kmod_k1 import (S2_N, DOGRU_IOU, YANLIS_IOU,  # noqa: E402
                                 _hucre, _s1, _s2, _s3)
from gazebo.y1_ortak import MODELLER, yolo_yukle                     # noqa: E402
from takip.egomotion import EgoMotion                          # noqa: E402
from takip.izleyici import Kalman                               # noqa: E402
from takip.tespit import HareketTespit, rafine_kutu               # noqa: E402
from collections import deque                                   # noqa: E402

DENEY = "kmod_k1"


def kol_olc_gorsel(kareler, kol, model, siniflar):
    tespit, ego = HareketTespit(), EgoMotion()
    kalman, ref_wh = None, None
    hucre_gecmisi = deque(maxlen=S2_N - 1)
    kayit = []

    for img, gt, satir in kareler:
        gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        M, _ = ego.guncelle(gri, gt if gt is not None else None)
        if gt is None:
            tespit.kare_ekle(gri, M)
            continue
        gt_c = gt[:2] + gt[2:] / 2.0
        gt_L = float(np.max(gt[2:]))
        if kalman is None:
            kalman = Kalman(gt_c[0], gt_c[1])
            ref_wh = gt[2:].copy()
        else:
            kalman.tahmin(M)

        adaylar, hareket_maske = tespit.adaylar(gri, M)
        rec = {"img": img, "gt": gt.tolist(), "gt_L": gt_L,
              "adaylar": [tuple(a["merkez"]) for a in adaylar],
              "hareket_haritasi": hareket_maske,
              "kanit_var": bool(adaylar)}

        if not adaylar:
            rec.update(sistem_kutu=None, secilen_xy=None, durum="kanit_yok", iou=None)
        else:
            ref_merkez = kalman.konum
            dt = 1.0 / 30.0
            secilen = (_s1(adaylar, ref_merkez, ref_wh, dt)[0] if kol == "S1"
                      else _s2(adaylar, ref_merkez, ref_wh, dt, hucre_gecmisi))
            if secilen is not None:
                r = rafine_kutu(img, secilen["merkez"], ref_wh)
                if r is not None:
                    secilen = {**secilen, "kutu": r, "merkez": r[:2] + r[2:] / 2.0}
            roi_kutu = None
            if kol == "S3":
                if secilen is not None:
                    rw, rh = 80, int(round(80 * 9.0 / 16.0))
                    cx, cy = secilen["merkez"]
                    roi_kutu = [cx - rw / 2, cy - rh / 2, rw, rh]
                secilen = _s3(secilen, model, siniflar, img)
            if secilen is None:
                rec.update(sistem_kutu=None, secilen_xy=None, roi_kutu=roi_kutu, durum="cekimser", iou=None)
            else:
                o = float(iou(secilen["kutu"], gt))
                durum = "dogru" if o >= DOGRU_IOU else ("yanlis" if o < YANLIS_IOU else "belirsiz")
                rec.update(sistem_kutu=secilen["kutu"].tolist(), secilen_xy=tuple(secilen["merkez"]),
                          roi_kutu=roi_kutu, durum=durum, iou=round(o, 4),
                          yanlis_kilit=(durum == "yanlis"))
        kayit.append(rec)
        hucre_gecmisi.append({_hucre(a["merkez"]) for a in adaylar})
        kalman.duzelt(gt_c)
        ref_wh = gt[2:].copy()
        tespit.kare_ekle(gri, M)
    return kayit


def main():
    agirlik = yolo_yukle(MODELLER["A6"]["agirlik"])
    siniflar = MODELLER["A6"]["siniflar"]
    uretilen = []

    for senaryo in ["Y1_A7_kucuk", "Y1_A8_cok_kucuk"]:
        kareler, *_ = kareleri_topla(senaryo)
        for kol in ["S1", "S3"]:      # en bilgilendirici ikisi: en iyi (S1) ve dedektorun coktugu (S3)
            print(f"--- {senaryo} / {kol} gorseli uretiliyor ---")
            kayit = kol_olc_gorsel(kareler, kol, agirlik, siniflar)
            v = video_uret(DENEY, senaryo, kol, kayit)
            z = zaman_serisi_uret(DENEY, senaryo, kol, kayit)
            g = kare_izgara_uret(DENEY, senaryo, kol, kayit)
            uretilen += [v, z, g]
            print("  ", v, z, g)
        # "sadece hareket haritasi" videosu (K1'e ozel talep)
        kayit_s1 = kol_olc_gorsel(kareler, "S1", agirlik, siniflar)
        hv = video_uret(DENEY, senaryo, "S1", kayit_s1, sadece_hareket_haritasi=True)
        uretilen.append(hv)
        print("  hareket haritasi:", hv)

    with open("cikti/kmod_k1.json") as f:
        k1 = json.load(f)
    satirlar = [{"kol": kol, "8x5 kapisi (dogru>=0.8, yanlis<=0.05)": k1["kapi_8x5"][kol]["gecti"]}
               for kol in ["S1", "S2", "S3"]]
    t = ozet_tablo_uret(DENEY, satirlar)
    uretilen.append(t)
    print("ozet tablo:", t)

    print(f"\nToplam {len([u for u in uretilen if u])} gorsel dosyasi uretildi -> cikti/gorsel/{DENEY}/")


if __name__ == "__main__":
    main()
