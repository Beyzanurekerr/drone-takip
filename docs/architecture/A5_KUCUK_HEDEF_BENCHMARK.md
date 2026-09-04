# A5.2 — Küçük hedef benchmark'ı (COCO pretrained YOLOv8n, saf taban)

**Tarih:** 2026-08-31 · **Commit/push:** YAPILMADI
**Veri:** `cikti/a5_kucuk_hedef.json` · **Kod:** `gazebo/bench_a52_kucuk_hedef.py` (salt okunur)
**Kabul ölçütü:** `docs/architecture/A5.2_KABUL_OLCUTU.md` (koşumdan **önce** yazıldı)

Değiştirilmedi: `takip/` (md5 6/6) · A5.1 (`veri/yolo_secici.py`, `main.py`) ·
A3.9 / A3.10 / A4. Fine-tuning yok · ONNX/NCNN/IMX500 yok · Optuna yok ·
ROI kırpma yok · model/conf/imgsz değişmedi.

---

## 1. Metodoloji — ve reddedilen iki yol

Hedef boyutunu kontrollü değiştirmenin üç yolu denendi. İkisi **ölçülerek** elendi.

### M0 (RED) — Tüm kareyi küçültmek işe yaramaz

Ultralytics letterbox'ı uzun kenarı `imgsz=640`'a normalize eder. Kareyi `s` ile
küçültmek ağ girdisinde birebir geri büyütülür. 117/23 kare 1'de ölçüldü:

| kare ölçeği | ağ girdisi | tespit | ort. güven | native-eşdeğer kutu |
|---|---|---|---|---|
| 1.000 | 2720×1530 | 8 | 0.539 | 140×93 |
| 0.500 | 1360×765 | 7 | 0.572 | 144×99 |
| 0.250 | 680×382 | 6 | 0.611 | 151×106 |
| 0.125 | 340×191 | 5 | 0.612 | 162×115 |

Dedektörün gördüğü şey değişmiyor. Bu yöntem "yeniden örnekleme kaybını" ölçer,
**hedef boyutunu değil**. Reddedildi.

### M1 (RED) — Gerçek arkaplanlı FOV kırpma yetmiyor

146×154 px'lik gerçek hedefi 640×360 tuvalde 5 px'e indirmek **19193×10796 px**
pencere ister; kaynak kare 2720×1530. En büyük seviye (57) bile 2774×1560 istiyor.
**Hiçbir seviye** gerçek arkaplanla ulaşılamıyor. Reddedildi.

### M2 (UYGULANAN) — Gerçek arkaplan üzerine gerçek hedef yaması

- **Tuval 640×360, her seviyede sabit.** Letterbox → **640×384, ölçek 1.000**
  (yalnızca dolgu, yeniden ölçekleme YOK). Yani **nominal piksel boyutu = ağın
  gördüğü boyut**. Bu, letterbox sorusunun bu benchmark'taki tam cevabıdır.
- **Hedef yaması:** GT kutusunun native çözünürlükteki kırpımı, **izotropik**
  (INTER_AREA) ölçeklenir. Kontrol edilen değişken **uzun kenar**dır.
  Bu hedeflerin gerçek en-boy oranı ~1:1 (117/23 GT medyan 146×154), nominal
  etiketlerinki ~2.7:1. İkisini birden zorlamak hedefi **bozardı**; bu yüzden
  seviye adı etikettir, **ulaşılan w×h her satırda ayrıca verilir**.
- **Arkaplan:** hedefe **en yakın**, hedefi ölçüm penceresinin hiçbir karesinde
  içermeyen 640×360 hücre — aynı yol dokusu, aynı ışık, aynı ölçek.
- Sabit: ağırlık · `conf=0.25` · `imgsz=640` · COCO [2,3,5,7] · `device=cpu` ·
  8 thread · rastgelelik yok. **Tek değişken: yamanın uzun kenarı.**

**Arkaplan ölçütünde bir yol denendi ve geri alındı.** Önce "dedektörün hiç tespit
üretmediği hücre" seçildi. Bu ölçüt, tanımı gereği **yola en az benzeyen** bölgeyi
seçiyor: oraya yapıştırılan native boyutlu gerçek araç 20 karede yalnızca **3** kez
bulundu (dokunulmamış karede 20/20). Ölçüt, ölçmek istediğimiz şeyi arkaplan
uyuşmazlığıyla karıştırıyordu; terk edildi. Arkaplanın kendi ürettiği tespitler
gizlenmiyor, `arkaplan_taban` olarak ayrıca ölçülüp raporlanıyor.

### Hareket konfaundu — ölçülerek elendi

