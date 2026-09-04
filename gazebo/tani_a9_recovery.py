"""A9 ASAMA 3 - Deney 3.0: OLAY TABANI + TETIKLEYICI TESHISI (SALT OKUNUR).

*** ACIK CEVRIM · TESHIS · GT YALNIZCA OFFLINE ETIKETLEME ***
Recovery mekanizmasi HENUZ KURULMADI. Dedektor KOSMUYOR. Esik SECILMEZ.
takip/ DEGISMEZ. Tracker davranisi DEGISMEZ.

Asama 2 hukmu: Mod A ve Mod B icin TEK ortak tetikleyici varsayilamaz.
Bu deney iki yolu AYRI olcer.

CEVAPLANAN SORULAR
------------------
S1 (3A "once olay tabanini olustur"):
    Recovery ne zaman GEREKLI? (GT ile etiketlenmis epizotlar)
    Epizot basinda takipcinin ic sinyalleri ne durumda?
S2 (3A adim 1-2, "son guvenilir merkez ve belirsizlik alani"):
    Arama yaricapi NE KADAR genis olmali, ve Kalman P bunu ONGORUYOR MU?
S3 (3B "once teshis"):
    benzerlik operasyonel bir tetikleyici olmaya YETIYOR MU?
    Ozellikle takipci KILITLI gorunurken (Mod B'nin tanimli oldugu kosul).

TANIMLAR: docs/architecture/A9_KABUL_OLCUTU.md EK-1 (bu deneyden ONCE yazildi).
  dogru hedef  : IoU >= 0.5
  yanlis hedef : IoU < 0.2
  epizot       : IoU < 0.2 olan, >= 5 kare uzunlugunda azami ardisik dizi
"""
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


A9 = _yukle("A9", "tani_a9_merkez.py")
KOP = _yukle("KOP", "tani_a9_kopus.py")
A7, B = A9.A7, A9.B
import takip.izleyici as IZ                                # noqa: E402
from calistir import iou                                   # noqa: E402
from takip.izleyici import KILITLI, HedefTakip             # noqa: E402
from veri.visdrone import VisDroneVidKaynak                # noqa: E402

SENSOR, N_KARE = A9.SENSOR, A9.N_KARE
SEVIYELER = [30, 20, 15, 10, 8]
SEVIYE_AD = A9.SEVIYE_AD
KOPAN = ["uav0000117_02622_v/23", "uav0000268_05773_v/31", "uav0000339_00001_v/49"]
DIZILER = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31),
           ("uav0000339_00001_v", 49), ("uav0000137_00458_v", 12),
           ("uav0000305_00000_v", 5), ("uav0000182_00000_v", 127)]
DOGRU_IOU, YANLIS_IOU, MIN_EPIZOT = 0.5, 0.2, 5
_ORIG_RAFINE = IZ.rafine_kutu


def hucre_kos(dizi):
    """Bir hucreyi bir kez kosar; kare basina sinyal + konum + GT etiketi."""
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    kilit_boyut = float(np.max(tak.boyut))
    log = []
    sar = A9.KayitKalman(tak.kf, log)
    object.__setattr__(sar, "_tak", tak)
    tak.kf = sar
    raf = []

    def _rk(bgr, merkez, boyut, **kw):
        r = _ORIG_RAFINE(bgr, merkez, boyut, **kw)
        raf.append(r is None)
        return r

    IZ.rafine_kutu = _rk
    K = []
    try:
        for t in range(1, len(dizi)):
            img, gt = dizi[t]
            gc = (gt[:2] + gt[2:] / 2.0).astype(np.float64)
            gL = float(max(gt[2], gt[3]))
            object.__setattr__(sar, "_gt", gc)
            n0 = len(log)
            s = tak.guncelle(img)
            duz = [e for e in log[n0:]
                   if e["kaynak"] == "_takip_adimi" and e["tip"] == "duzelt"]
            kfc = tak.kf.konum.astype(float)
            P = tak.kf.P
            o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
            K.append({
                "t": t,
                "psr": round(float(s["psr"]), 3),
                "benzerlik": round(float(s["benzerlik"]), 4),
                "P_konum_iz": round(float(P[0, 0] + P[1, 1]), 3),
                "kf_belirsizlik_px": round(float(np.sqrt(max(P[0, 0] + P[1, 1], 0.0))), 3),
                "kayip": int(s["kayip"]),
                "durum_kilitli": 1 if s["durum"] == KILITLI else 0,
                "olcum_yok": 0 if duz else 1,
                "boyut_orani": round(float(np.max(tak.boyut)) / max(kilit_boyut, 1e-6), 4),
                "rafine_none_kosan": round(float(np.mean(raf)) if raf else 0.0, 4),
                "kf_merkez": [round(float(v), 2) for v in kfc],
                # --- OFFLINE ETIKET ---
                "_gt_merkez": [round(float(v), 2) for v in gc],
                "_gt_L": round(gL, 2),
                "_iou": round(o, 4),
                "_hata_px": round(float(np.linalg.norm(kfc - gc)), 2),
            })
    finally:
        IZ.rafine_kutu = _ORIG_RAFINE
    return K


