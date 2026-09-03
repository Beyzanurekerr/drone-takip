# Deney 3 — açı referansı ego-motion entegrasyonundan

**Sonuç: BAŞARISIZ (kıl payı) → tamamen geri alındı.** `takip/` Deney 2 halinde
(`cekirdekler.py` md5 `c0fd7989…`, `izleyici.py` md5 `4257b94c…`), geri alma
sonrası G3_kritik 0.704 ve G3_agresif 0.760 birebir geri geldi. Commit/push yok.

Geri alınan yama: `deney3.patch` (117 satır, oturum çalışma alanı).

## Uygulanan tek değişiklik

`RenkDcfCekirdek`e `aci_ref` (ego entegrasyonu referansı) eklendi:

* kilitte `aci_ref = 0`
* **yalnızca arama açıkken** `aci_ref += dteta`
* adaylar `{n−1, n, n+1} × adım`, `n = round(aci_ref / adım)`
* seçilen açı `self.aci` yalnızca o karede kullanılır (yama kesme + aynı
  karedeki `ogren`), **`aci_ref`e yazılmaz** — bir sonraki kareye taşınmaz
* kapı kapalıyken `aci = 0` ve eski `getRectSubPix` yolu

Kapının açık kalma koşulu Deney 2'de `aci != 0` idi; `aci` artık taşınmadığı
için `round(aci_ref/adım) != 0` oldu. **Yeni eşik eklenmedi** — `aci_adim`
zaten vardı. `izleyici.py` hiç değişmedi (Deney 2'deki tek satır aynen).

Dokunulmayanlar: durum makinesi, Kalman, ego-motion hesabı, A3.8 yanlış-kilit
doğrulaması, örnekleme kutusu/boyut semantiği — hepsi aynen.

## Mekanizma çalıştı: açı hatası çöktü

| | A3.8 | Deney 2 | **Deney 3** | hedef |
|---|---|---|---|---|
| G3_agresif açı kayması | — | −0.0397 °/kare | **−0.0043** | ≤ 0.010 ✔ |
| G3_agresif \|hata\| p50 | — | 8.90° | **0.78°** | — |
| G3_agresif \|hata\| p95 | — | 13.01° | **1.74°** | ≤ 3° ✔ |
| G3_agresif kullanılan açı | — | −63.1…+1.6° | **−50.2…+1.6°** | gerçek −49.6…+1.5 |
| G3_kritik açı kayması | — | −0.0183 °/kare | **−0.0050** | — |
| G3_kritik \|hata\| p95 | — | 7.69° | **3.48°** | ≤ 5° ✔ |
| corr(hata, kare no) | — | −0.871 | −0.499 / −0.308 | ≤ 0.30 ✗ (kısmi) |

Ego yanlılığı ölçüldü: 281 karede **+0.21°** (G3_agresif), 293 karede **+0.76°**
(G3_kritik) — tasarımda öngörülenle aynı. Açı artık gerçeği neredeyse birebir
izliyor.

## Ama IoU beklendiği gibi gelmedi

| | A3.8 | Deney 2 | **Deney 3** | tasarım beklentisi |
|---|---|---|---|---|
| G3_agresif IoU | 0.766 | 0.760 | **0.768** | ≈0.789 |
| G3_kritik IoU | 0.579 | **0.704** | **0.702** | ≥0.704 |

G3_agresif kriteri geçti (0.768 ≥ 0.766) ama tasarımın öngördüğü 0.789'a
ulaşmadı: açı hatası 13.01° → 1.74° düştüğü hâlde IoU yalnızca +0.008 arttı.
Deney 2 teşhisindeki `dIoU`–`|hata|` ilişkisi (|hata| ≤ 4.8° → +0.023) burada
tekrarlanmadı. Yani açı hatası kaybın **tek** nedeni değilmiş; kalan kısım
büyük olasılıkla ön ölçüm 2'deki yama geometrisi (eksen hizalı kutunun en-boy
oranının kilitten %12–26 sapması) — bu deneyin kapsamı dışında.

