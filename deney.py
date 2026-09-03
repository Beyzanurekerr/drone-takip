"""A3.9 Faz C: TEK DEGISIKLIK / TEK DENEY A-B kosucusu.

Bir tracker degisikliginin UC olcum hattinda birden etkisini ayni komutla
alir, JSON'a yazar ve iki JSON'u yan yana kiyaslar. Amac tek metrigi
iyilestirmek degil; sim + Gazebo + gercek veri + performans arasindaki
DENGEYI gormek.

    python3 deney.py --etiket once              -> cikti/deney_once.json
    <degisikligi uygula>
    python3 deney.py --etiket sonra             -> cikti/deney_sonra.json
    python3 deney.py --kiyas once sonra         -> fark tablosu

Uc hat BILEREK ayri tutulur ve sayilari birbirine karistirilmaz:
    gazebo/  kontrollu kamera hareketi, kusursuz GT   (gazebo/tani.py)
    sim/     kontrollu hedef boyutu supurmesi         (calistir.py)
    visdrone gercek goruntu, gercek gurultu           (main.py)

ID SWITCH yalnizca sim ve Gazebo'da olculur; VisDrone'da tek track etiketli
oldugu icin tanimsizdir (`visdrone_kiyasla.py` basligindaki notla ayni gerekce).

GECIKME/FPS GURULTUSU: ayni ikili ard arda kosuldugunda FPS %3-5 oynar. Bu
yuzden `--kiyas` FPS icin +-%5 bandini "fark yok" sayar ve p95 gecikmeyi
tabloda ayrica gosterir.
"""
import argparse
import json
import os
import time

import numpy as np

GAZEBO_CEKIRDEK = ["G0",
                   "G1_yumusak", "G1_agresif", "G2_yumusak", "G2_agresif",
                   "G3_yumusak", "G3_agresif", "G4_yumusak", "G4_agresif",
                   "G5_yumusak", "G5_agresif", "G6_yumusak", "G6_agresif",
                   "G7_yumusak", "G7_agresif"]
GAZEBO_EK = ["G1_kritik", "G3_kritik", "G4_kritik", "G5_kritik", "G7_kritik",
             "G6_agresif_hedef", "G6_agresif_durakli"]
SIM_TESTLER = [f"test{i}" for i in range(1, 8)]
VISDRONE = [("uav0000117_02622_v", 23), ("uav0000268_05773_v", 31),
            ("uav0000182_00000_v", 127)]
VISDRONE_KOK = "data/datasets/visdrone_vid"
VISDRONE_GENISLIK = 960

# tabloda tasinan ortak alanlar (hepsi uc hatta da tanimli, id_switch haric)
ALANLAR = ["iou", "basari@0.5", "merkez_hata", "kilit_orani", "kesinti",
           "kurtarma_ort", "kurtarma_max", "id_switch", "t_drift",
           "fps", "gecikme_p50", "gecikme_p95"]


def _ortak(m, id_switch=None):
    """Farkli hatlarin metrik sozluklerini TEK bir sozluge indirger.

    calistir.kos ve main.kos "ort_iou" yazar, gazebo/tani.py "iou"; ikisi de
    kabul edilir. Ilk kosumda bu kacirildi ve Gazebo sutunu sessizce 0.000
    okundu - anahtar adlarinin ayni olduguna GUVENILMEMELI.
    """
    return {
        "iou": float(m.get("ort_iou", m.get("iou", 0.0))),
        "basari@0.5": float(m.get("basari@0.5", 0.0)),
        "basari@0.3": float(m.get("basari@0.3", 0.0)),
        "merkez_hata": float(m.get("merkez_hata", float("nan"))),
        "kilit_orani": float(m.get("kilit_orani", 0.0)),
        "kesinti": int(m.get("kesinti", 0)),
        "kurtarma_ort": float(m.get("kurtarma_ort", 0.0)),
        "kurtarma_max": int(m.get("kurtarma_max", 0)),
        "id_switch": (int(m["id_switch"]) if id_switch is None
                      and "id_switch" in m else id_switch),
        "t_drift": m.get("t_drift"),
        "fps": float(m.get("fps", 0.0)),
        "gecikme_p50": float(m.get("gecikme_p50", 0.0)),
        "gecikme_p95": float(m.get("gecikme_p95", 0.0)),
    }


