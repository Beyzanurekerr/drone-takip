#!/usr/bin/env python3
"""Pi olcum script - drone_takip PI_HAZIRLIK.

Raspberry Pi Zero 2 W + IMX500 (Pi AI Camera) uzerinde tek komutla kosar ve
pi/sonuc.json uretir. `--pc` bayragiyla ayni script bu depoyu klonlayan HER
PC'de de calisir (picamera2/vcgencmd yoksa o bolumler atlanir) -- amac, Pi
elimize gectiginde script'in ILK denemede calismasidir.

Olcen uc bagimsiz bolum:
  1) takip cekirdegi (takip/izleyici.py: ego-motion + Kalman, DCF korelasyon
     cekirdegi, yeniden-tespit/kutu-rafine) -- SAF PYTHON, Pi CPU'sunda da
     PC'de de calisir, --pc ile bu depoda da olculebilir.
  2) IMX500 sensor-ustu cikarim (tam kare ve sensor-ROI modu) -- yalnizca
     gercek Pi + AI Camera donanimi + surucusu ile calisir.
  3) CPU sicaklik / throttle (vcgencmd) -- yalnizca Raspberry Pi OS.

SAYI DISIPLINI (bkz. docs/architecture/KALICI_KISITLAR.md): bu script hicbir
sayi UYDURMAZ. Donanim/kutuphane yoksa ilgili alan {"durum": "ATLANDI", ...}
olarak isaretlenir, sifir/varsayilan bir sayi ILE DOLDURULMAZ.

Kullanim:
    # Pi'de, gercek donanimla:
    python3 pi/olc_pi.py

    # PC'de kuru kosum (yalnizca takip cekirdegi olculur):
    python3 pi/olc_pi.py --pc
"""
import argparse
import glob
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJE = os.path.dirname(ROOT)
sys.path.insert(0, PROJE)

# IMX500 (Sony) sensorunun tam cozunurlugu -- picamera2/devices/imx500/imx500.py
# icindeki IMX500.__get_full_sensor_resolution()'dan DOGRULANDI (kaynak
# okunarak, raspberrypi/picamera2 deposu, main, 2026-09). ROI koordinatlari
# bu tam-sensor piksel uzayinda verilir.
IMX500_TAM_SENSOR = (4056, 3040)


# --------------------------------------------------------------------------
# yardimcilar
# --------------------------------------------------------------------------
def _yuzdelik(sirali_degerler, q):
    n = len(sirali_degerler)
    if n == 1:
        return sirali_degerler[0]
    k = (n - 1) * (q / 100.0)
    f, c = int(k), min(int(k) + 1, n - 1)
    if f == c:
        return sirali_degerler[f]
    return sirali_degerler[f] + (sirali_degerler[c] - sirali_degerler[f]) * (k - f)


def _ozet(degerler_ms):
    if not degerler_ms:
        return None
    s = sorted(degerler_ms)
    return {
        "n": len(s),
        "p50_ms": round(_yuzdelik(s, 50), 4),
        "p95_ms": round(_yuzdelik(s, 95), 4),
        "ort_ms": round(sum(s) / len(s), 4),
        "min_ms": round(s[0], 4),
        "maks_ms": round(s[-1], 4),
    }


def _git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=PROJE, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


