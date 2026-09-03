"""Gazebo kontrollu senaryolari: G0 (kontrol) + G1-G7 (Faz B teshis ailesi).

TASARIM KURALI
--------------
Her senaryo TEK bir degiskeni degistirir; kalan her sey ortak "baz"dan gelir.
Boylece olculen fark tek bir nedene baglanabilir.

    G0        kamera SABIT, hedef duz gider           -> e_ego = 0 ucu
    G1-G5     ortak baz + YALNIZCA kamera bozulmasi   -> kamera esigi
    G7        ortak baz + YALNIZCA hedef bozulmasi    -> hedef esigi
    G6        ortak baz + IKISI birden                -> birlesik esik

ORTAK BAZ (G1-G7)
-----------------
Kamera hedefi TAKIP EDER: sabit 4.8 m/s ile dunya +X yonunde suzulur ve
hedefin baslangic noktasinin tam ustunden baslar. Sonuc:

  * hedef goruntude NOMINAL OLARAK SABIT kalir (u ~ 320, v ~ 264)
  * goruntudeki hedef hareketi = yalnizca HEDEF bozulmasi
  * arka plandaki akis         = yalnizca KAMERA bozulmasi
  * 300 kare boyunca hedef kadraj disina cikmaz (kenar payi ~267 px)

Bu bazin kendisi de bir ego yuku tasir: 4.8 m/s x 11.11 px/m / 30 Hz =
**1.78 px/kare** sabit arka plan kaymasi. G0'da bu sifirdir; G1-G7 tablolari
bu yuzden G0 ile degil, KENDI yumusak seviyeleriyle karsilastirilmalidir.

NEDEN KAMERA HEDEFI TAKIP EDIYOR
Alternatif (G0'daki gibi sabit kamera + hareketli hedef) denendi ve elendi:
hedefin kadraj icindeki payi 53 px'e iniyor, kamera salinim genligi 3.6 m'yi
(40 px) gecemiyor ve agresif seviye kurulamiyordu. Kamera hedefi takip edince
pay 267 px'e cikiyor; 40 m/s'lik salinim bile kadraj icinde kaliyor.

CERCEVE SOZLESMESI - IKISI FARKLI, BILEREK
------------------------------------------
    Arac.profil(t)  -> (v_ileri, v_yanal, wz)   ARACIN KENDI cercevesi
    GzSenaryo.kam_profil(t) -> (vx,vy,vz, wx,wy,wz)   DUNYA cercevesi

Arac icin govde cercevesi dogaldir (araba burnunun gittigi yere gider).
Kamera icin dunya cercevesi sarttir: G4'te drone pitch'lenince govde X'i
dunya X'i olmaktan cikar; profil govde cercevesinde yazilsaydi "ileri" komutu
kendiliginden dikey bilesen kazanirdi. `gazebo/kaydet.py:Surucu` dunya
komutunu o anki poza gore govde cercevesine cevirip yayinlar.

KAMERA YERLESIMI
----------------
Drone modeli DIK durur (model pozu 0 0 0 rpy); nadir donusu KAMERA SENSORUNUN
kendi `<pose>`'una tasindi (`KAM_ROT`). Boylece:
    govde wz = kamera yaw'i (goruntu duzleminde donme)
    govde wy = kamera pitch'i (optik eksenin nadirden sapmasi)
    govde vx = dunya +X (goruntude saga)
Aksi halde her acisal komut karisik bir eksende doner ve "yaw senaryosu"
aslinda yaw+pitch olurdu. Kamera dunya pozu = model pozu o KAM_ROT; bu
bileske `gazebo/kaydet.py` icinde alinip `pozlar.csv`'ye kam_* olarak yazilir,
yani `veri/gazebo.py` bu degisiklikten etkilenmez.

Kamera parametreleri bilerek `sim/world.py` ile hizalandi:
    odak 500 px  ·  irtifa 45 m  ->  11.11 px/m  ->  hedef ~56 x 22 px
"""
import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

