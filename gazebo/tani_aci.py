"""Deney 2 aci secimi teshisi: kare kare aday acilar, skorlar ve hata.

Takipciye DOKUNMAZ. `RenkDcfCekirdek`in `_yanit` ve `ara` metotlari disaridan
sarilir; her karede uc adayin (aci, PSR) ciftleri, secilen aday, ego tohumu ve
gercek kamera acisi yazilir. Hicbir esik ya da davranis degismez - sarma
yalnizca okur.

    python3 -m gazebo.tani_aci G3_agresif G3_kritik G3_yumusak
"""
import argparse
import math
import sys

import numpy as np

import main as ana
from calistir import iou
from gazebo.tani import gercek_goruntu_donmesi
from takip.cekirdekler import RenkDcfCekirdek
from takip.izleyici import HedefTakip
from veri.gazebo import GazeboKaynak


class TaniDcf(RenkDcfCekirdek):
    """Aday degerlendirmelerini kaydeden saydam sarma."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.kayit = []
        self._adaylar = []
        self._kare = -1

    def _yanit(self, bgr, merkez, boyut, aci):
        yeni, psr = super()._yanit(bgr, merkez, boyut, aci)
        self._adaylar.append((float(aci), float(psr)))
        return yeni, psr

    def ara(self, bgr, gri, merkez, boyut):
        self._adaylar = []
        onceki_aci, dteta = self.aci, self.dteta
        ref_once = getattr(self, "aci_ref", 0.0)
        yeni, psr = super().ara(bgr, gri, merkez, boyut)
        self.kayit.append({
            "kare": self._kare,
            "aktif": self.aktif,
            "adim": self.aci_adim,
            "onceki_aci": onceki_aci,
            "aci_ref_once": float(ref_once),
            "aci_ref": float(getattr(self, "aci_ref", 0.0)),
            "dteta": dteta,
            "tohum": float(getattr(self, "aci_ref", onceki_aci + dteta)),
            "adaylar": list(self._adaylar),
            "secilen": self.aci,
            "psr": float(psr),
            "kayma": float(np.linalg.norm(np.asarray(yeni) - np.asarray(merkez))),
        })
        return yeni, psr


class TaniTakip(HedefTakip):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)

    def guncelle(self, bgr):
        self.cekirdek._kare = self.kare + 1
        return super().guncelle(bgr)


def olc(senaryo, kok="data/gazebo"):
    kaynak = GazeboKaynak(kok=kok, senaryo=senaryo)
    ger = gercek_goruntu_donmesi(kaynak)
    gt = [kaynak._kutu(s, kaynak.hedef_ad) for s in kaynak.pozlar]

    cek = TaniDcf()
    ilk = ana.HedefTakip
    ana.HedefTakip = lambda *a, **k: TaniTakip(cekirdek=cek)
    try:
        m = ana.kos(kaynak, pencere=False)
    finally:
        ana.HedefTakip = ilk

    # kare hizalamasi: kayit[i] -> kare (n_kare - len(kayit) + i)
    n = int(m["kare"])
    ofset = n - len(cek.kayit)
    iou_kare = {r["kare"]: r["iou"] for r in m.get("_olcum", [])}
    ilk_kare = ofset
    taban = ger[ilk_kare] if ilk_kare < len(ger) else 0.0
    for i, r in enumerate(cek.kayit):
        k = ofset + i
        r["kare"] = k
        r["gercek"] = float(ger[k] - taban) if k < len(ger) else float("nan")
        r["hata"] = r["secilen"] - r["gercek"]
        r["iou"] = iou_kare.get(k)
        r["gt_wh"] = (float(gt[k][2]), float(gt[k][3])) if gt[k] is not None else None
    return m, cek.kayit


def ozet(ad, m, kayit):
    a = [r for r in kayit if r["aktif"]]
    print(f"\n=== {ad} ===  IoU {m['ort_iou']:.3f}  merkez {m['merkez_hata']:.2f} px  "
          f"drift {m['t_drift']}  aktif {len(a)}/{len(kayit)} kare")
    if not a:
        print("  aci aramasi hic acilmadi")
        return
    adim = a[0]["adim"]
    hata = np.array([r["hata"] for r in a])
    ger_d = np.diff([r["gercek"] for r in a])
    sec_d = np.diff([r["secilen"] for r in a])
    print(f"  adim {adim:.3f} deg | gercek aci {min(r['gercek'] for r in a):+.1f}"
          f"..{max(r['gercek'] for r in a):+.1f} | secilen {min(r['secilen'] for r in a):+.1f}"
          f"..{max(r['secilen'] for r in a):+.1f}")
    print(f"  HATA (secilen - gercek): ort {hata.mean():+.2f}  p50 {np.percentile(hata,50):+.2f}"
          f"  p05/p95 {np.percentile(hata,5):+.2f}/{np.percentile(hata,95):+.2f}"
          f"  |hata| p95 {np.percentile(np.abs(hata),95):.2f} deg")
    print(f"  KARE BASINA: gercek d {ger_d.mean():+.3f} +-{ger_d.std():.3f}  "
          f"secilen d {sec_d.mean():+.3f} +-{sec_d.std():.3f}  "
          f"ego dteta {np.mean([r['dteta'] for r in a]):+.3f} deg")

    # aday secimi: n-1 / n / n+1 hangisi ne siklikta kazandi
    say = {-1: 0, 0: 0, 1: 0}
    beraberlik = 0
    fark21 = []
    for r in a:
        ac = r["adaylar"]
        if len(ac) != 3:
            continue
        psr = [c[1] for c in ac]
        i = int(np.argmax(psr))
        say[i - 1] += 1
        s = sorted(psr, reverse=True)
        fark21.append((s[0] - s[1]) / max(1e-9, s[0]))
        if (s[0] - s[1]) / max(1e-9, s[0]) < 0.02:
            beraberlik += 1
    top = sum(say.values())
    print(f"  SECIM: alt aday (n-1) %{100*say[-1]/top:.1f} | orta (n) %{100*say[0]/top:.1f} "
          f"| ust (n+1) %{100*say[1]/top:.1f}")
    f = np.array(fark21)
    print(f"  SKOR AYRIMI (birinci-ikinci)/birinci: p50 %{100*np.percentile(f,50):.1f} "
          f"p05 %{100*np.percentile(f,5):.1f}  |  %2'den yakin: {beraberlik}/{top} kare "
          f"(%{100*beraberlik/top:.1f})")

    # hatanin IoU ile iliskisi
    io = [(abs(r["hata"]), r["iou"]) for r in a if r["iou"] is not None]
    if io:
        h = np.array([x[0] for x in io]); v = np.array([x[1] for x in io])
        alt, ust = v[h <= np.percentile(h, 33)], v[h >= np.percentile(h, 67)]
        print(f"  |hata| dusuk ucte birlik IoU {alt.mean():.3f}  vs  yuksek ucte birlik "
              f"IoU {ust.mean():.3f}  (fark {ust.mean()-alt.mean():+.3f})")
        print(f"  korelasyon(|hata|, IoU) = {np.corrcoef(h, v)[0,1]:+.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("senaryo", nargs="*", default=["G3_agresif"])
    ap.add_argument("--kok", default="data/gazebo")
    ap.add_argument("--kare", nargs="*", type=int, default=[],
                    help="bu karelerin aday skorlarini tek tek bas")
    a = ap.parse_args()
    for ad in a.senaryo:
        m, kayit = olc(ad, kok=a.kok)
        ozet(ad, m, kayit)
        if a.kare:
            print("  kare | gercek  tohum  ->  adaylar (aci:PSR)                       secilen  hata")
            d = {r["kare"]: r for r in kayit}
            for k in a.kare:
                r = d.get(k)
                if r is None or not r["aktif"]:
                    continue
                ad_s = "  ".join(f"{c[0]:+7.2f}:{c[1]:6.2f}" for c in r["adaylar"])
                print(f"  {k:4d} | {r['gercek']:+7.2f} {r['tohum']:+7.2f}  ->  {ad_s}  "
                      f"{r['secilen']:+7.2f} {r['hata']:+6.2f}")


if __name__ == "__main__":
    main()
