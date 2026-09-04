# A5 — Donanım / inference mimarisi karşılaştırması

**Karar belgesidir. Kod yazılmadı, model eğitilmedi, deney koşulmadı,
commit/push yok.** `takip/` md5 6/6; A3.9 checkpoint ve A3.10/A4
değişiklikleri korundu.

> **Sayı disiplini:** aşağıda **ÖLÇÜLDÜ**, **BÜYÜKLÜK MERTEBESİ TAHMİNİ**
> (aritmetiği gösterilmiş, ölçüm değil) ve **ÖLÇÜLMEDİ** etiketleri
> birbirinden ayrı tutulmuştur. Hiçbir FPS/latency değeri ölçülmüş gibi
> yazılmamıştır.

---

## 0. Elimizdeki ölçülmüş taban

| büyüklük | değer | kaynak |
|---|---|---|
| Klasik hat, 640×480 (masaüstü i7-11800H) | **FPS 309.9**, gecikme ort **3.23 ms**, p50 2.54, p95 5.33 | bu oturum, Gazebo G6 |
| Klasik hat, 960×540 (VisDrone) | FPS ~271–395 | bu oturum |
| Pi Zero 2 W klasik hat | **~28 FPS (×12)** — `README:405-407`: *"ekstrapolasyondur, cihazda ölçüm yapılmamıştır"* | **ÖLÇÜLMEDİ** |
| Buradan çıkan kare bütçesi | **~36 ms/kare** (28 FPS) — ve bunun **tamamı** klasik takipçiye ait | türetilmiş |

**Sonuç:** detector'ün *her karede* çalışması için ayrılabilecek bütçe
**pratikte sıfırdır**. Bu, üç seçeneği de baştan "seyrek detection" hattına
zorlar.

## 0b. Donanım künyesi (resmî özellikler)

| | |
|---|---|
| **Pi Zero 2 W** | Broadcom BCM2710A1, **4× Cortex-A53 @ 1 GHz** (64-bit), **512 MB LPDDR2**, CSI-2 (mini konnektör), 802.11n |
| **Pi AI Camera** | **Sony IMX500** — 12.3 MP sensör + **sensör üstü** hızlandırıcı; model sensöre yüklenir, çıkarım orada yapılır, sonuç CSI metadata olarak gelir. Model **Sony toolchain**'inden geçip (`imx500-converter` → `.rpk`) quantize edilmeli; **desteklenen operatör kümesi ve sensör üstü bellek sınırlı** |
| FC / motor / gövde | GEPRC TAKER F405 BLS 50A · XING-E Pro 2207 1800KV · 5 inch · ~750 g · **Betaflight**, PX4/ArduPilot yok |

---

## 1. Üç seçeneğin karşılaştırması

### Seçenek 1 — Pi Zero 2 W CPU'da YOLOv8n (PyTorch)

| eksen | değerlendirme |
|---|---|
| **RAM** | **YÜKSEK RİSK.** Toplam 512 MB. PyTorch runtime tek başına ~200–300 MB yerleşik; üstüne model, görüntü tamponu ve mevcut klasik hat. **Ölçülmedi**, ama sınırda olduğu açık |
| **CPU yükü** | YOLOv8n @640 ≈ **8.7 GFLOPs/kare**. 4× A53 @1 GHz için NEON ile iyimser sürdürülebilir ~1–2 GFLOPS ⇒ **kare başına saniyeler mertebesi**. @320 (~2.2 GFLOPs) bile ≫ 36 ms bütçe. *(BÜYÜKLÜK MERTEBESİ TAHMİNİ — ölçüm değil)* |
| **FPS** | **ÖLÇÜLMEDİ.** Yukarıdaki aritmetiğe göre <1 FPS beklenir |
| **Latency** | **ÖLÇÜLMEDİ**; kare başına saniye mertebesi beklenir |
| **Enerji / ısı** | Sürekli 4 çekirdek doygunluğu → termal throttling riski; Zero 2 W'de soğutucu yok. **Ölçülmedi** |
| **Entegrasyon** | **En kolay** — ultralytics zaten kurulu (`8.4.104`, `torch 2.13.0+cpu`), masaüstünde bugün çalıştırılabilir |
| **Küçük hedef** | **En esnek** — ROI kırpıp **tam çözünürlükte** çıkarım yapılabilir (aşağıda §2) |
| **Drone'a taşınabilirlik** | **DÜŞÜK.** Masaüstü prototipi için iyi, uçuşta gerçek zamanlı değil |

