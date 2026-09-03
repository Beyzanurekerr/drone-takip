"""Deney 4O - salt okunur: DCF olcumunun 141->142 gecisinde nerede ayristigi.

TAKIP/ HIC DEGISMEZ. Gercek `RenkDcfCekirdek` aynen calisir; sarmalayicilar
gercek cagriyi yapip sonucu aynen dondurur, yaninda AYNI matematigin bir
kopyasi kosturulup yanit haritasinin ozetleri okunur. Kopya ile gercegin
(yeni, psr) ciktisi her cagrida karsilastirilir (sadakat denetimi).

DCF BORU HATTI (cekirdekler.py, grep ile dogrulandi)
  ara(bgr, gri, merkez, boyut)                    satir 193
    aktif = |dteta| >= dteta_esik  or  aci != 0   satir 196
    aktif degilse: tek aday, aci = 0              satir 199-201
    aktif ise: uc aday (n-1, n, n+1) x aci_adim, en yuksek PSR secilir
  _yanit(bgr, merkez, boyut, aci)                 satir 187
    kan, (w, h) = _kanallar(...)   w = boyut[0]*dolgu(2.0), h = boyut[1]*2.0
    F = fft2(kan);  r = real(ifft2( sum(A*F) / (B + eps) ))
    return _tepe(r, N, merkez, w, h)
  _tepe(r, N, merkez, w, h)                       satir 321
    (iy, ix) = argmax(r);  parabolik alt-piksel dx, dy
    PSR: tepe cevresinde 11x11 dislanir, kalan yan lob
    yeni = merkez + ((ix+dx) - N//2) * w/N ,  merkez + ((iy+dy) - N//2) * h/N

ONEMLI OLCEK: bir izgara hucresi x'te w/N = boyut[0]*2/32 = boyut[0]/16 px.
boyut[0]=59 -> 3.69 px/hucre;  boyut[1]=36 -> 2.25 px/hucre.
Yani 1.2 px'lik bir artik farki x'te ~0.33 HUCRE'dir - tamsayi argmax degil,
alt-piksel bolgesi. Bu yuzden tamsayi tepe ile alt-piksel ayri raporlanir.

ARAMA MERKEZI = HARITA MERKEZI: `merkez` her zaman izgara (N//2, N//2)'ye
duser (yukaridaki formul). "Tepenin arama merkezine uzakligi" ile "tepenin
harita merkezine uzakligi" AYNI buyukluktur; ayri bir koordinat donusumu yok.

Kullanim: python3 -m gazebo.tani_4o_dcf
"""
import argparse
import json
import os

import numpy as np

import main as ana
from kaynak import kaynak_olustur
from takip.izleyici import HedefTakip
from veri.gazebo import GazeboKaynak

GAZEBO_KOK = "data/gazebo"
VISDRONE_KOK = "data/datasets/visdrone_vid"

HEDEFLER = [("G6_agresif_durakli", "gazebo", "G6_agresif_durakli"),
            ("G6_agresif", "gazebo", "G6_agresif"),
            ("117/23", "visdrone", ("uav0000117_02622_v", 23)),
            ("137/12", "visdrone", ("uav0000137_00458_v", 12))]

PENCERE = (130, 148)          # 4M'nin kritik penceresi
ARSIV = (134, 152)            # A/B ve yama arsivi (capraz cozumleme icin)


