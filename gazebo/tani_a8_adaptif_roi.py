"""A8 - ADAPTIF ROI: tasarim + SALT OKUNUR teshis.

KAPSAM
------
A8 bir SUREKLILIK / yeniden-tespit mekanizmasinin teshisidir, EDINME
mekanizmasinin DEGIL. Adaptif ROI bir onsel (konum + boyut) gerektirir;
soguk baslangicta onsel yoktur. A7 §3: "eksik olan cozunurluk degil,
konum bilgisi." Edinme bosluu A8'in konusu degildir.

BUYUTME ARITMETIGI (olculmez, turetilir)
----------------------------------------
A7 tanimi: seviye L = hedefin TAM KAREDE agdaki px boyu; sensorde hedef 2L px.
ROI kolunda mutlak olcek AG_W/R.

    ag_px = L_sensor * AG_W / R          R_opt = L_sensor * AG_W / NET_HEDEF

Merdiven {640,320,160} ile 60-90 bandi:
    R=640 (2x) -> net 2L -> L 30.0-45.0
    R=320 (4x) -> net 4L -> L 15.0-22.5
    R=160 (8x) -> net 8L -> L  7.5-11.25
BOSLUKLAR: L 11.25-15 ve L 22.5-30.
R=80 (16x) A7'DE OLCULMEDI; 5x5'in bir sansi olup olmadigini gormek icin
merdivene YENI BASAMAK olarak eklendi ve raporda ayrica etiketlenir.

KOLLAR
------
tam_kare        : referans (A7 ile ayni)
sabit_R320_kf   : R sabit 320, merkez takipciden  -> A7'nin roi320_takipci'si
adaptif_kf      : R takipci BOYUT tahmininden, merkez takipciden   <- ASIL KOL
oracle_merkez   : R takipci tahmininden, merkez GT   -> MERKEZ hatasini izole eder
oracle_boyut    : R GT boyutundan, merkez takipciden -> BOYUT hatasini izole eder
oracle_tam      : ikisi de GT                        -> mutlak tavan

oracle_* kollari BASARI DEGILDIR, ust sinirdir.
oracle_merkez / oracle_boyut ayrimi A8'in omurgasidir: hangi hata kanalinin
kac puan yedigini ayristirir (A3.9'daki tavan_iou mantigi).

EGO KOLU DUSURULDU - GEREKCESI
------------------------------
Revize plan bir `adaptif_ego` kolu ongoruyordu. Bu test yataginda ANLAMSIZ:
A5.2 kompoziti arkaplan penceresini SABIT tutar ("Arkaplan penceresi SABIT ->
kamera ego-hareketi yok", bench dosyasi satir 60). Ego homografisi birim
matrise yakindir ve hareket eden hedefi takip edemez. Ego tabanli merkez
ongorusu ancak gercek kamera hareketi olan bir yatakta (Gazebo / ham VisDrone)
olculebilir. DUSURULDU ve raporda boyle yazildi.

ACIK CEVRIM - ZORUNLU UYARI
---------------------------
Dedektor sonucu takipciyi BESLEMEZ. Takipci kendi DCF olcumuyle bagimsiz kosar
(A7'nin takipci kolundaki gibi). Bu salt-okunurlugu korur ama sunu da demektir:
OLCULEN HER SAYI BIR UST SINIRDIR. Gercek sistemde ROI'den gelen tespit
takipciyi besleyecek, takipci boyutu guncelleyecek, boyut R'yi secece
-> CEVRIM KAPANIR.
Deney 1/3/4A/4S/4U dersi ve 4T/4U ust-sinir dersi (ROC AUC 0.89 -> kapali
cevrimde IoU 0.548->0.190) burada da gecerlidir.

DEGISTIRILMEYENLER: takip/*.py, gazebo/bench_a52_kucuk_hedef.py, agirliklar.
Bench modul olarak import edilir, duzenlenmez.
"""
import importlib.util as iu
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def _yukle(ad, dosya):
    sp = iu.spec_from_file_location(ad, os.path.join(HERE, dosya))
    m = iu.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


