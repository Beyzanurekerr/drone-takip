"""A11.2/T1 - renk_dcf doku kaymasinin KOK NEDENI: boyut zincirinden mi,
yoksa cekirdegin kendi arama/korelasyonundan mi geliyor?

Tek degiskenli A/B, hicbir kol `takip/` dosyalarina KALICI dokunmuyor -
tumu monkeypatch/subclass ile, calisma bitince ORIJINAL fonksiyonlar geri
yuklenir. `takip/izleyici.py` ve `takip/cekirdekler.py` DEGISMEDI.

KOLLAR:
  H0   kontrol - degistirilmemis HedefTakip (Y1'deki ayni protokol)
  T1a  boyut TAMAMEN donuk - kilitle()'de olculen boyut, `guncelle()`'nin
       HER cagrisindan once VE sonra zorla geri yazilir (ego-olcek carpimi,
       _boyut_tazele, _boyut_sinirla dahil HICBIRI boyutu degistiremez).
       Soru: kayma boyut zincirinden mi geliyor?
  T1b  rafine_kutu HER YERDE (kilitle/arama/_boyut_tazele) devre disi -
       None dondurur; ama `_boyut_tazele`'in KENDI ZAMANLAMASI
       (`dogrulama_araligi` tetikleyicisi) dokunulmadan acik kalir - o da
       zaten rafine_kutu=None ile no-op'a duser (kayit icin: T1b, T1a'dan
       farkli olarak ego-olcek carpimini SERBEST birakir).
  T1c  TESHIS (davranisi degistirmez): `cekirdekler._tepe`'ye sarmalayici -
       yanit haritasinin (r) birincil tepe DISINDAKI en yuksek "ikinci tepe"
       degerini de cikarir. Oran = (ikinci_tepe - yan_ort)/(tepe - yan_ort).
       PSR yalniz ORTALAMA yan-lob istatistigine bakar; guclu ama KUCUK bir
       ikinci tepe (serit cizgisi gibi dar bir cizgi) PSR'yi dusurmeyebilir.

OLCUM: ilk yanlis-kilit karesi, yanlis-kilit orani, kutu en-boy (h/w) zaman
serisi (dikey sisme imzasi), IoU. Once Y1_A1_taban_500k (T1'in ana hedefi),
sonra A2-A6 (yalniz yama-ici kareler, Y1'deki `yama_ici_mi` ile ayni kural).

Kosum: python3 -m gazebo.tani_a11_2_t1
Cikti: cikti/a11_2_t1.json
"""
import json
import os
import sys
from contextlib import contextmanager

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from calistir import iou                                    # noqa: E402
from gazebo.a11_ortak import kareleri_topla                  # noqa: E402
from gazebo.y1_ortak import yama_ici_mi                      # noqa: E402
from takip import cekirdekler as CK                           # noqa: E402
from takip import tespit as TESPIT                            # noqa: E402
from takip.izleyici import KILITLI, HedefTakip                # noqa: E402

YANLIS_IOU = 0.2
SENARYO_DCF = "Y1_A1_taban_500k"
SENARYOLAR_EK = ["Y1_A2_kucul", "Y1_A3_yaw", "Y1_A4_irtifa",
                 "Y1_A5_kucul_yaw", "Y1_A6_celdirici"]


# --------------------------------------------------------------------------
# T1a - boyut TAMAMEN donuk
# --------------------------------------------------------------------------
class TakipT1a(HedefTakip):
    def kilitle(self, bgr, kutu):
        r = super().kilitle(bgr, kutu)
        self._donuk = self.boyut.copy()
        return r

    def guncelle(self, bgr, gt=None):
        if hasattr(self, "_donuk"):
            self.boyut = self._donuk.copy()
            self.boyut_olculen = self._donuk.copy()
        s = super().guncelle(bgr, gt)
        if hasattr(self, "_donuk"):
            self.boyut = self._donuk.copy()
            self.boyut_olculen = self._donuk.copy()
            s["kutu"] = self.kutu
        return s


