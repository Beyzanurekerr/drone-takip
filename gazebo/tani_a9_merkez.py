"""A9 Asama 1 - TAKIPCI MERKEZ GUVENI TESHISI (SALT OKUNUR).

AMAC
----
Yeni mekanizma EKLEMEDEN once, merkez kaymasinin HANGI ASAMADA uretildigini
olcmek. A8 merkezin baskin ariza kanali oldugunu gosterdi ama kanalin ICINDE
nerede bozuldugunu soylemedi.

MERKEZE YAZAN UC YOL (izleyici.py'de okundu)
-------------------------------------------
1. `kf.tahmin(M)`            <- guncelle(), ego-motion
2. `kf.duzelt(yeni[, 6.0])`  <- _takip_adimi(), DCF tepesi
   veya `kf.sondur()`        <- olcum reddedildi
3. `kf.duzelt(yeni_c, 1.0)`  <- _boyut_tazele(), rafine kutu merkezi (TAM AGIRLIK)
4. `kf.ata(z)`               <- _arama_adimi(), yeniden yakalama

(3) ONEMLI: istem "once merkez sonra boyut" siralamasi ongoruyordu, ama boyut
yolu merkeze TAM AGIRLIKLA yaziyor (izleyici.py:566-567) ve kapisi `self.boyut`a
bakiyor - yani kendi bozdugu buyukluge. Iki asama AYRILABILIR DEGILDIR.

SINANAN HIPOTEZ (H1)
--------------------
_takip_adimi'nin sicrama kapisi da `self.boyut`a bakiyor:
    maks_sicrama = max(6.0, 0.9 * boyut.max())          (izleyici.py:309)
A8'de olculdu: 117/23'te boyut tahmini 106-131 px'e sisiyor (gercek 12-80).
Sisen boyut -> KAPI GENISLIYOR -> DCF'nin yanlis tepeleri KABUL EDILIYOR ->
merkez uçuyor. Eger dogruysa merkez arizasi boyut arizasinin SONUCUDUR ve
istemin oncelik siralamasi TERSINE cevrilmelidir.

ENSTRUMANTASYON - takip/ DEGISMEZ
---------------------------------
Takipcinin `kf` nesnesi, kilitlemeden SONRA kayit yapan bir sarmalayiciyla
degistirilir. Merkeze yazan her yol Kalman uzerinden gectigi icin, cagiran
fonksiyonun adi yigindan okunarak her merkez degisimi kaynagina atfedilir.
`takip/*.py` dosyalarina DOKUNULMAZ (md5 raporda dogrulanir).

ATFETME OLCUTU
--------------
Her Kalman olayi icin:
    katki = |konum_sonra - GT| - |konum_once - GT|
Kaynak basina toplanir. Pozitif = o asama merkezi GT'den UZAKLASTIRDI.

YATAK
-----
A8'in sensor yatagi (A7.sensor_dizi, 1280x720). YOLO KOSMAZ - bu bir takipci
teshisidir, tespit olcumu degildir.

EGO KANALI UYARISI: bu yatakta arkaplan penceresi SABITTIR (A5.2 tasarimi),
yani ego M birim matrise yakindir. Ego katkisi burada OLCULEMEZ. Bu iddia
edilmiyor, OLCULUP KANITLANIYOR (`ego_oteleme_p95` alani).
"""
import importlib.util as iu
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def _yukle(ad, dosya):
    sp = iu.spec_from_file_location(ad, os.path.join(HERE, dosya))
    m = iu.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


A7 = _yukle("A7", "tani_a7_roi.py")
B = A7.B

from calistir import iou                                   # noqa: E402
from takip.izleyici import KILITLI, HedefTakip             # noqa: E402

SENSOR = A7.SENSOR
N_KARE = A7.N_KARE
SEVIYELER = [40, 30, 20, 15, 10, 8, 5]
SEVIYE_AD = {40: "40x15", 30: "30x12", 20: "20x10", 15: "15x7",
             10: "10x5", 8: "8x5", 5: "5x5"}
KOPUS_KAT = 0.5      # |hata| > KOPUS_KAT * GT_L  ->  kopuk sayilir
KOPUS_SABIR = 5      # kac ardisik kare


def p(v, q):
    return round(float(np.percentile(v, q)), 2) if len(v) else None


def ort(v, k=3):
    return round(float(np.mean(v)), k) if len(v) else None


