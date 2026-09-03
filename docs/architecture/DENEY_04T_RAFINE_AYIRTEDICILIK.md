# Deney 4T — Bozuk `rafine_kutu` çıktısı mevcut sinyallerle ayırt edilebiliyor mu?

**Tamamen salt okunur. Takipçi KOŞTURULMADI**; yalnızca `cikti/rafine_4n.json`
(Deney 4N) ve `cikti/boyut_4r.json` (Deney 4R) kare numarasıyla eşleştirildi.
`takip/` altında hiçbir dosya değişmedi, hiçbir eşik takipçiye uygulanmadı,
commit/push yok. Araç: `gazebo/tani_4t_ayirtedici.py`. Çıktı:
`cikti/ayirtedici_4t.json`. **`takip/` md5 6/6 Deney 2 baseline'ı ile aynı.**

## 0. Tanımlar — yeni sabit icat edilmedi

**"Bozuk" etiketi:** dönen rafine kutusu, deponun **kendi bandının**
(`izleyici.py:549`, `[0.60, 1.70]`) dışında kalıyorsa:
`rafine_w/GT_w` ya da `rafine_h/GT_h` < 0.60 veya > 1.70.

**Sinyal seçimi:** yalnızca **koşum anında erişilebilir** büyüklükler.
GT gerektiren hiçbir şey sinyal olarak kullanılmadı
(`bilesen_gt_iou`, `bilesen_alan_orani`, `gt_pencere_orani` yalnızca *etiket*
tarafında).

**Kapsam sınırı (dürüstçe):** 4N'in iç büyüklükleri (renk mesafesi, maske
doluluğu, bileşen sayısı, p82) yalnızca `G6_agresif`, `G6_agresif_durakli`,
`117/23`, `137/12` için kayıtlıdır. `182/127` ve `305/5` için yalnızca 4R'nin
sinyalleri (rafine/boyut oranları) var. Takipçiyi koşturmak yasak olduğu için
eksik kayıt tamamlanmadı.

## 1. Örneklem

| kaynak | `_boyut_tazele`'ye ulaşan çağrı | **bozuk** | oran |
|---|---:|---:|---:|
| 117/23 | 65 | 4 | %6 |
| G6_agresif | 49 | 4 | %8 |
| **G6_agresif_durakli** | 32 | **0** | **%0** |
| 137/12 | 36 | 11 | %31 |
| 305/5 | 27 | 6 | %22 |
| 182/127 | 16 | 12 | %75 |
| **toplam** | **225** | **37** | %16 |

`G6_agresif_durakli`'de **hiç bozuk rafine yok** — 4R/4S'in "orada sorun boyut
değil merkez" hükmüyle tutarlı; o kaynakta ayırt edicilik tanımsızdır.

## 2. Kaynak içi tek değişkenli ayırt edicilik (ROC-AUC)

En iyi üç sinyal, kaynak kaynak:

| kaynak | 1. | 2. | 3. |
|---|---|---|---|
| **182/127** | `enboy_fark` **0.979** | `log_oran_buyukluk` 0.812 | `olculen_log_buyukluk` 0.792 |
| **305/5** | `oran_ort` **0.992** | `oran_h` 0.897 | `enboy_fark` 0.889 |
| **G6_agresif** | `oran_w` **1.000** | `log_oran_buyukluk` 0.978 | `oran_ort` 0.972 |
| 137/12 | `bilesen_alan_pencere` **0.982** | `oran_ort` 0.960 | `log_oran_buyukluk` 0.836 |
| G6_agresif_durakli | — (tek sınıflı) | | |

**Kaynak içinde sinyal vardır ve güçlüdür** (0.84–1.00).

**4N'in iç büyüklükleri ayırt edici DEĞİL.** Ölçülebilen iki kaynakta:
`renk_mesafe` AUC 0.594, `n_bilesen` 0.678, `maske_doluluk` 0.800,
`p82` 0.750 — hepsi boyut oranının (1.000) altında. Yani bozuk kutuyu ele
veren şey rengin ya da segmentasyonun iç göstergeleri değil, **kutunun mevcut
boyuta oranıdır**.

