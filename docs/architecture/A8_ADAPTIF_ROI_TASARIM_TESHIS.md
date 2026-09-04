# A8 — Adaptif ROI: tasarım + salt okunur teşhis

**Tarih:** 2026-09-02 · **Kod:** `gazebo/tani_a8_adaptif_roi.py` (yeni, salt okunur gözlemci)
**Veri:** `cikti/a8_adaptif_roi_teshis.json` (3.8 MB, kare başına kayıtlar dahil)

## 0. Kapsam ve bütünlük

**Bu bir SÜREKLİLİK / yeniden-tespit teşhisidir, EDİNME teşhisi değildir.** Adaptif ROI
bir önsel (konum + boyut) gerektirir; soğuk başlangıçta önsel yoktur. A7 §3 bunu zaten
söylemişti: *"eksik olan çözünürlük değil, konum bilgisi."* Edinme boşluğu A8'in konusu
değildir ve burada çözülmemiştir.

**Bu turda:** eğitim yok · model/ağırlık değişikliği yok · hiperparametre değişikliği yok ·
P2 yok · imgsz değişikliği yok · SAHI çoklu tile yok · commit/push yok.

**Değişmediği doğrulanan dosyalar** (md5 koşum öncesi + sonrası, 9/9 aynı):

| dosya | md5 | mtime |
|---|---|---|
| `takip/cekirdekler.py` | `c0fd7989…` | 2026-08-25 |
| `takip/egomotion.py` | `959da09a…` | — |
| `takip/izleyici.py` | `4257b94c…` | 2026-08-28 15:28 |
| `takip/mosse.py` | `874b3ccd…` | — |
| `takip/tespit.py` | `3ff48dd8…` | — |
| `gazebo/bench_a52_kucuk_hedef.py` | **`45623cc5efa1c73d53d9f1a7865fb4a1`** | 2026-08-31 01:04 |
| `weights/yolov8n.pt` | `95a24496…` | — |
| `runs/a6/asamaB/weights/best.pt` | `1fa73c65…` | — |

`gazebo/tani_a7_roi.py` (md5 `4985e97c…`, mtime **2026-09-01 17:55**) yalnızca **modül
olarak içe aktarıldı**, düzenlenmedi — mtime koşumdan (2026-09-02 14:38) önce.
A5.2 bench'i de aynı şekilde modül olarak import edildi; yalnızca iki modül değişkeni
(`AGIRLIK`, `SINIFLAR`) geçersiz kılındı, A7'deki uygulamanın aynısı.

### AÇIK ÇEVRİM — her tabloya iliştirilen uyarı

