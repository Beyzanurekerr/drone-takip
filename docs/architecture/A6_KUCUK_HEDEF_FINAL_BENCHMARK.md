# A6 — Küçük hedef final benchmark'ı: A5 vs A6 kontrol vs A6 UAVDT→VisDrone

**Tarih:** 2026-09-01 · **Veri:** `cikti/a6_kucuk_hedef_final.json`
**Bu turda:** eğitim yok (kontrol kolu hariç, aşağıda), model/hiperparametre değişikliği yok,
commit/push yok.

## 0. Protokol — değiştirilmedi

`gazebo/bench_a52_kucuk_hedef.py` md5 **`45623cc5efa1c73d53d9f1a7865fb4a1`**, koşumdan
önce ve sonra **aynı**. Dosya hiç düzenlenmedi; modül olarak içe aktarılıp yalnızca iki
modül değişkeni geçersiz kılındı: `AGIRLIK` (ölçülen model) ve `SINIFLAR` (o modelin
kendi araç sınıf kimlikleri). Geri kalan her şey A5.2'nin aynısı: 640×360 tuval,
letterbox ölçeği **1.000**, `conf=0.25`, `imgsz=640`, kompozit yöntemi, arkaplan ölçütü,
8 seviye + native kontrol, 117/23 ve 137/12, **cihaz cpu**, torch thread 8.

**Sınıf eşlemesi — A5'in COCO haritası A6 modeline taşınmadı.**
A5 baseline COCO id `[2 car, 3 motorcycle, 5 bus, 7 truck]`; A6 modelleri VisDrone
4-sınıf `[0 car, 1 van, 2 truck, 3 bus]` (hepsi araç). COCO 5 = bus ama VisDrone 5 = van
olduğu için aynı listeyi taşımak yanlış sınıfı filtrelerdi.

**A5 baseline yeniden ölçüldü** (üç model de aynı ortamda olsun diye). Sonuç:
depodaki `cikti/a5_kucuk_hedef.json` ile **recall değerleri birebir aynı**. Yani
CUDA'lı torch kurulumu A5 baseline'ını etkilememiş ve protokol tekrar üretiyor.
Depodaki A5 dosyası **değiştirilmedi**.

**Kontrol kolu bu turda eğitildi** — plan onaylanmıştı ama koşulmamıştı; UAVDT'nin
katkısını ayrıştırmanın başka yolu yok. Aşama B ile birebir aynı konfigürasyon,
tek fark başlangıç ağırlığı (`weights/yolov8n.pt`). 105 epoch, erken durdurma,
en iyi epoch 75.

## 1. Modeller

| | A5 baseline | A6 kontrol | A6 UAVDT→VisDrone |
|---|---|---|---|
| ağırlık | `weights/yolov8n.pt` | `runs/a6/kontrol/weights/best.pt` | `runs/a6/asamaB/weights/best.pt` |
| yol | COCO pretrained | COCO → VisDrone | COCO → UAVDT(vehicle) → VisDrone |
| epoch | — | 105 (en iyi 75) | 111 (en iyi 81) |
| VisDrone val mAP50 | — | 0.2065 | **0.2169** |
| VisDrone val mAP50-95 | — | 0.1251 | **0.1338** |

## 2. recall@IoU≥0.5 — ana tablo

### uav0000117_02622_v / track 23

| boyut | A5 baseline | A6 kontrol | A6 UAVDT+VisDrone |
|---|---|---|---|
| native | 0.825 | **0.050** | 0.675 |
| **57×21** | **0.975** | 0.925 | 0.875 |
| **40×15** | 0.350 | **0.925** | **0.900** |
| **30×12** | 0.050 | 0.275 | **0.675** |
| **20×10** | 0.050 | 0.100 | 0.050 |
| **15×7** | 0.000 | 0.075 | 0.000 |
| **10×5** | 0.000 | 0.000 | 0.000 |
| **8×5** | 0.000 | 0.000 | 0.000 |
| **5×5** | 0.000 | 0.000 | 0.000 |

### uav0000137_00458_v / track 12