A7 = _yukle("A7", "tani_a7_roi.py")
B = A7.B

from calistir import iou                                   # noqa: E402
from takip.izleyici import KILITLI, HedefTakip             # noqa: E402

SENSOR = A7.SENSOR                 # (1280, 720)
AG = A7.AG                         # (640, 360)
MERDIVEN = [640, 320, 160, 80]     # sensor px ROI genisligi
YENI_BASAMAK = {80}                # A7'de OLCULMEDI
NET_HEDEF = 75.0
BANT = (60.0, 90.0)
N_KARE = A7.N_KARE                 # 60
MODELLER = A7.MODELLER

SEVIYELER = [40, 30, 20, 15, 10, 8, 5]
SEVIYE_AD = {40: "40x15", 30: "30x12", 20: "20x10", 15: "15x7",
             10: "10x5", 8: "8x5", 5: "5x5"}
SEVIYE_ROL = {40: "pozitif_kontrol", 30: "pozitif_kontrol", 20: "pozitif_kontrol",
              15: "asil", 10: "asil", 8: "asil", 5: "negatif_kontrol"}

KOLLAR = ["tam_kare", "sabit_R320_kf", "adaptif_kf",
          "oracle_merkez", "oracle_boyut", "oracle_tam"]
ORACLE_KOL = {"oracle_merkez", "oracle_boyut", "oracle_tam"}


# ------------------------------------------------------------------ istatistik
def p(v, q):
    return round(float(np.percentile(v, q)), 3) if len(v) else None


def ort(v, k=4):
    return round(float(np.mean(v)), k) if len(v) else None


# ------------------------------------------------------------------- ROI secim
def roi_wh(R):
    """ROI dikdortgeni; AG en-boy orani (16:9) korunur."""
    return int(R), int(round(R * 9.0 / 16.0))


def R_sec(L_sensor):
    """Merdivenden hedefi aga NET_HEDEF px'e EN YAKIN getiren basamagi sec.

    Yakinlik LOG uzayinda olculur: buyutme carpimsal bir buyukluktur, ve
    bandin kendisi (60-90) 75 etrafinda carpimsal olarak simetriktir.
    """
    if L_sensor is None or not np.isfinite(L_sensor) or L_sensor <= 0:
        return MERDIVEN[0]
    return min(MERDIVEN,
               key=lambda R: abs(np.log((L_sensor * AG[0] / float(R)) / NET_HEDEF)))


def roi_tespit(model, sensor, merkez, R):
    """SENSOR'den R genisliginde kirp -> AG boyuna getir -> YOLO -> sensor koord.

    A7'nin roi_tespit'i ile ayni geometri; tek fark R'nin serbest olmasi ve
    kirpma dikdortgeninin (kadraj sinirina KENETLENMIS hali) geri donmesi.
    Kenar payi bu GERCEK dikdortgenden hesaplanir, istenen merkezden degil.
    """
    SW, SH = SENSOR
    AW, AH = AG
    rw, rh = roi_wh(R)
    x0 = int(round(merkez[0] - rw / 2.0))
    y0 = int(round(merkez[1] - rh / 2.0))
    x0 = max(0, min(SW - rw, x0))
    y0 = max(0, min(SH - rh, y0))
    parca = sensor[y0:y0 + rh, x0:x0 + rw]
    if parca.shape[:2] != (rh, rw):
        return [], [], 0.0, (x0, y0, rw, rh)
    interp = cv2.INTER_LINEAR if rw < AW else cv2.INTER_AREA
    girdi = cv2.resize(parca, (AW, AH), interpolation=interp)
    kutular, guvenler, ms = B.yolo_calistir(model, girdi)
    kx, ky = rw / float(AW), rh / float(AH)
    geri = [np.array([k[0] * kx + x0, k[1] * ky + y0, k[2] * kx, k[3] * ky],
                     np.float32) for k in kutular]
    return geri, guvenler, ms, (x0, y0, rw, rh)


