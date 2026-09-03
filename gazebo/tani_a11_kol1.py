"""A11 KOL 1 - IMU EGO. Tek degisken: ego telafisi kaynagi.

*** KOMPOZIT YATAK KULLANILMAZ *** - butun kareler gazebo/kaydet.py kaydindan.

ON-KAYIT: docs/architecture/A11_ONKAYIT.md §3 (+ EK-2, KOL 1 kosulmadan once
eklendi - IMU'nun MUTLAK yonelimi kayiyor ama KARE-KARE BAGIL rotasyonu
gercege yakin; M_imu bu yuzden ROTASYON-ONLY + tek seferlik mount kalibrasyonu
ile insa edilir, OTELENME KASITLI SIFIR).

KOLLAR:
    1a (kontrol) - mevcut gorsel EgoMotion
    1b (deney)   - takip/egomotion.py:ImuEgo (gazebo/a11_ortak.py), gorsel
                   akis KAPALI

DEDEKTOR/HAKEM YOK - KOL 1 saf takipci (H0 tarzi) uzerinde, `tak.ego`
ornek-seviyesinde DEGISTIRILEREK olculur. takip/izleyici.py DEGISMEZ.
"""
import hashlib
import importlib.util as iu
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from calistir import iou                                          # noqa: E402
from gazebo.a11_ortak import (DOGRU_IOU, ImuEgo, MIN_EPIZOT,       # noqa: E402
                              YANLIS_IOU, gercek_kaydirma,
                              imu_oku, kareleri_topla, kosular)
from takip.izleyici import KILITLI, HedefTakip                     # noqa: E402

SENARYOLAR = ["A1_taban", "A2_kucul", "A3_yaw", "A4_irtifa",
             "A5_kucul_yaw", "A6_celdirici"]
KOLLAR = ["1a_gorsel", "1b_imu"]


def md5ler():
    return {f: hashlib.md5(open(os.path.join(ROOT, "takip", f), "rb").read()).hexdigest()
            for f in sorted(os.listdir(os.path.join(ROOT, "takip"))) if f.endswith(".py")}


def p(v, q):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return None if not v else round(float(np.percentile(v, q)), 3)


# --------------------------------------------------------------------------
# sahte ego - IMU kaynagi icin (KOL 0'daki gorsel olcumun ayni tanimi)
# --------------------------------------------------------------------------
def sahte_ego_imu(senaryo):
    kareler, W, H, fx, fy, cx, cy = kareleri_topla(senaryo)
    _, _, _, poz = None, None, None, [s for _, _, s in kareler]
    imu = imu_oku(f"data/gazebo/{senaryo}/imu.csv")
    ego = ImuEgo(imu, poz, W, H, fx, fy, cx, cy)
    x_ref = np.array([W / 2.0, H / 2.0])
    vals, guvenler, tanimsiz = [], [], 0
    for i in range(1, len(kareler)):
        M, guven = ego.guncelle(None, None)
        guvenler.append(guven)
        gercek = gercek_kaydirma(x_ref, poz[i - 1], poz[i], fx, fy, cx, cy)
        if gercek is None:
            tanimsiz += 1
            continue
        gorsel = M[:, :2] @ x_ref + M[:, 2]
        vals.append(float(np.linalg.norm(gorsel - gercek)))
    return {"kare": len(kareler), "nokta": len(vals), "tanimsiz": tanimsiz,
           "p50": p(vals, 50), "p95": p(vals, 95), "max": max(vals) if vals else None,
           "guven_ort": round(float(np.mean(guvenler)), 3) if guvenler else None}


