# Değişiklik Günlüğü

## Aşama 3 — VisDrone gerçek hava görüntüsü entegrasyonu (19 Ağustos 2026)

Gerçek drone görüntüsü + ground-truth destekli veri yolu eklendi. Takip
algoritmasına, simülatöre ve sim baseline'ına dokunulmadı.

### Eklendi

- **`veri/etiket.py`** — ortak GT temsili (`Etiket`) + VisDrone VID/DET
  annotation ayrıştırıcı. Satır numaralı hata mesajları, `olcekli()` ile
  downscale-tutarlı kutu ölçekleme, `en_uygun_arac_track()` (hareketli araç
  tercihli otomatik hedef seçimi)
- **`veri/visdrone.py`** — `VisDroneVidKaynak`, dizi keşfi, frame↔GT senkron
  doğrulaması, opsiyonel downscale
- **`visdrone_kiyasla.py`** — gerçek veri değerlendirmesi, `RAPOR_VISDRONE.md`
  üretir. Sim benchmark'ından tamamen ayrı
- **`test_visdrone.py`** — 21 test
- **`RAPOR_VISDRONE.md`** — ilk gerçek veri sonuçları
- `data/datasets/visdrone_vid/` (7 dizi, 2846 kare, 1.6 GB) ve
  `data/datasets/visdrone_det/` (548 görüntü, 81 MB) — **Git'e dahil değil**

### Değişti

- `kaynak.py` — fabrikaya `visdrone` dalı + veri kümesi parametreleri
- `main.py` — GT tabanlı hedef seçici, GT varsa kare kare metrik toplama
  (IoU / merkez hata / kilit / kurtarma), HUD'da IoU + merkez hata, GT kutusu
  ayrı stil (ince yeşil + "GT" etiketi)
- `docs/architecture/*`, `README.md`

### Değişmedi

`sim/` · `takip/` · `calistir.py` · `kiyasla.py` · `minboyut.py` ·
`tarama.py` · `RAPOR.md`

### İlk gerçek veri sonuçları

| dizi | track | kare | IoU | hassasiyet | kilit | p95 ms | FPS |
|---|---|---|---|---|---|---|---|
| uav0000117_02622_v | 23 | 343 | 0.701 | 100% | 100% | 5.90 | 311 |
| uav0000305_00000_v | 5 | 141 | 0.502 | 77% | 83% | 15.75 | 147 |
| uav0000137_00458_v | 12 | 221 | 0.215 | 34% | 83% | 16.35 | 183 |
| uav0000339_00001_v | 49 | 266 | 0.172 | 32% | 100% | 5.69 | 321 |
| uav0000182_00000_v | 127 | 335 | 0.095 | 34% | 34% | 18.62 | 114 |
| uav0000268_05773_v | 31 | 252 | 0.000 | 0% | 96% | 28.62 | 101 |
| **ORTALAMA** | | **1558** | **0.281** | **46%** | **83%** | **15.16** | **196** |

`uav0000086_00000_v` atlandı — dizide hiç araç sınıfı yok (sadece yaya).

### Bulgular

1. **Sim 0.742 → gerçek 0.281.** Klasik hat gerçek görüntüde belirgin şekilde
   zayıf. En iyi dizide (0.701) iyi çalışıyor, en kötüsünde tamamen kaybediyor.
2. **Yanlış güven doğrulandı.** `uav0000268_05773_v`'de kilit oranı %96 ama
   IoU 0.000 ve merkez hatası 409 px — sistem yanlış nesneyi takip ederken
   "KİLİTLİ" diyor. README'deki 1 numaralı bilinen sınır gerçek veride
   birebir görüldü.
3. **Eğik bakış varsayımı kırıyor.** VisDrone dizilerinin bir kısmı nadir
   değil, sokak seviyesine eğik bakıyor. `egomotion.py`'nin 2×3 afin düzlem
   modeli parallakslı 3B sahnede çalışmıyor; aday üretimi ağaç ve binalarda
   patlıyor.
4. **"En uzun track" hedef seçimi yanlıştı.** İlk denemede park halindeki bir
   minibüs seçildi (her karede kadrajda olduğu için) ve IoU 0.032 çıktı.
   Hareket ağırlıklı seçime geçildi.

---

## Aşama 2 — Görüntü kaynağı soyutlaması (19 Ağustos 2026)

Simülatör, MP4 video ve kamera aynı boru hattına kare veriyor; takip tarafı
görüntünün nereden geldiğini bilmiyor.

### Eklendi

