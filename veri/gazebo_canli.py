"""Gazebo CANLI kaynak: klavye kontrollu, GERCEK ZAMANLI ucus + takip.

`veri/gazebo.py:GazeboKaynak`'tan FARKLI: o kayittan (diskten) okur, bu
GERCEK ZAMANDA calisan bir `gz sim` surecine baglanir - kareler `/kamera`
konusundan geldigi anda islenir, drone `/model/drone/cmd_vel`'e klavye
komutlariyla YAYINLANAN Twist ile surulur. `kaynak.py`nin sozlesmesi disina
CIKMAZ: `oku()` -> Kare, `gt=None` (canli ucuste onceden kaydedilmis
kusursuz poz akisi yok - GT'siz calisir, bu yuzden `--mod demo`nun
YOLO-tabanli sicak-sizsiz edinme yolu kullanilmalidir), `kare_sayisi=-1`
("surekli").

Bridge deseni `arastirma-v1` dalindaki `gazebo/tani_a11_kol3.py`dan
alindi (kanitlanmis "kayit-sonra-oynat DEGIL, canli gz sim" kalibi):
`gz sim -s -r --headless-rendering` subprocess + `gz.transport13.Node`
ile `/kamera` (Image) ve `/model/drone/pose` (Pose_V) aboneligi +
`/model/drone/cmd_vel` (Twist) yayini, hepsi tek Python surecinde, kilit
korumali paylasilan durum uzerinden. KOL3 kamerayi SCRIPTED bir kontrol
yasasiyla suruyordu; burada onun yerine KLAVYEDEN gelen bir Twist var.

Sahne: DEMO ailesiyle AYNI kanitlanmis yerlesim (baylands zemini + IMX500
kamera, `gazebo/senaryolar.py:_demo`'nun kullandigi sabitler) - yalniz
`kam_profil=None` (drone'u BEN degil, KULLANICI/klavye surer) ve tek bir
sabit hizla ilerleyen hedef arac.

KLAVYE: main.kos() dongusu zaten her karede `cv2.waitKey` cagiriyor
(`goster()`); bu modul o ham tus kodunu `tus_isle()` ile alip
`/model/drone/cmd_vel`e cevirir - YENI bir okuma dongusu ACILMAZ.
    W/S : ileri/geri (govde +x/-x)      A/D : sol/sag (govde -y/+y)
    R/F : yukari/asagi (govde +z/-z)    Q/E : yaw sola/saga
Tus birakilinca (TUS_ZAMAN_ASIMI boyunca tekrar gelmezse) o bilesen
SIFIRLANIR - fiziksel klavyenin OS-seviyesi tekrarina guvenir, ayri bir
"tus yukarda" olayi YOKTUR (cv2.waitKey bunu vermez).

Scripted/otomatik kontrol (ornegin kabul testi) icin `komut_ayarla(vx,
vy, vz, wz)` dogrudan cagrilabilir - `tus_isle()` ile AYNI alt yapiyi
kullanir, klavye zaman asimina TABI DEGILDIR (cagiran kendi durdurma
mantigini kurar).
"""
import os
import signal
import subprocess
import threading
import time

import cv2
import numpy as np

from kaynak import Kare, Kaynak, KaynakHatasi
from gazebo.dunya_uret import dunya_yaz
from gazebo.senaryolar import (
    Arac, GzSenaryo, DEMO_MERKEZ_X, DEMO_MERKEZ_Y, DEMO_HIZ,
    ODAK_PX, KAM_HZ, Y1_MESH_L, Y1_MESH_W, Y1_MESH_H,
)

# CANLI CIKTI COZUNURLUGU (2026-09-08, olculdu): IMX500 tam cozunurlugu
# (2028x1520) canli modda RTF~0.22, ham kare FPS~6.6 veriyor - FPS>=15
# kabul esigini GECEMEZ. Arastirma kamerasi cozunurlugu (640x480, ayni
# G0-G7 ailesi) RTF~0.57, ham kare FPS~17.2'ye cikariyor - canli mod
# icin BUNU kullan (DEMO'nun offline kaydinda kullanilan IMX500 DEGIL -
# orada gercek zamanlilik onemsizdi, burada ESAS kisit budur).
CANLI_GEN, CANLI_YUK = 640, 480

