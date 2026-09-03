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
    n = DOKU_PX if n is None else int(n)
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
        return int(round(n / 2 + xm * TEXEL_PM)), int(round(n / 2 - ym * TEXEL_PM))

    def dm(v):
        return int(round(v * TEXEL_PM))

    # --- ana yol: y = 0 ekseni boyunca, 9 m genislik ---
    yol_w = 9.0
    x0, yust = m2t(-ZEMIN_M / 2, +yol_w / 2)
    x1, yalt = m2t(+ZEMIN_M / 2, -yol_w / 2)
    cv2.rectangle(img, (x0, yust), (x1, yalt), (68, 68, 70), -1)
    # asfalt greni: LK'nin yol uzerinde de kose bulabilmesi icin sart
    asf = rng.integers(-9, 9, (yalt - yust, x1 - x0, 1), dtype=np.int16)
    img[yust:yalt, x0:x1] = np.clip(
        img[yust:yalt, x0:x1].astype(np.int16) + asf, 0, 255).astype(np.uint8)
    # orta kesikli serit (9 m aralik, 3 m cizgi)
    ym = m2t(0, 0)[1]
    for xm in np.arange(-ZEMIN_M / 2, ZEMIN_M / 2, 9.0):
        a, _ = m2t(xm, 0)
        cv2.rectangle(img, (a, ym - 2), (a + dm(3.0), ym + 2), (215, 215, 215), -1)
    # kenar cizgileri
    cv2.line(img, (x0, yust + 3), (x1, yust + 3), (200, 200, 200), 2)
    cv2.line(img, (x0, yalt - 3), (x1, yalt - 3), (200, 200, 200), 2)

    # --- dikey yan yollar ---
    for xm in np.arange(-ZEMIN_M / 2 + 20, ZEMIN_M / 2, 45.0):
        a, _ = m2t(xm - 3.5, 0)
        b, _ = m2t(xm + 3.5, 0)
        cv2.rectangle(img, (a, 0), (b, n), (66, 66, 68), -1)

    # --- binalar / agaclar / calilar: LK'nin kose kaynagi ---
    for _ in range(140):
        bx, by = rng.uniform(-ZEMIN_M / 2, ZEMIN_M / 2, 2)
        if abs(by) < 14:
            continue
        w_, h_ = rng.uniform(8, 26, 2)
        col = tuple(int(v) for v in rng.integers(70, 190, 3))
        p0, p1 = m2t(bx, by), m2t(bx + w_, by + h_)
        cv2.rectangle(img, p0, p1, col, -1)
        cv2.rectangle(img, p0, p1, tuple(int(v * 0.6) for v in col), 3)
    for _ in range(600):
        tx, ty = rng.uniform(-ZEMIN_M / 2, ZEMIN_M / 2, 2)
        if abs(ty) < 8:
            continue
        cv2.circle(img, m2t(tx, ty), int(rng.uniform(2, 5) * TEXEL_PM), (30, 70, 35), -1)
    # kucuk olcekli detay - ego-motion'in can damari
    for _ in range(6000):
        tx, ty = rng.uniform(-ZEMIN_M / 2, ZEMIN_M / 2, 2)
        if abs(ty) < 7:
            continue
        r = max(1, int(rng.uniform(0.5, 1.5) * TEXEL_PM))
        col = (int(rng.integers(25, 60)), int(rng.integers(60, 110)),
               int(rng.integers(25, 60)))
        cv2.circle(img, m2t(tx, ty), r, col, -1)
    # tarla sinirlari
    for _ in range(60):
        tx, ty = rng.uniform(-ZEMIN_M / 2, ZEMIN_M / 2, 2)
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
    # simetrik.
    return cv2.transpose(img)


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
        rk, gk, bk = [c * 0.45 for c in a.renk]
        # profil varsa t=0 degeri baslangic hizi olur (govde cercevesi)
        v0 = a.profil(0.0) if a.profil else (a.vx, a.vy, a.wz)
        parcalar.append(_ARAC_SDF.format(
            ad=a.ad, x=a.x0, y=a.y0, z=a.H / 2.0, yaw=a.yaw,
            L=a.L, W=a.W, H=a.H,
            r=a.renk[0], g=a.renk[1], b=a.renk[2],
            rk=rk, gk=gk, bk=bk,
            tavan_dx=-0.25, tavan_dz=a.H * 0.42,
            tavan_L=a.L * 0.45, tavan_W=a.W * 0.80, tavan_H=a.H * 0.30,
            hiz_kontrol=_HIZ_KONTROL.format(vx=v0[0], vy=v0[1], vz=0.0,
                                            wx=0.0, wy=0.0, wz=v0[2]),
            poz_yayinci=_POZ_YAYINCI))

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
