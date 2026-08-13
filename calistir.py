"""Tek senaryoyu kosar, aciklamali video ve metrik uretir.

Kullanim:
    python3 calistir.py test1
    python3 calistir.py test6 --video cikti/test6.mp4
    python3 calistir.py --hepsi
"""
import argparse
import os
import sys
import time

import cv2
import numpy as np

from sim.senaryolar import TUM_TESTLER
from takip.izleyici import ARAMA, KAYIP, KILITLI, SUPHELI, HedefTakip

RENK = {KILITLI: (0, 255, 255), SUPHELI: (0, 165, 255), ARAMA: (0, 80, 255), KAYIP: (0, 0, 255)}


def iou(a, b):
    if a is None or b is None:
        return 0.0
    ax0, ay0, ax1, ay1 = a[0], a[1], a[0] + a[2], a[1] + a[3]
    bx0, by0, bx1, by1 = b[0], b[1], b[0] + b[2], b[1] + b[3]
    ix = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    iy = max(0.0, min(ay1, by1) - max(ay0, by0))
    kes = ix * iy
    birlesim = a[2] * a[3] + b[2] * b[3] - kes
    return float(kes / birlesim) if birlesim > 0 else 0.0


def _kutu_ciz(img, kutu, renk, kalinlik=1):
    if kutu is None:
        return
    x, y, w, h = [int(round(v)) for v in kutu]
    cv2.rectangle(img, (x, y), (x + w, y + h), renk, kalinlik)


def kos(sen, video=None, isinma=6, sessiz=False, yap_takipci=None):
    """Senaryoyu bastan sona kosar. Doner: metrik sozlugu."""
    sahne, hedef = sen.sahne, sen.hedef
    tak = (yap_takipci or HedefTakip)()
    yaz = None
    if video:
        os.makedirs(os.path.dirname(video) or ".", exist_ok=True)
        yaz = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*"mp4v"),
                              int(1 / sen.dt), (sahne.cam.w, sahne.cam.h))

    kayit = []
    id_switch = 0
    onceki_uzerinde = 0
    kilitlendi_mi = False
    ilk_tespit_kare = None
    kurtarmalar = []
    kayip_basi = None
    sureler = []

    for k in range(sen.kare):
        sen.kamera_fn(sahne, k, sen.dt)
        sahne.step(sen.dt)
        img = sahne.render()
        gt = sahne.gt_box(hedef)
        gorunur = sahne.visible(hedef)

        # ---- ISINMA: hareket tespiti ile aday listesi olustur, hedefi sec ----
        if not kilitlendi_mi:
            adaylar = tak.tarama(img)
            if k >= isinma and adaylar:
                gc = np.array([gt[0] + gt[2] / 2, gt[1] + gt[3] / 2], np.float32)
                # "kullanici listeden hedefi secti" -> GT'ye en yakin aday
                en = min(adaylar, key=lambda a: np.linalg.norm(a["merkez"] - gc))
                if np.linalg.norm(en["merkez"] - gc) < max(8.0, 0.8 * max(gt[2], gt[3])):
                    kutu = en["kutu"].copy()
                    kutu[2:] = np.maximum(kutu[2:] - 2.0, 4.0)  # dilate telafisi
                    kutu[:2] = en["merkez"] - kutu[2:] / 2
                    tak.kilitle(img, kutu)   # DIKKAT: GT kutusu degil, TESPIT kutusu
                    kilitlendi_mi = True
                    ilk_tespit_kare = k
            sonuc = {"kutu": tak.kutu, "durum": tak.durum, "psr": 0.0, "sure": {}}
            if yaz is not None:
                _ciz(img, sahne, hedef, gt, sonuc, k, adaylar, tarama=True)
                yaz.write(img)
            continue

        # ---- TAKIP ----
        sonuc = tak.guncelle(img)
        sureler.append(sonuc["sure"]["toplam"])
        o = iou(sonuc["kutu"], gt) if gorunur else np.nan
        # merkez hatasi: kucuk hedefte IoU 1 px hatada cokerken bu adil kalir
        if gorunur and sonuc["kutu"] is not None:
            tk, tg = sonuc["kutu"], gt
            mh = float(np.hypot(tk[0] + tk[2] / 2 - (tg[0] + tg[2] / 2),
                                tk[1] + tk[3] / 2 - (tg[1] + tg[3] / 2)))
        else:
            mh = np.nan

        # ID switch: takip kutusu BASKA bir aracin uzerine gecti mi?
        uzerinde = 0
        if sonuc["kutu"] is not None:
            en_iyi_o, en_iyi_i = 0.0, 0
            for i, v in enumerate(sahne.vehicles):
                oo = iou(sonuc["kutu"], sahne.gt_box(v))
                if oo > en_iyi_o:
                    en_iyi_o, en_iyi_i = oo, i
            uzerinde = en_iyi_i if en_iyi_o > 0.2 else -1
        if uzerinde >= 0 and onceki_uzerinde == sen.hedef_idx and uzerinde != sen.hedef_idx:
            id_switch += 1
        if uzerinde >= 0:
            onceki_uzerinde = uzerinde

        # kurtarma suresi: kilit koptuktan sonra kac karede geri geldi
        kilit = sonuc["durum"] == KILITLI and (not gorunur or o > 0.2)
        if not kilit and kayip_basi is None:
            kayip_basi = k
        elif kilit and kayip_basi is not None:
            kurtarmalar.append(k - kayip_basi)
            kayip_basi = None

        kayit.append({"k": k, "iou": o, "durum": sonuc["durum"], "psr": sonuc["psr"],
                      "gorunur": gorunur, "gt_w": gt[2], "gt_h": gt[3], "merkez_hata": mh,
                      "alt": sahne.cam.alt, "uzerinde": uzerinde})

        if yaz is not None:
            _ciz(img, sahne, hedef, gt, sonuc, k, tak.son_adaylar, o=o)
            yaz.write(img)

    if yaz is not None:
        yaz.release()

    gorunur_kayit = [r for r in kayit if r["gorunur"]]
    ious = np.array([r["iou"] for r in gorunur_kayit], np.float32) if gorunur_kayit else np.zeros(1)
    mhs = np.array([r["merkez_hata"] for r in gorunur_kayit], np.float32) if gorunur_kayit \
        else np.array([np.nan])
    kosegen = np.array([np.hypot(r["gt_w"], r["gt_h"]) for r in gorunur_kayit], np.float32) \
        if gorunur_kayit else np.array([1.0])
    m = {
        "senaryo": sen.ad,
        "kare": len(kayit),
        "ilk_tespit_kare": ilk_tespit_kare,
        "ort_iou": float(np.nanmean(ious)),
        "basari@0.5": float(np.mean(ious > 0.5)),
        "basari@0.3": float(np.mean(ious > 0.3)),
        # hassasiyet: merkez hatasi hedef kosegeninin yarisindan kucuk mu
        "hassasiyet": float(np.mean(np.nan_to_num(mhs, nan=1e9) < np.maximum(4.0, 0.5 * kosegen))),
        "merkez_hata": float(np.nanmedian(mhs)) if np.isfinite(mhs).any() else float("nan"),
        "kilit_orani": float(np.mean([r["durum"] == KILITLI for r in kayit])) if kayit else 0.0,
        "id_switch": id_switch,
        "kurtarma_ort": float(np.mean(kurtarmalar)) if kurtarmalar else 0.0,
        "kurtarma_max": int(max(kurtarmalar)) if kurtarmalar else 0,
        "kesinti": len(kurtarmalar),
        "fps": float(1000.0 / np.mean(sureler)) if sureler else 0.0,
        "ms_kare": float(np.mean(sureler)) if sureler else 0.0,
    }
    m["_kayit"] = kayit
    if not sessiz:
        print(f"  {sen.ad:18s} IoU {m['ort_iou']:.3f} | @0.5 {m['basari@0.5']:.1%} "
              f"| kilit {m['kilit_orani']:.1%} | IDsw {id_switch} | {m['fps']:.0f} FPS")
    return m


