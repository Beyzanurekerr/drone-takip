"""A9 Asama 1b - TEK DEGISKEN A/B: _boyut_tazele'nin MERKEZE yazmasi.

Kol A (kontrol) : mevcut davranis.
Kol B           : YALNIZCA `_boyut_tazele` kaynakli kf.duzelt(...) atlanir.
                  Boyut guncellemesi (self.boyut, self.boyut_olculen) AYNEN devam eder.
                  Baska hicbir sey degismez.

takip/ DEGISMEZ: mudahale Asama 1'in Kalman sarmalayicisinda yapilir; sarmalayici
cagiran fonksiyonu zaten yigindan taniyor.

Kabul olcutu A/B KOSULMADAN ONCE yazildi:
docs/architecture/A9_TAKIPCI_MERKEZ_RECOVERY.md -> "ASAMA 1b - KABUL OLCUTU"
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
A7, B = A9.A7, A9.B
from calistir import iou                                   # noqa: E402
from takip.izleyici import KILITLI, HedefTakip             # noqa: E402
from veri.visdrone import VisDroneVidKaynak                # noqa: E402

SENSOR, N_KARE = A9.SENSOR, A9.N_KARE
SEVIYELER = [30, 20, 15, 10, 8]
SEVIYE_AD = A9.SEVIYE_AD
KOPAN = ["uav0000117_02622_v/23", "uav0000268_05773_v/31", "uav0000339_00001_v/49"]
DIZILER = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31),
           ("uav0000339_00001_v", 49), ("uav0000137_00458_v", 12),
           ("uav0000305_00000_v", 5), ("uav0000182_00000_v", 127)]


class ABKalman(A9.KayitKalman):
    """Asama 1 sarmalayicisi + tek mudahale: secilen kaynaktan gelen duzelt yutulur."""
    _OZEL = A9.KayitKalman._OZEL + ("_atla",)

    def duzelt(self, z, r_carpan=1.0):
        atla = object.__getattribute__(self, "_atla")
        cagiran = sys._getframe(1).f_code.co_name
        if atla and cagiran in atla:
            kf = object.__getattribute__(self, "_kf")
            once = kf.konum
            self._kaydet("duzelt_ATLANDI", once, z=z, r_carpan=r_carpan)
            return
        super().duzelt(z, r_carpan)


def ab_olc(dizi, atla):
    """Bir kolu bir dizide kosar. GT yalniz OLCUM icin okunur."""
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    log = []
    sar = ABKalman(tak.kf, log)
    object.__setattr__(sar, "_tak", tak)
    object.__setattr__(sar, "_atla", atla)
    tak.kf = sar

    hata_l, iou_l, psr_l, kilit_l = [], [], [], []
    kabul = red = atlandi = 0
    guvenli_yanlis = 0                     # durum==KILITLI ama IoU<0.2
    kopus_kare, ard = None, 0
    for t in range(1, len(dizi)):
        img, gt = dizi[t]
        gc = gt[:2] + gt[2:] / 2.0
        gL = float(max(gt[2], gt[3]))
        object.__setattr__(sar, "_gt", gc.astype(np.float64))
        n0 = len(log)
        s = tak.guncelle(img)
        hata = float(np.linalg.norm(tak.kf.konum - gc))
        o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0
        hata_l.append(hata); iou_l.append(o); psr_l.append(float(s["psr"]))
        kilit_l.append(1 if (s["durum"] == KILITLI and o > 0.2) else 0)
        if s["durum"] == KILITLI and o < 0.2:
            guvenli_yanlis += 1
        for e in log[n0:]:
            if e["kaynak"] == "_takip_adimi":
                if e["tip"] == "duzelt":
                    kabul += 1
                elif e["tip"] == "sondur":
                    red += 1
            if e["tip"] == "duzelt_ATLANDI":
                atlandi += 1
        if hata > A9.KOPUS_KAT * gL:
            ard += 1
            if ard >= A9.KOPUS_SABIR and kopus_kare is None:
                kopus_kare = t - A9.KOPUS_SABIR + 1
        else:
            ard = 0
    return {"kare": len(hata_l),
            "merkez_hata_p50": A9.p(hata_l, 50), "merkez_hata_p95": A9.p(hata_l, 95),
            "ort_iou": A9.ort(iou_l), "kilit_orani": A9.ort(kilit_l),
            "guvenli_yanlis_kare": guvenli_yanlis,
            "psr_p50": A9.p(psr_l, 50),
            "dcf_kabul": kabul, "dcf_red": red, "boyut_merkez_atlandi": atlandi,
            "kopus_karesi": kopus_kare}


def topla(dizi, tid, n):
    k = VisDroneVidKaynak("data/datasets/visdrone_vid", dizi, track_id=tid)
    out = []
    for kare in k:
        if kare.gt is not None and kare.gorunur:
            out.append((kare.goruntu, np.asarray(kare.gt, np.float32), [],
                        kare.genislik, kare.yukseklik))
        if len(out) >= n:
            break
    return out


def main():
    cikti = {"asama": "A9 Asama 1b - tek degisken A/B: _boyut_tazele merkez yazmasi",
             "tek_degisken": "izleyici.py:567 kf.duzelt(yeni_c, r_carpan=1.0)",
             "kol_A": "kontrol (mevcut davranis)",
             "kol_B": "_boyut_tazele kaynakli duzelt ATLANIR; boyut guncellemesi devam eder",
             "takip_degismedi": True,
             "acik_cevrim_uyarisi": "Sonuc bir UST SINIRDIR; kapali cevrimde ayrica sinanmali.",
             "kabul_olcutu": "A/B'den ONCE yazildi (rapor: ASAMA 1b - KABUL OLCUTU)",
             "diziler": {}}
    for dizi_ad, tid in DIZILER:
        ad = f"{dizi_ad}/{tid}"
        kareler = topla(dizi_ad, tid, N_KARE)
        W, H = kareler[0][3], kareler[0][4]
        hucre, _ = B.arkaplan_hucresi(kareler, W, H, *SENSOR)
        rol = "KOPAN" if ad in KOPAN else "saglam"
        dd = {"rol": rol, "seviyeler": {}}
        print(f"\n--- {ad}  [{rol}] ---", flush=True)
        for L in SEVIYELER:
            d, s = A7.sensor_dizi(kareler, hucre, L, N_KARE)
            if len(d) < 10:
                dd["seviyeler"][SEVIYE_AD[L]] = {"not": "dizi kisa"}
                continue
            A = ab_olc(d, atla=None)
            Bk = ab_olc(d, atla={"_boyut_tazele"})
            dd["seviyeler"][SEVIYE_AD[L]] = {"A_kontrol": A, "B_merkez_kapali": Bk}
            dp95 = ((Bk["merkez_hata_p95"] - A["merkez_hata_p95"])
                    / max(A["merkez_hata_p95"], 1e-9) * 100.0)
            print(f"  {SEVIYE_AD[L]:6s} hata p95  A={A['merkez_hata_p95']:>8.2f} "
                  f"B={Bk['merkez_hata_p95']:>8.2f} ({dp95:+7.1f}%) | "
                  f"IoU A={A['ort_iou']} B={Bk['ort_iou']} | "
                  f"kopus A={str(A['kopus_karesi']):>4} B={str(Bk['kopus_karesi']):>4} | "
                  f"guv.yanlis A={A['guvenli_yanlis_kare']:>2} B={Bk['guvenli_yanlis_kare']:>2} | "
                  f"atlanan={Bk['boyut_merkez_atlandi']}", flush=True)
        cikti["diziler"][ad] = dd
    yol = sys.argv[1] if len(sys.argv) > 1 else "cikti/a9b_ab_boyut_merkez.json"
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
