"""K-MOD/K1 - KOL 2 aday secim kurallari (acik cevrim, tek oturum).

Adaylar: `takip/tespit.py:HareketTespit.adaylar()` (hareket-fark blob'lari,
takip/ DEGISMEDI). Referans: ORACLE-tarzi Kalman - her karede GT ile
duzeltilir (`Kalman.duzelt`), boylece "mukemmel onceki kilit olsaydi
ongoru ne olurdu" sorusuna cevap verir (A9_3_2_SECIM_KURALI.md'nin
ORACLE/OPERASYONEL ayrimindaki ORACLE kolu).

S1  d_norm TEK BASINA (A9_3_2_SECIM_KURALI.md'deki d_norm birebir, a_norm/
    r_norm YOK - K-MOD talimati yalniz "Kalman ongorusune yakinlik" istiyor).
    Kapi d_norm<=1.0, argmin, gecen yoksa CEKIMSER.
S2  S1 + zamansal kalicilik: adayin hucresi (8 px izgara) son N=3 karenin
    >=k=2'sinde (bu kare dahil) baska bir adayda da gorulmus olmali.
S3  S2 + dedektor dogrulama: secilen adayin merkezinde R=80 ROI (A7/A8
    geometrisiyle AYNI, `gazebo.y1_ortak.roi_dortx_tespit`), A6 modeli.
    Dedektor onaylamazsa CEKIMSER'e duser (S2'nin secimi geri alinir).

OLCUM: dogru secim (IoU>=0.5), yanlis secim (IoU<0.2), cekimser (aday VAR
ama hicbiri kapidan gecmedi/dogrulanmadi), kanit-yok (hic aday YOK).
Kova: gt_L = max(GT w,h). Kapi: 8x5 kovasinda dogru>=0.8, yanlis<=0.05.

Kosum: python3 -m gazebo.tani_kmod_k1
Cikti: cikti/kmod_k1.json
"""
import json
import os
import sys
from collections import deque

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from calistir import iou                                    # noqa: E402
from gazebo.a11_ortak import kareleri_topla                  # noqa: E402
from gazebo.y1_ortak import (MODELLER, roi_dortx_tespit,      # noqa: E402
                             yama_ici_mi, yolo_yukle)
import cv2                                                    # noqa: E402
from takip.egomotion import EgoMotion                          # noqa: E402
from takip.izleyici import Kalman                             # noqa: E402
from takip.tespit import HareketTespit, rafine_kutu            # noqa: E402

DOGRU_IOU, YANLIS_IOU = 0.5, 0.2
MAX_HIZ = Kalman.MAX_HIZ            # 35.0 px/kare, mevcut sabit
HUCRE_PX = 8.0                      # S2 kalicilik hucresi
S2_N, S2_K = 3, 2                   # son N karenin >=k'sinde gorulmeli
S3_R = 80                           # ROI genisligi (talimat: R=80)

KOVALAR = [(0, 10, "8x5"), (10, 15, "10x5_15x7"), (15, 20, "20x10"),
          (20, 25, "20_25"), (25, 1e9, "25_ustu")]
# DUZELTME (ilk kosumdan SONRA fark edildi): "8x5" (talimatin kapi kovasi)
# L=max(w,h)~8-9px'e denk dusuyor - Y1_A8_cok_kucuk BURAYA duser (0,10)
# araligi, ONCEKI adiyla "5x2_ve_alti" idi ve kapi kodu YANLIS ANAHTARLA
# ("8x5_10x5", 10-15px araligi - HICBIR senaryonun uretmedigi bos bir
# bant) ariyordu, n=0 veriyordu. Kovalar YENIDEN ADLANDIRILDI (sinirlar
# AYNI, yalniz etiket dogru); kapi artik doğru anahtari ("8x5") okuyor.


def kova_ad(L):
    for lo, hi, ad in KOVALAR:
        if lo <= L < hi:
            return ad
    return "?"


def _d_norm(aday_merkez, ref_merkez, ref_wh, dt):
    d = float(np.linalg.norm(np.asarray(aday_merkez, float) - np.asarray(ref_merkez, float)))
    d_bek = MAX_HIZ * float(dt) + max(float(ref_wh[0]), float(ref_wh[1])) / 2.0
    return d / max(d_bek, 1e-6)


