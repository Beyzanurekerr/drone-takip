"""Kaynak-bagimsiz calistirici: simulator / video / kamera -> ayni takip hatti.

    python3 main.py --source sim    --scenario test6
    python3 main.py --source video  --input data/test.mp4
    python3 main.py --source camera --camera-id 0

Takip tarafi (takip/izleyici.py) goruntunun nereden geldigini BILMEZ; bu dosyada
da `if video: ... if sim: ...` gibi bir dallanma yoktur. Tek fark, simulator
kaynagi yaninda ground-truth kutusu da tasidigi icin ekranda yesil GT cizilir.

Olcum ve kiyaslama icin `kiyasla.py` / `calistir.py` kullanilmaya devam edilir;
bu dosya onlarin yerini ALMAZ, yaninda durur.
"""
import argparse
import json
import os
import sys
import time
from collections import deque

import cv2
import numpy as np

from calistir import _kutu_ciz, iou      # cizim ve olcum ilkelerini yeniden kullan
from kaynak import KaynakHatasi, kaynak_olustur
from takip.izleyici import ARAMA, KAYIP, KILITLI, SUPHELI, HedefTakip
from takip.izleyici import KORUMA_ESIK as KORUMA_ESIK_VARSAYILAN

ISINMA = 6          # hareket tespiti icin gecmis gerekiyor (ilk kareler bos doner)
DRIFT_ESIK = 0.3    # bu IoU'nun altinda "kopmus" sayilir
DRIFT_SABIR = 5     # ust uste bu kadar kare -> gercek kopma (tek kare gurultu degil)
PENCERE_KUTUSU = (960, 540)     # baslangic penceresi bu kutuya sigar


def pencere_boyutu(genislik, yukseklik, kutu=PENCERE_KUTUSU):
    """Baslangic pencere boyutu: en-boy orani korunarak `kutu` icine sigdirilir.

    Ekrani kaplamasin diye; kullanici sonrasinda fareyle serbestce
    boyutlandirabilir (WINDOW_NORMAL). Kaynak cozunurlugu ne olursa olsun
    (sim 640x480, VisDrone 960x540 ya da 3840x2160) pencere ayni boyda acilir.
    """
    if genislik <= 0 or yukseklik <= 0:
        return kutu
    k = min(kutu[0] / genislik, kutu[1] / yukseklik)
    return max(160, int(round(genislik * k))), max(120, int(round(yukseklik * k)))


def gt_hedef_sec(adaylar, kare):
    """Ground-truth ile hedef secimi: GT kutusu varsa onu baslangic kutusu yap.

    Yalnizca KILIT ANINDA kullanilir; sonraki karelerde takipci kendi tahminiyle
    ilerler, GT'ye bir daha bakilmaz. Gercek veri kumelerinde adil SOT olcumu
    icin sart: aksi halde takipci rastgele bir nesneye kilitlenir ve IoU
    anlamsiz olur.
    """
    if kare.gt is None:
        return None
    kutu = np.asarray(kare.gt, np.float32)
    return {"kutu": kutu, "merkez": kutu[:2] + kutu[2:] / 2.0,
            "alan": float(kutu[2] * kutu[3])}


def otomatik_hedef_sec(adaylar, kare):
    """Varsayilan secici: GT varsa GT kutusu, yoksa merkeze yakin buyuk aday.

    Dallanma kaynak TIPINE degil, VERININ varligina bakar - bu yuzden dongu
    kaynak-bagimsiz kalir.

    HEDEF SECIMI TAKILIP CIKARILABILIR: `kos(..., hedef_secici=...)` ile
    baska bir secici verilebilir. Sozlesme:

        secici(adaylar, kare) -> aday sozlugu | None

    Fare ile secim (Asama 5) ayni imzayi uygulayacak; dongude tek satir bile
    degismeyecek. Kaynaktan bagimsiz olmasi icin burada GT kullanilmaz
    (calistir.py'deki GT tabanli secim yalnizca olcum icindir).
    """
    if kare.gt is not None:
        return gt_hedef_sec(adaylar, kare)
    if not adaylar:
        return None
    merkez = np.array([kare.genislik / 2.0, kare.yukseklik / 2.0], np.float32)
    kosegen = float(np.hypot(kare.genislik, kare.yukseklik))
    en_iyi, en_skor = None, -1.0
    for a in adaylar:
        d = float(np.linalg.norm(a["merkez"] - merkez))
        skor = a["alan"] / (1.0 + 2.0 * d / kosegen)
        if skor > en_skor:
            en_iyi, en_skor = a, skor
    return en_iyi


# --- A4: kullanici hedef secimi (fare ile ROI) -----------------------------
# `kos()` govdesine DOKUNULMAZ. Secici, `otomatik_hedef_sec` ile AYNI sozlesmeyi
# uygular: secici(adaylar, kare) -> aday sozlugu | None.


def _roi_aday(x0, y0, x1, y1, genislik, yukseklik, min_kenar=4.0):
    """Iki fare noktasindan aday sozlugu. Saf fonksiyon (GUI'siz test edilir).

    * TERS SURUKLEME desteklenir (min/max ile normalize edilir).
    * KADRAJ DISI kisim guvenle KIRPILIR.
    * Kirpma sonrasi kenar `min_kenar`in altindaysa secim GECERSIZ -> None.

    2 PX ON-TELAFI: `kos()` satir 382-384'te hareket lekesi icin
    `kutu[2:] -= 2` dilate telafisi uygular ve kutuyu `merkez`e gore yeniden
    konumlandirir. Elle cizilen ROI dilate edilmis DEGILDIR; bu yuzden burada
    kutu 2 px BUYUK dondurulur ve telafi sadelesir - `kos()` govdesi bit-birebir
    kalir, kullanici tam cizdigi kutuyu alir.
    """
    xa, xb = (float(x0), float(x1)) if x0 <= x1 else (float(x1), float(x0))
    ya, yb = (float(y0), float(y1)) if y0 <= y1 else (float(y1), float(y0))
    xa, ya = max(0.0, xa), max(0.0, ya)                       # kadraj disi kirpma
    xb, yb = min(float(genislik), xb), min(float(yukseklik), yb)
    w, h = xb - xa, yb - ya
    if not (np.isfinite(w) and np.isfinite(h)) or w < min_kenar or h < min_kenar:
        return None                                           # tek tik / sifir alan
    merkez = np.array([xa + w / 2.0, ya + h / 2.0], np.float32)
    kutu = np.array([xa - 1.0, ya - 1.0, w + 2.0, h + 2.0], np.float32)  # on-telafi
    return {"kutu": kutu, "merkez": merkez, "alan": float(w * h)}


