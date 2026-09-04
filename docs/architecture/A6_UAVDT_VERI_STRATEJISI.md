# A6 — UAVDT incelemesi ve veri stratejisi kararı

**Tarih:** 2026-08-31 · **Bu tur:** yalnızca inceleme + karşılaştırma + karar.
**Yapılmadı:** dosya taşıma · silme · veri setini yeniden düzenleme · kod değişikliği ·
model eğitimi · split oluşturma · commit/push. **Tar'a ve Downloads'a dokunulmadı.**
İnceleme, tar akış modunda (`tarfile "r|"`) yapıldı; diske hiçbir veri yazılmadı.

---

## 1. Dosya bulundu ve doğrulandı

| soru | cevap |
|---|---|
| **1. Exact path** | `/mnt/c/Users/Casper/Downloads/uavdt-DatasetNinja.tar` |
| **2. Boyut** | **13 993 973 760 bayt** (13.03 GiB / 14.0 GB) |
| **3. İndirme tamam mı?** | **EVET.** Boyut 20 sn arayla sabit; `.crdownload`/`.part`/`.tmp` izi yok; mtime 2026-08-31 02:33 |
| **4. Tar sağlam mı?** | **EVET.** Son 1024 bayt tamamen sıfır → geçerli tar bitiş bloğu. Boyut 512'ye tam bölünüyor (27 332 760 blok) |
| **5. `tar -tf` okunabiliyor mu?** | **EVET.** Baştan sona tam listeleme **EXIT=0**, **233 469 girdi** okundu, hata yok |
| **6. Çıkarılmış klasör** | **YOK.** `/home/beyza` ve `/mnt/c/Users/Casper` altında `*uavdt*` / `*DatasetNinja*` araması tek sonuç verdi: tar'ın kendisi |

Arama kapsamı: `/home/beyza`, `/mnt/c/Users/Casper`, `Downloads`. `/mnt/d`, `/mnt/e`
ve `İndirilenler` **mevcut değil**.

## 2. Yapı ve içerik envanteri

```
uavdt-DatasetNinja.tar
├── LICENSE.md · README.md · meta.json
├── train/  ann/ (24 143 .json) · img/ (24 143 .jpg) · meta/ (boş {})
└── test/   ann/ (53 676 .json) · img/ (53 676 .jpg) · meta/ (boş {})
```

- **Toplam görüntü: 77 819** · **annotation: 77 819** (1:1, bozuk JSON **0**)
- Görüntü 11.98 GB · annotation 1.57 GB
- **Çözünürlük:** 1024×540 (75 376) · 960×540 (2 443)
- **Format:** Supervisely/DatasetNinja JSON — `size` + `objects[].points.exterior`
  (iki köşe, `[[x1,y1],[x2,y2]]`) + görüntü ve nesne düzeyinde `tags`.
  **VisDrone'un CSV formatından tamamen farklı**, yeni bir dönüştürücü gerekecek.

### İki farklı alt küme (ÖNEMLİ)

| alt küme | kare | dizi | sınıf | split | not |
|---|---|---|---|---|---|
| **M** (`M####_img######.jpg`) | **40 735** | 50 | car / truck / bus | train 24 143 (30 dizi) + test 16 592 (20 dizi) | çok nesneli tespit/MOT |
| **S** (`S####_img######.jpg`) | **37 084** | 50 | yalnızca jenerik `vehicle` | tamamı `test` | tek nesne takibi; **kare başına tam 1 kutu** |

**Sınıflar (meta.json):** `bus`, `car`, `truck`, `vehicle`. **`van` YOK.**

| sınıf | kutu | % |
|---|---|---|
| car | 755 688 | 90.4% |
| vehicle (yalnız S) | 37 084 | 4.4% |
| truck | 25 086 | 3.0% |
| bus | 18 021 | 2.2% |
| **toplam araç** | **835 879** | |

M alt kümesi kare başına 19.6 kutu; VisDrone DET 31.1.

### Etiket zenginliği — VisDrone'da olmayan bilgiler

**Görüntü düzeyi tag'ler** (kamera/koşul bilgisi):
`daylight` 24 055 · `night` **11 501** · `fog` **5 179** ·
`low alt` 14 644 · `medium alt` 24 059 · `high alt` 2 032 ·
`front view` 23 601 · `side view` 17 672 · `bird view` 10 737 · `long term` 7 376.

> **İrtifa ve bakış açısı etiketli.** Bu, projenin "yükseklik arttıkça hedef küçülür"
> ekseninde **doğrudan stratifikasyon** imkânı verir — VisDrone DET'te bu bilgi yok.
> Gece ve sis kareleri de gerçek uçuş koşulları için değerli.

