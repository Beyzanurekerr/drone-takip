# Deney 4C — rafine_kutu merkez düzeltmesinin Kalman ağırlığı

**Sonuç: BAŞARISIZ → tamamen geri alındı.** `takip/` altındaki 6 dosyanın md5'i
Deney 2 durumuyla birebir (`md5sum -c` 6/6 OK); geri alma sonrası G0 0.912,
G3_agresif 0.760, G3_kritik 0.704 birebir geri geldi. Commit/push yok.
Yama: `deney4c.patch` (22 satır).

## 1. Değişiklik tam olarak neydi?

`takip/izleyici.py:567`, `_boyut_tazele` içinde:

```
-            self.kf.duzelt(yeni_c, r_carpan=1.0)
+            self.kf.duzelt(yeni_c, r_carpan=0.17)
```

Başka hiçbir şey değişmedi — tek sayı.

### `r_carpan` semantiği doğrulandı (ters DEĞİL)

```python
def duzelt(self, z, r_carpan=1.0):
    R = np.eye(2) * (self.R0 * r_carpan)        # R0 = 2.5
    S = self.H @ self.P @ self.H.T + R
    K = self.P @ self.H.T @ inv(S)
```

`R = R0 × r_carpan`; küçük `r_carpan` → küçük R → büyük Kalman kazancı → ölçüme
daha çok güven. Kodun kendi kullanımı da doğruluyor: satır 327 zayıf DCF ölçümü
için `r_carpan=6.0` kullanıyor ve yorumu "zayif olcum, az guven". Yani 0.17
doğru yönde.

`0.17 ≈ 1/5.9`, yani Deney 4B'de ölçülen doğruluk oranının standart sapma
karşılığı. (Not: R bir *varyans* olduğu için varyans-tutarlı değer
`(0.76/4.45)² ≈ 0.029` olurdu; 0.17 daha ılımlı bir adımdır.)

## 2. Merkez hatası ne kadar azaldı?

Mekanizma **tam olarak tasarlandığı gibi çalıştı**:

| senaryo | aşama | p50 | p95 | ort | dx ort | dy ort | sürüm |
|---|---|---|---|---|---|---|---|
| G3_agresif | DCF | 4.72 | 7.02 | 4.45 | −4.17 | −0.97 | Deney 2 |
| G3_agresif | DCF | **2.08** | **4.51** | **2.43** | **−2.20** | −0.79 | **Deney 4C** |
| G3_agresif | final | 3.82 | 6.37 | 3.87 | −3.63 | −0.88 | Deney 2 |
| G3_agresif | final | **1.49** | **4.03** | **1.84** | **−1.66** | −0.64 | **Deney 4C** |
| G3_kritik | DCF | 5.84 | 9.65 | 5.85 | −4.78 | −0.48 | Deney 2 |
| G3_kritik | DCF | **3.66** | 7.93 | **4.04** | **−3.35** | −0.50 | **Deney 4C** |
| G3_kritik | final | 5.09 | 9.42 | 5.25 | −4.30 | −0.44 | Deney 2 |
| G3_kritik | final | **2.42** | 7.81 | **3.32** | **−2.76** | −0.42 | **Deney 4C** |
| G0 | final | 1.24 | 2.59 | 1.33 | −0.93 | −0.35 | Deney 2 |
| G0 | final | **0.92** | 2.59 | **1.27** | **−0.47** | −0.40 | **Deney 4C** |

* G3_agresif final merkez hatası **3.87 → 1.84 px (−52%)**, p50 3.82 → 1.49
* G3_kritik **5.25 → 3.32 px (−37%)**
* 29 senaryonun 25'inde merkez hatası azaldı

## 3. IoU ne oldu?

* G3_agresif **0.760 → 0.817** (+0.057) — kriteri (≥0.766) geçti
* G3_kritik **0.704 → 0.750** (+0.046) — kriteri geçti
* 32 senaryoda: **24 iyileşme, 7 kötüleşme, 1 değişmedi**
* En büyük kazançlar: sim test3 +0.099, G6_agresif_hedef +0.095, test2 +0.062

