"""A10 - KAPALI CEVRIM HAKEM KOSUMU.

*** KAPALI CEVRIM *** dedektor -> hakem -> takipci. Hakemin karari takipcinin
davranisini DEGISTIRIR. Acik cevrim olcum YOK.

ON-KAYIT: docs/architecture/A10_ONKAYIT.md (+ EK-1 donmus taban, EK-2 Mod A
surum 2, EK-3 model kolu) - hepsi KOSUMDAN ONCE yazildi.

KOLLAR
    H0            hakem yok (kontrol)
    H1            yalnizca dogrulayici
    H2            H1 + boyut capasi
    H3            H2 + recovery
    H3-O-merkez   H3, dogrulama/recovery referansi GT merkezi   -> UST SINIR
    H3-O-boyut    H3, capa GT boyutu                            -> UST SINIR

METRIKLER: A9_KABUL_OLCUTU.md'nin tamami + dogrulama maliyeti + acik/kapali
cevrim farki icin gereken sayaclar.
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


def _yukle(ad, dosya):
    sp = iu.spec_from_file_location(ad, os.path.join(HERE, dosya))
    m = iu.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


A7 = _yukle("A7", "tani_a7_roi.py")
A8 = _yukle("A8", "tani_a8_adaptif_roi.py")
B = A7.B
from calistir import iou                                          # noqa: E402
from takip.hakem import Hakem                                     # noqa: E402
from takip.izleyici import KILITLI, HedefTakip                    # noqa: E402

SENSOR, N_KARE = A7.SENSOR, A7.N_KARE
SEVIYELER = [30, 20, 15, 10, 8]
SEVIYE_AD = {40: "40x15", 30: "30x12", 20: "20x10", 15: "15x7", 10: "10x5",
             8: "8x5", 5: "5x5"}
# ON-KAYIT EK-1: DONMUS TABAN (7 dizi)
DIZILER = [("uav0000117_02622_v", 23, "KOPAN"), ("uav0000268_05773_v", 31, "KOPAN"),
           ("uav0000339_00001_v", 49, "KOPAN"), ("uav0000137_00458_v", 12, "saglam"),
           ("uav0000305_00000_v", 5, "saglam"), ("uav0000182_00000_v", 127, "saglam"),
           ("uav0000370_00001_v", 0, "?")]
ARTEFAKT = {"uav0000339_00001_v/49", "uav0000305_00000_v/5", "uav0000182_00000_v/127"}
DOGRU_IOU, YANLIS_IOU, MIN_EPIZOT, STABIL = 0.5, 0.2, 5, 5
MODEL_AD = "A5_baseline"                     # ON-KAYIT EK-3

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


def md5ler():
    out = {}
    for f in sorted(os.listdir(os.path.join(ROOT, "takip"))):
        if f.endswith(".py"):
            out[f] = hashlib.md5(
                open(os.path.join(ROOT, "takip", f), "rb").read()).hexdigest()
    return out


def p(v, q):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return None if not v else round(float(np.percentile(v, q)), 3)


def kosular(dizi_iz, esik, n):
    """esik(x) dogru olan >= n uzunluktaki azami ardisik dizilerin (bas, son)."""
    out, i, N = [], 0, len(dizi_iz)
    while i < N:
        if esik(dizi_iz[i]):
            j = i
            while j < N and esik(dizi_iz[j]):
                j += 1
            if j - i >= n:
                out.append((i, j - 1))
            i = j
        else:
            i += 1
    return out


def hucre_kos(d, kol, model, gt_L):
    """Tek hucre, tek kol. KAPALI CEVRIM."""
    cfg = KOLLAR[kol]
    hakem = None
    if cfg.get("dogrulayici") is not False:
        hakem = Hakem(
            dedektor=lambda bgr, merkez, R: A8.roi_tespit(model, bgr, merkez, R)[:3],
            roi_kurali=A8.R_sec, **cfg)
    tak = HedefTakip(hakem=hakem)

    # salt-okunur enstrumantasyon: _boyut_tazele oncesi/sonrasi (A9 §1 precedent'i)
    tazele_kayit = []
    _orij = tak._boyut_tazele

    def _sarmal(bgr):
        onc = np.asarray(tak.boyut, float).copy()
        _orij(bgr)
        son = np.asarray(tak.boyut, float).copy()
        tazele_kayit.append({"t": tak.kare,
                             "oncesi": [round(float(v), 2) for v in onc],
                             "sonrasi": [round(float(v), 2) for v in son]})
    tak._boyut_tazele = _sarmal

    tak.kilitle(d[0][0], d[0][1].copy())
    iz = []
    for t in range(1, len(d)):
        img, gt = d[t]
        s = tak.guncelle(img, gt if kol in ORACLE else None)
        o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
        gtc = np.asarray(gt[:2], float) + np.asarray(gt[2:], float) / 2.0
        hata = float(np.linalg.norm(tak.kf.konum - gtc))
        L = float(np.max(gt[2:]))
        iz.append({"t": t, "iou": o, "durum": s["durum"], "psr": float(s["psr"]),
                   "durum_takipci": (hakem.log[-1]["durum_takipci"]
                                     if hakem is not None and hakem.log else s["durum"]),
                   "merkez_hata": hata, "gt_L": L,
                   "p_iz": float(np.trace(tak.kf.P[:2, :2])),
                   "bho": float(np.max(tak.boyut)) / max(L, 1e-6)})

    iou_l = [x["iou"] for x in iz]
    hata_l = [x["merkez_hata"] for x in iz]
    yk = sum(1 for x in iz if x["durum"] == KILITLI and x["iou"] < YANLIS_IOU)
    # ETIKET confound'u: hakem KILITLI demeyerek YK'yi dusurebilir. Takipcinin
    # kendi durumuyla da sayilir; ikisi birlikte raporlanir.
    yk_tak = sum(1 for x in iz if x["durum_takipci"] == KILITLI and x["iou"] < YANLIS_IOU)
    kopus = kosular(iz, lambda x: x["merkez_hata"] > 0.5 * x["gt_L"], 5)
    epiz = kosular(iz, lambda x: x["iou"] < YANLIS_IOU, MIN_EPIZOT)

    # EK-1 recovery tanimlari
    def stabil_ic(a, b, dogru):
        alt = iz[a:b + 1]
        f = ((lambda x: x["durum"] == KILITLI and x["iou"] >= DOGRU_IOU) if dogru
             else (lambda x: x["durum"] == KILITLI and x["iou"] < YANLIS_IOU))
        return kosular(alt, f, STABIL)
    basarili, sahte, sureler = 0, 0, []
    for a, b in epiz:
        dg = stabil_ic(a, b, True)
        yn = stabil_ic(a, b, False)
        if dg and not yn:
            basarili += 1
            sureler.append(dg[0][0])          # tetikleme -> stabil kilidin ilk karesi
        if yn:
            sahte += 1

    sonuc = {
        "kol": kol, "kare": len(iz),
        "iou_ort": round(float(np.mean(iou_l)), 4),
        "merkez_hata_p50": p(hata_l, 50), "merkez_hata_p95": p(hata_l, 95),
        "guvenli_yanlis_kilit": yk,
        "guvenli_yanlis_kilit_takipci_durumu": yk_tak,
        "kilit_orani_takipci": round(sum(1 for x in iz
                                         if x["durum_takipci"] == KILITLI) / len(iz), 4),
        "kopus_sayisi": len(kopus), "kopus_kareleri": [iz[a]["t"] for a, _b in kopus],
        "kopuslu": bool(kopus),
        "psr_p50": p([x["psr"] for x in iz], 50), "psr_p05": p([x["psr"] for x in iz], 5),
        "P_iz_p50": p([x["p_iz"] for x in iz], 50), "P_iz_p95": p([x["p_iz"] for x in iz], 95),
        "bho_p50": p([x["bho"] for x in iz], 50), "bho_p95": p([x["bho"] for x in iz], 95),
        "kilit_orani": round(sum(1 for x in iz if x["durum"] == KILITLI) / len(iz), 4),
        "boyut_tazele_cagri": len(tazele_kayit), "boyut_tazele_kayit": tazele_kayit[:12],
        "recovery_epizot": len(epiz), "basarili_recovery": basarili,
        "false_recovery": sahte, "recovery_sureleri": sureler,
        "gt_L_ort": round(float(np.mean([x["gt_L"] for x in iz])), 2),
    }
    if hakem is not None:
        sonuc["hakem"] = hakem.ozet(len(iz))
        sonuc["capa_kayit"] = hakem.capa_kayit[:12]
    return sonuc


def main():
    import torch
    torch.set_num_threads(8)
    from ultralytics import YOLO

    agirlik, siniflar = A8.MODELLER[MODEL_AD]
    B.AGIRLIK, B.SINIFLAR = agirlik, siniflar
    model = YOLO(agirlik)
    B.yolo_calistir(model, np.zeros((360, 640, 3), np.uint8))

    md5_bas = md5ler()
    cikti = {"etiketler": ["KAPALI CEVRIM", "dedektor -> hakem -> takipci"],
             "onkayit": "docs/architecture/A10_ONKAYIT.md (+EK-1, EK-2, EK-3)",
             "model": MODEL_AD, "agirlik": agirlik,
             "sabitler": {"N": Hakem.N, "G_kapisi": Hakem.G_KAPISI, "k": Hakem.K,
                          "R_merdiveni": "1-5:160, 6-20:320, 21+:640",
                          "P_iz_esik": Hakem.P_IZ_ESIK,
                          "capa_agirlik": Hakem.CAPA_AGIRLIK,
                          "sinyal": "yalnizca d_norm"},
             "taban": [{"dizi": f"{a}/{b}", "rol": c,
                        "yatak_artefakti": f"{a}/{b}" in ARTEFAKT} for a, b, c in DIZILER],
             "md5_baslangic": md5_bas, "hucreler": {}}

    for dizi_ad, tid, rol in DIZILER:
        ad = f"{dizi_ad}/{tid}"
        kareler = B.kareleri_topla(dizi_ad, tid, N_KARE)
        W, H = kareler[0][3], kareler[0][4]
        hucre, _uz = B.arkaplan_hucresi(kareler, W, H, *SENSOR)
        for L in SEVIYELER:
            d, _s = A7.sensor_dizi(kareler, hucre, L, N_KARE)
            if len(d) < 10:
                continue
            hd = f"{ad}|{SEVIYE_AD[L]}"
            cikti["hucreler"][hd] = {"dizi": ad, "rol": rol, "seviye": SEVIYE_AD[L],
                                     "yatak_artefakti": ad in ARTEFAKT, "kollar": {}}
            for kol in KOLLAR:
                r = hucre_kos(d, kol, model, L)
                cikti["hucreler"][hd]["kollar"][kol] = r
                print(f"  {hd:<32} {kol:<12} IoU={r['iou_ort']:.3f} "
                      f"YK={r['guvenli_yanlis_kilit']:<3} kopus={r['kopus_sayisi']} "
                      f"bho50={r['bho_p50']} kilit={r['kilit_orani']:.2f}", flush=True)
            del d

    cikti["md5_bitis"] = md5ler()
    cikti["md5_degismedi"] = cikti["md5_baslangic"] == cikti["md5_bitis"]
    yol = os.path.join(ROOT, "cikti", "a10_hakem.json")
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