# --- olcek sabitleri (rapor ve senaryo tasariminda kullanilir) --------------
IRTIFA = 45.0
ODAK_PX = 500.0
PX_PER_M = ODAK_PX / IRTIFA          # 11.11 px/m
KAM_HZ = 30.0
BAZ_HIZ = 4.8                        # hedefin nominal hizi = kameranin baz hizi

# kamera sensorunun govdeye gore duruSu: +90 pitch -> optik eksen dunya -Z,
# +90 yaw -> dunya +X goruntude SAGA, dunya +Y YUKARI.
KAM_ROT = (0.0, math.pi / 2, math.pi / 2)


def px_kare(v_ms):
    """m/s cinsinden hiz -> nadir kamerada px/kare goruntu kaymasi."""
    return v_ms * PX_PER_M / KAM_HZ


def px_kare_acisal(w_rads, yaricap_px=0.0):
    """rad/s acisal hiz -> px/kare. yaricap 0 ise pitch (odak x aci), degilse yaw."""
    if yaricap_px:
        return yaricap_px * w_rads / KAM_HZ
    return ODAK_PX * w_rads / KAM_HZ


def kosinus(A, f, faz=0.0):
    """A cos(2 pi f t + faz) - bozulma profillerinin TEK bicimi.

    NEDEN SINUS DEGIL. Profil bir HIZ verir; goruntude gorulen sey onun
    INTEGRALIDIR. Hiz sinus olursa konum (1 - cos) bicimini alir: tek yonlu
    ve genligin IKI KATI kadar sapar. Olculdu (G4 agresif, sinus surumu):
    hedeflenen +-16.2 derece pitch yerine 0..32.4 derece gitti, goruntu 312 px
    tek yone kaydi ve hedef 3 saniyede kadrajin sag kenarina dayandi (u = 639).
    Kosinus hizla integral temiz sinus olur: sifir ortalamali, +-A/(2 pi f).

    Bedeli t = 0'da hizin A'dan baslamasi. Kinematik modelde (VelocityControl,
    yercekimi kapali) bu zararsiz ve SDF'teki `initial_linear` zaten
    `profil(0)` ile kuruldugu icin siçrama da yok.
    """
    return lambda t: A * math.cos(2.0 * math.pi * f * t + faz)


def genlik_konum(A, f):
    """Hiz genligi A, frekans f -> konum/aci genligi (tek yon)."""
    return A / (2.0 * math.pi * f)


def yamuk(t0, ramp, sure):
    """0 -> 1 -> 0 yamuk darbe: [t0, t0+sure] arasi 1, kenarlarda `ramp` s rampa."""
    def g(t):
        if t <= t0 or t >= t0 + sure:
            return 0.0
        if t < t0 + ramp:
            return (t - t0) / ramp
        if t > t0 + sure - ramp:
            return (t0 + sure - t) / ramp
        return 1.0
    return g


@dataclass
class Arac:
    """Kinematik arac. Hiz VelocityControl ile dogrudan verilir (fizik surusu yok).

    `vx`, `vy` aracin KENDI cercevesinde; `yaw` ile birlikte dunya hizini verir.
    `profil` verilirse t (s) -> (v_ileri, v_yanal, wz) doner ve her poz
    orneginde cmd_vel olarak yayinlanir; `vx/vy/wz` o zaman yalnizca t=0
    baslangic degeridir.
    """
    ad: str
    x0: float
    y0: float
    yaw: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    wz: float = 0.0
    renk: tuple = (0.16, 0.16, 0.75)     # RGB 0..1 (SDF material)
    L: float = 4.6
    W: float = 1.9
    H: float = 1.50
    profil: Optional[Callable[[float], Tuple[float, float, float]]] = None


