"""Deney 4L eki - salt okunur: yanlis-kilit EPIZOTLARININ kare kare anatomisi.

TAKIP/ HIC DEGISMEZ. `tani_yanliskilit.py` bir dizide yanlis kilit OLDUGUNU
soyler; bu arac NEREDE ve NEYLE es zamanli oldugunu soyler.

Gazebo'da hedefin gercek hizi `pozlar.csv`'den okunur; boylece "duran arac"
sinirinin mi yoksa baska bir seyin mi ateslendigi ayirt edilir.

Kullanim: python3 -m gazebo.tani_yk_epizot
"""
import csv
import json
import os

import numpy as np

import main as ana
from kaynak import kaynak_olustur
from takip.izleyici import KILITLI, HedefTakip
from veri.gazebo import GazeboKaynak

VISDRONE_KOK = "data/datasets/visdrone_vid"
GAZEBO_KOK = "data/gazebo"

HEDEFLER = [("G6_agresif_durakli", "gazebo", "G6_agresif_durakli"),
            ("305/5", "visdrone", ("uav0000305_00000_v", 5)),
            ("137/12", "visdrone", ("uav0000137_00458_v", 12)),
            ("182/127", "visdrone", ("uav0000182_00000_v", 127)),
            ("339/49", "visdrone", ("uav0000339_00001_v", 49))]


class SayanTakip(HedefTakip):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []

    def guncelle(self, bgr):
        s = super().guncelle(bgr)
        self.iz.append({"yk": int(self.yanlis_kilit),
                        "psr": float(self.psr),
                        "benzerlik": float(self.benzerlik),
                        "hareketli": bool(self._hareketli),
                        "kutu": None if self.kutu is None
                                else [float(v) for v in self.kutu]})
        return s


def uzerinde(kaynak, k, kutu):
    """Takip kutusu k. karede NEYIN uzerinde? Olcut gazebo/tani.py:290 ile ayni
    (en cok ortusen arac, IoU > 0.2); hicbiri degilse 'zemin'."""
    if kutu is None or k >= len(kaynak.pozlar):
        return None, 0.0
    adlar = [kaynak.hedef_ad] + [a for a in kaynak.olculer
                                 if a != kaynak.hedef_ad]
    en_iyi, en_ad = 0.0, None
    for ad in adlar:
        gb = kaynak._kutu(kaynak.pozlar[k], ad)
        if gb is None:
            continue
        o = float(ana.iou(np.asarray(kutu, np.float32), gb))
        if o > en_iyi:
            en_iyi, en_ad = o, ad
    return (en_ad if en_iyi > 0.2 else "zemin"), en_iyi


def _kaynak(tur, arg):
    if tur == "gazebo":
        return GazeboKaynak(kok=GAZEBO_KOK, senaryo=arg)
    dz, tid = arg
    return kaynak_olustur("visdrone", veri_kok=VISDRONE_KOK, dizi=dz,
                          track_id=tid, hedef_genislik=960)


def hedef_hizi(senaryo):
    """Gazebo: kare basina hedefin DUNYA hizi (m/s)."""
    yol = os.path.join(GAZEBO_KOK, senaryo, "pozlar.csv")
    if not os.path.exists(yol):
        return {}
    t, x, y, k = [], [], [], []
    with open(yol) as f:
        for r in csv.DictReader(f):
            k.append(int(r["kare"]))
            t.append(float(r["t"]))
            x.append(float(r["hedef_x"]))
            y.append(float(r["hedef_y"]))
    t, x, y = np.array(t), np.array(x), np.array(y)
    v = np.zeros_like(t)
    v[1:] = np.hypot(np.diff(x), np.diff(y)) / np.maximum(1e-9, np.diff(t))
    v[0] = v[1]
    return dict(zip(k, (float(u) for u in v)))


def epizotlar(bayrak, kareler):
    """(ilk_kare, son_kare, YK_kareleri). Kare SAYISI ile kare ARALIGI ayni sey
    degildir: aralarinda KILITLI olmayan kareler bulunabilir."""
    out, bas = [], None
    for i, b in enumerate(bayrak):
        if b and bas is None:
            bas = i
        elif not b and bas is not None:
            out.append((kareler[bas], kareler[i - 1], kareler[bas:i]))
            bas = None
    if bas is not None:
        out.append((kareler[bas], kareler[-1], kareler[bas:]))
    return out