**Dedektör sonucu takipçiyi BESLEMEZ.** Takipçi kendi DCF ölçümüyle bağımsız koşar
(A7'nin takipçi kolundaki gibi). Bu salt-okunurluğu korur, ama şu demektir:

> **BU RAPORDAKİ HER SAYI BİR ÜST SINIRDIR.**
> Gerçek sistemde ROI'den gelen tespit takipçiyi besleyecek, takipçi boyutu güncelleyecek,
> boyut R'yi seçecek → **çevrim kapanır**. Deney 1/3/4A/4S/4U dersi ve 4T/4U üst-sınır
> dersi (açık çevrim ROC AUC 0.89 → kapalı çevrimde IoU 0.548 → 0.190) burada da geçerlidir.

### Plandan tek sapma: `adaptif_ego` kolu düşürüldü

Revize plan ego-telafili bir merkez kolu öngörüyordu. **Bu test yatağında anlamsız:**
A5.2 kompoziti arkaplan penceresini sabit tutar (`bench_a52_kucuk_hedef.py` satır 60:
*"Arkaplan penceresi SABIT → kamera ego-hareketi yok"*). Ego homografisi birim matrise
yakındır ve hareket eden hedefi izleyemez. Ego tabanlı merkez öngörüsü ancak gerçek
kamera hareketi olan bir yatakta (Gazebo / ham VisDrone) ölçülebilir. **Düşürüldü.**

---

## 1. Büyütme aritmetiği — ölçülmedi, türetildi

A7 tanımı: seviye `L` = hedefin **tam karede ağdaki** px boyu; sensörde hedef `2L` px.
ROI kolunda mutlak ölçek `AG_W / R`.

```
ag_px = L_sensor · 640 / R          R_opt = L_sensor · 640 / 75
```

| basamak | ROI (sensör px) | büyütme | ağdaki px | 60–90 bandını sağlayan L | A7'de ölçüldü |
|---|---|---|---|---|---|
| R=640 | 640×360 | 2× | 2·L | **30.0 – 45.0** | evet |
| R=320 | 320×180 | 4× | 4·L | **15.0 – 22.5** | evet |
| R=160 | 160×90 | 8× | 8·L | **7.5 – 11.25** | evet |
| R=80 | 80×45 | 16× | 16·L | **3.75 – 5.62** | **HAYIR — yeni basamak** |

**Merdiven boşlukları: L = 11.25–15 ve L = 22.5–30.** Bu bantlarda hiçbir basamak hedefi
60–90'a getiremez. Ölçüldü: L=12'de kural R=160 seçiyor ve hedef ağda **96 px** oluyor.

R=80 basamağı A7'de ölçülmemişti; 5×5'in bir şansı olup olmadığını görmek için eklendi
ve aşağıda ayrıca etiketlendi.

**Sorulan üç seviye mevcut merdivende zaten banttadır:** 15×7 → R=320 (net 60) ·
10×5 → R=160 (net 80) · 8×5 → R=160 (net 64). Yani büyütme yarısı A8'den önce çözülmüştü;
ölçüm harcanmadı.

---

## 2. Test yatağı düzeltmesi — A7'de bozuktu

A7'nin süreklilik ölçümü (§4, 14–20 px bulgusu) `daralan_dizi` ile yapılmıştı ve o fonksiyon
tuvali **`B.TUVAL` = 640×360**'ta kuruyor. ROI için kullanılamaz: **kırpılacak native piksel
yok.** Bu, A7 §1'de açıkça reddedilen hatanın aynısıdır (*"küçültülmüş bir kareyi dilimlemek
hiçbir şey vermez"*).

A8 iki yatak kurar, **ikisi de 1280×720 sensör çözünürlüğünde**:

- **Yatak S (statik seviye):** `A7.sensor_dizi` — hedef 60 kare boyunca sabit seviyede.
  Merkezleme ve boyut-tahmini hatalarını izole eder.
- **Yatak D (daralan):** `daralan_sensor_dizi` — **yeni**; hedef 60 karede L=40 → L=5'e
  geometrik küçülür. Kuralın *uyarlanıp uyarlanmadığını* test eder. A7'nin `daralan_dizi`'sinin
  sensör çözünürlüğüne taşınmış hâli; ölçek değişmezliği ilkesi (hareket her karede o karenin
  ölçeğiyle çarpılır) korunmuştur.

Diziler: **117/23 ve 137/12 karar için**, 305/5 destekleyici. Karar dışı kaynaklar
(182/127, 268/31, 339/49, 086, sim test2/test3) hiç kullanılmadı.

---

## 3. Kollar

| kol | ROI merkezi | R kaynağı | tür |
|---|---|---|---|
| `tam_kare` | — | — | referans |
| `sabit_R320_kf` | takipçi | sabit 320 | referans (A7'nin `roi320_takipci`'si) |
| **`adaptif_kf`** | **takipçi** | **takipçi boyut tahmini** | **ASIL OPERASYONEL KOL** |
| `oracle_merkez` | **GT** | takipçi tahmini | üst sınır — MERKEZ hatasını izole eder |
| `oracle_boyut` | takipçi | **GT** | üst sınır — BOYUT hatasını izole eder |
| `oracle_tam` | **GT** | **GT** | mutlak tavan |

`oracle_*` kolları **başarı değildir**, üst sınırdır. `oracle_merkez` / `oracle_boyut`
ayrımı A8'in omurgasıdır: hangi hata kanalının kaç puan yediğini ayrıştırır
(A3.9'daki `tavan_iou` mantığının aynısı).

Tüm kollar **aynı takipçi yörüngesini** kullanır (dizi başına bir kez koşulur), böylece
kollar arasındaki tek fark ROI seçimidir.

---

## 4. Ana sonuç tablosu — recall@IoU≥0.5

*(açık çevrim üst sınırı)*

### A5 baseline · uav0000117_02622_v / 23

| seviye | tam kare | sabit R320 | **adaptif** | o_merkez | o_boyut | o_tam |
|---|---|---|---|---|---|---|
| 40×15 | 0.983 | 0.683 | **1.000** | 1.000 | 1.000 | 1.000 |
| 30×12 | 0.667 | 0.983 | **0.983** | 0.983 | 1.000 | 1.000 |
| 20×10 | 0.117 | 0.300 | **0.417** | *0.833* | *0.300* | *1.000* |
| 15×7 | 0.000 | 0.367 | **0.333** | *0.467* | *0.367* | *0.917* |
| 10×5 | 0.000 | 0.233 | **0.217** | *0.217* | *0.250* | *0.850* |
| 8×5 | 0.000 | 0.100 | **0.183** | *0.133* | *0.167* | *0.467* |
| 5×5 | 0.000 | 0.000 | **0.017** | *0.050* | *0.017* | *0.050* |

### A5 baseline · uav0000137_00458_v / 12

| seviye | tam kare | sabit R320 | **adaptif** | o_merkez | o_boyut | o_tam |
|---|---|---|---|---|---|---|
| 40×15 | 1.000 | 0.800 | **1.000** | 1.000 | 1.000 | 1.000 |
| 30×12 | 1.000 | 0.583 | **1.000** | 1.000 | 1.000 | 1.000 |
| 20×10 | 0.600 | 0.950 | **0.950** | *0.983* | *0.950* | *0.983* |
| 15×7 | 0.400 | 1.000 | **1.000** | *1.000* | *1.000* | *1.000* |
| 10×5 | 0.000 | 0.750 | **1.000** | *1.000* | *1.000* | *1.000* |
| 8×5 | 0.000 | 0.050 | **1.000** | *1.000* | *1.000* | *1.000* |
| 5×5 | 0.000 | 0.000 | **0.950** | *0.883* | *0.950* | *0.883* |

### A6 UAVDT→VisDrone · 137/12 ve 305/5

| seviye | 137/12 tam | 137/12 **adaptif** | 305/5 tam | 305/5 **adaptif** |
|---|---|---|---|---|
| 40×15 | 1.000 | **1.000** | 1.000 | **1.000** |
| 30×12 | 1.000 | **1.000** | 0.867 | **1.000** |
| 20×10 | 0.417 | **1.000** | 0.050 | **1.000** |
| 15×7 | 0.033 | **1.000** | 0.000 | **1.000** |
| 10×5 | 0.000 | **1.000** | 0.000 | **0.550** |
| 8×5 | 0.000 | **1.000** | 0.000 | **0.250** |
| 5×5 | 0.000 | **0.483** | 0.000 | **0.000** |

> **305/5 · A5 baseline dışarıda bırakıldı.** O kolda tüm seviyeler 0.000 veriyor —
> ama bu A8'in bulgusu değil: **A7 de aynı dizide A5 için baştan sona 0.000 ölçmüştü**
> (A7 JSON'u, 305/5, tam/2×/4× hepsi 0.0). Model-sahne uyumsuzluğu, ROI ile ilgisi yok.
> 305/5 yalnızca A6 kolundan okunur.

**Okunan sonuç: adaptif ROI, takipçi merkezi tuttuğunda tam kareyi ezici biçimde geçiyor.**
137/12'de tam karenin 0.000 verdiği **10×5 ve 8×5'te adaptif 1.000**. 305/5·A6'da tam karenin
0.000 verdiği 15×7'de adaptif 1.000.

---

## 5. Merkezleme hatası — asıl bağlayıcı kısıt

`adaptif_kf` kolunda, takipçi merkezinin GT merkezine uzaklığı (sensör px):

| dizi | 40×15 | 30×12 | 20×10 | 15×7 | 10×5 | 8×5 | 5×5 |
|---|---|---|---|---|---|---|---|
| **117/23** p50 | 6.8 | 9.7 | **206.8** | **133.0** | **140.6** | **109.0** | **116.2** |
| **117/23 p95** | 13.8 | 20.7 | **380.4** | **434.6** | **607.1** | **150.6** | **188.9** |
| **137/12** p50 | 10.5 | 9.7 | 1.1 | 1.1 | 0.8 | 0.7 | 0.7 |
| **137/12 p95** | 25.6 | 26.1 | **5.1** | **3.9** | **2.6** | **2.1** | **1.3** |
| **305/5** p95 | 15.5 | 8.8 | 14.0 | 8.6 | 3.6 | 2.3 | 1.4 |

**İki dizi taban tabana zıt.** 137/12 ve 305/5'te takipçi p95'te bile 1–26 px içinde kalıyor.
117/23'te ≤20 px seviyelerinin tamamında **yüzlerce piksel** — takipçi tamamen kopmuş.

> **Ortalama kullanılsaydı bu görülmezdi.** A7 §4 yalnızca ortalama raporluyordu
> (117/23 için 39.9 px). p95 gerçek büyüklüğü 380–607 px olarak gösteriyor: felaket
> ortalamanın içinde saklanıyordu.

### 117/23 çöküşü ROI'nin özelliği değil

A3.9 Deney 4L: **"117/23 bir uçurumun 1 px yanındadır"** — ilk kilit kutusu (−1,+1) px
oynatılınca IoU 0.701 → 0.111. Buradaki kopuş o bilinen havza kararsızlığının aynısıdır;
adaptif ROI onu ne yaratıyor ne düzeltiyor. **A8, 117/23'ü ROI'nin değil takipçinin
sınırı olarak raporlar.**

---

## 6. Boyut tahmini hatası ve ağ px'ine taşınması

`bho = boyut_tahmini / GT_boyut`; `R ∝ bho` olduğu için hata ağdaki px'e **tersine** yansır.

| dizi · seviye | bho p50 | bho p95 | gerçek ağ px p50 | bant içi oran |
|---|---|---|---|---|
| 117/23 · 20×10 | 1.891 | 2.002 | 40.0 | 0.20 |
| 117/23 · 15×7 | **2.709** | 2.826 | 30.0 | 0.13 |
| 117/23 · 10×5 | **3.990** | **5.041** | 20.0 | 0.13 |
| 117/23 · 8×5 | **3.608** | 4.804 | 16.0 | 0.27 |
| 137/12 · 10×5 | 0.981 | 1.020 | 96.0 | 0.30 |
| 137/12 · 8×5 | 0.986 | 1.017 | 76.0 | 1.00 |
| 305/5 · 15×7 | 1.368 | 2.416 | 60.0 | 0.60 |

117/23'te takipçi hedefi **4–5 kat büyük** sanıyor → R gereğinden büyük seçiliyor →
hedef ağda 16–20 px'e düşüyor, yani A7 eğrisinin ölü bölgesine. **§6.2'de öngörülen
mekanizma birebir gerçekleşti.** 137/12'de bho ≈ 1.00 ve bant korunuyor.

**Yatak D bunu en temiz gösteren yer** (117/23, daralan 40→5):

| t | GT L (sensör) | tahmin L | bho | merkez hata | R | gerçek ağ px | kapsandı |
|---|---|---|---|---|---|---|---|
| 0 | 80.0 | 80.0 | 1.00 | 0.0 | 640 | 80.0 | ✓ |
| 12 | 52.0 | 128.6 | 2.47 | 41.7 | 640 | 52.0 | ✓ |
| 24 | 34.0 | 111.0 | 3.26 | 235.6 | 640 | 34.0 | ✓ |
| 30 | 28.0 | 111.0 | 3.97 | 455.3 | 640 | 28.0 | ✗ |
| 54 | 12.0 | 106.3 | **8.85** | 650.7 | 640 | 12.0 | ✗ |

**Takipçinin boyut tahmini hedefle birlikte küçülmüyor** — 106–131 px'e çakılı kalıyor
(gerçek 80 → 12 px'e inerken). Sonuç: R hiç değişmiyor (60 karenin 60'ında 640), hedef
ağda 80 → 12 px'e düşüyor ve banda **bir daha girmiyor**. Bu, `_boyut_tazele`
(`takip/izleyici.py:551`) arızasının ROI seçimine doğrudan yansımasıdır.

Karşılaştırma — **137/12 daralan, kural gerçekten uyarlanıyor**: R 640 → 320'ye adım
atıyor (60 karede `{640: 32, 320: 24, 160: 4}`), recall 0.717 vs tam kare 0.367.

---

## 7. Fizibilite testi — kapsama mı, büyütme mi?

```
R_büyütme = L_s · 640 / 75
R_kapsama = max( 2·(mh_p95 + L_s/2) ,  (32/9)·(mh_p95 + L_s/2) )     [16:9 → dikey dar]
uygulanabilir ⟺ R_kapsama ≤ R_büyütme
```

| dizi | seviye | mh p95 | R_kapsama | R_büyütme | sonuç | pay |
|---|---|---|---|---|---|---|
| 117/23 | 40×15 | 13.8 | 189.9 | 675.0 | UYGULANABİLİR | +485 |
| 117/23 | 30×12 | 20.7 | 180.2 | 511.1 | UYGULANABİLİR | +331 |
| 117/23 | 20×10 | 380.4 | 1423.3 | 340.5 | **DEĞİL** | **−1083** |
| 117/23 | 15×7 | 434.6 | 1598.4 | 256.0 | **DEĞİL** | **−1342** |
| 117/23 | 10×5 | 607.1 | 2194.2 | 170.7 | **DEĞİL** | **−2024** |
| 117/23 | 8×5 | 150.6 | 563.9 | 136.5 | **DEĞİL** | −427 |
| 117/23 | 5×5 | 188.9 | 689.5 | 85.3 | **DEĞİL** | −604 |
| 137/12 | 20×10 | 5.1 | 100.7 | 395.9 | UYGULANABİLİR | +295 |
| 137/12 | 15×7 | 3.9 | 75.6 | 296.1 | UYGULANABİLİR | +221 |
| 137/12 | 10×5 | 2.6 | 50.4 | 198.0 | UYGULANABİLİR | +148 |
| 137/12 | 8×5 | 2.1 | 40.5 | 157.9 | UYGULANABİLİR | +117 |
| 137/12 | 5×5 | 1.3 | 25.1 | 98.1 | UYGULANABİLİR | +73 |
| 305/5 | 8×5 | 2.3 | 38.8 | 145.9 | UYGULANABİLİR | +107 |
| 305/5 | 5×5 | 1.4 | 23.8 | 91.3 | UYGULANABİLİR | +68 |

**Gerilim gerçek ama tek yönlü:** takipçi tuttuğunda pay çok geniş (+68…+536 px), yani
kapsama ile büyütme hiç çatışmıyor. Takipçi koptuğunda ise fizibilite **her seviyede**
ihlal ediliyor. Yani "ROI'yi ne kadar küçültebilirim" sorusu değil, **"takipçi merkezi
tutuyor mu"** sorusu belirleyici.

### Hata kanalı ayrıştırması (o_merkez vs o_boyut)

117/23 · 20×10 · A6: adaptif **0.400** → `oracle_merkez` **1.000** · `oracle_boyut` **0.283**
117/23 · 20×10 · A5: adaptif **0.417** → `oracle_merkez` **0.833** · `oracle_boyut` **0.300**

**Yalnızca merkezi düzeltmek her şeyi kurtarıyor; yalnızca boyutu düzeltmek hiçbir şey
kurtarmıyor — hatta kötüleştiriyor.** Sebebi mekanik: GT boyutu verilince kural *doğru*
(daha küçük) R'yi seçiyor, ama merkez bozuk olduğu için daha dar ROI hedefi daha çok
kaçırıyor. **Baskın arıza kanalı MERKEZ'dir, boyut ikincildir.**

---

## 8. Kenar payı ve kapsama

`kenar_payı = (ROI yarı-boyut − |merkez sapması| − hedef/2) / ROI yarı-boyut`, kadraja
kenetlenmiş **gerçek** dikdörtgenden; x ve y ayrı (16:9 → dikey daha dar).

| dizi · seviye | kapsama | pay_x p05 | pay_y p05 |
|---|---|---|---|
| 117/23 · 20×10 | 0.43 | 0.69 | **−0.17** |
| 117/23 · 15×7 | 0.77 | **−0.12** | **−0.12** |
| 117/23 · 10×5 | 0.55 | 0.03 | **−0.08** |
| 117/23 · 5×5 | **0.23** | **−3.56** | **−4.01** |
| 137/12 · 8×5 | 1.00 | 0.85 | 0.78 |
| 137/12 · 5×5 | 1.00 | 0.82 | 0.71 |
| 305/5 · 5×5 | 1.00 | 0.93 | 0.67 |

**İkili kaçırma bunu göstermezdi.** 117/23 · 5×5'te pay −3.56: hedef ROI'nin dışında,
ROI genişliğinin 3.5 katı uzakta. Bu bir "sınırda kaçırma" değil, tamamen başka bir yere
bakmak. Buna karşılık 137/12'de pay p05 = 0.71–0.85, yani **emniyet katsayısı 3–6 kat**;
ROI çok daha küçük seçilebilirdi.

**Dikey her zaman daha dar** (pay_y < pay_x), 16:9 ROI'nin doğrudan sonucu.

---

## 9. Coast — takipçi kopuşu ROI kapsamasını nerede bozuyor

Yatak D (117/23, 40→5 px, 60 kare): **ilk bant-dışı kare t=9**, **ilk kapsama hatası t=27**.

t=24'te GT 34 px sensör = **17 px ağda**, merkez hatası 235 px.
t=30'da GT 28 px sensör = **14 px ağda**, merkez hatası 455 px, kapsama **çöküyor**.

> **Kapsama tam olarak A7 §4'ün ölçtüğü 14–20 px süreklilik tabanında bozuluyor.**
> Bu bağımsız bir doğrulamadır: ROI'nin sınırı ROI'nin kendi sınırı değil, takipçinin
> sınırıdır.

137/12 ve 305/5'te 60 karenin hiçbirinde kapsama hatası yok (`ilk_kapsama_hatasi = None`).

**Not:** buradaki takipçi kendi DCF ölçümüyle çalışır, yalnızca dedektörden beslenmez.
**Saf KF-coast (hiç ölçüm yok) ölçülmedi**, çünkü operasyonel tasarım DCF'yi koruyor.

---

## 10. 60–90 bandı fazla dar — ölçümle düzeltme

A7'nin 60–90 bandı 4 noktalı kaba bir ızgaradan çıkarılmıştı. A8 verisi bandı **doğrudan
çürütüyor**:

| dizi · seviye | gerçek ağ px p50 | bant içi oran | **recall** |
|---|---|---|---|
| 137/12 · 40×15 | 96.0 | 0.32 | **1.000** |
| 137/12 · 20×10 | 96.0 | 0.32 | **1.000** |
| 137/12 · 10×5 | 96.0 | 0.30 | **1.000** |
| 305/5 · 5×5 (A6) | 88.0 | 0.88 | 0.000 |

Hedef ağda **96–100 px** iken recall **1.000**. Yani 90 üst sınırı gerçek değil.
A7 eğrisinde bozulma ≥170 px'te başlıyordu (245 px'te 0.51), 96 px'te değil.

> **Düzeltme: operasyonel bant ≈ 55–110 px, hedef 75.** Üst sınırı 90'da tutmak kuralı
> gereksiz yere R=320'den R=160'a itiyor ve kapsama payını boşuna harcıyor.

---

## 11. Kaçırma oranı ve gecikme

ROI çıkarımı tam kareden **pahalı değil** — A7 §7 doğrulandı: adaptif kol **27.8–30.2 ms**,
tam kare 27.5–34.6 ms (aynı ağ girdisi boyutu).

Geri düşme politikası (**ROI ışkalarsa tam kare yeniden koşulur**):
`beklenen = 28.5 + kaçırma_oranı × 28.5 ms`

| dizi | seviye | kaçırma | beklenen gecikme |
|---|---|---|---|
| 137/12 | 15×7 | 0.000 | **28.6 ms** |
| 137/12 | 10×5 | 0.000 | **28.3 ms** |
| 137/12 | 8×5 | 0.000 | **28.0 ms** |
| 137/12 | 5×5 | 0.517 | 42.7 ms |
| 117/23 | 20×10 | 0.583 | 44.8 ms |
| 117/23 | 10×5 | 0.783 | 56.5 ms |
| 117/23 | 5×5 | 0.983 | 57.8 ms |

**Takipçi tuttuğunda adaptif ROI bedava** (geri düşme hiç tetiklenmiyor). Koptuğunda
gecikme iki katına çıkıyor — yani **takipçi kopuşu hem doğruluğu hem bütçeyi vuruyor**.

> **Pi Zero 2 W'de ölçüm YOK.** Masaüstü CPU'daki 28 ms zaten ~36 ms bütçesinin %78'i;
> geri düşme tetiklendiğinde 45–58 ms ile **bütçe aşılıyor**. IMX500 hiç denenmedi.
> Buradaki hiçbir sayı Pi'ye ekstrapole edilmemelidir.

### Yan kazanç: sahte pozitifler tamamen kayboluyor

60 kare, 137/12, `fp` (GT ile IoU=0 olan tespit sayısı):

| model | tam kare | sabit R320 | **adaptif** |
|---|---|---|---|
| A5 · 8×5 | **763** | 9 | **0** |
| A5 · 5×5 | **764** | 10 | **0** |
| A6 · 8×5 | **573** | 8 | **0** |
| A6 · 5×5 | **573** | 13 | **0** |

ROI kalabalık arkaplanı çerçeve dışında bıraktığı için sahte pozitif **~570–760'tan
sıfıra** düşüyor. A7 §6'nın ölçtüğü (320 → 0–4) etkinin daha da güçlü hâli.

---

## 12. 5×5'teki sıfırdan farklı sonuç — doğrulama ve sınırları

A5 baseline · 137/12 · 5×5'te adaptif kol **recall 0.950** verdi. Proje tarihinde 5×5'te
ilk kez sıfırdan farklı bir sonuç olduğu için ayrıca denetlendi:

| ölçüt | değer | yorum |
|---|---|---|
| ortalama IoU | **0.913** | eşiğin çok üstünde — sınırda eşleşme değil |
| ortalama güven | 0.455 | conf=0.25 eşiğinin belirgin üstünde |
| FP / FN | **0 / 3** (60 karede) | arkaplandan gelen kutu yok |
| ilk 8 karenin IoU'su | 0.93, 0.95, 0.93, 0.91, 0.91, 0.93, 0.87, 0.86 | kararlı, tesadüfi değil |
| kapsama | 1.00 | hedef her karede ROI içinde |

**Arkaplan artefaktı değildir.** A5.2 ve A6 raporlarındaki *"10×5 ve altındaki IoU değerleri
anlamlı değildir, yalnızca arkaplandaki başka bir aracın kesişmesini ölçer"* uyarısı burada
geçerli değil: orada recall@0.5 = 0 ve IoU ≤ 0.054 idi; burada IoU 0.91 ve FP = 0.

**Ama şu sınırlar geçerlidir ve sonucu genellemeyi yasaklar:**

1. **Tek dizide.** 117/23'te 0.017, 305/5'te 0.000. Kural iki birincil dizide birden 0.80
   ister — **geçilmedi**.
2. **Temiz küçültme yatağı.** Hedef yaması gerçek 146 px'lik yamadan `INTER_AREA` ile
   11.5 px'e indirilip ROI tarafından `INTER_LINEAR` ile 80 px'e geri büyütülüyor. Gerçek
   bir sensörde 11.5 px'lik bir araç **sensör gürültüsü, hareket bulanıklığı, titreşim ve
   sıkıştırma artefaktı** taşır; bu yatak bunların hiçbirini modellemiyor
   (bkz. `KALICI_KISITLAR.md` — hepsi "henüz ölçülmedi" listesinde).
3. **R=80 basamağı A7'de ölçülmedi**, A8'de ilk kez kullanıldı.

> **Hüküm: 5×5 çözülmüş DEĞİLDİR.** Ama "hiçbir koşulda hiçbir şey yok" da artık doğru
> değil: yeterli büyütme verildiğinde tek bir dizide güçlü ve tutarlı bir sinyal var.
> Bunun gerçek görüntüde de durup durmadığı **ölçülmemiştir**.

---

## 13. Adaptif seçim kuralı — önerilen tasarım

Ayrık merdivenden seçer (A7 yalnızca 3 R ölçtü; sürekli R ölçülmemiş noktalara
extrapolasyon olurdu).

```
GİRDİ : L_est (takipçi boyut tahmini, sensör px)
        u     (konum belirsizliği kestirimi, sensör px — KF kovaryansı)
        durum, PSR

1. GÜVEN KAPISI
   durum != KILITLI  veya  PSR < eşik  →  L_est'e GÜVENME:
        son güvenilir R'yi koru, güvensizlik sürdükçe bir basamak BÜYÜT.

2. BÜYÜTME ADAYI
   R_büyütme = L_est · 640 / 75

3. KAPSAMA TABANI          ← A8'in eklediği zorunlu kısıt
   R_kapsama = (32/9) · (k·u + L_est/2)          k ≈ 2 (p95 karşılığı)

4. SEÇİM
   R_ideal = max(R_büyütme, R_kapsama)      ← KAPSAMA BÜYÜTMEYİ EZER
   R = merdivendeki, ag_px = L_est·640/R değerini [55,110] bandına sokan
       ve R ≥ R_kapsama olan EN KÜÇÜK basamak; yoksa en büyük basamak.

MERDİVEN : {640, 320, 160, 80}      (80 A7'de ölçülmedi)
```

**3. adım neden zorunlu:** ölçülmüş karşı örnek — 117/23 · 5×5 · A6'da kural R=80 seçti
(bho≈1.07, "hedef 10 px" diyor), ama merkez hatası p95 = 189 px. Kapsama 0.23'e düştü,
adaptif **0.017** verdi; oysa aynı yerde sabit R=320 **0.383** verdi. **Kural büyütmeyi
kapsamaya tercih ettiği için kaybetti.** Kapsama tabanı olmadan adaptivite sabit
basamaktan daha kötüdür.

---

## 14. Operasyonel risk

1. **Kapalı çevrim.** Buradaki her sayı açık çevrimdir. Gerçek sistemde dedektör → takipçi →
   boyut → R → dedektör çevrimi kapanacak. Beş kez tekrarlanan ders geçerli: türetilmiş
   büyüklük bağımsız ölçümün yerine geçerse hata birikir. **R seçimi, `_boyut_tazele`
   çıktısına bağlanırsa aynı tuzağa düşer.**
2. **Boyut tahmini bağımsız değil.** P0.1 (bağımsız mutlak boyut ölçümü) hâlâ boş; adaptif
   ROI onun üstüne kuruluyor. 117/23 daralan yatağında bho 1.00 → 8.85'e tırmandı.
3. **Merkez tek arıza noktası.** Takipçi 14–20 px'te kopuyor; ROI onunla birlikte gidiyor.
   Yeniden edinme mekanizması **yok** (A8 kapsamı dışı).
4. **Gecikme bütçesi.** Geri düşme tetiklendiğinde 45–58 ms; Pi Zero 2 W bütçesi ~36 ms.
   Pi'de hiç ölçüm yok.
5. **R=80 basamağı doğrulanmamış.** A7'de ölçülmedi; 137/12'de 0.483 verdi ama 117/23'te
   0.017, 305/5'te 0.000.
6. **Dikey pay her zaman daha dar** (16:9). Dikey kaçış x'ten önce gelir.

---

## 15. Hüküm

- **Adaptif ROI GERÇEK ve BÜYÜK bir kazanç sağlıyor — takipçi merkezi tuttuğunda.**
  137/12'de tam karenin 0.000 verdiği **10×5 ve 8×5 seviyelerinde adaptif 1.000**
  (A5 ve A6, iki modelde de). 305/5·A6'da 15×7'de 0.000 → 1.000.
- **Bağlayıcı kısıt büyütme değil, MERKEZLEME.** `oracle_merkez` tek başına 117/23·20×10'u
  0.400 → 1.000'e çıkarıyor; `oracle_boyut` 0.283'te bırakıyor. Boyut ikincil kanaldır.
- **Fizibilite testi ikiye ayırıyor:** takipçi tuttuğunda kapsama–büyütme gerilimi yok
  (pay +68…+536 px); koptuğunda her seviyede ihlal (−427…−2024 px).
- **Boyut tahmini hatası ölçüldü ve öngörülen mekanizmayı doğruladı:** 117/23'te bho p50
  4.0'a, daralan yatakta 8.85'e çıkıyor; R sabitleniyor, hedef ağda 80 → 12 px'e düşüyor
  ve banda dönmüyor.
- **ROI kapsaması tam olarak 14–20 px'te bozuluyor** — A7 §4'ün süreklilik tabanının
  bağımsız doğrulaması.
- **60–90 bandı fazla dar; ölçüm 96–100 px'te recall 1.000 gösteriyor.**
  Operasyonel bant ≈ **55–110 px**.
- **Kurala KAPSAMA TABANI eklenmeli**, yoksa adaptivite sabit basamaktan kötüdür
  (117/23·5×5: adaptif 0.017 vs sabit320 0.383).
- **5×5 çözülmedi — ama tablo değişti.** Yeni R=80 basamağı 137/12'de ilk kez güçlü bir
  sonuç verdi: **A5 baseline 0.950** (IoU 0.913, FP 0), A6 0.483 — tam kare her ikisinde
  0.000. Buna karşılık 117/23'te 0.017, 305/5'te 0.000. Kural iki birincil dizide birden
  0.80 istiyor — **geçilmedi, 5×5 başarısı YOKTUR** (ayrıntı ve yatak sınırları §12).
- **Sahte pozitif tamamen kayboluyor:** 137/12'de tam kare 573–764, adaptif **0**.
- **Merdiven boşlukları açık:** L = 11.25–15 ve L = 22.5–30.
- **Pi Zero 2 W / IMX500'de ölçüm yok.**

**Bu bir TEŞHİStir, hüküm turu değildir. A7 kabul kriteri değiştirilmedi.**

### Sonraki tur için ölçüme dayanan sonuçlar

1. **Dedektörü daha da iyileştirmek 20 px altında tek başına işe yaramaz** — A7 bunu
   söylemişti, A8 sayısallaştırdı: kayıp merkezleme kanalından geliyor.
2. **Sıradaki iş takipçi tarafıdır:** ya merkezi bağımsız bir ölçümle çapalamak
   (P0.1 boyut ölçümüyle birlikte), ya da bir yeniden-edinme mekanizması eklemek.
3. **Kapalı çevrim mutlaka ayrıca ölçülmeli** — buradaki hiçbir sayı kapalı çevrimde
   geçerli sayılamaz.
