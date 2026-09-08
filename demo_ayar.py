"""DEMO modu ayarlari (Adim 3a/3b): adaptif ROI merdiveni + karo taramasi.

3a - R_MERDIVEN: `docs/TESHIS_2E_PX_BANDI.md` EK'inde kalibre edildi (kapi
GECTI, 12/12 hucrede recall 1.000). Kullanicinin bu tur icin verdigi IKI
DUZELTME: (1) tam kadraj kacisi YOK - `gazebo/teshis_2e_merdiven.py`'deki
1x fallback burada BILEREK tasinmadi, R_MERDIVEN'in en genis basamagi
(R=640) 3 test irtifasinda zaten yeterliydi; (2) KAYIP arama artik R_ZAMAN'in
"21+: tam" (tum kare, gorunum) basamagi yerine bu dosyadaki `KaroArayici`yi
kullanir - bkz. `takip/izleyici.py:_karo_arama_adimi` (kayip_dedektor
eklentisi, hakem=None ornegiyle AYNI ilke: verilmezse davranis degismez).

3b - KaroArayici: kare basina <=KARO_KARE_BASI adet karo, son guvenilir
merkezden DISA dogru siralanmis sirayla taranir (maliyeti kare basina
SABIT tutar). Adaylar D_NORM (son guvenilir merkeze log-degil DUZ
normalize uzaklik - buyutme degil KONUM sorusu oldugu icin log gerekmez)
ile puanlanir; en yuksek d_norm kazanir.

DUZELTME (2026-09-07, kullanicidan): karo genisligi artik SABIT 640 DEGIL -
`sifirla(merkez, L_native=...)` son guvenilir hedef boyutundan `r_sec` ile
R_MERDIVEN'den secilir (hedef ~20px'e kucculunce R=160/80'e iner, ag
girdisi tekrar [55,110]px bandina oturur). Boyut bilinmiyorsa (soguk
edinme) R=640 varsayilan kalir (`r_sec(None)`). R kucculdukce karo sayisi
ARTAR - `tam_tur_kare()` bunu raporlar.

KABUL OLCUTLERI ADIM 5'TE tanimlanacak - burada yalnizca CALISAN bir
iskelet var, esikler (`aday_esik_kayip` uzerinden) henuz ayarlanmadi.
"""
import cv2
import numpy as np
import torch

# YOLO CIHAZ SECIMI (2026-09-08, kullanicidan): CUDA varsa KULLAN - Gazebo'nun
# GPU render sorunuyla (WSL2 D3D12 cokme) ILGISIZ, ayri bir yol (PyTorch/CUDA
# dogrudan surucu, Gazebo'nun OpenGL/D3D12 yigininin DISINDA). half (fp16)
# yalniz CUDA'da anlamli - CPU'da desteklenmez/yavaslatir.
YOLO_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
YOLO_HALF = YOLO_DEVICE == "cuda"

AG = (640, 360)
_R_MERDIVEN_1X = (640, 320, 160, 80)  # sensor-px ROI merdiveni, IMX500 (odak_px=1561) icin kalibre
TUVAL_OLCEK = 1.0                     # aktif kamera odak_px / 1561 (IMX500 native) - kucuk tuvalde < 1.0
R_MERDIVEN = _R_MERDIVEN_1X            # ayarla_tuval_olcek() ile yeniden olceklenir
BANT = (55.0, 110.0)                  # ag girdisinde hedeflenen px bandi - resize SONRASI sabit
                                       # AG canvasinda oldugu icin TUVAL_OLCEK'ten BAGIMSIZ (talimat)
NET_HEDEF = sum(BANT) / 2.0           # 82.5 - log-simetrik secim referansi


def ayarla_tuval_olcek(k):
    """Kamera nativ cozunurlugu IMX500'den (2028x1520, odak_px=1561) FARKLI
    oldugunda cagirilir (`k = odak_px / 1561`) - sensor-px cinsinden
    kalibre edilmis R_MERDIVEN'i orantili yeniden olcekler (2026-09-08,
    kullanicidan: 640x480 arastirma kamerasina duserken R_MERDIVEN
    kalibrasyonu bozulmustu, bkz. docs/DEMO_SONUC.md 'Canlı (scripted)').
    BANT/NET_HEDEF (ag-girdisi bandi) resize SONRASI sabit AG canvasinda
    olctugu icin BILEREK degistirilmez."""
    global TUVAL_OLCEK, R_MERDIVEN
    TUVAL_OLCEK = float(k)
    R_MERDIVEN = tuple(max(1, int(round(r * TUVAL_OLCEK))) for r in _R_MERDIVEN_1X)

