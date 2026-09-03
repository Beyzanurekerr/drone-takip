"""A11 KOL 0 - TASIMA. Mevcut pipeline (takipci + dedektor + A10.1 hakemi,
histerezisli) Gazebo'da, KAPALI CEVRIM.

*** KOMPOZIT YATAK KULLANILMAZ *** - butun kareler gazebo/kaydet.py
kaydindan, GT gazebo/dunya_uret.py'nin ayni izdusum matematigiyle
(veri/gazebo.py) hesaplanir.

ON-KAYIT: docs/architecture/A11_ONKAYIT.md (+ EK-1: dedektor Gazebo'da KOR -
240 orneklenmis karede, tum siniflar, conf>=0.10 -> 0 tespit. H1-H3+oracle
kollarinin dogrulama/capa/recovery bilesenleri bu yuzden SIFIRA coker; bu
harness hatasi degil, olculen bir sonuctur).

KOLLAR: A10.1 ile AYNI - H0 (kontrol) · H1 (dogrulayici) · H2 (+boyut
capasi) · H3 (+recovery) · H3-O-merkez / H3-O-boyut (UST SINIR).
K1-K6 A9_KABUL_OLCUTU.md'den, AYNEN.

HUCRE = SENARYO (Gazebo'da A9'un "seviye merdiveni" yok; A2/A5 hedefi kendi
icinde 60->8 px kucultuyor, bu ayri bir seviye-bazli tablo olarak
raporlanir ama K1-K6 hesabi senaryo duzeyindedir).
"""
import hashlib
import importlib.util as iu
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)


def _yukle(ad, dosya):
    sp = iu.spec_from_file_location(ad, os.path.join(HERE, dosya))
    m = iu.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


A8 = _yukle("A8", "tani_a8_adaptif_roi.py")
from calistir import iou                                   # noqa: E402
from gazebo.a11_ortak import (DOGRU_IOU, MIN_EPIZOT,        # noqa: E402
                              YANLIS_IOU, gercek_kaydirma,
                              kareleri_topla, kosular,
                              mod_etiketle, roi_tespit_g)
from takip.egomotion import EgoMotion                       # noqa: E402
from takip.hakem import Hakem                                # noqa: E402
from takip.izleyici import KILITLI, HedefTakip               # noqa: E402

SENARYOLAR = ["A1_taban", "A2_kucul", "A3_yaw", "A4_irtifa",
             "A5_kucul_yaw", "A6_celdirici"]
MODEL_AD = "A5_baseline"          # A10.1 EK-3 kararı: A6_uavdt_visdrone kosulmuyor
KOLLAR = {
    "H0": dict(dogrulayici=False),
    "H1": dict(dogrulayici=True),
    "H2": dict(dogrulayici=True, boyut_capasi=True),
    "H3": dict(dogrulayici=True, boyut_capasi=True, recovery=True),
    "H3-O-merkez": dict(dogrulayici=True, boyut_capasi=True, recovery=True,
                        oracle_merkez=True),
    "H3-O-boyut": dict(dogrulayici=True, boyut_capasi=True, recovery=True,
                       oracle_boyut=True),
}
ORACLE = {"H3-O-merkez", "H3-O-boyut"}
SEVIYE_SINIRLARI = [(0, 10, "8x5"), (10, 13, "10x5"), (13, 18, "15x7"),
                    (18, 25, "20x10"), (25, 1e9, "30x12_ve_ustu")]


def md5ler():
    return {f: hashlib.md5(open(os.path.join(ROOT, "takip", f), "rb").read()).hexdigest()
            for f in sorted(os.listdir(os.path.join(ROOT, "takip"))) if f.endswith(".py")}


def p(v, q):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return None if not v else round(float(np.percentile(v, q)), 3)


def seviye_ad(L):
    for lo, hi, ad in SEVIYE_SINIRLARI:
        if lo <= L < hi:
            return ad
    return "?"


