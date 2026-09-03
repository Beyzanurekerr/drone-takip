# Deney 4A — kutu en-boyunu açıdan analitik türet

**Sonuç: BAŞARISIZ → tamamen geri alındı.** `takip/` altındaki altı dosyanın
md5'i Deney 2 durumuyla birebir eşleşiyor (`md5sum -c` ile doğrulandı) ve geri
alma sonrası G3_agresif 0.760 / G3_kritik 0.704 / G0 0.912 birebir geri geldi.
Commit/push yok. Geri alınan yama: `deney4a.patch` (212 satır).

## Uygulama öncesi bulunan engel ve düzeltmesi

Spesifikasyondaki `L/W = kilit kutusundan türetilen temel boyutlar` **geometrik
olarak çözümsüzdü**: kilit kutusu zaten bir AABB'dir, temel dikdörtgen değil.
Ölçüldü:

| senaryo | kilit kutusu | R²(w) | R²(h) | R²(oran) |
|---|---|---|---|---|
| G3_agresif | 57×42 | −86.3 | −18.1 | −3.24 |
| G3_kritik | 50×55 | −12.9 | −4.4 | −0.32 |
| G3_yumusak | 56×28 | −27.7 | −12.3 | −4.65 |

Kilit kutusu, aracın gerçek boyutuyla bilinmeyen kilit-anı yönelimini
karıştırıyor: G3_agresif'te gerçek araç 52.8 × 22.1 px ve α₀ = 24.8°, ve
AABB(24.8°) = 57.2 × 42.2 — yani gözlenen kilit kutusunun kendisi. Üç bilinmeyen
(L, W, α₀), kilit kutusundan iki denklem.

Kullanıcı onayıyla eksik skaler `cv2.minAreaRect` ile ölçüldü — `rafine_kutu`'nun
**zaten ürettiği** bağlantılı-bileşen maskesi üzerinde, kilit karesinde tek
ölçüm. Doğruluk:

| senaryo | ölçülen L / W / α₀ | beklenen | hata |
|---|---|---|---|
| G3_agresif | 53.7 / 23.1 / 24.9° | 52.8 / 22.1 / 24.8° | +0.9 px, +1.0 px, +0.1° |
| G3_kritik | 53.8 / 22.6 / 53.1° | 52.7 / 22.0 / 53.2° | +1.1 px, +0.6 px, −0.1° |

Yeni eşik eklenmedi (`minAreaRect` parametresizdir; kapısı olarak `rafine_kutu`'nun
mevcut `0.35 < oran.mean() < 2.6` denetimi kullanıldı).

## Uygulanan değişiklik

* `tespit.py`: maske hesabı `_leke()` yardımcısına çıkarıldı (davranış korunumlu
  yeniden düzenleme), üzerine `donuk_olcu()` eklendi → (L, W, α₀).
* `izleyici.py`:
  * `kilitle` — `rafine_kutu` başarılıysa `temel = (L, W)` ve `temel_aci = α₀`
  * `_boyut_analitik(olc)` — açı araması açıkken
    `w = L|cos a| + W|sin a|`, `h = L|sin a| + W|cos a|`, `a = α₀ + aci + dteta`
    (ego tohumu, bir kare gecikmeyi önlemek için)
  * `guncelle` — analitik yol devredeyse ego ölçeği `temel`e uygulanır
  * `_boyut_tazele` — analitik yol devredeyse atlanır
  * `_arama_adimi` — yeniden kilitte `temel = None` (bayatlamasın)

Durum makinesi, Kalman, ego-motion ve A3.8 yanlış-kilit doğrulaması değişmedi.

## Sonuçlar

### Deney 2 → Deney 4A

