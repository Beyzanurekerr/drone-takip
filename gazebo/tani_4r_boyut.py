"""Deney 4R - salt okunur: `boyut` hatasini UC yazma noktasina ayristir.

TAKIP/ HIC DEGISMEZ. Yalnizca gozlem: `boyut`u YAZAN her asamanin oncesi ve
sonrasi kaydedilir. Hicbir esik/lr/Kalman/DCF/sablon degismez, hicbir deger
geri yazilmaz.

`self.boyut`u yazan TUM noktalar (izleyici.py, grep ile dogrulandi):
  satir 198  kilitle()        ilk kutu
  satir 264  guncelle()       boyut = max(boyut * olc, min_kenar)   <- EGO OLCEGI
                              olc = clip(ego.olcek_katsayisi, 0.90, 1.10)
  satir 522  _arama_adimi()   boyut = max(0.5*boyut + 0.5*r2, min_kenar)  (ARAMA/KAYIP)
  satir 563  _boyut_tazele()  boyut = max(0.75*boyut + 0.25*rafine, min_kenar)
  satir 549  _boyut_sinirla() boyut = clip(boyut, 0.60*b, 1.70*b),
                              b = max(boyut_olculen, min_kenar)
  satir 564  _boyut_tazele()  boyut_olculen = 0.85*boyut_olculen + 0.15*rafine
  satir 523  _arama_adimi()   boyut_olculen = boyut

Kare ici SIRA (guncelle):
  ego olcegi (264) -> [_takip_adimi] -> [_bagimsiz_dogrula, _boyut_tazele]
  ya da [_arama_adimi] -> kadraj kontrolu -> _boyut_sinirla (294)

Yakalama noktalari (hicbiri kodu degistirmez):
  guncelle() girisi         -> A0  (onceki karenin cikisi)
  _takip_adimi/_arama_adimi -> A1  (EGO OLCEGI sonrasi)
  _boyut_tazele oncesi/sonrasi -> A2 / A3
  _boyut_sinirla oncesi/sonrasi -> A4 / A5

Kullanim: python3 -m gazebo.tani_4r_boyut
"""
import argparse
import json
import os

import numpy as np

import main as ana
import takip.izleyici as izl
from gazebo.tani_4o_dcf import _kaynak
from takip.izleyici import HedefTakip

HEDEFLER = [("182/127", "visdrone", ("uav0000182_00000_v", 127)),
            ("305/5", "visdrone", ("uav0000305_00000_v", 5)),
            ("G6_agresif", "gazebo", "G6_agresif"),
            ("G6_agresif_durakli", "gazebo", "G6_agresif_durakli")]

ONCE, SONRA = 30, 10


def _kutu(merkez, boyut):
    return np.array([merkez[0] - boyut[0] / 2, merkez[1] - boyut[1] / 2,
                     boyut[0], boyut[1]], np.float32)


