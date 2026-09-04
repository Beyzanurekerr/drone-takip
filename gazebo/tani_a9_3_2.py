"""A9 Deney 3.2 - GEOMETRIK ADAY SECIMI (SALT OKUNUR TESHIS).

*** ACIK CEVRIM · TESHIS · GT YALNIZCA OFFLINE ETIKETLEME ***
Hakem YOK · recovery state machine YOK · kalici kod degisikligi YOK.
takip/ DEGISMEZ (md5 kosum oncesi/sonrasi dogrulanir).

KURAL: docs/architecture/A9_3_2_SECIM_KURALI.md - BU DENEYDEN ONCE yazildi.
    d_norm = |c_aday - c_ref| / (MAX_HIZ*dt + max(ref_w,ref_h)/2)      MAX_HIZ=35 (izleyici.py)
    s      = sqrt((w_a*h_a)/(w_r*h_r))
    a_norm = |log s| / log(2.6)                                        2.6 (tespit.py:122)
    r_norm = |log((w_a/h_a)/(w_r/h_r))| / log(2.6)
    G      = max(d_norm, a_norm, r_norm)        kapi: G <= 1.0
    secim  = argmin G  (guven KULLANILMAZ);  gecen yoksa CEKIMSER

DEDEKTOR NEDEN YENIDEN KOSULUYOR
--------------------------------
3.1 yalnizca OPERASYONEL-goreli oznitelikleri sakladi (arama merkezine uzaklik,
alan orani, adayin kendi en-boyu). MUTLAK aday kutulari saklanmadi; ORACLE
referansi ve en-boy TUTARLILIGI stored havuzdan hesaplanamiyor. Ayrica KOL V
zaten yeni kosum gerektiriyor. Bu yuzden dedektor yeniden kosuldu.

IKI REFERANS AYRI (4U tuzagi)
-----------------------------
ORACLE      : son guvenilir karedeki GT kutusu        -> UST SINIR, basari degil
OPERASYONEL : son guvenilir karedeki TAKIPCI kutusu   -> gercek sistemde kullanilabilir

KOL R ust sinir uyarisi: "son guvenilir kare" GT ile belirlendi (3.1 ile ayni).
"""
import importlib.util as iu
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def _yukle(ad, dosya):
    sp = iu.spec_from_file_location(ad, os.path.join(HERE, dosya))
    m = iu.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


A9 = _yukle("A9", "tani_a9_merkez.py")
A8 = _yukle("A8", "tani_a8_adaptif_roi.py")
REC = _yukle("REC", "tani_a9_recovery.py")
A7, B = A9.A7, A9.B
from calistir import iou                                   # noqa: E402
from takip.izleyici import KILITLI, HedefTakip, Kalman     # noqa: E402
from veri.visdrone import VisDroneVidKaynak                # noqa: E402

SENSOR, N_KARE = A9.SENSOR, A9.N_KARE
SEVIYELER = [30, 20, 15, 10, 8]
SEVIYE_AD = A9.SEVIYE_AD
KOPAN = ["uav0000117_02622_v/23", "uav0000268_05773_v/31", "uav0000339_00001_v/49"]
DIZILER = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31),
           ("uav0000339_00001_v", 49), ("uav0000137_00458_v", 12),
           ("uav0000305_00000_v", 5), ("uav0000182_00000_v", 127)]
DOGRU_IOU, YANLIS_IOU = 0.5, 0.2
MAX_HIZ = Kalman.MAX_HIZ           # 35.0, mevcut sabit
TOL = 2.6                          # tespit.py:122, mevcut sabit
LOG_TOL = math.log(TOL)
GENISLIKLER = [160, 320, 640]
N_DOG = 5                          # dogrulama araligi (N=10, t%10 alt kumesinden)


def merdiven(dt):
    """3.0'in gerekli yaricap p95 tablosundan turetilmis; 3.2 sonucuna bakilmadi."""
    return 160 if dt <= 5 else (320 if dt <= 20 else 640)


def G_skor(kutu, ref_merkez, ref_wh, dt):
    """Onceden yazilmis kural. Dondurur: (G, d_norm, a_norm, r_norm)."""
    kc = kutu[:2] + kutu[2:] / 2.0
    rw, rh = float(ref_wh[0]), float(ref_wh[1])
    d = float(np.linalg.norm(kc - ref_merkez))
    d_bek = MAX_HIZ * float(dt) + max(rw, rh) / 2.0
    d_norm = d / max(d_bek, 1e-6)
    s = math.sqrt(max(float(kutu[2]) * float(kutu[3]), 1e-9) / max(rw * rh, 1e-9))
    a_norm = abs(math.log(max(s, 1e-9))) / LOG_TOL
    ar_a = float(kutu[2]) / max(float(kutu[3]), 1e-6)
    ar_r = rw / max(rh, 1e-6)
    r_norm = abs(math.log(max(ar_a / max(ar_r, 1e-9), 1e-9))) / LOG_TOL
    return max(d_norm, a_norm, r_norm), d_norm, a_norm, r_norm


