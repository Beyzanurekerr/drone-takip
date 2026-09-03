"""A11 - Gazebo yatagi icin KOL 0-3 arasinda paylasilan yardimcilar.

*** KOMPOZIT YATAK KULLANMAZ *** - butun fonksiyonlar veri/gazebo.py:
GazeboKaynak uzerinden calisir. On-kayit: docs/architecture/A11_ONKAYIT.md.

Icerdigi:
  gercek_kaydirma   - DUZ ZEMIN varsayimiyla, iki ardisik kamera pozundan
                       bir goruntu noktasinin "gercekte" nereye kaymasi
                       gerektigini hesaplar. KOL 0/1'in "sahte ego" olcumu
                       bunun uzerine kurulur.
  roi_tespit_g      - A8.roi_tespit ile AYNI geometri (kirp -> AG boyuna
                       getir -> YOLO -> geri donustur), ama SENSOR modul
                       sabitine (1280x720, VisDrone) degil VERILEN (W,H)'ye
                       kenetlenir. Gazebo karesi 640x480'dir; A8'in sabitini
                       kullanmak kirpma sinirlarini YANLIS hesaplardi.
  kareleri_topla    - GazeboKaynak'tan (goruntu, gt, W, H, pozlar_satiri)
                       listesi.
  mod_etiketle      - A9 Asama 2 ile AYNI olcut: kopus sonrasi DCF kabul
                       orani >= 0.8 -> Mod B, aksi Mod A.
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from veri.gazebo import GazeboKaynak, izdusur, kuaterniyon_matris  # noqa: E402

import csv as _csv

AG = (640, 360)          # A8'in aga verilen kare boyutu - DEGISMEDI
YANLIS_IOU, DOGRU_IOU, MIN_EPIZOT = 0.2, 0.5, 5


# --------------------------------------------------------------------------
# GERCEK EGO (duz zemin izdusumu) - KOL 0/1
# --------------------------------------------------------------------------
def _unproject_zemin(uv, C, R, fx, fy, cx, cy):
    """Piksel (u,v)'yi, KAMERA C,R pozunda, DUZ ZEMIN (z=0) ile kesistir.

    Kamera cercevesi (veri/gazebo.py ile AYNI sozlesme): +X ileri (optik
    eksen), +Y sol, +Z yukari.  u = cx - fx*(Y/X), v = cy - fy*(Z/X)
    -> Y/X = (cx-u)/fx, Z/X = (cy-v)/fy, dunya yonu d = R @ (1, Y/X, Z/X).
    """
    u, v = uv
    d_cam = np.array([1.0, (cx - u) / fx, (cy - v) / fy], np.float64)
    d_dunya = R @ d_cam
    if abs(d_dunya[2]) < 1e-9:
        return None
    t = -C[2] / d_dunya[2]
    if t <= 0:
        return None
    return C + t * d_dunya


def gercek_kaydirma(x_ref, satir_once, satir_sonra, fx, fy, cx, cy):
    """x_ref (piksel) SATIR_ONCE pozunda zeminde bir nokta olsaydi,
    SATIR_SONRA pozunda hangi pikselde gorunurdu? DUZ ZEMIN varsayimi.

    None doner: nokta ufkun uzerinde (t<=0) ya da SATIR_SONRA'da kamera
    arkasinda kaldiysa (izdusur'un onde=False'u).
    """
    C0 = np.array([satir_once["kam_x"], satir_once["kam_y"], satir_once["kam_z"]])
    R0 = kuaterniyon_matris(satir_once["kam_qw"], satir_once["kam_qx"],
                            satir_once["kam_qy"], satir_once["kam_qz"])
    P = _unproject_zemin(x_ref, C0, R0, fx, fy, cx, cy)
    if P is None:
        return None
    C1 = np.array([satir_sonra["kam_x"], satir_sonra["kam_y"], satir_sonra["kam_z"]])
    R1 = kuaterniyon_matris(satir_sonra["kam_qw"], satir_sonra["kam_qx"],
                            satir_sonra["kam_qy"], satir_sonra["kam_qz"])
    uv, onde = izdusur([P], C1, R1, fx, fy, cx, cy)
    if not onde[0]:
        return None
    return uv[0]


def sahte_ego_px(M_gorsel, x_ref, satir_once, satir_sonra, fx, fy, cx, cy):
    """On-kayit tanimi: |M_gorsel(x_ref) - M_gercek(x_ref)|.

    M_gorsel: takip/egomotion.py:EgoMotion.guncelle'nin donduregu 2x3 afin
    (onceki kareyi mevcut kareye tasir). None doner: gercek izdusum
    tanimsizsa (ufuk/kamera arkasi) - CAGIRAN taraf bu kareyi atlar.
    """
    gercek = gercek_kaydirma(x_ref, satir_once, satir_sonra, fx, fy, cx, cy)
    if gercek is None:
        return None
    x = np.asarray(x_ref, np.float64)
    gorsel = M_gorsel[:, :2] @ x + M_gorsel[:, 2]
    return float(np.linalg.norm(gorsel - np.asarray(gercek, np.float64)))


# --------------------------------------------------------------------------
# ROI TESPIT - Gazebo kare boyutuna KENETLI (A8 gemoetrisi birebir)
# --------------------------------------------------------------------------
def roi_wh(R):
    """A8.roi_wh ile AYNI: AG en-boy orani (16:9) korunur."""
    return int(R), int(round(R * 9.0 / 16.0))


def roi_tespit_g(model, img, merkez, R, yolo_calistir):
    """A8.roi_tespit ile AYNI geometri; W,H GORUNTUDEN okunur (VerILEN img).

    A8.roi_tespit modul-seviyesi SENSOR=(1280,720) sabitine kenetliydi -
    VisDrone'un 'sensor tuvali' icindi. Gazebo karesi 640x480'dir; o sabiti
    kullanmak kirpma sinirlarini (x0,y0 clamp) YANLIS hesaplardi. Bu fonksiyon
    W,H'yi VERILEN goruntuden okur - mekanizma birebir ayni, yalnizca dogru
    kareye kenetli.
    """
    H, W = img.shape[:2]
    rw, rh = roi_wh(R)
    x0 = int(round(merkez[0] - rw / 2.0))
    y0 = int(round(merkez[1] - rh / 2.0))
    x0 = max(0, min(W - rw, x0))
    y0 = max(0, min(H - rh, y0))
    parca = img[y0:y0 + rh, x0:x0 + rw]
    if parca.shape[:2] != (rh, rw):
        return [], [], 0.0
    interp = cv2.INTER_LINEAR if rw < AG[0] else cv2.INTER_AREA
    girdi = cv2.resize(parca, AG, interpolation=interp)
    kutular, guvenler, ms = yolo_calistir(model, girdi)
    kx, ky = rw / float(AG[0]), rh / float(AG[1])
    geri = [np.array([k[0] * kx + x0, k[1] * ky + y0, k[2] * kx, k[3] * ky],
                     np.float32) for k in kutular]
    return geri, guvenler, ms


# --------------------------------------------------------------------------
# VERI YUKLEME
# --------------------------------------------------------------------------
def kareleri_topla(senaryo, kok="data/gazebo", n=None):
    """(goruntu, gt, poz_satiri) listesi + (W,H,fx,fy,cx,cy). GT gorunmeyen
    kareler dahil edilir (dizinin ARDISIK kalmasi icin - Gazebo'da her kare
    senkronize, VisDrone'daki gorunurluk atlamasi burada yok)."""
    k = GazeboKaynak(kok=kok, senaryo=senaryo)
    out = []
    for i, kare in enumerate(k):
        out.append((kare.goruntu, None if kare.gt is None else np.asarray(kare.gt, np.float32),
                    k.pozlar[i]))
        if n is not None and len(out) >= n:
            break
    return out, k.genislik, k.yukseklik, k.fx, k.fy, k.cx, k.cy


# --------------------------------------------------------------------------
# MOD ETIKETLEME - A9 Asama 2 ile AYNI olcut
# --------------------------------------------------------------------------
def kosular(dizi, esik, n):
    """esik(x) DOGRU olan >= n uzunluktaki azami ardisik dizilerin (bas,son)."""
    out, i, N = [], 0, len(dizi)
    while i < N:
        if esik(dizi[i]):
            j = i
            while j < N and esik(dizi[j]):
                j += 1
            if j - i >= n:
                out.append((i, j - 1))
            i = j
        else:
            i += 1
    return out


def mod_etiketle(iz, kopus_idx):
    """A9 tani_a9_kopus.py ile AYNI olcut: kopus SONRASI kareler icin
    DCF kabul orani (durum_takipci == KILITLI) >= 0.8 -> Mod B, aksi Mod A.
    `iz`: t=kopus_idx'ten SONUNA kadar kayit listesi (her elemanda
    'durum_takipci' anahtari)."""
    sonrasi = iz[kopus_idx + 1:]
    if not sonrasi:
        return None, None
    kabul = sum(1 for x in sonrasi if x["durum_takipci"] == "KILITLI")
    oran = kabul / len(sonrasi)
    return ("B" if oran >= 0.8 else "A"), round(oran, 4)


# --------------------------------------------------------------------------
# IMU - KOL 1 (docs/architecture/A11_ONKAYIT.md EK-2)
# --------------------------------------------------------------------------
def imu_oku(yol):
    """imu.csv -> t sirali kayit listesi (t,wx,wy,wz,ax,ay,az,qw,qx,qy,qz)."""
    with open(yol) as f:
        r = list(_csv.DictReader(f))
    return [{k: float(v) for k, v in row.items()} for row in r]


def imu_en_yakin(t, imu_satirlar):
    """En yakin ornek (200 Hz IMU vs 30 Hz kare - enterpolasyon YOK)."""
    return min(imu_satirlar, key=lambda r: abs(r["t"] - t))


IMU_IZGARA_YARICAP = 0.35   # W,H'nin bu oraninda 3x3 ornekleme izgarasi


def _izgara(W, H):
    xs = [0.5 - IMU_IZGARA_YARICAP, 0.5, 0.5 + IMU_IZGARA_YARICAP]
    ys = [0.5 - IMU_IZGARA_YARICAP, 0.5, 0.5 + IMU_IZGARA_YARICAP]
    return [np.array([x * W, y * H]) for y in ys for x in xs]


def imu_M(R0, R1, C, W, H, fx, fy, cx, cy):
    """EK-2 mekanigi: ROTASYON-ONLY M. Kamera konumu C SABIT (oteleme YOK).

    3x3 izgara zemine dusurulup (C,R0) -> geri izdusurulur (C,R1); gorsel
    EgoMotion ile AYNI model sinifina (benzerlik donusumu) fit edilir.
    Basarisiz olursa (yetersiz gecerli nokta) BIRIM M doner.
    """
    src, dst = [], []
    for x_ref in _izgara(W, H):
        P = _unproject_zemin(x_ref, C, R0, fx, fy, cx, cy)
        if P is None:
            continue
        uv, onde = izdusur([P], C, R1, fx, fy, cx, cy)
        if not onde[0]:
            continue
        src.append(x_ref)
        dst.append(uv[0])
    if len(src) < 3:
        return np.array([[1, 0, 0], [0, 1, 0]], np.float32), 0.0
    src_a = np.asarray(src, np.float32).reshape(-1, 1, 2)
    dst_a = np.asarray(dst, np.float32).reshape(-1, 1, 2)
    M, inl = cv2.estimateAffinePartial2D(src_a, dst_a, method=cv2.RANSAC)
    if M is None:
        return np.array([[1, 0, 0], [0, 1, 0]], np.float32), 0.0
    oran = float(inl.sum()) / len(src) if inl is not None else 1.0
    return M.astype(np.float32), oran


class ImuEgo:
    """EgoMotion ile AYNI arayuz: guncelle(gri, hedef_kutu=None) -> (M, guven).

    gri KULLANILMAZ - gorsel akis KAPALI (EK-2). IMU + pozlar.csv'den YALNIZCA
    frame 0'da kalibrasyon icin okunur (R_kam_sabit, C_sabit); sonrasi
    saf IMU'dur.
    """

    def __init__(self, imu_satirlar, pozlar, W, H, fx, fy, cx, cy):
        self.imu = imu_satirlar
        self.pozlar = pozlar
        self.W, self.H = W, H
        self.fx, self.fy, self.cx, self.cy = fx, fy, cx, cy
        self._k = 0
        p0 = pozlar[0]
        s0 = imu_en_yakin(p0["t"], imu_satirlar)
        R_govde0 = kuaterniyon_matris(s0["qw"], s0["qx"], s0["qy"], s0["qz"])
        R_cam0 = kuaterniyon_matris(p0["kam_qw"], p0["kam_qx"], p0["kam_qy"], p0["kam_qz"])
        self.R_kam_sabit = R_govde0.T @ R_cam0      # TEK SEFERLIK kalibrasyon
        self.C_sabit = np.array([p0["kam_x"], p0["kam_y"], p0["kam_z"]])
        self._R_onceki = R_govde0 @ self.R_kam_sabit

    def guncelle(self, gri, hedef_kutu=None):
        self._k += 1
        p = self.pozlar[self._k]
        s = imu_en_yakin(p["t"], self.imu)
        R_govde = kuaterniyon_matris(s["qw"], s["qx"], s["qy"], s["qz"])
        R_cam = R_govde @ self.R_kam_sabit
        M, guven = imu_M(self._R_onceki, R_cam, self.C_sabit,
                         self.W, self.H, self.fx, self.fy, self.cx, self.cy)
        self._R_onceki = R_cam
        self.M, self.guven = M, guven
        return M, guven

    @property
    def olcek_katsayisi(self):
        """EgoMotion.olcek_katsayisi ile AYNI arayuz (izleyici.py bunu okur).
        M rotasyon-only (EK-2) oldugu icin ~1.0 civarinda kalmasi beklenir;
        yine de fit edilen benzerlik donusumunden GERCEK deger okunur,
        varsayimla DOLDURULMAZ."""
        return float(np.sqrt(abs(np.linalg.det(self.M[:, :2]))))
