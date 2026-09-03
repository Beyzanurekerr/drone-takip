# Deney 1 — DCF şablonunu ego-motion dönmesiyle hizala

**Sonuç: GERİ ALINDI.** `takip/` Faz B durumuna döndü
(`cekirdekler.py` md5 `2dbd7f0c…`, `izleyici.py` md5 `18421835…`,
`git status takip/` boş). Geri alma sonrası tam koşum "önce" sayılarını
**birebir** yeniden üretti (test1 0.925, test2 0.435, test3 0.560, test6 0.747,
117/23 0.701, 268/31 0.000, 182/127 0.088) — hat tamamen deterministik.

Geri alınan yama: `deney1_donme_hizalama.py.reverted` (oturum çalışma alanı).

## Hipotez

Faz B'de ölçüldü: kamera yaw'ı arttıkça G3 ailesi bozuluyor, **ama ego
benzerlik artığı `e_model = 0.00 px`** — yani benzerlik dönüşümü görüntü
düzlemi dönmesini tam temsil ediyor ve ego katmanı bunu doğru ölçüp Kalman'a
aktarıyor. Eksik olan tek şey, aynı bilginin DCF şablonuna verilmemesi.

Değişiklik: `RenkDcfCekirdek` kare-arası dönmeyi `atan2(M[1,0], M[0,0])` ile
biriktirir (`self.aci`) ve yamayı `getRectSubPix` yerine `warpAffine` ile
**kilit anındaki duruşa geri döndürerek** keser; tepe kayması aynı açıyla
görüntü çerçevesine geri döndürülür. `izleyici.py`'de tek satır
(`self.cekirdek.ego_guncelle(M)`).

İşaret yönü sentetik olarak doğrulandı: bilinen +8° döndürülmüş karede ego M'den
+7.995° okundu, düzeltilmiş yamanın referansla NCC'si 0.103 → **0.909**.

## Kurulum

`deney.py` üç hattı tek komutla koşar ve JSON'a yazar; hatlar birbirine
karıştırılmaz. Üç kol ölçüldü:

| kol | ne | dosya |
|---|---|---|
| **önce** | A3.8, değişiklik yok | `cikti/deney_once.json` |
| **kontrol** | `warpAffine` var ama **açı sabit 0** | `cikti/deney_kontrol.json` |
| **sonra** | tam değişiklik | `cikti/deney_sonra.json` |

Kontrol kolu sonradan eklendi ve **sonucu değiştirdi** — gerekçesi aşağıda.

## Sonuçlar

### Gazebo (22 kayıt)

