"""A9 A/B-3 hazirligi - BOYUT CAPASI: bagimsizlik denetimi + tanisal zincir testi.

BU BIR ADAY MEKANIZMA DEGERLENDIRMESI DEGILDIR.
Kullanicinin 4. maddesi: "Boyut hatasi azaldiginda gercekten DCF/PSR/kopus
zinciri azaliyor mu?" - once BU cevaplanir. Cevap icin GT kullanan bir ORACLE
capa kurulur; oracle BASARI DEGIL, UST SINIRDIR ve kabul olcutune sokulmaz.

KOLLAR
------
kontrol       : mevcut davranis (r_carpan 1.0, kapi baseline, merkez yolu aynen)
oracle_capa   : her karenin BASINDA tak.boyut ve tak.boyut_olculen GT boyutuna
                capalanir. Baska hicbir sey degismez: merkez yolu, r_carpan,
                kapi, PSR, KF, recovery, ROI - hepsi baseline.
                >>> TANISAL UST SINIR, aday mekanizma DEGIL.

AYRICA SINANAN: KILITLENME HIPOTEZI
-----------------------------------
rafine_kutu'nun kabul kapisi (tespit.py:121-122):
    oran = [bw,bh] / boyut ;  if not (0.35 < oran.mean() < 2.6): return None
Boyut 2.86 kattan fazla sismisse GERCEK hedefin orani 0.35'in altina duser ve
rafine REDDEDILIR -> boyut bir daha DUZELEMEZ. Bu hipotez, rafine'nin None
donme oraninin bho ile birlikte artip artmadigina bakilarak sinanir.

takip/ DEGISMEZ (md5 dogrulanir). Kabul olcutu degistirilmez.
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
import takip.izleyici as IZ                                # noqa: E402
from calistir import iou                                   # noqa: E402
from takip.izleyici import KILITLI, HedefTakip             # noqa: E402
from veri.visdrone import VisDroneVidKaynak                # noqa: E402

SENSOR, N_KARE = A9.SENSOR, A9.N_KARE
SEVIYELER = [30, 20, 15, 10, 8]
SEVIYE_AD = A9.SEVIYE_AD
KOPAN = ["uav0000117_02622_v/23", "uav0000268_05773_v/31", "uav0000339_00001_v/49"]
DIZILER = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31),
           ("uav0000339_00001_v", 49), ("uav0000137_00458_v", 12),
           ("uav0000305_00000_v", 5), ("uav0000182_00000_v", 127)]

_ORIG_RAFINE = IZ.rafine_kutu


def kol_olc(dizi, kol, kare_kaydi=False):
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    log = []
    sar = A9.KayitKalman(tak.kf, log)
    object.__setattr__(sar, "_tak", tak)
    tak.kf = sar

    durum = {"gt_wh": None, "gt_L": 0.0}
    raf = []

    def _rafine_kayitli(bgr, merkez, boyut, **kw):
        r = _ORIG_RAFINE(bgr, merkez, boyut, **kw)
        raf.append({"bho_girdi": round(float(np.max(boyut)) / durum["gt_L"], 3)
                    if durum["gt_L"] > 0 else None,
                    "None_dondu": r is None,
                    "cikti_max": None if r is None else round(float(np.max(r[2:])), 2)})
        return r

    IZ.rafine_kutu = _rafine_kayitli
    orig_guncelle = tak.guncelle

    def _guncelle_capali(bgr):
        tak.boyut = np.maximum(durum["gt_wh"].copy(), tak.min_kenar)
        tak.boyut_olculen = np.maximum(durum["gt_wh"].copy(), tak.min_kenar)
        return orig_guncelle(bgr)

    if kol == "oracle_capa":
        tak.guncelle = _guncelle_capali

    hata_l, iou_l, psr_l, kilit_l, P_l, bho_l = [], [], [], [], [], []
    guvenli_yanlis = 0
    kabul = red = 0
    kopus_kare, ard = None, 0
    kareler = []
    try:
        for t in range(1, len(dizi)):
            img, gt = dizi[t]
            gc = (gt[:2] + gt[2:] / 2.0).astype(np.float64)
            gL = float(max(gt[2], gt[3]))
            durum["gt_wh"] = np.asarray(gt[2:], np.float32)
            durum["gt_L"] = gL
            object.__setattr__(sar, "_gt", gc)
            n0, r0 = len(log), len(raf)
            s = tak.guncelle(img)
            hata = float(np.linalg.norm(tak.kf.konum - gc))
            o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
            bho = float(np.max(tak.boyut)) / gL if gL > 0 else np.nan
            hata_l.append(hata); iou_l.append(o); psr_l.append(float(s["psr"]))
            P_l.append(float(tak.kf.P[0, 0] + tak.kf.P[1, 1])); bho_l.append(bho)
            kilit_l.append(1 if (s["durum"] == KILITLI and o > 0.2) else 0)
            if s["durum"] == KILITLI and o < 0.2:
                guvenli_yanlis += 1
            dcf_kabul_bu = dcf_red_bu = 0
            for e in log[n0:]:
                if e["kaynak"] == "_takip_adimi":
                    if e["tip"] == "duzelt":
                        kabul += 1; dcf_kabul_bu += 1
                    elif e["tip"] == "sondur":
                        red += 1; dcf_red_bu += 1
            if hata > A9.KOPUS_KAT * gL:
                ard += 1
                if ard >= A9.KOPUS_SABIR and kopus_kare is None:
                    kopus_kare = t - A9.KOPUS_SABIR + 1
            else:
                ard = 0
            if kare_kaydi:
                yeni_raf = raf[r0:]
                kareler.append({"t": t, "gt_L": round(gL, 2), "bho": round(bho, 3),
                                "psr": round(float(s["psr"]), 2), "durum": str(s["durum"]),
                                "hata_px": round(hata, 2), "iou": round(o, 3),
                                "P_iz": round(float(tak.kf.P[0, 0] + tak.kf.P[1, 1]), 2),
                                "dcf_kabul": dcf_kabul_bu, "dcf_red": dcf_red_bu,
                                "rafine_cagri": len(yeni_raf),
                                "rafine_None": sum(1 for x in yeni_raf if x["None_dondu"])})
    finally:
        IZ.rafine_kutu = _ORIG_RAFINE

    n_raf = len(raf)
    n_none = sum(1 for x in raf if x["None_dondu"])
    d = {"kare": len(hata_l),
         "ort_iou": A9.ort(iou_l), "kilit_orani": A9.ort(kilit_l),
         "merkez_hata_p50": A9.p(hata_l, 50), "merkez_hata_p95": A9.p(hata_l, 95),
         "bho_p50": A9.p(bho_l, 50), "bho_p95": A9.p(bho_l, 95),
         "psr_p50": A9.p(psr_l, 50), "psr_p05": A9.p(psr_l, 5),
         "P_konum_iz_p50": A9.p(P_l, 50), "P_konum_iz_p95": A9.p(P_l, 95),
         "kopus_karesi": kopus_kare, "guvenli_yanlis_kare": guvenli_yanlis,
         "dcf_kabul": kabul, "dcf_red": red,
         "boyut_guncelleme_sayisi": n_raf,
         "rafine_None_sayisi": n_none,
         "rafine_None_orani": round(n_none / max(n_raf, 1), 4),
         "rafine_kayitlari": raf}
    if kare_kaydi:
        d["kareler"] = kareler
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


def main():
    cikti = {"asama": "A9 A/B-3 hazirligi - boyut capasi bagimsizlik denetimi + tanisal zincir",
             "oracle_uyarisi": "oracle_capa BASARI DEGIL, TANISAL UST SINIRDIR; "
                               "kabul olcutune sokulmaz.",
             "kilitlenme_hipotezi": "rafine_kutu oran kapisi [0.35,2.6] (tespit.py:122); "
                                    "bho>2.86 iken gercek hedef reddedilir -> boyut kilitlenir",
             "takip_degismedi": True, "diziler": {}}
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
            kk = (ad == "uav0000117_02622_v/23" and L in (20, 15))
            A = kol_olc(d, "kontrol", kare_kaydi=kk)
            O = kol_olc(d, "oracle_capa", kare_kaydi=kk)
            dd["seviyeler"][SEVIYE_AD[L]] = {"kontrol": A, "oracle_capa": O}
            print(f"  {SEVIYE_AD[L]:6s} bho50 {A['bho_p50']:>5.2f}->{O['bho_p50']:>5.2f} | "
                  f"PSR50 {A['psr_p50']:>6.1f}->{O['psr_p50']:>6.1f} | "
                  f"DCF k/r {A['dcf_kabul']:>2}/{A['dcf_red']:>2}->{O['dcf_kabul']:>2}/{O['dcf_red']:>2} | "
                  f"IoU {A['ort_iou']:.3f}->{O['ort_iou']:.3f} | "
                  f"p95 {A['merkez_hata_p95']:>7.2f}->{O['merkez_hata_p95']:>7.2f} | "
                  f"gy {A['guvenli_yanlis_kare']:>2}->{O['guvenli_yanlis_kare']:>2} | "
                  f"kopus {str(A['kopus_karesi']):>4}->{str(O['kopus_karesi']):>4} | "
                  f"rafineNone {A['rafine_None_orani']:.2f}->{O['rafine_None_orani']:.2f}",
                  flush=True)
        cikti["diziler"][ad] = dd
    yol = sys.argv[1] if len(sys.argv) > 1 else "cikti/a9_ab3_boyut_capasi.json"
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
