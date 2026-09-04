"""Gazebo dunyasi ureticisi: zemin dokusu (PNG) + dunya tanimi (SDF).

Neden doku uretiliyor da hazir bir Gazebo dunyasi kullanilmiyor:
ego-motion seyrek Lucas-Kanade'e dayaniyor ve KOSE ariyor. Duz renkli bir
zeminde `goodFeaturesToTrack` hicbir sey bulamaz; o zaman "kamera hareketinde
kopma" olctugumuzu sanirken aslinda dunyanin dokusuzlugunu olcmus oluruz.
`sim/world.py:Ground` bu sorunu zaten cozmus (asfalt greni, calilar, taslar,
tarla sinirlari); burada AYNI tasarim Gazebo dokusu olarak uretiliyor.

WSL2'de render llvmpipe (yazilim) uzerinden gidiyor. Bu yuzden:
  * gölge kapali (pahali, ve ego-motion icin bilgi tasimiyor)
  * zemin tek bir buyuk kutu + albedo dokusu (binlerce kucuk model degil)

Kullanim:
    python3 -m gazebo.dunya_uret G0
    -> data/gazebo/G0/dunya.sdf + data/gazebo/G0/zemin.png
"""
import os

import cv2
import numpy as np

# Doku bir kez uretilir ve senaryolar arasinda PAYLASILIR (sim/senaryolar.py:zemin()
# ile ayni gerekce: 2048x2048 uretimi pahali). Ayni tohum -> ayni doku ->
# senaryolar arasi karsilastirma adil.
DOKU_PX = 2048
ZEMIN_M = 160.0                     # zemin karesinin kenari (metre)
TEXEL_PM = DOKU_PX / ZEMIN_M        # 12.8 texel/m