| senaryo | IoU önce | IoU kontrol | IoU sonra | Δ örnekleyici | Δ dönme | @0.5 ö→s | kilit ö→s | drift ö→s | IDsw ö→s | kurtarma ö→s |
|---|---|---|---|---|---|---|---|---|---|---|
| G0 | 0.912 | 0.898 | 0.913 | -0.014 | +0.015 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G1_yumusak | 0.899 | 0.893 | 0.888 | -0.006 | -0.004 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G1_agresif | 0.897 | 0.888 | 0.902 | -0.009 | +0.014 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G2_yumusak | 0.862 | 0.876 | 0.874 | +0.013 | -0.001 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G2_agresif | 0.859 | 0.858 | 0.854 | -0.002 | -0.004 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G3_yumusak | 0.862 | 0.851 | 0.844 | -0.011 | -0.007 | 1.000→0.993 | 100.0%→97.3% | yok→yok | 0→0 | 0→4 |
| G3_agresif | 0.766 | 0.769 | 0.765 | +0.003 | -0.004 | 0.990→0.997 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G4_yumusak | 0.885 | 0.883 | 0.889 | -0.003 | +0.006 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G4_agresif | 0.871 | 0.870 | 0.855 | -0.002 | -0.015 | 1.000→0.993 | 100.0%→98.6% | yok→yok | 0→0 | 0→4 |
| G5_yumusak | 0.888 | 0.889 | 0.888 | +0.001 | -0.000 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G5_agresif | 0.883 | 0.886 | 0.886 | +0.002 | +0.000 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G6_yumusak | 0.807 | 0.802 | 0.803 | -0.005 | +0.001 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G6_agresif | 0.618 | 0.614 | 0.585 | -0.004 | -0.029 | 0.684→0.619 | 100.0%→100.0% | 294→258 | 0→0 | 0→0 |
| G7_yumusak | 0.893 | 0.896 | 0.891 | +0.003 | -0.005 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G7_agresif | 0.847 | 0.868 | 0.866 | +0.021 | -0.002 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G1_kritik | 0.890 | 0.891 | 0.886 | +0.001 | -0.005 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G3_kritik | 0.579 | 0.563 | 0.695 | -0.016 | +0.133 | 0.721→0.925 | 96.9%→100.0% | 133→yok | 0→0 | 9→0 |
| G4_kritik | 0.810 | 0.798 | 0.786 | -0.012 | -0.012 | 1.000→0.993 | 100.0%→99.7% | yok→yok | 0→0 | 0→1 |
| G5_kritik | 0.862 | 0.861 | 0.868 | -0.001 | +0.007 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G7_kritik | 0.865 | 0.870 | 0.871 | +0.006 | +0.001 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| G6_agresif_hedef | 0.662 | 0.631 | 0.631 | -0.031 | +0.000 | 0.915→0.861 | 97.3%→97.3% | yok→yok | 0→0 | 8→8 |
| G6_agresif_durakli | 0.383 | 0.380 | 0.381 | -0.003 | +0.001 | 0.469→0.473 | 87.8%→87.8% | 148→148 | 1→1 | 0→0 |

### sim (test1–test7)

| senaryo | IoU önce | IoU kontrol | IoU sonra | Δ örnekleyici | Δ dönme | @0.5 ö→s | kilit ö→s | drift ö→s | IDsw ö→s | kurtarma ö→s |
|---|---|---|---|---|---|---|---|---|---|---|
| test1 | 0.925 | 0.926 | 0.921 | +0.001 | -0.005 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| test2 | 0.435 | 0.686 | 0.514 | +0.251 | -0.172 | 0.447→0.375 | 98.0%→95.9% | 210→175 | 0→0 | 0→7 |
| test3 | 0.560 | 0.623 | 0.614 | +0.063 | -0.009 | 0.612→0.664 | 94.6%→100.0% | 458→458 | 0→0 | 1→0 |
| test4 | 0.866 | 0.869 | 0.899 | +0.004 | +0.030 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| test5 | 0.897 | 0.894 | 0.895 | -0.003 | +0.001 | 1.000→1.000 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |
| test6 | 0.747 | 0.745 | 0.726 | -0.002 | -0.019 | 0.806→0.798 | 78.1%→77.5% | 282→177 | 1→1 | 30→30 |
| test7 | 0.764 | 0.780 | 0.779 | +0.016 | -0.001 | 0.907→0.914 | 100.0%→100.0% | yok→yok | 0→0 | 0→0 |

### VisDrone

| senaryo | IoU önce | IoU kontrol | IoU sonra | Δ örnekleyici | Δ dönme | @0.5 ö→s | kilit ö→s | drift ö→s | IDsw ö→s | kurtarma ö→s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0000117/23 | 0.701 | 0.691 | 0.681 | -0.010 | -0.011 | 0.974→0.965 | 100.0%→100.0% | yok→yok | n/a | 0→0 |
| 0000268/31 | 0.000 | 0.000 | 0.000 | +0.000 | +0.000 | 0.000→0.000 | 71.0%→88.1% | 151→151 | n/a | 0→0 |
| 0000182/127 | 0.088 | 0.046 | 0.066 | -0.042 | +0.020 | 0.000→0.000 | 30.7%→11.9% | 39→34 | n/a | 2→8 |

## Okuma

### 1. Hedeflenen mekanizma DOĞRULANDI — ama tek bir senaryoda

`G3_kritik` (yaw ±55°, açısal hız p95 171 °/s), yalnızca dönme etkisi:

