"""Gazebo senaryosunu diske kaydeder: kareler + pozlar + meta (kayit-sonra-oynat).

NEDEN OFFLINE KAYIT
-------------------
Olculdu: bu makinede gz sim RTF ~0.35 (llvmpipe yazilim render). Yani sim
gercek zamanin gerisinde kosuyor ve canli bir boru hattinda FPS/gecikme olcumu
render hizini olcerdi, takipciyi degil. Kareler diske yazilinca:

  * olcum tekrarlanabilir olur (ayni kareler, her kosumda)
  * FPS/gecikme SADECE takipciyi olcer
  * A3.8 ve A3.9 takipcileri BIREBIR ayni girdiyle kosar -> karsilastirma durust

SENKRON
-------
Kamera ve poz akislari FARKLI hizlarda yayinlanir. Eslestirme kare indeksine
gore degil, sim zamani damgasina (header.stamp) gore yapilir; iki poz ornegi
arasinda dogrusal interpolasyon uygulanir. Damga toleransi asilirsa kare
DUSURULUR, sessizce yanlis GT yazilmaz.

ZAMANA BAGLI HAREKET (Faz B)
---------------------------
SDF'teki `initial_linear/angular` yalnizca SABIT hiz verir; G1-G7'nin salinimli
kamera hareketi ve G6/G7'nin hedef manevrasi zamana baglidir. `Surucu` bu isi
yapar: her poz ornegi (120 Hz, SIM zamani damgali) geldiginde senaryonun
profilini o anda degerlendirip `/model/<ad>/cmd_vel` uzerine Twist yayinlar.

Neden poz akisina baglandi: duvar saatiyle yayin yapmak RTF dalgalandiginda
sim zamaninda duzensiz bir profil uretirdi (G0'da ayni tuzak `real_time_factor`
uzerinden yasandi). Poz damgasi SIM zamanidir; profil boylece sim zamaninda
dogru kosar.

Kamera profili DUNYA cercevesinde yazilir, VelocityControl ise GOVDE
cercevesinde komut bekler; donusum yayin aninda o anki poz kullanilarak
yapilir (`_dunya_govde`). G4'te drone pitch'lenirken "ileri" komutunun dikey
bilesen kazanmasini bu onler.

Kullanim:
    python3 -m gazebo.kaydet G0
    python3 -m gazebo.kaydet G3_agresif --kare 300 --kok data/gazebo
    python3 -m gazebo.kaydet --hepsi              # Faz B'nin 14 senaryosu
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time

import cv2
import numpy as np

from gazebo.dunya_uret import ZEMIN_M, dunya_yaz, fov_hesapla
from gazebo.senaryolar import FAZ_B, SENARYOLAR

ATLA = 5              # ilk kareler sahne tam yuklenmeden render edilebilir
TOLERANS_S = 0.02     # kare damgasi ile poz ornegi arasi azami bosluk


def _q_carp(a, b):
    """Kuaterniyon carpimi (w, x, y, z): R(a o b) = R(a) @ R(b)."""
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw)


def _q_matris(q):
    """Birim kuaterniyon -> 3x3 donme matrisi (veri/gazebo.py ile ayni sozlesme)."""
    w, x, y, z = q
    n = float(np.sqrt(w * w + x * x + y * y + z * z)) or 1.0
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], np.float64)


def _stamp(hdr):
    return float(hdr.stamp.sec) + float(hdr.stamp.nsec) * 1e-9


def _poz_stamp(poz, msg):
    """Pose_V'de damga her Pose'un KENDI header'indadir; dis header bos gelir.

    Olculdu: dis header okunursa t = 0 cikar ve butun kareler senkron
    toleransinin disinda sayilip DUSER (20/20). Ikisi de denenir, sifir
    olmayan kullanilir.
    """
    t = _stamp(poz.header)
    return t if t > 0 else _stamp(msg.header)


class Surucu:
    """Profilli modellere sim zamaninda cmd_vel yayinlar.

    `kur(dugum)` cagrilmadan once yayinci yoktur; `tik(ad, t, q)` her poz
    orneginde cagrilir. `q` yalnizca kamera icin gerekir (dunya -> govde).
    Yayin, ayni komut tekrar ederse atlanir: 120 Hz x 14 senaryo boyunca
    gereksiz mesaj uretmemek icin kucuk bir olu bant var.
    """

    OLU_BANT = 1e-3

    def __init__(self, sen):
        self.sen = sen
        self.profiller = {a.ad: a.profil for a in sen.araclar if a.profil}
        self.kam_profil = sen.kam_profil if not sen.drone_statik else None
        self.yayincilar = {}
        self.son = {}
        self.t0 = {}
        self.sayac = 0

    def gerekli(self):
        return bool(self.profiller) or self.kam_profil is not None

    def kur(self, dugum, Twist):
        self.Twist = Twist
        adlar = list(self.profiller)
        if self.kam_profil is not None:
            adlar.append("drone")
        for ad in adlar:
            self.yayincilar[ad] = dugum.advertise(f"/model/{ad}/cmd_vel", Twist)

    @staticmethod
    def _dunya_govde(q, v_dunya, w_dunya):
        """Dunya cercevesindeki twist'i govde cercevesine cevir: R^T v."""
        R = _q_matris(q)
        return R.T @ np.asarray(v_dunya, np.float64), R.T @ np.asarray(w_dunya, np.float64)

    def tik(self, ad, t, q=None):
        if ad == "drone":
            profil = self.kam_profil
        else:
            profil = self.profiller.get(ad)
        if profil is None or ad not in self.yayincilar:
            return
        # profil zamani = SIM zamani (sim t=0'da baslar); ilk damga referans
        # alinmaz, cunku senaryo tanimlari mutlak sim zamaniyla yazildi.
        d = profil(float(t))
        if ad == "drone":
            v, w = self._dunya_govde(q, d[:3], d[3:])
        else:
            v, w = np.array([d[0], d[1], 0.0]), np.array([0.0, 0.0, d[2]])
        yeni = (float(v[0]), float(v[1]), float(v[2]),
                float(w[0]), float(w[1]), float(w[2]))
        eski = self.son.get(ad)
        if eski is not None and max(abs(a - b) for a, b in zip(eski, yeni)) < self.OLU_BANT:
            return
        self.son[ad] = yeni
        m = self.Twist()
        m.linear.x, m.linear.y, m.linear.z = yeni[0], yeni[1], yeni[2]
        m.angular.x, m.angular.y, m.angular.z = yeni[3], yeni[4], yeni[5]
        self.yayincilar[ad].publish(m)
        self.sayac += 1


