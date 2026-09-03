"""Deney 4B - salt okunur: merkez hatasi boru hattinin hangi asamasinda olusuyor?

TAKIPCIYE DOKUNMAZ. `takip/` altindaki hicbir dosya degismedi. Butun gozlem
alt sinif sarmasi ve gecici monkeypatch ile disaridan yapilir; hicbir esik,
hicbir karar, hicbir parametre degismez.

ASAMA HARITASI (koddaki gercek isimler, grep'lenerek dogrulandi)
---------------------------------------------------------------
    1 GT           veri/gazebo.py:GazeboKaynak._kutu  -> Kare.gt
    2 rafine       tespit.py:rafine_kutu -> izleyici.py:_boyut_tazele `yeni_c`
                   (ve satir 567'deki kf.duzelt(yeni_c, r_carpan=1.0))
    3 DCF tepesi   cekirdekler.py:RenkDcfCekirdek.ara -> _tepe
                   (izleyici.py:_takip_adimi icinde `yeni`)
    4 KF ongoru    izleyici.py:263 kf.tahmin(M) SONRASI kf.konum
    5 KF duzeltme  izleyici.py:312/327 kf.duzelt(...) SONRASI kf.konum
    6 ego          izleyici.py:253 ongoru = M[:,:2] @ _onceki_merkez + M[:,2]
    7 final        HedefTakip.kutu -> kf.konum (karenin sonunda)

MERKEZE IKI OLCUM GIRER: DCF her karede, rafine 4 karede bir. Ikisi ayri ayri
kaydedilir; aksi halde "Kalman kaydirdi" ile "rafine kaydirdi" ayrilamaz.

HATA IKI CERCEVEDE OLCULUR
--------------------------
Goruntu cercevesi ve SABLON cercevesi (hata vektoru -aci ile dondurulur).
Ayrim belirleyici: sablonun ogrendigi tepe hedefin gercek merkezinden sabit bir
vektor kadar kaymissa, bu kayma SABLON cercevesinde sabit gorunur, goruntu
cercevesinde ise aci ile birlikte doner. Tek cercevede bakmak ikisini ayirmaz.

Kullanim:
    python3 -m gazebo.tani_merkez
    python3 -m gazebo.tani_merkez --senaryo G3_agresif G3_kritik
"""
import argparse
import json
import os

import numpy as np

import main as ana
import takip.izleyici as izl
from takip.izleyici import KILITLI, HedefTakip
from veri.gazebo import GazeboKaynak

VARSAYILAN = ["G3_agresif", "G3_kritik", "G0", "G3_yumusak", "G4_kritik", "G6_agresif"]