def _gurultu(n, hucre, rng):
    k = max(2, n // hucre)
    return cv2.resize(rng.random((k, k)).astype(np.float32), (n, n),
                      interpolation=cv2.INTER_CUBIC)


def zemin_dokusu(seed=1, n=None):
    """sim/world.py:Ground ile ayni tasarim, Gazebo albedo dokusu olarak.

    Doku merkezi dunya orijinine denk gelir: texel (i, j) -> dunya
    (x, y) = ((j - N/2)/TEXEL_PM, (N/2 - i)/TEXEL_PM).
    """
    return cv2.transpose(_zemin_dokusu_ham(seed=seed, n=n))


def _zemin_dokusu_ham(seed=1, n=None, texel_pm=None, icerik_zemin_m=None):
    """zemin_dokusu'nun devrik ALINMADAN onceki hali (A11.1: hibrit yama icin).

    `texel_pm`/`icerik_zemin_m` verilmezse (VARSAYILAN - A1-A11 dahil TUM
    mevcut cagiranlar) davranis BIREBIR eskisi gibidir (modul sabitleri
    tpm=12.8, zm=160 - md5 ile dogrulandi, DEGISMEDI).

    A11.1/Y1 DUZELTMESI: modul sabitleri icerigi (yol/bina/agac) hep
    12.8 texel/m ile 160 m'lik bir alana YERLESTIRIYORDU, ama SDF kutusu
    A11 ailesinde 560 m (n=4096 -> fiili goruntulenen yogunluk 7.31
    texel/m). Yani icerik OLMASI GEREKENDEN ~1.75x kucuk render oluyordu
    VE m2t()'nin dondurdugu texel, dunya metresine YANLIS carpanla
    cevriliyordu (bir nesne "world x=16 m"de olsun diye yerlestirilse bile
    Gazebo onu fiilen baska bir x'te gosterirdi). A9-A11 arsivindeki
    HICBIR karsilastirma bundan etkilenmedi (hep AYNI tabanla, gorece
    olcum yapildi) ama Y1 gercek doku/mesh'i DOGRU dunya konumuna
    oturtmak zorunda (yoksa "gercek doku" iddiasi ve renk_dcf kayma
    olcumu bu hatanin urunu olabilir). Y1 bu yuzden dpx/sen.zemin_m'i
    ACIKCA gecirir (bkz. dunya_yaz, zemin_dokusu_hibrit); A9-A11 arsivi
    DOKUNULMADAN modul sabitleriyle calismaya devam eder.
    """
    n = DOKU_PX if n is None else int(n)
    tpm = TEXEL_PM if texel_pm is None else float(texel_pm)
    zm = ZEMIN_M if icerik_zemin_m is None else float(icerik_zemin_m)
    rng = np.random.default_rng(seed)

    g = (_gurultu(n, 96, rng) * 0.55 + _gurultu(n, 24, rng) * 0.30
         + _gurultu(n, 5, rng) * 0.15)
    img = np.empty((n, n, 3), np.float32)
    img[..., 0] = 50 + 50 * g          # B
    img[..., 1] = 85 + 65 * g          # G
    img[..., 2] = 55 + 45 * g          # R
    img = img.astype(np.uint8)
    del g

    def m2t(xm, ym):
        """dunya metre -> texel (sutun, satir)."""
        return int(round(n / 2 + xm * tpm)), int(round(n / 2 - ym * tpm))

    def dm(v):
        return int(round(v * tpm))

    # --- ana yol: y = 0 ekseni boyunca, 9 m genislik ---
    yol_w = 9.0
    x0, yust = m2t(-zm / 2, +yol_w / 2)
    x1, yalt = m2t(+zm / 2, -yol_w / 2)
    cv2.rectangle(img, (x0, yust), (x1, yalt), (68, 68, 70), -1)
    # asfalt greni: LK'nin yol uzerinde de kose bulabilmesi icin sart
    asf = rng.integers(-9, 9, (yalt - yust, x1 - x0, 1), dtype=np.int16)
    img[yust:yalt, x0:x1] = np.clip(
        img[yust:yalt, x0:x1].astype(np.int16) + asf, 0, 255).astype(np.uint8)
    # orta kesikli serit (9 m aralik, 3 m cizgi)
    ym = m2t(0, 0)[1]
    for xm in np.arange(-zm / 2, zm / 2, 9.0):
        a, _ = m2t(xm, 0)
        cv2.rectangle(img, (a, ym - 2), (a + dm(3.0), ym + 2), (215, 215, 215), -1)
    # kenar cizgileri
    cv2.line(img, (x0, yust + 3), (x1, yust + 3), (200, 200, 200), 2)
    cv2.line(img, (x0, yalt - 3), (x1, yalt - 3), (200, 200, 200), 2)

    # --- dikey yan yollar ---
    for xm in np.arange(-zm / 2 + 20, zm / 2, 45.0):
        a, _ = m2t(xm - 3.5, 0)
        b, _ = m2t(xm + 3.5, 0)
        cv2.rectangle(img, (a, 0), (b, n), (66, 66, 68), -1)

    # --- binalar / agaclar / calilar: LK'nin kose kaynagi ---
    for _ in range(140):
        bx, by = rng.uniform(-zm / 2, zm / 2, 2)
        if abs(by) < 14:
            continue
        w_, h_ = rng.uniform(8, 26, 2)
        col = tuple(int(v) for v in rng.integers(70, 190, 3))
        p0, p1 = m2t(bx, by), m2t(bx + w_, by + h_)
        cv2.rectangle(img, p0, p1, col, -1)
        cv2.rectangle(img, p0, p1, tuple(int(v * 0.6) for v in col), 3)
    for _ in range(600):
        tx, ty = rng.uniform(-zm / 2, zm / 2, 2)
        if abs(ty) < 8:
            continue
        cv2.circle(img, m2t(tx, ty), int(rng.uniform(2, 5) * tpm), (30, 70, 35), -1)
    # kucuk olcekli detay - ego-motion'in can damari
    for _ in range(6000):
        tx, ty = rng.uniform(-zm / 2, zm / 2, 2)
        if abs(ty) < 7:
            continue
        r = max(1, int(rng.uniform(0.5, 1.5) * tpm))
        col = (int(rng.integers(25, 60)), int(rng.integers(60, 110)),
               int(rng.integers(25, 60)))
        cv2.circle(img, m2t(tx, ty), r, col, -1)
    # tarla sinirlari
    for _ in range(60):
        tx, ty = rng.uniform(-zm / 2, zm / 2, 2)
        L = rng.uniform(20, 70)
        if rng.random() < 0.5:
            cv2.line(img, m2t(tx, ty), m2t(tx + L, ty), (60, 95, 75), 4)
        else:
            cv2.line(img, m2t(tx, ty), m2t(tx, ty + L), (60, 95, 75), 4)

    # --- otoparklar + park halinde araclar: STATIK celgiciler ---
    # Hareket tabanli tespit bunlari elemek zorunda; gercekci zorluk.
    for px, py in [(-55, 24), (10, -32), (60, 28)]:
        cv2.rectangle(img, m2t(px, py), m2t(px + 38, py + 18), (72, 72, 74), -1)
        for i in range(8):
            for j in range(3):
                cx_, cy_ = px + 3 + i * 4.4, py + 3 + j * 5.5
                col = tuple(int(v) for v in rng.integers(45, 210, 3))
                cv2.rectangle(img, m2t(cx_, cy_), m2t(cx_ + 4.2, cy_ + 1.8), col, -1)

    # UV KONVANSIYONU - ampirik olarak olculdu, varsayilmadi.
    # Gazebo'nun <box> ust yuzeyine doku eslemesi bu modulun `m2t` kabulunun
    # DEVRIGI: dunya x <- doku SATIRI, dunya y <- doku SUTUNU. Duzeltilmezse
    # yol dunyada x = sabit bandina duser, yani hedef asfaltta degil cimende
    # ilerler (olculdu: yol goruntude dikey, arac yolun 24 m solunda).
    # Devrik alinarak doku dunya eksenleriyle hizalanir. Yansima kalabilir ama
    # zararsiz: yol y = 0 etrafinda, doku gurultusu ise istatistiksel olarak
    # simetrik. Devrigin kendisi zemin_dokusu() sarmalayicisinda alinir (bu
    # ham fonksiyon HAM DUNYA-EKSENSIZ tuvali doner - A11.1 hibrit yama bu
    # uzayda calisir, devrik en sonda TEK sefer alinir).
    return img


# ---------------------------------------------------------------------------
# A11.1/Y1: gercek hava goruntusu dokusu (VisDrone hedefsiz kirpim)
# ---------------------------------------------------------------------------
# Tam 560 m alani gercek goruntuyle kaplamak tek bir VisDrone karesinin
# cozunurlugunu asiyor. Mozaikleme (ayna-tekrar VE duz-tekrar) denendi ve
# REDDEDILDI: ayna simetrisi yapay bir kaleydoskop-X cizgisi, duz tekrar
# periyodik yapay bir izgara cizgisi uretiyor - ikisi de "gercek goruntu"
# degil, KENDI mozaikleme artefaktimizi olcerdik. Bunun yerine: TEK, tekrarsiz,
# aynasiz bir yama hedef+celdirici operasyon alaninin merkezine yerlestirilir,
# kenarda prosedurel dokuya feather (yumusak alfa) ile karisir. Yuksek
# irtifada (>~1 patch yaricapi) kamera yama disina cikip prosedurel dokuyu
# gorur - BILINCLI kisit, A11_1_ONKAYIT.md'de belgelendi.
GERCEK_ZEMIN_YAMA = "data/gazebo/_assets/zemin_gercek_kirpim.png"
# Kaynak: VisDrone2019-DET 0000283_01001_d_0000679.jpg, kirpim [y 200:1080,
# x 0:1920], tek arac (1131,323,110,120) cv2.inpaint ile temizlendi (arac
# haric kutu yok, oteki 4 kutu y<175'te, kirpim disinda kaldi).
# A11.3/Y1.2: izgara kaydirildi - operasyon alani (x[-68.8,72.0], y[-9,29.1])
# artik TEK hucre (sol-ust) icinde kaliyor, ic dikisler (Y1.1'in "cifte
# pozlama" bulgusu) operasyon alaninin disina dustu. Eski deger (16,-2)
# grid KESISIMINI operasyon alaninin ORTASINA koyuyordu - Y1.2 bunu
# DUZELTIYOR (bkz. gazebo/y1_yama_uret.py, A11_3_ONKAYIT.md).
GERCEK_ZEMIN_MERKEZ_M = (90.35, -41.25)
GERCEK_ZEMIN_TUY_PX = 60               # feather kenar genisligi (texel)
# Yamanin KENDI piksel uzayinda (A11.2/Y1.1: 2200x1300, 2x2 dort-sahne
# bilesik - gazebo/y1_yama_uret.py), temizlenen arac bolgesi - KOL 2 icin:
# hareket biriktirme burada bir "hayalet" bulursa kaynagi bilinsin. Sol-ust
# hucredeki (eski tek-yama, pad=20 inpaint) aracin bilesik uzaydaki konumu -
# `y1_yama_uret.py --  data/gazebo/_assets/inpaint_konum_v2.json` ile
# URETILDI, elle hesaplanmadi.
INPAINT_PIKSEL_KUTUSU = (819, 95, 957, 242)


def _yama_yerlesimi(n, zemin_m):
    """(tx0, ty0, yw, yh, tpm) - yamanin HAM (devriksiz) tuvaldeki texel
    yerlesimi. zemin_dokusu_hibrit + Y1 dunya-koordinat yardimcilari (KAPSAM
    ve INPAINT konumu) AYNI bu fonksiyonu kullanir - tek dogruluk kaynagi."""
    tpm = n / float(zemin_m)
    yama_boyutu = cv2.imread(GERCEK_ZEMIN_YAMA)
    if yama_boyutu is None:
        raise FileNotFoundError(GERCEK_ZEMIN_YAMA)
    yh, yw = yama_boyutu.shape[:2]
    cx_m, cy_m = GERCEK_ZEMIN_MERKEZ_M
    cx_t = int(round(n / 2 + cx_m * tpm))
    cy_t = int(round(n / 2 - cy_m * tpm))
    tx0, ty0 = cx_t - yw // 2, cy_t - yh // 2
    return tx0, ty0, yw, yh, tpm


def _texel_dunya(tx, ty, n, tpm):
    """HAM tuval texel -> dunya metre (m2t'nin tersi)."""
    return (tx - n / 2.0) / tpm, (n / 2.0 - ty) / tpm


def yama_dunya_sinirlari(n, zemin_m, temiz=False):
    """Yamanin dunya-metre AABB'si: (x_min, x_max, y_min, y_max).

    `n`, `zemin_m`: cagiran senaryonun `doku_px`/`zemin_m`'i (ORNEGIN A11_DOKU_PX
    =4096, A11_ZEMIN_M=560.0 - gazebo/senaryolar.py'den) - bu modul bu
    sabitleri KENDI ICINDE TUTMAZ (senaryolar.py'ye bagimlilik olusturmamak
    icin), cagiran acikca gecirir.

    `temiz=True`: feather bandi HARIC (yalniz SAF gercek piksel, procedurelle
    hic karismamis bolge) - Y2 (2) talebindeki "yama_ici" bayragi bunu
    kullanmali, sinirdaki blend bolgesi ne tam gercek ne tam prosedurel."""
    n = int(n)
    tx0, ty0, yw, yh, tpm = _yama_yerlesimi(n, zemin_m)
    pay = GERCEK_ZEMIN_TUY_PX if temiz else 0
    x0, y1 = _texel_dunya(tx0 + pay, ty0 + pay, n, tpm)
    x1, y0 = _texel_dunya(tx0 + yw - pay, ty0 + yh - pay, n, tpm)
    return min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)