class _RoiSecim:
    """Fare olaylarindan ROI kuran durum makinesi (pencereden bagimsiz)."""

    def __init__(self, genislik, yukseklik, min_kenar=4.0):
        self.genislik, self.yukseklik = int(genislik), int(yukseklik)
        self.min_kenar = float(min_kenar)
        self.bas = self.son = None
        self.surukleniyor = False
        self._aday = None

    def olay(self, olay, x, y):
        if olay == cv2.EVENT_LBUTTONDOWN:
            self.bas, self.son, self.surukleniyor, self._aday = (x, y), (x, y), True, None
        elif olay == cv2.EVENT_MOUSEMOVE and self.surukleniyor:
            self.son = (x, y)
        elif olay == cv2.EVENT_LBUTTONUP and self.surukleniyor:
            self.son, self.surukleniyor = (x, y), False
            self._aday = _roi_aday(self.bas[0], self.bas[1], x, y,
                                   self.genislik, self.yukseklik, self.min_kenar)
            if self._aday is None:                 # gecersiz -> sifirla, bekle
                self.bas = self.son = None

    def dikdortgen(self):
        if self.bas is None or self.son is None:
            return None
        return (min(self.bas[0], self.son[0]), min(self.bas[1], self.son[1]),
                max(self.bas[0], self.son[0]), max(self.bas[1], self.son[1]))

    def aday(self):
        return self._aday


