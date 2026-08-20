"""Hedef takip orkestratoru: ego-motion + MOSSE + Kalman + yeniden tespit.

Durum makinesi
--------------
    KILITLI  : MOSSE guveniyor, ogreniyor
    SUPHELI  : PSR dustu -> ogrenmeyi DURDUR, Kalman ile devam et (coast)
    ARAMA    : hedef kayip -> tespit modulu aday uretiyor, imza ile eslestir
    KAYIP    : uzun sure bulunamadi

Ogrenmeyi supheli durumda durdurmak kritik: MOSSE kaybettigi anda ogrenmeye
devam ederse asfalti/baska araci ogrenir ve bir daha donemez.

BAGIMSIZ DOGRULAMA (A3.8)
-------------------------
PSR bir KIMLIK olcusu degil, filtrenin IC TUTARLILIK olcusudur: filtre neyi
ogrendiyse onu guvenle bulur. Filtre yola kayarsa yolu ogrenir, PSR duSMEZ -
tam tersine yukselir. Olculdu: uav0000268_05773_v'de kopmadan sonra PSR
12 -> 46 tirmaniyor ve sistem 978 karenin %99'unda KILITLI kaliyor, IoU 0.

Bu yuzden KILITLI durumunun PSR'dan BAGIMSIZ iki denetleyicisi var:

  1) IMZA: kilit anindaki gorunum imzasi DONDURULUR (`imza_ref`) ve bir daha
     guncellenmez. Periyodik olarak mevcut kutu bu referansla karsilastirilir.
     Yeniden tespit ve renk kapisi ise ayri, UYARLANAN bir imza kullanir
     (`imza`). Ikisi bilerek ayri: dogrulama capasini kaybetmemeli, esleStirme
     ise isik/gorunum degisimine uyum saglamali. Tek imzayla denendi ve
     test6'da ID switch 1 -> 2 oldu (oklüzyondan cikan arac artik eski
     imzayla eslesmiyordu).
  2) ZEMINE CAKILMA: takip kutusu ego telafisinden sonra hic hareket etmiyorsa
     arac degil, yer takip ediliyordur.

Ikisi birbirinin korunu kapatir; A3.7 teshisinde olculen ayirt edicilikleri
(medyan degerler):

    dizi        durum    imza benzerligi   ego-telafili kutu hareketi
    117/23      DOGRU    0.716 (p5 0.588)  5.53 px  <- ikisini de gecer
    268/31      YANLIS   0.824             0.36 px  <- (2) yakalar
    182/127     YANLIS   0.430             1.68 px  <- (1) yakalar

Tek basina imza yetmez: 268'de yanlis kilidin benzerligi 117'deki DOGRU
takiptan yuksek. Tek basina zemin testi de yetmez: gercekten duran bir arac
(182'nin dogru fazi, 0.58 px) yanlis alarm uretir. Bu yuzden ikisi ayri ayri
ve farkli sabirlarla calisir.
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
                 dogrulama_araligi=4, izgara=32, min_kenar=4.0,
                 kimlik_periyot=6, kimlik_esik=0.45, kimlik_sabir=2,
                 kimlik_hareket_kapisi=0.003, kimlik_min_kenar=10.0,
                 zemin_orani=0.0008, zemin_pencere=20, zemin_sabir=20,
                 zemin_dogrulama=True,
                 yasak_kare=30):
        self.ego = EgoMotion()
        self.tespit = HareketTespit()
        self.cekirdek = CEKIRDEKLER[cekirdek]() if isinstance(cekirdek, str) else cekirdek
        self.imza = Imza()          # uyarlanan: yeniden tespit + renk kapisi
        self.imza_ref = Imza()      # DONMUS referans: yalnizca dogrulama
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
        # --- bagimsiz dogrulama (A3.8) ---
        self.kimlik_periyot = kimlik_periyot      # kac karede bir imza kontrolu
        self.kimlik_esik = kimlik_esik            # dondurulmus imzaya asgari benzerlik
        self.kimlik_sabir = kimlik_sabir          # ard arda kac basarisiz kontrol
        self.kimlik_hareket_kapisi = kimlik_hareket_kapisi  # ustunde imza reddi yok
        self.kimlik_min_kenar = kimlik_min_kenar   # altinda imza anlamsiz
        self.zemin_orani = zemin_orani            # esik = bu oran x kare genisligi
        self.zemin_pencere = zemin_pencere        # kac karelik pencereye bakilir
        self.zemin_sabir = zemin_sabir            # kac kare ust uste esigin altinda
        self.zemin_dogrulama = zemin_dogrulama    # False -> yalnizca imza denetimi
        self.yasak_kare = yasak_kare              # reddedilen konum kac kare yasakli

        self.durum = KAYIP
        self.kf = None
        self.boyut = None
        self.kayip = 0
        self.kare = 0
        self.psr = 0.0
        self.son_adaylar = []
        self.sure = {}
        self.benzerlik = 1.0        # son imza kontrolunun sonucu (rapor icin)
        self.yanlis_kilit = 0       # kac kez yanlis kilit kirildi
        self._kimlik_hata = 0
        self._zemin_gecmis = []
        self._zemin_alt = 0
        self._hareketli = True        # kanit gelene kadar hedefin lehine varsay
        self._hareketli_guclu = True
        self._onceki_merkez = None
        self._yasak_merkez = None
        self._yasak_sayac = 0

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
        # REFERANS IMZA (imza_ref): burada dondurulur, bir daha guncellenmez.
        # Guncellenirse dogrulama kendi kendini onaylayan bir olcuye doner.
        self.imza.baslat(bgr, gri, np.r_[kutu[:2], self.boyut])
        self.imza_ref.baslat(bgr, gri, np.r_[kutu[:2], self.boyut])
        self.durum = KILITLI
        self.kayip = 0
        self._dogrulama_sifirla()
        return self.kutu

    def _dogrulama_sifirla(self):
        """Yeni guvenilir kilit: denetleyici sayaclari temizlenir."""
        self.benzerlik = 1.0
        self._kimlik_hata = 0
        self._zemin_gecmis = []
        self._zemin_alt = 0
        self._hareketli = True        # kanit gelene kadar hedefin lehine varsay
        self._hareketli_guclu = True
        self._onceki_merkez = None
        self._yasak_merkez = None
        self._yasak_sayac = 0

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

        # zemine cakilma testi icin: onceki kutu merkezinin ego ile ONGORULEN
        # yeni konumu. Gercek merkez buna esitse kutu araci degil, YERI takip
        # ediyordur (kamera hareketiyle birlikte suruklenip duruyor).
        ongoru = (None if self._onceki_merkez is None else
                  M[:, :2] @ self._onceki_merkez + M[:, 2])
        if self._yasak_sayac > 0 and self._yasak_merkez is not None:
            self._yasak_merkez = M[:, :2] @ self._yasak_merkez + M[:, 2]
            self._yasak_sayac -= 1

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
        else:
            if self.durum == KILITLI:
                self._bagimsiz_dogrula(bgr, gri, ongoru)
            if (self.durum in (KILITLI, SUPHELI) and self.dogrulama_araligi
                    and self.kare % self.dogrulama_araligi == 0):
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
        self._onceki_merkez = self.kf.konum.copy()
        s["toplam"] = (time.perf_counter() - t_bas) * 1e3
        self.sure = s
        return {"kutu": self.kutu, "durum": self.durum, "psr": self.psr,
                "kayip": self.kayip, "ego_guven": ego_guven, "olcek": olc,
                "benzerlik": self.benzerlik, "yanlis_kilit": self.yanlis_kilit,
                "sure": s}

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
            # Uyarlanan imza IKI kosulla ogrenir: kutu zeminden bagimsiz
            # hareket ediyor OLACAK ve DONMUS REFERANS hedefi hala taniyor
            # olacak. Ikincisi kritik - referans "bu artik o arac degil" derken
            # uyarlanan imza ogrenmeye devam ederse yol dokusunu ezberler,
            # sonra yeniden tespit de yol yamalarini hedefe benzetir. Olculdu:
            # bu kapi olmadan 182/127'de yanlis kilit orani %43.6, kapiyla %9'a
            # iniyor. imza_ref hicbir kosulda guncellenmez.
            if self._hareketli and self.benzerlik >= self.kimlik_esik:
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

    def _bagimsiz_dogrula(self, bgr, gri, ongoru):
        """KILITLI durumunun PSR'dan BAGIMSIZ iki denetleyicisi.

        TEST 1 - IMZA: `kimlik_periyot` karede bir, mevcut kutu DONDURULMUS
        referans imzayla karsilastirilir. `kimlik_sabir` kez ust uste esigin
        altinda kalirsa kilit reddedilir. Tek bir kotu kare (isik, kismi
        ortulme) kilidi kirmasin diye sabir sayaci var.

        TEST 2 - ZEMINE CAKILMA: kutu, ego telafisinden sonra hic hareket
        etmiyorsa araci degil YERI takip ediyordur. Olcut, `zemin_pencere`
        karelik kayan pencerenin P90'i; bu deger esigin altinda `zemin_sabir`
        kare ust uste kalirsa kilit reddedilir.

        P90 secildi - ne ardisik sayac ne medyan.
        Ikisi de denendi ve elendi:
          * ardisik sayac: 268/31'de karelerin %93'u esigin altinda olmasina
            ragmen tek bir gurultulu kare seriyi sifirliyor; kilit orani
            %92.5 -> %92.9, yani hicbir sey degismedi.
          * medyan: 117/23'te dur isaretinde bekleyen arac 20 karelik
            pencerede 1.02 px medyana iniyor ve DOGRU takip yanlis kilit
            sanildi (IoU 0.646 -> 0.49).
        P90 ikisini de cozer: duran bir aracin bile penceresinde birkac
        hareketli kare bulunur, yol yamasinda bulunmaz.

        Esik MUTLAK PIKSEL DEGIL, kare genisliginin orani. Mutlak 2.0 px
        denendi: 4K'da dogru calisti ama 640x480 simulasyonda dogru takibi
        bogdu (test3 kilit %100 -> %78). Ayni fiziksel hareket cozunurlukle
        birlikte olceklendigi icin olcut de olceklenmeli.

        Karar tek bir pencereye bakilarak verilmez - dagilimlar cakisiyor:
        117/23'un DOGRU takibinde p90 %0.057'ye kadar iniyor (arac durakta
        bekliyor), 268/31'in YANLIS kilidinde %0.073'e kadar cikiyor. Ayiran
        sey seviye degil SUREKLILIK: dogru takipte dusus anlik, yanlis kilitte
        kalici. Olculen en uzun ardisik seri (esik %0.08):
            117/23      DOGRU     8 kare
            268/31      YANLIS  106 kare
            268/31@1920 YANLIS   86 kare
            182/127     YANLIS  106 kare
        `zemin_sabir=20` dogru takibin en kotusunun 2.5 kati ustunde, yanlis
        kilidin en iyisinin 4 kati altinda.

        BILINEN SINIR: gercekten 20 kare boyunca duran bir arac bu testle
        yanlis kilit sanilir. `zemin_dogrulama=False` ile kapatilabilir.
        """
        kutu = self.kutu
        if kutu is None:
            return

        if self.zemin_dogrulama and ongoru is not None:
            artik = float(np.linalg.norm(self.kf.konum - ongoru))
            self._zemin_gecmis.append(artik)
            if len(self._zemin_gecmis) > self.zemin_pencere:
                del self._zemin_gecmis[0]
            if len(self._zemin_gecmis) >= self.zemin_pencere:
                p90 = float(np.percentile(self._zemin_gecmis, 90))
                oran = p90 / max(1, gri.shape[1])
                self._hareketli = oran >= self.zemin_orani
                self._hareketli_guclu = oran >= self.kimlik_hareket_kapisi
                self._zemin_alt = 0 if self._hareketli else self._zemin_alt + 1
                if self._zemin_alt >= self.zemin_sabir:
                    self._kilidi_reddet()
                    return

        # Kutu zeminden belirgin bicimde bagimsiz hareket ediyorsa gercek ve
        # hareketli bir cismi takip ediyordur; imza uyusmazligi o zaman kimlik
        # kaybindan cok GORUNUM DEGISIMIDIR (isik, donme, kismi ortulme).
        # Olculdu: test6'da oklüzyondan cikan arac benzerlik 0.35'e duSuyor ama
        # p90 orani %1.246 - kapinin (%0.3) 4 kati. 182/127'nin yanlis kilidinde
        # ise oran %0.13, kapinin altinda; orada imza reddi calismaya devam eder.
        # Cok kucuk hedefte imza olcusu anlamini yitirir: 12x12'lik sablon
        # birkac pikselden uretiliyor, ortalama renk tek bir pikselin gurultusu.
        # Esik deponun kendi olcumune dayanir: 20x10 px altinda doku bitiyor,
        # kutu olcusu 25x10 px altinda guvenilmez. Kisa kenar icin 10 px.
        # Olculdu: sim test3'te kutu 23.2x8.4 px iken benzerlik 0.37'ye
        # duSuyor ve DOGRU takip yanlis kilit sanilıyordu.
        if (self.kimlik_periyot and self.kare % self.kimlik_periyot == 0
                and not self._hareketli_guclu
                and float(self.boyut.min()) >= self.kimlik_min_kenar):
            # BOYUT terimi bilerek disarida: hedef uzaklasip kucululdugunde
            # (sim test2/test3) boyut skoru 0.10'a dusuyor ve dogru takibi
            # kimlik hatasi gibi gosteriyordu. Kimlik = renk + doku.
            _, s_renk, s_sab, _ = self.imza_ref.benzerlik(bgr, gri, kutu)
            s_gor = 0.5 * (s_renk + s_sab)
            self.benzerlik = float(s_gor)
            if s_gor < self.kimlik_esik:
                self._kimlik_hata += 1
                if self._kimlik_hata >= self.kimlik_sabir:
                    self._kilidi_reddet()
            else:
                self._kimlik_hata = 0

    def _kilidi_reddet(self):
        """Yanlis kilit: TESPIT burada biter, KURTARMA mevcut mekanizmaya devredilir.

        Iki sey birbirinden ayrildi. Bu fonksiyon yalnizca "bu kilit yanlis"
        der ve durumu teslim eder; nasil geri bulunacagi `_arama_adimi`'nin
        isidir ve orasi hic degismedi.

        Devir ARAMA moduna yapilir ve reddedilen konum `yasak_kare` boyunca
        yasaklanir. KAYIP moduna (tum kare, yalnizca gorunum) devretmek de
        denendi ve ELENDI: yol dokusu karenin her yerinde ayni gorundugu icin
        tum kare taramasi hemen baska bir yol yamasi buluyor ve sistem 3 karede
        yeniden yanlis kilitleniyor. Olculdu, 268/31'de yanlis kilit orani
        %60.3 -> %75.8. ARAMA + yasak bolge ise yaricap buyuyene kadar hic
        aday kabul etmiyor; sistem kaybettigini kabul edip bekliyor.

        Hiz sifirlanir (o hiz yanlis nesnenin hiziydi) ve kutunun bulundugu yer
        kisa sure yasaklanir; aksi halde ayni yamaya geri kilitlenir.
        Referans imza BURADA GUNCELLENMEZ - kimlik ilk kilide capali kalir.
        """
        self.yanlis_kilit += 1
        self._yasak_merkez = self.kf.konum.copy()
        self._yasak_sayac = self.yasak_kare
        self.benzerlik = 1.0        # yeni degerlendirme: bayat skor tasinmasin
        self._kimlik_hata = 0
        self._zemin_gecmis = []
        self._zemin_alt = 0
        self._hareketli = True
        self._hareketli_guclu = True
        self.psr = 0.0
        self.kf.x[2:] = 0.0
        self.durum = ARAMA
        self.kayip = self.coast_kare + 1

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
            if (self._yasak_sayac > 0 and self._yasak_merkez is not None
                    and float(np.linalg.norm(a["merkez"] - self._yasak_merkez))
                    < 0.75 * float(self.boyut.max())):
                continue          # az once reddedilen konum: geri kilitlenme
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
            # dogrulanmis kurtarma: sayaclar sifirlanir ama yasakli konum
            # durur (baska bir adaya kilitlendik, eskisine degil)
            self.benzerlik = 1.0
            self._kimlik_hata = 0
            self._zemin_gecmis = []
            self._zemin_alt = 0
            self._hareketli = True
            self._hareketli_guclu = True
            self._onceki_merkez = None
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
