"""Ego-motion kestirimi: kameranin kayma / donme / zoom hareketi.

Seyrek Lucas-Kanade optik akis + RANSAC benzerlik donusumu.
Cikti: onceki kareyi mevcut kareye tasiyan 2x3 afin matris.

Bu katman sistemin temeli:
  1) Arama penceresini daraltir       -> hiz
  2) Hareketli cisimleri arka plandan ayirir -> yeniden tespit
  3) Olcek katsayisi verir (irtifa degisimi)  -> bedava olcek takibi
"""
import cv2
import numpy as np

BIRIM = np.array([[1, 0, 0], [0, 1, 0]], np.float32)


def bileske(M1, M2):
    """Once M1 sonra M2 uygulamaya denk tek matris."""
    A1, t1 = M1[:, :2], M1[:, 2]
    A2, t2 = M2[:, :2], M2[:, 2]
    return np.hstack([(A2 @ A1), (A2 @ t1 + t2).reshape(2, 1)]).astype(np.float32)


def tersi(M):
    A = M[:, :2]
    Ai = np.linalg.inv(A)
    return np.hstack([Ai, (-Ai @ M[:, 2]).reshape(2, 1)]).astype(np.float32)


def uygula(M, pts):
    p = np.asarray(pts, np.float32).reshape(-1, 2)
    return p @ M[:, :2].T + M[:, 2]


class EgoMotion:
    def __init__(self, olcek=0.5, max_nokta=100, min_nokta=25, yenile=10):
        self.olcek = olcek
        self.max_nokta = max_nokta
        self.min_nokta = min_nokta
        self.yenile = yenile
        self.sayac = 0
        self.onceki = None
        self.noktalar = None
        self.lk = dict(winSize=(15, 15), maxLevel=2,
                       criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 12, 0.03))
        self.guven = 0.0
        self.M = BIRIM.copy()

    def _kose_bul(self, kucuk, maske=None):
        p = cv2.goodFeaturesToTrack(kucuk, self.max_nokta, 0.01, 8,
                                    mask=maske, blockSize=5)
        return p

    def guncelle(self, gri, hedef_kutu=None):
        """gri: tam cozunurluk gri kare. hedef_kutu: disla (kendi hareketi bozmasin).

        Doner: (M, guven). M onceki kareyi bu kareye tasir (tam cozunurluk px).
        """
        k = cv2.resize(gri, None, fx=self.olcek, fy=self.olcek, interpolation=cv2.INTER_AREA)
        if self.onceki is None:
            self.onceki = k
            self.noktalar = self._kose_bul(k, self._maske(k, hedef_kutu))
            self.M, self.guven = BIRIM.copy(), 0.0
            return self.M, self.guven

        # Noktalar yenilenmezse hayatta kalanlar karenin bir tarafinda toplanir
        # ve benzerlik uydurmasi OLCEKTE yanlilik uretir (sabit irtifada bile
        # kare kare %0.4 -> 300 karede 3x sisme). Periyodik yenileme sart.
        self.sayac += 1
        if (self.noktalar is None or len(self.noktalar) < self.min_nokta
                or self.sayac % self.yenile == 0):
            self.noktalar = self._kose_bul(self.onceki, self._maske(self.onceki, hedef_kutu))

        M, guven = BIRIM.copy(), 0.0
        if self.noktalar is not None and len(self.noktalar) >= 6:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(self.onceki, k, self.noktalar, None, **self.lk)
            # geri akis kontrolu: guvenilir olmayan eslesmeleri at
            p0r, st2, _ = cv2.calcOpticalFlowPyrLK(k, self.onceki, p1, None, **self.lk)
            iyi = (st.ravel() == 1) & (st2.ravel() == 1)
            iyi &= (np.abs(self.noktalar - p0r).reshape(-1, 2).max(1) < 1.0)
            a, b = self.noktalar[iyi], p1[iyi]
            if len(a) >= 6:
                Me, ic = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC,
                                                     ransacReprojThreshold=2.0,
                                                     maxIters=200, confidence=0.99)
                if Me is not None and ic is not None and int(ic.sum()) >= 8:
                    Me = Me.astype(np.float32)
                    s = float(np.sqrt(abs(np.linalg.det(Me[:, :2]))))
                    kayma = float(np.linalg.norm(Me[:, 2])) / self.olcek
                    # akil suzgeci: tek karede olcek %15'ten fazla degisemez,
                    # kayma da kare genisliginin yarisini gecemez. Aksi halde
                    # cozum bozuktur -> birim matrise dus (Kalman devrali).
                    if 0.85 < s < 1.18 and kayma < 0.5 * gri.shape[1]:
                        M = Me
                        M[:, 2] /= self.olcek  # kucuk -> tam cozunurluk (A ayni kalir)
                        guven = float(ic.sum()) / max(1, len(a))
            self.noktalar = b.reshape(-1, 1, 2) if len(b) >= self.min_nokta else None

        self.onceki = k
        self.M, self.guven = M, guven
        return M, guven

    def _maske(self, kucuk, hedef_kutu):
        if hedef_kutu is None:
            return None
        m = np.full(kucuk.shape, 255, np.uint8)
        x, y, w, h = np.asarray(hedef_kutu, np.float32) * self.olcek
        pad = 6
        cv2.rectangle(m, (int(x - pad), int(y - pad)), (int(x + w + pad), int(y + h + pad)), 0, -1)
        return m

    @property
    def olcek_katsayisi(self):
        """Arka plan olcek degisimi = irtifa degisimi. Hedef kutusu bununla buyur/kucult."""
        return float(np.sqrt(abs(np.linalg.det(self.M[:, :2]))))
