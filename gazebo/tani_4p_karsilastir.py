"""Deney 4P - 4O ile BIREBIR ayni olcumler, uc kosulda yan yana.

TAKIP/ HIC DEGISMEZ. Olcum kodu 4O'nunkidir (`gazebo.tani_4o_dcf`); yalnizca
kaynak listesi degisir. Kosullar:

    durakli        : 4O'nun kaydi (celdiricili)          -- referans
    tekrar         : AYNI sahne, YENIDEN kayit           -- KAYIT GURULTUSU tabani
    celdiricisiz   : tek degisken, celdirici cikarildi   -- nedensellik testi
    kontrol        : G6_agresif                          -- 4M/4O kontrolu

`tekrar` kolonu zorunludur: 4P'deki farkin celdiriciden mi yoksa Gazebo
kaydinin tekrarlanabilirliginden mi geldigini ayirir.

Kullanim: python3 -m gazebo.tani_4p_karsilastir
"""
import argparse
import json
import os

import cv2
import numpy as np

from gazebo.tani_4o_dcf import kos
from veri.gazebo import GazeboKaynak

KOSULLAR = [("durakli", "G6_agresif_durakli"),
            ("tekrar", "G6_agresif_durakli_tekrar"),
            ("celdiricisiz", "G6_agresif_durakli_celdiricisiz"),
            ("kontrol", "G6_agresif")]

N, DOLGU, EPS = 32, 2.0, 1e-4
_w = np.hanning(N).astype(np.float32)
HAN = np.outer(_w, _w)


def _kanallar(bgr, merkez, boyut):
    w = max(4, int(round(boyut[0] * DOLGU)))
    h = max(4, int(round(boyut[1] * DOLGU)))
    p = cv2.getRectSubPix(bgr, (w, h), (float(merkez[0]), float(merkez[1])))
    p = cv2.resize(p, (N, N), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    b, g_, r = p[..., 0], p[..., 1], p[..., 2]
    top = b + g_ + r + 1.0
    kan = np.stack([(b + g_ + r) / 3.0, 255 * (b - g_) / top, 255 * (r - g_) / top])
    for i in range(len(kan)):
        c = kan[i]
        kan[i] = (c - c.mean()) / (c.std() + 1e-5) * HAN
    return kan, (w, h)


def _dx(r):
    """`_tepe` ile AYNI kenar korumasi (cekirdekler.py:325 `0 < ix < N-1`)."""
    iy, ix = np.unravel_index(np.argmax(r), r.shape)
    if not (0 < ix < N - 1):
        return ix, 0.0
    t = r[iy, ix]
    l, s = r[iy, ix - 1], r[iy, ix + 1]
    d = l - 2 * t + s
    return ix, (0.5 * (l - s) / d if abs(d) > 1e-9 else 0.0)


def cekim_noktasi(img, A, B, mc, boyut, yari=16.0, adim=0.5):
    """Olculen yer degistirmenin sifirlandigi x (DCF'in kendiliginden oturdugu
    yer). 4O §6 ile AYNI yontem."""
    xs = np.arange(mc[0] - yari, mc[0] + yari + 1e-9, adim)
    f = []
    for x in xs:
        kan, (w, h) = _kanallar(img, (x, mc[1]), boyut)
        F = np.fft.fft2(kan, axes=(1, 2))
        rr = np.real(np.fft.ifft2((A * F).sum(0) / (B + EPS)))
        ix, dx = _dx(rr)
        f.append(((ix + dx) - N // 2) * w / N)
    f = np.asarray(f)
    for i in range(len(xs) - 1):
        if f[i] >= 0 > f[i + 1] or f[i] > 0 >= f[i + 1]:
            t = f[i] / (f[i] - f[i + 1])
            return float(xs[i] + t * (xs[i + 1] - xs[i]))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/dcf_4p.json")
    ap.add_argument("--a", type=int, default=138)
    ap.add_argument("--b", type=int, default=152)
    a = ap.parse_args()

    out = {}
    for et, sen in KOSULLAR:
        if not os.path.isdir(os.path.join("data/gazebo", sen)):
            print(f"ATLANDI (kayit yok): {sen}")
            continue
        r, arsiv = kos(sen, "gazebo", sen)
        k = GazeboKaynak(kok="data/gazebo", senaryo=sen)
        frs, gt = {}, {}
        for kare in k:
            if a.a <= kare.indeks <= a.b:
                frs[kare.indeks] = kare.goruntu.copy()
            if kare.gt is not None and kare.gorunur:
                b_ = kare.gt
                gt[kare.indeks] = (b_[0] + b_[2] / 2, b_[1] + b_[3] / 2)
        satir = {x["kare"]: x for x in r["satir"]}
        for fr in range(a.a, a.b + 1):
            if fr not in satir or fr not in arsiv or fr not in frs or fr not in gt:
                continue
            row, ar = satir[fr], arsiv[fr]
            c = cekim_noktasi(frs[fr], ar["A"], ar["B"],
                              (row["ara_merkez_x"], row["ara_merkez_y"]),
                              np.array([row["w"], row["h"]]))
            row["cekim_x"] = c
            row["cekim_gt"] = None if c is None else c - gt[fr][0]
        out[et] = {"senaryo": sen, "ort_iou": r["ort_iou"],
                   "kilit_orani": r["kilit_orani"], "t_drift": r["t_drift"],
                   "satir": r["satir"]}
        print(f"== {et:13s} ({sen}) IoU {r['ort_iou']:.6f} "
              f"kilit {100*r['kilit_orani']:.2f}% drift {r['t_drift']}", flush=True)

    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print(f"yazildi: {a.json}")


if __name__ == "__main__":
    main()