def kos_gazebo(adlar, cekirdek):
    from gazebo.tani import olc
    out = {}
    for ad in adlar:
        t = olc(ad, kok="data/gazebo", cekirdek=cekirdek)
        r = _ortak(t)
        # Gazebo'ya ozgu teshis alanlari da tasinir: degisiklik ego/DCF
        # dengesini bozarsa once burada gorunur.
        for k in ("tavan_iou", "e_ego_p95", "e_model_p95", "e_kest_p95",
                  "d_r_p95", "sicrama_p95", "ego_birim_orani",
                  "sicrama_red_orani", "yanlis_kilit_orani",
                  "kf_hiz_hatasi_p95", "kamera_acisal_p95", "psr_p50",
                  "ego_donme_p95", "aci_adim", "aci_aktif_orani",
                  "aci_aktif_kare", "aci_ilk_kare", "aci_kullanilan_min",
                  "aci_kullanilan_max", "aci_gercek_min", "aci_gercek_max",
                  "aci_hata_p50", "aci_hata_p95"):
            r[k] = t[k]
        out[ad] = r
        print(f"  gazebo {ad:20s} IoU {r['iou']:.3f} kilit {r['kilit_orani']:.1%} "
              f"IDsw {r['id_switch']} drift {r['t_drift']} PSR {r['psr_p50']:.0f} "
              f"{r['fps']:.0f} FPS", flush=True)
    return out


def kos_sim(testler, cekirdek):
    from calistir import kos
    from sim.senaryolar import TUM_TESTLER
    from takip.izleyici import HedefTakip
    out = {}
    for ad in testler:
        sen = TUM_TESTLER[ad]()
        m = kos(sen, sessiz=True, yap_takipci=lambda: HedefTakip(cekirdek=cekirdek))
        r = _ortak(m)
        r["hassasiyet"] = float(m.get("hassasiyet", 0.0))
        out[ad] = r
        print(f"  sim    {ad:20s} IoU {r['iou']:.3f} kilit {r['kilit_orani']:.1%} "
              f"IDsw {r['id_switch']} drift {r['t_drift']} {r['fps']:.0f} FPS",
              flush=True)
    return out


def kos_visdrone(hedefler, cekirdek):
    import main
    from kaynak import kaynak_olustur
    out = {}
    for dizi, tid in hedefler:
        kaynak = kaynak_olustur("visdrone", veri_kok=VISDRONE_KOK, dizi=dizi,
                                track_id=tid, hedef_genislik=VISDRONE_GENISLIK)
        m = main.kos(kaynak, cekirdek=cekirdek, pencere=False)
        ad = f"{dizi.split('_')[0][3:]}/{tid}"     # 117/23 gibi kisa ad
        r = _ortak(m, id_switch=None)
        r["id_switch"] = None                      # tanimsiz: tek track etiketli
        r["hassasiyet"] = float(m.get("hassasiyet", 0.0))
        r["dizi"], r["track_id"], r["gt_kare"] = dizi, tid, int(m.get("gt_kare", 0))
        out[ad] = r
        print(f"  visdr  {ad:20s} IoU {r['iou']:.3f} kilit {r['kilit_orani']:.1%} "
              f"drift {r['t_drift']} {r['fps']:.0f} FPS", flush=True)
    return out


def kos_hepsi(cekirdek="renk_dcf", ek=True):
    t0 = time.time()
    s = {"gazebo": kos_gazebo(GAZEBO_CEKIRDEK + (GAZEBO_EK if ek else []), cekirdek),
         "sim": kos_sim(SIM_TESTLER, cekirdek),
         "visdrone": kos_visdrone(VISDRONE, cekirdek)}
    s["_sure_s"] = round(time.time() - t0, 1)
    s["_cekirdek"] = cekirdek
    return s


# ---------------------------------------------------------------------------
YUKARI_IYI = {"iou", "basari@0.5", "basari@0.3", "kilit_orani", "hassasiyet",
              "fps", "tavan_iou", "psr_p50"}