# ------------------------------------------------------- kayit yapan Kalman
class KayitKalman:
    """Kalman'i saran, her merkez degisimini kaynagina atfeden gozlemci.

    Sadece kaydeder; hicbir degeri degistirmez. Bilinmeyen her oznitelik
    gercek Kalman'a devredilir (izleyici `kf.x[0] = ...` gibi yerinde
    degisiklikler yapiyor, bunlar aynen calisir).
    """
    _OZEL = ("_kf", "_log", "_gt", "_tak")

    def __init__(self, kf, log):
        object.__setattr__(self, "_kf", kf)
        object.__setattr__(self, "_log", log)
        object.__setattr__(self, "_gt", None)
        object.__setattr__(self, "_tak", None)

    def __getattr__(self, ad):
        return getattr(object.__getattribute__(self, "_kf"), ad)

    def __setattr__(self, ad, deger):
        if ad in KayitKalman._OZEL:
            object.__setattr__(self, ad, deger)
        else:
            setattr(object.__getattribute__(self, "_kf"), ad, deger)

    def _kaydet(self, tip, once, z=None, r_carpan=None):
        kf = object.__getattribute__(self, "_kf")
        log = object.__getattribute__(self, "_log")
        gt = object.__getattribute__(self, "_gt")
        tak = object.__getattribute__(self, "_tak")
        sonra = kf.konum
        kaynak = sys._getframe(2).f_code.co_name        # izleyici'deki cagiran
        e_once = float(np.linalg.norm(once - gt)) if gt is not None else None
        e_sonra = float(np.linalg.norm(sonra - gt)) if gt is not None else None
        kayit = {"tip": tip, "kaynak": kaynak,
                 "konum_once": [round(float(v), 2) for v in once],
                 "konum_sonra": [round(float(v), 2) for v in sonra],
                 "adim_px": round(float(np.linalg.norm(sonra - once)), 2),
                 "hata_once": round(e_once, 2) if e_once is not None else None,
                 "hata_sonra": round(e_sonra, 2) if e_sonra is not None else None,
                 "katki": round(e_sonra - e_once, 3) if e_once is not None else None,
                 "P_konum_iz": round(float(kf.P[0, 0] + kf.P[1, 1]), 3)}
        if z is not None:
            kayit["z"] = [round(float(v), 2) for v in np.asarray(z, np.float64)]
            kayit["sicrama_px"] = round(float(np.linalg.norm(np.asarray(z) - once)), 2)
            kayit["r_carpan"] = r_carpan
            if tak is not None and tak.boyut is not None:
                # izleyici.py:309 ile AYNI formul
                kayit["maks_sicrama_px"] = round(
                    max(6.0, 0.9 * float(np.max(tak.boyut))), 2)
                kayit["boyut_max"] = round(float(np.max(tak.boyut)), 2)
        log.append(kayit)

    def tahmin(self, M):
        kf = object.__getattribute__(self, "_kf")
        once = kf.konum
        hiz_once = float(np.linalg.norm(kf.x[2:]))
        # ego'nun SAF katkisi: konumu yalnizca M ile tasi (hiz adimi haric)
        saf_ego = (M[:, :2] @ once + M[:, 2]) - once
        kf.tahmin(M)
        self._kaydet("tahmin", once)
        object.__getattribute__(self, "_log")[-1].update({
            "ego_oteleme_px": round(float(np.linalg.norm(saf_ego)), 3),
            "ego_t_norm": round(float(np.linalg.norm(M[:, 2])), 3),
            "ego_A_sapma": round(float(np.linalg.norm(M[:, :2] - np.eye(2))), 5),
            "hiz_px_kare": round(hiz_once, 2)})

    def duzelt(self, z, r_carpan=1.0):
        kf = object.__getattribute__(self, "_kf")
        once = kf.konum
        kf.duzelt(z, r_carpan)
        self._kaydet("duzelt", once, z=z, r_carpan=r_carpan)

    def ata(self, z):
        kf = object.__getattribute__(self, "_kf")
        once = kf.konum
        kf.ata(z)
        self._kaydet("ata", once, z=z)

    def sondur(self, kat=0.97):
        kf = object.__getattribute__(self, "_kf")
        once = kf.konum
        kf.sondur(kat)
        self._kaydet("sondur", once)