# --------------------------------------------------------------------------
# 1) SAHTE EGO - koşumdan önceki sözü (§2 tanımı)
# --------------------------------------------------------------------------
def sahte_ego_olc(senaryo):
    kareler, W, H, fx, fy, cx, cy = kareleri_topla(senaryo)
    ego = EgoMotion()
    x_ref = np.array([W / 2.0, H / 2.0])
    vals, tanimsiz = [], 0
    for i, (img, gt, satir) in enumerate(kareler):
        gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        M, _guven = ego.guncelle(gri, None)
        if i == 0:
            continue
        gercek = gercek_kaydirma(x_ref, kareler[i - 1][2], satir, fx, fy, cx, cy)
        if gercek is None:
            tanimsiz += 1
            continue
        gorsel = M[:, :2] @ x_ref + M[:, 2]
        vals.append(float(np.linalg.norm(gorsel - gercek)))
    return {"kare": len(kareler), "nokta": len(vals), "tanimsiz": tanimsiz,
           "p50": p(vals, 50), "p95": p(vals, 95), "max": max(vals) if vals else None,
           "seri_ilk20": [round(v, 3) for v in vals[:20]]}


# --------------------------------------------------------------------------
# 2) HAKEM KOLLARI - A10.1 hucre_kos'un Gazebo'ya kenetlenmis hali
# --------------------------------------------------------------------------
def hucre_kos(kareler, kol, model, W, H):
    cfg = KOLLAR[kol]
    hakem = None
    if cfg.get("dogrulayici") is not False:
        hakem = Hakem(
            dedektor=lambda bgr, merkez, R: roi_tespit_g(model, bgr, merkez, R,
                                                         A8.B.yolo_calistir),
            **cfg)
    tak = HedefTakip(hakem=hakem)

    tazele_kayit = []
    _orij = tak._boyut_tazele

    def _sarmal(bgr):
        onc = np.asarray(tak.boyut, float).copy()
        _orij(bgr)
        son = np.asarray(tak.boyut, float).copy()
        tazele_kayit.append({"t": tak.kare, "oncesi": [round(float(v), 2) for v in onc],
                             "sonrasi": [round(float(v), 2) for v in son]})
    tak._boyut_tazele = _sarmal

    img0, gt0, _ = kareler[0]
    tak.kilitle(img0, gt0.copy())
    iz = []
    for t in range(1, len(kareler)):
        img, gt, satir = kareler[t]
        s = tak.guncelle(img, gt if kol in ORACLE else None)
        o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
        gtc = gt[:2] + gt[2:] / 2.0
        hata = float(np.linalg.norm(tak.kf.konum - gtc))
        L = float(np.max(gt[2:]))
        iz.append({"t": t, "iou": o, "durum": s["durum"],
                   "durum_takipci": (hakem.log[-1]["durum_takipci"]
                                    if hakem is not None and hakem.log else s["durum"]),
                   "psr": float(s["psr"]), "merkez_hata": hata, "gt_L": L,
                   "seviye": seviye_ad(L),
                   "p_iz": float(np.trace(tak.kf.P[:2, :2])),
                   "bho": float(np.max(tak.boyut)) / max(L, 1e-6)})

    iou_l = [x["iou"] for x in iz]
    hata_l = [x["merkez_hata"] for x in iz]
    yk = sum(1 for x in iz if x["durum"] == KILITLI and x["iou"] < YANLIS_IOU)
    yk_tak = sum(1 for x in iz if x["durum_takipci"] == "KILITLI" and x["iou"] < YANLIS_IOU)
    kopus = kosular(iz, lambda x: x["merkez_hata"] > 0.5 * x["gt_L"], 5)
    epiz = kosular(iz, lambda x: x["iou"] < YANLIS_IOU, MIN_EPIZOT)

    def stabil_ic(a, b, dogru):
        alt = iz[a:b + 1]
        f = ((lambda x: x["durum"] == KILITLI and x["iou"] >= DOGRU_IOU) if dogru
             else (lambda x: x["durum"] == KILITLI and x["iou"] < YANLIS_IOU))
        return kosular(alt, f, MIN_EPIZOT)
    basarili, sahte, sureler = 0, 0, []
    for a, b in epiz:
        dg = stabil_ic(a, b, True)
        yn = stabil_ic(a, b, False)
        if dg and not yn:
            basarili += 1
            sureler.append(dg[0][0])
        if yn:
            sahte += 1

    # Mod A/B etiketleme (A9 olcutu): ILK kopus icin, kopus SONRASI durum_takipci
    mod, dcf_oran = (None, None)
    if kopus:
        a0, _b0 = kopus[0]
        mod, dcf_oran = mod_etiketle(iz, a0)


    sonuc = {
        "kol": kol, "kare": len(iz),
        "iou_ort": round(float(np.mean(iou_l)), 4),
        "merkez_hata_p50": p(hata_l, 50), "merkez_hata_p95": p(hata_l, 95),
        "guvenli_yanlis_kilit": yk, "guvenli_yanlis_kilit_takipci_durumu": yk_tak,
        "kopus_sayisi": len(kopus), "kopus_kareleri": [iz[a]["t"] for a, _b in kopus],
        "kopuslu": bool(kopus), "mod": mod, "mod_dcf_kabul_orani": dcf_oran,
        "psr_p50": p([x["psr"] for x in iz], 50), "psr_p05": p([x["psr"] for x in iz], 5),
        "P_iz_p50": p([x["p_iz"] for x in iz], 50), "P_iz_p95": p([x["p_iz"] for x in iz], 95),
        "bho_p50": p([x["bho"] for x in iz], 50), "bho_p95": p([x["bho"] for x in iz], 95),
        "kilit_orani": round(sum(1 for x in iz if x["durum"] == KILITLI) / len(iz), 4),
        "kilit_orani_takipci": round(sum(1 for x in iz if x["durum_takipci"] == "KILITLI")
                                     / len(iz), 4),
        "boyut_tazele_cagri": len(tazele_kayit),
        "recovery_epizot": len(epiz), "basarili_recovery": basarili,
        "false_recovery": sahte, "recovery_sureleri": sureler,
        "gt_L_ort": round(float(np.mean([x["gt_L"] for x in iz])), 2),
    }
    if hakem is not None:
        sonuc["hakem"] = hakem.ozet(len(iz))
        # seviye bazinda kanit-yok (yalnizca dogrulama olan kareler)
        by_sev = {}
        for lg in hakem.log:
            if lg.get("kanit") is None:
                continue
            sev = seviye_ad(float(np.max(iz[min(lg["t"] - 1, len(iz) - 1)]["gt_L"])))
            d = by_sev.setdefault(sev, {"dogrulama": 0, "kanit_yok": 0})
            d["dogrulama"] += 1
            if lg["kanit"] == 0:
                d["kanit_yok"] += 1
        sonuc["kanit_yok_seviye"] = by_sev
    return sonuc