ASAGI_IYI = {"merkez_hata", "kesinti", "kurtarma_ort", "kurtarma_max",
             "id_switch", "gecikme_p50", "gecikme_p95", "e_ego_p95",
             "e_kest_p95", "sicrama_p95", "yanlis_kilit_orani",
             "kf_hiz_hatasi_p95"}
FPS_BANT = 0.05          # +-%5 gurultu bandi


def _fark(alan, a, b):
    """Doner: (fark, yon) - yon +1 iyilesme, -1 kotulesme, 0 farksiz."""
    if a is None or b is None:
        return None, 0
    d = b - a
    if alan == "fps":
        return d, (0 if abs(d) <= FPS_BANT * max(1e-9, a) else (1 if d > 0 else -1))
    if alan in YUKARI_IYI:
        return d, (0 if abs(d) < 1e-9 else (1 if d > 0 else -1))
    if alan in ASAGI_IYI:
        return d, (0 if abs(d) < 1e-9 else (1 if d < 0 else -1))
    return d, 0


def kiyas(a, b, alanlar=("iou", "basari@0.5", "merkez_hata", "kilit_orani",
                         "kesinti", "kurtarma_max", "id_switch", "t_drift",
                         "fps", "gecikme_p50", "gecikme_p95")):
    for hat in ("gazebo", "sim", "visdrone"):
        print(f"\n=== {hat.upper()} ===")
        bas = f"{'senaryo':22s}" + "".join(f"{x:>17s}" for x in alanlar)
        print(bas)
        print("-" * len(bas))
        toplam = {x: [0, 0] for x in alanlar}
        for ad in a[hat]:
            ra, rb = a[hat][ad], b[hat].get(ad)
            if rb is None:
                continue
            satir = f"{ad:22s}"
            for x in alanlar:
                va, vb = ra.get(x), rb.get(x)
                if x == "t_drift":
                    sa = "yok" if va is None else str(va)
                    sb = "yok" if vb is None else str(vb)
                    im = ""
                    if sa != sb:
                        iyi = (vb is None) or (va is not None and vb > va)
                        im = " +" if iyi else " -"
                        toplam[x][0 if iyi else 1] += 1
                    satir += f"{sa+'>'+sb+im:>17s}"
                    continue
                if va is None or vb is None:
                    satir += f"{'-':>17s}"
                    continue
                d, yon = _fark(x, va, vb)
                if yon > 0:
                    toplam[x][0] += 1
                elif yon < 0:
                    toplam[x][1] += 1
                im = "+" if yon > 0 else ("-" if yon < 0 else " ")
                bicim = "{:.3f}" if abs(vb) < 100 else "{:.1f}"
                satir += f"{bicim.format(vb)+' '+('%+.3f'%d if abs(d)<100 else '%+.1f'%d)+im:>17s}"
            print(satir)
        print(f"{'TOPLAM (iyi/kotu)':22s}" +
              "".join(f"{str(toplam[x][0])+'/'+str(toplam[x][1]):>17s}" for x in alanlar))


def main_():
    ap = argparse.ArgumentParser(description="A3.9 tek-degisiklik A-B kosucusu")
    ap.add_argument("--etiket", default=None, help="cikti/deney_<etiket>.json yaz")
    ap.add_argument("--kiyas", nargs=2, default=None, metavar=("ONCE", "SONRA"))
    ap.add_argument("--cekirdek", default="renk_dcf")
    ap.add_argument("--eksiz", action="store_true", help="Gazebo ek taramasini atla")
    a = ap.parse_args()

    if a.kiyas:
        yol = lambda e: e if e.endswith(".json") else f"cikti/deney_{e}.json"
        kiyas(json.load(open(yol(a.kiyas[0]))), json.load(open(yol(a.kiyas[1]))))
        return

    s = kos_hepsi(a.cekirdek, ek=not a.eksiz)
    if a.etiket:
        yol = f"cikti/deney_{a.etiket}.json"
        os.makedirs("cikti", exist_ok=True)
        with open(yol, "w") as f:
            json.dump(s, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nyazildi: {yol}  ({s['_sure_s']} s)")


if __name__ == "__main__":
    main_()
