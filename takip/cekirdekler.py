"""Takilip cikarilabilir izleme cekirdekleri - hepsi ayni arayuz.

    baslat(bgr, gri, kutu)
    ara(bgr, gri, merkez, boyut) -> (yeni_merkez, guven)
    ogren(bgr, gri, merkez, boyut, lr)
    ego_guncelle(M)                       # istege bagli, varsayilan: hicbir sey

`guven` olceklerini kiyaslanabilir tutmak icin hepsi kabaca "PSR benzeri"
bir sayi dondurur: ~3 altinda kotu, ~6 uzeri saglam.

Neden birden fazla cekirdek: 20x10 px'lik bir aracta DOKU diye bir sey kalmaz,
geriye RENK ve HAREKET kalir. Hangi sinyalin ne zaman hayatta kaldigini
olcmeden dogru cekirdek secilemez.
"""
import math

import cv2
import numpy as np

from .mosse import MOSSE, _hann


class _Cekirdek:
    """Ortak taban: ego bilgisini KULLANMAYAN cekirdekler icin no-op.

    `izleyici.py` her karede kosulsuz `ego_guncelle(M)` cagirir; hangi
    cekirdegin bu bilgiyi kullandigini bilmek zorunda kalmasin diye
    varsayilan burada durur.
    """

    def ego_guncelle(self, M):
        return


class MosseCekirdek(_Cekirdek):
    """Tek kanal (gri) korelasyon filtresi. En ucuzu."""
    ad = "mosse"
    esik_kilit, esik_supheli = 5.5, 3.2

    def __init__(self, izgara=32, dolgu=2.0, lr=0.125):
        self.f = MOSSE(izgara=izgara, dolgu=dolgu, lr=lr)

    def baslat(self, bgr, gri, kutu):
        self.f.baslat(gri, kutu)

    def ara(self, bgr, gri, merkez, boyut):
        return self.f.ara(gri, merkez, boyut)

    def ogren(self, bgr, gri, merkez, boyut, lr=None):
        self.f.ogren(gri, merkez, boyut, lr)


