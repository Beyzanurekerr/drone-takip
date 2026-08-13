"""7 test senaryosu.

Her senaryo: sahne + kamera davranisi + kac kare + hangi arac hedef.
Kamera her karede `kamera_fn(sahne, k, dt)` ile guncellenir.
"""
import math

import numpy as np

from .world import Camera, Ground, Scene, Vehicle

_GROUND = None


def zemin():
    """Zemin dokusu pahali (2100x2100) -> bir kez uret, senaryolar paylassin."""
    global _GROUND
    if _GROUND is None:
        _GROUND = Ground(extent_m=700, seed=1)
    return _GROUND


class Senaryo:
    def __init__(self, ad, aciklama, amac, sahne, kare, kamera_fn, hedef_idx=0, dt=1 / 30):
        self.ad = ad
        self.aciklama = aciklama
        self.amac = amac
        self.sahne = sahne
        self.kare = kare
        self.kamera_fn = kamera_fn
        self.hedef_idx = hedef_idx
        self.dt = dt

    @property
    def hedef(self):
        return self.sahne.vehicles[self.hedef_idx]


def _takip_kamera(kazanc=0.10, onde=0.0, jitter=0.0, yaw_hz=0.0, yaw_gen=0.0,
                  irtifa_fn=None, seed=3):
    """Hedefi gecikmeli takip eden kamera. Gercek drone gibi hep geriden gelir."""
    rng = np.random.default_rng(seed)

    def fn(sahne, k, dt):
        cam = sahne.cam
        h = sahne.vehicles[0] if not hasattr(sahne, "_hedef") else sahne._hedef
        hx = h.x + math.cos(h.h) * onde
        hy = h.y + math.sin(h.h) * onde
        cam.x += (hx - cam.x) * kazanc
        cam.y += (hy - cam.y) * kazanc
        if irtifa_fn is not None:
            cam.alt = irtifa_fn(k * dt)
        if yaw_gen:
            cam.yaw = yaw_gen * math.sin(2 * math.pi * yaw_hz * k * dt)
        if jitter:
            cam.jit_x = rng.normal(0, jitter)
            cam.jit_y = rng.normal(0, jitter)
            cam.jit_yaw = rng.normal(0, jitter * 0.004)

    return fn


def _yol_araci(x, dy, hiz, renk, **kw):
    g = zemin()
    return Vehicle(x, g.extent / 2 + dy, 0.0, hiz, renk, **kw)


def _kur(sahne, hedef_idx):
    sahne._hedef = sahne.vehicles[hedef_idx]
    # kamera hedefin uzerinde baslasin (yoksa ilk kareler kadraj disi gecer)
    sahne.cam.x, sahne.cam.y = sahne._hedef.x, sahne._hedef.y
    return sahne


# ----------------------------------------------------------------------------
# TEST 1 - Yakin arac
# ----------------------------------------------------------------------------
def test1_yakin():
    g = zemin()
    araclar = [
        _yol_araci(80, -2.2, 22.0, (40, 40, 190), name="HEDEF"),
        _yol_araci(120, +2.2, 18.0, (180, 170, 60)),
    ]
    s = _kur(Scene(g, Camera(alt=45), araclar), 0)
    return Senaryo("test1_yakin", "Irtifa 45 m, hedef buyuk (~50x20 px)",
                   "Temel takip calisiyor mu?", s, 300, _takip_kamera(0.12), 0)


# ----------------------------------------------------------------------------
# TEST 2 - Uzaklasan arac
# ----------------------------------------------------------------------------
def test2_uzaklasan():
    g = zemin()
    araclar = [
        _yol_araci(80, -2.2, 24.0, (40, 40, 190), name="HEDEF"),
        _yol_araci(150, +2.2, 20.0, (180, 170, 60)),
        _yol_araci(40, +2.2, 26.0, (60, 160, 60)),
    ]
    s = _kur(Scene(g, Camera(alt=40), araclar), 0)
    irt = lambda t: 40 + 22.0 * t  # 10 sn'de 40 -> 260 m
    return Senaryo("test2_uzaklasan", "Irtifa 40 -> 260 m rampa",
                   "Piksel boyutu kuculurken hedef korunuyor mu?",
                   s, 300, _takip_kamera(0.12, irtifa_fn=irt), 0)


# ----------------------------------------------------------------------------
# TEST 3 - Cok kucuk arac (minimum boyut taramasi)
# ----------------------------------------------------------------------------
def test3_cok_kucuk(seed=7):
    g = zemin()
    araclar = [
        _yol_araci(80, -2.2, 24.0, (40, 40, 190), name="HEDEF"),
        _yol_araci(150, +2.2, 21.0, (180, 170, 60)),
    ]
    s = _kur(Scene(g, Camera(alt=35), araclar, noise=4.0, seed=seed), 0)
    # ustel rampa: her karede sabit oranli kuculme -> boyut eksenine duzgun yayilir
    irt = lambda t: 35.0 * math.exp(0.13 * t)  # 20 sn'de 35 -> ~470 m
    return Senaryo("test3_cok_kucuk", "Irtifa 35 -> 470 m ustel rampa",
                   "Minimum takip edilebilen hedef boyutu kac px?",
                   s, 600, _takip_kamera(0.12, irtifa_fn=irt), 0)