# --------------------------------------------------------------- takipci onseli
def takipci_yorunge(dizi):
    """Takipciyi dizi boyunca BIR KEZ kosar; kare basina (merkez, boyut) onseli.

    t=0'da GT ile kilitlenir (senaryo B: onceden kilit VAR). t>0'da yalnizca
    kendi olcumuyle ilerler - GT'ye BAKMAZ. Tum kollar bu ayni yorungeyi
    kullanir; boylece kollar arasindaki fark yalnizca ROI secimidir.
    """
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    k0 = tak.kutu
    yor = [{"merkez": np.asarray(k0[:2] + k0[2:] / 2.0, np.float64),
            "L": float(max(k0[2], k0[3])), "durum": str(tak.durum),
            "psr": float(tak.psr), "var": True}]
    for t in range(1, len(dizi)):
        s = tak.guncelle(dizi[t][0])
        k = s["kutu"]
        if k is None:
            e = dict(yor[-1])
            e["var"] = False
            e["durum"] = str(s["durum"])
            e["psr"] = float(s["psr"])
            yor.append(e)
        else:
            yor.append({"merkez": np.asarray(k[:2] + k[2:] / 2.0, np.float64),
                        "L": float(max(k[2], k[3])), "durum": str(s["durum"]),
                        "psr": float(s["psr"]), "var": True})
    return yor


# ---------------------------------------------------------------------- kol
def kol_olc(model, dizi, yor, kol, kayit=False):
    """Bir kolu dizi boyunca kosar. GT yalniz ANALIZ icin okunur; operasyonel
    kollarda ROI secimine GT girmez."""
    n = vur05 = vur0 = fp = fn = 0
    iou_l, guv_l, ms_l = [], [], []
    mh_l, bho_l, gag_l, bag_l = [], [], [], []
    kaps_l, payx_l, payy_l, bant_l = [], [], [], []
    R_say = {}
    ilk_kapsama_hatasi = None
    satir = []
    for t, (img, gt) in enumerate(dizi):
        gc = gt[:2] + gt[2:] / 2.0
        gL = float(max(gt[2], gt[3]))
        e = yor[t]
        eC, eL = e["merkez"], e["L"]
        mh = float(np.hypot(eC[0] - gc[0], eC[1] - gc[1]))
        bho = float(eL / gL) if gL > 0 else None

        if kol == "tam_kare":
            kutular, guvenler, ms = A7.tam_kare_tespit(model, img)
            rect = (0, 0, SENSOR[0], SENSOR[1])
            R = None
            gag = gL * 0.5                      # tam kare letterbox olcegi
            bag = eL * 0.5
        else:
            merkez = gc if kol in ("oracle_merkez", "oracle_tam") else eC
            L_R = gL if kol in ("oracle_boyut", "oracle_tam") else eL
            R = 320 if kol == "sabit_R320_kf" else R_sec(L_R)
            kutular, guvenler, ms, rect = roi_tespit(model, img, merkez, R)
            gag = gL * AG[0] / float(R)         # GERCEK agdaki hedef px
            bag = eL * AG[0] / float(R)         # kuralin BEKLEDIGI px
        R_say[str(R)] = R_say.get(str(R), 0) + 1

        x0, y0, rw, rh = rect
        kaps = bool(gt[0] >= x0 and gt[1] >= y0 and
                    gt[0] + gt[2] <= x0 + rw and gt[1] + gt[3] <= y0 + rh)
        payx = float((rw / 2.0 - abs(gc[0] - (x0 + rw / 2.0)) - gt[2] / 2.0) / (rw / 2.0))
        payy = float((rh / 2.0 - abs(gc[1] - (y0 + rh / 2.0)) - gt[3] / 2.0) / (rh / 2.0))
        if not kaps and ilk_kapsama_hatasi is None:
            ilk_kapsama_hatasi = t

        n += 1
        ms_l.append(ms)
        mh_l.append(mh)
        if bho is not None:
            bho_l.append(bho)
        gag_l.append(gag)
        bag_l.append(bag)
        kaps_l.append(1 if kaps else 0)
        payx_l.append(payx)
        payy_l.append(payy)
        bant_l.append(1 if BANT[0] <= gag <= BANT[1] else 0)

        es = [(float(iou(k, gt)), k, g) for k, g in zip(kutular, guvenler)]
        iy = max(es, key=lambda z: z[0]) if es else (0.0, None, 0.0)
        fp += sum(1 for z in es if z[0] <= 0.0)
        if iy[0] > 0.0:
            vur0 += 1
            iou_l.append(iy[0])
            guv_l.append(iy[2])
            if iy[0] >= 0.5:
                vur05 += 1
        else:
            fn += 1
        if kayit:
            satir.append({"t": t, "gt_L_sensor": round(gL, 2),
                          "est_L_sensor": round(float(eL), 2),
                          "boyut_hata_orani": round(bho, 4) if bho else None,
                          "merkez_hata_px": round(mh, 2),
                          "R": R, "buyutme": round(AG[0] / float(R), 3) if R else 0.5,
                          "beklenen_ag_px": round(bag, 1),
                          "gercek_ag_px": round(gag, 1),
                          "bant_ici": bool(BANT[0] <= gag <= BANT[1]),
                          "kapsandi": kaps,
                          "kenar_payi_x": round(payx, 4),
                          "kenar_payi_y": round(payy, 4),
                          "iou": round(float(iy[0]), 4),
                          "takipci_durum": e["durum"], "psr": round(e["psr"], 2)})
    d = {"kare": n, "oracle": kol in ORACLE_KOL,
         "recall_iou50": round(vur05 / n, 4) if n else None,
         "recall_iou0": round(vur0 / n, 4) if n else None,
         "ort_iou": ort(iou_l), "ort_guven": ort(guv_l), "fp": fp, "fn": fn,
         "merkez_hata_p50": p(mh_l, 50), "merkez_hata_p95": p(mh_l, 95),
         "merkez_hata_ort": ort(mh_l, 2),
         "boyut_hata_orani_p50": p(bho_l, 50), "boyut_hata_orani_p95": p(bho_l, 95),
         "boyut_hata_orani_p05": p(bho_l, 5),
         "beklenen_ag_px_p50": p(bag_l, 50),
         "gercek_ag_px_p50": p(gag_l, 50), "gercek_ag_px_p05": p(gag_l, 5),
         "gercek_ag_px_p95": p(gag_l, 95),
         "bant_ici_orani": ort(bant_l), "kapsama_orani": ort(kaps_l),
         "kenar_payi_x_p50": p(payx_l, 50), "kenar_payi_x_p05": p(payx_l, 5),
         "kenar_payi_y_p50": p(payy_l, 50), "kenar_payi_y_p05": p(payy_l, 5),
         "ilk_kapsama_hatasi_karesi": ilk_kapsama_hatasi,
         "R_dagilimi": R_say,
         "gecikme_ort_ms": ort(ms_l, 2), "gecikme_p95_ms": p(ms_l, 95)}
    if kayit:
        d["kareler"] = satir
    return d


