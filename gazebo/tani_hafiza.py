"""Deney 4G - salt okunur: DCF biasi ile template ogrenme hafizasi iliskisi.

TAKIPCIYE DOKUNMAZ. Alt sinif + wrapper; hicbir esik/karar/parametre degismez.

GERCEK ISIMLER (grep ile dogrulandi, tahmin yok)
------------------------------------------------
  ogrenme orani   `cekirdekler.py:103` self.lr (varsayilan 0.09) AMA cagri
                  aninda ezilir: `izleyici.py:315`
                      lr = 0.125 if self.boyut.max() > 18 else 0.04
                  ve `izleyici.py:316` cekirdek.ogren(..., lr) ile gecirilir.
  template guncel `cekirdekler.py:214-215` ogren() icinde:
                      self.A = (1-lr)*self.A + lr*(G*conj(F))
                      self.B = (1-lr)*self.B + lr*(F*conj(F)).sum(0)
                  yani sablon durumu (A, B) ciftidir.
  peak            `cekirdekler.py:175` _yanit -> _tepe(r, self.N, merkez, w, h)
                  `ara` bunu dondurur; izleyici `_takip_adimi`'nda `yeni`.
  arka plan akisi ego matrisi M (`izleyici.py:249` cekirdek.ego_guncelle(M));
                  hedefteki bagil akis = M(c) - c. Ayni ifade `izleyici.py:255`
                  `ongoru` olarak zaten hesaplaniyor (zemine cakilma testi icin).
  ego/hedef ayrim `gazebo/tani.py:354` d_artik - ama POZ gerektirir, yalnizca
                  Gazebo'da var. VisDrone'da boru hattindaki karsiligi
                  `ongoru` artigidir (kestirilen M ile).

OLCULEN OGRENME SINYALLERI (sabit formul VARSAYILMADI, koddan turetildi)
    kisa_degisim  ||A_t - A_{t-1}||_F / ||A_t||_F      (bir adimlik guncelleme)
    kum_degisim   ||A_t - A_0||_F   / ||A_0||_F        (kilitten bu yana)
    lr            o karede gecirilen deger

Kullanim:  python3 -m gazebo.tani_hafiza
"""
import argparse
import json
import os

import numpy as np

import main as ana
from kaynak import kaynak_olustur
from takip.izleyici import HedefTakip
from veri.gazebo import GazeboKaynak

GAZEBO = ["G3_agresif", "G3_kritik", "G0"]
VISDRONE = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31)]
VISDRONE_KOK = "data/datasets/visdrone_vid"


class HafizaTakip(HedefTakip):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []
        c = self.cekirdek
        g_ara, g_ogr, g_ego = c.ara, c.ogren, c.ego_guncelle
        self._d = {}

        def ara_s(bgr, gri, merkez, boyut):
            yeni, psr = g_ara(bgr, gri, merkez, boyut)
            self._d["dcf"] = np.asarray(yeni, np.float64).copy()
            self._d["psr"] = float(psr)
            self._d["ongoru"] = np.asarray(merkez, np.float64).copy()
            return yeni, psr

        def ogr_s(bgr, gri, merkez, boyut, lr=None):
            A0 = None if c.A is None else c.A.copy()
            g_ogr(bgr, gri, merkez, boyut, lr)
            self._d["lr"] = float(c.lr if lr is None else lr)
            if A0 is not None and c.A is not None:
                nA = np.linalg.norm(c.A)
                self._d["kisa_degisim"] = float(np.linalg.norm(c.A - A0) / max(1e-12, nA))
            if self._A_kilit is not None:
                n0 = np.linalg.norm(self._A_kilit)
                self._d["kum_degisim"] = float(
                    np.linalg.norm(c.A - self._A_kilit) / max(1e-12, n0))

        def ego_s(M):
            self._d["M"] = np.asarray(M, np.float64).copy()
            return g_ego(M)

        c.ara, c.ogren, c.ego_guncelle = ara_s, ogr_s, ego_s
        self._A_kilit = None

    def kilitle(self, bgr, kutu):
        r = super().kilitle(bgr, kutu)
        self._A_kilit = None if self.cekirdek.A is None else self.cekirdek.A.copy()
        return r

    def guncelle(self, bgr):
        self._d = {}
        s = super().guncelle(bgr)
        d = self._d
        c = self.kf.konum.astype(np.float64)
        M = d.get("M")
        akis = None
        if M is not None:
            # hedefteki BAGIL arka plan akisi: zemin bu kareye nereye tasindi
            akis = (M[:, :2] @ c + M[:, 2]) - c
        self.iz.append({
            "durum": self.durum, "final": c,
            "dcf": d.get("dcf"), "psr": d.get("psr"), "ongoru": d.get("ongoru"),
            "lr": d.get("lr"), "kisa": d.get("kisa_degisim"),
            "kum": d.get("kum_degisim"), "akis": akis, "M": M,
            "aci": float(getattr(self.cekirdek, "aci", 0.0)),
            "boyut": self.boyut.astype(np.float64).copy(),
        })
        return s


