"""Deney 4M - salt okunur: G6_agresif_durakli / G6_agresif KONTROLLU CIFTI.

TAKIP/ HIC DEGISMEZ. Alt sinif + gecici sarmalayici; hicbir esik, parametre,
Kalman, DCF, sablon, ego, aci/sekil/padding/rafine ayari degistirilmez.
Yalnizca ZATEN hesaplanan degerler okunur.

Iki senaryo yalnizca HEDEF HIZ PROFILINDE farklidir (senaryolar.py:_G6,
hiz modulasyonu 3.0 vs 5.0 m/s); kamera bozulmasi, sahne, zemin, celdirici,
kamera hizi (32 m/s capraz) AYNIDIR. Bu yuzden aradaki fark tek degiskenlidir.

BORU HATTI SIRASI (izleyici.py:236-296, grep ile dogrulandi)
  1  ego.guncelle(gri, kutu)            -> M, ego_guven          (satir 242)
  2  cekirdek.ego_guncelle(M)                                    (satir 248)
  3  ongoru = M[:, :2] @ onceki_merkez + M[:, 2]                 (satir 255)
  4  kf.tahmin(M)                       -> KF ONGORUSU           (satir 264)
  5  boyut *= olcek                                              (satir 265)
  6  _takip_adimi: cekirdek.ara(...)    -> DCF TEPESI + PSR      (satir 305)
     kf.duzelt(yeni) | kf.sondur()      -> FINAL                 (satir 311/321/326)
     cekirdek.ogren(...)                -> SABLON                (satir 316)
  7  _bagimsiz_dogrula                  -> _hareketli, benzerlik (satir 276)

Kullanim: python3 -m gazebo.tani_g6_cift
"""
import argparse
import csv
import json
import os

import numpy as np

import main as ana
import takip.izleyici as izl
from takip.izleyici import KILITLI, HedefTakip
from veri.gazebo import GazeboKaynak

KOK = "data/gazebo"
CIFT = ["G6_agresif_durakli", "G6_agresif"]
PENCERE = (130, 165)        # yakin plan
ODAK = (145, 152)           # 4L'nin isaret ettigi kopus araligi


