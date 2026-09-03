"""Deney 4N - salt okunur: `rafine_kutu` NEDEN None donuyor?

TAKIP/ HIC DEGISMEZ. `takip.tespit.rafine_kutu` GERCEK haliyle cagrilir ve
sonucu aynen dondurulur; yaninda ayni matematigin ADIM ADIM ISARETLENMIS bir
KOPYASI kosturulup hangi kosulun ilk kez basarisiz oldugu okunur. Kopya ile
gercegin None/None-degil hukmu her cagrida karsilastirilir (sadakat denetimi).
`rafine_kutu` saf bir fonksiyondur (durum tutmaz), bu yuzden iki kez cagrilmasi
davranisi degistirmez - koda hicbir dokunus yok.

`rafine_kutu`'nun None dondurebilecegi TUM yollar (tespit.py:87-134):
  R1  n < 2                          satir 108  hic baglantili bilesen yok
  R2  merkez bos ve lbl tumden bos   satir 114  (n>=2 iken ULASILAMAZ)
  R3  merkez bos, en yakin bilesen   satir 117  (0.35*max(boyut))^2 + 4'ten uzak
  R4  oran.mean() araligi disinda    satir 122  0.35 < mean(bw/W, bh/H) < 2.6
  R5  sec.sum() < 1                  satir 129  (ULASILAMAZ: et bileseni dolu)
  R6  renk mesafesi > renk_tol       satir 132  |ort_renk - imza.renk| > 60
  (ayrica cv2 istisnasi -> ayri kaydedilir)

Cagri noktasi: izleyici.py:561 `_boyut_tazele`
  rafine_kutu(bgr, kf.konum, boyut, hedef_renk=self.imza.renk)
  -> buyutme=3.0, min_esik=16.0, renk_tol=60.0 (varsayilanlar)

Kullanim: python3 -m gazebo.tani_4n_rafine
"""
import argparse
import json
import os

import cv2
import numpy as np

import main as ana
import takip.izleyici as izl
from kaynak import kaynak_olustur
from takip.izleyici import HedefTakip
from veri.gazebo import GazeboKaynak

GAZEBO_KOK = "data/gazebo"
VISDRONE_KOK = "data/datasets/visdrone_vid"

HEDEFLER = [("G6_agresif_durakli", "gazebo", "G6_agresif_durakli"),
            ("G6_agresif", "gazebo", "G6_agresif"),
            ("117/23", "visdrone", ("uav0000117_02622_v", 23)),
            ("137/12", "visdrone", ("uav0000137_00458_v", 12))]

PENCERE = (120, 180)


