# A6 — Veri envanteri ve eğitim planı (PLANLAMA TURU)

**Tarih:** 2026-08-31 · **Bu tur:** yalnızca envanter + plan.
**Yapılmadı:** model eğitimi · kod değişikliği · commit/push · Optuna · ONNX/NCNN/IMX500.
**Taban:** `docs/architecture/A5_KUCUK_HEDEF_BENCHMARK.md` (A6 baseline'ı) ·
`cikti/a5_kucuk_hedef.json`

---

## 1. Klasör yapısı ve sayılar (1–3)

```
data/datasets/visdrone_det/
├── images/       548 × .jpg
└── annotations/  548 × .txt
```

Düz yapı — **hazır split yok**. Görüntü ↔ etiket eşleşmesi **548/548 tam**;
etiketsiz görüntü 0, görüntüsüz etiket 0. Boş annotation dosyası 0.
Toplam kutu **40 169** (görüntü başına ort. 73.3). Araçsız görüntü: 29.

Çözünürlük: 1360×768 (408) · 960×544 (121) · 1920×1080 (19).

## 2. Annotation formatı (10)

8 kolon, kare ve `track_id` **yok** (VID'in 10 kolonundan farklı):

```
<x>,<y>,<w>,<h>,<score>,<class>,<truncation>,<occlusion>
```

`score=0` ya da `class=0` → **yoksayılan** (ignored region), ölçüme katılmaz.
Repo bunu `veri/etiket.py:det_oku` ile zaten okuyor; yeni parser gerekmiyor.
Eğitim için **YOLO formatına** (normalize `cls cx cy w h`) dönüştürme gerekecek —
bu A6'nın ilk kod işi olacak, bu turda yapılmadı.

## 3. Sınıf dağılımı (4)

| id | sınıf | kutu | % | |
|---|---|---|---|---|
| 0 | ignored | 1378 | 3.4% | atılacak |
| 1 | pedestrian | 8844 | 22.0% | |
| 2 | people | 5125 | 12.8% | |
| 3 | bicycle | 1287 | 3.2% | |
| **4** | **car** | **14064** | **35.0%** | **ARAÇ** |
| **5** | **van** | **1975** | **4.9%** | **ARAÇ** |
| **6** | **truck** | **750** | **1.9%** | **ARAÇ** |
| 7 | tricycle | 1045 | 2.6% | |
| 8 | awning-tricycle | 532 | 1.3% | |
| **9** | **bus** | **251** | **0.6%** | **ARAÇ** |
| 10 | motor | 4886 | 12.2% | |
| 11 | others | 32 | 0.1% | |

Yoksayılan kutu 1410 (%3.5). **`ARAC_SINIFLARI = (4,5,6,9)` geçerli kutu: 17 040**
(tümünün %42.4). Sınıf içi denge kötü: car : bus = **56 : 1**.

## 4. bbox boyut dağılımı (5) ve küçük hedef (6)

Araç kutuları (17 040), native piksel: `w` medyan 38 [2..580] · `h` medyan 28 ·
**uzun kenar medyan 41**, p05=9, p95=129.

**Ama eğitimde/çıkarımda önemli olan ağ girdisindeki boyuttur.** `imgsz=640`
letterbox çarpanı: 1360×768 → 0.471 · 960×544 → 0.667 · 1920×1080 → 0.333.
Ağ girdisinde araç uzun kenarı: **medyan 19.8 px**, p05 4.7, p95 61.2.

### A5 basamaklarının A6 eğitim setindeki karşılığı

| A5 seviyesi | uzun kenar aralığı | native px | % | **ağ girdisi (640)** | **%** |
|---|---|---|---|---|---|
| 57×21 | > 57 | 5568 | 32.7% | 1097 | **6.4%** |
| 40×15 | (40, 57] | 3132 | 18.4% | 1698 | 10.0% |
| 30×12 | (30, 40] | 2111 | 12.4% | 2086 | 12.2% |
| 20×10 | (20, 30] | 2474 | 14.5% | 3566 | 20.9% |
| **15×7** | (15, 20] | 1324 | 7.8% | 2479 | 14.5% |
| **10×5** | (10, 15] | 1280 | 7.5% | 2402 | 14.1% |
| **8×5** | (8, 10] | 461 | 2.7% | 1040 | 6.1% |
| **5×5** | (5, 8] | 543 | 3.2% | 1728 | 10.1% |
| — | ≤ 5 | 147 | 0.9% | 944 | 5.5% |

> **A6'nın en önemli tek bulgusu:** ağ girdisinde araç kutularının **%93.6'sı
> 57 px'in altında** — yani eğitim verisi, tam olarak COCO pretrained YOLOv8n'in
> A5'te çöktüğü boyut bandından oluşuyor. A5 baseline'ı bu bandı hiç görmemiş bir
> modeldi; A6'nın tabanı aşağı çekme şansı buradan geliyor. Bu bir **gerekçedir,
> garanti değildir** — 8×5 ve altında toplam 2672 örnek (ağ girdisi) var ve bu
> boyutlarda öğrenilebilir sinyal olup olmadığı ölçülmeden bilinemez.

Sınıf bazında ağ girdisindeki uzun kenar (medyan / ≤20 px oranı):
car 19.8 / %51.0 · van 19.8 / %50.8 · truck 25.1 / %38.9 · bus 20.7 / %49.8.

## 5. Truncation / occlusion (11)

Araç kutuları: kırpılma 0 → %94.2, 1 → %5.8. Örtülme 0 → %47.1, 1 (kısmi) → %44.3,
2 (ağır) → %8.6. **Kutuların yarısından fazlası en az kısmen örtülü.** Ağır örtülü
(%8.6) kutuların eğitimde tutulup tutulmayacağı bir karardır — öneri: **tutulsun**
(gerçek uçuşta örtülme var), ama değerlendirme raporunda ayrı kırılım verilsin.

## 6. Split (7, 8, 9) — YOK, kurulacak

Hazır train/val/test ayrımı **yok**; aynı görüntünün birden fazla split'te bulunması
sorusu şu an **tanımsız** (split olmadığı için). Split kurulurken iki gerçek risk var:

**(a) Aynı görüntü iki kez.** DET içinde **birebir aynı** bir çift bulundu:
`0000022_00000_d_0000004.jpg` ≡ `0000023_00000_d_0000008.jpg` (md5 aynı, farklı
videoID'ler altında). 548 dosyada 547 benzersiz hash. Bu çift **aynı split'e**
konmalı ya da biri düşülmeli.

**(b) Aynı uçuştan komşu kareler.** 548 görüntü **76 videoID grubuna** dağılıyor
(grup başına medyan 4, en büyük 35). Rastgele görüntü-bazlı split, aynı uçuşun
karelerini train ile val arasına dağıtır → val optimist çıkar. **Split grup-bazlı
(videoID'ye göre) olmalı.**

### Önerilen split

| split | grup | ~görüntü | amaç |
|---|---|---|---|
| train | ~53 videoID | ~380 | eğitim |
| val | ~11 videoID | ~84 | epoch seçimi, early stopping, mAP |
| test | ~12 videoID | ~84 | eğitim boyunca **hiç açılmaz** |

Kural: bölme `videoID` grubuna göre (`GroupKFold` mantığı), araç kutusu sayısına
göre dengelenir, sabit tohumla (`seed=0`) ve split dosyaları diske yazılır ki
tekrar üretilebilsin. **Gerçek karar ölçütü A5.2 takip benchmark'ıdır** (aşağıda);
DET test split'i yalnızca mAP izlemek içindir.

## 7. LEAKAGE KONTROLÜ (14) — sızıntı BULUNDU ve kapatılacak

Bu kontrol dosya adına güvenmeden, **hash + piksel korelasyonu** ile yapıldı.

**Adım 1 — tam hash.** 548 DET görüntüsünün md5'i, repodaki 7 VID dizisinin
**tüm 2946 karesinin** md5'i ile karşılaştırıldı: **birebir çakışma 0.**
Hash tek başına yeterli değil, çünkü DET görüntüleri 1360×768, VID kareleri
2720×1530 — aynı sahne farklı çözünürlükte hash'i tutturmaz.

**Adım 2 — dosya adı öneki.** DET adı `<videoID>_<klip>_d_<indeks>.jpg`.
76 videoID'den **ikisi** repodaki VID dizileriyle aynı: `0000117` (5 görüntü) ve
`0000086` (5 görüntü). 137, 182, 268, 305, 339 → DET'te **hiç yok**.

**Adım 3 — piksel korelasyonu** (48×48 gri imza, tam yoğunlukta, her kareye karşı):

| DET görüntüsü | en yakın VID karesi | korelasyon | hüküm |
|---|---|---|---|
| `0000117_02708_d_0000090.jpg` | `uav0000117_02622_v/0000032.jpg` | **0.9990** | **SIZINTI** |
| `0000117_03096_d_0000091.jpg` | `uav0000117_02622_v/0000226.jpg` | **0.9975** | **SIZINTI** |
| `0000086_00000_d_0000001.jpg` | `uav0000086_00000_v/0000001.jpg` | **0.9999** | **SIZINTI** |
| `0000086_00592_d_0000002.jpg` | `uav0000086_00000_v/0000297.jpg` | **0.9998** | **SIZINTI** |
| `0000117_00112/01326/01731_*` | — | 0.42 / 0.32 / 0.27 | temiz (aynı uçuş, başka klip) |
| `0000086_01084/01443/01954_*` | — | 0.41 / 0.16 / 0.29 | temiz |

**137/12 ve 305/5 temiz:** 548 DET görüntüsünün tamamına karşı en yüksek
korelasyon sırasıyla **0.5146** ve **0.5571** — sızıntı yok.

### Bu neden ciddi

`uav0000117_02622_v/0000032.jpg`, A5.2'nin ölçüm penceresinin **içindedir**
(TESPİT ilk 40 kare, TAKİP ilk 60 kare). Yani bu iki DET görüntüsü eğitime
girerse, A6 modeli A5 benchmark'ının **ölçüm karesini ezberlemiş** olur ve
"minimum güvenilir boyut düştü" sonucu geçersizleşir. Dosya adı ya da hash'e
bakarak bu yakalanamazdı.

### Zorunlu önlem (A6 eğitiminden önce uygulanacak)

**Kural: repodaki VID dizileriyle aynı videoID'ye sahip TÜM DET görüntüleri
eğitim, val ve test dışında bırakılır.** Bu, `0000117_*` (5) + `0000086_*` (5)
= **10 görüntü**, setin %1.8'i. Minimal alternatif (yalnızca 4 sızıntılı görüntüyü
atmak) yeterli görünüyor ama aynı uçuşun aynı irtifa/ışık/zemin dağılımını
taşıdığı için grup düzeyinde atmak tercih edilir; maliyeti ihmal edilebilir.

Bu önlem uygulandığında **117/23 ve 137/12 geçerli benchmark dizileri olarak kalır**
ve A5↔A6 karşılaştırması anlamlı olur. Önlem uygulanmazsa 117/23 benchmark'tan
düşürülmeli.

## 8. Sınıf dönüşümü (12, 13)

A5.1 seçicisi COCO id'leriyle filtreliyor: `COCO_ARAC = {2 car, 3 motorcycle,
5 bus, 7 truck}`, projedeki karşılığı `ARAC_SINIFLARI = (4 car, 5 van, 6 truck,
9 bus)`. Fine-tuning sonrası model **doğrudan VisDrone id'leri** üretecek, dolayısıyla:

1. **`veri/yolo_secici.py`'nin sınıf filtresi A6 modeliyle YANLIŞ olur.** COCO
   id'leri VisDrone id'leriyle çakışıyor ama başka nesneleri gösteriyor
   (COCO 5 = bus, VisDrone 5 = van). Seçiciye model-tipine göre sınıf haritası
   gerekecek. **Bu turda değiştirilmedi**; A6'nın entegrasyon adımında yapılacak.
2. **`van` COCO'da yok.** A5'te van'ları COCO `truck` soğuruyordu. A6'da van kendi
   sınıfı olacak — bu, A5↔A6 karşılaştırmasında sınıf bazında değil, **araç/araç-değil**
   düzeyinde karşılaştırma yapılmasını gerektirir.
3. **`motorcycle` tutarsızlığı:** A5.1 COCO 3 (motorcycle) filtreliyor, ama
   `ARAC_SINIFLARI` VisDrone `motor`(10) sınıfını **içermiyor**. A6'da karar netleşmeli;
   öneri: `motor` araç sayılmasın (projedeki tanımla tutarlı olsun).

**Öneri: A6 modeli 4 sınıfla eğitilsin** — car, van, truck, bus (VisDrone 4,5,6,9),
diğer 8 sınıf atılsın. Gerekçe: proje tek-araç takibi yapıyor; yaya/bisiklet
sınıflarını öğrenmek kapasiteyi (YOLOv8n, 3.2M parametre) hedeften uzağa harcar.

---

## 9. Önerilen eğitim planı (öneri; UYGULANMADI)

| konu | öneri | gerekçe |
|---|---|---|
| model | YOLOv8n, COCO pretrained'den transfer | A5 ile aynı mimari → karşılaştırma geçerli kalır; Pi Zero 2 W bütçesi |
| sınıf | 4 (car, van, truck, bus) | kapasite hedefe odaklansın |
| **katmanlar** | **tam fine-tune, düşük LR** (`freeze` yok) | küçük nesne P3 seviyesindeki **düşük seviye** özelliklere bağlıdır; backbone donarsa tam da uyarlanması gereken katmanlar donar. `freeze=10` (backbone donuk) **ablasyon kolu** olarak koşulsun, ana kol değil |
| **imgsz** | **ana kol 640** + **tanı kolu 960** | 640: A5 ile birebir karşılaştırılabilir ve dağıtım bütçesine uygun. 960: tabanın ne kadarı *veri*, ne kadarı *giriş çözünürlüğü* — bunu ayırmak A6'nın asıl sorusuna cevap verir |
| epoch | 150, `patience=30` early stop | 548 görüntü küçük; erken durdurma şart |
| batch | 16 (bellek elverirse), aksi 8 | — |
| optimizer | AdamW, `lr0=1e-3`, `lrf=0.01`, `cos_lr=True`, `warmup=3` | küçük veri + pretrained ağırlık → düşük LR |
| augmentation | `mosaic=1.0` (+`close_mosaic=10`), `scale=0.5`, `fliplr=0.5`, **`flipud=0.5`**, **`degrees=180`**, hafif HSV, `perspective=0` | nadir hava görüntüsünde **yaw serbesttir** → dikey flip ve tam rotasyon geçerli ve bedava veri. Mosaic küçük nesneyi çoğaltır. Perspektif nadir görüntüde fiziksel değil |
| değerlendirme | DET val mAP **+ A5.2 protokolünün aynısı** | mAP eğitim izleme içindir; **karar A5.2 benchmark'ınındır** |

### Şimdi söylenmesi gereken bir kısıt

**Bu makinede GPU yok** (`torch 2.13.0+cpu`, `CUDA_available=False`, i7-11800H
8 thread). YOLOv8n'i 548 görüntü × 150 epoch, imgsz=640'ta **CPU'da** eğitmek
saatler alır ve 960 kolu bunun ~2 katıdır. Bu bir engel değil ama plana girmeli:
ya süre kabul edilir, ya epoch/imgsz küçültülür, ya da bir GPU'ya erişilir.
**Ölçülmemiş süreyi tahmin olarak yazmıyorum** — ilk uygulama turunda 2 epoch'luk
bir ısınma koşumuyla gerçek epoch süresi ölçülüp plan ona göre sabitlenecek.

### Donanım kısıtları (değişmedi, korunuyor)

Raspberry Pi Zero 2 W · Raspberry Pi AI Camera (IMX500) · GEPRC TAKER F405 BLS 50A ·
iFlight XING-E Pro 2207 1800KV · 5 inch · ~750 g · Betaflight. **PX4/ArduPilot yok.**
A6 yalnızca bir `.pt` üretir; ONNX/NCNN/IMX500 dönüşümü **A6'nın kapsamında değil**.
Pi Zero 2 W ve IMX500 üzerinde **hiçbir ölçüm yok — henüz ölçülmedi.**
"Yalnızca masaüstünde çalışıyor" bir başarı sayılmayacak; bu, A6 sonrası
dağıtım turunun açık borcu olarak duruyor.

---

## 10. A6 kabul kriterleri (öneri — uygulamadan önce onaylanmalı)

Temel soru: **"fine-tuning sonrası minimum güvenilir hedef boyutu A5
baseline'ından daha küçük bir seviyeye taşındı mı?"**

- **A6-1 (sızıntı).** Eğitim/val/test'te `0000117_*` ve `0000086_*` grupları
  yok; hash + korelasyon kontrolü eğitim sonrası **tekrarlanıp** rapora eklenir.
- **A6-2 (protokol aynılığı).** Değerlendirme A5.2 protokolünün **birebir aynısı**:
  aynı tuval (640×360, letterbox 1.000), aynı kompozit yöntemi, aynı arkaplan
  ölçütü, aynı 8 seviye, aynı 2 birincil dizi, `conf=0.25`. Değişen **tek şey
  ağırlık dosyası**. Protokol değiştirilirse A5 baseline'ı yeniden koşulur.
- **A6-3 (asıl ölçüt).** A5.2'nin Y8-D kuralı **kelimesi kelimesine** uygulanır:
  her iki birincil dizide `recall@IoU≥0.5 ≥ 0.80` **ve** YOLO-tohumlu takip
  kilitleniyor **ve** drift yok. **BAŞARI = nitelenen en küçük seviye 57'den küçük.**
  57'de kalırsa A6 "başarısız" değil, **"taban düşmedi"** diye raporlanır.
- **A6-4 (gerileme yok).** 57 ve native seviyelerinde A5'e göre düşüş olmamalı.
- **A6-5 (metrik seti).** A5 ile aynı metrikler: recall · bbox IoU · confidence ·
  lock · drift · merkez hatası · PSR · FPS · latency.
- **A6-6 (maliyet).** Çıkarım gecikmesi ort/p50/p95 A5 ile aynı koşulda ölçülür;
  imgsz=960 kolu ayrı raporlanır. Pi Zero 2 W: **henüz ölçülmedi** olarak işaretlenir.
- **A6-7 (dürüstlük).** `5×5` başarısı **önceden varsayılmıyor**. Ağ girdisinde
  ≤5 px 944 örnek, (5,8] 1728 örnek var; bu bandın öğrenilebilir olup olmadığı
  ölçülmeden iddia edilmeyecek.
- **A6-8.** Commit/push yok; `takip/` md5 6/6 korunur; A5.1 seçicisi ancak
  sınıf haritası adımında ve ayrı bir turda değiştirilir.

---

## 11. Özet

- **Veri:** 548 görüntü / 548 etiket / 40 169 kutu; 17 040'ı araç (4,5,6,9).
- **Split:** yok — grup-bazlı (videoID) 380/84/84 kurulacak; 1 birebir tekrar çifti var.
- **Leakage:** **BULUNDU.** 4 DET görüntüsü repo VID dizileriyle r≥0.997; ikisi
  A5'in birincil dizisi 117/23'ün **ölçüm penceresinde**. Hash yakalamıyor.
  Önlem: `0000117_*` ve `0000086_*` gruplarını (10 görüntü) tamamen dışarıda bırak.
  137/12 ve 305/5 **temiz** (max r 0.51 / 0.56).
- **Küçük hedef:** ağ girdisinde araç kutularının **%93.6'sı ≤57 px**, medyan
  **19.8 px** — eğitim verisi tam da A5'in çöktüğü banttan oluşuyor.
- **Eğitim:** YOLOv8n, 4 sınıf, tam fine-tune + düşük LR, imgsz 640 (ana) / 960 (tanı),
  nadir-uyumlu augmentation, 150 epoch + early stop. GPU yok — süre ilk turda ölçülecek.
- **Karar ölçütü:** A5.2'nin Y8-D kuralı, değişen tek şey ağırlık dosyası.
