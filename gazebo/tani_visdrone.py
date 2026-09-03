"""Deney 4I - salt okunur: VisDrone dizilerinin izlenebilirlik envanteri.

TAKIP/ HIC DEGISMEZ. Takipci calistirilir ama yalnizca gozlemlenir; hicbir
esik, parametre ya da karar degistirilmez.

Amac performans kiyaslamasi DEGIL: her dizinin Faz C deneylerinde
GUVENILIR BAGIMSIZ gercek veri kaynagi olarak kullanilip kullanilamayacagini
belirlemek. Her dizi KENDI veri ozellikleri uzerinden degerlendirilir;
117/23 olcut olarak alinmaz.

Kullanim: python3 -m gazebo.tani_visdrone
"""
import argparse
import json
import os

import cv2
import numpy as np

import main as ana
import takip.izleyici as izl
from kaynak import kaynak_olustur
from takip.izleyici import KILITLI, HedefTakip
from veri.etiket import en_uygun_arac_track, track_ozeti, vid_oku
from veri.visdrone import diziler

KOK = "data/datasets/visdrone_vid"
GENISLIK = 960
# koşum takiminda halen kullanilan uc secim
MEVCUT = {"uav0000117_02622_v": 23, "uav0000182_00000_v": 127,
          "uav0000268_05773_v": 31}


