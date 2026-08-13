"""Hedef takip orkestratoru: ego-motion + MOSSE + Kalman + yeniden tespit.

Durum makinesi
--------------
    KILITLI  : MOSSE guveniyor, ogreniyor
    SUPHELI  : PSR dustu -> ogrenmeyi DURDUR, Kalman ile devam et (coast)
    ARAMA    : hedef kayip -> tespit modulu aday uretiyor, imza ile eslestir
    KAYIP    : uzun sure bulunamadi

Ogrenmeyi supheli durumda durdurmak kritik: MOSSE kaybettigi anda ogrenmeye
devam ederse asfalti/baska araci ogrenir ve bir daha donemez.
"""
import time

import cv2
import numpy as np

from .egomotion import EgoMotion
from .cekirdekler import CEKIRDEKLER
from .tespit import HareketTespit, Imza, rafine_kutu

KILITLI, SUPHELI, ARAMA, KAYIP = "KILITLI", "SUPHELI", "ARAMA", "KAYIP"


class Kalman:
    """Sabit hizli 4 durumlu KF: [x, y, vx, vy], goruntu koordinatlarinda.

    Ego-motion her adimda duruma DOGRUDAN uygulanir; boylece hiz vektoru
    kameranin degil, ARACIN gercek hareketini temsil eder.
    """

    MAX_HIZ = 35.0  # px/kare - guvenlik siniri

    def __init__(self, x, y, q=0.8, r=2.5):
        self.x = np.array([x, y, 0.0, 0.0], np.float32)
        self.P = np.diag([4.0, 4.0, 25.0, 25.0]).astype(np.float32)
        self.F = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
        self.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
        self.Q = np.diag([q * 0.25, q * 0.25, q, q]).astype(np.float32)
        self.R0 = float(r)

    def tahmin(self, M):
        A, t = M[:, :2], M[:, 2]
        self.x[:2] = A @ self.x[:2] + t
        self.x[2:] = A @ self.x[2:]           # hiz da doner/olceklenir
        T = np.zeros((4, 4), np.float32)
        T[:2, :2] = A
        T[2:, 2:] = A
        self.P = T @ self.P @ T.T
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        self._hiz_sinirla()

    def _hiz_sinirla(self):
        v = float(np.linalg.norm(self.x[2:]))
        if v > self.MAX_HIZ:
            self.x[2:] *= self.MAX_HIZ / v

    def sondur(self, kat=0.97):
        """Olcum yokken hizi sondur: bozuk bir hiz tahminiyle ekrandan ucup gitme."""
        self.x[2:] *= kat

    def duzelt(self, z, r_carpan=1.0):
        R = np.eye(2, dtype=np.float32) * (self.R0 * r_carpan)
        S = self.H @ self.P @ self.H.T + R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ (np.asarray(z, np.float32) - self.H @ self.x)
        self.P = (np.eye(4, dtype=np.float32) - K @ self.H) @ self.P

    def ata(self, z):
        self.x[:2] = np.asarray(z, np.float32)
        self.P[:2, :2] = np.diag([4.0, 4.0])

    @property
    def konum(self):
        return self.x[:2].copy()

    @property
    def hiz(self):
        return self.x[2:].copy()


