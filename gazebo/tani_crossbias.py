"""Deney 4J - salt okunur: DCF merkez biasinin iki bagimsiz GERCEK dizide sinanmasi.

TAKIP/ HIC DEGISMEZ. Alt sinif + gecici monkeypatch; hicbir esik, parametre ya
da karar degistirilmez.

GERCEK PIPELINE NOKTALARI (grep ile dogrulandi)
    DCF peak        cekirdekler.py:175  `_yanit` -> `_tepe(r, self.N, merkez, w, h)`
                    (`_tepe` tanimi satir 321); `ara` bunu dondurur,
                    izleyici `_takip_adimi`'nda `yeni` adiyla kullanilir
    sablon durumu   cekirdekler.py:168-169 baslat  -> self.A, self.B
                    cekirdekler.py:215     ogren   -> A = (1-lr)A + lr(G conj F)
    lr uygulama     izleyici.py:315 lr = 0.125 if boyut.max() > 18 else 0.04
                    izleyici.py:316 cekirdek.ogren(..., lr)   <- cagri EZER
    GT kaynagi      veri/visdrone.py:160  Kare(gt=gt, gorunur=e is not None)
    ego / M         izleyici.py:249 cekirdek.ego_guncelle(M)
    hedef/arka plan izleyici.py:255 ongoru = M[:, :2] @ onceki_merkez + M[:, 2]
                    (ayni ifade burada GT ile kurulur: M(gt_onceki) - gt_simdi)
    rafine merkezi  izleyici.py:565 yeni_c = r[:2] + r[2:] / 2

Kullanim: python3 -m gazebo.tani_crossbias
"""
import argparse
import json
import os

import numpy as np

import main as ana
import takip.izleyici as izl
from kaynak import kaynak_olustur
from takip.izleyici import HedefTakip
from veri.gazebo import GazeboKaynak

VISDRONE_KOK = "data/datasets/visdrone_vid"
# 4I envanteri: birincil iki dizi + destekleyici bir dizi + Gazebo referansi
HEDEFLER = [("117/23", "visdrone", ("uav0000117_02622_v", 23)),
            ("137/12", "visdrone", ("uav0000137_00458_v", 12)),
            ("305/5", "visdrone", ("uav0000305_00000_v", 5)),
            ("G3_agresif", "gazebo", "G3_agresif"),
            ("G3_kritik", "gazebo", "G3_kritik")]


class BiasTakip(HedefTakip):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []
        self._A0 = None
        self._d = {}
        c = self.cekirdek
        g_ara, g_ogr, g_ego = c.ara, c.ogren, c.ego_guncelle

        def ara_s(bgr, gri, merkez, boyut):
            self._d["ongoru"] = np.asarray(merkez, np.float64).copy()
            yeni, psr = g_ara(bgr, gri, merkez, boyut)
            self._d["dcf"] = np.asarray(yeni, np.float64).copy()
            self._d["psr"] = float(psr)
            return yeni, psr

        def ogr_s(bgr, gri, merkez, boyut, lr=None):
            A0 = None if c.A is None else c.A.copy()
            g_ogr(bgr, gri, merkez, boyut, lr)
            self._d["lr"] = float(c.lr if lr is None else lr)
            if A0 is not None:
                self._d["kisa"] = float(np.linalg.norm(c.A - A0)
                                        / max(1e-12, np.linalg.norm(c.A)))
            if self._A0 is not None:
                self._d["kum"] = float(np.linalg.norm(c.A - self._A0)
                                       / max(1e-12, np.linalg.norm(self._A0)))

        def ego_s(M):
            self._d["M"] = np.asarray(M, np.float64).copy()
            return g_ego(M)

        c.ara, c.ogren, c.ego_guncelle = ara_s, ogr_s, ego_s

    def kilitle(self, bgr, kutu):
        r = super().kilitle(bgr, kutu)
        self._A0 = None if self.cekirdek.A is None else self.cekirdek.A.copy()
        return r

    def _boyut_tazele(self, bgr):
        izl.rafine_kutu.kayit = []
        super()._boyut_tazele(bgr)
        k = [x for x in izl.rafine_kutu.kayit if x["kutu"] is not None]
        if k:
            rr = np.asarray(k[-1]["kutu"], np.float64)
            self._d["rafine"] = rr[:2] + rr[2:] / 2

    def guncelle(self, bgr):
        self._d = {}
        s = super().guncelle(bgr)
        d = dict(self._d)
        d["durum"] = self.durum
        d["final"] = self.kf.konum.astype(np.float64)
        d["boyut"] = self.boyut.astype(np.float64).copy()
        d["aci"] = float(getattr(self.cekirdek, "aci", 0.0))
        self.iz.append(d)
        return s


