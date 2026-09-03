"""A11 KOL 3 - UCUS GEOMETRISI (spesifikasyon deneyi, KAPALI CEVRIM CANLI).

*** KOMPOZIT YATAK KULLANILMAZ *** · *** KAYIT-SONRA-OYNAT DEGIL, CANLI gz sim ***

ON-KAYIT: docs/architecture/A11_ONKAYIT.md §5 (+ EK-3, KOSUMDAN ONCE eklendi).

KONTROL YASASI (EK-3, yeni sabit uydurulmadi):
    L_est = max(tak.boyut)              (takipcinin KENDI tahmini, GT DEGIL)
    her poz orneginde:
        vz_taban = A2_kucul'un DEGISMEMIS kam_profil(t)'sinin vz'si
        vz = -vz_taban  eger L_est < 25 px (on-kayit esigi)  else  vz_taban

Dunya A2_kucul'un DUNYASI (SDF/arac/zemin degismedi); tek fark kam_profil'in
kapali cevrim sarmalayiciyla degistirilmesi.

HAKEM KULLANILMAZ (EK-3 kapsam daraltmasi: KOL 0 dedektorun Gazebo'da
%100 kor oldugunu olctu, hakem zaten inert olurdu). Saf takipci (H0/KOL1/
KOL2 ile ayni kapsam).

3a (kontrol) = A2_kucul'un degismemis hali, cikti/a11_kol0.json'da H0 olarak
ZATEN olculu - burada YENIDEN KOSULMUYOR.
"""
import dataclasses
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from calistir import iou                                          # noqa: E402
from gazebo.a11_ortak import kosular, YANLIS_IOU, MIN_EPIZOT       # noqa: E402
from gazebo.dunya_uret import dunya_yaz                            # noqa: E402
from gazebo.kaydet import Surucu, _stamp, _poz_stamp                # noqa: E402
from gazebo.senaryolar import A2_kucul                              # noqa: E402
from takip.izleyici import ARAMA, KAYIP, KILITLI, SUPHELI, HedefTakip  # noqa: E402
from veri.gazebo import _kutu_koseleri, izdusur, kuaterniyon_matris  # noqa: E402

ESIK_PX = 25.0             # on-kayit §5 esigi
KARE_HEDEF = 500
ATLA = 5
KOK = "/tmp/claude-1000/-home-beyza/3ac50ecf-233b-45f2-a7b3-eedcc1edc49a/scratchpad/a11_kol3_dunya"
ZAMAN_ASIMI_S = 180


class KontrolSarmalayici:
    """A2_kucul'un kam_profil'ini EK-3 kontrol yasasiyla sarar."""

    def __init__(self, taban_profil):
        self.taban = taban_profil
        self.L_est = None            # kamera geri cagrisi gunceller
        self.iz = []                 # (t, L_est, koruma_modu)

    def __call__(self, t):
        d = self.taban(t)
        koruma = self.L_est is not None and self.L_est < ESIK_PX
        vz = -d[2] if koruma else d[2]
        self.iz.append((float(t), self.L_est, bool(koruma)))
        return (d[0], d[1], vz, d[3], d[4], d[5])


