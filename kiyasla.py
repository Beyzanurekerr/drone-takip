"""Tam degerlendirme: 7 test + minimum boyut egrisi + zaman profili + RAPOR.md

    python3 kiyasla.py             -> olc, tabloyu bas, RAPOR.md yaz
    python3 kiyasla.py --video     -> ayrica cikti/*.mp4 uret
"""
import argparse
import time

import numpy as np

from calistir import kos
from sim.senaryolar import TUM_TESTLER
from takip.izleyici import HedefTakip

# Pi Zero 2 W (4xA53 1GHz, NEON) bu gelistirme makinesine gore kabaca bu kadar
# yavas. Kesin sayi degil; gercek olcum icin cihazda kosulmali.
PI_ZERO2_KAT = 12.0
PI_ZERO1_KAT = 45.0


def boyut_egrisi(kayit, kenarlar=(60, 45, 35, 28, 22, 18, 15, 12, 10, 8, 6, 4, 0)):
    """Hedef genisligine gore basari: sistemin DURUST alt siniri."""
    satir = []
    for i in range(len(kenarlar) - 1):
        ust, alt = kenarlar[i], kenarlar[i + 1]
        kova = [r for r in kayit if r["gorunur"] and alt <= r["gt_w"] < ust]
        if len(kova) < 5:
            continue
        iou = np.array([r["iou"] for r in kova])
        mh = np.array([r["merkez_hata"] for r in kova])
        kos_ = np.array([np.hypot(r["gt_w"], r["gt_h"]) for r in kova])
        satir.append({
            "aralik": f"{alt:.0f}-{ust:.0f}",
            "ort_px": float(np.mean([r["gt_w"] for r in kova])),
            "ort_py": float(np.mean([r["gt_h"] for r in kova])),
            "n": len(kova),
            "iou": float(np.mean(iou)),
            "hassasiyet": float(np.mean(np.nan_to_num(mh, nan=1e9) < np.maximum(4.0, 0.5 * kos_))),
            "merkez_hata": float(np.nanmedian(mh)),
            "kilit": float(np.mean([r["durum"] == "KILITLI" for r in kova])),
        })
    return satir


def hukum(s):
    if s["hassasiyet"] > 0.95 and s["merkez_hata"] < 3:
        return "BASARILI"
    if s["hassasiyet"] > 0.75:
        return "KARARSIZ"
    return "KAYIP"