### Seçenek 2 — Pi Zero 2 W + hafif runtime (ONNX Runtime / NCNN, int8)

| eksen | değerlendirme |
|---|---|
| **RAM** | Seçenek 1'den **belirgin iyi** — runtime birkaç on MB; int8 model ~3–6 MB. **Ölçülmedi** |
| **CPU yükü** | int8 + NEON ile 2–4× hızlanma tipik; ama **FLOP tabanı aynı** → @320 girişte bile kare başına **yüzlerce ms** beklenir. *(BÜYÜKLÜK MERTEBESİ TAHMİNİ)* |
| **FPS** | **ÖLÇÜLMEDİ.** Belki 1–3 FPS mertebesi; **seyrek** kullanım için yeterli olabilir |
| **Latency** | **ÖLÇÜLMEDİ** |
| **Enerji / ısı** | Seçenek 1'den iyi; yine de çıkarım anında 4 çekirdek doluyor. **Ölçülmedi** |
| **Entegrasyon** | **ORTA** — `onnxruntime`/`ncnn` **kurulu değil**; export + quantize + doğrulama adımı gerekir. Buna karşılık **masaüstünde de aynı runtime** kullanılabilir → *bir kod, iki platform* |
| **Küçük hedef** | **Esnek** — Seçenek 1 gibi ROI kırpma mümkün |
| **Drone'a taşınabilirlik** | **ORTA-İYİ.** Seyrek detection hattı için gerçekçi tek CPU seçeneği |

### Seçenek 3 — Sony IMX500 (Pi AI Camera) üzerinde çıkarım

| eksen | değerlendirme |
|---|---|
| **RAM** | **EN İYİ.** Ağırlıklar sensörde; Pi RAM'i yalnızca sonuç metadata'sını taşır. 512 MB baskısı **büyük ölçüde kalkar** |
| **CPU yükü** | **~0** — Pi CPU'su çıkarım yapmaz, yalnızca kutuları okur. **Bu, karşılaştırmanın en güçlü tek argümanıdır** |
| **FPS** | **ÖLÇÜLMEDİ.** Sensör üstü hattın kendi kare hızı vardır; Pi tarafında ek yük olmadığı için klasik takipçinin 36 ms bütçesi **korunur** |
| **Latency** | **ÖLÇÜLMEDİ.** Sensör→metadata gecikmesi bu projede hiç ölçülmedi (`KALICI_KISITLAR.md` §2b: kamera gecikmesi ölçülmedi) |
| **Enerji / ısı** | **EN İYİ** — CPU boşta; hızlandırıcı sensör tarafında ve düşük güçlü |
| **Entegrasyon** | **EN ZOR.** Sony toolchain'i (quantize + `.rpk` paketleme), sınırlı operatör kümesi, `picamera2`/`rpicam` yazılım yığını, **model sensöre sığmalı**. Ayrıca AI Camera'nın **Zero 2 W üzerindeki uyumluluğu ve mini-CSI kablosu bu projede DOĞRULANMADI** |
| **Küçük hedef** | **EN KISITLI — belirleyici sorun.** Bkz. §2 |
| **Drone'a taşınabilirlik** | **EN İYİ** — güç ve CPU bütçesi açısından uçuşa uygun tek seçenek |

---

## 2. Küçük hedef ekseni — mimariyi belirleyen çelişki

Projenin kalıcı hedefi: **hedef küçüldükçe takip sürekliliği**
(57×21 → 40×15 → 30×12 → 20×10 → 15×7 → 10×5 → 8×5 → 5×5).

Ölçülmüş bağlam: VisDrone dizileri **2720×1530 / 3840×2160** ham çözünürlükten
**960×540**'a indiriliyor (`DENEY_04I` §1) ve 268/31'in hedefi bu ölçekte
**15×7 px**'e düşüyor. Yani **ölçek indirimi küçük hedefi doğrudan yok ediyor.**

