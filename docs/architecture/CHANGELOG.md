# Değişiklik Günlüğü

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
