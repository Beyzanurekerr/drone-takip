"""A9 - _boyut_tazele aday duzeltmeleri icin TEK DEGISKEN A/B kosum takimi.

Kollar (her biri TEK degisken, hepsi monkey-patch; takip/ DEGISMEZ):
  kontrol          : mevcut davranis
  ab1_rcarpan_6    : _boyut_tazele'nin merkez duzeltmesi r_carpan=1.0 -> 6.0
                     (6.0 yeni bir sabit DEGIL: izleyici.py:327'de "zayif olcum,
                      az guven" icin zaten kullanilan deger)
  ab2_bagimsiz_kapi: (A/B-2'de tanimlanacak)
  ab3_ayir         : (A/B-3'te tanimlanacak)

Kabul olcutu: docs/architecture/A9_KABUL_OLCUTU.md (A/B'lerden ONCE yazildi).

Her kol icin takipci SIFIRDAN kurulur -> baseline kendiliginden geri yuklenir.
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
SAGLAM = ["uav0000137_00458_v/12", "uav0000305_00000_v/5", "uav0000182_00000_v/127"]
KOPAN = ["uav0000117_02622_v/23", "uav0000268_05773_v/31", "uav0000339_00001_v/49"]
DIZILER = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31),
           ("uav0000339_00001_v", 49), ("uav0000137_00458_v", 12),
           ("uav0000305_00000_v", 5), ("uav0000182_00000_v", 127)]

KOLLAR = {
    "kontrol": {},
    "ab1_rcarpan_6": {"rcarpan": {"_boyut_tazele": 6.0}},
}


class ABKalman(A9.KayitKalman):
    """Asama 1 sarmalayicisi + kaynak bazli tek mudahale."""
    _OZEL = A9.KayitKalman._OZEL + ("_mud",)

    def duzelt(self, z, r_carpan=1.0):
        mud = object.__getattribute__(self, "_mud") or {}
        cagiran = sys._getframe(1).f_code.co_name
        if cagiran in (mud.get("atla") or ()):
            kf = object.__getattribute__(self, "_kf")
            self._kaydet("duzelt_ATLANDI", kf.konum, z=z, r_carpan=r_carpan)
            return
        yeni_r = (mud.get("rcarpan") or {}).get(cagiran)
        if yeni_r is not None:
            r_carpan = yeni_r
        super().duzelt(z, r_carpan)


def kol_olc(dizi, mud):
    """Bir kolu bir dizide kosar. GT yalniz OLCUM icin okunur, takipciye girmez."""
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    log = []
    sar = ABKalman(tak.kf, log)
    object.__setattr__(sar, "_tak", tak)
    object.__setattr__(sar, "_mud", mud)
    tak.kf = sar

    # _boyut_tazele oncesi/sonrasi boyut degerlerini kaydet (kalici degisiklik yok)
    bt_kayit = []
    _orig_bt = tak._boyut_tazele

    def _sarmal_bt(bgr):
        once = None if tak.boyut is None else tak.boyut.copy()
        once_olc = None if tak.boyut_olculen is None else tak.boyut_olculen.copy()
        r = _orig_bt(bgr)
        bt_kayit.append({
            "boyut_once": None if once is None else round(float(np.max(once)), 2),
            "boyut_sonra": round(float(np.max(tak.boyut)), 2),
            "olculen_once": None if once_olc is None else round(float(np.max(once_olc)), 2),
            "olculen_sonra": round(float(np.max(tak.boyut_olculen)), 2)})
        return r

    tak._boyut_tazele = _sarmal_bt

    hata_l, iou_l, psr_l, kilit_l, P_l, bho_l = [], [], [], [], [], []
    kabul = red = 0
    guvenli_yanlis = 0
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
        P_l.append(float(tak.kf.P[0, 0] + tak.kf.P[1, 1]))
        bho_l.append(float(np.max(tak.boyut)) / gL if gL > 0 else np.nan)
        kilit_l.append(1 if (s["durum"] == KILITLI and o > 0.2) else 0)
        if s["durum"] == KILITLI and o < 0.2:
            guvenli_yanlis += 1
        for e in log[n0:]:
            if e["kaynak"] == "_takip_adimi":
                if e["tip"] == "duzelt":
                    kabul += 1
                elif e["tip"] == "sondur":
                    red += 1
        if hata > A9.KOPUS_KAT * gL:
            ard += 1
            if ard >= A9.KOPUS_SABIR and kopus_kare is None:
                kopus_kare = t - A9.KOPUS_SABIR + 1
        else:
            ard = 0

    oran = [k["boyut_sonra"] / k["boyut_once"] for k in bt_kayit
            if k["boyut_once"]]
    return {"kare": len(hata_l),
            "ort_iou": A9.ort(iou_l), "kilit_orani": A9.ort(kilit_l),
            "merkez_hata_p50": A9.p(hata_l, 50), "merkez_hata_p95": A9.p(hata_l, 95),
            "guvenli_yanlis_kare": guvenli_yanlis, "kopus_karesi": kopus_kare,
            "psr_p50": A9.p(psr_l, 50), "psr_p05": A9.p(psr_l, 5),
            "P_konum_iz_p50": A9.p(P_l, 50), "P_konum_iz_p95": A9.p(P_l, 95),
            "bho_p50": A9.p(bho_l, 50), "bho_p95": A9.p(bho_l, 95),
            "dcf_kabul": kabul, "dcf_red": red,
            "boyut_tazele_cagri": len(bt_kayit),
            "boyut_degisim_orani_p50": A9.p(oran, 50) if oran else None,
            "boyut_degisim_orani_p95": A9.p(oran, 95) if oran else None,
            "boyut_tazele_kayitlari": bt_kayit}


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
    kol_adi = sys.argv[1] if len(sys.argv) > 1 else "ab1_rcarpan_6"
    yol = sys.argv[2] if len(sys.argv) > 2 else f"cikti/a9_{kol_adi}.json"
    assert kol_adi in KOLLAR, f"bilinmeyen kol: {kol_adi}"
    cikti = {"asama": f"A9 - tek degisken A/B: {kol_adi}",
             "kol_tanimi": KOLLAR[kol_adi],
             "kontrol": "kontrol kolu her hucrede yeniden kosuluyor",
             "takip_degismedi": True,
             "kabul_olcutu_dosyasi": "docs/architecture/A9_KABUL_OLCUTU.md",
             "acik_cevrim_uyarisi": "Sonuc UST SINIRDIR.",
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
            A = kol_olc(d, KOLLAR["kontrol"])
            Bk = kol_olc(d, KOLLAR[kol_adi])
            dd["seviyeler"][SEVIYE_AD[L]] = {"A_kontrol": A, "B_" + kol_adi: Bk}
            dio = Bk["ort_iou"] - A["ort_iou"]
            dp = ((Bk["merkez_hata_p95"] - A["merkez_hata_p95"])
                  / max(A["merkez_hata_p95"], 1e-9) * 100.0)
            print(f"  {SEVIYE_AD[L]:6s} IoU {A['ort_iou']:.3f}->{Bk['ort_iou']:.3f} "
                  f"({dio:+.3f}) | p95 {A['merkez_hata_p95']:>7.2f}->{Bk['merkez_hata_p95']:>7.2f} "
                  f"({dp:+6.1f}%) | guv.yanlis {A['guvenli_yanlis_kare']:>2}->{Bk['guvenli_yanlis_kare']:>2} "
                  f"| kopus {str(A['kopus_karesi']):>4}->{str(Bk['kopus_karesi']):>4} "
                  f"| bho50 {A['bho_p50']:.2f}->{Bk['bho_p50']:.2f} "
                  f"| PSR50 {A['psr_p50']:.1f}->{Bk['psr_p50']:.1f}", flush=True)
        cikti["diziler"][ad] = dd
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