G3_kritik **0.002 geriledi** ve kabul eşiğinin (≥0.704) altında kaldı. Diğer
tüm G3_kritik ölçütleri Deney 2 ile birebir aynı: drift yok, kilit %100,
@0.5 0.922, @0.3 1.000, kesinti 0, kurtarma 0. Fark yalnızca IoU ve merkez
hatasında (5.07 → 5.10 px).

## Tam tablo (A3.8 / Deney 2 / **Deney 3**)

### Gazebo (22 kayıt)

| senaryo | IoU A3.8 / D2 / **D3** | @0.5 | @0.3 | merkez px | kilit | kesinti | kurt.max | IDsw | drift | açı aktif |
|---|---|---|---|---|---|---|---|---|---|---|
| G0 | 0.912 / 0.912 / **0.912** | 1.000 / 1.000 | 1.000 / 1.000 | 1.24 / 1.24 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G1_yumusak | 0.899 / 0.899 / **0.899** | 1.000 / 1.000 | 1.000 / 1.000 | 1.40 / 1.40 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G1_agresif | 0.897 / 0.897 / **0.897** | 1.000 / 1.000 | 1.000 / 1.000 | 1.24 / 1.24 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G2_yumusak | 0.862 / 0.862 / **0.862** | 1.000 / 1.000 | 1.000 / 1.000 | 2.28 / 2.28 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G2_agresif | 0.859 / 0.859 / **0.859** | 1.000 / 1.000 | 1.000 / 1.000 | 1.63 / 1.63 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G3_yumusak | 0.862 / 0.862 / **0.862** | 1.000 / 1.000 | 1.000 / 1.000 | 1.85 / 1.85 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| **G3_agresif** | 0.766 / 0.760 / **0.768** | 0.990 / 0.997 | 1.000 / 1.000 | 3.47 / 3.52 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | **281** |
| G4_yumusak | 0.885 / 0.885 / **0.885** | 1.000 / 1.000 | 1.000 / 1.000 | 1.44 / 1.44 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G4_agresif | 0.871 / 0.871 / **0.871** | 1.000 / 1.000 | 1.000 / 1.000 | 1.72 / 1.72 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G5_yumusak | 0.888 / 0.888 / **0.888** | 1.000 / 1.000 | 1.000 / 1.000 | 1.68 / 1.68 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G5_agresif | 0.883 / 0.883 / **0.883** | 1.000 / 1.000 | 1.000 / 1.000 | 1.62 / 1.62 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G6_yumusak | 0.807 / 0.807 / **0.807** | 1.000 / 1.000 | 1.000 / 1.000 | 2.81 / 2.81 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G6_agresif | 0.618 / 0.618 / **0.618** | 0.684 / 0.684 | 0.959 / 0.959 | 8.40 / 8.40 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | 294 / 294 | 0 |
| G7_yumusak | 0.893 / 0.893 / **0.893** | 1.000 / 1.000 | 1.000 / 1.000 | 1.29 / 1.29 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G7_agresif | 0.847 / 0.847 / **0.847** | 1.000 / 1.000 | 1.000 / 1.000 | 1.66 / 1.66 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G1_kritik | 0.890 / 0.890 / **0.890** | 1.000 / 1.000 | 1.000 / 1.000 | 1.43 / 1.43 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| **G3_kritik** | 0.579 / 0.704 / **0.702** | 0.721 / 0.922 | 0.969 / 1.000 | 9.25 / 5.10 | 96.9% / 100.0% | 1 / 0 | 9 / 0 | 0/0 | 133 / yok | **293** |
| G4_kritik | 0.810 / 0.810 / **0.810** | 1.000 / 1.000 | 1.000 / 1.000 | 1.57 / 1.57 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G5_kritik | 0.862 / 0.862 / **0.862** | 1.000 / 1.000 | 1.000 / 1.000 | 1.70 / 1.70 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G7_kritik | 0.865 / 0.865 / **0.865** | 1.000 / 1.000 | 1.000 / 1.000 | 2.27 / 2.27 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 |
| G6_agresif_hedef | 0.662 / 0.662 / **0.662** | 0.915 / 0.915 | 1.000 / 1.000 | 7.54 / 7.54 | 97.3% / 97.3% | 1 / 1 | 8 / 8 | 0/0 | yok / yok | 0 |
| G6_agresif_durakli | 0.383 / 0.383 / **0.383** | 0.469 / 0.469 | 0.483 / 0.483 | 61.53 / 61.53 | 87.8% / 87.8% | 0 / 0 | 0 / 0 | 1/1 | 148 / 148 | 0 |

