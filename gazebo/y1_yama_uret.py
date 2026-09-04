"""A11.2/Y1.1 - YAMA GENISLETME: 4 hedefsiz VisDrone karesi, feather ile
2x2 izgarada birlestirilir, tekrarsiz (dorduncusu de FARKLI bir gercek
sahne - Y1'in tek-yama mozaikleme reddi burada da gecerli: AYNI goruntuyu
tekrarlamak/aynalamak yapay periyodik cizgi/kaleydoskop uretir).

Hedef: >=300x170 m (talimat). Sonuc: 2200x1300 px / 7.3142857 texel/m (A11
ailesi doku_px=4096, zemin_m=560) = 300.8x177.7 m.

Kosum: python3 -m gazebo.y1_yama_uret
Uretir: data/gazebo/_assets/zemin_gercek_kirpim.png (ESKI TEK-YAMA SURUMUNUN
UZERINE YAZAR - dunya_uret.py:GERCEK_ZEMIN_YAMA sabiti degismez).
Ayrica: data/gazebo/_assets/inpaint_konum_v2.json (KOL 2 icin - inpaint
edilen aracin YENI bilesikteki piksel/dunya konumu).

DORT HUCRE (2x2, her biri farkli sahne, hicbiri tekrarlamiyor):
  sol-ust  : mevcut Y1 yaması (0000283_01001_d_0000679, otoyol, ZATEN
             temizlenmis tek arac icerir - inpaint konumu buradan turer)
  sag-ust  : 0000242_00843_d_0000004 (nadire yakin yol, catlak dokusu)
  sol-alt  : 0000103_04948_d_0000035 (agac/duvar/tarla)
  sag-alt  : 0000103_00180_d_0000026 (agac/kaldirim) - ORIJINALDE bir
             yaya vardi, kirpim onu disarida birakiyor (x>=600)
"""
import json
import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)

VARLIK_KOK = "data/gazebo/_assets"
DET_KOK = "data/datasets/visdrone_det/images"
HUCRE_W, HUCRE_H = 1100, 650
T = 60      # hucreler-arasi feather genisligi (px)
W2, H2 = HUCRE_W * 2, HUCRE_H * 2

# (kaynak_dosya, kirpim (x0,y0,x1,y1) ya da None -> zaten hazir dosya, (col,row))
HUCRELER = [
    (os.path.join(VARLIK_KOK, "zemin_gercek_kirpim.png"), None, 0, 0),
    (os.path.join(DET_KOK, "0000242_00843_d_0000004.jpg"), (320, 20, 960, 540), 1, 0),
    (os.path.join(DET_KOK, "0000103_04948_d_0000035.jpg"), (310, 0, 1360, 765), 0, 1),
    (os.path.join(DET_KOK, "0000103_00180_d_0000026.jpg"), (600, 0, 1360, 765), 1, 1),
]

# Eski (tek-yama) surumdeki inpaint kutusu - o dosyanin KENDI 1920x880
# uzayinda (bkz. A11_1_ONKAYIT.md). Bu script o dosyayi sol-ust hucreye
# gomerken donusumu izler ve YENI (bilesik) konumu hesaplar.
_ESKI_INPAINT_PX = (1111, 103, 1261, 263)


def _hucre_getir(img, hedef_w, hedef_h):
    h, w = img.shape[:2]
    olcek = max(hedef_w / w, hedef_h / h)
    nw, nh = int(np.ceil(w * olcek)), int(np.ceil(h * olcek))
    interp = cv2.INTER_AREA if olcek < 1 else cv2.INTER_LINEAR
    r = cv2.resize(img, (nw, nh), interpolation=interp)
    x0 = (nw - hedef_w) // 2
    y0 = (nh - hedef_h) // 2
    return r[y0:y0 + hedef_h, x0:x0 + hedef_w], (x0, y0, olcek)


def uret():
    tuval = np.zeros((H2, W2, 3), np.float32)
    agirlik = np.zeros((H2, W2), np.float32)
    ilk_hucre_donusumu = None

    for i, (yol, kirpim, col, row) in enumerate(HUCRELER):
        img = cv2.imread(yol)
        if img is None:
            raise FileNotFoundError(yol)
        if kirpim is not None:
            x0, y0, x1, y1 = kirpim
            img = img[y0:y1, x0:x1]

        sol_sinir, ust_sinir = (col == 0), (row == 0)
        sag_sinir, alt_sinir = (col == 1), (row == 1)
        ek_x = (0 if sol_sinir else T) + (0 if sag_sinir else T)
        ek_y = (0 if ust_sinir else T) + (0 if alt_sinir else T)
        hedef_w, hedef_h = HUCRE_W + ek_x, HUCRE_H + ek_y
        hucre, donusum = _hucre_getir(img, hedef_w, hedef_h)

        ox = col * HUCRE_W - (0 if sol_sinir else T)
        oy = row * HUCRE_H - (0 if ust_sinir else T)
        if i == 0:
            ilk_hucre_donusumu = (donusum, ox, oy)

        h, w = hucre.shape[:2]
        ramp_x = np.ones(w, np.float32)
        if not sol_sinir:
            ramp_x[:T] = np.linspace(0, 1, T)
        if not sag_sinir:
            ramp_x[-T:] = np.linspace(1, 0, T)
        ramp_y = np.ones(h, np.float32)
        if not ust_sinir:
            ramp_y[:T] = np.linspace(0, 1, T)
        if not alt_sinir:
            ramp_y[-T:] = np.linspace(1, 0, T)
        m = np.outer(ramp_y, ramp_x)

        tuval[oy:oy + h, ox:ox + w] += hucre.astype(np.float32) * m[..., None]
        agirlik[oy:oy + h, ox:ox + w] += m

    agirlik = np.maximum(agirlik, 1e-6)
    sonuc = (tuval / agirlik[..., None]).astype(np.uint8)

    # inpaint kutusunun YENI (bilesik) konumu: sol-ust hucrenin donusumunu uygula
    (cx0, cy0, olcek), ox, oy = ilk_hucre_donusumu
    ex0, ey0, ex1, ey1 = _ESKI_INPAINT_PX
    yeni_kutu = (ex0 * olcek - cx0 + ox, ey0 * olcek - cy0 + oy,
                ex1 * olcek - cx0 + ox, ey1 * olcek - cy0 + oy)
    return sonuc, tuple(round(v) for v in yeni_kutu)


if __name__ == "__main__":
    sonuc, yeni_inpaint_kutu = uret()
    yol = os.path.join(VARLIK_KOK, "zemin_gercek_kirpim.png")
    cv2.imwrite(yol, sonuc)
    tpm = 4096 / 560.0
    print(f"yazildi: {yol} ({sonuc.shape[1]}x{sonuc.shape[0]} px = "
         f"{sonuc.shape[1]/tpm:.1f}x{sonuc.shape[0]/tpm:.1f} m)")
    print(f"yeni inpaint piksel kutusu (bilesik uzayda): {yeni_inpaint_kutu}")
    with open(os.path.join(VARLIK_KOK, "inpaint_konum_v2.json"), "w") as f:
        json.dump({"inpaint_piksel_kutusu": list(yeni_inpaint_kutu),
                  "not": "dunya_uret.py:INPAINT_PIKSEL_KUTUSU bu degere guncellendi"},
                 f, indent=2)