# --------------------------------------------------------------------------
# 1) takip cekirdegi: ego / DCF (korelasyon) / tespit+rafine
# --------------------------------------------------------------------------
def takip_cekirdek_olc(kareler_dir, n=100, isinma=8):
    """640x480 Gazebo kareleri uzerinde HedefTakip.guncelle() bilesen sureleri.

    Kilit hedefi GT ile degil, tak.tarama()'nin dondurdugu en buyuk hareket
    adayiyla kurulur (bu bir DOGRULUK bench'i degil, SURE bench'idir -- IoU/
    kilit orani gibi dogruluk sayilari RAPOR.md ve A6 raporlarindaki ayri
    olculmus degerlerdir, burada UYDURULMAZ/tekrarlanmaz).

    izleyici.py'nin kendi zamanlayicisi ("sure" sozlugu) uc bilesen doner:
    "ego" (ego-motion), "mosse" (DCF korelasyon cekirdegi -- takip adimi),
    "tespit" (yeniden-tespit + periyodik kutu-rafine `_boyut_tazele` BIRLIKTE
    -- kodda ayri bir "rafine" sayaci yok, bu yuzden ikisi tek kalemde
    raporlanir), "toplam".
    """
    import cv2
    from takip.izleyici import HedefTakip

    dosyalar = sorted(
        glob.glob(os.path.join(kareler_dir, "*.png"))
        + glob.glob(os.path.join(kareler_dir, "*.jpg"))
    )
    gerekli = isinma + n
    if len(dosyalar) < gerekli:
        raise RuntimeError(
            f"{kareler_dir}: {len(dosyalar)} kare var, en az {gerekli} gerekiyor "
            f"(isinma={isinma} + olcum={n})"
        )

    tak = HedefTakip()
    ham = {"ego": [], "mosse": [], "tespit": [], "toplam": []}
    kilitlendi = False
    kilit_kare_i = None
    olculen = 0
    cozunurluk = None

    for i, yol in enumerate(dosyalar):
        img = cv2.imread(yol)
        if img is None:
            raise RuntimeError(f"kare okunamadi: {yol}")
        if cozunurluk is None:
            cozunurluk = f"{img.shape[1]}x{img.shape[0]}"

        if not kilitlendi:
            adaylar = tak.tarama(img)
            if i >= isinma and adaylar:
                en = max(adaylar, key=lambda a: float(a["kutu"][2]) * float(a["kutu"][3]))
                tak.kilitle(img, en["kutu"].copy())
                kilitlendi = True
                kilit_kare_i = i
            continue

        sonuc = tak.guncelle(img)
        for k in ham:
            ham[k].append(sonuc["sure"][k])
        olculen += 1
        if olculen >= n:
            break

    if not kilitlendi:
        raise RuntimeError(
            f"{kareler_dir}: ilk {isinma} kare icinde hicbir hareket adayi bulunamadi, kilit kurulamadi"
        )
    if olculen < n:
        print(
            f"UYARI: istenen {n} kare yerine {olculen} kare olculdu "
            f"({kareler_dir} kare deposu erken tukendi)",
            file=sys.stderr,
        )

    return {
        "girdi_dizini": os.path.relpath(kareler_dir, PROJE),
        "cozunurluk": cozunurluk,
        "isinma_kare": isinma,
        "kilit_kare_indeksi": kilit_kare_i,
        "olculen_kare": olculen,
        "not": (
            "Kilit dogrulukla degil sureyle ilgilidir; hedef tak.tarama()'nin "
            "en buyuk hareket adayiyla secildi. 'tespit' bileseni yeniden-tespit "
            "VE periyodik kutu-rafine'yi (_boyut_tazele) birlikte icerir."
        ),
        "bilesen_ms": {
            "ego_motion": _ozet(ham["ego"]),
            "dcf_korelasyon": _ozet(ham["mosse"]),
            "tespit_ve_rafine": _ozet(ham["tespit"]),
            "toplam": _ozet(ham["toplam"]),
        },
    }