def _gt(fn):
    g = {}
    for kare in fn():
        if kare.gt is not None:
            b = kare.gt
            g[kare.indeks] = np.array([b[0] + b[2] / 2, b[1] + b[3] / 2])
    return g


def kos(fn, ad):
    ilk = ana.HedefTakip
    kutu = {}
    ana.HedefTakip = lambda *a, **k: kutu.setdefault("t", HafizaTakip(*a, **k))
    try:
        m = ana.kos(fn(), pencere=False)
    finally:
        ana.HedefTakip = ilk
    tak = kutu["t"]
    gts = _gt(fn)
    ofset = int(m["kare"]) - len(tak.iz)
    satir = []
    for i, r in enumerate(tak.iz):
        k = ofset + i
        if k not in gts or r["dcf"] is None:
            continue
        gt = gts[k]
        e = r["dcf"] - gt
        d = {"kare": k, "kilitten": i, "durum": r["durum"],
             "gt": [float(v) for v in gt], "dcf": [float(v) for v in r["dcf"]],
             "dx": float(e[0]), "dy": float(e[1]),
             "hata": float(np.linalg.norm(e)),
             "final_hata": float(np.linalg.norm(r["final"] - gt)),
             "psr": r["psr"], "lr": r["lr"], "kisa": r["kisa"], "kum": r["kum"],
             "aci": r["aci"], "w": float(r["boyut"][0]), "h": float(r["boyut"][1])}
        if r["akis"] is not None:
            d["akis_x"], d["akis_y"] = float(r["akis"][0]), float(r["akis"][1])
            d["akis_buyuk"] = float(np.linalg.norm(r["akis"]))
        if r["ongoru"] is not None:
            d["ongoru"] = [float(v) for v in r["ongoru"]]
        # BAGIL arka plan akisi: zeminin hedefe GORE kaymasi.
        # = M(gt_onceki) - gt_simdi. Gazebo'da hedef goruntude sabit oldugu icin
        # mutlak akisa esittir; VisDrone'da hedef goruntude hareket ettigi icin
        # ikisi FARKLIDIR ve dogru olcut budur.
        kp = k - 1
        if r["M"] is not None and kp in gts:
            tas = r["M"][:, :2] @ gts[kp] + r["M"][:, 2]
            bg = tas - gt
            d["bagil_x"], d["bagil_y"] = float(bg[0]), float(bg[1])
        satir.append(d)
    return {"ad": ad, "ort_iou": float(m.get("ort_iou", 0.0)),
            "t_drift": m.get("t_drift"), "satir": satir}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/hafiza.json")
    a = ap.parse_args()
    out = {}
    for ad in GAZEBO:
        out[ad] = kos(lambda ad=ad: GazeboKaynak(kok="data/gazebo", senaryo=ad), ad)
        print(f"  {ad}: {len(out[ad]['satir'])} kare", flush=True)
    for dz, t in VISDRONE:
        et = f"{dz.split('_')[0][3:]}/{t}"
        out[et] = kos(lambda dz=dz, t=t: kaynak_olustur(
            "visdrone", veri_kok=VISDRONE_KOK, dizi=dz, track_id=t,
            hedef_genislik=960), et)
        print(f"  {et}: {len(out[et]['satir'])} kare", flush=True)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"yazildi: {a.json}")


if __name__ == "__main__":
    main()