| | önce | sonra |
|---|---|---|
| IoU | 0.579 | **0.695** (+0.116) |
| @0.5 | 0.721 | **0.925** |
| kilit | 96.9% | **100%** |
| drift karesi | **133** | **yok** |
| kurtarma max | 9 kare | 0 |
| PSR p50 | 21.4 | **54** |

Birikimli açı gerçeği neredeyse kusursuz izledi: ölçülen −108.0°, gerçek
−106.6°, |hata| p95 **1.40°**. Faz B'nin teşhisi doğruydu.

### 2. Ama açı integratörü SIZDIRIYOR

Dönme olmayan senaryolarda birikimli açı sıfırda kalmıyor. Gerçek kamera
dönmesiyle karşılaştırma (Gazebo pozlarından):

| senaryo | ölçülen birikimli açı | gerçek | not |
|---|---|---|---|
| G3_agresif | −50.4° | −49.6° | gerçek dönme, iyi izleniyor |
| G3_kritik | −108.0° | −106.6° | gerçek dönme, iyi izleniyor |
| **G4_kritik** | **−9.4°** | **0.0°** | tamamen sahte |
| G5_kritik | −2.6° | 0.0° | sahte |
| G4_agresif | −2.4° | 0.0° | sahte |
| G6_agresif | −1.7° | 0.0° | sahte |
| G1_kritik | −1.2° | 0.0° | sahte |

Nedeni Faz B'de zaten ölçülmüştü: **pitch'te benzerlik dönüşümü perspektifi
temsil edemiyor** (G4_kritik `e_model_p95` = 4.62 px) ve en iyi uyum, artığın
bir kısmını **sahte dönme** olarak soğuruyor. Açık çevrim bir integratör bunu
kare kare biriktiriyor. Ayrıca hızlı ötelemede RANSAC benzerlik kestiriminde
küçük ve **tek yönlü** (hep negatif) bir yanlılık var.

Regresyonlar tam buradan geliyor: G4_agresif −0.015, G4_kritik −0.012,
G6_agresif −0.029 (yalnızca dönme etkisi).

### 3. Deney istemeden İKİ değişkeni birden taşıdı

sim test2 (+0.080) ve test3 (+0.054) ilk bakışta kazanç gibi görünüyordu.
Ama o senaryolarda çekirdeğe giden **birikimli açı ≤ 0.4°** — dönme telafisi
orada fiilen devre dışı. Kazanç `getRectSubPix` → `warpAffine` **örnekleyici**
değişiminden geliyordu.

Kontrol kolu bunu ayırdı (açı sabit 0, yalnızca örnekleyici):

| hat | Δ örnekleyici (iyi/kötü) | Δ dönme (iyi/kötü) |
|---|---|---|
| Gazebo (22) | 8 / 14 | 10 / 12 |
| sim (7) | 5 / 2 | 2 / 5 |
| VisDrone (3) | 0 / 2 | 1 / 1 |

Örnekleyici değişikliği **tek başına** Gazebo'da ve VisDrone'da net olumsuz.
Bir yan etki olarak taşınması kabul edilemez.

### 4. Marjinal senaryolar KAOTİK — tek koşumluk IoU orada kanıt değil

Kontrol kolu anlam olarak aynı işlemi yapıyor (açı 0 → `warpAffine` birim
dönüşüm), tek fark örnekleme yuvarlaması. Buna rağmen:

* sim test2: 0.435 → **0.686** (+0.251)
* sim test2, kontrol → sonra: 0.686 → 0.514 (−0.172), oysa açı ≤0.08°
* VisDrone 182/127: 0.088 → 0.046 (−0.042)

Yani IoU'su 0.4–0.7 bandındaki senaryolarda alt-piksel düzeyinde bir sayısal
fark, yörüngeyi tümüyle değiştiriyor. **Bu senaryolarda ±0.2'lik IoU farkı
değişikliğin etkisi değil, kaosun kendisidir.** Bundan sonraki A/B kararları
test2 / test3 / 182/127 üzerine kurulmamalı; onlar ancak *çok sayıda* koşumun
dağılımıyla okunabilir.

### 5. Performans

