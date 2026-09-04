# Pi kurulum notu

Donanım (Pi Zero 2 W + Pi AI Camera / IMX500) elde olmadan önce yazıldı; amaç
donanım gelince **1 saat içinde ilk ölçüme başlamak**. Adımlar Raspberry Pi'nin
resmî IMX500/AI Camera belgeleriyle tutarlı tutuldu, ama bu depoda **hiçbiri
gerçek donanımla denenmedi** — `pi/olc_pi.py` içindeki IMX500 bölümü de aynı
sebeple işaretli (bkz. o dosyanın docstring'i).

## 1. İşletim sistemi

- **64-bit Raspberry Pi OS** (Bookworm veya üzeri) — Raspberry Pi Imager ile
  yazılır. 32-bit ile IMX500/picamera2 yığını desteklenmez.
- İlk açılışta `raspi-config` ile: kamera arayüzünü etkinleştir, SSH'ı aç
  (aşağıda), locale/saat dilimi ayarla.
- `sudo apt update && sudo apt full-upgrade -y` — IMX500 firmware ve
  picamera2 sürümleri hızlı değiştiği için güncel kalmak önemli.

## 2. IMX500 / AI Camera yığını

```
sudo apt install -y imx500-all
sudo reboot
```

`imx500-all`: sensör firmware'i, `imx500-tools` (cihaz üstü paket
doğrulama/yükleme araçları) ve gerekli `libcamera`/`rpicam-apps` bağımlılıklarını
kurar. Reboot **zorunlu** (sensör firmware'i açılışta yüklenir).

```
sudo apt install -y python3-picamera2 --no-install-recommends
```

picamera2 çoğu Raspberry Pi OS imajında ön yüklü gelir; gelmediyse yukarıdaki
komutla kurulur. `--no-install-recommends` GUI/Qt bağımlılıklarını atlar
(başsız/`--penceresiz` kullanım için yeterli, bu proje zaten GUI'siz çalışıyor
— bkz. `requirements.txt` başındaki not).

Doğrulama (kamera algılandı mı):

```
rpicam-hello --list-cameras
```

Çıktıda `imx500` sensör adı ve desteklenen modları görünmeli. Görünmüyorsa
kabloyu (mini-CSI, Zero 2 W'nin küçük konnektörü — **bu adaptör bu projede
doğrulanmadı**, bkz. `docs/architecture/A5_INFERENCE_MIMARISI_KARSILASTIRMA.md`
§0b) ve `imx500-all` kurulumunu/reboot'u kontrol et.

## 3. SSH

Imager'ın kendi SSH etkinleştirme seçeneği (kullanıcı adı/parola veya
public-key) en az sürtünmeli yol; `raspi-config` → `Interface Options` → `SSH`
alternatif. Statik bir mDNS adı (`raspberrypi.local`) genelde yeterli;
birden fazla Pi varsa `sudo raspi-config` → `System Options` → `Hostname` ile
ayırt edici bir isim ver.

```
ssh pi@raspberrypi.local
```

## 4. Repo klonu ve bağımlılıklar

```
git clone <bu repo> ~/drone_takip
cd ~/drone_takip
python3 -m venv --system-site-packages .venv   # --system-site-packages: picamera2 sistem paketi, venv'e taşınmaz
source .venv/bin/activate
pip install -r requirements.txt
```

`--system-site-packages` **kritik**: `picamera2`/`libcamera` Python binding'leri
`apt` ile kurulur ve pip ile venv içine taşınamaz (C uzantıları donanım
sürücüsüne bağlı). Bu bayrak olmadan venv içinden `import picamera2` başarısız
olur.

IMX500 paketlenmiş model dosyaları (`weights/imx500/a6_640.rpk`,
`weights/imx500/a6_320.rpk`) PC tarafında üretilip repoya commit'lendi
(adım: bkz. proje kökü `weights/imx500/`); Pi'de ayrıca dönüştürme
**gerekmiyor**, dosyalar klonla birlikte gelir.

## 5. `olc_pi.py` çalıştırma

```
cd ~/drone_takip
source .venv/bin/activate
python3 pi/olc_pi.py
```

Varsayılan davranış: takip çekirdeği (ego/DCF/tespit) + IMX500 (tam kare ve
sensör-ROI) + 5 dakikalık CPU sıcaklık/throttle kaydı — hepsi tek komutla,
`pi/sonuc.json`'a yazılır. Toplam çalışma süresi ~6-7 dakika (çoğu, termal
kaydın 5 dakikası).

Faydalı bayraklar:

```
python3 pi/olc_pi.py --imx500-sure-s 10 --termal-sure-s 60   # hızlı duman testi
python3 pi/olc_pi.py --sensor-roi 1014,760,2028,1520          # 320 modeli icin ozel ROI
```

Hata veren adım olursa script **durmaz**, o adımı `{"durum": "HATA", "hata": "..."}`
olarak JSON'a yazıp devam eder (bkz. `pi/olc_pi.py` docstring — sayı
uydurmama disiplini). `sonuc.json`'daki her `HATA`/`ATLANDI` alanı, ilgili
tabloyu `docs/PI_OLCUM.md`'de doldururken okunmalı.

### İlk denemede hata beklenen nokta

`pi/olc_pi.py`'nin `imx500_olc()` fonksiyonu, `picamera2.devices.imx500`
kaynak kodu **okunarak** yazıldı ama **hiç çalıştırılmadı** (donanım yok).
Muhtemel ilk-deneme sürtünmeleri:

- `IMX500(model_yolu)` bir `/dev/v4l-subdev*` sürücü düğümü arar; `imx500-all`
  kurulu değilse veya reboot yapılmadıysa `RuntimeError: IMX500: Requested
  camera dev-node not found` verir.
- `Picamera2(imx500.camera_num)` — kamera modülü fiziksel olarak takılı/
  algılanmış olmalı (`rpicam-hello --list-cameras` adım 2'deki doğrulama).
- `picamera2` API'si sürüm sürüm değişiyor; hata `AttributeError`/`TypeError`
  ise ilk yapılacak şey kurulu `picamera2` sürümünün örnek dizinine
  (`raspberrypi/picamera2` deposunun o anki `examples/imx500/` dizini —
  bu yazıldığı sırada üst düzey `examples/` dizini depoda yoktu, taşınmış
  olabilir) bakmaktır.

## 6. CPU sıcaklık / throttle

`vcgencmd` Raspberry Pi OS'te ön yüklü gelir, ekstra kurulum gerekmez.
`pi/olc_pi.py` bunu otomatik kullanır; `vcgencmd` bulunamazsa (örn. konteyner
içinde çalıştırılıyorsa) ilgili bölüm `ATLANDI` olarak işaretlenir.

## 7. Sonuçları geri taşıma

```
scp pi@raspberrypi.local:~/drone_takip/pi/sonuc.json ./pi/sonuc_pi.json
```

`docs/PI_OLCUM.md`'deki TODO hücreleri bu dosyadan elle doldurulur (script
şablonu otomatik doldurmaz — sayı disiplini gereği hangi sayının hangi
koşumdan geldiği belgeye elle, kaynağıyla birlikte yazılmalı).
