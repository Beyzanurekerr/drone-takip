"""MOSSE korelasyon filtresi (Bolme ve ark. 2010) - numpy FFT ile.

Neden MOSSE (KCF/CSRT degil):
  * Ham piksel kullanir, HOG hucresi gerektirmez -> 20x10 px hedefte bile calisir
  * Kare basina tek FFT cifti (32x32) -> mikrosaniyeler mertebesinde, Pi Zero'da bile ucuz
  * PSR (peak-to-sidelobe ratio) dogal bir "guven" olcusu verir -> kaybi ANLAR

Yama her zaman sabit `izgara` boyutuna olceklenir; bu sayede hedef kuculdukce
filtre bozulmaz, sadece giris cozunurlugu duser.
"""
import cv2
import numpy as np


def _hann(n):
    w = np.hanning(n).astype(np.float32)
    return np.outer(w, w)


class MOSSE:
    def __init__(self, izgara=32, sigma=2.0, lr=0.125, dolgu=2.0, eps=1e-5):
        self.N = izgara
        self.lr = lr
        self.dolgu = dolgu
        self.eps = eps
        self.han = _hann(izgara)
        # hedef tepki: merkeze oturtulmus gauss
        ax = np.arange(izgara, dtype=np.float32) - izgara // 2
        gx, gy = np.meshgrid(ax, ax)
        g = np.exp(-(gx ** 2 + gy ** 2) / (2 * sigma ** 2)).astype(np.float32)
        # DIKKAT: gauss MERKEZDE birakiliyor (ifftshift yok). `ara()` tepe konumunu
        # (ix - N//2) diye okudugu icin iki tarafin ayni konvansiyonu kullanmasi sart.
        self.G = np.fft.fft2(g)
        self.A = None
        self.B = None
        self.psr = 0.0

    # ---------------- yardimcilar ----------------
    def _yama(self, gri, merkez, boyut):
        w = max(4, int(round(boyut[0] * self.dolgu)))
        h = max(4, int(round(boyut[1] * self.dolgu)))
        p = cv2.getRectSubPix(gri, (w, h), (float(merkez[0]), float(merkez[1])))
        return cv2.resize(p, (self.N, self.N), interpolation=cv2.INTER_LINEAR), (w, h)

    def _on_isle(self, p):
        p = np.log(p.astype(np.float32) + 1.0)
        p = (p - p.mean()) / (p.std() + self.eps)
        return p * self.han

    def _rasgele_donusum(self, p, rng):
        a = rng.uniform(-8, 8)
        s = rng.uniform(0.92, 1.08)
        M = cv2.getRotationMatrix2D((self.N / 2, self.N / 2), a, s)
        return cv2.warpAffine(p, M, (self.N, self.N), borderMode=cv2.BORDER_REFLECT)

    # ---------------- API ----------------
    def baslat(self, gri, kutu, ornek=8, seed=0):
        x, y, w, h = kutu
        merkez = (x + w / 2, y + h / 2)
        ham, _ = self._yama(gri, merkez, (w, h))
        rng = np.random.default_rng(seed)
        self.A = np.zeros((self.N, self.N), np.complex64)
        self.B = np.zeros((self.N, self.N), np.complex64)
        for i in range(ornek):
            p = ham if i == 0 else self._rasgele_donusum(ham, rng)
            F = np.fft.fft2(self._on_isle(p))
            self.A += self.G * np.conj(F)
            self.B += F * np.conj(F)
        self.psr = 99.0

    def ara(self, gri, merkez, boyut):
        """Doner: (yeni_merkez, psr). Hicbir sey ogrenmez (salt okunur adim)."""
        p, (w, h) = self._yama(gri, merkez, boyut)
        F = np.fft.fft2(self._on_isle(p))
        H = self.A / (self.B + self.eps)
        r = np.real(np.fft.ifft2(H * F))

        iy, ix = np.unravel_index(np.argmax(r), r.shape)
        tepe = r[iy, ix]
        # alt-piksel: parabolik uydurma
        dx = dy = 0.0
        if 0 < ix < self.N - 1:
            l, c, sag = r[iy, ix - 1], tepe, r[iy, ix + 1]
            d = l - 2 * c + sag
            if abs(d) > 1e-9:
                dx = 0.5 * (l - sag) / d
        if 0 < iy < self.N - 1:
            u, c, alt = r[iy - 1, ix], tepe, r[iy + 1, ix]
            d = u - 2 * c + alt
            if abs(d) > 1e-9:
                dy = 0.5 * (u - alt) / d

        # PSR: tepe ne kadar baskin? Kayip tespitinin can damari.
        m = np.ones_like(r, bool)
        y0, y1 = max(0, iy - 5), min(self.N, iy + 6)
        x0, x1 = max(0, ix - 5), min(self.N, ix + 6)
        m[y0:y1, x0:x1] = False
        yan = r[m]
        self.psr = float((tepe - yan.mean()) / (yan.std() + self.eps))

        gx = (ix + dx) - self.N // 2
        gy = (iy + dy) - self.N // 2
        return (merkez[0] + gx * w / self.N, merkez[1] + gy * h / self.N), self.psr

    def ogren(self, gri, merkez, boyut, lr=None):
        lr = self.lr if lr is None else lr
        p, _ = self._yama(gri, merkez, boyut)
        F = np.fft.fft2(self._on_isle(p))
        self.A = (1 - lr) * self.A + lr * (self.G * np.conj(F))
        self.B = (1 - lr) * self.B + lr * (F * np.conj(F))
