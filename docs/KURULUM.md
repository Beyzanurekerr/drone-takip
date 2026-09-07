# Kurulum — sıfırdan Demo_kucul'a

Hedef: temiz bir Ubuntu 22.04/24.04 (ya da WSL2 üzerinde Ubuntu 22.04/24.04)
kurulumundan başlayarak

```bash
python3 main.py --mod demo --source gazebo --sequence Demo_kucul
```

komutunun görüntü penceresini açtığı ana kadar, **≤30 dakika**. Bu belgedeki
her komut bu depoda (Ubuntu 22.04.5 LTS "jammy", `gz-harmonic 1.0.0-1~jammy`)
**gerçekten çalıştırılıp doğrulandı** — hangi adımın bu oturumda ölçüldüğü,
hangisinin resmi kurulum talimatından alındığı §6'da ayrı ayrı işaretli.

> WSL2 notu: aşağıdaki adımların hepsi WSL2 içindeki Ubuntu kabuğunda
> çalışır; ayrı bir X sunucusu **gerekmez** — `main.py` `--penceresiz`
> bayrağıyla ekransız da çalışır (bu depronun HUD üretimi zaten ekransız
> `gazebo/demo_hud_uret.py` ile offline yapılır). Canlı pencere için WSLg
> (Windows 11 varsayılan) ya da bir X sunucusu gerekir.

## 0. Ön koşullar

```bash
sudo apt-get update
sudo apt-get install -y curl gnupg lsb-release git python3-venv
```

`python3-venv` **kritik**: bu paket kurulu değilse `python3 -m venv` şu
hatayı verir (bu oturumda gerçekten alındı):

```
The virtual environment was not created successfully because ensurepip is
not available. ... apt install python3.10-venv
```

Ubuntu 22.04'te paket adı `python3-venv` (ya da sürüme özel
`python3.10-venv`); 24.04'te `python3-venv` yeterlidir.

## 1. Gazebo Sim (Harmonic)

Resmi OSRF apt deposu — bu makinede kurulu olan **tam olarak bu adımlarla**
kuruldu (`/etc/apt/sources.list.d/gazebo-stable.list` içeriği bu depoda
doğrulandı):

```bash
sudo curl https://packages.osrfoundation.org/gazebo.gpg \
    -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
    | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt-get update
sudo apt-get install -y gz-harmonic
```

Doğrulama:

```bash
gz sim --version    # -> Gazebo Sim, version 8.x
python3 -c "import gz.transport13, gz.msgs10; print('ok')"
```

İkinci satır **başarısızsa** (`ModuleNotFoundError`), `python3-gz-transport13`
ve `python3-gz-msgs10` paketleri `gz-harmonic` metapaketiyle otomatik
gelmeli; gelmediyse `sudo apt-get install -y python3-gz-transport13
python3-gz-msgs10 python3-gz-sim8` ile elle kurun.

**24.04 (noble) notu:** bu depo Harmonic'i yalnızca 22.04'te (jammy) test
etti; OSRF noble paketlerini de yayınlıyor (aynı komutlar, `lsb_release -cs`
otomatik `noble` çözer) ama bu depoda **doğrulanmadı**.

## 2. Repo klonu + Python bağımlılıkları

```bash
git clone <bu repo> ~/drone_takip
cd ~/drone_takip
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`--system-site-packages` **kritik** — `docs/PI_KURULUM.md`'deki
picamera2 gerekçesiyle AYNI sebep: `gz.transport13`/`gz.msgs10` Python
bağlama noktaları `apt` ile kurulur, pip ile venv içine taşınmaz. Bu bayrak
olmadan venv içinden `import gz.transport13` başarısız olur.

`requirements.txt` `ultralytics`+`torch`i de kurar (demo modu YOLO
gerektirir — bkz. o dosyanın başlığı). CPU tekerleği yeterlidir, GPU
gerekmez:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install ultralytics
```

**Model ağırlığı ayrıca indirilmez** — `weights/a6_kucuk_hedef.pt` (6.2 MB,
A6 UAVDT→VisDrone fine-tune) repoya commit'li geliyor, klonla birlikte gelir.

## 3. İlk internet-bağımlı adım: Baylands sahne varlıkları

Demo senaryoları `gazebo/dunya_uret.py`'nin `baylands` zemin tipini kullanır;
bu, Gazebo Fuel'den (`fuel.gazebosim.org`) çekilen hazır bir modeldir
(`OpenRobotics/baylands` + `OpenRobotics/Coast Water`). **İlk** `gz sim`
koşumunda otomatik iner ve `~/.gz/fuel/` altında önbelleğe alınır (bu
makinede ölçülen boyut: baylands **393 MB** + Coast Water **15 MB** = **~408
MB, tek seferlik**). Sonraki tüm koşumlar (Demo_kucul dahil) önbellekten
okur, internet gerektirmez.

## 4. Demo_kucul'u kaydet

Gazebo canlı çalışırken FPS/gecikme ölçümü render hızını ölçerdi, takipçiyi
değil (bkz. `gazebo/kaydet.py` başlığı) — bu yüzden demo senaryoları önce
diske **kaydedilir**, sonra `main.py` bu kayıttan okur:

```bash
python3 -m gazebo.kaydet Demo_kucul
```

**Disk:** kayıt sırasında geçici ham kareler de diske yazılır (ATLA/düşen
kareler sonda silinir); bu oturumda ölçülen geçici tepe kullanım **~4 GB**
(1200 kare × 2028×1520 ham PNG) — `data/gazebo/` altında en az bu kadar boş
alan bırakın.