KARO_KARE_BASI = 2                    # kare basina en fazla taranan karo sayisi
A6_AGIRLIK = "weights/a6_kucuk_hedef.pt"
A6_SINIFLAR = [0, 1, 2, 3]            # car,van,truck,bus (asamaB egitimiyle AYNI)
YOLO_CONF = 0.25

# DEMO BOYUT OTORITESI (2026-09-07): boyut yalniz dogrulanmis dedektor
# tespitinde yazilir, _boyut_tazele/klasik rafine ARAYA KARISMAZ - kare
# ~698 sicramasinin (bkz. commit 2ab78a7) kaynagini kapatir. `main.py`
# `--mod demo`de `HedefTakip(dedektor_boyut=DEDEKTOR_BOYUT_OTORITESI)`
# olarak gecer - takip/izleyici.py'de False iken davranis degismez.
DEDEKTOR_BOYUT_OTORITESI = True

# DEMO DETEKTOR-KARAR (2026-09-07, teshis sonrasi): 10/10 ARAMA epizodunda
# sebep PSR/coast DEGIL, `_bagimsiz_dogrula` (imza/zemin) reddiydi - ROI
# 10/10 GT'yi kapsiyordu. Bu yuzden durum gecisini PSR/imzadan alip
# DOGRUDAN dedektore veriyoruz - bkz. takip/izleyici.py:_dedektor_karar_adimi.
DEDEKTOR_KARAR_OTORITESI = True
K_SUPHELI = 3    # ust uste bu kadar "tespit yok" ya da "celiski" -> SUPHELI
K_KAYIP = 15     # ust uste bu kadar "tespit yok" -> ARAMA/karo

# DEDEKTOR KADANSI (2026-09-07, FPS teshisi): N_TESPIT>1 -> ara karelerde
# YOLO ATLANIR, DCF koprusu tek basina pozisyonu tasir (takip/izleyici.py:
# _dedektor_karar_adimi).
#
# Profil (100 kare, oksuz `gz sim` sureci - 5 saattir CPU yiyordu -
# TEMIZLENDIKTEN sonra, ama baska bir oturumun Gazebo/kaydet.py isiyle
# PAYLASIMLI CPU'da olculdu, mutlak sayilar bu yuzden gurultulu):
#   YOLO cikarim     ~%84 (p50 284ms - PAYLASIMLI CPU'da inflated)
#   diger (ego/boyut) ~%7
#   Kalman ~2.4ms, DCF ~1.3ms, ROI kirpma+resize ~0.35ms, sonuc isleme
#   ~0.26ms, jsonl yazma ~0.04ms - hepsi ihmal edilebilir, DUZELTILECEK
#   YOLO-disi buyuk kalem YOK.
#
# N=1/2/3 kiyasi (Demo_kucul 210m, 1200 kare, AYNI paylasimli CPU):
#   N=1: FPS  8.77  kilit %96.4  IoU 0.789  yanlis 0  ARAMA 1
#   N=2: FPS 23.84  kilit %96.4  IoU 0.793  yanlis 0  ARAMA 1
#   N=3: FPS 12.66  kilit %97.5  IoU 0.788  yanlis 0  ARAMA 0
# N=3'un FPS'i N=2'den DUSUK cikti - bu N=3'un daha yavas olmasindan degil
# (daha az YOLO cagrisi yapar), olcumler ARDISIK kosuldugu ve paylasimli
# CPU yuku zamanla degistigi icin GURULTULU bir karsilastirma. N=2 hedefin
# UCUNU DE (FPS>=20, kilit>=%95, yanlis=0) rahat farkla saglayan TEK N -
# ONNX/int8 (Task 3) BU YUZDEN GEREKMEDI, hic denenmedi.
N_TESPIT = 2


def r_sec(L_native):
    """R_MERDIVEN'den, ag girdisinde NET_HEDEF'e (log uzayinda) en yakin
    basamagi secer. Tam kadraj kacisi YOK - MERDIVEN disina hic cikilmaz.
    `docs/TESHIS_2E_PX_BANDI.md` EK'indeki formulun AYNISI. Boyut
    bilinmiyorsa (soguk edinme) R_MERDIVEN[0]=640 varsayilan doner."""
    if L_native is None or not np.isfinite(L_native) or L_native <= 0:
        return R_MERDIVEN[0]
    return min(R_MERDIVEN,
               key=lambda R: abs(np.log((L_native * AG[0] / float(R)) / NET_HEDEF)))