| yaklaşım | küçük hedef üzerindeki etkisi |
|---|---|
| **CPU (Seçenek 1/2)** | Kare tam çözünürlükte elde; **takip kutusunun etrafından ROI kırpıp** dedektöre *native* piksellerle verilebilir. 5×5'lik bir hedef, 128×128'lik bir kırpıtta ağın giriş çözünürlüğünde **büyütülmüş** olarak görünür. Küçük hedef için **en güçlü kaldıraç budur** |
| **IMX500 (Seçenek 3)** | Çıkarım **sensörde**, sabit ağ girişine **tüm kare ölçeklenerek** verilir. 12 MP → ağ girişi indirimi, 5×5'lik hedefi **alt-piksel** düzeyine indirir. ROI kırpma sensör üstü hatta **serbestçe yapılamaz** |

> **Bu, kararın gövdesidir:** IMX500 *maliyet* ekseninde açık ara kazanıyor,
> ama *küçük hedef* ekseninde CPU tarafının en güçlü tekniğini (ROI kırpma)
> elimizden alıyor. İkisi aynı anda seçilemez — **ama sıralanabilir.**

---

## 3. "Pi CPU mu, IMX500 mü?" — doğrudan cevap

> **Gerçek drone üzerinde nihai hedef IMX500'dür; ama A5'te ona gidilmez.**

Gerekçe üç maddede:

1. **Uçuşta CPU'ya çıkarım vermek aritmetik olarak kapalıdır.** Klasik
   takipçinin Pi bütçesi ~36 ms/kare (ve o bile **ekstrapolasyon**); YOLOv8n'in
   FLOP tabanı bu bütçenin **iki mertebe** üstünde. IMX500'ün CPU yükünü
   **~0**'a indirmesi, uçuşta gerçek zamanlılığı mümkün kılan tek yapısal
   çözümdür.
2. **Ama IMX500 bugün bir karar veremez.** Model dönüşüm hattı, operatör
   kısıtları, sensör üstü bellek, **Zero 2 W uyumluluğu** ve **kamera
   gecikmesi** — hiçbiri bu projede ölçülmedi. Ölçülmemiş bir platformun
   üstüne A5'in *ilk* uygulamasını kurmak, Faz C'de beş kez düşülen
   "doğrulanmamış zemine inşa" hatasının tekrarı olur.
3. **Küçük hedef hedefi, karar sırasını tersine çevirir.** Önce COCO
   ön-eğitimli bir modelin **hangi hedef boyutunda recall'ünü kaybettiğini**
   bilmek gerekir. Bu sayı olmadan ne A6'nın (fine-tuning) kazancı ölçülebilir
   ne de IMX500'ün ölçek indiriminin ne kadar zarar verdiği. Bu ölçüm
   **masaüstünde, tam çözünürlükte** yapılır.

**Seçenek 1 tek başına bir hedef değildir**, ama **Seçenek 2'ye giden yolun
ilk adımıdır**: aynı model, aynı ön-işleme, önce PyTorch/CPU'da doğrulanır,
sonra ONNX'e export edilip *aynı sonuçları verdiği* gösterilir, ancak ondan
sonra Pi'ye ve IMX500'e taşınır.

---

## 4. Mimari — detector ile tracker'ın ayrı kalması

```
FRAME ──► DETECTOR ──► BBOX ──► TRACKER ──► RECOVERY
             │                     ▲
             └── (seyrek: yalnızca kilit anı + kayıp anı) ──┘
```

Bu ayrım **bugün zaten mimaride var** ve A5'te korunacak:

* Detector, `hedef_secici(adaylar, kare) -> {kutu, merkez, alan} | None`
  sözleşmesinin **üçüncü uygulaması** olur (birincisi `otomatik_hedef_sec`,
  ikincisi A4'ün `fare_hedef_sec`'i).
* `main.kos()` gövdesi **değişmez** — A4'te AST karşılaştırmasıyla kanıtlandı.
* `takip/` detector'ü **bilmez**; yalnızca `bgr` ndarray alır.
* Böylece detector'ün *nerede koştuğu* (masaüstü CPU / Pi CPU / IMX500)
  tracker'ı **hiç ilgilendirmez**. Runtime değişimi tek dosyada kalır.

---

