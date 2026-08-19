"""Goruntu kaynagi soyutlamasi: simulator / video dosyasi / kamera.

Takip tarafi goruntunun NEREDEN geldigini bilmez. Uc kaynak da ayni sozlesmeyi
uygular:

    kaynak = kaynak_olustur("video", girdi="data/test.mp4")
    for kare in kaynak:              # kare.goruntu -> BGR ndarray
        sonuc = tak.guncelle(kare.goruntu)
    kaynak.kapat()

Neden ayri bir modul: mevcut `calistir.kos()` sahne adimi, render ve GT
uretimini dongunun ICINDE yapiyor; yani simulatorsuz calisamiyor. Bu modul o
dongunun sadece "kare uret" kismini disari cikarir. `calistir.py` ve
`kiyasla.py` bilerek DEGISTIRILMEDI - mevcut olcumler bit duzeyinde ayni kalsin.
"""
import os
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


class KaynakHatasi(Exception):
    """Kaynak acilamadi / okunamadi / desteklenmiyor."""


@dataclass
class Kare:
    """Tek bir kare + yaninda tasidigi bilgi.

    `gt` ve `gorunur` yalnizca simulatorde doludur (kusursuz ground-truth);
    video/kamera icin None'dir - "bilinmiyor" demektir.
    """
    goruntu: np.ndarray          # BGR, (y, x, 3) uint8
    indeks: int                  # 0'dan baslar
    zaman: float                 # saniye, kaynagin basindan itibaren
    kaynak_adi: str              # "sim:test6" / "video:test.mp4" / "kamera:0"
    genislik: int
    yukseklik: int
    fps: float                   # kaynagin nominal FPS'i (bilinmiyorsa 0.0)
    gt: Optional[np.ndarray] = None       # hedefin GT kutusu (x, y, w, h)
    gorunur: Optional[bool] = None        # hedef bu karede goruluyor mu


class Kaynak:
    """Ortak taban. Alt siniflar sadece `oku()` ve `kapat()` yazar.

    `oku()` -> Kare, ya da akis bittiyse None.

    Yeni bir kaynak eklemek (ornegin UAV123 / UAVDT dizisi okuyan bir adapter)
    icin yapilacak tek sey: bu siniftan turetip `oku()` yazmak ve
    `kaynak_olustur()`'a bir dal eklemek. Etiketli veri kumeleri karelerini
    `Kare.gt` alaniyla dondurur; boylece olcum tarafi simulatorden gelen GT ile
    dataset'ten gelen GT'yi ayirt etmek zorunda kalmaz.
    """
    ad = "kaynak"
    tur = "kaynak"       # "sim" | "video" | "kamera"  (ekranda gosterilir)
    genislik = 0
    yukseklik = 0
    fps = 0.0
    kare_sayisi = -1     # bilinmiyorsa -1 (kamera, bazi videolar)

    def oku(self) -> Optional[Kare]:
        raise NotImplementedError

    def kapat(self):
        pass

    def acik_mi(self) -> bool:
        """Kaynak halen kare verebilir durumda mi?"""
        return True

    # --- kolaylik: for dongusu ve with blogu ---
    def __iter__(self):
        return self

    def __next__(self) -> Kare:
        kare = self.oku()
        if kare is None:
            raise StopIteration
        return kare

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.kapat()
        return False

    def bilgi(self) -> str:
        n = f"{self.kare_sayisi} kare" if self.kare_sayisi > 0 else "surekli"
        return (f"{self.ad}  {self.genislik}x{self.yukseklik}  "
                f"{self.fps:.0f} fps  {n}")


