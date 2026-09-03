# Deney 4K — DCF öğrenme kapısı

**Sonuç: BAŞARISIZ (müdahale karar kaynaklarında NO-OP) → geri alındı.**
`takip/` md5 6/6 Deney 2 ile birebir, commit/push yok.
Yama: `deney4k.patch` (25 satır).

## 1. Değişiklik neydi?

`izleyici.py:315-316`, `KILITLI` dalı:

```
             lr = 0.125 if self.boyut.max() > 18 else 0.04
-            self.cekirdek.ogren(bgr, gri, self.kf.konum, self.boyut, lr)
+            if self._hareketli and self.benzerlik >= self.kimlik_esik:
+                self.cekirdek.ogren(bgr, gri, self.kf.konum, self.boyut, lr)
```

Yani DCF şablon güncellemesi, **aynı dalda `imza.guncelle` için zaten
kullanılan** kapıya (`izleyici.py:324`) bağlandı. Yeni eşik yok —
`_hareketli`, `benzerlik`, `kimlik_esik` üçü de mevcut ve her karede
hesaplanıyor. `lr`, `r_carpan`, padding, Kalman, `rafine_kutu`, açı/şekil,
ego-motion ve DCF tepe hesabı **değişmedi**. Değişen tek şey şablonun
**ne zaman** öğrendiği.

### Baseline doğrulaması (değişiklik öncesi)

| kaynak | IoU | merkez | kilit | drift | Deney 2 ile |
|---|---|---|---|---|---|
| 117/23 | 0.701 | 5.51 | %100 | yok | **birebir** |
| 137/12 | 0.548 | 7.51 | %94.6 | 75 | **birebir** |
| 305/5 | 0.502 | 9.12 | %83.0 | 110 | **birebir** |
| G3_agresif | 0.760 | 3.81 | %100 | yok | **birebir** |
| G3_kritik | 0.704 | 5.07 | %100 | yok | **birebir** |

## 2. 117/23 sonucu

| | baseline | kapılı |
|---|---|---|
| `ogren` çağrısı | **342** | **342** |
| IoU | 0.700953 | **0.700953** |
| merkez hata | 5.513987 | **5.513987** |
| kilit | 1.000000 | 1.000000 |
| drift | yok | yok |

**Kapı 342 karenin hiçbirinde kapanmadı.** Değişiklik burada bit düzeyinde
etkisiz.

## 3. 137/12 sonucu

| | baseline | kapılı |
|---|---|---|
| `ogren` çağrısı | 214 | **208** (6 kare atlandı) |
| IoU | 0.547592 | 0.547564 (**−0.000028**) |
| merkez hata | 7.506260 | **7.506260** (aynı) |
| kilit | 0.945701 | 0.945701 |
| drift | 75 | 75 |

Kapı 6/214 karede kapanıyor; etkisi ölçüm gürültüsünün altında.

## 4. G3_agresif sonucu

IoU 0.760, merkez 3.81, kilit %100, drift yok — **değişmedi**.
Kapı 0/293 karede kapandı.

## 5. G3_kritik sonucu

IoU 0.704, merkez 5.07, kilit %100, drift yok — **değişmedi**.
Kapı 0/293 karede kapandı.

## Kapı ne sıklıkta kapanıyor? (kök neden)

`ogren` çağrısının olduğu karelerde kapı durumu ölçüldü:

| kaynak | öğrenme karesi | **kapı kapalı** | `_hareketli` nedeniyle | `benzerlik` nedeniyle |
|---|---|---|---|---|
| **117/23** | 342 | **0 (%0.0)** | 0 | 0 |
| **137/12** | 214 | **6 (%2.8)** | 0 | 6 |
| 305/5 | 116 | 0 (%0.0) | 0 | 0 |
| G0 | 293 | 0 (%0.0) | 0 | 0 |
| G3_agresif | 293 | 0 (%0.0) | 0 | 0 |
| G3_kritik | 293 | 0 (%0.0) | 0 | 0 |
| G6_agresif | 293 | 0 (%0.0) | 0 | 0 |
| G4_kritik | 293 | 0 (%0.0) | 0 | 0 |
| *182/127* | 101 | *25 (%24.8)* | 19 | 6 |
| *268/31* | 731 | *252 (%34.5)* | 252 | 0 |
| *339/49* | 200 | *39 (%19.5)* | 21 | 18 |
| *G6_agresif_durakli* | 256 | *19 (%7.4)* | 7 | 18 |

**Yapısal açıklama:** `benzerlik` yalnızca `_bagimsiz_dogrula` içinde,
`not self._hareketli_guclu` koşuluyla güncellenir (izleyici.py:417-421).
Sağlıklı takip edilen **hareketli** bir araçta `_hareketli_guclu` doğrudur →
kimlik denetimi hiç çalışmaz → `benzerlik` sıfırlama değeri 1.0'da kalır →
`_hareketli` de True kalır → **kapı yapısal olarak açık kalır.**

Yani bu kapı, ancak takipçi **zaten sıkıntıdayken** kapanabilir. Sağlıklı
takipte kapanamaz — dolayısıyla 4J'de bulunan asimetri (şablon koşulsuz, imza
kapılı) kodda gerçek ama **sağlıklı takipte işlevsizdir**: imza kapısı da aynı
sebeple neredeyse hiç ateşlemiyor.

## 6. Merkez biası azaldı mı?

**Hayır.** İki karar kaynağında da merkez hatası **birebir aynı**
(117/23: 5.513987 → 5.513987; 137/12: 7.506260 → 7.506260).

## 7. Drift / lock bozuldu mu?

**Hayır.** Beş kaynakta da drift karesi, kilit oranı, kesinti ve kurtarma
değişmedi. Regresyon **yok** — ama iyileşme de yok.