**Nesne düzeyi tag'ler:**
- **Occlusion:** `no occlusion` 715 470 · `small` 64 004 · `medium` 10 025 · `lagre`[sic] 9 296
- **Truncation (out-of-view):** `no out` 725 059 · `small out` 36 647 · `medium out` 37 089
- **`target id`** → 2 653 benzersiz hedef; **takip kimliği mevcut**, yani UAVDT
  yalnızca detection değil, MOT/SOT verisi de.

**Frame rate:** DatasetNinja paketinde **fps alanı yok** — tar içinde bulunamadı,
**varsayılmıyor**. Kareler ardışık video kareleridir (dosya adı `img000001…`),
ama fps değeri bu pakette **henüz ölçülmedi/yok**.

**Camera motion:** açık ego-hareket alanı **yok**; en yakın bilgi irtifa + bakış
açısı + `long term` tag'leridir.

---

## 3. VisDrone DET ile karşılaştırma

| | VisDrone DET | UAVDT | oran |
|---|---|---|---|
| görüntü | 548 | **77 819** | 142× |
| toplam bbox | 40 169 | 835 879 (hepsi araç) | 20.8× |
| **araç bbox** | **17 040** | **835 879** | **49.1×** |
| çözünürlük | 1360×768 / 960×544 / 1920×1080 | 1024×540 / 960×540 | — |
| letterbox (imgsz 640) | 0.471 / 0.667 / 0.333 | **0.625** | UAVDT daha az çözünürlük kaybediyor |
| native uzun kenar (medyan) | 41 px | 34 px | |
| **ağ girdisi uzun kenar (medyan)** | **19.8 px** | **21.9 px** | çok yakın |
| ağ girdisinde ≤57 px oranı | %93.6 | **%95.9** | |
| sınıf | car, van, truck, bus (+8 diğer) | car, truck, bus, vehicle | **van yok** |
| bağımsızlık | 548 bağımsız görüntü | 77 819 **video karesi** (yüksek korelasyon) | — |

### A5.2 seviyelerinde araç bbox sayısı (ağ girdisi, imgsz=640)

| A5 seviyesi | VisDrone DET | **UAVDT** | kat |
|---|---|---|---|
| 57×21 (>57) | 1 097 | 34 649 | 31.6× |
| 40×15 | 1 698 | 51 720 | 30.5× |
| 30×12 | 2 086 | 123 975 | 59.4× |
| 20×10 | 3 566 | 241 928 | 67.8× |
| **15×7** | **2 479** | **121 194** | **48.9×** |
| **10×5** | **2 402** | **165 953** | **69.1×** |
| **8×5** | **1 040** | **75 040** | **72.2×** |
| **5×5** | **1 728** | **21 169** | **12.3×** |
| ≤5 px | 944 | **251** | **0.3×** |
| **toplam** | 17 040 | 835 879 | 49.1× |