# --------------------------------------------------------------------------
# 2) IMX500 sensor-ustu cikarim -- yalnizca gercek Pi + AI Camera'da calisir
# --------------------------------------------------------------------------
def imx500_olc(model_yolu, sure_s=20, sensor_roi=None):
    """IMX500 uzerinde tam-kare veya sensor-ROI modunda cikarim gecikmesi/fps.

    *** BU FONKSIYON PC'DE HIC CALISTIRILAMAZ VE TEST EDILMEDI. ***
    picamera2.devices.imx500 /dev/v4l-subdev* surucu dugumune dogrudan ioctl
    yapar ve libcamera'ya baglanir -- yalnizca gercek IMX500 donanimi +
    Raspberry Pi OS surucusu ile calisir. API cagrilari
    (IMX500(model), Picamera2(imx500.camera_num), imx500.get_outputs(),
    imx500.set_inference_roi_abs()) raspberrypi/picamera2 (main, 2026-09)
    kaynak kodu OKUNARAK dogrulandi, ama UCTAN UCA hicbir zaman calistirilmadi.
    Pi'de ilk calistirmada hata verirse burasi (import yollari, config
    parametreleri) donanimla birlikte duzeltilmelidir -- oncelikle
    `raspberrypi/picamera2` deposunun o anki `examples/` dizinine (varsa)
    bakilmali.

    Olculen sey `picam2.capture_metadata()` + `imx500.get_outputs()` cagri
    suresidir: bu, TUKETICI tarafinda gorunen kare-basi gecikmedir (sensorun
    kendi kare periyoduyla sinirlidir), sensor-ici tensor hesaplama suresinin
    izole edilmis hali DEGILDIR -- IMX500'un ic profil verisi bu script'ten
    ayri, cihaz uzerindeki debug arayuzunden okunmalidir (bkz. yorum icinde
    gecen fw_progress/debugfs -- bu script onu okumuyor).
    """
    from picamera2 import Picamera2
    from picamera2.devices import IMX500

    imx500 = IMX500(model_yolu)
    picam2 = Picamera2(imx500.camera_num)

    def _mod_olc(roi):
        if roi is not None:
            imx500.set_inference_roi_abs(roi)
        else:
            imx500.set_inference_roi_abs((0, 0) + IMX500_TAM_SENSOR)
        cfg = picam2.create_preview_configuration(buffer_count=8)
        picam2.start(cfg, show_preview=False)
        time.sleep(0.5)  # AE/AF + ilk agirlik yuklemesi icin isinma, olculmez
        sureler_ms = []
        gecerli_kare = 0
        t_bitis = time.monotonic() + sure_s
        while time.monotonic() < t_bitis:
            t0 = time.perf_counter()
            metadata = picam2.capture_metadata()
            outputs = imx500.get_outputs(metadata, add_batch=True)
            t1 = time.perf_counter()
            if outputs is not None:
                sureler_ms.append((t1 - t0) * 1e3)
                gecerli_kare += 1
        picam2.stop()
        return {
            "roi_full_sensor_px": list(roi) if roi is not None else ["tam", "kare"],
            "gecerli_kare": gecerli_kare,
            "sure_s": sure_s,
            "gecikme_ms": _ozet(sureler_ms),
            "fps_yaklasik": round(gecerli_kare / sure_s, 2) if gecerli_kare else None,
        }

    try:
        sonuc = {
            "model": os.path.relpath(model_yolu, PROJE),
            "network_intrinsics": (
                str(imx500.network_intrinsics) if imx500.network_intrinsics else None
            ),
            "tam_kare": _mod_olc(None),
        }
        if sensor_roi is not None:
            sonuc["sensor_roi"] = _mod_olc(sensor_roi)
        return sonuc
    finally:
        picam2.close()


# --------------------------------------------------------------------------
# 3) CPU sicaklik / throttle (vcgencmd) -- Raspberry Pi OS'e ozgu
# --------------------------------------------------------------------------
def _vcgencmd_sicaklik():
    out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True).strip()
    return float(out.split("=")[1].split("'")[0])


def _vcgencmd_throttled():
    out = subprocess.check_output(["vcgencmd", "get_throttled"], text=True).strip()
    return out.split("=")[1]


def termal_olc(sure_s=300, aralik_s=5):
    if shutil.which("vcgencmd") is None:
        return {"durum": "ATLANDI", "neden": "vcgencmd bulunamadi (Raspberry Pi OS degil)"}
    kayitlar = []
    t_bas = time.monotonic()
    t_bitis = t_bas + sure_s
    while time.monotonic() < t_bitis:
        try:
            kayitlar.append({
                "t_s": round(time.monotonic() - t_bas, 1),
                "sicaklik_c": _vcgencmd_sicaklik(),
                "throttled_hex": _vcgencmd_throttled(),
            })
        except Exception as e:
            kayitlar.append({"t_s": round(time.monotonic() - t_bas, 1), "hata": str(e)})
        time.sleep(aralik_s)
    return {"durum": "TAMAMLANDI", "aralik_s": aralik_s, "kayit_sayisi": len(kayitlar), "kayitlar": kayitlar}


