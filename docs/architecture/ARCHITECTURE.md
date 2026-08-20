# Mimari

Aşama 3.8 sonu durumu (20 Ağustos 2026).

## Amaç

Drone görüntüsünde kullanıcının seçtiği tek bir aracı, kamera hareket ederken,
hedef diğer araçların arasına girerken ve görüntüde küçülürken yüksek FPS ile
takip etmek. Nihai hedef donanım Raspberry Pi sınıfı.

## Katmanlar

```
                 ┌── SimKaynak          (prosedürel simülatör + kusursuz GT)
                 ├── VideoKaynak        (MP4/AVI drone videosu)
INPUT ───────────┼── KameraKaynak       (webcam / USB kamera)
                 └── VisDroneVidKaynak  (gerçek hava görüntüsü + VisDrone GT)
                          │
                          ▼
                    kaynak.py  ·  Kare(goruntu, indeks, zaman, gt, ...)
                          │
                          ▼
   ┌──────────────────────────────────────────────────────┐
   │  takip/  —  görüntünün kaynağını BİLMEZ              │
   │                                                      │
   │  egomotion.py   LK + RANSAC afin  (= BoT-SORT GMC)   │
   │        ↓                                             │
   │  tespit.py      ego-telafili kare farkı → adaylar    │
   │        ↓                                             │
   │  cekirdekler.py renk_dcf / mosse / ncc / akis (SOT)  │
   │        ↓                                             │
   │  izleyici.py    Kalman + durum makinesi (target lock)│
   └──────────────────────────────────────────────────────┘
                          │
                          ▼
              main.py  ·  görselleştirme + gecikme + GT varsa metrik
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
   calistir.py / kiyasla.py    visdrone_kiyasla.py
   SİM BASELINE (dokunulmaz)   GERÇEK VERİ (ayrı rapor)
   → RAPOR.md                  → RAPOR_VISDRONE.md
```

İki benchmark hattı **bilerek ayrıdır**: sim baseline'ı kontrollü ve
tekrarlanabilir, gerçek veri sonuçları ise gürültülü ve senaryoya bağlıdır.
Sayıları aynı tabloda birleştirmek yanıltıcı olur.

## Dosya → görev

| Dosya | Görev |
|---|---|
| `kaynak.py` | Görüntü kaynağı soyutlaması. `Kare`, `Kaynak`, `SimKaynak`, `VideoKaynak`, `KameraKaynak`, `kaynak_olustur()` |
| `main.py` | Kaynak-bağımsız çalıştırıcı: CLI, OpenCV penceresi, HUD, gecikme ölçümü |
| `calistir.py` | Simülatör tabanlı ölçüm döngüsü `kos()` + çizim ilkeleri. **Baseline** |
| `kiyasla.py` | 7 senaryo + boyut eğrisi + zaman profili + `RAPOR.md`. **Baseline** |
| `minboyut.py` | Çekirdeklerin minimum takip boyutu karşılaştırması |
| `tarama.py` | Parametre ızgarası / çekirdek taraması |
| `sim/world.py` | `Ground`, `Vehicle`, `Camera` (nadir), `Scene` (render + GT) |
| `sim/senaryolar.py` | 7 senaryo, kamera kontrolcüsü, `TUM_TESTLER` |
| `takip/egomotion.py` | Ego-motion: seyrek LK + RANSAC benzerlik dönüşümü, ölçek katsayısı |
| `takip/tespit.py` | `HareketTespit` (aday üretimi), `rafine_kutu()`, `Imza` (hafif appearance) |
| `takip/cekirdekler.py` | 4 takılabilir SOT çekirdeği, ortak arayüz |
| `takip/mosse.py` | MOSSE korelasyon filtresi (numpy FFT) |
| `takip/izleyici.py` | `HedefTakip` orkestratörü, `Kalman`, durum makinesi |
| `veri/etiket.py` | Ortak GT temsili (`Etiket`) + VisDrone VID/DET annotation ayrıştırıcı |
| `veri/visdrone.py` | `VisDroneVidKaynak` + dizi keşfi + frame↔GT senkron doğrulaması |
| `visdrone_kiyasla.py` | **Gerçek veri** değerlendirmesi → `RAPOR_VISDRONE.md`. Sim benchmark'ından bağımsız |
| `test_kaynak.py` | Kaynak katmanı testleri (22 test) |
| `test_visdrone.py` | VisDrone adapter testleri (21 test) |

## Kaynak sözleşmesi