def isaretli_rafine(bgr, merkez, boyut, buyutme=3.0, min_esik=16.0,
                    hedef_renk=None, renk_tol=60.0):
    """tespit.rafine_kutu'nun SATIR SATIR AYNI kopyasi + hangi kosulun
    kestigi. Tek fark: erken donuslerde neden ve ara buyuklukler kaydedilir."""
    o = {"neden": None}
    cx, cy = float(merkez[0]), float(merkez[1])
    w = max(7, int(round(boyut[0] * buyutme)) | 1)
    h = max(7, int(round(boyut[1] * buyutme)) | 1)
    o["pencere_wh"] = [w, h]
    try:
        pen = cv2.getRectSubPix(bgr, (w, h), (cx, cy)).astype(np.float32)
    except cv2.error as e:
        o["neden"] = "CV_HATA_getRectSubPix"
        o["hata"] = str(e)[:120]
        return None, o
    med = np.median(pen.reshape(-1, 3), 0)
    o["pencere_medyan"] = [float(v) for v in med]
    d = np.linalg.norm(pen - med, axis=2)
    p82 = float(np.percentile(d, 82))
    esik = max(min_esik, p82)
    o["p82"] = p82
    o["esik"] = float(esik)
    o["esik_taban_mi"] = bool(p82 <= min_esik)      # min_esik mi bagladi?
    m = (d > esik).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    o["maske_doluluk"] = float(m.mean())

    n, lbl, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    o["n_bilesen"] = int(n)
    if n < 2:
        o["neden"] = "R1_bilesen_yok"
        return None, o
    ky, kx = h // 2, w // 2
    et = lbl[ky, kx]
    o["merkez_etiket"] = int(et)
    if et == 0:
        ys, xs = np.nonzero(lbl)
        if len(ys) == 0:
            o["neden"] = "R2_lbl_bos"
            return None, o
        i = np.argmin((ys - ky) ** 2 + (xs - kx) ** 2)
        d2 = float((ys[i] - ky) ** 2 + (xs[i] - kx) ** 2)
        lim = float((0.35 * max(boyut)) ** 2 + 4)
        o["merkez_uzaklik2"] = d2
        o["merkez_limit2"] = lim
        if d2 > lim:
            o["neden"] = "R3_merkez_uzak"
            return None, o
        et = lbl[ys[i], xs[i]]
    x, y, bw, bh, alan = stats[et]
    o["bilesen"] = [int(x), int(y), int(bw), int(bh), int(alan)]
    oran = np.array([bw, bh], np.float32) / np.maximum(boyut, 1.0)
    o["oran_w"], o["oran_h"] = float(oran[0]), float(oran[1])
    o["oran_ort"] = float(oran.mean())
    if not (0.35 < oran.mean() < 2.6):
        o["neden"] = "R4_oran"
        return None, o
    if hedef_renk is not None:
        sec = (lbl[y:y + bh, x:x + bw] == et)
        if sec.sum() < 1:
            o["neden"] = "R5_sec_bos"
            return None, o
        ort = pen[y:y + bh, x:x + bw][sec].mean(0)
        mes = float(np.linalg.norm(ort - np.asarray(hedef_renk, np.float32)))
        o["renk_mesafe"] = mes
        o["bilesen_renk"] = [float(v) for v in ort]
        o["hedef_renk"] = [float(v) for v in np.asarray(hedef_renk, np.float32)]
        if mes > renk_tol:
            o["neden"] = "R6_renk"
            return None, o
    o["neden"] = "OK"
    return np.array([cx - w / 2 + x, cy - h / 2 + y, bw, bh], np.float32), o