# ------------------------------------------------- YATAK D: daralan sensor dizi
def daralan_sensor_dizi(kareler, hucre, L_bas, L_son, n):
    """1280x720 SENSOR tuvalinde hedef L_bas -> L_son px'e (AG olceginde)
    geometrik kuculur. A7'nin daralan_dizi'si B.TUVAL=640x360'ta kuruluyordu;
    ROI icin kirpilacak native piksel birakmiyordu (A7 §1'de reddedilen hata).
    """
    SW, SH = SENSOR
    g0 = kareler[0][1]
    L0 = max(float(g0[2]), float(g0[3]))
    c0 = g0[:2] + g0[2:] / 2.0
    pk = np.array([SW / 2.0, SH / 2.0])
    onceki = c0
    dizi, seviye = [], []
    for t, (img, gt, _e, _W, _H) in enumerate(kareler[:n]):
        L_t = L_bas * (L_son / L_bas) ** (t / max(1, n - 1))
        s = (2.0 * L_t) / L0
        x, y, w, h = [int(round(v)) for v in gt]
        chip = img[max(0, y):y + h, max(0, x):x + w]
        if chip.size == 0 or chip.shape[0] < 2 or chip.shape[1] < 2:
            break
        nw = max(1, int(round(chip.shape[1] * s)))
        nh = max(1, int(round(chip.shape[0] * s)))
        interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR
        chip = cv2.resize(chip, (nw, nh), interpolation=interp)
        arka = img[hucre[1]:hucre[1] + SH, hucre[0]:hucre[0] + SW]
        if arka.shape[:2] != (SH, SW):
            break
        c = gt[:2] + gt[2:] / 2.0
        pk = pk + (c - onceki) * s
        onceki = c
        tuval, gt_yeni = B.yapistir(arka, chip, pk[0], pk[1])
        if tuval is None:
            break
        dizi.append((tuval, gt_yeni))
        seviye.append(round(float(L_t), 2))
    return dizi, seviye


