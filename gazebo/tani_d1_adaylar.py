"""D1 - salt okunur: `HareketTespit.adaylar()` KILITLI durumda MUTLAK ve
`boyut`tan BAGIMSIZ bir w/h olcumu veriyor mu?

TAKIP/ HIC DEGISMEZ. `adaylar()` gercek haliyle, kare icinde `_arama_adimi`nin
cagrilacagi NOKTADA (ego M hesaplandiktan sonra, `tespit.kare_ekle`den once)
FAZLADAN bir kez cagrilir ve yalnizca GOZLENIR; sonucu takipciye verilmez.

Davranisa etkisizligin kaniti: `adaylar()`in tek yan etkisi
`self._son_maske = ikili` (tespit.py:69) ve `_son_maske` depoda **hicbir yerde
okunmuyor** (grep: yalnizca tespit.py:32 ve :69). Ayrica kosum sonunda
baseline metrikleri karsilastirilir.

`adaylar()` KOD YOLU (tespit.py:47-84) - urettigi olcumler:
   52  w1 = warpAffine(g1, M)                 onceki kare ego ile hizalanir
   54  d  = absdiff(gri, w1)                  |I_t - warp(I_{t-1})|
   55-59 uc_kare=True ise d = min(d, |I_t - warp2(I_{t-2})|)   (varsayilan False)
   60  d  = GaussianBlur(d, 5x5)
   62-63 kenardan 8 px kirpilir (warp artefakti)
   65  esik = max(min_esik=8.0, d.mean() + esik_k(4.0) * d.std())   <- MUTLAK
   66  ikili = threshold(d, esik)
   67-68 MORPH_CLOSE(3x3) + dilate(3x3)
   71  connectedComponentsWithStats(ikili, 8)
   75  alan < min_alan(3) veya bw > max_kenar(160) veya bh > 160  -> ele
   77  max(bw,bh)/min(bw,bh) > 9                                  -> ele
   79-82 kutu=(x,y,bw,bh), merkez=centroid, alan, guc=d ortalamasi
   83-84 alana gore sirala, ilk 40
`self.boyut`, `kf.konum`, `rafine_kutu` ya da bunlardan turetilmis hicbir
buyukluk bu yolda OKUNMAZ. Tum esikler MUTLAKTIR (piksel / alan).

Kullanim: python3 -m gazebo.tani_d1_adaylar
"""
import argparse
import json
import os
import time

import numpy as np

import main as ana
from gazebo.tani_4o_dcf import _kaynak
import takip.izleyici as izl
from takip.izleyici import KILITLI, HedefTakip

KAYNAKLAR = [("117/23", "visdrone", ("uav0000117_02622_v", 23)),
             ("137/12", "visdrone", ("uav0000137_00458_v", 12)),
             ("305/5", "visdrone", ("uav0000305_00000_v", 5)),
             ("G6_agresif", "gazebo", "G6_agresif"),
             ("G6_agresif_durakli", "gazebo", "G6_agresif_durakli")]


def _iou(a, b):
    return float(ana.iou(np.asarray(a, np.float32), np.asarray(b, np.float32)))


class D1Takip(HedefTakip):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []
        self._M = None
        self._d = {}
        g_ego = self.ego.guncelle

        def ego_s(gri, kutu=None):
            M, gv = g_ego(gri, kutu)
            self._M = np.asarray(M, np.float64).copy()
            return M, gv

        self.ego.guncelle = ego_s

    def _gozle(self, gri):
        """`_arama_adimi`nin cagrilacagi noktada FAZLADAN bir adaylar() cagrisi."""
        if self._M is None or not self.tespit.hazir():
            return
        t0 = time.perf_counter()
        ad, d = self.tespit.adaylar(gri, self._M.astype(np.float32))
        sure = (time.perf_counter() - t0) * 1e3
        esik = None
        if d is not None:
            esik = float(max(self.tespit.min_esik,
                             float(d.mean() + self.tespit.esik_k * d.std())))
        self._d = {"n_aday": len(ad), "sure_ms": sure, "esik": esik,
                   "adaylar": [{"kutu": [float(v) for v in a["kutu"]],
                                "merkez": [float(v) for v in a["merkez"]],
                                "alan": a["alan"], "guc": a["guc"]} for a in ad]}

    def _takip_adimi(self, bgr, gri):
        r = super()._takip_adimi(bgr, gri)
        self._gozle(gri)
        return r

    def _boyut_tazele(self, bgr):
        izl.rafine_kutu.son = "yok"
        super()._boyut_tazele(bgr)
        s = izl.rafine_kutu.son
        self._d["rafine"] = None if s in (None, "yok") else s

    def guncelle(self, bgr):
        self._d = {}
        s = super().guncelle(bgr)
        d = dict(self._d)
        d["durum"] = self.durum
        d["merkez"] = self.kf.konum.astype(np.float64)
        d["boyut"] = self.boyut.astype(np.float64).copy()
        self.iz.append(d)
        return s


def _sar():
    gercek = izl.rafine_kutu

    def s(bgr, merkez, boyut, *a, **k):
        r = gercek(bgr, merkez, boyut, *a, **k)
        s.son = None if r is None else [float(v) for v in r]
        return r

    s.son = None
    izl.rafine_kutu = s
    return gercek


