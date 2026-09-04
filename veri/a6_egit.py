"""A6 egitim kosucusu. Ultralytics'i Python API'siyle kosar, epoch surelerini ve
kaynak kullanimini OLCER (tahmin etmez). takip/ ve A5 kodu okunmaz bile.

Kullanim:
  python3 veri/a6_egit.py warmup            # Asama A, 2 epoch, sure olcumu
  python3 veri/a6_egit.py asamaA            # Asama A, 100 epoch
  python3 veri/a6_egit.py asamaB            # Asama B, 150 epoch (A'nin best.pt'si)
  python3 veri/a6_egit.py kontrol           # kontrol kolu: COCO -> VisDrone
"""
import json
import os
import sys
import threading
import time

KOSUMLAR = {
    # ad: (model, data, ortak_olmayan_parametreler)
    "warmup": ("weights/yolov8n.pt", "data/a6/uavdt_pretrain/data.yaml",
               dict(epochs=2, lr0=0.001, close_mosaic=0)),
    # GPU olcumu: CPU warm-up'i ile BIREBIR ayni parametreler, tek fark cihaz.
    # Ayri isim, cunku CPU referans sonuclari (cikti/a6_egitim_warmup.json ve
    # runs/a6/warmup) korunacak.
    "warmup_gpu": ("weights/yolov8n.pt", "data/a6/uavdt_pretrain/data.yaml",
                   dict(epochs=2, lr0=0.001, close_mosaic=0)),
    "asamaA": ("weights/yolov8n.pt", "data/a6/uavdt_pretrain/data.yaml",
               dict(epochs=100, lr0=0.001, close_mosaic=10)),
    "asamaB": (os.path.abspath("runs/a6/asamaA/weights/best.pt"), "data/a6/visdrone_finetune/data.yaml",
               dict(epochs=150, lr0=0.0005, close_mosaic=10)),
    "kontrol": ("weights/yolov8n.pt", "data/a6/visdrone_finetune/data.yaml",
                dict(epochs=150, lr0=0.0005, close_mosaic=10)),
}

# Kabul edilmis plandan gelen ORTAK parametreler - kollar arasinda DEGISMEZ.
ORTAK = dict(imgsz=640, batch=16, optimizer="AdamW", lrf=0.01, cos_lr=True,
             warmup_epochs=3, patience=30, mosaic=1.0, scale=0.5,
             fliplr=0.5, flipud=0.5, degrees=180.0, perspective=0.0,
             device="cuda", workers=4, seed=0, deterministic=True,
             val=True, plots=True,
             # ultralytics 'project'i kendi runs_dir'ine gore cozuyor; goreli
             # verilince cikti runs/detect/runs/a6/... altina yuvalaniyor ve
             # Asama B'nin best.pt yolu tutmuyor. Mutlak yol veriliyor.
             project=os.path.abspath("runs/a6"))


class Kaynak:
    """Egitim boyunca RSS ve CPU ornekler (tahmin degil, olcum)."""

    def __init__(self, aralik=10.0):
        self.aralik, self.dur = aralik, False
        self.rss, self.cpu = [], []
        self._t = threading.Thread(target=self._kos, daemon=True)

    def _kos(self):
        try:
            import psutil
            p = psutil.Process(os.getpid())
            p.cpu_percent(None)
            while not self.dur:
                self.rss.append(p.memory_info().rss / 1e9)
                self.cpu.append(p.cpu_percent(None))
                time.sleep(self.aralik)
        except Exception:
            while not self.dur:                      # psutil yoksa /proc
                try:
                    with open(f"/proc/{os.getpid()}/status") as f:
                        for s in f:
                            if s.startswith("VmRSS:"):
                                self.rss.append(int(s.split()[1]) / 1e6)
                                break
                except Exception:
                    pass
                time.sleep(self.aralik)

    def __enter__(self):
        self._t.start(); return self

    def __exit__(self, *_):
        self.dur = True; self._t.join(timeout=2)

    def ozet(self):
        import numpy as np
        d = {}
        if self.rss:
            d["rss_gb_max"] = round(float(np.max(self.rss)), 2)
            d["rss_gb_ort"] = round(float(np.mean(self.rss)), 2)
        if self.cpu:
            d["cpu_yuzde_ort"] = round(float(np.mean(self.cpu[1:] or self.cpu)), 1)
            d["cpu_yuzde_max"] = round(float(np.max(self.cpu)), 1)
        d["ornek"] = len(self.rss)
        return d


def main():
    ad = sys.argv[1] if len(sys.argv) > 1 else "warmup"
    if ad not in KOSUMLAR:
        raise SystemExit(f"bilinmeyen kosum: {ad} (secenekler: {list(KOSUMLAR)})")
    model_yolu, veri, ek = KOSUMLAR[ad]
    if not os.path.exists(model_yolu):
        raise SystemExit(f"baslangic agirligi yok: {model_yolu}")

    import torch
    if ORTAK["device"] == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA istendi ama torch.cuda.is_available() False. "
                         "Sessizce CPU'ya DUSULMEZ; egitim baslatilmadi.")

    from ultralytics import YOLO
    sureler = []
    kayit = {"kosum": ad, "model": model_yolu, "veri": veri,
             "parametreler": {**ORTAK, **ek, "name": ad}}

    model = YOLO(model_yolu)
    durum = {"t": None}

    def epoch_basi(tr):
        durum["t"] = time.perf_counter()

    def epoch_sonu(tr):
        if durum["t"] is not None:
            sureler.append(round(time.perf_counter() - durum["t"], 2))
            print(f"  [OLCUM] epoch {len(sureler)} suresi: {sureler[-1]:.2f} s",
                  flush=True)

    model.add_callback("on_train_epoch_start", epoch_basi)
    model.add_callback("on_fit_epoch_end", epoch_sonu)

    t0 = time.perf_counter()
    with Kaynak() as k:
        sonuc = model.train(data=veri, name=ad, exist_ok=True, **{**ORTAK, **ek})
    kayit["toplam_sn"] = round(time.perf_counter() - t0, 2)
    kayit["epoch_sureleri_sn"] = sureler
    kayit["kaynak"] = k.ozet()
    try:
        kayit["metrikler"] = {kk: float(v) for kk, v in sonuc.results_dict.items()}
    except Exception as e:
        kayit["metrikler"] = f"okunamadi: {e}"
    kayit["kayit_dizini"] = str(sonuc.save_dir)
    for f in ("weights/best.pt", "weights/last.pt", "results.csv", "results.png"):
        kayit[f"var_{f.replace('/', '_')}"] = os.path.exists(
            os.path.join(str(sonuc.save_dir), f))

    os.makedirs("cikti", exist_ok=True)
    yol = f"cikti/a6_egitim_{ad}.json"
    json.dump(kayit, open(yol, "w"), indent=2, ensure_ascii=False)
    print(f"\nyazildi: {yol}")
    print(f"  toplam {kayit['toplam_sn']:.1f} s | epoch sureleri {sureler}")
    print(f"  kaynak: {kayit['kaynak']}")


if __name__ == "__main__":
    main()