# ----------------------------------------------------------------------------
# TEST 4 - Birden fazla arac
# ----------------------------------------------------------------------------
def test4_coklu():
    g = zemin()
    renkler = [(40, 40, 190), (180, 170, 60), (60, 160, 60), (200, 200, 200),
               (50, 120, 210), (140, 60, 160)]
    araclar = [_yol_araci(80, -2.2, 23.0, renkler[0], name="HEDEF")]
    # hicbiri hedefle ayni noktada dogmamali: x ofsetleri ve seritler ayri
    yerlesim = [(-34, +2.2, 24.6), (-17, -2.2, 21.8), (+16, +2.2, 25.4),
                (+33, -2.2, 24.2), (+55, +2.2, 21.2)]
    for r, (dx, dy, hiz) in zip(renkler[1:], yerlesim):
        araclar.append(_yol_araci(80 + dx, dy, hiz, r))
    s = _kur(Scene(g, Camera(alt=70), araclar), 0)
    return Senaryo("test4_coklu", "6 arac, sik konvoy, irtifa 70 m",
                   "Kilitli arac yerine baskasina geciyor mu? (ID switch)",
                   s, 320, _takip_kamera(0.12), 0)


# ----------------------------------------------------------------------------
# TEST 5 - Benzer araclar
# ----------------------------------------------------------------------------
def test5_benzer():
    g = zemin()
    beyaz = (205, 205, 205)
    araclar = [_yol_araci(80, -2.2, 23.0, beyaz, name="HEDEF")]
    # ayni serit konvoy (sikisik) + yan seritte sollayanlar; hepsi ayni gorunum
    yerlesim = [(-11, -2.2, 23.4), (+11, -2.2, 22.6), (-6, +2.2, 24.8), (+18, +2.2, 21.6)]
    for dx, dy, hiz in yerlesim:
        araclar.append(_yol_araci(80 + dx, dy, hiz, beyaz))
    s = _kur(Scene(g, Camera(alt=70), araclar), 0)
    return Senaryo("test5_benzer", "5 ayni renk/boyut arac, 9 m arayla",
                   "Gorunum ayirt edemez -> hareket modeli hedefi tutabiliyor mu?",
                   s, 320, _takip_kamera(0.12), 0)


# ----------------------------------------------------------------------------
# TEST 6 - Hedefin kisa sure kaybolmasi
# ----------------------------------------------------------------------------
def test6_okluzyon():
    g = zemin()
    c = g.extent / 2
    araclar = [
        _yol_araci(80, -2.2, 24.0, (40, 40, 190), name="HEDEF"),
        _yol_araci(95, +2.2, 24.0, (180, 170, 60)),
        _yol_araci(60, -2.2, 26.0, (60, 160, 60)),
    ]
    # kusbakisi okluzyon = ust gecit / agac ortusu (arac aracin onune gecemez)
    okluder = [(180.0, c - 30, 42.0, 60.0), (330.0, c - 30, 30.0, 60.0)]
    s = _kur(Scene(g, Camera(alt=55), araclar, occluders=okluder), 0)
    return Senaryo("test6_okluzyon", "Hedef 2 kez ust gecit altina giriyor (~1.7 sn / ~1.2 sn)",
                   "Tekrar gorununce AYNI arac bulunabiliyor mu?",
                   s, 340, _takip_kamera(0.12), 0)


# ----------------------------------------------------------------------------
# TEST 7 - Kamera hareketi
# ----------------------------------------------------------------------------
def test7_kamera():
    g = zemin()
    araclar = [
        _yol_araci(80, -2.2, 23.0, (40, 40, 190), name="HEDEF"),
        _yol_araci(140, +2.2, 19.0, (180, 170, 60)),
        _yol_araci(50, +2.2, 27.0, (60, 160, 60)),
    ]
    s = _kur(Scene(g, Camera(alt=65), araclar), 0)
    kam = _takip_kamera(kazanc=0.075, onde=-6.0, jitter=1.1,
                        yaw_hz=0.16, yaw_gen=math.radians(22))
    return Senaryo("test7_kamera", "Agresif yaw (+-22 deg), gevsek takip, titresim",
                   "Kamera hareketine ragmen hedef tutuluyor mu?",
                   s, 320, kam, 0)


TUM_TESTLER = {
    "test1": test1_yakin,
    "test2": test2_uzaklasan,
    "test3": test3_cok_kucuk,
    "test4": test4_coklu,
    "test5": test5_benzer,
    "test6": test6_okluzyon,
    "test7": test7_kamera,
}