@dataclass
class GzSenaryo:
    ad: str
    aciklama: str
    amac: str
    araclar: List[Arac]
    hedef_ad: str
    # --- kamera ---
    kam_x: float = 0.0
    kam_y: float = 0.0
    kam_z: float = IRTIFA
    # sensorun GOVDEYE gore duruSu (model pozu her zaman dik durur)
    kam_roll: float = KAM_ROT[0]
    kam_pitch: float = KAM_ROT[1]
    kam_yaw: float = KAM_ROT[2]
    kam_hz: float = KAM_HZ
    drone_statik: bool = True
    # t (s) -> (vx, vy, vz, wx, wy, wz) DUNYA cercevesinde
    kam_profil: Optional[Callable[[float], Tuple[float, ...]]] = None
    # --- goruntu ---
    genislik: int = 640
    yukseklik: int = 480
    odak_px: float = ODAK_PX
    gurultu: float = 0.007
    # --- kosum ---
    adim: float = 1.0 / 240.0           # kamera periyodunun tam boleni (8 adim/kare)
    kare: int = 300
    doku_seed: int = 1
    # --- A11 (Gazebo yatagi) ---
    zemin_m: float = 160.0              # zemin karesinin kenari; kucultme
                                        # senaryolari yuksek irtifada daha genis
                                        # zemin ister (goruntu 288 m'de 369 m)
    doku_px: int = 2048                 # doku cozunurlugu (zemin_m ile birlikte
                                        # texel/m'yi belirler)
    imu_hz: float = 200.0               # A11/KOL 1: IMU ornekleme
    aile: str = ""                      # G1..G7
    siddet: str = ""                    # yumusak | agresif
    beklenen: str = ""                  # tasarimda hedeflenen px/kare yuku
    etiketler: List[str] = field(default_factory=list)

    @property
    def hedef(self):
        return next(a for a in self.araclar if a.ad == self.hedef_ad)


# ---------------------------------------------------------------------------
# G0 - KONTROL SENARYOSU  (Faz A'da dondurulmustur, DEGISTIRILMEDI)
# ---------------------------------------------------------------------------
def G0():
    """Sabit nadir kamera + sabit hizla duz ilerleyen hedef.

    Bu senaryo bir SAGLIK TESTIDIR, bir zorluk testi degil. Amaci:
      * Gazebo'nun render'i / dokusu ego-motion'a yetiyor mu (M ~ birim mi)
      * GT izdusumu ve kare-poz senkronu dogru mu
      * A3.8 takipcisi Gazebo goruntusunde sim'deki gibi davraniyor mu

    Hedef 10 sn'de 48 m yol alir; kadraj yarim genisligi 28.8 m oldugundan
    -24 -> +24 araligi tamamen kadraj icinde kalir.
    """
    araclar = [
        Arac("hedef", x0=-24.0, y0=-2.2, yaw=0.0, vx=BAZ_HIZ,
             renk=(0.16, 0.16, 0.75)),                 # mavi
        Arac("celdirici", x0=+20.0, y0=+2.2, yaw=math.pi, vx=3.5,
             renk=(0.75, 0.65, 0.15)),                 # sari, ters yonde
    ]
    return GzSenaryo(
        ad="G0",
        aciklama="Sabit nadir kamera (45 m), sabit hizli hedef (4.8 m/s)",
        amac="Gazebo'nun kendisi takipciye regresyon getiriyor mu?",
        araclar=araclar, hedef_ad="hedef",
        kam_x=0.0, kam_y=0.0, kam_z=IRTIFA, drone_statik=True,
        kare=300, aile="G0", siddet="-",
        beklenen="arka plan 0.00 px/kare",
        etiketler=["kontrol", "e_ego=0"])


# ---------------------------------------------------------------------------
# G1-G7 ORTAK BAZ
# ---------------------------------------------------------------------------
HEDEF_X0, HEDEF_Y0 = -24.0, -2.2
CELDIRICI = dict(x0=+20.0, y0=+2.2, yaw=math.pi, vx=3.5, renk=(0.75, 0.65, 0.15))


def _baz_araclar(hedef_profil=None):
    return [
        Arac("hedef", x0=HEDEF_X0, y0=HEDEF_Y0, yaw=0.0, vx=BAZ_HIZ,
             renk=(0.16, 0.16, 0.75), profil=hedef_profil),
        Arac("celdirici", **CELDIRICI),
    ]