class IzTakip(HedefTakip):
    """Yalnizca gozlem. Her sarmalayici gercek cagriyi AYNEN yapar."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []
        self._d = {}
        c = self.cekirdek
        g_ara, g_ogr, g_ego_c = c.ara, c.ogren, c.ego_guncelle
        g_ego = self.ego.guncelle

        def ego_s(gri, kutu=None):
            M, gv = g_ego(gri, kutu)
            self._d["M"] = np.asarray(M, np.float64).copy()
            self._d["ego_guven"] = float(gv)
            return M, gv

        def egoc_s(M):
            return g_ego_c(M)

        def ara_s(bgr, gri, merkez, boyut):
            self._d["kf_ongoru"] = np.asarray(merkez, np.float64).copy()
            yeni, psr = g_ara(bgr, gri, merkez, boyut)
            self._d["dcf"] = np.asarray(yeni, np.float64).copy()
            self._d["psr"] = float(psr)
            return yeni, psr

        def ogr_s(bgr, gri, merkez, boyut, lr=None):
            A0 = None if c.A is None else c.A.copy()
            g_ogr(bgr, gri, merkez, boyut, lr)
            self._d["lr"] = float(c.lr if lr is None else lr)
            if A0 is not None and c.A is not None:
                self._d["sablon_degisim"] = float(
                    np.linalg.norm(c.A - A0) / max(1e-12, np.linalg.norm(c.A)))

        self.ego.guncelle = ego_s
        c.ara, c.ogren, c.ego_guncelle = ara_s, ogr_s, egoc_s

    def kilitle(self, bgr, kutu):
        r = super().kilitle(bgr, kutu)
        kf = self.kf
        g_tah, g_duz, g_son = kf.tahmin, kf.duzelt, kf.sondur

        def tah_s(M):
            g_tah(M)
            self._d["kf_tahmin_sonrasi"] = kf.konum.astype(np.float64)

        def duz_s(z, r_carpan=1.0):
            self._d["kf_duzelt_oncesi"] = kf.konum.astype(np.float64)
            g_duz(z, r_carpan)
            self._d["r_carpan"] = float(r_carpan)
            self._d["kf_duzeltildi"] = True

        def son_s(kat=0.97):
            g_son(kat)
            self._d["kf_sonduruldu"] = True

        kf.tahmin, kf.duzelt, kf.sondur = tah_s, duz_s, son_s
        return r

    def _boyut_tazele(self, bgr):
        izl.rafine_kutu.kayit = []
        b0 = self.boyut.copy()
        super()._boyut_tazele(bgr)
        k = izl.rafine_kutu.kayit
        self._d["rafine_cagri"] = len(k)
        self._d["rafine_basari"] = sum(1 for x in k if x is not None)
        self._d["boyut_degisim"] = float(np.linalg.norm(self.boyut - b0))

    def guncelle(self, bgr):
        self._d = {}
        onceki = None if self._onceki_merkez is None else \
            np.asarray(self._onceki_merkez, np.float64).copy()
        yk0 = int(self.yanlis_kilit)
        s = super().guncelle(bgr)
        d = dict(self._d)
        d["onceki_merkez"] = onceki
        d["final"] = self.kf.konum.astype(np.float64)
        d["kf_hiz"] = self.kf.hiz.astype(np.float64)
        d["boyut"] = self.boyut.astype(np.float64).copy()
        d["durum"] = self.durum
        d["psr_son"] = float(self.psr)
        d["aci"] = float(getattr(self.cekirdek, "aci", 0.0))
        d["hareketli"] = bool(self._hareketli)
        d["hareketli_guclu"] = bool(self._hareketli_guclu)
        d["benzerlik"] = float(self.benzerlik)
        d["kayip"] = int(self.kayip)
        d["yk_delta"] = int(self.yanlis_kilit) - yk0
        d["yk_toplam"] = int(self.yanlis_kilit)
        self.iz.append(d)
        return s


def gt_ve_hiz(senaryo):
    """GT merkezi/kutusu (goruntu) + hedefin DUNYA hizi ve ivmesi."""
    k = GazeboKaynak(kok=KOK, senaryo=senaryo)
    gt, gtb = {}, {}
    for kare in k:
        if kare.gt is not None and kare.gorunur:
            b = kare.gt
            gt[kare.indeks] = np.array([b[0] + b[2] / 2.0, b[1] + b[3] / 2.0])
            gtb[kare.indeks] = np.array([float(b[2]), float(b[3])])
    t, x, y, kk = [], [], [], []
    with open(os.path.join(KOK, senaryo, "pozlar.csv")) as f:
        for r in csv.DictReader(f):
            kk.append(int(r["kare"]))
            t.append(float(r["t"]))
            x.append(float(r["hedef_x"]))
            y.append(float(r["hedef_y"]))
    t, x, y = np.array(t), np.array(x), np.array(y)
    v = np.zeros_like(t)
    v[1:] = np.hypot(np.diff(x), np.diff(y)) / np.maximum(1e-9, np.diff(t))
    v[0] = v[1]
    a = np.zeros_like(t)
    a[1:] = np.diff(v) / np.maximum(1e-9, np.diff(t))
    return gt, gtb, dict(zip(kk, map(float, v))), dict(zip(kk, map(float, a)))


def _rafine_sar():
    gercek = izl.rafine_kutu

    def s(bgr, merkez, boyut, *a, **k):
        r = gercek(bgr, merkez, boyut, *a, **k)
        s.kayit.append(None if r is None else [float(v) for v in r])
        return r

    s.kayit = []
    izl.rafine_kutu = s
    return gercek


def kos(senaryo):
    gt, gtb, hiz, ivme = gt_ve_hiz(senaryo)
    gercek_rafine = _rafine_sar()
    ilk = ana.HedefTakip
    tut = {}
    ana.HedefTakip = lambda *a, **k: tut.setdefault("t", IzTakip(*a, **k))
    try:
        m = ana.kos(GazeboKaynak(kok=KOK, senaryo=senaryo), pencere=False)
    finally:
        ana.HedefTakip = ilk
        izl.rafine_kutu = gercek_rafine
    tak = tut["t"]
    ofset = int(m["kare"]) - len(tak.iz)
    iou_k = {r["kare"]: r["iou"] for r in m.get("_olcum", [])}

    satir = []
    for i, r in enumerate(tak.iz):
        k = ofset + i
        d = {"kare": k, "durum": r["durum"], "psr": r.get("psr"),
             "psr_son": r["psr_son"], "aci": r["aci"],
             "w": float(r["boyut"][0]), "h": float(r["boyut"][1]),
             "hareketli": r["hareketli"],
             "hareketli_guclu": r["hareketli_guclu"],
             "benzerlik": r["benzerlik"], "kayip": r["kayip"],
             "yk_delta": r["yk_delta"], "yk_toplam": r["yk_toplam"],
             "lr": r.get("lr"), "sablon_degisim": r.get("sablon_degisim"),
             "kf_duzeltildi": bool(r.get("kf_duzeltildi")),
             "kf_sonduruldu": bool(r.get("kf_sonduruldu")),
             "r_carpan": r.get("r_carpan"),
             "ego_guven": r.get("ego_guven"),
             "rafine_cagri": r.get("rafine_cagri"),
             "rafine_basari": r.get("rafine_basari"),
             "boyut_degisim": r.get("boyut_degisim"),
             "kf_hiz": float(np.linalg.norm(r["kf_hiz"])),
             "iou": iou_k.get(k),
             "hedef_hiz": hiz.get(k), "hedef_ivme": ivme.get(k)}
        fin = r["final"]
        d["final_x"], d["final_y"] = float(fin[0]), float(fin[1])
        M = r.get("M")
        onc = r.get("onceki_merkez")
        # 3) ego'nun onceki merkezi tasidigi yer
        ong = None
        if M is not None and onc is not None:
            ong = M[:, :2] @ onc + M[:, 2]
            d["ego_tasima"] = float(np.linalg.norm(ong - onc))
            d["ego_tasima_x"] = float((ong - onc)[0])
            d["ego_tasima_y"] = float((ong - onc)[1])
        if k in gt:
            g = gt[k]
            d["gt_x"], d["gt_y"] = float(g[0]), float(g[1])
            d["gt_w"], d["gt_h"] = float(gtb[k][0]), float(gtb[k][1])
            d["final_hata"] = float(np.linalg.norm(fin - g))
            d["dx"] = float(fin[0] - g[0])
            d["dy"] = float(fin[1] - g[1])
            if r.get("dcf") is not None:
                d["dcf_hata"] = float(np.linalg.norm(r["dcf"] - g))
                d["dcf_x"], d["dcf_y"] = float(r["dcf"][0]), float(r["dcf"][1])
            if r.get("kf_ongoru") is not None:
                d["kf_ongoru_hata"] = float(np.linalg.norm(r["kf_ongoru"] - g))
            if ong is not None:
                # ego UYGULANMIS vs UYGULANMAMIS onceki merkez
                d["ego_ongoru_hata"] = float(np.linalg.norm(ong - g))
                d["egosuz_hata"] = float(np.linalg.norm(onc - g))
            kp = k - 1
            if kp in gt:
                hh = g - gt[kp]
                d["gt_akis"] = float(np.linalg.norm(hh))
                d["gt_akis_x"], d["gt_akis_y"] = float(hh[0]), float(hh[1])
                if M is not None:
                    # ego'nun GT konumundaki otelemesi (hedeften bagimsiz)
                    eg = (M[:, :2] @ gt[kp] + M[:, 2]) - gt[kp]
                    d["ego_gt_x"], d["ego_gt_y"] = float(eg[0]), float(eg[1])
                    d["ego_gt"] = float(np.linalg.norm(eg))
                    # ego telafisinden ARTAKALAN: M(gt_onceki) - gt_simdi
                    bg = (M[:, :2] @ gt[kp] + M[:, 2]) - g
                    d["ego_artik"] = float(np.linalg.norm(bg))
                    d["ego_artik_x"], d["ego_artik_y"] = float(bg[0]), float(bg[1])
        # KF artigi ve guncellemesi
        pr = r.get("kf_tahmin_sonrasi")
        if pr is not None:
            d["kf_ongoru_x"], d["kf_ongoru_y"] = float(pr[0]), float(pr[1])
            if r.get("dcf") is not None:
                res = r["dcf"] - pr
                d["kf_artik"] = float(np.linalg.norm(res))
                d["kf_artik_x"], d["kf_artik_y"] = float(res[0]), float(res[1])
            upd = fin - pr
            d["kf_guncelleme"] = float(np.linalg.norm(upd))
        satir.append(d)
    return {"senaryo": senaryo, "ort_iou": float(m.get("ort_iou", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "t_drift": m.get("t_drift"), "satir": satir}


def _f(v, n=2):
    return "  .  " if v is None else f"{v:.{n}f}"


def tablo(r, a, b):
    print(f"\n--- {r['senaryo']}  kare {a}..{b - 1} ---")
    print("kare  hiz  ivme | egoGT egoArt | KFong  DCF  final |"
          " KFartik KFguc | PSR  IoU  durum  har benz  sabl")
    for d in r["satir"]:
        if not (a <= d["kare"] < b):
            continue
        print(f"{d['kare']:4d} {_f(d.get('hedef_hiz'))} {_f(d.get('hedef_ivme'),1):>6}"
              f" | {_f(d.get('ego_gt')):>5} {_f(d.get('ego_artik')):>5}"
              f" | {_f(d.get('kf_ongoru_hata')):>5} {_f(d.get('dcf_hata')):>5}"
              f" {_f(d.get('final_hata')):>5}"
              f" | {_f(d.get('kf_artik')):>6} {_f(d.get('kf_guncelleme')):>5}"
              f" | {_f(d.get('psr'),1):>5} {_f(d.get('iou')):>5} {d['durum']:<7}"
              f" {'H' if d['hareketli'] else '-'} {_f(d.get('benzerlik')):>4}"
              f" {_f(d.get('sablon_degisim'),3):>5}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/g6_cift.json")
    ap.add_argument("--a", type=int, default=PENCERE[0])
    ap.add_argument("--b", type=int, default=PENCERE[1])
    a = ap.parse_args()
    out = {}
    for s in CIFT:
        r = kos(s)
        out[s] = r
        print(f"\n== {s} == IoU {r['ort_iou']:.3f} kilit {100*r['kilit_orani']:.1f}% "
              f"merkez {r['merkez_hata']:.2f} drift {r['t_drift']}", flush=True)
        tablo(r, a.a, a.b)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"\nyazildi: {a.json}")


if __name__ == "__main__":
    main()
