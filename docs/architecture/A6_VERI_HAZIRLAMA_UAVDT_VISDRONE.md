# A6 — Veri hazırlama: UAVDT ön-eğitim + VisDrone fine-tuning

**Tarih:** 2026-08-31 · **Bu tur:** yalnızca veri hazırlama.
**Yapılmadı:** model eğitimi · train başlatma · ONNX/NCNN/IMX500 · Optuna · commit/push.

**Üretici:** `veri/a6_hazirla.py` (278→305 satır) · **Doğrulayıcı:** `veri/a6_dogrula.py`
**Manifest:** `data/a6/manifest/a6_hazirlik.json` · `data/a6/manifest/a6_dogrulama.json`

---

## 1. Exact kaynaklar (salt okunur)

| kaynak | yol | durum |
|---|---|---|
| UAVDT | `/mnt/c/Users/Casper/Downloads/uavdt-DatasetNinja.tar` | **13 993 973 760 bayt**, yalnızca `tarfile "r|"` akış modunda okundu |
| VisDrone DET | `data/datasets/visdrone_det/` | 548 görüntü + 548 etiket, yalnızca okundu |

Hiçbir kaynak dosya taşınmadı, silinmedi, üzerine yazılmadı. Tar hiç açılmadı
(diske çıkarılmadı); gereken kareler akıştan okunup **yeni** bir çalışma alanına
yazıldı.

## 2. Üretilen veri setleri

```
data/a6/
├── uavdt_pretrain/      images/{train,val,test}/  labels/{train,val,test}/  data.yaml
├── visdrone_finetune/   images/{train,val,test}/  labels/{train,val,test}/  data.yaml
└── manifest/            a6_hazirlik.json  a6_dogrulama.json
```

`data/a6/` `.gitignore`'a eklendi (görüntüler depoya girmez); `manifest/` istisna
tutuldu. Boyut: UAVDT 1.4 GB, VisDrone 80 MB.

### Aşama A — UAVDT ön-eğitim

- Yalnızca **M alt kümesi** (`M####_img######.jpg`). **S alt kümesi ilk turda
  dışarıda** — jenerik `vehicle` etiketi ve kare başına tek kutu.
- Seyreltme kuralı: `(kare_indeksi − 1) % 5 == 0` → 1, 6, 11, … kareler.
- **50 dizi · 8 165 görüntü · 160 080 kutu** (beklenen ~8 147 / ~159 800).
- Sınıf: **tek sınıf `0 = vehicle`**. Kaynak dağılımı car 151 432 + truck 5 033 +
  bus 3 615 = 160 080. **Atlanan kutu 0** → M alt kümesinde hiç `vehicle`-sınıfı
  kutu yok, yani S gerçekten tamamen dışarıda.

### Aşama B — VisDrone fine-tuning

- **10 görüntü tamamen dışarıda** (A5 sızıntısı, A6 planında kanıtlanmıştı):
  `0000117_*` (5) ve `0000086_*` (5).
- **538 görüntü · 16 963 kutu** (tam VisDrone DET araç sayısı 17 040; fark 77 kutu
  atılan 10 görüntüden geliyor).
- Sınıf: **0 car · 1 van · 2 truck · 3 bus**.

## 3. Split kararı

**Aşama A — dizi (sequence) bazlı, 70/15/15, ağırlık = seçilen kare sayısı.**
Belirlenimci greedy: diziler ağırlığa göre azalan sırada gezilir, her dizi o an
hedef payının en altında kalan bölüme verilir. Rastgelelik ve tohum yok.

| | train | val | test |
|---|---|---|---|
| görüntü | **5 722** | **1 222** | **1 221** |
| kutu | 111 771 (%69.8) | 22 001 (%13.7) | 26 308 (%16.4) |

