"""VisDrone VID dizilerini `Kaynak` olarak sunar.

Klasor yapisi (gercek, data/datasets/visdrone_vid altindan dogrulandi):

    visdrone_vid/
    ├── annotations/<dizi>.txt
    └── sequences/<dizi>/0000001.jpg, 0000002.jpg, ...

Takip tarafi bu modulu gormez; `kaynak.py` uzerinden baglanir ve karsisinda
diger kaynaklarla ayni `Kare` yapisini bulur.

Hedef secimi: `track_id` verilir, o track'in ILK gorundugu karedeki GT kutusu
takipciye baslangic kutusu olarak verilir. Sonraki karelerde GT yalnizca OLCUM
icin kullanilir - takipciye beslenmez.
"""
import os

import cv2
import numpy as np

from kaynak import Kare, Kaynak, KaynakHatasi
from veri.etiket import (EtiketHatasi, en_uygun_arac_track, track_bul,
                         track_ozeti, vid_oku)

KARE_UZANTILARI = (".jpg", ".jpeg", ".png")


def diziler(kok: str) -> list:
    """Veri kumesindeki dizi adlarini bulur (sequence discovery)."""
    if not os.path.isdir(kok):
        raise KaynakHatasi(f"veri kumesi klasoru bulunamadi: {kok}")
    dizi_kok = os.path.join(kok, "sequences")
    ann_kok = os.path.join(kok, "annotations")
    if not os.path.isdir(dizi_kok):
        raise KaynakHatasi(
            f"'sequences' klasoru yok: {dizi_kok}\n"
            f"       VisDrone2019-VID-val.zip dogru yere acildi mi?")
    if not os.path.isdir(ann_kok):
        raise KaynakHatasi(f"'annotations' klasoru yok: {ann_kok}")
    return sorted(a for a in os.listdir(dizi_kok)
                  if os.path.isdir(os.path.join(dizi_kok, a)))