**≤20 px bandı (A5'in çöktüğü bölge): VisDrone 8 593 → UAVDT 383 607, 44.6 kat.**

İki uyarı, gizlenmiyor:
1. UAVDT kovalarının **%4.4'ü** S alt kümesinin jenerik `vehicle` kutularıdır.
2. **≤5 px'te UAVDT DAHA AZ örnek veriyor** (251 vs 944). UAVDT'de native minimum
   kutu genişliği 5 px; 5×5 seviyesini UAVDT çözmüyor. Bu, "5×5 zorunlu değil"
   kararıyla tutarlı ama açıkça söylenmeli: **UAVDT 5×5'i kurtarmaz.**

---

## 4. LEAKAGE KONTROLÜ — UAVDT temiz

Aynı yöntem A6 planındaki VisDrone DET kontrolüyle birebir aynı: 48×48 gri imza,
normalize korelasyon, repodaki **7 VID dizisinin 2 846 karesinin tamamına** karşı.

| alt küme | örnek | en yüksek korelasyon | r>0.95 | 117/23 veya 137/12 ile eşleşme |
|---|---|---|---|---|
| **M** (50 dizi × 5 kare) | 250 | **0.8607** (M0604 ↔ `uav0000339`) | **0** | ilk 12'de **yok** |
| **S** (50 dizi × 5 kare) | 250 | **0.8013** (S0401 ↔ `uav0000339`) | **0** | ilk 12'de **yok** |

Kıyas ölçeği — aynı yöntem VisDrone DET'te sızıntıyı **yakalamıştı**:
`0000117_02708_d_0000090.jpg` ↔ `uav0000117_02622_v/0000032.jpg` **r = 0.9990**.
Yani "aynı görüntü" ≥0.997 bandında çıkıyor; UAVDT'nin en yükseği 0.86 ve o da
düşük kontrastlı bir gece sahnesi (`uav0000339`) ile sahte benzerlik.

**Hüküm: UAVDT ile A5 test dizileri (117/23, 137/12) arasında veri sızıntısı YOK.**

Sınırı da söyleyeyim: bu **örneklemli** bir kontroldür (dizi başına 5 kare, 100
dizinin tamamı kapsandı), tüm 77 819 kare tek tek karşılaştırılmadı. Yapısal kanıt
bunu destekliyor: farklı koleksiyon, ayrık isimlendirme (`M####`/`S####` ↔
`uav########`), farklı çözünürlük (1024×540 ↔ 2720×1530). Eğitim öncesi kontrol
**tam kapsamda tekrarlanacak** (A6-1).

> Not: VisDrone DET tarafındaki **gerçek sızıntı hâlâ geçerli** —
> `0000117_*` ve `0000086_*` grupları (10 görüntü) eğitim dışında bırakılacak.
> UAVDT'nin eklenmesi bu önlemi ortadan kaldırmaz.

---

## 5. Üç stratejinin karşılaştırması

| ölçüt | **1. Sadece VisDrone** | **2. UAVDT + VisDrone birlikte** | **3. UAVDT ön-eğitim → VisDrone fine-tune** |
|---|---|---|---|
| **küçük hedef** | ≤20 px bandında **8 593** kutu — A5'in çöktüğü bandı öğretmek için zayıf | **392 200** kutu (45×) ama VisDrone'un payı %2.2'ye düşer | **Her ikisi de**: önce 383 607 kutuyla küçük-nesne özelliği öğrenilir, sonra hedef domenle kalibre edilir |
| **domain uyumu** | Hedef domenin **kendisi** (benchmark VisDrone VID) | Karışık; UAVDT 49:1 baskın → model UAVDT'ye kayar | Ayrık: UAVDT genel görsel önsel, VisDrone son söz |
| **veri miktarı** | 538 görüntü (sızıntı sonrası) — **çok az** | 78 357 görüntü ama 77 819'u **video karesi**, etkin çeşitlilik ~100 dizi | Aşama A geniş, aşama B küçük ve odaklı |
| **sınıf uyumu** | Tam (car/van/truck/bus) | **Bozuk**: UAVDT'de `van` yok, S'te yalnız jenerik `vehicle` | Aşama A tek sınıf (`vehicle`), aşama B proje sınıfları — **uyumsuzluk çözülür** |
| **leakage riski** | DET'te **gerçek sızıntı var** (10 görüntü atılacak) | Aynı + UAVDT (temiz) | Aynı; UAVDT ek risk getirmiyor |
| **eğitim maliyeti** | **Düşük** (CPU'da bile yapılabilir) | **Fizibil değil**: 78k görüntü × 150 epoch, GPU yok → haftalar | Aşama A zamansal seyreltmeyle **8 147 görüntü**'ye iner, aşama B 538 → yönetilebilir |
| **gerçek drone'a uygunluk** | Mimari aynı (YOLOv8n) | Aynı | Aynı + UAVDT'nin **gece/sis/irtifa** çeşitliliği gerçek uçuşa yakın |

**Kritik nicel gerekçe (2 ve 3 arasındaki fark):** UAVDT'nin 77 819 karesi bağımsız
görüntü değil, **50+50 diziden gelen ardışık video kareleridir**. Karıştırıp tek
havuzda eğitmek (strateji 2) hem 49:1 dengesizliği hem de tekrarlı kareler yüzünden
etkin veri artışını çok abartır ve hedef domenden uzaklaştırır. Zamansal seyreltme
(M alt kümesinden her 5. kare → **8 147 görüntü, ~159 800 araç kutusu**) bilgi
kaybı olmadan maliyeti 5 kat düşürür; bu seyreltilmiş küme **ön-eğitim** için
doğru boyuttur.

**Sınıf kararı önerisi:** ön-eğitim **tek sınıf (`vehicle`)** yapılsın. Proje tek
araç takibi yapıyor; seçicinin ihtiyacı "bu bir araç mı" sorusunun cevabı.
Tek sınıf hem UAVDT'nin `van` eksiğini ve S'in jenerik etiketini sorun olmaktan
çıkarır, hem de YOLOv8n'in 3.2M parametrelik kapasitesini küçük-nesne problemine
yoğunlaştırır.

---

## 6. KARAR

# C) UAVDT → VisDrone ön-eğitim / fine-tuning

**Neden A değil.** Ana hedef küçük hedef sınırını aşağı çekmek. Ölçülen gerçek şu:
VisDrone DET'in ≤20 px bandında topu topu **8 593** araç kutusu var ve 548 görüntünün
%1.8'i sızıntı yüzünden atılacak. A5, COCO pretrained modelin bu bandı hiç görmediği
için çöktüğünü gösterdi; 8 593 kutunun bunu tersine çevirmesi için bir gerekçe yok.
Sadece VisDrone, tabanın *ne kadar* düşebileceğini test etmeden sınırlar.

**Neden B değil.** İki somut engel: (i) 49:1 dengesizlik — VisDrone'un payı %2'ye
düşer ve model hedef domenden uzaklaşır; (ii) sınıf uyumsuzluğu — UAVDT'de `van`
yok, S alt kümesinde yalnız jenerik `vehicle` var, tek havuzda bunlar birleştirilemez.
Üstelik GPU yokken 78k görüntülük tek havuz **fizibil değil**.

**Neden C.** Üç ölçülmüş nedenle:
1. **Küçük hedef arzı:** ön-eğitim aşaması ≤20 px bandında **383 607** kutu görür
   (VisDrone'un **44.6 katı**); 8×5 bandında 72×, 10×5 bandında 69×.
2. **Boyut dağılımı zaten hizalı:** ağ girdisinde medyan uzun kenar UAVDT 21.9 px,
   VisDrone DET 19.8 px — ön-eğitim, fine-tuning'in göreceği ölçekten sapmıyor.
   Ayrıca UAVDT'nin letterbox çarpanı daha yüksek (0.625 vs 0.471), yani aynı
   fiziksel araç ağ girdisinde daha az bozuluyor.
3. **Maliyet yönetilebilir:** zamansal seyreltmeyle aşama A **8 147 görüntü**;
   aşama B 538 görüntü. GPU yokluğu C'yi engellemiyor, B'yi engelliyor.

Ek kazanç: UAVDT'nin **gece (11 501) / sis (5 179) / irtifa etiketli** kareleri,
gerçek drone koşullarına VisDrone DET'ten daha yakın bir görsel önsel veriyor.

**Dürüst sınır:** UAVDT ≤5 px bandında VisDrone'dan **daha az** örnek içeriyor
(251 vs 944) ve native minimum kutu genişliği 5 px. **C stratejisi 5×5'i çözmeyi
vaat etmiyor.** Beklenti, tabanın 57'den aşağı taşınmasıdır; nereye kadar
taşındığı A5.2 protokolüyle **ölçülecek**, önceden iddia edilmeyecek.

---

## 7. Önerilen A6 akışı (uygulama İÇİN ONAY BEKLİYOR)

- **Aşama A — ön-eğitim.** UAVDT M alt kümesi, her 5. kare (~8 147 görüntü,
  ~159 800 kutu), **tek sınıf `vehicle`**, COCO pretrained YOLOv8n'den başlayarak,
  imgsz 640. S alt kümesi ilk turda dışarıda (jenerik etiket + kare başına tek kutu).
- **Aşama B — fine-tuning.** VisDrone DET 538 görüntü (`0000117_*`, `0000086_*`
  grupları hariç), grup-bazlı split, düşük LR.
- **Değerlendirme.** A5.2 protokolünün **birebir aynısı**; değişen tek şey ağırlık.
  Karar ölçütü Y8-D: *nitelenen en küçük seviye 57'den küçük mü?*
- **Kontrol kolu.** Strateji A (sadece VisDrone) da koşulsun — UAVDT'nin katkısı
  ancak bu iki kol karşılaştırılınca **ölçülmüş** olur, varsayılmış olmaz.
- **Donanım kısıtları değişmedi:** Pi Zero 2 W · IMX500 · GEPRC TAKER F405 BLS 50A ·
  5 inch · ~750 g · Betaflight; PX4/ArduPilot yok. Pi ve IMX500 üzerinde
  **henüz hiçbir ölçüm yok**. Bu makinede **GPU yok**; gerçek epoch süresi
  uygulama turunun ilk adımında ölçülecek, tahmin edilmeyecek.

**Bu turda hiçbir dosya taşınmadı, silinmedi, çıkarılmadı; kod değişmedi;
split oluşturulmadı; model eğitilmedi; commit/push yapılmadı.**
