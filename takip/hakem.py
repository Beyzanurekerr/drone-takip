"""A10 - KAPALI CEVRIM HAKEM.

Kural: docs/architecture/A10_ONKAYIT.md (+ EK-2), KOSUMDAN ONCE yazildi.

Hakem uc bilesenden olusur ve ucu de AYRI ACILIP KAPANIR (H1/H2/H3 kollari):

  1. DOGRULAYICI  - her N karede dedektor, takipcinin ROI'sinde koSar.
                    Sinyal YALNIZCA d_norm'dur (a_norm/r_norm hesaplanmaz;
                    3.3 §5: ikisi de bozuk boyuttan besleniyor).
                    Takipci kendi basina KILITLI ilan EDEMEZ.
  2. BOYUT CAPASI - onay geldiginde dedektor kutusunun BOYUTU takipciye
                    MUTLAK yazilir. Merkeze YAZMAZ. Carpimsal biriktirme yok.
                    P0.1 (bagimsiz mutlak boyut olcumu) tam olarak budur.
  3. RECOVERY     - LOST'ta son guvenilir merkez etrafinda R(gecen kare)
                    merdiveniyle arama; kapiyi gecen yoksa CEKIMSER.

SABITLER - hepsi on-kayitli, hicbiri bu dosyada uydurulmadi:
    N = 10          3.2 maliyet tablosu (4.14 ms/kare)
    G kapisi = 1.0  3.2 secim kurali
    k = 1           3.3 hukmu
    R merdiveni     3.0 "gerekli yaricap p95" tablosu
    MAX_HIZ = 35    izleyici.Kalman.MAX_HIZ
    P izi > 8.0     Kalman baslangic kovaryansi diag(4,4) izi
    0.75 / 0.25     izleyici._boyut_tazele'nin mevcut agirligi

BAGIMLILIK NOTU: bu modul dedektoru KENDISI cagirmaz; disaridan enjekte edilen
iki callable ile calisir (`dedektor`, `roi_kurali`). Boylece takip/ altinda
ultralytics/torch bagimliligi olusmaz ve A8'in ROI kurali kendi yerinde kalir.
"""
import numpy as np

from .izleyici import ARAMA, KAYIP, KILITLI, SUPHELI

ONAY, SUSPECT, LOST = "ONAY", "SUSPECT", "LOST"