def inpaint_dunya_bolgesi(n, zemin_m):
    """Temizlenen aracin dunya-metre AABB'si (x_min,x_max,y_min,y_max)."""
    n = int(n)
    tx0, ty0, yw, yh, tpm = _yama_yerlesimi(n, zemin_m)
    px0, py0, px1, py1 = INPAINT_PIKSEL_KUTUSU
    x0, y1 = _texel_dunya(tx0 + px0, ty0 + py0, n, tpm)
    x1, y0 = _texel_dunya(tx0 + px1, ty0 + py1, n, tpm)
    return min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)


def zemin_dokusu_hibrit(seed=1, n=None, zemin_m=None):
    """Prosedurel taban (LK korner kaynagi, kenar/yuksek irtifa) + merkeze
    yerlestirilmis GERCEK VisDrone yamasi (feather ile karistirilmis).

    `zemin_m` ZORUNLU ETKİLİ parametre: SDF kutusunun fiili kenar uzunlugu
    (A11 ailesinde 560.0). Fiili texel/m yogunlugu buradan (n/zemin_m)
    hesaplanir ve HEM prosedurel tabana HEM yamanin kendi yerlesimine
    gecirilir - ikisi ayni (dogru) olcekte olmazsa yama ile etrafindaki
    prosedurel doku farkli buyuklukte "gorunur" (dikis noktasinda ani bir
    yogunluk sicramasi olur). Verilmezse (varsayilan davranis KORUNUR,
    eski/hatali TEXEL_PM=12.8 kullanilir) - yalnizca geriye-donuk uyumluluk
    icin, YENI cagirandan HER ZAMAN acikca gecirilmeli (bkz. dunya_yaz).
    """
    zm_fiili = ZEMIN_M if zemin_m is None else float(zemin_m)
    tpm = (DOKU_PX / ZEMIN_M) if n is None and zemin_m is None else (
        (DOKU_PX if n is None else int(n)) / zm_fiili)
    taban = _zemin_dokusu_ham(seed=seed, n=n, texel_pm=tpm, icerik_zemin_m=zm_fiili)
    n = taban.shape[0]
    yama = cv2.imread(GERCEK_ZEMIN_YAMA)
    if yama is None:
        raise FileNotFoundError(GERCEK_ZEMIN_YAMA)
    tx0, ty0, yw, yh, tpm_dogrula = _yama_yerlesimi(n, zm_fiili)
    assert abs(tpm_dogrula - tpm) < 1e-9
    if tx0 < 0 or ty0 < 0 or tx0 + yw > n or ty0 + yh > n:
        raise ValueError(
            f"gercek yama ({yw}x{yh}) taban tuvaline ({n}x{n}) sigmiyor "
            f"(merkez texel {cx_t},{cy_t}) - n buyutulmeli ya da merkez kaydirilmali")

    t = GERCEK_ZEMIN_TUY_PX
    mask = np.ones((yh, yw), np.float32)
    ramp = np.linspace(0.0, 1.0, t, dtype=np.float32)
    mask[:t, :] *= ramp[:, None]
    mask[-t:, :] *= ramp[::-1, None]
    mask[:, :t] *= ramp[None, :]
    mask[:, -t:] *= ramp[None, ::-1]

    bolge = taban[ty0:ty0 + yh, tx0:tx0 + yw].astype(np.float32)
    karisim = (yama.astype(np.float32) * mask[..., None]
               + bolge * (1.0 - mask[..., None]))
    sonuc = taban.copy()
    sonuc[ty0:ty0 + yh, tx0:tx0 + yw] = np.clip(karisim, 0, 255).astype(np.uint8)
    return cv2.transpose(sonuc)