def _kam(vx=None, vy=None, vz=None, wx=None, wy=None, wz=None):
    """Baz (4.8 m/s +X) uzerine bozulma ekleyen dunya-cercevesi kamera profili.

    Argumanlar t -> deger fonksiyonu ya da None (sifir). Baz hiz her zaman
    eklenir; boylece hedef goruntude nominal olarak sabit kalir.
    """
    sifir = (lambda t: 0.0)
    fx, fy, fz = vx or sifir, vy or sifir, vz or sifir
    gx, gy, gz = wx or sifir, wy or sifir, wz or sifir

    def profil(t):
        return (BAZ_HIZ + fx(t), fy(t), fz(t), gx(t), gy(t), gz(t))
    return profil


def _sen(ad, aile, siddet, aciklama, amac, beklenen, kam_profil,
         hedef_profil=None, kam_x=HEDEF_X0, etiketler=()):
    return GzSenaryo(
        ad=ad, aciklama=aciklama, amac=amac,
        araclar=_baz_araclar(hedef_profil), hedef_ad="hedef",
        kam_x=kam_x, kam_y=0.0, kam_z=IRTIFA,
        drone_statik=False, kam_profil=kam_profil,
        kare=300, aile=aile, siddet=siddet, beklenen=beklenen,
        etiketler=list(etiketler))


# --- G1: kamera ileri (dunya +X = goruntude yatay) --------------------------
def _G1(siddet, A, f):
    return _sen(
        f"G1_{siddet}", "G1", siddet,
        f"Kamera ileri-geri oteleme: {A:.0f} m/s genlik, {f:.2f} Hz",
        "Saf yatay oteleme kac px/kare'de takipciyi koparir?",
        f"arka plan tepe {px_kare(A):.1f} px/kare",
        _kam(vx=kosinus(A, f)), etiketler=["kamera", "oteleme", "eksen-x"])


def G1_yumusak():
    return _G1("yumusak", 12.0, 0.40)


def G1_agresif():
    return _G1("agresif", 40.0, 0.50)


# --- G2: kamera yanal (dunya +Y = goruntude dikey) --------------------------
def _G2(siddet, A, f):
    return _sen(
        f"G2_{siddet}", "G2", siddet,
        f"Kamera yanal oteleme: {A:.0f} m/s genlik, {f:.2f} Hz",
        "Yanal oteleme yatay otelemeden farkli mi kopariyor?",
        f"arka plan tepe {px_kare(A):.1f} px/kare",
        _kam(vy=kosinus(A, f)), etiketler=["kamera", "oteleme", "eksen-y"])


def G2_yumusak():
    return _G2("yumusak", 12.0, 0.40)


def G2_agresif():
    return _G2("agresif", 40.0, 0.50)


# --- G3: kamera yaw (goruntu duzleminde donme) ------------------------------
def _G3(siddet, A, f):
    return _sen(
        f"G3_{siddet}", "G3", siddet,
        f"Kamera yaw salinimi: {A:.2f} rad/s genlik, {f:.2f} Hz",
        "Goruntu duzlemi donmesi (DCF donme-degismez degil) nerede kopar?",
        f"kadraj kenarinda tepe {px_kare_acisal(A, 300.0):.1f} px/kare, "
        f"aci genligi {math.degrees(genlik_konum(A, f)):.0f} deg",
        _kam(wz=kosinus(A, f)), etiketler=["kamera", "donme", "yaw"])


def G3_yumusak():
    return _G3("yumusak", 0.35, 0.35)


def G3_agresif():
    return _G3("agresif", 1.40, 0.50)


# --- G4: kamera pitch (optik eksen nadirden sapar) --------------------------
def _G4(siddet, A, f):
    return _sen(
        f"G4_{siddet}", "G4", siddet,
        f"Kamera pitch salinimi: {A:.2f} rad/s genlik, {f:.2f} Hz",
        "Nadirden sapma perspektif uretir; benzerlik modeli nerede yetmez?",
        f"merkezde tepe {px_kare_acisal(A):.1f} px/kare, "
        f"aci genligi {math.degrees(genlik_konum(A, f)):.0f} deg",
        _kam(wy=kosinus(A, f)), etiketler=["kamera", "donme", "pitch"])


def G4_yumusak():
    return _G4("yumusak", 0.20, 0.30)


def G4_agresif():
    return _G4("agresif", 0.80, 0.45)