- **`kaynak.py`** — görüntü kaynağı soyutlaması
  - `Kare` (dataclass): `goruntu`, `indeks`, `zaman`, `kaynak_adi`, `genislik`,
    `yukseklik`, `fps` + simülatöre özel `gt`, `gorunur`
  - `Kaynak` tabanı: `oku()`, `kapat()`, `acik_mi()`, `bilgi()`, `tur`;
    `for kare in kaynak` ve `with kaynak as k` desteği
  - `SimKaynak` — mevcut prosedürel simülatör, kare başına kusursuz GT ile.
    Döngü sırası `calistir.kos()` ile birebir aynı (kamera → step → render)
  - `VideoKaynak` — `cv2.VideoCapture`; MP4/AVI/MOV/MKV; dosya sonunda düzgün
    sonlanır
  - `KameraKaynak` — kamera index'i parametre; 3 üst üste okuma hatasında hata
  - `kaynak_olustur()` — akıllı dispatch: `sim`, `sim:test6`, `camera`,
    `camera:1`, doğrudan dosya yolu, ve eski `video` + `--input` biçimi
  - `KaynakHatasi` — dosya bulunamadı / açılamadı / desteklenmeyen kaynak
- **`main.py`** — kaynak-bağımsız çalıştırıcı
  - CLI: `--source`, `--input`, `--camera-id`, `--scenario`, `--cekirdek`,
    `--kaydet`, `--max-kare`, `--penceresiz`
  - OpenCV penceresi: durum, PSR, FPS, işlem gecikmesi, kaynak tipi, kare
    sayacı, çözünürlük; boşluk/n/q tuşları
  - Uçtan uca işlem gecikmesi + p50 / p95 / max ölçümü
  - Takılıp çıkarılabilir hedef seçici: `kos(..., hedef_secici=fn)`
- **`test_kaynak.py`** — 22 test; `pytest` olmadan da koşar
- **`data/videos/`, `data/datasets/`** — `.gitignore`'a alındı
- **`docs/architecture/`** — `ARCHITECTURE.md`, `BENCHMARK_BASELINE.md`,
  `CHANGELOG.md`

### Değişti

- `README.md` — "Görüntü kaynakları" bölümü, `data/` yapısı, gecikme özeti,
  hedef seçici sözleşmesi
- `.gitignore` — `data/videos/*`, `data/datasets/*`, `!data/*/.gitkeep`

### Değişmedi (bilinçli)

`sim/world.py` · `sim/senaryolar.py` · `takip/` altındaki **beş dosyanın
hiçbiri** · `calistir.py` · `kiyasla.py` · `minboyut.py` · `tarama.py`

`HedefTakip` zaten kaynak-bağımsızdı (yalnızca BGR alıyor); orada değişiklik
gerekmedi.

### Doğrulama

| Kontrol | Sonuç |
|---|---|
| Birim testleri | 22/22 geçti (`python3 test_kaynak.py` ve `pytest -q`) |
| `SimKaynak` mevcut davranışı koruyor mu | 12 kare `np.array_equal` ile birebir aynı |
| `main.py --source sim` | 80 kare, kilitlendi, p50 2.42 ms / p95 4.58 ms |
| `main.py --source cikti/test1.mp4` | 80 kare, kilitlendi, p50 2.37 ms / p95 4.10 ms |
| Eski biçim `--source video --input` | Çalışıyor |
| Hata yolları (5 senaryo) | Hepsi anlaşılır mesaj veriyor |
| Baseline (`kiyasla.py`) | 7 senaryonun tüm doğruluk metrikleri **değişmedi** |

### Bilinen sorunlar

- `cikti/*.mp4` dosyaları ham görüntü değildir; üzerlerine kutu ve yazı
  basılmıştır. Kaynak videosu olarak kullanılırsa HUD iki kat görünür.
- `data/videos/` boş — gerçek drone/aerial videosu henüz yok.
- `main.py`'deki otomatik hedef seçimi geçicidir (merkeze yakın + büyük aday);
  gerçek videoda hangi aracın kilitlendiği kullanıcı kontrolünde değil.

---

## Aşama 1 — Mevcut mimari analizi (19 Ağustos 2026)

Kod değişikliği yok; yalnızca analiz.

- 13 dosya / 2001 satır incelendi
- Katman katman mimari, ölçüm envanteri ve yeni mimariye hazırlık durumu
  çıkarıldı
- En büyük 5 teknik eksiklik belirlendi: kare kaynağı soyutlaması yok, MOT
  katmanı yok, detection sınıf-bilinçsiz, yanlış güven doğrulaması yok,
  benchmark simülatöre kilitli
- Uygulama sırası kararlaştırıldı (VideoSource → GT reader → harness → görsel
  arayüz → giriş katmanı → YOLO → MOT → target lock → hibrit → Pi)

---

## Aşama 0 — Baseline (13 Ağustos 2026)

`3b3f750` Drone havadan tek araç takibi: simülasyon + klasik CV boru hattı
`206449f` Canlı izleme modu: `calistir.py --canli`

- Prosedürel havadan simülatör, 7 senaryo, kare başına kusursuz ground-truth
- Ego-motion (LK + RANSAC), 4 takılabilir SOT çekirdeği, Kalman, target lock
  durum makinesi, yeniden tespit
- Ölçülen: ortalama IoU 0.742, kilit %96.9, 1 ID switch, minimum takip boyutu
  9.0 × 3.7 px, 640×480'de 2.52 ms/kare