def main():
    import torch
    torch.set_num_threads(8)
    from ultralytics import YOLO

    agirlik, siniflar = A8.MODELLER[MODEL_AD]
    A8.B.AGIRLIK, A8.B.SINIFLAR = agirlik, siniflar
    model = YOLO(agirlik)
    A8.B.yolo_calistir(model, np.zeros((360, 640, 3), np.uint8))

    md5_bas = md5ler()
    cikti = {"etiketler": ["KAPALI CEVRIM", "KOMPOZIT YATAK YOK", "GAZEBO"],
             "onkayit": "docs/architecture/A11_ONKAYIT.md (+EK-1)",
             "model": MODEL_AD, "agirlik": agirlik,
             "md5_baslangic": md5_bas,
             "sahte_ego": {}, "hucreler": {}}

    print("===== SAHTE EGO (koşumdan önceki söz) =====", flush=True)
    for s in SENARYOLAR:
        r = sahte_ego_olc(s)
        cikti["sahte_ego"][s] = r
        print(f"  {s:<16} n={r['nokta']:<4} p50={r['p50']:<7} p95={r['p95']:<7} "
              f"max={r['max']}", flush=True)

    print("\n===== HAKEM KOLLARI (H0..H3+oracle) =====", flush=True)
    for s in SENARYOLAR:
        kareler, W, H, fx, fy, cx, cy = kareleri_topla(s)
        cikti["hucreler"][s] = {"kollar": {}, "genislik": W, "yukseklik": H}
        for kol in KOLLAR:
            r = hucre_kos(kareler, kol, model, W, H)
            cikti["hucreler"][s]["kollar"][kol] = r
            print(f"  {s:<16}{kol:<12} IoU={r['iou_ort']:.3f} "
                  f"YKtak={r['guvenli_yanlis_kilit_takipci_durumu']:<4} "
                  f"kopus={r['kopus_sayisi']} mod={r['mod']} "
                  f"kilit_tak={r['kilit_orani_takipci']:.2f}", flush=True)
        del kareler

    cikti["md5_bitis"] = md5ler()
    cikti["md5_degismedi"] = cikti["md5_baslangic"] == cikti["md5_bitis"]
    yol = os.path.join(ROOT, "cikti", "a11_kol0.json")
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
