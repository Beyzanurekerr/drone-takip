"""A11 KOL 2 - ZAMANSAL HAREKET BIRIKTIRME (ACIK CEVRIM, takipciye YAZMAZ).

*** KOMPOZIT YATAK KULLANILMAZ ***

ON-KAYIT: docs/architecture/A11_ONKAYIT.md §4. N in {3,5,8}, sabit.

YONTEM: mevcut takip/tespit.py:HareketTespit'in "ego-hizali kare farki"
mekanizmasinin GENELLENMIS hali. HareketTespit N<=3 icin min(|D1|,|D2|)
(mantiksal VE, hayalet silme) kullanir. KOL 2, N kareyi SON karenin
cercevesine tasiyip farklari TOPLAR (SUM) - senaryo ailesinin kendi tasarim
onselini kullanir: hedef hizi = BAZ_HIZ = kamera baz hizi (_kam() docstring:
"boylece hedef goruntude nominal olarak sabit kalir"), yani ego-telafisi
sonrasi hedef YAKLASIK DURUR - N kare boyunca AYNI yerde biriken fark, MIN
ile silinecek bir "hayalet" degil, TAM ARANAN sinyaldir. SUM, tek karede
esigin altinda kalan zayif/kucuk hedefin SNR'ini N ile buyutur.

Takipciye YAZMAZ, GT'ye BAKMAZ (aday uretimi GT'siz). Yalnizca RAPORLAMA
icin aday GT ile karsilastirilir.
"""
import hashlib
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from gazebo.a11_ortak import kareleri_topla                        # noqa: E402
from takip.egomotion import BIRIM, EgoMotion, bileske               # noqa: E402

SENARYOLAR = ["A1_taban", "A2_kucul", "A3_yaw", "A4_irtifa",
             "A5_kucul_yaw", "A6_celdirici"]
N_ADAYLARI = [3, 5, 8]           # on-kayitli
KADANS = 10                      # hakemin dogrulama kadansiyla AYNI (karsilastirilabilirlik)
MIN_ALAN, MAX_KENAR = 3, 200
ESIK_K, MIN_ESIK = 3.0, 6.0      # HareketTespit ile AYNI mertebede


def md5ler():
    return {f: hashlib.md5(open(os.path.join(ROOT, "takip", f), "rb").read()).hexdigest()
            for f in sorted(os.listdir(os.path.join(ROOT, "takip"))) if f.endswith(".py")}


def p(v, q):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return None if not v else round(float(np.percentile(v, q)), 3)


def seviye_ad(L):
    if L < 10:
        return "8x5"
    if L < 13:
        return "10x5"
    if L < 18:
        return "15x7"
    if L < 25:
        return "20x10"
    return "30x12_ve_ustu"


