# Deney 4P — Çeldirici nedensellik testi

**Salt okunur takipçi. `takip/` altında hiçbir dosya değiştirilmedi**, hiçbir
eşik / DCF / Kalman / lr / padding / geometri / ölçüm yöntemi değiştirilmedi,
parametre taraması yapılmadı, commit/push yok.
Yeni dosyalar (yalnızca deney düzeni): `gazebo/kaydet_4p.py`,
`gazebo/tani_4p_karsilastir.py`. Çıktı: `cikti/dcf_4p.json`.

Ölçüm kodu **4O'nun kodudur** (`gazebo.tani_4o_dcf`); yalnızca kaynak listesi
değişti.

## 0. Tek değişken denetimi

Yeni sahne, `senaryolar.G6_agresif_durakli()` **çağrılarak** üretildi ve
yalnızca `araclar` listesinden `"celdirici"` çıkarıldı. Mevcut hiçbir dosya
değişmedi; senaryo yalnızca kayıt sürecinin belleğine kaydedildi.

| alan | 4P | orijinal | |
|---|---|---|---|
| araçlar | `['hedef']` | `['hedef', 'celdirici']` | **tek fark** |
| `kam_x, kam_y, kam_z` | −24.0, 0.0, 45.0 | −24.0, 0.0, 45.0 | aynı |
| kamera profili (101 örnek) | — | — | **birebir aynı** |
| hedef profili (101 örnek) | — | — | **birebir aynı** |
| hedef `x0,y0,yaw,vx,renk` | — | — | **birebir aynı** |
| `kare` | 300 | 300 | aynı |
| `doku_seed` | 1 | 1 | aynı (zemin `_doku/zemin_1.png` önbelleğinden) |
| `drone_statik`, `hedef_ad`, `aile`, `siddet` | — | — | aynı |

Kayıt sonrası doğrulama: `pozlar.csv` başlığında `celdirici_*` sütunları
**yok**; 300 kare, düşen kare 0, 640×480.

## 1. Baseline doğrulaması (deneyden ÖNCE)

`takip/` md5'leri Deney 2 durumuyla **6/6 aynı** (deney öncesi = sonrası):

```
d41d8cd98f00b204e9800998ecf8427e  takip/__init__.py
c0fd7989d4e81219cd99447a12f8d78b  takip/cekirdekler.py
959da09ab43501a983629368a8f699b1  takip/egomotion.py
4257b94ce7f4978e172b8bb7c89816c1  takip/izleyici.py
874b3ccd540c8a6c783320c619a78f41  takip/mosse.py
3ff48dd869374d36937c18b640f2b21b  takip/tespit.py
```

Mevcut `G6_agresif_durakli` kaydı üzerinde takipçi yeniden koşuldu:

| | IoU | kilit | merkez | drift |
|---|---|---|---|---|
| ölçülen | **0.383141** | **%87.76** | **61.5326** | **148** |
| 4L / 4M / 4N / 4O | 0.383 | %87.8 | 61.53 | 148 |

**Baseline birebir üretildi.**

## 2. ZORUNLU EK KONTROL: kayıt gürültüsü tabanı

Gazebo kaydı bit-deterministik değildir. 4P'nin farkının çeldiriciden mi yoksa
kaydın tekrarlanabilirliğinden mi geldiğini ayırmak için **değişmemiş sahne
yeniden kaydedildi** (`G6_agresif_durakli_tekrar`).

Poz tekrarlanabilirliği (300 kare boyunca orijinale göre maksimum sapma):

| kayıt | hedef konumu | kamera konumu |
|---|---|---|
| tekrar | 0.0190 m (≈0.3 px) | 0.1105 m (≈1.7 px) |
| çeldiricisiz | 0.0118 m (≈0.2 px) | 0.1150 m (≈1.8 px) |

İki yeni kaydın orijinalden sapması **aynı büyüklükte** — yani sapma
çeldiricinin çıkarılmasından değil, kayıttan geliyor.

**Kayıt gürültüsü altında NE tekrarlanıyor, ne tekrarlanmıyor:**