| | IoU | @0.5 | @0.3 | merkez px | kilit | kesinti | kurt.max | drift |
|---|---|---|---|---|---|---|---|---|
| G3_agresif A3.8 | 0.766 | 0.990 | 1.000 | 3.47 | 100% | 0 | 0 | yok |
| G3_agresif Deney 2 | 0.760 | 0.997 | 1.000 | 3.81 | 100% | 0 | 0 | yok |
| **G3_agresif Deney 4A** | **0.540** | **0.395** | 0.973 | **12.80** | 100% | 0 | 0 | yok |
| G3_kritik A3.8 | 0.579 | 0.721 | 0.969 | 9.25 | 96.9% | 1 | 9 | 133 |
| G3_kritik Deney 2 | **0.704** | 0.922 | 1.000 | 5.07 | 100% | 0 | 0 | yok |
| **G3_kritik Deney 4A** | **0.645** | **0.952** | 1.000 | **10.74** | 100% | 0 | 0 | yok |

Diğer 30 senaryo (sim ×7, VisDrone ×3, Gazebo ×20) **A3.8 ile birebir** —
`tespit.py` yeniden düzenlemesi davranış korunumlu çıktı ve açı araması
G4/G5/G6/VisDrone'da hiç açılmadı.

### Hipotez kontrolü — geometri modeli DOĞRU, ama yeterli değil

| senaryo | sürüm | takipçi oran p2p | GT oran p2p | izleme | **Δoran** |
|---|---|---|---|---|---|
| G3_agresif | Deney 2 | 0.381 | 1.043 | 37% | 0.116 |
| G3_agresif | **Deney 4A** | 1.786 | 1.043 | **171%** | **0.266** |
| G3_kritik | Deney 2 | 0.525 | 1.503 | 35% | 0.187 |
| G3_kritik | **Deney 4A** | 1.670 | 1.503 | **111%** | **0.084** |

* **G3_kritik: hipotez doğrulandı.** `_boyut_tazele` gecikmesi gerçekten ortadan
  kalktı (izleme %35 → %111) ve şekil artığı **yarıya indi** (0.187 → 0.084).
* **G3_agresif: ters tepti.** İzleme %171 — kutu artık GT'den *fazla* salınıyor,
  Δoran 0.116 → 0.266.

### Neden ters teptiği ölçüldü

| | Deney 2 | Deney 4A |
|---|---|---|
| G3_agresif açı hatası p50 / p95 | 8.90° / 13.01° | **28.71° / 53.23°** |
| G3_kritik açı hatası p50 / p95 | 2.40° / 7.69° | 4.27° / 12.18° |
| G3_agresif merkez hatası | 3.81 px | 12.80 px |
| G3_agresif PSR p50 | 54.3 | 48.5 |
| G3_agresif sıçrama p95 | 2.70 px | **0.39 px** |

PSR neredeyse değişmedi (54 → 48) ve sıçrama **küçüldü** — yani DCF hâlâ güvenle
bir tepe buluyor, ama giderek yanlış bir yerde. Bu, **bağımsız ölçümün
kaldırılmasının** imzasıdır:

Deney 2'de `boyut`, `rafine_kutu` ile **açıdan bağımsız** ölçülüyordu. Deney 4A'da
`boyut` açıdan **türetiliyor**. Böylece kapalı bir çevrim oluştu:

    aci -> boyut (sekil) -> yama geometrisi -> aday karsilastirmasi -> aci

Bir karedeki açı hatası kutunun şeklinde kalıcılaşıyor, o şekil bir sonraki
karenin aday karşılaştırmasını aynı yönde yanlılaştırıyor ve hata büyüyor.
G3_agresif'te açı hatası p95 13° → 53°'ye fırladı; kutu da onu takip ederek
GT'nin 1.7 katı salındı.

**`_boyut_tazele`'nin 16 karelik gecikmesi yalnızca bir gecikme değilmiş — açıdan
bağımsız tek ölçüm o'ymuş ve geometriyi çapalıyormuş.** Deney 1 (açık çevrim açı)
ve Deney 3 (ego referansı) ile aynı sınıf hata: türetilmiş bir büyüklüğün
bağımsız bir ölçümün yerine geçmesi.