def sec(adaylar, ref_merkez, ref_wh, dt):
    """Kapi + argmin G. Gecen yoksa CEKIMSER (None)."""
    puanli = []
    for a in adaylar:
        G, dn, an, rn = G_skor(a["kutu"], ref_merkez, ref_wh, dt)
        puanli.append({**a, "G": G, "d_norm": dn, "a_norm": an, "r_norm": rn})
    gecen = [p for p in puanli if p["G"] <= 1.0]
    return (min(gecen, key=lambda p: p["G"]) if gecen else None), puanli


def adaylari_uret(model, img, merkez, R):
    kutular, guvenler, ms, _ = A8.roi_tespit(model, img, merkez, R)
    return [{"kutu": np.asarray(k, float), "guven": float(g)}
            for k, g in zip(kutular, guvenler)], ms


def hucre_izi(dizi):
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    K = []
    for t in range(1, len(dizi)):
        img, gt = dizi[t]
        s = tak.guncelle(img)
        o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
        K.append({"t": t, "iou": o, "durum_kilitli": 1 if s["durum"] == KILITLI else 0,
                  "kf_merkez": tak.kf.konum.astype(float).copy(),
                  "kutu": None if s["kutu"] is None else np.asarray(s["kutu"], float).copy(),
                  "boyut_max": float(np.max(tak.boyut))})
    return K


