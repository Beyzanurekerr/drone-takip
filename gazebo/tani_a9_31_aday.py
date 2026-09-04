"""A9 Deney 3.1 - SAF ADAY TARAMA (SALT OKUNUR TESHIS).

*** ACIK CEVRIM · TESHIS · GT YALNIZCA OFFLINE ETIKETLEME ***

Recovery tracker'a ENTEGRE EDILMEDI. State machine YOK. Esik SECILMEZ.
takip/ DEGISMEZ. Tracker davranisi DEGISMEZ.

SORU
----
Son guvenilir merkez cevresinde bagimsiz dedektor aramasi yapildiginda
DOGRU hedef celdiriciden ayristirilabiliyor mu?

BASARI TANIMI (kullanici talimati)
----------------------------------
"kilide dondu" BASARI DEGILDIR.
Basari = DOGRU GT hedef adaylar arasinda SECILDI ve yanlis hedef SECILMEDI.
  dogru aday : GT ile IoU >= 0.5
  yanlis aday: GT ile IoU <  0.2
  secilen    : en yuksek guvenli aday (dedektorun kendi secimi)

ARAMA GENISLIKLERI (onceden tanimli, TEK OPTIMAL FORMUL UYDURULMADI)
--------------------------------------------------------------------
A8 merdiveni + tam kare ust sinir referansi:
    R = 160, 320, 640 (sensor px)  ve  TAM KARE (1280x720)
Her R icin kirpim 640x360'a getirilir (A8 ile ayni geometri) -> buyutme 640/R.
3.0'da olculen GEREKLI yaricap ayrica raporlanir; boylece hangi basamagin
yetecegi VERIDEN okunur, formul uydurulmaz.

UST SINIR UYARISI - ONEMLI
--------------------------
"Son guvenilir kare"nin hangisi oldugu GT ile etiketlenir (IoU >= 0.5).
Gercek sistemde bunu TETIKLEYICI secer ve Deney 3.0 tetikleyicilerin zayif
oldugunu gosterdi (benzerlik AUC 0.722, %40 kor nokta).
=> 3.1'in merkezleme kalitesi bir UST SINIRDIR.
Arama MERKEZI operasyoneldir (takipcinin kendi konumu), ama o merkezin
SECILDIGI AN degildir.
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
A8 = _yukle("A8", "tani_a8_adaptif_roi.py")
REC = _yukle("REC", "tani_a9_recovery.py")
A7, B = A9.A7, A9.B
from calistir import iou                                   # noqa: E402
from takip.izleyici import KILITLI, HedefTakip             # noqa: E402
from veri.visdrone import VisDroneVidKaynak                # noqa: E402
import takip.izleyici as IZ                                # noqa: E402

SENSOR, N_KARE = A9.SENSOR, A9.N_KARE
SEVIYELER = [30, 20, 15, 10, 8]
SEVIYE_AD = A9.SEVIYE_AD
GENISLIKLER = [160, 320, 640, "tam"]
DOGRU_IOU, YANLIS_IOU = 0.5, 0.2
KOPAN = ["uav0000117_02622_v/23", "uav0000268_05773_v/31", "uav0000339_00001_v/49"]
DIZILER = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31),
           ("uav0000339_00001_v", 49), ("uav0000137_00458_v", 12),
           ("uav0000305_00000_v", 5), ("uav0000182_00000_v", 127)]
_ORIG_RAFINE = IZ.rafine_kutu


def hucre_izi(dizi):
    """Takipciyi bir kez kosar: kare basina kf merkezi, kutusu ve GT IoU'su."""
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    K = []
    for t in range(1, len(dizi)):
        img, gt = dizi[t]
        s = tak.guncelle(img)
        o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
        K.append({"t": t, "iou": o,
                  "kf_merkez": tak.kf.konum.astype(float).copy(),
                  "kutu": None if s["kutu"] is None else np.asarray(s["kutu"], float).copy()})
    return K


def adaylari_degerlendir(model, img, merkez, R, gt, son_kutu):
    """Bir arama genisliginde adaylari uret ve DOGRU/YANLIS olarak etiketle."""
    if R == "tam":
        kutular, guvenler, ms = A8.A7.tam_kare_tespit(model, img)
        siniflar = None
    else:
        kutular, guvenler, ms, _rect = A8.roi_tespit(model, img, merkez, R)
        siniflar = None
    adaylar = []
    for k, g in zip(kutular, guvenler):
        o = float(iou(k, gt))
        kc = k[:2] + k[2:] / 2.0
        alan = float(k[2] * k[3])
        s_alan = None if son_kutu is None else float(son_kutu[2] * son_kutu[3])
        adaylar.append({
            "iou": round(o, 4), "guven": round(float(g), 4),
            "merkez_uzakligi_px": round(float(np.linalg.norm(kc - merkez)), 2),
            "alan_orani": round(alan / s_alan, 4) if s_alan else None,
            "en_boy": round(float(k[2]) / max(float(k[3]), 1e-6), 3),
            "dogru": bool(o >= DOGRU_IOU), "yanlis": bool(o < YANLIS_IOU)})
    d = [a for a in adaylar if a["dogru"]]
    y = [a for a in adaylar if a["yanlis"]]
    secilen = max(adaylar, key=lambda a: a["guven"]) if adaylar else None
    en_d = max(d, key=lambda a: a["guven"]) if d else None
    en_y = max(y, key=lambda a: a["guven"]) if y else None
    return {
        "aday_sayisi": len(adaylar),
        "dogru_bulundu": bool(d), "yanlis_bulundu": bool(y),
        "ikisi_de": bool(d and y), "hicbiri": not adaylar,
        "secim_dogru": bool(secilen is not None and secilen["dogru"]),
        "secim_yanlis": bool(secilen is not None and secilen["yanlis"]),
        "dogru_iou": en_d["iou"] if en_d else None,
        "yanlis_iou": en_y["iou"] if en_y else None,
        "dogru_guven": en_d["guven"] if en_d else None,
        "yanlis_guven": en_y["guven"] if en_y else None,
        "skor_farki": (round(en_d["guven"] - en_y["guven"], 4)
                       if (en_d and en_y) else None),
        "dogru_merkez_uzakligi": en_d["merkez_uzakligi_px"] if en_d else None,
        "gecikme_ms": round(float(ms), 2),
        "adaylar": adaylar}


