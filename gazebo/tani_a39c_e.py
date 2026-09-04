"""A3.9c - SALT OKUNUR gozlemci: aday E (RANSAC outlier kumesinin uzami).

TAKIPCIYE HICBIR SEY BESLENMEZ. `takip/` degismez. Olcum her KILITLI karede
hesaplanir, kaydedilir ve ATILIR.

OLCUM HATTI (D_YENI_BOYUT_OLUM_TASARIMI.md, Aday 1):
    goodFeaturesToTrack (MASKESIZ)  ->  cift yonlu LK  ->
    estimateAffinePartial2D (RANSAC) -> inlier / OUTLIER ayrimi ->
    outlier kumesinin geometrik uzami

NEDEN GERCEK `EgoMotion`'IN NOKTALARI KULLANILMIYOR:
`egomotion.py:105-110 _maske` hedef kutusunu 6 px payla MASKELER, yani gercek
ego nokta kumesinde hedefin ustunde nokta YOKTUR. O kumeyi kullanmak hem
olcumu imkansiz kilardi hem de A1'i (kutudan bagimsizlik) ihlal ederdi.
Bu yuzden gozlemci KENDI maskesiz nokta kumesini kurar - hicbir yerde kutu
okunmaz.

TAM COZUNURLUK: gercek ego 0.5x kucultulmus karede calisir (`olcek=0.5`).
Burada olcum TAM COZUNURLUKTE yapilir ve nokta sayisi 100 -> 1000'e cikarilir.
Bu, adaya MUMKUN OLAN EN IYI SANSI verir; burada basarisiz olan bir olcum
0.5x ve 100 noktayla evleviyetle basarisiz olur.

ILISKILENDIRME KURALLARI (hicbiri `boyut` kullanmaz):
    E1  tum outlier'lar (kume yok)
    E2  takip MERKEZINE en yakin outlier'in tek-baglantili kumesi
        (baglanti olcegi VERIDEN turetilir: outlier'larin en yakin komsu
         mesafelerinin medyani)
    E3  GT kutusu icine dusen outlier'lar  -> KOSUMDA KULLANILAMAZ, UST SINIR
        ("olcum hic var mi?" sorusunu yanitlar)

Kullanim: python3 -m gazebo.tani_a39c_e
"""
import argparse
import json
import os
import time

import cv2
import numpy as np

import main as ana
from gazebo.tani_4o_dcf import _kaynak
from takip.izleyici import KILITLI, HedefTakip

KAYNAKLAR = [("117/23", "visdrone", ("uav0000117_02622_v", 23), "birincil"),
             ("137/12", "visdrone", ("uav0000137_00458_v", 12), "birincil"),
             ("305/5", "visdrone", ("uav0000305_00000_v", 5), "destek"),
             ("G6_agresif", "gazebo", "G6_agresif", "destek"),
             ("G6_agresif_durakli", "gazebo", "G6_agresif_durakli", "destek"),
             ("G3_agresif", "gazebo", "G3_agresif", "destek"),
             ("G3_kritik", "gazebo", "G3_kritik", "destek"),
             ("G0", "gazebo", "G0", "destek")]

# Kose parametreleri: kalite/mesafe/blok `egomotion.py:50` ile AYNI.
# Yalnizca sayi 100 -> 1000 (adaya en iyi sans) ve MASKE YOK.
MAX_NOKTA, KALITE, MIN_MESAFE, BLOK = 1000, 0.01, 8, 5
LK = dict(winSize=(15, 15), maxLevel=2,
          criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 12, 0.03))
FB_ESIK = 1.0          # egomotion.py:81 ile ayni
RANSAC_ESIK = 2.0      # egomotion.py:84 ile ayni


def _uzam(p):
    """Nokta bulutunun uzami: eksen hizali, PCA yonelimli ve kovaryans."""
    if len(p) < 3:
        return None
    mu = p.mean(0)
    C = np.cov(p.T) if len(p) > 2 else np.zeros((2, 2))
    ea = p.max(0) - p.min(0)                       # eksen hizali (min-max)
    q = np.percentile(p, [5, 95], axis=0)
    ep = q[1] - q[0]                               # eksen hizali (p5-p95)
    try:
        w, V = np.linalg.eigh(C)
        sira = np.argsort(w)[::-1]
        w, V = w[sira], V[:, sira]
        pr = (p - mu) @ V
        eo = pr.max(0) - pr.min(0)                 # yonelimli uzam
        # yonelimli kutunun eksen hizali sinirlayicisi
        kose = np.array([[eo[0] / 2, eo[1] / 2], [eo[0] / 2, -eo[1] / 2],
                         [-eo[0] / 2, eo[1] / 2], [-eo[0] / 2, -eo[1] / 2]])
        kd = kose @ V.T + mu
        eob = kd.max(0) - kd.min(0)
    except np.linalg.LinAlgError:
        w, V, eo, eob = np.zeros(2), np.eye(2), np.zeros(2), np.zeros(2)
    return {"n": int(len(p)),
            "centroid": [float(mu[0]), float(mu[1])],
            "kovaryans": [[float(C[0, 0]), float(C[0, 1])],
                          [float(C[1, 0]), float(C[1, 1])]],
            "ozdeger": [float(w[0]), float(w[1])],
            "ana_eksen": [float(V[0, 0]), float(V[1, 0])],
            "eksen_hizali_minmax": [float(ea[0]), float(ea[1])],
            "eksen_hizali_p5p95": [float(ep[0]), float(ep[1])],
            "yonelimli": [float(eo[0]), float(eo[1])],
            "yonelimli_aabb": [float(eob[0]), float(eob[1])]}


