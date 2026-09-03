# Proje durumu ve revize roadmap

**Salt okunur durum analizi.** Kod değiştirilmedi, dosya düzenlenmedi, deney
koşulmadı, ölçüm yapılmadı, commit/push yok. Yalnızca repo, dokümanlar,
raporlar ve şimdiye kadar üretilmiş `cikti/` sonuçları kullanıldı.
`takip/` md5'leri Deney 2 baseline'ı ile 6/6 aynı.

---

# 1. ORİJİNAL PROJE PLANI (repodan, olduğu gibi)

Kaynak: `README.md:5-33` ("Proje Durumu") ve `README.md:429-444`
("Sonraki Adımlar"). Terminoloji değiştirilmedi.

| aşama | orijinal tanım (README) | README'deki işaret |
|---|---|---|
| Aşama 0 | Baseline (13 Ağustos 2026) — `CHANGELOG.md:260` | — |
| **Aşama 1** | Mevcut sistem analizi ve simülasyon baseline'ı | ✅ |
| **Aşama 2** | Sim / video / kamera kaynak soyutlaması | ✅ |
| **Aşama 3** | VisDrone gerçek aerial veri entegrasyonu | ✅ |
| **Aşama 3.7** | Gerçek veri hata teşhisi | ✅ |
| **Aşama 3.8** | False-lock / bağımsız doğrulama | ✅ |
| **Aşama 3.9** | *"Hızlı hedef hareketi ve hareket kestirimi"* — `README:18`; ayrıntı `README:431`: **"Kilit sonrası hız kestirimi; arama penceresi hedefin hareketine göre konumlanmalı (268/31)."** README notu: *"A3.8'in çıktısı olarak tanımlandı; kodda karşılığı **henüz yok**"* | 🔄 aktif |
| **Aşama 3.10** | *"Kontrollü simülasyonun genişletilmesi"* — `README:433`: **"Hızlı hedef ve duran hedef senaryolarının sim tarafında tekrarlanabilir hale getirilmesi."** | ⏳ |
| **Aşama 4** | Kullanıcı hedef seçimi (fare ile seçim; `hedef_secici` sözleşmesi hazır) | ⏳ |
| **Aşama 5** | YOLO detection | ⏳ |
| **Aşama 6** | VisDrone fine-tuning (`visdrone_det`, 548 görüntü hazır) | ⏳ |
| **Aşama 7** | ByteTrack / BoT-SORT | ⏳ |
| **Aşama 8** | Target Lock + MOT ID | ⏳ |
| **Aşama 9** | Hibrit seyrek detection + klasik tracker | ⏳ |
| **Aşama 10** | Recovery / oklüzyon (duran hedef için görünüm tabanlı aday üretimi) | ⏳ |
| **Aşama 11** | Raspberry Pi optimizasyonu (320×240 giriş + ROI-only işleme, cihazda gerçek ölçüm) | ⏳ |

> **Dikkat:** Orijinal planda **Gazebo hiçbir aşamada geçmiyor.** Planlı
> simülasyon aşaması A3.10'dur ve orada da *"sim tarafında"* denmektedir —
> yani `sim/world.py` sentetik simülatörü. Gazebo, plan dışından A3.9'a
> çekilmiştir (bkz. §4).

---

# 2. GERÇEKTE YAPILANLAR (kronolojik, kanıtlı)

Ortak kayıtlar: tüm A3.9 çalışması **commitsizdir** — son commit `9a058c7`
(*"docs: add requirements.txt and clone-to-run instructions"*, A3.8 sonu).
Çalışan ağaçta 85 değişik/izlenmeyen yol var; `takip/` altında yalnızca
**Deney 2**'nin değişikliği duruyor (`cekirdekler.py`, `izleyici.py`).

## 2a. A3.9 Faz A — Gazebo tabanı

| | |
|---|---|
| amaç | Kontrollü kamera hareketi altında **kusursuz GT** ile referans tablo dondurmak (`BENCHMARK_GAZEBO.md:12`) |
| değişiklik | **YOK** — *"Bu tablo A3.8 takipçisiyle, `takip/` altındaki beş dosyanın hiçbirine dokunulmadan alınmıştır"* |
| sonuç | `BENCHMARK_GAZEBO.md` (24 Ağustos 2026) |
| hüküm | **başarılı** (altyapı) · geri alma yok · commit yok |
| açıkladığı | Gazebo hattının kendisi takipçiye regresyon getirmiyor (G0 sağlık testi) |

## 2b. A3.9 Faz B — 22 senaryo teşhisi

| | |
|---|---|
| amaç | G1–G7 × {yumuşak, agresif} + 7 ek koşum ile kopma eşiklerini süpürmek |
| değişiklik | **YOK** — *"Bu faz yalnızca teşhistir; çözüm Faz C'de"* |
| sonuç | `BENCHMARK_GAZEBO_FAZB.md`; **ana bulgu: ego-motion katmanı sağlam**, K1–K4 hiçbir senaryoda ateşlemedi; koparan tek kamera kanalı **dönme** |
| hüküm | **başarılı** · commit yok |
| açtığı | *"A3.9'da ego-motion katmanına dokunmak yanlış olur"* (`FAZB:224`) |

## 2c. A3.9 Faz C — çözüm denemeleri (Deney 1 … 4U)

