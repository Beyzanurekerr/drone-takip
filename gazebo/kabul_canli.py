"""CANLI mod kabul testi (2026-09-08): scripted 60 s tirmanis 50->200 m.

Kullanicinin kabul olcutu: 60 s canli surusте 50->200 m tirmanis, kilit
orani >=%90, FPS >=15. Klavye/insan YOK - "kendin sur" istegi geri-beslemeli
bir tirmanis kontrolcusuyle KARSILANIR (asagi bkz.); GERCEK elle surus
KULLANICI tarafindan ayrica test edilecek (bkz. docs/KURULUM.md).

GT YOK (canli ucuste onceden kaydedilmis poz akisi yok - bkz.
veri/gazebo_canli.py docstring) - "kilit orani" GT'ye karsi IoU DEGIL,
takipcinin KENDI durum raporunun (`durum=="KILITLI"`) orani. `--mod demo`
ile AYNI boru hatti (KaroArayici/YOLO soguk edinme + dedektor_karar) -
main.py'nin demo dalinin BIREBIR ayni kurulumu, yalniz kaynak CANLI.

Tirmanis kontrolcusu: her ~0.2 s'de bir
    vz = clip((HEDEF_IRTIFA - mevcut_irtifa) / kalan_sure, 0, VZ_MAKS)
- boylece GERCEK RTF ne olursa olsun (olculdu: baglanti-testinde ~0.54-0.57,
ama YOLO/tracking CPU yukuyle DEGISEBILIR - bu script ONU da olcer) sistem
60 s'lik butceyi hedefe gore ADAPTIF kullanir, sabit bir vz varsayimina
GUVENMEZ.
"""
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import demo_ayar                                                   # noqa: E402
from ultralytics import YOLO                                       # noqa: E402
from main import kos                                               # noqa: E402
from veri.gazebo_canli import GazeboCanliKaynak, CANLI_TUVAL_OLCEK  # noqa: E402
from takip.izleyici import KILITLI                                 # noqa: E402
from takip.izleyici import KORUMA_ESIK as KORUMA_ESIK_VARSAYILAN   # noqa: E402

BASLANGIC_IRTIFA = 50.0
HEDEF_IRTIFA = 200.0
SURE_S = 60.0
VZ_MAKS = 8.0
FPS_ESIK = 15.0
KILIT_ESIK = 0.90
CIKTI = "cikti/canli/kabul"


def main():
    os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
    model = YOLO(demo_ayar.A6_AGIRLIK)
    # sensor-px kalibrasyonu (Plan B, 2026-09-08): kamera IMX500'un yarisi
    # (1014x760, odak_px=780.5) - R_MERDIVEN/koruma_esik/min_kenar bu
    # kameraya gore TUVAL_OLCEK ile yeniden olceklenmeden KaroArayici/
    # HedefTakip KURULMAZ (bkz. veri/gazebo_canli.py, demo_ayar.py).
    demo_ayar.ayarla_tuval_olcek(CANLI_TUVAL_OLCEK)
    koruma_esik = KORUMA_ESIK_VARSAYILAN * CANLI_TUVAL_OLCEK
    min_kenar = 4.0 * CANLI_TUVAL_OLCEK
    kaynak = GazeboCanliKaynak(kam_z0=BASLANGIC_IRTIFA, sure_sn=SURE_S)
    karayici = demo_ayar.KaroArayici(kaynak.genislik, kaynak.yukseklik, model)
    karayici.sifirla((kaynak.genislik / 2.0, kaynak.yukseklik / 2.0))
    secici = demo_ayar.demo_hedef_sec(karayici)

    t0 = time.time()
    irtifa_gecmis = []
    dur = threading.Event()

    def tirman():
        while not dur.is_set():
            kalan = SURE_S - (time.time() - t0)
            irtifa_gecmis.append((time.time() - t0, kaynak.irtifa))
            if kalan <= 0.5:
                kaynak.komut_ayarla(0.0, 0.0, 0.0, 0.0)
                break
            vz = max(0.0, min(VZ_MAKS, (HEDEF_IRTIFA - kaynak.irtifa) / kalan))
            kaynak.komut_ayarla(0.0, 0.0, vz, 0.0)
            time.sleep(0.2)

    t = threading.Thread(target=tirman, daemon=True)
    t.start()
    print(f"baslangic irtifa={kaynak.irtifa:.1f} m, hedef={HEDEF_IRTIFA} m, "
          f"sure={SURE_S} s", flush=True)

    try:
        m = kos(kaynak, cekirdek="renk_dcf", pencere=False,
                kaydet=CIKTI + ".mp4", hedef_secici=secici,
                kayip_dedektor=karayici,
                dedektor_boyut=demo_ayar.DEDEKTOR_BOYUT_OTORITESI,
                dedektor_karar=demo_ayar.DEDEKTOR_KARAR_OTORITESI,
                n_tespit=demo_ayar.N_TESPIT, demo_kayit=True,
                mod_etiketi="demo",
                koruma_esik=koruma_esik, min_kenar=min_kenar)
    finally:
        dur.set()
        t.join(timeout=2)

    satirlar = [json.loads(s) for s in open(CIKTI + ".jsonl")]
    n = len(satirlar)
    kilit = sum(1 for s in satirlar if s["durum"] == KILITLI) / max(n, 1)
    irtifalar = [s["irtifa"] for s in satirlar if s.get("irtifa") is not None]

    ozet = {
        "kare": n, "fps": m["fps"], "kilit_orani": kilit,
        "irtifa_baslangic": irtifalar[0] if irtifalar else None,
        "irtifa_bitis": irtifalar[-1] if irtifalar else None,
        "irtifa_gecmis_ornek": irtifa_gecmis[::10],
        "kabul_fps": m["fps"] >= FPS_ESIK,
        "kabul_kilit": kilit >= KILIT_ESIK,
    }
    ozet["GECTI"] = ozet["kabul_fps"] and ozet["kabul_kilit"]
    json.dump(ozet, open(CIKTI + ".json", "w"), indent=2, ensure_ascii=False)
    print(json.dumps(ozet, indent=2, ensure_ascii=False))
    print("GECTI" if ozet["GECTI"] else "KALDI")


if __name__ == "__main__":
    main()
