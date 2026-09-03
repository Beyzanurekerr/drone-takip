"""Deney 4Q - salt okunur: 4P mekanizmasi yanlis kilitlerin ne kadarini aciklar?

TAKIP/ HIC DEGISMEZ. Olcum atomlari 4O'nun (`gazebo.tani_4o_dcf.IzDcf`),
yanlis-kilit tanimi 4L'nin (durum == KILITLI ve IoU == 0), cekim noktasi
yontemi 4P'nin (`gazebo.tani_4p_karsilastir.cekim_noktasi`). Yeni esik yok.

4P'de NEDENSEL olarak dogrulanan mekanizmanin OLCULEN imzasi uc bilesenlidir:
  (i)   hedef DISINDA bir nesne DCF penceresine giriyor ve mesafe KAPANIYOR
  (ii)  DCF cekim noktasi GT'den UZAKLASIYOR (kopus oncesi tek yonlu)
  (iii) KF hizi cokuyor ve PSR dusuyor
Siniflama bu uc bilesenin VARLIGINA gore yapilir; hicbirine yeni bir sayisal
esik konmaz - her biri kopus oncesi 20 karede olculur ve ham degerleriyle
raporlanir.

DCF penceresi: `_kanallar` yamayi boyut x dolgu(2.0) kesiyor -> arama
merkezine gore yari-genislik = boyut_w, yari-yukseklik = boyut_h.

Kullanim: python3 -m gazebo.tani_4q_konjonksiyon
"""
import argparse
import json
import os

import numpy as np

import main as ana
from gazebo.tani_4o_dcf import IzDcf, _kaynak
from gazebo.tani_4p_karsilastir import cekim_noktasi
from takip.izleyici import KILITLI

GAZEBO_KOK = "data/gazebo"
DOLGU = 2.0
ONCE = 20            # kopus oncesi pencere (kare)

VISDRONE = [("117/23", ("uav0000117_02622_v", 23)),
            ("137/12", ("uav0000137_00458_v", 12)),
            ("182/127", ("uav0000182_00000_v", 127)),
            ("268/31", ("uav0000268_05773_v", 31)),
            ("305/5", ("uav0000305_00000_v", 5)),
            ("339/49", ("uav0000339_00001_v", 49))]


def kaynaklar():
    g = sorted(d for d in os.listdir(GAZEBO_KOK)
               if not d.startswith("_")
               and os.path.isdir(os.path.join(GAZEBO_KOK, d))
               and not d.endswith(("_tekrar", "_celdiricisiz")))
    return [(s, "gazebo", s) for s in g] + \
           [(a, "visdrone", x) for a, x in VISDRONE]


def digerleri(tur, kyn, k, hedef_kutu):
    """k. karede HEDEF DISINDAKI GT kutulari (goruntu koordinatlari)."""
    out = []
    if tur == "gazebo":
        if k >= len(kyn.pozlar):
            return out
        for ad, b in kyn.celdiriciler(k).items():
            if b is not None:
                out.append((ad, np.asarray(b, np.float64)))
    else:
        for e in kyn.kare_etiketleri(k):
            if e.yoksayilan or e.track_id == kyn.track_id:
                continue
            out.append((f"t{e.track_id}", np.asarray(e.kutu, np.float64)))
    return out


def kos(ad, tur, arg):
    ilk = ana.HedefTakip
    tut = {}
    ana.HedefTakip = lambda *a, **k: tut.setdefault("t", IzDcf(*a, **k))
    try:
        m = ana.kos(_kaynak(tur, arg), pencere=False)
    finally:
        ana.HedefTakip = ilk
    return m, tut["t"]


def epizotlar(olcum):
    """4L tanimi: durum == KILITLI ve IoU == 0 olan ardisik kareler."""
    kl = [r for r in olcum if r["durum"] == KILITLI]
    bay = [r["iou"] == 0.0 for r in kl]
    out, bas = [], None
    for i, b in enumerate(bay):
        if b and bas is None:
            bas = i
        elif not b and bas is not None:
            out.append((kl[bas]["kare"], kl[i - 1]["kare"], i - bas))
            bas = None
    if bas is not None:
        out.append((kl[bas]["kare"], kl[-1]["kare"], len(bay) - bas))
    return out, len(kl), sum(bay)


