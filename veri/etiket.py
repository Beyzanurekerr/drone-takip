"""Ortak ground-truth temsili + VisDrone annotation ayristirici.

VisDrone bicimi dogrudan takip tarafina tasinmaz; once bu moduldeki `Etiket`
yapisina cevrilir. Boylece ileride UAV123 / UAVDT / DTB70 eklendiginde olcum
tarafi degismez.

VisDrone VID/MOT annotation satiri (10 kolon, virgul ayrik):

    102,0,38,666,71,88,1,1,1,0
    kare,track_id,x,y,w,h,score,sinif,kirpilma,ortulme

VisDrone DET annotation satiri (8 kolon; kare ve track_id yok):

    871,572,54,92,1,4,0,0
    x,y,w,h,score,sinif,kirpilma,ortulme

Kaynak: VisDrone2019 toolkit README (deger araliklari `data/datasets/` altindaki
gercek dosyalardan dogrulanmistir).
"""
import os
from dataclasses import dataclass

import numpy as np

SINIFLAR = {
    0: "ignored", 1: "pedestrian", 2: "people", 3: "bicycle", 4: "car",
    5: "van", 6: "truck", 7: "tricycle", 8: "awning-tricycle", 9: "bus",
    10: "motor", 11: "others",
}

# Bizim ilgilendigimiz siniflar: araclar
ARAC_SINIFLARI = (4, 5, 6, 9)          # car, van, truck, bus

ORTULME = {0: "yok", 1: "kismi", 2: "agir"}


class EtiketHatasi(Exception):
    """Annotation dosyasi okunamadi / bozuk / bos."""


@dataclass
class Etiket:
    """Tek bir ground-truth kutusu."""
    kare: int                # 1-tabanli (VisDrone boyle); DET'te 0
    track_id: int            # DET'te -1
    sinif: int
    kutu: np.ndarray         # (x, y, w, h) float32, sol-ust kokenli
    yoksayilan: bool         # score==0 ya da sinif==0 -> olcume katilmaz
    kirpilma: int            # 0 = kadraj icinde, 1 = kenardan kirpik
    ortulme: int             # 0 yok, 1 kismi, 2 agir

    @property
    def merkez(self) -> np.ndarray:
        return self.kutu[:2] + self.kutu[2:] / 2.0

    @property
    def arac_mi(self) -> bool:
        return self.sinif in ARAC_SINIFLARI

    @property
    def sinif_adi(self) -> str:
        return SINIFLAR.get(self.sinif, f"bilinmeyen({self.sinif})")

    def olcekli(self, k: float) -> "Etiket":
        """Kare kucultuldugunde GT kutusu AYNI oranda kucultulmeli."""
        if k == 1.0:
            return self
        return Etiket(self.kare, self.track_id, self.sinif,
                      (self.kutu * float(k)).astype(np.float32),
                      self.yoksayilan, self.kirpilma, self.ortulme)


def _sayi(parca, dosya, satir_no, kolon):
    try:
        return int(float(parca))
    except ValueError:
        raise EtiketHatasi(
            f"{os.path.basename(dosya)}:{satir_no} {kolon}. kolon sayi degil: "
            f"{parca!r}")


def vid_oku(yol: str) -> dict:
    """VisDrone VID/MOT annotation dosyasini oku.

    Doner: {kare_no: [Etiket, ...]}  — kare numaralari 1-tabanli.
    Dosya track_id'ye gore siralidir, kareye gore degil; burada kareye gore
    gruplanir.
    """
    if not os.path.exists(yol):
        raise EtiketHatasi(f"annotation dosyasi bulunamadi: {yol}")

    kareler = {}
    n = 0
    with open(yol, "r") as f:
        for satir_no, satir in enumerate(f, 1):
            satir = satir.strip().rstrip(",")
            if not satir:
                continue
            p = satir.split(",")
            if len(p) < 10:
                raise EtiketHatasi(
                    f"{os.path.basename(yol)}:{satir_no} 10 kolon bekleniyordu, "
                    f"{len(p)} bulundu: {satir!r}")
            kare = _sayi(p[0], yol, satir_no, 1)
            track_id = _sayi(p[1], yol, satir_no, 2)
            x, y, w, h = (_sayi(p[i], yol, satir_no, i + 1) for i in range(2, 6))
            skor = _sayi(p[6], yol, satir_no, 7)
            sinif = _sayi(p[7], yol, satir_no, 8)
            if w <= 0 or h <= 0:
                raise EtiketHatasi(
                    f"{os.path.basename(yol)}:{satir_no} gecersiz kutu boyutu: "
                    f"{w}x{h}")
            e = Etiket(kare=kare, track_id=track_id, sinif=sinif,
                       kutu=np.array([x, y, w, h], np.float32),
                       yoksayilan=(skor == 0 or sinif == 0),
                       kirpilma=_sayi(p[8], yol, satir_no, 9),
                       ortulme=_sayi(p[9], yol, satir_no, 10))
            kareler.setdefault(kare, []).append(e)
            n += 1

    if n == 0:
        raise EtiketHatasi(f"annotation dosyasi bos: {yol}")
    return kareler


