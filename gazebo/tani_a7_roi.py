"""A7 - ROI tespit teshisi (SALT OKUNUR gozlemci).

A5.2 protokol dosyasi (gazebo/bench_a52_kucuk_hedef.py) DEGISTIRILMEZ; modul
olarak ice aktarilip fonksiyonlari yeniden kullanilir. takip/ degistirilmez.
Model egitimi yok, agirlik degismez.

NEDEN YENI BIR TEST YATAGI GEREKTI (olculdu, varsayilmadi)
---------------------------------------------------------
Ilk deneme ROI'yi dogrudan A5.2'nin 640x360 tuvali uzerinde kirpti. Sonuc:
117/23 10x5 seviyesinde ROI **oracle** (merkezi GT'den alan ust sinir) bile
recall 0.000 verdi. Sebep acik: A5.2 tuvali zaten 640x360'tir ve oradaki 10 px'lik
hedef, 146 px'lik gercek yamanin kuculmus halidir - bilgi ORADA YOK. 4x buyutmek
gercek piksel eklemez, yalnizca bulanik bir leke uretir.

Gercek dronede durum farklidir: sensor (IMX500 / Pi kamera) agin girdisinden
DAHA COK piksel toplar. ROI'nin anlami "sensorun zaten sahip oldugu cozunurlugu
aga tasimak"tir. Bunu olcmek icin tuval SENSOR cozunurlugunde kurulur:

    SENSOR tuvali : 1280x720 (gercek VisDrone karesinden kirpilmis gercek arkaplan)
    tam kare      : 1280x720 -> letterbox 640x384, olcek 0.5
                    => "seviye L" = hedefin AG GIRDISINDEKI px boyu (A5.2 ile ayni tanim)
    hedef yamasi  : sensorde 2L px (gercek 146 px'lik yamadan SADECE KUCULTEREK)
    ROI kolu      : sensorden R genisliginde kirp -> 640x360'a getir
                    buyutme = 1280/R  (R=640 -> 2x, R=320 -> 4x, R=160 -> 8x)

Boylece "seviye" tanimi A5.2 ile birebir ayni kalir (agin gordugu px), degisen
TEK sey dedektorun o pikselleri nereden aldigidir: kuculmus tam kareden mi,
yoksa sensorun kirpilmis gercek pikselinden mi.

ROI MERKEZI - ORACLE DEGIL
    Yama, GT hareketinin s katiyla tuval icinde HAREKET eder; boylece t-1
    karesindeki kestirim t icin gercek (oracle olmayan) bir adaydir.
      tam_kare           : temel
      roi640_*, roi320_*, roi160_*  : 2x / 4x / 8x buyutme
      *_onceki_tespit    : merkez = onceki KABUL EDILEN tespitin merkezi,
                           0. karede TAM KARE tespitiyle baslatilir (soguk baslangic)
      *_takipci          : merkez = onceki karedeki TAKIPCI kutusunun merkezi;
                           takipci 0. karede GT ile kilitlenir = "onceden kilit VAR"
      *_oracle           : merkez = o karenin GT merkezi -> YALNIZCA UST SINIR,
                           basari sayilmaz
"""
import importlib.util as iu
import json
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = iu.spec_from_file_location(
    "B", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "bench_a52_kucuk_hedef.py"))
B = iu.module_from_spec(_spec)
_spec.loader.exec_module(B)

from calistir import iou                                   # noqa: E402
from takip.izleyici import KILITLI, HedefTakip             # noqa: E402

MODELLER = {
    "A5_baseline": ("weights/yolov8n.pt", [2, 3, 5, 7]),
    "A6_uavdt_visdrone": ("runs/a6/asamaB/weights/best.pt", [0, 1, 2, 3]),
}
SENSOR = (1280, 720)          # sensor tuvali (gercek arkaplan, native cozunurluk)
AG = (640, 360)               # aga verilen kare -> letterbox 640x384, olcek 1.000
ROI = {"roi640": (640, 360), "roi320": (320, 180), "roi160": (160, 90)}   # sensor px
BUYUTME = {"roi640": 2.0, "roi320": 4.0, "roi160": 8.0}
N_KARE = 60


