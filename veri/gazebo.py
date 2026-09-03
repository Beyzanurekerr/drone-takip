"""Gazebo kayit adaptoru: diske alinmis kareleri + kusursuz GT'yi `Kare` olarak verir.

`kaynak.py`'deki sozlesmenin disina CIKMAZ: takip tarafi goruntunun Gazebo'dan
geldigini bilmez, `Kare.gt` alanini simulatorden gelen GT'den ayirt etmez.
`Kare` dataclass'ina alan EKLENMEDI - eklenirse tum kaynaklar etkilenirdi.
Teshis icin gereken ham veri (kamera/arac pozlari) kaynagin uzerinde
`self.pozlar` / `self.meta` olarak durur; olcum yolu onlara bakmaz.

GT NASIL URETILIYOR
-------------------
Kaydedilen sey kutu degil, POZ. Kutu burada, kamera ic parametreleriyle
(`/camera_info`) hesaplanir. Boylece:
  * ayni kayit farkli izdusum varsayimlariyla yeniden degerlendirilebilir
  * izdusum matematigi TEK yerde durur (sim/world.py:gt_box ile ayni sozlesme)

Kamera cerceve donusumu (gz sim):
    +X = optik eksen (ileri) · +Y = sol · +Z = yukari
    u = cx - fx * (Y / X)      v = cy - fy * (Z / X)
Isaretler `_kendini_dogrula()` ile her yuklemede sinaniyor; sessizce ters
donmus bir eksen tum IoU olcumunu anlamsiz kilar.
"""
import json
import os

import cv2
import numpy as np

from kaynak import Kare, Kaynak, KaynakHatasi

GAZEBO_VARSAYILAN = "data/gazebo"


