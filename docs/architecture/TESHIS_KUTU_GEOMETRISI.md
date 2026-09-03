# Teşhis — örnekleme kutusu geometrisi (Deney 3 sonrası)

**Kod değişikliği yok, commit/push yok.** `takip/` Deney 2 halinde
(`cekirdekler.py` md5 `c0fd7989…`, `izleyici.py` md5 `4257b94c…`).
Ölçüm aracı: `gazebo/tani_geometri.py` — `HedefTakip` alt sınıfı + `rafine_kutu`
saydam sarması. Hiçbir eşik, hiçbir karar değişmedi.

## Kısa cevap

**"G3'teki IoU kaybını açıklayan temel değişken gerçekten örnekleme kutusunun
en-boy oranı mı?"**

Hipotez iki iddia taşıyordu; ölçümler ikisini ayırıyor:

* **(a) "En-boy sapması DCF'i bozuyor (PSR çöküyor, açı kestirimi kayıyor)" →
  ÇÜRÜDÜ.** Gerçek koşumda `corr(sapma, PSR)` **pozitif**: +0.090 (G3_agresif),
  +0.195 (G3_kritik). Beklenen negatifti.
* **(b) "Kutu şekli, dönen hedefin eksen hizalı GT kutusuna uymuyor" →
  DOĞRULANDI ve G3 ailesindeki EN BÜYÜK tek IoU terimi bu.**

Ama yön ters: kutu kilit oranında **tutulmamalı**, GT'yi **daha iyi izlemeli**.

## 1. Ölçülen geometri

| senaryo | kilit kutu | kilit oranı | kutu oranı min..max | \|sapma\| p50 / p95 | GT oranı min..max | GT \|sapma\| p95 |
|---|---|---|---|---|---|---|
| G3_yumusak | 56×28 | 2.00 | 1.72..2.13 | 3.3% / 7.8% | 1.83..2.37 | 19.9% |
| G3_agresif | 57×42 | 1.36 | 1.34..1.72 | 12.1% / 25.9% | 1.32..2.37 | 63.7% |
| G3_kritik | 50×55 | 0.91 | 0.89..1.42 | 23.9% / 44.4% | 0.85..2.35 | 132.2% |
| G4_kritik | 63×26 | 2.42 | 2.10..2.49 | 1.5% / 8.0% | 2.35..2.46 | 3.7% |
| G6_agresif | 57×39 | 1.46 | 1.46..2.17 | 20.3% / 42.0% | 1.48..2.42 | 24.0% |
| 0000117/23 | 44×55 | 0.80 | 0.80..1.82 | 63.1% / 110.7% | 0.75..1.45 | 42.4% |
| 0000268/31 | 132×135 | 0.98 | 0.43..0.43 | 56.2% / 56.2% | 1.56..2.82 | 43.9% |
| 0000182/127 | 12×11 | 1.09 | 0.93..2.07 | 10.5% / 80.4% | 0.93..1.36 | 21.2% |