| deney | amaç | kod değişti mi | sonuç | hüküm | geri alındı mı |
|---|---|---|---|---|---|
| **1** | DCF şablonunu ego dönmesiyle hizala | evet | fikir doğru, uygulama iki yerden sızdı | başarısız | **evet** |
| **2** | Kapalı çevrim açı kestirimi | **evet** | 32 senaryonun 30'u bit-birebir; G3_kritik drift kalktı | **başarılı — KORUNDU** | hayır |
| **3** | Açı referansı = ego entegrasyonu | evet | açı hatası p95 13.01→1.74 ama IoU gelmedi (0.704→0.702) | başarısız | **evet** |
| **4A** | Kutu en-boyunu açıdan türet | evet | R²=−86; G3_agresif 0.760→0.540 | başarısız | **evet** |
| **4B** | Merkez teşhisi | hayır (salt okunur) | bias'ın kökü DCF yamasındaki arka plan bulaşması (`dolgu=2.0` → yamanın ~%75'i arka plan) | teşhis | — |
| **4C** | Rafine ağırlığı sabit 0.17 | evet | 117/23 çöktü | başarısız | **evet** |
| **4D** | Rafine ağırlığı **adaptif** | hayır | **ayırt edici sinyal yok** | teşhis (negatif) | — |
| **4E** | DCF padding süpürmesi | hayır | Gazebo'ya özgü; kilit/drift bozuyor | elendi | — |
| **4G** | DCF bias ↔ şablon hafızası teşhisi | hayır | ilişki var | teşhis | — |
| **4H** | Öğrenme **hızı** (lr) nedenselliği | evet | gerçek veride **ters** yönde etki | başarısız | **evet** |
| **4I** | VisDrone izlenebilirlik envanteri | hayır | 7 dizinin 4'ü kullanılamaz; karar havuzu **117/23 + 137/12** (+305/5 destek) | teşhis | — |
| **4J** | DCF bias çapraz kaynak | hayır | öğrenme–bias ilişkisi gerçek veride sağlam **asosiyasyon** | teşhis | — |
| **4K** | Öğrenme **zamanı** kapısı | evet | kapı sağlıklı takipte **hiç kapanmıyor** (0/342) | başarısız (no-op) | **evet** |
| **4L** | Yanlış-kilit envanteri + ±1 px kaos probu | hayır | 22 Gazebo'nun 21'inde YK yok; **117/23 ±1 px'te 0.701→0.111** (havza sınırı) | teşhis | — |
| **4M** | G6 kontrollü çifti | hayır | ilk ayrışan değişken: **DCF along-track artığı, kare 142**; ego/KF değil | teşhis | — |
| **4N** | `rafine_kutu` neden ölüyor | hayır | **R6 renk kapısı** (%86); üst akış: birleşme / parçalanma / referans renk | teşhis | — |
| **4O** | DCF ayrışma atomları | hayır | fark **alt-piksel `dx`**'te; 2×2: değişimin **%94'ü yamadan**, %0.5'i şablondan | teşhis | — |
| **4P** | Çeldiricisiz sahne (nedensellik) | hayır (yeni **kayıt** üretildi) | çeldirici çıkarılınca kopuş **kayboluyor** → G6_agresif_durakli'nin YK'si **sahne artefaktı** | **nedensellik kanıtlandı** | — |
| **4Q** | Çeldirici mekanizmasının genellemesi | hayır | 6 epizottan **1'ini** açıklıyor (%23.7); baskın aile **BOYUT** | teşhis | — |
| **4R** | Boyut hatasının kaynağı | hayır | üretici **`_boyut_tazele`** (×0.890/×1.336/×1.807); `_boyut_sinirla` **×1.000** | teşhis | — |
| **4S** | Çapa karşıt-olgusu | hayır (takipçi hiç koşmadı) | sabit çapa 182/127'de **sıfır etki**; band da yetersiz | hipotez reddedildi | — |
| **4T** | Bozuk rafine ayırt edilebilir mi | hayır | sinyal var (havuz AUC 0.890) ama **mevcut kapı bozukların %100'ünü geçiriyor** | teşhis | — |
| **4U** | Oran kapısını daraltma **A/B** | **evet** | 137/12 IoU 0.548→**0.190**; G3_kritik −0.008 | **başarısız** | **evet** |
| **D1** | `adaylar()` mutlak boyut verir mi | hayır | bağımsız + mutlak **ama yanlış** (h/GT 0.30; kullanılabilirlik %7) | teşhis (negatif) | — |
| **D2\*** | Yeni ölçüm envanteri | hayır | **A sınıfı boş**; depoda kontur/kenar/yoğun akış/ölçek araması **hiç yok** | teşhis | — |
| **E tasarım** | Yeni boyut ölçümü tasarımı | hayır | önerilen: ego RANSAC outlier kümesinin uzamı; yedek: akış artığı | tasarım | — |

**Commit/push:** yukarıdakilerin **hiçbiri** commit edilmedi.

---

# 3. A3.8 DURUMU

**Çözdüğü problem** (`CHANGELOG.md:3-11`): A3.7, `uav0000268_05773_v`'de
sistemin 978 karenin %99'unda "KİLİTLİ" dediğini ama IoU'nun 0 olduğunu
ölçmüştü. Kök neden: **PSR bir kimlik ölçüsü değil, filtrenin iç tutarlılık
ölçüsüdür** — filtre yol dokusuna kayınca yolu öğreniyor ve PSR 12'den 46'ya
*tırmanıyor*.

**Tamamlanan:** `KİLİTLİ` durumuna PSR'dan bağımsız **iki denetleyici**
(dondurulmuş imza testi + zemine çakılma testi) ve yanlış alarmı önleyen üç
kapı. Bunlar bugün hâlâ `izleyici.py:338 _bagimsiz_dogrula` içindedir.

**A3.8 baseline'ı bugün hangi kod durumu?** Son commit `9a058c7`'nin
`takip/` durumu. Faz A ve Faz B tabloları bu durumla alınmıştır.

**Neden Deney 2 baseline olarak kullanılıyor?** Faz C'de yapılan **tek kabul
edilmiş değişiklik** Deney 2'dir (kapalı çevrim açı kestirimi;
`cekirdekler.py` + `izleyici.py`, 32 senaryonun 30'u bit-birebir). Ondan
sonraki her deney "değişiklik yok" iddiasını `takip/` **md5'lerinin Deney 2
durumuyla 6/6 aynı** olmasıyla kanıtladı. Yani Deney 2, A3.8'in üzerine
eklenen ve *geri alınmayan* tek fark olduğu için Faz C'nin referans noktasıdır.

