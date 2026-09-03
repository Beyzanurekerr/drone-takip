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
