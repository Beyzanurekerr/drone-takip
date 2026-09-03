# Deney 4O — 141 → 142 geçişinde DCF ölçümü nerede ayrışıyor?

**Salt okunur. `takip/` altında hiçbir dosya değiştirilmedi**, hiçbir eşik/
Kalman/DCF/öğrenme/rafine parametresi değiştirilmedi, commit/push yok.
Araç: `gazebo/tani_4o_dcf.py`. Çıktı: `cikti/dcf_4o.json`,
`cikti/dcf_4o_arsiv.npz`.

## 0. Baseline doğrulaması

`takip/` md5'leri Deney 2 durumuyla **6/6 aynı** (deney öncesi = sonrası):

```
d41d8cd98f00b204e9800998ecf8427e  takip/__init__.py
c0fd7989d4e81219cd99447a12f8d78b  takip/cekirdekler.py
959da09ab43501a983629368a8f699b1  takip/egomotion.py
4257b94ce7f4978e172b8bb7c89816c1  takip/izleyici.py
874b3ccd540c8a6c783320c619a78f41  takip/mosse.py
3ff48dd869374d36937c18b640f2b21b  takip/tespit.py
```

| kaynak | IoU | kilit | drift | **sadakat ihlali** |
|---|---|---|---|---|
| G6_agresif_durakli | 0.383 | %87.8 | 148 | **0** |
| G6_agresif | 0.618 | %100.0 | 294 | **0** |
| 117/23 | 0.701 | %100.0 | yok | **0** |
| 137/12 | 0.548 | %94.6 | 75 | **0** |

Gerçek `RenkDcfCekirdek` aynen çalıştı; sarmalayıcı yanında koşan kopyanın
ürettiği `(yeni, psr)` her çağrıda gerçekle karşılaştırıldı — **hiç sapma yok.**

## 1. Ölçekten gelen zorunlu bilgi

`_kanallar` yamayı `w = boyut[0]·dolgu(2.0)`, `h = boyut[1]·2.0` kesip
**32×32** ızgaraya indiriyor. `_tepe` yer değiştirmeyi
`((ix + dx) − N//2) · w/N` ile piksele çeviriyor. Bu pencerede:

* `boyut = (59.1, 36.3)` → bir ızgara hücresi x'te **3.69 px**, y'de 2.28 px.

4M'nin ayrışması **1.2 px = 0.33 hücre**tir. Yani ayrışma tamsayı `argmax`
bölgesinde değil, **alt-piksel parabolik terimde** aranmalıdır. Bu yüzden
tamsayı tepe ile alt-piksel terim ayrı ayrı raporlanıyor.

Ayrıca: `merkez` her zaman ızgara `(16, 16)`'ya düşer (formülün kendisi
böyle). **"Tepenin arama merkezine uzaklığı" ile "tepenin harita merkezine
uzaklığı" aynı büyüklüktür**; ayrı bir koordinat dönüşümü yoktur.

## 2. Kare kare DCF atomları (130–148)

`akt` = açı araması aktif mi, `nA` = değerlendirilen aday sayısı.

### `G6_agresif_durakli`

| kare | akt | nA | ix | iy | **dx** | dy | tepe | ikinci | tepe/ikinci | PSR | artık_x (px) |
|---:|:--:|--:|--:|--:|---:|---:|---:|---:|---:|---:|---:|
| 138 | – | 1 | 16 | 16 | −0.014 | −0.052 | 0.655 | 0.085 | 7.66 | 23.9 | −0.05 |
| 139 | – | 1 | 16 | 16 | +0.001 | −0.058 | 0.667 | 0.083 | 8.07 | 26.0 | +0.00 |
| 140 | – | 1 | 16 | 16 | +0.037 | +0.004 | 0.679 | 0.077 | 8.86 | 27.6 | +0.14 |
| **141** | – | 1 | **16** | **16** | **+0.044** | +0.010 | 0.683 | 0.077 | 8.89 | 27.3 | **+0.16** |
| **142** | – | 1 | **16** | **16** | **−0.314** | −0.002 | 0.672 | 0.081 | 8.34 | 25.7 | **−1.16** |
| 143 | – | 1 | 16 | 16 | −0.485 | +0.052 | 0.672 | 0.089 | 7.55 | 24.8 | −1.79 |
| 144 | – | 1 | 16 | 16 | −0.325 | +0.051 | 0.561 | 0.103 | 5.45 | 19.2 | −1.20 |
| 145 | – | 1 | 16 | 16 | −0.350 | +0.026 | 0.495 | 0.135 | 3.67 | 15.7 | −1.29 |
| 146 | – | 1 | 16 | 16 | +0.005 | +0.179 | 0.375 | 0.172 | 2.18 | 10.5 | +0.02 |
| 147 | – | 1 | 16 | 16 | +0.110 | +0.150 | 0.250 | 0.213 | 1.18 | 6.7 | +0.41 |
| **148** | – | 1 | **9** | 16 | +0.053 | +0.450 | 0.251 | 0.107 | 2.34 | 7.9 | **−25.62** |