# --------------------------------------------------------------- merdiven tablo
def merdiven_tablosu():
    t = []
    for R in MERDIVEN:
        b = AG[0] / float(R)                       # sensor->ag mutlak olcek
        t.append({"R_sensor_px": R, "roi": list(roi_wh(R)),
                  "buyutme_tam_kareye_gore": round(b / 0.5, 2),
                  "ag_px_carpani_seviyeye_gore": round(2.0 * b, 2),
                  "bant_L_alt": round(BANT[0] / (2.0 * b), 2),
                  "bant_L_ust": round(BANT[1] / (2.0 * b), 2),
                  "A7de_olculdu": R not in YENI_BASAMAK})
    return t


# ------------------------------------------------------------------------ main
def main():
    import torch
    torch.set_num_threads(8)
    from ultralytics import YOLO

    cikti = {
        "asama": "A8 - Adaptif ROI tasarim + salt okunur teshis",
        "kapsam": ("SUREKLILIK / yeniden-tespit teshisi. EDINME degil: adaptif "
                   "ROI onsel (konum+boyut) gerektirir, soguk baslangicta onsel yok."),
        "acik_cevrim_uyarisi": ("Dedektor takipciyi BESLEMEZ. Olculen her sayi bir "
                                "UST SINIRDIR; kapali cevrimde bozulur (4T/4U dersi)."),
        "protokol": {
            "a52_dosyasi": "gazebo/bench_a52_kucuk_hedef.py",
            "a52_degistirilmedi": True,
            "a7_dosyasi": "gazebo/tani_a7_roi.py", "a7_degistirilmedi": True,
            "sensor_tuvali": list(SENSOR), "ag_karesi": list(AG),
            "tam_kare_letterbox_olcegi": 0.5,
            "seviye_tanimi": "hedefin TAM KAREDE ag girdisindeki px boyu (A5.2 ile ayni)",
            "merdiven": merdiven_tablosu(),
            "merdiven_bosluklari_L": [[11.25, 15.0], [22.5, 30.0]],
            "net_hedef_px": NET_HEDEF, "bant": list(BANT),
            "conf": B.CONF, "imgsz": B.IMGSZ, "kare": N_KARE, "cihaz": "cpu",
            "ego_kolu": "DUSURULDU - A5.2 yataginda arkaplan penceresi sabit, "
                        "kamera ego-hareketi yok; ego merkez ongorusu anlamsiz.",
        },
        "kollar": KOLLAR, "modeller": {},
    }

    for mad, (agirlik, siniflar) in MODELLER.items():
        B.AGIRLIK, B.SINIFLAR = agirlik, siniflar
        model = YOLO(agirlik)
        B.yolo_calistir(model, np.zeros((AG[1], AG[0], 3), np.uint8))
        print(f"\n===== {mad} ({agirlik}) siniflar={siniflar} =====", flush=True)
        md = {"agirlik": agirlik, "siniflar": siniflar, "diziler": {}}
        for dizi_ad, tid, rol in B.DIZILER:
            kareler = B.kareleri_topla(dizi_ad, tid, N_KARE)
            W, H = kareler[0][3], kareler[0][4]
            ad = f"{dizi_ad}/{tid}"
            if W < SENSOR[0] or H < SENSOR[1]:
                print(f"  --- {ad}: kare {W}x{H} sensor tuvalinden kucuk, ATLANDI")
                md["diziler"][ad] = {"rol": rol, "kare_boyutu": [W, H],
                                     "atlandi": "kare sensor tuvalinden kucuk"}
                continue
            hucre, _u = B.arkaplan_hucresi(kareler, W, H, *SENSOR)
            dd = {"rol": rol, "kare_boyutu": [W, H], "arkaplan_hucre": list(hucre),
                  "seviyeler": {}}
            print(f"  --- {ad} ({rol}) sensor hucresi {hucre} ---", flush=True)

            for L in SEVIYELER:
                sad = SEVIYE_AD[L]
                d, s = A7.sensor_dizi(kareler, hucre, L, N_KARE)
                if len(d) < 10:
                    dd["seviyeler"][sad] = {"not": "dizi 10 kareden kisa"}
                    continue
                yor = takipci_yorunge(d)
                gL = float(np.mean([max(g[2], g[3]) for _i, g in d]))
                r = {"seviye_L": L, "rol": SEVIYE_ROL[L], "olcek_s": round(s, 4),
                     "kare": len(d), "gt_L_sensor_ort": round(gL, 1),
                     "gt_L_ag_tam_kare": round(gL * 0.5, 1),
                     "R_opt_ideal": round(gL * AG[0] / NET_HEDEF, 1)}
                for kol in KOLLAR:
                    r[kol] = kol_olc(model, d, yor, kol,
                                     kayit=(kol in ("adaptif_kf", "sabit_R320_kf")))
                dd["seviyeler"][sad] = r
                q = lambda k: r[k]["recall_iou50"]
                a = r["adaptif_kf"]
                print(f"    {sad:6s} agda{r['gt_L_ag_tam_kare']:5.1f}px R_ideal="
                      f"{r['R_opt_ideal']:6.1f} | recall@.5 tam={q('tam_kare'):.3f} "
                      f"sabit320={q('sabit_R320_kf'):.3f} ADAPTIF={q('adaptif_kf'):.3f} "
                      f"[oM={q('oracle_merkez'):.3f} oB={q('oracle_boyut'):.3f} "
                      f"oT={q('oracle_tam'):.3f}] | mh_p95={a['merkez_hata_p95']} "
                      f"bho_p95={a['boyut_hata_orani_p95']} bant={a['bant_ici_orani']} "
                      f"kaps={a['kapsama_orani']} R={a['R_dagilimi']}", flush=True)

            # ---- YATAK D: sensor cozunurlugunde DARALAN dizi (57->5)
            dz, sev = daralan_sensor_dizi(kareler, hucre, 40.0, 5.0, N_KARE)
            if len(dz) >= 10:
                yor_d = takipci_yorunge(dz)
                dd["daralan"] = {"kare": len(dz), "seviye_serisi": sev,
                                 "L_bas": sev[0], "L_son": sev[-1]}
                for kol in ["tam_kare", "sabit_R320_kf", "adaptif_kf", "oracle_tam"]:
                    dd["daralan"][kol] = kol_olc(model, dz, yor_d, kol,
                                                 kayit=(kol == "adaptif_kf"))
                da = dd["daralan"]["adaptif_kf"]
                print(f"    DARALAN {sev[0]:.0f}->{sev[-1]:.0f}px  recall@.5 "
                      f"tam={dd['daralan']['tam_kare']['recall_iou50']:.3f} "
                      f"sabit320={dd['daralan']['sabit_R320_kf']['recall_iou50']:.3f} "
                      f"ADAPTIF={da['recall_iou50']:.3f} "
                      f"oracle={dd['daralan']['oracle_tam']['recall_iou50']:.3f} | "
                      f"bant={da['bant_ici_orani']} kaps={da['kapsama_orani']} "
                      f"ilk_kapsama_hatasi={da['ilk_kapsama_hatasi_karesi']} "
                      f"R={da['R_dagilimi']}", flush=True)
            md["diziler"][ad] = dd
        cikti["modeller"][mad] = md

    os.makedirs("cikti", exist_ok=True)
    yol = sys.argv[1] if len(sys.argv) > 1 else "cikti/a8_adaptif_roi_teshis.json"
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