TUS_HIZ_YATAY = 5.0      # m/s - W/A/S/D
TUS_HIZ_DIKEY = 3.0      # m/s - R/F (200 m'ye kadar tirmanis icin yeterli)
TUS_HIZ_YAW = 0.6        # rad/s - Q/E
TUS_ZAMAN_ASIMI = 0.35   # s - bu sureden uzun tekrar gelmeyen tus birakildi sayilir

# tus -> (komut bileseni index'i [vx,vy,vz,wz], isaret)
TUSLAR = {
    ord("w"): (0, +1), ord("s"): (0, -1),
    ord("d"): (1, +1), ord("a"): (1, -1),
    ord("r"): (2, +1), ord("f"): (2, -1),
    ord("e"): (3, +1), ord("q"): (3, -1),
}


def canli_senaryo(kam_z0=50.0):
    """DEMO ailesinin baylands zemini + celdiricisiz tek hedef, ama IMX500
    DEGIL arastirma kamerasi cozunurlugu (640x480, odak 500px, ayni
    G0-G7 ailesi) - CANLI_GEN/YUK ustteki not, RTF/FPS olcumu gerekcesi."""
    hedef = Arac("hedef", x0=DEMO_MERKEZ_X - 30.0, y0=DEMO_MERKEZ_Y, yaw=0.0,
                 vx=DEMO_HIZ, renk=(0.16, 0.16, 0.75), mesh="hatchback",
                 L=Y1_MESH_L, W=Y1_MESH_W, H=Y1_MESH_H)
    return GzSenaryo(
        ad="Canli", aciklama="Klavye kontrollu canli ucus + takip",
        amac="canli baglanti + kontrol dongusu kabul testi",
        araclar=[hedef], hedef_ad="hedef",
        kam_x=DEMO_MERKEZ_X - 30.0, kam_y=DEMO_MERKEZ_Y, kam_z=kam_z0,
        kam_profil=None, drone_statik=False, kare=1,
        zemin_tipi="baylands", genislik=CANLI_GEN, yukseklik=CANLI_YUK,
        odak_px=ODAK_PX, kam_hz=KAM_HZ, aile="CANLI")