def kuaterniyon_matris(qw, qx, qy, qz):
    """Birim kuaterniyon -> 3x3 donme matrisi (sutunlari cismin eksenleri)."""
    n = np.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    if n < 1e-9:
        return np.eye(3)
    qw, qx, qy, qz = qw / n, qx / n, qy / n, qz / n
    return np.array([
        [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
        [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
        [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
    ], np.float64)


def izdusur(P_dunya, C, R, fx, fy, cx, cy):
    """Dunya noktalarini goruntu pikseline tasi. Kameranin ARKASI None ile elenir."""
    P = np.atleast_2d(np.asarray(P_dunya, np.float64))
    p = (P - np.asarray(C, np.float64)) @ R          # R^T @ d  ==  d @ R
    X, Y, Z = p[:, 0], p[:, 1], p[:, 2]
    onde = X > 1e-6
    u = np.full(len(P), np.nan)
    v = np.full(len(P), np.nan)
    u[onde] = cx - fx * (Y[onde] / X[onde])
    v[onde] = cy - fy * (Z[onde] / X[onde])
    return np.stack([u, v], 1), onde


def _kutu_koseleri(poz, L, W, H):
    """Aracin 8 kosesini dunya koordinatlarinda ver."""
    x, y, z, qw, qx, qy, qz = poz
    R = kuaterniyon_matris(qw, qx, qy, qz)
    yerel = np.array([[sx * L / 2, sy * W / 2, sz * H / 2]
                      for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)],
                     np.float64)
    return yerel @ R.T + np.array([x, y, z])


class GazeboKaynak(Kaynak):
    """`gazebo/kaydet.py` ciktisini okur. Canli sim'e BAGLANMAZ (bilerek).

    Canli baglanti RTF ~0.35 yuzunden FPS olcumunu render hizina baglardi ve
    kosumlar tekrarlanamaz olurdu; ayrintisi `gazebo/kaydet.py` basliginda.
    """

    def __init__(self, kok=GAZEBO_VARSAYILAN, senaryo=None, olcek=1.0,
                 hedef_genislik=0):
        kok = kok or GAZEBO_VARSAYILAN
        if senaryo:
            dizin = os.path.join(kok, senaryo)
        else:
            dizin = kok
            senaryo = os.path.basename(os.path.normpath(kok))
        if not os.path.isdir(dizin):
            mevcut = (sorted(d for d in os.listdir(kok)
                             if os.path.isdir(os.path.join(kok, d)))
                      if os.path.isdir(kok) else [])
            raise KaynakHatasi(
                f"Gazebo kaydi bulunamadi: {dizin}\n"
                f"       mevcut kayitlar: {', '.join(mevcut) or '(yok)'}\n"
                f"       once kaydet: python3 -m gazebo.kaydet {senaryo}")

        meta_yolu = os.path.join(dizin, "meta.json")
        if not os.path.exists(meta_yolu):
            raise KaynakHatasi(f"meta.json yok: {meta_yolu} (kayit yarim kalmis)")
        with open(meta_yolu) as f:
            self.meta = json.load(f)

        self.dizin = dizin
        self.kare_dizin = os.path.join(dizin, "kareler")
        self.pozlar = self._pozlar_oku(os.path.join(dizin, "pozlar.csv"))

        self.dosyalar = sorted(
            os.path.join(self.kare_dizin, d)
            for d in os.listdir(self.kare_dizin) if d.endswith(".png"))
        if not self.dosyalar:
            raise KaynakHatasi(f"kare bulunamadi: {self.kare_dizin}")
        if len(self.dosyalar) != len(self.pozlar):
            raise KaynakHatasi(
                f"senkron bozuk: {len(self.dosyalar)} kare ama "
                f"{len(self.pozlar)} poz satiri ({dizin})")

        self.ad = f"gazebo:{senaryo}"
        self.tur = "gazebo"
        self.senaryo = senaryo
        ham_g = int(self.meta["genislik"])
        ham_y = int(self.meta["yukseklik"])
        self.olcek = self._olcek_hesapla(olcek, hedef_genislik, ham_g)
        self.genislik = int(round(ham_g * self.olcek))
        self.yukseklik = int(round(ham_y * self.olcek))
        self.fps = float(self.meta.get("fps", 30.0))
        self.kare_sayisi = len(self.dosyalar)

        self.fx = float(self.meta["fx"]) * self.olcek
        self.fy = float(self.meta["fy"]) * self.olcek
        self.cx = float(self.meta["cx"]) * self.olcek
        self.cy = float(self.meta["cy"]) * self.olcek
        self.hedef_ad = self.meta["hedef"]
        self.olculer = {a["ad"]: (a["L"], a["W"], a["H"])
                        for a in self.meta["araclar"]}
        self._k = 0
        self._kendini_dogrula()

    # ------------------------------------------------------------------
    @staticmethod
    def _olcek_hesapla(olcek, hedef_genislik, ham_g):
        if hedef_genislik and ham_g > 0:
            return float(hedef_genislik) / float(ham_g)
        if olcek and olcek > 0:
            return float(olcek)
        return 1.0

    @staticmethod
    def _pozlar_oku(yol):
        if not os.path.exists(yol):
            raise KaynakHatasi(f"pozlar.csv yok: {yol}")
        with open(yol) as f:
            basliklar = f.readline().strip().split(",")
            satirlar = [s.strip().split(",") for s in f if s.strip()]
        return [{b: (v if b == "kare" else float(v))
                 for b, v in zip(basliklar, s)} for s in satirlar]

    def _kamera(self, satir):
        C = np.array([satir["kam_x"], satir["kam_y"], satir["kam_z"]])
        R = kuaterniyon_matris(satir["kam_qw"], satir["kam_qx"],
                               satir["kam_qy"], satir["kam_qz"])
        return C, R

    def _kutu(self, satir, ad):
        """Aracin eksen-hizali GT kutusu (x, y, w, h) - sim/world.py:gt_box ile ayni."""
        L, W, H = self.olculer[ad]
        poz = tuple(satir[f"{ad}_{s}"] for s in
                    ("x", "y", "z", "qw", "qx", "qy", "qz"))
        C, R = self._kamera(satir)
        uv, onde = izdusur(_kutu_koseleri(poz, L, W, H), C, R,
                           self.fx, self.fy, self.cx, self.cy)
        if not onde.all():
            return None
        x0, y0 = uv.min(0)
        x1, y1 = uv.max(0)
        return np.array([x0, y0, x1 - x0, y1 - y0], np.float32)

    def _gorunur(self, kutu):
        """sim/world.py:visible ile ayni olcut: kutu merkezi kadraj icinde mi."""
        if kutu is None:
            return False
        cx, cy = kutu[0] + kutu[2] / 2, kutu[1] + kutu[3] / 2
        return bool(0 <= cx < self.genislik and 0 <= cy < self.yukseklik)

    def _kendini_dogrula(self):
        """Izdusum isaretlerini kayittan bagimsiz olarak sina.

        Nadir kamerada dunya +X goruntude YUKARI (v azalir), dunya +Y SOLA
        (u azalir) dusmelidir. Bir eksen ters donmusse GT sessizce yanlis olur
        ve butun IoU olcumu anlamsizlasir - bu yuzden yukleme aninda kontrol.
        """
        s = self.pozlar[0]
        C, R = self._kamera(s)
        merkez, _ = izdusur([C + R @ np.array([1.0, 0.0, 0.0])], C, R,
                            self.fx, self.fy, self.cx, self.cy)
        if not np.allclose(merkez[0], [self.cx, self.cy], atol=1e-3):
            raise KaynakHatasi(
                "izdusum tutarsiz: optik eksen uzerindeki nokta goruntu "
                f"merkezine dusmuyor ({merkez[0]} != {[self.cx, self.cy]})")

    # ------------------------------------------------------------------
    def oku(self):
        if self._k >= self.kare_sayisi:
            return None
        k = self._k
        goruntu = cv2.imread(self.dosyalar[k], cv2.IMREAD_COLOR)
        if goruntu is None:
            raise KaynakHatasi(f"kare okunamadi: {self.dosyalar[k]}")
        if self.olcek != 1.0:
            goruntu = cv2.resize(goruntu, (self.genislik, self.yukseklik),
                                 interpolation=cv2.INTER_AREA)
        s = self.pozlar[k]
        gt = self._kutu(s, self.hedef_ad)
        self._k += 1
        return Kare(goruntu=goruntu, indeks=k, zaman=float(s["t"]),
                    kaynak_adi=self.ad, genislik=self.genislik,
                    yukseklik=self.yukseklik, fps=self.fps,
                    gt=gt, gorunur=self._gorunur(gt))

    def acik_mi(self):
        return self._k < self.kare_sayisi

    def bilgi(self):
        r = self.meta.get("kayit", {})
        return (f"{self.ad}  {self.genislik}x{self.yukseklik}  "
                f"{self.fps:.0f} fps  {self.kare_sayisi} kare  "
                f"| senkron ort {r.get('senkron_bosluk_ms_ort')} ms "
                f"max {r.get('senkron_bosluk_ms_max')} ms  "
                f"| RTF {r.get('rtf')}")

    # --- teshis icin (olcum yolu kullanmaz) ---
    def celdiriciler(self, k):
        """k. karede hedef DISINDAKI araclarin GT kutulari - ID switch olcumu icin."""
        s = self.pozlar[k]
        return {ad: self._kutu(s, ad) for ad in self.olculer
                if ad != self.hedef_ad}