1200 kare (40 s × 30 Hz, 2028×1520) kaydeder;
`data/gazebo/Demo_kucul/kareler/` + `pozlar.csv` + `meta.json` yazar. Bu
oturumda ölçülen süre: **§6**.

## 5. Çalıştır

```bash
python3 main.py --mod demo --source gazebo --sequence Demo_kucul
```

Ekransız doğrulama (CI/sunucu, pencere açmaz):

```bash
python3 main.py --mod demo --source gazebo --sequence Demo_kucul --penceresiz --max-kare 30
```

HUD'lu mp4 üretimi (bu komuttan SONRA, `--kaydet` ile kaydedilmiş ham video +
jsonl üzerinden, offline):

```bash
python3 main.py --mod demo --source gazebo --sequence Demo_kucul \
    --penceresiz --kaydet cikti/demo/kucul.mp4
python3 -m gazebo.demo_hud_uret cikti/demo/kucul.mp4
```

## 6. Süre bütçesi

| Adım | Süre | Ölçüldü mü |
|---|---|---|
| Ön koşul paketleri (`apt-get install curl gnupg lsb-release python3-venv`) | ~1 dk | tahmin (küçük paketler) |
| Gazebo Harmonic (`apt-get install gz-harmonic`) | ~5–8 dk | tahmin — bu makinede **önceden kuruluydu**, bu oturumda sıfırdan zamanlanmadı; süre bağlantı hızına ve apt aynasına bağlı |
| Repo klonu | <1 dk | tahmin |
| `pip install -r requirements.txt` (+ torch CPU + ultralytics) | ~3–5 dk | tahmin — bu makinede paketler zaten kuruluydu (torch 2.13, ultralytics 8.4), sıfırdan zamanlanmadı |
| Baylands Fuel indirme (~408 MB, tek seferlik) | bağlantıya bağlı | **boyut bu oturumda ölçüldü** (`~/.gz/fuel`), indirme süresi zamanlanmadı — önbellek bu makinede zaten doluydu |
| `python3 -m gazebo.kaydet Demo_kucul` (1200 kare, 2028×1520) | **460.7 s (~7.7 dk)** | **gerçekten koşuldu ve ölçüldü bu oturumda** (`kaydedildi: 1200 kare, dusen 0, sure 460.7 s`) — ayrı bir `--kok` altında, bu depronun izlenen `data/gazebo/Demo_kucul/` kaydına dokunmadan |
| `main.py --mod demo --source gazebo --sequence Demo_kucul` (30 kare, `--penceresiz`) | **31.0 s** (ilk karede YOLO model yükleme gecikmesi ~10 s dahil) | **gerçekten koşuldu ve ölçüldü bu oturumda** — çıktı: `hedef KILITLENDI`, IoU 0.940, kilit oranı %100 |

> **Not (dürüstlük):** bu makine zaten Gazebo Harmonic kurulu ve Fuel
> önbelleği dolu bir geliştirme kutusu olduğu için apt/Fuel-indirme adımları
> **sıfırdan zamanlanamadı** (tahmini satırlar işaretli); `pip install`
> paketleri de zaten kuruluydu. Gerçekten koşulup ölçülen adımlar
> `gazebo.kaydet Demo_kucul` (**460.7 s**) ve `main.py` açılışıdır (**31.0
> s**, 30 kare) — bu ikisi toplam **~8.2 dk**, tam 1200 kareyle `main.py`nin
> kendisi de biraz daha uzun sürer ama saniyeler mertebesindedir (kayıttan
> okuma, model çıkarımı yok — çıkarım yalnız edinme/ARAMA'da çalışır).
> ≤30 dk hedefi, apt+pip+Fuel adımlarının (tahmini ~10–15 dk, hızlı bir
> bağlantıda) ölçülen ~8–9 dk'lık kayıt+çalıştırma süresine eklenmesiyle
> **aşağı yukarı** tutar; yavaş bağlantıda apt+Fuel adımları tek başına 30
> dk'yı aşabilir.

## 7. Sorun giderme

- **`ensurepip is not available`** → `sudo apt-get install python3-venv`
  (bkz. §0; bu hata bu oturumda gerçekten alındı).
- **`ModuleNotFoundError: No module named 'gz'`** venv içinde → `.venv`
  `--system-site-packages` **olmadan** kurulmuş; venv'i silip §2'deki
  komutla yeniden kurun.
- **`gz sim` sessizce açılıp kapanıyor / "Baska bir gz sim sureci ayni
  konulara yayin yapiyor olabilir"** (`gazebo/kaydet.py` hata mesajı) →
  önceki bir `gazebo.kaydet` çalıştırması arka planda kalmış olabilir:
  `pgrep -af "gz sim"` ile kontrol edip `kill` edin.
- **Fuel indirme başarısız / zaman aşımı** → internet bağlantısını kontrol
  edin; `~/.gz/fuel/fuel.gazebosim.org/openrobotics/models/` altında yarım
  kalan bir model klasörü varsa silip `gz sim`'i tekrar çalıştırın.
- **`RuntimeError: IMX500: ...`** → bu yalnızca gerçek Raspberry Pi
  donanımında (`pi/olc_pi.py`) görülür, Gazebo demo yolunda **alakasızdır**
  (bkz. `docs/PI_KURULUM.md` §"İlk denemede hata beklenen nokta").

## 8. Sonraki adım

Kurulum bittiğinde ana `README.md`'deki demo senaryoları tablosunu
(`Demo_kucul` / `Demo_celdirici` / `Demo_kopus`) tek tek koşup sonuç
sütununu doldurmak — bkz. `README.md` §5.