def det_oku(yol: str) -> list:
    """VisDrone DET annotation dosyasini oku (8 kolon, tek goruntu).

    Su an olcume baglanmiyor; ileride YOLO fine-tuning icin kullanilacak.
    """
    if not os.path.exists(yol):
        raise EtiketHatasi(f"annotation dosyasi bulunamadi: {yol}")
    cikti = []
    with open(yol, "r") as f:
        for satir_no, satir in enumerate(f, 1):
            satir = satir.strip().rstrip(",")
            if not satir:
                continue
            p = satir.split(",")
            if len(p) < 8:
                raise EtiketHatasi(
                    f"{os.path.basename(yol)}:{satir_no} 8 kolon bekleniyordu, "
                    f"{len(p)} bulundu: {satir!r}")
            x, y, w, h = (_sayi(p[i], yol, satir_no, i + 1) for i in range(4))
            skor = _sayi(p[4], yol, satir_no, 5)
            sinif = _sayi(p[5], yol, satir_no, 6)
            cikti.append(Etiket(
                kare=0, track_id=-1, sinif=sinif,
                kutu=np.array([x, y, w, h], np.float32),
                yoksayilan=(skor == 0 or sinif == 0),
                kirpilma=_sayi(p[6], yol, satir_no, 7),
                ortulme=_sayi(p[7], yol, satir_no, 8)))
    return cikti


# ----------------------------------------------------------------------------
def track_ozeti(kareler: dict) -> dict:
    """{track_id: {"kare_sayisi", "ilk_kare", "son_kare", "sinif", "arac_mi"}}"""
    ozet = {}
    for kare_no, etiketler in kareler.items():
        for e in etiketler:
            if e.yoksayilan:
                continue
            o = ozet.setdefault(e.track_id, {
                "kare_sayisi": 0, "ilk_kare": kare_no, "son_kare": kare_no,
                "sinif": e.sinif, "arac_mi": e.arac_mi})
            o["kare_sayisi"] += 1
            o["ilk_kare"] = min(o["ilk_kare"], kare_no)
            o["son_kare"] = max(o["son_kare"], kare_no)
    return ozet


def track_bul(kareler: dict, track_id: int) -> dict:
    """{kare_no: Etiket} — verilen track'in tum kareleri. Yoksa hata."""
    cikti = {kare_no: e for kare_no, etiketler in kareler.items()
             for e in etiketler if e.track_id == track_id}
    if not cikti:
        mevcut = sorted(track_ozeti(kareler))
        ornek = ", ".join(str(t) for t in mevcut[:15])
        raise EtiketHatasi(
            f"track_id {track_id} bu dizide yok. "
            f"Mevcut id'ler ({len(mevcut)} adet): {ornek}"
            f"{' ...' if len(mevcut) > 15 else ''}")
    return cikti


def track_yolu(kareler: dict, track_id: int) -> float:
    """Track'in kare kare toplam yer degistirmesi (px)."""
    noktalar = [(k, e.merkez) for k in sorted(kareler)
                for e in kareler[k] if e.track_id == track_id and not e.yoksayilan]
    if len(noktalar) < 2:
        return 0.0
    m = np.array([p for _, p in noktalar], np.float64)
    return float(np.linalg.norm(np.diff(m, axis=0), axis=1).sum())


def en_uygun_arac_track(kareler: dict, min_kare: int = 30) -> int:
    """Olcume en uygun hedef: uzun sure gorunen ve HAREKET EDEN arac track'i.

    Sadece "en cok karede gorunen" secilirse park halindeki bir arac secilir
    (o hep kadrajdadir). Hareketsiz hedef takip olcumu icin anlamsizdir:
    hareket tabanli aday uretimi onu hic gormez ve sonuc yaniltici olur.
    Bu yuzden skor = kare sayisi x toplam yer degistirme.
    """
    ozet = {t: o for t, o in track_ozeti(kareler).items() if o["arac_mi"]}
    if not ozet:
        raise EtiketHatasi("bu dizide arac sinifindan hic track yok")
    uygun = {t: o for t, o in ozet.items() if o["kare_sayisi"] >= min_kare}
    if not uygun:
        uygun = ozet
    return max(uygun, key=lambda t: uygun[t]["kare_sayisi"] * track_yolu(kareler, t))
