"""Salt okunur teshis: ornekleme kutusu geometrisi ve en-boy orani sapmasi.

TAKIPCIYE DOKUNMAZ. `takip/` altindaki hicbir dosya degismedi; buradaki her sey
alt sinif sarmasi ya da gecici monkeypatch ile DISARIDAN gozlemdir.

NE SORUYOR
----------
Deney 3, aci hatasini 7.5 kat dusurdugu halde IoU kazanci getirmedi. Demek ki
aci hatasi ile IoU arasindaki -0.729 korelasyonu nedensel degil, ortak bir
ucuncu degiskenin golgesi. Aday: DCF yamasinin EN-BOY ORANI.

Sentetik olcum (Deney 3 tasarim raporu, on olcum 2): ornekleme kutusu kilit
en-boy oranini korurken aci kestirimi -60..+60 derece arasinda TAM dogru
(hata 0.0, PSR ~146); oran %12 saparsa PSR 7 kat duser, %22 saparsa kestirim
tamamen coker.

Bu modul o sapmayi GERCEK kosumlarda kare kare olcer ve dort kaynak adayina
ayristirir:
    1) sabit boyutlu kutu               (kilit boyutunun kendisi)
    2) rafine_kutu                      (renk kontrastiyla yeniden olcum)
    3) _boyut_sinirla                   (boyut_olculen etrafindaki kelepce)
    4) donen kutunun EKSEN HIZALI bounding box'a donusmesi  (GT'nin kendisi)

Ayristirma icin `boyut`un her asamadaki degisimi ayri ayri kaydedilir:
    ego olcegi  -> guncelle icinde `boyut *= olc`
    tazele      -> `_boyut_tazele` (dogrulama_araligi karede bir)
    kelepce     -> `_boyut_sinirla` (her kare)

Kullanim:
    python3 -m gazebo.tani_geometri
    python3 -m gazebo.tani_geometri --senaryo G3_agresif G3_kritik
"""
import argparse
import json
import os
import sys

import numpy as np

import main as ana
import takip.izleyici as izl
from calistir import iou
from kaynak import kaynak_olustur
from takip.izleyici import HedefTakip

GAZEBO = ["G3_yumusak", "G3_agresif", "G3_kritik", "G4_kritik", "G6_agresif"]
VISDRONE = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31),
            ("uav0000182_00000_v", 127)]
VISDRONE_KOK = "data/datasets/visdrone_vid"