---

# 4. A3.9 DURUMU

## 4a. Orijinal tanım (dar)

> **"A3.9 — hızlı hareket / hareket kestirimi. Kilit sonrası hız kestirimi;
> arama penceresi hedefin hareketine göre konumlanmalı (268/31)."**
> — `README.md:431`

Yani orijinal A3.9 **tek bir diziye** (268/31) ve **tek bir mekanizmaya**
(hızlı hedef → arama penceresi konumlandırma) bağlıydı.

## 4b. Genişleme sonrası fiilî kapsam

A3.9 üç faza bölündü: **Faz A** (Gazebo tabanı) → **Faz B** (22 senaryo
teşhisi) → **Faz C** (çözüm; Deney 1–4U + D1/D2 + tasarım).

| konu | A3.9'a girdi mi | plan içi mi |
|---|---|---|
| **hızlı hedef** | evet — orijinal amaç | **plan içi** |
| **hedef hareketi** | evet (G6, G7 aileleri) | genişleme |
| **kamera yaw** | evet (G4/G5 aileleri; Faz B'nin ana bulgusu dönme) | **plan dışı → çekildi** |
| **kamera pitch/roll** | evet (Faz B senaryoları) | **plan dışı → çekildi** |
| **çapraz kamera hareketi** | evet (G6 = kamera + hedef birlikte) | **plan dışı → çekildi** |
| **ego-motion** | evet — Faz B ölçtü ve **temize çıkardı** | **plan dışı → çekildi** |
| **Gazebo** | evet — Faz A/B/C'nin tamamı | **plan dışı → çekildi** (planda Gazebo hiç yok; planlı simülasyon A3.10 ve *sim tarafında*) |
| **gerçek VisDrone** | evet (4I havuzu, 117/23 + 137/12) | plan içi (A3 mirası) |
| **DCF** | evet (4B/4G/4J/4M/4O) | **plan dışı → çekildi** |
| **Kalman** | evet (yalnızca gözlem; hiç değiştirilmedi) | **plan dışı → çekildi** |
| **yanlış kilit** | evet (4L/4P/4Q) | **A3.8'in konusuydu, A3.9'a taştı** |
| **drift** | evet (tüm Faz C) | genişleme |
| **boyut problemi** | evet (4A/4C/4R/4S/4T/4U/D1) — **Faz C'nin sonunda baskın konu oldu** | **plan dışı → çekildi** |

## 4c. Hüküm: **KISMEN TAMAMLANDI**

**Kanıt:**

* **Tamamlanan:** teşhis tarafı bitti ve kapandı — `A39_FAZ_C_KARAR_KAPANIS.md`
  11 kanıtlanmış mekanizma, 14 reddedilmiş hipotez ve 5 açık kalem listeliyor.
* **Tamamlanmayan (asıl amaç):** orijinal A3.9 hedefi **268/31'in hızlı
  hedefini geri bulmaktı**. 4I bu diziyi **karar dışı** ilan etti (GT
  görünürlüğü 0.26, IoU≈0 oranı %100) ve dizi bir daha karar kaynağı olarak
  kullanılmadı. Yani A3.9'un **orijinal problemi hâlâ çözülmedi**;
  README:18'in *"kodda karşılığı henüz yok"* notu **bugün de geçerli**:
  kilit sonrası hız kestirimine ya da arama penceresinin hedef hareketine göre
  konumlandırılmasına dönük **hiçbir kod eklenmedi**.
* **Tek kalıcı kazanım:** Deney 2 (açı) — ve 4M/4O ölçtü ki karar
  kaynaklarında açı araması karelerin **%0–9.8**'inde etkin.
* **Yeni açılan ve kapanmayan cephe:** boyut ölçümü (§6, P0).

---

# 5. A3.10 VE SONRASI

| aşama | orijinal amaç | beklenen çıktı | mevcut durum | A3.9 bağımlılığı | şimdi başlanabilir mi | önce çözülmesi gereken |
|---|---|---|---|---|---|---|
| **A3.10** | Hızlı ve duran hedef senaryolarının **sim tarafında** tekrarlanabilir hale getirilmesi | `sim/senaryolar.py` içinde yeni testler | **başlamadı**; ama Gazebo tarafı fiilen bunun yerini doldurdu (22 senaryo + 3 ek kayıt) | orta — A3.9 senaryo altyapısını zaten kurdu | **EVET** | yok |
| **A4** | Kullanıcı hedef seçimi (fare) | `hedef_secici` yerine fare seçici | başlamadı; **sözleşme hazır** (`main.py:61-88`, `kos(..., hedef_secici=...)`) | **yok** | **EVET** | yok |
| **A5** | YOLO detection | Detector entegrasyonu | **BAŞLAMADI** | yok (paralel hat) | evet ama donanım kararı gerekiyor (§9) | Pi Zero 2W'de derin öğrenme kısıtı |
| **A6** | VisDrone fine-tuning (`visdrone_det`, 548 görüntü hazır) | Eğitilmiş ağırlık | başlamadı | A5 | hayır | A5 |
| **A7** | ByteTrack / BoT-SORT | MOT hattı | başlamadı | A5/A6 | hayır | A5, A6 |
| **A8** | Target Lock + MOT ID | Kimlik yönetimi | başlamadı | A7 | hayır | A7 |
| **A9** | Hibrit seyrek detection + klasik tracker | Karma hat | başlamadı | A5–A8 | hayır | A5–A8 |
| **A10** | Recovery / oklüzyon (duran hedef için **görünüm tabanlı** aday üretimi) | Yeniden yakalama | başlamadı | **A3.9'un yanlış-kilit bulgularına bağlı** | kısmen | 182/127'nin duran hedefi (README bilinen sınır #2) |
| **A11** | Raspberry Pi optimizasyonu (320×240 + ROI-only, **cihazda gerçek ölçüm**) | Cihaz ölçümü | başlamadı | zayıf | **EVET** (donanım varsa) | yok |

**Gazebo'nun planlı yeri:** **yok.** Orijinal planda Gazebo hiçbir aşamada
geçmiyor; A3.10 açıkça *"sim tarafında"* diyor. Gazebo A3.9 Faz A'da
plan dışından eklendi ve bugün 24 kayıt dizini + 5 modüllük bir altyapıya
dönüştü. **Bu bir kazanımdır ama plana geri yazılmamıştır.**

---

# 6. TEKNİK PROBLEM ENVANTERİ

| # | problem | sınıf | dayanak |
|---|---|---|---|
| 1 | **DCF merkez biası** | **KANITLANDI** | 4B, 4G, 4J, 4M (kare 142 ayrışması), 4O (%94 yama) |
| 2 | **DCF yama / arka plan etkisi** (`dolgu=2.0` → yamanın ~%75'i arka plan) | **KISMEN KANITLANDI** — kök neden olarak işaret edildi ama doğrudan sınanmadı; 4E padding süpürmesi elendi | 4B notu, 4E |
| 3 | **`rafine_kutu` kalitesi** | **KANITLANDI** | 4N (R6 %86), 4R (GT 57 px iken 106–174 px), 4T (mevcut kapı bozukların %100'ünü geçiriyor) |
| 4 | **`_boyut_tazele` hatayı üretiyor** | **KANITLANDI** | 4R log ayrıştırması artıksız (×0.890/×1.336/×1.807) |
| 5 | **`_boyut_sinirla` inert** | **KANITLANDI** | 4R (kırpma 0/293, 0/140, 0/293, 4/334), 4S (çapa değişse de düzelmiyor) |
| 6 | **Yanlış kilit** | **KANITLANDI ama yeniden tanımlandı** — Gazebo'daki tek örnek **sahne artefaktı** (4P); gerçek veride baskın aile **boyut** (4Q) | 4L, 4P, 4Q |
| 7 | **Kamera hareketi** (öteleme) | **ELENDİ** — 80 m/s'ye kadar koparmıyor; ego kanalı sağlam | Faz B (K1–K4 hiç ateşlemedi), 4M (`ego_gt` 0.01 px içinde özdeş) |
| 8 | **Kamera dönmesi** | **KANITLANDI**, kısmen çözüldü (Deney 2) | Faz B ana bulgusu; Deney 2 |
| 9 | **Hedef hareketi / yavaşlama** | **KISMEN KANITLANDI** — pencere düzeyinde ilişkili ama senaryo içi kontrol nedenselliği çürüttü | 4M (§H.3: aynı dizide ilk duruş sorunsuz geçiliyor) |
| 10 | **Başlangıç kutusu hassasiyeti** | **KANITLANDI** | 4L (117/23: ±1 px → IoU 0.701 → 0.111), 4R (182/127 kilit kutusu GT'nin 0.62'si) |
| 11 | **117/23 havza kırılganlığı** | **KANITLANDI** | 4L (havza sınırı 0.5–1 px arasında; 8 komşunun 1'i çöküyor) |
| 12 | **137/12 regresyon hassasiyeti** | **KANITLANDI** | 4U (tek kapı değişikliği IoU −0.358) |
| 13 | **Gazebo ↔ VisDrone genelleme problemi** | **KANITLANDI** | 4C/4D/4E/4H hepsi aynı duvara çarptı (`DENEY_04E:son`); 4I kontrast ekseninin bunu açıklayıp açıklamadığını **ölçmedi** |
| 14 | **Bağımsız mutlak boyut ölçümünün eksikliği** | **KANITLANDI** | D1 (`adaylar()` yanlış), D2 (A sınıfı boş), 4S (çapa bağımsız değil) |
| 15 | **Pi Zero 2W maliyeti** | **HENÜZ AÇIK** — README:405-407: *"Pi sayıları **ekstrapolasyondur, cihazda ölçüm yapılmamıştır**"* | README bilinen sınır #5 |
| 16 | **Gerçek drone kamera / latency riski** | **HENÜZ AÇIK** — repoda hiç ölçüm yok | — |
| 17 | **ARAMA modu maliyeti** (4K'da p50 12.9→43.4 ms) | **KANITLANDI**, çözülmedi | README bilinen sınır #3 |
| 18 | **Çözünürlük kalibrasyonu eksik** | **KANITLANDI**, çözülmedi | README bilinen sınır #4 |
| 19 | **Ego ölçek yanlılığı** (~%8/300 kare) | **KANITLANDI**, tasarımla dolanıldı (integre edilmiyor) | README son not, `egomotion.py:68-72` |

---

# 7. KESİN OLARAK KAPANMIŞ — BİR DAHA UĞRAŞILMAMALI

| konu | neden kapandı |
|---|---|
| **Ego-motion katmanına dokunmak** | Faz B: K1–K4 hiçbir senaryoda ateşlemedi; 4M: iki senaryoda `ego_gt` 0.01 px içinde özdeş, `ego_artik` kopuşta **azalıyor** |
| **Açının ego'dan biriktirilmesi** (Deney 1, 3) | Açık çevrim sızıntı üretiyor; Deney 3'te açı 7.5× düzeldi ama **IoU gelmedi** |
| **Kutu şeklinin açıdan türetilmesi** (4A) | R² = −86; G3_agresif 0.760 → 0.540 |
| **Rafine ağırlığı** (sabit 4C / adaptif 4D) | 4C 117/23'ü çökertti; 4D'de **ayırt edici sinyal yok** |
| **DCF padding süpürmesi** (4E) | Gazebo'ya özgü; kilit/drift bozuyor |
| **Öğrenme hızı ve zamanı** (4H, 4K) | 4H gerçek veride **ters** etki; 4K kapı sağlıklı takipte **hiç kapanmıyor** |
| **`rafine_kutu` ölümünün kök neden olması** (4N) | Kontrol **aynı ölümü** yaşıyor ve kopmuyor |
| **Çeldirici bastırma müdahalesi** (4Q) | Mekanizma 6 epizottan 1'ini açıklıyor; o da sahne artefaktı |
| **`_boyut_sinirla` çapasının kök neden olması** (4S) | Sabit çapa 182/127'de **sıfır etki**; band GT'nin meşru değişimini keserdi |
| **Oran kapısını daraltmak** (4T/4U) | Kapalı çevrim: 137/12 IoU 0.548 → 0.190 |
| **`HareketTespit.adaylar()`ı boyut ölçümü olarak kullanmak** (D1) | Bağımsız + mutlak ama **yanlış** ve %7 kullanılabilir |
| **`G6_agresif_durakli`'yi "duran araç sınırı" örneği saymak** (4M/4P) | Kopuş araç 3.84 m/s'de başlıyor; asıl neden **çeldirici konjonksiyonu** = sahne artefaktı |
| **Ölçek-uzayı araması (C ailesi)** | Z1/Z7'yi tanım gereği ihlal ediyor; ölçek çarpımsal ve sınırsız (4R'deki ×1.807 tam bu kip) |

> **Ortak ders (5 kez tekrarlandı):** türetilmiş bir büyüklük bağımsız bir
> ölçümün yerine geçtiğinde ya da bir kapı kendi etkilediği büyüklüğe
> baktığında çevrim kapanır (Deney 1, 3, 4A, 4R/4S, 4U).

---

# 8. AÇIK PROBLEMLER (öncelik sıralı)

## P0 — kritik

**P0.1 — Bağımsız, mutlak boyut ölçümünün olmaması**
*Neden önemli:* 4Q'ya göre gerçek veride yanlış kilidin **baskın ailesi
boyut**tur (`tavan_iou = IoU`, merkez hatası 1.9–2.5 px). 4R üreticiyi,
4S/4T/4U ise mevcut sinyallerle düzeltilemeyeceğini gösterdi. D2: A sınıfı boş.
*Hangi aşamada:* A3.9'un kapanışı (revize A3.9c).
*Gerçek drone:* kutu 1.9× şişerse hedef merkezi hâlâ doğru olsa bile
gimbal/uçuş komutu üretilecekse ölçek hatası doğrudan komuta taşınır — **etki
yüksek, henüz ölçülmedi**.
*Gazebo:* G6_agresif'te IoU 0.618, kutu/GT 1.88.
*Gerçek veri:* 182/127 kutu GT'nin yarısı, 305/5 2.7 katı.

**P0.2 — A3.9'un ORİJİNAL problemi hiç çözülmedi (hızlı hedef, 268/31)**
*Neden önemli:* Aşamanın tanımı bu. `README:18` notu hâlâ geçerli: kodda
karşılığı yok. 4I diziyi karar dışı ilan etti ama **problemi çözmedi**.
*Hangi aşamada:* revize A3.9a.
*Gerçek drone:* hızlı hedef gerçek uçuşta normaldir; kare başına yer
değiştirme kutu eninin %61'i olduğunda mevcut hat hedefi tek karede kaybeder.
*Gazebo:* G7 ailesi (ani hedef ivmesi) kaydı **var**, bu açıdan hiç
analiz edilmedi.
*Gerçek veri:* 268/31 (IoU 0.005).

## P1 — yüksek

**P1.1 — DCF yamasındaki arka plan bulaşması (`dolgu = 2.0`, ~%75 arka plan)**
*Neden:* 4B merkez biasının kökü olarak işaret etti; 4O ayrışmanın **%94'ünün
yamadan** geldiğini ölçtü. 4E yalnızca padding **süpürmesini** eledi, bulaşmayı
hedefleyen bir değişiklik hiç denenmedi.
*Aşama:* revize A3.9c sonrası. *Gerçek drone:* düşük kontrastlı gerçek
görüntüde etki daha büyük (117/23 kontrastı 5.2).

**P1.2 — Başlangıç kutusu / havza kırılganlığı (117/23)**
*Neden:* Karar dizisinin sonuçları **tek havzanın** özelliği; ±1 px → 0.701 →
0.111. Gerçek uçuşta ilk kutu kullanıcı ya da dedektörden gelecek (A4/A5) ve
1 px hassasiyetle gelmeyecek.
*Aşama:* A4 (kullanıcı seçimi) ile birlikte.

**P1.3 — Cihazda hiç ölçüm yapılmamış olması (Pi Zero 2W)**
*Neden:* Tüm FPS sayıları WSL2'de ve ekstrapolasyon. A11 kararlarının hepsi
bu ölçüme bağlı.
*Aşama:* A11 — ama **şimdi başlatılabilir**, A3.9'u beklemez.

## P2 — orta
ARAMA modu maliyeti (README #3) · çözünürlük kalibrasyonu (README #4) ·
Gazebo↔VisDrone genelleme ekseninin (kontrast) ölçülmemiş olması (4I'nın
açtığı, kapatılmayan soru) · 182/127 duran hedefin geri bulunamaması
(README #2 → A10).

## P3 — sonradan
A5–A9 hattının tamamı (YOLO/MOT) · A3.10'un sim tarafındaki karşılığı ·
`gazebo:X` kısa biçiminin büyük harf hatası (`kaynak.py:281`, kozmetik).

---

# 9. GERÇEK DRONE KISITLARI (kullanıcıdan gelen donanım + repo kanıtı)

Donanım (kullanıcı beyanı): **GEPRC TAKER F405 BLS 50A** stack ·
**Raspberry Pi Zero 2 W** · **iFlight XING-E Pro 2207 1800KV** ·
**Raspberry Pi AI Camera Module** · 5 inch · ~750 g · **Betaflight**
(ArduPilot/PX4 **kullanılmayacak**).

| konu | bilinen | durum |
|---|---|---|
| **Onboard CPU maliyeti** | WSL2'de 309–338 FPS (bu oturumda G6 koşumu 309.9 FPS, gecikme ort 3.23 ms). README ekstrapolasyonu: **Pi Zero 2 W ≈ 28 FPS (×12)** | **HENÜZ ÖLÇÜLMEDİ** — cihazda ölçüm yok (README #5) |
| **Kamera FPS / çözünürlük gereksinimi** | Repo 640×480 (Gazebo) ve 960 px genişlik (VisDrone) ile çalışıyor; A11 planı 320×240 + ROI-only | Gereksinim **belirlenmedi**; Pi AI Camera'nın hangi modda kullanılacağı **kararlaştırılmadı** |
| **Latency** | Uçtan uca gecikme (sensör → görüntü → takip → çıktı) | **HENÜZ ÖLÇÜLMEDİ** — repoda yalnızca *işlem* gecikmesi var (p50 2.54 ms), kamera/aktarım gecikmesi yok |
| **Gerçek zamanlı takip** | Mevcut hat kayıt-sonra-oynat; **canlı kamera yolu var** (`kaynak.py` `camera` dalı, `calistir.py --canli`) ama **gerçek kamerayla hiç test edilmedi** | **HENÜZ ÖLÇÜLMEDİ** |
| **Titreşim** | 5 inch + 2207 1800KV motorlar; rolling-shutter jello riski | **HENÜZ ÖLÇÜLMEDİ** — repoda titreşim modeli/senaryosu yok |
| **Motion blur** | Gazebo senaryolarında **yok** (render blur'suz); VisDrone'da doğal olarak var ama ayrıştırılmadı | **HENÜZ ÖLÇÜLMEDİ** |
| **Yaw / pitch / roll** | Faz B'de **kontrollü olarak süpürüldü** (G4/G5 aileleri); ana bulgu: koparan kanal **dönme** (~120 °/s, kare başına ~4°) | **KISMEN ÖLÇÜLDÜ** (simülasyonda) |
| **Kamera hareketi (öteleme)** | 80 m/s'ye kadar koparmıyor | **ÖLÇÜLDÜ** (Faz B) |
| **Veri akışı** | Betaflight ile Pi arasında bağ **tanımlanmadı**; repo'da uçuş kontrolüne hiçbir çıktı yok | **YOK** |
| **Uçuş kontrolüne bağlanabilecek noktalar** | `main.kos` her karede `sonuc` sözlüğü üretiyor (`kutu`, `durum`, `psr`, `merkez`) — bir MSP/serial köprüsünün tüketebileceği tek nokta burasıdır | **TASARLANMADI** |

> **Pi AI Camera notu:** bu modül sensör üstünde hızlandırıcı taşır; teoride
> A5'in detection yükünü CPU'dan alabilir. Ancak bu projede **hiç
> denenmedi ve ölçülmedi**; roadmap'te varsayım olarak kullanılmamalıdır.

---

# 10. REVİZE PROJE ROADMAP

Orijinal isimler korundu; eklediklerim **REVIZE ALT AŞAMA** olarak işaretli.

### A3.9a — *REVIZE ALT AŞAMA*: orijinal A3.9 borcunu kapat (hızlı hedef)
| | |
|---|---|
| amaç | Kilit sonrası hız kestirimi + arama penceresinin hedef hareketine göre konumlanması (README:431'in tanımı) |
| girdi | G7 ailesi kayıtları (ani hedef ivmesi, **zaten diskte**), sim test'leri |
| çıktı | Hızlı hedefte yeniden yakalama ölçümü |
| kabul | G7_agresif/G7_kritik'te drift yok; 117/23 + 137/12'de regresyon yok |
| veri / ortam | **A) offline + B) Gazebo** |
| kod değişikliği | **evet** (arama adımı) |
| bağımlılık | yok |
| süre | 1–2 tur |
| bitti sayılır | Kabul ölçütü sağlanır **ve** kayıt commitlenir |

### A3.9b — *REVIZE ALT AŞAMA*: Faz C'yi commitle ve dondur
| | |
|---|---|
| amaç | 85 dosyalık commitsiz çalışmayı (Gazebo altyapısı, `deney.py`, 20+ rapor, `cikti/`) kalıcı hale getirmek |
| girdi | mevcut çalışan ağaç |
| çıktı | Deney 2 + Gazebo altyapısı + raporlar commit'te |
| kabul | `takip/` md5 6/6 korunur; baseline metrikleri birebir |
| ortam | **A) offline** |
| kod değişikliği | **hayır** (yalnızca commit) |
| bağımlılık | yok — **şimdi yapılabilir** |
| süre | tek oturum |
| bitti sayılır | commit atıldı, README'ye A3.9 bölümü eklendi |

### A3.9c — *REVIZE ALT AŞAMA*: bağımsız mutlak boyut ölçümü (P0.1)
| | |
|---|---|
| amaç | `E tasarım`ın önerdiği ölçümü **gözlemci olarak** doğrulamak |
| girdi | ego RANSAC nokta çiftleri + inlier maskesi (zaten hesaplanıyor) |
| çıktı | `(w_px, h_px, n_nokta, guven)` + GT karşılaştırma raporu |
| kabul | `D_YENI_BOYUT_OLUM_TASARIMI.md` §3'teki **A1–A5** (koşumdan önce yazılacak) |
| veri | 117/23, 137/12 (birincil), 305/5, G3_agresif, G3_kritik, G0, G6_agresif |
| ortam | **A) offline + B) Gazebo + C) VisDrone** |
| kod değişikliği | **hayır** (gözlemci); entegrasyon ayrı tur |
| bağımlılık | yok |
| süre | 1 tur ölçüm + 1 tur karar |
| bitti sayılır | A1–A5 geçilir **ya da** aday açıkça düşer |

### A3.10 — Kontrollü simülasyonun genişletilmesi *(orijinal)*
Amaç: hızlı ve duran hedef senaryolarının **sim tarafında** tekrarlanabilir
hale getirilmesi. Girdi: `sim/senaryolar.py`. Ortam: **A) offline**.
Bağımlılık: A3.9a. Not: Gazebo tarafı fiilen bu işi görüyor; **karar:
A3.10 ya Gazebo'ya devredilmeli ya da sim tarafında ayrıca yapılmalı** —
bu bir plan kararıdır, teknik zorunluluk değil.

### A4 — Kullanıcı hedef seçimi *(orijinal)*
Sözleşme hazır (`kos(..., hedef_secici=...)`). **Şimdi başlanabilir.**
P1.2 ile birlikte ele alınmalı: seçim 1 px hassas olmayacağı için
başlangıç kutusu duyarlılığı burada ölçülmeli. Ortam: **A + D**.

### A11 — Raspberry Pi optimizasyonu *(orijinal, ÖNE ÇEKİLDİ)*
Amaç: 320×240 + ROI-only, **cihazda gerçek ölçüm**. Bağımlılığı yok, A3.9'u
beklemez ve P1.3'ü kapatır. Ortam: **E) Raspberry Pi**.
Bitti sayılır: Pi Zero 2 W'de gerçek FPS/latency tablosu README'ye girer.

### A5 → A9 — Detection ve MOT hattı *(orijinal, sırası korunur)*
A5 (YOLO) → A6 (fine-tuning) → A7 (ByteTrack/BoT-SORT) → A8 (Target Lock +
MOT ID) → A9 (hibrit). **Ön koşul:** A11'in cihaz ölçümü — Pi Zero 2 W'de
derin öğrenmenin mümkün olup olmadığı (ya da Pi AI Camera'nın sensör üstü
hızlandırıcısının kullanılıp kullanılamayacağı) **ölçülmeden** bu hat
planlanamaz.

### A10 — Recovery / oklüzyon *(orijinal)*
Duran hedef için görünüm tabanlı aday üretimi (README bilinen sınır #2).
Bağımlılık: A3.9c (boyut ölçümü) — çünkü duran hedefte hareket sinyali yok,
geriye görünüm ve **geometri** kalıyor.

### FINAL — *REVIZE ALT AŞAMA*: gerçek drone entegrasyonu
Bkz. §13.

---

# 11. ORTAM AYRIMI

| ortam | tanım | hangi aşamalar |
|---|---|---|
| **A) Offline / kayıtlı veri** | Diskteki PNG/video, takipçi replay eder | A3.9a, A3.9b, A3.9c, A3.10, A4 (geliştirme) |
| **B) Gazebo** | **Kayıt-sonra-oynat.** `python3 -m gazebo.kaydet <SEN>` bir kez koşar, PNG'leri yazar; takipçi Gazebo'ya **canlı bağlanmaz** | A3.9a (G7), A3.9c (çapa senaryoları) |
| **C) VisDrone** | Gerçek hava görüntüsü, karar havuzu **117/23 + 137/12** (+305/5 destek) | A3.9c, A4, A5–A9 doğrulaması |
| **D) Gerçek kamera** | `kaynak.py` `camera` dalı, `calistir.py --canli` — kod var, **hiç test edilmedi** | A4, FINAL |
| **E) Raspberry Pi** | Pi Zero 2 W üstünde ölçüm | A11 (ve A5 kararı) |
| **F) Gerçek drone** | Uçan platform, Betaflight | FINAL |