# ------------------------------------------------------------------ ROI cikarim
def roi_tespit(model, sensor, merkez, roi_wh):
    """SENSOR tuvalinden ROI kirp -> aga verilecek boya getir -> YOLO -> sensor koord."""
    SW, SH = SENSOR
    AW, AH = AG
    rw, rh = roi_wh
    x0 = int(round(merkez[0] - rw / 2.0)); y0 = int(round(merkez[1] - rh / 2.0))
    x0 = max(0, min(SW - rw, x0)); y0 = max(0, min(SH - rh, y0))
    parca = sensor[y0:y0 + rh, x0:x0 + rw]
    if parca.shape[:2] != (rh, rw):
        return [], [], 0.0, (x0, y0)
    interp = cv2.INTER_LINEAR if rw < AW else cv2.INTER_AREA
    girdi = cv2.resize(parca, (AW, AH), interpolation=interp)
    kutular, guvenler, ms = B.yolo_calistir(model, girdi)
    kx, ky = rw / float(AW), rh / float(AH)
    geri = [np.array([k[0] * kx + x0, k[1] * ky + y0, k[2] * kx, k[3] * ky],
                     np.float32) for k in kutular]
    return geri, guvenler, ms, (x0, y0)


def tam_kare_tespit(model, sensor):
    """Sensor karesini oldugu gibi ver: letterbox 1280x720 -> 640x384 (olcek 0.5)."""
    return B.yolo_calistir(model, sensor)


def kol_olc(model, dizi, kol):
    """Bir kolu 60 kare boyunca kosar. Doner: metrik sozlugu."""
    roi_wh = ROI.get(kol.split("_")[0])
    kaynak = kol.split("_", 1)[1] if "_" in kol else ""
    tak = None
    if kaynak == "takipci":
        tak = HedefTakip()
        tak.kilitle(dizi[0][0], dizi[0][1].copy())         # onceden kilit VAR (senaryo B)
    son_merkez = None
    bootstrap = None
    vur05 = vur0 = 0; n = 0
    iou_l, guv_l, ms_l = [], [], []
    fp = fn = 0
    for t, (img, gt) in enumerate(dizi):
        gc = gt[:2] + gt[2:] / 2.0
        # --- ROI merkezini SEC (oracle disinda gecmise dayanir) ---
        if kol == "tam_kare":
            merkez = None
        elif kaynak == "oracle":
            merkez = gc
        elif kaynak == "takipci":
            if t == 0:
                merkez = dizi[0][1][:2] + dizi[0][1][2:] / 2.0
            else:
                merkez = son_merkez
        else:                                              # onceki_tespit zinciri
            if t == 0:
                kutular, guvenler, ms, *_ = (*tam_kare_tespit(model, img), None)  # soguk baslangic
                ms_l.append(ms)
                es = [(float(iou(k, gt)), k, g) for k, g in zip(kutular, guvenler)]
                es = [e for e in es if e[0] > 0.0]
                bootstrap = bool(es)
                if not es:
                    continue                               # zincir hic baslamadi
                o, k, g = max(es, key=lambda e: e[0])
                son_merkez = k[:2] + k[2:] / 2.0
                merkez = son_merkez
                n += 1; vur0 += 1; vur05 += 1 if o >= 0.5 else 0
                iou_l.append(o); guv_l.append(g)
                continue
            merkez = son_merkez
        if merkez is None:
            kutular, guvenler, ms = tam_kare_tespit(model, img)
        else:
            kutular, guvenler, ms, _o = roi_tespit(model, img, merkez, roi_wh)
        ms_l.append(ms); n += 1
        es = [(float(iou(k, gt)), k, g) for k, g in zip(kutular, guvenler)]
        iy = max(es, key=lambda e: e[0]) if es else (0.0, None, 0.0)
        fp += sum(1 for e in es if e[0] <= 0.0)
        if iy[0] > 0.0:
            vur0 += 1; iou_l.append(iy[0]); guv_l.append(iy[2])
            if iy[0] >= 0.5:
                vur05 += 1
            if kaynak == "onceki_tespit":
                son_merkez = iy[1][:2] + iy[1][2:] / 2.0
        else:
            fn += 1
        if kaynak == "takipci" and t + 1 < len(dizi):
            s = tak.guncelle(dizi[t + 1][0])
            son_merkez = (s["kutu"][:2] + s["kutu"][2:] / 2.0
                          if s["kutu"] is not None else son_merkez)
    f = lambda v, k=4: round(float(np.mean(v)), k) if v else None
    return {"kare": n, "recall_iou50": round(vur05 / n, 4) if n else None,
            "recall_iou0": round(vur0 / n, 4) if n else None,
            "ort_iou": f(iou_l), "ort_guven": f(guv_l), "fp": fp, "fn": fn,
            "gecikme_ort_ms": f(ms_l, 2),
            "gecikme_p95_ms": round(float(np.percentile(ms_l, 95)), 2) if ms_l else None,
            "esdeger_fps": round(1000.0 / float(np.mean(ms_l)), 1) if ms_l else None,
            "bootstrap": bootstrap}


