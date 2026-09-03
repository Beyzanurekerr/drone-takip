# A11 — GAZEBO YATAĞI + DÖNGÜ DIŞI BİLGİ · ÖN-KAYIT

**Yazıldığı tarih:** 2026-09-03 · **A11 kolları KOŞULMADAN ÖNCE yazıldı.**
Sonuçlara bakılıp değiştirilmeyecek; değişmesi gerekirse gerekçeli yeni sürüm
eklenir, bu sürüm silinmez.

> **Kompozit yatak ARŞİVDİR.** A5.2 / A7 / A8 / A9 / A10 / A10.1 yatağı
> (VisDrone karesine yapıştırılmış ölçekli yama) A11'de **kullanılmayacak**.
> **A10.1 hükmü son sözdür, tekrar koşulmaz.**
> A11'in bütün ölçümleri Gazebo'da, gerçek kamera hareketiyle yapılır.

> **Değişmeyenler:** `A9_KABUL_OLCUTU.md` **K1–K6 aynen** · iki sütunlu yanlış
> kilit raporlaması (hakem durumu / takipçi durumu) · oracle kolların
> "ÜST SINIR" etiketi · `KALICI_KISITLAR.md` (K6 dahil).
> **Yasaklar aynen:** eğitim · ağırlık · `imgsz` · SAHI · Pi optimizasyonu ·
> 5×5 · sonuca göre sabit değiştirme — **artı: kompozit yatak kullanmak.**

---

## 1. Karar tabanı — Gazebo senaryoları

`gazebo/senaryolar.py:A11_AILE`, kayıt `gazebo/kaydet.py`,
veri `data/gazebo/<senaryo>/` (kareler + `pozlar.csv` + **`imu.csv`** + meta).

| ön-kayıtlı gereklilik | nerede karşılanıyor |
|---|---|
| **≥ 6 senaryo** | A1…A6 (**6**) |
| **hedef 60 → 8 px küçülme** | **A2**, **A5** — irtifa rampası 38.3 → 287.5 m, 12.46 m/s, 600 kare |
| **yaw ±30°** | **A3**, **A5** — `wz = A cos(2πft)`, `A = 30° · 2πf`, f = 0.25 Hz → açı genliği tam **30°** |
| **irtifa değişimi** | **A2**, **A4** (±35 m salınım, 38.3–108.3 m), **A5** |
| **≥ 2 çeldirici** | **hepsinde** (`celdirici`, `celdirici2`) |
| **tohum sabit** | `doku_seed = 11`, **bütün ailede aynı** |
| **kayıtlı GT, tekrarlanabilir** | `pozlar.csv` (hedef + 2 çeldirici + kamera, sim-zamanı damgalı, interpolasyonlu) · `imu.csv` (200 Hz) |

| senaryo | kare | içerik |
|---|---|---|
| **A1_taban** | 300 | sabit 38.3 m, bozulmasız kamera — kontrol |
| **A2_kucul** | 600 | irtifa rampası, hedef 60 → 8 px |
| **A3_yaw** | 300 | yaw ±30°, sabit irtifa |
| **A4_irtifa** | 300 | irtifa salınımı ±35 m (60 → 21 px) |
| **A5_kucul_yaw** | 600 | küçültme **ve** yaw birlikte |
| **A6_celdirici** | 300 | iki çeldirici, yanlış kilit stresi |

**Zemin bütün ailede AYNI**: 560 m kenar, 4096 px doku (7.31 texel/m).
Gerekçe: senaryolar arası ego/doku karşılaştırması ancak zemin aynıysa
geçerlidir. 560 m, 287.5 m irtifadaki görüş genişliğini (369 m) kapsar.
**Bu, mevcut G-ailesinden (160 m / 2048 px) farklıdır**; G ailesiyle
doğrudan sayı karşılaştırması yapılmayacak.

Ölçek: `odak = 500 px`, araç `L = 4.6 m` → `px = 500·4.6/h`.
38.3 m → 60.0 px · 287.5 m → 8.0 px.

---

## 2. KOL 0 — TAŞIMA (mevcut pipeline Gazebo'da H0)

Değişiklik **yok**: mevcut takipçi + dedektör + **A10.1 hakemi (histerezisli)**
Gazebo kayıtlarında koşulur. Kollar A10.1'deki gibi: H0 · H1 · H2 · H3 +
iki oracle.

**Sorulan tek soru:** kompozit yatakta bulunan şeyler gerçek kamera
hareketinde sağ kalıyor mu?