**Karıştırılmaması gerekenler:** Gazebo **canlı bir simülasyon döngüsü
değildir** (kayıt-sonra-oynat); VisDrone **doğrulama** ortamıdır, geliştirme
ortamı değil (4C ve 4U tam olarak burada düştü); gerçek drone entegrasyonu
ayrı bir ortamdır ve hiçbir aşama "Gazebo'da çalıştı → dronda çalışır"
varsayımıyla kapatılamaz (4C/4D/4E/4H bu duvara çarptı).

---

# 12. OPTUNA'NIN YERİ

**Şimdi kullanılmamalı.** Gerekçe ölçülmüştür: Faz C'de denenen her parametre
ayarı, mekanizması doğrulanmadığı için ya kapalı çevrime ya da kaynaklar arası
genellememeye takıldı. Optuna bu koşullarda **tek bir kaynağa aşırı uyum**
üretir — 4T'nin LOSO ölçümü bunu sayıyla gösteriyor: eşik hangi kaynakta
seçilirse TPR **0.00–1.00** arasında değişiyor.

Aşamaların ayrımı:

| aşama | ne yapar | Optuna? |
|---|---|---|
| **teşhis** | değişkeni ölçer, müdahale etmez (4B/4L/4M/4O/4R/D1) | **hayır** |
| **mekanizma doğrulama** | nedenselliği kontrollü çiftle sınar (4P) | **hayır** |
| **tek değişkenli müdahale** | tek satır, önceden yazılmış ölçütle A/B (4U) | **hayır** |
| **hiperparametre optimizasyonu** | mekanizması doğrulanmış, birbirinden bağımsız knob'ları birlikte ayarlar | **EVET** |
| **final test** | dokunulmamış veri + cihaz | hayır |