def main():
    ad = "A11_KOL3_canli"
    sen = A2_kucul()
    kontrol = KontrolSarmalayici(sen.kam_profil)
    sen = dataclasses.replace(sen, ad=ad, kam_profil=kontrol, kare=KARE_HEDEF)

    partisyon = f"a11k3-{os.getpid()}"
    os.environ["GZ_PARTITION"] = partisyon
    sdf, dizin = dunya_yaz(sen, kok=KOK)
    print(f"dunya: {sdf}", flush=True)

    ortam = dict(os.environ)
    onceki = ortam.get("GZ_SIM_RESOURCE_PATH", "")
    ortam["GZ_SIM_RESOURCE_PATH"] = os.path.abspath(dizin) + (":" + onceki if onceki else "")
    ortam.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    ortam["GZ_PARTITION"] = partisyon
    log = open(os.path.join(dizin, "gz.log"), "w")
    surec = subprocess.Popen(
        ["gz", "sim", "-s", "-r", "--headless-rendering", "-v", "1", os.path.abspath(sdf)],
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=ortam)

    from gz.transport13 import Node
    from gz.msgs10.camera_info_pb2 import CameraInfo
    from gz.msgs10.image_pb2 import Image
    from gz.msgs10.pose_v_pb2 import Pose_V
    from gz.msgs10.twist_pb2 import Twist

    kilit = threading.Lock()
    durum = {"goruntu_sayisi": 0, "kam_bilgi": None, "hedef_poz": None,
            "drone_poz": None, "kayit": [], "tak": None, "bitti": False}

    def kambilgi_cb(msg):
        if durum["kam_bilgi"] is not None:
            return
        k = list(msg.intrinsics.k) if len(msg.intrinsics.k) == 9 else None
        if k is None:
            return
        durum["kam_bilgi"] = {"fx": k[0], "fy": k[4], "cx": k[2], "cy": k[5],
                              "genislik": msg.width, "yukseklik": msg.height}

    def hedef_poz_cb(msg):
        for pz in msg.pose:
            if pz.name != "hedef":
                continue
            with kilit:
                durum["hedef_poz"] = (pz.position.x, pz.position.y, pz.position.z,
                                      pz.orientation.w, pz.orientation.x,
                                      pz.orientation.y, pz.orientation.z)

    def drone_poz_cb(msg):
        for pz in msg.pose:
            if pz.name != "drone":
                continue
            with kilit:
                durum["drone_poz"] = (pz.position.x, pz.position.y, pz.position.z)
            surucu.tik("drone", _poz_stamp(pz, msg), (pz.orientation.w, pz.orientation.x,
                                                       pz.orientation.y, pz.orientation.z))

    def goruntu_cb(msg):
        with kilit:
            if durum["bitti"]:
                return
            durum["goruntu_sayisi"] += 1
            n = durum["goruntu_sayisi"]
            kb = durum["kam_bilgi"]
            hp = durum["hedef_poz"]
            dp = durum["drone_poz"]
        if n <= ATLA or kb is None or hp is None or dp is None:
            return
        a = np.frombuffer(msg.data, np.uint8)
        try:
            rgb = a.reshape(msg.height, msg.width, 3)
        except ValueError:
            return
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        # GT kutusu (yaklasik - EN YAKIN poz orneginden, enterpolasyonSUZ,
        # KOL 3 CANLI oldugu icin Kayitci'nin offline enterpolasyonu yok.
        # Bu bir SINIRDIR, raporda belirtilir.)
        C = np.array([dp[0], dp[1], dp[2]])
        # kamera GOVDE+sabit sensor donusu: A11'de drone modeli dik durur,
        # sensor kendi <pose>'unda doner (KAM_ROT) - govde q'sunu OKUMUYORUZ
        # (poz akisinda yok); bunun yerine hedef_poz ile SADECE mesafe/boyut
        # kestirimi icin kaba bir izdusum kullanilir: dogrudan L_est=tak.boyut
        # KARSILASTIRMASI icin GT kutusu gerekmiyor, yalnizca RAPORLAMA icin
        # yaklasik bir GT_L (irtifa uzerinden) hesaplanir.
        irtifa = float(dp[2])
        GT_L_yaklasik = 500.0 * 4.6 / max(irtifa, 1e-6)

        tak = durum["tak"]
        ilk = False
        if tak is None:
            tak = HedefTakip()
            # ilk kilit: goruntu merkezine yakin, GT_L_yaklasik boyutunda kaba kutu
            H, W = bgr.shape[:2]
            b = GT_L_yaklasik
            kutu0 = np.array([W / 2 - b / 2, H / 2 - b * 0.4, b, b * 0.42], np.float32)
            tak.kilitle(bgr, kutu0)
            durum["tak"] = tak
            ilk = True

        if not ilk:
            s = tak.guncelle(bgr)
        else:
            s = {"kutu": tak.kutu, "durum": tak.durum, "psr": tak.psr}

        L_est = float(np.max(tak.boyut)) if tak.boyut is not None else None
        kontrol.L_est = L_est

        with kilit:
            durum["kayit"].append({
                "t": n, "L_est": L_est, "GT_L_yaklasik": round(GT_L_yaklasik, 2),
                "irtifa": round(irtifa, 2), "durum": str(s["durum"]),
                "koruma_modu": bool(L_est is not None and L_est < ESIK_PX),
            })
            if durum["goruntu_sayisi"] >= KARE_HEDEF + ATLA:
                durum["bitti"] = True

    dugum = Node()
    surucu = Surucu(sen)
    surucu.kur(dugum, Twist)
    assert dugum.subscribe(Image, "/kamera", goruntu_cb)
    assert dugum.subscribe(CameraInfo, "/camera_info", kambilgi_cb)
    assert dugum.subscribe(Pose_V, "/model/hedef/pose", hedef_poz_cb)
    assert dugum.subscribe(Pose_V, "/model/drone/pose", drone_poz_cb)

    t0 = time.time()
    try:
        while True:
            with kilit:
                bitti = durum["bitti"]
                n = durum["goruntu_sayisi"]
            if bitti:
                break
            if time.time() - t0 > ZAMAN_ASIMI_S:
                print("ZAMAN ASIMI", flush=True)
                break
            if int(time.time() - t0) % 10 == 0:
                print(f"  ... {n}/{KARE_HEDEF + ATLA} kare, {time.time()-t0:.0f}s", flush=True)
            time.sleep(0.5)
    finally:
        try:
            os.killpg(os.getpgid(surec.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            surec.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass

    kayit = durum["kayit"]
    print(f"\ntoplanan kare: {len(kayit)}", flush=True)

    # ---------------- ozet ----------------
    esik20 = sum(1 for k in kayit if k["L_est"] is not None and k["L_est"] < 20)
    koruma = [k for k in kayit if k["koruma_modu"]]
    yk = sum(1 for k in koruma if k["durum"] == "KILITLI" and
            (k["L_est"] is None or k["L_est"] < 3))   # kaba GT'siz vekil - bkz. sinirlar
    kopus_benzeri = kosular(kayit, lambda k: k["durum"] in ("ARAMA", "KAYIP"), 5)

    cikti = {
        "etiketler": ["KAPALI CEVRIM", "CANLI gz sim", "KOMPOZIT YATAK YOK",
                     "HAKEM KULLANILMADI (EK-3)"],
        "onkayit": "docs/architecture/A11_ONKAYIT.md §5 (+EK-3)",
        "esik_px": ESIK_PX, "kare_toplanan": len(kayit),
        "kayit": kayit,
        "kontrol_izi": kontrol.iz,
        "ozet": {
            "kare_20px_altinda_orani": round(esik20 / max(len(kayit), 1), 4),
            "koruma_modu_kare_sayisi": len(koruma),
            "koruma_modu_orani": round(len(koruma) / max(len(kayit), 1), 4),
            "koruma_modunda_ARAMA_KAYIP_kare": sum(
                1 for k in koruma if k["durum"] in ("ARAMA", "KAYIP")),
            "ARAMA_KAYIP_benzeri_epizot": len(kopus_benzeri),
            "irtifa_min": round(min(k["irtifa"] for k in kayit), 2) if kayit else None,
            "irtifa_max": round(max(k["irtifa"] for k in kayit), 2) if kayit else None,
        },
    }
    yol = os.path.join(ROOT, "cikti", "a11_kol3.json")
    json.dump(cikti, open(yol, "w"), indent=2, ensure_ascii=False)
    print("yazildi:", yol)
    print(json.dumps(cikti["ozet"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