def r_basamak_buyu(R):
    """R_MERDIVEN'de bir basamak BUYUR (daha az zoom, daha genis ROI) -
    KaroArayici.roi_buyut / demo detektor-karar SUPHELI girisinde kullanilir."""
    idx = R_MERDIVEN.index(R) if R in R_MERDIVEN else 0
    return R_MERDIVEN[max(0, idx - 1)]


def _karo_wh(R):
    return int(R), int(round(R * 9.0 / 16.0))


def _karo_izgara(W, H, R, bindirme=0.25):
    rw, rh = _karo_wh(R)
    adim_x = max(1, int(rw * (1.0 - bindirme)))
    adim_y = max(1, int(rh * (1.0 - bindirme)))
    xs = sorted(set(list(range(0, max(1, W - rw) + 1, adim_x)) + [max(0, W - rw)]))
    ys = sorted(set(list(range(0, max(1, H - rh) + 1, adim_y)) + [max(0, H - rh)]))
    return [(x, y, rw, rh) for y in ys for x in xs]


def tam_tur_kare(W, H, kare_basi=KARO_KARE_BASI):
    """R_MERDIVEN'in her basamaginda bir TAM turun kac kare surdugunu
    dondurur ({R: kare_sayisi}) - R kucculdukce karo sayisi artar."""
    import math
    return {R: math.ceil(len(_karo_izgara(W, H, R)) / kare_basi) for R in R_MERDIVEN}


