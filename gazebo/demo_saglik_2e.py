"""DEMO_DALI Adim 2e - saglik kapisi: A6, 80 m'den 100 karede ROI-4x recall.

Talimat: "@=40 px" varsayimi eski arastirma kamerasinin (odak_px~500-780)
kalintisi olabilir - gazebo/kamera_imx500.sdf'nin GERCEK IMX500 odagi
(1561 px) 80 m'de hedefi ~80 px yapiyor (GT'den OLCULDU, asagida
raporlanir). Bu script hem VARSAYILAN 80 m/100 kare olcumunu hem GERCEK
hedef boyutunu YAZAR - hicbir sayi gizlenmez.

Kosum: python3 -m gazebo.demo_saglik_2e [--senaryo Demo_celdirici]
"""
import argparse
import os
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from calistir import iou                        # noqa: E402
from veri.gazebo import GazeboKaynak              # noqa: E402

A6_AGIRLIK = "weights/a6_kucuk_hedef.pt"
A6_SINIFLAR = [0, 1, 2, 3]      # VisDrone: car,van,truck,bus
CONF, IMGSZ = 0.25, 640
AG = (640, 360)                 # aga verilen ROI kare boyutu (A7/A8 ile ayni)
BUYUTME = 4.0
ALT_ESIK, UST_ESIK = 0.65, 0.85


def roi_kirp_buyut(img, merkez, R):
    H, W = img.shape[:2]
    rw, rh = int(R), int(round(R * 9.0 / 16.0))
    x0 = int(round(merkez[0] - rw / 2.0))
    y0 = int(round(merkez[1] - rh / 2.0))
    x0 = max(0, min(W - rw, x0))
    y0 = max(0, min(H - rh, y0))
    parca = img[y0:y0 + rh, x0:x0 + rw]
    if parca.shape[:2] != (rh, rw):
        return None, None
    girdi = cv2.resize(parca, AG, interpolation=cv2.INTER_AREA)
    return girdi, (x0, y0, rw, rh)


def geri_donustur(kutu_ag, roi):
    x0, y0, rw, rh = roi
    kx, ky = rw / float(AG[0]), rh / float(AG[1])
    return np.array([kutu_ag[0] * kx + x0, kutu_ag[1] * ky + y0,
                     kutu_ag[2] * kx, kutu_ag[3] * ky], np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--senaryo", default="Demo_celdirici")
    ap.add_argument("--kok", default="data/gazebo")
    a = ap.parse_args()

    from ultralytics import YOLO
    model = YOLO(A6_AGIRLIK)

    k = GazeboKaynak(kok=a.kok, senaryo=a.senaryo)
    Ls, dogru, ms_l = [], 0, []
    n = 0
    for kare in k:
        if kare.gt is None:
            continue
        gt = np.asarray(kare.gt, np.float32)
        L = float(max(gt[2], gt[3]))
        Ls.append(L)
        merkez = (gt[0] + gt[2] / 2.0, gt[1] + gt[3] / 2.0)
        # ROI-4x: AG[0]/R = 4 -> R = 160 (A7/A8/Y1.1/Y1.2'nin "roi_dortx"
        # ile AYNI R=160 sabiti - hedef boyutundan BAGIMSIZ SABIT kirpim
        # genisligi, sonra AG=(640,360)'a buyutulunce 4x buyutme cikar).
        R = AG[0] / BUYUTME
        girdi, roi = roi_kirp_buyut(kare.goruntu, merkez, R)
        if girdi is None:
            n += 1
            continue
        t0 = time.perf_counter()
        r = model.predict(girdi, conf=CONF, imgsz=IMGSZ, classes=A6_SINIFLAR,
                          verbose=False, device="cpu")[0]
        ms_l.append((time.perf_counter() - t0) * 1e3)
        buldu = False
        if r.boxes is not None and len(r.boxes):
            for (x1, y1, x2, y2) in r.boxes.xyxy.cpu().numpy():
                kutu = geri_donustur(np.array([x1, y1, x2 - x1, y2 - y1], np.float32), roi)
                if iou(kutu, gt) >= 0.5:
                    buldu = True
                    break
        dogru += int(buldu)
        n += 1

    recall = dogru / n if n else None
    L_p50 = float(np.percentile(Ls, 50)) if Ls else None
    print(f"senaryo={a.senaryo} n={n} dogru={dogru} recall={recall}")
    print(f"hedef L (px) p50={L_p50:.1f} (VARSAYILAN '~40px' DEGIL - "
         f"gercek IMX500 odagi 1561px ile 80 m'de boyle cikiyor)")
    if ms_l:
        print(f"ms/kare (ROI+YOLO) p50={np.percentile(ms_l,50):.1f}")
    if recall is None:
        print("SAGLIK KAPISI: OLCULEMEDI (n=0)")
    elif ALT_ESIK <= recall <= UST_ESIK:
        print(f"SAGLIK KAPISI: GECTI ({ALT_ESIK}-{UST_ESIK} icinde)")
    else:
        print(f"SAGLIK KAPISI: KALDI (beklenen [{ALT_ESIK},{UST_ESIK}], "
             f"olculen {recall:.3f}) - NOT: 40px varsayimiyla degil, "
             f"gercek {L_p50:.0f}px hedef boyutuyla olculdu, DUR gerekcesi budur")


if __name__ == "__main__":
    main()