## 4. DCF bias ne oldu?

**Beklenmedik ve önemli:** DCF tepesinin *kendi* hatası da düştü —
G3_agresif 4.45 → 2.43 px, dx −4.17 → **−2.20**. Oysa DCF koduna hiç
dokunulmadı.

Nedeni yapısal: DCF, KF öngörüsünün etrafında arıyor. Öngörü daha iyi
merkezlenince yama hedefin üstüne daha simetrik oturuyor, arka plan
bulaşması azalıyor ve tepe daha az çekiliyor. Yani Deney 4B'nin teşhis ettiği
"arka plan sürüklemesi" kısmen kendi kendini besleyen bir döngüymüş ve
merkezi düzeltmek onu da zayıflatıyor.

## 5. 32 senaryoda regresyon

**0/32 senaryo değişmeden kaldı.** Değişiklik açı kapısına bağlı olmadığı için
`_boyut_tazele`'nin ateşlediği **her** senaryoyu etkiliyor.

| senaryo | IoU D2 → 4C | merkez px D2 → 4C | kilit D2 → 4C | kesinti | drift D2 → 4C |
|---|---|---|---|---|---|
| G0 | 0.912 → 0.904 (**KÖTÜ**) | 1.24 → 0.92 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| G1_yumusak | 0.899 → 0.908 (iyi) | 1.40 → 0.87 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| G1_agresif | 0.897 → 0.910 (iyi) | 1.24 → 0.94 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| G2_yumusak | 0.862 → 0.895 (iyi) | 2.28 → 0.95 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| G2_agresif | 0.859 → 0.879 (iyi) | 1.63 → 1.20 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| G3_yumusak | 0.862 → 0.868 (iyi) | 1.85 → 0.99 | 100.0% → 98.6% | 0 → 1 | yok → yok |
| **G3_agresif** | 0.760 → 0.817 (iyi) | 3.81 → 1.48 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| G4_yumusak | 0.885 → 0.913 (iyi) | 1.44 → 0.79 | 100.0% → 99.3% | 0 → 1 | yok → yok |
| G4_agresif | 0.871 → 0.884 (iyi) | 1.72 → 0.91 | 100.0% → 99.0% | 0 → 1 | yok → yok |
| G5_yumusak | 0.888 → 0.923 (iyi) | 1.68 → 0.88 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| G5_agresif | 0.883 → 0.902 (iyi) | 1.62 → 1.15 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| G6_yumusak | 0.807 → 0.827 (iyi) | 2.81 → 1.65 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| **G6_agresif** | 0.618 → 0.674 (iyi) | 8.40 → 3.87 | 100.0% → 87.1% | 0 → 1 | 294 → 250 |
| G7_yumusak | 0.893 → 0.890 (**KÖTÜ**) | 1.29 → 0.90 | 100.0% → 99.0% | 0 → 1 | yok → yok |
| G7_agresif | 0.847 → 0.855 (iyi) | 1.66 → 1.86 | 100.0% → 99.0% | 0 → 1 | yok → yok |
| G1_kritik | 0.890 → 0.900 (iyi) | 1.43 → 1.15 | 100.0% → 99.0% | 0 → 1 | yok → yok |
| **G3_kritik** | 0.704 → 0.750 (iyi) | 5.07 → 2.42 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| G4_kritik | 0.810 → 0.800 (**KÖTÜ**) | 1.57 → 0.98 | 100.0% → 99.0% | 0 → 1 | yok → yok |
| G5_kritik | 0.862 → 0.881 (iyi) | 1.70 → 1.34 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| G7_kritik | 0.865 → 0.873 (iyi) | 2.27 → 1.60 | 100.0% → 99.3% | 0 → 1 | yok → yok |
| G6_agresif_hedef | 0.662 → 0.756 (iyi) | 7.54 → 2.91 | 97.3% → 98.0% | 1 → 1 | yok → yok |
| G6_agresif_durakli | 0.383 → 0.393 (iyi) | 61.53 → 60.95 | 87.8% → 87.8% | 0 → 0 | 148 → 148 |
| test1 | 0.925 → 0.934 (iyi) | 0.25 → 0.24 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| test2 | 0.435 → 0.497 (iyi) | 1.59 → 2.90 | 98.0% → 98.3% | 0 → 2 | 210 → 210 |
| test3 | 0.560 → 0.659 (iyi) | 1.75 → 0.45 | 94.6% → 96.3% | 1 → 7 | 458 → 371 |
| test4 | 0.866 → 0.869 (iyi) | 0.57 → 0.38 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| test5 | 0.897 → 0.892 (**KÖTÜ**) | 0.15 → 0.17 | 100.0% → 100.0% | 0 → 0 | yok → yok |
| test6 | 0.747 → 0.745 (**KÖTÜ**) | 0.99 → 0.45 | 78.1% → 77.5% | 3 → 3 | 282 → 281 |
| test7 | 0.764 → 0.779 (iyi) | 0.97 → 0.60 | 100.0% → 99.4% | 0 → 1 | yok → yok |
| **0000117/23** | 0.701 → 0.011 (**KÖTÜ**) | 5.51 → 394.81 | 100.0% → 66.5% | 0 → 0 | yok → 10 |
| 0000268/31 | 0.000 → 0.000 (—) | 383.61 → 371.26 | 71.0% → 55.2% | 0 → 0 | 151 → 151 |
| 0000182/127 | 0.088 → 0.047 (**KÖTÜ**) | 265.66 → 170.94 | 30.7% → 46.9% | 2 → 0 | 39 → 38 |

