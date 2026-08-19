# Benchmark Baseline — SİMÜLASYON

Aşama 2 sonunda dondurulan referans değerler (19 Ağustos 2026).

> **Bu dosya yalnızca kontrollü simülasyon sonuçlarını içerir.**
> Gerçek hava görüntüsü (VisDrone) sonuçları `RAPOR_VISDRONE.md` dosyasındadır
> ve bu tablolarla **birleştirilmemelidir**. İkisi farklı şeyleri ölçer:
> sim → hedef boyutunun kontrollü süpürülmesi; VisDrone → gerçek kamera
> hareketi, gerçek gürültü, gerçek sahne karmaşıklığı.

**Bu dosyanın amacı:** bundan sonra eklenecek her şey (YOLO, ByteTrack,
BoT-SORT, hibrit takip, Pi optimizasyonu) bu sayılarla karşılaştırılacak.
Doğruluk metriklerinde bir düşüş olursa **raporlanmak zorundadır**.

## Ölçüm ortamı

| | |
|---|---|
| Makine | WSL2 Ubuntu 22.04, Linux 6.6.114.1 |
| Python | 3.10, opencv-python 4.11.0, numpy 1.26.4 |
| Çözünürlük | 640 × 480 |
| Çekirdek | `renk_dcf` (varsayılan) |
| Komut | `python3 kiyasla.py` |
| Süre | ~33 s |

## 7 senaryo

| test | amaç | IoU | @0.5 | @0.3 | hassasiyet | merkez hata | kilit | ID switch |
|---|---|---|---|---|---|---|---|---|
| test1_yakin | Temel takip çalışıyor mu? | 0.925 | 100.0% | 100.0% | 100.0% | 0.25 px | 100.0% | 0 |
| test2_uzaklasan | Piksel boyutu küçülürken korunuyor mu? | 0.435 | 44.7% | 69.3% | 82.6% | 1.59 px | 100.0% | 0 |
| test3_cok_kucuk | Minimum takip boyutu kaç px? | 0.560 | 61.2% | 76.1% | 84.8% | 1.75 px | 100.0% | 0 |
| test4_coklu | Başka araca geçiyor mu? | 0.866 | 100.0% | 100.0% | 100.0% | 0.57 px | 100.0% | 0 |
| test5_benzer | Görünüm ayırt edemezken? | 0.897 | 100.0% | 100.0% | 100.0% | 0.15 px | 100.0% | 0 |
| test6_okluzyon | Tekrar görününce aynı araç mı? | 0.747 | 80.6% | 86.9% | 92.1% | 0.99 px | 78.1% | 1 |
| test7_kamera | Kamera hareketine rağmen? | 0.764 | 90.7% | 100.0% | 100.0% | 0.97 px | 100.0% | 0 |
| **ORTALAMA** | | **0.742** | **82.5%** | **90.3%** | **94.2%** | | **96.9%** | **1** |

`hassasiyet` = merkez hatasının hedef köşegeninin yarısından küçük olduğu kare
oranı. Küçük hedefte IoU 1 piksellik kutu hatasında çökerken bu ölçü adil kalır.

test6'da kilit oranının tavanı %76'dır — karelerin %24'ünde hedef üst geçit
altındadır.

## Minimum takip boyutu (test3, 3 gürültü tohumu)

| hedef boyutu | kare | IoU | hassasiyet | merkez hata | hüküm |
|---|---|---|---|---|---|
| 52.2 × 21.6 | 201 | 0.943 | 100.0% | 0.44 px | BAŞARILI |
| 39.8 × 16.4 | 174 | 0.918 | 100.0% | 0.50 px | BAŞARILI |
| 31.4 × 13.0 | 153 | 0.910 | 100.0% | 0.44 px | BAŞARILI |
| 24.9 × 10.3 | 168 | 0.782 | 100.0% | 0.59 px | BAŞARILI |
| 19.9 × 8.2 | 138 | 0.673 | 100.0% | 0.81 px | BAŞARILI |
| 16.5 × 6.8 | 126 | 0.718 | 100.0% | 0.70 px | BAŞARILI |
| 13.5 × 5.6 | 156 | 0.555 | 93.6% | 1.14 px | KARARSIZ |
| 11.0 × 4.5 | 126 | 0.394 | 100.0% | 0.43 px | BAŞARILI |
| 9.0 × 3.7 | 153 | 0.348 | 99.3% | 0.37 px | BAŞARILI |
| 7.0 × 2.9 | 201 | 0.243 | 79.1% | 0.32 px | KARARSIZ |
| 5.4 × 2.2 | 141 | 0.174 | 66.7% | 0.37 px | KAYIP |