# ---------------------------------------------------------------------------
_ARAC_SDF = """
    <model name="{ad}">
      <static>false</static>
      <pose>{x} {y} {z} 0 0 {yaw}</pose>
      <link name="govde">
        <gravity>false</gravity>
        <inertial>
          <mass>1200</mass>
          <inertia><ixx>500</ixx><iyy>2000</iyy><izz>2200</izz>
                   <ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia>
        </inertial>
        <visual name="kasa">
          <geometry><box><size>{L} {W} {H}</size></box></geometry>
          <material>
            <ambient>{r} {g} {b} 1</ambient>
            <diffuse>{r} {g} {b} 1</diffuse>
            <specular>0.2 0.2 0.2 1</specular>
          </material>
        </visual>
        <visual name="tavan">
          <pose>{tavan_dx} 0 {tavan_dz} 0 0 0</pose>
          <geometry><box><size>{tavan_L} {tavan_W} {tavan_H}</size></box></geometry>
          <material>
            <ambient>{rk} {gk} {bk} 1</ambient>
            <diffuse>{rk} {gk} {bk} 1</diffuse>
          </material>
        </visual>
      </link>
{hiz_kontrol}
{poz_yayinci}
    </model>"""

# A11.1/Y1: gercekci dokulu mesh (Fuel). Kutu template'iyle AYNI iskelet
# (gravity/inertial/hiz_kontrol/poz_yayinci) - yalnizca gorsel farkli, collision
# YOK (kutu template'inde de yok, kinematik arac hicbir seyle çarpismiyor).
_ARAC_SDF_MESH = """
    <model name="{ad}">
      <static>false</static>
      <pose>{x} {y} {z} 0 0 {yaw}</pose>
      <link name="govde">
        <gravity>false</gravity>
        <inertial>
          <mass>1200</mass>
          <inertia><ixx>500</ixx><iyy>2000</iyy><izz>2200</izz>
                   <ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia>
        </inertial>
        <visual name="mesh">
          <pose>{mx} {my} {mz} {mroll} {mpitch} {myaw}</pose>
          <geometry><mesh><scale>{s} {s} {s}</scale><uri>{obj}</uri></mesh></geometry>
        </visual>
      </link>
{hiz_kontrol}
{poz_yayinci}
    </model>"""

