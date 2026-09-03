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
    P_IZ_ESIK = 8.0           # Kalman baslangic kovaryansi izi (diag(4,4))
    CAPA_AGIRLIK = 0.25       # izleyici._boyut_tazele: 0.75*eski + 0.25*yeni

    def __init__(self, dedektor, roi_kurali, dogrulayici=True, boyut_capasi=False,
                 recovery=False, oracle_merkez=False, oracle_boyut=False, N=None):
        """dedektor(bgr, merkez, R) -> (kutular, guvenler, ms)
        roi_kurali(L_sensor) -> R  (A8'in adaptif merdiveni)"""
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

        # ---------- Mod A (EK-2 surum 2) ----------
        p_iz = float(np.trace(tak.kf.P[:2, :2])) if tak.kf is not None else 0.0
        kayit["p_iz"] = round(p_iz, 3)
        mod_a = (tak.durum in (ARAMA, KAYIP)) or (p_iz > self.P_IZ_ESIK)

        if not self.dogrulayici:
            self.log.append(kayit)
            return kayit                        # H0: hakem hic karismaz

        if mod_a:
            self.onay = False
            kayit["karar"] = LOST
            self.lost_sayisi += 1
            if tak.durum not in (ARAMA, KAYIP):
                tak.durum = ARAMA
                tak.kayip = tak.coast_kare + 1
                tak.kf.x[2:] = 0.0
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
            R = self.roi_kurali(float(np.max(tak.boyut)))
            kutular = self._dedektor(bgr, merkez, R)
            kayit["kanit"] = len(kutular)
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