def epizotlari_bul(K):
    """IoU < YANLIS_IOU olan, >= MIN_EPIZOT uzunlugunda azami ardisik diziler."""
    ep, i, n = [], 0, len(K)
    while i < n:
        if K[i]["_iou"] < YANLIS_IOU:
            j = i
            while j < n and K[j]["_iou"] < YANLIS_IOU:
                j += 1
            if j - i >= MIN_EPIZOT:
                # son guvenilir kare: epizot oncesi IoU >= DOGRU_IOU olan SON kare
                sg = None
                for k in range(i - 1, -1, -1):
                    if K[k]["_iou"] >= DOGRU_IOU:
                        sg = k
                        break
                ep.append({"bas_idx": i, "son_idx": j - 1, "uzunluk": j - i,
                           "son_guvenilir_idx": sg})
            i = j
        else:
            i += 1
    return ep


def main():
    hucreler, epizotlar = {}, []
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
        print(f"\n--- {ad} [{rol}] ---", flush=True)
        for L in SEVIYELER:
            d, s = A7.sensor_dizi(kareler, hucre, L, N_KARE)
            if len(d) < 10:
                continue
            K = hucre_kos(d)
            anahtar = f"{ad}|{SEVIYE_AD[L]}"
            hucreler[anahtar] = {"rol": rol, "kareler": K}
            eps = epizotlari_bul(K)
            for e in eps:
                e["hucre"] = anahtar
                e["rol"] = rol
                b = K[e["bas_idx"]]
                e["bas_t"] = b["t"]
                e["bas_sinyaller"] = {x: b[x] for x in
                                      ["psr", "benzerlik", "P_konum_iz", "kayip",
                                       "durum_kilitli", "olcum_yok", "boyut_orani"]}
                # KILITLI gorunurken mi basliyor? (Mod B imzasi)
                e["baslangicta_kilitli"] = bool(b["durum_kilitli"])
                # S2: gerekli arama yaricapi vs Kalman belirsizligi
                if e["son_guvenilir_idx"] is not None:
                    sg = K[e["son_guvenilir_idx"]]
                    merkez0 = np.array(sg["kf_merkez"])
                    yari = []
                    for i in range(e["bas_idx"], e["son_idx"] + 1):
                        g = np.array(K[i]["_gt_merkez"])
                        yari.append({
                            "gecen_kare": K[i]["t"] - sg["t"],
                            "gerekli_yaricap_px": round(float(np.linalg.norm(g - merkez0)), 2),
                            "kf_belirsizlik_px": K[i]["kf_belirsizlik_px"],
                            "gt_L": K[i]["_gt_L"]})
                    e["yaricap_serisi"] = yari
                epizotlar.append(e)
            print(f"  {SEVIYE_AD[L]:6s} epizot={len(eps)} "
                  f"{[(x['bas_t'], x['uzunluk'], 'KILITLI' if x['baslangicta_kilitli'] else 'degil') for x in eps]}",
                  flush=True)

    # ---------------- S1: OLAY TABANI OZETI ----------------
    kilitli_bas = [e for e in epizotlar if e["baslangicta_kilitli"]]
    print(f"\n=== OLAY TABANI ===")
    print(f"  toplam epizot: {len(epizotlar)}  (KOPAN dizilerde "
          f"{sum(1 for e in epizotlar if e['rol']=='KOPAN')}, saglamda "
          f"{sum(1 for e in epizotlar if e['rol']=='saglam')})")
    print(f"  epizot BASLANGICINDA durum KILITLI olanlar: {len(kilitli_bas)}/{len(epizotlar)}"
          f"  <-- 'durum != KILITLI' tetikleyicisinin KACIRACAGI epizotlar")

    # ---------------- S2: ARAMA YARICAPI ----------------
    yr = [(y["gecen_kare"], y["gerekli_yaricap_px"], y["kf_belirsizlik_px"], y["gt_L"])
          for e in epizotlar if "yaricap_serisi" in e for y in e["yaricap_serisi"]]
    s2 = {}
    if yr:
        arr = np.array(yr)
        print(f"\n=== S2: ARAMA YARICAPI (son guvenilir merkeze gore) ===")
        print(f"  {'gecen kare':<12}{'n':>5}{'gerekli yaricap p50':>22}{'p95':>9}"
              f"{'KF belirsizlik p50':>21}{'yaricap/belirsizlik p50':>25}")
        for lo, hi in [(1, 5), (5, 10), (10, 20), (20, 40), (40, 999)]:
            m = (arr[:, 0] >= lo) & (arr[:, 0] < hi)
            if m.sum() < 3:
                continue
            g, bel = arr[m, 1], arr[m, 2]
            oran = g / np.maximum(bel, 1e-6)
            s2[f"{lo}-{hi}"] = {"n": int(m.sum()),
                                "gerekli_yaricap_p50": round(float(np.percentile(g, 50)), 1),
                                "gerekli_yaricap_p95": round(float(np.percentile(g, 95)), 1),
                                "kf_belirsizlik_p50": round(float(np.percentile(bel, 50)), 1),
                                "yaricap_bolu_belirsizlik_p50": round(float(np.percentile(oran, 50)), 2),
                                "yaricap_bolu_belirsizlik_p95": round(float(np.percentile(oran, 95)), 2)}
            v = s2[f"{lo}-{hi}"]
            print(f"  {f'{lo}-{hi}':<12}{v['n']:>5}{v['gerekli_yaricap_p50']:>22.1f}"
                  f"{v['gerekli_yaricap_p95']:>9.1f}{v['kf_belirsizlik_p50']:>21.1f}"
                  f"{v['yaricap_bolu_belirsizlik_p50']:>25.2f}")

    # ---------------- S3: BENZERLIK YETERLI MI ----------------
    dogru_b, yanlis_b, dogru_k, yanlis_k = [], [], [], []
    dogru_psr, yanlis_psr = [], []
    for h in hucreler.values():
        for x in h["kareler"]:
            if x["_iou"] >= DOGRU_IOU:
                dogru_b.append(x["benzerlik"]); dogru_psr.append(x["psr"])
                if x["durum_kilitli"]:
                    dogru_k.append(x["benzerlik"])
            elif x["_iou"] < YANLIS_IOU:
                yanlis_b.append(x["benzerlik"]); yanlis_psr.append(x["psr"])
                if x["durum_kilitli"]:
                    yanlis_k.append(x["benzerlik"])
    f = lambda L: {"n": len(L), "p05": A9.p(L, 5), "p25": A9.p(L, 25),
                   "p50": A9.p(L, 50), "p95": A9.p(L, 95)} if L else None
    s3 = {
        "benzerlik_dogru_hedef": f(dogru_b), "benzerlik_yanlis_hedef": f(yanlis_b),
        "benzerlik_auc_tum": KOP._auc([-x for x in yanlis_b], [-x for x in dogru_b]),
        "benzerlik_dogru_KILITLI": f(dogru_k), "benzerlik_yanlis_KILITLI": f(yanlis_k),
        "benzerlik_auc_KILITLI_iken": KOP._auc([-x for x in yanlis_k], [-x for x in dogru_k]),
        "psr_auc_KILITLI_iken": None,
        "benzerlik_esitlik_orani_dogru": round(float(np.mean([x == 1.0 for x in dogru_k])), 4) if dogru_k else None,
        "benzerlik_esitlik_orani_yanlis": round(float(np.mean([x == 1.0 for x in yanlis_k])), 4) if yanlis_k else None,
    }
    dpsr_k, ypsr_k = [], []
    for h in hucreler.values():
        for x in h["kareler"]:
            if not x["durum_kilitli"]:
                continue
            (dpsr_k if x["_iou"] >= DOGRU_IOU else
             (ypsr_k if x["_iou"] < YANLIS_IOU else [])).append(x["psr"])
    s3["psr_auc_KILITLI_iken"] = KOP._auc([-x for x in ypsr_k], [-x for x in dpsr_k])
    s3["psr_dogru_KILITLI"] = f(dpsr_k)
    s3["psr_yanlis_KILITLI"] = f(ypsr_k)
    print(f"\n=== S3: BENZERLIK TETIKLEYICI OLARAK ===")
    print(f"  TUM kareler   : dogru n={s3['benzerlik_dogru_hedef']['n']} p50={s3['benzerlik_dogru_hedef']['p50']} | "
          f"yanlis n={s3['benzerlik_yanlis_hedef']['n']} p50={s3['benzerlik_yanlis_hedef']['p50']} | "
          f"AUC={s3['benzerlik_auc_tum']}")
    print(f"  KILITLI iken  : dogru n={s3['benzerlik_dogru_KILITLI']['n']} p50={s3['benzerlik_dogru_KILITLI']['p50']} | "
          f"yanlis n={s3['benzerlik_yanlis_KILITLI']['n']} p50={s3['benzerlik_yanlis_KILITLI']['p50']} | "
          f"AUC={s3['benzerlik_auc_KILITLI_iken']}")
    print(f"  benzerlik==1.0 orani: dogru={s3['benzerlik_esitlik_orani_dogru']} "
          f"yanlis={s3['benzerlik_esitlik_orani_yanlis']}")
    print(f"  KILITLI iken PSR AUC={s3['psr_auc_KILITLI_iken']}")

    yol = "cikti/a9_takipci_merkez_recovery.json"
    J = json.load(open(yol))
    J["phase3_recovery"] = {
        "etiketler": ["ACIK CEVRIM", "TESHIS", "GT YALNIZCA OFFLINE ETIKETLEME"],
        "deney": "3.0 - olay tabani + tetikleyici teshisi",
        "not": ("Recovery mekanizmasi KURULMADI, dedektor KOSMADI, esik SECILMEDI, "
                "takip/ ve tracker davranisi DEGISMEDI."),
        "tanimlar_kaynagi": "docs/architecture/A9_KABUL_OLCUTU.md EK-1 (deneyden ONCE yazildi)",
        "mod_a": {
            "olay_tabani": {
                "toplam_epizot": len(epizotlar),
                "kopan_dizilerde": sum(1 for e in epizotlar if e["rol"] == "KOPAN"),
                "saglam_dizilerde": sum(1 for e in epizotlar if e["rol"] == "saglam"),
                "baslangicta_KILITLI_epizot": len(kilitli_bas),
                "not": "baslangicta KILITLI olan epizotlari 'durum != KILITLI' tetikleyicisi KACIRIR"},
            "arama_yaricapi_vs_kf_belirsizligi": s2,
            "epizotlar": epizotlar},
        "mod_b": {"benzerlik_teshisi": s3},
        "limitations": [
            "Acik cevrim; dedektor kosmadi. Recovery'nin DOGRU hedefi bulup bulamayacagi HENUZ olculmedi.",
            "Epizot sayisi dusuk; istatistiksel guc sinirli.",
            "Yatak: A8/A9 kompozit (sureklilik icin). Gazebo senaryolari AYRI etiketlenecek, bu deneyde kullanilmadi.",
            "GT yalnizca epizot etiketleme ve yaricap olcumu icin; hicbir tetikleyici GT kullanmiyor.",
        ],
    }
    json.dump(J, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
