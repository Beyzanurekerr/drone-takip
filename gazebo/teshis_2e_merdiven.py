"""2e-TESHIS EK: A8 merdiveniyle (adaptif ROI) yeniden olcum.

teshis_2e_px_bandi.py sabit ROI-4x kullanmisti (R=160 her irtifada) ve
80/120m'de girdi 210-319px'e sisip cokmustu. Bu betik A8'in ORIJINAL
tasariminin (silinmis `gazebo/tani_a8_adaptif_roi.py`, git tarihi 03c15f5~1)
R_sec mantigini AYNEN tasir: merdivenden ({640,320,160,80} sensor-px ROI
genisligi) hedefi ag girdisinde NET_HEDEF'e (bant ortasi, LOG uzayinda) en
yakin getiren basamak secilir. Bant burada [55,110] (eski A8'in 60-90'i
DEGIL - kullanicinin bu tur icin verdigi yeni bant).

Hicbir mevcut dosya degistirilmedi (`teshis_2e_px_bandi.py`'den yalnizca
okunan yardimcilar import edilir), yeni kayit gerekmez (mevcut
Demo_celdirici/Teshis2e_120m/Teshis2e_160m kullanilir).

Kosum: python3 -m gazebo.teshis_2e_merdiven
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from calistir import iou                                          # noqa: E402
from veri.gazebo import GazeboKaynak                               # noqa: E402
from gazebo.teshis_2e_px_bandi import MODELLER, IRTIFALAR, CONF, IMGSZ, FULL_W, _tam_kadraj_girdi  # noqa: E402

AG = (640, 360)
MERDIVEN = [640, 320, 160, 80]     # sensor-px ROI genisligi (A8 ile AYNI)
BANT = (55.0, 110.0)               # kullanicinin bu tur icin verdigi bant
NET_HEDEF = sum(BANT) / 2.0        # 82.5 - log-uzayinda ortalama nokta
NATIVE_W = 2028                    # gazebo/kamera_imx500.sdf genisligi


def roi_wh(R):
    return int(R), int(round(R * 9.0 / 16.0))


def R_sec(L_native):
    """MERDIVEN'den, LOG uzayinda NET_HEDEF'e en yakin basamagi sec.

    A8'in R_sec'iyle AYNI formul (bkz. dosya basligi): buyutme carpimsal
    bir buyukluktur, log mesafe bandi (carpimsal olarak simetrik) dogru
    olcer.
    """
    if L_native is None or not np.isfinite(L_native) or L_native <= 0:
        return MERDIVEN[0]
    return min(MERDIVEN,
               key=lambda R: abs(np.log((L_native * AG[0] / float(R)) / NET_HEDEF)))


def roi_kirp(img, merkez, R):
    H, W = img.shape[:2]
    rw, rh = roi_wh(R)
    x0 = int(round(merkez[0] - rw / 2.0))
    y0 = int(round(merkez[1] - rh / 2.0))
    x0 = max(0, min(W - rw, x0))
    y0 = max(0, min(H - rh, y0))
    parca = img[y0:y0 + rh, x0:x0 + rw]
    if parca.shape[:2] != (rh, rw):
        return None, None
    interp = cv2.INTER_LINEAR if rw < AG[0] else cv2.INTER_AREA
    girdi = cv2.resize(parca, AG, interpolation=interp)
    return girdi, (x0, y0, rw, rh)


def geri_donustur(kutu_ag, roi):
    x0, y0, rw, rh = roi
    kx, ky = rw / float(AG[0]), rh / float(AG[1])
    return np.array([kutu_ag[0] * kx + x0, kutu_ag[1] * ky + y0,
                     kutu_ag[2] * kx, kutu_ag[3] * ky], np.float32)


def _degerlendir_merdiven(kaynak, model, siniflar):
    n, dogru = 0, 0
    Ln, Lg, Rsec_l = [], [], []
    tam_kadraj_kacisi = 0
    for kare in kaynak:
        if kare.gt is None:
            continue
        gt = np.asarray(kare.gt, np.float32)
        L = float(max(gt[2], gt[3]))
        Ln.append(L)
        R = R_sec(L)
        Rsec_l.append(R)
        girdi_px_R = L * AG[0] / float(R)
        tam_px = L * (FULL_W / float(NATIVE_W))
        if not (BANT[0] <= girdi_px_R <= BANT[1]) and BANT[0] <= tam_px <= BANT[1]:
            # merdivenin en yakin basamagi bile banda girmiyor ama tam
            # kadraj giriyor -> A8 tasariminda olmayan, kullanicinin
            # istedigi "gerekiyorsa 1x/tam kadraj" kacisi
            girdi, olcek = _tam_kadraj_girdi(kare.goruntu)
            geri = lambda kutu_ag, olcek=olcek: kutu_ag / olcek  # noqa: E731
            Lg.append(tam_px)
            tam_kadraj_kacisi += 1
        else:
            merkez = (gt[0] + gt[2] / 2.0, gt[1] + gt[3] / 2.0)
            girdi, roi = roi_kirp(kare.goruntu, merkez, R)
            if girdi is None:
                n += 1
                continue
            geri = lambda kutu_ag, roi=roi: geri_donustur(kutu_ag, roi)  # noqa: E731
            Lg.append(girdi_px_R)
        r = model.predict(girdi, conf=CONF, imgsz=IMGSZ, classes=siniflar,
                          verbose=False, device="cpu")[0]
        buldu = False
        if r.boxes is not None and len(r.boxes):
            for (x1, y1, x2, y2) in r.boxes.xyxy.cpu().numpy():
                kutu_ag = np.array([x1, y1, x2 - x1, y2 - y1], np.float32)
                kutu = geri(kutu_ag)
                if iou(kutu, gt) >= 0.5:
                    buldu = True
                    break
        dogru += int(buldu)
        n += 1
    return dict(n=n, dogru=dogru, recall=dogru / n if n else float("nan"),
                L_native_p50=float(np.percentile(Ln, 50)) if Ln else float("nan"),
                L_girdi_p50=float(np.percentile(Lg, 50)) if Lg else float("nan"),
                R_kullanilan=sorted(set(Rsec_l)), tam_kadraj_kacisi=tam_kadraj_kacisi)


def analiz():
    from ultralytics import YOLO
    modeller = {ad: (YOLO(yol), sinif) for ad, (yol, sinif) in MODELLER.items()
                if ad in ("A5_UAVDT", "A6_final")}

    satirlar = []
    for kam_z, senaryo in sorted(IRTIFALAR.items()):
        dizin = os.path.join("data/gazebo", senaryo)
        if not os.path.isdir(dizin):
            print(f"UYARI: {dizin} yok, atlaniyor")
            continue
        for model_ad, (model, siniflar) in modeller.items():
            # tam kadraj (ayni tanim, karsilastirma icin tekrar olculur)
            kaynak = GazeboKaynak(kok="data/gazebo", senaryo=senaryo)
            n, dogru = 0, 0
            Ln = []
            for kare in kaynak:
                if kare.gt is None:
                    continue
                gt = np.asarray(kare.gt, np.float32)
                L = float(max(gt[2], gt[3]))
                Ln.append(L)
                girdi, olcek = _tam_kadraj_girdi(kare.goruntu)
                r = model.predict(girdi, conf=CONF, imgsz=IMGSZ, classes=siniflar,
                                  verbose=False, device="cpu")[0]
                buldu = False
                if r.boxes is not None and len(r.boxes):
                    for (x1, y1, x2, y2) in r.boxes.xyxy.cpu().numpy():
                        kutu_ag = np.array([x1, y1, x2 - x1, y2 - y1], np.float32) / olcek
                        if iou(kutu_ag, gt) >= 0.5:
                            buldu = True
                            break
                dogru += int(buldu)
                n += 1
            satirlar.append(dict(irtifa=kam_z, model=model_ad, yol="tam", n=n, dogru=dogru,
                                  recall=dogru / n if n else float("nan"),
                                  L_native_p50=float(np.percentile(Ln, 50)) if Ln else float("nan"),
                                  L_girdi_p50=float(np.percentile(Ln, 50)) * (FULL_W / NATIVE_W) if Ln else float("nan"),
                                  R_kullanilan=["tam_kadraj"], tam_kadraj_kacisi=n))

            # merdiven-ROI
            kaynak = GazeboKaynak(kok="data/gazebo", senaryo=senaryo)
            sonuc = _degerlendir_merdiven(kaynak, model, siniflar)
            sonuc.update(irtifa=kam_z, model=model_ad, yol="merdiven")
            satirlar.append(sonuc)

    for s in satirlar:
        print(f"irtifa={s['irtifa']:5.0f}m model={s['model']:9s} yol={s['yol']:9s} "
              f"n={s['n']:3d} recall={s['recall']:.3f} "
              f"L_native_p50={s['L_native_p50']:.1f}px L_girdi_p50={s['L_girdi_p50']:.1f}px "
              f"R={s['R_kullanilan']} tam_kacis={s.get('tam_kadraj_kacisi', 0)}")
    return satirlar


if __name__ == "__main__":
    analiz()