### Gecikme

| hat | gecikme p95 D2 → D4A | FPS D2 → D4A |
|---|---|---|
| Gazebo | 5.56 → 4.51 ms | 322 → 348 |
| sim | 4.92 → 5.41 ms | 355 → 350 |
| VisDrone | 18.38 → 20.16 ms | 107 → 104 |

Tam koşum FPS'i makine yüküyle 2 kata kadar oynadığı için bu sayılar gürültü
bandındadır; analitik yol zaten `rafine_kutu` çağrısının yerine geçtiği için
maliyet artışı beklenmiyordu.

## Kabul kriterleri

| # | kriter | sonuç |
|---|---|---|
| 1 | değişmeyen senaryo ≥ 30/32 | **GEÇTİ** (30/32) |
| 2 | G3_kritik drift yok | **GEÇTİ** (yok) |
| 3 | G3_kritik kilit %100 | **GEÇTİ** (%100) |
| 4 | **G3_kritik IoU ≥ 0.704** | **KALDI** (0.645, −0.059) |
| 5 | **G3_agresif IoU ≥ 0.766** | **KALDI** (0.540, −0.226) |
| 6 | VisDrone/G4/G5/G6'da gereksiz açı araması yok | **GEÇTİ** (0 kare) |
| 7 | latency anlamlı bozulmadı | **GEÇTİ** (gürültü bandı) |

7 kriterden 5'i geçti, **2'si belirgin farkla kaldı**. Eşikler gevşetilmedi,
sonuç "kıl payı" sayılmadı; değişiklik tamamen geri alındı.

## Geri alma doğrulaması

```
md5sum -c  ->  takip/*.py  6/6 OK
G0          IoU 0.912  merkez 1.24  kilit 100.0%  drift yok
G3_agresif  IoU 0.760  merkez 3.81  kilit 100.0%  drift yok
G3_kritik   IoU 0.704  merkez 5.07  kilit 100.0%  drift yok
G4_kritik   IoU 0.810  merkez 1.57  kilit 100.0%  drift yok
```

## Sonraki adım için öneri (uygulanmadı)

Üç deney üst üste aynı dersi verdi: **türetilmiş bir büyüklük, bağımsız bir
ölçümün yerine geçtiğinde çevrim kapanıyor ve hata birikiyor.** Deney 1 (açı
ego'dan biriktirildi), Deney 3 (açı referansı ego'ya bağlandı), Deney 4A (şekil
açıdan türetildi) — üçü de bu sınıf.

Buna göre bir sonraki adayın **ölçümün yerine geçmemesi, ölçümü hızlandırması**
gerekir. En doğrudan biçimi, teşhis raporundaki **B adayı**:

> `_boyut_tazele`'yi yalnızca açı araması açıkken hızlandır — `dogrulama_araligi`
> ve %25 karışım **mevcut parametreler**, yeni eşik gerekmez.

Bu, `rafine_kutu`'nun açıdan bağımsız ölçümünü **korur** (çevrim kapanmaz),
yalnızca aktarım zaman sabitini 16 kareden düşürür. Deney 4A'nın ölçtüğü
şey bu adayın üst sınırını da veriyor: G3_kritik'te tam izleme Δoran'ı 0.187 →
0.084 yapıyor, yani şekil tarafında kazanılabilecek en fazla şey bu.

Ancak önce şunu teşhis etmek daha değerli olabilir: G3_agresif'te Deney 4A
merkez hatasını 3.81 → 12.80 px'e çıkardı, G3_kritik'te 5.07 → 10.74. Merkez
hatası zaten teşhis raporunda ikinci büyük terimdi (0.096–0.100) ve **ne açıyla
ne şekille açıklanıyordu**. Şekli mükemmelleştirmek IoU'yu kurtarmıyorsa,
sıradaki teşhis konusu merkez hatasının kaynağı olmalıdır.