### sim (test1–test7)

| senaryo | IoU A3.8 / D2 / **D3** | @0.5 | @0.3 | merkez px | kilit | kesinti | kurt.max | IDsw | drift | açı aktif |
|---|---|---|---|---|---|---|---|---|---|---|
| test1 | 0.925 / 0.925 / **0.925** | 1.000 / 1.000 | 1.000 / 1.000 | 0.25 / 0.25 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 \* |
| test2 | 0.435 / 0.435 / **0.435** | 0.447 / 0.447 | 0.693 / 0.693 | 1.59 / 1.59 | 98.0% / 98.0% | 0 / 0 | 0 / 0 | 0/0 | 210 / 210 | 0 \* |
| test3 | 0.560 / 0.560 / **0.560** | 0.612 / 0.612 | 0.761 / 0.761 | 1.75 / 1.75 | 94.6% / 94.6% | 1 / 1 | 1 / 1 | 0/0 | 458 / 458 | 0 \* |
| test4 | 0.866 / 0.866 / **0.866** | 1.000 / 1.000 | 1.000 / 1.000 | 0.57 / 0.57 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 \* |
| test5 | 0.897 / 0.897 / **0.897** | 1.000 / 1.000 | 1.000 / 1.000 | 0.15 / 0.15 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 \* |
| test6 | 0.747 / 0.747 / **0.747** | 0.806 / 0.806 | 0.869 / 0.869 | 0.99 / 0.99 | 78.1% / 78.1% | 3 / 3 | 30 / 30 | 1/1 | 282 / 282 | 0 \* |
| test7 | 0.764 / 0.764 / **0.764** | 0.907 / 0.907 | 1.000 / 1.000 | 0.97 / 0.97 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | 0/0 | yok / yok | 0 \* |

### VisDrone

| senaryo | IoU A3.8 / D2 / **D3** | @0.5 | @0.3 | merkez px | kilit | kesinti | kurt.max | IDsw | drift | açı aktif |
|---|---|---|---|---|---|---|---|---|---|---|
| 0000117/23 | 0.701 / 0.701 / **0.701** | 0.974 / 0.974 | 1.000 / 1.000 | 5.51 / 5.51 | 100.0% / 100.0% | 0 / 0 | 0 / 0 | — | yok / yok | 0 \* |
| 0000268/31 | 0.000 / 0.000 / **0.000** | 0.000 / 0.000 | 0.000 / 0.000 | 383.61 / 383.61 | 71.0% / 71.0% | 0 / 0 | 0 / 0 | — | 151 / 151 | 0 \* |
| 0000182/127 | 0.088 / 0.088 / **0.088** | 0.000 / 0.000 | 0.099 / 0.099 | 265.66 / 265.66 | 30.7% / 30.7% | 2 / 2 | 2 / 2 | — | 39 / 39 | 0 \* |

\* VisDrone'da çekirdek içi sayaç loglanmıyor; metriklerin birebir aynı olması
tek başına kanıt — arama açılsaydı örnekleyici değişir, sayılar kayardı.

## Değişmezlik kanıtı

Alan alan (IoU, @0.5, @0.3, merkez hata, kilit, kesinti, kurtarma ort/max,
ID switch, drift; tolerans 1e-12):

* **Deney 3 vs A3.8: 30/32 senaryo farksız.** Değişen: G3_agresif, G3_kritik.
* **Deney 3 vs Deney 2: 30/32 farksız.** Değişen iki senaryoda da yalnızca
  `iou` ve `merkez_hata`; @0.5, @0.3, kilit, kesinti, kurtarma, drift Deney 2
  ile birebir aynı.
