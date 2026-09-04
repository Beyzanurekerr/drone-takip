"""A9 A/B-2 - _boyut_tazele KABUL KAPISININ self.boyut bagimliligi (SALT OKUNUR).

SORU
----
izleyici.py:566:
    if norm(yeni_c - kf.konum) < 0.6 * self.boyut.max():   -> kf.duzelt(yeni_c, 1.0)

Kapi, kendi kararlarinin bozdugu `self.boyut`a bakiyor (4U dersi). Boyut sisince
kapi genisliyor, kuculunce daraliyor. Yanlis olcumleri kabul/dogru olcumleri
reddediyor olabilir mi?

KOLLAR (r_carpan HER KOLDA 1.0 - A/B-1'in 6.0'i KULLANILMIYOR)
--------------------------------------------------------------
kontrol_orig   : gercek _boyut_tazele metodu, hic dokunulmamis
kontrol_repro  : metodun birebir yeniden yazimi, kapi = 0.6*self.boyut.max()
                 >>> ESDEGERLIK TESTI: kontrol_orig ile AYNI olmali, yoksa deney gecersiz
ab2_bagimsiz   : TEK DEGISKEN - kapi = 0.6*max(r[2:])  (rafine'nin TAZE olcumu)
                 Ayni 0.6 sabiti; yeni esik yok. r[2:] kapinin gecmis
                 kararlarindan ETKILENMEZ; self.boyut etkilenir.
oracle_kapi    : TANISAL UST SINIR, BASARI DEGIL - kapi GT'ye bakar:
                 |yeni_c - GT| < |kf.konum - GT| ise kabul.
                 Mukemmel kapi bile duzeltmiyorsa sorun kapida degildir.

KAPI KARAR ETIKETI (GT ile, yalnizca OLCUM icin)
------------------------------------------------
"iyi" olcum  <=> |yeni_c - GT| < |kf.konum - GT|   (merkez hatasini AZALTIRDI)
2x2: kabul_iyi / kabul_kotu / red_iyi / red_kotu

SINIR - DURUSTLUK NOTU
----------------------
Kapinin self.boyut bagimliligi kirilir, ama `rafine_kutu` ARAMA PENCERESI hala
self.boyut ile besleniyor (izleyici.py:559). Bagimlilik girdide kirilmiyor.

takip/ DEGISMEZ. Kabul olcutu: docs/architecture/A9_KABUL_OLCUTU.md (degistirilmedi).
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


A9 = _yukle("A9", "tani_a9_merkez.py")
A7, B = A9.A7, A9.B
from calistir import iou                                   # noqa: E402
from takip.izleyici import KILITLI, HedefTakip             # noqa: E402
from takip.tespit import rafine_kutu                       # noqa: E402
from veri.visdrone import VisDroneVidKaynak                # noqa: E402

SENSOR, N_KARE = A9.SENSOR, A9.N_KARE
SEVIYELER = [30, 20, 15, 10, 8]
SEVIYE_AD = A9.SEVIYE_AD
KOPAN = ["uav0000117_02622_v/23", "uav0000268_05773_v/31", "uav0000339_00001_v/49"]
DIZILER = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31),
           ("uav0000339_00001_v", 49), ("uav0000137_00458_v", 12),
           ("uav0000305_00000_v", 5), ("uav0000182_00000_v", 127)]
KOLLAR = ["kontrol_orig", "kontrol_repro", "ab2_bagimsiz", "oracle_kapi"]


def _bt_fabrika(tak, kapi_modu, durum):
    """izleyici.py:551-567'nin BIREBIR yeniden yazimi; TEK degisken: kapi ifadesi.

    Fonksiyon adi bilerek `_boyut_tazele` - Kalman sarmalayicisi cagirani
    yigindan bu adla taniyor.
    """
    def _boyut_tazele(bgr):
        r = rafine_kutu(bgr, tak.kf.konum, tak.boyut, hedef_renk=tak.imza.renk)
        if r is None:
            return
        tak.boyut = np.maximum(0.75 * tak.boyut + 0.25 * r[2:], tak.min_kenar)
        tak.boyut_olculen = 0.85 * tak.boyut_olculen + 0.15 * np.maximum(r[2:], tak.min_kenar)
        yeni_c = r[:2] + r[2:] / 2
        d = float(np.linalg.norm(yeni_c - tak.kf.konum))

        gt = durum["gt"]
        e_simdi = float(np.linalg.norm(tak.kf.konum - gt))
        e_olcum = float(np.linalg.norm(np.asarray(yeni_c, np.float64) - gt))
        iyi = e_olcum < e_simdi                      # kabul edilirse hata AZALIR mi

        if kapi_modu == "mevcut":
            kabul = d < 0.6 * float(tak.boyut.max())
        elif kapi_modu == "rafine":
            kabul = d < 0.6 * float(np.max(r[2:]))   # TAZE olcum, gecmisten bagimsiz
        elif kapi_modu == "oracle":
            kabul = iyi
        else:
            raise ValueError(kapi_modu)

        durum["kayit"].append({
            "kabul": bool(kabul), "iyi": bool(iyi),
            "d_px": round(d, 2),
            "esik_mevcut": round(0.6 * float(tak.boyut.max()), 2),
            "esik_rafine": round(0.6 * float(np.max(r[2:])), 2),
            "boyut_max": round(float(tak.boyut.max()), 2),
            "rafine_max": round(float(np.max(r[2:])), 2),
            "gt_L": round(durum["gt_L"], 2),
            "rafine_boyut_hatasi": round(float(np.max(r[2:])) / durum["gt_L"], 3)
            if durum["gt_L"] > 0 else None,
            "hata_simdi": round(e_simdi, 2), "hata_olcum": round(e_olcum, 2),
            "kazanc_px": round(e_simdi - e_olcum, 2)})

        if kabul:
            tak.kf.duzelt(yeni_c, r_carpan=1.0)      # r_carpan HER KOLDA 1.0
    return _boyut_tazele


def kol_olc(dizi, kol):
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    log = []
    sar = A9.KayitKalman(tak.kf, log)
    object.__setattr__(sar, "_tak", tak)
    tak.kf = sar

    durum = {"gt": None, "gt_L": 0.0, "kayit": []}
    if kol != "kontrol_orig":
        modu = {"kontrol_repro": "mevcut", "ab2_bagimsiz": "rafine",
                "oracle_kapi": "oracle"}[kol]
        tak._boyut_tazele = _bt_fabrika(tak, modu, durum)

    hata_l, iou_l, psr_l, kilit_l, P_l, bho_l = [], [], [], [], [], []
    guvenli_yanlis = 0
    kopus_kare, ard = None, 0
    for t in range(1, len(dizi)):
        img, gt = dizi[t]
        gc = (gt[:2] + gt[2:] / 2.0).astype(np.float64)
        gL = float(max(gt[2], gt[3]))
        durum["gt"], durum["gt_L"] = gc, gL
        object.__setattr__(sar, "_gt", gc)
        s = tak.guncelle(img)
        hata = float(np.linalg.norm(tak.kf.konum - gc))
        o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
        hata_l.append(hata); iou_l.append(o); psr_l.append(float(s["psr"]))
        P_l.append(float(tak.kf.P[0, 0] + tak.kf.P[1, 1]))
        bho_l.append(float(np.max(tak.boyut)) / gL if gL > 0 else np.nan)
        kilit_l.append(1 if (s["durum"] == KILITLI and o > 0.2) else 0)
        if s["durum"] == KILITLI and o < 0.2:
            guvenli_yanlis += 1
        if hata > A9.KOPUS_KAT * gL:
            ard += 1
            if ard >= A9.KOPUS_SABIR and kopus_kare is None:
                kopus_kare = t - A9.KOPUS_SABIR + 1
        else:
            ard = 0

    kk = durum["kayit"]
    ki = sum(1 for k in kk if k["kabul"] and k["iyi"])
    kk_ = sum(1 for k in kk if k["kabul"] and not k["iyi"])
    ri = sum(1 for k in kk if not k["kabul"] and k["iyi"])
    rk = sum(1 for k in kk if not k["kabul"] and not k["iyi"])
    kabul_hata = [k["rafine_boyut_hatasi"] for k in kk if k["kabul"]]
    zarar = [-k["kazanc_px"] for k in kk if k["kabul"] and not k["iyi"]]
    kacan = [k["kazanc_px"] for k in kk if not k["kabul"] and k["iyi"]]
    d = {"kare": len(hata_l),
         "ort_iou": A9.ort(iou_l), "kilit_orani": A9.ort(kilit_l),
         "merkez_hata_p50": A9.p(hata_l, 50), "merkez_hata_p95": A9.p(hata_l, 95),
         "guvenli_yanlis_kare": guvenli_yanlis, "kopus_karesi": kopus_kare,
         "psr_p50": A9.p(psr_l, 50), "psr_p05": A9.p(psr_l, 5),
         "P_konum_iz_p50": A9.p(P_l, 50), "P_konum_iz_p95": A9.p(P_l, 95),
         "bho_p50": A9.p(bho_l, 50), "bho_p95": A9.p(bho_l, 95),
         "boyut_tazele_cagri": len(kk),
         "kapi_kabul": ki + kk_, "kapi_red": ri + rk,
         "kabul_iyi": ki, "kabul_kotu": kk_, "red_iyi": ri, "red_kotu": rk,
         "kabul_edilen_rafine_boyut_hatasi_p50": A9.p(kabul_hata, 50) if kabul_hata else None,
         "kabul_edilen_rafine_boyut_hatasi_p95": A9.p(kabul_hata, 95) if kabul_hata else None,
         "kabul_kotu_toplam_zarar_px": round(float(np.sum(zarar)), 1) if zarar else 0.0,
         "red_iyi_kacan_kazanc_px": round(float(np.sum(kacan)), 1) if kacan else 0.0}
    if kol != "kontrol_orig":
        d["kapi_kayitlari"] = kk
    return d


def topla(dizi, tid, n):
    k = VisDroneVidKaynak("data/datasets/visdrone_vid", dizi, track_id=tid)
    out = []
    for kare in k:
        if kare.gt is not None and kare.gorunur:
            out.append((kare.goruntu, np.asarray(kare.gt, np.float32), [],
                        kare.genislik, kare.yukseklik))
        if len(out) >= n:
            break
    return out


ESD_ALAN = ["ort_iou", "merkez_hata_p50", "merkez_hata_p95", "guvenli_yanlis_kare",
            "kopus_karesi", "psr_p50", "bho_p50", "bho_p95", "kilit_orani"]


def main():
    cikti = {"asama": "A9 A/B-2 - _boyut_tazele kabul kapisinin self.boyut bagimliligi",
             "tek_degisken": "izleyici.py:566 kapi ifadesi (0.6*self.boyut.max() -> 0.6*max(r[2:]))",
             "r_carpan": "TUM kollarda 1.0 (A/B-1'in 6.0'i kullanilmadi)",
             "takip_degismedi": True,
             "kabul_olcutu_dosyasi": "docs/architecture/A9_KABUL_OLCUTU.md",
             "oracle_uyarisi": "oracle_kapi BASARI DEGIL, tanisal UST SINIRDIR.",
             "sinir": ("kapi self.boyut'tan kurtarildi, ama rafine_kutu ARAMA PENCERESI "
                       "hala self.boyut ile besleniyor (izleyici.py:559)."),
             "acik_cevrim_uyarisi": "Sonuc UST SINIRDIR.",
             "esdegerlik": {}, "diziler": {}}
    esd_fark = []
    for dizi_ad, tid in DIZILER:
        ad = f"{dizi_ad}/{tid}"
        kareler = topla(dizi_ad, tid, N_KARE)
        W, H = kareler[0][3], kareler[0][4]
        hucre, _ = B.arkaplan_hucresi(kareler, W, H, *SENSOR)
        rol = "KOPAN" if ad in KOPAN else "saglam"
        dd = {"rol": rol, "seviyeler": {}}
        print(f"\n--- {ad}  [{rol}] ---", flush=True)
        for L in SEVIYELER:
            d, s = A7.sensor_dizi(kareler, hucre, L, N_KARE)
            if len(d) < 10:
                dd["seviyeler"][SEVIYE_AD[L]] = {"not": "dizi kisa"}
                continue
            r = {k: kol_olc(d, k) for k in KOLLAR}
            for alan in ESD_ALAN:
                if r["kontrol_orig"][alan] != r["kontrol_repro"][alan]:
                    esd_fark.append({"dizi": ad, "seviye": SEVIYE_AD[L], "alan": alan,
                                     "orig": r["kontrol_orig"][alan],
                                     "repro": r["kontrol_repro"][alan]})
            dd["seviyeler"][SEVIYE_AD[L]] = r
            k0, k2, ko = r["kontrol_repro"], r["ab2_bagimsiz"], r["oracle_kapi"]
            print(f"  {SEVIYE_AD[L]:6s} IoU {k0['ort_iou']:.3f}->{k2['ort_iou']:.3f} "
                  f"[or {ko['ort_iou']:.3f}] | p95 {k0['merkez_hata_p95']:>7.2f}->"
                  f"{k2['merkez_hata_p95']:>7.2f} | gy {k0['guvenli_yanlis_kare']:>2}->"
                  f"{k2['guvenli_yanlis_kare']:>2} [or {ko['guvenli_yanlis_kare']:>2}] | "
                  f"kopus {str(k0['kopus_karesi']):>4}->{str(k2['kopus_karesi']):>4} "
                  f"[or {str(ko['kopus_karesi']):>4}] | kapi ki/kk/ri/rk "
                  f"{k0['kabul_iyi']}/{k0['kabul_kotu']}/{k0['red_iyi']}/{k0['red_kotu']}"
                  f" -> {k2['kabul_iyi']}/{k2['kabul_kotu']}/{k2['red_iyi']}/{k2['red_kotu']}",
                  flush=True)
        cikti["diziler"][ad] = dd
    cikti["esdegerlik"] = {"fark_sayisi": len(esd_fark), "farklar": esd_fark[:20],
                           "gecerli": len(esd_fark) == 0}
    yol = sys.argv[1] if len(sys.argv) > 1 else "cikti/a9_ab2_kapi.json"
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print(f"\nESDEGERLIK: {'TAMAM (orig == repro)' if not esd_fark else f'BOZUK - {len(esd_fark)} fark!'}")
    print("yazildi:", yol)


if __name__ == "__main__":
    main()