İki ayrı sınır vardır, karıştırılmamalıdır:

- **konum kilidi** ~9 × 4 px'e kadar korunur (merkez hatası hâlâ 1 px altında)
- **kutu ölçüsü** ~25 × 10 px altında güvenilmez olur (IoU bu yüzden düşer)

Takip uygulaması için belirleyici olan birincisidir.

## Çekirdek karşılaştırması

| çekirdek | 7 test skoru | en küçük hedef | not |
|---|---|---|---|
| **renk_dcf** | 0.892 | **9.0 × 3.7 px** | gri + renk kanalları; varsayılan |
| mosse | 0.888 | 16.5 × 6.8 px | tek kanal gri, en ucuzu |
| ncc | 0.770 | 16.5 × 6.8 px | `matchTemplate`, görünüm değişimine kırılgan |
| akis | 0.630 | — | Median Flow; küçük hedefte köşe bulamıyor |

Ana bulgu: **20 × 10 px altında doku kalmıyor, renk kalıyor.** Renk kanallarını
eklemek minimum takip boyutunu yarıya indiriyor — aynı araç için iki katı irtifa.

Komut: `python3 minboyut.py`

## Zaman profili

| aşama | ms | pay |
|---|---|---|
| ego-motion (LK + RANSAC) | 0.94 | 37% |
| korelasyon çekirdeği | 1.01 | 40% |
| tespit / kutu rafinesi | 0.23 | 9% |
| **TOPLAM** | **2.52** | 100% |

- bu makine: **397 FPS**
- Pi Zero 2 W kaba tahmin: 33.1 FPS (×12)
- Pi Zero 1 kaba tahmin: 8.8 FPS (×45)

Pi katsayıları **tahmindir**; kesin sonuç için cihazda ölçülmelidir.

## Gecikme (main.py, Aşama 2'de eklendi)

80 kare, `--penceresiz`:

| kaynak | FPS | ort | p50 | p95 | max |
|---|---|---|---|---|---|
| `sim:test1` | 362.8 | 2.76 ms | 2.42 ms | 4.58 ms | 5.28 ms |
| `video:test1.mp4` | 372.9 | 2.68 ms | 2.37 ms | 4.10 ms | 6.31 ms |

## Regresyon kuralları

**Regresyon sayılan (kırmızı çizgi):**

- Herhangi bir senaryoda IoU'nun 0.01'den fazla düşmesi
- Herhangi bir senaryoda hassasiyet veya kilit oranının düşmesi
- Toplam ID switch sayısının 1'in üstüne çıkması
- `renk_dcf` minimum takip boyutunun 9.0 × 3.7 px'in üstüne çıkması

**Regresyon sayılmayan:**

- FPS oynamaları. Ölçüm makine yüküne çok duyarlı: aynı kod, aynı gün,
  245–434 FPS arasında ölçüldü. **FPS'i regresyon kriteri olarak kullanma;**
  doğruluk metrikleri bit düzeyinde tekrarlanabilirdir, FPS değildir.

## Nasıl tekrarlanır

```bash
python3 kiyasla.py        # 7 senaryo + boyut eğrisi + zaman profili (~33 s)
python3 minboyut.py       # çekirdek karşılaştırmalı minimum boyut
python3 test_kaynak.py    # kaynak katmanı testleri (22 test)
python3 test_visdrone.py  # VisDrone adapter testleri (21 test)
```

Gerçek veri için ayrı komut (bu tabloları etkilemez):

```bash
python3 visdrone_kiyasla.py --hepsi --rapor    # → RAPOR_VISDRONE.md
```

## Sim ↔ Gerçek veri farkı (Aşama 3 ölçümü)

Aynı takip hattı, farklı girdi:

| ortam | ortalama IoU | kilit oranı | not |
|---|---|---|---|
| Simülasyon (7 senaryo) | **0.742** | 96.9% | kontrollü, nadir bakış, sentetik doku |
| VisDrone (6 dizi) | **0.281** | 82.8% | gerçek görüntü, eğik bakışlar, parallaks |

Bu fark bir regresyon **değildir** — sistemin gerçek dünyadaki gerçek
performansıdır ve YOLO + MOT yönündeki kararın niceliksel gerekçesidir.
Ayrıntı: `RAPOR_VISDRONE.md`.

Ölçüm sırasında makinede başka ağır iş çalıştırma; doğruluk sayıları
etkilenmez ama FPS ve zaman profili yanıltıcı çıkar.
