"""A10.1 / D1 - A9 olculerinin TEMIZ YATAKTA yeniden kosumu.

D1: `bench_a52_kucuk_hedef.arkaplan_hucresi` artik (0,0)'a DUSMUYOR, hata veriyor.
Gecerli bos arkaplan hucresi olmayan diziler tabandan DUSTU:
    uav0000339_00001_v/49 · uav0000305_00000_v/5 · uav0000182_00000_v/127
TEMIZ TABAN: 117/23 · 268/31 · 137/12 · 370/0

Bu betik A9'un uc olcumunu ayni script'lerle, ayni parametrelerle, yalnizca
TEMIZ tabanda yeniden kosar:
    Asama 2  (kopus tespiti / mod etiketleme)   -> gazebo/tani_a9_kopus.py
    Deney 3.0 (olay tabani + tetikleyici)        -> gazebo/tani_a9_recovery.py
    Deney 3.2 KOL V (dogrulama, min_G)           -> gazebo/tani_a9_3_2.py mantigi

A9'un KENDI ciktisi (cikti/a9_takipci_merkez_recovery.json) DEGISTIRILMEZ:
kosum oncesi yedeklenir, sonrasi geri yazilir. Temiz yatak sonuclari AYRI
dosyaya (cikti/a10_1_temiz_yatak.json) gider.

Kural: 3.2'nin KOL V ayarlari BIREBIR korunur (N_DOG=5, A8.R_sec, tam G =
max(d_norm,a_norm,r_norm), kapi 1.0). Degisen TEK sey yataktir.
"""
import copy
import importlib.util as iu
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

A9_JSON = "cikti/a9_takipci_merkez_recovery.json"
CIKTI = "cikti/a10_1_temiz_yatak.json"
TEMIZ = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31),
         ("uav0000137_00458_v", 12), ("uav0000370_00001_v", 0)]
DUSEN = {"uav0000339_00001_v/49": "gecerli 1280x720 bos arkaplan hucresi yok (1904x1071)",
         "uav0000305_00000_v/5": "gecerli 1280x720 bos arkaplan hucresi yok (1904x1071)",
         "uav0000182_00000_v/127": "gecerli 1280x720 bos arkaplan hucresi yok (1344x756)"}
KOPAN_TEMIZ = ["uav0000117_02622_v/23", "uav0000268_05773_v/31", "uav0000370_00001_v/0"]


def _yukle(ad, dosya):
    sp = iu.spec_from_file_location(ad, os.path.join(HERE, dosya))
    m = iu.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def kol_v(model, E32, A8, A7, B):
    """Deney 3.2 KOL V'nin birebir tekrari, temiz tabanda, A5_baseline ile."""
    from calistir import iou
    from takip.izleyici import KILITLI
    kayit = []
    for dizi_ad, tid in TEMIZ:
        ad = f"{dizi_ad}/{tid}"
        kareler = B.kareleri_topla(dizi_ad, tid, E32.N_KARE)
        W, H = kareler[0][3], kareler[0][4]
        hucre, _ = B.arkaplan_hucresi(kareler, W, H, *E32.SENSOR)
        rol = "KOPAN" if ad in KOPAN_TEMIZ else "saglam"
        for L in E32.SEVIYELER:
            d, _s = A7.sensor_dizi(kareler, hucre, L, E32.N_KARE)
            if len(d) < 10:
                continue
            K = E32.hucre_izi(d)
            for x in K:
                if not x["durum_kilitli"] or x["kutu"] is None:
                    continue
                if x["t"] % E32.N_DOG != 0:
                    continue
                img, gt = d[x["t"]]
                Rv = A8.R_sec(x["boyut_max"])
                ad_l, ms = E32.adaylari_uret(model, img, x["kf_merkez"], Rv)
                puanli = [E32.G_skor(a["kutu"], x["kf_merkez"], x["kutu"][2:], 0)[0]
                          for a in ad_l]
                enG = min(puanli) if puanli else None
                kayit.append({"dizi": ad, "hucre": f"{ad}|{E32.SEVIYE_AD[L]}", "rol": rol,
                              "t": x["t"], "seviye": E32.SEVIYE_AD[L], "R": Rv,
                              "kanit_yok": len(ad_l) == 0,
                              "min_G": None if enG is None else round(float(enG), 4),
                              "takipci_dogru": bool(x["iou"] >= 0.5),
                              "takipci_yanlis": bool(x["iou"] < 0.2),
                              "takipci_iou": round(x["iou"], 4),
                              "gecikme_ms": round(float(ms), 2)})
            print(f"  KOL V {ad:<26}{E32.SEVIYE_AD[L]:>6} nokta={len(kayit)}", flush=True)
    return kayit


def main():
    yedek = json.load(open(A9_JSON))
    out = {"etiketler": ["TEMIZ YATAK", "ACIK CEVRIM", "TESHIS"],
           "d1": "arkaplan_hucresi (0,0) dususu kaldirildi; gecersiz yatak -> YatakHatasi",
           "temiz_taban": [f"{a}/{b}" for a, b in TEMIZ],
           "dusen_diziler": DUSEN,
           "a9_ciktisi_degismedi": True}
    try:
        KOP = _yukle("KOP", "tani_a9_kopus.py")
        KOP.DIZILER = TEMIZ
        print("=== ASAMA 2 (kopus tespiti) - temiz yatak ===", flush=True)
        KOP.main()
        J = json.load(open(A9_JSON))
        out["phase2_break_detection"] = J["phase2_break_detection"]

        REC = _yukle("REC", "tani_a9_recovery.py")
        REC.DIZILER = TEMIZ
        print("\n=== DENEY 3.0 (olay tabani) - temiz yatak ===", flush=True)
        REC.main()
        J = json.load(open(A9_JSON))
        out["phase3_0"] = {k: v for k, v in J["phase3_recovery"].items()
                           if k in ("mod_a", "mod_b", "limitations", "etiketler", "deney")}
    finally:
        json.dump(yedek, open(A9_JSON, "w"), indent=2, ensure_ascii=False)
        print("\nA9 ciktisi geri yazildi (degismedi).", flush=True)

    print("\n=== DENEY 3.2 KOL V - temiz yatak (A5_baseline) ===", flush=True)
    import torch
    torch.set_num_threads(8)
    from ultralytics import YOLO
    E32 = _yukle("E32", "tani_a9_3_2.py")
    A8, A7 = E32.A8, E32.A7
    B = E32.B
    agirlik, siniflar = A8.MODELLER["A5_baseline"]
    B.AGIRLIK, B.SINIFLAR = agirlik, siniflar
    model = YOLO(agirlik)
    B.yolo_calistir(model, np.zeros((360, 640, 3), np.uint8))
    out["kol_v"] = {"A5_baseline": kol_v(model, E32, A8, A7, B)}

    json.dump(out, open(CIKTI, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", CIKTI)


if __name__ == "__main__":
    main()
