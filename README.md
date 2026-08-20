# Drone Hedef Takip

Havadan çekilen görüntüde **seçilen tek bir aracı**, araç görüntüde çok küçük hale
gelse bile, mümkün olduğunca uzun süre ve yüksek FPS ile takip etmek.

## Proje Durumu

Tamamlanan:

- ✅ **Aşama 1** — Mevcut sistem analizi ve simülasyon baseline'ı
- ✅ **Aşama 2** — Sim / video / kamera kaynak soyutlaması
- ✅ **Aşama 3** — VisDrone gerçek aerial veri entegrasyonu
- ✅ **Aşama 3.7** — Gerçek veri hata teşhisi
- ✅ **Aşama 3.8** — False-lock / bağımsız doğrulama

Aktif:

- 🔄 **Aşama 3.9** — Hızlı hedef hareketi ve hareket kestirimi
  *(A3.8'in çıktısı olarak tanımlandı; kodda karşılığı **henüz yok**)*

Sonraki aşamalar:

- ⏳ **Aşama 3.10** — Kontrollü simülasyonun genişletilmesi
- ⏳ **Aşama 4** — Kullanıcı hedef seçimi
- ⏳ **Aşama 5** — YOLO detection
- ⏳ **Aşama 6** — VisDrone fine-tuning
- ⏳ **Aşama 7** — ByteTrack / BoT-SORT
- ⏳ **Aşama 8** — Target Lock + MOT ID
- ⏳ **Aşama 9** — Hibrit seyrek detection + klasik tracker
- ⏳ **Aşama 10** — Recovery / oklüzyon
- ⏳ **Aşama 11** — Raspberry Pi optimizasyonu

Aşama günlüğünün tamamı: `docs/architecture/CHANGELOG.md`.

## Problem Tanımı

Problem klasik araç tespiti değil; şu dört kısıtın **aynı anda** sağlanması:

- **Küçük nesne** — irtifa arttıkça araç 20 × 10 px'in altına iner; o boyutta
  doku diye bir şey kalmaz.
- **Hareketli kamera** — drone kayar, döner, irtifa değiştirir; hedefin görüntüdeki
  hareketi kendi hareketiyle kameranınkinin toplamıdır.
- **Benzer nesneler** — aynı yolda aynı renkte araçlar; görünüm tek başına kimlik
  ayırt etmeye yetmez.
- **Düşük donanım** — hedef donanım Raspberry Pi sınıfı; her karede CNN koşturmak
  bütçe dışı.

## Mevcut Sistem

Şu anki hat **tamamen klasik CV**'dir; derin öğrenme bağımlılığı yoktur
(`opencv-python` + `numpy`).

| Bileşen | Dosya | Görev |
|---|---|---|
| Ego-motion | `takip/egomotion.py` | Seyrek LK optik akış + RANSAC benzerlik dönüşümü |
| DCF takip | `takip/cekirdekler.py` | Renk kanallı korelasyon filtresi (`renk_dcf`, varsayılan) |
| Kalman | `takip/izleyici.py` | Sabit hızlı 4 durumlu KF; ego dönüşümü doğrudan duruma uygulanır |
| Kutu rafinesi | `takip/tespit.py` | Yerel renk kontrastıyla kutuyu doğrudan ölçme (çapa) |
| Yeniden tespit | `takip/tespit.py` | Ego-telafili kare farkı → hareketli lekeler |
| Görünüm imzası | `takip/tespit.py` | Renk + şablon + boyut; eşleştirme için uyarlanır |
| False-lock doğrulama | `takip/izleyici.py` | Donmuş referans imza + zemine çakılma testi (A3.8) |

**YOLO ve MOT (ByteTrack / BoT-SORT) henüz sisteme entegre değildir.** Aşama 5–8
olarak planlanmıştır; bu depodaki hiçbir ölçüm onları içermez.

## Görüntü Kaynakları

Takip hattı görüntünün nereden geldiğini bilmez; dört kaynak da aynı boru hattına
`Kare` nesnesi verir (`kaynak.py`).

```bash
python3 main.py --source sim                                # prosedürel simülatör
python3 main.py --source sim:test6                          # senaryo seçerek
python3 main.py --source data/videos/drone_traffic_01.mp4   # MP4 drone videosu
python3 main.py --source camera                             # webcam (index 0)
python3 main.py --source camera:1                           # ikinci kamera
python3 main.py --source visdrone --sequence uav0000305_00000_v \
                --track-id 30 --hedef-genislik 960          # gerçek aerial veri
```

- Eski biçim de çalışır: `--source video --input dosya.mp4`
- Ek seçenekler: `--cekirdek mosse` · `--kaydet cikti/kayit.mp4` · `--max-kare 300` ·
  `--olcek 0.5` · `--penceresiz` (ekransız koşum)
- Canlı pencerede: **boşluk** duraklat/devam · **n** tek kare ilerle · **q**/**ESC** çık
- Koşum sonunda gecikme özeti basılır (FPS · ort · p50 · p95 · max)

Kod içinden:

```python
from kaynak import kaynak_olustur

with kaynak_olustur("video", girdi="data/ucus.mp4") as kaynak:
    for kare in kaynak:
        sonuc = tak.guncelle(kare.goruntu)   # kare.goruntu -> BGR ndarray
```

Her `Kare`: `goruntu`, `indeks`, `zaman`, `kaynak_adi`, `genislik`, `yukseklik`,
`fps`; simülatör ve VisDrone kaynaklarında ayrıca `gt` ve `gorunur` (video/kamerada
`None`). Hedef seçimi takılıp çıkarılabilir — Aşama 4'teki fare ile seçim aynı
imzayı kullanacak, döngü değişmeyecek:

```python
def secici(adaylar, kare):    # -> aday sözlüğü ya da None
    ...
main.kos(kaynak, hedef_secici=secici)
```

## Simülasyon

`sim/` prosedürel havadan sahne üretir: asfalt, şeritler, binalar, ağaçlar, park
halinde araçlar (statik çeldirici). Kamera dik bakar; irtifa → ölçek, yaw → dönme,
titreşim → gürültü. **Her kare için kusursuz ground-truth kutusu bilinir** — gerçek
videoda bu elle etiketleme gerektirirdi.

Hedef ilk karede elle değil, sistemin **kendi hareket tespiti listesinden** seçilir.
GT kutusuyla kilitlemek ölçümü şişirirdi. Kuşbakışı görüntüde araç aracın önüne
geçemediği için test 6'daki oklüzyon üst geçit / ağaç örtüsü olarak modellenmiştir.

### 7 test — sim baseline

```bash
python3 kiyasla.py --video     # 7 test + metrikler + cikti/*.mp4 + RAPOR.md
python3 calistir.py test6 --canli
```

| test | IoU | @0.5 | hassasiyet | merkez hata | kilit | ID switch |
|---|---|---|---|---|---|---|
| 1 yakın araç | 0.925 | 100% | 100% | 0.25 px | 100% | 0 |
| 2 uzaklaşan | 0.435 | 45% | 83% | 1.59 px | 98% | 0 |
| 3 çok küçük | 0.560 | 61% | 85% | 1.75 px | 95% | 0 |
| 4 çoklu araç | 0.866 | 100% | 100% | 0.57 px | 100% | 0 |
| 5 benzer araçlar | 0.897 | 100% | 100% | 0.15 px | 100% | 0 |
| 6 kısa kayıp | 0.747 | 81% | 92% | 0.99 px | 78% | 1 |
| 7 kamera hareketi | 0.764 | 91% | 100% | 0.97 px | 100% | 0 |

Ortalama IoU **0.742** · hassasiyet **%94.2** · @0.5 **%82.5** · ID switch **1** —
bu dört değer A3.8'de birebir korundu.

**hassasiyet** = merkez hatasının hedef köşegeninin yarısından küçük olduğu kare
oranı. Küçük hedefte IoU 1 piksellik kutu hatasında çökerken bu ölçü adil kalır.

test6'da kilit oranının tavanı %76'dır (karelerin %24'ünde hedef üst geçit altında).
test2 (%100 → %98.0) ve test3 (%100 → %94.6) kilit düşüşü A3.8'in **gerçek** yanlış
kilitleri reddetmesidir; ayrıntı `docs/architecture/BENCHMARK_BASELINE.md`.

### Küçük hedef deneyi: 52 × 22 px → 5 × 2 px

Aynı senaryo, hedef boyutu kontrollü biçimde küçültülerek 3 gürültü tohumuyla
koşulur (`python3 minboyut.py`):

| hedef | IoU | hassasiyet | merkez hata | hüküm |
|---|---|---|---|---|
| 52 × 22 px | 0.94 | 100% | 0.44 px | başarılı |
| 31 × 13 px | 0.91 | 100% | 0.44 px | başarılı |
| 20 × 8 px | 0.67 | 100% | 0.81 px | başarılı |
| 16 × 7 px | 0.72 | 100% | 0.70 px | başarılı |
| 13 × 6 px | 0.56 | 94% | 1.14 px | kararsız |
| 9 × 4 px | 0.35 | 99% | 0.37 px | başarılı |
| 7 × 3 px | 0.24 | 79% | 0.32 px | kararsız |
| 5 × 2 px | 0.17 | 67% | 0.37 px | kayıp |

İki ayrı sınır vardır, karıştırılmamalıdır:

- **konum kilidi** ~9 × 4 px'e kadar korunur (merkez hatası hâlâ 1 px altında)
- **kutu ölçüsü** ~25 × 10 px altında güvenilmez olur (IoU bu yüzden düşer)

Takip uygulaması için belirleyici olan birincisidir.

### Çekirdek karşılaştırması

Takip çekirdeği takılıp çıkarılabilir (`HedefTakip(cekirdek="...")`).

| çekirdek | 7 test skoru | en küçük hedef | not |
|---|---|---|---|
| **renk_dcf** | 0.892 | **9.0 × 3.7 px** | gri + renk kanalları; varsayılan |
| mosse | 0.888 | 16.5 × 6.8 px | tek kanal gri, en ucuzu |
| ncc | 0.770 | 16.5 × 6.8 px | `matchTemplate`, görünüm değişimine kırılgan |
| akis | 0.630 | — | Median Flow; küçük hedefte köşe bulamıyor |

Ana bulgu: **20 × 10 px altında doku kalmıyor, renk kalıyor.** Renk kanallarını
eklemek minimum takip boyutunu yarıya indiriyor — aynı araç için iki katı irtifa.

## Gerçek Aerial Veri — VisDrone

VisDrone2019-VID seçildi çünkü aradığımız dört kısıtı aynı anda içeriyor:
gerçek drone kamerası, küçük araçlar, kare kare **track kimlikli GT anotasyonu**
ve gerçek uçuş senaryoları (kayma, dönme, irtifa değişimi, eğik bakış).

```bash
python3 visdrone_kiyasla.py --hepsi --rapor    # → RAPOR_VISDRONE.md
```

Hedef, track'in ilk karesindeki GT kutusuyla kilitlenir; sonraki karelerde GT
**yalnızca ölçüm için** kullanılır, takipçiye beslenmez. `--track-id` verilmezse
en uzun süre görünen **hareketli** araç seçilir. Kareler 960 px genişliğe indirilir,
GT kutuları aynı oranda ölçeklenir.

| dizi | track | kare | IoU | @0.5 | hassasiyet | merkez hata | kilit | FPS |
|---|---|---|---|---|---|---|---|---|
| uav0000117_02622_v | 23 | 343 | 0.701 | 97% | 100% | 5.51 px | 100% | 311 |
| uav0000305_00000_v | 5 | 141 | 0.502 | 65% | 77% | 9.12 px | 83% | 147 |
| uav0000137_00458_v | 12 | 221 | 0.215 | 26% | 34% | 82.90 px | 83% | 183 |
| uav0000339_00001_v | 49 | 266 | 0.172 | 0% | 32% | 28.72 px | 100% | 321 |
| uav0000182_00000_v | 127 | 335 | 0.095 | 0% | 34% | 266.30 px | 34% | 114 |
| uav0000268_05773_v | 31 | 252 | 0.000 | 0% | 0% | 408.84 px | 96% | 101 |
| **ORTALAMA** | | **1558** | **0.281** | **31%** | **46%** | | **83%** | **196** |

Bu tablodaki `kilit` sütunu **A3.8 öncesi** davranışı gösterir (19 Ağustos 2026);
IoU ve merkez hatası değerleri geçerlidir. A3.8 sonrası yanlış kilit oranları
aşağıdadır. Sim ve VisDrone sayıları **aynı tabloda birleştirilmemelidir** —
farklı şeyleri ölçerler.

`uav0000086_00000_v` atlandı: dizide hiç araç sınıfı yok (sadece yaya).

### Veri kümesini kurma

Veri kümeleri **depoya dahil değildir** (1.6 GB; `.gitignore`'da).
[github.com/VisDrone/VisDrone-Dataset](https://github.com/VisDrone/VisDrone-Dataset)
adresinden indirip şöyle açın:

```bash
mkdir -p data/datasets && cd data/datasets
unzip VisDrone2019-VID-val.zip && mv VisDrone2019-VID-val visdrone_vid
unzip VisDrone2019-DET-val.zip && mv VisDrone2019-DET-val visdrone_det
```

```
data/
├── videos/                # kendi drone/aerial mp4'lerin
└── datasets/
    ├── visdrone_vid/      # 7 dizi, 2846 kare, 1.6 GB
    │   ├── annotations/<dizi>.txt
    │   └── sequences/<dizi>/0000001.jpg ...
    └── visdrone_det/      # 548 görüntü (Aşama 6, YOLO fine-tuning için)
```

`VisDrone2019-MOT-val.zip`'i açmaya gerek yok — içeriği VID-val ile birebir
aynıdır (kök klasör adı dışında MD5'leri eşleşiyor).

## Gerçek Veri Bulguları

Sim 0.742 → gerçek 0.281. Farkın kökeni Aşama 3.7'de iki dizide teşhis edildi.

### 268/31 — hızlı hedef

- Araç bir karede **kutu eninin %61'i** kadar yol alıyor; korelasyon penceresinin
  merkezinden tek karede çıkıyor ve takipçi geride kalıyor.
- Kopan filtre yol dokusunu öğreniyor. PSR bir kimlik ölçüsü değil, filtrenin **iç
  tutarlılık** ölçüsüdür: filtre yola kayınca PSR düşmüyor, 12'den 46'ya **çıkıyor**.
- Sonuç: sistem 978 karenin %99'unda "KİLİTLİ" diyor ama IoU 0.000.
- A3.8 sonrası yanlış kilit oranı **%98.4 → %44.0** (en uzun kesintisiz yanlış kilit
  144 → 38 kare). 1920 px'e indirilmiş aynı dizide %99.2 → %69.4.
- Gerçek hedef **hâlâ geri bulunamıyor** (IoU 0.005). Aşama 3.9'un konusu budur.

### 182/127 — duran hedef

- Yeniden tespit yalnızca **hareket lekesi** üretiyor. Hedef durduğunda aday listesi
  boş kalıyor ve araç geri bulunamıyor.
- Uyarlanan imza yol dokusunu ezberleyince yeniden tespit de yol yamalarını hedefe
  benzetiyordu; A3.8'in referans-imza kapısı bunu kesti.
- A3.8 sonrası yanlış kilit oranı **%47.8 → %11.3** (123 → 18 kare).
- Duran hedef için **görünüm tabanlı** bir aday kaynağı hâlâ gerekiyor.

Ek olarak: VisDrone dizilerinin bir kısmı nadir değil, sokak seviyesine **eğik**
bakıyor. `egomotion.py`'nin 2 × 3 afin düzlem modeli parallakslı 3B sahnede
zayıflıyor; aday üretimi ağaç ve binalarda gürültüleniyor.

## Aşama 3.8 — False-Lock Doğrulama

`KİLİTLİ` durumu artık PSR'dan **bağımsız** iki denetleyiciyle sınanır:

1. **Donmuş görünüm imzası.** Kilit anındaki imza (`imza_ref`) dondurulur ve bir daha
   güncellenmez; 6 karede bir mevcut kutu bu referansla karşılaştırılır (renk + doku).
   İki kez üst üste eşiğin altında kalırsa kilit reddedilir. Eşleştirmede kullanılan
   uyarlanan imza (`imza`) bundan **ayrıdır** — doğrulama çapası kaymamalı,
   eşleştirme ise ışık/görünüm değişimine uyum sağlamalıdır.
2. **Zemine çakılma testi.** Kutunun ego telafili yer değiştirmesi 20 karelik kayan
   pencerede p90 olarak ölçülür. Kare genişliğinin %0.08'inin altında 20 kare üst
   üste kalırsa kutu aracı değil **yeri** takip ediyordur.

Tek başına hiçbiri yetmez: 268'de yanlış kilidin imza benzerliği (0.824) 117'deki
**doğru** takiptan (0.716) yüksek; 182'nin duran hedefi ise zemin testini yanlış
tetikler. İkisi birbirinin körünü kapatır.

| dizi | yanlış kilit | en uzun kesintisiz |
|---|---|---|
| 117/23 (doğru takip) | %0 → %0 | 0 → 0 kare |
| 268/31 @3840 | %98.4 → **%44.0** | 144 → 38 kare |
| 268/31 @1920 | %99.2 → **%69.4** | 250 → 39 kare |
| 182/127 | %47.8 → **%11.3** | 123 → 18 kare |

**Sınırı net olsun:** A3.8 yanlış kilidi **tespit etmeyi** hedefledi, hedefi geri
bulmayı değil. Reddetme yalnızca "bu kilit yanlış" der; kurtarma mevcut arama
mekanizmasına devredilir ve o taraf değişmedi. İkisi de IoU'yu düzeltmedi.
Gerçekten 20+ kare boyunca duran bir araç bu testçe yanlış kilit sanılabilir;
`HedefTakip(zemin_dogrulama=False)` testi kapatır.

## Mimari

```
                        Kare  (sim / video / kamera / VisDrone)
                          │
                          ▼
                    [1] EGO-MOTION          LK + RANSAC benzerlik dönüşümü
                          │                 tek hesap, üç kazanç:
                          │                   · arama penceresini daraltır
                          │                   · hareketliyi arka plandan ayırır
                          │                   · ölçek katsayısı verir
                          ▼
                    [2] TAKİP               renk kanallı DCF + Kalman (sabit hız)
                          │
                          ▼
                    [3] KUTU RAFİNESİ       yerel renk kontrastıyla çapa (her 4 kare)
                          │
                          ▼
                    [4] YENİDEN TESPİT      ego-telafili kare farkı → adaylar
                          │  (kayıpta)      → renk + şablon + boyut imzasıyla eşleştirme
                          ▼
                    [5] FALSE-LOCK DOĞRULAMA  donmuş imza + zemine çakılma  (A3.8)
                          │
                          ▼
                    [6] DURUM MAKİNESİ
                        KİLİTLİ → ŞÜPHELİ (ölü hesap) → ARAMA → KAYIP (aramayı sürdürür)
```

Şüpheli durumda **öğrenme durur**. Kritik: filtre kaybettiği anda öğrenmeye devam
ederse asfaltı öğrenir ve bir daha geri dönemez.

Katman ayrıntısı ve dosya → görev tablosu: `docs/architecture/ARCHITECTURE.md`.

## Performans

640 × 480, `renk_dcf`, WSL2 (Python 3.10 · opencv-python 4.11 · numpy 1.26):

| aşama | ms | pay |
|---|---|---|
| ego-motion (LK + RANSAC) | 1.07 | %36 |
| korelasyon çekirdeği | 1.15 | %39 |
| tespit / kutu rafinesi | 0.38 | %13 |
| **TOPLAM** | **2.96** | 100% |

Bu makinede **338 FPS** (A3.8 koşumu; Aşama 2'de dondurulan referans 2.52 ms /
397 FPS'ti). **FPS bir regresyon kriteri değildir** — aynı kod aynı gün 245–434 FPS
arasında ölçüldü; doğruluk metrikleri tekrarlanabilir, FPS değildir.

Pahalı olan yeniden tespit **sadece kayıpta** çalışır; kilitliyken kare başına iş
sabittir.

Raspberry Pi sayıları **ekstrapolasyondur, cihazda ölçüm yapılmamıştır**:
Pi Zero 2 W ≈ 28 FPS (×12), Pi Zero 1 ≈ 8 FPS (×45). Kesin sonuç için cihazda
ölçülmelidir (Aşama 11).

## Bilinen Sınırlar

1. **268/31 hızlı hedefi yeniden bulunamıyor.** Kare başına yer değiştirme kutu
   eninin %61'i; araç korelasyon penceresinin merkezinden bir karede çıkıyor.
   IoU 0.005. Aşama 3.9'un konusu.
2. **182/127 duran hedefi yeniden bulunamıyor.** Yeniden tespit yalnızca hareket
   lekesi üretiyor; duran araç için aday listesi boş kalıyor.
3. **ARAMA modu 4K'da pahalı.** Aday üretimi her karede tam çözünürlükte çalışıyor:
   p50 12.9 → 43.4 ms, FPS 30.4 → 14.1. Çözünürlüğe göre alt-örnekleme gerekiyor.
4. **Çözünürlük kalibrasyonu eksik.** 268'de yanlış kilit 4K'da %44.0, 1920'de %69.4.
   Tespit gecikmesi (20 kare pencere + 20 kare sabır) iki çözünürlükte farklı sayıda
   yeniden-kilit döngüsüne denk geliyor.
5. **Raspberry Pi üzerinde ölçüm yapılmadı;** yukarıdaki Pi sayıları tahmindir.
6. **YOLO ve MOT entegre değil.** Detection, ByteTrack/BoT-SORT, MOT ID ve hibrit
   takip Aşama 5–9'da planlanmıştır; mevcut hat tümüyle klasik CV'dir.

Ayrıca **ego ölçek yanlılığı**: kare kare ölçek kestirimi kısa vadede doğru, uzun
vadede ~%8/300 kare yanlı. Bu yüzden ölçek **integre edilmiyor**; kutu boyutu
doğrudan ölçümle çapalanıyor.

## Sonraki Adımlar

1. **A3.9 — hızlı hareket / hareket kestirimi.** Kilit sonrası hız kestirimi;
   arama penceresi hedefin hareketine göre konumlanmalı (268/31).
2. **A3.10 — kontrollü simülasyonun genişletilmesi.** Hızlı hedef ve duran hedef
   senaryolarının sim tarafında tekrarlanabilir hale getirilmesi.
3. **A4 — kullanıcı hedef seçimi** (fare ile seçim; `hedef_secici` sözleşmesi hazır).
4. **A5 — YOLO detection.**
5. **A6 — VisDrone fine-tuning** (`visdrone_det`, 548 görüntü hazır).
6. **A7 — ByteTrack / BoT-SORT.**
7. **A8 — Target Lock + MOT ID.**
8. **A9 — hibrit seyrek detection + klasik tracker.**
9. **A10 — recovery / oklüzyon** (duran hedef için görünüm tabanlı aday üretimi).
10. **A11 — Raspberry Pi optimizasyonu** (320 × 240 giriş + ROI-only işleme, cihazda
    gerçek ölçüm).

Her yeni aşama `docs/architecture/BENCHMARK_BASELINE.md`'deki sayılarla
karşılaştırılır; doğruluk metriklerinde düşüş olursa raporlanmak zorundadır.

## Test ve Dokümantasyon

```bash
python3 test_kaynak.py     # kaynak katmanı, 22 test (pytest gerektirmez)
python3 test_visdrone.py   # VisDrone adapter, 21 test
python3 kiyasla.py         # sim baseline: 7 senaryo + boyut eğrisi + zaman profili
python3 minboyut.py        # çekirdek karşılaştırmalı minimum boyut deneyi
python3 tarama.py          # çekirdek / parametre taraması (paralel)
python3 visdrone_kiyasla.py --hepsi --rapor
```

| Dosya | İçerik |
|---|---|
| `RAPOR.md` | Simülasyon sonuç raporu (7 test + boyut eğrisi + zaman profili) |
| `RAPOR_VISDRONE.md` | Gerçek VisDrone sonuçları — sim raporundan **ayrı** |
| `docs/architecture/ARCHITECTURE.md` | Katmanlar, dosya → görev, tasarım gerekçeleri |
| `docs/architecture/CHANGELOG.md` | Aşama aşama değişiklik günlüğü + denenip elenenler |
| `docs/architecture/BENCHMARK_BASELINE.md` | Dondurulmuş sim referansı + regresyon kuralları |
| `docs/architecture/BENCHMARK_WINDOWS.md` | Windows üzerindeki ayrı ölçüm (Linux sayılarıyla kıyaslanmaz) |

## GitHub

<https://github.com/Beyzanurekerr/drone-takip>

Commit mesaj biçimi: `feat:` · `fix:` · `docs:` · `test:` · `refactor:`
