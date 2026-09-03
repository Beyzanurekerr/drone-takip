# A11 KOL 0 — TAŞIMA: mevcut pipeline Gazebo'da

> ### `KAPALI ÇEVRİM` · `KOMPOZİT YATAK YOK` · Gazebo, gerçek kamera hareketi
> **İki net sonuç, bir beklenmedik bulgu.**
> 1. **117/23'teki 17–19 px "sahte ego" sağ KALMADI — bir yatak artefaktıydı.**
>    Gazebo'da 6 senaryonun hepsinde ego katmanının kalıntı hatası
>    **alt-piksel** (p95 ≤ 0.31 px).
> 2. **Dedektör Gazebo'da TAMAMEN kör** (EK-1'in ön-kayıtlı beklentisi
>    doğrulandı): 156 doğrulama fırsatının **156'sında da** kanıt yok
>    (**%100**). H1, H2, H3 ve iki oracle kolu **her hücrede bit düzeyinde
>    özdeş** çıktı.
> 3. **Beklenmedik: klasik takipçinin KENDİSİ (H0) Gazebo'da erken kopuyor** —
>    en basit kontrol senaryosunda (A1, bozulmasız kamera) bile 299 karede
>    2 kopuş. Kök neden görsel olarak teşhis edildi: DCF, hedefin düz renkli
>    kutusundan **prosedürel zemin dokusundaki yüksek kontrastlı statik bir
>    çizgiye** kayıyor.

**Tarih:** 2026-09-03 · **Kod:** `gazebo/tani_a11_kol0.py`, `gazebo/a11_ortak.py`
**Veri:** `cikti/a11_kol0.json` · **Ön-kayıt:** `A11_ONKAYIT.md` §2 (+ EK-1)
**Bütünlük:** `takip/*.py` md5 koşum öncesi = sonrası. `izleyici.py`/`hakem.py`
**değişmedi** — A10.1'in kodu aynen kullanıldı.

---

## 1. Sahte ego — 117/23'ün 17–19 px'i sağ kalmadı

**Tanım (ön-kayıt):** `sahte_ego_px = ‖M_gorsel(x_ref) − M_gercek(x_ref)‖`,
`x_ref` = görüntü merkezi, `M_gercek` düz zemin varsayımıyla **gerçek** kamera
pozundan (`pozlar.csv`) türetildi — A9'un kompozit yatağında **ölçülemeyen**
bir büyüklük (orada gerçek kamera hareketi yoktu, "gerçek ego = 0" varsayımı
vardı).

| senaryo | nokta | p50 (px) | p95 (px) | max (px) |
|---|---|---|---|---|
| A1_taban (bozulmasız) | 299 | 0.116 | 0.234 | 0.272 |
| A2_kucul (irtifa rampası) | 599 | 0.017 | 0.045 | 0.147 |
| **A3_yaw** (±30° dönme) | 299 | 0.119 | **0.311** | 0.376 |
| A4_irtifa (±35 m salınım) | 299 | 0.035 | 0.173 | 0.237 |
| A5_kucul_yaw (küçültme+dönme) | 599 | 0.032 | 0.059 | 0.115 |
| A6_celdirici | 299 | 0.115 | 0.233 | 0.273 |

**Karşılaştırma (A9 Aşama 1 §6, "saf ego p95"):**

| | A9 kompozit (gerçek ego = 0) | A11 Gazebo (gerçek ego ≠ 0, ölçülüyor) |
|---|---|---|
| en kötü dizi/senaryo | 117/23: **18.62 px** | A3_yaw: **0.311 px** |
| en iyi dizi/senaryo | 305/5: 1.38 px | A2_kucul: 0.045 px |

> **Görsel tabanlı ego katmanı gerçek kamera hareketini alt-piksel doğrulukla
> kestiriyor — dönme kanalında bile** (A3_yaw en yüksek p95'i veriyor ama yine
> de 0.31 px). A9'un "117/23'ün arkaplanında kare başına ~17–19 px sahte
> hareket" bulgusu, **kompozit yatağın "gerçek ego = 0" varsayımının bir
> yapaylığıydı** — ego katmanı orada da muhtemelen makul bir apparent-motion
> kestirimi yapıyordu, sadece kıyaslayacağı "gerçek" sıfırdı. Gazebo'da gerçek
> hareket olunca kestirim **doğru** çıkıyor.

**Sınır:** bu ölçüm **takip döngüsünden bağımsız** yapıldı (kilitlenmemiş,
saf `EgoMotion()` problobu — A9'un "saf ego" ölçümü ise KİLİTLİ bir takipçi
içinde, dışlama maskesiyle yapılmıştı). Kilitliyken dışlama maskesinin
sonucu değiştirip değiştirmediği **ölçülmedi**; KOL 1 bunu dolaylı olarak
kapsayacak.

---

