# Deney 4I — VisDrone veri / izlenebilirlik envanteri

**Salt okunur. `takip/` hiç değiştirilmedi** (md5 6/6 Deney 2 ile birebir),
commit/push yok. Ölçüm aracı: `gazebo/tani_visdrone.py`.

Amaç performans karşılaştırması değil; tek soru:

> **Hangi VisDrone dizileri Faz C deneylerinde güvenilir bağımsız gerçek veri
> kaynağı olarak kullanılabilir?**

Her dizi **kendi veri özellikleri üzerinden** değerlendirildi; 117/23 ölçüt
olarak alınmadı.

## Depodaki diziler ve hedef seçimi

Hedef, deponun kendi otomatik seçicisiyle belirlendi
(`veri/etiket.py:en_uygun_arac_track` — araç sınıfı, ≥30 kare,
skor = kare sayısı × toplam yer değiştirme):

| dizi | toplam track | **araç track** | otomatik seçim | koşum takımındaki mevcut |
|---|---|---|---|---|
| uav0000086_00000_v | 82 | **0** | **yok** | — |
| uav0000117_02622_v | 145 | 28 | 23 | 23 |
| uav0000137_00458_v | 180 | 44 | 12 | — |
| uav0000182_00000_v | 155 | 59 | 127 | 127 |
| uav0000268_05773_v | 52 | 44 | 31 | 31 |
| uav0000305_00000_v | 69 | 48 | 5 | — |
| uav0000339_00001_v | 75 | 23 | 49 | — |

Otomatik seçim, halen kullanılan üç dizide mevcut track ile **birebir aynı**
çıktı (23, 127, 31) — yani karşılaştırma tabanı değişmiyor.

## 1. Görüntü ve GT özellikleri

| dizi / track | ham | çözünürlük | kare | GT kare | **görünürlük** | kutu ort | w p5..p95 | h p5..p95 | göreli alan (ppm) | bozuk/NaN |
|---|---|---|---|---|---|---|---|---|---|---|
| 0000117/23 | 2720x1530 | 960x540 | 349 | 349 | **1.00** | 57×52 | 45..73 | 46..55 | 5768 | 0 |
| 0000137/12 | 2688x1512 | 960x540 | 233 | 227 | **0.97** | 73×66 | 50..123 | 46..100 | 9972 | 0 |
| 0000182/127 | 1344x756 | 960x540 | 363 | 341 | **0.94** | 24×21 | 19..36 | 16..34 | 1045 | 0 |
| 0000268/31 | 3840x2160 | 960x540 | 978 | 252 | **0.26** | 15×7 | 12..21 | 6..8 | 214 | 0 |
| 0000305/5 | 1904x1071 | 960x540 | 184 | 147 | **0.80** | 31×49 | 24..58 | 31..57 | 2919 | 0 |
| 0000339/49 | 1904x1071 | 960x540 | 275 | 272 | **0.99** | 50×24 | 49..51 | 24..25 | 2365 | 0 |

## 2. Üretilebilirlik ve takip davranışı

| dizi / track | kilitlendi | DCF karesi | PSR p50 / p5 | **rafine başarı** | IoU | kilit | kesinti | **drift** | **IoU≈0 oranı** |
|---|---|---|---|---|---|---|---|---|---|
| 0000117/23 | evet | 342 / 349 | 68.5 / 30.3 | **76.7%** | 0.701 | 100.0% | 0 | **yok** | **0%** |
| 0000137/12 | evet | 214 / 233 | 40.8 / 21.3 | **67.3%** | 0.548 | 94.6% | 1 | **75** | **0%** |
| 0000182/127 | evet | 126 / 363 | 31.2 / 4.8 | **50.0%** | 0.088 | 30.7% | 2 | **39** | **67%** |
| 0000268/31 | evet | 731 / 978 | 110.5 / 57.2 | **2.7%** | 0.000 | 71.0% | 0 | **151** | **100%** |
| 0000305/5 | evet | 116 / 184 | 82.0 / 38.0 | **93.5%** | 0.502 | 83.0% | 0 | **110** | **21%** |
| 0000339/49 | evet | 200 / 275 | 59.7 / 20.6 | **52.8%** | 0.064 | 74.4% | 3 | **6** | **65%** |

## 3. `rafine_kutu` varsayımı ve hedef ölçeği

| dizi / track | ayrım AUC | kontrast | köşegen ort | ölçek |
|---|---|---|---|---|
| 0000117/23 | 0.612 | 5.2 | 77.6 | 0.353 |
| 0000137/12 | 0.764 | 57.3 | 99.2 | 0.357 |
| 0000182/127 | 0.685 | 41.9 | 31.8 | 0.714 |
| 0000268/31 | 0.272 | -37.0 | 16.6 | 0.250 |
| 0000305/5 | 0.861 | 58.7 | 59.5 | 0.504 |
| 0000339/49 | 0.464 | -1.9 | 55.7 | 0.504 |

