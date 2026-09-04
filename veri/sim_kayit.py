"""A3.10 - sim senaryosunu diske kaydet ve sonradan oynat.

Gazebo tarafindaki kayit-sonra-oynat mantiginin sim karsiligi, ama cok daha
kucugu: burada sim ZATEN deterministiktir (ayni seed -> ayni kare), o yuzden
poz akisi, senkron denetimi, RTF ve dunya uretimi gibi Gazebo'ya ozgu hicbir
sey YOKTUR. Yalnizca uc sey saklanir:

    data/sim/<ad>/meta.json          senaryo kunyesi + hiz profili + seed'ler
    data/sim/<ad>/gt.csv             kare basina GT, gorunurluk, hedef hizi
    data/sim/<ad>/kareler/000000.png kareler (kayipsiz)

Dongu sirasi `calistir.kos()` ve `kaynak.SimKaynak.oku()` ile BIREBIR aynidir
(kamera -> step -> render); aksi halde kayit canli sim'den farkli goruntu
uretirdi.

Kullanim:
    from sim.senaryolar import TUM_TESTLER
    from veri.sim_kayit import kaydet, SimKayitKaynak
    kaydet(TUM_TESTLER["hizli_hedef"]())          # -> data/sim/hizli_hedef/
    k = SimKayitKaynak(senaryo="hizli_hedef")     # tracker'a verilebilir
"""
import csv
import json
import os

import cv2
import numpy as np

from kaynak import Kare, Kaynak, KaynakHatasi

SIM_KAYIT_VARSAYILAN = "data/sim"
BASLIK = ["kare", "t", "gt_x", "gt_y", "gt_w", "gt_h", "gorunur",
          "hedef_x", "hedef_y", "hedef_hiz"]


def _profil_olaylari(meta):
    """Meta'daki analitik profilden ZAMAN OLAYLARINI turet (yeni sabit yok)."""
    t0 = float(meta.get("t0_s", 0.0))
    ramp = float(meta.get("ramp_s", 0.0))
    duz = float(meta.get("duz_sure_s", 0.0))
    o = {"hareket_baslangici_s": 0.0,
         "profil_degisim_baslangici_s": t0,
         "duz_kisim_baslangici_s": t0 + ramp,
         "duz_kisim_bitisi_s": t0 + ramp + duz,
         "geri_donus_bitisi_s": t0 + ramp + duz + ramp}
    if float(meta.get("durus_suresi_s", 0.0)) > 0.0:
        o["durus_baslangici_s"] = t0 + ramp
        o["durus_suresi_s"] = duz
        o["tekrar_hareket_s"] = t0 + ramp + duz
    return o


