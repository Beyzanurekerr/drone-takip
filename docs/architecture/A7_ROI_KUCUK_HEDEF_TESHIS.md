# A7 — ROI tespit teşhisi: edinme (acquisition) vs süreklilik (persistence)

**Tarih:** 2026-09-01 · **Kod:** `gazebo/tani_a7_roi.py` (salt okunur gözlemci)
**Veri:** `cikti/a7_roi_teshis.json`
**Bu turda:** eğitim yok · model/ağırlık değişmedi · augmentasyon, imgsz, P2 yok · commit/push yok.
A5.2 protokol dosyası `gazebo/bench_a52_kucuk_hedef.py` md5 **`45623cc5…`** — **değişmedi**,
modül olarak içe aktarılıp fonksiyonları yeniden kullanıldı. `takip/` md5 6/6 aynı.

---

## 1. İlk deneme reddedildi — ve nedeni bu turun en önemli bulgusu

ROI'yi doğrudan A5.2'nin 640×360 tuvali üzerinde kırptım. Sonuç: 117/23 · 10×5
seviyesinde **ROI oracle bile recall 0.000**.

Sebep açık: A5.2 tuvali zaten 640×360'tır ve oradaki 10 px hedef, 146 px'lik gerçek
yamanın küçültülmüş halidir — **bilgi orada yok**. 4× büyütmek gerçek piksel eklemez,
yalnızca bulanık bir leke üretir.

> Bu doğrudan SAHI'yi de bağlar: **dilimleme ancak native çözünürlükteki kareyi
> dilimlerse kazandırır.** Küçültülmüş bir kareyi dilimlemek hiçbir şey vermez.

**Düzeltilmiş test yatağı:** tuval **sensör çözünürlüğünde** (1280×720, gerçek
VisDrone karesinden kırpılmış gerçek arkaplan). Tam kare ağa verilince letterbox
0.5 ile iner, yani "seviye L" yine **hedefin ağ girdisindeki px boyu** — A5.2 ile
birebir aynı tanım. Hedef yaması sensörde 2L px, 146 px'lik gerçek yamadan
**yalnızca küçültülerek** üretilir; uydurma detay yok.

ROI kolları sensörden kırpıp 640×360'a getirir: R=640 → **2×**, R=320 → **4×**,
R=160 → **8×**. Değişen tek şey dedektörün pikselleri nereden aldığı.

## 2. Büyütme eğrisi — büyütmenin bir OPTİMUMU var

A5 baseline, iki birincil dizinin ortalaması. Her hücre: `recall@0.5 @ hedefin ağdaki px boyu`.

| seviye | tam kare | ROI 2× | ROI 4× | ROI 8× |
|---|---|---|---|---|
| 57 | **0.98** @61px | **0.99** @123px | 0.51 @245px | 0.05 @490px |
| 40 | **0.99** @43px | **1.00** @86px | 0.78 @172px | 0.23 @344px |
| 30 | 0.83 @32px | **1.00** @65px | 0.78 @130px | 0.17 @259px |
| 20 | 0.36 @22px | 0.81 @43px | **0.93** @86px | 0.42 @173px |
| 15 | 0.20 @16px | 0.09 @32px | 0.50 @65px | 0.35 @130px |
| 10 | 0.00 @11px | 0.00 @22px | 0.00 @43px | 0.00 @86px |
| 8 | 0.00 @9px | 0.00 @17px | 0.00 @34px | 0.00 @69px |
| 5 | 0.00 @5px | 0.00 @11px | 0.00 @22px | 0.00 @43px |

**Okunan kural:** dedektör, hedef ağ girdisinde kabaca **40–130 px**'e düştüğünde
çalışıyor; en iyi bant **~60–90 px**. Bunun altında (≤22 px) bulamıyor, üstünde
(≥170 px) aşırı büyütmenin bulanıklığı yüzünden yine kaybediyor.

> **Sonuç: sabit bir büyütme (dolayısıyla sabit bir SAHI tile boyutu) tüm bandı
> kapatamaz.** Her büyütme yalnızca bir boyut bandında doğru çalışıyor.
> Büyütme, kestirilen hedef boyutuna göre **uyarlanabilir** olmalı.

## 3. A) EDİNME — recall@IoU≥0.5 ≥ 0.80 (her iki birincil dizide)

| model / kol | nitelenen seviyeler | **en küçük** |
|---|---|---|
| A5 · tam kare | 57, 40 | **40** |
| A5 · ROI 2× zincir | 57, 40, 30 | **30** |
| A5 · ROI 4× zincir | 20 | **20** |
| A6 · tam kare | 57, 40, 30 | **30** |
| A6 · ROI 2× zincir | 40, 30, 20 | **20** |
| *(oracle 8× — üst sınır, başarı sayılmaz)* | *…10* | *10 (recall 0.93)* |

**ROI, edinme tabanını 40 px'ten 20 px'e indirdi** — doğru büyütme seçildiğinde.
Bu, A5/A6'nın tam-kare 57 px tabanına göre gerçek ve büyük bir kazanç.

**Zincirleme kolun 15 px'in altında çökmesinin sebebi soğuk başlangıçtır:**
0. karede tam-kare tespiti başarısız olunca zincir hiç başlamıyor. Oracle kolu
aynı seviyede 0.93 veriyor — yani **eksik olan çözünürlük değil, konum bilgisi.**
Bu boşluğu kapatmanın iki yolu var: SAHI (konum bilmeden tüm kareyi tarar) veya
takipçiden gelen önceki konum.