class RenkDcfCekirdek(_Cekirdek):
    """Cok kanalli DCF: gri + renk fark kanallari.

    Kucuk hedefte gri doku biter ama arac rengi yoldan ayrilmaya devam eder.
    Kanallar: [gri, B-G, R-G] -> aydinlatmaya gore normalize edilmis renk.
    Maliyet tek kanalin ~3 kati ama 32x32'de bu hala mikro saniyeler.

    KAPALI CEVRIM ACI KESTIRIMI (A3.9 Faz C, deney 2)
    -------------------------------------------------
    Korelasyon filtresi donme-degismez degildir. Kamera yaw yapinca hedefin
    goruntudeki durusu doner, sablon eksen hizali kesilmeye devam eder ve her
    karede biraz daha uyumsuzlasir (Faz B, G3 ailesi: yaw genligi +-55 derece
    iken PSR 113 -> 21, IoU 0.579, 133. karede drift).

    DENEY 1'DE NE OLDU. Ilk denemede aci ego M'sinden ACIK CEVRIM biriktirildi
    ve geri alindi. Iki kusuru olculdu:
      * Sizinti: donme OLMAYAN senaryolarda bile aci sifirda kalmadi
        (G4_kritik'te -9.4 derece birikti, gercek 0). Nedeni pitch'te benzerlik
        donusumunun perspektifi temsil edememesi ve artigin bir kismini SAHTE
        DONME olarak sogurmasi (e_model 4.62 px). Olu bant bunu cozmez, cunku
        0.30 derece/kare gurultu degil, benzerligin gercekten soyledigi seydir.
      * Ornekleyici sizintisi: yamayi her karede warpAffine ile kesmek
        getRectSubPix'ten farkli ornekler ve TEK BASINA Gazebo'da 8/14,
        VisDrone'da 0/2 ile net olumsuzdu.

    BURADAKI TASARIM ikisini de kapatir:
      1. Aci BIRIKTIRILMEZ. Ego yalnizca TOHUM verir; secim her karede sablon
         yanitiyla yapilir (`ara` icinde uc aday aci denenir, PSR'si en yuksek
         olan secilir). Sablon o acida ogrenildigi icin olcut kendi capasina
         geri doner: ego yanlilik uretse bile arama onu her karede geri ceker.
      2. Donme suphesi yokken TEK aday (aci = 0) denenir ve eski
         `getRectSubPix` yolu AYNEN kullanilir - o karelerde davranis A3.8 ile
         BIREBIR aynidir, ek maliyet de sifirdir.

    TEK YENI SABIT: `tolerans_px`. Adim ve esik ondan turetilir:
        aci_adim   = derece(tolerans_px / kutu_yari_kosegeni)
                     -> bir adimlik hata kutu kenarinda tolerans_px kayma yapar
        dteta_esik = aci_adim / 2
                     -> ego kare-arasi donmesi yarim adimi gecince suphelen
    Kucuk hedefte kutu yari kosegeni kucuktur, adim buyur ve esik yukselir;
    yani 12x5 px'lik bir hedefte donme telafisi kendiliginden devreye girmez.
    Dogru davranis: o boyutta zaten donmeyi tasiyacak doku yoktur.
    """
    ad = "renk_dcf"
    esik_kilit, esik_supheli = 9.0, 4.5

    def __init__(self, izgara=32, dolgu=2.0, lr=0.09, sigma=2.0, eps=1e-4,
                 tolerans_px=1.0):
        self.N = izgara
        self.dolgu = dolgu
        self.lr = lr
        self.eps = eps
        self.han = _hann(izgara)
        ax = np.arange(izgara, dtype=np.float32) - izgara // 2
        gx, gy = np.meshgrid(ax, ax)
        g = np.exp(-(gx ** 2 + gy ** 2) / (2 * sigma ** 2)).astype(np.float32)
        self.G = np.fft.fft2(g)
        self.A = self.B = None
        self.tolerans_px = float(tolerans_px)
        self.aci = 0.0          # secili sablon acisi (derece) - BIRIKIMLI DEGIL
        self.dteta = 0.0        # ego'nun bu kare icin olctugu donme (derece)
        self.aktif = False      # bu karede aci aramasi yapiliyor mu
        self.aci_adim = 0.0     # baslat() kutu boyutundan turetir
        self.dteta_esik = float("inf")

    def ego_guncelle(self, M):
        """Ego'nun olctugu kare-arasi goruntu donmesini SAKLA (biriktirme).

        M benzerliktir: A = s x R(theta), theta = atan2(M[1,0], M[0,0]).
        Bu sayi yalnizca iki ise yarar: (a) donme suphesi kapisi,
        (b) aci aramasina tohum. Duruma yazilmaz.
        """
        self.dteta = math.degrees(math.atan2(float(M[1, 0]), float(M[0, 0])))

    def _yama(self, bgr, merkez, w, h, aci):
        """Yamayi kes. aci arama KAPALIYKEN eski yol; acikken dondurulmus yol.

        Ayrim bilerek `self.aktif` uzerinden, `aci != 0` uzerinden DEGIL:
        arama sirasinda uc adayin (biri 0 olabilir) hepsi AYNI ornekleyiciyle
        kesilmeli, yoksa secim ornekleyici farkindan yanlilik kapar - deney
        1'in birinci kusuru tam buydu.
        """
        cx, cy = float(merkez[0]), float(merkez[1])
        if not self.aktif:
            return cv2.getRectSubPix(bgr, (w, h), (cx, cy))
        W = cv2.getRotationMatrix2D((cx, cy), aci, 1.0)
        W[0, 2] += w / 2.0 - cx
        W[1, 2] += h / 2.0 - cy
        return cv2.warpAffine(bgr, W, (w, h), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)

    def _kanallar(self, bgr, merkez, boyut, aci=None):
        w = max(4, int(round(boyut[0] * self.dolgu)))
        h = max(4, int(round(boyut[1] * self.dolgu)))
        p = self._yama(bgr, merkez, w, h,
                       self.aci if aci is None else aci)
        p = cv2.resize(p, (self.N, self.N), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        b, g_, r = p[..., 0], p[..., 1], p[..., 2]
        top = b + g_ + r + 1.0
        kan = np.stack([(b + g_ + r) / 3.0, 255 * (b - g_) / top, 255 * (r - g_) / top])
        for i in range(len(kan)):
            c = kan[i]
            kan[i] = (c - c.mean()) / (c.std() + 1e-5) * self.han
        return kan, (w, h)

    def baslat(self, bgr, gri, kutu):
        # Yeni kilit = yeni referans durus ve yeni kutu olcegi. Aci sifirlanir,
        # adim/esik kutunun yari kosegeninden TURETILIR (bkz. sinif basligi).
        self.aci, self.aktif = 0.0, False
        r = 0.5 * float(np.hypot(max(1.0, kutu[2]), max(1.0, kutu[3])))
        self.aci_adim = math.degrees(self.tolerans_px / max(1.0, r))
        self.dteta_esik = 0.5 * self.aci_adim
        merkez = (kutu[0] + kutu[2] / 2, kutu[1] + kutu[3] / 2)
        kan, _ = self._kanallar(bgr, merkez, kutu[2:])
        F = np.fft.fft2(kan, axes=(1, 2))
        self.A = self.G[None] * np.conj(F)
        self.B = (F * np.conj(F)).sum(0)

    def _yanit(self, bgr, merkez, boyut, aci):
        kan, (w, h) = self._kanallar(bgr, merkez, boyut, aci)
        F = np.fft.fft2(kan, axes=(1, 2))
        r = np.real(np.fft.ifft2((self.A * F).sum(0) / (self.B + self.eps)))
        return _tepe(r, self.N, merkez, w, h)

    def ara(self, bgr, gri, merkez, boyut):
        # Donme suphesi: ego bu karede yarim adimdan fazla donme olcmus mu,
        # ya da sablon zaten dondurulmus durumda mi (o zaman 0'a geri
        # donebilmek icin arama ACIK kalmali).
        self.aktif = (abs(self.dteta) >= self.dteta_esik) or (self.aci != 0.0)

        if not self.aktif:
            # A3.8 yolu, birebir: tek aday, eski ornekleyici, aci = 0.
            return self._yanit(bgr, merkez, boyut, 0.0)

        # Ego yalnizca TOHUM: nereye bakilacagini soyler, ne secilecegini degil.
        # Adaylar adim izgarasina oturtulur; boylece aci her zaman adimin tam
        # kati olur ve "aci kucuk" ile "aci = 0" ayni sey haline gelir.
        n = int(round((self.aci + self.dteta) / self.aci_adim))
        en_iyi = None
        for k in (n - 1, n, n + 1):
            aday = k * self.aci_adim
            yeni, psr = self._yanit(bgr, merkez, boyut, aday)
            # Olcut PSR: tepenin KENDI yan lobelerine gore keskinligi. Ham tepe
            # degeri denendi ve elendi - kanallar yama basina normalize edildigi
            # icin farkli acilarda olcegi tam kiyaslanabilir degil.
            if en_iyi is None or psr > en_iyi[0]:
                en_iyi = (psr, aday, yeni)
        psr, self.aci, yeni = en_iyi

        if self.aci:
            # tepe kaymasi DONDURULMUS yamada olculdu -> goruntu cercevesine
            # geri dondur.
            t = math.radians(self.aci)
            c, sn = math.cos(t), math.sin(t)
            dx, dy = yeni[0] - merkez[0], yeni[1] - merkez[1]
            yeni = (merkez[0] + c * dx - sn * dy, merkez[1] + sn * dx + c * dy)
        return yeni, psr

    def ogren(self, bgr, gri, merkez, boyut, lr=None):
        lr = self.lr if lr is None else lr
        kan, _ = self._kanallar(bgr, merkez, boyut)
        F = np.fft.fft2(kan, axes=(1, 2))
        self.A = (1 - lr) * self.A + lr * (self.G[None] * np.conj(F))
        self.B = (1 - lr) * self.B + lr * (F * np.conj(F)).sum(0)


class NccCekirdek(_Cekirdek):
    """Normalize edilmis capraz korelasyon ile sablon eslestirme.

    Kucuk hedefte kaba kuvvet zaten ucuz (`matchTemplate` SIMD optimize).
    Surukleme yok denecek kadar az cunku sablon yavas guncellenir; buna karsilik
    gorunum degisimine (donme, isik) MOSSE'den daha kirilgan.
    """
    ad = "ncc"
    esik_kilit, esik_supheli = 3.2, 2.0

    def __init__(self, arama=1.6, lr=0.03, max_sablon=48):
        self.arama = arama
        self.lr = lr
        self.max_sablon = max_sablon
        self.sablon = None
        self.olcek = 1.0

    def _sablon_boyut(self, boyut):
        w, h = max(3, int(round(boyut[0]))), max(3, int(round(boyut[1])))
        s = min(1.0, self.max_sablon / max(w, h))
        return max(3, int(w * s)), max(3, int(h * s)), s

    def baslat(self, bgr, gri, kutu):
        w, h, s = self._sablon_boyut(kutu[2:])
        merkez = (kutu[0] + kutu[2] / 2, kutu[1] + kutu[3] / 2)
        p = cv2.getRectSubPix(gri, (max(3, int(kutu[2])), max(3, int(kutu[3]))), merkez)
        self.sablon = cv2.resize(p, (w, h)).astype(np.float32)
        self.olcek = s

    def ara(self, bgr, gri, merkez, boyut):
        tw, th, s = self._sablon_boyut(boyut)
        sab = self.sablon if self.sablon.shape[::-1] == (tw, th) else cv2.resize(self.sablon, (tw, th))
        # arama penceresi once GORUNTU pikselinde alinir, sonra sablon olcegine indirilir
        pw_g = int(round(boyut[0] * (1 + self.arama))) + 4
        ph_g = int(round(boyut[1] * (1 + self.arama))) + 4
        pen = cv2.getRectSubPix(gri, (pw_g, ph_g), (float(merkez[0]), float(merkez[1])))
        pw, ph = max(tw + 2, int(round(pw_g * s))), max(th + 2, int(round(ph_g * s)))
        pen = cv2.resize(pen, (pw, ph)).astype(np.float32)

        r = cv2.matchTemplate(pen, sab.astype(np.float32), cv2.TM_CCOEFF_NORMED)
        iy, ix = np.unravel_index(np.argmax(r), r.shape)
        # NCC skorunu PSR benzeri bir sayiya cevir (cekirdekler kiyaslanabilsin)
        m = np.ones_like(r, bool)
        m[max(0, iy - 2):iy + 3, max(0, ix - 2):ix + 3] = False
        yan = r[m]
        guven = float((r[iy, ix] - yan.mean()) / (yan.std() + 1e-5)) if yan.size > 4 else 0.0

        # sablon olceginden goruntu pikseline geri don
        dx = (ix + tw / 2 - pw / 2) * (pw_g / pw)
        dy = (iy + th / 2 - ph / 2) * (ph_g / ph)
        return (merkez[0] + float(dx), merkez[1] + float(dy)), guven

    def ogren(self, bgr, gri, merkez, boyut, lr=None):
        lr = self.lr if lr is None else lr
        w, h, _ = self._sablon_boyut(boyut)
        p = cv2.getRectSubPix(gri, (max(3, int(boyut[0])), max(3, int(boyut[1]))),
                              (float(merkez[0]), float(merkez[1])))
        p = cv2.resize(p, self.sablon.shape[::-1]).astype(np.float32)
        self.sablon = (1 - lr) * self.sablon + lr * p


class AkisCekirdek(_Cekirdek):
    """Median Flow benzeri: hedefin ICINDEKI noktalari LK ile tasi.

    Ileri-geri hata dogal bir basarisizlik dedektoru. 10x5 px hedefte kose
    bulamaz -> orada coker; sinirini olcmek testin amaci.
    """
    ad = "akis"
    esik_kilit, esik_supheli = 4.0, 2.0

    def __init__(self, n=24):
        self.n = n
        self.lk = dict(winSize=(11, 11), maxLevel=2,
                       criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 12, 0.03))
        self.onceki = None

    def baslat(self, bgr, gri, kutu):
        self.onceki = gri.copy()

    def ara(self, bgr, gri, merkez, boyut):
        if self.onceki is None:
            return merkez, 0.0
        w, h = max(4, boyut[0]), max(4, boyut[1])
        x0, y0 = merkez[0] - w / 2, merkez[1] - h / 2
        gx, gy = np.meshgrid(np.linspace(x0, x0 + w, 6), np.linspace(y0, y0 + h, 4))
        p0 = np.stack([gx.ravel(), gy.ravel()], 1).astype(np.float32).reshape(-1, 1, 2)
        p1, st, _ = cv2.calcOpticalFlowPyrLK(self.onceki, gri, p0, None, **self.lk)
        p0r, st2, _ = cv2.calcOpticalFlowPyrLK(gri, self.onceki, p1, None, **self.lk)
        hata = np.abs(p0 - p0r).reshape(-1, 2).max(1)
        iyi = (st.ravel() == 1) & (st2.ravel() == 1) & (hata < 1.0)
        if iyi.sum() < 4:
            return merkez, 0.0
        d = (p1 - p0).reshape(-1, 2)[iyi]
        dm = np.median(d, 0)
        yayilim = float(np.median(np.abs(d - dm)))
        guven = float(iyi.sum()) / len(p0) * 10.0 / (1.0 + 3.0 * yayilim)
        return (merkez[0] + float(dm[0]), merkez[1] + float(dm[1])), guven

    def ogren(self, bgr, gri, merkez, boyut, lr=None):
        self.onceki = gri.copy()


def _tepe(r, N, merkez, w, h):
    iy, ix = np.unravel_index(np.argmax(r), r.shape)
    tepe = r[iy, ix]
    dx = dy = 0.0
    if 0 < ix < N - 1:
        l, sag = r[iy, ix - 1], r[iy, ix + 1]
        d = l - 2 * tepe + sag
        if abs(d) > 1e-9:
            dx = 0.5 * (l - sag) / d
    if 0 < iy < N - 1:
        u, alt = r[iy - 1, ix], r[iy + 1, ix]
        d = u - 2 * tepe + alt
        if abs(d) > 1e-9:
            dy = 0.5 * (u - alt) / d
    m = np.ones_like(r, bool)
    m[max(0, iy - 5):iy + 6, max(0, ix - 5):ix + 6] = False
    yan = r[m]
    psr = float((tepe - yan.mean()) / (yan.std() + 1e-5))
    return (merkez[0] + ((ix + dx) - N // 2) * w / N,
            merkez[1] + ((iy + dy) - N // 2) * h / N), psr


CEKIRDEKLER = {
    "mosse": MosseCekirdek,
    "renk_dcf": RenkDcfCekirdek,
    "ncc": NccCekirdek,
    "akis": AkisCekirdek,
}
