"""Deney 4L - salt okunur: KARAR VERILEBILIR yanlis-kilit kaynagi var mi?

TAKIP/ HIC DEGISMEZ. Takipci kosturulur ama yalnizca gozlemlenir; hicbir esik,
parametre ya da karar degistirilmez. Tek mudahale, `main.kos`'un ZATEN
destekledigi `hedef_secici` kancasiyla ILK KILIT KUTUSUNU +-1 px oynatmaktir
(kaos olcumu icin); takipcinin kendi kodu bundan habersizdir.

4K'nin birakti�i tek soru:

    Yanlis kilidi olcebilecek, metrigi doygun OLMAYAN ve kaotik OLMAYAN bir
    kaynak var mi? Yoksa 4K'nin gercek degeri (bias mi, yanlis kilit mi)
    olculemez.

TANIM (esik icat edilmedi): takipci KILITLI diyor ama kutunun GT ile ortusmesi
SIFIR olan kare = YANLIS KILIT KARESI. "Kilitliyim" iddiasi ile "baska bir sey
takip ediyorum" gercegi arasindaki celiski dogrudan budur.
Takipcinin kendi `yanlis_kilit` sayaci AYRI raporlanir: o, savunmanin kac kez
ATESLEDIGIdir; yukaridaki ise savunmanin kac kez ATESLEMEDIGIdir.

Kullanim:
    python3 -m gazebo.tani_yanliskilit            # envanter + kaos olcumu
    python3 -m gazebo.tani_yanliskilit --hizli    # yalnizca envanter
"""
import argparse
import json
import os

import numpy as np

import main as ana
from kaynak import kaynak_olustur
from takip.izleyici import KILITLI, HedefTakip
from veri.gazebo import GazeboKaynak

VISDRONE_KOK = "data/datasets/visdrone_vid"
GAZEBO_KOK = "data/gazebo"

# 4I'nin envanterindeki tum arac track'leri (086'da arac track'i yok).
VISDRONE = [("117/23", "uav0000117_02622_v", 23),
            ("137/12", "uav0000137_00458_v", 12),
            ("182/127", "uav0000182_00000_v", 127),
            ("268/31", "uav0000268_05773_v", 31),
            ("305/5", "uav0000305_00000_v", 5),
            ("339/49", "uav0000339_00001_v", 49)]

