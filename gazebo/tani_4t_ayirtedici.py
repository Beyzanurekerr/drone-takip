"""Deney 4T - salt okunur: bozuk `rafine_kutu` cikitisi MEVCUT sinyallerle
onceden ayirt edilebiliyor mu?

TAKIPCI KOSTURULMAZ. Yalnizca iki kayitli dosya okunur ve kare numarasiyla
eslestirilir:
    cikti/rafine_4n.json  (Deney 4N) - rafine_kutu'nun IC buyuklukleri
    cikti/boyut_4r.json   (Deney 4R) - donen kutu + GT + boyut serisi
`takip/` okunmaz, hicbir sabit degismez, hicbir esik takipciye uygulanmaz.

BOZUK TANIMI - yeni sabit ICAT EDILMEDI:
    Donen rafine kutusu, deponun KENDI bandinin ([0.60, 1.70],
    izleyici.py:549) disinda kaliyorsa "bozuk" sayilir:
        rafine_w / GT_w  ya da  rafine_h / GT_h  <0.60  ya da  >1.70

SINYAL SECIMI - yalnizca KOSUM ANINDA ERISILEBILIR olanlar:
    GT gerektiren hicbir buyukluk sinyal olarak kullanilmaz
    (bilesen_gt_iou, bilesen_alan_orani, gt_pencere_orani DISLANDI - bunlar
    yalnizca ETIKET tarafinda, "bozuk mu" sorusunu tanimlarken kullanilir).

Kullanim: python3 -m gazebo.tani_4t_ayirtedici
"""
import argparse
import json
import os

import numpy as np

ALT, UST = 0.60, 1.70        # izleyici.py:549 - deponun kendi bandi
KARAR = ["182/127", "305/5", "G6_agresif", "G6_agresif_durakli"]