# --------------------------------------------- SENSOR cozunurlugunde dizi
def sensor_dizi(kareler, hucre, seviye_px, n):
    """1280x720 SENSOR karesi: gercek arkaplan + gercek hedef yamasi.

    Yama sensorde 2*seviye px olur; tam kare aga verilince letterbox 0.5 ile
    kuculur ve hedef AGDA tam olarak `seviye_px` olur - A5.2'deki seviye
    tanimiyla birebir ayni. Yama yalnizca KUCULTULEREK uretilir (146 px kaynak),
    yani uydurma detay yok.
    """
    SW, SH = SENSOR
    g0 = kareler[0][1]
    L0 = max(float(g0[2]), float(g0[3]))
    hedef_sensor = 2.0 * seviye_px
    s = hedef_sensor / L0
    c0 = g0[:2] + g0[2:] / 2.0
    dizi = []
    for img, gt, _e, _W, _H in kareler[:n]:
        x, y, w, h = [int(round(v)) for v in gt]
        chip = img[max(0, y):y + h, max(0, x):x + w]
        if chip.size == 0 or chip.shape[0] < 2 or chip.shape[1] < 2:
            break
        nw = max(1, int(round(chip.shape[1] * s))); nh = max(1, int(round(chip.shape[0] * s)))
        interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR
        chip = cv2.resize(chip, (nw, nh), interpolation=interp)
        arka = img[hucre[1]:hucre[1] + SH, hucre[0]:hucre[0] + SW]
        if arka.shape[:2] != (SH, SW):
            break
        c = gt[:2] + gt[2:] / 2.0
        p = np.array([SW / 2.0, SH / 2.0]) + (c - c0) * s
        tuval, gt_yeni = B.yapistir(arka, chip, p[0], p[1])
        if tuval is None:
            break
        dizi.append((tuval, gt_yeni))
    return dizi, s


