"""Deney 4H - template ogrenme hafizasi NEDENSELLIK testi (lr kontrollu).

TAKIP/ HIC DEGISMEZ. `lr` `izleyici.py:315`'te uretilip `ogren`e geciriliyor:
    lr = 0.125 if self.boyut.max() > 18 else 0.04
Bu degeri degistirmek icin izleyici'yi duzenlemek YERINE, gecirilen lr'yi
carpan bir TESHIS ALT SINIFI kullanilir ve `izleyici.py:128` uzerinden ornek
olarak gecirilir:
    self.cekirdek = CEKIRDEKLER[cekirdek]() if isinstance(cekirdek, str) else cekirdek
Boylece takip/ altindaki md5'ler kosum boyunca hic bozulmaz; geri alinacak bir
sey de kalmaz.

carpan = 1.0 kosumu Deney 2 ile BIREBIR olmalidir (lr * 1.0 kayan noktada tam).
Bu, deneyin kendi kontrolu olarak her kosumda dogrulanir.
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

CARPANLAR = [0.5, 1.0, 2.0]
GAZEBO = ["G3_agresif", "G3_kritik", "G0"]
VISDRONE = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31)]
VISDRONE_KOK = "data/datasets/visdrone_vid"


class LrCekirdek(RenkDcfCekirdek):
    """Gecirilen ogrenme oranini `carpan` ile olcekler. Baska hicbir fark yok."""

    def __init__(self, carpan=1.0, **k):
        super().__init__(**k)
        self.carpan = float(carpan)

    def ogren(self, bgr, gri, merkez, boyut, lr=None):
        etkin = (self.lr if lr is None else lr) * self.carpan
        super().ogren(bgr, gri, merkez, boyut, etkin)


class LrTakip(HedefTakip):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []
        c = self.cekirdek
        g_ara, g_ogr, g_ego = c.ara, c.ogren, c.ego_guncelle
        self._d = {}
        self._A0 = None

        def ara_s(bgr, gri, merkez, boyut):
            self._d["ongoru"] = np.asarray(merkez, np.float64).copy()
            yeni, psr = g_ara(bgr, gri, merkez, boyut)
            self._d["dcf"] = np.asarray(yeni, np.float64).copy()
            self._d["psr"] = float(psr)
            return yeni, psr

        def ogr_s(bgr, gri, merkez, boyut, lr=None):
            A0 = None if c.A is None else c.A.copy()
            g_ogr(bgr, gri, merkez, boyut, lr)
            self._d["lr_etkin"] = float((c.lr if lr is None else lr) * c.carpan)
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

    def _takip_adimi(self, bgr, gri):
        super()._takip_adimi(bgr, gri)
        self._d["duzeltme"] = self.kf.konum.astype(np.float64)

    def guncelle(self, bgr):
        self._d = {}
        s = super().guncelle(bgr)
        d = self._d
        self.iz.append({
            "durum": self.durum, "final": self.kf.konum.astype(np.float64),
            "dcf": d.get("dcf"), "psr": d.get("psr"), "ongoru": d.get("ongoru"),
            "duzeltme": d.get("duzeltme"), "lr": d.get("lr_etkin"),
            "kisa": d.get("kisa"), "kum": d.get("kum"), "M": d.get("M"),
            "aci": float(getattr(self.cekirdek, "aci", 0.0)),
            "boyut": self.boyut.astype(np.float64).copy()})
        return s


def _gt(fn):
    g = {}
    for kare in fn():
        if kare.gt is not None:
            b = kare.gt
            g[kare.indeks] = np.array([b[0] + b[2] / 2, b[1] + b[3] / 2])
    return g


def kos(fn, gts, carpan):
    ilk = ana.HedefTakip
    kutu = {}
    cek = LrCekirdek(carpan=carpan)
    ana.HedefTakip = lambda *a, **k: kutu.setdefault("t", LrTakip(cekirdek=cek))
    try:
        m = ana.kos(fn(), pencere=False)
    finally:
        ana.HedefTakip = ilk
    tak = kutu["t"]
    ofset = int(m["kare"]) - len(tak.iz)
    satir = []
    for i, r in enumerate(tak.iz):
        k = ofset + i
        if k not in gts or r["dcf"] is None:
            continue
        gt = gts[k]
        e = r["dcf"] - gt
        d = {"kare": k, "kilitten": i, "durum": r["durum"],
             "lr": r["lr"], "kisa": r["kisa"], "kum": r["kum"],
             "dx": float(e[0]), "dy": float(e[1]),
             "hata": float(np.linalg.norm(e)),
             "final_hata": float(np.linalg.norm(r["final"] - gt)),
             "gt": [float(v) for v in gt], "dcf": [float(v) for v in r["dcf"]],
             "psr": r["psr"], "aci": r["aci"],
             "w": float(r["boyut"][0]), "h": float(r["boyut"][1])}
        for ad in ("ongoru", "duzeltme"):
            if r[ad] is not None:
                d[ad] = [float(v) for v in r[ad]]
        satir.append(d)
    return {"iou": float(m.get("ort_iou", 0.0)),
            "basari@0.5": float(m.get("basari@0.5", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "kesinti": int(m.get("kesinti", 0)),
            "kurtarma_max": int(m.get("kurtarma_max", 0)),
            "id_switch": int(m.get("id_switch", 0)) if "id_switch" in m else None,
            "t_drift": m.get("t_drift"), "satir": satir}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/lr.json")
    a = ap.parse_args()
    hedefler = [(ad, (lambda ad=ad: GazeboKaynak(kok="data/gazebo", senaryo=ad)))
                for ad in GAZEBO]
    hedefler += [(f"{d.split('_')[0][3:]}/{t}",
                  (lambda d=d, t=t: kaynak_olustur("visdrone", veri_kok=VISDRONE_KOK,
                                                   dizi=d, track_id=t,
                                                   hedef_genislik=960)))
                 for d, t in VISDRONE]
    out = {}
    for ad, fn in hedefler:
        gts = _gt(fn)                     # GT bir kez, tum carpanlarda ayni
        out[ad] = {}
        for c in CARPANLAR:
            r = kos(fn, gts, c)
            out[ad][str(c)] = r
            lr = [x["lr"] for x in r["satir"] if x["lr"] is not None]
            print("  %-14s carpan %.1f  lr %.4f  IoU %.3f  merkez %6.2f  "
                  "dx %+7.2f  drift %s" % (
                      ad, c, np.median(lr) if lr else float("nan"), r["iou"],
                      r["merkez_hata"],
                      float(np.mean([x["dx"] for x in r["satir"]])), r["t_drift"]),
                  flush=True)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"yazildi: {a.json}")


if __name__ == "__main__":
    main()
