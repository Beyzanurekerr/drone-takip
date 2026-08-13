"""Hareket tabanli arac tespiti + gorunum imzasi.

Ego-motion ile hizalanmis 3 kare farki:
    D = min(|I_t - warp(I_{t-1})| , |I_t - warp(I_{t-2})|)
`min` bir mantiksal VE gibi davranir: eski konumdaki "hayalet" lekeleri siler,
geriye sadece cismin SU ANKI konumu kalir.

Ayni modul iki isi birden yapar:
  * ilk karede hedef secim listesi (kullanici/otomatik secer)
  * takip koptugunda aday uretimi (yeniden tespit)
CNN yok -> Pi Zero'da da calisabilir.
"""
import cv2
import numpy as np

from .egomotion import BIRIM, bileske


class HareketTespit:
    def __init__(self, min_alan=3, max_kenar=160, esik_k=4.0, min_esik=8.0, uc_kare=False):
        self.min_alan = min_alan
        self.max_kenar = max_kenar
        self.esik_k = esik_k
        self.min_esik = min_esik
        # uc_kare=True daha temiz maske verir AMA lekeyi aracin on kismina kaydirir
        # (yer degistirme < arac boyu oldugu surece). Kutu dogrulugu daha onemli,
        # bu yuzden varsayilan 2 kare farki: merkez hatasi sadece ~d/2 piksel.
        self.uc_kare = uc_kare
        self.g1 = None   # t-1
        self.g2 = None   # t-2
        self.M12 = BIRIM.copy()  # t-2 -> t-1
        self._son_maske = None

    def kare_ekle(self, gri, M):
        """Kare islendikten SONRA cagrilir (ucuz: sadece kopya + kaydirma).

        M: bu karenin ego donusumu (t-1 -> t). Kaydirmadan sonra
        g1 = I_t, g2 = I_{t-1}, M12 = (t-1 -> t) olur.
        """
        self.g2 = self.g1
        self.M12 = M.copy()
        self.g1 = gri.copy()

    def hazir(self):
        return self.g1 is not None and (self.g2 is not None or not self.uc_kare)

    def adaylar(self, gri, M):
        """Pahali adim: sadece gerektiginde cagir (kayipta ya da periyodik dogrulamada)."""
        if not self.hazir():
            return [], None
        h, w = gri.shape
        w1 = cv2.warpAffine(self.g1, M, (w, h), flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_REPLICATE)
        d = cv2.absdiff(gri, w1)
        if self.uc_kare:
            M2 = bileske(self.M12, M)
            w2 = cv2.warpAffine(self.g2, M2, (w, h), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_REPLICATE)
            d = np.minimum(d, cv2.absdiff(gri, w2))
        d = cv2.GaussianBlur(d, (5, 5), 0)
        # kenarlarda warp artefakti olur -> kirp
        k = 8
        d[:k], d[-k:], d[:, :k], d[:, -k:] = 0, 0, 0, 0

        esik = max(self.min_esik, float(d.mean() + self.esik_k * d.std()))
        _, ikili = cv2.threshold(d, esik, 255, cv2.THRESH_BINARY)
        ikili = cv2.morphologyEx(ikili, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        ikili = cv2.dilate(ikili, np.ones((3, 3), np.uint8))
        self._son_maske = ikili

        n, _, stats, cent = cv2.connectedComponentsWithStats(ikili, 8)
        out = []
        for i in range(1, n):
            x, y, bw, bh, alan = stats[i]
            if alan < self.min_alan or bw > self.max_kenar or bh > self.max_kenar:
                continue
            if max(bw, bh) / max(1, min(bw, bh)) > 9:
                continue
            out.append({"kutu": np.array([x, y, bw, bh], np.float32),
                        "merkez": np.array(cent[i], np.float32),
                        "alan": float(alan),
                        "guc": float(d[y:y + bh, x:x + bw].mean())})
        out.sort(key=lambda c: -c["alan"])
        return out[:40], d


def rafine_kutu(bgr, merkez, boyut, buyutme=3.0, min_esik=16.0,
                hedef_renk=None, renk_tol=60.0):
    """Hareket lekesini duzgun bir kutuya cevir.

    Leke, cismin t-1 ve t konumlarinin BIRLESIMI oldugu icin hareket yonunde
    uzar ve dilate ile sisirilir -> kutu olarak kotudur.
    Burada kucuk bir pencerede yerel arka plan rengi (medyan) cikarilir,
    merkezdeki baglantili bilesenin sinir kutusu alinir. Ucuz ve keskin.
    Komsu araca atlamaz cunku sadece MERKEZI iceren bilesen kabul edilir.
    """
    cx, cy = float(merkez[0]), float(merkez[1])
    w = max(7, int(round(boyut[0] * buyutme)) | 1)
    h = max(7, int(round(boyut[1] * buyutme)) | 1)
    pen = cv2.getRectSubPix(bgr, (w, h), (cx, cy)).astype(np.float32)
    med = np.median(pen.reshape(-1, 3), 0)
    d = np.linalg.norm(pen - med, axis=2)
    esik = max(min_esik, float(np.percentile(d, 82)))
    m = (d > esik).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    n, lbl, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n < 2:
        return None
    ky, kx = h // 2, w // 2
    et = lbl[ky, kx]
    if et == 0:  # merkez bos: en yakin bileseni ara
        ys, xs = np.nonzero(lbl)
        if len(ys) == 0:
            return None
        i = np.argmin((ys - ky) ** 2 + (xs - kx) ** 2)
        if (ys[i] - ky) ** 2 + (xs[i] - kx) ** 2 > (0.35 * max(boyut)) ** 2 + 4:
            return None
        et = lbl[ys[i], xs[i]]
    x, y, bw, bh, _ = stats[et]
    oran = np.array([bw, bh], np.float32) / np.maximum(boyut, 1.0)
    if not (0.35 < oran.mean() < 2.6):
        return None
    # RENK KAPISI: yuksek kontrastli her leke arac degil. Serit cizgileri,
    # yol kenari, golge hepsi medyandan uzaktir. Hedefin bilinen rengine
    # uymayan lekeyi kabul etmektense rafine etmemek daha iyidir.
    if hedef_renk is not None:
        sec = (lbl[y:y + bh, x:x + bw] == et)
        if sec.sum() < 1:
            return None
        ort = pen[y:y + bh, x:x + bw][sec].mean(0)
        if float(np.linalg.norm(ort - np.asarray(hedef_renk, np.float32))) > renk_tol:
            return None
    return np.array([cx - w / 2 + x, cy - h / 2 + y, bw, bh], np.float32)


class Imza:
    """Hedefin hafif gorunum parmak izi: ortalama renk + kucuk normalize sablon + boyut.

    Toplam ~150 sayi. Derin oznitelik yok; kucuk hedefte zaten anlamli olmazdi.
    """
    S = 12

    def __init__(self):
        self.renk = None
        self.sablon = None
        self.boyut = None

    @staticmethod
    def _yamalar(bgr, gri, kutu):
        x, y, w, h = kutu
        cx, cy = x + w / 2, y + h / 2
        iw, ih = max(2, int(w * 0.8)), max(2, int(h * 0.8))
        renk = cv2.getRectSubPix(bgr, (iw, ih), (float(cx), float(cy))).reshape(-1, 3).mean(0)
        p = cv2.getRectSubPix(gri, (max(3, int(w * 1.3)), max(3, int(h * 1.3))),
                              (float(cx), float(cy)))
        p = cv2.resize(p, (Imza.S, Imza.S), interpolation=cv2.INTER_AREA).astype(np.float32)
        p = (p - p.mean()) / (p.std() + 1e-5)
        return renk.astype(np.float32), p

    def baslat(self, bgr, gri, kutu):
        self.renk, self.sablon = self._yamalar(bgr, gri, kutu)
        self.boyut = np.array(kutu[2:], np.float32)

    def guncelle(self, bgr, gri, kutu, lr=0.05):
        r, s = self._yamalar(bgr, gri, kutu)
        self.renk = (1 - lr) * self.renk + lr * r
        self.sablon = (1 - lr) * self.sablon + lr * s
        self.boyut = (1 - lr) * self.boyut + lr * np.array(kutu[2:], np.float32)

    def benzerlik(self, bgr, gri, kutu):
        """0..1 arasi gorunum benzerligi (renk + sablon + boyut)."""
        r, s = self._yamalar(bgr, gri, kutu)
        s_renk = float(np.exp(-np.linalg.norm(r - self.renk) / 45.0))
        ncc = float((self.sablon * s).mean() / (
            self.sablon.std() * s.std() + 1e-5))
        s_sab = 0.5 * (np.clip(ncc, -1, 1) + 1)
        a1 = max(1.0, self.boyut[0] * self.boyut[1])
        a2 = max(1.0, kutu[2] * kutu[3])
        s_boy = float(np.exp(-abs(np.log(a2 / a1))))
        return 0.40 * s_renk + 0.40 * s_sab + 0.20 * s_boy, s_renk, s_sab, s_boy