# ------------------------------------------------- B) PERSISTENCE: daralan hedef
def daralan_dizi(kareler, hucre, L_bas, L_son, n):
    """Hedef n kare boyunca L_bas -> L_son px'e KUCULUR (geometrik).

    Gorevin gercek hali: drone uzaklasirken hedef kuculur. Hareket her karede
    o karenin olcegiyle carpilir, boylece 'kendi eninin kac kati/kare' sabit
    kalir (A5.2'deki olcek degismezligi ile ayni ilke).
    """
    CW, CH = B.TUVAL
    g0 = kareler[0][1]
    L0 = max(float(g0[2]), float(g0[3]))
    c0 = g0[:2] + g0[2:] / 2.0
    p = np.array([CW / 2.0, CH / 2.0])
    onceki_c = c0
    dizi, boylar = [], []
    for t, (img, gt, _e, _W, _H) in enumerate(kareler[:n]):
        oran = (L_son / L_bas) ** (t / max(1, n - 1))
        s = (L_bas / L0) * oran                            # o karedeki olcek
        x, y, w, h = [int(round(v)) for v in gt]
        chip = img[max(0, y):y + h, max(0, x):x + w]
        if chip.size == 0 or chip.shape[0] < 2 or chip.shape[1] < 2:
            break
        nw = max(1, int(round(chip.shape[1] * s))); nh = max(1, int(round(chip.shape[0] * s)))
        interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR
        chip = cv2.resize(chip, (nw, nh), interpolation=interp)
        arka = img[hucre[1]:hucre[1] + CH, hucre[0]:hucre[0] + CW]
        if arka.shape[:2] != (CH, CW):
            break
        c = gt[:2] + gt[2:] / 2.0
        p = p + (c - onceki_c) * s                         # olcekli hareket
        onceki_c = c
        tuval, gt_yeni = B.yapistir(arka, chip, p[0], p[1])
        if tuval is None:
            break
        dizi.append((tuval, gt_yeni)); boylar.append(max(nw, nh))
    return dizi, boylar


def persistence_olc(dizi, boylar):
    """B) PERSISTENCE: onceden kilit VAR (GT ile baslatilir), hedef kuculurken
    takipci ne kadar dayaniyor. Bu bir TESPIT basarisi DEGILDIR."""
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    iou_l, mh_l, psr_l, kilit_l = [], [], [], []
    ard = 0; kayip_boy = None; kayip_kare = None
    for k in range(1, len(dizi)):
        img, gt = dizi[k]
        s = tak.guncelle(img)
        o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
        iou_l.append(o); psr_l.append(float(s["psr"]))
        if s["kutu"] is not None:
            t_, g_ = s["kutu"], gt
            mh_l.append(float(np.hypot(t_[0] + t_[2] / 2 - (g_[0] + g_[2] / 2),
                                       t_[1] + t_[3] / 2 - (g_[1] + g_[3] / 2))))
        kilit_l.append(1 if (s["durum"] == KILITLI and o > 0.2) else 0)
        if o < 0.3:
            ard += 1
            if ard >= 5 and kayip_kare is None:
                kayip_kare = k - 4; kayip_boy = boylar[kayip_kare]
        else:
            ard = 0
    f = lambda v, k=4: round(float(np.mean(v)), k) if v else None
    return {"kare": len(dizi), "baslangic_px": boylar[0], "bitis_px": boylar[-1],
            "ort_iou": f(iou_l), "kilit_orani": f(kilit_l),
            "ort_merkez_hata_px": f(mh_l, 2), "ort_psr": f(psr_l, 2),
            "kayip_karesi": kayip_kare,
            "KAYBEDILEN_BOYUT_px": kayip_boy,
            "son_kareye_kadar_dayandi": kayip_kare is None}