class Kayitci:
    def __init__(self, sen, kok="data/gazebo", kare_hedef=None, ayrinti=True):
        # KONU IZOLASYONU - sessiz veri karisiminin onlenmesi.
        # Olculdu: onceki bir kosumdan kalan `gz sim` sureci ayni konulara
        # (/kamera, /model/*/pose) yayin yapmaya devam ediyordu; kaydedici IKI
        # simin verisini karistirdi ve hedef x = 5334 m gibi anlamsiz pozlar
        # yazildi. Hata sessizdi: kare sayisi ve senkron boslugu SAGLIKLI
        # gorunuyordu. GZ_PARTITION her kosuma kendi ad alanini verir; artik
        # kacak bir surec olsa bile konular carpisamaz.
        self.partisyon = f"a39-{sen.ad}-{os.getpid()}"
        os.environ["GZ_PARTITION"] = self.partisyon   # kendi Node'umuz icin
        self.sen = sen
        self.kare_hedef = int(kare_hedef or sen.kare)
        self.ayrinti = ayrinti
        self.sdf, self.dizin = dunya_yaz(sen, kok)
        self.kare_dizin = os.path.join(self.dizin, "kareler")
        os.makedirs(self.kare_dizin, exist_ok=True)

        self.kilit = threading.Lock()
        self.goruntuler = []      # (t, BGR)
        # Her modelin poz akisi AYRI tutulur: yayinlar bagimsiz konulardan
        # geliyor ve damgalari birebir ortusmuyor. Tek bir ortak izgaraya
        # zorlamak yerine her model kendi ornekleri arasinda interpole edilir.
        self.poz_akis = {a.ad: [] for a in sen.araclar}
        self.imu_akis = []        # A11/KOL 1: (t, wx,wy,wz, ax,ay,az, qw,qx,qy,qz)
        if not sen.drone_statik:
            self.poz_akis["drone"] = []
        self.surucu = Surucu(sen)
        self.kam_bilgi = None
        self.sure = None
        self._surec = None

    # -- gz.transport geri cagirmalari (kendi is parcaciklarinda kosar) ------
    def _goruntu_cb(self, msg):
        with self.kilit:
            if len(self.goruntuler) >= self.kare_hedef + ATLA:
                return
        a = np.frombuffer(msg.data, np.uint8)
        try:
            rgb = a.reshape(msg.height, msg.width, 3)
        except ValueError:
            return                                   # eksik/bozuk kare: atla
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        with self.kilit:
            self.goruntuler.append((_stamp(msg.header), bgr))

    def _poz_cb_yap(self, ad):
        """`ad` modelinin poz konusu icin geri cagirma uretir."""
        def cb(msg):
            for p in msg.pose:
                if p.name != ad:
                    continue
                t = _poz_stamp(p, msg)
                v = (p.position.x, p.position.y, p.position.z,
                     p.orientation.w, p.orientation.x,
                     p.orientation.y, p.orientation.z)
                with self.kilit:
                    self.poz_akis[ad].append((t, v))
                # HAREKET SURUCUSU: profil sim zamaninda burada kosar.
                self.surucu.tik(ad, t, v[3:])
                return
        return cb

    def _imu_cb(self, msg):
        """A11/KOL 1: IMU ornegi. Damga SIM zamanidir (poz akisiyla ayni saat)."""
        t = _stamp(msg.header)
        with self.kilit:
            self.imu_akis.append((
                t,
                msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z,
                msg.linear_acceleration.x, msg.linear_acceleration.y,
                msg.linear_acceleration.z,
                msg.orientation.w, msg.orientation.x, msg.orientation.y,
                msg.orientation.z))

    def _kambilgi_cb(self, msg):
        if self.kam_bilgi is not None:
            return
        k = list(msg.intrinsics.k) if len(msg.intrinsics.k) == 9 else None
        if k is None:
            return
        self.kam_bilgi = {"fx": k[0], "fy": k[4], "cx": k[2], "cy": k[5],
                          "genislik": msg.width, "yukseklik": msg.height}

    # ----------------------------------------------------------------------
    def _sim_baslat(self):
        ortam = dict(os.environ)
        # albedo_map goreli yazildi -> dokunun bulunabilmesi icin kaynak yolu
        onceki = ortam.get("GZ_SIM_RESOURCE_PATH", "")
        ortam["GZ_SIM_RESOURCE_PATH"] = (
            os.path.abspath(self.dizin) + (":" + onceki if onceki else ""))
        ortam.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
        ortam["GZ_PARTITION"] = self.partisyon
        log = open(os.path.join(self.dizin, "gz.log"), "w")
        self._surec = subprocess.Popen(
            ["gz", "sim", "-s", "-r", "--headless-rendering", "-v", "1",
             os.path.abspath(self.sdf)],
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            env=ortam)

    def _sim_durdur(self):
        if self._surec is None:
            return
        try:
            os.killpg(os.getpgid(self._surec.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            self._surec.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        self._surec = None

    def _rtf_oku(self):
        """Sim istatistiklerinden gercek-zaman carpanini oku (rapor icin)."""
        try:
            ck = subprocess.run(
                ["gz", "topic", "-t", f"/world/{self.sen.ad}/stats", "-e", "-n", "1"],
                capture_output=True, text=True, timeout=15,
                env=dict(os.environ, GZ_PARTITION=self.partisyon)).stdout
            for satir in ck.splitlines():
                if "real_time_factor" in satir:
                    return float(satir.split(":")[1])
        except Exception:
            pass
        return None

    # ----------------------------------------------------------------------
    def kaydet(self):
        from gz.transport13 import Node
        from gz.msgs10.camera_info_pb2 import CameraInfo
        from gz.msgs10.image_pb2 import Image
        from gz.msgs10.pose_v_pb2 import Pose_V
        from gz.msgs10.twist_pb2 import Twist
        from gz.msgs10.imu_pb2 import IMU          # A11/KOL 1

        self._sim_baslat()
        dugum = Node()
        if self.surucu.gerekli():
            self.surucu.kur(dugum, Twist)
        # Abonelikler sim ayaga kalkmadan da kurulabilir; konu yayinlanmaya
        # basladiginda baglanir.
        assert dugum.subscribe(Image, "/kamera", self._goruntu_cb)
        assert dugum.subscribe(CameraInfo, "/camera_info", self._kambilgi_cb)
        for ad in self.poz_akis:
            assert dugum.subscribe(Pose_V, f"/model/{ad}/pose",
                                   self._poz_cb_yap(ad))
        # A11/KOL 1: IMU. Konu yoksa (eski dunya SDF'i) abonelik sessizce bos
        # kalir ve imu.csv yazilmaz - eski senaryolar bozulmaz.
        dugum.subscribe(IMU, "/imu", self._imu_cb)

        hedef_toplam = self.kare_hedef + ATLA
        t0 = time.time()
        son_bildirim, rtf = 0, None
        try:
            while True:
                time.sleep(0.5)
                with self.kilit:
                    n = len(self.goruntuler)
                if n >= hedef_toplam:
                    break
                if time.time() - t0 > 25 and rtf is None:
                    rtf = self._rtf_oku()
                if self.ayrinti and n // 25 > son_bildirim:
                    son_bildirim = n // 25
                    print(f"    {n}/{hedef_toplam} kare  "
                          f"({time.time() - t0:.0f} s)", flush=True)
                if time.time() - t0 > 900:
                    raise RuntimeError(
                        f"zaman asimi: 900 s'de {n}/{hedef_toplam} kare geldi. "
                        f"Log: {os.path.join(self.dizin, 'gz.log')}")
                if self._surec.poll() is not None:
                    raise RuntimeError(
                        f"gz sim beklenmedik bicimde sonlandi "
                        f"(cikis {self._surec.returncode}). "
                        f"Log: {os.path.join(self.dizin, 'gz.log')}")
        finally:
            if rtf is None:
                rtf = self._rtf_oku()
            self._sim_durdur()

        self.sure = time.time() - t0
        return self._diske_yaz(rtf)

    # ----------------------------------------------------------------------
    @staticmethod
    def _tek_ara(akis, zamanlar, t):
        """Tek modelin akisinda t anini interpole et. Doner: (poz, bosluk_s)."""
        if not akis:
            return None, float("inf")
        i = np.searchsorted(zamanlar, t)
        if i == 0:
            return akis[0][1], abs(akis[0][0] - t)
        if i >= len(akis):
            return akis[-1][1], abs(akis[-1][0] - t)
        t0_, v0 = akis[i - 1]
        t1_, v1 = akis[i]
        bosluk = min(abs(t - t0_), abs(t1_ - t))
        a0, a1 = np.array(v0), np.array(v1)
        if float(a0[3:] @ a1[3:]) < 0:          # kuaterniyon isaret tutarliligi
            a1 = a1 * np.array([1, 1, 1, -1, -1, -1, -1])
        w = 0.0 if t1_ <= t0_ else (t - t0_) / (t1_ - t0_)
        v = (1 - w) * a0 + w * a1
        q = v[3:] / max(1e-9, np.linalg.norm(v[3:]))
        return tuple(v[:3]) + tuple(q), bosluk

    def _poz_ara(self, t):
        """t anindaki TUM model pozlari. Herhangi biri tolerans disiysa None."""
        cikti, en_kotu = {}, 0.0
        for ad, akis in self._akis_zamanlari.items():
            poz, bosluk = self._tek_ara(self.poz_akis[ad], akis, t)
            if poz is None or bosluk > TOLERANS_S:
                return None, bosluk
            cikti[ad] = poz
            en_kotu = max(en_kotu, bosluk)
        return cikti, en_kotu

    def _diske_yaz(self, rtf):
        sen = self.sen
        with self.kilit:
            kareler = self.goruntuler[ATLA:ATLA + self.kare_hedef]
            n_poz = {ad: len(v) for ad, v in self.poz_akis.items()}
            self._akis_zamanlari = {ad: [p[0] for p in v]
                                    for ad, v in self.poz_akis.items()}

        if self.kam_bilgi is None:
            raise RuntimeError("/camera_info hic gelmedi - intrinsics bilinmiyor")

        # KAMERA POZU = MODEL POZU o SENSOR POZU.
        # Nadir donusu sensorun kendi <pose>'unda durdugu icin (bkz.
        # gazebo/dunya_uret.py) model pozu tek basina kamerayi vermez.
        # Statik drone'da model pozu birimdir -> bileske = sensor pozu, yani
        # G0'in yazdigi deger BIREBIR ayni kalir.
        q_off = _rpy_kuaterniyon(sen.kam_roll, sen.kam_pitch, sen.kam_yaw)
        kam_sabit = (sen.kam_x, sen.kam_y, sen.kam_z)

        adlar = [a.ad for a in sen.araclar]
        basliklar = ["kare", "t"]
        for ad in adlar:
            basliklar += [f"{ad}_{s}" for s in
                          ("x", "y", "z", "qw", "qx", "qy", "qz")]
        basliklar += ["kam_x", "kam_y", "kam_z", "kam_qw", "kam_qx", "kam_qy",
                      "kam_qz", "senkron_bosluk_ms"]

        satirlar, dusen, bosluklar = [], 0, []
        t_ilk = kareler[0][0] if kareler else 0.0
        yazilan = 0
        for (t, bgr) in kareler:
            pozlar, bosluk = self._poz_ara(t)
            if pozlar is None or any(ad not in pozlar for ad in adlar):
                dusen += 1
                continue
            bosluklar.append(bosluk)
            cv2.imwrite(os.path.join(self.kare_dizin, f"{yazilan:06d}.png"), bgr)
            s = [yazilan, f"{t - t_ilk:.6f}"]
            for ad in adlar:
                s += [f"{v:.6f}" for v in pozlar[ad]]
            if "drone" in pozlar:
                d = pozlar["drone"]
                kam_p, q = d[:3], _q_carp(d[3:], q_off)
            else:
                kam_p, q = kam_sabit, q_off
            s += [f"{v:.6f}" for v in kam_p] + [f"{v:.6f}" for v in q]
            s += [f"{bosluk * 1e3:.3f}"]
            satirlar.append(",".join(str(v) for v in s))
            yazilan += 1

        with open(os.path.join(self.dizin, "pozlar.csv"), "w") as f:
            f.write(",".join(basliklar) + "\n")
            f.write("\n".join(satirlar) + "\n")

        # A11/KOL 1: IMU AYRI dosyada - orneklem hizi kare hizindan farkli
        # (200 Hz vs 30 Hz) ve kareye indirgemek bilgi atardi.
        if self.imu_akis:
            with open(os.path.join(self.dizin, "imu.csv"), "w") as f:
                f.write("t,wx,wy,wz,ax,ay,az,qw,qx,qy,qz\n")
                for r in self.imu_akis:
                    f.write(",".join(f"{v:.9f}" for v in r) + "\n")

        meta = {
            "senaryo": sen.ad,
            "aile": sen.aile,
            "siddet": sen.siddet,
            "beklenen": sen.beklenen,
            "etiketler": list(sen.etiketler),
            "aciklama": sen.aciklama,
            "amac": sen.amac,
            "t_ofset_s": round(float(t_ilk), 6),
            "kare_sayisi": yazilan,
            "dusen_kare": dusen,
            "fps": sen.kam_hz,
            "genislik": self.kam_bilgi["genislik"],
            "yukseklik": self.kam_bilgi["yukseklik"],
            "fx": self.kam_bilgi["fx"], "fy": self.kam_bilgi["fy"],
            "cx": self.kam_bilgi["cx"], "cy": self.kam_bilgi["cy"],
            "fov": fov_hesapla(sen.genislik, sen.odak_px),
            "zemin_m": ZEMIN_M,
            "hedef": sen.hedef_ad,
            "araclar": [{"ad": a.ad, "L": a.L, "W": a.W, "H": a.H,
                         "hedef": a.ad == sen.hedef_ad} for a in sen.araclar],
            "kayit": {
                "sure_s": round(self.sure or 0.0, 1),
                "rtf": rtf,
                "poz_ornegi": n_poz,
                "cmd_vel_mesaj": self.surucu.sayac,
                "senkron_bosluk_ms_ort": round(float(np.mean(bosluklar)) * 1e3, 3)
                if bosluklar else None,
                "senkron_bosluk_ms_max": round(float(np.max(bosluklar)) * 1e3, 3)
                if bosluklar else None,
                "tolerans_ms": TOLERANS_S * 1e3,
            },
        }
        with open(os.path.join(self.dizin, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        self.sen_t_ofset = float(t_ilk)
        self._akil_denetimi(satirlar, basliklar)
        return meta

    def _akil_denetimi(self, satirlar, basliklar):
        """Kayit gecerli mi? Sessiz bozulmalari BURADA yakala, olcumde degil.

        Once ogrenildi: kacak bir sim sureci yuzunden karisan pozlarda kare
        sayisi ve senkron boslugu saglikli gorunuyordu; bozulma ancak IoU
        olculdukten sonra fark edilebilirdi. Bu denetim onu one alir.
        """
        if not satirlar:
            raise RuntimeError("hicbir kare yazilamadi - poz akisi bos ya da senkron disi")
        i = {b: n for n, b in enumerate(basliklar)}
        ilk = satirlar[0].split(",")
        yari = ZEMIN_M / 2.0
        for a in self.sen.araclar:
            x, y, z = (float(ilk[i[f"{a.ad}_{s}"]]) for s in ("x", "y", "z"))
            bek_z = a.H / 2.0
            if abs(x - a.x0) > 5.0 or abs(y - a.y0) > 5.0:
                raise RuntimeError(
                    f"{a.ad}: baslangic pozu SDF ile uyusmuyor "
                    f"({x:.1f}, {y:.1f}) != ({a.x0:.1f}, {a.y0:.1f}). "
                    f"Baska bir gz sim sureci ayni konulara yayin yapiyor olabilir.")
            if abs(z - bek_z) > 1.0:
                raise RuntimeError(
                    f"{a.ad}: z = {z:.2f} m, beklenen {bek_z:.2f} m "
                    f"(arac zemine oturmuyor - yercekimi/fizik sorunu)")
            if max(abs(x), abs(y)) > yari:
                raise RuntimeError(f"{a.ad} zemin disinda: ({x:.1f}, {y:.1f})")
        self._kamera_denetimi(satirlar, i)

    def _kamera_denetimi(self, satirlar, i):
        """Kamera GERCEKTEN komut edilen gibi hareket etti mi?

        En sinsi Faz B hatasi bu olurdu: cmd_vel hic ulasmaz, drone sabit
        kalir, kayit kusursuz gorunur ve "agresif kamera senaryosunda kopma
        yok" diye YANLIS bir sonuc yazilir. Bu yuzden kayitli poza bakip
        olculen tepe hizi profilin komut ettigi tepe hizla karsilastirilir.
        """
        sen = self.sen
        if sen.drone_statik or sen.kam_profil is None:
            return
        d = np.array([[float(r.split(",")[i[b]]) for b in
                       ("t", "kam_x", "kam_y", "kam_z",
                        "kam_qw", "kam_qx", "kam_qy", "kam_qz")]
                      for r in satirlar])
        t, P, Q = d[:, 0], d[:, 1:4], d[:, 4:8]
        dt = np.diff(t)
        if not len(dt) or dt.min() <= 0:
            raise RuntimeError("kamera denetimi: zaman damgalari artmiyor")
        v_olculen = float(np.linalg.norm(np.diff(P, axis=0), axis=1).max() / dt.min())
        # ardisik donmeler arasi aci: q_rel = q_{k-1}^-1 o q_k
        aci = []
        for k in range(1, len(Q)):
            a, b = Q[k - 1], Q[k]
            nokta = float(np.clip(abs(a @ b), -1.0, 1.0))
            aci.append(2.0 * np.arccos(nokta))
        w_olculen = float(np.max(aci) / dt.min()) if aci else 0.0

        izgara = np.linspace(t[0], t[-1], 400) + float(self.sen_t_ofset)
        komut = np.array([sen.kam_profil(float(x)) for x in izgara])
        v_komut = float(np.linalg.norm(komut[:, :3], axis=1).max())
        w_komut = float(np.linalg.norm(komut[:, 3:], axis=1).max())

        for ad, olc, kom, esik in (("dogrusal", v_olculen, v_komut, 0.40),
                                   ("acisal", w_olculen, w_komut, 0.40)):
            if kom > 0.05 and olc < esik * kom:
                raise RuntimeError(
                    f"kamera {ad} hareketi komutu izlemiyor: olculen tepe "
                    f"{olc:.3f}, komut {kom:.3f} (cmd_vel drone'a ulasmiyor "
                    f"olabilir; VelocityControl eklentisi ve /model/drone/cmd_vel "
                    f"konusunu denetle)")


def _rpy_kuaterniyon(roll, pitch, yaw):
    cr, sr = np.cos(roll / 2), np.sin(roll / 2)
    cp, sp = np.cos(pitch / 2), np.sin(pitch / 2)
    cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)
    return (cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy)


def _tek(ad, kok, kare):
    sen = SENARYOLAR[ad]()
    print(f"{sen.ad}: {sen.aciklama}")
    print(f"  amac: {sen.amac}")
    if sen.beklenen:
        print(f"  tasarim yuku: {sen.beklenen}")
    k = Kayitci(sen, kok=kok, kare_hedef=kare or sen.kare)
    print(f"  dunya: {k.sdf}")
    meta = k.kaydet()
    print(f"  kaydedildi: {meta['kare_sayisi']} kare "
          f"({meta['genislik']}x{meta['yukseklik']}), "
          f"dusen {meta['dusen_kare']}, sure {meta['kayit']['sure_s']} s")
    print(f"  RTF: {meta['kayit']['rtf']}  "
          f"cmd_vel {meta['kayit']['cmd_vel_mesaj']} mesaj  "
          f"senkron bosluk ort {meta['kayit']['senkron_bosluk_ms_ort']} ms / "
          f"max {meta['kayit']['senkron_bosluk_ms_max']} ms")
    return meta


def _hepsi(adlar, kok, kare):
    """Her senaryoyu AYRI SURECTE kaydet.

    Tek surecte ard arda kaydetmek denenmedi bile: gz.transport Node'u
    GZ_PARTITION'i olusturma aninda okur ve onceki kosumun abonelikleri ayni
    surecte yasamaya devam eder. G0'da tam bu sinif hata (kacak sim + karisan
    konular) sessizce bozuk GT uretmisti; ayri surec o kapiyi kapatir.
    """
    basarili, basarisiz = [], []
    for n, ad in enumerate(adlar, 1):
        print(f"\n[{n}/{len(adlar)}] {ad}", flush=True)
        cmd = [sys.executable, "-m", "gazebo.kaydet", ad, "--kok", kok]
        if kare:
            cmd += ["--kare", str(kare)]
        r = subprocess.run(cmd, cwd=os.getcwd())
        (basarili if r.returncode == 0 else basarisiz).append(ad)
    print(f"\nbitti: {len(basarili)} basarili, {len(basarisiz)} basarisiz")
    if basarisiz:
        print("  basarisiz: " + ", ".join(basarisiz))
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Gazebo senaryosunu diske kaydet")
    ap.add_argument("senaryo", nargs="?", default="G0")
    ap.add_argument("--kok", default="data/gazebo")
    ap.add_argument("--kare", type=int, default=0)
    ap.add_argument("--hepsi", action="store_true",
                    help="Faz B'nin 14 senaryosunu sirayla kaydet")
    a = ap.parse_args()

    if a.hepsi:
        _hepsi(FAZ_B, a.kok, a.kare)
        return

    if a.senaryo not in SENARYOLAR:
        print(f"HATA: bilinmeyen senaryo {a.senaryo!r} "
              f"(secenekler: {', '.join(SENARYOLAR)})")
        sys.exit(1)
    _tek(a.senaryo, a.kok, a.kare)


if __name__ == "__main__":
    main()