# Mesh kaydi: obj yolu + olcek + GORSEL yerel pozu. Poz, meshin KENDI bbox
# merkezini link kokenine (== GT kutusunun merkezi, veri/gazebo.py:
# _kutu_koseleri, Arac.L/W/H) tasir - aksi halde mesh gorunumu GT kutusuna
# gore kayik olur (hatchback.obj kendi ekseninde simetrik degil, govde
# on agirlikli: bbox merkezi geometrik merkezden 0.34 m kayik). Turetme:
# A11_1_ONKAYIT.md.
_MESH_KOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "gazebo", "_assets")
MESH_KAYIT = {
    "hatchback": dict(
        obj=os.path.join(_MESH_KOK, "hatchback", "hatchback.obj"),
        olcek=0.0254,
        # (x, y, z, roll, pitch, yaw) - bbox merkezini (0,-0.34355,0.77261)
        # local origin'e tasiyip 90 derece dondurur (mesh Y ekseni = uzunluk
        # -> govde/dunya +X, Fuel model.sdf'teki bakili pose ile ayni yon).
        pose=(-0.34355, 0.0, -0.77261, 0.0, 0.0, 1.5707963267948966),
    ),
}

# SceneBroadcaster'in /dynamic_pose/info yayini DUVAR SAATIYLE kisitlanir; sim
# degisken hizda kostugu icin ornekler arasi SIM-ZAMANI araligi duzensiz olur ve
# kare-poz eslestirmesi tolerans disina taSar (olculdu: 20 karenin 10'u dustu).
# PosePublisher ise `_info.simTime` uzerinden kisitlar -> duzenli sim-zamani izgarasi.
_POZ_YAYINCI = """      <plugin filename="gz-sim-pose-publisher-system"
              name="gz::sim::systems::PosePublisher">
        <publish_link_pose>false</publish_link_pose>
        <publish_visual_pose>false</publish_visual_pose>
        <publish_collision_pose>false</publish_collision_pose>
        <publish_sensor_pose>false</publish_sensor_pose>
        <publish_model_pose>true</publish_model_pose>
        <publish_nested_model_pose>false</publish_nested_model_pose>
        <use_pose_vector_msg>true</use_pose_vector_msg>
        <static_publisher>false</static_publisher>
        <update_frequency>120</update_frequency>
      </plugin>"""

