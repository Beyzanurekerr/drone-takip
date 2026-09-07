"""DEMO offline HUD uretimi (Adim 6): kutu + ROI + 4x inset + sag panel +
alt serit.

`main.py --mod demo --kaydet X.mp4` HAM kare + `X.jsonl` (kare basina durum)
yazar (bkz. `main.py:kos()` demo_kayit bloğu - gerçek şema: kare/durum/kutu/
roi/px/irtifa/mod/komut/iou/gt). Bu script ikisini birleştirip HUD'lu videoyu
OFFLINE üretir - kendi çizim kodu YOK, tüm çizim `gazebo/gorsel_uret.py`nin
"DEMO HUD" bölümündeki fonksiyonlardadır (talimat: "her deney BUNU çağırır,
kendi çizim kodu yazmaz").

DEMO ilkesi (bkz. `gorsel_uret.py` DEMO HUD başlığı): izleyici GT görmez,
hiçbir teşhis metriği (IoU/PSR/hassasiyet) ekrana yazılmaz - `rec["gt"]` ve
`rec["iou"]` jsonl'de varsa bile burada hiç OKUNMAZ.

Kosum: python3 -m gazebo.demo_hud_uret cikti/demo/kucul.mp4
"""
import argparse
import json
import os
import sys

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from gazebo import gorsel_uret  # noqa: E402
from gazebo.gorsel_uret import _dosya_govdesi  # noqa: E402

# 2026-09-07 (Adim 4 DUZELTME, burada da GECERLI): `video_uret()` tum
# kareleri bellekte biriktirir (kaydet.py'nin OOM'una AYNI sinif hata, 900
# karede ~8GB). Bunun YERINE gecilmez - kare goruntuleri STREAMING okunup
# hemen yazilir, bellek kare-goruntusu icin O(1) kalir. JSONL kayitlari
# (kare basina birkac float/str, goruntu DEGIL) tek seferde belleğe
# alinir - bu "biriktirme yok" kuralinin kapsami DISINDA (900 kayit
# ihmal edilebilir bellek, alt seridin TUM klip egrisini/bandini cizmesi
# icin ZATEN gerekli, bkz. gorsel_uret.demo_klip_serit_hazirla).


def _demo_olaylar_cikar(kayitlar, fps):
    """Durum degisikliklerini (kare_no, "t=..s ONCEKI -> YENI") olarak
    cikarir - `gorsel_uret._demo_serit_ciz`'in alt seritteki "son olay"
    notu icin. Yalniz JSONL kayitlarindan (goruntusuz) turetilir."""
    olaylar = []
    onceki = None
    for i, r in enumerate(kayitlar):
        d = r.get("durum")
        if d != onceki:
            t = i / fps if fps else 0.0
            onceki_ad = onceki or "-"
            olaylar.append((i, f"t={t:.1f}s  {onceki_ad}->{d}"))
            onceki = d
    return olaylar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ham_video")
    ap.add_argument("--json", default=None,
                    help="varsayilan: ham_video ile ayni govde, .jsonl")
    ap.add_argument("--deney", default="demo")
    ap.add_argument("--kol", default="mod_demo")
    a = ap.parse_args()

    json_yol = a.json or os.path.splitext(a.ham_video)[0] + ".jsonl"
    with open(json_yol) as f:
        kayitlar = [json.loads(satir) for satir in f if satir.strip()]

    cap = cv2.VideoCapture(a.ham_video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    durum_dizisi = [r.get("durum") for r in kayitlar]
    irtifa_dizisi = [r.get("irtifa") for r in kayitlar]
    olaylar = _demo_olaylar_cikar(kayitlar, fps)
    serit = gorsel_uret.demo_klip_serit_hazirla(durum_dizisi, irtifa_dizisi, W)
    odak_px = gorsel_uret.demo_odak_px(W)

    senaryo = os.path.splitext(os.path.basename(a.ham_video))[0]
    dizin = os.path.join(gorsel_uret.KOK, a.deney)
    os.makedirs(dizin, exist_ok=True)
    cikti_yol = os.path.join(dizin, _dosya_govdesi(a.deney, senaryo, a.kol, False) + ".mp4")
    vw = cv2.VideoWriter(cikti_yol, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))

    n, tespit_sayisi = 0, 0
    for rec in kayitlar:
        ok, img = cap.read()
        if not ok:
            break
        if rec.get("kutu") is not None:
            tespit_sayisi += 1
        vw.write(gorsel_uret.demo_hud_kare_ciz(
            img, rec, n, tespit_sayisi, fps, serit, olaylar, odak_px))
        n += 1
    cap.release()
    vw.release()
    print(f"HUD'lu video: {cikti_yol}  ({n} kare)")


if __name__ == "__main__":
    main()
