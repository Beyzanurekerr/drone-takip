# Deney 4Q — 4P mekanizması yanlış kilitlerin ne kadarını açıklıyor?

**Salt okunur. `takip/` altında hiçbir dosya değiştirilmedi**, hiçbir eşik /
Kalman / DCF / padding / lr / şablon / geometri değişmedi, yeni eşik icat
edilmedi, commit/push yok. Yalnızca **mevcut kayıtlar** ve mevcut takipçi
çıktısı analiz edildi.
Araç: `gazebo/tani_4q_konjonksiyon.py`. Çıktı: `cikti/konjonksiyon_4q.json`,
`cikti/konjonksiyon_4q_drift.json`.

`takip/` md5'leri Deney 2 durumuyla **6/6 aynı** (deney öncesi = sonrası):

```
d41d8cd98f00b204e9800998ecf8427e  takip/__init__.py
c0fd7989d4e81219cd99447a12f8d78b  takip/cekirdekler.py
959da09ab43501a983629368a8f699b1  takip/egomotion.py
4257b94ce7f4978e172b8bb7c89816c1  takip/izleyici.py
874b3ccd540c8a6c783320c619a78f41  takip/mosse.py
3ff48dd869374d36937c18b640f2b21b  takip/tespit.py
```

## 0. Yöntem ve tek metodolojik düzeltme

Yanlış-kilit (YK) tanımı **4L'nin**: `durum == KILITLI` ve `IoU == 0`.
Ölçüm atomları **4O'nun**, çekim noktası yöntemi **4P'nin**. Yeni eşik yok.

4P'de nedensel olarak doğrulanan imza üç bileşenlidir:
**(i)** hedef dışında bir nesne DCF penceresine giriyor **ve mesafe kapanıyor**;
**(ii)** DCF çekim noktası GT'den tek yönlü uzaklaşıyor;
**(iii)** KF hızı çöküyor ve PSR düşüyor.
DCF penceresi `boyut × dolgu(2.0)` olduğundan arama merkezine göre
yarı-genişlik = `boyut_w`, yarı-yükseklik = `boyut_h`.

