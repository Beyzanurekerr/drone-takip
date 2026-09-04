"""A5 - YOLO tabanli hedef secici.

Mevcut sozlesmenin UCUNCU uygulamasidir:

    secici(adaylar, kare) -> {"kutu", "merkez", "alan"} | None

Birincisi `main.otomatik_hedef_sec` (hareket adaylari), ikincisi
`main.fare_hedef_sec` (A4, kullanici ROI'si). Bu modul takipciyi HIC bilmez;
`takip/` altindan hicbir sey import etmez. `main.kos()` govdesi degismez.

MIMARI (A5_INFERENCE_MIMARISI_KARSILASTIRMA.md):
    FRAME -> DETECTOR -> BBOX -> TRACKER -> RECOVERY
Detector'un NEREDE kostugu (masaustu CPU / Pi CPU / IMX500) tracker'i
ilgilendirmez; runtime degisimi yalnizca bu dosyada kalir.

AGIRLIK: sessizce INDIRILMEZ. Dosya yoksa `YoloHatasi` atilir ve cagiran
taraf temiz bir hata basar; klasik hat etkilenmez.

2 PX ON-TELAFI: `main.kos()` satir 382-384'te hareket lekesi icin
`kutu[2:] -= 2` uygular ve kutuyu `merkez`e gore yeniden konumlandirir.
Dedektor kutusu dilate edilmis DEGILDIR; bu yuzden burada kutu 2 px BUYUK
dondurulur ve telafi sadelesir - `kos()` govdesi bit-birebir kalir.
(A4'te `main._roi_aday` ile ayni kural; oradan import EDILMEZ ki
`veri/` -> `main` bagimliligi olusmasin.)
"""
import os
import time

import numpy as np

# COCO sinif kimlikleri -> repo `veri/etiket.py:ARAC_SINIFLARI` (4 car, 5 van,
# 6 truck, 9 bus) ile kavramsal karsiligi. VisDrone'un "van" sinifinin COCO'da
# dogrudan karsiligi yoktur; COCO "truck" onu da kapsar.
COCO_ARAC = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
VISDRONE_KARSILIK = {2: 4, 3: None, 5: 9, 7: 6}     # yalnizca belge amacli


class YoloHatasi(Exception):
    """Model bulunamadi / yuklenemedi. Klasik hat bundan etkilenmez."""


def _aday(x1, y1, x2, y2, genislik, yukseklik, min_kenar):
    """xyxy -> aday sozlugu. Kadraj disi kirpilir; gecersizse None."""
    kose = (float(x1), float(y1), float(x2), float(y2))
    if not all(np.isfinite(v) for v in kose):
        return None          # NaN/inf siralamayi ve min/max'i sessizce bozar
    x1, y1, x2, y2 = kose
    xa, xb = (x1, x2) if x1 <= x2 else (x2, x1)
    ya, yb = (y1, y2) if y1 <= y2 else (y2, y1)
    xa, ya = max(0.0, xa), max(0.0, ya)
    xb, yb = min(float(genislik), xb), min(float(yukseklik), yb)
    w, h = xb - xa, yb - ya
    if not (np.isfinite(w) and np.isfinite(h)) or w <= 0.0 or h <= 0.0:
        return None
    if w < min_kenar or h < min_kenar:
        return None
    merkez = np.array([xa + w / 2.0, ya + h / 2.0], np.float32)
    kutu = np.array([xa - 1.0, ya - 1.0, w + 2.0, h + 2.0], np.float32)  # on-telafi
    return {"kutu": kutu, "merkez": merkez, "alan": float(w * h)}


def _ortusuyor(aday, gt):
    """Aday kutusu GT kutusuyla ortusuyor mu (IoU > 0)."""
    a = aday["merkez"] - np.asarray(aday["kutu"][2:], np.float64) / 2.0
    aw, ah = float(aday["kutu"][2]), float(aday["kutu"][3])
    x1 = max(float(a[0]), float(gt[0]))
    y1 = max(float(a[1]), float(gt[1]))
    x2 = min(float(a[0]) + aw, float(gt[0]) + float(gt[2]))
    y2 = min(float(a[1]) + ah, float(gt[1]) + float(gt[3]))
    return (x2 - x1) > 0.0 and (y2 - y1) > 0.0


