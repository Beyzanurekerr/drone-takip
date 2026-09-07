"""K-MOD ortak GORSEL URETIM araci - her deney BUNU cagirir, kendi cizim
kodunu yazmaz (talimat).

Girdi: bir deneyin URETTIGI, kare-basina sozluk listesi (`kayit`). Her
sozluk asagidaki anahtarlari TASIYABILIR (hepsi opsiyonel, olmayan alan
cizilmez):

    img          ndarray BGR (zorunlu - kare goruntusu)
    gt           [x,y,w,h] ya da None           - GT kutusu (YESIL)
    sistem_kutu  [x,y,w,h] ya da None            - sistem/secilen kutu (MAVI)
    roi_kutu     [x,y,w,h] ya da None            - ROI penceresi (SARI)
    adaylar      [(x,y), ...] ya da None         - hareket adaylari (KUCUK KIRMIZI nokta)
    secilen_xy   (x,y) ya da None                - secilen aday (KALIN KIRMIZI daire)
    durum        str ya da None                  - "TRUSTED"/"SUSPECT"/"LOST" ya da
                                                    "dogru"/"yanlis"/"cekimser"/"kanit_yok"
    iou          float ya da None
    psr          float ya da None
    ikinci_tepe  float ya da None
    kanit_var    bool ya da None
    mod          str ya da None                  - K3: "dedektor"/"hibrit"/"kucuk_hedef"
    gt_L         float ya da None                 - hedefin px boyutu (verilmezse gt'den turetilir)
    yanlis_kilit bool ya da None                  - True ise kare KIRMIZI kutuyla isaretlenir
    kopus        bool ya da None                  - True ise ekran kenarina KIRMIZI cerceve

KURAL: GT disinda hicbir gorselde oracle bilgisi YOK - `oracle=True`
verilirse dosya adina/HUD'a "ORACLE" damgasi eklenir (cagiran, oracle
kollarini acikca isaretlemekle YUKUMLU).

Dosya adi: <deney>_<senaryo>_<kol>.mp4/png (oracle ise ..._ORACLE eki).
"""
import os

import cv2
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

KOK = "cikti/gorsel"
RENK_GT = (0, 220, 0)          # yesil BGR
RENK_SISTEM = (255, 120, 0)    # mavi
RENK_ROI = (0, 220, 255)       # sari
RENK_ADAY = (60, 60, 220)      # kucuk kirmizi
RENK_SECILEN = (0, 0, 255)     # kalin kirmizi
RENK_KOPUS_CERCEVE = (0, 0, 255)


def _dosya_govdesi(deney, senaryo, kol, oracle):
    ek = "_ORACLE" if oracle else ""
    return f"{deney}_{senaryo}_{kol}{ek}"


def _kutu_ciz(img, kutu, renk, kalinlik=1):
    if kutu is None:
        return
    x, y, w, h = [int(round(v)) for v in kutu]
    cv2.rectangle(img, (x, y), (x + w, y + h), renk, kalinlik)


