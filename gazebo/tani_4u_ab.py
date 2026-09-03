"""Deney 4U - A/B olcum kosucusu (tek kapi degisikligi).

Takipciyi kosturur ama HICBIR SEY DEGISTIRMEZ; yalnizca gozlem yapar.
Ayni arac hem A (baseline) hem B (kapi degisikligi) durumunda kosulur;
degisiklik dosyada yapilir, bu arac degismez.

Olculenler: IoU, merkez hatasi, drift, kilit orani, yanlis kilit (4L tanimi),
PSR, boyut w/h serisi, rafine kabul/red orani, boyut/GT orani ve
"boyut donmasi" (boyutun degismeden gectigi en uzun ardisik kare serisi).

Kullanim: python3 -m gazebo.tani_4u_ab --etiket A
"""
import argparse
import json
import os

import numpy as np

import main as ana
import takip.izleyici as izl
from gazebo.tani_4o_dcf import _kaynak
from takip.izleyici import KILITLI, HedefTakip

KAYNAKLAR = [("117/23", "visdrone", ("uav0000117_02622_v", 23), "birincil"),
             ("137/12", "visdrone", ("uav0000137_00458_v", 12), "birincil"),
             ("305/5", "visdrone", ("uav0000305_00000_v", 5), "destek"),
             ("G3_agresif", "gazebo", "G3_agresif", "capa"),
             ("G3_kritik", "gazebo", "G3_kritik", "capa"),
             ("G0", "gazebo", "G0", "capa"),
             ("G6_agresif", "gazebo", "G6_agresif", "ayri_soru")]


class OlcTakip(HedefTakip):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []
        self._tz = None

    def _boyut_tazele(self, bgr):
        izl.rafine_kutu.son = "yok"
        b0 = self.boyut.copy()
        super()._boyut_tazele(bgr)
        self._tz = {"kabul": izl.rafine_kutu.son is not None
                    and izl.rafine_kutu.son != "yok",
                    "cagri": izl.rafine_kutu.son != "yok",
                    "degisti": bool(not np.allclose(b0, self.boyut))}

    def guncelle(self, bgr):
        self._tz = None
        b0 = self.boyut.copy()
        s = super().guncelle(bgr)
        self.iz.append({"boyut": self.boyut.copy(), "psr": float(self.psr),
                        "durum": self.durum, "yk": int(self.yanlis_kilit),
                        "tz": self._tz,
                        "boyut_ayni": bool(np.allclose(b0, self.boyut))})
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


def olc(ad, tur, arg, rol):
    gercek = _sar()
    ilk = ana.HedefTakip
    tut = {}
    ana.HedefTakip = lambda *a, **k: tut.setdefault("t", OlcTakip(*a, **k))
    try:
        m = ana.kos(_kaynak(tur, arg), pencere=False)
    finally:
        ana.HedefTakip = ilk
        izl.rafine_kutu = gercek
    tak = tut["t"]
    ofset = int(m["kare"]) - len(tak.iz)
    olcum = m.get("_olcum") or []
    gt = {}
    for kare in _kaynak(tur, arg):
        if kare.gt is not None and kare.gorunur:
            gt[kare.indeks] = (float(kare.gt[2]), float(kare.gt[3]))

    kl = [r for r in olcum if r["durum"] == KILITLI]
    yk = [r["iou"] == 0.0 for r in kl]
    ser, cur = [], 0
    for r in tak.iz:
        cur = cur + 1 if r["boyut_ayni"] else 0
        ser.append(cur)
    tz = [r["tz"] for r in tak.iz if r["tz"] and r["tz"]["cagri"]]
    oran = []
    for i, r in enumerate(tak.iz):
        k = ofset + i
        if k in gt:
            oran.append([r["boyut"][0] / max(1e-9, gt[k][0]),
                         r["boyut"][1] / max(1e-9, gt[k][1])])
    o = np.array(oran) if oran else np.ones((1, 2))
    psr = [r["psr"] for r in tak.iz if r["durum"] in (KILITLI,) and r["psr"] > 0]
    return {"ad": ad, "rol": rol,
            "ort_iou": float(m.get("ort_iou", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "t_drift": m.get("t_drift"),
            "kesinti": int(m.get("kesinti", 0)) if "kesinti" in m else None,
            "n_kilitli": len(kl), "yk_kare": int(sum(yk)),
            "yk_orani": float(sum(yk)) / max(1, len(kl)),
            "yanlis_kilit_sayaci": int(tak.iz[-1]["yk"]) if tak.iz else 0,
            "psr_med": float(np.median(psr)) if psr else None,
            "psr_p5": float(np.percentile(psr, 5)) if psr else None,
            "tazele_cagri": len(tz),
            "tazele_kabul": int(sum(t["kabul"] for t in tz)),
            "tazele_red": int(sum(not t["kabul"] for t in tz)),
            "kabul_orani": float(np.mean([t["kabul"] for t in tz])) if tz else None,
            "boyut_don_maks": int(max(ser)) if ser else 0,
            "boyut_don_ort": float(np.mean(ser)) if ser else 0.0,
            "oran_log_ort": float(np.mean(np.abs(np.log(o)))),
            "oran_w_son": float(o[-1][0]), "oran_h_son": float(o[-1][1]),
            "oran_w_maks": float(o[:, 0].max()), "oran_h_maks": float(o[:, 1].max()),
            "boyut_son": [float(v) for v in tak.iz[-1]["boyut"]] if tak.iz else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiket", required=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    yol = a.json or f"cikti/4u_{a.etiket}.json"
    out = {}
    for ad, tur, arg, rol in KAYNAKLAR:
        r = olc(ad, tur, arg, rol)
        out[ad] = r
        print("%-12s %-9s IoU %.6f merkez %7.3f kilit %.4f drift %-5s YK %3d/%3d "
              "kabul %s tazele %d/%d don_maks %3d oran|log| %.3f" % (
                  ad, rol, r["ort_iou"], r["merkez_hata"], r["kilit_orani"],
                  r["t_drift"], r["yk_kare"], r["n_kilitli"],
                  "%.2f" % r["kabul_orani"] if r["kabul_orani"] is not None else " -- ",
                  r["tazele_kabul"], r["tazele_cagri"], r["boyut_don_maks"],
                  r["oran_log_ort"]), flush=True)
    os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
    with open(yol, "w") as f:
        json.dump(out, f, indent=1)
    print("yazildi:", yol)


if __name__ == "__main__":
    main()