def main():
    import torch
    torch.set_num_threads(8)
    from ultralytics import YOLO

    sonuc = {"etiketler": ["ACIK CEVRIM", "TESHIS", "GT YALNIZCA OFFLINE ETIKETLEME"],
             "deney": "3.1 - saf aday tarama",
             "basari_tanimi": "DOGRU GT hedef SECILDI ve yanlis hedef SECILMEDI",
             "ust_sinir_uyarisi": ("son guvenilir kare GT ile etiketlendi; gercek "
                                   "sistemde tetikleyici secer ve 3.0 tetikleyicilerin "
                                   "zayif oldugunu gosterdi -> merkezleme UST SINIRDIR"),
             "arama_genislikleri": [str(x) for x in GENISLIKLER],
             "not": "recovery tracker'a entegre EDILMEDI, state machine YOK, takip/ DEGISMEDI",
             "modeller": {}}

    for mad, (agirlik, siniflar) in A8.MODELLER.items():
        B.AGIRLIK, B.SINIFLAR = agirlik, siniflar
        model = YOLO(agirlik)
        B.yolo_calistir(model, np.zeros((360, 640, 3), np.uint8))
        print(f"\n===== {mad} =====", flush=True)
        md = {"agirlik": agirlik, "epizotlar": []}
        for dizi_ad, tid in DIZILER:
            ad = f"{dizi_ad}/{tid}"
            k = VisDroneVidKaynak("data/datasets/visdrone_vid", dizi_ad, track_id=tid)
            kareler = []
            for kare in k:
                if kare.gt is not None and kare.gorunur:
                    kareler.append((kare.goruntu, np.asarray(kare.gt, np.float32), [],
                                    kare.genislik, kare.yukseklik))
                if len(kareler) >= N_KARE:
                    break
            W, H = kareler[0][3], kareler[0][4]
            hucre, _ = B.arkaplan_hucresi(kareler, W, H, *SENSOR)
            rol = "KOPAN" if ad in KOPAN else "saglam"
            for L in SEVIYELER:
                d, s = A7.sensor_dizi(kareler, hucre, L, N_KARE)
                if len(d) < 10:
                    continue
                K = hucre_izi(d)
                Kd = [{"t": x["t"], "_iou": x["iou"]} for x in K]
                eps = REC.epizotlari_bul(Kd)
                for e in eps:
                    sg = e["son_guvenilir_idx"]
                    if sg is None:
                        merkez = K[0]["kf_merkez"]; son_kutu = K[0]["kutu"]; sg_t = 0
                        merkez_kaynagi = "kilit_karesi (epizot oncesi guvenilir kare yok)"
                    else:
                        merkez = K[sg]["kf_merkez"]; son_kutu = K[sg]["kutu"]; sg_t = K[sg]["t"]
                        merkez_kaynagi = "son guvenilir karedeki takipci konumu"
                    bas_t = K[e["bas_idx"]]["t"]
                    ep = {"hucre": f"{ad}|{SEVIYE_AD[L]}", "rol": rol,
                          "bas_t": bas_t, "uzunluk": e["uzunluk"],
                          "son_guvenilir_t": sg_t, "merkez_kaynagi": merkez_kaynagi,
                          "arama_merkezi": [round(float(v), 2) for v in merkez],
                          "kareler": []}
                    for i in range(e["bas_idx"], e["son_idx"] + 1):
                        img, gt = d[K[i]["t"]]
                        gc = gt[:2] + gt[2:] / 2.0
                        kayit = {"t": K[i]["t"],
                                 "gecen_kare": K[i]["t"] - sg_t,
                                 "gerekli_yaricap_px": round(
                                     float(np.linalg.norm(gc - merkez)), 2),
                                 "gt_L": round(float(max(gt[2], gt[3])), 2),
                                 "genislikler": {}}
                        for R in GENISLIKLER:
                            kayit["genislikler"][str(R)] = adaylari_degerlendir(
                                model, img, merkez, R, gt, son_kutu)
                        ep["kareler"].append(kayit)
                    md["epizotlar"].append(ep)
                    ilk = {}
                    for R in GENISLIKLER:
                        f = next((k2["t"] for k2 in ep["kareler"]
                                  if k2["genislikler"][str(R)]["secim_dogru"]), None)
                        ilk[str(R)] = None if f is None else f - ep["bas_t"]
                    ep["ilk_dogru_secim_gecen_kare"] = ilk
                    print(f"  {ad:<26}{SEVIYE_AD[L]:>6} ep t={ep['bas_t']:>3} "
                          f"len={ep['uzunluk']:>3} | ilk dogru secim (kare): {ilk}", flush=True)
        sonuc["modeller"][mad] = md

    yol = "cikti/a9_takipci_merkez_recovery.json"
    J = json.load(open(yol))
    J["phase3_recovery"]["phase3_1_candidate_search"] = sonuc
    json.dump(J, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
