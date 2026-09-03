"""Deney 4E - salt okunur: DCF yamasindaki `dolgu` (padding) supurmesi.

TAKIPCIYE DOKUNMAZ. `takip/` altindaki hicbir dosya degismedi.

NASIL KOD DEGISTIRMEDEN YAPILIYOR
---------------------------------
`izleyici.py:128`:
    self.cekirdek = CEKIRDEKLER[cekirdek]() if isinstance(cekirdek, str) else cekirdek
yani `HedefTakip` hazir bir cekirdek ORNEGI kabul ediyor. `dolgu` da
`RenkDcfCekirdek.__init__`'in parametresi (satir 99) ve yalnizca `_kanallar`
satir 145-146'da kullaniliyor:
    w = max(4, round(boyut[0] * self.dolgu));  h = max(4, round(boyut[1] * self.dolgu))
Yama `boyut x dolgu` olarak kesilip 32x32'ye yeniden olcekleniyor.

Bu yuzden farkli dolgu degerleri, tek satir kod degistirmeden
`RenkDcfCekirdek(dolgu=p)` ornegi gecirilerek KAPALI CEVRIM kosulabilir -
yani IoU / drift / kilit / yanlis kilit gibi davranis metrikleri de olculebilir,
yalnizca acik cevrim tepe sapmasi degil.

Kullanim:
    python3 -m gazebo.tani_dolgu
"""
import argparse
import json
import os

import numpy as np

import main as ana
from kaynak import kaynak_olustur
from takip.cekirdekler import RenkDcfCekirdek
from takip.izleyici import HedefTakip
from veri.gazebo import GazeboKaynak

DOLGULAR = [1.3, 1.5, 1.7, 2.0, 2.5]
GAZEBO = ["G3_agresif", "G3_kritik"]
GAZEBO_GENIS = ["G0", "G3_yumusak", "G4_kritik", "G5_agresif", "G6_agresif",
                "G7_agresif", "G1_agresif", "G2_agresif"]
VISDRONE = [("uav0000117_02622_v", 23), ("uav0000182_00000_v", 127),
            ("uav0000268_05773_v", 31)]
VISDRONE_KOK = "data/datasets/visdrone_vid"


class TepeTakip(HedefTakip):
    """DCF tepesini ve PSR'yi kare kare yazar. Davranis birebir korunur."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []
        gercek = self.cekirdek.ara

        def ara_sarma(bgr, gri, merkez, boyut):
            yeni, psr = gercek(bgr, gri, merkez, boyut)
            self._son = (np.asarray(yeni, np.float64).copy(), float(psr),
                         np.asarray(boyut, np.float64).copy())
            return yeni, psr

        self.cekirdek.ara = ara_sarma
        self._son = None

    def guncelle(self, bgr):
        self._son = None
        s = super().guncelle(bgr)
        d = {"kare_ic": self.kare, "durum": self.durum,
             "final": self.kf.konum.astype(np.float64),
             "yanlis_kilit": int(self.yanlis_kilit)}
        if self._son is not None:
            d["dcf"], d["psr"], d["boyut"] = self._son
        self.iz.append(d)
        return s


def _gt(kaynak_fn):
    g = {}
    for kare in kaynak_fn():
        if kare.gt is not None:
            b = kare.gt
            g[kare.indeks] = np.array([b[0] + b[2] / 2, b[1] + b[3] / 2])
    return g


def tepe_olc(kaynak_fn, dolgu):
    ilk = ana.HedefTakip
    kutu = {}
    cek = RenkDcfCekirdek(dolgu=dolgu)
    ana.HedefTakip = lambda *a, **k: kutu.setdefault("t", TepeTakip(cekirdek=cek))
    try:
        m = ana.kos(kaynak_fn(), pencere=False)
    finally:
        ana.HedefTakip = ilk
    tak = kutu["t"]
    gts = _gt(kaynak_fn)
    ofset = int(m["kare"]) - len(tak.iz)
    e, ps, rt = [], [], []
    for i, r in enumerate(tak.iz):
        k = ofset + i
        if k not in gts or "dcf" not in r:
            continue
        e.append(r["dcf"] - gts[k])
        ps.append(r["psr"])
        b = r["boyut"]
        rt.append(min(max(6.0, 0.9 * float(b.max())), 0.5 * dolgu * float(b.min())))
    e = np.array(e) if e else np.zeros((0, 2))
    n = np.linalg.norm(e, axis=1) if len(e) else np.zeros(1)
    return {
        "iou": float(m.get("ort_iou", 0.0)),
        "basari@0.5": float(m.get("basari@0.5", 0.0)),
        "merkez_p50": float(np.percentile(
            [r["merkez_hata"] for r in m.get("_olcum", [])] or [0], 50)),
        "merkez_p95": float(np.percentile(
            [r["merkez_hata"] for r in m.get("_olcum", [])] or [0], 95)),
        "merkez_ort": float(np.mean(
            [r["merkez_hata"] for r in m.get("_olcum", [])] or [0])),
        "kilit_orani": float(m.get("kilit_orani", 0.0)),
        "kesinti": int(m.get("kesinti", 0)),
        "kurtarma_max": int(m.get("kurtarma_max", 0)),
        "t_drift": m.get("t_drift"),
        "fps": float(m.get("fps", 0.0)),
        "gecikme_p95": float(m.get("gecikme_p95", 0.0)),
        "dcf_p50": float(np.percentile(n, 50)), "dcf_p95": float(np.percentile(n, 95)),
        "dcf_ort": float(n.mean()),
        "dcf_dx": float(e[:, 0].mean()) if len(e) else 0.0,
        "dcf_dy": float(e[:, 1].mean()) if len(e) else 0.0,
        "psr_p50": float(np.percentile(ps, 50)) if ps else 0.0,
        "r_etkin": float(np.median(rt)) if rt else 0.0,
        "yanlis_kilit": int(tak.iz[-1]["yanlis_kilit"]) if tak.iz else 0,
        "n": len(e),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/dolgu.json")
    ap.add_argument("--genis", action="store_true")
    a = ap.parse_args()
    out = {}
    hedefler = [(ad, (lambda ad=ad: GazeboKaynak(kok="data/gazebo", senaryo=ad)), True)
                for ad in GAZEBO + (GAZEBO_GENIS if a.genis else [])]
    hedefler += [(f"{d.split('_')[0][3:]}/{t}",
                  (lambda d=d, t=t: kaynak_olustur("visdrone", veri_kok=VISDRONE_KOK,
                                                   dizi=d, track_id=t,
                                                   hedef_genislik=960)), False)
                 for d, t in VISDRONE]
    for ad, fn, gz in hedefler:
        out[ad] = {}
        for p in DOLGULAR:
            r = tepe_olc(fn, p)
            if gz:
                from gazebo.tani import olc
                t = olc(ad, kok="data/gazebo", cekirdek=RenkDcfCekirdek(dolgu=p))
                r["d_artik_r_p95"] = t["d_artik_r_p95"]
                r["d_r_p95"] = t["d_r_p95"]
                r["sicrama_p95"] = t["sicrama_p95"]
                r["yanlis_kilit_orani"] = t["yanlis_kilit_orani"]
                r["tavan_iou"] = t["tavan_iou"]
            out[ad][str(p)] = r
            print(f"  {ad:14s} dolgu {p}: IoU {r['iou']:.3f} merkez {r['merkez_ort']:5.2f} "
                  f"dcf_dx {r['dcf_dx']:+6.2f} PSR {r['psr_p50']:5.1f} "
                  f"drift {r['t_drift']}", flush=True)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"yazildi: {a.json}")


if __name__ == "__main__":
    main()