class GeoTakip(HedefTakip):
    """Her karede `boyut`un asama asama nasil degistigini yazar."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.kilit_boyut = None
        self.gunluk = []
        self._d = {}

    def kilitle(self, bgr, kutu):
        r = super().kilitle(bgr, kutu)
        self.kilit_boyut = self.boyut.copy()
        return r

    def _boyut_tazele(self, bgr):
        once = self.boyut.copy()
        super()._boyut_tazele(bgr)
        self._d["tazele"] = self.boyut - once

    def _boyut_sinirla(self):
        once = self.boyut.copy()
        super()._boyut_sinirla()
        self._d["kelepce"] = self.boyut - once

    def guncelle(self, bgr):
        giris = self.boyut.copy()
        self._d = {"tazele": np.zeros(2), "kelepce": np.zeros(2)}
        izl.rafine_kutu.kayit = []          # bu karedeki rafine cagrilari
        sonuc = super().guncelle(bgr)
        olc = float(np.clip(self.ego.olcek_katsayisi, 0.90, 1.10))
        d_ego = giris * olc - giris
        self.gunluk.append({
            "kare_ic": self.kare,
            "durum": self.durum,
            "psr": float(self.psr),
            "giris_boyut": giris,
            "boyut": self.boyut.copy(),
            "boyut_olculen": self.boyut_olculen.copy(),
            "d_ego": d_ego,
            "d_tazele": self._d["tazele"].copy(),
            "d_kelepce": self._d["kelepce"].copy(),
            "olc": olc,
            "aci": float(getattr(self.cekirdek, "aci", 0.0)),
            "aktif": bool(getattr(self.cekirdek, "aktif", False)),
            "rafine": list(izl.rafine_kutu.kayit),
            "merkez": self.kf.konum.copy(),
        })
        return sonuc


def _rafine_sar():
    """`rafine_kutu`yu saydam sar: cikti kaydedilir, davranis DEGISMEZ."""
    gercek = izl.rafine_kutu

    def sarma(bgr, merkez, boyut, *a, **k):
        # imza AYNEN aktarilir: rafine_kutu(bgr, merkez, boyut, buyutme=3.0,
        # min_esik=16.0, hedef_renk=None, renk_tol=60.0). Konumlu 4. argumani
        # hedef_renk sanmak sessiz bir TypeError uretiyordu.
        r = gercek(bgr, merkez, boyut, *a, **k)
        sarma.kayit.append({
            "giris": [float(boyut[0]), float(boyut[1])],
            "cikti": None if r is None else [float(r[2]), float(r[3])],
        })
        return r

    sarma.kayit = []
    sarma._gercek = gercek
    izl.rafine_kutu = sarma
    return gercek


def _rafine_coz(gercek):
    izl.rafine_kutu = gercek


def kos(kaynak, etiket):
    gercek = _rafine_sar()
    ilk = ana.HedefTakip
    kutu = {}
    ana.HedefTakip = lambda *a, **k: kutu.setdefault("t", GeoTakip(*a, **k))
    try:
        m = ana.kos(kaynak, pencere=False)
    finally:
        ana.HedefTakip = ilk
        _rafine_coz(gercek)
    tak = kutu["t"]
    g = tak.gunluk
    n = int(m["kare"])
    ofset = n - len(g)
    for i, r in enumerate(g):
        r["kare"] = ofset + i
    olcum = {r["kare"]: r for r in m.get("_olcum", [])}
    kb = tak.kilit_boyut
    kilit_oran = float(kb[0] / max(1e-6, kb[1]))

    satir = []
    for r in g:
        o = olcum.get(r["kare"])
        if o is None:
            continue
        b = r["boyut"]
        oran = float(b[0] / max(1e-6, b[1]))
        gw, gh = float(o["gt_w"]), float(o["gt_h"])
        satir.append({
            "kare": r["kare"],
            "kilit_w": float(kb[0]), "kilit_h": float(kb[1]),
            "kilit_oran": kilit_oran,
            "w": float(b[0]), "h": float(b[1]), "oran": oran,
            "sapma_pct": 100.0 * (oran / kilit_oran - 1.0),
            "gt_w": gw, "gt_h": gh, "gt_oran": gw / max(1e-6, gh),
            "gt_sapma_pct": 100.0 * ((gw / max(1e-6, gh)) /
                                     (satir[0]["gt_oran"] if satir else gw / max(1e-6, gh)) - 1.0),
            "aci": r["aci"], "aktif": r["aktif"], "psr": r["psr"],
            "iou": float(o["iou"]), "merkez_hata": float(o["merkez_hata"]),
            "d_ego": [float(x) for x in r["d_ego"]],
            "d_tazele": [float(x) for x in r["d_tazele"]],
            "d_kelepce": [float(x) for x in r["d_kelepce"]],
            "rafine": r["rafine"],
            "olculen_w": float(r["boyut_olculen"][0]),
            "olculen_h": float(r["boyut_olculen"][1]),
            "merkez": [float(x) for x in r["merkez"]],
        })
    return {"etiket": etiket, "kilit_boyut": [float(kb[0]), float(kb[1])],
            "kilit_oran": kilit_oran, "ort_iou": float(m.get("ort_iou", 0.0)),
            "satir": satir}


def gazebo_kos(ad):
    from veri.gazebo import GazeboKaynak
    return kos(GazeboKaynak(kok="data/gazebo", senaryo=ad), ad)


def visdrone_kos(dizi, tid):
    k = kaynak_olustur("visdrone", veri_kok=VISDRONE_KOK, dizi=dizi,
                       track_id=tid, hedef_genislik=960)
    return kos(k, f"{dizi.split('_')[0][3:]}/{tid}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--senaryo", nargs="*", default=None)
    ap.add_argument("--json", default="cikti/geometri.json")
    a = ap.parse_args()
    cikti = {}
    adlar = a.senaryo or GAZEBO
    for ad in adlar:
        cikti[ad] = gazebo_kos(ad)
        print(f"  {ad} bitti ({len(cikti[ad]['satir'])} kare)", flush=True)
    if a.senaryo is None:
        for dizi, tid in VISDRONE:
            r = visdrone_kos(dizi, tid)
            cikti[r["etiket"]] = r
            print(f"  {r['etiket']} bitti ({len(r['satir'])} kare)", flush=True)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(cikti, f)
    print(f"yazildi: {a.json}")


if __name__ == "__main__":
    main()
