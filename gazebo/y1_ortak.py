"""A11.1/Y1 - yatak kapisi olcumu icin paylasilan yardimcilar.

Icerdigi:
  yama_ici_mi     - kamera gorus alani (kosegen yaricapi, yaw'a karsi tutucu)
                     gercek-doku yamasinin (feather HARIC, SAF gercek piksel)
                     icinde mi? DISINDA olan kareler kapiya/renk_dcf zaman
                     serisine GIRMEZ (ust talimat: "yalnizca yama-ici
                     karelerden, tasma orani ayri raporlanir").
  MODELLER        - COCO (weights/yolov8n.pt) + A6 (runs/a6/asamaB/weights/
                     best.pt), on-kayitli iki model.
  yolo_yukle      - ultralytics.YOLO yukler (once import hatasi net mesajla).
  tam_kare_tespit - dogrudan 640x480 kare uzerinde tespit.
  roi_dortx_tespit - a11_ortak.roi_tespit_g ile 4x buyutme (R=160, A7'nin
                     "roi320"/1280px-sensor karsiligi 640px Gazebo karesine
                     olceklendi - bkz. A11_1_ONKAYIT.md).
  recall_tablosu  - GT L=max(w,h) kovalarina gore recall@IoU>=0.5.
"""
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from calistir import iou                                            # noqa: E402
from gazebo.a11_ortak import roi_tespit_g, roi_wh                    # noqa: E402
from gazebo.dunya_uret import fov_hesapla, yama_dunya_sinirlari       # noqa: E402
from gazebo.senaryolar import A11_DOKU_PX, A11_ZEMIN_M               # noqa: E402

CONF, IMGSZ = 0.25, 640     # A6_KUCUK_HEDEF_FINAL_BENCHMARK.md ile AYNI protokol
ROI_R = 160                 # 640px Gazebo karesinde 4x buyutme (A7'nin 1280px
                            # sensorundeki roi320/4x'ine ORANSAL karsilik - bkz.
                            # A11_1_ONKAYIT.md "ROI protokolu" notu)

MODELLER = {
    "COCO": dict(agirlik="weights/yolov8n.pt", siniflar=[2, 3, 5, 7]),
    "A6": dict(agirlik="runs/a6/asamaB/weights/best.pt", siniflar=[0, 1, 2, 3]),
}


def yolo_yukle(agirlik):
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise RuntimeError(
            "ultralytics kurulu degil (requirements.txt: pip install ultralytics "
            "+ torch cpu wheel)") from e
    yol = os.path.join(ROOT, agirlik)
    if not os.path.exists(yol):
        raise FileNotFoundError(f"agirlik yok: {yol}")
    return YOLO(yol)


def yolo_calistir(model, img, siniflar):
    t0 = time.perf_counter()
    r = model.predict(img, conf=CONF, imgsz=IMGSZ, classes=siniflar,
                      verbose=False, device="cpu")[0]
    ms = (time.perf_counter() - t0) * 1e3
    kutular, guvenler = [], []
    if r.boxes is not None and len(r.boxes):
        for (x1, y1, x2, y2), g in zip(r.boxes.xyxy.cpu().numpy(),
                                       r.boxes.conf.cpu().numpy()):
            kutular.append(np.array([x1, y1, x2 - x1, y2 - y1], np.float32))
            guvenler.append(float(g))
    return kutular, guvenler, ms


def tam_kare_tespit(model, img, siniflar):
    return yolo_calistir(model, img, siniflar)


def roi_dortx_tespit(model, img, merkez, siniflar, R=None):
    """A7/A8 ROI geometrisiyle AYNI (kirp->AG->YOLO->geri donustur).
    Varsayilan R=ROI_R=160 (640px Gazebo karesinde 4x, Y1.1/Y1.2 kapisi).
    `R` acikca verilirse (orn. K-MOD/K1'in R=80'i) onu kullanir. `merkez`:
    GT merkezi ya da (K1) secilen aday merkezi - cagiran belirler."""
    R = ROI_R if R is None else R

    def _calistir(_model, im):
        return yolo_calistir(model, im, siniflar)
    return roi_tespit_g(model, img, merkez, R, _calistir)