def _sar():
    gercek = izl.rafine_kutu

    def s(bgr, merkez, boyut, *a, **k):
        r = gercek(bgr, merkez, boyut, *a, **k)
        s.kayit.append({"kutu": None if r is None else [float(v) for v in r]})
        return r

    s.kayit = []
    izl.rafine_kutu = s
    return gercek


def _kaynak(tur, arg):
    if tur == "gazebo":
        return GazeboKaynak(kok="data/gazebo", senaryo=arg)
    dz, tid = arg
    return kaynak_olustur("visdrone", veri_kok=VISDRONE_KOK, dizi=dz,
                          track_id=tid, hedef_genislik=960)


def _gt(tur, arg):
    g, wh = {}, {}
    for kare in _kaynak(tur, arg):
        if kare.gt is not None and kare.gorunur:
            b = kare.gt
            g[kare.indeks] = np.array([b[0] + b[2] / 2, b[1] + b[3] / 2])
            wh[kare.indeks] = np.array([float(b[2]), float(b[3])])
    return g, wh


def kos(ad, tur, arg):
    gts, gtb = _gt(tur, arg)
    gercek = _sar()
    ilk = ana.HedefTakip
    kutu = {}
    ana.HedefTakip = lambda *a, **k: kutu.setdefault("t", BiasTakip(*a, **k))
    try:
        m = ana.kos(_kaynak(tur, arg), pencere=False)
    finally:
        ana.HedefTakip = ilk
        izl.rafine_kutu = gercek
    tak = kutu["t"]
    ofset = int(m["kare"]) - len(tak.iz)
    satir = []
    for i, r in enumerate(tak.iz):
        k = ofset + i
        if k not in gts or r.get("dcf") is None:
            continue
        gt = gts[k]
        e = r["dcf"] - gt
        d = {"kare": k, "kilitten": i, "durum": r["durum"],
             "gt_x": float(gt[0]), "gt_y": float(gt[1]),
             "dcf_x": float(r["dcf"][0]), "dcf_y": float(r["dcf"][1]),
             "dx": float(e[0]), "dy": float(e[1]),
             "hata": float(np.linalg.norm(e)),
             "final_hata": float(np.linalg.norm(r["final"] - gt)),
             "psr": r.get("psr"), "lr": r.get("lr"),
             "kisa": r.get("kisa"), "kum": r.get("kum"),
             "aci": r["aci"],
             "gt_w": float(gtb[k][0]), "gt_h": float(gtb[k][1]),
             "w": float(r["boyut"][0]), "h": float(r["boyut"][1])}
        if r.get("ongoru") is not None:
            d["ongoru_x"], d["ongoru_y"] = float(r["ongoru"][0]), float(r["ongoru"][1])
        if r.get("rafine") is not None:
            d["rafine_hata"] = float(np.linalg.norm(r["rafine"] - gt))
        kp = k - 1
        if kp in gts:
            # 11) hedefin KENDI goruntu hareketi
            hh = gt - gts[kp]
            d["hedef_x"], d["hedef_y"] = float(hh[0]), float(hh[1])
            if r.get("M") is not None:
                M = r["M"]
                # 13) ego: M'nin hedefteki otelemesi
                eg = (M[:, :2] @ gts[kp] + M[:, 2]) - gts[kp]
                d["ego_x"], d["ego_y"] = float(eg[0]), float(eg[1])
                # 12) BAGIL arka plan akisi = M(gt_onceki) - gt_simdi
                bg = (M[:, :2] @ gts[kp] + M[:, 2]) - gt
                d["bagil_x"], d["bagil_y"] = float(bg[0]), float(bg[1])
        satir.append(d)
    return {"ad": ad, "ort_iou": float(m.get("ort_iou", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "t_drift": m.get("t_drift"), "satir": satir}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/crossbias.json")
    a = ap.parse_args()
    out = {}
    for ad, tur, arg in HEDEFLER:
        out[ad] = kos(ad, tur, arg)
        r = out[ad]
        print(f"  {ad:12s} {len(r['satir']):4d} kare  IoU {r['ort_iou']:.3f}  "
              f"merkez {r['merkez_hata']:.2f}  kilit {100*r['kilit_orani']:.1f}%  "
              f"drift {r['t_drift']}", flush=True)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"yazildi: {a.json}")


if __name__ == "__main__":
    main()
