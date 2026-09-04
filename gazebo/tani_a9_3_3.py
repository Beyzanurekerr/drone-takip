"""A9 Deney 3.3 - ZAMANSAL KALICILIK (SALT OKUNUR TESHIS).

*** ACIK CEVRIM · TESHIS · GT YALNIZCA OFFLINE ETIKETLEME ***
Hakem YOK · recovery state machine YOK · kalici kod degisikligi YOK.
takip/ DEGISMEZ (bu dosya takip/ altindaki hicbir seyi import edip calistirmaz).

ON-KAYIT: docs/architecture/A9_3_3_ONKAYIT.md - BU DENEYDEN ONCE yazildi.
    esik SABIT   : G <= 1.0  (3.2'nin kurali, degistirilmedi)
    tek degisken : k ardisik ihlal, k in {1,2,3,5}
    kanit yok    : SIFIRLA / DONDUR - ikisi de olculur
    kabul        : saglam dizilerde yanlis alarm <= X
                   X = (0.03*59) / (5.8*0.5) / nokta_hucre  -> N=5: %5.5, N=10: %12.2
                   (K1b · N_KARE · 3.2 §5 gecikme p95 · DOGRU_IOU - hepsi mevcut)

DEDEKTOR YENIDEN KOSMUYOR
-------------------------
3.3'un degiskeni k, dedektor ciktisi degil. 3.2'nin sakli KOL V kayitlari
(min_G serisi) uzerinde farkli bir sayac uygulanir. Boylece 3.2 ile bit
duzeyinde ayni yatak garanti edilir. Kisit: 3.3 o yatagin disina cikamaz.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

YOL = os.path.join(ROOT, "cikti", "a9_takipci_merkez_recovery.json")

KAPI = 1.0                       # 3.2 kurali - DEGISMEDI
K_ADAYLARI = [1, 2, 3, 5]        # on-kayitli
POLITIKALAR = ["SIFIRLA", "DONDUR"]
N_DEGERLERI = [5, 10]
BIRINCIL_MODEL = "A5_baseline"
BIRINCIL_N = 5
DOGRU_IOU, YANLIS_IOU = 0.5, 0.2
N_KARE = 60
# X: on-kayit §5.1 - hucre basina 0.61 yanlis tetikleme
BUTCE_HUCRE = (0.03 * (N_KARE - 1)) / (5.8 * DOGRU_IOU)
NOKTA_HUCRE = {5: 11, 10: 5}     # yataktan, sonuctan degil
X_ORAN = {n: BUTCE_HUCRE / NOKTA_HUCRE[n] for n in N_DEGERLERI}
SAGLAM = ["uav0000137_00458_v/12", "uav0000305_00000_v/5", "uav0000182_00000_v/127"]


def p(v, q):
    v = [x for x in v if x is not None]
    return None if not v else round(float(np.percentile(v, q)), 2)


# --------------------------------------------------------------------------
# sayac - on-kayit §3/§4
# --------------------------------------------------------------------------
def sayac_izi(noktalar, k, politika):
    """Dondurur: her nokta icin (t, alarm, tetikleme, sayac_deger)."""
    sayac, onceki_alarm, out = 0, False, []
    for r in noktalar:
        if r["kanit_yok"] or r["min_G"] is None:
            if politika == "SIFIRLA":
                sayac = 0
            # DONDUR: sayac degismez
        elif r["min_G"] > KAPI:
            sayac += 1
        else:
            sayac = 0
        alarm = sayac >= k
        out.append({"t": r["t"], "alarm": alarm, "tetikleme": alarm and not onceki_alarm,
                    "sayac": sayac, "kayit": r})
        onceki_alarm = alarm
    return out


def hucreler(kayitlar, N):
    """hucre -> t sirali nokta listesi (N periyoduna sadik alt kume)."""
    h = {}
    for r in kayitlar:
        if r["t"] % N != 0:
            continue
        h.setdefault(r["hucre"], []).append(r)
    for v in h.values():
        v.sort(key=lambda r: r["t"])
    return h


# --------------------------------------------------------------------------
# olcumler
# --------------------------------------------------------------------------
def yanlis_alarm(hcr, k, politika):
    """Saglam dizilerde yanlis tetikleme (on-kayit §5.2)."""
    tet, payda, kirli_hucre = 0, 0, set()
    for hd, noktalar in hcr.items():
        if noktalar[0]["dizi"] not in SAGLAM:
            continue
        iz = sayac_izi(noktalar, k, politika)
        for x in iz:
            if x["kayit"]["takipci_iou"] < DOGRU_IOU:
                continue
            payda += 1
            if x["tetikleme"]:
                tet += 1
                kirli_hucre.add(hd)
    return {"yanlis_tetikleme": tet, "uygun_nokta": payda,
            "oran": None if payda == 0 else round(tet / payda, 4),
            "kirli_hucre": sorted(kirli_hucre),
            "kirli_hucre_sayisi": len(kirli_hucre),
            "saglam_hucre_sayisi": len([1 for n in hcr.values() if n[0]["dizi"] in SAGLAM])}


def nokta_duzeyi(hcr, k, politika):
    """BETIMLEYICI (kabul olcutu DEGIL): 3.2 ile kiyaslanabilir nokta-duzeyi oranlar.

    3.2'nin bildirdigi '%48 yanlis alarm' NOKTA duzeyidir ve paydasi yalnizca
    KANIT TASIYAN noktalardir. On-kayit §5.2'nin olcutu ise YUKSELEN KENAR sayar.
    Ikisi ayri buyukluktur; ikisi de raporlanir ki 3.3 bir 'iyilesme' sanilmasin.
    """
    nokta = [x for hd, n in hcr.items() if n[0]["dizi"] in SAGLAM
             for x in sayac_izi(n, k, politika)
             if x["kayit"]["takipci_iou"] >= DOGRU_IOU]
    kanitli = [x for x in nokta if not (x["kayit"]["kanit_yok"] or x["kayit"]["min_G"] is None)]
    ihlal = [x for x in kanitli if x["kayit"]["min_G"] > KAPI]
    alarm = [x for x in nokta if x["alarm"]]
    return {"nokta": len(nokta), "kanit_tasiyan": len(kanitli), "kanit_yok": len(nokta) - len(kanitli),
            "ihlal_orani_kanitli_payda": round(len(ihlal) / len(kanitli), 4) if kanitli else None,
            "ihlal_orani_tum_payda": round(len(ihlal) / len(nokta), 4) if nokta else None,
            "alarm_durumu_orani": round(len(alarm) / len(nokta), 4) if nokta else None}


def yanlis_alarm_duyarlilik(hcr, k, politika):
    """On-kayit §5.2'nin 'takipci_iou >= 0.5' dislamasinin sonucu degistirip
    degistirmedigi. Disarida kalan yukselen kenarlar da sayilirsa oran ne olur."""
    tum, dis, payda = 0, 0, 0
    for hd, noktalar in hcr.items():
        if noktalar[0]["dizi"] not in SAGLAM:
            continue
        payda += len(noktalar)
        for x in sayac_izi(noktalar, k, politika):
            if x["tetikleme"]:
                tum += 1
                if x["kayit"]["takipci_iou"] < DOGRU_IOU:
                    dis += 1
    return {"tum_tetikleme": tum, "olcutun_disladigi": dis, "tum_nokta": payda,
            "oran_hepsi_sayilsa": round(tum / payda, 4) if payda else None}


def mod_b_yakalama(hcr, k, politika, modb, gecis):
    """on-kayit §6."""
    sat = []
    for hd in modb:
        noktalar = hcr.get(hd)
        if not noktalar:
            sat.append({"hucre": hd, "durum": "nokta yok"})
            continue
        g = gecis[hd]
        iz = sayac_izi(noktalar, k, politika)
        tetler = [x["t"] for x in iz if x["tetikleme"]]
        sonra = [t for t in tetler if t >= g]
        once = [t for t in tetler if t < g]
        sat.append({"hucre": hd, "gecis_karesi": g, "tetiklemeler": tetler,
                    "yakalandi": bool(sonra),
                    "gecikme": (sonra[0] - g) if sonra else None,
                    "erken_uyari": once[0] - g if once else None,
                    "durum": "yakalandi" if sonra else ("yalnizca erken" if once else "kacirildi")})
    yk = [s for s in sat if s.get("yakalandi")]
    gec = [s["gecikme"] for s in yk]
    return {"hucre_sayisi": len(modb), "yakalanan": len(yk),
            "oran": round(len(yk) / len(modb), 4) if modb else None,
            "gecikme_p50": p(gec, 50), "gecikme_p95": p(gec, 95),
            "gecikmeler": gec, "hucreler": sat}


def sec_k(tablo, N):
    """on-kayit §5.4 - havuz bos ise 'YOK'."""
    havuz = [k for k in K_ADAYLARI
             if tablo[k]["yanlis_alarm"]["oran"] is not None
             and tablo[k]["yanlis_alarm"]["oran"] <= X_ORAN[N]]
    if not havuz:
        return {"secim": None, "gerekce": "havuz bos - yanlis alarm hicbir k'da X'i saglamiyor",
                "X": round(X_ORAN[N], 4), "havuz": []}
    en = max(tablo[k]["mod_b"]["oran"] or 0.0 for k in havuz)
    a1 = [k for k in havuz if (tablo[k]["mod_b"]["oran"] or 0.0) == en]
    if len(a1) > 1:
        g = [(tablo[k]["mod_b"]["gecikme_p50"] if tablo[k]["mod_b"]["gecikme_p50"]
              is not None else 1e9, k) for k in a1]
        en_g = min(x[0] for x in g)
        a1 = [k for gg, k in g if gg == en_g]
    return {"secim": min(a1), "gerekce": "on-kayit §5.4", "X": round(X_ORAN[N], 4),
            "havuz": havuz, "mod_b_oran": en}


def main():
    J = json.load(open(YOL))
    p3 = J["phase3_recovery"]
    e32 = p3["experiment_3_2"]
    p2 = J["phase2_break_detection"]

    modb = list(p2["mode_b"]["hucreler"])
    eps = p3["mod_a"]["epizotlar"]

    # gecis karesi = hucredeki ILK epizodun bas_t'si (on-kayit §6)
    gecis, kilitli_eps = {}, []
    for e in eps:
        gecis.setdefault(e["hucre"], e["bas_t"])
        if e.get("baslangicta_kilitli"):
            kilitli_eps.append(e)
    p2kk = {h: p2["hucre_kayitlari"][h]["kopus_karesi"] for h in modb}

    cikti = {
        "etiketler": ["ACIK CEVRIM", "TESHIS", "GT YALNIZCA OFFLINE ETIKETLEME"],
        "deney": "3.3 - zamansal kalicilik (k ardisik ihlal)",
        "onkayit_dosyasi": "docs/architecture/A9_3_3_ONKAYIT.md (deneyden ONCE yazildi)",
        "esik": {"G_kapisi": KAPI, "degisti_mi": False,
                 "not": "3.2 kurali aynen; tek degisken k"},
        "dedektor_kosmadi": ("3.2'nin sakli KOL V kayitlari yeniden kullanildi; "
                             "min_G serisi bit duzeyinde 3.2 ile ayni"),
        "takip_degismedi": True,
        "kabul": {"X_turetme": "0.03*59 / (5.8*0.5) = 0.61 tetikleme/hucre",
                  "X": {str(n): round(X_ORAN[n], 4) for n in N_DEGERLERI},
                  "katim_olcut": "saglam hucrelerde sifir yanlis tetikleme"},
        "gecis_kareleri": {h: {"epizot_bas_t": gecis.get(h), "phase2_kopus_karesi": p2kk[h]}
                           for h in modb},
        "gecerlilik": {}, "modeller": {},
    }

    # ---------------- §8 gecerlilik denetimi ----------------
    kv = e32["kol_v"][BIRINCIL_MODEL]
    ihlal, kontrol = [], 0
    for e in eps:
        b, s = e["bas_t"], e["bas_t"] + e["uzunluk"] - 1
        for r in kv:
            if r["hucre"] == e["hucre"] and b <= r["t"] <= s:
                kontrol += 1
                if r["takipci_iou"] >= YANLIS_IOU:
                    ihlal.append({"hucre": r["hucre"], "t": r["t"], "iou": r["takipci_iou"]})
    cikti["gecerlilik"] = {"epizot_ici_kolV_noktasi": kontrol, "ihlal": ihlal,
                           "gecti": len(ihlal) == 0,
                           "tanim": "epizot ici KOL V noktalarinin takipci_iou < 0.2 olmasi"}
    print(f"gecerlilik: epizot ici {kontrol} nokta, ihlal {len(ihlal)} -> "
          f"{'GECTI' if not ihlal else 'KALDI'}")
    if ihlal:
        print("ON-KAYIT §8: 3.3 DURDU, sonuc raporlanmiyor.")
        cikti["durdu"] = True
        J["phase3_recovery"]["experiment_3_3"] = cikti
        json.dump(J, open(YOL, "w"), indent=2, ensure_ascii=False)
        return

    # ---------------- ana tarama ----------------
    for mad, kayitlar in e32["kol_v"].items():
        mout = {}
        for N in N_DEGERLERI:
            hcr = hucreler(kayitlar, N)
            nout = {"nokta_sayisi": sum(len(v) for v in hcr.values()),
                    "hucre_sayisi": len(hcr),
                    "kanit_yok_orani": round(
                        sum(1 for v in hcr.values() for r in v if r["kanit_yok"])
                        / max(sum(len(v) for v in hcr.values()), 1), 4),
                    "politikalar": {}}
            for pol in POLITIKALAR:
                tablo = {}
                for k in K_ADAYLARI:
                    tablo[k] = {
                        "yanlis_alarm": yanlis_alarm(hcr, k, pol),
                        "mod_b": mod_b_yakalama(hcr, k, pol, modb, gecis),
                        "nokta_duzeyi": nokta_duzeyi(hcr, k, pol),
                        "ya_duyarlilik": yanlis_alarm_duyarlilik(hcr, k, pol),
                    }
                    tablo[k]["X_gecti"] = bool(
                        tablo[k]["yanlis_alarm"]["oran"] is not None
                        and tablo[k]["yanlis_alarm"]["oran"] <= X_ORAN[N])
                    tablo[k]["kati_gecti"] = tablo[k]["yanlis_alarm"]["kirli_hucre_sayisi"] == 0
                nout["politikalar"][pol] = {
                    "k": {str(k): tablo[k] for k in K_ADAYLARI},
                    "secim": sec_k(tablo, N),
                }
            mout[f"N{N}"] = nout
        cikti["modeller"][mad] = mout
        print(f"\n===== {mad} =====")
        for N in N_DEGERLERI:
            for pol in POLITIKALAR:
                t = cikti["modeller"][mad][f"N{N}"]["politikalar"][pol]
                s = t["secim"]
                print(f"  N={N:<3} {pol:<8} secim={s['secim']}  havuz={s['havuz']}")
                for k in K_ADAYLARI:
                    kk = t["k"][str(k)]
                    ya, mb = kk["yanlis_alarm"], kk["mod_b"]
                    print(f"      k={k}  YA={ya['oran']} ({ya['yanlis_tetikleme']}/"
                          f"{ya['uygun_nokta']}, kirli hucre {ya['kirli_hucre_sayisi']}/"
                          f"{ya['saglam_hucre_sayisi']})  modB={mb['yakalanan']}/"
                          f"{mb['hucre_sayisi']} gecikme p50={mb['gecikme_p50']}")

    # ---------------- KILITLI-baslangicli 5 epizot ----------------
    hcr5 = hucreler(e32["kol_v"][BIRINCIL_MODEL], BIRINCIL_N)
    ke = []
    for e in kilitli_eps:
        b, s = e["bas_t"], e["bas_t"] + e["uzunluk"] - 1
        kayit = {"hucre": e["hucre"], "rol": e["rol"], "bas_t": b, "son_t": s, "k": {}}
        noktalar = hcr5.get(e["hucre"], [])
        for pol in POLITIKALAR:
            for k in K_ADAYLARI:
                iz = sayac_izi(noktalar, k, pol)
                ic = [x["t"] for x in iz if x["tetikleme"] and b <= x["t"] <= s]
                kayit["k"][f"{pol}|k={k}"] = {"ilk_uyari_t": ic[0] if ic else None,
                                              "gecikme": (ic[0] - b) if ic else None}
        ke.append(kayit)
    cikti["kilitli_baslangicli_epizotlar"] = ke

    # ---------------- kanonik Mod B: 339/49 15x7 ----------------
    kan = "uav0000339_00001_v/49|15x7"
    knt = {"hucre": kan, "gecis_karesi": gecis.get(kan),
           "phase2_kopus_karesi": p2kk.get(kan), "seri": [], "k": {}}
    for r in hcr5.get(kan, []):
        knt["seri"].append({"t": r["t"], "min_G": r["min_G"], "kanit_yok": r["kanit_yok"],
                            "takipci_iou": r["takipci_iou"]})
    for pol in POLITIKALAR:
        for k in K_ADAYLARI:
            iz = sayac_izi(hcr5.get(kan, []), k, pol)
            tet = [x["t"] for x in iz if x["tetikleme"]]
            sonra = [t for t in tet if t >= knt["gecis_karesi"]]
            knt["k"][f"{pol}|k={k}"] = {"tetiklemeler": tet,
                                        "gecikme": (sonra[0] - knt["gecis_karesi"])
                                        if sonra else None}
    cikti["kanonik_mod_b"] = knt

    # ---------------- LOSO ----------------
    loso = {}
    tum_diziler = SAGLAM + ["uav0000117_02622_v/23", "uav0000268_05773_v/31",
                            "uav0000339_00001_v/49"]
    for cikar in tum_diziler:
        kalan = [r for r in e32["kol_v"][BIRINCIL_MODEL] if r["dizi"] != cikar]
        hcr = hucreler(kalan, BIRINCIL_N)
        mb_k = [h for h in modb if not h.startswith(cikar + "|")]
        alt = {}
        for pol in POLITIKALAR:
            tablo = {k: {"yanlis_alarm": yanlis_alarm(hcr, k, pol),
                         "mod_b": mod_b_yakalama(hcr, k, pol, mb_k, gecis)}
                     for k in K_ADAYLARI}
            s = sec_k(tablo, BIRINCIL_N)
            alt[pol] = {"secim": s["secim"], "havuz": s["havuz"],
                        "mod_b_hucre": len(mb_k),
                        "k_ozet": {str(k): {"YA": tablo[k]["yanlis_alarm"]["oran"],
                                            "modB": tablo[k]["mod_b"]["oran"]}
                                   for k in K_ADAYLARI}}
        loso[cikar] = alt
    cikti["loso"] = loso

    J["phase3_recovery"]["experiment_3_3"] = cikti
    json.dump(J, open(YOL, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", YOL, "-> phase3_recovery.experiment_3_3")


if __name__ == "__main__":
    main()
