"""A10 karar tabani genisletme - ON-KAYIT §1'in MEKANIK uygulamasi.

docs/architecture/A10_ONKAYIT.md §1.1 kurali:
    O-A  arac track'i var (en_uygun_arac_track secebiliyor)          [4I O1]
    O-B  secilen track'in ILK 60 gorunur karesi ARDISIK
         (gercek span = 60, maks bosluk = 1)                          [A9 1-EK]
    O-C  native >= 1280x720 VE arkaplan_hucresi gecerli bir
         1280x720 bos hucre bulabiliyor                               [A5.2/A7]
    O-D  ayni uav##### onekinden en cok bir dizi
    -> gecenler DIZI ADINA gore artan siralanir, ILK 3 alinir.

Takipci/dedektor davranisina BAKILMAZ. Hicbir basari olcusu kullanilmaz.

Kaynak: VisDrone2019-MOT-test-dev.zip (HuggingFace vanthanh/VisDrone2019-MOT).
Zip'in tamami indirilmez; HTTP Range ile yalnizca gereken uyeler cekilir.
"""
import io
import os
import sys
import urllib.request
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from veri.etiket import vid_oku, en_uygun_arac_track, track_bul   # noqa: E402

ZIP_URL = ("https://huggingface.co/datasets/vanthanh/VisDrone2019-MOT/"
           "resolve/main/VisDrone2019-MOT-test-dev.zip")
KOK_ICI = "VisDrone2019-MOT-test-dev"
HEDEF = os.path.join(ROOT, "data", "datasets", "visdrone_vid")
SENSOR = (1280, 720)
N_KARE = 60
SECILECEK = 3
UA = {"User-Agent": "curl/8", "Accept": "*/*"}


class UzakDosya(io.RawIOBase):
    """HTTP Range destekli dosya-benzeri nesne; zipfile bunun uzerinden calisir."""

    def __init__(self, url, blok=1 << 20):
        self.url, self.pos, self.blok = url, 0, blok
        self.onbellek, self.indirilen = {}, 0
        r = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(r, timeout=60) as f:
            self.boyut = int(f.headers["Content-Length"])

    def _istek(self, bas, son):
        r = urllib.request.Request(self.url, headers={**UA, "Range": f"bytes={bas}-{son}"})
        for deneme in range(4):
            try:
                with urllib.request.urlopen(r, timeout=180) as f:
                    d = f.read()
                self.indirilen += len(d)
                return d
            except Exception:
                if deneme == 3:
                    raise
        return b""

    def seekable(self):
        return True

    def readable(self):
        return True

    def seek(self, off, whence=0):
        self.pos = (off if whence == 0 else
                    self.pos + off if whence == 1 else self.boyut + off)
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.boyut - self.pos
        n = min(n, self.boyut - self.pos)
        if n <= 0:
            return b""
        bas, son = self.pos, self.pos + n - 1
        ilk, sonb = bas // self.blok, son // self.blok
        parcalar = []
        for b in range(ilk, sonb + 1):
            if b not in self.onbellek:
                bb = b * self.blok
                self.onbellek[b] = self._istek(bb, min(bb + self.blok - 1, self.boyut - 1))
                if len(self.onbellek) > 96:
                    for k in list(self.onbellek)[:32]:
                        if k != b:
                            del self.onbellek[k]
            parcalar.append(self.onbellek[b])
        veri = b"".join(parcalar)
        self.pos = son + 1
        return veri[bas - ilk * self.blok:][:n]


