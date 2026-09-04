"""A11.3/T2 - renk_dcf duzeltme A/B'si. T1'in bulgusu uzerine uc BAGIMSIZ
onlem (+ hepsi gecerse birlesimi), tek degiskenli, `takip/*.py` DEGISMEDI
(tumu monkeypatch/instance-attribute - md5 sabit kalir, calisma bitince
orijinal fonksiyonlar geri yuklenir).

T2a - SABLON GUNCELLEME KAPISI: T1c'nin ikinci-tepe orani, ONCEDEN
     (bu script T2a'yi kosmadan) H0'in SAGLIKLI karelerinden (durum==KILITLI
     ve IoU>=0.5, "dogru hedef" tanimi A9_KABUL_OLCUTU.md EK-1) toplanan
     dagilimin P95'i esik olarak KAYDEDILIR. Esik asilirsa o karede
     `cekirdek.ogren()` ATLANIR (sablon o kare OGRENMEZ).
T2b - UZAMSAL/RENK GUVENILIRLIK MASKESI (CSR-DCF ilkesi, ogrenme YOK - maske
     her karede TAZE hesaplanir, biriktirilmez): guncelleme yamasinin HER
     PIKSELI, mevcut `imza.renk` referansina (zaten var olan, izleyici'nin
     KENDI durumu) renk uzakligina gore agirliklandirilir. Uzaklik->agirlik
     donusumu `Imza.benzerlik`'teki AYNI tau=45.0 sabitini kullanir (yeni
     sayi YOK). Yalnizca `ogren()` (guncelleme) maskelenir; `ara()` (arama)
     DOKUNULMAZ.
T2c - RAFINE_KUTU BAGIMSIZ-BILESEN KAPISI (T1'in onerisi AYNEN): rafine_kutu
     sonucunun en-boy orani (h/w), MEVCUT boyutun en-boy oranindan
     `_boyut_sinirla`'nin ZATEN VAR OLAN [0.60, 1.70] bandinin disina
     cikiyorsa SONUC REDDEDILIR (None dondurulur) - orantisiz (dikey sisme
     gibi) olcumler elenir, orantili (gercek kucculme/buyume) SERBEST kalir.
T2d - a+b+c BIRLESIMI - YALNIZCA ucu de TEK BASINA K6'yi gectiyse kosulur.

OLCUM: A1 birincil (Y1_A1_taban_500k), A2-A6 regresyon (yama-ici, Y1'deki
AYNI filtre). K6-UYARLANMIS kriter (A9_KABUL_OLCUTU.md K1/K6, VisDrone
"dizi" kavramini Gazebo "senaryo"suna tasir - ayrinti asagida).

Kosum: python3 -m gazebo.tani_a11_3_t2
Cikti: cikti/a11_3_t2.json
"""
import json
import os
import sys
from contextlib import contextmanager

import cv2
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

YANLIS_IOU, DOGRU_IOU = 0.2, 0.5
SENARYO_A1 = "Y1_A1_taban_500k"
SENARYOLAR_EK = ["Y1_A2_kucul", "Y1_A3_yaw", "Y1_A4_irtifa",
                 "Y1_A5_kucul_yaw", "Y1_A6_celdirici"]
# _boyut_sinirla'nin ZATEN VAR OLAN bandi (izleyici.py:557) - T2c bunu
# YENIDEN KULLANIR, yeni sayi uydurmaz.
BOYUT_BAND_ALT, BOYUT_BAND_UST = 0.60, 1.70
# Imza.benzerlik'teki (tespit.py:174) AYNI renk-uzaklik olcegi - T2b bunu
# YENIDEN KULLANIR.
RENK_TAU = 45.0


# --------------------------------------------------------------------------
# ikinci-tepe olcumu (T1c ile AYNI mekanizma) - hem teshis hem T2a'nin
# esik-kapisi bunun uzerine kurulur.
# --------------------------------------------------------------------------
_son_ikinci_tepe = [None]
_ikinci_tepe_kayit = []


