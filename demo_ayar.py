"""DEMO modu ayarlari (Adim 3a/3b): adaptif ROI merdiveni + karo taramasi.

3a - R_MERDIVEN: `docs/TESHIS_2E_PX_BANDI.md` EK'inde kalibre edildi (kapi
GECTI, 12/12 hucrede recall 1.000). Kullanicinin bu tur icin verdigi IKI
DUZELTME: (1) tam kadraj kacisi YOK - `gazebo/teshis_2e_merdiven.py`'deki
1x fallback burada BILEREK tasinmadi, R_MERDIVEN'in en genis basamagi
(R=640) 3 test irtifasinda zaten yeterliydi; (2) KAYIP arama artik R_ZAMAN'in
"21+: tam" (tum kare, gorunum) basamagi yerine bu dosyadaki `KaroArayici`yi
kullanir - bkz. `takip/izleyici.py:_karo_arama_adimi` (kayip_dedektor
eklentisi, hakem=None ornegiyle AYNI ilke: verilmezse davranis degismez).

3b - KaroArayici: kare basina <=KARO_KARE_BASI adet R=640(sensor-px) karo,
son guvenilir merkezden DISA dogru siralanmis sirayla taranir (maliyeti
kare basina SABIT tutar). Adaylar D_NORM (son guvenilir merkeze log-degil
DUZ normalize uzaklik - buyutme degil KONUM sorusu oldugu icin log
gerekmez) ile puanlanir; en yuksek d_norm kazanir.

KABUL OLCUTLERI ADIM 5'TE tanimlanacak - burada yalnizca CALISAN bir
iskelet var, esikler (`aday_esik_kayip` uzerinden) henuz ayarlanmadi.
"""
import cv2
import numpy as np

AG = (640, 360)
R_MERDIVEN = (640, 320, 160, 80)     # sensor-px ROI genisligi merdiveni (3a)
BANT = (55.0, 110.0)                  # ag girdisinde hedeflenen px bandi
NET_HEDEF = sum(BANT) / 2.0           # 82.5 - log-simetrik secim referansi

KARO_R = 640                          # KAYIP/edinme taramasinda karo genisligi (native px)
KARO_KARE_BASI = 2                    # kare basina en fazla taranan karo sayisi
A6_AGIRLIK = "weights/a6_kucuk_hedef.pt"
A6_SINIFLAR = [0, 1, 2, 3]            # car,van,truck,bus (asamaB egitimiyle AYNI)
YOLO_CONF = 0.25


def r_sec(L_native):
    """R_MERDIVEN'den, ag girdisinde NET_HEDEF'e (log uzayinda) en yakin
    basamagi secer. Tam kadraj kacisi YOK - MERDIVEN disina hic cikilmaz.

    `docs/TESHIS_2E_PX_BANDI.md` EK'indeki formulun AYNISI. Bu turda
    dinamik olarak CAGRILMAZ (KAYIP/edinme sabit R=640 karo kullanir, cunku
    o asamada hedef boyutu icin guvenilir bir onsel yok) - kalibrasyon
    kaydi + gelecekteki boyut-bilgili yollar icin burada tutulur.
    """
    if L_native is None or not np.isfinite(L_native) or L_native <= 0:
        return R_MERDIVEN[0]
    return min(R_MERDIVEN,
               key=lambda R: abs(np.log((L_native * AG[0] / float(R)) / NET_HEDEF)))


def _karo_wh(R):
    return int(R), int(round(R * 9.0 / 16.0))


def _karo_izgara(W, H, R=KARO_R, bindirme=0.25):
    rw, rh = _karo_wh(R)
    adim_x = max(1, int(rw * (1.0 - bindirme)))
    adim_y = max(1, int(rh * (1.0 - bindirme)))
    xs = sorted(set(list(range(0, max(1, W - rw) + 1, adim_x)) + [max(0, W - rw)]))
    ys = sorted(set(list(range(0, max(1, H - rh) + 1, adim_y)) + [max(0, H - rh)]))
    return [(x, y, rw, rh) for y in ys for x in xs]


class KaroArayici:
    """Kare basina <=KARO_KARE_BASI adet R=640 karoyla kadraj taramasi.

    Neden: her karede tum kareyi (ya da tum kareyi tek YOLO cagrisiyla)
    taramak pahali; karolama maliyeti kare basina SABIT tutar, tarama
    coklu kareye yayilir. Sira, son bilinen/varsayilan merkezden DISA
    dogru (en yakin karo once) - "ASLA kalici pes etmez" ilkesiyle tutarli
    (bkz. `takip/izleyici.py:_arama_adimi` docstring): kuyruk biterse
    bastan baslar.
    """

    def __init__(self, native_w, native_h, model, siniflar=A6_SINIFLAR,
                 conf=YOLO_CONF, kare_basi=KARO_KARE_BASI):
        self.W, self.H = native_w, native_h
        self.model = model
        self.siniflar = siniflar
        self.conf = conf
        self.kare_basi = kare_basi
        self._karolar = _karo_izgara(native_w, native_h)
        self._sira = list(self._karolar)
        self._imlec = 0
        self._merkez = np.array([native_w / 2.0, native_h / 2.0], np.float32)
        self.taranan_karo_sayisi = 0

    def sifirla(self, merkez):
        """Verilen merkezden disa dogru siralanmis karo kuyrugu kurar."""
        self._merkez = np.asarray(merkez, np.float32)
        def _uzaklik2(k):
            cx, cy = k[0] + k[2] / 2.0, k[1] + k[3] / 2.0
            return (cx - self._merkez[0]) ** 2 + (cy - self._merkez[1]) ** 2
        self._sira = sorted(self._karolar, key=_uzaklik2)
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
            parca = bgr[y0:y0 + rh, x0:x0 + rw]
            if parca.shape[:2] != (rh, rw):
                continue
            girdi = cv2.resize(parca, AG, interpolation=cv2.INTER_AREA)
            r = self.model.predict(girdi, conf=self.conf, imgsz=640,
                                    classes=self.siniflar, verbose=False,
                                    device="cpu")[0]
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