> UAVDT'nin kendi train/test ayrımı **korunmadı**; 50 M dizisinin tamamı havuza
> alınıp yeniden bölündü. Gerekçe: A6'nın gerçek karar ölçütü VisDrone VID
> benchmark'ıdır (117/23, 137/12) ve UAVDT'nin ondan bağımsız olduğu doğrulandı;
> UAVDT'nin kendi test rezervi bize bir şey kazandırmaz, fazladan ön-eğitim
> dizisi kazandırır.

**Aşama B — videoID grubu bazlı, 70/15/15, ağırlık = araç kutusu sayısı.**

| | train | val | test |
|---|---|---|---|
| görüntü | **331** | **111** | **96** |
| kutu | 11 874 (%70.0) | 2 545 (%15.0) | 2 544 (%15.0) |

**Test split'i eğitim sırasında açılmayacak.** `data.yaml`'da `test:` ayrı bir yol
olarak tanımlı; ultralytics `train` komutu yalnızca `train`/`val` kullanır.

### Split kurulurken bulunan ve düzeltilen gerçek hata

İlk üretimde VisDrone'un **birebir aynı** iki görüntüsü
(`0000022_00000_d_0000004.jpg` ≡ `0000023_00000_d_0000008.jpg`, md5 aynı) **farklı
videoID'ler taşıdığı için train ile test'e dağılmıştı** — tam anlamıyla train/test
sızıntısı. Yalnızca videoID'ye bakan bir grup ölçütü bunu yakalayamaz.

Düzeltme: split'ten önce aynı md5'i paylaşan videoID'ler **birleştiriliyor**
(union-find), sonra grup ataması yapılıyor. Sonuç: çiftin ikisi de **train**'de;
manifest'te `hash_ile_birlestirilen_gruplar: [["0000022","0000023"]]`.
Bu yüzden Aşama B split sayıları 327/111/100 → **331/111/96** olarak değişti.

## 4. Annotation dönüşümü ve sınıf eşlemesi

**UAVDT Supervisely JSON → YOLO.** `points.exterior` = `[[x1,y1],[x2,y2]]`
→ sol-üst köşe + genişlik/yükseklik → kadraja kırpma → normalize
`cls cx cy w h` (6 ondalık).

**Sınıf eşlemeleri — A5'in COCO haritası A6'ya TAŞINMADI:**

| | eşleme | doğrulama |
|---|---|---|
| Aşama A | car, truck, bus → **`0` vehicle** | yazılan tüm etiketlerde sınıf kimliği kümesi `{0}`, 160 080 kutu |
| Aşama B | VisDrone `4 car→0`, `5 van→1`, `6 truck→2`, `9 bus→3` | 538 etiket dosyası kaynaktan **bağımsız yeniden türetilip** karşılaştırıldı: **uyuşmayan 0**; car 13 997 · van 1 968 · truck 747 · bus 251 — hepsi birebir |

`veri/a6_hazirla.py` içinde COCO kimliği (2,3,5,7) **hiç geçmiyor**.
`veri/yolo_secici.py` (A5.1) **değiştirilmedi** — md5 `c8cdb6b4…`, A5.1 kaydıyla
aynı. Seçicinin sınıf filtresi A6 modeliyle uyumsuz kalmaya devam ediyor; bu
**bilinen ve ayrı bir turda** yapılacak entegrasyon işi.

**Round-trip kontrolü** (yazılan normalize değer geri çözülüp kaynak kutuyla
karşılaştırıldı): Aşama A 160 080 kutu, **max hata 0.000768 px**;
Aşama B 16 963 kutu, **max hata 0.001280 px**. İkisi de 6 ondalık normalizasyonun
niceleme sınırında; 1 px'in çok altında.

## 5. Leakage sonuçları

Üretilen **8 703 A6 görüntüsünün tamamı**, A5 benchmark dizilerinin
**582 karesinin tamamına** karşı üç yöntemle sınandı (örnekleme yok):