### `G6_agresif` (kontrol)

| kare | akt | nA | ix | iy | **dx** | dy | tepe | ikinci | tepe/ikinci | PSR | artık_x (px) |
|---:|:--:|--:|--:|--:|---:|---:|---:|---:|---:|---:|---:|
| 138 | – | 1 | 16 | 16 | −0.136 | +0.040 | 0.757 | 0.092 | 8.21 | 26.0 | −0.50 |
| 139 | – | 1 | 16 | 16 | −0.080 | +0.048 | 0.749 | 0.112 | 6.67 | 22.5 | −0.29 |
| 140 | – | 1 | 16 | 16 | −0.037 | +0.054 | 0.734 | 0.114 | 6.44 | 20.2 | −0.14 |
| **141** | – | 1 | **16** | **16** | **+0.086** | +0.023 | 0.719 | 0.102 | 7.08 | 20.4 | **+0.31** |
| **142** | – | 1 | **16** | **16** | **+0.147** | +0.007 | 0.714 | 0.093 | 7.71 | 22.2 | **+0.54** |
| 143 | – | 1 | 16 | 16 | +0.136 | −0.051 | 0.708 | 0.092 | 7.67 | 24.0 | +0.50 |
| 144 | – | 1 | 16 | 16 | +0.096 | −0.032 | 0.715 | 0.089 | 8.04 | 24.6 | +0.35 |
| 145–148 | – | 1 | 16 | 16 | −0.054…−0.172 | ±0.1 | 0.700–0.727 | 0.082–0.120 | 6.0–8.8 | 23.0–25.6 | −0.20…−0.63 |

## 3. İlk farklılaşan değişken

141'de iki senaryo aşağıdaki **her** değişkende aynıdır: tamsayı tepe (16, 16),
tepe merkezden uzaklık 0 hücre, aday sayısı 1, açı araması kapalı, ölçek
3.69 px/hücre, ego taşıması (−8.31, −10.99) vs (−8.31, −10.99).

142'de **ilk ve tek kez farklılaşan büyüklük `dx`'tir:**

| | 141 | 142 | Δ |
|---|---:|---:|---:|
| durakli `dx` | +0.044 | **−0.314** | **−0.358 hücre = −1.32 px** |
| kontrol `dx` | +0.086 | **+0.147** | +0.061 hücre = +0.22 px |

`dx` yalnızca üç komşu hücreden hesaplanır
(`dx = 0.5·(sol − sağ) / (sol − 2·tepe + sağ)`), yani **yanıt haritasının
tepe çevresindeki sol/sağ asimetrisi**dir. Ham değerler:

| kare | senaryo | sol | tepe | sağ | **sol − sağ** | eğrilik |
|---:|---|---:|---:|---:|---:|---:|
| 141 | durakli | 0.60782 | 0.68275 | 0.61999 | **−0.01216** | −0.1377 |
| **142** | durakli | 0.64763 | 0.67205 | 0.56508 | **+0.08256** | −0.1314 |
| 141 | kontrol | 0.65412 | 0.71930 | 0.67316 | **−0.01904** | −0.1113 |
| **142** | kontrol | 0.63845 | 0.71371 | 0.67271 | **−0.03426** | −0.1163 |

durakli'de tek karede sol komşu **+0.040 yükseliyor**, sağ komşu
**−0.055 düşüyor**; eğrilik ve tepe değeri neredeyse sabit. Kontrolde aynı
karede asimetri yönünü korumakla kalmıyor, biraz **güçleniyor**.

## 4. A–J hipotezlerinin tek tek ölçümü

