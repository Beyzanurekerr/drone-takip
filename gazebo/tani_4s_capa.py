"""Deney 4S - salt okunur karsit-olgu: `_boyut_sinirla`'nin CAPASI degisseydi?

TAKIPCI KOSTURULMAZ. Yalnizca `cikti/boyut_4r.json`'daki kayitli seri
kullanilir. `takip/` okunmaz bile; hicbir sabit degismez. Kullanilan band
`izleyici.py:549`'un KENDI bandidir: [0.60, 1.70].

    A) MEVCUT     : b = max(boyut_olculen, min_kenar)   <- rafine ile guncellenir
    B) KARSIT-OLGU: b = max(kilit_boyutu, min_kenar)    <- sabit capa

Iki test ayri ayri raporlanir:

  S1  ACIK CEVRIM (geri besleme yok): her karede KAYITLI A4 degerine iki band
      da uygulanir; "band bu kaceyi GORUR muydu?" sorusu yanitlanir. Kesindir.

  S2  KAPALI CEVRIM (yaklasik): boyut ozyinelemesi kayitli `olcek_katsayisi`
      ve kayitli `rafine` kutulariyla yeniden kosturulur, yalnizca capa
      degistirilir.
      *** YAKLASIKLIK UYARISI: `rafine_kutu` girdi olarak `boyut`u alir
      (pencere = 3 x boyut) ve `kf.konum`a bagimlidir. Kutu degisince rafine
      cikitisi da degisirdi. Bu yuzden S2, capanin TEK BASINA saglayabilecegi
      iyilesmenin bir UST SINIRIDIR, bir tahmin degil. ***

  Sadakat denetimi: S2 MEVCUT capayla kosturulunca kayitli seriyi birebir
  uretmeli. Uretmiyorsa S2 sonucu okunmaz.

Kullanim: python3 -m gazebo.tani_4s_capa
"""
import argparse
import json
import os

import numpy as np

MIN_KENAR = 4.0          # izleyici.py:120 varsayilani
ALT, UST = 0.60, 1.70    # izleyici.py:549 bandi - DEGISTIRILMEDI
KARAR = ["182/127", "305/5", "G6_agresif"]
AYRI = ["G6_agresif_durakli"]


def seri(r):
    return sorted(r["satir"], key=lambda x: x["kare"])


def kilit_boyut(s):
    """En erken kaydedilen kare girisi = kilitle()'nin biraktigi boyut."""
    return np.array([s[0]["A0_w"], s[0]["A0_h"]], np.float64)


def s1_acik(s, b_cf):
    """Her karede KAYITLI A4'e iki bandi da uygula. Geri besleme yok."""
    out = []
    for x in s:
        if "A4_w" not in x:
            continue
        a4 = np.array([x["A4_w"], x["A4_h"]])
        b_a = np.array([x["sinir_alt_w"] / ALT, x["sinir_alt_h"] / ALT])  # = b mevcut
        a5_a = np.clip(a4, ALT * b_a, UST * b_a)
        a5_b = np.clip(a4, ALT * b_cf, UST * b_cf)
        out.append({"kare": x["kare"], "gt": np.array([x["gt_w"], x["gt_h"]]),
                    "a4": a4, "a5_a": a5_a, "a5_b": a5_b,
                    "ihlal_a": bool(np.any(np.abs(a5_a - a4) > 1e-9)),
                    "ihlal_b": bool(np.any(np.abs(a5_b - a4) > 1e-9)),
                    "kirp_b": a5_b - a4})
    return out


def s2_kapali(s, capa):
    """Ozyinelemeyi kayitli olc + kayitli rafine ile yeniden kostur.

    capa=None -> MEVCUT davranis (boyut_olculen de yeniden uretilir)
    capa=vec  -> sabit capa
    """
    b = kilit_boyut(s).copy()
    olculen = b.copy()
    iz = []
    for x in s:
        olc = x.get("olcek_katsayisi")
        if olc is not None:                       # izleyici.py:264
            b = np.maximum(b * float(np.clip(olc, 0.90, 1.10)), MIN_KENAR)
        raf = x.get("rafine")
        if "A3_w" in x:                           # _boyut_tazele cagrildi
            if raf is not None:
                rw = np.array([raf[2], raf[3]], np.float64)
                b = np.maximum(0.75 * b + 0.25 * rw, MIN_KENAR)      # :563
                olculen = 0.85 * olculen + 0.15 * np.maximum(rw, MIN_KENAR)  # :564
        if "arama_yazdi_w" in x:                  # :522-523 (ARAMA dali)
            b = np.array([x["arama_yazdi_w"], x["arama_yazdi_h"]], np.float64)
            olculen = b.copy()
        cap = np.maximum(olculen, MIN_KENAR) if capa is None else np.maximum(capa, MIN_KENAR)
        b_once = b.copy()
        b = np.clip(b, ALT * cap, UST * cap)      # :549
        iz.append({"kare": x["kare"], "boyut": b.copy(),
                   "kirpildi": bool(np.any(np.abs(b - b_once) > 1e-9)),
                   "gt": np.array([x["gt_w"], x["gt_h"]]),
                   "kayitli": np.array([x["son_w"], x["son_h"]])})
    return iz