Her kaynak aynı arayüzü uygular:

```python
kaynak.oku()      -> Kare | None      # None = akış bitti
kaynak.kapat()
kaynak.acik_mi()  -> bool
kaynak.bilgi()    -> str
kaynak.tur        # "sim" | "video" | "kamera"
kaynak.ad, .genislik, .yukseklik, .fps, .kare_sayisi
```

`for kare in kaynak:` ve `with kaynak as k:` tabanda tanımlı.

`Kare` alanları: `goruntu` (BGR ndarray), `indeks`, `zaman`, `kaynak_adi`,
`genislik`, `yukseklik`, `fps`, `gt`, `gorunur`.

`gt` ve `gorunur` simülatör ve VisDrone kaynağında doludur; video ve kamerada
`None`'dır — "bilinmiyor" anlamına gelir. Ölçüm tarafı GT'nin nereden geldiğini
ayırt etmez; ileride UAV123/UAVDT/DTB70 adapter'ları da aynı alanı dolduracak.

## Ortak GT temsili (`veri/etiket.py`)

VisDrone formatı doğrudan takip tarafına taşınmaz; önce `Etiket`'e çevrilir:

```python
@dataclass
class Etiket:
    kare: int          # 1-tabanlı (VisDrone böyle); DET'te 0
    track_id: int      # DET'te -1
    sinif: int         # 0=ignored 4=car 5=van 6=truck 9=bus ...
    kutu: np.ndarray   # (x, y, w, h) float32, sol-üst kökenli
    yoksayilan: bool   # score==0 ya da sinif==0 → ölçüme katılmaz
    kirpilma: int      # 0/1
    ortulme: int       # 0 yok, 1 kısmi, 2 ağır
```

`olcekli(k)` metodu downscale'de GT kutusunu aynı oranda küçültür — kare
küçülüp GT küçülmezse tüm IoU ölçümü sessizce bozulur.

## VisDrone VID kaynağı

```
data/datasets/visdrone_vid/
├── annotations/<dizi>.txt      10 kolon: kare,track_id,x,y,w,h,score,sinif,kirpilma,ortulme
└── sequences/<dizi>/0000001.jpg ...
```

- **Hedef seçimi:** `--track-id` ile belirtilir; verilmezse *en uzun süre
  görünen ve hareket eden* araç track'i seçilir. Sadece "en uzun" seçmek park
  halindeki aracı seçer — hareketsiz hedef ölçüm için anlamsızdır.
- **GT kullanımı:** yalnızca **kilit anında** başlangıç kutusu olarak. Sonraki
  karelerde takipçi kendi tahminiyle ilerler; GT sadece ölçümde kullanılır.
- **Senkron doğrulaması:** kare adları sayısal mı, 1'den başlıyor mu, eksik kare
  var mı, annotation kare sayısını aşıyor mu — hepsi açık hata mesajıyla.
- **Downscale:** `--olcek 0.5` ya da `--hedef-genislik 960`. Diziler
  1344×756 ile 3840×2160 arasında değişiyor; sistem 640×480'e ayarlı
  parametreler taşıdığı için ölçekleme fiilen zorunlu.

## Kaynak seçimi

```
"sim"                    → SimKaynak(senaryo)
"sim:test6"              → SimKaynak("test6")
"camera" / "camera:1"    → KameraKaynak
"video" + girdi=...      → VideoKaynak   (eski biçim, geriye uyumluluk)
"data/videos/x.mp4"      → VideoKaynak   (doğrudan dosya yolu)
```

Yeni bir kaynak tipi eklemek `kaynak_olustur()`'a bir dal eklemekten ibarettir;
çağıran taraf değişmez.

## Durum makinesi (target lock)

```
KİLİTLİ ──PSR düştü──▶ ŞÜPHELİ ──8 kare──▶ ARAMA ──90 kare──▶ KAYIP
   ▲                       │                   │                 │
   └───────────────────────┴─── imza eşleşti ──┴─────────────────┘
```

Kritik kural: **ŞÜPHELİ durumda öğrenme durur.** Filtre kaybettiği anda
öğrenmeye devam ederse zemini öğrenir ve bir daha geri dönemez.

### Bağımsız doğrulama (Aşama 3.8)

PSR bir **kimlik** ölçüsü değil, filtrenin **iç tutarlılık** ölçüsüdür: filtre
neyi öğrendiyse onu güvenle bulur. Yola kayarsa yolu öğrenir ve PSR düşmez —
tam tersine yükselir. Bu yüzden `KİLİTLİ` durumunun PSR'dan bağımsız iki
denetleyicisi var:

```
KİLİTLİ
  ├─ kutu zeminden bağımsız hareket ediyor mu?   (ego-telafili p90, 20 kare)
  │    EVET → imza uyuşmazlığı = görünüm değişimi → KİLİTLİ devam
  │    HAYIR ↓
  ├─ İMZA testi     : kilit anında DONDURULAN referansa benzerlik
  └─ ZEMİN testi    : p90, kare genişliğinin %0.08'i altında 20 kare üst üste
       └─ yeterli kanıt → kilit reddedilir → ARAMA + reddedilen konum yasaklı
```

İki imza ayrı tutulur: `imza_ref` dondurulmuştur ve **yalnızca doğrulama**
kullanır; `imza` uyarlanır ve **yalnızca yeniden tespit + renk kapısı** kullanır.
Uyarlanan imza ancak kutu hareketliyken *ve* referans hedefi hâlâ tanırken
öğrenir.

Tespit ile kurtarma birbirinden ayrıdır: doğrulama yalnızca "bu kilit yanlış"
der, geri bulma işi `_arama_adimi`'nindir. Eşiklerin nasıl ölçüldüğü ve
denenip elenen dört tasarım `CHANGELOG.md`, Aşama 3.8'de.

İkinci kritik kural: uzun kayıpta konum önbilgisi kullanılmaz, tüm kare
görünüm imzasıyla taranır ve **en iyi aday ikinciyi belirgin farkla geçmezse
hiçbiri kabul edilmez**. Benzer araçlarda yanlış kilidi engelleyen budur.

## Genişleme noktaları

| Nokta | Nasıl |
|---|---|
| Yeni görüntü kaynağı | `Kaynak`'tan türet, `oku()` yaz, fabrikaya dal ekle |
| Dataset adapter'ı (UAV123 vb.) | Aynı yol + `Kare.gt` doldur |
| Hedef seçimi (fare) | `main.kos(..., hedef_secici=fn)`; sözleşme `fn(adaylar, kare) -> aday \| None` |
| Yeni takip çekirdeği | `takip/cekirdekler.py` içindeki `CEKIRDEKLER` sözlüğüne ekle |
| YOLO / MOT | `takip/tespit.py`'nin yerine ya da yanına aday üretici olarak |

## Bilinen sınırlar

1. **Yanlış güven** — *büyük ölçüde giderildi (Aşama 3.8).* Kilitliyken artık
   bağımsız doğrulama var; gerçek veride yanlış kilit oranı %98.4 → %44.0
   (268/31) ve %47.8 → %11.3 (182/127). Kalan sürenin tabanı tespit
   gecikmesidir (20 kare pencere + 20 kare sabır).
2. **MOT katmanı yok** — tek hedef takip ediliyor; track listesi, ID atama ve
   veri ilişkilendirme yok.
3. **Detection sınıf-bilinçsiz** — hareket tabanlı; duran araç görünmez. Aşama
   3.7'de ölçüldü: `uav0000182_00000_v`'nin hedefi 0.8 px/kare hareket ettiği
   için kaybedildikten sonra yeniden tespit onu hiç bulamıyor.

7. **Hızlı hedef** — Aşama 3.7'nin ana bulgusu: kare başına yer değiştirme
   hedef boyutuna göre büyükse araç bir karede korelasyon penceresinin
   merkezinden çıkıyor. `uav0000268_05773_v`'de oran 0.61 kutu eni/kare ve
   takip kilitten bir kare sonra kopuyor; `uav0000117_02622_v`'de oran 0.03 ve
   takip 349 kare boyunca sağlam. Arama penceresi hedefin hareketine göre
   konumlanmalı.
4. **Benchmark simülatöre kilitli** — `calistir.kos()` sahne adımı, render ve
   GT üretimini döngü içinde yapıyor.
5. **ID switch metriği tüm nesnelerin GT'sini istiyor** — tek hedefli SOT veri
   kümelerinde hesaplanamaz, yeniden tanımlanmalı.
6. **Nadir bakış varsayımı** — `Camera.matrix()` 2×3 benzerlik dönüşümü; eğik
   (oblique) bakış için homografiye geçmek gerekir.

## Bağımlılıklar

`opencv-python` ve `numpy`. Derin öğrenme bağımlılığı yok. Testler `pytest`
olmadan da koşar.