def kos(ad, tur, arg):
    ilk = ana.HedefTakip
    kutu = {}
    ana.HedefTakip = lambda *a, **k: kutu.setdefault("t", SayanTakip(*a, **k))
    try:
        m = ana.kos(_kaynak(tur, arg), pencere=False)
    finally:
        ana.HedefTakip = ilk
    olcum = m.get("_olcum") or []
    tak = kutu["t"]
    ofset = int(m["kare"]) - len(tak.iz)

    kilitli = [r for r in olcum if r["durum"] == KILITLI]
    kareler = [r["kare"] for r in kilitli]
    bayrak = [r["iou"] == 0.0 for r in kilitli]
    ep = epizotlar(bayrak, kareler)

    hiz = hedef_hizi(arg) if tur == "gazebo" else {}
    kyn = _kaynak(tur, arg) if tur == "gazebo" else None
    d = {"ad": ad, "n_kilitli": len(kilitli), "epizot": []}
    for a, b, yk_k in ep:
        n = len(yk_k)
        i0, i1 = a - ofset, b - ofset
        dil = tak.iz[max(0, i0):max(0, i1) + 1]
        e = {"bas": a, "son": b, "yk_kare": n, "aralik": b - a + 1,
             "psr_med": float(np.median([r["psr"] for r in dil])) if dil else None,
             "benzerlik_med": float(np.median([r["benzerlik"] for r in dil])) if dil else None,
             "hareketli_oran": float(np.mean([r["hareketli"] for r in dil])) if dil else None,
             "red_icinde": (dil[-1]["yk"] - dil[0]["yk"]) if dil else 0}
        if kyn is not None:
            sayim = {}
            for kk in yk_k:                       # YALNIZCA YK kareleri
                r = tak.iz[kk - ofset]
                nm, _ = uzerinde(kyn, kk, r["kutu"])
                sayim[nm] = sayim.get(nm, 0) + 1
            e["uzerinde"] = sayim
        if hiz:
            ic = [hiz[k] for k in range(a, b + 1) if k in hiz]
            onc = [hiz[k] for k in range(max(0, a - 30), a) if k in hiz]
            e["hedef_hiz_med"] = float(np.median(ic)) if ic else None
            e["hedef_hiz_min"] = float(np.min(ic)) if ic else None
            e["hiz_onceki30_med"] = float(np.median(onc)) if onc else None
            # epizotun BASLADIGI andaki hiz: "duran arac" siniri mi?
            bas_p = [hiz[k] for k in range(max(0, a - 10), a + 1) if k in hiz]
            e["hiz_baslangic"] = [round(float(v), 2) for v in bas_p]
        d["epizot"].append(e)
    if hiz:
        tv = np.array([hiz[k] for k in sorted(hiz)])
        d["hiz_ozet"] = {"med": float(np.median(tv)), "min": float(tv.min()),
                         "maks": float(tv.max()),
                         "durma_karesi": int(np.sum(tv < 0.5))}
    return d


def main():
    out = {}
    for ad, tur, arg in HEDEFLER:
        r = kos(ad, tur, arg)
        out[ad] = r
        print(f"\n== {ad} == kilitli {r['n_kilitli']}", flush=True)
        if "hiz_ozet" in r:
            h = r["hiz_ozet"]
            print(f"   hedef hizi med {h['med']:.2f} min {h['min']:.2f} "
                  f"maks {h['maks']:.2f} m/s, <0.5 m/s kare {h['durma_karesi']}")
        for e in r["epizot"]:
            s = (f"   epizot {e['bas']}..{e['son']} (YK {e['yk_kare']} kare / "
                 f"aralik {e['aralik']}) "
                 f"PSR~{e['psr_med']:.1f} benz~{e['benzerlik_med']:.2f} "
                 f"hareketli %{100*e['hareketli_oran']:.0f} red+{e['red_icinde']}")
            if "uzerinde" in e:
                s += "\n      kutu neyin uzerinde: " + str(e["uzerinde"])
            if "hedef_hiz_med" in e:
                s += (f"  hedef hizi med {e['hedef_hiz_med']:.2f} "
                      f"min {e['hedef_hiz_min']:.2f} "
                      f"(onceki 30 kare {e['hiz_onceki30_med']:.2f})"
                      f"\n      basta -10..0 kare hizi: {e['hiz_baslangic']}")
            print(s, flush=True)
    os.makedirs("cikti", exist_ok=True)
    with open("cikti/yk_epizot.json", "w") as f:
        json.dump(out, f, indent=1)
    print("\nyazildi: cikti/yk_epizot.json")


if __name__ == "__main__":
    main()