_HIZ_KONTROL = """      <plugin filename="gz-sim-velocity-control-system"
              name="gz::sim::systems::VelocityControl">
        <initial_linear>{vx} {vy} {vz}</initial_linear>
        <initial_angular>{wx} {wy} {wz}</initial_angular>
      </plugin>"""

_DUNYA_SDF = """<?xml version="1.0" ?>
<!-- URETILMISTIR - elle duzenlemeyin. Kaynak: gazebo/dunya_uret.py -->
<sdf version="1.9">
  <world name="{dunya}">
    <physics name="varsayilan" type="ignored">
      <max_step_size>{adim}</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
      <background_color>0.55 0.65 0.80</background_color>
    </plugin>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <plugin filename="gz-sim-scene-broadcaster-system"
            name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-user-commands-system"
            name="gz::sim::systems::UserCommands"/>

    <gravity>0 0 -9.8</gravity>
    <scene>
      <ambient>0.75 0.75 0.75 1</ambient>
      <background>0.55 0.65 0.80</background>
      <shadows>false</shadows>
    </scene>
    <light type="directional" name="gunes">
      <cast_shadows>false</cast_shadows>
      <pose>0 0 120 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <specular>0.15 0.15 0.15 1</specular>
      <direction>-0.35 0.25 -0.90</direction>
    </light>

    <!-- zemin: tek buyuk kutu + uretilmis albedo dokusu -->
    <model name="zemin">
      <static>true</static>
      <pose>0 0 -0.10 0 0 0</pose>
      <link name="l">
        <collision name="c">
          <geometry><box><size>{zemin} {zemin} 0.2</size></box></geometry>
        </collision>
        <visual name="v">
          <geometry><box><size>{zemin} {zemin} 0.2</size></box></geometry>
          <material>
            <ambient>1 1 1 1</ambient>
            <diffuse>1 1 1 1</diffuse>
            <specular>0 0 0 1</specular>
            <pbr><metal>
              <albedo_map>zemin.png</albedo_map>
              <metalness>0.0</metalness>
              <roughness>1.0</roughness>
            </metal></pbr>
          </material>
        </visual>
      </link>
    </model>
{araclar}

    <!-- drone: kamera tasiyicisi.
         MODEL DIK DURUR; nadir donusu sensorun kendi <pose>'unda.
         Neden: VelocityControl komutlari GOVDE cercevesindedir. Nadir donus
         model pozunda kalsaydi govde +X'i dunya -Z olurdu ve "ileri git"
         komutu kamerayi asagi surerdi; "yaw" komutu da goruntude yaw degil
         pitch uretirdi. Donus sensore tasininca govde eksenleri dunya
         eksenleriyle ortusur: wz -> goruntu donmesi, wy -> pitch, vx -> saga.
         Kameranin DUNYA pozu = model pozu o sensor pozu; bileske
         gazebo/kaydet.py icinde alinip pozlar.csv'ye kam_* olarak yazilir. -->
    <model name="drone">
      <static>{drone_statik}</static>
      <pose>{kx} {ky} {kz} 0 0 0</pose>
      <link name="govde">
        <gravity>false</gravity>
        <inertial>
          <mass>2.0</mass>
          <inertia><ixx>0.05</ixx><iyy>0.05</iyy><izz>0.08</izz>
                   <ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia>
        </inertial>
        <sensor name="kam" type="camera">
          <pose>0 0 0 {kroll} {kpitch} {kyaw}</pose>
          <always_on>1</always_on>
          <update_rate>{kam_hz}</update_rate>
          <topic>kamera</topic>
          <camera>
            <horizontal_fov>{fov}</horizontal_fov>
            <image>
              <width>{gen}</width><height>{yuk}</height><format>R8G8B8</format>
            </image>
            <clip><near>0.5</near><far>800</far></clip>
            <noise><type>gaussian</type><mean>0</mean><stddev>{gurultu}</stddev></noise>
          </camera>
        </sensor>
        <!-- A11/KOL 1: ego telafisi icin IMU. Sensor GOVDEDE, kamera gibi
             dondurulmus DEGIL: gorsel ego kamera cercevesinde olculuyor,
             IMU govde cercevesinde; donusum okuma tarafinda yapilir
             (kam_roll/pitch/yaw meta.json'da). -->
        <sensor name="imu" type="imu">
          <always_on>1</always_on>
          <update_rate>{imu_hz}</update_rate>
          <topic>imu</topic>
        </sensor>
      </link>
{drone_eklenti}
    </model>
  </world>
</sdf>
"""