Ayrım AUC ve kontrast, `tespit.py:rafine_kutu`'nun dayandığı varsayımın
(hedef pikselleri yerel medyandan ayrılır) doğrudan ölçüsüdür.

---

## Kullanılabilirlik ölçütleri

Bir dizinin **deney kaynağı** olabilmesi için metriğin bir değişikliği
ayırt edebilmesi gerekir. Ölçütler (her biri veriden ölçülür):

| # | ölçüt | eşik | gerekçe |
|---|---|---|---|
| Ö1 | araç track'i var mı | ≥1 | hedef yoksa dizi konu dışı |
| Ö2 | GT görünürlüğü | ≥ 0.70 | GT yoksa ölçüm yok |
| Ö3 | DCF karesi / toplam kare | ≥ 0.70 | takipçi karelerin çoğunda ARAMA/KAYIP'taysa ölçülen şey takip değil |
| Ö4 | IoU ≈ 0 olan kare oranı | ≤ 0.25 | metrik başarısızlıkta doygunsa değişikliği ayırt edemez |
| Ö5 | bozuk/NaN kare | 0 | — |

Ö4 keyfi değil: Deney 1'de ölçüldü — doygun/marjinal senaryolarda anlamca
aynı bir işlem değişimi IoU'yu 0.435 → 0.686 oynatabiliyor (kaotik).

## Dizi dizi hüküm

### uav0000086_00000_v — **KULLANILAMAZ**
82 track var ama **araç sınıfından track yok** (Ö1). `en_uygun_arac_track`
`EtiketHatasi` atıyor. Bu bir yaya dizisi; projenin konusu tek araç takibi.

### 117/23 — **GÜVENİLİR**
349 kare, GT 349 (**görünürlük 1.00**), kutu 57×52, 342/349 karede DCF üretimi
(0.98), PSR p50 68.5, kilit %100, drift yok, **IoU≈0 oranı %0**. Beş ölçütü de
geçiyor.
*Uyarı:* kontrast yalnızca **5.2** ve ayrım AUC 0.612 → bu dizide
`rafine_kutu` güvenilmez (%76.7 başarı ama merkezi 4.78 px hatalı, 4C/4D).
Yani dizi **takip deneyleri için** güvenilir, **rafine türevli büyüklükler
için değil**.

### 137/12 — **GÜVENİLİR (yeni)**
233 kare, GT 227 (0.97), kutu 73×66 — en büyük hedef. 214/233 DCF (0.92),
PSR 40.8, rafine %67.3, IoU 0.548, kilit %94.6, **IoU≈0 oranı %0**.
75. karede drift var ama hedeften tamamen kopmuyor (IoU≈0 hiç olmuyor) →
metrik iki yöne de duyarlı. Kontrast **57.3**, ayrım AUC 0.764.