def fare_hedef_sec(min_kenar=4.0):
    """Fare ile hedef secimi. `kos(..., hedef_secici=fare_hedef_sec())`.

    Sol tus bas -> surukle -> birak = secim. ESC = guvenli iptal (bir daha
    sorulmaz, kosum kilitsiz devam eder). Gecersiz ROI'de secim sifirlanir ve
    beklemeye devam edilir; program cokmez.

    MALIYET: yalnizca KILIT ONCESI calisir. Kilit kurulduktan sonra `kos()`
    seciciyi bir daha CAGIRMAZ (main.py:377 `if not kilitli`), dolayisiyla takip
    dongusune surekli maliyet EKLEMEZ.
    """
    durum = {"secim": None, "iptal": False, "kurulu": False, "sure_ms": 0.0}

    def secici(adaylar, kare):
        if durum["iptal"]:
            return None
        ad = kare.kaynak_adi
        t0 = time.perf_counter()
        if not durum["kurulu"]:
            durum["secim"] = _RoiSecim(kare.genislik, kare.yukseklik, min_kenar)
            cv2.namedWindow(ad, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
            cv2.resizeWindow(ad, *pencere_boyutu(kare.genislik, kare.yukseklik))
            cv2.setMouseCallback(ad, lambda o, x, y, b, p: durum["secim"].olay(o, x, y))
            durum["kurulu"] = True
        s = durum["secim"]
        f = hud_olcek(kare.genislik, kare.yukseklik)
        while True:
            gor = kare.goruntu.copy()          # ORIJINALE YAZMA: kos() ayni kareyi kullanir
            d = s.dikdortgen()
            if d is not None:
                cv2.rectangle(gor, (d[0], d[1]), (d[2], d[3]), (0, 255, 255), 2)
            _yaz(gor, "HEDEFI SEC: surukle  |  ESC: iptal",
                 (int(10 * f), int(26 * f)), 0.6 * f, (0, 255, 255), max(1, int(2 * f)))
            cv2.imshow(ad, gor)
            if (cv2.waitKey(20) & 0xFF) == 27:      # ESC -> guvenli iptal
                durum["iptal"] = True
                durum["sure_ms"] += (time.perf_counter() - t0) * 1e3
                return None
            a = s.aday()
            if a is not None:
                durum["sure_ms"] += (time.perf_counter() - t0) * 1e3
                return a

    secici.durum = durum          # olcum/teshis icin (kos() bunu okumaz)
    return secici


# --- HUD -------------------------------------------------------------------
# Iki kural:
#
# 1) OLCEK. Yazi KAYNAK piksellerine cizilir, pencere ise `pencere_boyutu` ile
#    960x540 kutusuna sigdirilir. Sabit font kullanilirsa 3840x2160 bir dizide
#    yazi ekranda 4 kat kucuk gorunur. Font ve kalinlik cozunurlukle birlikte
#    buyutulur: HUD ekranda her kaynakta AYNI boyda gorunur.
# 2) TEK YER. Butun sistem bilgisi sol ustteki tek panelde toplanir; goruntunun
#    baska kosesine yazi dagitilmaz. Kutularin yaninda yalnizca "GT" / "TRACK"
#    etiketi durur, o da kutunun DISINDA - hedefin pikselleri asla kapanmaz.
#
# Buradaki hicbir sey olcume girmez: sadece gorsellestirme.
FONT = cv2.FONT_HERSHEY_SIMPLEX
HUD_GORUNEN = 0.70       # 960x540 penceresinde govde yazisinin gorunen olcegi
HUD_MIN_OLCEK = 0.72     # ham pikselde de font 0.5'in altina inme
HUD_MAKS_PAY = 0.62      # panel goruntu genisliginin bu kadarindan genis olamaz

# Durum adlari ve renkleri yalnizca EKRAN icindir; takip tarafi Turkce
# sabitleri kullanmaya devam eder; calistir.RENK olcum tarafinda duruyor.
DURUM_ADI = {KILITLI: "LOCKED", SUPHELI: "SUSPECT",
             ARAMA: "SEARCHING", KAYIP: "LOST"}
DURUM_RENK = {KILITLI: (0, 255, 255),      # sari
              SUPHELI: (0, 165, 255),      # turuncu
              ARAMA: (255, 160, 0),        # gok mavisi
              KAYIP: (0, 0, 255)}          # kirmizi
GT_RENK = (0, 230, 0)            # yesil - dort durum renginin hicbiri yesil degil
ADAY_RENK = (200, 110, 0)
ETIKET_RENK = (165, 165, 165)    # panelde alan adi
DEGER_RENK = (245, 245, 245)     # panelde deger
YOK = "-"


def hud_olcek(genislik, yukseklik, kutu=PENCERE_KUTUSU):
    """Cozunurluge gore font/kalinlik carpani.

    Pencere `kutu` icine k = min(kutu_w/W, kutu_h/H) orani ile sigdiriliyor;
    yazi da ayni kuculmeye ugruyor, 1/k ile telafi edilir:
    960x540 -> 1.00 · 1920x1080 -> 2.00 · 3840x2160 -> 4.00 ·
    640x480 (4:3) -> alt sinir 0.72.
    """
    if genislik <= 0 or yukseklik <= 0:
        return 1.0
    return max(HUD_MIN_OLCEK, genislik / kutu[0], yukseklik / kutu[1])


def _yaz(img, metin, konum, olcek, renk, kalinlik):
    """Siyah kontur + renkli govde: acik betonda da koyu golgede de okunur."""
    cv2.putText(img, metin, konum, FONT, olcek, (0, 0, 0),
                kalinlik + 2 * max(1, kalinlik // 2), cv2.LINE_AA)
    cv2.putText(img, metin, konum, FONT, olcek, renk, kalinlik, cv2.LINE_AA)


def _karart(img, x0, y0, x1, y1, alfa=0.62):
    """Panel zemini: kesip karartmak, addWeighted'dan hem ucuz hem yerinde."""
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(img.shape[1], int(x1)), min(img.shape[0], int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    roi = img[y0:y1, x0:x1]
    roi[:] = (roi * (1.0 - alfa)).astype(img.dtype)


def _kesikli_kutu(img, kutu, renk, kalinlik, adim):
    """GT KESIK cizgi, takip DUZ cizgi.

    Renk tek basina yetmiyor (kucuk hedefte iki kutu ust uste biner); cizgi
    deseni ikinci ve renkten bagimsiz bir ayirt edici.
    """
    x, y, w, h = [int(round(v)) for v in kutu]
    adim = max(2, int(adim))
    if w < 6 * adim or h < 6 * adim:      # kucuk kutuda kesik cizgi kayboluyor
        cv2.rectangle(img, (x, y), (x + w, y + h), renk, kalinlik)
        return
    for i in range(x, x + w, 2 * adim):
        j = min(i + adim, x + w)
        cv2.line(img, (i, y), (j, y), renk, kalinlik)
        cv2.line(img, (i, y + h), (j, y + h), renk, kalinlik)
    for i in range(y, y + h, 2 * adim):
        j = min(i + adim, y + h)
        cv2.line(img, (x, i), (x, j), renk, kalinlik)
        cv2.line(img, (x + w, i), (x + w, j), renk, kalinlik)


def _cakisiyor(a, b):
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or
                a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])


def _kutu_etiketi(img, metin, kutu, renk, olcek, kal, bosluk, yasak=None):
    """Kutunun DISINA rozet: dolu renkli zemin + siyah yazi. Rozet kutusunu doner.

    Sira: kutunun ustu -> altina -> sagina. Hedefin uzerine hicbir kosulda
    binmez; 15x7 px bir aracta bile arac pikselleri temiz kalir.
    """
    x, y, w, h = [int(round(v)) for v in kutu]
    (tw, th), _ = cv2.getTextSize(metin, FONT, olcek, kal)
    ped = max(2, int(round(olcek * 7)))
    kw, kh = tw + 2 * ped, th + 2 * ped
    adaylar = [(x, y - kh - bosluk),          # ustu (varsayilan)
               (x, y + h + bosluk),           # alti
               (x + w + bosluk, y)]           # sagi
    x0, y0 = adaylar[0]
    for ax, ay in adaylar:
        if ay < 0 or ay + kh > img.shape[0]:
            continue
        if yasak is not None and _cakisiyor((ax, ay, kw, kh), yasak):
            continue
        x0, y0 = ax, ay
        break
    x0 = int(min(max(0, x0), max(0, img.shape[1] - kw)))
    y0 = int(min(max(0, y0), max(0, img.shape[0] - kh)))
    cv2.rectangle(img, (x0, y0), (x0 + kw, y0 + kh), renk, -1)
    cv2.rectangle(img, (x0, y0), (x0 + kw, y0 + kh), (0, 0, 0),
                  max(1, kal // 2))
    cv2.putText(img, metin, (x0 + ped, y0 + kh - ped), FONT, olcek,
                (0, 0, 0), kal, cv2.LINE_AA)
    return (x0, y0, kw, kh)


def _panel_olcu(satirlar, f, kal, ped, ayrac, sutun_ara):
    """Izgara olculeri. Alan adi ve deger sutunlari AYRI hizalanir.

    Boylece FPS / IoU / LATENCY degerleri birbirinin icine giremez: her
    sutunun genisligi o sutundaki en uzun metne gore sabitlenir.
    """
    n = max(len(s) for s in satirlar)
    ad_w = [0] * n
    deger_w = [0] * n
    tam_w = 0                      # tek hucreli satirlarin (SOURCE) genisligi
    for s in satirlar:
        for c, (ad, deger, _) in enumerate(s):
            ad_w[c] = max(ad_w[c], cv2.getTextSize(ad + ":", FONT, f, kal)[0][0])
            if len(s) > 1:
                deger_w[c] = max(deger_w[c],
                                 cv2.getTextSize(deger, FONT, f, kal)[0][0])
    for s in satirlar:
        if len(s) == 1:
            tam_w = max(tam_w, ad_w[0] + ayrac +
                        cv2.getTextSize(s[0][1], FONT, f, kal)[0][0])
    yuk = cv2.getTextSize("Ag", FONT, f, kal)[0][1]
    hucre_w = [ad_w[c] + ayrac + deger_w[c] for c in range(n)]
    ic_w = max(sum(hucre_w) + sutun_ara * (n - 1), tam_w)
    satir_h = int(round(yuk * 2.05))
    return {"ad_w": ad_w, "hucre_w": hucre_w, "yuk": yuk, "satir_h": satir_h,
            "genislik": ic_w + 2 * ped,
            "yukseklik": 2 * ped + yuk + satir_h * (len(satirlar) - 1)}


def _bilgi_paneli(img, satirlar, s, vurgu):
    """Sol ust kosede TEK panel. Butun sistem bilgisi burada.

    Panel goruntu genisliginin `HUD_MAKS_PAY`ini asarsa olcek kucultulup
    yeniden olculur - 4:3 ya da dar kaynakta duzen bozulmasin diye.
    """
    for _ in range(4):
        f = HUD_GORUNEN * s
        kal = max(1, int(round(2.2 * s)))
        ped = max(6, int(round(11 * s)))
        ayrac = max(4, int(round(9 * s)))
        sutun_ara = max(8, int(round(24 * s)))
        o = _panel_olcu(satirlar, f, kal, ped, ayrac, sutun_ara)
        if o["genislik"] <= HUD_MAKS_PAY * img.shape[1] or s <= HUD_MIN_OLCEK:
            break
        s *= (HUD_MAKS_PAY * img.shape[1]) / o["genislik"]

    bar = max(3, int(round(5 * s)))
    pw, ph = o["genislik"] + bar, o["yukseklik"]
    _karart(img, 0, 0, pw, ph)
    cv2.rectangle(img, (0, 0), (bar, ph), vurgu, -1)          # durum rengi seridi
    cv2.rectangle(img, (0, 0), (pw - 1, ph - 1), (60, 60, 60),
                  max(1, int(round(s))))

    y = ped + o["yuk"]
    for satir in satirlar:
        x = bar + ped
        for c, (ad, deger, renk) in enumerate(satir):
            _yaz(img, ad + ":", (x, y), f, ETIKET_RENK, kal)
            _yaz(img, deger, (x + o["ad_w"][c] + ayrac, y), f, renk, kal)
            x += o["hucre_w"][c] + sutun_ara
        y += o["satir_h"]


def ciz(img, kare, sonuc, adaylar, fps, kilitli, gecikme_ms=0.0,
        tur="kaynak", toplam=0, hedef_id=None):
    """Ekran ustu bilgi. Kaynak ne olursa olsun ayni; GT varsa ek olarak cizilir.

    Yalnizca gorsellestirme: hicbir metrik burada hesaplanmaz, `sonuc` sozlugu
    degistirilmez.
    """
    durum = sonuc["durum"]
    h, w = img.shape[:2]
    s = hud_olcek(w, h)
    f_etiket = 0.58 * s
    kal = max(1, int(round(2.2 * s)))
    bosluk = max(2, int(round(4 * s)))
    vurgu = DURUM_RENK.get(durum, DURUM_RENK[ARAMA])

    # --- kutular: GT kesik yesil, takip duz durum renginde ---
    gt_rozet = None
    if kare.gt is not None and kare.gorunur:
        _kesikli_kutu(img, kare.gt, GT_RENK, max(1, int(round(1.6 * s))),
                      round(4 * s))
        gt_rozet = _kutu_etiketi(img, "GT", kare.gt, GT_RENK, f_etiket, kal,
                                 bosluk)
    if (not kilitli) or durum in (ARAMA, KAYIP):
        for a in (adaylar or []):
            _kutu_ciz(img, a["kutu"], ADAY_RENK, max(1, int(round(s))))
    if kilitli and sonuc["kutu"] is not None:
        _kutu_ciz(img, sonuc["kutu"], vurgu, max(2, int(round(2.4 * s))))
        _kutu_etiketi(img, "TRACK", sonuc["kutu"], vurgu, f_etiket, kal,
                      bosluk, yasak=gt_rozet)

    # --- tek bilgi paneli ---
    ad = DURUM_ADI.get(durum, durum) if kilitli else "SCANNING"
    hedef = f"#{hedef_id}" if hedef_id is not None else YOK
    ioumetin = f"{sonuc['iou']:.3f}" if sonuc.get("iou") is not None else YOK
    merkez = (f"{sonuc['merkez_hata']:.1f} px"
              if sonuc.get("merkez_hata") is not None else YOK)
    olcu_renk = GT_RENK if sonuc.get("iou") is not None else ETIKET_RENK
    sayac = f"{kare.indeks} / {toplam}" if toplam > 0 else str(kare.indeks)
    psr = f"{sonuc['psr']:.1f}" if kilitli else f"{len(adaylar or [])} cand"
    satirlar = [
        [("STATUS", ad, vurgu), ("TARGET", hedef, DEGER_RENK)],
        [("FPS", f"{fps:.1f}", DEGER_RENK), ("IoU", ioumetin, olcu_renk)],
        [("LATENCY", f"{gecikme_ms:.1f} ms", DEGER_RENK),
         ("CENTER", merkez, olcu_renk)],
        [("FRAME", sayac, DEGER_RENK), ("PSR", psr, DEGER_RENK)],
        [("SOURCE", f"[{tur}] {kare.kaynak_adi.split(':', 1)[-1]}  "
                    f"{kare.genislik}x{kare.yukseklik}", DEGER_RENK)],
    ]
    _bilgi_paneli(img, satirlar, s, vurgu)


def goster(pencere, img, bekleme_ms, duraklat):
    """Doner: (durum, tus). durum: "devam" | "duraklat" | "cik". `tus`: ham
    `cv2.waitKey` kodu (0xFF maskeli) - CANLI kaynaklarin (`gazebo_canli`)
    klavye kontrolu icin (bkz. `veri/gazebo_canli.py:GazeboCanliKaynak.
    tus_isle`); diger kaynaklar YOK SAYAR, DAVRANIS DEGISMEZ. Bosluk
    duraklat, n tek kare, q/ESC cik."""
    cv2.imshow(pencere, img)
    while True:
        tus = cv2.waitKey(0 if duraklat else bekleme_ms) & 0xFF
        if tus in (27, ord("q")):
            return "cik", tus
        if tus == ord(" "):
            duraklat = not duraklat
            if not duraklat:
                return "devam", tus
            continue
        if duraklat and tus in (ord("n"), 83):
            return "duraklat", tus
        if not duraklat:
            return "devam", tus


def _hafif_ciz(img, sonuc):
    """Canli pencere icin HAFIF HUD (Adim 4 duzeltmesi - THREAD kalkti,
    agir `ciz()`/panel yerine kutu + 2 satir, senkron ama ucuz).

    CANLI mod (2026-09-08): `sonuc` icinde varsa `mod`/`px`/`irtifa` de
    3. satirda gosterilir - digerlerinde bu alanlar YOK, satir hic
    eklenmez (DAVRANIS DEGISMEZ)."""
    _kutu_ciz(img, sonuc.get("kutu"), (255, 120, 0), 2)
    komut = f" komut={sonuc['komut']}" if sonuc.get("komut") else ""
    cv2.putText(img, f"durum={sonuc['durum']}{komut}", (8, 22),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(img, f"kare={sonuc.get('kare_no', '?')}", (8, 44),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    if any(k in sonuc for k in ("mod", "px", "irtifa")):
        px = sonuc.get("px")
        irtifa = sonuc.get("irtifa")
        parcalar = [f"mod={sonuc['mod']}"] if sonuc.get("mod") else []
        if px is not None:
            parcalar.append(f"px={px:.0f}")
        if irtifa is not None:
            parcalar.append(f"irtifa={irtifa:.1f}m")
        cv2.putText(img, "  ".join(parcalar), (8, 66),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)


def kos(kaynak, cekirdek="renk_dcf", pencere=True, kaydet=None, max_kare=0,
        hedef_secici=None, kayip_dedektor=None, dedektor_boyut=False,
        dedektor_karar=False, n_tespit=1, demo_kayit=False, mod_etiketi=None,
        koruma_esik=None, min_kenar=None):
    """Kaynak-bagimsiz calisma dongusu.

    `hedef_secici`: None ise `otomatik_hedef_sec` kullanilir. Fare ile secim
    geldiginde buraya baska bir fonksiyon verilecek; dongu degismeyecek.
    `kayip_dedektor`/`dedektor_boyut`/`dedektor_karar`: varsayilanlarinda
    (None/False) davranis BIREBIR eskisi gibidir (bkz.
    `takip/izleyici.py:HedefTakip`); DEMO modu ucunu de verir.
    `koruma_esik`/`min_kenar`: None ise `HedefTakip` varsayilanlarinda
    (IMX500 nativ 2028px icin kalibre) davranis BIREBIR eskisi gibidir;
    kamera nativ cozunurlugu farkliysa (bkz. `--tuval-olcek`) cagiran
    bunlari `TUVAL_OLCEK` ile ONCEDEN olcekleyip verir.
    `demo_kayit` (Adim 4, DUZELTME - THREAD KALKTI): True ise `kaydet` HAM
    kareyi yazar (ciz() YOK) + kare basina durum bir `.jsonl` yan dosyasina
    yazilir (ayni govde, uzanti .jsonl - `gazebo/gorsel_uret.py` HUD'lu
    videoyu bunlardan OFFLINE uretir). `pencere` ile birlikte hafif HUD
    (`_hafif_ciz`) senkron cizilir - agir `ciz()` bu yolda KULLANILMAZ.
    """
    secici = hedef_secici or otomatik_hedef_sec
    tak_kw = {}
    if koruma_esik is not None:
        tak_kw["koruma_esik"] = koruma_esik
    if min_kenar is not None:
        tak_kw["min_kenar"] = min_kenar
    tak = HedefTakip(cekirdek=cekirdek, kayip_dedektor=kayip_dedektor,
                     dedektor_boyut=dedektor_boyut, dedektor_karar=dedektor_karar,
                     n_tespit=n_tespit, **tak_kw)
    kilitli = False
    yaz = None
    duraklat = False
    sureler = deque(maxlen=30)      # anlik FPS icin kayan pencere
    gecikmeler = []                 # tum kareler: p50 / p95 icin
    olcum = []                      # GT varsa kare kare: iou, merkez hata, durum
    kayip_basi, kurtarmalar = None, []
    # DRIFT KARESI (A3.9): IoU'nun ilk kez SUREKLI olarak esigin altina
    # dustugu kare. Tek karelik gurultu kopma sayilmasin diye sabir sayaci
    # var; "kesinti" sayisindan farkli olarak yalnizca ILK kopmayi verir ve
    # kamera hareketi siddetiyle iliskilendirilecek olan budur.
    t_drift, _drift_sayac = None, 0
    bekleme = max(1, int(1000.0 / kaynak.fps)) if kaynak.fps > 0 else 1
    hedef_id = getattr(kaynak, "track_id", None)   # VisDrone track; yoksa None

    if pencere:
        # WINDOW_NORMAL  : kullanici fareyle boyutlandirabilsin
        # WINDOW_KEEPRATIO: elle boyutlandirirken en-boy orani korunsun
        cv2.namedWindow(kaynak.ad, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        cv2.resizeWindow(kaynak.ad, *pencere_boyutu(kaynak.genislik,
                                                    kaynak.yukseklik))

    json_yol = None
    json_f = None
    if demo_kayit and kaydet:
        json_yol = os.path.splitext(kaydet)[0] + ".jsonl"
        os.makedirs(os.path.dirname(json_yol) or ".", exist_ok=True)
        json_f = open(json_yol, "w")
    pozlar = getattr(kaynak, "pozlar", None)   # gazebo kaynagi: kare basina kam_z

    try:
        for kare in kaynak:
            t0 = time.perf_counter()
            adaylar = []
            if not kilitli:
                adaylar = tak.tarama(kare.goruntu)
                if kare.indeks >= ISINMA:
                    secili = secici(adaylar, kare)
                    if secili is not None:
                        kutu = secili["kutu"].copy()
                        kutu[2:] = np.maximum(kutu[2:] - 2.0, 4.0)   # dilate telafisi
                        kutu[:2] = secili["merkez"] - kutu[2:] / 2
                        tak.kilitle(kare.goruntu, kutu)
                        kilitli = True
                sonuc = {"kutu": tak.kutu, "durum": tak.durum, "psr": 0.0,
                        "komut": None, "sure": {}}
            else:
                sonuc = tak.guncelle(kare.goruntu)
                adaylar = tak.son_adaylar
            gecikme = time.perf_counter() - t0          # islem: takip (cizim haric)

            # --- GT varsa olcum (kaynaktan bagimsiz) ---
            sonuc["iou"] = sonuc["merkez_hata"] = None
            if kilitli and kare.gt is not None and kare.gorunur:
                sonuc["iou"] = iou(sonuc["kutu"], kare.gt)
                tk, gt = sonuc["kutu"], kare.gt
                sonuc["merkez_hata"] = float(np.hypot(
                    tk[0] + tk[2] / 2 - (gt[0] + gt[2] / 2),
                    tk[1] + tk[3] / 2 - (gt[1] + gt[3] / 2)))
                if sonuc["iou"] < DRIFT_ESIK:
                    _drift_sayac += 1
                    if _drift_sayac >= DRIFT_SABIR and t_drift is None:
                        t_drift = kare.indeks - DRIFT_SABIR + 1
                else:
                    _drift_sayac = 0
                kilit = sonuc["durum"] == KILITLI and sonuc["iou"] > 0.2
                if not kilit and kayip_basi is None:
                    kayip_basi = kare.indeks
                elif kilit and kayip_basi is not None:
                    kurtarmalar.append(kare.indeks - kayip_basi)
                    kayip_basi = None
                olcum.append({
                    "kare": kare.indeks, "iou": sonuc["iou"],
                    "merkez_hata": sonuc["merkez_hata"],
                    "durum": sonuc["durum"],
                    "gt_w": float(gt[2]), "gt_h": float(gt[3])})

            sureler.append(gecikme)
            gecikmeler.append(gecikme * 1e3)
            fps = len(sureler) / max(1e-6, sum(sureler))

            if demo_kayit:
                # Adim 4 DUZELTME: THREAD YOK - kaydet HAM kareyi yazar
                # (ciz() maliyeti yok), durum ayri .jsonl'e dusuyor; HUD'lu
                # video `gazebo/gorsel_uret.py` ile OFFLINE uretilir.
                kutu = sonuc.get("kutu")
                px = float(max(kutu[2], kutu[3])) if kutu is not None else None
                # irtifa: kayitli gazebo kaynaginda pozlar'dan (kam_z), CANLI
                # kaynakta (pozlar YOK) `kaynak.irtifa`den (bkz.
                # veri/gazebo_canli.py:GazeboCanliKaynak.irtifa) - DAVRANIS
                # ikisi de yoksa DEGISMEZ (None).
                irtifa = (pozlar[kare.indeks].get("kam_z")
                         if pozlar is not None and kare.indeks < len(pozlar)
                         else getattr(kaynak, "irtifa", None))
                if kaydet:
                    if yaz is None:
                        os.makedirs(os.path.dirname(kaydet) or ".", exist_ok=True)
                        yaz = cv2.VideoWriter(
                            kaydet, cv2.VideoWriter_fourcc(*"mp4v"),
                            kaynak.fps if kaynak.fps > 0 else 30.0,
                            (kare.genislik, kare.yukseklik))
                    yaz.write(kare.goruntu)
                    if json_f is not None:
                        roi = (getattr(kayip_dedektor, "son_roi", None)
                              if kayip_dedektor is not None and sonuc["durum"] in (ARAMA, KAYIP)
                              else None)
                        json_f.write(json.dumps({
                            "kare": kare.indeks, "durum": sonuc["durum"],
                            "kutu": [float(v) for v in kutu] if kutu is not None else None,
                            "roi": list(roi) if roi is not None else None,
                            "px": px, "irtifa": irtifa, "mod": mod_etiketi,
                            "komut": sonuc.get("komut"), "iou": sonuc.get("iou"),
                            "gt": [float(v) for v in kare.gt] if kare.gt is not None else None,
                        }) + "\n")
                if pencere:
                    _hafif_ciz(kare.goruntu, {**sonuc, "kare_no": kare.indeks,
                                              "mod": mod_etiketi, "px": px,
                                              "irtifa": irtifa})
                    cevap, tus = goster(kaynak.ad, kare.goruntu, bekleme, duraklat)
                    if hasattr(kaynak, "tus_isle"):
                        kaynak.tus_isle(tus)
                    if cevap == "cik":
                        break
                    duraklat = (cevap == "duraklat")
            elif pencere or kaydet:
                ciz(kare.goruntu, kare, sonuc, adaylar, fps, kilitli,
                    gecikme * 1e3, kaynak.tur, kaynak.kare_sayisi,
                    hedef_id=hedef_id)
                if kaydet:
                    if yaz is None:
                        os.makedirs(os.path.dirname(kaydet) or ".", exist_ok=True)
                        yaz = cv2.VideoWriter(
                            kaydet, cv2.VideoWriter_fourcc(*"mp4v"),
                            kaynak.fps if kaynak.fps > 0 else 30.0,
                            (kare.genislik, kare.yukseklik))
                    yaz.write(kare.goruntu)
                if pencere:
                    cevap, tus = goster(kaynak.ad, kare.goruntu, bekleme, duraklat)
                    if hasattr(kaynak, "tus_isle"):
                        kaynak.tus_isle(tus)
                    if cevap == "cik":
                        break
                    duraklat = (cevap == "duraklat")

            if max_kare and kare.indeks + 1 >= max_kare:
                break
    finally:
        kaynak.kapat()
        if yaz is not None:
            yaz.release()
        if json_f is not None:
            json_f.close()
        if pencere:
            cv2.destroyWindow(kaynak.ad)

    g = np.array(gecikmeler, np.float64) if gecikmeler else np.zeros(1)
    m = {
        "kaynak": kaynak.ad,
        "tur": kaynak.tur,
        "kare": len(gecikmeler),
        "kilitli": kilitli,
        "fps": float(1000.0 / g.mean()) if gecikmeler else 0.0,
        "gecikme_ort": float(g.mean()),
        "gecikme_p50": float(np.percentile(g, 50)),
        "gecikme_p95": float(np.percentile(g, 95)),
        "gecikme_max": float(g.max()),
        "gt_kare": len(olcum),
        "json_yol": json_yol,
    }
    if olcum:
        io = np.array([r["iou"] for r in olcum], np.float64)
        mh = np.array([r["merkez_hata"] for r in olcum], np.float64)
        kos = np.array([np.hypot(r["gt_w"], r["gt_h"]) for r in olcum], np.float64)
        m.update({
            "ort_iou": float(io.mean()),
            "basari@0.5": float((io > 0.5).mean()),
            "basari@0.3": float((io > 0.3).mean()),
            "merkez_hata": float(np.median(mh)),
            "hassasiyet": float((mh < np.maximum(4.0, 0.5 * kos)).mean()),
            "kilit_orani": float(np.mean([r["durum"] == KILITLI for r in olcum])),
            "t_drift": t_drift,
            "hedef_kayip": float(np.mean([r["durum"] != KILITLI for r in olcum])),
            "kesinti": len(kurtarmalar),
            "kurtarma_ort": float(np.mean(kurtarmalar)) if kurtarmalar else 0.0,
            "kurtarma_max": int(max(kurtarmalar)) if kurtarmalar else 0,
            "gt_boyut": (float(np.mean([r["gt_w"] for r in olcum])),
                         float(np.mean([r["gt_h"] for r in olcum]))),
            "_olcum": olcum,
        })
    return m


def main():
    ap = argparse.ArgumentParser(
        description="Drone hedef takip - simulator / video / kamera",
        epilog="ornek: python3 main.py --source data/videos/drone_traffic_01.mp4")
    ap.add_argument("--source", default="sim",
                    help="sim | sim:test6 | camera | camera:1 | <video dosyasi yolu>")
    ap.add_argument("--input", default=None,
                    help="video dosyasi yolu (eski bicim: --source video ile)")
    ap.add_argument("--camera-id", type=int, default=0, dest="camera_id")
    ap.add_argument("--scenario", default="test1", help="sim senaryosu (test1..test7)")
    ap.add_argument("--dataset", default=None,
                    help="veri kumesi kok klasoru (varsayilan: data/datasets/visdrone_vid)")
    ap.add_argument("--sequence", default=None, help="VisDrone dizi adi")
    ap.add_argument("--track-id", type=int, default=None, dest="track_id",
                    help="hedef track id (verilmezse en uzun arac track'i)")
    ap.add_argument("--olcek", type=float, default=1.0, help="downscale carpani")
    ap.add_argument("--hedef-genislik", type=int, default=0, dest="hedef_genislik",
                    help="kareyi bu genislige indir (olcek'ten oncelikli)")
    ap.add_argument("--cekirdek", default="renk_dcf", help="renk_dcf | mosse | ncc | akis")
    ap.add_argument("--kaydet", default=None, help="cikti videosu yolu")
    ap.add_argument("--max-kare", type=int, default=0, dest="max_kare")
    ap.add_argument("--penceresiz", action="store_true", help="ekranda pencere acma")
    ap.add_argument("--sec", action="store_true",
                    help="hedefi FARE ile sec (A4); verilmezse otomatik secim")
    ap.add_argument("--yolo", default=None, metavar="AGIRLIK",
                    help="hedefi YOLO ile sec (A5), or: weights/yolov8n.pt")
    ap.add_argument("--yolo-conf", type=float, default=0.25, dest="yolo_conf",
                    help="YOLO guven esigi (varsayilan 0.25)")
    ap.add_argument("--yolo-gt-esle", action="store_true", dest="yolo_gt_esle",
                    help="YOLO tespitleri icinden GT'ye en yakini (adil SOT olcumu)")
    ap.add_argument("--mod", default="klasik", choices=["klasik", "demo"],
                    help="demo: A6 + adaptif ROI edinme + karo taramali KAYIP "
                         "(Adim 3a/3b, bkz. demo_ayar.py)")
    ap.add_argument("--n-tespit", type=int, default=None, dest="n_tespit",
                    help="demo modu dedektor kadansi (1=her kare, 2/3=... "
                         "araya DCF koprusu girer) - verilmezse demo_ayar.N_TESPIT")
    ap.add_argument("--tuval-olcek", type=float, default=1.0, dest="tuval_olcek",
                    help="--mod demo: aktif kamera odak_px / 1561 (IMX500 nativ) "
                         "- demo_ayar.R_MERDIVEN ve HedefTakip.koruma_esik/"
                         "min_kenar'i orantili yeniden olcekler (kucuk-tuval "
                         "kamera icin gerekli, bkz. docs/DEMO_SONUC.md); "
                         "verilmezse (1.0) davranis BIREBIR eskisi gibidir")
    ap.add_argument("--hedef-gt-ilk", action="store_true", dest="hedef_gt_ilk",
                    help="--mod demo: ilk kilit demo_hedef_sec (soguk edinme, "
                         "YOLO+karo tarama) YERINE kayitli GT kutusuyla yapilir "
                         "(VisDrone --yolo-gt-esle ile AYNI ilke: tikla-sec'in "
                         "kayit karsiligi) - ilk kilidin KENDI hatasini olcum "
                         "disi birakip yalniz kilit-SONRASI kurtarmayi/takibi "
                         "test eder (bkz. docs/DEMO_SONUC.md 'v1 + GT-ilk-kilit')")
    ap.add_argument("--gui", action="store_true",
                    help="--source gazebo_canli: gz sim'in KENDI gorsel "
                         "istemcisini de ac (`gz sim -g`, izlemek icin - "
                         "takip hattini etkilemez, WSL2'de X/WSLg gerekir)")
    ap.add_argument("--sure", type=float, default=None,
                    help="--source gazebo_canli: bu sure (sn, duvar saati) "
                         "dolunca kaynak temiz bicimde biter - sinirli-sureli "
                         "otomatik/kabul kosumlari icin; verilmezse sinirsiz")
    a = ap.parse_args()

    if a.mod == "demo":
        import demo_ayar
        from ultralytics import YOLO
        _demo_model = YOLO(demo_ayar.A6_AGIRLIK)
        # kaynak boyutu bilinmeden karayici kurulamaz -> kaynak_olustur'dan
        # SONRA (asagida) baglanir; burada yalniz modeli yukle.
        a.yolo = None  # demo kendi edinme yolunu kurar, --yolo'yla CAKISMASIN

    # --- hedef secici: uc yol, oncelik --sec > --yolo > otomatik ---
    secici = None
    if a.sec:
        if a.yolo:
            print("UYARI: --sec ve --yolo birlikte verildi; --sec onceliklidir.")
        secici = fare_hedef_sec()
    elif a.yolo:
        from veri.yolo_secici import YoloHatasi, yolo_hedef_sec
        try:
            secici = yolo_hedef_sec(a.yolo, conf=a.yolo_conf,
                                    gt_esle=a.yolo_gt_esle)
        except YoloHatasi as e:
            print(f"HATA: {e}")
            sys.exit(1)

    try:
        kaynak = kaynak_olustur(a.source, girdi=a.input,
                                kamera_id=a.camera_id, senaryo=a.scenario,
                                veri_kok=a.dataset, dizi=a.sequence,
                                track_id=a.track_id, olcek=a.olcek,
                                hedef_genislik=a.hedef_genislik,
                                gui=a.gui, sure_sn=a.sure)
    except KaynakHatasi as e:
        print(f"HATA: {e}")
        sys.exit(1)

    kayip_dedektor = None
    koruma_esik = min_kenar = None
    if a.mod == "demo":
        if a.tuval_olcek != 1.0:
            demo_ayar.ayarla_tuval_olcek(a.tuval_olcek)
            koruma_esik = KORUMA_ESIK_VARSAYILAN * a.tuval_olcek
            min_kenar = 4.0 * a.tuval_olcek
        karayici = demo_ayar.KaroArayici(kaynak.genislik, kaynak.yukseklik, _demo_model)
        karayici.sifirla((kaynak.genislik / 2.0, kaynak.yukseklik / 2.0))
        # --hedef-gt-ilk: ilk kilit demo_hedef_sec (soguk edinme) YERINE GT -
        # kilit-SONRASI kurtarma (kayip_dedektor=karayici, dedektor_karar)
        # DEGISMEDEN kalir, yalniz ilk-kilidin KENDI hatasi olcum disi kalir.
        secici = gt_hedef_sec if a.hedef_gt_ilk else demo_ayar.demo_hedef_sec(karayici)
        kayip_dedektor = karayici

    print(kaynak.bilgi())
    try:
        m = kos(kaynak, cekirdek=a.cekirdek, pencere=not a.penceresiz,
                kaydet=a.kaydet, max_kare=a.max_kare,
                hedef_secici=secici, kayip_dedektor=kayip_dedektor,
                dedektor_boyut=(a.mod == "demo" and demo_ayar.DEDEKTOR_BOYUT_OTORITESI),
                dedektor_karar=(a.mod == "demo" and demo_ayar.DEDEKTOR_KARAR_OTORITESI),
                n_tespit=(a.n_tespit if a.n_tespit is not None else
                         (demo_ayar.N_TESPIT if a.mod == "demo" else 1)),
                demo_kayit=(a.mod == "demo"), mod_etiketi=a.mod,
                koruma_esik=koruma_esik, min_kenar=min_kenar)
    except KaynakHatasi as e:
        print(f"HATA: {e}")
        sys.exit(1)
    print("-" * 58)
    print(f"  kaynak      : {m['kaynak']}  ({m['tur']})")
    print(f"  islenen kare: {m['kare']}")
    print(f"  hedef       : {'KILITLENDI' if m['kilitli'] else 'kilitlenmedi'}")
    print(f"  FPS         : {m['fps']:.1f}")
    print(f"  gecikme     : ort {m['gecikme_ort']:.2f} ms | "
          f"p50 {m['gecikme_p50']:.2f} | p95 {m['gecikme_p95']:.2f} | "
          f"max {m['gecikme_max']:.2f}")
    if m.get("json_yol"):
        print(f"  durum JSON  : {m['json_yol']} (HUD'lu video icin gorsel_uret.py'ye verilir)")
    if m.get("gt_kare"):
        print(f"  --- GT ile olcum ({m['gt_kare']} kare) ---")
        print(f"  IoU         : {m['ort_iou']:.3f}  "
              f"(@0.5 {m['basari@0.5']:.1%} | @0.3 {m['basari@0.3']:.1%})")
        print(f"  merkez hata : {m['merkez_hata']:.2f} px  "
              f"(hassasiyet {m['hassasiyet']:.1%})")
        print(f"  kilit orani : {m['kilit_orani']:.1%}  "
              f"(hedef kayip {m['hedef_kayip']:.1%})")
        print(f"  kurtarma    : {m['kesinti']} kesinti, "
              f"ort {m['kurtarma_ort']:.0f} kare, max {m['kurtarma_max']} kare")
        print(f"  drift karesi: "
              f"{'yok' if m['t_drift'] is None else m['t_drift']}"
              f"  (IoU<{DRIFT_ESIK} x {DRIFT_SABIR} kare)")
        print(f"  hedef boyut : {m['gt_boyut'][0]:.1f} x {m['gt_boyut'][1]:.1f} px")
    if a.kaydet:
        print(f"  kayit       : {a.kaydet}")


if __name__ == "__main__":
    main()