Takip kolunda hedefin tuvaldeki yer değiştirmesi GT hareketinin `s` katıdır.
Böylece "kendi eninin kaç katı / kare" her seviyede **sabit** kalır (projenin
ölçek değişmezliği: doluluk = v/(fps·L)). Doğrulandı:

| dizi | native | 57 | 30 | 15 | 5 |
|---|---|---|---|---|---|
| 117/23 (kendi eni/kare) | 0.0616 | 0.0593 | 0.0600 | 0.0625 | 0.0737 |
| 137/12 (kendi eni/kare) | 0.0205 | 0.0189 | 0.0208 | 0.0249 | 0.0295 |

Yani seviyeler arası fark **hareketten değil boyuttan** geliyor.

### İki ölçüm ayrı tutuldu

1. **TESPİT** — YOLO hedefi buluyor mu? (kare başına, yama tuval merkezinde)
2. **TAKİP** — alınan başlangıç kutusu takibi ne kadar sürdürüyor? İki kol:
   **GT-tohumlu** (takipçinin kendi sınırı, dedektörden bağımsız) ve
   **YOLO-tohumlu** (dedektörün başlatabildiği sınır).
   Takip kolunda arkaplan penceresi sabittir → kamera ego-hareketi yoktur;
   bu kol **iyimser bir üst sınırdır** ve boyut etkisini izole eder.

---

## 2. Kabul kriterleri

| | Sonuç |
|---|---|
| **Y8-A** 8 seviyenin tamamı ölçülebilir | **GEÇTİ** — iki birincil dizide 8/8 seviye, hem TESPİT hem TAKİP bloğunda eksiksiz satır (+ `native` kontrol satırı) |
| **Y8-B** Tekrarlanabilirlik | **GEÇTİ** — TESPİT bloğunun **tüm metrik alanları birebir aynı** (0 fark), TAKİP 54/54 kol birebir aynı (en büyük sayısal fark **0**), arkaplan hücreleri ve kompozit kontrolü aynı |
| **Y8-C** 57×21 taban + kompozit geçerliliği | **GEÇTİ** — 57 seviyesi r@.5 = 0.975 / 1.000; kompozit kontrolü 117/23 20→17, 137/12 20→20 |
| **Y8-D** Minimum güvenilir boyut | **GEÇTİ** — belirlendi: **uzun kenar 57 px** |

> **Y8-B'de bir kapsam düzeltmesi:** ölçütü "JSON bit-birebir" diye yazmıştım.
> Gecikme/FPS alanları duvar saatidir ve hiçbir koşumda birebir olamaz. Ölçüt
> gevşetilmedi; kapsamı net söyleniyor: **metrik alanlarının tamamı bit-birebir**,
> duvar saati alanları hariç (107 alan, beklendiği gibi).

---

## 3. TESPİT sonuçları

Tuval 640×360 → ağ girdisi 640×384, **letterbox ölçeği 1.000**: aşağıdaki
"ulaşılan" sütunu **ağın gördüğü piksel boyutudur**.

### 117/23 (birincil) — kare 2720×1530, native GT 147×156, arkaplan tabanı 3.05 tespit/kare

| seviye | ulaşılan (=ağ girdisi) | **recall@IoU≥0.5** | ort IoU | ort güven | ekstra tespit (40 kare) |
|---|---|---|---|---|---|
| native | 146.9×155.2 | 0.825 | 0.782 | 0.481 | 106 |
| **57×21** | 54.1×57.0 | **0.975** | 0.954 | 0.443 | 126 |
| 40×15 | 38.0×40.0 | 0.350 | 0.904 | 0.293 | 120 |
| 30×12 | 28.2×30.0 | 0.050 | 0.924 | 0.295 | 117 |
| 20×10 | 19.0×20.0 | 0.050 | 0.749 | 0.380 | 119 |
| **15×7** | 14.0×15.0 | **0.000** | — | — | 120 |
| **10×5** | 9.2×10.0 | **0.000** | — | — | 122 |
| **8×5** | 8.0×8.0 | **0.000** | — | — | 122 |
| **5×5** | 5.0×5.0 | **0.000** | — | — | 123 |

### 137/12 (birincil) — kare 2688×1512, native GT 126×130, arkaplan tabanı 7.15 tespit/kare