**Zorunlu karşılaştırmalar (A9/A10 sayılarıyla yan yana):**

| kompozit bulgu | A11'de ölçülecek karşılığı |
|---|---|
| **117/23'te 17–19 px "sahte ego"** (A9 Aşama 1 §6, "saf ego p95 18.4 px") | Gazebo'da ego katmanının ürettiği px/kare — gerçek kamera hareketi biliniyor (`pozlar.csv` + `imu.csv`), **sahte olanı ayırt edilebilir** |
| doğrulamada **kanıt yok %43–51** | aynı metrik, Gazebo'da |
| Mod A / Mod B ayrımı (temiz yatakta 8 / 2 hücre) | aynı ölçütle (kopuş sonrası DCF kabul oranı ≥ 0.8 → Mod B) |
| `bho` şişmesi (p50 ≈ 1.98) | aynı |
| yanlış kilit, iki sütun | aynı |

**Ego "sahte hareket" tanımı (koşumdan önce sabit):**
> `sahte_ego_px = ‖M_gorsel(x_ref) − M_gercek(x_ref)‖`, ölçüm noktası
> `x_ref` = görüntü merkezi; `M_gercek` `pozlar.csv`'deki kamera pozundan
> türetilir. Bu, kompozit yatakta **ölçülemeyen** bir büyüklüktür (orada
> gerçek kamera hareketi yoktu) ve A11'in temel kazancıdır.

---

## 3. KOL 1 — IMU EGO

**Tek değişken:** ego telafisi kaynağı.
- **1a (kontrol):** mevcut görüntü tabanlı ego (`takip/egomotion.py`).
- **1b:** Gazebo IMU'sundan ego; **görüntü tabanlı ego KAPALI**.

IMU açısal hızı gövde çerçevesinde, görsel ego kamera çerçevesinde ölçülür;
dönüşüm `meta.json`'daki `kam_roll/pitch/yaw` ile yapılır. IMU **yönelim**
kuaterniyonu da kayıtlıdır ve ayrık integrasyon hatası ölçülecektir.

**Ölçülecekler:** sahte hareket px/kare (§2 tanımı) · **Mod A kaçış hızı**
(kopuştan sonra merkez hatasının kare başına artışı, px/kare) · PSR p50/p05 ·
IoU · yanlış kilit (iki sütun).

**IMU bir ÜST SINIR değildir** — gerçek dronda da IMU vardır (GEPRC/Betaflight).
Ama Gazebo IMU'su gürültüsüzdür; **gürültü modeli eklenmeyecek** ve sonuç
"gürültüsüz IMU" etiketiyle raporlanacaktır.

---

## 4. KOL 2 — ZAMANSAL HAREKET BİRİKTİRME

Ego-telafili kare farkı **N** kare biriktirilir; birikimden **bağımsız bir
MERKEZ adayı** üretilir. `N ∈ {3, 5, 8}` — üç değer **koşumdan önce** sabit.

> **Takipçiye YAZMAZ.** Bu tur **açık çevrimdir** ve bilerek öyledir:
> A10/A10.1'in dersi, bir bileşeni çevrime sokmadan önce beslemesini
> ölçmektir.

**Ölçülecekler:**
1. **merkez hatası vs GT** (px) — p50/p95, seviye (hedef px boyutu) bazında;
2. **kanıt oranı** — kaç karede aday üretiliyor, seviye bazında;
3. **8×5 bandında** (hedef ≤ 10 px) dedektörün kanıt üretmediği karelerde
   bu kanalın kanıt üretip üretmediği — **bire bir aynı kareler**.

3. madde bu kolun varlık sebebidir: hakemin **kanıt-yok %43–51**'ine doğrudan
cevaptır. Ölçüt: *o karelerde kanıt oranı* ve *merkez hatası*.

**Başarı iddiası için eşik YOK** — dağılım olarak raporlanacak (EK-1 geleneği).

---

## 5. KOL 3 — UÇUŞ GEOMETRİSİ (spesifikasyon deneyi)

> **Bu bir algı deneyi değildir.** Sorulan şey "algı ne kadar iyi" değil,
> "**uçuş nasıl olmalı ki algı çalışsın**".

Kural (ön-kayıtlı): **hedef < 25 px → yaklaşma komutu**; takip **koruma
moduna** girer. 25 px, A7 §4'ün ölçtüğü takipçi süreklilik sınırının
(**14–20 px**) üstünde seçildi — sınıra varmadan tepki verilmesi için;
sonuca göre değiştirilmeyecektir.