class RafineTakip(HedefTakip):
    """Yalnizca gozlem: her `_boyut_tazele` cagrisini kare numarasiyla etiketler."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.kayit = []
        self._kare_ic = 0

    def _boyut_tazele(self, bgr):
        izl.rafine_kutu.son = None
        b0 = self.boyut.copy()
        merkez = self.kf.konum.copy()
        renk = None if self.imza.renk is None else self.imza.renk.copy()
        super()._boyut_tazele(bgr)
        o = izl.rafine_kutu.son or {}
        o = dict(o)
        o["kare_ic"] = self._kare_ic
        o["boyut_w"], o["boyut_h"] = float(b0[0]), float(b0[1])
        o["merkez"] = [float(merkez[0]), float(merkez[1])]
        o["imza_renk"] = None if renk is None else [float(v) for v in renk]
        o["boyut_degisti"] = float(np.linalg.norm(self.boyut - b0))
        self.kayit.append(o)

    def guncelle(self, bgr):
        self._kare_ic = self.kare + 1
        return super().guncelle(bgr)


def _sar():
    """Gercek rafine_kutu AYNEN cagrilir; kopya yalnizca teshis icin kosar."""
    gercek = izl.rafine_kutu

    def s(bgr, merkez, boyut, *a, **k):
        r = gercek(bgr, merkez, boyut, *a, **k)
        try:
            r2, o = isaretli_rafine(bgr, merkez, boyut, *a, **k)
        except Exception as e:                       # teshis asla kosumu bozmasin
            o = {"neden": "TESHIS_HATASI", "hata": str(e)[:120]}
            r2 = None
        o["gercek_none"] = r is None
        o["kopya_none"] = r2 is None
        o["sadik"] = (r is None) == (r2 is None)
        if r is not None and r2 is not None:
            o["sadik"] = bool(np.allclose(np.asarray(r), np.asarray(r2)))
        s.son = o
        return r

    s.son = None
    izl.rafine_kutu = s
    return gercek


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
            g[kare.indeks] = [float(v) for v in kare.gt]
    return g


def kos(ad, tur, arg):
    gt = _gt(tur, arg)
    gercek = _sar()
    ilk = ana.HedefTakip
    tut = {}
    ana.HedefTakip = lambda *a, **k: tut.setdefault("t", RafineTakip(*a, **k))
    try:
        m = ana.kos(_kaynak(tur, arg), pencere=False)
    finally:
        ana.HedefTakip = ilk
        izl.rafine_kutu = gercek
    tak = tut["t"]
    ofset = int(m["kare"]) - tak.kare          # kare_ic -> gercek kare
    for o in tak.kayit:
        k = o["kare_ic"] + ofset
        o["kare"] = k
        if k in gt:
            b = gt[k]
            o["gt"] = b
            o["gt_w"], o["gt_h"] = b[2], b[3]
            bl = o.get("bilesen")
            if bl is not None and o.get("merkez") is not None:
                pw, ph = o["pencere_wh"]
                cx, cy = o["merkez"]
                # bilesenin GORUNTU koordinatlarindaki kutusu
                cb = [cx - pw / 2 + bl[0], cy - ph / 2 + bl[1], bl[2], bl[3]]
                o["bilesen_kutu"] = cb
                o["bilesen_gt_iou"] = float(ana.iou(
                    np.asarray(cb, np.float32), np.asarray(b, np.float32)))
                o["bilesen_alan_orani"] = float(bl[4]) / max(1.0, b[2] * b[3])
                o["gt_pencere_orani"] = float(b[2] * b[3]) / max(1.0, pw * ph)
    return {"ad": ad, "ort_iou": float(m.get("ort_iou", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "t_drift": m.get("t_drift"), "kayit": tak.kayit}


def ozet(r, a, b):
    print(f"\n--- {r['ad']}  kare {a}..{b}  (IoU {r['ort_iou']:.3f}) ---")
    print("kare  neden            n  doluluk  p82  esik | oran_w oran_h ort |"
          " renk_mes | kutu w/h  GT w/h  bilesen w/h")
    for o in r["kayit"]:
        if not (a <= o.get("kare", -1) <= b):
            continue
        bl = o.get("bilesen")
        print("%4d  %-15s %2s %7s %5s %5s | %6s %6s %5s | %8s | %4.0f/%-4.0f %4s/%-4s %4s/%-4s" % (
            o["kare"], o.get("neden"), o.get("n_bilesen", "."),
            "%.3f" % o["maske_doluluk"] if "maske_doluluk" in o else ".",
            "%.1f" % o["p82"] if "p82" in o else ".",
            "%.1f" % o["esik"] if "esik" in o else ".",
            "%.2f" % o["oran_w"] if "oran_w" in o else ".",
            "%.2f" % o["oran_h"] if "oran_h" in o else ".",
            "%.2f" % o["oran_ort"] if "oran_ort" in o else ".",
            "%.1f" % o["renk_mesafe"] if "renk_mesafe" in o else ".",
            o["boyut_w"], o["boyut_h"],
            "%.0f" % o["gt_w"] if "gt_w" in o else "?",
            "%.0f" % o["gt_h"] if "gt_h" in o else "?",
            bl[2] if bl else "?", bl[3] if bl else "?"))


def sayim(r):
    c = {}
    for o in r["kayit"]:
        c[o.get("neden")] = c.get(o.get("neden"), 0) + 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/rafine_4n.json")
    ap.add_argument("--a", type=int, default=PENCERE[0])
    ap.add_argument("--b", type=int, default=PENCERE[1])
    a = ap.parse_args()
    out = {}
    for ad, tur, arg in HEDEFLER:
        r = kos(ad, tur, arg)
        out[ad] = r
        sad = sum(1 for o in r["kayit"] if not o.get("sadik", True))
        print(f"\n== {ad} == cagri {len(r['kayit'])}  sadakat ihlali {sad}  "
              f"IoU {r['ort_iou']:.3f} kilit {100*r['kilit_orani']:.1f}% "
              f"drift {r['t_drift']}")
        print("   tum kosum nedenleri:", sayim(r))
        ozet(r, a.a, a.b)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"\nyazildi: {a.json}")


if __name__ == "__main__":
    main()