# ------------------------------------------------------------------------ main
def main():
    import torch
    torch.set_num_threads(8)
    from ultralytics import YOLO
    KOLLAR = ["tam_kare",
              "roi640_onceki_tespit", "roi320_onceki_tespit", "roi160_onceki_tespit",
              "roi320_takipci", "roi320_oracle", "roi160_oracle"]
    cikti = {"asama": "A7 - ROI tespit teshisi (salt okunur)",
             "protokol": {"a52_dosyasi": "gazebo/bench_a52_kucuk_hedef.py",
                          "a52_degistirilmedi": True,
                          "sensor_tuvali": list(SENSOR), "ag_karesi": list(AG),
                          "tam_kare_letterbox_olcegi": 0.5,
                          "seviye_tanimi": "hedefin AG GIRDISINDEKI px boyu (A5.2 ile ayni)",
                          "roi_boyutlari_sensor_px": {k: list(v) for k, v in ROI.items()},
                          "buyutme": BUYUTME, "conf": B.CONF, "imgsz": B.IMGSZ,
                          "kare": N_KARE},
             "kollar": KOLLAR, "modeller": {}}
    for mad, (agirlik, siniflar) in MODELLER.items():
        B.AGIRLIK, B.SINIFLAR = agirlik, siniflar
        model = YOLO(agirlik)
        B.yolo_calistir(model, np.zeros((AG[1], AG[0], 3), np.uint8))
        print(f"\n===== {mad} ({agirlik}) siniflar={siniflar} =====", flush=True)
        md = {"agirlik": agirlik, "siniflar": siniflar, "diziler": {}}
        for dizi_ad, tid, rol in B.DIZILER:
            kareler = B.kareleri_topla(dizi_ad, tid, N_KARE)
            W, H = kareler[0][3], kareler[0][4]
            if W < SENSOR[0] or H < SENSOR[1]:
                print(f"  --- {dizi_ad}/{tid}: kare {W}x{H} sensor tuvalinden kucuk, ATLANDI")
                continue
            hucre, _u = B.arkaplan_hucresi(kareler, W, H, *SENSOR)
            dd = {"rol": rol, "kare_boyutu": [W, H], "arkaplan_hucre": list(hucre),
                  "seviyeler": {}}
            print(f"  --- {dizi_ad}/{tid} ({rol}) sensor hucresi {hucre} ---", flush=True)
            for sad, uzun in B.SEVIYELER:
                if uzun is None:
                    continue
                d, s = sensor_dizi(kareler, hucre, uzun, N_KARE)
                if len(d) < 10:
                    dd["seviyeler"][sad] = {"not": "dizi 10 kareden kisa"}
                    continue
                r = {"olcek_s": round(s, 4), "kare": len(d),
                     "sensor_px": round(float(np.mean([max(g[2], g[3]) for _i, g in d])), 1),
                     "ag_px_tam_kare": round(float(np.mean([max(g[2], g[3]) for _i, g in d])) * 0.5, 1)}
                for kol in KOLLAR:
                    r[kol] = kol_olc(model, d, kol)
                dd["seviyeler"][sad] = r
                t = lambda k: r[k]["recall_iou50"]
                print(f"    {sad:6s} agda {r['ag_px_tam_kare']:5.1f}px  recall@.5  "
                      f"tam={t('tam_kare'):.3f} | roi2x={t('roi640_onceki_tespit'):.3f} "
                      f"roi4x={t('roi320_onceki_tespit'):.3f} roi8x={t('roi160_onceki_tespit'):.3f} "
                      f"| takipci4x={t('roi320_takipci'):.3f} "
                      f"[oracle4x={t('roi320_oracle'):.3f} 8x={t('roi160_oracle'):.3f}]",
                      flush=True)
            if mad == list(MODELLER)[0]:
                h2, _u2 = B.arkaplan_hucresi(kareler, W, H, *B.TUVAL)
                dz, boy = daralan_dizi(kareler, h2, 57.0, 5.0, N_KARE)
                if len(dz) >= 10:
                    dd["persistence_daralan"] = persistence_olc(dz, boy)
                    pz = dd["persistence_daralan"]
                    print(f"    PERSISTENCE (57->5 px, onceden kilitli): IoU {pz['ort_iou']} "
                          f"kilit {pz['kilit_orani']} kaybedilen boyut "
                          f"{pz['KAYBEDILEN_BOYUT_px']} px", flush=True)
            md["diziler"][f"{dizi_ad}/{tid}"] = dd
        cikti["modeller"][mad] = md
    os.makedirs("cikti", exist_ok=True)
    yol = sys.argv[1] if len(sys.argv) > 1 else "cikti/a7_roi_teshis.json"
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