## 3. Havuzda ve kaynaklar arasında — asıl sınav

Dört sinyal her kaynakta aynı tanımla mevcut (`bilesen / boyut`):

| sinyal | **havuz AUC** | en iyi çalışma noktası | TPR | FPR |
|---|---:|---:|---:|---:|
| `oran_w` | 0.671 | ≥ 1.31 | 0.49 | 0.04 |
| `oran_h` | 0.628 | ≥ 1.21 | 0.46 | 0.07 |
| `oran_ort` | 0.747 | ≥ 1.12 | 0.73 | 0.12 |
| **`log_oran_buyukluk`** = \|log oran_w\| + \|log oran_h\| | **0.890** | ≥ 0.40 | **0.84** | **0.13** |

**Yönlü sinyaller havuzda çöküyor, yönsüz olan ayakta kalıyor.** Nedeni
ölçüldü: 182/127'de bozuk kutular **küçük** (eşik ≤ 0.94), diğerlerinde
**büyük** (≥ 1.12…1.84) — işaret ters. Tek yönlü bir kapı iki aileyi birden
yakalayamaz; simetrik (iki taraflı) bir kapı yakalayabilir.

### Eşik aktarımı (LOSO): eşik bir kaynakta seçilip diğerlerinde sınandı

`log_oran_buyukluk` için:

| eğitim kaynağı | eşik | test sonuçları (TPR / FPR) |
|---|---:|---|
| **137/12** | 0.42 | 117/23 **1.00**/0.08 · G6_agresif **1.00**/0.07 · 305/5 0.83/0.29 · 182/127 0.67/0.25 |
| 117/23 | 0.56 | G6_agresif 1.00/0.02 · 305/5 0.83/0.10 · 137/12 0.55/0.12 · 182/127 0.50/0.25 |
| 305/5 | 0.62 | G6_agresif 1.00/0.02 · 137/12 0.55/0.08 · 182/127 0.50/0.25 · 117/23 0.50/0.00 |
| G6_agresif | 1.07 | 137/12 **0.00**/0.00 · 305/5 **0.17**/0.00 · 182/127 0.25/0.25 |
| 182/127 | 0.08 | hepsinde TPR 1.00 ama **FPR 0.74–0.92** (dejenere: çağrılarının %75'i bozuk) |

> Aktarım **eğitim kaynağına bağlı**: 137/12'den seçilen eşik dört kaynakta
> iyi çalışıyor (TPR 0.67–1.00, FPR 0.07–0.29); G6_agresif'ten seçilen eşik
> ise TPR'yi 0.00–0.25'e düşürüyor. Tek küresel eşik **her kaynakta yüksek
> TPR vermiyor**.

## 4. Asıl bulgu: doğru değişken zaten kodda var, kapı çok geniş

`tespit.py:122`'deki mevcut kapı **tam olarak bu değişkeni** kullanıyor:

```
oran = np.array([bw, bh], np.float32) / np.maximum(boyut, 1.0)
if not (0.35 < oran.mean() < 2.6):
    return None
```

Bu kapının 225 çağrı üzerindeki fiili performansı:

| kaynak | bozuk | **R4'ün geçirdiği bozuk** | R4'ün reddettiği iyi |
|---|---:|---:|---:|
| G6_agresif | 4 | **4/4 (%100)** | 0/45 |
| 137/12 | 11 | **11/11 (%100)** | 0/25 |
| 117/23 | 4 | **4/4 (%100)** | 0/61 |
| 305/5 | 6 | **6/6 (%100)** | 0/21 |
| 182/127 | 12 | **12/12 (%100)** | 0/4 |
| G6_agresif_durakli | 0 | — | 0/32 |
| **HAVUZ** | **37** | **37/37 (%100)** | **0/188** |

> **Mevcut kapı bozuk kutuların HEPSİNİ geçiriyor.** `[0.35, 2.6]` bandı bu
> arıza kipi için fiilen inerttir — 4S'te `_boyut_sinirla` için ölçülen
> yapının aynısı.

### Karşıt-olgu (UYGULANMADI): deponun kendi `[0.60, 1.70]` bandı, iki eksende ayrı

| kaynak | TPR (yakalanan bozuk) | FPR (yanlışlıkla reddedilen iyi) |
|---|---:|---:|
| G6_agresif | **4/4 = 1.00** | 1/45 = 0.02 |
| 305/5 | 5/6 = 0.83 | 3/21 = 0.14 |
| 117/23 | 2/4 = 0.50 | 0/61 = 0.00 |
| 182/127 | 6/12 = 0.50 | 1/4 = 0.25 |
| 137/12 | 5/11 = 0.45 | 1/25 = 0.04 |
| G6_agresif_durakli | — (bozuk yok) | 0/32 = 0.00 |
| **HAVUZ** | **22/37 = 0.59** | **6/188 = 0.03** |

Yeni sabit yok: hem değişken (`oran`) hem band (`[0.60, 1.70]`) depoda zaten
var; değişen tek şey bandın **ortalamaya değil iki eksene ayrı** uygulanması
ve `[0.35, 2.6]` yerine mevcut dar bandın kullanılması.

---

# HÜKÜM: **KISMEN_KAPILAN**

* **Sinyal var ve doğru değişken zaten kodda.** Kaynak içi AUC 0.84–1.00;
  yönsüz `log_oran_buyukluk` havuzda AUC **0.890** (TPR 0.84 / FPR 0.13).
  Bozuk kutuyu ele veren şey renk/segmentasyon iç göstergeleri değil
  (AUC 0.59–0.80), **kutunun mevcut boyuta oranıdır** — yani `tespit.py:122`
  kapısının kendi değişkeni.
* **Ama tek küresel eşik her kaynakta yüksek TPR vermiyor.** İşaret kaynağa
  göre ters dönüyor (182/127 küçültme, diğerleri büyütme) ve LOSO aktarımı
  eğitim kaynağına göre TPR 0.00–1.00 arasında değişiyor.
* **Mevcut kapı ise hiç çalışmıyor:** bozuk kutuların **%100'ünü** geçiriyor,
  iyi kutuların %0'ını reddediyor.

Yani "mevcut sinyalle kapılan" demek fazla iyimser, "rafine üretim sorunu"
demek ise ölçülene aykırı: sinyal mevcut ve depoda zaten hesaplanıyor, eksik
olan kapının **darlığı** ve **iki eksene ayrı** uygulanması.

### Sonraki TEK müdahale adayı — artık teşhis değil, müdahale + regresyon

> **`tespit.py:122`'deki mevcut kapıyı, deponun kendi `[0.60, 1.70]` bandıyla
> ve iki eksende AYRI uygula** (bugün `0.35 < oran.mean() < 2.6`).
> Tek satırlık, **yeni sabit içermeyen** bir değişiklik; beklenen etkisi bu
> deneyde ölçüldü: bozuk kutuların **%59'u reddedilir**, iyi kutuların
> **%3'ü** kaybedilir.
>
> **Zorunlu regresyon kapsamı ve asıl risk:** bir rafine reddedildiğinde
> `_boyut_tazele` erken döner ve **boyut donar** — 4N/4R'de G6_agresif'in
> 104 px'te donmasının kipi budur. Yani müdahale "bozuk ölçümle şişme" ile
> "ölçümsüz bayatlama" arasında bir takas yapar ve iyileşme **varsayılamaz**.
> A/B, `deney.py` ile karar kümesinde koşulmalı: **117/23 + 137/12**
> (birincil), **305/5** (destekleyici), **G3_agresif / G3_kritik / G0**
> (Gazebo çapası), ve boyut serisi `gazebo.tani_4r_boyut` ile yeniden
> ölçülmelidir. Kabul ölçütü öncesinde yazılmalı; 182/127, 268/31, 339/49
> 4I'ya göre karar dışıdır.

**Bu turda hiçbir eşik takipçiye uygulanmadı; `takip/` md5 6/6 aynı.**
