"""A3.9a - SALT OKUNUR teshis: hizli hedefte basarisizlik hangi asamada?

TAKIP/ HIC DEGISMEZ, takipciye hicbir sey beslenmez. Yalnizca gozlem +
KAYITLI degerlerden karsit-olgusal hesap.

OLCULEN KOD NOKTALARI (grep ile dogrulandi)
    izleyici.py:263  kf.tahmin(M)        -> ONGORU (ego + sabit hiz) burada olusur
    izleyici.py:305  tahmin = kf.konum   -> DCF ARAMA MERKEZI
    izleyici.py:306  cekirdek.ara(...)   -> DCF tepesi
    izleyici.py:308  sicrama = |yeni - tahmin|
    izleyici.py:309  maks_sicrama = max(6.0, 0.9 * boyut.max())
    izleyici.py:311  psr >= psr_kilit AND sicrama <= maks_sicrama  -> kabul
    cekirdekler.py:150-152 yama = boyut * dolgu(2.0)
    cekirdekler.py:328-329 tepe = merkez + (ix+dx - N//2) * w/N
        -> DCF'in gorebilecegi EN BUYUK yer degistirme = +-w/2 = +-boyut
           yani ARAMA YARICAPI x'te boyut_w, y'de boyut_h

KARSIT-OLGULAR (hicbiri takipciye uygulanmaz)
    H1  KF hizi yerine hedefin GERCEK goruntu hizi kullanilsaydi ongoru
        hatasi ne olurdu?   pred_H1 = M(onceki_final) + (gt_k - M(gt_{k-1}))
    H2  Merkez ayni kalirken yarICAP hedefi kapsayacak kadar buyuk olsaydi
        kac kare kurtarilirdi?  (GT pencerenin disinda mi?)
    H3  DCF tepesi GT kutusunun ICINDE oldugu halde sicrama kapisi
        reddediyor mu?

SINIFLAR
    A  GT arama penceresinin DISINDA
    B  GT icerde, tepe yanlis, ama H1 (dogru hiz) ongoru hatasini AZALTIRDI
    C  Tepe GT kutusunun icinde ama sicrama kapisi REDDETTI
    D  GT icerde, tepe yanlis ve H1 de duzeltmezdi -> baska asama

Kullanim: python3 -m gazebo.tani_a39a_h123
"""
import argparse
import json
import os

import numpy as np

import main as ana
from gazebo.tani_4o_dcf import _kaynak
from takip.izleyici import ARAMA, KAYIP, KILITLI, SUPHELI, HedefTakip

KAYNAKLAR = [("G7_agresif", "gazebo", "G7_agresif", "birincil"),
             ("G7_kritik", "gazebo", "G7_kritik", "birincil"),
             ("117/23", "visdrone", ("uav0000117_02622_v", 23), "gercek"),
             ("137/12", "visdrone", ("uav0000137_00458_v", 12), "gercek"),
             ("G0", "gazebo", "G0", "capa"),
             ("G3_agresif", "gazebo", "G3_agresif", "capa"),
             ("G3_kritik", "gazebo", "G3_kritik", "capa"),
             ("268/31", "visdrone", ("uav0000268_05773_v", 31), "yalnizca_rapor")]

DURUM_AD = {KILITLI: "KILITLI", SUPHELI: "SUPHELI", ARAMA: "ARAMA", KAYIP: "KAYIP"}