# ----------------------------------------------------------------------------
class SimKaynak(Kaynak):
    """Mevcut prosedurel simulator. Kare basina kusursuz GT de verir.

    Dongu sirasi `calistir.kos()` ile BIREBIR aynidir (kamera -> step -> render);
    aksi halde ayni senaryo farkli goruntu uretirdi ve mevcut olcumler kayardi.
    """

    def __init__(self, senaryo: str = "test1"):
        from sim.senaryolar import TUM_TESTLER   # sim'i ancak gerekince yukle

        if senaryo not in TUM_TESTLER:
            raise KaynakHatasi(
                f"bilinmeyen senaryo: {senaryo!r}  "
                f"(secenekler: {', '.join(TUM_TESTLER)})")
        self.senaryo = TUM_TESTLER[senaryo]()
        self.sahne = self.senaryo.sahne
        self.hedef = self.senaryo.hedef
        self.ad = f"sim:{senaryo}"
        self.tur = "sim"
        self.genislik = self.sahne.cam.w
        self.yukseklik = self.sahne.cam.h
        self.fps = 1.0 / self.senaryo.dt
        self.kare_sayisi = self.senaryo.kare
        self._k = 0

    def oku(self):
        if self._k >= self.kare_sayisi:
            return None
        k = self._k
        self.senaryo.kamera_fn(self.sahne, k, self.senaryo.dt)
        self.sahne.step(self.senaryo.dt)
        goruntu = self.sahne.render()
        gt = self.sahne.gt_box(self.hedef)
        gorunur = self.sahne.visible(self.hedef)
        self._k += 1
        return Kare(goruntu=goruntu, indeks=k, zaman=k * self.senaryo.dt,
                    kaynak_adi=self.ad, genislik=self.genislik,
                    yukseklik=self.yukseklik, fps=self.fps,
                    gt=gt, gorunur=gorunur)

    def acik_mi(self):
        return self._k < self.kare_sayisi