### 305/5 — **SINIRDA KULLANILABILIR**
184 kare (en kısa), GT 147 (0.80), kutu 31×49, rafine başarısı **%93.6**
(en yüksek), kontrast **58.7** ve ayrım AUC **0.861** (en yüksek).
Ama DCF karesi 116/184 = **0.63** (Ö3'ün altında), 110. karede drift ve
IoU≈0 oranı %21. Kullanılabilir ama kısa ve gürültülü; **tek başına karar
dayanağı yapılmamalı**.

### 182/127 — **KULLANILAMAZ**
Ö3 ve Ö4'ü ihlal ediyor: DCF karesi 126/363 = **0.35** (takipçi karelerin
üçte ikisinde ARAMA/KAYIP'ta) ve **IoU≈0 oranı %67**. 39. karede drift,
kilit %30.7, IoU 0.088.
GT sağlam (görünürlük 0.94) ve kontrast makul (41.9) — sorun veri değil,
takipçinin 24×21 px'lik hedefte erken kopması. Metrik başarısızlıkta doygun,
bir değişikliği ayırt edemez. (Deney 1'de zaten kaotik olarak işaretlenmişti.)

### 268/31 — **KULLANILAMAZ (dört bağımsız gerekçeyle)**
1. **Görünürlük 0.26** — 978 karenin yalnızca 252'sinde GT var (Ö2 ihlali).
2. Hedef **15×7 px**, göreli alan 214 ppm — deponun kendi ölçtüğü
   `renk_dcf` alt sınırının (9.0×3.7 px) hemen üstünde, doku yok.
3. **Kontrast −37.0**, ayrım AUC **0.272** (şanstan kötü) — `rafine_kutu`
   varsayımı burada **tersine dönmüş**; başarı oranı **%2.66**.
4. **IoU≈0 oranı %100** — ölçülen 252 karenin hepsinde IoU sıfır; 151. karede
   drift. Metrik tamamen doygun.

### 339/49 — **KULLANILAMAZ**
GT sağlam (görünürlük 0.99, kutu 50×24) ama takipçi **6. karede** drift ediyor
ve **IoU≈0 oranı %65**, IoU 0.064. Kontrast **−1.9**, ayrım AUC 0.464
(şanstan kötü). Ö4 ihlali; metrik başarısızlıkta doygun.

---

## Özet tablo

| dizi / track | Ö1 araç | Ö2 görünürlük | Ö3 DCF oranı | Ö4 IoU≈0 | Ö5 bozuk | **hüküm** |
|---|---|---|---|---|---|---|
| 086 | **0** ✗ | — | — | — | — | **KULLANILAMAZ** |
| **117/23** | 28 ✓ | 1.00 ✓ | 0.98 ✓ | %0 ✓ | 0 ✓ | **GÜVENİLİR** |
| **137/12** | 44 ✓ | 0.97 ✓ | 0.92 ✓ | %0 ✓ | 0 ✓ | **GÜVENİLİR** |
| 305/5 | 48 ✓ | 0.80 ✓ | **0.63** ✗ | %21 ✓ | 0 ✓ | **SINIRDA** |
| 182/127 | 59 ✓ | 0.94 ✓ | **0.35** ✗ | **%67** ✗ | 0 ✓ | **KULLANILAMAZ** |
| 268/31 | 44 ✓ | **0.26** ✗ | 0.75 ✓ | **%100** ✗ | 0 ✓ | **KULLANILAMAZ** |
| 339/49 | 23 ✓ | 0.99 ✓ | 0.73 ✓ | **%65** ✗ | 0 ✓ | **KULLANILAMAZ** |

## Beklenmedik ve önemli bir yan bulgu

Mevcut üçlü **kontrast bakımından dejenereydi**: 117/23 = 5.2, 182/127 = 41.9,
268/31 = −37.0 — ve ikisi zaten kullanılamaz. Yani Faz C boyunca gerçek veri
tarafı fiilen **tek noktadan** (kontrast 5.2) ibaretti.

Yeni havuz bu ekseni **kapsıyor**:

| dizi | kontrast | ayrım AUC |
|---|---|---|
| 117/23 | **5.2** | 0.612 |
| 137/12 | **57.3** | 0.764 |
| 305/5 | **58.7** | 0.861 |
| *(Gazebo G3 karşılaştırma)* | *47.7–79.8* | *0.699–0.738* |

137/12 ve 305/5 **Gazebo bandında** kontrasta sahip. Bu, 4C/4D/4E/4H'de
gözlenen Gazebo↔VisDrone tersine dönüşünün gerçekten kontrasttan mı yoksa
"sentetik vs gerçek" ayrımından mı geldiğini ilk kez **ayırt edilebilir**
kılıyor — çünkü artık yüksek kontrastlı *gerçek* veri var.

Not: 182/127 kontrastı 41.9 olmasına rağmen kullanılamıyor → kontrast tek
başına izlenebilirliği belirlemiyor; hedef boyutu (24×21 px) da belirleyici.

---

# Cevaplar

**Kaç VisDrone dizisi güvenilir?**
**2 tam güvenilir + 1 sınırda.** (7 dizinin 4'ü kullanılamaz.)

**Hangileri güvenilir?**
* **117/23** — 349 kare, görünürlük 1.00, kilit %100, drift yok, IoU≈0 %0
* **137/12** — 233 kare, görünürlük 0.97, kilit %94.6, IoU≈0 %0 *(yeni)*
* **305/5** — sınırda: DCF oranı 0.63 ve yalnızca 184 kare; destekleyici
  kullanılabilir, tek başına karar dayanağı olmamalı *(yeni)*

**Hangileri neden kullanılamaz?**
* **086** — araç sınıfından hiç track yok (0/82)
* **182/127** — takipçi karelerin %65'inde ARAMA/KAYIP'ta, ölçülen karelerin
  %67'sinde IoU≈0; metrik doygun
* **268/31** — GT yalnızca karelerin %26'sında; hedef 15×7 px; kontrast −37.0
  ve ayrım AUC 0.272 (şanstan kötü); rafine başarısı %2.66; IoU≈0 %100
* **339/49** — 6. karede drift, IoU≈0 %65, kontrast −1.9; metrik doygun

**Bundan sonraki deneyler için gerçek veri havuzu hangisi?**

> **Birincil: 117/23 + 137/12.**
> **Destekleyici: 305/5** (raporlanır, tek başına karar verdirmez).
> **Karar dışı: 182/127, 268/31, 339/49, 086** — bunlar yalnızca "çökmedi mi"
> kontrolü olarak okunmalı, IoU değerleri kanıt sayılmamalı.

Bu, gerçek veri tarafını **tek diziden ikiye** çıkarıyor ve — daha önemlisi —
kontrast eksenini kapsayan bir havuz veriyor. Faz C'nin şimdiye kadarki
kararları (4C, 4E, 4H) tek dizinin sonucuyla yön değiştirmişti; bu havuzla
gelecek deneyler **iki bağımsız gerçek dizide** doğrulanabilir.

**Hiçbir optimizasyon uygulanmadı.**