class GazeboCanliKaynak(Kaynak):
    """`--source gazebo_canli`. `gazebo/kaydet.py:Kayitci` ile AYNI gz.transport
    ilkeleri (GZ_PARTITION izolasyonu, headless-rendering) ama DISKE
    YAZMAZ - yalniz SON kareyi bellekte tutar, canli tuketilir."""

    tur = "gazebo_canli"
    kare_sayisi = -1
    KARE_ZAMAN_ASIMI = 5.0   # s - bu sure boyunca yeni kare gelmezse ariza say
    BASLAMA_ZAMAN_ASIMI = 60.0

    def __init__(self, kok="data/gazebo", kam_z0=50.0, gui=False, sure_sn=None):
        """`gui=True`: `gz sim -g` istemcisi de acilir (sunucuya AYNI
        GZ_PARTITION ile baglanir, yalniz GORSEL izleme icin - takip
        hattini etkilemez, WSL2'de X sunucusu/WSLg gerekir, bkz.
        docs/KURULUM.md). `sure_sn`: verilirse `oku()` bu sure (duvar
        saati) dolunca temiz bicimde None doner (StopIteration) - kabul
        testi gibi sinirli-sureli otomatik kosumlar icin; verilmezse
        (varsayilan) sinirsiz, davranis DEGISMEZ."""
        self.sen = canli_senaryo(kam_z0=kam_z0)
        self.sdf, self.dizin = dunya_yaz(self.sen, kok)
        self.genislik, self.yukseklik = self.sen.genislik, self.sen.yukseklik
        self.fps = float(self.sen.kam_hz)
        self.ad = f"gazebo_canli:{self.sen.ad}"
        self.sure_sn = float(sure_sn) if sure_sn is not None else None
        self._baslangic = time.time()   # asagida _baglan() sonrasi YENIDEN ayarlanir
        # KONU IZOLASYONU: gazebo/kaydet.py:Kayitci ile AYNI gerekce - onceki
        # bir kosumdan kalan `gz sim` ayni konulara yayin yapiyor olabilir.
        self.partisyon = f"canli-{os.getpid()}"
        os.environ["GZ_PARTITION"] = self.partisyon

        self._kilit = threading.Lock()
        self._son_kare = None
        self._yeni_kare = threading.Event()
        self._irtifa = kam_z0
        self._komut = np.zeros(4, np.float32)      # vx,vy,vz,wz (govde cercevesi)
        self._son_tus_t = [0.0, 0.0, 0.0, 0.0]
        self._k = 0
        self._surec = None
        self._gui_surec = None
        self._log = None

        self._sim_baslat()
        if gui:
            self._gui_baslat()
        try:
            self._baglan()
        except Exception:
            self.kapat()
            raise
        # `sure_sn` BAGLANTI TAMAMLANDIKTAN SONRA baslar - dunya yuklemesi
        # (Fuel/baylands) birkac saniye surebiliyor, __init__ basindan
        # saymak butceyi baglanti bitmeden tuketip ilk oku()'da 0 kare
        # dondururdu (olculdu, bkz. commit).
        self._baslangic = time.time()

    # ------------------------------------------------------------------
    def _sim_baslat(self):
        ortam = dict(os.environ)
        onceki = ortam.get("GZ_SIM_RESOURCE_PATH", "")
        ortam["GZ_SIM_RESOURCE_PATH"] = (
            os.path.abspath(self.dizin) + (":" + onceki if onceki else ""))
        ortam.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
        ortam["GZ_PARTITION"] = self.partisyon
        self._log = open(os.path.join(self.dizin, "gz_canli.log"), "w")
        self._surec = subprocess.Popen(
            ["gz", "sim", "-s", "-r", "--headless-rendering", "-v", "1",
             os.path.abspath(self.sdf)],
            stdout=self._log, stderr=subprocess.STDOUT, start_new_session=True,
            env=ortam)

    def _gui_baslat(self):
        """`--gui`: yalniz GORSEL izleme icin AYRI bir `gz sim -g` istemcisi.
        Ayni GZ_PARTITION'a sunucu OLMADAN (`-g`, `-s` YOK) baglanir; takip
        hattina hicbir etkisi yok, acilamazsa (DISPLAY yok vb.) SESSIZCE
        vazgecilir - `--gui` verilmemis gibi devam eder."""
        ortam = dict(os.environ)
        ortam["GZ_PARTITION"] = self.partisyon
        try:
            self._gui_surec = subprocess.Popen(
                ["gz", "sim", "-g"], env=ortam,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            self._gui_surec = None

    def _baglan(self):
        from gz.transport13 import Node
        from gz.msgs10.image_pb2 import Image
        from gz.msgs10.pose_v_pb2 import Pose_V
        from gz.msgs10.twist_pb2 import Twist
        self._Twist = Twist
        self._dugum = Node()
        assert self._dugum.subscribe(Image, "/kamera", self._goruntu_cb)
        assert self._dugum.subscribe(Pose_V, "/model/drone/pose", self._poz_cb)
        self._yayinci = self._dugum.advertise("/model/drone/cmd_vel", Twist)

        t0 = time.time()
        while True:
            with self._kilit:
                geldi = self._son_kare is not None
            if geldi:
                return
            if self._surec.poll() is not None:
                raise KaynakHatasi(
                    f"gz sim baslamadan sonlandi (log: {self._log.name})")
            if time.time() - t0 > self.BASLAMA_ZAMAN_ASIMI:
                raise KaynakHatasi(
                    f"{self.BASLAMA_ZAMAN_ASIMI:.0f} s'de ilk kare gelmedi "
                    f"(log: {self._log.name})")
            time.sleep(0.1)

    # -- gz.transport geri cagirmalari (kendi is parcaciklarinda kosar) ----
    def _goruntu_cb(self, msg):
        try:
            rgb = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, 3)
        except ValueError:
            return                                  # eksik/bozuk kare: atla
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        with self._kilit:
            self._son_kare = bgr
        self._yeni_kare.set()

    def _poz_cb(self, msg):
        for p in msg.pose:
            if p.name == "drone":
                with self._kilit:
                    self._irtifa = float(p.position.z)
                return

    # -- klavye/otomatik -> hiz komutu ---------------------------------
    def komut_ayarla(self, vx, vy, vz, wz):
        """`/model/drone/cmd_vel`e DOGRUDAN Twist yayinlar (govde cercevesi,
        m/s ve rad/s) - klavye zaman asimina TABI DEGIL. Scripted/otomatik
        kontrol (ornegin kabul testi) icindir; `tus_isle()` ile PAYLASILAN
        `self._komut`u da gunceller (ikisi karisik kullanilirsa tutarli
        kalsin diye)."""
        self._komut[:] = (vx, vy, vz, wz)
        self._yayinla()

    def tus_isle(self, tus_kod):
        """`cv2.waitKey() & 0xFF` sonucunu isler ve GUNCEL komutu
        `/model/drone/cmd_vel`e yayinlar (tus gelmese bile HER KAREDE
        cagrilmali - aksi halde zaman asimiyla sifirlama calismaz)."""
        if tus_kod in TUSLAR:
            i, isaret = TUSLAR[tus_kod]
            hiz = TUS_HIZ_YAW if i == 3 else (TUS_HIZ_DIKEY if i == 2 else TUS_HIZ_YATAY)
            self._komut[i] = isaret * hiz
            self._son_tus_t[i] = time.time()
        simdi = time.time()
        for i in range(4):
            if simdi - self._son_tus_t[i] > TUS_ZAMAN_ASIMI:
                self._komut[i] = 0.0
        self._yayinla()

    def _yayinla(self):
        m = self._Twist()
        m.linear.x = float(self._komut[0])
        m.linear.y = float(self._komut[1])
        m.linear.z = float(self._komut[2])
        m.angular.z = float(self._komut[3])
        self._yayinci.publish(m)

    @property
    def irtifa(self):
        with self._kilit:
            return self._irtifa

    # ------------------------------------------------------------------
    def oku(self):
        if self.sure_sn is not None and time.time() - self._baslangic >= self.sure_sn:
            return None                              # temiz bitis (kabul testi)
        if self._surec.poll() is not None:
            raise KaynakHatasi(
                f"gz sim beklenmedik bicimde sonlandi (log: {self._log.name})")
        if not self._yeni_kare.wait(timeout=self.KARE_ZAMAN_ASIMI):
            raise KaynakHatasi(
                f"{self.KARE_ZAMAN_ASIMI:.0f} s'de yeni kare gelmedi - sim "
                f"takilmis olabilir (log: {self._log.name})")
        self._yeni_kare.clear()
        with self._kilit:
            goruntu = self._son_kare.copy()
        k = self._k
        self._k += 1
        return Kare(goruntu=goruntu, indeks=k, zaman=time.time(),
                    kaynak_adi=self.ad, genislik=self.genislik,
                    yukseklik=self.yukseklik, fps=self.fps,
                    gt=None, gorunur=None)

    def acik_mi(self):
        return self._surec is not None and self._surec.poll() is None

    def bilgi(self):
        return (f"{self.ad}  {self.genislik}x{self.yukseklik}  "
                f"{self.fps:.0f} fps  surekli (CANLI)  irtifa~{self.irtifa:.1f} m")

    def kapat(self):
        if self._gui_surec is not None:
            try:
                self._gui_surec.terminate()
            except Exception:
                pass
            self._gui_surec = None
        if self._surec is not None:
            try:
                os.killpg(os.getpgid(self._surec.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                self._surec.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            self._surec = None
        if self._log is not None:
            self._log.close()
            self._log = None