def profil(n=200):
    """Asama basina ms. Tek surecte olculur (paralel kosuda sayilar sisiyor)."""
    sen = TUM_TESTLER["test4"]()
    tak = HedefTakip()
    kilit = False
    top = {}
    say = 0
    for k in range(n):
        sen.kamera_fn(sen.sahne, k, sen.dt)
        sen.sahne.step(sen.dt)
        img = sen.sahne.render()
        if not kilit:
            ad = tak.tarama(img)
            if k >= 6 and ad:
                gt = sen.sahne.gt_box(sen.hedef)
                gc = np.array([gt[0] + gt[2] / 2, gt[1] + gt[3] / 2], np.float32)
                en = min(ad, key=lambda a: np.linalg.norm(a["merkez"] - gc))
                b = en["kutu"].copy()
                b[2:] = np.maximum(b[2:] - 2, 4)
                b[:2] = en["merkez"] - b[2:] / 2
                tak.kilitle(img, b)
                kilit = True
            continue
        r = tak.guncelle(img)
        for kk, vv in r["sure"].items():
            top[kk] = top.get(kk, 0.0) + vv
        say += 1
    return {kk: vv / max(1, say) for kk, vv in top.items()}, say


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", action="store_true")
    a = ap.parse_args()

    print("=" * 96)
    print("DRONE HEDEF TAKIP - DEGERLENDIRME")
    print("=" * 96)
    sonuc = {}
    t0 = time.time()
    for ad in TUM_TESTLER:
        sen = TUM_TESTLER[ad]()
        sonuc[ad] = kos(sen, video=f"cikti/{ad}.mp4" if a.video else None, sessiz=True)
        sonuc[ad]["aciklama"] = sen.aciklama
        sonuc[ad]["amac"] = sen.amac

    bas = (f"{'test':18s} {'IoU':>6s} {'@0.5':>7s} {'@0.3':>7s} {'hassas':>7s} "
           f"{'mrkz.px':>8s} {'kilit':>7s} {'IDsw':>5s} {'kurtarma':>9s} {'FPS':>6s}")
    print("\n" + bas)
    print("-" * len(bas))
    for ad, m in sonuc.items():
        print(f"{m['senaryo']:18s} {m['ort_iou']:6.3f} {m['basari@0.5']:7.1%} {m['basari@0.3']:7.1%} "
              f"{m['hassasiyet']:7.1%} {m['merkez_hata']:8.2f} {m['kilit_orani']:7.1%} "
              f"{m['id_switch']:5d} {m['kurtarma_ort']:6.0f}kr {m['fps']:6.0f}")
    ort = {k: np.mean([m[k] for m in sonuc.values()])
           for k in ["ort_iou", "basari@0.5", "basari@0.3", "hassasiyet", "kilit_orani", "fps"]}
    print("-" * len(bas))
    print(f"{'ORTALAMA':18s} {ort['ort_iou']:6.3f} {ort['basari@0.5']:7.1%} {ort['basari@0.3']:7.1%} "
          f"{ort['hassasiyet']:7.1%} {'':8s} {ort['kilit_orani']:7.1%} "
          f"{sum(m['id_switch'] for m in sonuc.values()):5d} {'':9s} {ort['fps']:6.0f}")

    # --- TEST 3: minimum takip boyutu (cok tohumlu, istatistiksel) ---
    from sim.senaryolar import test3_cok_kucuk
    ham = list(sonuc["test3"]["_kayit"])
    for sd in (21, 99):
        ham += kos(test3_cok_kucuk(seed=sd), sessiz=True)["_kayit"]
    egri = boyut_egrisi(ham)
    print("\n" + "=" * 96)
    print("TEST 3 - MINIMUM TAKIP BOYUTU (irtifa rampasi, 3 gurultu tohumu)")
    print("=" * 96)
    print(f"{'hedef boyutu':>16s} {'kare':>6s} {'IoU':>6s} {'hassasiyet':>11s} "
          f"{'merkez hata':>12s} {'kilit':>7s}   hukum")
    for s in egri:
        print(f"{s['ort_px']:7.1f}x{s['ort_py']:<8.1f} {s['n']:6d} {s['iou']:6.3f} "
              f"{s['hassasiyet']:11.1%} {s['merkez_hata']:10.2f}px {s['kilit']:7.1%}   {hukum(s)}")

    # --- zaman profili ---
    pr, n = profil()
    print("\n" + "=" * 96)
    print(f"ZAMAN PROFILI (640x480, {n} kare, tek surec)")
    print("=" * 96)
    for k in ["ego", "mosse", "tespit", "toplam"]:
        if k in pr:
            etiket = {"ego": "ego-motion (LK+RANSAC)", "mosse": "korelasyon cekirdegi",
                      "tespit": "tespit / kutu rafine", "toplam": "TOPLAM"}[k]
            print(f"  {etiket:28s} {pr[k]:6.2f} ms  ({pr[k] / pr['toplam']:5.1%})")
    fps = 1000.0 / pr["toplam"]
    print(f"\n  bu makine        : {pr['toplam']:6.2f} ms/kare -> {fps:6.0f} FPS")
    print(f"  Pi Zero 2 W tahmin: {pr['toplam'] * PI_ZERO2_KAT:6.2f} ms/kare -> "
          f"{fps / PI_ZERO2_KAT:6.1f} FPS   (x{PI_ZERO2_KAT:.0f} kaba katsayi)")
    print(f"  Pi Zero 1  tahmin : {pr['toplam'] * PI_ZERO1_KAT:6.2f} ms/kare -> "
          f"{fps / PI_ZERO1_KAT:6.1f} FPS   (x{PI_ZERO1_KAT:.0f} kaba katsayi)")
    print("  NOT: katsayilar tahmindir, gercek sayi icin cihazda olculmeli.")
    print(f"\n  320x240 girisde beklenen kazanc: ~2.5-3x (ego ve tespit alan ile olcekleniyor)")
    print(f"\ntoplam sure {time.time() - t0:.1f} s")

    rapor(sonuc, egri, pr, fps)
    print("-> RAPOR.md yazildi")