## 2. Dedektör Gazebo'da tamamen kör — EK-1 doğrulandı

**156/156 doğrulama noktasının TÜMÜNDE kanıt yok (%100)**, 6 senaryonun
hepsinde, her seviyede (30×12'den 8×5'e). Ön-koşum taraması (240 kare, tüm
sınıflar, `conf≥0.10` → 0 tespit) tam koşumla **birebir doğrulandı**.

**Sonuç: H1, H2, H3, H3-O-merkez, H3-O-boyut her hücrede BİT DÜZEYİNDE
ÖZDEŞ.** Boyut çapası hiç yazmadı (`capa_yazim=0`, 6 senaryo toplamı),
recovery hiç denenmedi (`recovery_deneme=0`), oracle referanslar hiçbir
zaman kullanılmadı (`sec()` boş `kutular` listesiyle referanstan bağımsız
her zaman `None` döner). Beş kol arasındaki **tek** ayrım kanalı — ön-kayıtta
yazıldığı gibi — **Mod A histerezisidir** (`iz(P)` + takipçinin kendi
ARAMA/KAYIP durumu, YOLO'ya bağımlı değil).

> **A9/A10/A10.1'in bütün D3 (kapsama tabanlı ROI) ve boyut-çapası
> emeği, sentetik render'da dedektörün kendisi hiç çalışmadığı için
> Gazebo'ya HİÇ TAŞINAMADI.** Bu bir harness hatası değil: COCO'nun "araba"
> dağılımıyla Gazebo'nun düz renkli kutu-primitiflerinin hiçbir görsel ortak
> noktası yok (bkz. EK-1 ve aşağıdaki §4 görseli).

Bu yüzden §3'ten itibaren yalnızca **H0** (hakemsiz) ile **H(hakem)**
(H1=H2=H3=H3-O-*, tek sütun) karşılaştırılıyor.

---

## 3. BEKLENMEYEN BULGU — klasik takipçi Gazebo'da erken kopuyor

En basit kontrol senaryosunda (**A1_taban**: sabit 38.3 m, bozulmasız kamera,
tek çeldirici yok — yalnızca hedefin düz hareketi) **H0, 299 karede 2 kez
kopuyor** ve ortalama IoU **0.066**. Kare kare iz:

| t | durum | PSR | IoU | not |
|---|---|---|---|---|
| 1–7 | KİLİTLİ | 78–232 | 0.88–0.92 | doğru kilit |
| **8** | KİLİTLİ | 94.0 | **0.561** | kutu aniden büyüyor (28→41.6 px yükseklik) |
| 9–19 | ŞÜPHELİ | 4.3–7.2 | 0.35–0.56 | PSR çöküyor, kutu büyümeye devam ediyor |
| 20 | KİLİTLİ | 75.5 | **0.183** | yeniden "kilitleniyor" — ama YANLIŞ yere |
| 45 | KİLİTLİ | 24.7 | 0.063 | PSR hâlâ yüksek görünüyor |
| 55 | ARAMA | 0.0 | 0.009 | tamamen kayboldu |

**Görsel teşhis (t=20, kırmızı = takipçi, yeşil = GT):**

Takipçi hedeften (yeşil kutu, yol üzerindeki mavi araç) tamamen ayrılmış;
kırmızı kutu yolun ortasından geçen **koyu yeşil dikey bir çizgiyi** (zemin
dokusunun bir parçası — ağaç sırası/doku dikişi) ve bir şerit çizgisini
kapsıyor. **DCF, hedefin düz renkli, düşük kontrastlı kutusundan, yakındaki
daha yüksek kontrastlı statik bir zemin özelliğine kaymış** ve orada
**kararlı bir şekilde kilitli kalmış** — PSR bu yanlış kilitte bile yüksek
(t=45'te 24.7).

**Aynı desen A1, A3, A6'da (hepsi gt_L ≈ 60+ px, "küçük hedef" değil)
neredeyse özdeş kopuş karelerinde tekrarlanıyor** (A1/A6: [26, 113] — birebir
aynı, çünkü aynı kamera+hedef yörüngesi, aynı doku tohumu; çeldirici bu erken
kopuşu etkilemiyor). A4 (irtifa salınımı) **9 kez** kopuyor — bu deseni
tekrarlayan bir döngü mü yoksa ayrı bir mekanizma mı olduğu **derinlemesine
incelenmedi** (§6 Sınırlar).

> **Bu, A9/A10/A10.1'in hiçbirinde görülmeyen YENİ bir arıza modudur.**
> VisDrone'un kompozit yatağında `renk_dcf` çekirdeği hiç bu şekilde bir
> statik zemin özelliğine kaymadı (VisDrone'un gerçek fotoğraflarında böyle
> keskin, yapay-görünümlü yüksek-kontrast çizgiler yok). Gazebo'nun
> prosedürel doku üreticisi (`gazebo/dunya_uret.py:zemin_dokusu`) DCF için
> **hedeften daha çekici bir tuzak** üretiyor.

---

## 4. H0 vs H(hakem) — ana tablo

| senaryo | H0 IoU | H(hakem) IoU | H0 YKtak | H(hakem) YKtak | H0 kopuş | H(hakem) kopuş | mod (H0→H) |
|---|---|---|---|---|---|---|---|
| A1_taban | 0.066 | 0.064 | 198 | 149 | 2 | 1 | A→A |
| A2_kucul | 0.090 | 0.090 | 356 | 356 | 1 | 1 | A→A |
| A3_yaw | 0.242 | 0.242 | 154 | **50** | 2 | 2 | **B→A** |
| A4_irtifa | 0.293 | 0.292 | 100 | 100 | **9** | **7** | B→B |
| A5_kucul_yaw | 0.055 | 0.056 | 409 | 340 | 1 | 1 | A→A |
| A6_celdirici | 0.066 | 0.064 | 137 | 149 | 2 | 1 | A→A |
| **toplam** | **ort 0.135** | **ort 0.135** | **1354** | **1144** | **17** | **13** | |

**K2 (mutlak, toplam bazlı):** güvenli yanlış kilit **1354 → 1144**,
**toplamda azaldı** — geçiyor. Ama hücre bazında A6'da **arttı** (137→149);
bu, Mod A histerezisinin bu senaryoda tak.durum'u erken ARAMA'ya iterek
farklı bir yanlış-yörüngeye yönlendirdiğinin işareti (A1 ile A6 H0'da farklı
YKtak veriyordu — 198 vs 137 — hakem sonrası ikisi de 149'a yakınsıyor,
tesadüf değil: Mod A tetikleyicisi celdirici'den bağımsız aynı P-izi
dinamiğini görüyor).

**K3a (kopuşlu hücre azalması):** 17 → 13, **geçiyor**.
**K3b (≥2 ayrı dizide IoU artışı):** yalnızca A5'te marjinal artış
(+0.001) var, **geçmiyor**.
**K5:** `recovery_deneme = 0` (< 5) → **SINANMADI**.
**K1 / K6:** **ölçülemez** — post-hoc "sağlam dizi" (H0'da hiç kopuş
olmayan senaryo) **YOK**; 6 senaryonun 6'sı da KOPAN.

> Bu KOL 0'ın kendisi kabul ölçütüne tabi değildir (ön-kayıt §6) — yukarıdaki
> hesap yalnızca A9/A10.1 ile aynı muhasebeyi Gazebo'da göstermek içindir.

---

## 5. `bho`, PSR, P izi — kısa not

`bho` (boyut/GT oranı) A1'de p50=2.85–3.03 — **VisDrone'daki ~1.98'in
belirgin üstünde**; DCF'nin §3'teki kutu büyümesi bunu doğrudan besliyor.
P izi p95 A1'de **~14 000**, A3'te H1 kolunda **782 302** — Mod A'nın kendi
GİRİŞ eşiğinin (54.08, VisDrone'dan) çok üstünde; bu sayılar Gazebo'nun kendi
açık-çevrim dağılımıyla **yeniden kalibre edilmeden** kullanılamaz (K5/D2
hükmü burada da geçerli — yeni sabit uydurulmadı, ama mevcut sabitlerin bu
yatakta hâlâ anlamlı olduğu iddia edilmiyor).

---

## 6. Sınırlar

Sahte-ego ölçümü kilitlenmemiş, saf problobu (§1 notu) · A4'ün 9 kopuşunun
kök nedeni derinlemesine incelenmedi · A2/A5'in kopuş zamanlaması (t=103,
t=53) küçük-hedef eşiğiyle (A7: 14–20 px) ilişkilendirilmedi, ayrı bir
analiz ister · yalnızca A5_baseline (A10.1 EK-3 kararı) · IMU henüz
kullanılmadı (KOL 1) · zamansal hareket biriktirme henüz yok (KOL 2) ·
tek koşum, tekrar edilmedi · Pi Zero 2 W'ye ekstrapolasyon yapılmadı.

---

## 7. DUR

Kalıcı değişiklik yok (`takip/` değişmedi, kabul zaten tabi değildi).

**Sıradaki (KOL 1'e taşınan sorular):**
- KOL 1'in IMU-tabanlı ego'su, kilitliyken de aynı alt-piksel doğruluğu
  koruyor mu (dışlama maskesi etkisi burada henüz ölçülmedi)?
- §3'ün DCF-doku-kayması arızası KOL 1/2/3'te de tekrar edecek mi — bu,
  KOL 2'nin (zamansal hareket biriktirme, hareket TABANLI aday üretimi)
  neden özellikle ilgili olduğunu gösteriyor: hareket biriktirme statik
  zemin özelliklerine bu şekilde kanmaz.
