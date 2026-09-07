"""DEMO offline HUD uretimi (Adim 4 duzeltmesi - THREAD KALKTI).

`main.py --mod demo --kaydet X.mp4` artik HAM kare + `X.jsonl` (kare basina
durum) yazar. Bu script ikisini birlestirip HUD'lu videoyu OFFLINE uretir -
kendi cizim kodu YOK, `gazebo/gorsel_uret.py:video_uret()` cagirir (talimat:
"her deney BUNU cagirir, kendi cizim kodu yazmaz").

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
from gazebo.gorsel_uret import _dosya_govdesi, _kare_ciz  # noqa: E402

# 2026-09-07 DUZELTME: `video_uret()` tum kareleri bellekte biriktirir
# (kaydet.py'nin OOM'una AYNI sinif hata, 900 karede ~8GB). Burada onun
# YERINE gecilmez - `_kare_ciz`'i (AYNI cizim, tek kare) STREAMING
# cagirip diske hemen yaziyoruz, boylece bellek O(1) kalir.


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

    senaryo = os.path.splitext(os.path.basename(a.ham_video))[0]
    dizin = os.path.join(gorsel_uret.KOK, a.deney)
    os.makedirs(dizin, exist_ok=True)
    cikti_yol = os.path.join(dizin, _dosya_govdesi(a.deney, senaryo, a.kol, False) + ".mp4")
    vw = cv2.VideoWriter(cikti_yol, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))

    n = 0
    hafif_kayit = []      # img YOK - zaman_serisi_uret icin (bellek ucuz)
    for rec in kayitlar:
        ok, img = cap.read()
        if not ok:
            break
        kare_rec = {
            "sistem_kutu": rec.get("kutu"),
            "roi_kutu": rec.get("roi"),
            "gt": rec.get("gt"),
            "durum": rec.get("durum"),
            "mod": rec.get("komut"),      # KORUMA'da "YAKLAS" - HUD'da gorunur
            "iou": rec.get("iou"),
        }
        vw.write(_kare_ciz({**kare_rec, "img": img}, n, oracle=False))
        hafif_kayit.append(kare_rec)
        n += 1
    cap.release()
    vw.release()
    print(f"HUD'lu video: {cikti_yol}  ({n} kare)")

    seri = gorsel_uret.zaman_serisi_uret(a.deney, senaryo, a.kol, hafif_kayit)
    if seri:
        print(f"zaman serisi: {seri}")


if __name__ == "__main__":
    main()