def biriktir(gri_buf, M_buf, esik_k=ESIK_K, min_esik=MIN_ESIK):
    """gri_buf: son N gri kare (indeks 0 EN ESKI, -1 EN YENI).
    M_buf: N-1 ardisik M (M_buf[i] = kare i -> kare i+1).
    Hepsini SON karenin cercevesine tasiyip |fark|'i TOPLAR."""
    hedef = gri_buf[-1]
    h, w = hedef.shape
    toplam = np.zeros((h, w), np.float32)
    M_kum = BIRIM.copy()
    for i in range(len(gri_buf) - 2, -1, -1):
        M_kum = bileske(M_buf[i], M_kum)
        warped = cv2.warpAffine(gri_buf[i], M_kum, (w, h), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_REPLICATE)
        toplam += cv2.absdiff(hedef, warped).astype(np.float32)

    toplam = cv2.GaussianBlur(toplam, (5, 5), 0)
    k = 8
    toplam[:k], toplam[-k:], toplam[:, :k], toplam[:, -k:] = 0, 0, 0, 0

    esik = max(min_esik * (len(gri_buf) - 1), float(toplam.mean() + esik_k * toplam.std()))
    _, ikili = cv2.threshold(toplam, esik, 255, cv2.THRESH_BINARY)
    ikili = cv2.morphologyEx(ikili.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    ikili = cv2.dilate(ikili, np.ones((3, 3), np.uint8))

    n, _, stats, cent = cv2.connectedComponentsWithStats(ikili, 8)
    out = []
    for i in range(1, n):
        x, y, bw, bh, alan = stats[i]
        if alan < MIN_ALAN or bw > MAX_KENAR or bh > MAX_KENAR:
            continue
        out.append({"merkez": np.array(cent[i], np.float32), "alan": float(alan)})
    out.sort(key=lambda c: -c["alan"])
    return out


def olc(senaryo):
    kareler, W, H, fx, fy, cx, cy = kareleri_topla(senaryo)
    ego = EgoMotion()
    gri_tum, M_tum = [], []          # gri_tum[i], M_tum[i] = kare i -> i+1
    kayitlar = {N: [] for N in N_ADAYLARI}

    for t, (img, gt, satir) in enumerate(kareler):
        gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if t == 0:
            M = BIRIM.copy()
        else:
            M, _guven = ego.guncelle(gri, None)
        gri_tum.append(gri)
        if t > 0:
            M_tum.append(M)          # M_tum[t-1] = kare (t-1) -> kare t

        if t % KADANS != 0 or t == 0:
            continue
        gtc = gt[:2] + gt[2:] / 2.0
        L = float(np.max(gt[2:]))
        for N in N_ADAYLARI:
            if t < N - 1:
                continue
            gri_buf = gri_tum[t - (N - 1):t + 1]
            M_buf = M_tum[t - (N - 1):t]
            adaylar = biriktir(gri_buf, M_buf)
            # OPERASYONEL: en buyuk alan secilir (gercek kullanimda GT yok)
            # ORACLE: GT'ye EN YAKIN aday - "sinyal dogru bolgede VAR MI" sorusu,
            # secim sorunundan AYRI (A9/A10'un oracle/operasyonel ayrimiyla ayni ilke)
            hata_op = hata_or = None
            if adaylar:
                hata_op = float(np.linalg.norm(adaylar[0]["merkez"] - gtc))
                hata_or = min(float(np.linalg.norm(a["merkez"] - gtc)) for a in adaylar)
            kayitlar[N].append({"t": t, "kanit": len(adaylar) > 0,
                                "merkez_hata_operasyonel": hata_op,
                                "merkez_hata_oracle": hata_or,
                                "gt_L": L, "seviye": seviye_ad(L),
                                "aday_sayisi": len(adaylar)})
    return kayitlar


def ozet(kayitlar):
    tot = len(kayitlar)
    kanit = sum(1 for k in kayitlar if k["kanit"])
    hop = [k["merkez_hata_operasyonel"] for k in kayitlar if k["kanit"]]
    hor = [k["merkez_hata_oracle"] for k in kayitlar if k["kanit"]]
    by_sev = {}
    for k in kayitlar:
        d = by_sev.setdefault(k["seviye"], {"nokta": 0, "kanit": 0, "hop": [], "hor": []})
        d["nokta"] += 1
        if k["kanit"]:
            d["kanit"] += 1
            d["hop"].append(k["merkez_hata_operasyonel"])
            d["hor"].append(k["merkez_hata_oracle"])
    for sev, d in by_sev.items():
        d["kanit_orani"] = round(d["kanit"] / d["nokta"], 4) if d["nokta"] else None
        d["hata_operasyonel_p50"] = p(d["hop"], 50)
        d["hata_oracle_p50"] = p(d["hor"], 50)
        del d["hop"], d["hor"]
    return {"nokta": tot, "kanit": kanit,
           "kanit_orani": round(kanit / tot, 4) if tot else None,
           "hata_operasyonel_p50": p(hop, 50), "hata_operasyonel_p95": p(hop, 95),
           "hata_oracle_p50": p(hor, 50), "hata_oracle_p95": p(hor, 95),
           "seviye": by_sev}


def main():
    md5_bas = md5ler()
    cikti = {"etiketler": ["ACIK CEVRIM", "KOMPOZIT YATAK YOK", "GAZEBO",
                           "TAKIPCIYE YAZMAZ"],
             "onkayit": "docs/architecture/A11_ONKAYIT.md §4",
             "N_adaylari": N_ADAYLARI, "kadans": KADANS,
             "md5_baslangic": md5_bas, "hucreler": {}}

    for s in SENARYOLAR:
        kayitlar = olc(s)
        cikti["hucreler"][s] = {N: {"kayit": kayitlar[N], "ozet": ozet(kayitlar[N])}
                                for N in N_ADAYLARI}
        print(f"\n{s}:", flush=True)
        for N in N_ADAYLARI:
            oz = cikti["hucreler"][s][N]["ozet"]
            print(f"  N={N:<2} nokta={oz['nokta']:<3} kanit_orani={oz['kanit_orani']} "
                  f"OP_p50={oz['hata_operasyonel_p50']} OR_p50={oz['hata_oracle_p50']}",
                  flush=True)

    cikti["md5_bitis"] = md5ler()
    cikti["md5_degismedi"] = cikti["md5_baslangic"] == cikti["md5_bitis"]
    yol = os.path.join(ROOT, "cikti", "a11_kol2.json")
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("\nyazildi:", yol)


if __name__ == "__main__":
    main()