## 4. B) SÜREKLİLİK — mevcut takipçinin gerçek sınırı

Hedef **57 px'ten 5 px'e küçülürken**, takipçi 0. karede (hedef büyükken) kilitli.
Bu bir **tespit** ölçümü değildir.

| dizi | kaybedilen boyut | kare | ort IoU | kilit oranı | PSR | merkez hata |
|---|---|---|---|---|---|---|
| 117/23 | **20 px** | 25 | 0.252 | 0.53 | 15.7 | 39.9 px |
| 137/12 | **18 px** | 33 | 0.358 | 0.66 | 30.8 | 6.9 px |
| 305/5 | **14 px** | 36 | 0.330 | 0.59 | 50.4 | 2.6 px |

> **Mevcut takipçinin gerçek süreklilik sınırı ~14–20 px.**

## 5. Bunun sistem düzeyindeki anlamı

| | önce | A7 sonrası |
|---|---|---|
| dedektör edinme tabanı | 40 px (tam kare) | **20 px** (ROI, doğru büyütme) |
| takipçi süreklilik tabanı | bilinmiyordu | **14–20 px** |

İki taban artık **aynı yerde**. Yani ROI dedektörü takipçiyle aynı seviyeye çekti;
buradan aşağısı için dedektörü daha da iyileştirmek **tek başına işe yaramaz** —
takipçi de 14–20 px'te bırakıyor. A5.2'de "zincir başlatmada kırılıyor" demiştik;
artık **zincir iki uçta birden, aynı boyutta kırılıyor.**

## 6. Yan kazanç: sahte pozitifler çöküyor

117/23, 60 kare, A5 baseline:

| seviye | tam kare FP | ROI 2× | ROI 4× |
|---|---|---|---|
| 57 | 321 | 128 | **3** |
| 40 | 324 | 106 | **4** |
| 30 | 317 | 84 | **0** |
| 20 | 312 | 82 | **4** |

ROI, kalabalık arkaplanı çerçeve dışında bıraktığı için sahte pozitifi
**~320'den 0–4'e** düşürüyor. A6 fine-tuning'in sağladığı 3–6 kat azalmanın
çok ötesinde, temiz bir kazanç.

## 7. Gecikme / FPS

Tüm kollarda tek çıkarım maliyeti aynı: **ort 34.8 ms → 28.8 FPS** (masaüstü CPU,
640×360 ağ girdisi). ROI çıkarımı tam kareden **daha pahalı değil** — aynı ağ
girdisi boyutu. Maliyet ancak kare başına birden fazla dilim çalıştırılırsa artar
(SAHI durumu). **Pi Zero 2 W / IMX500'de hâlâ ölçüm yok.**

## 8. A6 modeli ROI altında farklı davranıyor

Tam-kare benchmark'ında A6'nın katkısı sınırlı görünüyordu. ROI altında tablo değişiyor:
117/23 · 5 px seviyesinde A5 oracle 8× = 0.117 iken **A6 oracle 8× = 0.800**;
A6 zincirleme kol 5 px'te 0.271–0.356 verirken A5 tam 0.000.
**A6'nın küçük-hedef kazancı ancak yeterli piksel verildiğinde ortaya çıkıyor.**
Buna karşılık A6 büyük hedefte ROI altında kötü (57 px'te 0.067) — daha önce
ölçülen "büyük nesne yeteneği kaybı" burada da görünüyor.

## 9. Sorulan seviyeler — dürüst sonuç

| seviye | tam kare | en iyi operasyonel ROI | oracle tavanı |
|---|---|---|---|
| 15×7 | 0.20 | 0.50 (4×) · takipçi 0.68 | 0.96 |
| **10×5** | **0.00** | **0.49** (takipçi 4×) | 0.93 (8×) |
| **8×5** | **0.00** | **0.08** (takipçi 4×) | 0.73 (8×) |
| **5×5** | **0.00** | **0.00** | 0.33 (8×) |

**5×5'te hiçbir operasyonel kolda başarı yok.** 10×5'te takipçi merkezli ROI
0.49'a çıkıyor (137/12'de 0.75, 117/23'te 0.23) — anlamlı ama 0.80 eşiğinin altında.

## 10. Hüküm

- **ROI tespiti küçük hedef recall'ünü anlamlı biçimde ARTIRIYOR.** 40×15 → 20×10
  bandında etki çok net: 20 px'te tam kare 0.36 → ROI 4× **0.93**.
- **Edinme tabanı 40 px → 20 px'e indi** (A6 modeliyle 2× büyütmede de 20 px).
- **Büyütmenin optimumu var** (~60–90 px ağda); sabit büyütme/tile tüm bandı kapatmaz,
  **uyarlanabilir olmalı**.
- **Takipçinin süreklilik sınırı 14–20 px** ölçüldü; artık dedektörle aynı seviyede.
- **5×5 için başarı yok**, varsayılmadı.
- Yan kazanç: sahte pozitif ~320 → 0–4.
- A6 kabul kriteri **değiştirilmedi**; bu bir teşhistir, hüküm turu değildir.

**Sonraki adım için ölçüme dayanan iki sonuç:** (a) SAHI native çözünürlükte
dilimlenmeli ve tile boyutu hedefi ağda ~60–90 px'e getirecek şekilde seçilmeli;
(b) 20 px'in altına inmek isteniyorsa **takipçi tarafı da** ele alınmalı, tek başına
dedektör yetmez.