def _ciz(img, sahne, hedef, gt, sonuc, k, adaylar=None, o=None, tarama=False):
    for v in sahne.vehicles:
        if v is not hedef:
            _kutu_ciz(img, sahne.gt_box(v), (150, 150, 150), 1)
    _kutu_ciz(img, gt, (0, 255, 0), 1)
    d = sonuc["durum"]
    if tarama:
        for a in (adaylar or []):
            _kutu_ciz(img, a["kutu"], (255, 120, 0), 1)
        cv2.putText(img, f"TARAMA - aday: {len(adaylar or [])}", (8, 18), 0, 0.5, (255, 160, 0), 1)
    else:
        if d in (ARAMA, KAYIP):
            for a in (adaylar or []):
                _kutu_ciz(img, a["kutu"], (255, 120, 0), 1)
        _kutu_ciz(img, sonuc["kutu"], RENK.get(d, (0, 0, 255)), 2)
        t1 = f"{d}  PSR {sonuc['psr']:.1f}  IoU {o:.2f}" if o == o else f"{d}  PSR {sonuc['psr']:.1f}"
        cv2.putText(img, t1, (8, 18), 0, 0.5, RENK.get(d, (0, 0, 255)), 1)
    cv2.putText(img, f"kare {k}  hedef {gt[2]:.0f}x{gt[3]:.0f} px  irtifa {sahne.cam.alt:.0f} m",
                (8, sahne.cam.h - 10), 0, 0.45, (255, 255, 255), 1)
    if not tarama and sonuc["sure"]:
        s = sonuc["sure"]
        cv2.putText(img, f"{s['toplam']:.1f} ms (ego {s['ego']:.1f} | mosse {s['mosse']:.1f} "
                         f"| tespit {s['tespit']:.1f})", (8, 36), 0, 0.4, (200, 200, 200), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("test", nargs="?", default="test1")
    ap.add_argument("--video", default=None)
    ap.add_argument("--hepsi", action="store_true")
    a = ap.parse_args()

    testler = list(TUM_TESTLER) if a.hepsi else [a.test]
    for ad in testler:
        if ad not in TUM_TESTLER:
            print(f"bilinmeyen test: {ad}  (secenekler: {', '.join(TUM_TESTLER)})")
            sys.exit(1)
        sen = TUM_TESTLER[ad]()
        vid = a.video if (a.video and not a.hepsi) else f"cikti/{ad}.mp4"
        t = time.time()
        kos(sen, video=vid)
        print(f"    -> {vid}  ({time.time() - t:.1f} s)")


if __name__ == "__main__":
    main()