class Hakem:
    N = 10
    G_KAPISI = 1.0
    K = 1
    MAX_HIZ = 35.0            # izleyici.Kalman.MAX_HIZ
    CAPA_AGIRLIK = 0.25       # izleyici._boyut_tazele: 0.75*eski + 0.25*yeni

    # --- D2: HISTEREZIS (A10.1) -------------------------------------------
    # A10'da tek esik 8.0'di ve bu, hakemin KENDI eyleminin yazdigi degerdi:
    # LOST -> ARAMA -> _arama_adimi -> Kalman.ata -> P[:2,:2]=diag(4,4) -> iz
    # TAM 8.0 -> sonraki tahmin adimi esigi asar -> yeniden LOST. Kendi kendini
    # besleyen cevrim. Artik giris ve cikis esikleri AYRI ve IKISI DE 8.0'dan
    # uzak; ikisi de A9 Asama 2'nin YAYIMLANMIS acik cevrim dagilimindan gelir
    # (hakem yokken olculdu, dolayisiyla hicbir eylemin yazdigi deger degil):
    #     saglam        p95 =  14.86     -> CIKIS
    #     Mod B         p95 =  29.52
    #     kopus oncesi  p95 =  54.08     -> GIRIS
    #     Mod A         p50 = 243.52
    #     (sifirlama degeri 8.00: GIRIS'in 6.8 KATI ALTINDA -> Kalman.ata'dan
    #      sonra esik kendiliginden asilamaz; A10'un kendi kendini besleyen
    #      cevrimi boylece imkansiz. A9'un kirli-yatak sayilari (saglam p95
    #      4.17, Mod B p95 11.97) artefaktliydi ve KULLANILMADI - D1'e bak.)
    MOD_A_GIRIS = 54.08
    MOD_A_CIKIS = 14.86
    P_SIFIRLAMA = 8.0         # Kalman.ata'nin yazdigi iz - ESIK OLARAK KULLANILMAZ

    # --- D3: DOGRULAYICI ROI = A8 §13 (merdiven + KAPSAMA TABANI) ----------
    MERDIVEN = [640, 320, 160, 80]
    NET_HEDEF = 75.0          # A8: hedefin ag girdisindeki ideal px boyu
    AG_W = 640                # A8: aga verilen kare genisligi
    BANT = (55.0, 110.0)      # A8 §15: operasyonel bant
    KAPSAMA_K = 2.0           # A8 §13: k ~ 2 (p95 karsiligi)
    KAPSAMA_EN_BOY = 32.0 / 9.0   # A8 §13: 16:9 -> dikey dar

    def __init__(self, dedektor, roi_kurali=None, dogrulayici=True, boyut_capasi=False,
                 recovery=False, oracle_merkez=False, oracle_boyut=False, N=None):
        """dedektor(bgr, merkez, R) -> (kutular, guvenler, ms)

        roi_kurali: A10'da A8.R_sec idi; A10.1/D3'ten sonra dogrulama ROI'si
        `R_dogrulama` (A8 §13, kapsama tabani dahil) ile secilir ve bu
        parametre KULLANILMAZ. Geriye donuk uyum icin duruyor."""
        self.dedektor, self.roi_kurali = dedektor, roi_kurali
        self.dogrulayici = dogrulayici
        self.boyut_capasi = boyut_capasi
        self.recovery = recovery
        self.oracle_merkez = oracle_merkez
        self.oracle_boyut = oracle_boyut
        if N is not None:
            self.N = int(N)
        self.sifirla()

    # ------------------------------------------------------------------
    def sifirla(self):
        self.onay = True                  # ilk kilit kullanicidan gelir
        self.son_guvenilir = None         # (kare, merkez, boyut)
        self.log = []
        self.dedektor_cagri = 0
        self.dedektor_ms = 0.0
        self.dogrulama_sayisi = 0
        self.onay_sayisi = 0
        self.suspect_sayisi = 0
        self.lost_sayisi = 0
        self.kanit_yok = 0
        self.capa_yazim = 0
        self.capa_kayit = []              # (kare, oncesi, sonrasi)
        self.recovery_deneme = 0
        self.recovery_cekimser = 0
        self.recovery_tohum = 0
        self.dogrulama_kosmadi_kare = 0   # SUSPECT'te tutuldugu icin _bagimsiz_dogrula kosmayan kare
        self._mod_a_aktif = False         # D2 histerezis mandali
        self._kendi_itti = False          # ARAMA'yi hakem mi yazdi (D2 kurali)
        self._son_R = None                # A8 §13 adim 1: son guvenilir R
        self.kanit_var = 0                # D3 birincil metrik: kanit_yok orani icin

    # ------------------------------------------------------------------
    @staticmethod
    def d_norm(kutu, ref_merkez, ref_wh, dt):
        """3.2'nin d_norm'u, BIREBIR. a_norm / r_norm HESAPLANMAZ."""
        kc = np.asarray(kutu[:2], float) + np.asarray(kutu[2:], float) / 2.0
        rw, rh = float(ref_wh[0]), float(ref_wh[1])
        d = float(np.linalg.norm(kc - np.asarray(ref_merkez, float)))
        d_bek = Hakem.MAX_HIZ * float(dt) + max(rw, rh) / 2.0
        return d / max(d_bek, 1e-6)

    @staticmethod
    def R_recovery(gecen_kare):
        """Deney 3.0'in gerekli-yaricap p95 tablosundan; 3.2'de de bu kullanildi."""
        return 160 if gecen_kare <= 5 else (320 if gecen_kare <= 20 else 640)

    def R_dogrulama(self, tak):
        """A8 §13'un adaptif secim kurali - KAPSAMA TABANI dahil (D3).

        1. GUVEN KAPISI : durum != KILITLI ya da PSR dusukse L_est'e guvenme;
                          son guvenilir R korunur ve bir basamak BUYUTULUR.
        2. BUYUTME      : R_buyutme = L_est * 640 / 75
        3. KAPSAMA      : R_kapsama = (32/9) * (k*u + L_est/2),  u = sqrt(iz P)
        4. SECIM        : ag_px = L_est*640/R bandi [55,110] icinde OLAN ve
                          R >= R_kapsama olan EN KUCUK basamak; yoksa en buyuk.
        A10'da yalnizca A8.R_sec (adim 2) kullaniliyordu; kapsama tabani yoktu.
        """
        L = float(np.max(tak.boyut))
        u = float(np.sqrt(max(np.trace(tak.kf.P[:2, :2]), 0.0)))
        guvenilir = (tak.durum == KILITLI and tak.psr >= tak.psr_kilit)
        if not guvenilir and self._son_R is not None:
            i = self.MERDIVEN.index(self._son_R)
            return self.MERDIVEN[max(0, i - 1)]        # bir basamak BUYUT
        R_kapsama = self.KAPSAMA_EN_BOY * (self.KAPSAMA_K * u + L / 2.0)
        uygun = [R for R in sorted(self.MERDIVEN)
                 if self.BANT[0] <= L * self.AG_W / float(R) <= self.BANT[1]
                 and R >= R_kapsama]
        R = uygun[0] if uygun else self.MERDIVEN[0]
        if guvenilir:
            self._son_R = R
        return R

    def _sec(self, kutular, ref_merkez, ref_wh, dt):
        """Kapi + argmin d_norm. Gecen yoksa CEKIMSER (None)."""
        if not len(kutular):
            return None, None
        skor = [self.d_norm(k, ref_merkez, ref_wh, dt) for k in kutular]
        i = int(np.argmin(skor))
        return (i, skor[i]) if skor[i] <= self.G_KAPISI else (None, skor[i])

    def _dedektor(self, bgr, merkez, R):
        kut, guv, ms = self.dedektor(bgr, merkez, R)
        self.dedektor_cagri += 1
        self.dedektor_ms += float(ms)
        return kut

    # ------------------------------------------------------------------
    def adim(self, tak, bgr, gt=None):
        """tak.guncelle(bgr) SONRASI cagrilir. Takipcinin durumunu degistirir."""
        t = tak.kare
        # Takipcinin KENDI verdigi durum, hakem dokunmadan once. Olcum
        # confound'unu onlemek icin saklanir: hakem "KILITLI demeyerek"
        # guvenli-yanlis-kilit sayacini dusurebilir; bu bir DAVRANIS kazanci
        # degil ETIKET degisikligidir ve ayri raporlanmalidir.
        kayit = {"t": t, "karar": None, "min_d": None, "kanit": None,
                 "durum_takipci": tak.durum}

        # ---------- Mod A: HISTEREZIS (D2) ----------
        p_iz = float(np.trace(tak.kf.P[:2, :2])) if tak.kf is not None else 0.0
        kayit["p_iz"] = round(p_iz, 3)

        if not self.dogrulayici:
            self.log.append(kayit)
            return kayit                        # H0: hakem hic karismaz

        # Cikis once degerlendirilir: iz CIKIS esiginin altina inince mandal duser.
        if self._mod_a_aktif and p_iz < self.MOD_A_CIKIS:
            self._mod_a_aktif = False
        # Takipcinin KENDI arama durumu Mod A kanitidir; ama ARAMA'yi HAKEM
        # yazdiysa kanit degildir (kendi eyleminin ciktisini olcut yapmak,
        # KALICI_KISITLAR.md'deki yasagin ta kendisi).
        takipci_aramada = (tak.durum in (ARAMA, KAYIP)) and not self._kendi_itti
        yeni_giris = (not self._mod_a_aktif) and (p_iz > self.MOD_A_GIRIS
                                                  or takipci_aramada)
        if yeni_giris:
            self._mod_a_aktif = True
            self.onay = False
            kayit["karar"] = LOST
            self.lost_sayisi += 1
            if tak.durum not in (ARAMA, KAYIP):
                tak.durum = ARAMA
                tak.kayip = tak.coast_kare + 1
                tak.kf.x[2:] = 0.0
                self._kendi_itti = True
        elif self._mod_a_aktif:
            self.onay = False
            kayit["karar"] = LOST                # mandal acik; YENI itme YOK
        if tak.durum not in (ARAMA, KAYIP):
            self._kendi_itti = False
        elif tak.kayip > 0:
            self.onay = False
            kayit["karar"] = SUSPECT
            self.suspect_sayisi += 1

        # ---------- DOGRULAMA (N kadansi) ----------
        if t % self.N == 0 and tak.durum in (KILITLI, SUPHELI) and tak.kutu is not None:
            self.dogrulama_sayisi += 1
            merkez = (np.asarray(gt[:2], float) + np.asarray(gt[2:], float) / 2.0
                      if (self.oracle_merkez and gt is not None) else tak.kf.konum)
            wh = (np.asarray(gt[2:], float)
                  if (self.oracle_merkez and gt is not None) else np.asarray(tak.boyut, float))
            R = self.R_dogrulama(tak)           # D3: A8 §13 + kapsama tabani
            kayit["R"] = R
            kutular = self._dedektor(bgr, merkez, R)
            kayit["kanit"] = len(kutular)
            if len(kutular):
                self.kanit_var += 1
            if not len(kutular):
                self.kanit_yok += 1             # ON-KAYIT: durum DEGISMEZ
            else:
                i, skor = self._sec(kutular, merkez, wh, 0)
                kayit["min_d"] = None if skor is None else round(float(skor), 4)
                if i is None:
                    self.onay = False
                    kayit["karar"] = SUSPECT
                    self.suspect_sayisi += 1
                else:
                    self.onay = True
                    self._mod_a_aktif = False   # bagimsiz kanit mandali dusurur
                    kayit["karar"] = ONAY
                    self.onay_sayisi += 1
                    self.son_guvenilir = (t, tak.kf.konum.copy(),
                                          np.asarray(tak.boyut, float).copy())
                    if self.boyut_capasi:
                        self._capa(tak, kutular[i], gt, t)

        # ---------- RECOVERY (LOST, N kadansi) ----------
        if (self.recovery and not self.onay and tak.durum in (ARAMA, KAYIP)
                and t % self.N == 0 and self.son_guvenilir is not None):
            self._recovery(tak, bgr, t, gt)

        # ---------- KILITLI ilanini hakem verir ----------
        if not self.onay and tak.durum == KILITLI:
            tak.durum = SUPHELI
            self.dogrulama_kosmadi_kare += 1

        kayit["durum"] = tak.durum
        kayit["onay"] = self.onay
        self.log.append(kayit)
        return kayit

    # ------------------------------------------------------------------
    def _capa(self, tak, kutu, gt, t):
        """ONAY'da boyut capasi. MERKEZE YAZMAZ. Mutlak yazim."""
        olcum = (np.asarray(gt[2:], float) if (self.oracle_boyut and gt is not None)
                 else np.asarray(kutu[2:], float))
        olcum = np.maximum(olcum, tak.min_kenar)
        oncesi = np.asarray(tak.boyut, float).copy()
        tak.boyut = np.maximum((1.0 - self.CAPA_AGIRLIK) * tak.boyut
                               + self.CAPA_AGIRLIK * olcum, tak.min_kenar)
        tak.boyut_olculen = olcum.copy()          # MUTLAK - bagimsiz olcum
        self.capa_yazim += 1
        self.capa_kayit.append({"t": t, "oncesi": [round(float(v), 2) for v in oncesi],
                                "olcum": [round(float(v), 2) for v in olcum],
                                "sonrasi": [round(float(v), 2) for v in tak.boyut]})

    def _recovery(self, tak, bgr, t, gt):
        kare0, merkez0, boyut0 = self.son_guvenilir
        dt = t - kare0
        if self.oracle_merkez and gt is not None:
            merkez0 = np.asarray(gt[:2], float) + np.asarray(gt[2:], float) / 2.0
            boyut0 = np.asarray(gt[2:], float)
        R = self.R_recovery(dt)
        self.recovery_deneme += 1
        kutular = self._dedektor(bgr, merkez0, R)
        if not len(kutular):
            self.recovery_cekimser += 1
            return
        i, _skor = self._sec(kutular, merkez0, boyut0, dt)
        if i is None:
            self.recovery_cekimser += 1           # kapiyi gecen yok -> CEKIMSER
            return
        tak.kilitle(bgr, np.asarray(kutular[i], np.float32))
        tak.durum = SUPHELI                       # onay gelene kadar SUSPECT
        self.onay = False
        self.recovery_tohum += 1

    # ------------------------------------------------------------------
    def ozet(self, toplam_kare):
        return {
            "dedektor_cagri": self.dedektor_cagri,
            "dedektor_ms_toplam": round(self.dedektor_ms, 2),
            "dogrulama_ms_kare_basina": round(self.dedektor_ms / max(toplam_kare, 1), 3),
            "dedektor_ms_cagri_basina": round(self.dedektor_ms / max(self.dedektor_cagri, 1), 2),
            "dogrulama_sayisi": self.dogrulama_sayisi,
            "onay": self.onay_sayisi, "suspect": self.suspect_sayisi,
            "lost": self.lost_sayisi, "kanit_yok": self.kanit_yok,
            "capa_yazim": self.capa_yazim,
            "recovery_deneme": self.recovery_deneme,
            "recovery_cekimser": self.recovery_cekimser,
            "recovery_tohum": self.recovery_tohum,
            "kilitli_ilani_dusurulen_kare": self.dogrulama_kosmadi_kare,
        }