def auc(skor, etiket):
    """Mann-Whitney U tabanli ROC-AUC (baglar ortalanir). 0.5 = ayirt etmiyor."""
    s = np.asarray(skor, float)
    y = np.asarray(etiket, bool)
    if y.all() or not y.any() or len(s) < 4:
        return None
    r = np.empty(len(s), float)
    sira = np.argsort(s, kind="mergesort")
    ss = s[sira]
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[sira[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    n1, n0 = int(y.sum()), int((~y).sum())
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def en_iyi_esik(skor, etiket):
    """Youden J (TPR - FPR) en yuksek nokta. YALNIZCA RAPOR icin; takipciye
    uygulanmaz."""
    s = np.asarray(skor, float)
    y = np.asarray(etiket, bool)
    en = None
    for t in np.unique(s):
        for yon in (1, -1):
            p = (s >= t) if yon > 0 else (s <= t)
            tpr = float((p & y).sum()) / max(1, y.sum())
            fpr = float((p & ~y).sum()) / max(1, (~y).sum())
            j = tpr - fpr
            if en is None or j > en[0]:
                en = (j, float(t), yon, tpr, fpr)
    return en


def sinyaller_4n(o):
    """4N kaydindan KOSUM ANINDA hesaplanan buyuklukler."""
    if o.get("neden") != "OK":
        return None
    d = {"n_bilesen": o.get("n_bilesen"),
         "maske_doluluk": o.get("maske_doluluk"),
         "p82": o.get("p82"),
         "esik_taban_mi": float(bool(o.get("esik_taban_mi"))),
         "oran_w": o.get("oran_w"), "oran_h": o.get("oran_h"),
         "oran_ort": o.get("oran_ort"),
         "renk_mesafe": o.get("renk_mesafe")}
    if o.get("bilesen") and o.get("pencere_wh"):
        bw, bh, alan = o["bilesen"][2], o["bilesen"][3], o["bilesen"][4]
        pw, ph = o["pencere_wh"]
        d["bilesen_alan_pencere"] = alan / max(1.0, pw * ph)
        d["bilesen_dolgunluk"] = alan / max(1.0, bw * bh)
        d["bilesen_enboy"] = bw / max(1.0, bh)
    if o.get("oran_w") and o.get("oran_h"):
        d["log_oran_buyukluk"] = abs(np.log(max(1e-6, o["oran_w"]))) + \
                                 abs(np.log(max(1e-6, o["oran_h"])))
    return {k: float(v) for k, v in d.items() if v is not None}


def sinyaller_4r(x):
    """4R satirindan KOSUM ANINDA hesaplanan buyuklukler (GT kullanilmaz)."""
    raf = x.get("rafine")
    if raf is None or "A2_w" not in x:
        return None
    rw, rh = float(raf[2]), float(raf[3])
    bw, bh = x["A2_w"], x["A2_h"]
    ow, oh = x["olculen_w"], x["olculen_h"]
    d = {"oran_w": rw / max(1e-6, bw), "oran_h": rh / max(1e-6, bh),
         "olculen_oran_w": rw / max(1e-6, ow), "olculen_oran_h": rh / max(1e-6, oh),
         "rafine_w": rw, "rafine_h": rh,
         "enboy_fark": abs(rw / max(1e-6, rh) - bw / max(1e-6, bh))}
    d["oran_ort"] = 0.5 * (d["oran_w"] + d["oran_h"])
    d["log_oran_buyukluk"] = abs(np.log(max(1e-6, d["oran_w"]))) + \
                             abs(np.log(max(1e-6, d["oran_h"])))
    d["olculen_log_buyukluk"] = abs(np.log(max(1e-6, d["olculen_oran_w"]))) + \
                                abs(np.log(max(1e-6, d["olculen_oran_h"])))
    return d


def bozuk_mu(rw, rh, gw, gh):
    a, b = rw / max(1e-6, gw), rh / max(1e-6, gh)
    return bool(a < ALT or a > UST or b < ALT or b > UST), a, b


def topla():
    n4 = json.load(open("cikti/rafine_4n.json"))
    r4 = json.load(open("cikti/boyut_4r.json"))
    kume = {}
    for ad in set(list(n4) + list(r4)):
        satir = []
        # --- 4R tabanli (dort karar kaynagi) ---
        if ad in r4:
            for x in r4[ad]["satir"]:
                s = sinyaller_4r(x)
                if s is None:
                    continue
                raf = x["rafine"]
                bz, ow, oh = bozuk_mu(raf[2], raf[3], x["gt_w"], x["gt_h"])
                satir.append({"kare": x["kare"], "kaynak": "4R", "sinyal": s,
                              "bozuk": bz, "gt_oran_w": ow, "gt_oran_h": oh,
                              "bagil_hata": max(abs(np.log(max(1e-6, ow))),
                                                abs(np.log(max(1e-6, oh))))})
        # --- 4N tabanli (ic buyuklukler; yalniz 4N'de olan kaynaklar) ---
        if ad in n4:
            r4k = {x["kare"]: x for x in r4.get(ad, {}).get("satir", [])}
            for o in n4[ad]["kayit"]:
                s = sinyaller_4n(o)
                if s is None or "gt_w" not in o:
                    continue
                bw, bh = o["bilesen"][2], o["bilesen"][3]
                bz, ow, oh = bozuk_mu(bw, bh, o["gt_w"], o["gt_h"])
                satir.append({"kare": o["kare"], "kaynak": "4N", "sinyal": s,
                              "bozuk": bz, "gt_oran_w": ow, "gt_oran_h": oh,
                              "bagil_hata": max(abs(np.log(max(1e-6, ow))),
                                                abs(np.log(max(1e-6, oh)))),
                              "eslesti": o["kare"] in r4k})
        if satir:
            kume[ad] = satir
    return kume


def coz(ad, satir, kok):
    alt = [x for x in satir if x["kaynak"] == kok]
    if len(alt) < 6:
        return None
    n_b = sum(x["bozuk"] for x in alt)
    d = {"kaynak_kayit": kok, "cagri": len(alt), "bozuk": n_b,
         "bozuk_orani": n_b / len(alt), "sinyal": {}}
    if n_b == 0 or n_b == len(alt):
        return d
    adlar = sorted({k for x in alt for k in x["sinyal"]})
    for nm in adlar:
        v = [(x["sinyal"][nm], x["bozuk"], x["bagil_hata"])
             for x in alt if nm in x["sinyal"]]
        if len(v) < 6:
            continue
        s = np.array([q[0] for q in v]); y = np.array([q[1] for q in v], bool)
        a = auc(s, y)
        if a is None:
            continue
        en = en_iyi_esik(s, y)
        d["sinyal"][nm] = {"auc": a, "yonlu_auc": max(a, 1 - a),
                           "esik": en[1], "yon": en[2],
                           "tpr": en[3], "fpr": en[4], "j": en[0], "n": len(v)}
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/ayirtedici_4t.json")
    a = ap.parse_args()
    kume = topla()
    out = {}
    for ad in KARAR + [k for k in kume if k not in KARAR]:
        if ad not in kume:
            continue
        out[ad] = {}
        for kok in ("4R", "4N"):
            d = coz(ad, kume[ad], kok)
            if d is None:
                continue
            out[ad][kok] = d
            print(f"\n== {ad}  [{kok} kaydi] == cagri {d['cagri']}, "
                  f"BOZUK {d['bozuk']} (%{100*d['bozuk_orani']:.1f})")
            if not d["sinyal"]:
                print("   (tek sinifli - ayirt edicilik tanimsiz)")
                continue
            sr = sorted(d["sinyal"].items(), key=lambda kv: -kv[1]["yonlu_auc"])
            print("   %-24s %6s %6s | %6s %5s %5s" % (
                "sinyal", "AUC", "yonlu", "esik", "TPR", "FPR"))
            for nm, q in sr:
                print("   %-24s %6.3f %6.3f | %6.2f %5.2f %5.2f %s" % (
                    nm, q["auc"], q["yonlu_auc"], q["esik"], q["tpr"], q["fpr"],
                    ">=" if q["yon"] > 0 else "<="))
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nyazildi: {a.json}")


if __name__ == "__main__":
    main()