# --- G5: capraz kamera hareketi (Lissajous) ---------------------------------
def _G5(siddet, A, f):
    """Iki eksen FARKLI frekansta -> akis yonu surekli doner.

    Tek bir 45 derece dogru boyunca oteleme G1/G2'den yalnizca YON olarak
    ayrilirdi ve yeni bir sey olcmezdi. Lissajous (fy = 2 fx, +45 deg faz)
    akis yonunu tum acilara suurup LK nokta yenilenmesini ve RANSAC'i
    eksen hizasiz yukle sinar - mentorun kastettigi "capraz" budur.
    """
    return _sen(
        f"G5_{siddet}", "G5", siddet,
        f"Capraz (Lissajous) kamera otelemesi: {A:.0f} m/s/eksen, "
        f"fx={f:.2f} Hz, fy={2 * f:.2f} Hz",
        "Yonu surekli degisen eksen-hizasiz kamera hareketi nerede kopariyor?",
        f"bileske tepe ~{px_kare(A) * math.sqrt(2):.1f} px/kare",
        _kam(vx=kosinus(A, f), vy=kosinus(A, 2 * f, math.pi / 4)),
        etiketler=["kamera", "capraz", "lissajous"])


def G5_yumusak():
    return _G5("yumusak", 10.0, 0.35)


def G5_agresif():
    return _G5("agresif", 32.0, 0.45)


# --- G6: kamera + hedef manevrasi (birlesik) --------------------------------
def _G6(siddet, A, f, w_hedef, f_hedef, dv, f_dv):
    """G5 kamera yuku + hedefin kendi manevrasi (dokunma + hiz modulasyonu).

    Hedef `wz` ile burnunu cevirir: GT kutusunun EN-BOY orani degisir, yani
    DCF sablonu ve imza da degisir. Kamera dogru gittigi icin hedef ayni
    zamanda goruntude kayar. Iki kaynak ust uste biner - kopmanin hangisinden
    geldigi ancak e_ego ile kf_hiz_hatasi ayri ayri okunarak anlasilir.
    """
    # hedefte de kosinus: aksi halde hem hiz hem yon sapmasi tek yonlu
    # birikir (bkz. kosinus()). Kosinusla hedef gercekten SALINIR.
    hedef_profil = (lambda t: (BAZ_HIZ + dv * math.cos(2 * math.pi * f_dv * t),
                               0.0,
                               w_hedef * math.cos(2 * math.pi * f_hedef * t)))
    return _sen(
        f"G6_{siddet}", "G6", siddet,
        f"Capraz kamera ({A:.0f} m/s) + hedef manevrasi "
        f"(yaw {w_hedef:.2f} rad/s, hiz +-{dv:.1f} m/s)",
        "Kamera ve hedef hareketi ayni anda oldugunda esik nereye kayiyor?",
        f"kamera ~{px_kare(A) * math.sqrt(2):.1f} px/kare + "
        f"hedef ~{px_kare(dv):.1f} px/kare",
        _kam(vx=kosinus(A, f), vy=kosinus(A, 2 * f, math.pi / 4)),
        hedef_profil=hedef_profil,
        etiketler=["kamera", "hedef", "birlesik"])


def G6_yumusak():
    return _G6("yumusak", 10.0, 0.35, 0.25, 0.20, 2.0, 0.15)


def G6_agresif():
    # hiz modulasyonu 5.0 DEGIL 3.0. Olculdu: 5.0 ile hedefin dunya hizi
    # 4.8 +- 5.0 -> 299 karenin 69'unda 1 m/s'nin ALTINA, tepe noktasinda tam
    # 0'a iniyordu. Arac duruyor demektir ve bu, takipcinin BELGELENMIS bir
    # sinirini tetikler (izleyici.py `_bagimsiz_dogrula`: "gercekten 20 kare
    # boyunca duran bir arac bu testle yanlis kilit sanilir"). O halde olculen
    # sey "manevra esigi" degil, bilinen bir sinirin yeniden gosterilmesi
    # olurdu. 3.0 ile hiz 1.8..7.8 m/s araliginda kalir; arac manevra yapar
    # ama HIC DURMAZ. Duraklama iceren surum `G6_agresif_durakli` olarak ayri
    # tutuldu - iki farkli soruyu ayri ayri yanitlarlar.
    return _G6("agresif", 32.0, 0.45, 0.60, 0.30, 3.0, 0.25)