class KaroArayici:
    """Kare basina <=KARO_KARE_BASI karoyla kadraj taramasi.

    Neden: her karede tum kareyi (ya da tum kareyi tek YOLO cagrisiyla)
    taramak pahali; karolama maliyeti kare basina SABIT tutar, tarama
    coklu kareye yayilir. Sira, son bilinen/varsayilan merkezden DISA
    dogru (en yakin karo once) - "ASLA kalici pes etmez" ilkesiyle tutarli
    (bkz. `takip/izleyici.py:_arama_adimi` docstring): kuyruk biterse
    bastan baslar. Karo genisligi (R) `sifirla()`'da hedefin son bilinen
    boyutundan `r_sec` ile secilir - SABIT DEGIL (bkz. modul basligi).
    """

    def __init__(self, native_w, native_h, model, siniflar=A6_SINIFLAR,
                 conf=YOLO_CONF, kare_basi=KARO_KARE_BASI):
        self.W, self.H = native_w, native_h
        self.model = model
        self.siniflar = siniflar
        self.conf = conf
        self.kare_basi = kare_basi
        self._izgara_onbellek = {}     # R -> karo listesi (tekrar tekrar kurulmasin)
        self.R = R_MERDIVEN[0]
        self._sira = self._izgara(self.R)
        self._imlec = 0
        self._merkez = np.array([native_w / 2.0, native_h / 2.0], np.float32)
        self.taranan_karo_sayisi = 0
        self.son_roi = None    # bu karede TARANAN son karo (x,y,w,h) - HUD/JSON icin

    def _izgara(self, R):
        if R not in self._izgara_onbellek:
            self._izgara_onbellek[R] = _karo_izgara(self.W, self.H, R)
        return self._izgara_onbellek[R]

    def sifirla(self, merkez, L_native=None):
        """Verilen merkezden disa dogru siralanmis karo kuyrugu kurar.

        `L_native`: son guvenilir hedef boyutu (px) - verilirse R, `r_sec`
        ile o boyuta gore secilir; verilmezse (soguk edinme) R=640."""
        self.R = r_sec(L_native)
        self._merkez = np.asarray(merkez, np.float32)
        def _uzaklik2(k):
            cx, cy = k[0] + k[2] / 2.0, k[1] + k[3] / 2.0
            return (cx - self._merkez[0]) ** 2 + (cy - self._merkez[1]) ** 2
        self._sira = sorted(self._izgara(self.R), key=_uzaklik2)
        self._imlec = 0

    def adim(self, bgr):
        """Bu karede <=kare_basi karo tara. Bulunursa (merkez, kutu, d_norm),
        yoksa None doner. `d_norm` = 1 - clip(uzaklik/kadraj_kosegeni, 0, 1)
        - son merkeze YAKIN adaylar yuksek skor alir (buyutme degil DUZ
        oklid uzaklik - A9'un d_norm'uyla AYNI ilke, gorunum degil KONUM
        tutarliligi)."""
        tam = float(np.hypot(self.W, self.H))
        en_iyi = None
        for _ in range(self.kare_basi):
            if not self._sira:
                return None
            if self._imlec >= len(self._sira):
                self._imlec = 0
            x0, y0, rw, rh = self._sira[self._imlec]
            self._imlec += 1
            self.taranan_karo_sayisi += 1
            self.son_roi = (x0, y0, rw, rh)
            parca = bgr[y0:y0 + rh, x0:x0 + rw]
            if parca.shape[:2] != (rh, rw):
                continue
            girdi = cv2.resize(parca, AG, interpolation=cv2.INTER_AREA)
            r = self.model.predict(girdi, conf=self.conf, imgsz=640,
                                    classes=self.siniflar, verbose=False,
                                    device=YOLO_DEVICE, half=YOLO_HALF)[0]
            if r.boxes is None or not len(r.boxes):
                continue
            kx, ky = rw / float(AG[0]), rh / float(AG[1])
            for (x1, y1, x2, y2) in r.boxes.xyxy.cpu().numpy():
                kutu = np.array([x1 * kx + x0, y1 * ky + y0,
                                 (x2 - x1) * kx, (y2 - y1) * ky], np.float32)
                merkez = kutu[:2] + kutu[2:] / 2.0
                d = float(np.linalg.norm(merkez - self._merkez))
                d_norm = 1.0 - min(1.0, d / tam)
                if en_iyi is None or d_norm > en_iyi[2]:
                    en_iyi = (merkez, kutu, d_norm)
        return en_iyi

    # --- demo detektor-karar (2026-09-07): tek-ROI arayuzu -----------------
    def roi_sec(self, L_native):
        return r_sec(L_native)

    def roi_buyut(self, R):
        return r_basamak_buyu(R)

    def tek_roi(self, bgr, merkez, R):
        """TEK sabit ROI'de TEK YOLO cagrisi (kadraj taramasi DEGIL -
        `adim()`'in kuyruk-donen mantigindan BAGIMSIZ). Demo detektor-karar
        modunun KILITLI/SUPHELI'de HER KAREDE yaptigi kontrol icindir.
        Donen: (merkez, kutu, d_norm) | None - `adim()` ile AYNI skor
        formulu (son merkeze duz oklid uzaklik, kadraj kosegenine normalize)."""
        tam = float(np.hypot(self.W, self.H))
        merkez = np.asarray(merkez, np.float32)
        rw, rh = _karo_wh(R)
        x0 = int(round(merkez[0] - rw / 2.0))
        y0 = int(round(merkez[1] - rh / 2.0))
        x0 = max(0, min(self.W - rw, x0))
        y0 = max(0, min(self.H - rh, y0))
        parca = bgr[y0:y0 + rh, x0:x0 + rw]
        if parca.shape[:2] != (rh, rw):
            return None
        girdi = cv2.resize(parca, AG, interpolation=cv2.INTER_AREA)
        r = self.model.predict(girdi, conf=self.conf, imgsz=640,
                                classes=self.siniflar, verbose=False,
                                device=YOLO_DEVICE, half=YOLO_HALF)[0]
        if r.boxes is None or not len(r.boxes):
            return None
        kx, ky = rw / float(AG[0]), rh / float(AG[1])
        en_iyi = None
        for (x1, y1, x2, y2) in r.boxes.xyxy.cpu().numpy():
            kutu = np.array([x1 * kx + x0, y1 * ky + y0,
                             (x2 - x1) * kx, (y2 - y1) * ky], np.float32)
            m = kutu[:2] + kutu[2:] / 2.0
            d = float(np.linalg.norm(m - merkez))
            d_norm = 1.0 - min(1.0, d / tam)
            if en_iyi is None or d_norm > en_iyi[2]:
                en_iyi = (m, kutu, d_norm)
        return en_iyi


def demo_hedef_sec(karayici, esik=0.0):
    """`main.kos(..., hedef_secici=...)` sozlesmesine uyan edinme secicisi.

    `adaylar` (klasik hareket lekesi) YOK SAYILIR - `veri/yolo_secici.py`
    ile AYNI ilke (secici kendi tespitini yapar). `esik=0.0`: edinmede
    herhangi bir tespit yeterli (d_norm KAYIP kurtarmasindaki gibi bir
    ret esigi degil, yalniz siralama icin) - Adim 5'te sikilastirilabilir.
    """
    def secici(adaylar, kare):
        sonuc = karayici.adim(kare.goruntu)
        if sonuc is None:
            return None
        merkez, kutu, d_norm = sonuc
        if d_norm < esik:
            return None
        return {"kutu": kutu, "merkez": merkez, "alan": float(kutu[2] * kutu[3])}
    return secici