def _kume(p, merkez):
    """Merkeze en yakin outlier'in tek-baglantili kumesi.
    Baglanti olcegi VERIDEN: en yakin komsu mesafelerinin medyani."""
    if len(p) < 2:
        return p
    D = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=2)
    np.fill_diagonal(D, np.inf)
    olc = float(np.median(D.min(1)))
    if not np.isfinite(olc) or olc <= 0:
        return p
    baslangic = int(np.argmin(np.linalg.norm(p - np.asarray(merkez), axis=1)))
    kume, sinir = {baslangic}, [baslangic]
    while sinir:
        i = sinir.pop()
        for j in np.nonzero(D[i] <= olc)[0]:
            if int(j) not in kume:
                kume.add(int(j))
                sinir.append(int(j))
    return p[sorted(kume)]


class GozTakip(HedefTakip):
    """Yalnizca kare ve merkezi disari verir; takipci davranisi degismez."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []

    def guncelle(self, bgr):
        s = super().guncelle(bgr)
        self.iz.append({"durum": self.durum,
                        "merkez": self.kf.konum.astype(np.float64)})
        return s


def kos(ad, tur, arg, rol):
    ilk = ana.HedefTakip
    tut = {}
    ana.HedefTakip = lambda *a, **k: tut.setdefault("t", GozTakip(*a, **k))
    try:
        m = ana.kos(_kaynak(tur, arg), pencere=False)
    finally:
        ana.HedefTakip = ilk
    tak = tut["t"]
    ofset = int(m["kare"]) - len(tak.iz)
    td = m.get("t_drift")

    # kareleri ve GT'yi ayri gecerek oku (takipci yeniden kosturulmaz)
    gri, gt = {}, {}
    for kare in _kaynak(tur, arg):
        gri[kare.indeks] = cv2.cvtColor(kare.goruntu, cv2.COLOR_BGR2GRAY)
        if kare.gt is not None and kare.gorunur:
            gt[kare.indeks] = [float(v) for v in kare.gt]
    iou_k = {r["kare"]: r["iou"] for r in m.get("_olcum") or []}

    satir = []
    for i, r in enumerate(tak.iz):
        k = ofset + i
        if r["durum"] != KILITLI or k not in gt or k not in gri or (k - 1) not in gri:
            continue
        g = np.asarray(gt[k], np.float32)
        gc = (g[0] + g[2] / 2, g[1] + g[3] / 2)
        d = {"kare": k, "rol": rol, "durum": r["durum"],
             "drift_state": "once" if (td is None or k < td) else "sonra",
             "gt_w": float(g[2]), "gt_h": float(g[3]),
             "merkez_hata": float(np.hypot(r["merkez"][0] - gc[0],
                                           r["merkez"][1] - gc[1])),
             "iou_takip": iou_k.get(k)}
        t0 = time.perf_counter()
        onc, sim = gri[k - 1], gri[k]
        p0 = cv2.goodFeaturesToTrack(onc, MAX_NOKTA, KALITE, MIN_MESAFE,
                                     mask=None, blockSize=BLOK)
        if p0 is None or len(p0) < 6:
            d.update({"failure_reason": "kose_yok",
                      "n_kose": 0 if p0 is None else int(len(p0))})
            d["sure_ms"] = (time.perf_counter() - t0) * 1e3
            satir.append(d)
            continue
        p1, st, _ = cv2.calcOpticalFlowPyrLK(onc, sim, p0, None, **LK)
        p0r, st2, _ = cv2.calcOpticalFlowPyrLK(sim, onc, p1, None, **LK)
        iyi = (st.ravel() == 1) & (st2.ravel() == 1)
        iyi &= (np.abs(p0 - p0r).reshape(-1, 2).max(1) < FB_ESIK)
        a_, b_ = p0[iyi], p1[iyi]
        d["n_kose"] = int(len(p0))
        d["n_lk"] = int(iyi.sum())
        if len(a_) < 6:
            d["failure_reason"] = "lk_yetersiz"
            d["sure_ms"] = (time.perf_counter() - t0) * 1e3
            satir.append(d)
            continue
        M, ic = cv2.estimateAffinePartial2D(a_, b_, method=cv2.RANSAC,
                                            ransacReprojThreshold=RANSAC_ESIK,
                                            maxIters=200, confidence=0.99)
        if M is None or ic is None:
            d["failure_reason"] = "ransac_yok"
            d["sure_ms"] = (time.perf_counter() - t0) * 1e3
            satir.append(d)
            continue
        ic = ic.ravel().astype(bool)
        d["inlier_count"] = int(ic.sum())
        d["outlier_count"] = int((~ic).sum())
        d["sure_ms"] = (time.perf_counter() - t0) * 1e3
        # outlier'lar: SIMDIKI karedeki konumlari
        out = b_.reshape(-1, 2)[~ic]
        if len(out) < 3:
            d["failure_reason"] = "outlier_az"
            satir.append(d)
            continue
        d["failure_reason"] = None
        # --- E1: tum outlier'lar ---
        d["E1"] = _uzam(out)
        # --- E2: merkeze en yakin tek-baglantili kume ---
        d["E2"] = _uzam(_kume(out, r["merkez"]))
        # --- E3: GT kutusu icindekiler (UST SINIR) ---
        ig = ((out[:, 0] >= g[0]) & (out[:, 0] <= g[0] + g[2])
              & (out[:, 1] >= g[1]) & (out[:, 1] <= g[1] + g[3]))
        d["gt_icindeki_outlier"] = int(ig.sum())
        d["E3_oracle"] = _uzam(out[ig])
        satir.append(d)

    return {"ad": ad, "rol": rol, "ort_iou": float(m.get("ort_iou", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "t_drift": td, "satir": satir}


def dag(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if len(v) < 3:
        return None
    return {"n": int(len(v)), "med": float(np.median(v)),
            "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95))}


def ozet(r):
    td = r["t_drift"]
    print(f"\n== {r['ad']} ({r['rol']}) == IoU {r['ort_iou']:.6f} "
          f"kilit {100*r['kilit_orani']:.2f}% drift {td}  "
          f"KILITLI+GT kare {len(r['satir'])}")
    if not r["satir"]:
        return
    sr = [x for x in r["satir"] if "sure_ms" in x]
    print(f"   ek maliyet ort {np.mean([x['sure_ms'] for x in sr]):.1f} ms/kare"
          f"  |  kose ort {np.mean([x.get('n_kose', 0) for x in r['satir']]):.0f}"
          f"  LK ort {np.mean([x.get('n_lk', 0) for x in r['satir']]):.0f}"
          f"  outlier ort {np.mean([x.get('outlier_count', 0) for x in r['satir']]):.1f}"
          f"  GT icinde ort {np.mean([x.get('gt_icindeki_outlier', 0) for x in r['satir']]):.1f}")
    nedenler = {}
    for x in r["satir"]:
        nedenler[x.get("failure_reason")] = nedenler.get(x.get("failure_reason"), 0) + 1
    print("   failure_reason:", nedenler)
    for faz in ("once", "sonra"):
        s = [x for x in r["satir"] if x["drift_state"] == faz]
        if len(s) < 3:
            continue
        print(f"   -- drift {faz} ({len(s)} kare)")
        for nm in ("E1", "E2", "E3_oracle"):
            v = [x for x in s if x.get(nm)]
            if len(v) < 3:
                print(f"      {nm:10s} kullanilabilir {len(v)}/{len(s)} (yetersiz)")
                continue
            for et, alan in (("minmax", "eksen_hizali_minmax"),
                             ("p5p95", "eksen_hizali_p5p95")):
                ow = dag([x[nm][alan][0] / x["gt_w"] for x in v])
                oh = dag([x[nm][alan][1] / x["gt_h"] for x in v])
                if not ow or not oh:
                    continue
                print(f"      {nm:10s} [{et}] kull %{100*len(v)/len(s):5.1f}  "
                      f"w/GT med {ow['med']:5.2f} [{ow['p5']:5.2f}..{ow['p95']:5.2f}]  "
                      f"h/GT med {oh['med']:5.2f} [{oh['p5']:5.2f}..{oh['p95']:5.2f}]  "
                      f"n_nokta med {np.median([x[nm]['n'] for x in v]):.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/a39c_e_observer.json")
    a = ap.parse_args()
    out = {}
    for ad, tur, arg, rol in KAYNAKLAR:
        r = kos(ad, tur, arg, rol)
        out[ad] = r
        ozet(r)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"\nyazildi: {a.json}")


if __name__ == "__main__":
    main()