def kaydet(sen, kok=SIM_KAYIT_VARSAYILAN, ad=None):
    """Senaryoyu kare kare diske yaz. Doner: meta sozlugu."""
    ad = ad or sen.ad
    dizin = os.path.join(kok, ad)
    kare_dizin = os.path.join(dizin, "kareler")
    os.makedirs(kare_dizin, exist_ok=True)
    sahne, hedef = sen.sahne, sen.hedef
    satir = []
    for k in range(sen.kare):
        sen.kamera_fn(sahne, k, sen.dt)
        p0 = (hedef.x, hedef.y)
        sahne.step(sen.dt)
        img = sahne.render()
        cv2.imwrite(os.path.join(kare_dizin, f"{k:06d}.png"), img)
        b = sahne.gt_box(hedef)
        satir.append([k, k * sen.dt, float(b[0]), float(b[1]), float(b[2]),
                      float(b[3]), int(bool(sahne.visible(hedef))),
                      float(hedef.x), float(hedef.y),
                      float(np.hypot(hedef.x - p0[0], hedef.y - p0[1]) / sen.dt)])
    with open(os.path.join(dizin, "gt.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(BASLIK)
        w.writerows(satir)

    meta = dict(getattr(sen, "meta", {}) or {})
    meta.update({
        "ad": ad, "senaryo": sen.ad, "aciklama": sen.aciklama, "amac": sen.amac,
        "kare_sayisi": int(sen.kare), "dt": float(sen.dt),
        "fps": float(1.0 / sen.dt),
        "genislik": int(sahne.cam.w), "yukseklik": int(sahne.cam.h),
        "irtifa_m": float(sahne.cam.alt),
        "hedef_ad": hedef.name, "hedef_L_m": float(hedef.L),
        "hedef_W_m": float(hedef.W),
        "hareket_yon_derece": float(np.degrees(hedef.h)),
        "hiz_profili_var": hedef.profil is not None,
        "profil_olaylari": _profil_olaylari(meta),
        "kayit": {"kare_dizin": "kareler", "gt": "gt.csv",
                  "bicim": "png (kayipsiz)"},
    })
    with open(os.path.join(dizin, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    return meta


class SimKayitKaynak(Kaynak):
    """Diske alinmis sim senaryosunu `Kare` olarak verir (kayit-sonra-oynat)."""

    def __init__(self, kok=SIM_KAYIT_VARSAYILAN, senaryo=None):
        if not senaryo:
            raise KaynakHatasi("sim kaydi icin senaryo adi gerekli")
        dizin = os.path.join(kok, senaryo)
        if not os.path.isdir(dizin):
            mevcut = sorted(d for d in os.listdir(kok)) if os.path.isdir(kok) else []
            raise KaynakHatasi(
                f"sim kaydi bulunamadi: {dizin}\n"
                f"       mevcut kayitlar: {', '.join(mevcut) or '(yok)'}\n"
                f"       once kaydet: veri.sim_kayit.kaydet(senaryo)")
        with open(os.path.join(dizin, "meta.json")) as f:
            self.meta = json.load(f)
        with open(os.path.join(dizin, "gt.csv")) as f:
            self.satir = list(csv.DictReader(f))
        self.dosyalar = sorted(
            os.path.join(dizin, "kareler", d)
            for d in os.listdir(os.path.join(dizin, "kareler"))
            if d.endswith(".png"))
        if len(self.dosyalar) != len(self.satir):
            raise KaynakHatasi(
                f"kayit tutarsiz: {len(self.dosyalar)} kare, "
                f"{len(self.satir)} GT satiri")
        self.ad = f"simkayit:{senaryo}"
        self.tur = "sim"
        self.genislik = int(self.meta["genislik"])
        self.yukseklik = int(self.meta["yukseklik"])
        self.fps = float(self.meta["fps"])
        self.kare_sayisi = len(self.dosyalar)
        self._k = 0

    def oku(self):
        if self._k >= self.kare_sayisi:
            return None
        k = self._k
        img = cv2.imread(self.dosyalar[k], cv2.IMREAD_COLOR)
        if img is None:
            raise KaynakHatasi(f"kare okunamadi: {self.dosyalar[k]}")
        s = self.satir[k]
        gt = np.array([float(s["gt_x"]), float(s["gt_y"]),
                       float(s["gt_w"]), float(s["gt_h"])], np.float32)
        self._k += 1
        return Kare(goruntu=img, indeks=k, zaman=float(s["t"]),
                    kaynak_adi=self.ad, genislik=self.genislik,
                    yukseklik=self.yukseklik, fps=self.fps,
                    gt=gt, gorunur=bool(int(s["gorunur"])))

    def acik_mi(self):
        return self._k < self.kare_sayisi

    def bilgi(self):
        m = self.meta
        return (f"{self.ad}  {self.genislik}x{self.yukseklik}  "
                f"{self.fps:.0f} fps  {self.kare_sayisi} kare  "
                f"| {m.get('tip', '-')}  profil {m.get('hiz_profili', '-')}  "
                f"v {m.get('v0_m_s', '?')}..{m.get('v_maks_m_s', '?')} m/s")