# --------------------------------------------------------------------------
# T1b - rafine_kutu devre disi (baglam yoneticisi, takip/tespit.py'yi
# KALICI degistirmez - `izleyici` ve `tespit` modullerindeki referanslari
# GECICI olarak stub'lar).
# --------------------------------------------------------------------------
@contextmanager
def rafine_kutu_kapali():
    import takip.izleyici as IZ
    orij_iz, orij_tespit = IZ.rafine_kutu, TESPIT.rafine_kutu
    stub = lambda *a, **k: None
    IZ.rafine_kutu = stub
    TESPIT.rafine_kutu = stub
    try:
        yield
    finally:
        IZ.rafine_kutu = orij_iz
        TESPIT.rafine_kutu = orij_tespit


# --------------------------------------------------------------------------
# T1c - TESHIS: ikinci tepe olcumu (davranisi DEGISTIRMEZ, sadece kaydeder)
# --------------------------------------------------------------------------
_ikinci_tepe_kayit = []


def _tepe_sarmali(r, N, merkez, w, h):
    iy, ix = np.unravel_index(np.argmax(r), r.shape)
    tepe = r[iy, ix]
    m_yan = np.ones_like(r, bool)
    m_yan[max(0, iy - 5):iy + 6, max(0, ix - 5):ix + 6] = False
    yan = r[m_yan]
    yan_ort, yan_std = float(yan.mean()), float(yan.std() + 1e-5)

    # "hedef-disi" = birincil tepenin YAKIN cevresi (N//6 yaricap) HARIC her yer
    yr = max(2, N // 6)
    m_disi = np.ones_like(r, bool)
    m_disi[max(0, iy - yr):iy + yr + 1, max(0, ix - yr):ix + yr + 1] = False
    if m_disi.any():
        ikinci = float(r[m_disi].max())
    else:
        ikinci = float(yan_ort)
    oran = (ikinci - yan_ort) / max(1e-6, (float(tepe) - yan_ort))
    _ikinci_tepe_kayit.append(round(float(np.clip(oran, -5, 5)), 4))
    return CK._tepe_orijinal(r, N, merkez, w, h)


@contextmanager
def ikinci_tepe_olcumu():
    CK._tepe_orijinal = CK._tepe
    CK._tepe = _tepe_sarmali
    _ikinci_tepe_kayit.clear()
    try:
        yield _ikinci_tepe_kayit
    finally:
        CK._tepe = CK._tepe_orijinal
        del CK._tepe_orijinal


# --------------------------------------------------------------------------
def kol_kos(kareler, kol):
    """kol in {'H0','T1a','T1b','T1c'} - kapali cevrim, hakem=None."""
    if kol == "T1a":
        tak = TakipT1a(hakem=None)
    else:
        tak = HedefTakip(hakem=None)

    baglam = rafine_kutu_kapali() if kol == "T1b" else _bos_baglam()
    olcum_baglam = ikinci_tepe_olcumu() if kol == "T1c" else _bos_baglam()

    with baglam, olcum_baglam as ikinci_tepe:
        img0, gt0, _ = kareler[0]
        tak.kilitle(img0, gt0.copy())
        seri = []
        for t in range(1, len(kareler)):
            img, gt, satir = kareler[t]
            s = tak.guncelle(img, None)
            o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
            kutu = s["kutu"]
            eb = None
            if kutu is not None and kutu[2] > 1e-6:
                eb = float(kutu[3] / kutu[2])          # h/w - dikey sisme imzasi
            kayit = {"t": t, "iou": round(o, 4), "durum": s["durum"], "eb": eb}
            if kol == "T1c" and ikinci_tepe:
                kayit["ikinci_tepe_orani"] = ikinci_tepe[-1]
            seri.append(kayit)

    ilk_kopus = next((x["t"] for x in seri
                      if x["durum"] == KILITLI and x["iou"] < YANLIS_IOU), None)
    kilitli = [x for x in seri if x["durum"] == KILITLI]
    yanlis = [x for x in kilitli if x["iou"] < YANLIS_IOU]
    ebler = [x["eb"] for x in seri if x["eb"] is not None]
    ozet = {
        "ilk_yanlis_kilit": ilk_kopus,
        "kilitli_toplam": len(kilitli),
        "yanlis_kilit_orani": round(len(yanlis) / max(1, len(kilitli)), 4),
        "iou_p50": round(float(np.percentile([x["iou"] for x in seri], 50)), 4),
        "eb_p50": round(float(np.percentile(ebler, 50)), 3) if ebler else None,
        "eb_maks": round(float(np.max(ebler)), 3) if ebler else None,
        "kare_sayisi": len(seri),
    }
    if kol == "T1c":
        ozet["ikinci_tepe_orani_p50"] = (round(float(np.percentile(ikinci_tepe, 50)), 4)
                                         if ikinci_tepe else None)
        ozet["ikinci_tepe_orani_p90"] = (round(float(np.percentile(ikinci_tepe, 90)), 4)
                                         if ikinci_tepe else None)
        # kopustan ONCEKI ve SONRAKI karsilastirma - "gormus mu" sorusu
        if ilk_kopus:
            once = [x["ikinci_tepe_orani"] for x in seri if x["t"] < ilk_kopus]
            sonra = [x["ikinci_tepe_orani"] for x in seri if x["t"] >= ilk_kopus]
            ozet["ikinci_tepe_kopus_oncesi_p50"] = (
                round(float(np.percentile(once, 50)), 4) if once else None)
            ozet["ikinci_tepe_kopus_sonrasi_p50"] = (
                round(float(np.percentile(sonra, 50)), 4) if sonra else None)
    return ozet, seri


class _bos_baglam:
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False


# --------------------------------------------------------------------------
def main():
    sonuc = {"ana_senaryo": SENARYO_DCF, "kollar": {}, "ek_senaryolar": {}}

    print(f"=== T1 ana kosum: {SENARYO_DCF} (kapali cevrim, dort kol) ===")
    kareler, W, H, fx, fy, cx, cy = kareleri_topla(SENARYO_DCF)
    for kol in ["H0", "T1a", "T1b", "T1c"]:
        ozet, seri = kol_kos(kareler, kol)
        sonuc["kollar"][kol] = ozet
        print(f"  {kol}: ilk_yanlis_kilit={ozet['ilk_yanlis_kilit']} "
             f"yanlis_kilit_orani={ozet['yanlis_kilit_orani']} "
             f"iou_p50={ozet['iou_p50']} eb_p50={ozet['eb_p50']} eb_maks={ozet['eb_maks']}")
        if kol == "T1c":
            print(f"    ikinci_tepe_orani p50={ozet['ikinci_tepe_orani_p50']} "
                 f"p90={ozet['ikinci_tepe_orani_p90']} "
                 f"kopus_oncesi={ozet.get('ikinci_tepe_kopus_oncesi_p50')} "
                 f"kopus_sonrasi={ozet.get('ikinci_tepe_kopus_sonrasi_p50')}")
        if kol == "H0":
            sonuc["H0_iou_serisi_ilk40"] = [x["iou"] for x in seri[:40]]
            sonuc["H0_eb_serisi_ilk40"] = [x["eb"] for x in seri[:40]]

    print(f"\n=== T1 ek dogrulama: A2-A6 (yalniz yama-ici) ===")
    for ad in SENARYOLAR_EK:
        # yama-ici filtre (Y1'deki AYNI kural)
        kareler_ek2, W2, H2, fx2, fy2, cx2, cy2 = kareleri_topla(ad)
        ici = []
        for i, (img, gt, satir) in enumerate(kareler_ek2):
            if gt is not None and yama_ici_mi(satir["kam_x"], satir["kam_y"],
                                              satir["kam_z"], W2, H2, fx2):
                ici.append((img, gt, satir))
        if len(ici) < 10:
            print(f"  {ad}: yama-ici orneklem cok kucuk (n={len(ici)}), atlandi")
            continue
        sonuc["ek_senaryolar"][ad] = {"n_yama_ici": len(ici), "kollar": {}}
        for kol in ["H0", "T1a", "T1b"]:
            ozet, _ = kol_kos(ici, kol)
            sonuc["ek_senaryolar"][ad]["kollar"][kol] = ozet
        print(f"  {ad} (n={len(ici)}): "
             f"H0 yk_orani={sonuc['ek_senaryolar'][ad]['kollar']['H0']['yanlis_kilit_orani']} "
             f"T1a yk_orani={sonuc['ek_senaryolar'][ad]['kollar']['T1a']['yanlis_kilit_orani']} "
             f"T1b yk_orani={sonuc['ek_senaryolar'][ad]['kollar']['T1b']['yanlis_kilit_orani']}")

    os.makedirs("cikti", exist_ok=True)
    with open("cikti/a11_2_t1.json", "w") as f:
        json.dump(sonuc, f, indent=2, ensure_ascii=False)
    print("\nyazildi: cikti/a11_2_t1.json")
    return sonuc


if __name__ == "__main__":
    main()