def G6_agresif_durakli():
    """Hedefin PERIYODIK OLARAK DURDUGU surum (hiz 4.8 +- 5.0 m/s).

    Bilerek saklandi: takipcinin duran-arac sinirinin Gazebo'da da
    tekrarlanabildigini gosterir ve G6_agresif'in ondan ne kadar farkli
    oldugunu olcmeye yarar.
    """
    s = _G6("agresif", 32.0, 0.45, 0.60, 0.30, 5.0, 0.25)
    s.ad = "G6_agresif_durakli"
    s.siddet = "agresif (duraklamali)"
    return s


# --- G7: ani hedef hizlanmasi ----------------------------------------------
def _G7(siddet, v_tepe, t0, sure, ramp):
    """Kamera BOZULMASIZ (yalnizca baz), hedef yamuk hiz darbesi yapar.

    Kamera x0'i hedefin 20 m gerisinden baslar; hedef darbede one firlar ve
    kadrajin solundan sagina gecer ama disari cikmaz. Boylece olculen sey
    yalnizca "hedef ivmesi" degiskeni olur.
    """
    dv = v_tepe - BAZ_HIZ
    kapi = yamuk(t0, ramp, sure)
    hedef_profil = (lambda t: (BAZ_HIZ + dv * kapi(t), 0.0, 0.0))
    return _sen(
        f"G7_{siddet}", "G7", siddet,
        f"Ani hedef hizlanmasi: {BAZ_HIZ:.1f} -> {v_tepe:.0f} m/s, "
        f"t={t0:.1f} s, {sure:.1f} s surer",
        "Yalnizca hedef ivmesi: KF sabit-hiz modeli nerede yetmez?",
        f"hedef tepe {px_kare(dv):.1f} px/kare (kameraya gore)",
        _kam(), hedef_profil=hedef_profil,
        kam_x=HEDEF_X0 + 20.0,
        etiketler=["hedef", "ivme"])


def G7_yumusak():
    return _G7("yumusak", 16.0, 3.0, 3.0, 0.5)


def G7_agresif():
    return _G7("agresif", 30.0, 3.0, 1.75, 0.25)


# ---------------------------------------------------------------------------
# EK TARAMA - istenen 14 senaryonun DISINDA, yalnizca esik bulmak icin
# ---------------------------------------------------------------------------
# G1-G5'in agresif seviyesinde HICBIRI kopmadi; o yuzden "kamera hareketi
# kaynakli kopma esigi" ancak bir ALT SINIR olarak bilinebiliyordu. Asagidaki
# `_kritik` seviyeler esigi kusatmak icin var. Ayrica G6'daki kopmanin ne
# kadari kameradan ne kadari hedeften geliyor sorusu, hedef profilini
# BOZULMASIZ kamerayla kosarak ayristirilir (kamera-tek esi zaten
# G5_agresif'tir - ayni Lissajous, hedef manevrasi yok).
def G1_kritik():
    return _G1("kritik", 80.0, 0.70)


def G3_kritik():
    return _G3("kritik", 3.00, 0.50)


def G4_kritik():
    return _G4("kritik", 2.00, 0.80)


def G5_kritik():
    return _G5("kritik", 70.0, 0.70)


def G7_kritik():
    return _G7("kritik", 45.0, 3.0, 1.0, 0.15)


def G6_agresif_hedef():
    """G6_agresif'in HEDEF profili + bozulmasiz kamera.

    2x2 ayristirmanin eksik hucresi:
        kamera yok / hedef yok   -> G0 mertebesi (baz)
        kamera var / hedef yok   -> G5_agresif
        kamera yok / hedef var   -> BU
        kamera var / hedef var   -> G6_agresif
    """
    s = _G6("agresif", 32.0, 0.45, 0.60, 0.30, 3.0, 0.25)
    s.ad = "G6_agresif_hedef"
    s.siddet = "agresif (hedef-tek)"
    s.kam_profil = _kam()
    s.aciklama = "Bozulmasiz kamera + G6_agresif hedef manevrasi"
    s.amac = "G6'daki kopmanin hedef payini kamera payindan ayir"
    s.beklenen = "kamera 0 px/kare + hedef manevrasi"
    return s


