# A5 — YOLOv8n (COCO) hedef seçicisinin entegrasyonu

**Tarih:** 2026-08-30
**Kapsam:** Y1–Y7. **Y8 (küçük hedef benchmark'ı) bu turda YAPILMADI** — ayrı tur.
**Commit / push:** YAPILMADI.
**Veri:** `cikti/a5_yolo_integration.json`

---

## 0. Ne yapıldı, ne yapılmadı

Yapıldı: YOLOv8n + COCO pretrained dedektör, mevcut `hedef_secici` sözleşmesinin
**üçüncü** uygulaması olarak bağlandı. Takipçi çekirdeği bu turda hiç değişmedi.

Yapılmadı (kasıtlı, A5 kapsam dışı): MOT/ByteTrack/BoT-SORT · fine-tuning ·
Optuna · IMX500 · ONNX/NCNN · ROI kırpma · `visdrone_det` kullanımı (A6'ya ayrıldı) ·
Y8 küçük hedef benchmark'ı.

Mimari yerleşim — dedektörün **nerede** koştuğu takipçiyi ilgilendirmez:

```
KAMERA → FRAME → [DEDEKTÖR | KULLANICI SEÇİMİ] → TAKİPÇİ → KURTARMA → ÇIKTI
                   A5 burada       A4 burada
```

`veri/yolo_secici.py` `takip/` altından **hiçbir şey import etmez**.

---

## 1. Y1 — Sözleşme uyumu · GEÇTİ

`veri/yolo_secici.py` (126 satır), `yolo_hedef_sec(...) -> secici(adaylar, kare)`.

| Konu | Karar |
|---|---|
| Sınıflar | COCO 2 car · 3 motorcycle · 5 bus · 7 truck |
| Reddedilen | `w<=0`, `h<=0`, `min_kenar` (4.0) altı, kadraj dışı, NaN/±inf |
| Dönen | `{"kutu", "merkez", "alan"}` (+ tanı için `guven`, `sinif`) |
| Ağırlık | **sessizce indirilmez** — dosya yoksa `YoloHatasi` |

**Birim testi: 11/11 geçti.** İlk turda NaN vakası kaldı ve düzeltildi: `x1 <= x2`
karşılaştırması NaN'da `False` döndüğü için köşeler ters sıralanıyor, ardından
`min(640, nan)` sessizce `640` veriyor ve **geçersiz kutu geçerli görünüyordu.**
Sonlu-luk kontrolü sıralamadan **önce**ye alındı.

**2 px ön-telafi (A4 ile aynı kural).** `kos()` satır 491–492 hareket lekesi için
`kutu[2:] = max(kutu[2:] - 2, 4)` uygular. Dedektör kutusu dilate edilmiş değildir,
bu yüzden seçici kutuyu 2 px **büyük** döndürür ve telafi sadeleşir:

```
YOLO xyxy [100,100,157,121] → seçici [99,99,59,23] → kos() sonrası [100,100,57,21] = gerçek ✔
```

`kos()` gövdesine dokunulmadı.

## 2. Y2 — `main.py` entegrasyonu · GEÇTİ

Eklenen: `--yolo AĞIRLIK`, `--yolo-conf` (vars. 0.25), `--yolo-gt-esle`.
Öncelik: `--sec` > `--yolo` > `otomatik_hedef_sec` (ikisi birlikte verilirse uyarı basılır).

| Fonksiyon | AST md5 önce → sonra |
|---|---|
| `kos` | `6c39bda7` → `6c39bda7` **AYNI** |
| `fare_hedef_sec` | `21bfd408` → `21bfd408` AYNI |
| `otomatik_hedef_sec` | `6631b0e6` → `6631b0e6` AYNI |
| `_roi_aday` | `2def3919` → `2def3919` AYNI |
| `main` | `ea8b072d` → `0795de69` — **tek değişen fonksiyon** |

## 3. Y3 — `takip/` dokunulmadı · GEÇTİ

6/6 md5 Deney 2 tabanıyla aynı (`__init__` d41d8cd9 · `cekirdekler` c0fd7989 ·
`egomotion` 959da09a · `izleyici` 4257b94c · `mosse` 874b3ccd · `tespit` 3ff48dd8).

## 4. Y4 — `--yolo` verilmediğinde regresyon · GEÇTİ

A5 **öncesi** `main.py` yedeği ile A5 **sonrası** `main.py`, aynı 11 koşumda
çalıştırılıp çıktıları diff'lendi (FPS/gecikme satırları hariç — makine gürültüsü):

`sim:test1..test7` · `sim:hizli_hedef` · `sim:duran_hedef` ·
`visdrone 117/23 (120 kare)` · `visdrone 137/12 (120 kare)`

→ **11/11 bit-birebir aynı** (çıktı md5 `359bbd31…`). `--sec` yolu da AST olarak
aynı ve dallanması doğrulandı.

## 5. Y5 — Temiz hata · GEÇTİ

```
$ main.py … --yolo weights/yok.pt
HATA: YOLO agirligi bulunamadi: 'weights/yok.pt'
       Agirlik SESSIZCE INDIRILMEZ. Once indirin, ornegin: …          → çıkış 1

$ main.py … --yolo /tmp/bozuk.pt
HATA: model yuklenemedi (/tmp/bozuk.pt): invalid load key, '\x1b'.     → çıkış 1
```

Traceback yok. Sessiz indirme yok — `os.path.exists()`, ultralytics'in kendi
otomatik indirmesinden **önce** kontrol eder. `weights/` `.gitignore`'a eklendi.

## 6. Y6 — Çıkarım maliyeti · GEÇTİ (masaüstü)

Masaüstü CPU (i7-11800H, 8 iş parçacığı, `torch 2.13.0+cpu`, **CUDA yok**), imgsz=640,
ilk çağrı (ısınma) atıldı, 39 çağrı:

| Kaynak | ort | p50 | p95 | max | eşdeğer FPS |
|---|---|---|---|---|---|
| sim 640×480 | 36.95 ms | 37.17 | 38.97 | 40.32 | 27.1 |
| VisDrone 1904×1071 | 32.63 ms | 32.61 | 34.86 | 37.01 | 30.6 |
| VisDrone 2720×1530 | 30.14 ms | 30.74 | 35.07 | 36.23 | 33.2 |

Süre çözünürlükten bağımsız — her kare 640'a letterbox edilir.

**Kritik gözlem — bu maliyet kare başına DEĞİLDİR.** `kos()` seçiciyi yalnızca
`not kilitli` iken çağırır (satır 486–489); kilit sonrası YOLO hiç koşmaz. Ölçülen:

| Dizi | 120 karede seçici çağrısı |
|---|---|
| 117/23 | **1** |
| 137/12 | **1** |
| 305/5 | 112 (111'i örtüşme reddi — dedektör hedefi ~111 kare boyunca hiç göremedi) |

> **Raspberry Pi Zero 2 W üzerinde HENÜZ ÖLÇÜLMEDİ. IMX500 HENÜZ ÖLÇÜLMEDİ.**
> Masaüstü sayıları Pi'ye taşınamaz; A5 bu yüzden "başarılı" ilan edilmiş sayılmaz.

## 7. Y7 — Çıktılar · GEÇTİ

`docs/architecture/A5_YOLO_INTEGRATION.md` · `cikti/a5_yolo_integration.json` ·
`requirements.txt` opsiyonel A5 bölümü · `.gitignore` `weights/`.

---

## 8. İşlevsel sonuç (gerçek görüntü, 80 karelik aynı pencere, aynı takipçi)

Fark **yalnızca** kilit anındaki kutuyu kimin verdiğidir.

| Dizi | otomatik (taban) | `--yolo` saf | `--yolo --yolo-gt-esle` |
|---|---|---|---|
| 117/23 | IoU 0.706 / 6.6 px | **IoU 0.000 / 775 px** | IoU **0.761** / 10.6 px |
| 137/12 | IoU 0.608 / 18.3 px | — | IoU 0.608 / 19.0 px |
| 305/5 | IoU 0.728 / 12.2 px | — | **kilit YOK** |

Sim senaryolarında (`test1`, `hizli_hedef`) YOLO **hiç kilitlenmedi**: prosedürel
sim yapay dikdörtgen çiziyor, COCO YOLOv8n bunları araç olarak tanımıyor. Bu bir
entegrasyon hatası değil, alan uyuşmazlığıdır — ve YOLO yolunun sim üzerinde
ölçülemeyeceğini gösterir.

### 8.1 Saf dedektör tek nesne takibinde hedefi seçemez

`--yolo` tek başına **en yüksek güvenli** aracı seçer. 117/23'te bu, hedeften
775 px uzaktaki başka bir araçtır. Bu bir kusur değil, tanım gereğidir: dedektör
"hangi araç" sorusunu yanıtlamaz. Gerçek dronede bu soruyu **A4 (kullanıcı ROI)**
yanıtlar; `--yolo-gt-esle` yalnızca **ölçüm** içindir (gerekçesi `gt_hedef_sec`
ile aynı).

### 8.2 `gt_esle`'ye örtüşme şartı eklendi — kapalı döngü tuzağı

İlk uygulama GT'ye **en yakın** tespiti seçiyordu. 305/5'te dedektör hedefi hiç
bulamayınca "en yakın" 535 px uzaktaki başka bir araç oldu ve takipçi
**sessizce yanlış nesneye kilitlendi** (IoU 0.000 ama `kilit oranı %100`).

Bu, Faz C boyunca beş kez görülen kalıbın aynısıdır: **bir ölçüm yardımcısının,
cevabı bilmediğinde makul görünen bir cevap uydurması.** Düzeltme, uydurulmuş bir
eşik değil, "aynı nesne" tanımının kendisidir: aday GT kutusuyla **örtüşmüyorsa**
(IoU > 0 değilse) seçici `None` döner.

Sonuç: 305/5 artık dürüstçe **kilitlenmiyor** — YOLOv8n@640, 1904×1071 karedeki
46×93 px hedefi 80 kare boyunca gerçekten hiç tespit etmiyor (tüm karede yalnızca
3 araç buluyor, en yakını 568 px uzakta).

---

## 9. Açık borçlar

1. **P0.1 — bağımsız mutlak boyut ölçümü. A5 bunu ÇÖZMEZ.** YOLO yalnızca kilit
   anında koşar; kilit sonrası kutu boyutu yine `_boyut_tazele` / `rafine_kutu`'ya
   bırakılır. Kilit sonrası dedektör beslemesi A5 kapsamında değildir.
2. **YOLOv8n@640 küçük hedef geri çağırması.** 8.2'deki 46×93 px kaçırması, Y8
   benchmark'ının ölçeceği şeyin ta kendisidir ve A6'nın (ROI kırpma / girdi
   çözünürlüğü) gerekçesidir.
3. **Raspberry Pi Zero 2 W üzerinde hiçbir ölçüm yok.**
4. ONNX / NCNN / IMX500 yolları açılmadı (A6).

---

## 10. Hüküm

**A5 YOLO ENTEGRASYONU TAMAMLANDI** — Y1–Y7: 7/7.

Sınırı açıkça: bağlantı ve sözleşme uyumu kanıtlandı; dedektörün küçük hedefteki
**yeteneği** kanıtlanmadı (Y8) ve **hedef donanımdaki maliyeti** ölçülmedi.