def arkaplan_hucresi(kutular, W, H, cw, ch):
    """gazebo/bench_a52_kucuk_hedef.py:arkaplan_hucresi ile AYNI kural.

    Burada yeniden yazilmasinin tek sebebi: o modul YOLO/torch import ediyor ve
    taban secimi icin dedektor gerekmiyor. Kural birebir kopyalandi.
    """
    mc = np.mean([[g[0] + g[2] / 2.0, g[1] + g[3] / 2.0] for g in kutular], axis=0)
    en_iyi, en_uzak = None, float("inf")
    for y in range(0, max(1, H - ch + 1), ch // 2):
        for x in range(0, max(1, W - cw + 1), cw // 2):
            if y + ch > H or x + cw > W:
                continue
            if any(not (g[0] + g[2] < x or g[0] > x + cw or
                        g[1] + g[3] < y or g[1] > y + ch) for g in kutular):
                continue
            d = float(np.hypot(x + cw / 2.0 - mc[0], y + ch / 2.0 - mc[1]))
            if d < en_uzak:
                en_iyi, en_uzak = (x, y), d
    return en_iyi, round(en_uzak, 1)


def main():
    d = UzakDosya(ZIP_URL)
    z = zipfile.ZipFile(d)
    adlar = z.namelist()
    diziler = sorted({a.split("/")[2] for a in adlar
                      if a.startswith(f"{KOK_ICI}/sequences/") and a.count("/") >= 3
                      and a.split("/")[2]})
    print(f"test-dev dizileri: {len(diziler)}")

    kayit = []
    for dz in diziler:
        sat = {"dizi": dz}
        # ---- O-A
        ham = z.read(f"{KOK_ICI}/annotations/{dz}.txt").decode("utf-8", "replace")
        gecici = os.path.join("/tmp", f"a10_{dz}.txt")
        open(gecici, "w").write(ham)
        kareler = vid_oku(gecici)
        os.remove(gecici)
        try:
            tid = en_uygun_arac_track(kareler)
        except Exception as e:
            sat.update({"O_A": False, "not": str(e)[:60]})
            kayit.append(sat)
            print(f"  {dz:<24} O-A RED ({str(e)[:40]})")
            continue
        sat.update({"O_A": True, "track": int(tid)})
        # ---- O-B  (kareleri_topla semantigi: track_bul uyeligi = gorunur)
        hk = track_bul(kareler, tid)
        kl = sorted(hk)
        if len(kl) < N_KARE:
            sat.update({"O_B": False, "gorunur": len(kl)})
            kayit.append(sat)
            print(f"  {dz:<24} O-B RED (gorunur {len(kl)} < 60)")
            continue
        ilk = kl[:N_KARE]
        span = ilk[-1] - ilk[0] + 1
        bosluk = int(max(np.diff(ilk))) if len(ilk) > 1 else 0
        sat.update({"gorunur": len(kl), "span": int(span), "maks_bosluk": bosluk,
                    "O_B": bool(span == N_KARE and bosluk == 1)})
        if not sat["O_B"]:
            kayit.append(sat)
            print(f"  {dz:<24} O-B RED (span {span}, bosluk {bosluk})")
            continue
        # ---- O-C
        kare1 = z.read(f"{KOK_ICI}/sequences/{dz}/0000001.jpg")
        import cv2
        img = cv2.imdecode(np.frombuffer(kare1, np.uint8), cv2.IMREAD_COLOR)
        H, W = img.shape[:2]
        kutular = [hk[k].kutu for k in ilk]
        hucre, uzaklik = arkaplan_hucresi(kutular, W, H, *SENSOR)
        kut = np.array(kutular)
        sat.update({"native": f"{W}x{H}",
                    "O_C": bool(W >= SENSOR[0] and H >= SENSOR[1] and hucre is not None),
                    "hucre": hucre, "hucre_uzaklik": uzaklik,
                    "gt_w_ort": round(float(kut[:, 2].mean()), 1),
                    "gt_h_ort": round(float(kut[:, 3].mean()), 1)})
        kayit.append(sat)
        print(f"  {dz:<24} track={tid:<4} {W}x{H}  gorunur={len(kl):<4} "
              f"span={span} bosluk={bosluk}  hucre={hucre}  "
              f"{'GECTI' if sat['O_C'] else 'O-C RED'}")

    gecen = [s for s in kayit if s.get("O_A") and s.get("O_B") and s.get("O_C")]
    # ---- O-D: onek basina bir dizi, sonra dizi adina gore artan
    gecen.sort(key=lambda s: s["dizi"])
    secili, onekler = [], set()
    for s in gecen:
        on = s["dizi"].split("_")[0]
        if on in onekler:
            s["O_D"] = False
            continue
        s["O_D"] = True
        onekler.add(on)
        if len(secili) < SECILECEK:
            secili.append(s)

    print(f"\nO-A..O-C gecen: {len(gecen)} · O-D sonrasi secilen ilk {SECILECEK}:")
    for s in secili:
        print(f"  {s['dizi']}  track={s['track']}  {s['native']}  "
              f"gt~{s['gt_w_ort']}x{s['gt_h_ort']}")

    # ---- indirme
    os.makedirs(os.path.join(HEDEF, "sequences"), exist_ok=True)
    os.makedirs(os.path.join(HEDEF, "annotations"), exist_ok=True)
    for s in secili:
        dz = s["dizi"]
        hedef_dz = os.path.join(HEDEF, "sequences", dz)
        if os.path.isdir(hedef_dz) and len(os.listdir(hedef_dz)) > 0:
            print(f"  {dz} zaten var, atlaniyor")
            continue
        os.makedirs(hedef_dz, exist_ok=True)
        uyeler = sorted(a for a in adlar
                        if a.startswith(f"{KOK_ICI}/sequences/{dz}/") and a.endswith(".jpg"))
        print(f"  {dz}: {len(uyeler)} kare indiriliyor...", flush=True)
        for i, u in enumerate(uyeler):
            open(os.path.join(hedef_dz, os.path.basename(u)), "wb").write(z.read(u))
            if (i + 1) % 100 == 0:
                print(f"     {i+1}/{len(uyeler)}  ({d.indirilen/1e6:.0f} MB)", flush=True)
        open(os.path.join(HEDEF, "annotations", f"{dz}.txt"), "wb").write(
            z.read(f"{KOK_ICI}/annotations/{dz}.txt"))

    import json
    json.dump({"kural": "docs/architecture/A10_ONKAYIT.md §1.1",
               "kaynak": ZIP_URL, "tarama": kayit,
               "secilen": [{"dizi": s["dizi"], "track": s["track"],
                            "native": s["native"]} for s in secili],
               "indirilen_MB": round(d.indirilen / 1e6, 1)},
              open(os.path.join(ROOT, "cikti", "a10_taban_secim.json"), "w"),
              indent=2, ensure_ascii=False)
    print(f"\ntoplam indirilen: {d.indirilen/1e6:.1f} MB")


if __name__ == "__main__":
    main()