**Düzeltme:** ilk çözümleme YK epizodunun başına çapalandı ve dört dizide
epizot öncesi 20 karenin **zaten IoU ≈ 0** olduğu görüldü — yani epizot başı
arızanın anı değil, takipçinin KILITLI'yi yeniden ilan ettiği andır. Bu yüzden
çözümleme **`t_drift`** (IoU'nun ilk kez sürekli düştüğü kare) çapasıyla
tekrarlandı; aşağıdaki hükümler bu ikinci çapaya dayanır.

VisDrone'da "çeldirici" GT'si yok sanılıyordu (`gazebo/tani.py:301` notu); ama
`VisDroneVidKaynak.kare_etiketleri` **karedeki tüm etiketleri** ölçekli verir.
Bu deneyde hedef dışındaki en yakın etiketli nesne oradan ölçüldü — yani
mekanizma gerçek veride de sınanabildi.

## 1. Koşum düzeyinde envanter (22 Gazebo + 6 VisDrone)

`en yakın` = koşum boyunca hedef dışındaki en yakın GT nesnesinin merkez
mesafesi. `pencerede` = o nesnenin DCF penceresi içinde olduğu kare oranı.

| kaynak | YK | epizot | **en yakın (px)** | **pencerede** |
|---|---:|---:|---:|---:|
| G0, G1×3, G2×2, G3×3, G4×3, G5×3, G7×3 (18 senaryo) | %0.0 | 0 | 49.8–55.0 | %0–5 |
| G6_yumusak | %0.0 | 0 | 38.8 | %0 |
| **G6_agresif** | **%0.0** | 0 | **11.3** | **%18** |
| **G6_agresif_hedef** | **%0.0** | 0 | **11.6** | **%18** |
| **G6_agresif_durakli** | **%44.6** | 1 | **1.5** | **%34** |
| **117/23** | **%0.0** | 0 | **28.9** | **%70** |
| 137/12 | %0.5 | 1 | 33.3 | %79 |
| 182/127 | %61.2 | 1 | 27.1 | %0 |
| 268/31 | %100.0 | 1 | 2.3 | %0 |
| 305/5 | %9.4 | 1 | 30.2 | %1 |
| 339/49 | %59.1 | 1 | 1.1 | %29 |

İki **negatif kontrol** hemen görülüyor:

* **117/23**: karelerin **%70'inde** başka bir nesne DCF penceresinin içinde,
  en yakını 28.9 px — ve **hiç yanlış kilit yok**.
* **G6_agresif / G6_agresif_hedef**: çeldirici 11.3 / 11.6 px'e kadar
  yaklaşıyor, %18 kare pencerede — **hiç yanlış kilit yok**.

> Yani "başka bir nesne DCF penceresinde" tek başına hiçbir şey açıklamıyor.
> 4P'nin geometrisi çok daha uçtur: **1.5 px ve Δy ≈ 0 (aynı görüntü satırı)**.

## 2. Epizot epizot: `t_drift` öncesi 14 kare

### G6_agresif_durakli — drift 148 · **TAM İMZA**

| kare | IoU | çekim−GT | dx | KF hızı | PSR | en yakın: mesafe / Δx / Δy | pencerede |
|---:|---:|---:|---:|---:|---:|---|---|
| 134 | 0.72 | −4.42 | −0.155 | 2.25 | 22.2 | 46.7 / +46.6 / −3.1 | EVET |
| 138 | 0.64 | −7.26 | −0.014 | 1.98 | 23.9 | 29.7 / +29.6 / −0.7 | EVET |
| 141 | 0.61 | −8.23 | +0.044 | 2.09 | 27.3 | 18.3 / +18.3 / **+0.4** | EVET |
| **142** | 0.58 | **−9.85** | **−0.314** | 1.74 | 25.7 | **14.7** / +14.6 / **+0.6** | EVET |
| 144 | 0.50 | −13.39 | −0.325 | **0.89** | 19.2 | 7.7 / +7.7 / +1.0 | EVET |
| 146 | 0.42 | −16.45 | +0.005 | **0.52** | **10.5** | **1.5** / +1.1 / +1.1 | EVET |
| 147 | 0.39 | **−27.24** | +0.110 | **0.51** | **6.7** | 2.0 / −1.7 / +1.1 | EVET |

(i) ✓ mesafe 46.7 → 1.5 px, Δy −3.1 → +1.1 (satır hizalanıyor) · (ii) ✓ çekim
−4.42 → −27.24 · (iii) ✓ KF 2.25 → 0.51, PSR 22.2 → 6.7. **AÇIKLANAN.**

### 137/12 — drift 75 · **KISMEN**

| kare | IoU | çekim−GT | dx | KF hızı | PSR | en yakın: mesafe / Δy | pencerede |
|---:|---:|---:|---:|---:|---:|---|---|
| 61 | 0.52 | −10.34 | +0.046 | 2.13 | 42.8 | 38.3 / +22.7 | EVET |
| 67 | 0.41 | −19.84 | +0.174 | 1.97 | 21.6 | 39.1 / +37.7 | EVET |
| 74 | 0.32 | −30.33 | +0.166 | 1.85 | 21.7 | **42.1** / +35.2 | EVET |

(i) **✗** — nesne pencerede ama mesafe **kapanmıyor, açılıyor** (38.3 → 42.1)
ve ayrı satırda (Δy +23…+39) · (ii) ✓ çekim −10.3 → −30.3 · (iii) kısmî
(PSR 42.8 → 21.7 düşüyor, KF hızı 2.13 → 1.85 **çökmüyor**).
Çekim noktası kayıyor ama **konjonksiyon olmadan**. **KISMEN AÇIKLANAN.**

### 182/127 — drift 39 · **AÇIKLANAMAYAN**

| kare | IoU | çekim−GT | KF hızı | PSR | en yakın: mesafe | pencerede |
|---:|---:|---:|---:|---:|---:|---|
| 25 | 0.45 | +0.32 | 0.09 | 40.7 | 150.2 | hayır |
| 33 | 0.38 | −0.23 | 0.28 | 33.8 | 148.5 | hayır |
| 38 | 0.30 | +1.50 | 0.33 | 28.8 | 146.8 | hayır |

(i) ✗ (en yakın nesne **146–150 px**, pencerede hiç değil) · (ii) ✗ (çekim
noktası **+0.3 … +1.5 px'te sabit**) · (iii) ✗. Hiçbiri yok.

### 305/5 — drift 110 · **AÇIKLANAMAYAN**

| kare | IoU | çekim−GT | KF hızı | PSR | en yakın: mesafe | pencerede |
|---:|---:|---:|---:|---:|---:|---|
| 96 | 0.47 | −3.23 | 3.46 | 59.3 | 99.6 | hayır |
| 104 | 0.55 | −1.33 | 3.06 | 63.3 | 98.3 | hayır |
| 109 | 0.34 | −1.89 | 1.60 | 58.2 | 79.7 | hayır |

(i) ✗ (80–102 px) · (ii) ✗ (çekim −3.2 → −1.9, GT'ye **yaklaşıyor**) ·
(iii) ✗ (PSR 59 → 58).

### 268/31 — drift 151 · **ÖLÇÜLEMEDİ**
Drift öncesi 20 karenin hiçbirinde eşzamanlı GT + DCF yok (4I: GT görünürlüğü
**0.26**). Mekanizma sınanamaz.

### 339/49 — drift 6 · **ÖLÇÜLEMEDİ**
Drift **6. karede**; öncesinde pencere yok. (Koşum boyunca en yakın nesne
1.1 px'e iniyor ama bu, kopuştan **çok sonra**.)

## 3. Sınıflandırma

| epizot | YK karesi | (i) kapanan konjonksiyon | (ii) çekim kayması | (iii) KF+PSR çöküşü | **hüküm** |
|---|---:|---|---|---|---|
| **G6_agresif_durakli** | **115** | ✓ 46.7 → 1.5 px, Δy→0 | ✓ −4.4 → −27.2 | ✓ 2.25 → 0.51 / 22 → 6.7 | **AÇIKLANAN** |
| 137/12 | 1 | ✗ 38.3 → 42.1 px, ayrı satır | ✓ −10.3 → −30.3 | kısmî | **KISMEN** |
| 182/127 | 63 | ✗ 146–150 px | ✗ sabit | ✗ | **AÇIKLANAMAYAN** |
| 305/5 | 11 | ✗ 80–102 px | ✗ yaklaşıyor | ✗ | **AÇIKLANAMAYAN** |
| 268/31 | 179 | — | — | — | **ÖLÇÜLEMEDİ** (GT %26) |
| 339/49 | 117 | — | — | — | **ÖLÇÜLEMEDİ** (drift kare 6) |

**Cevap:** 4P mekanizması **6 epizottan 1'ini** açıklıyor — üstelik türetildiği
epizodu. YK karesi ağırlığıyla **115 / 486 = %23.7**; ölçülebilen dört epizot
içinde **1/4**. Ve 4P'ye göre o tek epizot bir takipçi zaafı değil, **sahne
artefaktıdır**.

> **Mekanizma GENELLEŞMİYOR.**

## 4. Peki baskın mekanizma ne? — ölçüldü

IoU düşüşünün **merkez** hatasından mı **kutu boyutundan** mı geldiğini
ayırmak için `tavan_iou` hesaplandı: takipçinin **kendi boyutu**, GT merkezine
tam oturtulduğunda elde edeceği IoU. `tavan_iou ≈ IoU` ise kayıp tamamen
boyuttandır.

| kaynak | drift | IoU | **tavan IoU** | kutu w/h | GT w/h | merkez hata | arıza |
|---|---:|---:|---:|---|---|---:|---|
| **G6_agresif_durakli** | 148 | 0.25 | **0.69** | 59/36 | 56/26 | **30.05** | **MERKEZ** |
| 137/12 | 75 | 0.28 | 0.49 | 75/86 | 55/58 | 28.80 | karışık |
| **182/127** | 39 | 0.29 | **0.29** | 11/9 | 21/16 | **2.52** | **BOYUT** |
| **305/5** | 110 | 0.23 | **0.26** | 36/85 | 25/32 | 29.34 | **BOYUT** |
| **G6_agresif** | 294 | 0.29 | **0.29** | 104/50 | 56/27 | 11.20 | **BOYUT** |

Ayrım keskindir: **4P'nin konjonksiyon mekanizması bir MERKEZ arızası
üretiyor** (tavan 0.69, merkez hatası 30 px); diğer bütün kaynaklarda
`tavan_iou = IoU` ve merkez hatası küçük — **kutu BOYUTU yanlış**.
182/127'de kutu hedefin **yarısı** (11×9 vs 21×16), 305/5'te **2.7 katı yüksek**
(36×85 vs 25×32), G6_agresif'te **1.9 katı** (104/50 vs 56/27) — ve bu sonuncu
hiç yanlış kilide düşmüyor, yalnızca IoU'yu kaybediyor.

Bu, 4N'in bulgusuyla tutarlıdır: `rafine_kutu` boyutun **açıdan ve şekilden
bağımsız tek ölçümüdür** ve dört kaynağın hepsinde uzun aralıklarla ölüyor.

---

# SONUÇ

**"4P'de doğrulanan çeldirici mekanizması yanlış kilitlerin ne kadarını
açıklıyor?"**

> **6 epizottan 1'i (YK karelerinin %23.7'si); ölçülebilen 4 epizottan 1'i.**
> Açıkladığı tek epizot, mekanizmanın türetildiği epizottur ve 4P'ye göre
> **sahne artefaktıdır**. İki negatif kontrol de aynı yöne bakıyor: 117/23'te
> başka nesneler karelerin %70'inde DCF penceresinde ve YK **sıfır**;
> G6_agresif'te çeldirici 11.3 px'e kadar geliyor ve YK **sıfır**.

**Bu nedenle bir sonraki aşamada çeldirici bastırma müdahalesi TASARLANMAMALI.**
Kullanıcının koyduğu koşul ("mekanizma yanlış kilitlerin büyük bölümünü
açıklıyorsa") **sağlanmadı**: %23.7 ve 1/6.

**Baskın alternatif mekanizma: KUTU BOYUTU.** Ölçülen dört kaynağın üçünde
`tavan_iou = IoU` — yani takipçi hedefin üzerinde ama kutusu yanlış ölçekte;
merkez hatası 1.9–2.5 px'e kadar küçük. 4P mekanizması bu ailenin dışında
kalan **tek** vakadır.

### Sonraki TEK deney adayı (yine salt okunur)

> **`boyut` hatasının kaynağını üç bileşene ayır: ego ölçeği, `_boyut_tazele`
> ve `_boyut_sinirla`.**
> `izleyici.py`'de `boyut` üç yerden yazılır — her karede
> `boyut *= ego.olcek_katsayisi` (satır 265), periyodik olarak
> `_boyut_tazele`'nin `0.75·boyut + 0.25·rafine` karışımı (satır 563) ve
> `_boyut_sinirla`'nın `boyut_olculen`e göre `[0.60, 1.70]` kırpması.
> 182/127 (kutu GT'nin yarısı), 305/5 (2.7 katı) ve G6_agresif (1.9 katı)
> için bu üç katkı kare kare ayrıştırılıp hangisinin hatayı **ürettiği**,
> hangisinin yalnızca **taşıdığı** ölçülmelidir.
> Bu ölçülmeden hiçbir boyut düzeltmesi doğru bileşene nişan alamaz — ve
> 4Q'ya göre asıl hedef budur, çeldirici değil.

**Bu turda hiçbir optimizasyon ya da düzeltme uygulanmadı; `takip/` md5 6/6
aynı.**
