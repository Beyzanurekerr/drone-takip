"""Deney 4D - salt okunur: rafine merkezinin guvenilirligi ONCEDEN kestirilebilir mi?

TAKIPCIYE DOKUNMAZ. Alt sinif sarmasi + gecici monkeypatch; hicbir esik, karar
ya da parametre degismez.

SORU
----
Deney 4C, `r_carpan`i 1.0'dan 0.17'ye sabitleyerek dustu: rafine merkezinin
dogrulugu SAHNEYE gore degisiyor (Gazebo 0.76 px, VisDrone 117/23 4.78 px -
6.3 kat) ve tek bir sabit agirlik ikisine birden uyamiyor. Bu modul, agirligin
o karede TUREYEBILECEGI sinyalleri arar.

KARAR ANI: izleyici.py:567, `kf.duzelt(yeni_c, r_carpan=...)`. O anda kodda
zaten hazir olan ya da bedelsiz turetilebilen sinyaller:

    d_kf     |yeni_c - kf.konum|        satir 568'de ZATEN hesaplaniyor
    oran_w   r[2] / boyut[0]            rafine kutusunun mevcut kutuya orani
    oran_h   r[3] / boyut[1]
    oran_ort (oran_w + oran_h) / 2      rafine_kutu ICINDE ZATEN deneniyor
    psr      self.psr                   bu karenin DCF guveni
    ego_guven self.ego.guven            RANSAC ic oran
    boyut    kutunun kendisi            4B'de merkez hatasiyla iliskili cikti
    tutarlilik  ardisik rafine merkezlerinin ego-telafili hareketi (hafiza ister)

HEDEF DEGISKEN: |rafine merkezi - GT merkezi| (yalnizca olcum icin; takipci
bunu goremez).

Kullanim:
    python3 -m gazebo.tani_agirlik
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

GAZEBO = ["G3_agresif", "G3_kritik", "G0", "G6_agresif"]
VISDRONE = [("uav0000117_02622_v", 23), ("uav0000182_00000_v", 127),
            ("uav0000268_05773_v", 31)]
VISDRONE_KOK = "data/datasets/visdrone_vid"


class AgirlikTakip(HedefTakip):
    """`_boyut_tazele` KARAR ANINDAKI durumu yazar. Davranis birebir korunur."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.kayit = []
        self._M = None
        gercek_ego = self.cekirdek.ego_guncelle

        def ego_sarma(M):
            self._M = np.asarray(M, np.float64).copy()
            return gercek_ego(M)

        self.cekirdek.ego_guncelle = ego_sarma

    def _boyut_tazele(self, bgr):
        # satir 562'nin ONCESI: rafine_kutu bu `boyut` ve `kf.konum` ile cagrilir
        boyut_once = self.boyut.astype(np.float64).copy()
        konum_once = self.kf.konum.astype(np.float64)
        izl.rafine_kutu.kayit = []
        super()._boyut_tazele(bgr)
        k = [x for x in izl.rafine_kutu.kayit if x["kutu"] is not None]
        if not k:
            return
        r = np.asarray(k[-1]["kutu"], np.float64)
        yeni_c = r[:2] + r[2:] / 2
        self.kayit.append({
            "kare": self.kare,
            "durum": self.durum,
            "psr": float(self.psr),
            "ego_guven": float(self.ego.guven),
            "aci": float(getattr(self.cekirdek, "aci", 0.0)),
            "konum_once": konum_once,
            "yeni_c": yeni_c,
            "d_kf": float(np.linalg.norm(yeni_c - konum_once)),
            "boyut": boyut_once,
            "rafine_wh": r[2:],
            "oran_w": float(r[2] / max(1e-6, boyut_once[0])),
            "oran_h": float(r[3] / max(1e-6, boyut_once[1])),
            "M": self._M,
            "konum_sonra": self.kf.konum.astype(np.float64),
        })