# --------------------------------------------------------------------------
# YAMA KAPSAMI
# --------------------------------------------------------------------------
def yama_ici_mi(kam_x, kam_y, kam_z, genislik, yukseklik, odak_px):
    """Kameranin gorus alani (kosegen yaricapiyla tutucu tahmin, yaw'dan
    bagimsiz) tamamen SAF gercek doku bolgesinde mi (feather bandi haric)?"""
    x_min, x_max, y_min, y_max = yama_dunya_sinirlari(
        A11_DOKU_PX, A11_ZEMIN_M, temiz=True)
    fov_h = fov_hesapla(genislik, odak_px)
    fov_v = fov_hesapla(yukseklik, odak_px)
    yaricap = kam_z * math.hypot(math.tan(fov_h / 2.0), math.tan(fov_v / 2.0))
    return (x_min <= kam_x - yaricap and kam_x + yaricap <= x_max
            and y_min <= kam_y - yaricap and kam_y + yaricap <= y_max)


def dikis_yakini_mi(kam_x, kam_y, kam_z, genislik, yukseklik, odak_px):
    """Kamera GERCEKTEN yamayi gorurken (kendisi yama sinirlari icindeyken),
    gorus alani IC DIKISLERDEN (2x2 izgaranin kesisim cizgileri) birinin
    yaricap kadar yakinina giriyor mu? `kam_z` disari cikinca (yuksek
    irtifa) yaricap dev buyuyup dikisi "uzaktan" kapsayabilir - bu YAMAYI
    HIC GORMEDEN "dikise yakin" saymak anlamsiz olurdu, o yuzden once
    KAMERANIN KENDISI yama sinirlari icinde mi kontrol edilir (yama_ici_mi
    ile AYNI 'tam' sinir, ama nokta-icinde testi, yaricap-genisletilmis
    degil)."""
    from gazebo.dunya_uret import GERCEK_ZEMIN_MERKEZ_M
    x_min, x_max, y_min, y_max = yama_dunya_sinirlari(
        A11_DOKU_PX, A11_ZEMIN_M, temiz=False)
    if not (x_min <= kam_x <= x_max and y_min <= kam_y <= y_max):
        return False
    dikis_x, dikis_y = GERCEK_ZEMIN_MERKEZ_M
    fov_h = fov_hesapla(genislik, odak_px)
    fov_v = fov_hesapla(yukseklik, odak_px)
    yaricap = kam_z * math.hypot(math.tan(fov_h / 2.0), math.tan(fov_v / 2.0))
    dikey_dikis = (x_min <= dikis_x <= x_max) and (abs(kam_x - dikis_x) <= yaricap)
    yatay_dikis = (y_min <= dikis_y <= y_max) and (abs(kam_y - dikis_y) <= yaricap)
    return bool(dikey_dikis or yatay_dikis)


# --------------------------------------------------------------------------
# RECALL TABLOSU
# --------------------------------------------------------------------------
KOVALAR = [(0, 10, "5x2_ve_alti"), (10, 15, "10x5"), (15, 20, "15x7"),
          (20, 25, "20x10"), (25, 35, "30x12"), (35, 50, "40x15"),
          (50, 70, "60x22"), (70, 1e9, "70_ustu")]


def kova_ad(L):
    for lo, hi, ad in KOVALAR:
        if lo <= L < hi:
            return ad
    return "?"


def recall_tablosu(kayitlar):
    """kayitlar: [(gt_L, dogru_mu)] -> {kova_ad: (n, dogru, recall)}."""
    grup = {}
    for L, dogru in kayitlar:
        ad = kova_ad(L)
        grup.setdefault(ad, [0, 0])
        grup[ad][0] += 1
        grup[ad][1] += int(bool(dogru))
    return {ad: (n, d, round(d / n, 4) if n else None) for ad, (n, d) in grup.items()}


def esle(tespitler, gt):
    """GT ile en yuksek IoU'lu tespiti dondur (IoU>=0.5 -> dogru)."""
    if gt is None or not len(tespitler):
        return False, 0.0
    best = max((iou(t, gt) for t in tespitler), default=0.0)
    return best >= 0.5, best