# --------------------------------------------------------------- olcum
def merkez_teshisi(dizi, kayit_karesi=False):
    """Takipciyi dizi boyunca kosar, her merkez degisimini kaynagina atfeder."""
    log = []
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    sarmal = KayitKalman(tak.kf, log)
    object.__setattr__(sarmal, "_tak", tak)
    tak.kf = sarmal

    kaynak_katki = {}
    kaynak_sayi = {}
    hata_l, psr_l, P_l, ego_ot_l, ego_olc_l = [], [], [], [], []
    hiz_l, egoA_l = [], []
    kapi_kabul = kapi_red = 0
    kapi_gevsek = 0          # maks_sicrama > 2x gercek hedef boyu
    kareler = []
    kopus_kare, kopus_ard, kopus_tetik = None, 0, None

    for t in range(1, len(dizi)):
        img, gt = dizi[t]
        gc = gt[:2] + gt[2:] / 2.0
        gL = float(max(gt[2], gt[3]))
        object.__setattr__(sarmal, "_gt", gc.astype(np.float64))
        n0 = len(log)
        onceki_hata = float(np.linalg.norm(tak.kf.konum - gc))

        s = tak.guncelle(img)

        olaylar = log[n0:]
        hata = float(np.linalg.norm(tak.kf.konum - gc))
        hata_l.append(hata)
        psr_l.append(float(s["psr"]))
        P_l.append(float(tak.kf.P[0, 0] + tak.kf.P[1, 1]))

        for o in olaylar:
            k = f"{o['kaynak']}:{o['tip']}"
            if o["katki"] is not None:
                kaynak_katki[k] = kaynak_katki.get(k, 0.0) + o["katki"]
            kaynak_sayi[k] = kaynak_sayi.get(k, 0) + 1
            if o["kaynak"] == "_takip_adimi":
                if o["tip"] == "duzelt":
                    kapi_kabul += 1
                    ms = o.get("maks_sicrama_px")
                    if ms is not None and ms > 2.0 * gL:
                        kapi_gevsek += 1
                elif o["tip"] == "sondur":
                    kapi_red += 1

        # ego kanalinin ATIL oldugunu KANITLA (iddia etme)
        tah = [o for o in olaylar if o["tip"] == "tahmin"]
        if tah:
            ego_ot_l.append(tah[0]["ego_oteleme_px"])
            hiz_l.append(tah[0]["hiz_px_kare"])
            egoA_l.append(tah[0]["ego_A_sapma"])
        ego_olc_l.append(float(s["olcek"]))

        # kopus: hata GT'nin yariboyunu asiyor ve KOPUS_SABIR kare suruyor
        if hata > KOPUS_KAT * gL:
            kopus_ard += 1
            if kopus_ard >= KOPUS_SABIR and kopus_kare is None:
                kopus_kare = t - KOPUS_SABIR + 1
        else:
            kopus_ard = 0

        if kayit_karesi:
            kareler.append({
                "t": t, "gt_L": round(gL, 2),
                "gt_merkez": [round(float(v), 2) for v in gc],
                "kf_merkez": [round(float(v), 2) for v in tak.kf.konum],
                "hata_px": round(hata, 2), "hata_artis": round(hata - onceki_hata, 2),
                "psr": round(float(s["psr"]), 2), "durum": str(s["durum"]),
                "boyut_max": round(float(np.max(tak.boyut)), 2),
                "boyut_hata_orani": round(float(np.max(tak.boyut)) / gL, 3),
                "P_konum_iz": round(float(tak.kf.P[0, 0] + tak.kf.P[1, 1]), 3),
                "ego_olcek": round(float(s["olcek"]), 4),
                "benzerlik": round(float(s["benzerlik"]), 3),
                "yanlis_kilit": int(s["yanlis_kilit"]),
                "olaylar": olaylar})

    # kopus tetigi: kopus karesindeki olaylarin en buyuk pozitif katkisi
    if kopus_kare is not None and kayit_karesi:
        for kr in kareler:
            if kr["t"] == kopus_kare:
                ad = [o for o in kr["olaylar"] if o["katki"] is not None]
                if ad:
                    en = max(ad, key=lambda o: o["katki"])
                    kopus_tetik = {"kare": kopus_kare,
                                   "kaynak": f"{en['kaynak']}:{en['tip']}",
                                   "katki_px": en["katki"],
                                   "sicrama_px": en.get("sicrama_px"),
                                   "maks_sicrama_px": en.get("maks_sicrama_px"),
                                   "boyut_max": en.get("boyut_max"),
                                   "psr": kr["psr"], "gt_L": kr["gt_L"]}
                break

    d = {"kare": len(hata_l),
         "merkez_hata_p50": p(hata_l, 50), "merkez_hata_p95": p(hata_l, 95),
         "merkez_hata_ort": ort(hata_l, 2), "merkez_hata_son": round(hata_l[-1], 2),
         "psr_p50": p(psr_l, 50), "psr_p05": p(psr_l, 5),
         "P_konum_iz_p50": p(P_l, 50), "P_konum_iz_p95": p(P_l, 95),
         "ego_oteleme_p95": p(ego_ot_l, 95), "ego_oteleme_p50": p(ego_ot_l, 50),
         "ego_A_sapma_p95": p(egoA_l, 95), "ego_olcek_p50": p(ego_olc_l, 50),
         "kf_hiz_p50": p(hiz_l, 50), "kf_hiz_p95": p(hiz_l, 95),
         "dcf_kapi_kabul": kapi_kabul, "dcf_kapi_red": kapi_red,
         "dcf_kapi_gevsek": kapi_gevsek,
         "kaynak_katki_px": {k: round(v, 2) for k, v in
                             sorted(kaynak_katki.items(), key=lambda z: -abs(z[1]))},
         "kaynak_sayi": kaynak_sayi,
         "kopus_karesi": kopus_kare, "kopus_tetigi": kopus_tetik}
    if kayit_karesi:
        d["kareler"] = kareler
    return d