def _sar():
    gercek = izl.rafine_kutu

    def s(bgr, merkez, boyut, *a, **k):
        r = gercek(bgr, merkez, boyut, *a, **k)
        s.kayit.append({"kutu": None if r is None else [float(v) for v in r]})
        return r

    s.kayit = []
    izl.rafine_kutu = s
    return gercek


def _gt_merkezler(kaynak_fn):
    gts = {}
    for kare in kaynak_fn():
        if kare.gt is not None:
            g = kare.gt
            gts[kare.indeks] = np.array([g[0] + g[2] / 2, g[1] + g[3] / 2])
    return gts


def kos(kaynak_fn, etiket):
    gercek = _sar()
    ilk = ana.HedefTakip
    kutu = {}
    ana.HedefTakip = lambda *a, **k: kutu.setdefault("t", AgirlikTakip(*a, **k))
    try:
        m = ana.kos(kaynak_fn(), pencere=False)
    finally:
        ana.HedefTakip = ilk
        izl.rafine_kutu = gercek
    tak = kutu["t"]
    gts = _gt_merkezler(kaynak_fn)

    # gunlukteki `kare` takipcinin ic sayacidir; kilit sonrasi kare indeksine
    # cevirmek icin toplam kare sayisindan ofset cikarilir.
    n_gun = tak.kare
    ofset = int(m["kare"]) - n_gun

    satir = []
    onceki = None
    for r in tak.kayit:
        k = ofset + r["kare"] - 1
        if k not in gts:
            continue
        gt = gts[k]
        d = {"kare": k, "psr": r["psr"], "ego_guven": r["ego_guven"],
             "aci": r["aci"], "d_kf": r["d_kf"],
             "oran_w": r["oran_w"], "oran_h": r["oran_h"],
             "oran_ort": 0.5 * (r["oran_w"] + r["oran_h"]),
             "oran_sapma": abs(0.5 * (r["oran_w"] + r["oran_h"]) - 1.0),
             "w": float(r["boyut"][0]), "h": float(r["boyut"][1]),
             "kosegen": float(np.hypot(*r["boyut"])),
             "rafine_hata": float(np.linalg.norm(r["yeni_c"] - gt)),
             "kf_hata": float(np.linalg.norm(r["konum_once"] - gt)),
             "yeni_c": [float(v) for v in r["yeni_c"]]}
        # ardisik rafine merkezlerinin EGO TELAFILI hareketi: hedef gercekse
        # hareket duzgun, leke atliyorsa sicrar. (Hafiza ister - takipcide yok,
        # burada yalnizca sinyalin degerini olcmek icin hesaplaniyor.)
        d["tutarlilik"] = float("nan")
        if onceki is not None and r["M"] is not None:
            tasinan = r["M"][:, :2] @ onceki["yeni_c"] + r["M"][:, 2]
            d["tutarlilik"] = float(np.linalg.norm(r["yeni_c"] - tasinan)
                                    / max(1.0, r["kare"] - onceki["kare"]))
        onceki = r
        satir.append(d)
    return {"etiket": etiket, "ort_iou": float(m.get("ort_iou", 0.0)),
            "satir": satir}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/agirlik.json")
    a = ap.parse_args()
    out = {}
    for ad in GAZEBO:
        out[ad] = kos(lambda ad=ad: GazeboKaynak(kok="data/gazebo", senaryo=ad), ad)
        print(f"  {ad}: {len(out[ad]['satir'])} rafine olcumu", flush=True)
    for dizi, tid in VISDRONE:
        et = f"{dizi.split('_')[0][3:]}/{tid}"
        out[et] = kos(lambda d=dizi, t=tid: kaynak_olustur(
            "visdrone", veri_kok=VISDRONE_KOK, dizi=d, track_id=t,
            hedef_genislik=960), et)
        print(f"  {et}: {len(out[et]['satir'])} rafine olcumu", flush=True)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"yazildi: {a.json}")


if __name__ == "__main__":
    main()
