"""2e-TESHIS: A6'nin baylands 80 m'de 0 tespit vermesinin sebebi px bandi mi?

Talimat (kayit yok = yeni SENARYOLAR kaydi eklenmez/commitlenmez, kod
degisikligi yok = mevcut dosyalar DEGISTIRILMEDI, fine-tune yok, mesh
degistirme yok): ayni Demo_celdirici duzeni (hatchback hedef + 2 celdirici,
baylands, IMX500 kamerasi) 3 irtifada (80/120/160 m) x 3 modelde (COCO
yolov8n, A5=runs/a6/asamaA UAVDT-on-egitim, A6=runs/a6/asamaB nihai) x 2
yolda (tam kadraj 640, ROI-4x) recall olcer.

Bu script HICBIR mevcut dosyayi degistirmez; sadece mevcuttaki
`gazebo.senaryolar._demo` / `gazebo.kaydet.Kayitci` / `gazebo.demo_saglik_2e`
yardimcilarini import edip YENI parametrelerle cagirir. 120/160 m kayitlari
data/gazebo/Teshis2e_*m altina yazilir (kareler/ zaten .gitignore'da genel
`data/gazebo/*/kareler/` kuraliyla ignore edilir - resmi SENARYOLAR kaydina
EKLENMEZ).

Kosum:
  python3 -m gazebo.teshis_2e_px_bandi capture --kam_z 120
  python3 -m gazebo.teshis_2e_px_bandi capture --kam_z 160
  python3 -m gazebo.teshis_2e_px_bandi analiz
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

from calistir import iou                                    # noqa: E402
from veri.gazebo import GazeboKaynak                         # noqa: E402
from gazebo.senaryolar import _demo, _demo_kam_profil         # noqa: E402
from gazebo.kaydet import Kayitci                             # noqa: E402
from gazebo.demo_saglik_2e import roi_kirp_buyut, geri_donustur, AG, BUYUTME  # noqa: E402

KOK = "data/gazebo"
KARE = 100
CONF, IMGSZ = 0.25, 640
FULL_W = 640

MODELLER = {
    "COCO": ("weights/yolov8n.pt", [2, 5, 7]),                 # car,bus,truck
    "A5_UAVDT": ("runs/a6/asamaA/weights/best.pt", [0]),        # vehicle
    "A6_final": ("runs/a6/asamaB/weights/best.pt", [0, 1, 2, 3]),  # car,van,truck,bus
}

IRTIFALAR = {80.0: "Demo_celdirici", 120.0: "Teshis2e_120m", 160.0: "Teshis2e_160m"}


def ad_kam_z(kam_z):
    return f"Teshis2e_{int(kam_z)}m"


def capture(kam_z, kare=KARE):
    ad = ad_kam_z(kam_z)
    sen = _demo(
        ad, f"2e-TESHIS: sabit {kam_z:.0f} m, Demo_celdirici ile AYNI duzen "
            "(hatchback+2 celdirici, baylands, IMX500)",
        "2e-teshis: A6'nin 80m'de 0 tespitinin sebebi px bandi mi?",
        f"px bandi karsilastirmasi icin {kare} kare", _demo_kam_profil(),
        kam_z=kam_z, kare=kare, celdirici_var=True,
        etiketler=["teshis_2e", "arastirma_disi_demo_olcumu"])
    print(f"{sen.ad}: {sen.aciklama}\n  amac: {sen.amac}")
    k = Kayitci(sen, kok=KOK, kare_hedef=kare)
    meta = k.kaydet()
    print(f"  kaydedildi: {meta['kare_sayisi']} kare, dusen {meta['dusen_kare']}, "
          f"RTF {meta['kayit']['rtf']}")
    return meta


def _tam_kadraj_girdi(img):
    H, W = img.shape[:2]
    olcek = FULL_W / float(W)
    boy = int(round(H * olcek))
    girdi = cv2.resize(img, (FULL_W, boy), interpolation=cv2.INTER_AREA)
    return girdi, olcek


def _degerlendir(kaynak, model, siniflar, yol):
    """yol: 'tam' | 'roi'. Doner: (n, dogru, L_native_list, L_girdi_list, ms_list)."""
    n, dogru = 0, 0
    Ln, Lg, ms = [], [], []
    for kare in kaynak:
        if kare.gt is None:
            continue
        gt = np.asarray(kare.gt, np.float32)
        L = float(max(gt[2], gt[3]))
        Ln.append(L)
        if yol == "tam":
            girdi, olcek = _tam_kadraj_girdi(kare.goruntu)
            gt_g = gt * olcek
            geri = lambda kutu_ag: kutu_ag / olcek  # noqa: E731
            Lg.append(L * olcek)
        else:
            merkez = (gt[0] + gt[2] / 2.0, gt[1] + gt[3] / 2.0)
            R = AG[0] / BUYUTME
            girdi, roi = roi_kirp_buyut(kare.goruntu, merkez, R)
            if girdi is None:
                n += 1
                continue
            Lg.append(L * BUYUTME)
            geri = lambda kutu_ag, roi=roi: geri_donustur(kutu_ag, roi)  # noqa: E731
        t0 = time.perf_counter()
        r = model.predict(girdi, conf=CONF, imgsz=IMGSZ, classes=siniflar,
                          verbose=False, device="cpu")[0]
        ms.append((time.perf_counter() - t0) * 1e3)
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
    return n, dogru, Ln, Lg, ms


def _parlaklik(kaynak):
    vals = []
    for kare in kaynak:
        vals.append(float(np.mean(cv2.cvtColor(kare.goruntu, cv2.COLOR_BGR2GRAY))))
    return np.array(vals)


def analiz():
    from ultralytics import YOLO
    modeller = {ad: (YOLO(yol), sinif) for ad, (yol, sinif) in MODELLER.items()}

    satirlar = []
    parlaklik = {}
    for kam_z, senaryo in sorted(IRTIFALAR.items()):
        dizin = os.path.join(KOK, senaryo)
        if not os.path.isdir(dizin):
            print(f"UYARI: {dizin} yok, atlaniyor (once `capture --kam_z {kam_z:.0f}`)")
            continue
        kaynak_p = GazeboKaynak(kok=KOK, senaryo=senaryo)
        parlaklik[kam_z] = _parlaklik(kaynak_p)
        for model_ad, (model, siniflar) in modeller.items():
            for yol in ("tam", "roi"):
                kaynak = GazeboKaynak(kok=KOK, senaryo=senaryo)
                n, dogru, Ln, Lg, ms = _degerlendir(kaynak, model, siniflar, yol)
                recall = dogru / n if n else float("nan")
                satirlar.append(dict(
                    irtifa=kam_z, model=model_ad, yol=yol, n=n, dogru=dogru,
                    recall=recall, L_native_p50=float(np.percentile(Ln, 50)) if Ln else float("nan"),
                    L_girdi_p50=float(np.percentile(Lg, 50)) if Lg else float("nan"),
                    ms_p50=float(np.percentile(ms, 50)) if ms else float("nan")))
                print(f"irtifa={kam_z:5.0f}m model={model_ad:9s} yol={yol:3s} "
                      f"n={n:3d} recall={recall:.3f} "
                      f"L_native_p50={satirlar[-1]['L_native_p50']:.1f}px "
                      f"L_girdi_p50={satirlar[-1]['L_girdi_p50']:.1f}px "
                      f"ms_p50={satirlar[-1]['ms_p50']:.1f}")

    return satirlar, parlaklik


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="komut", required=True)
    ap_cap = sub.add_parser("capture")
    ap_cap.add_argument("--kam_z", type=float, required=True)
    ap_cap.add_argument("--kare", type=int, default=KARE)
    sub.add_parser("analiz")
    a = ap.parse_args()
    if a.komut == "capture":
        capture(a.kam_z, a.kare)
    else:
        analiz()