### Kritik regresyon: VisDrone 117/23

| | Deney 2 | Deney 4C |
|---|---|---|
| IoU | 0.701 | **0.011** |
| merkez hata | 5.51 px | **394.81 px** |
| kilit | 100% | **66.5%** |
| drift karesi | yok | **10** |

Çalışan **tek** gerçek veri dizisi 10 karede çöktü.

### Neden çöktü — ölçüldü

Deney 4C'nin dayandığı oran **Gazebo'ya özgüymüş.** Baseline kodla ölçülen
medyan merkez hatası:

| dizi | rafine−GT | DCF−GT | **oran** |
|---|---|---|---|
| Gazebo G3_agresif | 0.76 px | 4.45 px | **5.9×** |
| Gazebo G3_kritik | 0.76 px | 5.85 px | **7.7×** |
| VisDrone 117/23 | **4.78 px** | 5.42 px | **1.13×** |
| VisDrone 182/127 | 2.10 px | 257.91 px | (zaten kopuk) |

Gazebo'da hedef temiz renkli bir kutu, zemin dokulu; `rafine_kutu` neredeyse
kusursuz. Gerçek hava görüntüsünde rafine DCF'ten yalnızca **%13** daha iyi.
`r_carpan = 0.17` ile ona 5.9 kat ağırlık vermek, gürültülü bir ölçüme aşırı
güvenmek demek; takipçi rafine'nin lekesi nereye kayarsa oraya çekiliyor.

**Deney 4B'nin teşhisi yalnızca Gazebo üzerinde yapılmıştı ve anahtar oranı
gerçek veriye genellenmiyor.** Bu, teşhis metodolojisinin kendisine dair bir
bulgudur.

## 6. Kabul kriterleri