| | hipotez | **hüküm** | ölçüm |
|---|---|---|---|
| **A** | DCF tepesi haritada başka bir yere sıçrıyor | **HAYIR** | tamsayı `argmax` 130–147 arasında **her karede (16, 16)**; iki senaryoda da. İlk sıçrama **148**'de (ix 16 → 9), yani ayrışmadan **6 kare sonra** |
| **B** | yanıt haritasının tamamı kayıyor | **HAYIR** | tepe merkezde kalıyor (uzaklık 0 hücre); tepe değeri 0.683 → 0.672 (durakli), 0.719 → 0.714 (kontrol) |
| **C** | arama merkezi (KF/ego) değişiyor | **HAYIR** | ego taşıması iki senaryoda 0.01 px içinde aynı; arama merkezinin GT'ye göre konumu 141'de (−8.46, +2.88) vs (−8.55, +2.63), 142'de (−8.67, +2.59) vs (−9.00, +2.77) — **fark 0.4 px'in altında ve yönü ayrışmayı açıklamıyor** |
| **D** | arama penceresi farklı bir bölge görüyor | **EVET — ayrışmanın kaynağı burada** | §5'teki 2×2 çözümleme: değişimin **%94'ü yamadan** geliyor |
| **E** | şablon A/B içerikleri farklılaşıyor | **HAYIR (≤%6)** | §5; ayrıca `dA` durakli 0.0450 → 0.0467, kontrol 0.0355 → 0.0354 — 142'de sıçrama yok |
| **F** | PSR düşüşü tepe seçimini değiştiriyor | **HAYIR** | `nA = 1` (tek aday) her karede; PSR seçimde kullanılmıyor. PSR 142'de 27.3 → 25.7 (durakli) ve 20.4 → **22.2 yükseliyor** (kontrol) — ama seçimi etkileyen bir yol yok |
| **G** | ikinci tepe / çeldirici tepe çıkıyor | **HAYIR (142'de)** | ikinci tepe 0.077 → 0.081, oran 8.89 → 8.34. Rekabet **146–147'de** başlıyor (oran 2.18 → 1.18) — ayrışmadan 4–5 kare sonra |
| **H** | alt-piksel / tepe rafinesi | **EVET — farkın tamamı burada görünüyor** | §3; ayrışma −0.358 hücre, tamsayı terim sabit |
| **I** | koordinat dönüşümü farkı | **HAYIR** | `aci = 0`, `aktif = False` her karede → `ara`'nın döndürme kolu (satır 213–218) hiç çalışmıyor; ölçek iki senaryoda 3.688 / 2.281 vs 3.656 / 2.188 |
| **J** | hiçbiri | — | D + H |

**A/B/C/E/F/G/I ölçülerek elendi. Kalan: yamanın içeriği (D), etkisi
alt-piksel terimde (H) görünüyor.**

## 5. Şablon mu, yama mı? — 2×2 çapraz çözümleme

`ara` çağrısında kullanılan şablon (`A`, `B`) ve yama (`kan`) 134–152 arası
arşivlendi; sonra dört bileşim için `dx` yeniden hesaplandı (salt okunur):

### `G6_agresif_durakli`

| şablon ↓ / yama → | 141 | 142 |
|---|---:|---:|
| **A₁₄₁** | +0.044 *(gerçek 141)* | **−0.291** |
| **A₁₄₂** | +0.046 | −0.314 *(gerçek 142)* |

* yama 141 → 142 (şablon sabit): **−0.335 hücre** → toplam değişimin **%94'ü**
* şablon 141 → 142 (yama sabit): **+0.002 hücre** → **%0.5**

### `G6_agresif` (kontrol)

| şablon ↓ / yama → | 141 | 142 |
|---|---:|---:|
| **A₁₄₁** | +0.086 | +0.184 |
| **A₁₄₂** | +0.072 | +0.147 |

Kontrolde de yama baskın (+0.098 vs −0.014), ama **işareti ters**.

> **Şablon hipotezi (E) sayısal olarak elendi. Ayrışma yamadan geliyor.**

## 6. DCF'in "çekim noktası" — asıl kayan büyüklük

Yamanın hangi yönde çektiğini tek karede okumak yanıltıcıdır. Bu yüzden salt
okunur olarak, o karenin **gerçek `A`, `B`'siyle** arama merkezi x ekseninde
±16 px taranıp ölçülen yer değiştirmenin sıfırlandığı **sabit nokta** (DCF'in
kendiliğinden oturduğu yer) bulundu:

| kare | durakli çekim − GT | kontrol çekim − GT |
|---:|---:|---:|
| 140 | −8.03 | −7.84 |
| **141** | **−8.23** | **−8.23** |
| **142** | **−9.85** | −8.32 |
| 143 | **−12.07** | −8.49 |
| 144 | **−13.39** | −8.60 |

**141'de iki senaryonun çekim noktası GT'ye göre birebir aynıdır (−8.23).**
142'den itibaren durakli'ninki hızla kaçıyor (−1.62, −2.22, −1.32 px/kare),
kontrolünki −0.1 px/kare ile yerinde duruyor. Takipçinin merkezi bu çekim
noktasını izliyor — 4M'de ölçülen artık işareti bunun gözlenen yüzüdür.

## 7. Sahne geometrisi: iki senaryoda çeldirici aynı yerde değil

Çekim noktasını taşıyan şey yamanın içeriğidir; yamanın içine ne girdiği
GT ile ölçüldü (DCF penceresi `dolgu=2.0` ile **118×72 px**):

| kare | durakli: çeldirici Δx, Δy, mesafe | kontrol: çeldirici Δx, Δy, mesafe |
|---:|---|---|
| 138 | +29.65, −0.70, **29.65** | +42.30, −12.89, **44.22** |
| 140 | +21.97, +0.07, **21.97** | +35.21, −12.04, **37.21** |
| **141** | +18.27, +0.37, **18.27** | +31.74, −11.76, **33.85** |
| **142** | +14.64, +0.62, **14.66** | +28.32, −11.54, **30.58** |
| 143 | +11.11, +0.81, **11.14** | +24.95, −11.36, **27.42** |
| 145 | +4.33, +1.05, **4.46** | +18.39, −11.13, **21.49** |

İki fark birden var:
1. **Mesafe**: durakli'de çeldirici 142'de 14.7 px'e giriyor; kontrolde 30.6 px.
2. **Satır hizası**: durakli'de Δy ≈ **0** (iki araç aynı görüntü satırında);
   kontrolde Δy ≈ **−12 px** (ayrı satır).

Kamera özdeş, çeldirici dünyada sabit; fark **hedefin hız profilinden doğan
konum farkıdır**. 4N'de 3× rafine penceresinde ölçülen birleşme (kare 135) ile
burada 2× DCF penceresinde ölçülen ayrışma (kare 142) **aynı sahne olayının**
iki farklı pencere ölçeğindeki görünümüdür — büyük pencere önce etkileniyor.

## 8. Karşıt-olgu denemesi ve NEDEN YETERSİZ olduğu

Görüntüden çeldirici `cv2.inpaint` ile silinip çekim noktası yeniden ölçüldü.
Müdahalenin kendi artefaktını ölçmek için **plasebo** eklendi: aynı boyutta
kutu, çeldiricinin hedefe göre **ayna** konumunda (boş zemin olması beklenir).

| kare | senaryo | gerçek | çeldirici silinmiş | **çeldirici etkisi** | **plasebo artefaktı** |
|---:|---|---:|---:|---:|---:|
| 142 | durakli | −9.85 | −8.37 | **+1.48** | **−2.91** |
| 143 | durakli | −12.07 | −8.57 | **+3.50** | **+3.77** |
| 142 | kontrol | −8.32 | −7.75 | +0.56 | **−0.26** |
| 143 | kontrol | −8.49 | −7.94 | +0.55 | **−0.56** |

Silme durakli'de çekim noktasını tam kontrolün seviyesine (−8.37 / −8.57) geri
getiriyor — beklenen yönde. **Ama plasebo da aynı büyüklükte oynuyor**
(−2.91, +3.77), çünkü çeldirici hedefe 11–15 px mesafededir ve ayna konumu da,
inpaint maskesi de hedefin kendisine değiyor. Kontrolde çeldirici 28–31 px
uzakta olduğu için plasebo temiz (≈0) ve orada çeldiricinin ölçülen etkisi
yalnızca **+0.5 px**.

> **Bu karşıt-olgu, çeldiriciyi nedensel olarak kanıtlamaz.** Doğru yönü
> gösteriyor ama müdahale ile hedef birbirinden ayrılamıyor. Rapor bunu
> korelasyon olarak kaydeder, mekanizma ilan etmez.

## 9. Gerçek veride kontrol (karar dayanağı değil)

| kaynak | DCF karesi | **tamsayı tepe = merkez** | ort \|dx\| | ort \|dy\| | hücre boyu (px) |
|---|---:|---:|---:|---:|---:|
| G6_agresif_durakli | 263 | **%91.3** | 0.119 | 0.086 | 3.69 |
| G6_agresif | 293 | **%81.2** | 0.134 | 0.112 | 3.69 |
| 117/23 | 342 | **%80.7** | 0.169 | 0.125 | 3.53 |
| 137/12 | 214 | **%85.5** | 0.147 | 0.142 | 4.81 |

Yani **DCF ölçümü karelerin %81–91'inde tamamen alt-piksel terimden
ibarettir**; bu G6'ya özgü değil, dört kaynakta da geçerli genel rejimdir.
Fark: 137/12'nin drift ettiği pencerede (kare 63–80) tamsayı tepe **gerçekten
merkezden ayrılıyor** (8 kare) — yani gerçek veride kopuş G6'dakinden farklı
bir rejimde de olabiliyor. Bu iki dizi karar için kullanılmadı.

---

# KARAR: **KÖK NEDEN ADAYI DESTEKLENDİ**

**Kesin olarak saptanan (ölçümle, korelasyonla değil):**

1. **İlk farklılaşan değişken: alt-piksel `dx`, kare 142.** 141'de tamsayı
   tepe, tepe konumu, aday sayısı, açı, ölçek, ego taşıması ve arama
   merkezinin GT'ye göre konumu iki senaryoda aynıdır; 142'de yalnızca `dx`
   ayrışır (−0.358 hücre vs +0.061 hücre).
2. **Aşama: DCF ölçümünün YAMASI.** 2×2 çapraz çözümleme değişimin **%94'ünü
   yamaya**, **%0.5'ini şablona** veriyor. Şablon (E), tamsayı sıçrama (A),
   harita kayması (B), arama merkezi (C), PSR ile seçim (F), ikinci tepe (G)
   ve koordinat dönüşümü (I) **ölçülerek elendi**.
3. **Kayan asıl büyüklük DCF'in çekim noktasıdır**: 141'de iki senaryoda
   GT − 8.23 px ile **birebir aynı**; 142'den itibaren durakli'de
   −9.85 → −12.07 → −13.39, kontrolde −8.32 → −8.49 → −8.60.
4. Zamansal sıra: çekim noktası kayması (142) → KF hızının çökmesi (143) →
   PSR düşüşü (144) → SUPHELI (147) → tamsayı tepe sıçraması (148) →
   yanlış kilit (151). **Tamsayı tepe sıçraması bir sonuçtur, sebep değildir.**

**Desteklenen ama henüz kanıtlanmayan:** yamayı bozan içeriğin **çeldirici
araç** olduğu. Lehine: 141–142'de durakli'de çeldirici 18.3 → 14.7 px'e ve
Δy ≈ 0'a (aynı satır) giriyor, kontrolde 33.9 → 30.6 px ve Δy ≈ −12 px'te
kalıyor; silme denemesi çekim noktasını tam kontrolün değerine getiriyor.
Aleyhine: plasebo aynı büyüklükte oynuyor (§8), yani müdahale hedeften
ayrıştırılamıyor.

### Sonraki TEK deney adayı

> **`G6_agresif_durakli_celdiricisiz` kaydı al ve tek ölçümü yap.**
> Aynı kamera bozulması, aynı hedef hız/yaw profili, aynı zemin —
> **tek fark: çeldirici araç dünyadan çıkarılır** (`gazebo/dunya_uret.py`
> ikinci aracı üretmez). Sonra bu deneyin çekim-noktası ölçümü (§6) aynı
> karelerde tekrarlanır.
> * Çekim noktası 141'den sonra GT − 8.2 px'te kalıyorsa → çeldirici
>   **nedensel olarak kanıtlanır** ve yanlış kilit kaybolur.
> * Çekim noktası yine kaçıyorsa → yamayı bozan şey çeldirici değildir ve
>   arama, hedefin kendi görünüm değişimine (yaw/kısalma) yönelir.
>
> Bu, §8'in plasebo sorununu tamamen ortadan kaldıran **tek** ölçümdür:
> müdahale görüntüde değil, sahnenin kendisinde yapılır; hedefe hiç
> dokunulmaz.

**Bu turda hiçbir optimizasyon, hiçbir eşik değişikliği yapılmadı;
`takip/` md5 6/6 aynı.**