def rapor(sonuc, egri, pr, fps):
    L = ["# Drone Hedef Takip - Sonuc Raporu", ""]
    L += ["Sentetik havadan goruntu simulasyonu uzerinde, her kare icin kusursuz",
          "ground-truth ile olculmustur. Hedef ilk karede ELLE degil, sistemin kendi",
          "hareket tespiti listesinden secilir (gercek kullanim boyle).", ""]
    L += ["## Mimari", "",
          "```", "kare",
          " |- ego-motion  : seyrek LK + RANSAC benzerlik donusumu",
          " |                (arama daraltma + hareketli cisim ayirma + olcek)",
          " |- takip       : MOSSE korelasyon filtresi + Kalman (sabit hiz)",
          " |                olcek ego-motion'dan bedava gelir",
          " |- capa        : yerel renk kontrastiyla kutu rafinesi (surukleme onleme)",
          " |- yeniden     : ego-telafili kare farki -> aday lekeler",
          " |  tespit        -> renk + sablon + boyut imzasiyla eslestirme",
          "```", ""]
    L += ["## Test sonuclari", "",
          "| test | amac | IoU | @0.5 | hassasiyet | merkez hata | kilit | ID switch |",
          "|---|---|---|---|---|---|---|---|"]
    for ad, m in sonuc.items():
        L.append(f"| {m['senaryo']} | {m['amac']} | {m['ort_iou']:.3f} | {m['basari@0.5']:.0%} | "
                 f"{m['hassasiyet']:.0%} | {m['merkez_hata']:.2f} px | {m['kilit_orani']:.0%} | "
                 f"{m['id_switch']} |")
    L += ["", "**hassasiyet** = merkez hatasi hedef kosegeninin yarisindan kucuk olan kare orani.",
          "Kucuk hedefte IoU 1 piksellik hatada cokerken bu olcu adil kalir.", ""]
    L += ["## Test 3 - minimum takip edilebilen hedef boyutu", "",
          "| hedef boyutu (px) | kare | IoU | hassasiyet | merkez hata | hukum |",
          "|---|---|---|---|---|---|"]
    for s in egri:
        L.append(f"| {s['ort_px']:.1f} x {s['ort_py']:.1f} | {s['n']} | {s['iou']:.3f} | "
                 f"{s['hassasiyet']:.0%} | {s['merkez_hata']:.2f} px | {hukum(s)} |")
    L += ["", "## Zaman profili (640x480)", "",
          "| asama | ms | pay |", "|---|---|---|"]
    for k, e in [("ego", "ego-motion"), ("mosse", "korelasyon cekirdegi"),
                 ("tespit", "tespit / kutu rafine"), ("toplam", "TOPLAM")]:
        if k in pr:
            L.append(f"| {e} | {pr[k]:.2f} | {pr[k] / pr['toplam']:.0%} |")
    L += ["", f"- bu makine: **{fps:.0f} FPS**",
          f"- Pi Zero 2 W kaba tahmin: **{fps / PI_ZERO2_KAT:.1f} FPS** (x{PI_ZERO2_KAT:.0f})",
          f"- Pi Zero 1 kaba tahmin: **{fps / PI_ZERO1_KAT:.1f} FPS** (x{PI_ZERO1_KAT:.0f})",
          "", "Katsayilar tahmindir; kesin sonuc icin cihazda olculmelidir.", ""]
    with open("RAPOR.md", "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