## 8. Mekanizma desteklendi mi?

| test | sonuç |
|---|---|
| A) kapı değişince merkez biası azalıyor mu | **hayır** — birebir aynı |
| B) şablon değişim miktarı azalıyor mu | 117/23'te **0**, 137/12'de 6/214 |
| C) biasın zamanla büyümesi azalıyor mu | **hayır** — seri değişmedi |
| D) 4J'deki öğrenme–bias ilişkisi kırılıyor mu | **test edilemedi** — müdahale sistemi yeterince kıpırdatmıyor |
| E) rafine_kutu etkisi değişiyor mu | değişmedi |
| F) PSR korunuyor mu | **evet**, birebir |
| G) 117/23 ve 137/12 aynı yönde mi | ikisi de "etki yok" — tutarlı ama boş |
| H) G3_agresif/G3_kritik'te aynı mekanizma | kapı orada da hiç kapanmıyor |

**Mekanizma desteklenmedi — çünkü sınanamadı.** Müdahale, karar kaynaklarında
hiç devreye girmiyor.

## Kapının fiilen ateşlediği yer (karar dışı diziler)

Yalnızca bilgi olarak; 4I bu dizileri **karar dışı** ilan etti (metrik
başarısızlıkta doygun, Deney 1'de kaotik):

| dizi | IoU önce→sonra | merkez önce→sonra | kilit önce→sonra | kesinti |
|---|---|---|---|---|
| *182/127* | 0.0877 → 0.1038 | **265.66 → 67.09** | 0.307 → **0.510** | 2 → **0** |
| *339/49* | 0.0639 → 0.0638 | 76.31 → **65.12** | 0.744 → **0.880** | 3 → 3 |
| *268/31* | 0.000 → 0.000 | 383.61 → 398.39 | 0.710 → 0.726 | 0 → 0 |
| *G6_agresif_durakli* | 0.3831 → 0.3831 | 61.53 → 61.53 | 0.878 → 0.878 | 0 → 0 |

Üç dizide merkez hatası ve kilit oranı **aynı yönde** iyileşiyor. Ama bu
diziler karar kanıtı sayılamaz: 4I'da IoU≈0 oranları %67/%65/%100 ölçüldü ve
Deney 1'de sayısal olarak eşdeğer bir işlem değişiminin 182/127'yi ±0.04
oynattığı gösterildi.

## 9. Deney: **BAŞARISIZ**

Karar kuralı: *"Değişiklik ancak 117/23 VE 137/12'de regresyon yaratmıyorsa,
**merkez biasını anlamlı azaltıyorsa**, drift/lock'u bozmadıysa ... başarılı
kabul edilecek."*

| ölçüt | sonuç |
|---|---|
| 117/23 + 137/12'de regresyon yok | **GEÇTİ** (birebir / −2.8e-5) |
| **merkez biasını anlamlı azaltıyor** | **KALDI** (birebir aynı) |
| drift / lock bozulmadı | **GEÇTİ** |
| G3_agresif / G3_kritik kabul edilebilir | **GEÇTİ** (birebir) |
| iki gerçek dizide zıt yön yok | **GEÇTİ** |

Dört ölçüt geçti, ana ölçüt kaldı. Değişiklik **geri alındı**; md5 6/6
doğrulandı ve baseline metrikleri birebir geri geldi.

## 10. Sonraki TEK aday

Bu tur, hedeflenen mekanizma için **ikinci** kolun da kapandığını gösterdi:

| kol | deney | sonuç |
|---|---|---|
| öğrenme **hızı** (`lr`) | 4H | gerçek veride **ters** yönde etki |
| öğrenme **zamanı** (mevcut kapı) | **4K** | sağlıklı takipte **hiç kapanmıyor** |

Öğrenme–bias ilişkisi (4J) gerçek veride sağlam bir **asosiyasyon** ama
üzerinde işleyen bir kol bulunamadı. Yeni bir kapı koşulu icat etmek **yeni
eşik** demektir ve Faz C'nin beş turluk geçmişi böyle bir eşiğin
genellenmeyeceğini söylüyor.

Buna karşılık bu deney **beklenmedik ve tutarlı** bir yan sonuç üretti: kapı,
ateşlediği üç dizide merkez hatasını ve kilit oranını **aynı yönde**
iyileştirdi (182/127 merkez 265.66 → 67.09, kilit %30.7 → %51.0, kesinti 2 → 0;
339/49 merkez 76.31 → 65.12, kilit %74.4 → %88.0). Bunlar **yanlış kilide
yatkın** dizilerdir ve kodun kendi yorumu aynı kapının imza tarafında yanlış
kilit oranını %43.6 → %9'a indirdiğini söylüyor.

Yani değişiklik muhtemelen bir **bias** düzeltmesi değil, bir **yanlış kilit
dayanıklılığı** düzeltmesidir — ama bu hipotez **şu anda sınanamaz**, çünkü
4I'a göre yanlış kilit gösteren dizilerin hepsi karar dışı.

> ### Sonraki tek aday — takipçi değişikliği değil
> **Karar verilebilir bir yanlış-kilit kaynağı var mı, salt okunur belirle.**
> Gazebo tarafında `G6_agresif_durakli` yanlış kilit oranı %39.9 ile
> ölçülebilir tek adaydı ama bu deneyde hiç kıpırdamadı. Gerçek veri tarafında
> yanlış kilit gösteren üç dizi de metrik olarak doygun.
> Bu belirlenmeden 4K'nın gerçek değeri (bias mı, yanlış kilit mi) ölçülemez.

**Bu bir öneridir, uygulanmadı. Bu turda başka optimizasyon yapılmadı.**