def ozet(ad, r):
    s = seri(r)
    kb = kilit_boyut(s)
    td = r["t_drift"]
    gt0 = np.array([s[0]["gt_w"], s[0]["gt_h"]])
    gtw = np.array([[x["gt_w"], x["gt_h"]] for x in s])
    d = {"ad": ad, "t_drift": td,
         "kilit_boyut": [float(v) for v in kb],
         "kilit_gt": [float(v) for v in gt0],
         "gt_oran_min": [float(v) for v in (gtw / gt0).min(0)],
         "gt_oran_maks": [float(v) for v in (gtw / gt0).max(0)]}

    a = s1_acik(s, kb)
    d["s1"] = {"kare": len(a),
               "ihlal_mevcut": sum(x["ihlal_a"] for x in a),
               "ihlal_capa": sum(x["ihlal_b"] for x in a),
               "ilk_ihlal_capa": next((x["kare"] for x in a if x["ihlal_b"]), None),
               "maks_kirpma": float(max((np.abs(x["kirp_b"]).max() for x in a),
                                        default=0.0))}
    if td is not None:
        d["s1"]["ihlal_capa_drift_oncesi"] = sum(
            x["ihlal_b"] for x in a if x["kare"] <= td)

    sim_a = s2_kapali(s, None)
    sim_b = s2_kapali(s, kb)
    sap = max(float(np.abs(x["boyut"] - x["kayitli"]).max()) for x in sim_a)
    d["s2_sadakat_maks_sapma_px"] = sap
    def oran(sim, k=None):
        v = [x["boyut"] / np.maximum(x["gt"], 1e-9) for x in sim
             if k is None or x["kare"] <= k]
        return np.array(v)
    for et, sim in (("mevcut", sim_a), ("capa", sim_b)):
        o = oran(sim, td)
        d["s2_" + et] = {
            "son_oran_w": float(oran(sim)[-1][0]), "son_oran_h": float(oran(sim)[-1][1]),
            "drift_oran_w": float(o[-1][0]) if len(o) else None,
            "drift_oran_h": float(o[-1][1]) if len(o) else None,
            "maks_oran_w": float(o[:, 0].max()) if len(o) else None,
            "maks_oran_h": float(o[:, 1].max()) if len(o) else None,
            "ort_mutlak_log": float(np.mean(np.abs(np.log(o)))) if len(o) else None,
            "kirpma_kare": sum(x["kirpildi"] for x in sim)}
    return d, a, sim_a, sim_b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--giris", default="cikti/boyut_4r.json")
    ap.add_argument("--json", default="cikti/capa_4s.json")
    a = ap.parse_args()
    veri = json.load(open(a.giris))
    out = {}
    for ad in KARAR + AYRI:
        r = veri[ad]
        d, s1, sa, sb = ozet(ad, r)
        out[ad] = d
        print(f"\n== {ad} == drift {d['t_drift']}  kilit boyut "
              f"{d['kilit_boyut'][0]:.1f}/{d['kilit_boyut'][1]:.1f}  "
              f"(kilit GT {d['kilit_gt'][0]:.1f}/{d['kilit_gt'][1]:.1f})")
        print(f"   GT boyutu kosum boyunca kilit GT'sinin "
              f"{d['gt_oran_min'][0]:.2f}..{d['gt_oran_maks'][0]:.2f} x (w), "
              f"{d['gt_oran_min'][1]:.2f}..{d['gt_oran_maks'][1]:.2f} x (h) kati")
        print(f"   S1 acik cevrim: {d['s1']['kare']} kare | ihlal MEVCUT capa "
              f"{d['s1']['ihlal_mevcut']} | ihlal SABIT capa "
              f"{d['s1']['ihlal_capa']} (ilk kare {d['s1']['ilk_ihlal_capa']}, "
              f"drift oncesi {d['s1'].get('ihlal_capa_drift_oncesi')})")
        print(f"   S2 sadakat: maks sapma {d['s2_sadakat_maks_sapma_px']:.4f} px")
        for et in ("mevcut", "capa"):
            q = d["s2_" + et]
            print(f"   S2 {et:7s}: drift kutu/GT {q['drift_oran_w']:.2f}/"
                  f"{q['drift_oran_h']:.2f}  maks {q['maks_oran_w']:.2f}/"
                  f"{q['maks_oran_h']:.2f}  |log| ort {q['ort_mutlak_log']:.3f}  "
                  f"kirpma {q['kirpma_kare']} kare")
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nyazildi: {a.json}")


if __name__ == "__main__":
    main()