def fov_hesapla(genislik, odak_px):
    """horizontal_fov: istenen odak uzakligindan (px) turetilir.

    Mevcut simulator FOCAL = 500 px*m kullaniyor (sim/world.py). Ayni odagi
    Gazebo'da kurmak, ayni irtifada AYNI piksel/metre oranini verir; boylece
    hedef piksel boyutu sim baseline'iyla karsilastirilabilir kalir.
    """
    return 2.0 * float(np.arctan(0.5 * genislik / odak_px))


def dunya_yaz(sen, kok="data/gazebo"):
    """Senaryo tanimindan SDF + doku uretir. Doner: (sdf_yolu, dizin)."""
    dizin = os.path.join(kok, sen.ad)
    os.makedirs(dizin, exist_ok=True)

    # DOKU ONBELLEGI: 2048^2 uretimi ~10 s surer ve 14 senaryo icin ayni
    # tohumla ayni dokudur. Bir kez uretilir, senaryo dizinlerine sabit bag
    # (hardlink) ile takilir - hem hizli hem 14 x 12 MB disk israfi yok.
    # Bag kurulamayan dosya sistemlerinde kopyaya duser.
    onbellek = os.path.join(kok, "_doku")
    os.makedirs(onbellek, exist_ok=True)
    dpx = int(getattr(sen, "doku_px", DOKU_PX))
    zemin_tipi = getattr(sen, "zemin_tipi", "prosedurel")
    if zemin_tipi == "gercek":
        # A11.1/Y1: sabit (tohumsuz) - GERCEK_ZEMIN_YAMA + merkez tek bir
        # yerlesim tanimlar, seed'e gore degismez.
        zm_sen = getattr(sen, "zemin_m", ZEMIN_M)
        kaynak_doku = os.path.join(onbellek, f"zemin_gercek_{dpx}_{zm_sen:.0f}.png")
        if not os.path.exists(kaynak_doku):
            cv2.imwrite(kaynak_doku, zemin_dokusu_hibrit(seed=sen.doku_seed, n=dpx,
                                                          zemin_m=zm_sen))
    else:
        kaynak_doku = os.path.join(onbellek, f"zemin_{sen.doku_seed}_{dpx}.png")
        if not os.path.exists(kaynak_doku):
            cv2.imwrite(kaynak_doku, zemin_dokusu(seed=sen.doku_seed, n=dpx))
    doku_yolu = os.path.join(dizin, "zemin.png")
    if not os.path.exists(doku_yolu):
        try:
            os.link(kaynak_doku, doku_yolu)
        except OSError:
            import shutil
            shutil.copyfile(kaynak_doku, doku_yolu)

    parcalar = []
    for a in sen.araclar:
        # profil varsa t=0 degeri baslangic hizi olur (govde cercevesi)
        v0 = a.profil(0.0) if a.profil else (a.vx, a.vy, a.wz)
        hiz_kontrol = _HIZ_KONTROL.format(vx=v0[0], vy=v0[1], vz=0.0,
                                          wx=0.0, wy=0.0, wz=v0[2])
        if getattr(a, "mesh", None):
            m = MESH_KAYIT[a.mesh]
            parcalar.append(_ARAC_SDF_MESH.format(
                ad=a.ad, x=a.x0, y=a.y0, z=a.H / 2.0, yaw=a.yaw,
                s=m["olcek"], obj=m["obj"],
                mx=m["pose"][0], my=m["pose"][1], mz=m["pose"][2],
                mroll=m["pose"][3], mpitch=m["pose"][4], myaw=m["pose"][5],
                hiz_kontrol=hiz_kontrol, poz_yayinci=_POZ_YAYINCI))
            continue
        rk, gk, bk = [c * 0.45 for c in a.renk]
        parcalar.append(_ARAC_SDF.format(
            ad=a.ad, x=a.x0, y=a.y0, z=a.H / 2.0, yaw=a.yaw,
            L=a.L, W=a.W, H=a.H,
            r=a.renk[0], g=a.renk[1], b=a.renk[2],
            rk=rk, gk=gk, bk=bk,
            tavan_dx=-0.25, tavan_dz=a.H * 0.42,
            tavan_L=a.L * 0.45, tavan_W=a.W * 0.80, tavan_H=a.H * 0.30,
            hiz_kontrol=hiz_kontrol, poz_yayinci=_POZ_YAYINCI))

    if sen.drone_statik:
        drone_eklenti = ""
    else:
        # baslangic hizi = profilin t=0 degeri (DUNYA -> govde donusumu gerekmez:
        # model t=0'da dik durur, iki cerceve ortusur). Sonraki her ornekte
        # gazebo/kaydet.py:Surucu cmd_vel yayinlar.
        v0 = sen.kam_profil(0.0) if sen.kam_profil else (0.0,) * 6
        drone_eklenti = (_HIZ_KONTROL.format(
            vx=v0[0], vy=v0[1], vz=v0[2], wx=v0[3], wy=v0[4], wz=v0[5])
            + "\n" + _POZ_YAYINCI)

    sdf = _DUNYA_SDF.format(
        dunya=sen.ad, adim=sen.adim, zemin=getattr(sen, "zemin_m", ZEMIN_M),
        imu_hz=getattr(sen, "imu_hz", 200.0),
        araclar="\n".join(parcalar),
        drone_statik="true" if sen.drone_statik else "false",
        kx=sen.kam_x, ky=sen.kam_y, kz=sen.kam_z,
        kroll=sen.kam_roll, kpitch=sen.kam_pitch, kyaw=sen.kam_yaw,
        kam_hz=sen.kam_hz, fov=fov_hesapla(sen.genislik, sen.odak_px),
        gen=sen.genislik, yuk=sen.yukseklik, gurultu=sen.gurultu,
        drone_eklenti=drone_eklenti)

    sdf_yolu = os.path.join(dizin, "dunya.sdf")
    with open(sdf_yolu, "w") as f:
        f.write(sdf)
    return sdf_yolu, dizin


if __name__ == "__main__":
    import sys

    from gazebo.senaryolar import SENARYOLAR

    ad = sys.argv[1] if len(sys.argv) > 1 else "G0"
    yol, dizin = dunya_yaz(SENARYOLAR[ad]())
    print(f"yazildi: {yol}")
    print(f"doku   : {os.path.join(dizin, 'zemin.png')}")