# ----------------------------------------------------------------------------
class VideoKaynak(Kaynak):
    """Video dosyasi (mp4 / avi / mov ...). Dosya bitince duzgun sonlanir."""

    def __init__(self, yol: str):
        if not os.path.exists(yol):
            raise KaynakHatasi(f"video bulunamadi: {yol}")
        if os.path.isdir(yol):
            raise KaynakHatasi(f"klasor verildi, dosya bekleniyor: {yol}")
        self.yol = yol
        self.cap = cv2.VideoCapture(yol)
        if not self.cap.isOpened():
            self.cap.release()
            raise KaynakHatasi(
                f"video acilamadi (bozuk dosya ya da desteklenmeyen codec): {yol}")
        self.ad = f"video:{os.path.basename(yol)}"
        self.tur = "video"
        self.genislik = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.yukseklik = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self.cap.get(cv2.CAP_PROP_FPS))
        self.fps = fps if np.isfinite(fps) and fps > 0 else 0.0
        n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.kare_sayisi = n if n > 0 else -1     # bazi codec'ler bildirmez
        self._k = 0

    def oku(self):
        if self.cap is None:
            return None
        ok, goruntu = self.cap.read()
        if not ok or goruntu is None:
            return None                            # dosya sonu: normal bitis
        k = self._k
        self._k += 1
        ms = float(self.cap.get(cv2.CAP_PROP_POS_MSEC))
        if ms > 0:
            zaman = ms / 1000.0
        else:
            zaman = k / self.fps if self.fps > 0 else 0.0
        h, w = goruntu.shape[:2]
        return Kare(goruntu=goruntu, indeks=k, zaman=zaman, kaynak_adi=self.ad,
                    genislik=w, yukseklik=h, fps=self.fps)

    def kapat(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def acik_mi(self):
        return self.cap is not None and self.cap.isOpened()


# ----------------------------------------------------------------------------
class KameraKaynak(Kaynak):
    """Webcam / USB kamera. Kendiliginden bitmez; dongu disaridan durdurulur."""

    MAX_HATA = 3          # ust uste bu kadar okuma hatasi -> gercek ariza

    def __init__(self, kamera_id: int = 0, genislik: int = 0, yukseklik: int = 0):
        self.kamera_id = int(kamera_id)
        self.cap = cv2.VideoCapture(self.kamera_id)
        if not self.cap.isOpened():
            self.cap.release()
            raise KaynakHatasi(
                f"kamera acilamadi (index {self.kamera_id}). "
                f"Baska bir uygulama kullaniyor olabilir, index yanlis olabilir "
                f"ya da WSL kullaniyorsan USB kamera WSL'e baglanmamis olabilir.")
        if genislik and yukseklik:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(genislik))
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(yukseklik))
        self.ad = f"kamera:{self.kamera_id}"
        self.tur = "kamera"
        self.genislik = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.yukseklik = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self.cap.get(cv2.CAP_PROP_FPS))
        self.fps = fps if np.isfinite(fps) and 0 < fps < 1000 else 0.0
        self.kare_sayisi = -1
        self._k = 0
        self._t0 = time.perf_counter()
        self._hata = 0

    def oku(self):
        if self.cap is None:
            return None
        ok, goruntu = self.cap.read()
        if not ok or goruntu is None:
            self._hata += 1
            if self._hata >= self.MAX_HATA:
                raise KaynakHatasi(
                    f"kameradan {self.MAX_HATA} kare ust uste okunamadi "
                    f"(index {self.kamera_id}); cihaz cikarilmis olabilir")
            return self.oku()                      # gecici tokezleme: yeniden dene
        self._hata = 0
        k = self._k
        self._k += 1
        h, w = goruntu.shape[:2]
        return Kare(goruntu=goruntu, indeks=k,
                    zaman=time.perf_counter() - self._t0, kaynak_adi=self.ad,
                    genislik=w, yukseklik=h, fps=self.fps)

    def kapat(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def acik_mi(self):
        return self.cap is not None and self.cap.isOpened()


# ----------------------------------------------------------------------------
TURLER = ("sim", "video", "camera", "visdrone")
KAMERA_ADLARI = ("camera", "kamera", "webcam")
VISDRONE_VARSAYILAN = "data/datasets/visdrone_vid"
VIDEO_UZANTILARI = (".mp4", ".avi", ".mov", ".mkv", ".m4v", ".webm", ".mpg",
                    ".mpeg", ".wmv")


def kaynak_olustur(kaynak: str, girdi: str = None, kamera_id: int = 0,
                   senaryo: str = "test1", veri_kok: str = None,
                   dizi: str = None, track_id: int = None,
                   olcek: float = 1.0, hedef_genislik: int = 0) -> Kaynak:
    """Tek giris noktasi.

    Kabul edilen bicimler:
        "sim"                       -> senaryo parametresiyle simulator
        "sim:test6"                 -> senaryoyu dogrudan yaz
        "camera" / "camera:1"       -> kamera (varsayilan index 0)
        "video" + girdi="a.mp4"     -> eski bicim, geriye uyumluluk icin
        "data/videos/a.mp4"         -> DOGRUDAN DOSYA YOLU
        "visdrone"                  -> VisDrone VID dizisi (veri_kok, dizi,
                                       track_id, olcek parametreleriyle)

    Yeni bir kaynak tipi (dataset adapter'i vb.) eklemek icin buraya bir dal
    eklemek yeterlidir; cagiran taraf degismez.
    """
    ham = (kaynak or "").strip()
    t = ham.lower()

    # --- kisa bicimler: "sim:test6", "camera:1" ---
    on, _, arg = t.partition(":")
    if on == "sim":
        return SimKaynak(arg or senaryo)
    if on == "visdrone":
        from veri.visdrone import VisDroneVidKaynak     # ancak gerekince yukle
        return VisDroneVidKaynak(veri_kok or VISDRONE_VARSAYILAN,
                                 dizi=dizi or (arg or None), track_id=track_id,
                                 olcek=olcek, hedef_genislik=hedef_genislik)
    if on in KAMERA_ADLARI and arg:
        try:
            return KameraKaynak(int(arg))
        except ValueError:
            raise KaynakHatasi(f"kamera index'i sayi olmali: {arg!r}")

    if t == "video":
        if not girdi:
            raise KaynakHatasi("video kaynagi icin --input <dosya> gerekli")
        return VideoKaynak(girdi)
    if t in KAMERA_ADLARI:
        return KameraKaynak(kamera_id)

    # --- dosya yolu olarak yorumla ---
    if ham and (os.path.exists(ham)
                or os.path.splitext(ham)[1].lower() in VIDEO_UZANTILARI):
        return VideoKaynak(ham)

    raise KaynakHatasi(
        f"desteklenmeyen kaynak: {kaynak!r}\n"
        f"       secenekler: {', '.join(TURLER)} ya da bir video dosyasi yolu "
        f"({', '.join(VIDEO_UZANTILARI[:4])} ...)")
