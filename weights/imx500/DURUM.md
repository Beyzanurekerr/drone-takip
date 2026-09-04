# IMX500 paketleme - durum (2026-09-04, bu PC'de)

**Sonuc: BASARISIZ - ama model/converter reddi degil, PC kaynak yetersizligi.**
Hicbir `.rpk`/`.onnx` ciktisi uretilemedi. Asagida tam olarak nereye kadar
gidildigi ve neden durdugu var - sayilar bu oturumda GERCEKTEN olculdu,
uydurulmadi.

## Model

`runs/a6/asamaB/weights/best.pt` - A6 final (UAVDT->VisDrone), YOLOv8n,
4 sinif (car/van/truck/bus). Baska model denenmedi, degistirilmedi.

## Kurulum (calisiyor, tekrar kullanilabilir)

- `weights/imx500/../.venv_imx500/` (repo disi degil, `~/drone_takip/.venv_imx500`) -
  `virtualenv` ile (stdlib `venv` calismadi: `python3.10-venv` apt paketi yok,
  sudo sifre istiyor). Icinde: `imx500-converter[pt]==3.18.2`,
  `model-compression-toolkit==2.5.1`, `mct-quantizers==1.6.0`,
  `edge-mdt-cl==1.1.1`, `torch==2.5.1+cpu`, `torchvision==0.20.1+cpu`,
  `ultralytics==8.4.138`. Bu tam pin seti calisiyor (`pip check` temiz).
- **Gercek celiskiye dikkat:** ultralytics'in kendi `format=imx` yolu
  (`ultralytics/utils/export/imx.py`) `edge-mdt-cl<1.1.0` ister, ama
  `imx500-converter[pt]==3.18.2`'nin `uni-pytorch` bagimliligi
  `edge-mdt-cl~=1.1.0` ister - **bu ikisi ayni anda saglanamaz** (kesisim
  bos). `YOLO_AUTOINSTALL=False` ile ultralytics'in bunu otomatik "duzeltip"
  kurulumu bozmasi engellendi; `edge-mdt-cl==1.1.1` tarafi secildi (converter
  paketinin gercek ihtiyaci) ve is gordu.
- Java: `openjdk-21-jre` apt paketi de sudo gerektiriyordu - Adoptium'dan
  taşinabilir JDK 21.0.12.1 indirilip `~/drone_takip/.jdk/jdk-21.0.12.1+1/`
  altina acildi, `PATH`e eklendi. Ultralytics'in `java --version` kontrolu
  bunu kabul ediyor.
- Kalibrasyon: `weights/imx500/calib/` - VisDrone DET'in 548 goruntusunden
  `np.linspace` ile deterministik 200 kare (`calib.yaml`, sembolik linkler).

## Nereye kadar gidildi

`yolo`/ultralytics'in yerlesik `format=imx` yolu kullanildi (Sony converter'ini
dogrudan CLI'dan cagirmak yerine - ayni MCT+converter zincirini calistiriyor,
"imx500-converter[pt]>=3.17.3"i kendi de gerektiriyor). Hem **imgsz=640** hem
**imgsz=320** icin, IKI kosumda da AYNI noktada oldu:

1. ONNX'e cikis (fused, 3 006 428 parametre, 8.1 GFLOPs) - OK.
2. `model_compression_toolkit 2.5.1` ile PTQ: 200 kalibrasyon goruntusu
   uzerinde istatistik toplama (200/200 tamamlandi) + kuantizasyon
   parametresi hesaplama (191/191 tamamlandi) - OK, hata yok.
3. sdspconv'un bellek/katman atama cozucusu (Coin-OR CBC, ILP): "Result -
   Optimal solution found" - **cozucu basariyla bitiyor**.
4. Hemen sonrasinda, cikti dosyasi yazilmadan **is OOM-killer tarafindan
   SIGKILL ile olduruluyor** (exit 137). `dmesg` dogrulandi:
   `oom-kill: ... task=python3 ... total-vm:11056544kB anon-rss:6769044kB`.
   Bu, farkli sanslarla DEGIL, **3 ayri denemede** (640 bir kez, 320 iki kez)
   **hep ayni asamada** oldu - flaky degil, tekrarlanabilir tavan.

Bu makine (WSL2) toplam **7.6 GiB RAM** + 2 GiB swap'a sahip; sureç
~6.7 GB RSS'e ulasip oldugu anda bosta sadece ~1 GB vardi. **imgsz=320'nin
640'tan daha az RAM'e ihtiyaci OLMADI** - darbogaz girdi boyutundan degil,
tum agin/kuantize temsilinin bellekte tutulup sdspconv'a Java altsurecinin
de eklenmesinden kaynaklaniyor gibi gorunuyor (kesin profil cikarilmadi -
zaman butcesi asildi).

## Neden "converter reddetti" DEGIL

MCT/uni katmani hicbir op/katmani reddetmedi; kuantizasyon istatistikleri
ve parametreleri hatasiz tamamlandi; ILP cozucu de "Optimal solution found"
dedi. Hata calisma zamaninda, cikti yazilmadan hemen once, isletim
sistemi seviyesinde (OOM). Bu yuzden RAPOR'a "model uyumsuz" DEGIL,
"bu PC'de bellek yetmedi" olarak gecmeli.

## Onerilen sonraki adim

Ayni kurulum (venv + JDK zaten hazir, tekrar kurulum gerekmez) **>=16 GB
RAM'li bir makinede/VM'de** tekrar denenebilir. WSL2 ise Windows tarafinda
`.wslconfig`'e `memory=16GB` yazip `wsl --shutdown` ile yeniden baslatilirsa
ayni PC'de de denenebilir - bu oturumdan yapilamadi (Windows tarafi,
oturum disi).

## PC'de yaklasik mAP karsilastirmasi (madde 5)

**Denenmedi.** Hicbir kuantize model/dosya uretilemedigi icin karsilastirilacak
bir cikti yok. ONNX Runtime int8 kuantizasyonuyla ayri bir "yaklasik" yol
denenebilirdi ama bu, IMX500'un gercek Sony MCT/sdspconv zincirinden FARKLI
bir yoldur ve gorevin asil sorusuna (IMX500 paketleme calisiyor mu) cevap
vermez - zaman/kaynak butcesi bu ayri yola degil, asil yolu bitirmeye
ayrildi.