**Optuna için uygun aşama: A11 (Raspberry Pi optimizasyonu)** — ve ancak
cihazda gerçek ölçüm alındıktan sonra.

**Optimize edilmesi uygun parametreler** (hepsi maliyet/doğruluk takası,
mekanizması anlaşılmış, kapalı çevrimde değil):
`giriş çözünürlüğü` · `ROI boyutu` · `kayip_periyot` (ARAMA'da arama sıklığı) ·
`dogrulama_araligi` (`_boyut_tazele` periyodu) · `EgoMotion.olcek` (0.5) ·
`max_nokta` / `yenile`.

**Optimize EDİLMEMESİ gerekenler** (mekanizma doğrulanmadı; Faz C'de düştüler):
`rafine_kutu` eşikleri (`p82`, `renk_tol`, oran bandı) · `_boyut_tazele`
ağırlığı · `_boyut_sinirla` bandı · `lr` · `dolgu` · `psr_kilit` /
`psr_supheli` · `zemin_*` ve `kimlik_*` kapıları.

---

# 13. FİNAL DEMO HEDEFİ

Gerçek drone özelliklerine mümkün olduğunca yakın **simülasyon + kamera
görüntüsü + tracker + hedef hareketi + kamera hareketi + hedef kaybı +
yeniden yakalama + FPS/latency + drift/lock ölçümü.**
ArduPilot/PX4 zorunluluğu **yok**; Betaflight kalır, uçuş kontrolü kapsam dışı.

### Minimum uygulanabilir sürüm (MVP)
* Gazebo kaydı üzerinde uçtan uca koşum, HUD'lı **video çıktısı** (bugün
  `--kaydet` ile **zaten mümkün**).
* Kamera hareketi (Faz B ailesi) + hedef hareketi (G6/G7) tek senaryoda.
* Hedef kaybı ve yeniden yakalama **görünür** biçimde (durum makinesi zaten
  LOCKED/SUSPECT/SEARCHING/LOST gösteriyor).
* FPS ve gecikme ekranda (zaten var), drift/lock sayıları koşum sonunda
  (zaten var).
* **Eksik olan tek şey:** boyut ölçümünün düzelmesi (P0.1) — onsuz demo
  "kutu şişiyor ama merkez doğru" görüntüsü verir.

### İdeal sürüm
* MVP + **Pi Zero 2 W üzerinde canlı kamerayla** koşum (A11 + D ortamı).
* Gerçek titreşim/motion blur altında ölçüm (**henüz ölçülmedi**).
* `sonuc` sözlüğünün bir serial/MSP köprüsüne verilmesi (**tasarlanmadı**) —
  uçuş kontrolüne bağlanmadan, yalnızca telemetri olarak.
* 117/23 + 137/12'de regresyonsuz doğrulama.

---

# 14. NET DURUM RAPORU

**ŞU AN:**
Proje genelinde **Aşama 3.9'un içindeyiz** — Faz A ve Faz B bitti, Faz C'nin
**teşhis kısmı kapandı**, çözüm kısmı **açık**. Orijinal A3.9 problemi
(hızlı hedef / 268/31) **hâlâ çözülmedi**.

**TAMAMLANANLAR:**
Aşama 0, 1, 2, 3, 3.7, 3.8 (README'ye göre ✅) · A3.9 Faz A (Gazebo tabanı) ·
A3.9 Faz B (22 senaryo teşhisi) · A3.9 Faz C'nin **teşhis hattı**
(4B/4D/4G/4I/4J/4L/4M/4N/4O/4P/4Q/4R/4S/4T/D1/D2 + karar kapanışı) ·
**Deney 2** (Faz C'nin tek kalıcı kod kazanımı).

**KISMEN TAMAMLANANLAR:**
A3.9 (teşhis bitti, çözüm yok) · yanlış-kilit problemi (A3.8'de kısmen
çözüldü, A3.9'da yeniden tanımlandı) · kamera dönmesi (Deney 2 ile kısmen).

**YAPILMAYANLAR:**
A3.9'un orijinal amacı (hızlı hedef hız kestirimi) · A3.10 · A4 · A5 · A6 ·
A7 · A8 · A9 · A10 · A11 · **cihazda hiçbir ölçüm** · gerçek kamerayla hiçbir
test · Faz C'nin **commit'i**.

**EN KRİTİK 3 PROBLEM:**
1. **Bağımsız mutlak boyut ölçümünün olmaması** (P0.1) — gerçek veride yanlış
   kilidin baskın ailesi; mevcut sinyallerle çözülemeyeceği 4S/4T/4U/D1/D2 ile
   kanıtlandı.
2. **A3.9'un orijinal probleminin hiç ele alınmamış olması** (P0.2) — aşama
   tanımı bu; kodda karşılığı hâlâ yok.
3. **Cihazda hiç ölçüm yapılmamış olması** (P1.3) — A5–A9 ve A11'in tüm
   kararları bu ölçüme bağlı, ve tüm FPS sayıları ekstrapolasyon.

**BİR SONRAKİ AŞAMA:**
**A3.9b** (Faz C'yi commitle ve dondur) → **A3.9c** (bağımsız boyut ölçümünün
gözlemci doğrulaması) → **A3.9a** (orijinal hızlı-hedef borcu).
Paralelde, bağımsız olarak **A11** başlatılabilir (donanım eldeyse).

**İLK YAPILACAK TEK İŞ:**
**A3.9b — 85 dosyalık commitsiz Faz C çalışmasını commitlemek.** Kod
değişikliği içermez, risk taşımaz, ve şu an tüm A3.9 çıktısı (Gazebo
altyapısı, 24 kayıt, 20+ rapor, `deney.py`, `cikti/`) tek bir kaza ile
kaybedilebilir durumdadır.

**A5 (YOLO detection):** **BAŞLAMADI.** Ön koşulu A11'in cihaz ölçümüdür;
Pi Zero 2 W'de derin öğrenmenin mümkün olup olmadığı ölçülmeden
planlanamaz.

**ARTIK GERİ DÖNÜLMEMESİ GEREKEN DENEYLER:** §7'deki 13 kalemin tamamı —
özellikle ego-motion'a dokunmak, açıyı ego'dan biriktirmek, rafine ağırlığını
(sabit ya da adaptif) ayarlamak, padding süpürmek, lr/öğrenme kapısı
denemek, oran kapısını daraltmak, `adaylar()`ı boyut ölçümü sanmak ve
`G6_agresif_durakli`'yi duran-araç örneği saymak.

---

**Bu belgede hiçbir kod değişikliği, deney ya da ölçüm yoktur.**