# ------------------------------------------------------------------------ main
def main():
    cikti = {
        "asama": "A9 Asama 1 - takipci merkez guveni teshisi (SALT OKUNUR)",
        "kapsam": ("Merkez kaymasinin hangi asamada uretildigini olcer. "
                   "Yeni mekanizma EKLENMEDI, esik DEGISTIRILMEDI, "
                   "takip/ DEGISMEDI. YOLO kosmaz."),
        "acik_cevrim_uyarisi": "Tum olcumler ACIK CEVRIMDIR; dedektor yok.",
        "merkeze_yazan_yollar": {
            "guncelle:tahmin": "ego-motion (izleyici.py:263)",
            "_takip_adimi:duzelt": "DCF tepesi (izleyici.py:312 / 327)",
            "_takip_adimi:sondur": "olcum reddedildi, hiz sonduruldu (izleyici.py:332)",
            "_boyut_tazele:duzelt": "rafine kutu merkezi, TAM AGIRLIK (izleyici.py:567)",
            "_arama_adimi:ata": "yeniden yakalama (izleyici.py:525)"},
        "hipotez_H1": ("sicrama kapisi maks_sicrama = max(6.0, 0.9*boyut.max()) "
                       "(izleyici.py:309) bozuk boyuta bakiyor; boyut sisince kapi "
                       "genisliyor ve yanlis DCF tepeleri kabul ediliyor."),
        "kopus_tanimi": f"|hata| > {KOPUS_KAT}*GT_L, {KOPUS_SABIR} ardisik kare",
        "yatak": {"sensor": list(SENSOR), "kare": N_KARE,
                  "not": "A5.2 kompoziti: arkaplan penceresi SABIT -> ego atil; "
                         "ego_oteleme_p95 ile kanitlanir"},
        "diziler": {},
    }
    for dizi_ad, tid, rol in B.DIZILER:
        kareler = B.kareleri_topla(dizi_ad, tid, N_KARE)
        W, H = kareler[0][3], kareler[0][4]
        ad = f"{dizi_ad}/{tid}"
        if W < SENSOR[0] or H < SENSOR[1]:
            cikti["diziler"][ad] = {"rol": rol, "atlandi": "kare sensor tuvalinden kucuk"}
            continue
        hucre, _u = B.arkaplan_hucresi(kareler, W, H, *SENSOR)
        dd = {"rol": rol, "kare_boyutu": [W, H], "seviyeler": {}}
        print(f"\n--- {ad} ({rol}) ---", flush=True)
        for L in SEVIYELER:
            d, s = A7.sensor_dizi(kareler, hucre, L, N_KARE)
            if len(d) < 10:
                dd["seviyeler"][SEVIYE_AD[L]] = {"not": "dizi 10 kareden kisa"}
                continue
            r = merkez_teshisi(d, kayit_karesi=True)
            r["seviye_L"] = L
            r["gt_L_sensor"] = round(float(np.mean([max(g[2], g[3]) for _i, g in d])), 1)
            dd["seviyeler"][SEVIYE_AD[L]] = r
            kk = r["kaynak_katki_px"]
            bas = list(kk.items())[:2]
            print(f"  {SEVIYE_AD[L]:6s} hata p50={r['merkez_hata_p50']:>7.2f} "
                  f"p95={r['merkez_hata_p95']:>8.2f} | PSR p50={r['psr_p50']:>6.2f} "
                  f"P_iz p95={r['P_konum_iz_p95']:>8.2f} | kapi kabul/red/gevsek="
                  f"{r['dcf_kapi_kabul']:>3}/{r['dcf_kapi_red']:>3}/{r['dcf_kapi_gevsek']:>3}"
                  f" | SAF ego p95={r['ego_oteleme_p95']} hiz p95={r['kf_hiz_p95']}"
                  f" | kopus={r['kopus_karesi']}"
                  f" | en buyuk katki: {bas}", flush=True)
        cikti["diziler"][ad] = dd

    os.makedirs("cikti", exist_ok=True)
    yol = sys.argv[1] if len(sys.argv) > 1 else "cikti/a9_takipci_merkez_recovery.json"
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
