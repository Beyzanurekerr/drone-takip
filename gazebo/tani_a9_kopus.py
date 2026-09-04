"""A9 ASAMA 2 - ERKEN KOPUS TESPITI (SALT OKUNUR TESHIS).

*** ACIK CEVRIM · TESHIS · GT YALNIZCA OFFLINE ETIKETLEME ***

A/B YOK. ESIK SECILMEZ. TRACKER DAVRANISI DEGISMEZ. takip/ DEGISMEZ.

AMAC
----
Iki ariza modunu MUMKUN OLDUGUNCA ERKEN ve BIRBIRINDEN BAGIMSIZ tespit
edebilecek MEVCUT sinyalleri olcmek.

  MOD A: boyut/DCF bozulmasi -> PSR dususu -> olcum kaybi -> Kalman coast
         -> merkez kacisi
  MOD B: PSR yuksek kalirken yanlis hedefe kayma / yanlis kilit

Kopusu YALNIZCA PSR ile tanimlamiyoruz; tek sinyalin iki modu da yakaladigini
VARSAYMIYORUZ - bu olculecek bir sey.

OLCUM KONVANSIYONLARI (onerilen calisma esigi DEGIL, sinyalleri kiyaslanabilir
kilan tanisal kurallar)
-----------------------------------------------------------------------------
K1. "ilk bozulma karesi": sinyalin, o hucrenin ILK 5 karesinden hesaplanan
    kendi tabanina gore 3 sigma bozulma yonunde saptigi ilk kare (t>5).
    sigma=0 ise eps=1e-6.
K2. "onceleme (lead)" = kopus_karesi - ilk_bozulma_karesi. Pozitif = ERKEN uyari.
K3. Ayirma gucu ESIKSIZ olculur: ROC AUC (siralama tabanli).
    Pozitif = kopan hucrelerde kopustan onceki W=10 kare.
    Negatif = SAGLAM dizilerin TUM kareleri.
K4. Yanlis alarm = saglam dizilerde K1 kuralinin ateslediği hucre orani.
    ROC egrisi ayrica FPR@TPR=0.5/0.8/0.95 ile nitelenir; bunlar EGRIYI
    TANIMLAR, calisma noktasi ONERMEZ.

bho HAKKINDA
------------
Kullanici talimati: bho erken haberci olabilir ama GT'den turetilmis GERCEK
boyut olarak degil, TAKIPCI BOYUT TAHMINI olarak raporlanacak.
  * `boyut_orani`  = tak.boyut.max() / KILIT anindaki boyut  -> OPERASYONEL,
                     GT icermez. Asama 2'nin aday sinyali BUDUR.
  * `bho_gt`       = tak.boyut.max() / GT_L -> yalnizca OFFLINE ETIKETLEME,
                     aday sinyal DEGIL, ayri etiketlenir.

takip/ DEGISMEZ: Kalman sarmalayicisi ve rafine_kutu kaydedicisi salt okunur.
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
import takip.izleyici as IZ                                # noqa: E402
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
W_ONCE = 10          # K3: kopustan onceki pencere
_ORIG_RAFINE = IZ.rafine_kutu

# sinyal -> (bozulma yonu, turetilmis mi, aciklama)
SINYALLER = {
    "psr":              (-1, "tracker ici", "DCF tepe kalitesi (cekirdek dondurur)"),
    "psr_norm":         (-1, "TURETILMIS", "psr / kendi kosan medyani (ilk 5 kare)"),
    "boyut_orani":      (+1, "tracker ici", "tak.boyut.max()/kilit boyutu - OPERASYONEL"),
    "rafine_none_kosan":(+1, "tracker ici", "rafine_kutu None donme orani (kosan)"),
    "P_konum_iz":       (+1, "tracker ici", "Kalman konum kovaryans izi"),
    "dcf_sicrama":      (+1, "tracker ici", "|z_dcf - kf.konum| duzeltmeden once"),
    "dcf_kf_ayrim":     (+1, "tracker ici", "|z_dcf - kf.konum| / boyut.max()"),
    "kayip":            (+1, "tracker ici", "ardisik olcumsuz kare sayaci"),
    "durum_disi":       (+1, "tracker ici", "durum != KILITLI (0/1)"),
    "benzerlik":        (-1, "tracker ici", "imza dogrulama skoru"),
    "ego_guven":        (-1, "tracker ici", "ego-motion cozum guveni"),
    "ego_olcek_sapma":  (+1, "tracker ici", "|olcek - 1|"),
    "olcum_yok":        (+1, "tracker ici", "o karede DCF duzeltmesi olmadi (0/1)"),
}


def _y(L, yon):
    """Bozulma yonune gore isaretle: buyuk deger = daha bozuk olsun."""
    return [None if (x is None or not np.isfinite(x)) else yon * x for x in L]


def _auc(poz, neg):
    """Siralama tabanli ROC AUC (esiksiz)."""
    poz = [x for x in poz if x is not None and np.isfinite(x)]
    neg = [x for x in neg if x is not None and np.isfinite(x)]
    if not poz or not neg:
        return None
    h = np.concatenate([poz, neg])
    r = np.argsort(np.argsort(h)) + 1.0
    # esitlikler icin ortalama rank
    _, ters, say = np.unique(h, return_inverse=True, return_counts=True)
    top = np.zeros(len(say)); np.add.at(top, ters, r)
    r = (top / say)[ters]
    n1, n0 = len(poz), len(neg)
    return round(float((r[:n1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)), 4)


def _fpr_at_tpr(poz, neg, hedef):
    poz = np.array([x for x in poz if x is not None and np.isfinite(x)])
    neg = np.array([x for x in neg if x is not None and np.isfinite(x)])
    if not len(poz) or not len(neg):
        return None
    esik = np.percentile(poz, 100 * (1 - hedef))     # TPR=hedef veren esik
    return round(float((neg >= esik).mean()), 4)


def _ilk_bozulma(seri, yon):
    """K1: ilk 5 kareye gore 3 sigma bozulma yonunde sapan ilk kare (t>5)."""
    s = np.asarray([np.nan if v is None else v for v in seri], float)
    if len(s) < 8 or not np.isfinite(s[:5]).any():
        return None
    tab = s[:5][np.isfinite(s[:5])]
    mu, sd = float(tab.mean()), float(tab.std())
    sd = max(sd, 1e-6)
    for i in range(5, len(s)):
        if not np.isfinite(s[i]):
            continue
        if yon * (s[i] - mu) > 3.0 * sd:
            return i + 1                       # kare indeksi 1'den basliyor
    return None


def hucre_olc(dizi):
    """Bir hucreyi bir kez kosar; kare basina TUM sinyalleri kaydeder."""
    tak = HedefTakip()
    tak.kilitle(dizi[0][0], dizi[0][1].copy())
    kilit_boyut = float(np.max(tak.boyut))
    log = []
    sar = A9.KayitKalman(tak.kf, log)
    object.__setattr__(sar, "_tak", tak)
    tak.kf = sar

    raf = []

    def _rafine_kayitli(bgr, merkez, boyut, **kw):
        r = _ORIG_RAFINE(bgr, merkez, boyut, **kw)
        raf.append(r is None)
        return r

    IZ.rafine_kutu = _rafine_kayitli
    kareler = []
    kopus_kare, ard = None, 0
    psr_gecmis = []
    try:
        for t in range(1, len(dizi)):
            img, gt = dizi[t]
            gc = (gt[:2] + gt[2:] / 2.0).astype(np.float64)
            gL = float(max(gt[2], gt[3]))
            object.__setattr__(sar, "_gt", gc)
            n0, r0 = len(log), len(raf)
            s = tak.guncelle(img)

            olaylar = log[n0:]
            dcf = [e for e in olaylar if e["kaynak"] == "_takip_adimi"]
            duz = [e for e in dcf if e["tip"] == "duzelt"]
            sic = duz[0]["sicrama_px"] if duz else None
            boy = float(np.max(tak.boyut))
            psr = float(s["psr"])
            psr_gecmis.append(psr)
            tab5 = np.median(psr_gecmis[:5]) if len(psr_gecmis) >= 5 else np.median(psr_gecmis)
            hata = float(np.linalg.norm(tak.kf.konum - gc))
            o = float(iou(s["kutu"], gt)) if s["kutu"] is not None else 0.0

            kareler.append({
                "t": t,
                # --- ADAY SINYALLER (operasyonel, GT icermez) ---
                "psr": round(psr, 3),
                "psr_norm": round(psr / max(tab5, 1e-6), 4),
                "boyut_orani": round(boy / max(kilit_boyut, 1e-6), 4),
                "rafine_none_kosan": round(float(np.mean(raf)) if raf else 0.0, 4),
                "P_konum_iz": round(float(tak.kf.P[0, 0] + tak.kf.P[1, 1]), 3),
                "dcf_sicrama": None if sic is None else round(float(sic), 3),
                "dcf_kf_ayrim": None if sic is None else round(float(sic) / max(boy, 1e-6), 4),
                "kayip": int(s["kayip"]),
                "durum_disi": 0 if s["durum"] == KILITLI else 1,
                "benzerlik": round(float(s["benzerlik"]), 4),
                "ego_guven": round(float(s["ego_guven"]), 4),
                "ego_olcek_sapma": round(abs(float(s["olcek"]) - 1.0), 5),
                "olcum_yok": 0 if duz else 1,
                # --- OFFLINE ETIKET (GT) - ADAY SINYAL DEGIL ---
                "_etiket_hata_px": round(hata, 2),
                "_etiket_iou": round(o, 4),
                "_etiket_bho_gt": round(boy / gL, 4) if gL > 0 else None,
                "_etiket_durum": str(s["durum"]),
            })
            if hata > A9.KOPUS_KAT * gL:
                ard += 1
                if ard >= A9.KOPUS_SABIR and kopus_kare is None:
                    kopus_kare = t - A9.KOPUS_SABIR + 1
            else:
                ard = 0
    finally:
        IZ.rafine_kutu = _ORIG_RAFINE

    # --- MOD etiketi (offline, GT ile) ---
    mod = None
    if kopus_kare is not None:
        son = [k for k in kareler if k["t"] >= kopus_kare]
        kabul_orani = 1.0 - float(np.mean([k["olcum_yok"] for k in son])) if son else 0.0
        gy = sum(1 for k in son if k["_etiket_durum"] == KILITLI and k["_etiket_iou"] < 0.2)
        mod = {"dcf_kabul_orani_kopus_sonrasi": round(kabul_orani, 4),
               "guvenli_yanlis_kopus_sonrasi": gy,
               "psr_p50_kopus_sonrasi": round(float(np.median([k["psr"] for k in son])), 2)}
    return {"kopus_karesi": kopus_kare, "kilit_boyut": round(kilit_boyut, 2),
            "mod_olcumleri": mod, "kareler": kareler}


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
    hucreler = {}
    for dizi_ad, tid in DIZILER:
        ad = f"{dizi_ad}/{tid}"
        kareler = topla(dizi_ad, tid, N_KARE)
        W, H = kareler[0][3], kareler[0][4]
        hucre, _ = B.arkaplan_hucresi(kareler, W, H, *SENSOR)
        rol = "KOPAN" if ad in KOPAN else "saglam"
        print(f"\n--- {ad} [{rol}] ---", flush=True)
        for L in SEVIYELER:
            d, s = A7.sensor_dizi(kareler, hucre, L, N_KARE)
            if len(d) < 10:
                continue
            r = hucre_olc(d)
            r["dizi"], r["seviye"], r["rol"] = ad, SEVIYE_AD[L], rol
            hucreler[f"{ad}|{SEVIYE_AD[L]}"] = r
            print(f"  {SEVIYE_AD[L]:6s} kopus={str(r['kopus_karesi']):>5} "
                  f"mod_olc={r['mod_olcumleri']}", flush=True)

    # ---------------- MOD ETIKETLEME (offline) ----------------
    kopan_h = {k: v for k, v in hucreler.items() if v["kopus_karesi"] is not None}
    kab = {k: v["mod_olcumleri"]["dcf_kabul_orani_kopus_sonrasi"] for k, v in kopan_h.items()}
    # veri kendi ayrimini gostersin: medyanla degil, gozlenen bimodalliga bak
    sirali = sorted(kab.values())
    print(f"\nkopus sonrasi DCF kabul orani (kopan hucreler, sirali): "
          f"{[round(x,2) for x in sirali]}")
    for k, v in kopan_h.items():
        v["mod"] = "B" if kab[k] >= 0.8 else "A"
    modA = [k for k, v in kopan_h.items() if v["mod"] == "A"]
    modB = [k for k, v in kopan_h.items() if v["mod"] == "B"]
    print(f"MOD A hucre: {len(modA)}  MOD B hucre: {len(modB)}")

    # ---------------- SINYAL ANALIZI ----------------
    saglam_h = {k: v for k, v in hucreler.items() if v["rol"] == "saglam"}
    sinyal_ozet = {}
    for sad, (yon, tur, acik) in SINYALLER.items():
        poz, neg = [], []
        for k, v in kopan_h.items():
            kf = v["kopus_karesi"]
            poz += [x[sad] for x in v["kareler"] if kf - W_ONCE <= x["t"] < kf]
        for k, v in saglam_h.items():
            neg += [x[sad] for x in v["kareler"]]
        # mod ayrimi: kopus SONRASI kareler
        ma, mb = [], []
        for k in modA:
            ma += [x[sad] for x in hucreler[k]["kareler"] if x["t"] >= hucreler[k]["kopus_karesi"]]
        for k in modB:
            mb += [x[sad] for x in hucreler[k]["kareler"] if x["t"] >= hucreler[k]["kopus_karesi"]]
        # ilk bozulma + onceleme
        lead, bozulma_kopan, bozulma_saglam = [], 0, 0
        for k, v in kopan_h.items():
            ib = _ilk_bozulma([x[sad] for x in v["kareler"]], yon)
            if ib is not None:
                bozulma_kopan += 1
                lead.append(v["kopus_karesi"] - ib)
        for k, v in saglam_h.items():
            if _ilk_bozulma([x[sad] for x in v["kareler"]], yon) is not None:
                bozulma_saglam += 1
        def dag(L):
            v = [x for x in L if x is not None and np.isfinite(x)]
            return {"p05": A9.p(v, 5), "p50": A9.p(v, 50), "p95": A9.p(v, 95)} if v else None
        sinyal_ozet[sad] = {
            "bozulma_yonu": "artis" if yon > 0 else "azalis",
            "turetilmis_mi": tur, "aciklama": acik,
            "auc_kopus_onu_vs_saglam": _auc(_y(poz, yon), _y(neg, yon)),
            "auc_notu": "bozulma yonune gore YONLENDIRILDI; 0.5=ayirmiyor, 1.0=kusursuz",
            "fpr_at_tpr50": _fpr_at_tpr(_y(poz, yon), _y(neg, yon), 0.50),
            "fpr_at_tpr80": _fpr_at_tpr(_y(poz, yon), _y(neg, yon), 0.80),
            "fpr_at_tpr95": _fpr_at_tpr(_y(poz, yon), _y(neg, yon), 0.95),
            "auc_modA_vs_modB": _auc(_y(ma, yon), _y(mb, yon)),
            "auc_modAB_notu": "bozulma yonunde P(ModA>ModB); 0.5=iki modu ayirmiyor",
            "dagilim_saglam": dag(neg), "dagilim_kopus_onu": dag(poz),
            "dagilim_modA": dag(ma), "dagilim_modB": dag(mb),
            "onceleme_kare_p50": A9.p(lead, 50) if lead else None,
            "onceleme_kare_p05": A9.p(lead, 5) if lead else None,
            "onceleme_kare_p95": A9.p(lead, 95) if lead else None,
            "onceleme_pozitif_orani": round(float(np.mean([x > 0 for x in lead])), 3) if lead else None,
            "atesleyen_kopan_hucre": f"{bozulma_kopan}/{len(kopan_h)}",
            "yanlis_alarm_saglam_hucre": f"{bozulma_saglam}/{len(saglam_h)}",
            "yanlis_alarm_orani": round(bozulma_saglam / max(len(saglam_h), 1), 3),
        }
        print(f"  {sad:<20} AUC={str(sinyal_ozet[sad]['auc_kopus_onu_vs_saglam']):>7} "
              f"AUC(A|B)={str(sinyal_ozet[sad]['auc_modA_vs_modB']):>7} "
              f"lead p50={str(sinyal_ozet[sad]['onceleme_kare_p50']):>7} "
              f"yanlis alarm={sinyal_ozet[sad]['yanlis_alarm_saglam_hucre']}", flush=True)

    # ---------------- JSON'a ekle ----------------
    yol = "cikti/a9_takipci_merkez_recovery.json"
    J = json.load(open(yol))
    J["phase2_break_detection"] = {
        "etiketler": ["ACIK CEVRIM", "TESHIS", "GT YALNIZCA OFFLINE ETIKETLEME"],
        "not": "A/B yok, esik secilmedi, tracker davranisi degismedi, takip/ degismedi.",
        "konvansiyonlar": {
            "K1_ilk_bozulma": "ilk 5 kareye gore 3 sigma, bozulma yonunde (tanisal kural)",
            "K2_onceleme": "kopus_karesi - ilk_bozulma_karesi",
            "K3_ayirma": f"ROC AUC; pozitif=kopustan onceki {W_ONCE} kare, negatif=saglam dizilerin tum kareleri",
            "K4_yanlis_alarm": "saglam hucrelerde K1'in atesleme orani; FPR@TPR EGRIYI TANIMLAR, calisma noktasi ONERMEZ"},
        "mod_etiketleme": {
            "olcut": "kopus sonrasi DCF kabul orani >= 0.8 -> MOD B, aksi MOD A",
            "gozlenen_dagilim": [round(x, 3) for x in sirali],
            "modA_hucre": modA, "modB_hucre": modB},
        "signals": sinyal_ozet,
        "mode_a": {"hucreler": modA, "tanim": "olcum kaybi -> Kalman coast -> merkez kacisi"},
        "mode_b": {"hucreler": modB, "tanim": "PSR yuksek kalirken yanlis hedefe kilit"},
        "early_warning": {s: {"lead_p50": v["onceleme_kare_p50"],
                              "lead_pozitif_orani": v["onceleme_pozitif_orani"],
                              "auc": v["auc_kopus_onu_vs_saglam"]}
                          for s, v in sinyal_ozet.items()},
        "false_alarm": {s: v["yanlis_alarm_orani"] for s, v in sinyal_ozet.items()},
        "limitations": [
            "Acik cevrim; dedektor yok. Sonuclar UST SINIRDIR.",
            "6 dizi, 30 hucre; kopan hucre sayisi 13. Istatistiksel guc dusuk.",
            "MOD B ornekleri agirlikli olarak 339/49'dan geliyor.",
            "117/23 Deney 4L'de patolojik isaretli (1 px ucurumu, kontrast 5.2).",
            "K1'in 3 sigma kurali bir TANISAL KONVANSIYONDUR, onerilen esik degildir.",
            "bho_gt yalnizca offline etikettir; aday sinyal boyut_orani'dir.",
            "DCF ham tepe degeri cekirdek disina cikmiyor; PSR tek erisilebilir vekil.",
        ],
        "hucre_kayitlari": {k: {"dizi": v["dizi"], "seviye": v["seviye"], "rol": v["rol"],
                                "kopus_karesi": v["kopus_karesi"], "mod": v.get("mod"),
                                "mod_olcumleri": v["mod_olcumleri"]}
                            for k, v in hucreler.items()},
    }
    # zincir yeniden kurulumu icin iki ornek hucrenin kare kayitlari
    for k in ["uav0000117_02622_v/23|20x10", "uav0000339_00001_v/49|15x7"]:
        if k in hucreler:
            J["phase2_break_detection"].setdefault("zincir_kareleri", {})[k] = hucreler[k]["kareler"]
    json.dump(J, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