# ilk kilit kutusunun oynatildigi +-1 px komsulugu (kaos probu)
OFSETLER = [(0.0, 0.0), (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
            (1.0, 1.0), (1.0, -1.0), (-1.0, 1.0), (-1.0, -1.0)]

GORUNURLUK_ESIK = 0.70          # 4I O2, aynen devralindi


class SayanTakip(HedefTakip):
    """Yalnizca gozlem: kare kare `yanlis_kilit` sayacini kaydeder."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.yk_izi = []

    def guncelle(self, bgr):
        s = super().guncelle(bgr)
        self.yk_izi.append(int(self.yanlis_kilit))
        return s


def _kaynak(tur, arg):
    if tur == "gazebo":
        return GazeboKaynak(kok=GAZEBO_KOK, senaryo=arg)
    dz, tid = arg
    return kaynak_olustur("visdrone", veri_kok=VISDRONE_KOK, dizi=dz,
                          track_id=tid, hedef_genislik=960)


def _secici(ofset):
    """`otomatik_hedef_sec`'i sarar, secilen kutuyu `ofset` kadar oteler."""
    if ofset == (0.0, 0.0):
        return None
    d = np.asarray(ofset, np.float32)

    def s(adaylar, kare):
        a = ana.otomatik_hedef_sec(adaylar, kare)
        if a is None:
            return None
        a = dict(a)
        a["merkez"] = np.asarray(a["merkez"], np.float32) + d
        return a
    return s


def _seriler(bayrak):
    """Ardisik True serilerinin uzunluklari."""
    out, n = [], 0
    for b in bayrak:
        if b:
            n += 1
        elif n:
            out.append(n)
            n = 0
    if n:
        out.append(n)
    return out


def kos(tur, arg, ofset=(0.0, 0.0)):
    ilk = ana.HedefTakip
    kutu = {}
    ana.HedefTakip = lambda *a, **k: kutu.setdefault("t", SayanTakip(*a, **k))
    try:
        m = ana.kos(_kaynak(tur, arg), pencere=False,
                    hedef_secici=_secici(ofset))
    finally:
        ana.HedefTakip = ilk
    olcum = m.get("_olcum") or []
    tak = kutu.get("t")

    kilitli = [r for r in olcum if r["durum"] == KILITLI]
    yk = [r["iou"] == 0.0 for r in kilitli]
    n_k = len(kilitli)
    seri = _seriler(yk)
    return {"kare": int(m["kare"]), "gt_kare": int(m.get("gt_kare", 0)),
            "gorunurluk": float(m.get("gt_kare", 0)) / max(1, int(m["kare"])),
            "n_kilitli": n_k,
            "yk_kare": int(sum(yk)),
            "yk_orani": float(sum(yk)) / n_k if n_k else float("nan"),
            "yk_epizot": len(seri),
            "yk_en_uzun": max(seri) if seri else 0,
            "red_sayisi": int(tak.yanlis_kilit) if tak else 0,
            "ort_iou": float(m.get("ort_iou", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "t_drift": m.get("t_drift")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/yanliskilit.json")
    ap.add_argument("--hizli", action="store_true", help="kaos probunu atla")
    a = ap.parse_args()

    kaynaklar = [(s, "gazebo", s) for s in
                 sorted(d for d in os.listdir(GAZEBO_KOK)
                        if not d.startswith("_")
                        and os.path.isdir(os.path.join(GAZEBO_KOK, d)))]
    kaynaklar += [(ad, "visdrone", (dz, t)) for ad, dz, t in VISDRONE]

    out = {}
    print("== envanter ==", flush=True)
    for ad, tur, arg in kaynaklar:
        r = kos(tur, arg)
        out[ad] = {"tur": tur, "taban": r}
        print(f"  {ad:22s} kare {r['kare']:4d} gor {r['gorunurluk']:.2f} "
              f"kilitli {r['n_kilitli']:4d}  YK %{100*r['yk_orani']:5.1f} "
              f"epizot {r['yk_epizot']:2d} enuzun {r['yk_en_uzun']:4d}  "
              f"red {r['red_sayisi']:2d}  IoU {r['ort_iou']:.3f}", flush=True)

    if not a.hizli:
        print("\n== kaos probu (ilk kilit kutusu +-1 px) ==", flush=True)
        for ad, tur, arg in kaynaklar:
            t = out[ad]["taban"]
            if t["gorunurluk"] < GORUNURLUK_ESIK or t["n_kilitli"] == 0:
                continue
            oranlar, iou = [], []
            for of in OFSETLER:
                r = t if of == (0.0, 0.0) else kos(tur, arg, of)
                oranlar.append(r["yk_orani"])
                iou.append(r["ort_iou"])
            o = np.asarray(oranlar, np.float64)
            i = np.asarray(iou, np.float64)
            out[ad]["kaos"] = {"yk_oranlar": [float(v) for v in o],
                               "iou_lar": [float(v) for v in i],
                               "yk_aralik": float(np.nanmax(o) - np.nanmin(o)),
                               "yk_std": float(np.nanstd(o)),
                               "iou_aralik": float(np.nanmax(i) - np.nanmin(i)),
                               "iou_std": float(np.nanstd(i))}
            k = out[ad]["kaos"]
            print(f"  {ad:22s} YK %{100*np.nanmin(o):5.1f}..%{100*np.nanmax(o):5.1f} "
                  f"(aralik %{100*k['yk_aralik']:5.1f}, std %{100*k['yk_std']:.1f})   "
                  f"IoU {np.nanmin(i):.3f}..{np.nanmax(i):.3f} "
                  f"(aralik {k['iou_aralik']:.3f})", flush=True)

    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nyazildi: {a.json}")


if __name__ == "__main__":
    main()