Koşum içi FPS sayıları makine yüküyle dalgalanıyor (aynı kod, aynı veri:
sim test1 için 220–475 FPS arası). Dönüşümlü koşum (eski/yeni/eski/yeni…) ve
mikro-benchmark gerçek maliyeti veriyor:

| yama boyutu | `getRectSubPix` | `warpAffine` | fark |
|---|---|---|---|
| 112×44 | 12.5 µs | 23.1 µs | +10.6 µs (+84%) |
| 120×84 | 24.2 µs | 43.7 µs | +19.5 µs (+81%) |
| 64×32 | 5.6 µs | 11.8 µs | +6.2 µs (+111%) |

Kare başına 2 çağrı (`ara` + `ogren`), tipik kare bütçesi ~2200 µs →
**%1–2 FPS maliyeti**. Tek başına kabul edilebilir bir bedel; ama karşılığında
gelen fayda tek senaryoyla sınırlı.

## Karar

**Tamamen geri alındı.** Gerekçe, "en iyi dengeli çözüm" ölçütüne göre:

* **VisDrone (gerçek veri) kesin olarak kötüleşti** — 117/23 −0.020,
  182/127 −0.022, 268/31 değişmedi. Üç gerçek diziden hiçbiri iyileşmedi.
* **Gazebo net olumsuz** — 22 kayıtta IoU 10 iyi / 12 kötü; G3_kritik dışındaki
  tek anlamlı hareketler regresyon (G4, G6).
* **sim'deki kazanç deneyin konusu değil** — örnekleyici yan etkisinden
  geliyordu ve o yan etki diğer iki hatta zarar veriyor.
* **Maliyet var** — %1–2 kare süresi.

Tek bir sentetik senaryodaki büyük kazanç (G3_kritik), üç hattaki yaygın küçük
kayıpları ve gerçek veri regresyonunu karşılamıyor.

## Deney 2 için tasarım (uygulanmadı)

Deney 1 fikri çürütmedi; **uygulamayı** çürüttü. İki kusur ayrı ayrı ölçüldü,
ikisinin de düzeltmesi belli:

1. **Açı açık çevrim biriktirilmemeli.** Sızıntı, benzerliğin perspektifi sahte
   dönme olarak soğurmasından geliyor ve ölü bant çözmez (G4_kritik'te sapma
   0.30 °/kare, yani gürültü tabanının çok üstünde ve *gerçekten* benzerliğin
   söylediği şey). Yerine **kapalı çevrim**: her karede şablon yanıtını birkaç
   aday açıda (ör. mevcut açı ve ±Δ) değerlendirip tepesi en yüksek olanı seç.
   Şablona her karede yeniden çapalandığı için sürüklenemez. Bedeli korelasyonun
   3 katı — ama yalnızca dönme şüphesi varken açılırsa bütçe korunur.
2. **Örnekleyici değişkeni deneyden çıkarılmalı.** `|açı|` bir eşiğin altındayken
   (yamanın kenarında alt-piksel kayma üretmeyen açı) `getRectSubPix` yolunda
   kalınmalı. Bu hem yan etkiyi hem de %1–2 maliyeti dönme olmayan karelerden
   siler; G0/G1/G2/G5/G7 ve sim'in tamamı **bit-birebir** değişmeden kalır ve
   deney gerçekten tek değişkenli olur.

Kabul ölçütü (Deney 1'den öğrenilerek): karar **G3 ailesi + G0 + VisDrone
117/23** üzerinden verilmeli; test2 / test3 / 182/127 kaotik oldukları için
karar dışı bırakılmalı, yalnızca "çökmedi" kontrolü olarak okunmalı.

## Ölçüm altyapısında yapılan (takipçi dışı) eklemeler

```
deney.py                YENİ - üç hattı tek komutla koşan A-B kıyaslayıcı
calistir.py             + gecikme_p50/p95, + t_drift (main.py ile aynı tanım)
gazebo/tani.py          + id_switch (calistir.py ile aynı ölçüt)
```

Bunların hiçbiri takipçi davranışını değiştirmez; `takip/` ve `sim/` dokunulmadı.