| boyut | A5 baseline | A6 kontrol | A6 UAVDT+VisDrone |
|---|---|---|---|
| native | 1.000 | 1.000 | 1.000 |
| **57×21** | 1.000 | 1.000 | 1.000 |
| **40×15** | 0.400 | **0.700** | 0.600 |
| **30×12** | 0.375 | **0.550** | 0.325 |
| **20×10** | **0.375** | 0.200 | 0.175 |
| **15×7** | **0.275** | 0.000 | 0.000 |
| **10×5** | 0.000 | 0.000 | 0.000 |
| **8×5** | 0.000 | 0.000 | 0.000 |
| **5×5** | 0.000 | 0.000 | 0.000 |

## 3. Ortalama IoU (eşleşen tespit)

| boyut | 117/23 A5 / kontrol / UAVDT | 137/12 A5 / kontrol / UAVDT |
|---|---|---|
| native | 0.782 / 0.265 / **0.798** | 0.918 / **0.930** / 0.924 |
| 57×21 | **0.954** / 0.869 / 0.810 | 0.791 / **0.845** / 0.813 |
| 40×15 | **0.904** / 0.795 / 0.779 | 0.548 / **0.729** / 0.687 |
| 30×12 | **0.924** / 0.852 / 0.806 | 0.455 / **0.605** / 0.487 |
| 20×10 | 0.749 / **0.790** / 0.787 | **0.382** / 0.307 / 0.352 |
| 15×7 | — / **0.702** / — | **0.282** / 0.069 / 0.061 |
| 10×5 | — / — / — | 0.020 / 0.030 / **0.032** |
| 8×5 | — / — / — | 0.012 / 0.018 / **0.019** |
| 5×5 | — / — / — | 0.006 / 0.008 / **0.009** |