EK = {
    "G6_agresif_durakli": G6_agresif_durakli,
    "G1_kritik": G1_kritik, "G3_kritik": G3_kritik, "G4_kritik": G4_kritik,
    "G5_kritik": G5_kritik, "G7_kritik": G7_kritik,
    "G6_agresif_hedef": G6_agresif_hedef,
}

SENARYOLAR = {
    "G0": G0,
    "G1_yumusak": G1_yumusak, "G1_agresif": G1_agresif,
    "G2_yumusak": G2_yumusak, "G2_agresif": G2_agresif,
    "G3_yumusak": G3_yumusak, "G3_agresif": G3_agresif,
    "G4_yumusak": G4_yumusak, "G4_agresif": G4_agresif,
    "G5_yumusak": G5_yumusak, "G5_agresif": G5_agresif,
    "G6_yumusak": G6_yumusak, "G6_agresif": G6_agresif,
    "G7_yumusak": G7_yumusak, "G7_agresif": G7_agresif,
}

FAZ_B = [a for a in SENARYOLAR if a != "G0"]
SENARYOLAR.update(EK)


# ---------------------------------------------------------------------------
# A11 - GAZEBO KARAR TABANI  (docs/architecture/A11_ONKAYIT.md)
# ---------------------------------------------------------------------------
# Kompozit yatak (A5.2/A7/A8/A9/A10) ARSIVDIR. A11 kendi tabanini Gazebo'da
# kurar. On-kayitli gereklilikler ve nerede karsilandiklari:
#     >= 6 senaryo          -> A1..A6
#     hedef 60 -> 8 px      -> A2, A5 (irtifa rampasi 38 -> 288 m, 600 kare)
#     yaw +-30 derece       -> A3, A5 (genlik = A_w / (2 pi f) = 0.5236 rad)
#     irtifa degisimi       -> A2, A4, A5
#     >= 2 celdirici        -> HEPSINDE (celdirici, celdirici2)
#     tohum sabit           -> doku_seed = 11, butun ailede AYNI
#     kayitli GT            -> pozlar.csv + imu.csv (gazebo/kaydet.py)
#
# Zemin butun ailede AYNI (560 m, 4096 px doku = 7.31 texel/m): senaryolar
# arasi ego/doku karsilastirmasi ancak zemin ayni olursa gecerlidir.
A11_ZEMIN_M = 560.0
A11_DOKU_PX = 4096
A11_SEED = 11
A11_IRTIFA0 = 38.3                  # ODAK_PX * 4.6 / 38.3 = 60.0 px hedef
A11_IRTIFA1 = 287.5                 # -> 8.0 px
CELDIRICI2 = dict(x0=+6.0, y0=-9.0, yaw=math.pi * 0.85, vx=4.2,
                  renk=(0.15, 0.62, 0.35))


def _a11_araclar(hedef_profil=None):
    """Hedef + IKI celdirici (on-kayit: >= 2)."""
    return [
        Arac("hedef", x0=HEDEF_X0, y0=HEDEF_Y0, yaw=0.0, vx=BAZ_HIZ,
             renk=(0.16, 0.16, 0.75), profil=hedef_profil),
        Arac("celdirici", **CELDIRICI),
        Arac("celdirici2", **CELDIRICI2),
    ]


def _a11(ad, aciklama, amac, beklenen, kam_profil, kare=300, kam_z=None,
         etiketler=()):
    return GzSenaryo(
        ad=ad, aciklama=aciklama, amac=amac, araclar=_a11_araclar(),
        hedef_ad="hedef", kam_x=HEDEF_X0, kam_y=0.0,
        kam_z=A11_IRTIFA0 if kam_z is None else kam_z,
        kam_profil=kam_profil, drone_statik=False, kare=kare,
        doku_seed=A11_SEED, zemin_m=A11_ZEMIN_M, doku_px=A11_DOKU_PX,
        aile="A11", siddet="", beklenen=beklenen,
        etiketler=list(etiketler))