class VisDroneVidKaynak(Kaynak):
    """Tek bir VisDrone VID dizisi + secilen track'in ground-truth'u."""

    def __init__(self, kok: str, dizi: str = None, track_id: int = None,
                 olcek: float = 1.0, hedef_genislik: int = 0):
        mevcut = diziler(kok)
        if dizi is None:
            dizi = mevcut[0]
        if dizi not in mevcut:
            raise KaynakHatasi(
                f"dizi bulunamadi: {dizi!r}\n"
                f"       mevcut diziler: {', '.join(mevcut)}")

        self.kok = kok
        self.dizi = dizi
        self.kare_kok = os.path.join(kok, "sequences", dizi)
        self.ann_yolu = os.path.join(kok, "annotations", f"{dizi}.txt")

        # --- kare dosyalari ---
        self.kare_dosyalari = sorted(
            f for f in os.listdir(self.kare_kok)
            if os.path.splitext(f)[1].lower() in KARE_UZANTILARI)
        if not self.kare_dosyalari:
            raise KaynakHatasi(f"dizide hic kare yok: {self.kare_kok}")

        # --- annotation ---
        try:
            self.etiketler = vid_oku(self.ann_yolu)
        except EtiketHatasi as e:
            raise KaynakHatasi(str(e))

        self._senkron_dogrula()

        # --- hedef track ---
        # Bu katman disariya yalnizca KaynakHatasi verir; EtiketHatasi sizmamali.
        try:
            if track_id is None:
                track_id = en_uygun_arac_track(self.etiketler)
            self.hedef_kareler = track_bul(self.etiketler, int(track_id))
        except EtiketHatasi as e:
            raise KaynakHatasi(f"{dizi}: {e}")
        self.track_id = int(track_id)
        self.ilk_hedef_kare = min(self.hedef_kareler)

        # --- olcek ---
        ilk = cv2.imread(os.path.join(self.kare_kok, self.kare_dosyalari[0]))
        if ilk is None:
            raise KaynakHatasi(
                f"ilk kare okunamadi: {self.kare_dosyalari[0]} (bozuk jpg?)")
        self.ham_genislik, self.ham_yukseklik = ilk.shape[1], ilk.shape[0]
        if hedef_genislik and hedef_genislik > 0:
            olcek = hedef_genislik / float(self.ham_genislik)
        self.olcek = float(olcek)
        if not (0.05 <= self.olcek <= 1.0):
            raise KaynakHatasi(
                f"olcek 0.05-1.0 araliginda olmali, verilen: {self.olcek:.3f}")

        self.ad = f"visdrone:{dizi}"
        self.tur = "visdrone"
        self.genislik = int(round(self.ham_genislik * self.olcek))
        self.yukseklik = int(round(self.ham_yukseklik * self.olcek))
        self.fps = 30.0                     # VisDrone VID nominal
        self.kare_sayisi = len(self.kare_dosyalari)
        self._k = 0

    # ------------------------------------------------------------------
    def _senkron_dogrula(self):
        """Kare <-> annotation eslesmesini dogrula. Sessizce yanlis eslestirme."""
        n_kare = len(self.kare_dosyalari)

        # kare adlari sayisal ve 1..N kesintisiz mi?
        try:
            numaralar = [int(os.path.splitext(f)[0]) for f in self.kare_dosyalari]
        except ValueError:
            raise KaynakHatasi(
                f"kare dosya adlari sayisal degil: {self.kare_dosyalari[0]!r} "
                f"(0000001.jpg bekleniyordu)")
        if numaralar[0] != 1:
            raise KaynakHatasi(
                f"kare numaralari 1'den baslamiyor (ilk: {numaralar[0]})")
        eksik = sorted(set(range(1, n_kare + 1)) - set(numaralar))
        if eksik:
            raise KaynakHatasi(
                f"{self.dizi}: {len(eksik)} kare eksik, ilk eksikler: "
                f"{eksik[:5]}")

        # annotation kare numaralari kare sayisini asmamali
        ann_min, ann_max = min(self.etiketler), max(self.etiketler)
        if ann_min < 1:
            raise KaynakHatasi(
                f"{self.dizi}: annotation'da gecersiz kare numarasi {ann_min}")
        if ann_max > n_kare:
            raise KaynakHatasi(
                f"{self.dizi}: annotation {ann_max}. kareye atif yapiyor ama "
                f"dizide {n_kare} kare var (kare/GT sayisi uyusmuyor)")

    # ------------------------------------------------------------------
    def oku(self):
        if self._k >= self.kare_sayisi:
            return None
        k = self._k
        yol = os.path.join(self.kare_kok, self.kare_dosyalari[k])
        goruntu = cv2.imread(yol)
        if goruntu is None:
            raise KaynakHatasi(f"kare okunamadi: {yol}")
        if self.olcek != 1.0:
            goruntu = cv2.resize(goruntu, (self.genislik, self.yukseklik),
                                 interpolation=cv2.INTER_AREA)

        kare_no = k + 1                      # VisDrone 1-tabanli
        e = self.hedef_kareler.get(kare_no)
        gt = e.olcekli(self.olcek).kutu if e is not None else None
        self._k += 1
        return Kare(goruntu=goruntu, indeks=k, zaman=k / self.fps,
                    kaynak_adi=self.ad, genislik=self.genislik,
                    yukseklik=self.yukseklik, fps=self.fps,
                    gt=gt, gorunur=e is not None)

    def acik_mi(self):
        return self._k < self.kare_sayisi

    # ------------------------------------------------------------------
    def kare_etiketleri(self, kare_indeks: int) -> list:
        """Bir karedeki TUM GT kutulari (gorsellestirme icin), olcekli."""
        return [e.olcekli(self.olcek)
                for e in self.etiketler.get(kare_indeks + 1, [])]

    def bilgi(self):
        return (f"{self.ad}  {self.genislik}x{self.yukseklik} "
                f"(ham {self.ham_genislik}x{self.ham_yukseklik}, olcek "
                f"{self.olcek:.3f})  {self.kare_sayisi} kare  "
                f"hedef track {self.track_id} "
                f"({len(self.hedef_kareler)} karede gorunuyor, "
                f"ilk kare {self.ilk_hedef_kare})")

    def track_listesi(self):
        return track_ozeti(self.etiketler)