class IzTakip(HedefTakip):
    """Yalnizca gozlem; her sarmalayici gercek cagriyi AYNEN yapar."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []
        self._d = {}
        c = self.cekirdek
        g_ara = c.ara
        g_ego = self.ego.guncelle

        def ego_s(gri, kutu=None):
            M, gv = g_ego(gri, kutu)
            self._d["M"] = np.asarray(M, np.float64).copy()
            return M, gv

        def ara_s(bgr, gri, merkez, boyut):
            self._d["ara_merkez"] = np.asarray(merkez, np.float64).copy()
            self._d["ara_boyut"] = np.asarray(boyut, np.float64).copy()
            yeni, psr = g_ara(bgr, gri, merkez, boyut)
            self._d["dcf"] = np.asarray(yeni, np.float64).copy()
            self._d["psr"] = float(psr)
            # izleyici.py:308-309 ile AYNI hesap
            self._d["sicrama"] = float(np.linalg.norm(
                np.asarray(yeni) - np.asarray(merkez)))
            self._d["maks_sicrama"] = float(max(6.0, 0.9 * float(boyut.max())))
            return yeni, psr

        self.ego.guncelle = ego_s
        c.ara = ara_s

    def kilitle(self, bgr, kutu):
        r = super().kilitle(bgr, kutu)
        kf = self.kf
        g_tah = kf.tahmin

        def tah_s(M):
            g_tah(M)
            self._d["kf_ongoru"] = kf.konum.astype(np.float64)
            self._d["kf_hiz"] = kf.hiz.astype(np.float64)

        kf.tahmin = tah_s
        return r

    def guncelle(self, bgr):
        self._d = {}
        onc = None if self._onceki_merkez is None else \
            np.asarray(self._onceki_merkez, np.float64).copy()
        d0 = self.durum
        s = super().guncelle(bgr)
        d = dict(self._d)
        d["onceki_merkez"] = onc
        d["durum_once"] = d0
        d["durum_sonra"] = self.durum
        d["final"] = self.kf.konum.astype(np.float64)
        d["boyut"] = self.boyut.astype(np.float64).copy()
        self.iz.append(d)
        return s


def kos(ad, tur, arg, rol):
    ilk = ana.HedefTakip
    tut = {}
    ana.HedefTakip = lambda *a, **k: tut.setdefault("t", IzTakip(*a, **k))
    try:
        m = ana.kos(_kaynak(tur, arg), pencere=False)
    finally:
        ana.HedefTakip = ilk
    tak = tut["t"]
    ofset = int(m["kare"]) - len(tak.iz)
    td = m.get("t_drift")
    gt = {}
    for kare in _kaynak(tur, arg):
        if kare.gt is not None and kare.gorunur:
            b = kare.gt
            gt[kare.indeks] = (np.array([b[0] + b[2] / 2, b[1] + b[3] / 2]),
                               np.array([float(b[2]), float(b[3])]),
                               np.asarray(b, np.float64))
    iou_k = {r["kare"]: r["iou"] for r in m.get("_olcum") or []}

    satir = []
    for i, r in enumerate(tak.iz):
        k = ofset + i
        if k not in gt:
            continue
        gc, gwh, gb = gt[k]
        d = {"kare": k, "rol": rol,
             "durum_once": DURUM_AD.get(r["durum_once"]),
             "durum_sonra": DURUM_AD.get(r["durum_sonra"]),
             "drift_state": "once" if (td is None or k < td) else "sonra",
             "gt_x": float(gc[0]), "gt_y": float(gc[1]),
             "gt_w": float(gwh[0]), "gt_h": float(gwh[1]),
             "iou": iou_k.get(k),
             "boyut_w": float(r["boyut"][0]), "boyut_h": float(r["boyut"][1])}
        M, onc = r.get("M"), r.get("onceki_merkez")
        # 2) GT kareler arasi yer degistirme
        if (k - 1) in gt:
            gp = gt[k - 1][0]
            dd = gc - gp
            d["dx_gt"], d["dy_gt"] = float(dd[0]), float(dd[1])
            d["d_gt"] = float(np.linalg.norm(dd))
            if M is not None:
                # 3) ego telafili hedef OZ hareketi
                mgp = M[:, :2] @ gp + M[:, 2]
                oz = gc - mgp
                d["oz_dx"], d["oz_dy"] = float(oz[0]), float(oz[1])
                d["oz_d"] = float(np.linalg.norm(oz))
                if onc is not None:
                    # H1 karsit-olgusu: ongoru = M(onceki_final) + GERCEK oz hiz
                    ong = M[:, :2] @ onc + M[:, 2]
                    ph1 = ong + oz
                    d["H1_ongoru_hata"] = float(np.linalg.norm(ph1 - gc))
        # 4/5/6) KF ongorusu, hizi, ongoru hatasi
        if r.get("kf_ongoru") is not None:
            p = r["kf_ongoru"]
            d["pred_x"], d["pred_y"] = float(p[0]), float(p[1])
            d["pred_hata"] = float(np.linalg.norm(p - gc))
            d["pred_hata_x"] = float(p[0] - gc[0])
            d["pred_hata_y"] = float(p[1] - gc[1])
        if r.get("kf_hiz") is not None:
            v = r["kf_hiz"]
            d["vx"], d["vy"] = float(v[0]), float(v[1])
            d["v"] = float(np.linalg.norm(v))
        # 7/8) DCF arama merkezi ve YARICAPI
        if r.get("ara_merkez") is not None:
            am = r["ara_merkez"]
            ab = r["ara_boyut"]
            d["ara_x"], d["ara_y"] = float(am[0]), float(am[1])
            d["r_x"], d["r_y"] = float(ab[0]), float(ab[1])   # +-boyut
            e = gc - am
            d["gt_merkez_dx"], d["gt_merkez_dy"] = float(e[0]), float(e[1])
            d["gt_merkez_d"] = float(np.linalg.norm(e))
            # 11) GT pencerenin disinda mi (bilesen bazinda)
            d["pencere_disi"] = bool(abs(e[0]) > ab[0] or abs(e[1]) > ab[1])
            d["pencere_dolgu_x"] = float(abs(e[0]) / max(1e-9, ab[0]))
            d["pencere_dolgu_y"] = float(abs(e[1]) / max(1e-9, ab[1]))
        # 9/10) DCF tepesi
        if r.get("dcf") is not None:
            pk = r["dcf"]
            d["peak_x"], d["peak_y"] = float(pk[0]), float(pk[1])
            d["peak_gt_d"] = float(np.linalg.norm(pk - gc))
            d["peak_gt_icinde"] = bool(gb[0] <= pk[0] <= gb[0] + gb[2]
                                       and gb[1] <= pk[1] <= gb[1] + gb[3])
        # 12/13) sicrama kapisi
        for nm in ("sicrama", "maks_sicrama", "psr"):
            if r.get(nm) is not None:
                d[nm] = r[nm]
        if "sicrama" in d and "maks_sicrama" in d:
            d["sicrama_reddi"] = bool(d["sicrama"] > d["maks_sicrama"])
        satir.append(d)

    return {"ad": ad, "rol": rol, "ort_iou": float(m.get("ort_iou", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "t_drift": td, "satir": satir}


def sinifla(r):
    """A/B/C/D ayrimi - hepsi KARSILASTIRMA, yeni esik yok."""
    s = [x for x in r["satir"]
         if x["durum_once"] in ("KILITLI", "SUPHELI") and "pencere_disi" in x]
    c = {"A": [], "B": [], "C": [], "D": [], "OK": []}
    for x in s:
        peak_ok = x.get("peak_gt_icinde", False)
        if x["pencere_disi"]:
            c["A"].append(x)
        elif peak_ok and x.get("sicrama_reddi"):
            c["C"].append(x)
        elif peak_ok:
            c["OK"].append(x)
        elif ("H1_ongoru_hata" in x and "pred_hata" in x
              and x["H1_ongoru_hata"] < x["pred_hata"]):
            c["B"].append(x)
        else:
            c["D"].append(x)
    return c, len(s)


def ozet(r):
    print(f"\n== {r['ad']} ({r['rol']}) == IoU {r['ort_iou']:.4f} "
          f"kilit {100*r['kilit_orani']:.1f}% drift {r['t_drift']}")
    s = [x for x in r["satir"] if "d_gt" in x and "r_x" in x]
    if not s:
        print("   (olculebilir kare yok)")
        return
    dg = np.array([x["d_gt"] for x in s])
    oz = np.array([x.get("oz_d", np.nan) for x in s])
    rx = np.array([x["r_x"] for x in s])
    px = np.array([x["pencere_dolgu_x"] for x in s])
    py = np.array([x["pencere_dolgu_y"] for x in s])
    pe = np.array([x.get("pred_hata", np.nan) for x in s])
    v = np.array([x.get("v", np.nan) for x in s])
    print(f"   d_gt (kamera dahil) med {np.median(dg):6.2f} maks {dg.max():6.2f} px/kare"
          f"  |  hedef OZ hareketi med {np.nanmedian(oz):5.2f} maks {np.nanmax(oz):6.2f}")
    print(f"   DCF yaricapi (boyut) med {np.median(rx):6.2f} px"
          f"  |  pencere doluluk x med {np.median(px):.2f} maks {px.max():.2f}"
          f"  y med {np.median(py):.2f} maks {py.max():.2f}")
    print(f"   ongoru hatasi med {np.nanmedian(pe):5.2f} maks {np.nanmax(pe):7.2f}"
          f"  |  KF hizi med {np.nanmedian(v):5.2f} maks {np.nanmax(v):6.2f}")
    c, n = sinifla(r)
    if n:
        print(f"   SINIF ({n} KILITLI/SUPHELI kare):", {k: len(v_) for k, v_ in c.items()})
        for k in ("A", "B", "C", "D"):
            if c[k]:
                ilk = min(x["kare"] for x in c[k])
                print(f"      {k}: {len(c[k]):3d} kare (%{100*len(c[k])/n:4.1f}), ilk kare {ilk}")
    # H1/H2/H3 karsit-olgu ozeti
    h1a = np.array([x["pred_hata"] for x in s if "H1_ongoru_hata" in x and "pred_hata" in x])
    h1b = np.array([x["H1_ongoru_hata"] for x in s if "H1_ongoru_hata" in x and "pred_hata" in x])
    if len(h1a):
        print(f"   H1: ongoru hatasi med {np.median(h1a):5.2f} -> gercek hizla "
              f"{np.median(h1b):5.2f} px  (iyilesen kare %{100*np.mean(h1b<h1a):.0f})")
    print(f"   H2: GT pencere disinda {sum(x['pencere_disi'] for x in s)}/{len(s)} kare")
    h3 = [x for x in s if x.get("peak_gt_icinde") and x.get("sicrama_reddi")]
    print(f"   H3: tepe GT icinde ama sicrama reddi {len(h3)}/{len(s)} kare")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/a39a_h123.json")
    a = ap.parse_args()
    out = {}
    for ad, tur, arg, rol in KAYNAKLAR:
        r = kos(ad, tur, arg, rol)
        out[ad] = r
        ozet(r)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"\nyazildi: {a.json}")


if __name__ == "__main__":
    main()