VisDrone 268/31 ve 182/127 zaten yanlış kilitte (IoU 0.000 / 0.088); kutuları
patlamış (268/31'de h ≈ 290 px, GT h ≈ 7 px). Geometri sorusu için geçerli
örnek değiller, tabloda referans olarak duruyorlar.

## 2. (a) neden çürüdü — sentetik bulgu gerçek döngüye taşınmıyor

Deney 3 tasarım raporundaki ön ölçüm, **dondurulmuş** bir şablonla yapılmıştı:
kilit filtresi sabit, örnekleme kutusunun oranı saptırılıyor → PSR 144 → 19.5
(%12 sapma), kestirim −90° (%22 sapma).

Gerçek döngüde bu koşul **oluşmuyor**, çünkü şablon her karede `ogren` ile
yeniden öğreniliyor ve güncel orana uyum sağlıyor. Ölçülen:

* `corr(sapma, PSR)` = **+0.090** (G3_agresif), **+0.195** (G3_kritik) — pozitif
* kare-arası oran değişimi \|d\| p50 = **0.0000**
* (Deney 2 teşhisinden) `corr(arama adımı, d_oran)` = **−0.055**

Yani kilit-ile-şimdi arasındaki oran farkı DCF'e hiç yansımıyor; şablon zaten
oranı takip ediyor.

## 3. (b) neden doğrulandı — IoU açığının üç yollu ayrıştırması

Her karede takipçi kutusu sırayla düzeltiliyor: önce GT merkezine oturtuluyor,
sonra GT alanına, sonra GT oranına (son adım tanımı gereği IoU = 1.000).

| senaryo | gerçek IoU | +merkez | +alan | +oran | Δmerkez | Δalan | **Δoran** |
|---|---|---|---|---|---|---|---|
| G3_yumusak | 0.862 | 0.911 | 0.941 | 1.000 | +0.049 | +0.031 | **+0.059** |
| G3_agresif | 0.759 | 0.856 | 0.884 | 1.000 | +0.096 | +0.028 | **+0.116** |
| G3_kritik | 0.703 | 0.803 | 0.813 | 1.000 | +0.100 | +0.010 | **+0.187** |
| G4_kritik | 0.810 | 0.824 | 0.977 | 1.000 | +0.015 | +0.153 | **+0.023** |
| G6_agresif | 0.618 | 0.772 | 0.897 | 1.000 | +0.155 | +0.125 | **+0.103** |
| 0000117/23 | 0.701 | 0.806 | 0.836 | 1.000 | +0.106 | +0.030 | **+0.164** |
| 0000268/31 | 0.000 | 0.003 | 0.297 | 1.000 | +0.003 | +0.293 | **+0.703** |
| 0000182/127 | 0.087 | 0.314 | 0.868 | 1.000 | +0.227 | +0.554 | **+0.132** |

**En-boy artığı (Δoran) dönme genliğiyle tekdüze büyüyor: 0.059 → 0.116 → 0.187**
(G3_yumuşak → agresif → kritik). G3 ailesinde en büyük tek terim bu.
Merkezleme ikinci (0.049 → 0.096 → 0.100), alan üçüncü.

Karşılaştırma için: G4_kritik'te (dönme yok) baskın terim **alan** (0.153),
en-boy yalnızca 0.023 — kontrol olarak doğru davranıyor.

### Ama kilit oranına sabitlemek IoU'yu KÖTÜLEŞTİRİR

Şekil kehaneti (GT merkezli, aynı alan, yalnızca oran değiştiriliyor):

| senaryo | takipçi oranı | **kilit oranı** | GT oranı |
|---|---|---|---|
| G3_yumusak | 0.911 | 0.902 (−0.009) | 0.914 |
| G3_agresif | 0.856 | **0.823 (−0.033)** | 0.857 |
| G3_kritik | 0.803 | **0.779 (−0.024)** | **0.876 (+0.073)** |
| G6_agresif | 0.772 | 0.744 (−0.028) | 0.783 |
| 117/23 | 0.806 | **0.739 (−0.067)** | **0.857 (+0.051)** |

Kutunun oranı değişmesi bir **kusur değil, gereklilik**. Dönen aracın eksen
hizalı izdüşümü gerçekten oran değiştiriyor ve kutu onu izlemek zorunda.

## 4. Dört adaydan hangisi sapmayı üretiyor?

| aday | hüküm | kanıt |
|---|---|---|
| **1. Sabit boyutlu kutu** | değil | kutu adapte oluyor; sorun adaptasyonun **yetersizliği** |
| **2. `rafine_kutu`** | **ölçümü DOĞRU, suçlu değil** | `corr(rafine oranı, GT oranı)` = **0.991** (G3_agresif), **0.999** (G3_kritik); `rafine/GT` = **1.001 / 1.000**; aralığı GT ile birebir (0.84..2.35 vs 0.85..2.33) |
| **3. `_boyut_sinirla`** | **ELENDİ** | 7/8 senaryoda **0/293 kare** etkin; yalnızca zaten bozuk olan 182/127'de 4/334 |
| **4. Dönen kutu → eksen hizalı bbox** | **fiziksel sürücü** | GT oranı p95 sapması %63.7 (agresif) / %132.2 (kritik) |

### Kök neden: `_boyut_tazele`'nin aktarım hızı

Şekli uyarlayan **tek yol** `_boyut_tazele` ve bu bir birinci mertebe
alçak-geçirgen:

* `dogrulama_araligi = 4` → 4 karede bir ateşleniyor
* karışım `0.75·boyut + 0.25·rafine` → kazanç %25
* zaman sabiti ≈ 4 / 0.25 = **16 kare**

`boyut` değişiminin asama ayrıştırması (kare başına |dw|+|dh| px):

| senaryo | ego ölçek | **tazele** | kelepçe | tazele/kare | rafine boş döndü |
|---|---|---|---|---|---|
| G3_yumusak | 0.011 | **0.270** | 0.000 | 72/293 | 1 |
| G3_agresif | 0.017 | **0.365** | 0.000 | 62/293 | 11 |
| G3_kritik | 0.020 | **0.488** | 0.000 | 49/293 | 24 |
| G4_kritik | **0.782** | 0.641 | 0.000 | 73/293 | 0 |
| G6_agresif | 0.021 | **0.727** | 0.000 | 49/293 | 24 |

G3'te tazele ego ölçeğinin **20–24 katı**; G4'te (pitch) ego ölçeği baskın —
beklenen davranış.

### Alçak-geçirgen modeli ölçümle uyuşuyor

GT oran salınımının baskın periyodu FFT ile ölçüldü; 16 karelik zaman
sabitiyle beklenen genlik aktarımı ile karşılaştırıldı:

| senaryo | GT oranı periyodu | beklenen aktarım | **ölçülen aktarım** | fark |
|---|---|---|---|---|
| **G3_agresif** | 29.3 kare | 0.28 | **0.37** | +0.09 |
| **G3_kritik** | 29.3 kare | 0.28 | **0.35** | +0.07 |
| G3_yumusak | 41.9 kare | 0.38 | 0.76 | +0.37 |
| G6_agresif | 48.8 kare | 0.44 | 0.76 | +0.32 |

Dönmenin baskın olduğu iki senaryoda model ölçümü **±0.09 içinde** açıklıyor.
G3_yumuşak ve G6'da fazla sönüm öngörüyor — oradaki oran değişimi yalnızca
kamera dönmesinden gelmiyor (G6'da hedefin kendi dönüşü var), başka uyum
yolları da katkı veriyor.

**Sonuç: `rafine_kutu` doğru ölçüyor ama `_boyut_tazele` salınımın yalnızca
%35–37'sini kutuya aktarıyor.** Kalan %63–65 doğrudan Δoran terimi olarak
IoU'dan düşüyor.

Ek olarak `rafine_kutu` **sessizce boş dönüyor**: G3_agresif'te 11,
G3_kritik ve G6_agresif'te 24 kez — o tazeleme adımlarında hiç güncelleme yok.

## 5. Merkezleme terimi ayrı bir sorun

Δmerkez, G3'te 0.096–0.100 ve G6_agresif'te 0.155 ile ikinci büyük terim ve
**ne açıyla ne en-boy oranıyla açıklanıyor**:

* Deney 3'te açı hatası 7.5 kat düştü (p95 13.01° → 1.74°), merkez hatası
  yalnızca 3.81 → 3.52 px değişti.
* `corr(sapma, merkez_hata)` = +0.345 (agresif) / +0.617 (kritik) — ilişkili
  ama ikisi de dönme genliğiyle birlikte büyüdüğü için nedensellik kurulamaz.

Bu ayrı bir teşhis konusu; bu raporun kapsamında değil.

## 6. Sonraki deney için en az müdahaleli adaylar (uygulanmadı)

### A) En-boy oranını AÇIDAN analitik türet — *önerilen*

Dönen bir dikdörtgenin eksen hizalı kutusu kapalı formda bilinir:

    w = L·|cos α| + W·|sin α|
    h = L·|sin α| + W·|cos α|

Takipçi α'yı **zaten ölçüyor** (Deney 2'nin `aci`'si). Modelin GT'yi ne kadar
açıkladığı ölçüldü (α = pozlardan gelen gerçek görüntü dönmesi):

| senaryo | R² (w) | R² (h) | **R² (oran)** | uydurulan L × W |
|---|---|---|---|---|
| **G3_agresif** | 0.9989 | 0.9997 | **0.9995** | 52.8 × 22.1 px |
| **G3_kritik** | 0.9996 | 0.9999 | **0.9998** | 52.7 × 22.0 px |
| G4_kritik | ~0 | ~0 | ~0 | (kamera dönmesi yok) |
| G6_agresif | ~0 | ~0 | ~0 | (dönen kamera değil, hedef) |

Uydurma, aracın **gerçek** izdüşüm boyutunu geri buluyor (52.8 × 22.1 px;
fiziksel 4.6 m × 1.9 m → 51.1 × 21.1 px). Yani model doğru.

* **Gecikme sıfır** — alçak-geçirgen tamamen devre dışı kalır.
* **Yeni eşik yok** — L, W kilit kutusundan, α mevcut `aci`'den.
* **Patlama yarıçapı dar** — yalnızca açı araması açıkken; 30/32 senaryoda
  bit-birebir eşleşme korunur.
* **Sınırı:** yalnızca **kamera kaynaklı** dönmeyi kapsar. G6'daki hedefin
  kendi dönüşünü açıklamaz (R² ≈ 0) ve küçük açısal salınımda L, W, α₀
  ayrıştırılamaz (G3_yumuşak'ta uydurma çöküyor) — ama takipçi bunları
  uydurmaz, kilit kutusundan alır.

### B) `_boyut_tazele`'yi yalnızca açı araması açıkken hızlandır

`dogrulama_araligi` ve %25 karışım **mevcut parametreler**; yeni eşik gerekmez.
Açı kapısına bağlanırsa 30/32 senaryo yine bit-birebir kalır. Beklenen aktarım
%35 → %70–80. A'dan zayıf (hâlâ gecikmeli) ama kavramsal olarak daha küçük bir
değişiklik.

### C) `rafine_kutu`'nun boş dönmesini ele al

Koşum başına 11–24 sessiz atlama var. En ucuzu ama etkisi en küçüğü; tek
başına Δoran terimini kapatmaz.

## 7. Özet

* Hipotezin **DCF'i bozma** kısmı çürüdü — gerçek döngüde şablon oranı takip
  ediyor, PSR düşmüyor (korelasyon pozitif).
* Hipotezin **kutu şekli** kısmı doğrulandı — Δoran G3'te en büyük IoU terimi
  (0.116 / 0.187) ve dönme genliğiyle büyüyor.
* Kök neden `rafine_kutu` değil, **`_boyut_tazele`'nin 16 karelik zaman
  sabiti**: ölçüm doğru (korelasyon 0.99+), aktarım %35.
* `_boyut_sinirla` ve "sabit kutu" elendi; eksen hizalı bbox dönüşümü sorunun
  **kaynağı değil, izlenmesi gereken gerçeği**.
* En az müdahaleli çözüm adayı: en-boy oranını ölçmek yerine **açıdan
  türetmek** (R² = 0.9995 / 0.9998).