def main():
    md5_bas = md5ler()
    cikti = {"etiketler": ["ACIK CEVRIM", "KOMPOZIT YATAK YOK", "GAZEBO"],
             "onkayit": "docs/architecture/A11_ONKAYIT.md §3 (+EK-2)",
             "md5_baslangic": md5_bas, "sahte_ego_imu": {}, "hucreler": {}}

    print("===== SAHTE EGO - IMU kaynagi =====", flush=True)
    for s in SENARYOLAR:
        r = sahte_ego_imu(s)
        cikti["sahte_ego_imu"][s] = r
        print(f"  {s:<16} n={r['nokta']:<4} p50={r['p50']:<7} p95={r['p95']:<7} "
              f"guven_ort={r['guven_ort']}", flush=True)

    print("\n===== TAKIPCI: 1a (gorsel) vs 1b (IMU) =====", flush=True)
    for s in SENARYOLAR:
        kareler, W, H, fx, fy, cx, cy = kareleri_topla(s)
        poz = [sr for _, _, sr in kareler]
        imu = imu_oku(f"data/gazebo/{s}/imu.csv")
        cikti["hucreler"][s] = {"kollar": {}}

        # 1a - gorsel (degistirilmemis tak.ego)
        tak = HedefTakip()
        img0, gt0, _ = kareler[0]
        tak.kilitle(img0, gt0.copy())
        iz = []
        for t in range(1, len(kareler)):
            img, gt, satir = kareler[t]
            st = tak.guncelle(img)
            o = float(iou(st["kutu"], gt)) if st["kutu"] is not None else 0.0
            gtc = gt[:2] + gt[2:] / 2.0
            hata = float(np.linalg.norm(tak.kf.konum - gtc))
            iz.append({"t": t, "iou": o, "durum": st["durum"], "psr": float(st["psr"]),
                       "merkez_hata": hata, "gt_L": float(np.max(gt[2:]))})
        iou_l = [x["iou"] for x in iz]; hata_l = [x["merkez_hata"] for x in iz]
        yk = sum(1 for x in iz if x["durum"] == KILITLI and x["iou"] < YANLIS_IOU)
        kopus = kosular(iz, lambda x: x["merkez_hata"] > 0.5 * x["gt_L"], 5)
        kacis = None
        if kopus:
            a, b = kopus[0]
            if b > a:
                seg = [x["merkez_hata"] for x in iz[a:b + 1]]
                kacis = round((seg[-1] - seg[0]) / max(len(seg) - 1, 1), 3)
        r1a = {"kol": "1a_gorsel", "kare": len(iz), "iou_ort": round(float(np.mean(iou_l)), 4),
              "merkez_hata_p50": p(hata_l, 50), "merkez_hata_p95": p(hata_l, 95),
              "guvenli_yanlis_kilit": yk, "kopus_sayisi": len(kopus),
              "kopus_kareleri": [iz[a]["t"] for a, _b in kopus], "kopuslu": bool(kopus),
              "mod_a_kacis_hizi_px_kare": kacis,
              "psr_p50": p([x["psr"] for x in iz], 50), "psr_p05": p([x["psr"] for x in iz], 5),
              "kilit_orani": round(sum(1 for x in iz if x["durum"] == KILITLI) / len(iz), 4),
              "gt_L_ort": round(float(np.mean([x["gt_L"] for x in iz])), 2)}
        cikti["hucreler"][s]["kollar"]["1a_gorsel"] = r1a

        # 1b - IMU (tak.ego DEGISTIRILDI)
        tak2 = HedefTakip()
        tak2.ego = ImuEgo(imu, poz, W, H, fx, fy, cx, cy)
        tak2.kilitle(img0, gt0.copy())
        iz2 = []
        for t in range(1, len(kareler)):
            img, gt, satir = kareler[t]
            st = tak2.guncelle(img)
            o = float(iou(st["kutu"], gt)) if st["kutu"] is not None else 0.0
            gtc = gt[:2] + gt[2:] / 2.0
            hata = float(np.linalg.norm(tak2.kf.konum - gtc))
            iz2.append({"t": t, "iou": o, "durum": st["durum"], "psr": float(st["psr"]),
                       "merkez_hata": hata, "gt_L": float(np.max(gt[2:]))})
        iou_l2 = [x["iou"] for x in iz2]; hata_l2 = [x["merkez_hata"] for x in iz2]
        yk2 = sum(1 for x in iz2 if x["durum"] == KILITLI and x["iou"] < YANLIS_IOU)
        kopus2 = kosular(iz2, lambda x: x["merkez_hata"] > 0.5 * x["gt_L"], 5)
        kacis2 = None
        if kopus2:
            a, b = kopus2[0]
            if b > a:
                seg = [x["merkez_hata"] for x in iz2[a:b + 1]]
                kacis2 = round((seg[-1] - seg[0]) / max(len(seg) - 1, 1), 3)
        r1b = {"kol": "1b_imu", "kare": len(iz2), "iou_ort": round(float(np.mean(iou_l2)), 4),
              "merkez_hata_p50": p(hata_l2, 50), "merkez_hata_p95": p(hata_l2, 95),
              "guvenli_yanlis_kilit": yk2, "kopus_sayisi": len(kopus2),
              "kopus_kareleri": [iz2[a]["t"] for a, _b in kopus2], "kopuslu": bool(kopus2),
              "mod_a_kacis_hizi_px_kare": kacis2,
              "psr_p50": p([x["psr"] for x in iz2], 50), "psr_p05": p([x["psr"] for x in iz2], 5),
              "kilit_orani": round(sum(1 for x in iz2 if x["durum"] == KILITLI) / len(iz2), 4),
              "gt_L_ort": round(float(np.mean([x["gt_L"] for x in iz2])), 2)}
        cikti["hucreler"][s]["kollar"]["1b_imu"] = r1b

        print(f"  {s:<16} 1a IoU={r1a['iou_ort']:.3f} kopus={r1a['kopus_sayisi']} | "
              f"1b IoU={r1b['iou_ort']:.3f} kopus={r1b['kopus_sayisi']}", flush=True)
        del kareler

    cikti["md5_bitis"] = md5ler()
    cikti["md5_degismedi"] = cikti["md5_baslangic"] == cikti["md5_bitis"]
    yol = os.path.join(ROOT, "cikti", "a11_kol1.json")
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