def _hucre(merkez):
    return (int(merkez[0] // HUCRE_PX), int(merkez[1] // HUCRE_PX))


def _s1(adaylar, ref_merkez, ref_wh, dt):
    puanli = [(a, _d_norm(a["merkez"], ref_merkez, ref_wh, dt)) for a in adaylar]
    gecen = [(a, dn) for a, dn in puanli if dn <= 1.0]
    if not gecen:
        return None, puanli
    return min(gecen, key=lambda t: t[1])[0], puanli


def _s2(adaylar, ref_merkez, ref_wh, dt, hucre_gecmisi):
    """hucre_gecmisi: son (S2_N-1) karenin hucre kumeleri (bu kare HARIC)."""
    secilen, puanli = _s1(adaylar, ref_merkez, ref_wh, dt)
    if secilen is None:
        return None
    hid = _hucre(secilen["merkez"])
    bu_kare_hucreler = {_hucre(a["merkez"]) for a in adaylar}
    gecmis_sayim = sum(1 for kume in hucre_gecmisi if hid in kume)
    # bu kare dahil: kendi karesindeki varligi da sayilir (S2_K esigi buna gore)
    toplam = gecmis_sayim + (1 if hid in bu_kare_hucreler else 0)
    return secilen if toplam >= S2_K else None


def _s3(secilen, model, siniflar, img):
    if secilen is None:
        return None
    kutular, guvenler, ms = roi_dortx_tespit(model, img, secilen["merkez"], siniflar, R=S3_R)
    return secilen if len(kutular) > 0 else None


def kol_olc(kareler, kol, model=None, siniflar=None):
    """kol in {'S1','S2','S3'}. Doner: kayitlar (liste), her biri
    {gt_L, sonuc: 'dogru'|'yanlis'|'cekimser'|'kanit_yok', n_aday}."""
    tespit = HareketTespit()
    ego = EgoMotion()
    kalman = None
    hucre_gecmisi = deque(maxlen=S2_N - 1)
    kayitlar = []

    for i, (img, gt, satir) in enumerate(kareler):
        gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # GERCEK ego-motion (takip/egomotion.py, izleyici.py'nin KENDI
        # kullandigi mekanizma) - kamera BAZ_HIZ ile hedefi takip ettigi
        # icin BIRIM M kullanmak arka planin tamamini "hareket" sayardi.
        # GT kutusu (varsa) keypoint'lerden HARIC tutulur (izleyici.py'nin
        # `self.kutu if KILITLI else None` deseniyle AYNI ilke).
        M, _ego_guven = ego.guncelle(gri, gt if gt is not None else None)
        if gt is None:
            tespit.kare_ekle(gri, M)
            continue
        gt_c = gt[:2] + gt[2:] / 2.0
        gt_L = float(np.max(gt[2:]))

        if kalman is None:
            kalman = Kalman(gt_c[0], gt_c[1])
            ref_wh = gt[2:].copy()
        else:
            kalman.tahmin(M)

        adaylar, _ = tespit.adaylar(gri, M)

        if not adaylar:
            kayitlar.append({"gt_L": gt_L, "sonuc": "kanit_yok", "n_aday": 0})
        else:
            ref_merkez = kalman.konum
            dt = 1.0 / 30.0
            if kol == "S1":
                secilen, _ = _s1(adaylar, ref_merkez, ref_wh, dt)
            else:
                secilen = _s2(adaylar, ref_merkez, ref_wh, dt, hucre_gecmisi)

            # Ham hareket lekesi kutusu yerine RAFINE EDILMIS kutu -
            # `_arama_adimi`'nin (izleyici.py:528) yaptigi gibi. Boyut
            # ipucu Kalman-izlenen ref_wh'den (GT'den DEGIL - GT sizmasin).
            if secilen is not None:
                r = rafine_kutu(img, secilen["merkez"], ref_wh)
                if r is not None:
                    secilen = {**secilen, "kutu": r, "merkez": r[:2] + r[2:] / 2.0}

            if kol == "S3":
                secilen = _s3(secilen, model, siniflar, img)

            if secilen is None:
                kayitlar.append({"gt_L": gt_L, "sonuc": "cekimser", "n_aday": len(adaylar)})
            else:
                o = float(iou(secilen["kutu"], gt))
                sonuc = "dogru" if o >= DOGRU_IOU else ("yanlis" if o < YANLIS_IOU else "belirsiz")
                kayitlar.append({"gt_L": gt_L, "sonuc": sonuc, "n_aday": len(adaylar), "iou": round(o, 4)})

        hucre_gecmisi.append({_hucre(a["merkez"]) for a in adaylar})
        kalman.duzelt(gt_c)         # ORACLE: mukemmel duzeltme (bir sonraki karenin oncoru icin)
        ref_wh = gt[2:].copy()
        tespit.kare_ekle(gri, M)

    return kayitlar


def kova_tablosu(kayitlar):
    grup = {}
    for k in kayitlar:
        ad = kova_ad(k["gt_L"])
        grup.setdefault(ad, {"dogru": 0, "yanlis": 0, "cekimser": 0, "kanit_yok": 0,
                             "belirsiz": 0, "n": 0})
        grup[ad][k["sonuc"]] += 1
        grup[ad]["n"] += 1
    out = {}
    for ad, g in grup.items():
        n = g["n"]
        out[ad] = {**g, "dogru_oran": round(g["dogru"] / n, 4) if n else None,
                  "yanlis_oran": round(g["yanlis"] / n, 4) if n else None}
    return out


def main():
    print("=== K-MOD/K1: aday secim kurallari (S1/S2/S3) ===")
    agirlik = yolo_yukle(MODELLER["A6"]["agirlik"])
    siniflar = MODELLER["A6"]["siniflar"]

    sonuc = {"senaryolar": {}}
    for ad in ["Y1_A7_kucuk", "Y1_A8_cok_kucuk"]:
        print(f"\n--- {ad} ---")
        kareler, W, H, fx, fy, cx, cy = kareleri_topla(ad)
        ic_sayisi = sum(1 for _, gt, satir in kareler if gt is not None
                        and yama_ici_mi(satir["kam_x"], satir["kam_y"], satir["kam_z"], W, H, fx))
        print(f"  {len(kareler)} kare, yama-ici (GT gorunur): {ic_sayisi}")
        sonuc["senaryolar"][ad] = {"n_kare": len(kareler), "yama_ici_gt": ic_sayisi, "kollar": {}}
        for kol in ["S1", "S2", "S3"]:
            kayitlar = kol_olc(kareler, kol, agirlik, siniflar)
            tablo = kova_tablosu(kayitlar)
            sonuc["senaryolar"][ad]["kollar"][kol] = tablo
            print(f"  {kol}: " + ", ".join(f"{k}(n={v['n']}) dogru={v['dogru_oran']} "
                                          f"yanlis={v['yanlis_oran']}" for k, v in tablo.items()))

    # KAPI: 8x5 kovasinda dogru>=0.8, yanlis<=0.05 - her iki senaryonun
    # BIRLESTIRILMIS kovasinda (n arttirmak icin)
    print("\n=== KAPI: 8x5 kovasi, dogru>=0.8 yanlis<=0.05 ===")
    kapi = {}
    for kol in ["S1", "S2", "S3"]:
        toplam = {"dogru": 0, "yanlis": 0, "cekimser": 0, "kanit_yok": 0, "belirsiz": 0, "n": 0}
        for ad in sonuc["senaryolar"]:
            g = sonuc["senaryolar"][ad]["kollar"][kol].get("8x5")
            if g:
                for k in toplam:
                    toplam[k] += g.get(k, 0)
        n = toplam["n"]
        dogru_oran = round(toplam["dogru"] / n, 4) if n else None
        yanlis_oran = round(toplam["yanlis"] / n, 4) if n else None
        gecti = (dogru_oran is not None and dogru_oran >= 0.8 and yanlis_oran <= 0.05)
        kapi[kol] = {**toplam, "dogru_oran": dogru_oran, "yanlis_oran": yanlis_oran, "gecti": gecti}
        print(f"  {kol}: n={n} dogru={dogru_oran} yanlis={yanlis_oran} -> "
             f"{'GECTI' if gecti else 'KALDI'}")
    sonuc["kapi_8x5"] = kapi

    os.makedirs("cikti", exist_ok=True)
    with open("cikti/kmod_k1.json", "w") as f:
        json.dump(sonuc, f, indent=2, ensure_ascii=False)
    print("\nyazildi: cikti/kmod_k1.json")
    return sonuc


if __name__ == "__main__":
    main()