class BoyutTakip(HedefTakip):
    """Yalnizca gozlem. Her sarmalayici gercek cagriyi AYNEN yapar."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []
        self._d = {}
        g_ego = self.ego.guncelle

        def ego_s(gri, kutu=None):
            M, gv = g_ego(gri, kutu)
            self._d["olcek_katsayisi"] = float(self.ego.olcek_katsayisi)
            return M, gv

        self.ego.guncelle = ego_s

    def _takip_adimi(self, bgr, gri):
        self._d["A1"] = self.boyut.copy()          # EGO OLCEGI sonrasi
        self._d["dal"] = "takip"
        return super()._takip_adimi(bgr, gri)

    def _arama_adimi(self, bgr, gri, M):
        if "A1" not in self._d:
            self._d["A1"] = self.boyut.copy()
            self._d["dal"] = "arama"
        b0 = self.boyut.copy()
        r = super()._arama_adimi(bgr, gri, M)
        if not np.allclose(b0, self.boyut):
            self._d["arama_yazdi"] = self.boyut.copy()
        return r

    def _boyut_tazele(self, bgr):
        izl.rafine_kutu.son = None
        self._d["A2"] = self.boyut.copy()
        o0 = self.boyut_olculen.copy()
        super()._boyut_tazele(bgr)
        self._d["A3"] = self.boyut.copy()
        self._d["rafine"] = izl.rafine_kutu.son
        self._d["olculen_once"] = o0
        self._d["olculen_sonra"] = self.boyut_olculen.copy()

    def _boyut_sinirla(self):
        self._d["A4"] = self.boyut.copy()
        b = np.maximum(self.boyut_olculen, self.min_kenar)
        self._d["sinir_alt"] = 0.60 * b
        self._d["sinir_ust"] = 1.70 * b
        super()._boyut_sinirla()
        self._d["A5"] = self.boyut.copy()

    def guncelle(self, bgr):
        self._d = {"A0": self.boyut.copy()}
        s = super().guncelle(bgr)
        d = dict(self._d)
        d["son"] = self.boyut.copy()
        d["merkez"] = self.kf.konum.copy()
        d["durum"] = self.durum
        d["olculen"] = self.boyut_olculen.copy()
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


def analiz(ad, tur, arg):
    gercek = _sar()
    ilk = ana.HedefTakip
    tut = {}
    ana.HedefTakip = lambda *a, **k: tut.setdefault("t", BoyutTakip(*a, **k))
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
            gt[kare.indeks] = np.asarray(kare.gt, np.float64)
    olc = {r["kare"]: r for r in m.get("_olcum") or []}
    td = m.get("t_drift")

    satir = []
    for i, r in enumerate(tak.iz):
        k = ofset + i
        if k not in gt:
            continue
        g = gt[k]
        gc = g[:2] + g[2:] / 2
        mc = r["merkez"]
        d = {"kare": k, "durum": r["durum"], "dal": r.get("dal"),
             "gt_w": float(g[2]), "gt_h": float(g[3]),
             "olcek_katsayisi": r.get("olcek_katsayisi"),
             "merkez_hata": float(np.linalg.norm(mc - gc)),
             "iou_gercek": olc.get(k, {}).get("iou"),
             "rafine": r.get("rafine"),
             "olculen_w": float(r["olculen"][0]), "olculen_h": float(r["olculen"][1])}
        for et in ("A0", "A1", "A2", "A3", "A4", "A5", "son", "arama_yazdi"):
            if r.get(et) is None:
                continue
            b = np.asarray(r[et], np.float64)
            d[et + "_w"], d[et + "_h"] = float(b[0]), float(b[1])
            d[et + "_ow"] = float(b[0] / max(1e-9, g[2]))
            d[et + "_oh"] = float(b[1] / max(1e-9, g[3]))
        if r.get("sinir_alt") is not None:
            d["sinir_alt_w"] = float(r["sinir_alt"][0])
            d["sinir_alt_h"] = float(r["sinir_alt"][1])
            d["sinir_ust_w"] = float(r["sinir_ust"][0])
            d["sinir_ust_h"] = float(r["sinir_ust"][1])
            a4, a5 = np.asarray(r["A4"]), np.asarray(r["A5"])
            d["kirpma_w"] = float(a5[0] - a4[0])
            d["kirpma_h"] = float(a5[1] - a4[1])
            d["kirpildi"] = bool(abs(d["kirpma_w"]) > 1e-9 or abs(d["kirpma_h"]) > 1e-9)
        # IoU ayristirmasi: SADECE boyut degisir, merkez sabit (kare sonu)
        son = np.asarray(r["son"], np.float64)
        d["iou_son"] = float(ana.iou(_kutu(mc, son), g))
        d["tavan_son"] = float(ana.iou(_kutu(gc, son), g))
        for et in ("A1", "A3", "A5"):
            if r.get(et) is None:
                continue
            b = np.asarray(r[et], np.float64)
            d["tavan_" + et] = float(ana.iou(_kutu(gc, b), g))
        d["boyut_katkisi"] = 1.0 - d["tavan_son"]
        d["merkez_katkisi"] = d["tavan_son"] - (d["iou_gercek"]
                                                if d["iou_gercek"] is not None
                                                else d["iou_son"])
        satir.append(d)
    return {"ad": ad, "tur": tur, "ort_iou": float(m.get("ort_iou", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "t_drift": td, "satir": satir}


def tablo(r):
    td = r["t_drift"]
    if td is None:
        return
    a, b = td - ONCE, td + SONRA
    print(f"\n--- {r['ad']}  drift {td}  (kare {a}..{b}) ---")
    print("kare dal   olc   | A0 w/h    A1 w/h    A3 w/h    A5 w/h  | GT w/h  "
          "| oran A1  A3  A5 (w) | kirp w/h | rafine | IoU  tavan | merkez")
    for d in r["satir"]:
        if not (a <= d["kare"] <= b):
            continue
        f = lambda p: ("%5.1f/%-5.1f" % (d[p + "_w"], d[p + "_h"])) if (p + "_w") in d else "     .     "
        print("%4d %-5s %5s | %s %s %s %s | %5.1f/%-5.1f | %5s %5s %5s | %5s %5s | %-6s | %4s %4s | %5.1f" % (
            d["kare"], (d.get("dal") or "-")[:5],
            "%.3f" % d["olcek_katsayisi"] if d.get("olcek_katsayisi") else "  .  ",
            f("A0"), f("A1"), f("A3"), f("A5"), d["gt_w"], d["gt_h"],
            "%.2f" % d["A1_ow"] if "A1_ow" in d else "  .  ",
            "%.2f" % d["A3_ow"] if "A3_ow" in d else "  .  ",
            "%.2f" % d["A5_ow"] if "A5_ow" in d else "  .  ",
            "%+.2f" % d["kirpma_w"] if "kirpma_w" in d else "  .  ",
            "%+.2f" % d["kirpma_h"] if "kirpma_h" in d else "  .  ",
            "yok" if d.get("rafine") is None else "%.0f/%.0f" % (d["rafine"][2], d["rafine"][3]),
            "%.2f" % d["iou_gercek"] if d.get("iou_gercek") is not None else "  . ",
            "%.2f" % d["tavan_son"], d["merkez_hata"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/boyut_4r.json")
    a = ap.parse_args()
    out = {}
    for ad, tur, arg in HEDEFLER:
        r = analiz(ad, tur, arg)
        out[ad] = r
        print(f"\n== {ad} == IoU {r['ort_iou']:.6f} kilit {100*r['kilit_orani']:.2f}% "
              f"merkez {r['merkez_hata']:.4f} drift {r['t_drift']}", flush=True)
        tablo(r)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"\nyazildi: {a.json}")


if __name__ == "__main__":
    main()