**Koruma modu:** yaklaşma sırasında hakem **LOST ilan etmez** ve recovery
tetiklenmez; takipçi mevcut kilidi sürdürür. (Yaklaşma, hedefi bilerek
büyüttüğü için ego/ölçek kanalı geçici olarak güvenilmezdir.)

Bu kol **kapalı çevrimdir**: kamera → takipçi → `cmd_vel`. Offline
kayıt-sonra-oynat kullanılamaz; canlı `gz sim` gerekir.

**Ölçülecekler:**
- **hedefin 20 px altında geçirdiği kare oranı** (birincil);
- koruma modunda kayıp: IoU, yanlış kilit (iki sütun), kopuş sayısı;
- yaklaşma komutunun ürettiği irtifa profili (GT'den).

**Karşılaştırma kolu:** aynı senaryo, yaklaşma **kapalı** (irtifa rampası
kendi haline bırakılır) — A2/A5 zaten budur.

---

## 6. Kabul

`A9_KABUL_OLCUTU.md` K1–K6 **aynen**. Ek olarak:

- **KOL 2 ve KOL 3 kabul ölçütüne tabi değildir** — ikisi de teşhis/
  spesifikasyon; `takip/` değiştirmezler.
- **KOL 1** bir A/B'dir ve K1–K6'ya tabidir.
- **KOL 0** kontroldür; kabul değil, **taşıma** ölçer.
- A10.1'in K5 kuralı geçerli: **toplam recovery denemesi < 5 ise
  "SINANMADI"** yazılır.

---

## 7. Çıktı ve commit

| kol | rapor | veri | commit |
|---|---|---|---|
| altyapı + ön-kayıt | bu dosya | `data/gazebo/A*` | 1 |
| KOL 0 | `A11_KOL0_TASIMA.md` | `cikti/a11_kol0.json` | 2 |
| KOL 1 | `A11_KOL1_IMU_EGO.md` | `cikti/a11_kol1.json` | 3 |
| KOL 2 | `A11_KOL2_HAREKET_BIRIKTIRME.md` | `cikti/a11_kol2.json` | 4 |
| KOL 3 | `A11_KOL3_UCUS_GEOMETRISI.md` | `cikti/a11_kol3.json` | 5 |

**push YOK.** Sonunda **DUR**.

---

# EK-1 — İstem denetimi: dedektör Gazebo'da KÖR (KOL 0 koşulmadan önce eklendi)

**Eklendiği tarih:** 2026-09-03 · **Hiçbir KOL koşulmadan önce yazıldı.**
A9 Aşama 1-EK precedent'i: sonuçlara bakıp değil, koşumdan önce yapılan bir
sistematik taramayla bulundu.

**Bulgu:** COCO-eğitilmiş `A5_baseline` (yolov8n), Gazebo'nun kutu-primitif
araçlarını **hiç görmüyor**. Sistematik tarama: 6 senaryonun her 10. karesi
(**240 kare**), tam kare, **sınıf kısıtlamasız**, `conf ≥ 0.10` → **0 tespit**.
Tek kare değil, tüm taban.

**Sebep görsel:** Gazebo'daki "araç" düz renkli bir kutu + üstünde ikinci bir
kutu (kabin) — doku, tekerlek, cam, gölgeleme yok. COCO'nun "araba" dağılımıyla
hiçbir ortak özelliği yok.

**Kapsam üzerindeki etki:**

- **Yasaklar gereği düzeltilmeyecek** (eğitim, ağırlık, `imgsz` değişikliği
  yasak — bu tam olarak "sonuca göre sabit değiştirme"nin kapsadığı şey).
- **H0 etkilenmiyor.** H0 saf klasik takipçidir (`hakem=None`), YOLO hiç
  çağrılmaz. KOL 0'ın asıl talebi (sahte-ego karşılaştırması, taşıma) **H0
  üzerinden tam olarak ölçülebilir.**
- **H1/H2/H3/oracle kolları YOLO'ya bağımlı bileşenlerde SIFIRA çöker:**
  doğrulama hiçbir zaman ONAY vermez (kanıt her zaman yok), boyut çapası hiç
  yazmaz, recovery hiçbir zaman aday bulamaz (her zaman çekimser).
  **Bu bir harness hatası değil, ölçülen bir sonuçtur** ve öyle raporlanır.
- **Mod A histerezisi (D2) etkilenMİYOR** — `iz(P)` ve `takipçinin kendi
  ARAMA/KAYIP durumu`na dayanır, YOLO'ya bağımlı değil. H1–H3 arası fark
  bu kanaldan gelmeye devam eder ve **anlamlı kalır**.

**Sonuç olarak KOL 0'da H1, H2, H3 ve iki oracle kolu birbirine neredeyse
özdeş davranacaktır** (hepsi doğrulama/çapa/recovery'de aynı şekilde
"kanıtsız"); bu beş kol arasındaki TEK ayrım kanalı Mod A histerezisidir.
Bu, koşumdan ÖNCE yazılan bir beklentidir; sonuç bunu doğrularsa "harness
bozuk" değil "dedektör transfer olmuyor" diye okunacaktır.

---

# EK-2 — KOL 1 tasarım kararı: IMU ego'nun kapsamı (KOL 1 koşulmadan önce)

**Eklendiği tarih:** 2026-09-03 · **KOL 1 ölçümü koşulmadan önce yazıldı.**
İki hızlı doğrulama koşumuyla (A3_yaw, ~300 kare) bulundu; hiçbir eşik veya
kabul ölçütü bu bulguya göre değiştirilmedi.

**Bulgu 1 — IMU `orientation` alanının MUTLAK değeri gerçek kamera
yöneliminden sapıyor** (Frobenius farkı ~0.09–0.19, sabit değil, A3'ün kendi
yaw salınımıyla aynı periyotta osile ediyor — muhtemelen gz-sim IMU
eklentisinin kendi entegrasyon referansıyla ilgili bir yapaylık).

**Bulgu 2 — KARE-KARE BAĞIL rotasyon (`R(t-1)⁻¹·R(t)`) gerçeğe YAKIN**
(açı farkı tipik olarak <0.5°). Mutlak sapma kare-kare farkta büyük ölçüde
iptal oluyor.

## Tasarım kararı

**M_imu YALNIZCA ROTASYONU telafi eder; ÖTELENME (ileri uçuş, irtifa
değişimi) KASITLI OLARAK SIFIRDIR.**

**Gerekçe:** İvmeölçerden öteleme çıkarmak çift integrasyon gerektirir ve
sürüklenmesi bilinen bir IMU sınırıdır (denenmedi — kapsam dışı bırakıldı,
"sonuca göre" değil, fiziksel bir kısıt olarak). Bu, projenin kendi
A3.9 Faz B bulgusuyla ("koparan tek kanal DONME... kamera ötelemesi 80 m/s'ye
kadar koparmıyor") doğrudan hizalı bir kapsam daraltmasıdır — test edilen tam
olarak IMU'nun İYİ olabileceği kanaldır.

**Mekanik:**
1. `R_kam_sabit`, HER senaryo için **bir kez**, **frame 0**'da kalibre edilir:
   `R_kam_sabit = R_govde_imu(t0)⁻¹ · R_kamera_gercek(t0)`. Bu, gerçek bir
   dronda kamera-IMU dış kalibrasyonunun (mount offset) tek seferlik
   ölçümüne karşılık gelir — **çalışma zamanında** GT kullanılmaz.
2. Kamera konumu **frame 0'ın gerçek konumunda SABİTLENİR** (`C_sabit`) —
   ötelenme dışlandığı için bu bir yer tutucudur, her karede GT'ye
   bakılmaz.
3. Her kare geçişinde: `R_govde_imu(t)` IMU'nun **en yakın örneğinden**
   okunur (200 Hz, kare 30 Hz — enterpolasyon yok, en yakın örnek).
   `R_cam_imu(t) = R_govde_imu(t) · R_kam_sabit`.
4. 3×3 örnekleme ızgarası, `(C_sabit, R_cam_imu(t-1))` ile zemine
   düşürülüp `(C_sabit, R_cam_imu(t))` ile geri izdüşürülür — **görsel
   EgoMotion'ın kendi uydurduğu model** olan **benzerlik dönüşümüne**
   (`cv2.estimateAffinePartial2D`, RANSAC) fit edilir. Adil karşılaştırma
   için görsel ego ile AYNI dönüşüm sınıfı kullanılır (tam 6-DOF afin değil).

**Bu, KOL 1'in bir ÜST SINIR olmadığını doğrular** (ön-kayıt §3): IMU
ötelemeyi hiç görmediği için karışık (öteleme+dönme) senaryolarda
(A1, A2, A4) **beklenen sonuç görsel egodan BELİRGİN kötü**dür — bu
beklenti, sonuçlara bakılmadan burada yazılmıştır.