def _a11_yaw(f=0.25, derece=30.0):
    """wz genligi: aci genligi `derece` olacak sekilde (kosinus kurali)."""
    A = math.radians(derece) * 2.0 * math.pi * f
    return kosinus(A, f)


def A1_taban():
    """Kontrol: sabit irtifa, bozulmasiz kamera, iki celdirici."""
    return _a11("A1_taban",
                "Sabit 38.3 m, bozulmasiz kamera, iki celdirici",
                "Gazebo tabani: kompozit bulgular gercek kamerada sag kaliyor mu?",
                "hedef 60 px sabit, arka plan 0 px/kare bozulma",
                _kam(), etiketler=["taban", "celdirici"])


def A2_kucul():
    """Hedef 60 -> 8 px: irtifa rampasi 38.3 -> 287.5 m, 20 s."""
    vz = (A11_IRTIFA1 - A11_IRTIFA0) / 20.0        # 12.46 m/s
    return _a11("A2_kucul",
                f"Irtifa rampasi {A11_IRTIFA0:.1f} -> {A11_IRTIFA1:.1f} m "
                f"({vz:.2f} m/s, 20 s): hedef 60 -> 8 px",
                "Kucuk hedef sinirlari gercek kamerada nerede?",
                "hedef 60 -> 8 px, 600 kare",
                _kam(vz=lambda t: vz), kare=600,
                etiketler=["kucultme", "irtifa", "celdirici"])


def A3_yaw():
    """Yaw +-30 derece salinim, sabit irtifa."""
    return _a11("A3_yaw",
                "Yaw +-30 derece (f=0.25 Hz), sabit 38.3 m",
                "Donme kanali: A3.9 Faz B'nin 'koparan tek kanal DONME' bulgusu",
                f"aci genligi 30 derece, tepe {px_kare_acisal(_a11_yaw()(0.0)):.1f} px/kare",
                _kam(wz=_a11_yaw()), etiketler=["yaw", "donme", "celdirici"])


def A4_irtifa():
    """Irtifa salinimi (monoton degil): 38.3 m etrafinda +-35 m."""
    f = 0.2
    A = 35.0 * 2.0 * math.pi * f
    return _a11("A4_irtifa",
                "Irtifa salinimi +-35 m (f=0.2 Hz), 38.3 m etrafinda",
                "Olcek kanali: ego olcek kestirimi gercek irtifa degisiminde ne yapiyor?",
                "irtifa 38.3 - 108.3 m -> hedef 60 - 21 px salinim",
                _kam(vz=kosinus(A, f)), kam_z=A11_IRTIFA0 + 35.0,
                etiketler=["irtifa", "olcek", "celdirici"])


def A5_kucul_yaw():
    """Kucultme + yaw birlikte: en zor kol."""
    vz = (A11_IRTIFA1 - A11_IRTIFA0) / 20.0
    yaw = _a11_yaw()

    def profil(t):
        return (BAZ_HIZ, 0.0, vz, 0.0, 0.0, yaw(t))
    return _a11("A5_kucul_yaw",
                "Irtifa rampasi 38.3 -> 287.5 m VE yaw +-30 derece",
                "Iki kanal birlikte: kucultme ve donme etkilesiyor mu?",
                "hedef 60 -> 8 px, aci genligi 30 derece",
                profil, kare=600,
                etiketler=["kucultme", "yaw", "celdirici"])


def A6_celdirici():
    """Celdiriciler hedefe yakinsar: yanlis kilit stresi."""
    return _a11("A6_celdirici",
                "Iki celdirici hedefe yakinsiyor, sabit irtifa",
                "Yanlis kilit: iki celdirici ayni goruntu bolgesinde",
                "en kucuk hedef-celdirici ayrimi KAYITTAN olculecek (tasarimda iddia yok)",
                _kam(), etiketler=["celdirici", "yanlis_kilit"])


A11_AILE = [A1_taban, A2_kucul, A3_yaw, A4_irtifa, A5_kucul_yaw, A6_celdirici]

SENARYOLAR.update({f.__name__: f for f in A11_AILE})