def auc(poz, neg):
    poz = [x for x in poz if x is not None and np.isfinite(x)]
    neg = [x for x in neg if x is not None and np.isfinite(x)]
    if not poz or not neg:
        return None
    h = np.concatenate([poz, neg])
    r = np.argsort(np.argsort(h)) + 1.0
    _, inv, cnt = np.unique(h, return_inverse=True, return_counts=True)
    tot = np.zeros(len(cnt)); np.add.at(tot, inv, r); r = (tot / cnt)[inv]
    n1, n0 = len(poz), len(neg)
    return round(float((r[:n1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)), 4)


def main():
    import torch
    torch.set_num_threads(8)
    from ultralytics import YOLO

    cikti = {"etiketler": ["ACIK CEVRIM", "TESHIS", "GT YALNIZCA OFFLINE ETIKETLEME"],
             "deney": "3.2 - geometrik aday secimi",
             "kural_dosyasi": "docs/architecture/A9_3_2_SECIM_KURALI.md (deneyden ONCE yazildi)",
             "dedektor_yeniden_kosuldu": ("3.1 mutlak aday kutularini saklamadi; ORACLE "
                                          "referansi ve en-boy tutarliligi hesaplanamiyordu. "
                                          "KOL V zaten yeni kosum gerektiriyor."),
             "kol_r_ust_sinir": "son guvenilir kare GT ile belirlendi (3.1 ile ayni)",
             "takip_degismedi": True, "kol_r": {}, "kol_v": {}}

    for mad, (agirlik, siniflar) in A8.MODELLER.items():
        B.AGIRLIK, B.SINIFLAR = agirlik, siniflar
        model = YOLO(agirlik)
        B.yolo_calistir(model, np.zeros((360, 640, 3), np.uint8))
        print(f"\n===== {mad} =====", flush=True)
        kolR, kolV = [], []
        for dizi_ad, tid in DIZILER:
            ad = f"{dizi_ad}/{tid}"
            k = VisDroneVidKaynak("data/datasets/visdrone_vid", dizi_ad, track_id=tid)
            kareler = []
            for kare in k:
                if kare.gt is not None and kare.gorunur:
                    kareler.append((kare.goruntu, np.asarray(kare.gt, np.float32), [],
                                    kare.genislik, kare.yukseklik))
                if len(kareler) >= N_KARE:
                    break
            W, H = kareler[0][3], kareler[0][4]
            hucre, _ = B.arkaplan_hucresi(kareler, W, H, *SENSOR)
            rol = "KOPAN" if ad in KOPAN else "saglam"
            for L in SEVIYELER:
                d, _s = A7.sensor_dizi(kareler, hucre, L, N_KARE)
                if len(d) < 10:
                    continue
                K = hucre_izi(d)

                # ---------------- KOL R ----------------
                eps = REC.epizotlari_bul([{"t": x["t"], "_iou": x["iou"]} for x in K])
                for e in eps:
                    sg = e["son_guvenilir_idx"]
                    idx = 0 if sg is None else sg
                    sg_t = K[idx]["t"]
                    op_merkez = K[idx]["kf_merkez"]
                    op_wh = (K[idx]["kutu"][2:] if K[idx]["kutu"] is not None
                             else np.array([K[idx]["boyut_max"]] * 2))
                    gt_sg = d[K[idx]["t"]][1]
                    or_merkez = (gt_sg[:2] + gt_sg[2:] / 2.0).astype(float)
                    or_wh = np.asarray(gt_sg[2:], float)
                    for i in range(e["bas_idx"], e["son_idx"] + 1):
                        img, gt = d[K[i]["t"]]
                        dt = K[i]["t"] - sg_t
                        for R in GENISLIKLER + ["merdiven"]:
                            Rr = merdiven(dt) if R == "merdiven" else R
                            ad_l, ms = adaylari_uret(model, img, op_merkez, Rr)
                            for refad, rm, rw in (("operasyonel", op_merkez, op_wh),
                                                  ("oracle", or_merkez, or_wh)):
                                s_, puanli = sec(ad_l, rm, rw, dt)
                                o = None if s_ is None else float(iou(s_["kutu"], gt))
                                kolR.append({
                                    "dizi": ad, "hucre": f"{ad}|{SEVIYE_AD[L]}", "rol": rol,
                                    "t": K[i]["t"], "gecen_kare": dt, "genislik": str(R),
                                    "referans": refad,
                                    "aday_sayisi": len(ad_l),
                                    "cekimser": s_ is None,
                                    "secim_dogru": bool(s_ is not None and o >= DOGRU_IOU),
                                    "secim_yanlis": bool(s_ is not None and o < YANLIS_IOU),
                                    "secim_iou": None if o is None else round(o, 4),
                                    "dogru_havuzda": bool(any(
                                        float(iou(a["kutu"], gt)) >= DOGRU_IOU for a in ad_l)),
                                    "G": None if s_ is None else round(s_["G"], 4),
                                    "bilesenler": [
                                        {"dogru": bool(float(iou(p["kutu"], gt)) >= DOGRU_IOU),
                                         "yanlis": bool(float(iou(p["kutu"], gt)) < YANLIS_IOU),
                                         "G": round(p["G"], 4), "d": round(p["d_norm"], 4),
                                         "a": round(p["a_norm"], 4), "r": round(p["r_norm"], 4),
                                         "guven": round(p["guven"], 4)} for p in puanli],
                                })

                # ---------------- KOL V ----------------
                for i, x in enumerate(K):
                    if not x["durum_kilitli"] or x["kutu"] is None:
                        continue
                    if x["t"] % N_DOG != 0:
                        continue
                    img, gt = d[x["t"]]
                    Rv = A8.R_sec(x["boyut_max"])
                    ad_l, ms = adaylari_uret(model, img, x["kf_merkez"], Rv)
                    puanli = [dict(a, **dict(zip(("G", "d_norm", "a_norm", "r_norm"),
                                                 G_skor(a["kutu"], x["kf_merkez"],
                                                        x["kutu"][2:], 0))))
                              for a in ad_l]
                    enG = min((p["G"] for p in puanli), default=None)
                    kolV.append({
                        "dizi": ad, "hucre": f"{ad}|{SEVIYE_AD[L]}", "rol": rol,
                        "t": x["t"], "seviye": SEVIYE_AD[L], "R": Rv,
                        "kanit_yok": len(ad_l) == 0,
                        "min_G": None if enG is None else round(float(enG), 4),
                        "takipci_dogru": bool(x["iou"] >= DOGRU_IOU),
                        "takipci_yanlis": bool(x["iou"] < YANLIS_IOU),
                        "takipci_iou": round(x["iou"], 4),
                        "gecikme_ms": round(float(ms), 2)})
                print(f"  {ad:<26}{SEVIYE_AD[L]:>6} epizot={len(eps)} "
                      f"kolR={len(kolR)} kolV={len(kolV)}", flush=True)
        cikti["kol_r"][mad] = kolR
        cikti["kol_v"][mad] = kolV

    yol = "cikti/a9_takipci_merkez_recovery.json"
    J = json.load(open(yol))
    J["phase3_recovery"]["experiment_3_2"] = cikti
    json.dump(J, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