def tepe_ozet(r, N):
    """`_tepe` ile AYNI matematik + harita ozetleri. Karar esigi icat edilmez."""
    iy, ix = np.unravel_index(np.argmax(r), r.shape)
    tepe = float(r[iy, ix])
    dx = dy = 0.0
    if 0 < ix < N - 1:
        l, sag = float(r[iy, ix - 1]), float(r[iy, ix + 1])
        d = l - 2 * tepe + sag
        if abs(d) > 1e-9:
            dx = 0.5 * (l - sag) / d
    if 0 < iy < N - 1:
        u, alt = float(r[iy - 1, ix]), float(r[iy + 1, ix])
        d = u - 2 * tepe + alt
        if abs(d) > 1e-9:
            dy = 0.5 * (u - alt) / d
    m = np.ones_like(r, bool)
    m[max(0, iy - 5):iy + 6, max(0, ix - 5):ix + 6] = False
    yan = r[m]
    psr = float((tepe - yan.mean()) / (yan.std() + 1e-5))
    # ikinci tepe = dislanan blogun DISINDAKI en buyuk deger (ayni maske)
    rm = np.where(m, r, -np.inf)
    iy2, ix2 = np.unravel_index(np.argmax(rm), rm.shape)
    ikinci = float(rm[iy2, ix2])
    return {"ix": int(ix), "iy": int(iy), "tepe": tepe, "dx": float(dx),
            "dy": float(dy), "psr": psr,
            "ix2": int(ix2), "iy2": int(iy2), "ikinci": ikinci,
            "tepe_ikinci_oran": tepe / ikinci if ikinci > 0 else float("inf"),
            "yan_ort": float(yan.mean()), "yan_std": float(yan.std()),
            # tanimlayici (karar esigi degil): tepenin yariisindan buyuk hucre sayisi
            "hucre_yarim_ustu": int((r > 0.5 * tepe).sum()),
            "tepe_merkez_hucre": float(np.hypot(ix - N // 2, iy - N // 2))}


def yanit_haritasi(A, B, kan, eps):
    F = np.fft.fft2(kan, axes=(1, 2))
    return np.real(np.fft.ifft2((A * F).sum(0) / (B + eps)))


class IzDcf(HedefTakip):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iz = []
        self.arsiv = {}
        self._d = {}
        c = self.cekirdek
        g_kan, g_yanit, g_ara, g_ogr, g_egoc = (
            c._kanallar, c._yanit, c.ara, c.ogren, c.ego_guncelle)
        g_ego = self.ego.guncelle

        def ego_s(gri, kutu=None):
            M, gv = g_ego(gri, kutu)
            self._d["M"] = np.asarray(M, np.float64).copy()
            self._d["ego_guven"] = float(gv)
            return M, gv

        def egoc_s(M):
            r = g_egoc(M)
            self._d["dteta"] = float(c.dteta)
            return r

        def kan_s(bgr, merkez, boyut, aci=None):
            kan, wh = g_kan(bgr, merkez, boyut, aci)
            self._d["son_kan"] = kan.copy()
            self._d["son_wh"] = (int(wh[0]), int(wh[1]))
            return kan, wh

        def yanit_s(bgr, merkez, boyut, aci):
            A0 = None if c.A is None else c.A.copy()
            B0 = None if c.B is None else c.B.copy()
            yeni, psr = g_yanit(bgr, merkez, boyut, aci)
            kan = self._d.get("son_kan")
            o = {"aci": float(aci)}
            if A0 is not None and kan is not None:
                r = yanit_haritasi(A0, B0, kan, c.eps)
                o.update(tepe_ozet(r, c.N))
                w, h = self._d["son_wh"]
                o["w"], o["h"] = w, h
                o["olcek_x"], o["olcek_y"] = w / c.N, h / c.N
                yeni2 = (merkez[0] + ((o["ix"] + o["dx"]) - c.N // 2) * w / c.N,
                         merkez[1] + ((o["iy"] + o["dy"]) - c.N // 2) * h / c.N)
                o["sadik"] = bool(np.allclose(np.asarray(yeni2),
                                              np.asarray(yeni), atol=1e-6)
                                  and abs(o["psr"] - psr) < 1e-4)
            self._d.setdefault("adaylar", []).append(o)
            return yeni, psr

        def ara_s(bgr, gri, merkez, boyut):
            self._d["ara_merkez"] = np.asarray(merkez, np.float64).copy()
            self._d["ara_boyut"] = np.asarray(boyut, np.float64).copy()
            self._d["aci_once"] = float(c.aci)
            self._d["adaylar"] = []
            yeni, psr = g_ara(bgr, gri, merkez, boyut)
            self._d["aktif"] = bool(c.aktif)
            self._d["aci_sonra"] = float(c.aci)
            self._d["dcf"] = np.asarray(yeni, np.float64).copy()
            self._d["psr"] = float(psr)
            self._d["kan_ara"] = None if self._d.get("son_kan") is None \
                else self._d["son_kan"].copy()
            self._d["A_ara"] = None if c.A is None else c.A.copy()
            self._d["B_ara"] = None if c.B is None else c.B.copy()
            return yeni, psr

        def ogr_s(bgr, gri, merkez, boyut, lr=None):
            A0 = None if c.A is None else c.A.copy()
            B0 = None if c.B is None else c.B.copy()
            g_ogr(bgr, gri, merkez, boyut, lr)
            self._d["lr"] = float(c.lr if lr is None else lr)
            if A0 is not None:
                self._d["A_norm"] = float(np.linalg.norm(c.A))
                self._d["B_norm"] = float(np.linalg.norm(c.B))
                self._d["dA"] = float(np.linalg.norm(c.A - A0)
                                      / max(1e-12, np.linalg.norm(c.A)))
                self._d["dB"] = float(np.linalg.norm(c.B - B0)
                                      / max(1e-12, np.linalg.norm(c.B)))

        self.ego.guncelle = ego_s
        c._kanallar, c._yanit, c.ara, c.ogren, c.ego_guncelle = (
            kan_s, yanit_s, ara_s, ogr_s, egoc_s)

    def kilitle(self, bgr, kutu):
        r = super().kilitle(bgr, kutu)
        kf = self.kf
        g_tah, g_duz = kf.tahmin, kf.duzelt

        def tah_s(M):
            g_tah(M)
            self._d["kf_ongoru"] = kf.konum.astype(np.float64)

        def duz_s(z, r_carpan=1.0):
            g_duz(z, r_carpan)
            self._d["r_carpan"] = float(r_carpan)

        kf.tahmin, kf.duzelt = tah_s, duz_s
        return r

    def guncelle(self, bgr):
        self._d = {}
        onc = None if self._onceki_merkez is None else \
            np.asarray(self._onceki_merkez, np.float64).copy()
        s = super().guncelle(bgr)
        d = dict(self._d)
        d["onceki_merkez"] = onc
        d["final"] = self.kf.konum.astype(np.float64)
        d["kf_hiz"] = self.kf.hiz.astype(np.float64)
        d["boyut"] = self.boyut.astype(np.float64).copy()
        d["durum"] = self.durum
        d["benzerlik"] = float(self.benzerlik)
        d["hareketli"] = bool(self._hareketli)
        d["kare_ic"] = self.kare
        self.iz.append(d)
        return s


def _kaynak(tur, arg):
    if tur == "gazebo":
        return GazeboKaynak(kok=GAZEBO_KOK, senaryo=arg)
    dz, tid = arg
    return kaynak_olustur("visdrone", veri_kok=VISDRONE_KOK, dizi=dz,
                          track_id=tid, hedef_genislik=960)


def _gt(tur, arg):
    g = {}
    for kare in _kaynak(tur, arg):
        if kare.gt is not None and kare.gorunur:
            b = kare.gt
            g[kare.indeks] = np.array([b[0] + b[2] / 2, b[1] + b[3] / 2])
    return g


def kos(ad, tur, arg):
    gt = _gt(tur, arg)
    ilk = ana.HedefTakip
    tut = {}
    ana.HedefTakip = lambda *a, **k: tut.setdefault("t", IzDcf(*a, **k))
    try:
        m = ana.kos(_kaynak(tur, arg), pencere=False)
    finally:
        ana.HedefTakip = ilk
    tak = tut["t"]
    ofset = int(m["kare"]) - len(tak.iz)
    satir, arsiv = [], {}
    for i, r in enumerate(tak.iz):
        k = ofset + i
        d = {"kare": k, "durum": r["durum"], "psr": r.get("psr"),
             "aktif": r.get("aktif"), "dteta": r.get("dteta"),
             "aci_once": r.get("aci_once"), "aci_sonra": r.get("aci_sonra"),
             "n_aday": len(r.get("adaylar") or []),
             "lr": r.get("lr"), "dA": r.get("dA"), "dB": r.get("dB"),
             "A_norm": r.get("A_norm"), "B_norm": r.get("B_norm"),
             "benzerlik": r["benzerlik"], "hareketli": r["hareketli"],
             "w": float(r["boyut"][0]), "h": float(r["boyut"][1]),
             "kf_hiz": float(np.linalg.norm(r["kf_hiz"])),
             "ego_guven": r.get("ego_guven"), "r_carpan": r.get("r_carpan")}
        ad_l = r.get("adaylar") or []
        if ad_l:
            # secilen aday = aci_sonra ile eslesen
            sec = ad_l[0]
            for c in ad_l:
                if abs(c["aci"] - (r.get("aci_sonra") or 0.0)) < 1e-9:
                    sec = c
            d["harita"] = sec
            d["sadik"] = bool(sec.get("sadik", True))
        for ad_k, v in (("ara_merkez", "ara_merkez"), ("kf_ongoru", "kf_ongoru"),
                        ("dcf", "dcf"), ("final", "final"),
                        ("onceki_merkez", "onceki_merkez")):
            if r.get(ad_k) is not None:
                d[v + "_x"] = float(r[ad_k][0])
                d[v + "_y"] = float(r[ad_k][1])
        M, onc = r.get("M"), r.get("onceki_merkez")
        if M is not None and onc is not None:
            ong = M[:, :2] @ onc + M[:, 2]
            d["ego_tasima_x"] = float((ong - onc)[0])
            d["ego_tasima_y"] = float((ong - onc)[1])
        if k in gt:
            g = gt[k]
            d["gt_x"], d["gt_y"] = float(g[0]), float(g[1])
            kp = k - 1
            if kp in gt and M is not None:
                bg = (M[:, :2] @ gt[kp] + M[:, 2]) - g
                d["ego_artik_x"], d["ego_artik_y"] = float(bg[0]), float(bg[1])
        satir.append(d)
        if ARSIV[0] <= k <= ARSIV[1] and r.get("A_ara") is not None:
            arsiv[k] = {"A": r["A_ara"], "B": r["B_ara"], "kan": r["kan_ara"],
                        "merkez": r["ara_merkez"], "boyut": r["ara_boyut"]}
    return {"ad": ad, "ort_iou": float(m.get("ort_iou", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "t_drift": m.get("t_drift"), "satir": satir,
            "eps": float(tak.cekirdek.eps), "N": int(tak.cekirdek.N)}, arsiv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/dcf_4o.json")
    ap.add_argument("--npz", default="cikti/dcf_4o_arsiv.npz")
    a = ap.parse_args()
    out, ars = {}, {}
    for ad, tur, arg in HEDEFLER:
        r, arsiv = kos(ad, tur, arg)
        out[ad] = r
        n_sad = sum(1 for x in r["satir"] if x.get("sadik") is False)
        print(f"== {ad} == IoU {r['ort_iou']:.3f} kilit {100*r['kilit_orani']:.1f}% "
              f"drift {r['t_drift']}  sadakat ihlali {n_sad}", flush=True)
        for k, v in arsiv.items():
            for nm, arr in v.items():
                ars[f"{ad}|{k}|{nm}"] = np.asarray(arr)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    np.savez_compressed(a.npz, **ars)
    print(f"yazildi: {a.json}, {a.npz}")


if __name__ == "__main__":
    main()