def sec(adaylar, merkez, gt):
    """UC secim kurali. S1/S2 YALNIZCA merkezi kullanir (boyut kullanmaz).
    S3 GT kullanir -> kosumda kullanilamaz, yalnizca UST SINIR."""
    if not adaylar:
        return {}
    cx, cy = float(merkez[0]), float(merkez[1])
    out = {}
    ic = [a for a in adaylar
          if a["kutu"][0] <= cx <= a["kutu"][0] + a["kutu"][2]
          and a["kutu"][1] <= cy <= a["kutu"][1] + a["kutu"][3]]
    if ic:
        out["S1"] = max(ic, key=lambda a: a["alan"])
    out["S2"] = min(adaylar, key=lambda a: (a["merkez"][0] - cx) ** 2
                    + (a["merkez"][1] - cy) ** 2)
    if gt is not None:
        en = max(adaylar, key=lambda a: _iou(a["kutu"], gt))
        if _iou(en["kutu"], gt) > 0:
            out["S3_oracle"] = en
    return out


def kos(ad, tur, arg):
    gercek = _sar()
    ilk = ana.HedefTakip
    tut = {}
    ana.HedefTakip = lambda *a, **k: tut.setdefault("t", D1Takip(*a, **k))
    try:
        m = ana.kos(_kaynak(tur, arg), pencere=False)
    finally:
        ana.HedefTakip = ilk
        izl.rafine_kutu = gercek
    tak = tut["t"]
    ofset = int(m["kare"]) - len(tak.iz)
    gt = {}
    for kare in _kaynak(tur, arg):
        if kare.gt is not None and kare.gorunur:
            gt[kare.indeks] = [float(v) for v in kare.gt]
    olc = {r["kare"]: r for r in m.get("_olcum") or []}
    td = m.get("t_drift")

    satir = []
    for i, r in enumerate(tak.iz):
        k = ofset + i
        if r["durum"] != KILITLI or k not in gt or "adaylar" not in r:
            continue
        g = gt[k]
        gc = (g[0] + g[2] / 2, g[1] + g[3] / 2)
        d = {"kare": k, "drift_oncesi": td is None or k < td,
             "n_aday": r["n_aday"], "esik": r["esik"], "sure_ms": r["sure_ms"],
             "gt_w": g[2], "gt_h": g[3],
             "boyut_w": float(r["boyut"][0]), "boyut_h": float(r["boyut"][1]),
             "merkez_hata": float(np.hypot(r["merkez"][0] - gc[0],
                                           r["merkez"][1] - gc[1])),
             "iou_takip": olc.get(k, {}).get("iou")}
        if r.get("rafine"):
            rf = r["rafine"]
            d["rafine_w"], d["rafine_h"] = rf[2], rf[3]
            d["rafine_ow"], d["rafine_oh"] = rf[2] / g[2], rf[3] / g[3]
        for nm, a in sec(r["adaylar"], r["merkez"], g).items():
            kb = a["kutu"]
            d[nm] = {"w": kb[2], "h": kb[3], "ow": kb[2] / g[2],
                     "oh": kb[3] / g[3], "alan": a["alan"],
                     "iou_gt": _iou(kb, g),
                     "merkez_hata": float(np.hypot(a["merkez"][0] - gc[0],
                                                   a["merkez"][1] - gc[1]))}
        satir.append(d)
    return {"ad": ad, "ort_iou": float(m.get("ort_iou", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "t_drift": td, "satir": satir}


def dagilim(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if len(v) < 3:
        return None
    return {"n": int(len(v)), "med": float(np.median(v)),
            "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95)),
            "yayilim": float(np.percentile(v, 95) - np.percentile(v, 5))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/d1_adaylar.json")
    a = ap.parse_args()
    out = {}
    for ad, tur, arg in KAYNAKLAR:
        r = kos(ad, tur, arg)
        out[ad] = r
        td = r["t_drift"]
        print(f"\n== {ad} == IoU {r['ort_iou']:.6f} kilit {100*r['kilit_orani']:.2f}% "
              f"drift {td}  KILITLI+GT kare {len(r['satir'])}  "
              f"adaylar ort {np.mean([x['n_aday'] for x in r['satir']]):.1f}  "
              f"sure ort {np.mean([x['sure_ms'] for x in r['satir']]):.2f} ms")
        for faz, sec_f in (("drift ONCESI", lambda x: x["drift_oncesi"]),
                           ("drift SONRASI", lambda x: not x["drift_oncesi"])):
            s = [x for x in r["satir"] if sec_f(x)]
            if len(s) < 3:
                continue
            print(f"  -- {faz} ({len(s)} kare)")
            for nm in ("S1", "S2", "S3_oracle", "rafine"):
                if nm == "rafine":
                    ow = dagilim([x.get("rafine_ow") for x in s])
                    oh = dagilim([x.get("rafine_oh") for x in s])
                    ek = ""
                else:
                    ow = dagilim([x[nm]["ow"] for x in s if nm in x])
                    oh = dagilim([x[nm]["oh"] for x in s if nm in x])
                    io = dagilim([x[nm]["iou_gt"] for x in s if nm in x])
                    ek = f"  IoU_GT med {io['med']:.2f}" if io else ""
                if not ow or not oh:
                    print(f"     {nm:10s} (yetersiz)")
                    continue
                print(f"     {nm:10s} n={ow['n']:3d}  w/GT med {ow['med']:5.2f} "
                      f"[{ow['p5']:5.2f}..{ow['p95']:5.2f}] yay {ow['yayilim']:5.2f} | "
                      f"h/GT med {oh['med']:5.2f} [{oh['p5']:5.2f}..{oh['p95']:5.2f}] "
                      f"yay {oh['yayilim']:5.2f}{ek}")
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"\nyazildi: {a.json}")


if __name__ == "__main__":
    main()