# SONUÇ

### Önerilen mimari

> **Nihai hedef: IMX500 (Seçenek 3) — sensör üstü çıkarım, Pi CPU ~0.**
> **A5'in yolu: Seçenek 1 → Seçenek 2 → Seçenek 3, bu sırayla.**
> **A5'in ilk modeli: YOLOv8n, COCO ön-eğitimli, CPU'da, fine-tuning'siz.**

### Neden

* IMX500 uçuşta gerçek zamanlılığı mümkün kılan **tek** yapısal çözüm (CPU
  yükü ~0, RAM baskısı yok, ısı yok) — ama **hiçbir kalemi ölçülmedi** ve
  ROI kırpmayı engelleyerek **küçük hedef hedefine karşı** çalışıyor.
* Pi CPU'da PyTorch (Seçenek 1) uçuş için **kapalı**, ama masaüstünde
  **bugün çalışır** ve taban ölçümünü verir.
* ONNX/NCNN (Seçenek 2) **köprüdür**: aynı model, iki platform, ve IMX500
  dönüşümünün de girdisi zaten bir ONNX grafiğidir.
* Sıralama tersine çevrilirse, elimizde bir **taban** olmadan IMX500'ün
  ölçek indiriminin küçük hedefe verdiği zarar ölçülemez.

### A5'in ilk uygulaması (henüz yapılmadı)

| | |
|---|---|
| dosya | **`veri/yolo_secici.py`** (yeni) |
| fonksiyon | `yolo_hedef_sec(...) -> secici` — `hedef_secici` sözleşmesini uygular |
| model | **YOLOv8n, COCO ön-eğitimli**, `torch 2.13.0+cpu` + `ultralytics 8.4.104` (**ikisi de kurulu**) |
| sınıf süzgeci | COCO `car/motorcycle/bus/truck` → repo `ARAC_SINIFLARI` karşılığı |
| bbox dönüşümü | `xyxy` → `(x,y,w,h)` + **A4'teki 2 px ön-telafi** (`kos():382-384` sadeleşsin diye) |
| ROI kırpma | **A5'te uygulanmaz**; §2'deki kaldıraç olarak *kaydedilir*, tam kare ölçümü taban olsun diye |
| ek diff | `main.py` +3 satır (`--yolo` bayrağı + seçici dalı) · `requirements.txt`'e **ayrı "opsiyonel A5"** bölümü |
| dokunulmaz | `takip/` (6 dosya), `kos()` gövdesi, `fare_hedef_sec`, `sim/`, `veri/sim_kayit.py`, `gazebo/`, `visdrone_det` (A6'nın seti) |
| ölçüm | 8 boyut basamağında **recall · bbox IoU · confidence · lock · drift · merkez hatası · PSR · FPS · latency**; kaynak: A3.10 irtifa rampası kalıbı (`test3`, deterministik, kusursuz GT) + 117/23, 137/12 |
| maliyet raporu | masaüstü ms/kare **ölçülecek**; Pi Zero 2 W ve IMX500 kalemleri **"ÖLÇÜLMEDİ"** olarak işaretlenecek |

### A6'ya geçiş yolu

1. **A5 kapanışı**: taban tablosu hazır — COCO modelinin **hangi hedef
   boyutunda recall'ü çöktüğü** ölçülmüş olacak. Bu sayı A6'nın varlık
   gerekçesidir.
2. **A6 (VisDrone fine-tuning, `visdrone_det` 548 görüntü)**: aynı boyut
   basamaklarında **aynı tablo** yeniden üretilir; kabul ölçütü *"fine-tuning,
   recall'ün çöktüğü boyutu kaç basamak aşağı taşıdı?"* olur.
3. **A6 sonrası, ayrı bir tur olarak**: seçilen model ONNX'e export edilir ve
   **masaüstünde PyTorch ile bit-benzeri sonuç verdiği** gösterilir
   (Seçenek 2'ye köprü). Ancak bundan sonra Pi ve IMX500 ölçümleri gündeme
   gelir — ve o ölçümler **A11'in** (Raspberry Pi optimizasyonu) kapsamıdır,
   A5/A6'nın değil.

**Bu belgede kod, model eğitimi, deney ve commit/push yoktur.**