def _hud_yaz(img, satirlar):
    y = 14
    for s in satirlar:
        cv2.putText(img, s, (4, y), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(img, s, (4, y), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
        y += 13


def _kare_ciz(rec, kare_no, oracle):
    img = rec["img"].copy()
    H, W = img.shape[:2]

    _kutu_ciz(img, rec.get("roi_kutu"), RENK_ROI, 1)
    for i, xy in enumerate(rec.get("adaylar") or []):
        cv2.circle(img, (int(xy[0]), int(xy[1])), 2, RENK_ADAY, -1)
    if rec.get("secilen_xy") is not None:
        sx, sy = rec["secilen_xy"]
        cv2.circle(img, (int(sx), int(sy)), 4, RENK_SECILEN, 2)
    _kutu_ciz(img, rec.get("gt"), RENK_GT, 1)
    sistem_renk = (0, 0, 255) if rec.get("yanlis_kilit") else RENK_SISTEM
    _kutu_ciz(img, rec.get("sistem_kutu"), sistem_renk, 1)

    if rec.get("kopus"):
        cv2.rectangle(img, (0, 0), (W - 1, H - 1), RENK_KOPUS_CERCEVE, 4)

    gt_L = rec.get("gt_L")
    if gt_L is None and rec.get("gt") is not None:
        gt_L = max(rec["gt"][2], rec["gt"][3])
    satirlar = [f"kare {kare_no}"]
    if oracle:
        satirlar.append("*** ORACLE ***")
    if gt_L is not None:
        satirlar.append(f"hedef {gt_L:.1f}px")
    if rec.get("mod"):
        satirlar.append(f"mod={rec['mod']}")
    if rec.get("durum"):
        satirlar.append(f"durum={rec['durum']}")
    if rec.get("iou") is not None:
        satirlar.append(f"IoU={rec['iou']:.2f}")
    if rec.get("psr") is not None:
        satirlar.append(f"PSR={rec['psr']:.1f}")
    if rec.get("kanit_var") is not None:
        satirlar.append(f"kanit={'VAR' if rec['kanit_var'] else 'YOK'}")
    _hud_yaz(img, satirlar)
    return img


def video_uret(deney, senaryo, kol, kayit, oracle=False, fps=30, sadece_hareket_haritasi=False):
    """kayit: kare-basina sozluk listesi (yukaridaki formatta). mp4 yazar."""
    if not kayit:
        return None
    dizin = os.path.join(KOK, deney)
    os.makedirs(dizin, exist_ok=True)
    ek = "_hareket" if sadece_hareket_haritasi else ""
    yol = os.path.join(dizin, _dosya_govdesi(deney, senaryo, kol, oracle) + ek + ".mp4")

    H, W = kayit[0]["img"].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(yol, fourcc, fps, (W, H))
    for i, rec in enumerate(kayit):
        if sadece_hareket_haritasi:
            taban = rec.get("hareket_haritasi")
            img = (cv2.cvtColor(taban, cv2.COLOR_GRAY2BGR) if taban is not None
                  else np.zeros((H, W, 3), np.uint8))
            for xy in rec.get("adaylar") or []:
                cv2.circle(img, (int(xy[0]), int(xy[1])), 2, RENK_ADAY, -1)
            _kutu_ciz(img, rec.get("gt"), RENK_GT, 1)
            _hud_yaz(img, [f"kare {i}", "hareket haritasi + adaylar + GT"])
        else:
            img = _kare_ciz(rec, i, oracle)
        vw.write(img)
    vw.release()
    return yol


def zaman_serisi_uret(deney, senaryo, kol, kayit, oracle=False):
    """3 panelli PNG: (ust) px boyutu+mod gecisleri, (orta) merkez hatasi(log)+IoU,
    (alt) PSR+ikinci-tepe+kanit-yok bandi. Kopus/yanlis-kilit kareleri kirmizi."""
    if plt is None or not kayit:
        return None
    dizin = os.path.join(KOK, deney)
    os.makedirs(dizin, exist_ok=True)
    yol = os.path.join(dizin, _dosya_govdesi(deney, senaryo, kol, oracle) + "_seri.png")

    t = list(range(len(kayit)))
    gt_L = [r.get("gt_L") if r.get("gt_L") is not None else
           (max(r["gt"][2], r["gt"][3]) if r.get("gt") is not None else None) for r in kayit]
    merkez_hata = []
    for r in kayit:
        if r.get("gt") is not None and r.get("sistem_kutu") is not None:
            gc = np.array(r["gt"][:2]) + np.array(r["gt"][2:]) / 2.0
            sc = np.array(r["sistem_kutu"][:2]) + np.array(r["sistem_kutu"][2:]) / 2.0
            merkez_hata.append(float(np.linalg.norm(gc - sc)))
        else:
            merkez_hata.append(None)
    iou_ = [r.get("iou") for r in kayit]
    psr_ = [r.get("psr") for r in kayit]
    ikinci_ = [r.get("ikinci_tepe") for r in kayit]
    kanit_yok = [1.0 if r.get("kanit_var") is False else 0.0 for r in kayit]
    kirmizi_kareler = [i for i, r in enumerate(kayit) if r.get("yanlis_kilit") or r.get("kopus")]

    fig, eksen = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    ax0, ax1, ax2 = eksen

    ax0.plot(t, gt_L, color="black", lw=1.2, label="hedef px boyutu")
    ax0b = ax0.twinx()
    modlar = [r.get("mod") for r in kayit]
    onceki = None
    for i, m in enumerate(modlar):
        if m is not None and m != onceki:
            ax0.axvline(i, color="tab:purple", lw=0.6, ls="--", alpha=0.6)
            onceki = m
    ax0.set_ylabel("px boyutu")
    ax0.legend(loc="upper right", fontsize=7)
    ax0.set_title(f"{deney} / {senaryo} / {kol}" + (" [ORACLE]" if oracle else ""))

    if any(v is not None for v in merkez_hata):
        ax1.plot(t, [v if v and v > 0 else None for v in merkez_hata], color="tab:red",
                 lw=1.0, label="merkez hatasi (px, log)")
        ax1.set_yscale("log")
    if any(v is not None for v in iou_):
        ax1b = ax1.twinx()
        ax1b.plot(t, iou_, color="tab:blue", lw=1.0, label="IoU")
        ax1b.set_ylim(0, 1.05)
        ax1b.set_ylabel("IoU", color="tab:blue")
    ax1.set_ylabel("merkez hatasi (px)", color="tab:red")

    if any(v is not None for v in psr_):
        ax2.plot(t, psr_, color="tab:green", lw=1.0, label="PSR")
    if any(v is not None for v in ikinci_):
        ax2b = ax2.twinx()
        ax2b.plot(t, ikinci_, color="tab:orange", lw=1.0, label="ikinci-tepe orani")
        ax2b.set_ylabel("ikinci-tepe orani", color="tab:orange")
    ax2.fill_between(t, 0, [k * (max([v for v in psr_ if v is not None], default=1) or 1)
                            for k in kanit_yok], color="grey", alpha=0.25, step="mid",
                     label="kanit yok")
    ax2.set_ylabel("PSR", color="tab:green")
    ax2.set_xlabel("kare")

    for ax in (ax0, ax1, ax2):
        for k in kirmizi_kareler:
            ax.axvline(k, color="red", lw=0.8, alpha=0.5)

    fig.tight_layout()
    fig.savefig(yol, dpi=110)
    plt.close(fig)
    return yol


def kare_izgara_uret(deney, senaryo, kol, kayit, indeksler=None, oracle=False):
    """8 karelik ONEMLI-AN izgarasi. `indeksler` verilmezse otomatik secilir:
    kilitlenme (0), 3 kucculme noktasi (30/20/10px'e en yakin), ilk kopus
    (varsa), recovery (kopustan sonraki ilk 'dogru'), celdirici gecisi
    (yoksa son kare), son kare."""
    if not kayit:
        return None
    if indeksler is None:
        indeksler = _otomatik_secim(kayit)
    indeksler = indeksler[:8]
    dizin = os.path.join(KOK, deney)
    os.makedirs(dizin, exist_ok=True)
    yol = os.path.join(dizin, _dosya_govdesi(deney, senaryo, kol, oracle) + "_izgara.png")

    n = len(indeksler)
    kutu_boy = 2
    satir = int(np.ceil(n / 4))
    sutun = min(4, n)
    hucre_h, hucre_w = kayit[0]["img"].shape[:2]
    tuval = np.full((satir * (hucre_h + 16), sutun * hucre_w, 3), 255, np.uint8)
    for i, idx in enumerate(indeksler):
        r, c = divmod(i, 4)
        rec = kayit[idx]
        im = _kare_ciz(rec, idx, oracle)
        y0 = r * (hucre_h + 16)
        tuval[y0:y0 + hucre_h, c * hucre_w:(c + 1) * hucre_w] = im
        gt_L = rec.get("gt_L") or (max(rec["gt"][2], rec["gt"][3]) if rec.get("gt") is not None else None)
        etiket = f"#{idx} L={gt_L:.0f}px IoU={rec.get('iou'):.2f}" if (gt_L and rec.get('iou') is not None) \
            else f"#{idx}"
        cv2.putText(tuval, etiket, (c * hucre_w + 4, y0 + hucre_h + 12),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(yol, tuval)
    return yol


def _otomatik_secim(kayit):
    n = len(kayit)
    secim = [0]
    Ls = [(r.get("gt_L") or (max(r["gt"][2], r["gt"][3]) if r.get("gt") is not None else None))
          for r in kayit]
    for hedef_L in (30, 20, 10):
        gecerli = [(abs((L or 1e9) - hedef_L), i) for i, L in enumerate(Ls)]
        secim.append(min(gecerli)[1])
    kopus_idx = next((i for i, r in enumerate(kayit) if r.get("kopus") or r.get("yanlis_kilit")), None)
    if kopus_idx is not None:
        secim.append(kopus_idx)
        sonraki_dogru = next((i for i in range(kopus_idx + 1, n)
                             if kayit[i].get("durum") in ("dogru", "TRUSTED")), None)
        if sonraki_dogru is not None:
            secim.append(sonraki_dogru)
    secim.append(n - 1)
    # tekrarlari at, sirala
    return sorted(set(secim))


def ozet_tablo_uret(deney, satirlar, basliklar=None):
    """satirlar: [{"kol":.., "K1":True/False/None, "K2":..., ...}, ...] ->
    renkli GECTI/KALDI tablosu PNG."""
    if plt is None or not satirlar:
        return None
    dizin = os.path.join(KOK, deney)
    os.makedirs(dizin, exist_ok=True)
    yol = os.path.join(dizin, f"{deney}_ozet_tablo.png")

    basliklar = basliklar or [k for k in satirlar[0] if k != "kol"]
    kollar = [s["kol"] for s in satirlar]

    fig, ax = plt.subplots(figsize=(1.4 * (len(basliklar) + 1), 0.6 * (len(satirlar) + 1)))
    ax.axis("off")
    hucre_metin, hucre_renk = [], []
    for s in satirlar:
        satir_m, satir_r = [], []
        for b in basliklar:
            v = s.get(b)
            if v is True:
                satir_m.append("GEÇTİ"); satir_r.append("#c8f0c8")
            elif v is False:
                satir_m.append("KALDI"); satir_r.append("#f0c8c8")
            else:
                satir_m.append("—"); satir_r.append("#eeeeee")
        hucre_metin.append(satir_m)
        hucre_renk.append(satir_r)
    tablo = ax.table(cellText=hucre_metin, rowLabels=kollar, colLabels=basliklar,
                     cellColours=hucre_renk, loc="center", cellLoc="center")
    tablo.scale(1, 1.6)
    fig.tight_layout()
    fig.savefig(yol, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return yol


# =============================================================================
# DEMO HUD (Adim 6) - gazebo/demo_hud_uret.py CAGIRIR
#
# Yukarıdaki `_kare_ciz`'den BİLEREK AYRI: o bir teşhis aracı (GT/IoU/PSR
# oracle bilgisi taşır); bu bölüm ÜRÜN demosu içindir - demo izleyicisi GT
# görmez, hiçbir teşhis metriği (IoU/PSR/hassasiyet) ekrana yazılmaz. Aynı
# "kendi çizim kodunu yazma" ilkesi burada da geçerli: `demo_hud_uret.py`
# yalnızca bu fonksiyonları çağırır.
# =============================================================================
DEMO_FONT = cv2.FONT_HERSHEY_SIMPLEX
DEMO_YOK = "-"

# durum renkleri: takip/izleyici.py'deki 5 durumla (main.py:DURUM_RENK'in
# supersetiyle) AYNI aile; KORUMA main.py'de yok (demo'ya özgü), burada
# eklendi - kritik küçülmeyi (KORUMA_ESIK altı) diğer 4 durumdan ayırt eden
# 5. renk.
DEMO_DURUM_RENK = {
    "KILITLI": (0, 255, 255),    # sari
    "SUPHELI": (0, 165, 255),    # turuncu
    "ARAMA":   (255, 160, 0),    # gok mavisi
    "KAYIP":   (0, 0, 255),      # kirmizi
    "KORUMA":  (255, 0, 255),    # magenta - hedef KORUMA_ESIK altina kucculdu
}

# gazebo/kamera_imx500.sdf ile AYNI sayilar (TEK kaynak orada, bkz. o
# dosyanin basligindaki turetim); burada yalnizca KOPYALANDI, TEKRAR
# OLCULMEDI - gazebo/senaryolar.py:IMX500_ODAK_PX ile de AYNI.
IMX500_GEN_REF = 2028
IMX500_ODAK_PX_REF = 1561.0


def demo_odak_px(genislik):
    """Video genişliği IMX500 referansından (2028) farklıysa (ölçekleme)
    odağı orantılı türet - sayı kaynağı `gazebo/kamera_imx500.sdf`, burada
    TEKRAR ÖLÇÜLMEZ."""
    if not genislik or genislik <= 0:
        return IMX500_ODAK_PX_REF
    return IMX500_ODAK_PX_REF * (genislik / float(IMX500_GEN_REF))


def _demo_yaz(img, metin, konum, olcek=0.5, renk=(255, 255, 255), kalinlik=1):
    """Siyah kontur + renkli govde - acik/koyu zeminde okunur (main.py:_yaz
    ile ayni ilke, bagimlilik yaratmamak icin burada kucuk kopyasi)."""
    cv2.putText(img, metin, konum, DEMO_FONT, olcek, (0, 0, 0),
                kalinlik + 2, cv2.LINE_AA)
    cv2.putText(img, metin, konum, DEMO_FONT, olcek, renk, kalinlik, cv2.LINE_AA)


def _demo_karart(img, x0, y0, x1, y1, alfa=0.55):
    """Panel/serit zemini: kesip karartmak (main.py:_karart ile ayni ilke)."""
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(img.shape[1], int(x1)), min(img.shape[0], int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    roi = img[y0:y1, x0:x1]
    roi[:] = (roi * (1.0 - alfa)).astype(img.dtype)


def _demo_mesafe_hesapla(kutu, irtifa, W, H, odak_px):
    """Nadir kamera + düz zemin varsayımıyla PINHOLE geometriden hedefin
    eğik mesafesi + gerçek boyu.

    `irtifa` (m) jsonl'den (Gazebo pozundan) gelir - GERÇEK ölçüm. Yanal
    ofset (kutunun kadraj merkezine göre px uzaklığı) ve gerçek boy ise
    BURADA türetilir: dx_m = irtifa * dx_px / odak_px (benzer üçgenler),
    mesafe = hypot(irtifa, dx_m, dy_m), boy_m = px_boyut * mesafe / odak_px.
    Bu bir TAHMİNDİR (düz zemin varsayımı) - ölçüm değil; hedef aracın
    gerçek boyu (~4.0 m, bkz. `gazebo/senaryolar.py:Y1_MESH_L`) sağlaması
    için kabaca örtüşmesi beklenir.

    Döner: (mesafe_m, boy_m) ya da (None, None) - veri eksikse.
    """
    if kutu is None or irtifa is None or not odak_px:
        return None, None
    cx, cy = kutu[0] + kutu[2] / 2.0, kutu[1] + kutu[3] / 2.0
    dx_px, dy_px = cx - W / 2.0, cy - H / 2.0
    dx_m, dy_m = irtifa * dx_px / odak_px, irtifa * dy_px / odak_px
    mesafe = float(np.hypot(irtifa, np.hypot(dx_m, dy_m)))
    px_boy = max(float(kutu[2]), float(kutu[3]))
    boy_m = float(px_boy * mesafe / odak_px)
    return mesafe, boy_m


def _demo_inset_ciz(img, bolge, buyutme=4, kenar=(0, 220, 255)):
    """Sağ üst köşede `bolge` (x,y,w,h) `buyutme`x büyütülmüş önizleme
    (ROI varsa ROI, yoksa sistem kutusu). Kadraj dışı kısım kırpılır;
    alan geçersizse (kutu None ya da kırpma sonrası boş) hiçbir şey
    çizilmez. Döner: sonraki içeriğin başlayabileceği y (panel bu y'nin
    altından başlar, inset'in üstüne binmesin diye)."""
    UST_PAY = 6
    if bolge is None:
        return UST_PAY
    H, W = img.shape[:2]
    x, y, w, h = [int(round(v)) for v in bolge]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return UST_PAY
    parca = img[y0:y1, x0:x1]
    iw = min(int((x1 - x0) * buyutme), W // 3)
    ih = min(int((y1 - y0) * buyutme), H // 3)
    if iw < 8 or ih < 8:
        return UST_PAY
    inset = cv2.resize(parca, (iw, ih), interpolation=cv2.INTER_NEAREST)
    ix0, iy0 = W - iw - UST_PAY, UST_PAY + 12
    img[iy0:iy0 + ih, ix0:ix0 + iw] = inset
    cv2.rectangle(img, (ix0 - 2, iy0 - 2), (ix0 + iw + 2, iy0 + ih + 2), kenar, 2)
    _demo_yaz(img, "ROI 4x", (ix0, iy0 - 4), 0.42, kenar, 1)
    return iy0 + ih + 10


def _demo_panel_ciz(img, satirlar, vurgu, ust_y):
    """Sağ kenarda TEK bilgi paneli. `satirlar`: [(etiket, deger), ...].
    `ust_y`: panelin başlayacağı y (inset'in altında kalsın diye
    `_demo_inset_ciz`'in dönüşü verilir)."""
    H, W = img.shape[:2]
    f, kal, ped = 0.5, 1, 8
    etiket_w = max(cv2.getTextSize(e + ":", DEMO_FONT, f, kal)[0][0] for e, _ in satirlar)
    deger_w = max(cv2.getTextSize(str(d), DEMO_FONT, f, kal)[0][0] for _, d in satirlar)
    satir_h = int(cv2.getTextSize("Ag", DEMO_FONT, f, kal)[0][1] * 2.2)
    pw = etiket_w + deger_w + 3 * ped
    ph = ped * 2 + satir_h * len(satirlar)
    x0, y0 = W - pw - 6, min(ust_y, max(0, H - ph - 6))
    _demo_karart(img, x0, y0, x0 + pw, y0 + ph)
    cv2.rectangle(img, (x0, y0), (x0 + pw, y0 + ph), (60, 60, 60), 1)
    cv2.rectangle(img, (x0, y0), (x0 + 4, y0 + ph), vurgu, -1)
    y = y0 + ped + satir_h // 2 + 4
    for etiket, deger in satirlar:
        _demo_yaz(img, etiket + ":", (x0 + ped + 6, y), f, (170, 170, 170), kal)
        _demo_yaz(img, str(deger), (x0 + ped + 6 + etiket_w + ped, y), f, (245, 245, 245), kal)
        y += satir_h


def demo_klip_serit_hazirla(durum_dizisi, irtifa_dizisi, genislik, yukseklik=90):
    """Alt şeridin STATİK kısmını (durum bandı + irtifa eğrisi, TÜM klip)
    BİR KEZ çizer - kare başına yeniden hesaplanmaz (900 kare × O(genislik)
    yerine kare başı O(1); `demo_hud_kare_ciz` yalnızca bu tabanı yapıştırıp
    oynatma imlecini çizer). Girdiler `durum_dizisi`/`irtifa_dizisi`: TÜM
    klibin JSONL'den (görüntüsüz) okunmuş hafif skaler listeleri - "bellekte
    biriktirme yok" kuralı KARE GÖRÜNTÜLERİ içindir, bu listeler için değil
    (900 float/str, ihmal edilebilir bellek).

    Döner: `demo_hud_kare_ciz`e `serit=` olarak verilecek sözlük.
    """
    n = len(durum_dizisi)
    bant_h, bosluk, egri_h = 10, 6, 30
    taban = np.zeros((yukseklik, genislik, 3), np.uint8)
    band_y = bosluk
    for x in range(genislik):
        idx = min(n - 1, int(x / max(1, genislik - 1) * (n - 1))) if n > 1 else 0
        renk = DEMO_DURUM_RENK.get(durum_dizisi[idx], (120, 120, 120))
        taban[band_y:band_y + bant_h, x] = renk
    egri_y0 = band_y + bant_h + 16
    gecerli = [v for v in irtifa_dizisi if v is not None]
    if gecerli and n > 1:
        vmin, vmax = min(gecerli), max(gecerli)
        span = max(1e-6, vmax - vmin)
        onceki = None
        for i, v in enumerate(irtifa_dizisi):
            x = int(i / (n - 1) * (genislik - 1))
            if v is None:
                onceki = None
                continue
            y = int(egri_y0 + egri_h - (v - vmin) / span * egri_h)
            if onceki is not None:
                cv2.line(taban, onceki, (x, y), (0, 220, 0), 1, cv2.LINE_AA)
            onceki = (x, y)
        etiket = f"irtifa {vmin:.0f}-{vmax:.0f} m"
    else:
        etiket = "irtifa -"
    return {"taban": taban, "etiket": etiket, "n": n, "yukseklik": yukseklik,
            "alt_sinir": egri_y0 + egri_h}


def _demo_serit_ciz(img, serit, olaylar, kare_no):
    """Alt şerit: (üst) durum bandı + oynatma imleci, (orta) irtifa eğrisi,
    (alt) en yakın olay notu. `serit`: `demo_klip_serit_hazirla` çıktısı.
    `olaylar`: [(kare_no, metin), ...] - durum geçişleri, `demo_hud_uret.py`
    tarafından JSONL'den (görüntüsüz) önceden çıkarılır."""
    H, W = img.shape[:2]
    taban, yukseklik, n = serit["taban"], serit["yukseklik"], serit["n"]
    y0 = H - yukseklik
    _demo_karart(img, 0, y0, W, H)
    cv2.line(img, (0, y0), (W, y0), (80, 80, 80), 1)
    bant = img[y0:y0 + yukseklik, 0:W]
    maske = taban.any(axis=2)
    bant[maske] = taban[maske]
    alt_sinir = y0 + serit["alt_sinir"]     # "alt_sinir" seride GORE LOKAL (0..yukseklik)
    cx = int(kare_no / max(1, n - 1) * (W - 1)) if n > 1 else 0
    cv2.line(img, (cx, y0), (cx, alt_sinir), (255, 255, 255), 1)
    _demo_yaz(img, serit["etiket"], (6, alt_sinir - 4), 0.4, (0, 220, 0), 1)
    yakin = [(k, ad) for k, ad in olaylar if k <= kare_no]
    metin = f"son olay: kare {yakin[-1][0]}  {yakin[-1][1]}" if yakin else "olay yok"
    _demo_yaz(img, metin, (6, alt_sinir + 14), 0.42, (255, 255, 255), 1)


def demo_hud_kare_ciz(img, rec, kare_no, tespit_sayisi, fps, serit, olaylar, odak_px):
    """Adım 6 demo HUD - TEK kare (streaming, `demo_hud_uret.py` diskten
    okuyup hemen yazar; `img` YERİNDE değiştirilir).

    Çizilenler: kutu (durum rengi), ROI, sağ-üst ROI 4x inset, sağ bilgi
    paneli (irtifa/mesafe/px+~m/mod/durum/tespit sayısı/FPS/komut), alt
    şerit (durum bandı + irtifa eğrisi + son olay notu). GT/IoU/PSR gibi
    hiçbir teşhis/oracle bilgisi KULLANILMAZ - `rec` içinde varsa bile
    (bu depoda sim kayıtları GT taşır) burada OKUNMAZ.

    `rec`: jsonl'den TEK kare kaydı (`kare/durum/kutu/roi/px/irtifa/mod/
    komut` anahtarları - bkz. `main.py:kos()` demo_kayit bloğu, gerçek
    şema). `tespit_sayisi`: bu koşumda şimdiye kadar `kutu is not None`
    olan kare sayısı (basit bir çalışan sayaç - resmi bir metrik değil,
    yalnızca demo bilgisi). `fps`: kaynak videonun kare hızı (kaydın
    okuma FPS'i; kare-başı gecikme jsonl'de YOK, uydurulmaz).
    """
    H, W = img.shape[:2]
    durum = rec.get("durum")
    renk = DEMO_DURUM_RENK.get(durum, (200, 200, 200))
    kutu, roi = rec.get("kutu"), rec.get("roi")

    _kutu_ciz(img, kutu, renk, 2)
    if kutu is not None:
        _demo_yaz(img, durum or "?", (int(kutu[0]), max(12, int(kutu[1]) - 6)), 0.5, renk, 1)
    _kutu_ciz(img, roi, RENK_ROI, 1)

    inset_alt = _demo_inset_ciz(img, roi if roi is not None else kutu, buyutme=4)

    mesafe, boy_m = _demo_mesafe_hesapla(kutu, rec.get("irtifa"), W, H, odak_px)
    px_deger = rec.get("px")
    satirlar = [
        ("IRTIFA", f"{rec['irtifa']:.1f} m" if rec.get("irtifa") is not None else DEMO_YOK),
        ("MESAFE", f"{mesafe:.1f} m" if mesafe is not None else DEMO_YOK),
        ("BOYUT", f"{px_deger:.0f} px (~{boy_m:.2f} m)"
                  if px_deger is not None and boy_m is not None else DEMO_YOK),
        ("MOD", rec.get("mod") or DEMO_YOK),
        ("DURUM", durum or DEMO_YOK),
        ("TESPIT", str(tespit_sayisi)),
        ("FPS", f"{fps:.1f}"),
        ("KOMUT", rec.get("komut") or DEMO_YOK),
    ]
    _demo_panel_ciz(img, satirlar, renk, inset_alt)
    _demo_serit_ciz(img, serit, olaylar, kare_no)
    return img