| büyüklük | durakli | tekrar | hüküm |
|---|---|---|---|
| çekim noktası (138–146) | −7.26…−16.45 | −7.23…−16.53 | **≤ 0.15 px — tekrarlanır** |
| `dx` (138–148) | −0.014…−0.485 | −0.014…−0.462 | **≤ 0.07 hücre — tekrarlanır** |
| drift karesi | **148** | **148** | **tekrarlanır** |
| YK epizodunun başı | **151** | **151** | **tekrarlanır** |
| PSR (141–151) | 27.3…6.7 | 27.2…7.3 | ≤ 0.9 — tekrarlanır |
| KF hızı (141–151) | 2.09…0.51 | 2.10…0.49 | ≤ 0.06 — tekrarlanır |
| durum dizisi | KILITLI…SUPHELI(147,148) | aynı | **tekrarlanır** |
| **IoU** | **0.383** | **0.466** | **TEKRARLANMAZ (+0.083)** |
| **YK oranı** | **%44.6** | **%11.1** | **TEKRARLANMAZ** |

> Kopuşun **başlangıcı** tekrarlanabilir; kopuştan **sonrasının süresi**
> değildir. Bu yüzden 4P kararı IoU/YK oranı üzerinden değil, 4O'nun
> tekrarlanabilir büyüklükleri üzerinden verildi.

## 3. Dört koşulun genel sonucu

| koşul | senaryo | IoU | kilit | drift | YK karesi | YK oranı | ilk YK epizodu |
|---|---|---|---|---|---|---|---|
| durakli (4O) | `G6_agresif_durakli` | 0.383 | %87.8 | **148** | 115/258 | %44.6 | **151** |
| tekrar | `..._tekrar` | 0.466 | %88.8 | **148** | 29/261 | %11.1 | **151** |
| **çeldiricisiz** | `..._celdiricisiz` | 0.512 | %88.4 | **182** | **3/260** | **%1.2** | **262** |
| kontrol | `G6_agresif` | 0.618 | %100.0 | 294 | 0/294 | %0.0 | — |

## 4. 4O ölçümleri, kare 141–151, yan yana

### 1) DCF çekim noktası − GT (px)

| kare | durakli | tekrar | **çeldiricisiz** | kontrol |
|---:|---:|---:|---:|---:|
| 138 | −7.26 | −7.23 | **−3.88** | −6.55 |
| 140 | −8.03 | −8.14 | **−3.87** | −7.84 |
| **141** | **−8.23** | −8.18 | **−3.95** | **−8.23** |
| **142** | **−9.85** | −9.74 | **−3.99** | −8.32 |
| 143 | −12.07 | −12.02 | **−4.01** | −8.49 |
| 144 | −13.39 | −13.27 | **−4.05** | −8.60 |
| 145 | −15.43 | −15.50 | **−3.93** | −8.87 |
| 146 | −16.45 | −16.53 | **−3.76** | −9.25 |
| 147 | −27.24 | −29.64 | **−3.63** | −10.75 |
| 149 | −49.95 | −49.77 | **−3.12** | −11.02 |
| 151 | −55.06 | −55.00 | **−2.39** | −10.67 |

**Çeldiricisiz koşulda kayma yok**: 138–152 boyunca çekim noktası −4.05 ile
−2.39 px arasında **düz**. Üstelik hem çeldiricili koşulun 141 değerinden
(−8.23) hem de kontrolün değerinden (−8.23) **daha yakın**.

### 2) Alt-piksel `dx` (ızgara hücresi; 1 hücre = 3.69 px)

| kare | durakli | tekrar | **çeldiricisiz** | kontrol |
|---:|---:|---:|---:|---:|
| **141** | +0.044 | +0.099 | −0.069 | +0.086 |
| **142** | **−0.314** | **−0.303** | **+0.066** | +0.147 |
| 143 | −0.485 | −0.462 | −0.349 | +0.136 |
| 145 | −0.350 | −0.341 | −0.113 | −0.054 |
| 147 | +0.110 | +0.073 | −0.412 | −0.163 |

4O'nun 142'deki işaret dönüşü (−0.314) çeldiricisiz koşulda **yok** (+0.066).

### 3) DCF along-track artığı → 4) KF hızı → 5) PSR → 6) durum