| # | kriter | sonuç |
|---|---|---|
| 1 | **30/32 değişmeyen senaryo** | **KALDI** (0/32) |
| 2 | G3_kritik IoU ≥ 0.704 | **GEÇTİ** (0.750) |
| 3 | G3_agresif IoU ≥ 0.766 | **GEÇTİ** (0.817) |
| 4 | gereksiz açı araması açılmamalı | **GEÇTİ** (yalnız G3 ailesi, değişmedi) |
| 5 | **drift/lock davranışı bozulmamalı** | **KALDI** (117/23 drift@10, kilit 100→66.5%; G6_agresif 100→87.1%; 9 senaryoda 100→98.6–99.4%) |
| 6 | FPS anlamlı düşmemeli | **GEÇTİ** |
| E1 | G3_agresif merkez hatasında belirgin düşüş | **GEÇTİ** (3.81 → 1.48 px) |
| E2 | dx bias azalması | **GEÇTİ** (−3.63 → −1.66 px) |

FPS/gecikme (ek hesap yok, beklendiği gibi nötr):

| hat | FPS D2 → 4C | gecikme p50 | p95 |
|---|---|---|---|
| Gazebo | 322 → 361 | 2.77 → 2.42 | 5.56 → 4.63 |
| sim | 355 → 345 | 2.60 → 2.71 | 4.92 → 5.11 |
| VisDrone | 107 → 118 | 6.12 → 6.07 | 18.38 → 22.52 |

## 7. Sonuç: BAŞARISIZ

8 ölçütten 6'sı geçti; **2'si kaldı** ve ikisi de sert:

* 0/32 değişmezlik — değişiklik kapısız olduğu için yapısal olarak imkânsızdı
* VisDrone 117/23'te tam kopma

Eşikler gevşetilmedi, "kıl payı" sayılmadı, geri alındı ve doğrulandı.

**Ama fikir çürümedi.** Gazebo/sim tarafında ölçülen kazanç büyük ve
mekanizması doğrulandı: merkez hatası −52%, dx bias −54%, 24/32 senaryoda IoU
artışı, sıfır ek maliyet. Başarısızlığın nedeni fikir değil, **ağırlığın sabit
olması**: rafine'nin doğruluğu sahneye göre 0.76 px ile 4.78 px arasında
değişiyor ve tek bir `r_carpan` ikisine birden uyamıyor.

## 8. Sonraki adım için TEK aday

**`r_carpan`'ı sabit bir sayı yerine rafine ölçümünün o karedeki kendi
tutarlılığından türet.**

Gerekçe doğrudan ölçümden: rafine'nin doğruluğu Gazebo'da 0.76 px, VisDrone
117/23'te 4.78 px — **6.3 kat fark**. Sabit bir ağırlık ya Gazebo'da fırsatı
kaçırır (mevcut 1.0) ya da gerçek veride kopartır (0.17). Ağırlık ölçümün
kendi kalitesini yansıtmalı.

`_boyut_tazele` içinde zaten hesaplanan ve ek maliyeti olmayan iki aday sinyal
var:

* `rafine_kutu`'nun döndürdüğü kutunun mevcut `boyut`a oranı — kod bunu zaten
  `0.35 < oran.mean() < 2.6` olarak deniyor; oranın 1'e yakınlığı ölçümün
  tutarlılığının doğrudan göstergesi.
* `yeni_c` ile `kf.konum` arasındaki mesafe — satır 568'de zaten hesaplanıyor
  (`0.6 * boyut.max()` kapısı için).

Bu, mevcut ölçümlerin yerine geçmez, yalnızca ağırlığını ayarlar; Deney 1/3/4A'yı
düşüren "türetilmiş büyüklük ölçümün yerine geçti" tuzağına girmez.

**Uygulamadan önce yapılması gereken:** aday sinyalin rafine'nin gerçek hatasıyla
korelasyonunu hem Gazebo'da hem VisDrone'da salt okunur ölçmek. Korelasyon
zayıfsa bu aday da düşer ve o zaman doğru hamle, ağırlığı sabit tutup DCF'in
arka plan bulaşmasını kaynağında ele almaktır (yama penceresi / `dolgu`), ki
o da 32 senaryonun tamamını etkiler ve ayrı bir tasarım turu gerektirir.