def _tepe_sarmali(r, N, merkez, w, h):
    iy, ix = np.unravel_index(np.argmax(r), r.shape)
    tepe = r[iy, ix]
    m_yan = np.ones_like(r, bool)
    m_yan[max(0, iy - 5):iy + 6, max(0, ix - 5):ix + 6] = False
    yan = r[m_yan]
    yan_ort = float(yan.mean())
    yr = max(2, N // 6)
    m_disi = np.ones_like(r, bool)
    m_disi[max(0, iy - yr):iy + yr + 1, max(0, ix - yr):ix + yr + 1] = False
    ikinci = float(r[m_disi].max()) if m_disi.any() else yan_ort
    oran = (ikinci - yan_ort) / max(1e-6, (float(tepe) - yan_ort))
    oran = float(np.clip(oran, -5, 5))
    _son_ikinci_tepe[0] = oran
    _ikinci_tepe_kayit.append(oran)
    return CK._tepe_orijinal(r, N, merkez, w, h)


@contextmanager
def ikinci_tepe_izleme():
    CK._tepe_orijinal = CK._tepe
    CK._tepe = _tepe_sarmali
    _ikinci_tepe_kayit.clear()
    _son_ikinci_tepe[0] = None
    try:
        yield _ikinci_tepe_kayit
    finally:
        CK._tepe = CK._tepe_orijinal
        del CK._tepe_orijinal


# --------------------------------------------------------------------------
# T2a - sablon guncelleme kapisi
# --------------------------------------------------------------------------
def _ogren_kapili_fabrika(esik):
    _orij = CK.RenkDcfCekirdek.ogren

    def _ogren_kapili(self, bgr, gri, merkez, boyut, lr=None):
        if _son_ikinci_tepe[0] is not None and _son_ikinci_tepe[0] > esik:
            return          # GUNCELLEME ATLANDI - sablon bu kare ogrenmedi
        return _orij(self, bgr, gri, merkez, boyut, lr)
    return _ogren_kapili, _orij


@contextmanager
def sablon_kapisi(esik):
    fn, orij = _ogren_kapili_fabrika(esik)
    CK.RenkDcfCekirdek.ogren = fn
    try:
        yield
    finally:
        CK.RenkDcfCekirdek.ogren = orij


# --------------------------------------------------------------------------
# T2b - renk guvenilirlik maskesi (CSR-DCF ilkesi, ogrenme yok)
# --------------------------------------------------------------------------
def _ogren_maskeli(self, bgr, gri, merkez, boyut, lr=None):
    lr = self.lr if lr is None else lr
    kan, (w, h) = self._kanallar(bgr, merkez, boyut)
    ref = getattr(self, "_t2b_renk_ref", None)
    if ref is not None:
        ham = self._yama(bgr, merkez, w, h, self.aci)
        ham = cv2.resize(ham, (self.N, self.N), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        d = np.linalg.norm(ham - np.asarray(ref, np.float32)[None, None, :], axis=2)
        maske = np.exp(-d / RENK_TAU).astype(np.float32)
        kan = kan * maske[None]
    F = np.fft.fft2(kan, axes=(1, 2))
    self.A = (1 - lr) * self.A + lr * (self.G[None] * np.conj(F))
    self.B = (1 - lr) * self.B + lr * (F * np.conj(F)).sum(0)


@contextmanager
def renk_maskesi():
    orij = CK.RenkDcfCekirdek.ogren
    CK.RenkDcfCekirdek.ogren = _ogren_maskeli
    try:
        yield
    finally:
        CK.RenkDcfCekirdek.ogren = orij


# --------------------------------------------------------------------------
# T2c - rafine_kutu bagimsiz-bilesen (en-boy) kapisi
# --------------------------------------------------------------------------
@contextmanager
def rafine_oran_kapisi():
    import takip.izleyici as IZ
    orij_iz, orij_tespit = IZ.rafine_kutu, TESPIT.rafine_kutu

    def _sarmali(bgr, merkez, boyut, *a, **kw):
        r = orij_tespit(bgr, merkez, boyut, *a, **kw)
        if r is None:
            return None
        mevcut_oran = float(boyut[1]) / max(1e-6, float(boyut[0]))
        yeni_oran = float(r[3]) / max(1e-6, float(r[2]))
        if not (BOYUT_BAND_ALT * mevcut_oran <= yeni_oran <= BOYUT_BAND_UST * mevcut_oran):
            return None      # ORANTISIZ - reddedildi (T1 bulgusu: dikey sisme buradan giriyor)
        return r
    IZ.rafine_kutu = _sarmali
    TESPIT.rafine_kutu = _sarmali
    try:
        yield
    finally:
        IZ.rafine_kutu = orij_iz
        TESPIT.rafine_kutu = orij_tespit


# --------------------------------------------------------------------------
# T2d - uc onlemin birlesimi
# --------------------------------------------------------------------------
def _ogren_birlesim_fabrika(esik):
    def _ogren_birlesim(self, bgr, gri, merkez, boyut, lr=None):
        if _son_ikinci_tepe[0] is not None and _son_ikinci_tepe[0] > esik:
            return
        return _ogren_maskeli(self, bgr, gri, merkez, boyut, lr)
    return _ogren_birlesim


@contextmanager
def birlesim(esik):
    orij = CK.RenkDcfCekirdek.ogren
    CK.RenkDcfCekirdek.ogren = _ogren_birlesim_fabrika(esik)
    with rafine_oran_kapisi():
        try:
            yield
        finally:
            CK.RenkDcfCekirdek.ogren = orij


class _bos:
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False


# --------------------------------------------------------------------------
def kol_kos(kareler, kol, esik=None):
    """kol in {'H0','T2a','T2b','T2c','T2d'}."""
    tak = HedefTakip(hakem=None)
    tak.cekirdek._t2b_renk_ref = None  # T2b/T2d ogren() bunu okur

    if kol == "T2a":
        baglam = sablon_kapisi(esik)
    elif kol == "T2b":
        baglam = renk_maskesi()
    elif kol == "T2c":
        baglam = rafine_oran_kapisi()
    elif kol == "T2d":
        baglam = birlesim(esik)
    else:
        baglam = _bos()

    with ikinci_tepe_izleme() as ikinci_tepe, baglam:
        img0, gt0, _ = kareler[0]
        tak.kilitle(img0, gt0.copy())
        seri = []
        for t in range(1, len(kareler)):
            img, gt, satir = kareler[t]
            # T2b/T2d: guncel renk referansi HER KAREDE, ogren() cagrilmadan
            # ONCE tazelenir (imza onceki karenin degeriyle - guncelle()
            # icinde ogren() imza.guncelle()'DEN ONCE calisiyor, izleyici.py
            # degismedi, biz sadece disaridan OKUYORUZ).
            tak.cekirdek._t2b_renk_ref = (
                None if tak.imza.renk is None else tak.imza.renk.copy())
            s = tak.guncelle(img, None)
            o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
            kutu = s["kutu"]
            eb = float(kutu[3] / kutu[2]) if (kutu is not None and kutu[2] > 1e-6) else None
            gtc = gt[:2] + gt[2:] / 2.0
            hata = float(np.linalg.norm(tak.kf.konum - gtc))
            seri.append({"t": t, "iou": round(o, 4), "durum": s["durum"],
                        "eb": eb, "psr": round(float(s["psr"]), 3),
                        "merkez_hata": round(hata, 3),
                        "ikinci_tepe": ikinci_tepe[-1] if ikinci_tepe else None})

    ilk_kopus = next((x["t"] for x in seri
                      if x["durum"] == KILITLI and x["iou"] < YANLIS_IOU), None)
    kilitli = [x for x in seri if x["durum"] == KILITLI]
    yanlis = [x for x in kilitli if x["iou"] < YANLIS_IOU]
    ebler = [x["eb"] for x in seri if x["eb"] is not None]
    ozet = {
        "ilk_yanlis_kilit": ilk_kopus,
        "kilitli_toplam": len(kilitli),
        "yanlis_kilit_orani": round(len(yanlis) / max(1, len(kilitli)), 4),
        "yanlis_kilit_sayisi": len(yanlis),
        "iou_ort": round(float(np.mean([x["iou"] for x in seri])), 4),
        "merkez_hata_p95": round(float(np.percentile([x["merkez_hata"] for x in seri], 95)), 3),
        "eb_p50": round(float(np.percentile(ebler, 50)), 3) if ebler else None,
        "eb_maks": round(float(np.max(ebler)), 3) if ebler else None,
        "kare_sayisi": len(seri),
    }
    return ozet, seri


# --------------------------------------------------------------------------
def esik_topla():
    """T2a ONCESI: H0'in SAGLIKLI karelerinden (KILITLI + IoU>=0.5) ikinci-
    tepe dagilimi, TUM senaryolar (A1 500k + A2-A6 yama-ici) havuzlanarak.
    P95 esik olarak KAYDEDILIR - T2a'yi kosmadan ONCE, sonucuna BAKMADAN."""
    havuz = []
    kareler_a1, *_ = kareleri_topla(SENARYO_A1)
    _, seri_a1 = kol_kos(kareler_a1, "H0")
    havuz += [x["ikinci_tepe"] for x in seri_a1
             if x["durum"] == KILITLI and x["iou"] >= DOGRU_IOU and x["ikinci_tepe"] is not None]

    for ad in SENARYOLAR_EK:
        kareler2, W2, H2, fx2, fy2, cx2, cy2 = kareleri_topla(ad)
        ici = [(img, gt, satir) for img, gt, satir in kareler2
              if gt is not None and yama_ici_mi(satir["kam_x"], satir["kam_y"],
                                                satir["kam_z"], W2, H2, fx2)]
        if len(ici) < 10:
            continue
        _, seri = kol_kos(ici, "H0")
        havuz += [x["ikinci_tepe"] for x in seri
                 if x["durum"] == KILITLI and x["iou"] >= DOGRU_IOU and x["ikinci_tepe"] is not None]

    esik = float(np.percentile(havuz, 95)) if havuz else 1.0
    return esik, len(havuz)


# --------------------------------------------------------------------------
def k6_degerlendir(h0_ozet, varyant_ozet):
    """K6-uyarlanmis: IoU_ort 0.03 mutlaktan fazla dusmesin, merkez_hata_p95
    %20'den fazla artmasin, yanlis_kilit_sayisi H0'i ASMASIN (K2 mutlak)."""
    d_iou = varyant_ozet["iou_ort"] - h0_ozet["iou_ort"]
    if h0_ozet["merkez_hata_p95"] > 1e-6:
        d_hata_oran = (varyant_ozet["merkez_hata_p95"] - h0_ozet["merkez_hata_p95"]) / h0_ozet["merkez_hata_p95"]
    else:
        d_hata_oran = 0.0
    d_yk = varyant_ozet["yanlis_kilit_sayisi"] - h0_ozet["yanlis_kilit_sayisi"]
    gecti = (d_iou >= -0.03) and (d_hata_oran <= 0.20) and (d_yk <= 0)
    return {"d_iou_ort": round(d_iou, 4), "d_merkez_hata_p95_oran": round(d_hata_oran, 4),
           "d_yanlis_kilit_sayisi": d_yk, "gecti": bool(gecti)}


def kol_topla(kareler, kol, esik=None):
    ozet, seri = kol_kos(kareler, kol, esik)
    return ozet


def main():
    print("=== T2 esik toplama (T1c'nin SAGLIKLI dagilimindan P95, TUM senaryolar) ===")
    esik, n_havuz = esik_topla()
    print(f"  havuz n={n_havuz}, esik(P95)={esik:.4f}")

    sonuc = {"esik_t2a": round(esik, 4), "esik_havuz_n": n_havuz,
            "boyut_band": [BOYUT_BAND_ALT, BOYUT_BAND_UST], "renk_tau": RENK_TAU,
            "senaryolar": {}}

    print(f"\n=== A1 birincil: {SENARYO_A1} ===")
    kareler_a1, *_ = kareleri_topla(SENARYO_A1)
    kollar_a1 = {}
    for kol in ["H0", "T2a", "T2b", "T2c"]:
        ozet, _ = kol_kos(kareler_a1, kol, esik)
        kollar_a1[kol] = ozet
        print(f"  {kol}: ilk_yanlis_kilit={ozet['ilk_yanlis_kilit']} "
             f"yk_orani={ozet['yanlis_kilit_orani']} iou_ort={ozet['iou_ort']} "
             f"eb_maks={ozet['eb_maks']}")

    # T2d sadece uc kol da K6'yi A1+A2-A6 UZERINDE tek basina gecerse - once
    # bagimsiz K6 sonuclarini asagida A2-A6 ile birlikte topluyoruz, sonra
    # karar veriyoruz.
    sonuc["senaryolar"][SENARYO_A1] = {"kollar": kollar_a1}

    for ad in SENARYOLAR_EK:
        print(f"\n=== ek: {ad} ===")
        kareler2, W2, H2, fx2, fy2, cx2, cy2 = kareleri_topla(ad)
        ici = [(img, gt, satir) for img, gt, satir in kareler2
              if gt is not None and yama_ici_mi(satir["kam_x"], satir["kam_y"],
                                                satir["kam_z"], W2, H2, fx2)]
        if len(ici) < 10:
            print(f"  atlandi (n={len(ici)})")
            continue
        kollar = {}
        for kol in ["H0", "T2a", "T2b", "T2c"]:
            ozet, _ = kol_kos(ici, kol, esik)
            kollar[kol] = ozet
        sonuc["senaryolar"][ad] = {"n": len(ici), "kollar": kollar}
        print(f"  H0 iou_ort={kollar['H0']['iou_ort']} "
             f"T2a={kollar['T2a']['iou_ort']} T2b={kollar['T2b']['iou_ort']} "
             f"T2c={kollar['T2c']['iou_ort']}")

    # K6 degerlendirmesi: her kol icin TUM senaryolarda gecti mi?
    print("\n=== K6 degerlendirmesi (her senaryoda H0'a karsi) ===")
    k6_sonuc = {}
    for kol in ["T2a", "T2b", "T2c"]:
        hepsi_gecti = True
        detay = {}
        for ad, blok in sonuc["senaryolar"].items():
            if kol not in blok["kollar"]:
                continue
            d = k6_degerlendir(blok["kollar"]["H0"], blok["kollar"][kol])
            detay[ad] = d
            hepsi_gecti = hepsi_gecti and d["gecti"]
        k6_sonuc[kol] = {"detay": detay, "K6_gecti_tumunde": hepsi_gecti}
        print(f"  {kol}: K6 {'GECTI (tumunde)' if hepsi_gecti else 'KALDI (en az bir senaryoda)'}")

    sonuc["k6"] = k6_sonuc

    ucu_de_gecti = all(k6_sonuc[k]["K6_gecti_tumunde"] for k in ["T2a", "T2b", "T2c"])
    sonuc["t2d_kosuldu"] = ucu_de_gecti
    if ucu_de_gecti:
        print("\n=== T2a+T2b+T2c ucu de K6'yi gecti - T2d (birlesim) kosuluyor ===")
        kollar_a1["T2d"], _ = kol_kos(kareler_a1, "T2d", esik)
        d_a1 = k6_degerlendir(kollar_a1["H0"], kollar_a1["T2d"])
        print(f"  T2d A1: ilk_yanlis_kilit={kollar_a1['T2d']['ilk_yanlis_kilit']} "
             f"K6={d_a1['gecti']}")
        sonuc["senaryolar"][SENARYO_A1]["kollar"]["T2d"] = kollar_a1["T2d"]
        sonuc["k6"]["T2d_A1"] = d_a1
    else:
        print("\n=== T2d KOSULMADI - ucunden en az biri K6'yi gecmedi ===")

    # A1 hedefi: >=300 kare gecerli kilit (ilk_yanlis_kilit >= 300 ya da None)
    print("\n=== A1 hedefi: ilk yanlis-kilit >= 300 kare ===")
    for kol, ozet in kollar_a1.items():
        ik = ozet["ilk_yanlis_kilit"]
        basardi = (ik is None) or (ik >= 300)
        print(f"  {kol}: ilk_yanlis_kilit={ik} -> {'BASARDI' if basardi else 'basaramadi'}")

    os.makedirs("cikti", exist_ok=True)
    with open("cikti/a11_3_t2.json", "w") as f:
        json.dump(sonuc, f, indent=2, ensure_ascii=False)
    print("\nyazildi: cikti/a11_3_t2.json")
    return sonuc


if __name__ == "__main__":
    main()