class GozTakip(HedefTakip):
    """Uretilebilirlik sayaclari. Davranis birebir korunur."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.n_ara = 0
        self.psr_ler = []
        self.n_nan = 0
        g = self.cekirdek.ara

        def ara_s(bgr, gri, merkez, boyut):
            yeni, psr = g(bgr, gri, merkez, boyut)
            self.n_ara += 1
            if not np.isfinite(psr) or not np.all(np.isfinite(yeni)):
                self.n_nan += 1
            else:
                self.psr_ler.append(float(psr))
            return yeni, psr

        self.cekirdek.ara = ara_s


def _rafine_sar():
    gercek = izl.rafine_kutu

    def s(bgr, merkez, boyut, *a, **k):
        r = gercek(bgr, merkez, boyut, *a, **k)
        s.cagri += 1
        if r is not None:
            s.basari += 1
        return r

    s.cagri = s.basari = 0
    izl.rafine_kutu = s
    return gercek


def veri_ozellikleri(dizi, tid):
    """Takipci KOSTURULMADAN: goruntu ve GT ozellikleri."""
    k = kaynak_olustur("visdrone", veri_kok=KOK, dizi=dizi, track_id=tid,
                       hedef_genislik=GENISLIK)
    W, H = k.genislik, k.yukseklik
    gt, gorunur, bozuk = [], 0, 0
    kareler = 0
    for kare in k:
        kareler += 1
        if kare.goruntu is None or kare.goruntu.size == 0:
            bozuk += 1
            continue
        if kare.gt is not None and kare.gorunur:
            g = np.asarray(kare.gt, float)
            if not np.all(np.isfinite(g)) or g[2] <= 0 or g[3] <= 0:
                bozuk += 1
                continue
            gt.append(g)
            gorunur += 1
    gt = np.array(gt) if gt else np.zeros((0, 4))
    d = {"ham": f"{k.ham_genislik}x{k.ham_yukseklik}",
         "cozunurluk": f"{W}x{H}", "olcek": round(k.olcek, 4),
         "kare": kareler, "gt_kare": len(gt),
         "gorunurluk": round(gorunur / max(1, kareler), 4),
         "bozuk_kare": bozuk, "track_id": k.track_id}
    if len(gt):
        d.update({
            "gt_w_ort": float(gt[:, 2].mean()), "gt_h_ort": float(gt[:, 3].mean()),
            "gt_w_p5": float(np.percentile(gt[:, 2], 5)),
            "gt_w_p95": float(np.percentile(gt[:, 2], 95)),
            "gt_h_p5": float(np.percentile(gt[:, 3], 5)),
            "gt_h_p95": float(np.percentile(gt[:, 3], 95)),
            "goreli_alan_ppm": float(1e6 * (gt[:, 2] * gt[:, 3]).mean() / (W * H)),
            "kosegen_ort": float(np.hypot(gt[:, 2], gt[:, 3]).mean()),
        })
    return d


def ayrilabilirlik(dizi, tid, n=30):
    """rafine_kutu'nun dayandigi varsayim: hedef yerel medyandan ayrilir mi?"""
    from scipy.stats import rankdata
    k = kaynak_olustur("visdrone", veri_kok=KOK, dizi=dizi, track_id=tid,
                       hedef_genislik=GENISLIK)
    kare = [(x.goruntu.copy(), x.gt.copy()) for x in k
            if x.gt is not None and x.gorunur][:400]
    if not kare:
        return {}
    idx = np.linspace(0, len(kare) - 1, min(n, len(kare))).astype(int)
    auc, kon = [], []
    for i in idx:
        img, gt = kare[i]
        cx, cy = gt[0] + gt[2] / 2, gt[1] + gt[3] / 2
        w = max(7, int(round(gt[2] * 3.0)) | 1)
        h = max(7, int(round(gt[3] * 3.0)) | 1)
        pen = cv2.getRectSubPix(img, (w, h), (float(cx), float(cy))).astype(np.float32)
        med = np.median(pen.reshape(-1, 3), 0)
        d = np.linalg.norm(pen - med, axis=2)
        x0 = max(0, int(round(w / 2 - gt[2] / 2))); y0 = max(0, int(round(h / 2 - gt[3] / 2)))
        x1 = min(w, x0 + int(round(gt[2]))); y1 = min(h, y0 + int(round(gt[3])))
        if x1 - x0 < 3 or y1 - y0 < 3:
            continue
        m = np.zeros((h, w), bool); m[y0:y1, x0:x1] = True
        ic, dis = d[m], d[~m]
        if len(ic) < 9 or len(dis) < 9:
            continue
        v = np.r_[ic, dis]; lab = np.r_[np.ones(len(ic), bool), np.zeros(len(dis), bool)]
        r = rankdata(v); n1 = lab.sum(); n0 = (~lab).sum()
        auc.append((r[lab].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
        kon.append(float(np.median(ic) - np.median(dis)))
    if not auc:
        return {}
    return {"ayrim_auc": float(np.median(auc)), "kontrast": float(np.median(kon))}


def takipci_kos(dizi, tid):
    gercek = _rafine_sar()
    sarma = izl.rafine_kutu          # sayaclari geri almadan ONCE yakala
    ilk = ana.HedefTakip
    kutu = {}
    ana.HedefTakip = lambda *a, **k: kutu.setdefault("t", GozTakip(*a, **k))
    try:
        m = ana.kos(kaynak_olustur("visdrone", veri_kok=KOK, dizi=dizi,
                                   track_id=tid, hedef_genislik=GENISLIK),
                    pencere=False)
    finally:
        ana.HedefTakip = ilk
        izl.rafine_kutu = gercek
    t = kutu["t"]
    io = [r["iou"] for r in m.get("_olcum", [])]
    return {"kilitlendi": bool(m.get("kilitli", False)),
            "dcf_kare": t.n_ara, "psr_p50": float(np.median(t.psr_ler)) if t.psr_ler else None,
            "psr_p5": float(np.percentile(t.psr_ler, 5)) if t.psr_ler else None,
            "nan_kare": t.n_nan,
            "rafine_cagri": int(sarma.cagri),
            "rafine_basari": int(sarma.basari),
            "rafine_basari_orani": (round(sarma.basari / sarma.cagri, 4)
                                    if sarma.cagri else None),
            "iou": float(m.get("ort_iou", 0.0)),
            "merkez_hata": float(m.get("merkez_hata", 0.0)),
            "kilit_orani": float(m.get("kilit_orani", 0.0)),
            "kesinti": int(m.get("kesinti", 0)),
            "t_drift": m.get("t_drift"),
            "olculen_kare": len(io),
            "iou0_orani": float(np.mean([x <= 0.01 for x in io])) if io else None,
            "fps": float(m.get("fps", 0.0))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="cikti/visdrone_envanter.json")
    a = ap.parse_args()
    out = {}
    for dizi in diziler(KOK):
        et = vid_oku(os.path.join(KOK, "annotations", dizi + ".txt"))
        ozet = track_ozeti(et)
        arac = {t: o for t, o in ozet.items() if o["arac_mi"]}
        try:
            oto = en_uygun_arac_track(et)
        except Exception as e:                      # noqa: BLE001
            oto = None
        hedefler = {}
        if oto is not None:
            hedefler["oto"] = oto
        if dizi in MEVCUT:
            hedefler["mevcut"] = MEVCUT[dizi]
        kayit = {"dizi": dizi, "track_sayisi": len(ozet),
                 "arac_track": len(arac),
                 "oto_track": oto, "mevcut_track": MEVCUT.get(dizi),
                 "hedefler": {}}
        for etiket, tid in hedefler.items():
            if any(v.get("track_id") == tid for v in kayit["hedefler"].values()):
                continue
            try:
                r = veri_ozellikleri(dizi, tid)
                r.update(ayrilabilirlik(dizi, tid))
                r.update(takipci_kos(dizi, tid))
                r["rol"] = etiket
            except Exception as e:                  # noqa: BLE001
                r = {"track_id": tid, "rol": etiket, "hata": f"{type(e).__name__}: {e}"}
            kayit["hedefler"][str(tid)] = r
            print(f"  {dizi} track {tid} ({etiket}): "
                  f"IoU {r.get('iou', float('nan')):.3f} "
                  f"kilit {100*r.get('kilit_orani', 0):.1f}% "
                  f"drift {r.get('t_drift')} "
                  f"kutu {r.get('gt_w_ort', 0):.0f}x{r.get('gt_h_ort', 0):.0f} "
                  f"kontrast {r.get('kontrast', float('nan')):.1f}", flush=True)
        out[dizi] = kayit
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"yazildi: {a.json}")


if __name__ == "__main__":
    main()