def analiz(ad, tur, arg, arsivli=True, capa="epizot"):
    """capa='epizot': 4L'nin YK epizot basi. capa='drift': `t_drift` (IoU'nun
    ILK kez surekli dustugu kare). Ikinci capa gerekli, cunku bazi dizilerde
    takipci YK epizodundan cok once hedefi kaybediyor ve epizot basi arizanin
    ani degil, KILITLI'nin yeniden ilan edildigi andir."""
    m, tak = kos(ad, tur, arg)
    olcum = m.get("_olcum") or []
    ep, n_kilitli, n_yk = epizotlar(olcum)
    if capa == "drift":
        td = m.get("t_drift")
        ep = [(int(td), int(td), 0)] if td is not None else []
    ofset = int(m["kare"]) - len(tak.iz)
    iz = {ofset + i: r for i, r in enumerate(tak.iz)}
    gtk = {r["kare"]: r for r in olcum}

    kyn = _kaynak(tur, arg)
    gt_kutu, frs = {}, {}
    ilgi = set()
    for a, _, _ in ep:
        ilgi |= set(range(max(0, a - ONCE), a + 2))
    for kare in kyn:
        if kare.gt is not None and kare.gorunur:
            gt_kutu[kare.indeks] = np.asarray(kare.gt, np.float64)
        if arsivli and kare.indeks in ilgi:
            frs[kare.indeks] = kare.goruntu.copy()

    d = {"ad": ad, "tur": tur, "ort_iou": float(m.get("ort_iou", 0.0)),
         "kilit_orani": float(m.get("kilit_orani", 0.0)),
         "t_drift": m.get("t_drift"), "n_kilitli": n_kilitli, "n_yk": n_yk,
         "yk_orani": n_yk / max(1, n_kilitli), "epizot": []}

    # yakinlik: TUM koşum boyunca en yakin diger nesne (kontrol icin de gerekli)
    yak = {}
    for k in sorted(gt_kutu):
        g = gt_kutu[k]
        gc = g[:2] + g[2:] / 2
        en = None
        for nm, b in digerleri(tur, kyn, k, g):
            c = b[:2] + b[2:] / 2
            dd = float(np.linalg.norm(c - gc))
            if en is None or dd < en[1]:
                en = (nm, dd, float(c[0] - gc[0]), float(c[1] - gc[1]),
                      [float(v) for v in b])
        if en:
            yak[k] = {"ad": en[0], "mesafe": en[1], "dx": en[2], "dy": en[3],
                      "kutu": en[4]}
    # pencere icinde mi (arama merkezine gore, yari = boyut)
    ic_sayac, ic_toplam = 0, 0
    for k, r in iz.items():
        if r.get("ara_merkez") is None or k not in yak:
            continue
        ic_toplam += 1
        w, h = float(r["boyut"][0]), float(r["boyut"][1])
        c = np.asarray(yak[k]["kutu"][:2]) + np.asarray(yak[k]["kutu"][2:]) / 2
        e = c - r["ara_merkez"]
        yak[k]["pencerede"] = bool(abs(e[0]) <= w and abs(e[1]) <= h)
        ic_sayac += yak[k]["pencerede"]
    d["pencerede_oran"] = ic_sayac / max(1, ic_toplam)
    d["en_yakin_kosum"] = min((v["mesafe"] for v in yak.values()), default=None)

    for a, b, n in ep:
        w0 = [k for k in range(max(0, a - ONCE), a) if k in iz and k in gt_kutu]
        e = {"bas": a, "son": b, "yk_kare": n, "once": []}
        for k in w0:
            r = iz[k]
            hm = None
            adl = r.get("adaylar") or []
            if adl:
                hm = adl[0]
                for c in adl:
                    if abs(c["aci"] - (r.get("aci_sonra") or 0.0)) < 1e-9:
                        hm = c
            cek = None
            if arsivli and k in frs and r.get("A_ara") is not None:
                c = cekim_noktasi(frs[k], r["A_ara"], r["B_ara"],
                                  tuple(r["ara_merkez"]),
                                  np.asarray(r["boyut"]))
                if c is not None:
                    g = gt_kutu[k]
                    cek = float(c - (g[0] + g[2] / 2))
            e["once"].append({
                "kare": k, "durum": r["durum"], "psr": r.get("psr"),
                "kf_hiz": float(np.linalg.norm(r["kf_hiz"])),
                "dx": None if hm is None else hm["dx"],
                "dy": None if hm is None else hm["dy"],
                "ix": None if hm is None else hm["ix"],
                "cekim_gt": cek,
                "iou": gtk.get(k, {}).get("iou"),
                "yakin": yak.get(k)})
        d["epizot"].append(e)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/konjonksiyon_4q.json")
    ap.add_argument("--capa", default="epizot", choices=["epizot", "drift"])
    a = ap.parse_args()
    out = {}
    for ad, tur, arg in kaynaklar():
        r = analiz(ad, tur, arg, capa=a.capa)
        out[ad] = r
        print("%-22s YK %5.1f%% (%3d/%3d) epizot %d | kosum en yakin diger "
              "nesne %s px | pencerede %.0f%%" % (
                  ad, 100 * r["yk_orani"], r["n_yk"], r["n_kilitli"],
                  len(r["epizot"]),
                  "%6.1f" % r["en_yakin_kosum"] if r["en_yakin_kosum"] else "  yok ",
                  100 * r["pencerede_oran"]), flush=True)
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f)
    print("yazildi:", a.json)


if __name__ == "__main__":
    main()