class HedefTakip:
    def __init__(self, cekirdek="renk_dcf",
                 psr_kilit=None, psr_supheli=None,
                 coast_kare=8, max_arama_kare=90,
                 aday_esik=0.52, aday_esik_kayip=0.62, aday_marj=0.06, arama_r0=28.0, arama_buyume=7.0, kayip_periyot=3,
                 dogrulama_araligi=4, izgara=32, min_kenar=4.0):
        self.ego = EgoMotion()
        self.tespit = HareketTespit()
        self.cekirdek = CEKIRDEKLER[cekirdek]() if isinstance(cekirdek, str) else cekirdek
        self.imza = Imza()
        # esikler cekirdege gore degisir (guven olcekleri ayni degil)
        self.psr_kilit = self.cekirdek.esik_kilit if psr_kilit is None else psr_kilit
        self.psr_supheli = self.cekirdek.esik_supheli if psr_supheli is None else psr_supheli
        self.coast_kare = coast_kare
        self.max_arama_kare = max_arama_kare
        self.aday_esik = aday_esik
        self.aday_esik_kayip = aday_esik_kayip
        self.aday_marj = aday_marj
        self.arama_r0 = arama_r0
        self.arama_buyume = arama_buyume
        self.kayip_periyot = kayip_periyot
        self.dogrulama_araligi = dogrulama_araligi
        self.min_kenar = min_kenar

        self.durum = KAYIP
        self.kf = None
        self.boyut = None
        self.kayip = 0
        self.kare = 0
        self.psr = 0.0
        self.son_adaylar = []
        self.sure = {}

    # ------------------------------------------------------------------
    # ILK TESPIT: hedef listesini uret (kullanici / otomatik secim icin)
    # ------------------------------------------------------------------
    def tarama(self, bgr):
        """Her karede cagir; hareketli arac adaylarini dondurur.

        Ilk 3 karede bos doner (fark icin gecmis gerekli). Park halindeki
        araclar hareket etmedigi icin listede CIKMAZ - istenen davranis.
        """
        gri = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        M, _ = self.ego.guncelle(gri)
        adaylar, _ = self.tespit.adaylar(gri, M)
        self.tespit.kare_ekle(gri, M)
        self.son_adaylar = adaylar
        return adaylar

    def kilitle(self, bgr, kutu):
        gri = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        kutu = np.asarray(kutu, np.float32)
        # hareket lekesi kaba bir kutudur -> renk kontrastiyla keskinlestir
        r = rafine_kutu(bgr, kutu[:2] + kutu[2:] / 2, kutu[2:])
        if r is not None:
            kutu = r
        self.boyut = np.maximum(kutu[2:], self.min_kenar)
        # kutu boyutunun fizik capasi: kilit anindaki boyut x birikimli ego olcegi.
        # Ego olcegi 400 karede ~%5 kayiyor; tek bir bozuk rafine ise kutuyu
        # %65 sisirebiliyor. Bu yuzden boyut bu bandin disina cikamaz.
        # OLCUM tabanli capa: her basarili rafine dogrudan kutuyu OLCER.
        # (Ego olceginin kare kare carpimi ustel hata biriktirdigi icin terk edildi.)
        self.boyut_olculen = self.boyut.copy()
        self.kf = Kalman(kutu[0] + kutu[2] / 2, kutu[1] + kutu[3] / 2)
        self.cekirdek.baslat(bgr, gri, np.r_[kutu[:2], self.boyut])
        self.imza.baslat(bgr, gri, np.r_[kutu[:2], self.boyut])
        self.durum = KILITLI
        self.kayip = 0
        return self.kutu

    # ------------------------------------------------------------------
    @property
    def kutu(self):
        if self.kf is None:
            return None
        c, b = self.kf.konum, self.boyut
        return np.array([c[0] - b[0] / 2, c[1] - b[1] / 2, b[0], b[1]], np.float32)

    def guncelle(self, bgr):
        t_bas = time.perf_counter()
        gri = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        H, W = gri.shape
        self.kare += 1
        s = {}

        t0 = time.perf_counter()
        M, ego_guven = self.ego.guncelle(gri, self.kutu if self.durum == KILITLI else None)
        s["ego"] = (time.perf_counter() - t0) * 1e3

        # olcek: arka planin buyume/kuculme katsayisi = irtifa degisimi
        olc = float(np.clip(self.ego.olcek_katsayisi, 0.90, 1.10))
        self.kf.tahmin(M)
        self.boyut = np.maximum(self.boyut * olc, self.min_kenar)

        t0 = time.perf_counter()
        if self.durum in (KILITLI, SUPHELI):
            self._takip_adimi(bgr, gri)
        s["mosse"] = (time.perf_counter() - t0) * 1e3

        t0 = time.perf_counter()
        if self.durum in (ARAMA, KAYIP):
            self._arama_adimi(bgr, gri, M)
        elif self.dogrulama_araligi and self.kare % self.dogrulama_araligi == 0:
            self._boyut_tazele(bgr)
        s["tespit"] = (time.perf_counter() - t0) * 1e3

        # kadraj disi: tahmini SINIRA CAPALA ve hizi sifirla.
        # Aksi halde olu hesap kareler boyunca uzaklasip (-600, 150) gibi
        # anlamsiz bir konuma gider; sonra hedef geri gorunse bile mesafe
        # kapisi onu eler ve sistem bir daha asla kilitlenemez.
        c = self.kf.konum
        if not (-20 < c[0] < W + 20 and -20 < c[1] < H + 20):
            self.durum = KAYIP
            self.kf.x[0] = float(np.clip(c[0], 0, W - 1))
            self.kf.x[1] = float(np.clip(c[1], 0, H - 1))
            self.kf.x[2:] = 0.0

        self._boyut_sinirla()
        self.tespit.kare_ekle(gri, M)
        s["toplam"] = (time.perf_counter() - t_bas) * 1e3
        self.sure = s
        return {"kutu": self.kutu, "durum": self.durum, "psr": self.psr,
                "kayip": self.kayip, "ego_guven": ego_guven, "olcek": olc, "sure": s}

    # ------------------------------------------------------------------
    def _takip_adimi(self, bgr, gri):
        tahmin = self.kf.konum
        yeni, psr = self.cekirdek.ara(bgr, gri, tahmin, self.boyut)
        self.psr = psr
        sicrama = float(np.linalg.norm(np.asarray(yeni) - tahmin))
        maks_sicrama = max(6.0, 0.9 * float(self.boyut.max()))

        if psr >= self.psr_kilit and sicrama <= maks_sicrama:
            self.kf.duzelt(yeni)
            self.durum, self.kayip = KILITLI, 0
            # kucuk hedefte yavas ogren: surukleme riski yuksek
            lr = 0.125 if self.boyut.max() > 18 else 0.04
            self.cekirdek.ogren(bgr, gri, self.kf.konum, self.boyut, lr)
            self.imza.guncelle(bgr, gri, self.kutu, lr=0.03)
        elif psr >= self.psr_supheli and sicrama <= maks_sicrama * 1.6:
            self.kf.duzelt(yeni, r_carpan=6.0)   # zayif olcum, az guven
            self.durum = SUPHELI
            self.kayip += 1
        else:
            self.durum = SUPHELI                  # olcum yok: sadece Kalman
            self.kf.sondur()
            self.kayip += 1

        if self.kayip > self.coast_kare:
            self.durum = ARAMA

    def _arama_adimi(self, bgr, gri, M):
        """Yeniden tespit. ASLA kalici olarak pes etmez.

        Uzun kayipta (KAYIP) her karede degil, `kayip_periyot` karede bir aranir:
        boylece umutsuz durumda FPS dusmez ama sistem hedefi aramayi surdurur.
        Arama yaricapi buyudukce konum terimi guvenilmez hale gelir; skor
        agirligi kademeli olarak GORUNUME kayar.
        """
        self.kayip += 1
        gecen = self.kayip - self.coast_kare
        if gecen > self.max_arama_kare:
            self.durum = KAYIP
            if self.kare % self.kayip_periyot:
                return
        adaylar, _ = self.tespit.adaylar(gri, M)
        self.son_adaylar = adaylar
        if not adaylar:
            return

        tahmin = self.kf.konum
        H, W = gri.shape
        tam = float(np.hypot(W, H))
        if self.durum == KAYIP:
            # uzun kayip: konum tahmini artik bilgi tasimiyor -> TUM kareyi
            # sadece gorunum imzasiyla tara
            r, w_konum = np.inf, 0.0
        else:
            r = min(tam, self.arama_r0 + self.arama_buyume * gecen)
            w_konum = 0.45 * float(np.clip(1.0 - (r - self.arama_r0) / tam, 0.15, 1.0))
        en_iyi, en_skor, ikinci = None, 0.0, 0.0
        for a in adaylar:
            d = float(np.linalg.norm(a["merkez"] - tahmin))
            if d > r:
                continue
            # blob kutusu yerine TAHMIN EDILEN boyutu kullan: daha kararli
            kutu = np.array([a["merkez"][0] - self.boyut[0] / 2,
                             a["merkez"][1] - self.boyut[1] / 2,
                             self.boyut[0], self.boyut[1]], np.float32)
            s_gor, *_ = self.imza.benzerlik(bgr, gri, kutu)
            skor = w_konum * (1.0 - d / r) + (1.0 - w_konum) * s_gor
            if skor > en_skor:
                en_iyi, en_skor, ikinci = (a, kutu), skor, en_skor
            elif skor > ikinci:
                ikinci = skor

        # BELIRSIZLIK KURALI: konum onbilgisi yokken (tum kare taramasi) sadece
        # "en yuksek skor" yetmez; en iyi aday ikinciyi belirgin farkla gecmeli.
        # Aksi halde benzer araclar arasinda rastgele birine kilitlenir.
        if en_iyi is not None and w_konum == 0.0:
            if en_skor < self.aday_esik_kayip or (en_skor - ikinci) < self.aday_marj:
                en_iyi = None

        if en_iyi is not None and en_skor >= self.aday_esik:
            a, kutu = en_iyi
            r2 = rafine_kutu(bgr, a["merkez"], self.boyut, hedef_renk=self.imza.renk)
            if r2 is not None:
                self.boyut = np.maximum(0.5 * self.boyut + 0.5 * r2[2:], self.min_kenar)
                self.boyut_olculen = self.boyut.copy()
                kutu = np.r_[r2[:2] + r2[2:] / 2 - self.boyut / 2, self.boyut]
            self.kf.ata(kutu[:2] + kutu[2:] / 2)
            self.cekirdek.baslat(bgr, gri, kutu)
            self.durum, self.kayip = KILITLI, 0
            self.psr = 99.0
        elif self.durum != KAYIP:
            self.durum = ARAMA

    def _boyut_sinirla(self):
        """Kutuyu son OLCULEN boyutun etrafinda bir banda hapset.

        Ego olcegi kisa vadede dogru (irtifa degisimine aninda tepki verir) ama
        birikimli hatasi ustel. Rafine ise gurultulu ama YANSIZ. Ikisini boyle
        birlestirmek her ikisinin de zayifligini kapatiyor.
        """
        b = np.maximum(self.boyut_olculen, self.min_kenar)
        self.boyut = np.clip(self.boyut, 0.60 * b, 1.70 * b)

    def _boyut_tazele(self, bgr):
        """Periyodik capa: kutuyu yerel renk kontrastiyla yeniden olc.

        Iki derdi birden cozer:
          * ego olcegi kareler boyunca birikimli carpim oldugu icin uzun
            irtifa rampalarinda yavasca kayar -> geri toplar
          * MOSSE'nin yavas surukleniyor olmasini merkezden duzeltir
        Maliyeti dusuk: tam kare degil, hedefin etrafinda kucuk bir pencere.
        """
        r = rafine_kutu(bgr, self.kf.konum, self.boyut, hedef_renk=self.imza.renk)
        if r is None:
            return
        self.boyut = np.maximum(0.75 * self.boyut + 0.25 * r[2:], self.min_kenar)
        self.boyut_olculen = 0.85 * self.boyut_olculen + 0.15 * np.maximum(r[2:], self.min_kenar)
        yeni_c = r[:2] + r[2:] / 2
        if float(np.linalg.norm(yeni_c - self.kf.konum)) < 0.6 * float(self.boyut.max()):
            self.kf.duzelt(yeni_c, r_carpan=1.0)