# --------------------------------------------------------------------------
def _roi_parse(metin):
    x, y, w, h = (int(v) for v in metin.split(","))
    return (x, y, w, h)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pc", action="store_true",
                     help="PC kuru kosum: yalnizca takip cekirdegini olcer, IMX500/termal ATLANIR")
    ap.add_argument("--kareler", default=os.path.join(PROJE, "data/gazebo/G0/kareler"),
                     help="takip cekirdegi icin kare dizini (varsayilan: data/gazebo/G0/kareler)")
    ap.add_argument("--n", type=int, default=100, help="olculecek kare sayisi (varsayilan 100)")
    ap.add_argument("--isinma", type=int, default=8, help="kilit kurulana kadar taranan kare sayisi ustsiniri")
    ap.add_argument("--model-640", default=os.path.join(PROJE, "weights/imx500/a6_640.rpk"))
    ap.add_argument("--model-320", default=os.path.join(PROJE, "weights/imx500/a6_320.rpk"))
    ap.add_argument("--imx500-sure-s", type=int, default=20, help="IMX500 modu basina olcum suresi (sn)")
    ap.add_argument("--sensor-roi", default=None,
                     help="320 modeli icin sensor-ROI 'x,y,w,h' (tam-sensor px). "
                          "Varsayilan: sensorun merkezine gore yarisi (yer/kalibrasyon "
                          "kararidir, OLCULMEDI/tuning gerekir).")
    ap.add_argument("--termal-sure-s", type=int, default=300, help="termal/throttle kayit suresi (sn)")
    ap.add_argument("--termal-aralik-s", type=int, default=5)
    ap.add_argument("--cikti", default=os.path.join(ROOT, "sonuc.json"))
    args = ap.parse_args()

    rapor = {
        "olusturma_zamani_utc": datetime.now(timezone.utc).isoformat(),
        "mod": "PC_KURU_KOSUM" if args.pc else "PI",
        "host_platform": platform.platform(),
        "python": sys.version.split()[0],
        "git_commit": _git_commit(),
    }

    print("== [1/3] takip cekirdegi (ego / DCF / tespit+rafine) olculuyor ==", file=sys.stderr)
    try:
        rapor["takip_cekirdek"] = takip_cekirdek_olc(args.kareler, n=args.n, isinma=args.isinma)
    except Exception as e:
        rapor["takip_cekirdek"] = {"durum": "HATA", "hata": f"{type(e).__name__}: {e}"}
        print(f"  HATA: {e}", file=sys.stderr)

    if args.pc:
        rapor["imx500"] = {"durum": "ATLANDI", "neden": "--pc: gercek IMX500 donanimi/surucusu yok"}
        rapor["termal"] = {"durum": "ATLANDI", "neden": "--pc: vcgencmd Raspberry Pi OS'e ozgu"}
    else:
        print("== [2/3] IMX500 cikarim (tam kare + sensor-ROI) olculuyor ==", file=sys.stderr)
        rapor["imx500"] = {}
        try:
            import picamera2  # noqa: F401
        except ImportError as e:
            rapor["imx500"] = {"durum": "ATLANDI", "neden": f"picamera2 kurulu degil: {e}"}
        else:
            if os.path.exists(args.model_640):
                try:
                    rapor["imx500"]["640"] = imx500_olc(args.model_640, sure_s=args.imx500_sure_s)
                except Exception as e:
                    rapor["imx500"]["640"] = {"durum": "HATA", "hata": f"{type(e).__name__}: {e}"}
                    print(f"  HATA (640): {e}", file=sys.stderr)
            else:
                rapor["imx500"]["640"] = {"durum": "ATLANDI", "neden": f"{args.model_640} bulunamadi -- once paketleme (adim 1)"}

            if os.path.exists(args.model_320):
                if args.sensor_roi:
                    roi = _roi_parse(args.sensor_roi)
                else:
                    w, h = IMX500_TAM_SENSOR
                    roi = (w // 4, h // 4, w // 2, h // 2)
                try:
                    rapor["imx500"]["320_sensor_roi"] = imx500_olc(
                        args.model_320, sure_s=args.imx500_sure_s, sensor_roi=roi)
                except Exception as e:
                    rapor["imx500"]["320_sensor_roi"] = {"durum": "HATA", "hata": f"{type(e).__name__}: {e}"}
                    print(f"  HATA (320/roi): {e}", file=sys.stderr)
            else:
                rapor["imx500"]["320_sensor_roi"] = {"durum": "ATLANDI", "neden": f"{args.model_320} bulunamadi -- once paketleme (adim 1)"}

        print("== [3/3] CPU sicaklik/throttle kaydi (~5 dk) ==", file=sys.stderr)
        try:
            rapor["termal"] = termal_olc(sure_s=args.termal_sure_s, aralik_s=args.termal_aralik_s)
        except Exception as e:
            rapor["termal"] = {"durum": "HATA", "hata": f"{type(e).__name__}: {e}"}

    os.makedirs(os.path.dirname(args.cikti) or ".", exist_ok=True)
    with open(args.cikti, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    print(f"yazildi: {args.cikti}", file=sys.stderr)


if __name__ == "__main__":
    main()