* sim test1–7 ve VisDrone ×3: **hepsi A3.8 ile birebir**.
* 22 Gazebo kaydının **20'sinde** açı araması hiç açılmadı.

## Performans

Dönüşümlü mikro-benchmark (3 tur, d2/d3 sırayla, tek çekirdek):

| | kapalı yol | açık yol (3 aday) |
|---|---|---|
| Deney 2 | 320 / 300 / 302 µs | 970 / 983 / 928 µs |
| Deney 3 | 299 / 306 / 367 µs | 975 / 1000 / 988 µs |

Fark ~%2, gürültü bandında. Kapalı yolda kod birebir aynı olduğu için ek
maliyet yapısal olarak sıfır. Tam koşum FPS'leri makine yüküyle 2 kata kadar
oynadığı için karar bu benchmark'a dayandırıldı.

## Kabul kriterleri

| # | kriter | sonuç |
|---|---|---|
| 1 | değişmeyen senaryo ≥ 30/32 | **GEÇTİ** (30/32) |
| 2 | G3_kritik drift yok | **GEÇTİ** (yok) |
| 3 | G3_kritik kilit %100 | **GEÇTİ** (%100) |
| 4 | **G3_kritik IoU ≥ 0.704** | **KALDI** (0.702, −0.002) |
| 5 | G3_agresif IoU ≥ 0.766 | **GEÇTİ** (0.768) |
| 6 | VisDrone / G4 / G5 / G6'da gereksiz açılma yok | **GEÇTİ** (0 kare) |
| 7 | FPS/latency bozulmadı | **GEÇTİ** (+%2, gürültü) |
| 8 | G3_agresif drift ≤ 0.010 °/kare | **GEÇTİ** (0.0043) |
| 9 | G3_agresif açı hatası p95 ≤ 3° | **GEÇTİ** (1.74°) |

**9 ölçütten 8'i geçti, 1'i %0.29'luk bir farkla kaldı.** Kural gereği
(“kriterlerden biri başarısız olursa tamamen geri al”) değişiklik geri alındı.

## Değerlendirme

Deney 3'ün **mekanizması doğrulandı**: ego referansı açı kaymasını 9 kat
(−0.0397 → −0.0043 °/kare), açı hatası p95'ini 7.5 kat (13.01° → 1.74°)
düşürdü ve bunu hiçbir yeni eşik eklemeden, 30/32 senaryoyu birebir koruyarak
yaptı. Ama **hedeflenen IoU kazancı gelmedi**: G3_agresif 0.789 yerine 0.768,
G3_kritik 0.002 geriledi.

Bu, Deney 2 teşhisinin bir varsayımını çürütüyor: açı hatası ile IoU arasındaki
korelasyon (−0.729) nedensel bir kaldıraç değil, ortak bir üçüncü değişkenin
gölgesiymiş. Ön ölçüm 2 o değişkeni işaret ediyor — **yama geometrisi**:
`boyut` eksen hizalı sınırlayıcı kutu olduğu için hedef döndükçe en-boy oranı
kilitten %12–26 (G3_agresif) / %24–44 (G3_kritik) sapıyor ve PSR 7 kata kadar
düşüyor. Açıyı düzeltmek bu sapmayı düzeltmiyor.

Karar verecek olan kullanıcıdır; iki seçenek net:
* **Eşiği gevşetme yok →** Deney 3 geri alınmış hâlde kalır (şu anki durum).
* **G3_kritik eşiği ≥0.700 olsaydı** Deney 3 tüm kriterleri geçerdi ve
  G3_agresif'te +0.008, açı hatasında 7.5 kat iyileşme kalıcı olurdu.

Bir sonraki deney adayı değişmedi: **örnekleme kutusunun kilit en-boy oranını
koruyup açıyla dönmesi** (ölçüldü: o durumda kestirim −60°…+60° arasında tam
doğru, PSR ~146). Ama bu `boyut` semantiğini, `rafine_kutu`'yu ve
`_boyut_sinirla`'yı birden etkiler; tek değişiklik değildir.