| kare | | durakli | tekrar | **çeldiricisiz** | kontrol |
|---:|---|---:|---:|---:|---:|
| 141 | PSR | 27.3 | 27.2 | 24.7 | 20.4 |
| 144 | PSR | 19.2 | 18.9 | **20.7** | 24.6 |
| 146 | PSR | **10.5** | 9.8 | **21.9** | 24.8 |
| 147 | PSR | **6.7** | 7.3 | **18.5** | 24.4 |
| 150 | PSR | 13.4 | 12.7 | **26.9** | 18.2 |
| 141 | KF hızı | 2.09 | 2.10 | 2.02 | 1.44 |
| 145 | KF hızı | **0.64** | 0.63 | **1.83** | 1.83 |
| 147 | KF hızı | **0.51** | 0.49 | **2.01** | 1.42 |
| 149 | KF hızı | **7.61** | 7.66 | **1.63** | 1.25 |
| 147 | durum | **SUPHELI** | **SUPHELI** | **KILITLI** | KILITLI |
| 148 | durum | **SUPHELI** | **SUPHELI** | **KILITLI** | KILITLI |

### 7) Yanlış kilit

| koşul | 141–151 aralığında YK | ilk epizot |
|---|---|---|
| durakli | var (151'den itibaren) | 151 |
| tekrar | var (151'den itibaren) | 151 |
| **çeldiricisiz** | **yok** | 262 (3 kare) |
| kontrol | yok | — |

### 8) Ego artığı (px) — DEĞİŞMİYOR

| kare | durakli | tekrar | çeldiricisiz | kontrol |
|---:|---:|---:|---:|---:|
| 141 | 2.32 | 2.33 | 2.29 | 2.08 |
| 145 | 2.03 | 2.02 | 1.98 | 1.92 |
| 149 | 1.64 | 1.66 | 1.65 | 1.76 |

Ego kanalı dört koşulda da aynı (≤0.1 px) — beklendiği gibi, çeldiricinin
ego kestirimine etkisi yok.

### 9) Arama merkezi − GT (px)

| kare | durakli | tekrar | **çeldiricisiz** | kontrol |
|---:|---:|---:|---:|---:|
| 141 | −8.46 | −8.61 | **−3.74** | −8.55 |
| 143 | −9.95 | −9.88 | **−2.22** | −8.97 |
| 145 | −14.47 | −14.46 | **−3.41** | −8.69 |
| 147 | −18.41 | −18.37 | **−1.41** | −9.27 |
| 149 | −35.51 | −35.57 | **−2.61** | −10.86 |
| 151 | −62.07 | −61.91 | **−1.38** | −11.53 |

## 5. Sorulara nokta yanıt

| soru | yanıt |
|---|---|
| 141'de başlangıç durumları aynı mı? | Çeldiricili iki kayıt (durakli/tekrar) birebir; **çeldiricisiz koşul 141'de zaten daha iyi** (çekim −3.95 vs −8.23) — çünkü çeldirici 141'de de 18 px'te ve etkisi zaten var |
| 142'de çekim noktası yine kayıyor mu? | **HAYIR.** −3.95 → −3.99 (Δ = −0.04 px); çeldiricili koşulda Δ = −1.62 px |
| 142→147 kayma devam ediyor mu? | **HAYIR.** −3.95 → −3.63 (net **+0.32 px**); çeldiricili: −8.23 → −27.24 |
| KF hızı yine çöküyor mu? | **HAYIR.** 2.02 → 2.01 (çeldiricili: 2.09 → 0.51) |
| PSR yine düşüyor mu? | **HAYIR.** 24.7 → 18.5 → 26.9 (çeldiricili: 27.3 → 6.7) |
| 147 sonrası lock kaybı oluşuyor mu? | **HAYIR.** SUPHELI'ye hiç girmiyor; çeldiricili koşulda 147–148 SUPHELI, 151'de YK |

## 6. Kalan olay: kare 186 — AYNI mekanizma değil

Çeldiricisiz koşum yine de kare 182'de drift eşiğinin altına iniyor ve 186'da
kilit reddediliyor. Bu olayın karakteri 4O'nunkinden **tamamen farklıdır**:

| | 4O olayı (çeldiricili, 142–151) | 4P kalan olayı (186) |
|---|---|---|
| hedef hızı | 6.1 → 4.6 m/s (yavaşlıyor) | **0.07–0.27 m/s (DURMUŞ)** |
| çekim noktası | −8.2 → −27 → −55 (kaçıyor) | −5.5 … +1.5 (**düz**) |
| PSR | 27 → 6.7 (çöküyor) | 18–38 (**sağlıklı**) |
| IoU | **0.00** (kutu zeminde) | **0.23–0.33** (kutu hâlâ araçta) |
| kilit reddi | 180, 222, 258 — hepsi IoU = 0'da | **tek red: 186**, IoU 0.27'de |
| önceki 25 karede <0.5 m/s | 12 | **18** |
| durum geçişi | SUPHELI → yanlış KILITLI | KILITLI → **ARAMA** (savunma reddetti) |

Yani çeldiricisiz koşumda takipçi **hedefi hiç bırakmıyor**; araç 18 kare
durduğu için `_bagimsiz_dogrula`'nın **belgelenmiş "duran araç" sınırı**
(`zemin_sabir = 20`) doğru kilidi reddediyor.

Bu, 4L'nin açtığı bir soruyu da kapatıyor: `senaryolar.py:399`'un iddiası
(*"takipçinin duran-araç sınırının Gazebo'da tekrarlanabildiğini gösterir"*)
**sahne tasarımı için doğruymuş**; ama sahnedeki çeldirici, o sınırdan
**34 kare önce** başka bir arıza üretip onu maskeliyordu. 4L'nin "iddia
desteklenmiyor" hükmü gözlenen arıza için doğruydu; 4P sebebini gösteriyor.

---

# KARAR: **A) ÇELDİRİCİ NEDENSEL OLARAK DESTEKLENDİ**

Önceden sabitlenen kural A'nın iki koşulu da sağlandı:

1. **Çekim noktası / kritik DCF `dx` kontrol koşuluna döndü** — hatta ondan
   iyi: 142'de `dx` −0.314 → **+0.066**; çekim noktası 138–152 boyunca −4.05
   ile −2.39 px arasında **düz** (çeldiricili: −8.23 → −55.06).
2. **Test edilen kopuş ortadan kalktı** — 147'deki SUPHELI, 148'deki tamsayı
   tepe sıçraması ve 151'deki yanlış kilit **hiç oluşmuyor**; PSR, KF hızı,
   arama merkezi ve durum dizisi 141–151 boyunca sağlıklı kalıyor.

Bu hüküm **kayıt gürültüsü tabanına karşı** verildi: değişmemiş sahnenin
yeniden kaydı (`tekrar`) 4O'nun bütün kritik büyüklüklerini ≤0.15 px / ≤0.07
hücre içinde tekrarladı ve **aynı karede (148) kırıldı, aynı karede (151)
yanlış kilide düştü**. Yani 4P'deki değişim kayıttan gelemez.

**Ne kanıtlanmadı (ve iddia edilmiyor):** çeldiricinin kaldırılması senaryoyu
düzeltmez. Kalan kopuş (kare 186) ayrı ve **belgelenmiş** bir mekanizmadır
(duran araç → `zemin_sabir` kilidi reddeder), 4O mekanizması değildir; §6'daki
altı ölçüt bunu ayırıyor. `G6_agresif_durakli_celdiricisiz` bir "çözüm" değil,
bir **teşhis düzeneğidir**.

### Sonraki tek mantıklı adım

> **4M–4O zincirinin karar çiftini yeniden kur.**
> `G6_agresif_durakli`'nin yanlış kilidi artık bir takipçi arızası değil,
> **sahne artefaktı** olarak açıklanmıştır (aynı satırda 1.5 px'e kadar
> yaklaşan çeldirici). 4L'nin "karar verilebilir tek yanlış-kilit kaynağı"
> hükmü bu nedenle geçersizdir: ölçtüğü şey takipçinin genel bir zaafı değil,
> tek bir sahnenin geometrisidir.
> Bu yüzden bir sonraki tur, **optimizasyon değil**, karar tabanının yeniden
> kurulması olmalı: 4L'nin envanteri (22 Gazebo + 6 VisDrone) **çeldirici–hedef
> görüntü mesafesi** sütunuyla yeniden okunmalı ve "yanlış kilit" karelerinin
> kaçının bu konjonksiyonla açıklandığı salt okunur olarak ölçülmelidir.
> Bu ölçülmeden hiçbir yanlış-kilit optimizasyonu doğru hedefe nişan alamaz.

**Bu turda hiçbir optimizasyon, parametre taraması ya da çözüm uygulanmadı;
`takip/` md5 6/6 aynı.**