| yöntem | sonuç |
|---|---|
| exact hash (md5) | **0 çakışma** |
| dosya adı | **0 çakışma** |
| videoID | **0 çakışma** (`0000117`, `0000086`, `uav0000117`, `uav0000137` A6'da yok) |
| piksel korelasyonu (48×48 gri imza) | **en yüksek 0.6603**; r>0.95: **0**, r>0.80: **0** |

En yakın çift: `M1008_img000566.jpg` ↔ `uav0000117_02622_v/0000146.jpg`, r = 0.6603.
Kıyas ölçeği: aynı yöntem VisDrone DET'teki gerçek sızıntıyı **0.9990**'da
yakalamıştı. 0.66 "aynı görüntü" bandının çok uzağında.

**Hüküm: A6 eğitim verisi ile A5 benchmark dizileri (117/23, 137/12) arasında
sızıntı YOK.**

A6 havuzu içinde 1 birebir tekrar var (yukarıdaki VisDrone çifti) — artık **ikisi de
train**'de, split'ler arasında değil.

## 6. Küçük hedef envanteri

Ağ girdisi = native uzun kenar × letterbox çarpanı (imgsz 640).
Medyan: UAVDT **21.88 px**, VisDrone **19.76 px**. ≤57 px oranı: %96.13 / %93.63.

| A5 seviyesi | **UAVDT ön-eğitim** | **VisDrone fine-tune** | oran |
|---|---|---|---|
| 57×21 (>57) | 6 191 | 1 080 | 5.7× |
| 40×15 | 9 985 | 1 688 | 5.9× |
| 30×12 | 24 777 | 2 075 | 11.9× |
| **20×10** | **45 785** | 3 562 | 12.9× |
| **15×7** | **26 947** | 2 454 | 11.0× |
| **10×5** | **30 034** | 2 427 | **12.4×** |
| **8×5** | **12 497** | 1 005 | **12.4×** |
| 5×5 | 3 864 | 1 729 | 2.2× |
| ≤5 px | **0** | 943 | — |
| **toplam** | **160 080** | **16 963** | 9.4× |

**UAVDT'nin arzı — sorulan üç kalem:**
- **≤20 px bandı** (15×7 ve altı): **73 342** kutu (VisDrone'da 8 558) → **8.6×**
- **10×5**: **30 034** kutu → 12.4×
- **8×5**: **12 497** kutu → 12.4×

**Dürüst sınır:** UAVDT seyreltilmiş havuzda **≤5 px kutu YOK** (native minimum kutu
genişliği 5 px). 5×5 seviyesinde UAVDT 3 864, VisDrone 1 729 kutu veriyor; bu bant
zayıf kalıyor. **A6'nın 5×5'i çözeceği varsayılmıyor.**

## 7. Reproducibility

Betik tamamen belirlenimci: sıralı gezinme, sabit kurallar, **rastgelelik ve tohum
yok**. Bağımsız ikinci bir üretim yapılıp karşılaştırıldı:

```
1. üretim 17 406 dosya | 2. üretim 17 406 dosya
yalnız 1.'de 0 | yalnız 2.'de 0 | içerik farkı 0
parmak izi 1: f7ddc2068f7044351df3ea253a566834
parmak izi 2: f7ddc2068f7044351df3ea253a566834
```

Görüntü ve etiket dosyalarının **tamamı md5 düzeyinde birebir aynı**.
Yeniden üretmek için: `python3 veri/a6_hazirla.py` (tar aynı yerde olmalı).

## 8. Sonraki eğitim komutu (BU TURDA ÇALIŞTIRILMADI)

```bash
# Aşama A - UAVDT ön-eğitim (tek sınıf vehicle)
yolo detect train model=weights/yolov8n.pt data=data/a6/uavdt_pretrain/data.yaml \
     imgsz=640 epochs=100 batch=16 optimizer=AdamW lr0=0.001 lrf=0.01 cos_lr=True \
     warmup_epochs=3 patience=30 mosaic=1.0 close_mosaic=10 scale=0.5 \
     fliplr=0.5 flipud=0.5 degrees=180 perspective=0 device=cpu \
     project=runs/a6 name=asamaA_uavdt

# Aşama B - VisDrone fine-tuning (4 sınıf), A'nın best.pt'sinden
yolo detect train model=runs/a6/asamaA_uavdt/weights/best.pt \
     data=data/a6/visdrone_finetune/data.yaml \
     imgsz=640 epochs=150 batch=16 optimizer=AdamW lr0=0.0005 lrf=0.01 cos_lr=True \
     patience=30 mosaic=1.0 close_mosaic=10 fliplr=0.5 flipud=0.5 degrees=180 \
     device=cpu project=runs/a6 name=asamaB_visdrone

# Kontrol kolu - UAVDT'siz, yalnızca VisDrone (COCO'dan doğrudan)
yolo detect train model=weights/yolov8n.pt data=data/a6/visdrone_finetune/data.yaml \
     ... project=runs/a6 name=kontrol_sadece_visdrone
```

Kontrol kolu şart: UAVDT'nin katkısı ancak iki kol karşılaştırılınca **ölçülmüş**
olur. Değerlendirme A5.2 protokolünün birebir aynısıyla yapılacak; değişen tek şey
ağırlık dosyası.

> **GPU yok** (`torch 2.13.0+cpu`, CUDA False). Gerçek epoch süresi eğitim turunun
> ilk adımında 2 epoch'luk ısınmayla **ölçülecek**, tahmin edilmeyecek.

## 9. Donanım (değişmedi)

Raspberry Pi Zero 2 W · Raspberry Pi AI Camera (IMX500) · GEPRC TAKER F405 BLS 50A ·
iFlight XING-E Pro 2207 1800KV · 5 inch · ~750 g · Betaflight · **PX4/ArduPilot yok**.
A6'da Pi/IMX500 üzerinde çalıştırma **yok**; bu donanımlarda **henüz hiçbir ölçüm yok**.

## 10. Kabul kriterleri

| | ölçüt | sonuç |
|---|---|---|
| **D1** | UAVDT 5-kare seyreltilmiş set reproducible | **GEÇTİ** — iki bağımsız üretim md5 düzeyinde birebir |
| **D2** | VisDrone 538 temiz görüntü reproducible | **GEÇTİ** — aynı parmak izi `f7ddc206…` |
| **D3** | Train/val/test sequence leakage yok | **GEÇTİ** — Aşama A 50 dizi, Aşama B 74 grup; **split'ler arası çakışan grup: 0**. Birebir aynı görüntü çifti bulunup aynı split'e alındı |
| **D4** | YOLO dönüşümü round-trip | **GEÇTİ** — max hata 0.000768 px (A) / 0.001280 px (B) |
| **D5** | Sınıf eşlemeleri doğrulanmış | **GEÇTİ** — 538/538 dosya bağımsız türetimle birebir; UAVDT tek sınıf `{0}`; COCO haritası taşınmadı |
| **D6** | Küçük hedef dağılımı raporlanmış | **GEÇTİ** — §6 |
| **D7** | A5 benchmark dizileri sızmıyor | **GEÇTİ** — hash 0, ad 0, videoID 0, piksel max **0.6603** (r>0.80 yok) |
| **D8** | Orijinal tar ve kaynak değişmedi | **GEÇTİ** — tar boyut/mtime/baş-son 64MB md5 aynı; visdrone_det 548/548, bugün değişen dosya 0 |
| **D9** | `takip/` md5 6/6 aynı | **GEÇTİ** |
| **D10** | A3.9/A3.10/A4/A5 korunuyor | **GEÇTİ** — `kos`/`fare_hedef_sec`/`otomatik_hedef_sec`/`_roi_aday` AST aynı; `yolo_secici.py` A5.1 kaydıyla aynı |