10×5 ve altındaki IoU değerleri **anlamlı değildir**: recall@0.5 = 0 olduğu için
bunlar yalnızca yoğun arkaplandaki başka bir aracın kutusunun yamayla kesişmesini ölçer
(A5.2'de de aynı uyarı yapılmıştı).

## 4. Ortalama güven

| boyut | 117/23 A5 / kontrol / UAVDT | 137/12 A5 / kontrol / UAVDT |
|---|---|---|
| 57×21 | 0.443 / 0.675 / **0.683** | 0.574 / **0.804** / 0.737 |
| 40×15 | 0.293 / 0.549 / **0.645** | 0.551 / **0.695** / 0.594 |
| 30×12 | 0.295 / 0.319 / **0.557** | 0.581 / **0.698** / 0.523 |
| 20×10 | 0.380 / **0.389** / 0.288 | **0.573** / 0.493 / 0.399 |

Fine-tuning, 57–30 px bandında **güveni belirgin yükseltiyor** — 117/23 30×12'de UAVDT
kolu 0.295 → 0.557. Bu, eşiğe yakın kararların sağlamlaşması demek.

## 5. False positive / false negative

Arkaplanın kendi ürettiği taban (tespit/kare): 117/23 → A5 **3.05**, kontrol **0.50**,
UAVDT **1.10**. 137/12 → 7.15 / 7.78 / 6.92.

| 117/23 | A5 FP/FN | kontrol FP/FN | UAVDT FP/FN |
|---|---|---|---|
| 57×21 | 126 / 1 | **26** / 3 | 40 / 4 |
| 40×15 | 120 / 26 | **24** / 3 | 41 / **1** |
| 30×12 | 117 / 38 | **22** / 29 | 41 / **11** |
| 20×10 | 119 / 38 | **20** / 36 | 42 / 38 |
| 5×5 | 123 / 40 | **19** / 40 | 45 / 40 |

**A6'nın en net ve tartışmasız kazancı burada:** 117/23'te sahte pozitif sayısı
~120'den ~20–45'e düşüyor (3–6 kat azalma). 137/12'de böyle bir kazanç yok
(227→229/278); o sahnenin arkaplanı zaten araç dolu.

## 6. Takip (YOLO-tohumlu) — kilit / drift / PSR

| boyut | 117/23 | 137/12 |
|---|---|---|
| **57×21** | A5 IoU 0.523 kl 0.98 · **KN 0.763 kl 1.00** · UV 0.741 kl 1.00 — üçü de drift yok | A5 0.740 · KN 0.728 · UV 0.728, üçü de kl 1.00 drift yok |
| **40×15** | A5 0.402 · **KN 0.775** · UV 0.774, üçü de kl 1.00 drift yok | A5 0.774 · KN 0.744 · UV 0.751, üçü de kl 1.00 drift yok |
| **30×12** | **A5 0.832 kl 1.00 drift yok** · KN 0.328 drift 25 · UV 0.338 drift 25 | A5 0.798 · **KN 0.821** · UV 0.789, üçü de kl 1.00 |
| **20×10** | A5 0.042 drift 50 · **KN 0.696 kl 0.86 drift yok** · UV 0.268 drift 37 | **A5 0.803** · KN 0.747 · UV 0.722, üçü de kl 1.00 |
| **15×7** | A5 0.000 drift 54 · KN 0.107 drift 46 · **UV 0.432 kl 0.75 drift yok** | **A5 0.703 kl 0.97 drift yok** · KN 0.034 drift 15 · UV 0.019 drift 25 |
| **10×5 ve altı** | üç modelde de **kilit yok** | üçü de kilitleniyor ama IoU ≤0.054, kilit oranı 0.00 — yanlış nesne |

Takip kolu monoton değil ve seviyeler arası dalgalanıyor; A5.2'de belirtilen sınır
burada da geçerli — ≤10 px satırları takip yeteneği kanıtı sayılmaz.

## 7. Gecikme / FPS (CPU, 640×360 tuval → ağ girdisi 640×384)

| | ort gecikme | eşdeğer FPS |
|---|---|---|
| A5 baseline | 38.27 ms | 26.1 |
| A6 kontrol | 36.40 ms | 27.5 |
| A6 UAVDT→VisDrone | **33.88 ms** | **29.5** |

Üç model aynı mimari (YOLOv8n); fark tespit sayısının NMS maliyetine yansımasından
geliyor. Hedef boyutu gecikmeyi değiştirmiyor — A5.2'deki bulgu korunuyor.
**Raspberry Pi Zero 2 W ve IMX500 üzerinde hâlâ hiçbir ölçüm yok.**

## 8. Y8-D / A6-3 kuralı — DEĞİŞTİRİLMEDİ

Kural: her iki birincil dizide `recall@IoU≥0.5 ≥ 0.80` **ve** YOLO-tohumlu kilit
**ve** drift yok.

| model | nitelenen seviyeler | **minimum güvenilir boyut** |
|---|---|---|
| A5 baseline | `57×21` | **57** |
| A6 kontrol | `57×21` | **57** |
| A6 UAVDT→VisDrone | `57×21` | **57** |

40×15'te kalma nedenleri: A5 → 117/23 recall 0.350 · kontrol → 137/12 recall 0.700 ·
UAVDT → 137/12 recall 0.600. Üçü de 0.80 eşiğinin altında.

> ### HÜKÜM
> **Fine-tuning küçük hedef hedefini bu konfigürasyonla iyileştirmedi.**
> Minimum güvenilir boyut üç modelde de **57 px**'te kaldı; **taban düşmedi**.

## 9. Beş soruya cevap

**1. UAVDT ön-eğitimi küçük hedef recall'ünü artırdı mı?**
**Tutarlı biçimde hayır.** Tek net kazanç 117/23 · 30×12'de: kontrol 0.275 → UAVDT
**0.675** (+0.400) ve güven 0.319 → 0.557. 137/12'de ise UAVDT **her seviyede kontrolün
altında** (40×15: 0.600 vs 0.700 · 30×12: 0.325 vs 0.550 · 20×10: 0.175 vs 0.200).
UAVDT val mAP'i biraz yükseltti (mAP50 0.2065 → 0.2169) ama bu benchmark'a
sistematik olarak yansımadı.

**2. VisDrone fine-tuning tek başına yeterli mi?**
Belirli bir bantta **evet, çok etkili**; ama bedeli var. 40×15'te 117/23 recall
0.350 → **0.925**, 137/12 0.400 → **0.700**. Buna karşılık 137/12'nin **20×10 ve
15×7** seviyelerinde A5'in *altına* düşüyor (0.375 → 0.200 ve 0.275 → **0.000**),
ve 117/23 native'de kontrol kolu **0.825 → 0.050** ile çöküyor. Yani fine-tuning
orta bandı kazandırdı, en küçük bandı ve büyük hedefi kaybetti.

**3. Güvenilir minimum hedef boyutu A5'ten aşağı indi mi?** **Hayır — 57'de kaldı.**

**4. UAVDT katkısı hangi piksel boyutunda görülüyor?**
Üç yerde: (a) **117/23 30×12** (28.2×30.0 px) — recall +0.400, güven +0.238;
(b) **büyük hedefte koruma** — 117/23 native'de kontrol 0.050'ye çökerken UAVDT
0.675'te kalıyor, yani UAVDT ön-eğitimi fine-tuning'in büyük nesne yeteneğini
yok etmesini engelliyor; (c) **117/23 15×7 takip** — tek kilitlenip drift etmeyen
kol UAVDT (IoU 0.432, kilit 0.75).

**5. 5×5 / 8×5 / 10×5 gerçek sonuç nedir?**
**Üç modelde de, her iki birincil dizide recall@IoU≥0.5 = 0.000.** 117/23'te FN 40/40.
Hiçbir model bu boyutlarda hedefi bulmuyor. 137/12'de görünen "kilit var" satırları
arkaplandaki başka bir araca kilitlenmedir (IoU ≤0.054). **5×5 başarısı yok.**

## 10. mAP ile benchmark'ı karıştırmama notu

Aşama B'nin VisDrone val mAP'i düşük: mAP50 **0.2169**, mAP50-95 **0.1338**
(kontrol 0.2065 / 0.1251). Sınıf bazında car mAP50 0.569, van 0.061, truck 0.037,
bus 0.201 — ortalamayı van/truck çöküşü aşağı çekiyor ve bunun sebebi sınıf
dengesizliği (car 13 997 vs bus 251) ile UAVDT'de van sınıfının hiç olmaması.
**Bu düşük mAP gizlenmiyor**, ama bu benchmark'ın ölçütü değil: A5.2 protokolü
sınıf ayrımını değil hedefin bulunup bulunmadığını ölçer. İki sonuç ayrı raporlanmıştır.

**Düşük mAP'e rağmen belirgin iyileşen yerler** (istendiği gibi ayrıca belirtiliyor):
- 117/23 **40×15**: recall 0.350 → 0.925 / 0.900 — **2.6 kat**
- 117/23 **30×12**: 0.050 → 0.675 (UAVDT) — **13.5 kat**
- 137/12 **40×15**: 0.400 → 0.700 (kontrol)
- 117/23 sahte pozitif: ~120 → ~20–45 (**3–6 kat azalma**)
- 57–30 px bandında güven belirgin yükseldi

Bunlar gerçek ve ölçülmüş kazançlar; ancak **Y8-D eşiğini geçmeye yetmiyorlar**
çünkü kural her iki dizide birden 0.80 istiyor ve 137/12 tarafında aynı seviyeler
0.60–0.70'te kalıyor.

## 11. Genel hüküm

- **Minimum güvenilir boyut: 57 px — üç modelde de aynı. A6 tabanı düşürmedi.**
- **UAVDT katkısı ölçülebilir ama tutarsız**: bir dizide bir seviyede güçlü
  (117/23 30×12), diğer dizide hafif negatif. Büyük hedef yeteneğini korumadaki
  rolü net ve değerli.
- **VisDrone fine-tuning bir takas yaptı**: 57–30 px bandını belirgin iyileştirdi,
  20×10–15×7 bandını ve büyük hedefi kötüleştirdi.
- **5×5 / 8×5 / 10×5: hiçbir modelde tespit yok.**
- Gecikme üç modelde benzer (~34–38 ms CPU); hedef boyutundan bağımsız.
- **Pi Zero 2 W / IMX500 üzerinde ölçüm yok.**

Açık kalan borçlar: P0.1 bağımsız mutlak boyut ölçümü · imgsz=640'ın küçük hedefte
dayattığı sınır (A6 planındaki 960 tanı kolu koşulmadı) · sınıf dengesizliği ·
`veri/yolo_secici.py` sınıf filtresi hâlâ COCO haritalı (A6 modeliyle kullanılacaksa
güncellenmeli — bu turda **dokunulmadı**).
