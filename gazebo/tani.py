"""Faz B teshis kosucusu: G0-G7 kayitlarini olcer ve kopmayi K1-K8'e esler.

NE YAPAR, NE YAPMAZ
-------------------
Bu modul TAKIPCIYE DOKUNMAZ. `takip/` altindaki bes dosyanin hicbiri
degismedi; buradaki her sey ya disaridan gozlem (alt sinif + cekirdek sarmasi)
ya da kayitli POZLARDAN turetilen bagimsiz bir referanstir.

Standart metrikler (IoU, @0.5, merkez hata, kilit, kurtarma, FPS, gecikme,
drift karesi) `main.kos()`'tan OLDUGU GIBI alinir - Faz A tablosuyla
karsilastirilabilirligi bozmamak icin yeniden yazilmadi. `main.HedefTakip`
gecici olarak gozlemleyen bir alt sinifla degistirilir; dongu, esikler,
kilit secimi, olcum tanimlari birebir ayni kalir.

BAGIMSIZ EGO REFERANSI
----------------------
Takipcinin `M`'si dogru mu sorusunu takipcinin kendisine sormak anlamsizdir.
Referans kayitli KAMERA POZUNDAN uretilir:

    goruntu noktasi (k-1) -> zemin duzlemine (z=0) geri izdusum
                          -> k. karenin kamerasina ileri izdusum

Bu, arka planin GERCEK kare-arasi eslesmesidir. Uc sayi ayrilir:

    e_model : gercek eslesmeye EN IYI benzerlik donusumunun artigi.
              Benzerlik (oteleme+donme+olcek) modelinin kendi sinirini
              olcer; nadir kamerada ~0, kamera pitch'lendikce buyur
              (perspektif artik benzerlikle temsil edilemez).  -> K6
    e_ego   : takipcinin M'sinin artigi. e_model bunun ALT SINIRIDIR.
    e_kest  : e_ego - e_model, yani kestirimin kendi hatasi.  -> K1

Bu ayrim olmadan "ego hatasi" tek bir sayidir ve K1 ile K6 birbirinden
ayrilamaz: pitch senaryosunda e_ego buyur ama sucu LK/RANSAC'ta degil,
MODELDEDIR.

Kullanim:
    python3 -m gazebo.tani                 # G0 + 14 Faz B senaryosu
    python3 -m gazebo.tani G3_agresif
    python3 -m gazebo.tani --kok data/gazebo --json cikti/fazb.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np

import main as ana
from calistir import iou
from takip.egomotion import BIRIM
from takip.izleyici import KILITLI, HedefTakip
from veri.gazebo import GazeboKaynak, kuaterniyon_matris

IZGARA = 7          # bagimsiz ego referansi icin kare basina 7x7 nokta
KENAR = 40          # kadraj kenarindan uzak dur (LK de kenarda nokta bulmaz)


# ---------------------------------------------------------------------------
# 1) GOZLEMLEYEN TAKIPCI  (takip/ degismeden ic durumu disari verir)
# ---------------------------------------------------------------------------
class IzlenenTakip(HedefTakip):
    """A3.8 takipcisinin davranisi AYNEN; yalnizca her karede ic durum yazilir.

    Iki gozlem noktasi var:
      * `cekirdek.ara` ORNEK ile sarilir. Cagrildigi an KF'nin ONGORUSUdur
        (izleyici.py `_takip_adimi`'nda `tahmin = self.kf.konum` hemen once
        okunur), yani sicrama kapisinin gordugu iki sayiyi da orada yakalariz:
        ongoru ve olcum. Kapi kararini YENIDEN URETMIYORUZ; sadece kapinin
        girdilerini kaydedip aritmetigi disarida tekrarliyoruz.
      * `guncelle` sarilir: ego M'si, guven, olcek, KF durumu, boyut, imza
        benzerligi ve yanlis kilit sayaci kare kare alinir.

    Hicbir esik, hicbir karar burada degistirilmez.
    """

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.gunluk = []
        self._ara = None
        gercek = self.cekirdek.ara

        def ara_sarma(bgr, gri, merkez, boyut):
            ongoru = np.asarray(merkez, np.float64).copy()
            hiz = self.kf.hiz.astype(np.float64) if self.kf is not None else None
            yeni, psr = gercek(bgr, gri, merkez, boyut)
            self._ara = {"ongoru": ongoru, "kf_hiz": hiz,
                         "boyut": np.asarray(boyut, np.float64).copy(),
                         "olcum": np.asarray(yeni, np.float64).copy(),
                         "psr": float(psr)}
            return yeni, psr

        self.cekirdek.ara = ara_sarma
        self.kilit_boyut = None
        # DCF arama penceresinin yari genisligi: yama boyut x dolgu olarak
        # kesilir, tepe +-N/2 hucre icinde aranir -> azami tespit edilebilir
        # kayma = boyut x dolgu / 2. Cekirdek dolgu tasimiyorsa 1.0 varsayilir.
        self.dolgu = float(getattr(self.cekirdek, "dolgu", 1.0))

    def kilitle(self, bgr, kutu):
        r = super().kilitle(bgr, kutu)
        self.kilit_boyut = self.boyut.copy()
        return r

    def guncelle(self, bgr):
        self._ara = None
        sonuc = super().guncelle(bgr)
        self.gunluk.append({
            "kare_ic": self.kare,
            "durum": self.durum,
            "psr": float(self.psr),
            "M": self.ego.M.astype(np.float64).copy(),
            "ego_guven": float(self.ego.guven),
            "ego_birim": bool(np.array_equal(self.ego.M, BIRIM)),
            "olcek": float(self.ego.olcek_katsayisi),
            "kf_konum": self.kf.konum.astype(np.float64),
            "kf_hiz": self.kf.hiz.astype(np.float64),
            "boyut": self.boyut.astype(np.float64).copy(),
            "benzerlik": float(self.benzerlik),
            # Deney 2 (kapali cevrim aci kestirimi) gozlem noktalari.
            # Cekirdek bunlari tasimiyorsa (mosse/ncc/akis, ya da deney
            # geri alinmissa) getattr varsayilanlari devreye girer.
            "aci": float(getattr(self.cekirdek, "aci", 0.0)),
            "aci_ref": float(getattr(self.cekirdek, "aci_ref", 0.0)),
            "aci_aktif": bool(getattr(self.cekirdek, "aktif", False)),
            "aci_adim": float(getattr(self.cekirdek, "aci_adim", 0.0)),
            "yanlis_kilit": int(self.yanlis_kilit),
            "ara": self._ara,
        })
        return sonuc


# ---------------------------------------------------------------------------
# 2) BAGIMSIZ EGO REFERANSI  (kayitli pozlardan)
# ---------------------------------------------------------------------------
def _kamera(satir):
    C = np.array([satir["kam_x"], satir["kam_y"], satir["kam_z"]], np.float64)
    R = kuaterniyon_matris(satir["kam_qw"], satir["kam_qx"],
                           satir["kam_qy"], satir["kam_qz"])
    return C, R


def _zemine_geri(uv, C, R, fx, fy, cx, cy):
    """Goruntu noktalarini z = 0 zemin duzlemine geri izdusur.

    Kamera cercevesi (gz sim): +X optik eksen, +Y sol, +Z yukari; ileri
    izdusum u = cx - fx Y/X, v = cy - fy Z/X. Tersine cevirince isin yonu
    d_kam = (1, (cx-u)/fx, (cy-v)/fy) olur.
    """
    uv = np.atleast_2d(np.asarray(uv, np.float64))
    d_kam = np.stack([np.ones(len(uv)), (cx - uv[:, 0]) / fx,
                      (cy - uv[:, 1]) / fy], 1)
    d = d_kam @ R.T                       # R @ d_kam (satir vektorleri)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = -C[2] / d[:, 2]
    P = C[None] + s[:, None] * d
    return P, (s > 0) & np.isfinite(s)


def _ileri(P, C, R, fx, fy, cx, cy):
    p = (np.atleast_2d(P) - C) @ R
    X, Y, Z = p[:, 0], p[:, 1], p[:, 2]
    onde = X > 1e-6
    uv = np.full((len(p), 2), np.nan)
    uv[onde, 0] = cx - fx * (Y[onde] / X[onde])
    uv[onde, 1] = cy - fy * (Z[onde] / X[onde])
    return uv, onde


def _benzerlik_uydur(a, b):
    """a -> b icin en kucuk kareler benzerligi (oteleme + donme + olcek).

    RANSAC yok, kirpma yok: burada aykiri deger yok, sorulan sey modelin
    KENDI siniri. cv2.estimateAffinePartial2D kullanilmadi cunku o RANSAC
    ile bir alt kume secer; biz TUM noktalarin artigini istiyoruz.
    """
    ma, mb = a.mean(0), b.mean(0)
    A, B = a - ma, b - mb
    # kapali cozum: kompleks duzlemde tek katsayi
    za = A[:, 0] + 1j * A[:, 1]
    zb = B[:, 0] + 1j * B[:, 1]
    payda = float((za * np.conj(za)).real.sum())
    if payda < 1e-9:
        return np.array([[1, 0, 0], [0, 1, 0]], np.float64)
    k = complex((zb * np.conj(za)).sum() / payda)
    R = np.array([[k.real, -k.imag], [k.imag, k.real]], np.float64)
    t = mb - R @ ma
    return np.hstack([R, t.reshape(2, 1)])


def ego_referansi(kaynak):
    """Kare kare gercek arka plan eslesmesi + benzerlik modelinin alt siniri.

    Doner: liste (kare k icin, k>=1) -> dict(M_gercek, e_model, ok)
    `M_gercek` gercek eslesmeye en iyi uyan benzerliktir; KF/artik
    hesaplarinda tek bir 2x3 gerektigi icin bu kullanilir, `e_model` de onun
    ne kadar yetersiz kaldigini soyler.
    """
    W, H = kaynak.genislik, kaynak.yukseklik
    fx, fy, cx, cy = kaynak.fx, kaynak.fy, kaynak.cx, kaynak.cy
    gx = np.linspace(KENAR, W - KENAR, IZGARA)
    gy = np.linspace(KENAR, H - KENAR, IZGARA)
    izgara = np.stack(np.meshgrid(gx, gy), -1).reshape(-1, 2)

    cikti = [None]
    for k in range(1, len(kaynak.pozlar)):
        C0, R0 = _kamera(kaynak.pozlar[k - 1])
        C1, R1 = _kamera(kaynak.pozlar[k])
        P, ok0 = _zemine_geri(izgara, C0, R0, fx, fy, cx, cy)
        uv1, ok1 = _ileri(P, C1, R1, fx, fy, cx, cy)
        ok = ok0 & ok1 & np.isfinite(uv1).all(1)
        if ok.sum() < 6:
            cikti.append(None)
            continue
        a, b = izgara[ok], uv1[ok]
        M = _benzerlik_uydur(a, b)
        art = np.linalg.norm(a @ M[:, :2].T + M[:, 2] - b, axis=1)
        cikti.append({"M": M, "a": a, "b": b,
                      "e_model": float(np.median(art)),
                      "e_model_p95": float(np.percentile(art, 95))})
    return cikti


def gercek_goruntu_donmesi(kaynak):
    """Kameranin GORUNTU DUZLEMINDEKI birikimli donmesi (derece), pozlardan.

    Optik eksen etrafindaki bilesen: A = R_k^T R_{k-1} icin atan2(A[2,1], A[2,2]).
    Cekirdegin `aci` alaniyla AYNI isaret sozlesmesindedir; ikisi dogrudan
    cikarilabilir (deney 1'de G3_kritik icin olculen -108.0 / gercek -106.6
    bu formulle elde edildi).
    """
    Q = [[s["kam_qw"], s["kam_qx"], s["kam_qy"], s["kam_qz"]] for s in kaynak.pozlar]
    R = [kuaterniyon_matris(*q) for q in Q]
    top = [0.0]
    for k in range(1, len(R)):
        A = R[k].T @ R[k - 1]
        top.append(top[-1] + math.degrees(math.atan2(A[2, 1], A[2, 2])))
    return np.array(top)


def kamera_hizlari(kaynak):
    """Kare basina kamera dogrusal (m/s) ve acisal (deg/s) hizi."""
    P = np.array([[s["kam_x"], s["kam_y"], s["kam_z"]] for s in kaynak.pozlar])
    Q = np.array([[s["kam_qw"], s["kam_qx"], s["kam_qy"], s["kam_qz"]]
                  for s in kaynak.pozlar])
    t = np.array([s["t"] for s in kaynak.pozlar])
    dt = np.diff(t)
    dt[dt <= 0] = 1.0 / max(1e-6, kaynak.fps)
    v = np.r_[0.0, np.linalg.norm(np.diff(P, axis=0), axis=1) / dt]
    aci = [0.0]
    for k in range(1, len(Q)):
        nokta = float(np.clip(abs(Q[k - 1] @ Q[k]), -1.0, 1.0))
        aci.append(math.degrees(2.0 * math.acos(nokta)) / dt[k - 1])
    return v, np.array(aci)


# ---------------------------------------------------------------------------
# 3) TEK SENARYO OLCUMU
# ---------------------------------------------------------------------------
def olc(senaryo, kok="data/gazebo", cekirdek="renk_dcf"):
    kaynak = GazeboKaynak(kok=kok, senaryo=senaryo)
    meta = kaynak.meta
    ref = ego_referansi(kaynak)
    ger_aci = gercek_goruntu_donmesi(kaynak)
    kam_v, kam_w = kamera_hizlari(kaynak)
    gt = [kaynak._kutu(s, kaynak.hedef_ad) for s in kaynak.pozlar]
    gt_c = [None if g is None else np.array([g[0] + g[2] / 2, g[1] + g[3] / 2])
            for g in gt]

    # --- standart metrikler: main.kos AYNEN, yalnizca takipci gozlemleniyor
    ilk = HedefTakip
    kutu = {}

    def fabrika(*a, **k):
        t = IzlenenTakip(*a, **k)
        kutu["t"] = t
        return t

    ana.HedefTakip = fabrika
    try:
        m = ana.kos(kaynak, cekirdek=cekirdek, pencere=False)
    finally:
        ana.HedefTakip = ilk
    tak = kutu["t"]
    gunluk = tak.gunluk

    # gunluk[i] hangi kareye denk geliyor: guncelle() kilit sonrasi her karede
    # tam bir kez cagrilir, yani son len(gunluk) kare.
    n_kare = int(m["kare"])
    ofset = n_kare - len(gunluk)
    for i, g in enumerate(gunluk):
        g["kare"] = ofset + i
    assert all(g["kare_ic"] == i + 1 for i, g in enumerate(gunluk)), \
        "gunluk hizalamasi bozuk"

    iou_kare = {r["kare"]: r["iou"] for r in m.get("_olcum", [])}

    # --- ID SWITCH ---------------------------------------------------------
    # Olcut calistir.py:kos ile BIREBIR ayni: takip kutusunun EN COK ortustugu
    # arac (IoU > 0.2) bir onceki karede HEDEF iken baskasina gecerse bir
    # switch sayilir. Gazebo'da celdiricinin GT'si var (veri/gazebo.py:
    # celdiriciler), o yuzden sim ile ayni sutunda okunabilir; VisDrone'da
    # yoktur (tek track etiketli) ve orada olculmez.
    id_switch, onceki_uzerinde = 0, "hedef"
    adlar = [kaynak.hedef_ad] + [a for a in kaynak.olculer if a != kaynak.hedef_ad]
    for g in gunluk:
        k = g["kare"]
        if k >= len(kaynak.pozlar):
            continue
        kutu = np.array([g["kf_konum"][0] - g["boyut"][0] / 2,
                         g["kf_konum"][1] - g["boyut"][1] / 2,
                         g["boyut"][0], g["boyut"][1]], np.float32)
        en_iyi, en_ad = 0.0, None
        for ad in adlar:
            gb = kaynak._kutu(kaynak.pozlar[k], ad)
            if gb is None:
                continue
            o = iou(kutu, gb)
            if o > en_iyi:
                en_iyi, en_ad = o, ad
        uzerinde = en_ad if en_iyi > 0.2 else None
        if (uzerinde is not None and onceki_uzerinde == kaynak.hedef_ad
                and uzerinde != kaynak.hedef_ad):
            id_switch += 1
        if uzerinde is not None:
            onceki_uzerinde = uzerinde

    # --- kare kare teshis ---------------------------------------------------
    e_ego, e_kest, e_model = [], [], []
    d_gor, d_artik, oran, kf_hata = [], [], [], []
    sicrama_v, sicrama_oran, artik_oran = [], [], []
    birim, sicrama_red, sicrama_var = 0, 0, 0
    yanlis = []
    for g in gunluk:
        k = g["kare"]
        r = ref[k] if 0 < k < len(ref) else None
        if g["ego_birim"]:
            birim += 1
        if r is not None:
            a, b = r["a"], r["b"]
            M = g["M"]
            art = np.linalg.norm(a @ M[:, :2].T + M[:, 2] - b, axis=1)
            e = float(np.median(art))
            e_ego.append(e)
            e_model.append(r["e_model"])
            e_kest.append(max(0.0, e - r["e_model"]))
        if k > 0 and gt_c[k] is not None and gt_c[k - 1] is not None:
            d = float(np.linalg.norm(gt_c[k] - gt_c[k - 1]))
            d_gor.append(d)
            if r is not None:
                Mg = r["M"]
                tasinan = Mg[:, :2] @ gt_c[k - 1] + Mg[:, 2]
                v_ger = gt_c[k] - tasinan
                d_artik.append(float(np.linalg.norm(v_ger)))
                if g["ara"] is not None and g["ara"]["kf_hiz"] is not None:
                    kf_hata.append(float(np.linalg.norm(g["ara"]["kf_hiz"] - v_ger)))
        A = g["ara"]
        if A is not None:
            b = A["boyut"]
            kapi = max(6.0, 0.9 * float(b.max()))
            dcf = 0.5 * tak.dolgu * float(b.min())
            r_et = min(kapi, dcf)
            if d_gor:
                oran.append(d_gor[-1] / max(1e-6, r_et))
            if d_artik:
                artik_oran.append(d_artik[-1] / max(1e-6, r_et))
            s = float(np.linalg.norm(A["olcum"] - A["ongoru"]))
            sicrama_v.append(s)
            sicrama_oran.append(s / max(1e-6, r_et))
            if A["psr"] >= tak.psr_kilit:
                sicrama_var += 1
                if s > kapi:
                    sicrama_red += 1
        io = iou_kare.get(k)
        if io is not None:
            yanlis.append(1.0 if (g["durum"] == KILITLI and io < 0.2) else 0.0)

    b_son = gunluk[-1]["boyut"] if gunluk else np.ones(2)
    r_etkin = min(max(6.0, 0.9 * float(b_son.max())),
                  0.5 * tak.dolgu * float(b_son.min()))

    # --- TAVAN IoU: GT kutusu tanimindan gelen kacinilmaz kayip -----------
    # GT kutusu aracin 3B kutusunun EKSEN HIZALI izdusumudur. Arac goruntude
    # donunce (kamera yaw'i ya da hedefin kendi manevrasi) bu kutu BUYUR;
    # takipcinin sabit en-boy oranli kutusu onu asla dolduramaz. Yani G3/G6'da
    # IoU dususunun bir kismi takipcinin hatasi DEGILDIR.
    #   tavan_iou : GT merkezine tam oturmus, KILIT ANINDAKI boyutta kutu
    #   merkez_iou: GT merkezine tam oturmus, takipcinin O ANKI boyutu
    # Ikisi arasindaki fark boyut suruklenmesini, tavan ile gercek IoU
    # arasindaki fark merkez hatasini yalitir.
    kb = tak.kilit_boyut if tak.kilit_boyut is not None else b_son
    tavan, merkez_iou = [], []
    boyut_kare = {g["kare"]: g["boyut"] for g in gunluk}
    for r in m.get("_olcum", []):
        k = r["kare"]
        g = gt[k]
        if g is None or gt_c[k] is None:
            continue
        c = gt_c[k]
        tavan.append(iou(np.array([c[0] - kb[0] / 2, c[1] - kb[1] / 2,
                                   kb[0], kb[1]], np.float32), g))
        bk = boyut_kare.get(k)
        if bk is not None:
            merkez_iou.append(iou(np.array([c[0] - bk[0] / 2, c[1] - bk[1] / 2,
                                            bk[0], bk[1]], np.float32), g))

    # --- Deney 2: kullanilan aci, aci hatasi, devreye girme -----------------
    aci_kul = np.array([g["aci"] for g in gunluk])
    aktif = np.array([g["aci_aktif"] for g in gunluk], bool)
    kareler = np.array([g["kare"] for g in gunluk])
    ger = ger_aci[np.clip(kareler, 0, len(ger_aci) - 1)]
    ger = ger - (ger[0] if len(ger) else 0.0)      # kilit karesine gore
    aci_hata = np.abs(aci_kul - ger)
    aktif_kareler = kareler[aktif]

    def p(v, q):
        return float(np.percentile(v, q)) if len(v) else 0.0

    t = {
        "senaryo": senaryo,
        "aile": meta.get("aile", ""),
        "siddet": meta.get("siddet", ""),
        "aciklama": meta.get("aciklama", ""),
        "beklenen": meta.get("beklenen", ""),
        "kare": n_kare,
        "gt_kare": int(m.get("gt_kare", 0)),
        # --- standart (main.kos) ---
        "iou": float(m.get("ort_iou", 0.0)),
        "basari@0.5": float(m.get("basari@0.5", 0.0)),
        "basari@0.3": float(m.get("basari@0.3", 0.0)),
        "merkez_hata": float(m.get("merkez_hata", 0.0)),
        "kilit_orani": float(m.get("kilit_orani", 0.0)),
        "kesinti": int(m.get("kesinti", 0)),
        "kurtarma_ort": float(m.get("kurtarma_ort", 0.0)),
        "kurtarma_max": int(m.get("kurtarma_max", 0)),
        "id_switch": int(id_switch),
        "t_drift": m.get("t_drift"),
        "fps": float(m["fps"]),
        "gecikme_p50": float(m["gecikme_p50"]),
        "gecikme_p95": float(m["gecikme_p95"]),
        "gt_boyut": list(m.get("gt_boyut", (0.0, 0.0))),
        "tavan_iou": float(np.mean(tavan)) if tavan else 0.0,
        "merkez_iou": float(np.mean(merkez_iou)) if merkez_iou else 0.0,
        "kilit_boyut": [float(kb[0]), float(kb[1])],
        # --- Faz B teshis ---
        "e_ego_p50": p(e_ego, 50), "e_ego_p95": p(e_ego, 95),
        "e_model_p50": p(e_model, 50), "e_model_p95": p(e_model, 95),
        "e_kest_p50": p(e_kest, 50), "e_kest_p95": p(e_kest, 95),
        "d_goruntu_p50": p(d_gor, 50), "d_goruntu_p95": p(d_gor, 95),
        "d_artik_p50": p(d_artik, 50), "d_artik_p95": p(d_artik, 95),
        "r_etkin": float(r_etkin),
        "d_r_p50": p(oran, 50), "d_r_p95": p(oran, 95),
        # d_goruntu HAM kaymadir; takipcinin gercekten YUTMASI gereken artik
        # once ego M'si sonra KF hizi tarafindan cikarilir. Uc oran birlikte
        # okunmali: d_goruntu/r ham yuk, d_artik/r ego sonrasi, sicrama/r ise
        # sicrama kapisinin fiilen gordugu sayidir.
        "d_artik_r_p95": p(artik_oran, 95),
        "sicrama_p50": p(sicrama_v, 50), "sicrama_p95": p(sicrama_v, 95),
        "sicrama_r_p95": p(sicrama_oran, 95),
        "ego_birim_orani": birim / max(1, len(gunluk)),
        "sicrama_red_orani": sicrama_red / max(1, sicrama_var),
        "yanlis_kilit_orani": float(np.mean(yanlis)) if yanlis else 0.0,
        "yanlis_kilit_sayac": int(gunluk[-1]["yanlis_kilit"]) if gunluk else 0,
        "kf_hiz_hatasi_p50": p(kf_hata, 50), "kf_hiz_hatasi_p95": p(kf_hata, 95),
        "kamera_dogrusal_p95": float(np.percentile(kam_v, 95)),
        "kamera_acisal_p50": float(np.percentile(kam_w, 50)),
        "kamera_acisal_p95": float(np.percentile(kam_w, 95)),
        "kamera_acisal_max": float(kam_w.max()),
        "ego_guven_p50": p([g["ego_guven"] for g in gunluk], 50),
        "psr_p50": p([g["psr"] for g in gunluk], 50),
        "olcek_p95": p([abs(g["olcek"] - 1.0) for g in gunluk], 95),
        # DCF sablonunun her karede sogurmasi gereken donme (olculen M'den)
        "ego_donme_p95": p([abs(math.degrees(math.atan2(g["M"][1, 0], g["M"][0, 0])))
                            for g in gunluk], 95),
        "aci_adim": float(gunluk[-1]["aci_adim"]) if gunluk else 0.0,
        "aci_aktif_orani": float(aktif.mean()) if len(aktif) else 0.0,
        "aci_aktif_kare": int(aktif.sum()),
        "aci_ilk_kare": int(aktif_kareler[0]) if len(aktif_kareler) else -1,
        "aci_kullanilan_min": float(aci_kul.min()) if len(aci_kul) else 0.0,
        "aci_kullanilan_max": float(aci_kul.max()) if len(aci_kul) else 0.0,
        "aci_gercek_min": float(ger.min()) if len(ger) else 0.0,
        "aci_gercek_max": float(ger.max()) if len(ger) else 0.0,
        "aci_hata_p50": p(aci_hata, 50), "aci_hata_p95": p(aci_hata, 95),
    }
    return t


# ---------------------------------------------------------------------------
# 4) K1-K8 ESLEMESI
# ---------------------------------------------------------------------------
# Her hipotez TEK bir olculen buyuklugu isaret eder. Puan, o buyuklugun G0
# saglikli tabanina (ya da fiziksel bir tabana - hangisi buyukse) oranidir:
# "taban davranisin kac kati". Boylece esikler elle uydurulmus sabitler degil,
# olculmus bir referansa gore normalize edilmis olur.
K_TANIM = [
    ("K1", "Ego kestirim hatasi", "e_kest_p95", 0.60,
     "LK/RANSAC cozumu gercek arka plan eslesmesinden sapiyor"),
    ("K2", "Ego birim matrise dusme", "ego_birim_orani", 0.010,
     "akil suzgeci cozumu atiyor, M = I; Kalman kor devraliyor"),
    # K3'un gostergesi BILEREK d_r_p95 degil d_artik_r_p95. Olculdu:
    # G1_kritik'te d_goruntu/r = 1.32 iken sicrama kapisina gelen gercek artik
    # 1.09 px (r'nin %5'i) - cunku ham kaymanin tamamini once ego M'si, sonra
    # KF hizi soguruyor. Ham oranla puanlamak "arama yaricapi yetmedi" der,
    # oysa hicbir sey kacmamistir. Arama penceresinin gercekten karsilamasi
    # gereken sey EGO SONRASI bagimsiz hedef hareketidir.
    ("K3", "Arama yaricapi yetersiz", "d_artik_r_p95", 1.00,
     "ego sonrasi bagimsiz hedef hareketi DCF penceresi / kapi yaricapini asiyor"),
    ("K4", "Sicrama kapisi cok dar", "sicrama_red_orani", 0.020,
     "PSR yeterli ama olcum kapida atiliyor"),
    ("K5", "KF hiz modeli gecikmesi", "kf_hiz_hatasi_p95", 2.00,
     "sabit hiz varsayimi ivme/manevrada ongoruyu kaciriyor"),
    # K6'nin IKI YUZU VAR ve tek gosterge ikisini de goremez:
    #   (a) EGO tarafi - benzerlik donusumu gercek arka plan eslesmesini
    #       temsil edemiyor. Gostergesi e_model_p95. Yalnizca PITCH'te ateslenir
    #       (perspektif); yaw'da 0'dir, cunku goruntu duzlemi donmesi benzerlik
    #       tarafindan TAM temsil edilir.
    #   (b) GORUNUM tarafi - ego katmani donmeyi dogru olcup KF'ye aktarsa bile
    #       DCF SABLONU dondurulmez; sablon her karede biraz daha uyumsuz olur.
    #       Gostergesi kamera acisal hizidir.
    # Olculdu: G3_kritik'te e_model = 0.00 px (yuz a temiz) ama IoU acigi 0.213
    # ve 133. karede drift var; acisal hiz p95 171 deg/s. Tek gostergeyle
    # puanlansaydi K6 = 0 cikar ve G3'un kopmasi yanlisikla K5'e yazilirdi.
    ("K6", "Olcek/donme modellenmiyor",
     (("e_model_p95", 0.60), ("kamera_acisal_p95", 30.0)),
     None,
     "benzerlik artigi (pitch/perspektif) ya da sablonun dondurulmemesi (yaw)"),
    ("K7", "Gorunum modeli kirlenmesi", "yanlis_kilit_orani", 0.020,
     "KILITLI ama IoU < 0.2: filtre baska bir seyi ogrenmis"),
    ("K8", "Yeniden tespit basarisiz", "kurtarma_max", 20.0,
     "kopma sonrasi geri donus yok ya da cok uzun"),
]


def hipotez_puanla(t, taban):
    """Her hipotez icin puan = gosterge / max(G0 tabani, fiziksel doseme).

    Bir hipotezin birden fazla gostergesi olabilir (bkz. K6); o zaman puan
    gostergelerin EN BUYUGUDUR - hipotez, yuzlerinden biri bile ateslendiginde
    aday olmalidir.
    """
    puan = {}
    for kod, ad, alan, doseme, _ in K_TANIM:
        ciftler = alan if isinstance(alan, tuple) else ((alan, doseme),)
        puan[kod] = max(float(t.get(f, 0.0)) / max(float(taban.get(f, 0.0)), d)
                        for f, d in ciftler)
    return puan


def kopma_var(t):
    """Kopma olcutu: TAVAN IoU'ya gore acik, mutlak IoU'ya gore degil.

    Mutlak esik (ornegin IoU > 0.85) yaniltir: G3'te kamera yaw'i araci
    goruntude dondurur, GT'nin EKSEN HIZALI kutusu buyur ve sabit en-boy
    oranli hicbir takipci 0.84'un ustune cikamaz. O senaryoda 0.83 mukemmel
    takip demektir. Bu yuzden olcut `tavan_iou - iou` acigidir; G0'da bu acik
    0.026'dir ve saglikli tabani verir.
    """
    acik = t["tavan_iou"] - t["iou"]
    return (t["t_drift"] is not None) or (acik > 0.10) or (t["kilit_orani"] < 0.98)


# ---------------------------------------------------------------------------
def _senaryo_listesi(kok):
    from gazebo.senaryolar import FAZ_B
    var = [d for d in ["G0"] + FAZ_B
           if os.path.isdir(os.path.join(kok, d))]
    return var


def main():
    ap = argparse.ArgumentParser(description="Faz B teshis kosucusu")
    ap.add_argument("senaryo", nargs="*", default=None)
    ap.add_argument("--kok", default="data/gazebo")
    ap.add_argument("--cekirdek", default="renk_dcf")
    ap.add_argument("--json", default="cikti/fazb_tani.json")
    a = ap.parse_args()

    adlar = a.senaryo or _senaryo_listesi(a.kok)
    sonuc = {}
    for ad in adlar:
        try:
            sonuc[ad] = olc(ad, kok=a.kok, cekirdek=a.cekirdek)
        except Exception as e:                       # noqa: BLE001
            print(f"{ad}: HATA {type(e).__name__}: {e}", file=sys.stderr)
            continue
        t = sonuc[ad]
        print(f"{ad:12s} IoU {t['iou']:.3f}  kilit {t['kilit_orani']*100:5.1f}%  "
              f"drift {str(t['t_drift']):>4s}  e_ego {t['e_ego_p50']:5.2f}/"
              f"{t['e_ego_p95']:5.2f}  d/r {t['d_r_p95']:4.2f}  "
              f"kf {t['kf_hiz_hatasi_p95']:5.2f}  "
              f"birim {t['ego_birim_orani']*100:4.1f}%  "
              f"red {t['sicrama_red_orani']*100:4.1f}%  "
              f"yk {t['yanlis_kilit_orani']*100:4.1f}%", flush=True)

    taban = sonuc.get("G0", {})
    for ad, t in sonuc.items():
        t["k_puan"] = hipotez_puanla(t, taban)
        t["kopma"] = kopma_var(t)
        t["iou_acik"] = t["tavan_iou"] - t["iou"]
        sirali = sorted(t["k_puan"].items(), key=lambda kv: -kv[1])
        # Baskin hipotez KOPMA OLMASA DA yazilir: G4 ailesinde K6 puani 7.7'ye
        # cikiyor ama IoU acigi hala 0.03 - yani model hatasi olculuyor,
        # takipci henuz kopmuyor. Bu "gizli yuk" bilgisi Faz C'nin sirasini
        # belirlemekte kopma listesinden daha degerli; bastirilmamali.
        # Puan 0.5'in altindaysa hicbir hipotez yuklenmemistir; en yuksegi
        # yazmak gurultuyu bulgu gibi gosterir. G0'in kendi en yuksek puani
        # 0.21 - saglikli tabanin "hipotezi" olamaz.
        t["ana_puan"] = round(sirali[0][1], 2)
        t["ana_hipotez"] = sirali[0][0] if sirali[0][1] >= 0.5 else "-"
        t["ikincil_hipotez"] = sirali[1][0] if sirali[1][1] >= 0.5 else "-"

    if a.json:
        os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
        with open(a.json, "w") as f:
            json.dump(sonuc, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nyazildi: {a.json}")
    return sonuc


if __name__ == "__main__":
    main()