class MerkezTakip(HedefTakip):
    """Asama asama merkez kaydedici. Davranis birebir korunur."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.gunluk = []
        self._c = {}
        gercek_ara = self.cekirdek.ara

        def ara_sarma(bgr, gri, merkez, boyut):
            # bu an: kf.tahmin(M) yapilmis, olcum henuz uygulanmamis
            self._c["kf_ongoru"] = np.asarray(merkez, np.float64).copy()
            yeni, psr = gercek_ara(bgr, gri, merkez, boyut)
            self._c["dcf"] = np.asarray(yeni, np.float64).copy()
            self._c["psr"] = float(psr)
            return yeni, psr

        self.cekirdek.ara = ara_sarma
        gercek_ego = self.cekirdek.ego_guncelle

        def ego_sarma(M):
            self._c["M"] = np.asarray(M, np.float64).copy()
            return gercek_ego(M)

        self.cekirdek.ego_guncelle = ego_sarma

    def _takip_adimi(self, bgr, gri):
        super()._takip_adimi(bgr, gri)
        self._c["kf_duzeltme"] = self.kf.konum.astype(np.float64)

    def _boyut_tazele(self, bgr):
        once = self.kf.konum.astype(np.float64)
        izl.rafine_kutu.kayit = []
        super()._boyut_tazele(bgr)
        self._c["tazele_once"] = once
        self._c["tazele_sonra"] = self.kf.konum.astype(np.float64)
        k = [x for x in izl.rafine_kutu.kayit if x["kutu"] is not None]
        self._c["rafine"] = np.asarray(k[-1]["kutu"], np.float64) if k else None

    def guncelle(self, bgr):
        onceki = None if self._onceki_merkez is None else self._onceki_merkez.copy()
        self._c = {}
        sonuc = super().guncelle(bgr)
        c = self._c
        M = c.get("M")
        ego = None
        if M is not None and onceki is not None:
            ego = M[:, :2] @ onceki + M[:, 2]        # asama 6
        self.gunluk.append({
            "kare_ic": self.kare,
            "durum": self.durum,
            "psr": c.get("psr", float(self.psr)),
            "aci": float(getattr(self.cekirdek, "aci", 0.0)),
            "aktif": bool(getattr(self.cekirdek, "aktif", False)),
            "boyut": self.boyut.astype(np.float64).copy(),
            "onceki": onceki,
            "ego": ego,
            "kf_ongoru": c.get("kf_ongoru"),
            "dcf": c.get("dcf"),
            "kf_duzeltme": c.get("kf_duzeltme"),
            "rafine": c.get("rafine"),
            "tazele_once": c.get("tazele_once"),
            "tazele_sonra": c.get("tazele_sonra"),
            "final": self.kf.konum.astype(np.float64),
        })
        return sonuc


def _rafine_sar():
    gercek = izl.rafine_kutu

    def sarma(bgr, merkez, boyut, *a, **k):
        r = gercek(bgr, merkez, boyut, *a, **k)
        sarma.kayit.append({"kutu": None if r is None else [float(v) for v in r]})
        return r

    sarma.kayit = []
    izl.rafine_kutu = sarma
    return gercek


def kos(senaryo, kok="data/gazebo"):
    kaynak = GazeboKaynak(kok=kok, senaryo=senaryo)
    gercek = _rafine_sar()
    ilk = ana.HedefTakip
    kutu = {}
    ana.HedefTakip = lambda *a, **k: kutu.setdefault("t", MerkezTakip(*a, **k))
    try:
        m = ana.kos(kaynak, pencere=False)
    finally:
        ana.HedefTakip = ilk
        izl.rafine_kutu = gercek
    tak = kutu["t"]
    g = tak.gunluk
    ofset = int(m["kare"]) - len(g)
    olcum = {r["kare"]: r for r in m.get("_olcum", [])}

    satir = []
    for i, r in enumerate(g):
        k = ofset + i
        gt = kaynak._kutu(kaynak.pozlar[k], kaynak.hedef_ad) if k < len(kaynak.pozlar) else None
        if gt is None or k not in olcum:
            continue
        gc = np.array([gt[0] + gt[2] / 2, gt[1] + gt[3] / 2])
        d = {"kare": k, "senaryo": senaryo, "psr": r["psr"], "aci": r["aci"],
             "aktif": r["aktif"], "durum": r["durum"],
             "w": float(r["boyut"][0]), "h": float(r["boyut"][1]),
             "gt_w": float(gt[2]), "gt_h": float(gt[3]),
             "gt": [float(gc[0]), float(gc[1])], "iou": float(olcum[k]["iou"])}
        for ad in ("onceki", "ego", "kf_ongoru", "dcf", "kf_duzeltme",
                   "tazele_once", "tazele_sonra", "final"):
            v = r[ad]
            d[ad] = None if v is None else [float(v[0]), float(v[1])]
        rf = r["rafine"]
        d["rafine"] = None if rf is None else [float(rf[0] + rf[2] / 2),
                                               float(rf[1] + rf[3] / 2)]
        d["rafine_wh"] = None if rf is None else [float(rf[2]), float(rf[3])]
        satir.append(d)
    return {"senaryo": senaryo, "ort_iou": float(m.get("ort_iou", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)), "satir": satir}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--senaryo", nargs="*", default=VARSAYILAN)
    ap.add_argument("--kok", default="data/gazebo")
    ap.add_argument("--json", default="cikti/merkez.json")
    a = ap.parse_args()
    out = {}
    for ad in a.senaryo:
        out[ad] = kos(ad, kok=a.kok)
        print(f"  {ad}: {len(out[ad]['satir'])} kare, IoU {out[ad]['ort_iou']:.3f}, "
              f"merkez {out[ad]['merkez_hata']:.2f} px", flush=True)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"yazildi: {a.json}")


if __name__ == "__main__":
    main()