| seviye | ulaşılan | **recall@IoU≥0.5** | ort IoU | ort güven | ekstra tespit |
|---|---|---|---|---|---|
| native | 146.1×138.4 | 1.000 | 0.918 | 0.695 | 191 |
| **57×21** | 56.9×54.0 | **1.000** | 0.791 | 0.574 | 227 |
| 40×15 | 39.9×37.8 | 0.400 | 0.548 | 0.551 | 233 |
| 30×12 | 29.9×28.5 | 0.375 | 0.455 | 0.581 | 253 |
| 20×10 | 20.0×19.0 | 0.375 | 0.382 | 0.573 | 257 |
| **15×7** | 15.0×14.2 | **0.275** | 0.282 | 0.559 | 257 |
| **10×5** | 10.0×9.3 | **0.000** | 0.020 | 0.657 | 259 |
| **8×5** | 8.0×7.4 | **0.000** | 0.012 | 0.656 | 259 |
| **5×5** | 5.0×5.0 | **0.000** | 0.006 | 0.664 | 261 |

### 305/5 (destek) — kare 1904×1071, native GT 46×93

Bu dizide **kompozit kontrolü başarısız**: dokunulmamış karede 0/20, native
yamada 0/20. Yani hedefin **kendi doğal boyutu zaten YOLO'nun tabanının altında**
(A5.1'de de aynı sonuç alınmıştı). Bu yüzden 305/5 bir boyut süpürmesi vermiyor;
tabanı **doğrulayan** bir veri noktası olarak duruyor: native r@.5 = 0.025,
57 ve altındaki her seviyede 0.000.

### `hit` (recall@IoU>0) sütunu neden raporlanmadı

JSON'da var ama **güvenilmez**: yoğun arkaplanda (137/12 tabanı 7.15 tespit/kare)
arkaplandaki bir aracın kutusu 5×5'lik yamayı kapsayınca `hit=1.0` çıkıyor —
ama aynı satırda ort IoU 0.006. `hit` orada hedefi bulmayı değil, arkaplanı ölçüyor.
Karar ölçütü `recall@IoU≥0.5`'tir ve Y8-D onu kullanır.

---

## 4. TAKİP sonuçları (TESPİT'ten ayrı)

### 117/23

| seviye | GT-tohum IoU | kilit | drift | PSR | merkez hata | YOLO-tohum: kilit | IoU | drift |
|---|---|---|---|---|---|---|---|---|
| native | 0.176 | 0.00 | 1 | 20.5 | 16.5 | True | 0.228 | 2 |
| 57×21 | 0.751 | 1.00 | yok | 29.0 | 3.5 | True | 0.523 | yok |
| 40×15 | 0.778 | 1.00 | yok | 25.7 | 3.4 | True | 0.402 | yok |
| 30×12 | 0.339 | 0.39 | 25 | 11.3 | 125.1 | True | 0.832 | yok |
| 20×10 | 0.284 | 0.34 | 24 | 10.3 | 121.2 | True | 0.042 | 50 |
| 15×7 | 0.281 | 0.42 | 14 | 15.7 | 21.8 | True | 0.000 | 54 |
| 10×5 | 0.161 | 0.24 | 13 | 13.3 | 44.5 | **False** | — | — |
| 8×5 | 0.145 | 0.20 | 13 | 16.2 | 96.1 | **False** | — | — |
| 5×5 | 0.103 | 0.17 | 11 | 14.3 | 120.4 | **False** | — | — |

### 137/12

| seviye | GT-tohum IoU | kilit | drift | PSR | merkez hata | YOLO-tohum: kilit | IoU | drift |
|---|---|---|---|---|---|---|---|---|
| native | 0.720 | 1.00 | yok | 37.3 | 21.2 | True | 0.114 | 1 |
| 57×21 | 0.808 | 1.00 | yok | 45.0 | 3.4 | True | 0.740 | yok |
| 40×15 | 0.765 | 1.00 | yok | 39.7 | 3.9 | True | 0.774 | yok |
| 30×12 | 0.807 | 1.00 | yok | 40.0 | 1.6 | True | 0.798 | yok |
| 20×10 | 0.835 | 1.00 | yok | 37.6 | 1.1 | True | 0.803 | yok |
| 15×7 | 0.557 | 0.97 | yok | 28.8 | 2.2 | True | 0.703 | yok |
| 10×5 | 0.301 | 0.41 | 21 | 36.0 | 16.3 | True | 0.021 | 13 |
| 8×5 | 0.614 | 0.73 | 47 | 23.6 | 2.0 | True | 0.017 | 13 |
| 5×5 | 0.734 | 0.95 | yok | 21.5 | 0.7 | True | 0.009 | 15 |

### Bu tablonun iki satır grubu YORUMLANAMAZ — açıkça işaretleniyor

**(a) `native` takip satırı geçersiz.** 640×360 tuvalde native yama 147×155 px;
DCF yaması `boyut × dolgu(2.0)` = ~310 px ve hedef tuvalde 9.6 px/kare ilerleyip
42 karede tuvali terk ediyor. Burada kırılan **tuval geometrisi**, boyut değil.
`native` bir **TESPİT kontrolüdür**, takip seviyesi değildir.

**(b) ≤10 px seviyelerdeki GT-tohumlu satırlar takip yeteneği göstermez.**
137/12'de 5×5 satırı (IoU 0.734, kilit 0.95, drift yok) 10×5'ten (0.301) *daha iyi*
görünüyor. Bu monoton olmayışı "5×5 çalışıyor" diye okumak yanlış olur. Hareket
konfaundu ölçülerek elendi (§1), dolayısıyla kalan açıklama takipçinin
**mutlak piksel tabanlarıdır**: `min_kenar=4.0`, `maks_sicrama=max(6.0, 0.9·boyut)`
— 5.8 px'lik hedefte 6.0 px tabanı devreye giriyor, yani arama yarıçapı hedefin
kendisinden büyük — ve 32×32 DCF ızgarası `boyut×2.0` yamaya oturuyor. Bu boyutlarda
ölçüm, takip yeteneğini değil bu tabanların davranışını ölçüyor: neredeyse duran
birkaç piksellik bir leke, homojen yol üzerinde yerinde kalarak yüksek IoU
üretebilir. **Bu satırlar kanıt olarak kullanılmadı.**

Yorumlanabilir bölge: **15 px ve üzeri.** Orada tablo monoton ve tutarlı.

---

## 5. Minimum güvenilir boyut (Y8-D)

Kural (önceden sabit): her iki birincil dizide `recall@IoU≥0.5 ≥ 0.80`
**ve** YOLO-tohumlu takip kilitleniyor **ve** YOLO-tohumlu `drift yok`.

| seviye | r@.5 117/23 | r@.5 137/12 | ≥0.80 (ikisi) | YOLO kilit | YOLO drift yok | **nitelik** |
|---|---|---|---|---|---|---|
| native | 0.825 | 1.000 | ✔ | ✔ | ✘ (117/23 drift 2) | hayır |
| **57×21** | **0.975** | **1.000** | **✔** | **✔** | **✔** | **EVET** |
| 40×15 | 0.350 | 0.400 | ✘ | ✔ | ✔ | hayır |
| 30×12 | 0.050 | 0.375 | ✘ | ✔ | ✔ | hayır |
| 20×10 | 0.050 | 0.375 | ✘ | ✔ | ✘ | hayır |
| 15×7 | 0.000 | 0.275 | ✘ | ✔ | ✘ | hayır |
| 10×5 | 0.000 | 0.000 | ✘ | ✘ | — | hayır |
| 8×5 | 0.000 | 0.000 | ✘ | ✘ | — | hayır |
| 5×5 | 0.000 | 0.000 | ✘ | ✘ | — | hayır |

> **MİNİMUM GÜVENİLİR BOYUT = uzun kenar 57 px** (ulaşılan 54.1×57.0 ve 56.9×54.0).
> Ölçülen en küçük nitelikli seviye budur; 40 px'te recall zaten 0.35–0.40'a düşüyor.

Vurgulanması istenen dört seviye:

| seviye | 117/23 r@.5 | 137/12 r@.5 | YOLO kilitlenebiliyor mu |
|---|---|---|---|
| **15×7** | 0.000 | 0.275 | evet ama sürdüremiyor (drift 54 / yok ama IoU 0.70) |
| **10×5** | 0.000 | 0.000 | 117/23 **hayır** · 137/12 evet ama IoU 0.021 |
| **8×5** | 0.000 | 0.000 | 117/23 **hayır** · 137/12 evet ama IoU 0.017 |
| **5×5** | 0.000 | 0.000 | 117/23 **hayır** · 137/12 evet ama IoU 0.009 |

10×5 ve altında `recall@IoU≥0.5` **her iki birincil dizide 0.000**. 137/12'de
"kilit=True" görünmesi, arkaplandaki başka bir aracın kutusunun yamayla örtüşmesinden
kaynaklanıyor (IoU 0.009 bunu gösteriyor) — hedefin bulunması değil.

---

## 6. Sorulan karşılaştırma

> **"YOLOv8n COCO pretrained, klasik tracker'ın daha önce ölçülen ~9×4 konum
> sınırını ve ~25×10 kutu ölçüsü sınırını aşağı çekebiliyor mu?"**

**HAYIR. Aşağı çekmiyor; kullanılabilir tabanı YUKARI taşıyor.**

| | klasik takipçi (önceki ölçüm) | YOLOv8n COCO (bu ölçüm) |
|---|---|---|
| konum sınırı | ~9×4 px | ~9×10 px'te (10×5 seviyesi) recall **0.000** — hedefi hiç bulamıyor |
| kutu ölçüsü sınırı | ~25×10 px | 28×30 px'te (30×12 seviyesi) recall 0.05 / 0.375 — **güvenilir değil** |
| güvenilir taban | — | **uzun kenar 57 px** |

Doğrudan kanıt, aynı karelerde iki kolun karşılaştırılmasından geliyor:
137/12'de **20×10** seviyesinde GT-tohumlu takipçi IoU **0.835**, kilit **1.00**,
drift **yok** — yani takipçi o boyutta hedefi taşıyor; aynı seviyede YOLO'nun
`recall@0.5`'i **0.375**. Takipçi, dedektörün güvenilir bulamadığı boyutta
takibi sürdürüyor.

Bunun mimarideki karşılığı: **A5 dedektörü bir başlatıcıdır, bir küçültücü değil.**
Küçük hedefte zincirin kırıldığı yer takipçi değil, **başlatma**dır. Bu, A6'nın
(giriş çözünürlüğü / ROI kırpma / fine-tuning) gerekçesini ölçüyle kurar.

---

## 7. Çıkarım maliyeti

Tuval her seviyede sabit (640×360 → ağ girdisi 640×384), dolayısıyla maliyet de sabit.

| seviye | ort ms | p50 | p95 | eşdeğer FPS |
|---|---|---|---|---|
| native | 35.12 | 34.12 | 39.49 | 28.5 |
| 57×21 | 34.09 | 33.28 | 39.50 | 29.3 |
| 40×15 | 32.20 | 31.83 | 36.37 | 31.1 |
| 30×12 | 33.16 | 32.79 | 36.27 | 30.2 |
| 20×10 | 33.55 | 32.40 | 37.07 | 29.8 |
| 15×7 | 32.46 | 32.43 | 34.68 | 30.8 |
| 10×5 | 32.29 | 32.06 | 34.95 | 31.0 |
| 8×5 | 32.33 | 32.06 | 35.02 | 30.9 |
| 5×5 | 32.29 | 32.12 | 35.10 | 31.0 |

3 dizi × 9 seviye ortalaması **33.22 ms** (min 32.20, max 36.80); seviyeler arası
tüm aralık **4.60 ms**. **Hedef boyutu çıkarım maliyetini değiştirmiyor** — maliyet
`imgsz`'e bağlı, hedefe değil.

Donanım: masaüstü CPU i7-11800H, 8 thread, `torch 2.13.0+cpu`, CUDA yok.
> **Raspberry Pi Zero 2 W: HENÜZ ÖLÇÜLMEDİ. IMX500: HENÜZ ÖLÇÜLMEDİ.**

---

## 8. Bu benchmark'ın sınırları (kapatılmadı, işaretlendi)

1. **Kompozit yapıdır.** Hedef ve arkaplan gerçek, ama yama dikdörtgeni bir dikiş
   yeri bırakır; arkaplan native çözünürlükte kalıp hedef `s` ile küçüldüğü için
   hedef arkaplandan "daha uzak" görünür. Geçerlilik kontrolü (dokunulmamış kare
   vs native yama) bu etkiyi sınırlıyor ama sıfırlamıyor.
2. **Takip kolunda kamera ego-hareketi yok** → takip sayıları iyimser üst sınırdır.
3. **≤10 px GT-tohumlu takip satırları yorumlanamaz** (§4b).
4. **305/5 boyut süpürmesi vermiyor**; native'i zaten tabanın altında.
5. `visdrone_det` (548 görüntü) **kullanılmadı** — A6'ya ayrılmıştır.
6. Sim kayıtları (`hizli_hedef`, `duran_hedef`) bu benchmark'a **alınmadı**:
   A5.1'de ölçüldüğü gibi COCO YOLOv8n prosedürel sim dikdörtgenlerini araç olarak
   hiç tanımıyor (kilit yok), dolayısıyla bir boyut süpürmesi üretemezler.

---

## 9. Hüküm

**Y8-A GEÇTİ · Y8-B GEÇTİ · Y8-C GEÇTİ · Y8-D GEÇTİ**

- Minimum güvenilir boyut: **uzun kenar 57 px**
- YOLOv8n COCO pretrained, takipçinin ~9×4 / ~25×10 sınırlarını **aşağı çekmiyor**
- Çıkarım maliyeti hedef boyutundan **bağımsız** (~33 ms, masaüstü CPU)
- Hedef donanımda ölçüm **yok**