def yolo_hedef_sec(model_yolu, conf=0.25, siniflar=None, min_kenar=4.0,
                   gt_esle=False, imgsz=640):
    """YOLO ile hedef secici uret.

    model_yolu : agirlik dosyasi (ORNEK: "weights/yolov8n.pt"). Yoksa YoloHatasi.
    conf       : ultralytics guven esigi (modelin kendi parametresi)
    siniflar   : COCO sinif kimlikleri; None -> COCO_ARAC (arac siniflari)
    min_kenar  : bu kenarin altindaki kutu aday sayilmaz (izleyici.min_kenar=4.0)
    gt_esle    : True ise, GT olan karelerde GT'ye EN YAKIN tespit secilir.
                 Gerekce `main.gt_hedef_sec` ile aynidir: tek-nesne takibinde
                 adil olcum icin kilit ANINDA dogru araca kilitlenmek sart.
                 Varsayilan False -> saf dedektor davranisi (en yuksek guven).
    imgsz      : ultralytics giris boyutu. A5'te ROI KIRPMA YOKTUR; tam kare.
    """
    if not model_yolu or not os.path.exists(model_yolu):
        raise YoloHatasi(
            f"YOLO agirligi bulunamadi: {model_yolu!r}\n"
            f"       Agirlik SESSIZCE INDIRILMEZ. Once indirin, ornegin:\n"
            f"         python3 -c \"import urllib.request as u; u.urlretrieve("
            f"'https://github.com/ultralytics/assets/releases/download/v8.3.0/"
            f"yolov8n.pt','weights/yolov8n.pt')\"\n"
            f"       Sonra: --yolo weights/yolov8n.pt")
    try:
        from ultralytics import YOLO
    except Exception as e:                       # kurulu degil / bozuk kurulum
        raise YoloHatasi(f"ultralytics yuklenemedi: {e}") from e
    try:
        model = YOLO(model_yolu)
    except Exception as e:
        raise YoloHatasi(f"model yuklenemedi ({model_yolu}): {e}") from e

    izin = tuple(sorted(COCO_ARAC if siniflar is None else siniflar))
    olcum = {"cagri": 0, "tespit": 0, "aday": 0, "esitsiz": 0, "sureler_ms": []}

    def secici(adaylar, kare):
        t0 = time.perf_counter()
        olcum["cagri"] += 1
        try:
            r = model.predict(kare.goruntu, conf=conf, imgsz=imgsz,
                              classes=list(izin), verbose=False, device="cpu")[0]
        except Exception:                        # cikarim hatasi kosumu bozmasin
            olcum["sureler_ms"].append((time.perf_counter() - t0) * 1e3)
            return None
        kutular = []
        if r.boxes is not None and len(r.boxes):
            xyxy = r.boxes.xyxy.cpu().numpy()
            gv = r.boxes.conf.cpu().numpy()
            sn = r.boxes.cls.cpu().numpy().astype(int)
            for (x1, y1, x2, y2), g, s in zip(xyxy, gv, sn):
                a = _aday(x1, y1, x2, y2, kare.genislik, kare.yukseklik, min_kenar)
                if a is not None:
                    a["guven"], a["sinif"] = float(g), int(s)
                    kutular.append(a)
        olcum["tespit"] += len(kutular)
        olcum["sureler_ms"].append((time.perf_counter() - t0) * 1e3)
        if not kutular:
            return None
        if gt_esle and getattr(kare, "gt", None) is not None and kare.gorunur:
            g = np.asarray(kare.gt, np.float64)
            gc = g[:2] + g[2:] / 2.0
            sec = min(kutular, key=lambda a: float(np.linalg.norm(a["merkez"] - gc)))
            # EN YAKIN yeterli DEGILDIR: dedektor hedefi hic bulamadiysa "en
            # yakin" baska bir aractir ve sessizce YANLIS nesneye kilitlenir.
            # Ortusme sarti keyfi bir esik degil, "ayni nesne" tanimidir.
            if not _ortusuyor(sec, g):
                olcum["esitsiz"] += 1
                return None
        else:
            sec = max(kutular, key=lambda a: a["guven"])
        olcum["aday"] += 1
        return sec

    secici.olcum = olcum          # teshis/maliyet icin; `kos()` bunu okumaz
    secici.model_yolu = model_yolu
    return secici
