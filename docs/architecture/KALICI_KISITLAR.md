# Kalıcı kısıtlar — küçük hedef performansı, gerçek donanım, mimari

**Bu belge bir tasarım kısıtı kaydıdır. Kod değişikliği içermez.** A4'te
uygulama gerektirmiyor; bundan sonraki her aşamada kabul kriterleri
kurulurken **zorunlu girdi** sayılacak. `takip/` md5 6/6 aynı, commit/push yok.

---

## 1. KALICI PERFORMANS HEDEFİ — küçük hedef sürekliliği

**Hedef:** hedef görüntüde küçüldükçe takip sürekliliğini mümkün olduğunca
korumak; sistemin **gerçekten dayanabildiği en düşük güvenilir hedef piksel
boyutunu deneysel olarak** belirlemek.
**5 × 5 zorunlu bir hedef değildir**; 5 × 5 dâhil olmak üzere kademeli olarak
ölçülecek ve güvenilir kalınan minimum boyut raporlanacaktır.

### 1a. Bu eksende ZATEN ölçülmüş olanlar (yeni ölçüm değil, kayıt)

`README.md:162-190` — `python3 minboyut.py`, `test3` üstel irtifa rampası,
3 gürültü tohumu:

| hedef | IoU | hassasiyet | merkez hata | hüküm |
|---|---|---|---|---|
| 52 × 22 px | 0.94 | %100 | 0.44 px | başarılı |
| 31 × 13 px | 0.91 | %100 | 0.44 px | başarılı |
| 20 × 8 px | 0.67 | %100 | 0.81 px | başarılı |
| 16 × 7 px | 0.72 | %100 | 0.70 px | başarılı |
| 13 × 6 px | 0.56 | %94 | 1.14 px | kararsız |
| **9 × 4 px** | 0.35 | %99 | **0.37 px** | başarılı |
| 7 × 3 px | 0.24 | %79 | 0.32 px | kararsız |
| **5 × 2 px** | 0.17 | %67 | 0.37 px | **kayıp** |

**Karıştırılmaması gereken iki ayrı sınır** (`README:180-184`):
* **Konum kilidi** ~**9 × 4 px**'e kadar korunuyor (merkez hatası hâlâ 1 px altında).
* **Kutu ölçüsü** ~**25 × 10 px** altında güvenilmez oluyor — IoU bu yüzden düşüyor.

Çekirdek karşılaştırması (`README:198-208`): `renk_dcf` **9.0 × 3.7 px**,
`mosse` 16.5 × 6.8 px, `ncc` 16.5 × 6.8 px, `akis` küçük hedefte köşe bulamıyor.
Ana bulgu: **20 × 10 px altında doku bitiyor, renk kalıyor.**

> **Bu tabloların bugünkü durumu:** A3.9 Faz C'nin kanıtladığı **boyut ölçümü
> sorunu** (`A3.9_KAPANIS.md` §8.2) tam olarak yukarıdaki *ikinci* sınırın
> altında yatıyor. Küçük hedef benchmark'ı bu yüzden yalnızca bir hedef değil,
> aynı zamanda P0.1'in ölçüm yüzeyidir.

### 1b. Bundan sonraki her aşamada raporlanacak sütunlar

Hedef piksel boyutu ↓ eksene alınarak: **IoU · lock oranı · drift karesi ·
merkez hatası · PSR · FPS · p50/p95 latency**. Ayrıca `tavan_iou`
(boyut/merkez katkı ayrımı, `DENEY_04R` §7) — çünkü küçük hedefte IoU düşüşünün
kaynağı ayrılmadan sonuç yorumlanamaz.

### 1c. Ölçüm ortamı sırası
Kayıtlı veri → sim / Gazebo → gerçek kamera → Pi Zero 2 W → gerçek drone.
Bir aşamada ölçülmemiş bir değer **sonraki aşamaya varsayım olarak taşınmaz**.

---

## 2. KALICI DONANIM KISITI — gerçek drone

| bileşen | model |
|---|---|
| FC / stack | **GEPRC TAKER F405 BLS 50A** |
| Onboard bilgisayar | **Raspberry Pi Zero 2 W** |
| Kamera | **Raspberry Pi AI Camera Module** |
| Motor | **iFlight XING-E Pro 2207 1800KV** |
| Drone | 5 inch, ~**750 g** |
| FC yazılımı | **Betaflight** |
| PX4 / ArduPilot | **kullanılmayacak**; çözüm bunlara bağımlı olmayacak |

### 2a. Yeni yöntem tasarlanırken zorunlu 10 başlık
Pi Zero 2 W'de çalışabilirlik · CPU/RAM maliyeti · gerçek zamanlı FPS ·
kare-arası latency · kamera gecikmesi · hareket bulanıklığı · titreşim ·
yaw/pitch/roll · gerçek kamera akışı · onboard çalıştırma.

### 2b. Bu başlıkların BUGÜNKÜ ölçüm durumu (dürüst envanter)

| başlık | durum | kaynak |
|---|---|---|
| Pi Zero 2 W FPS | **HENÜZ ÖLÇÜLMEDİ** — `README:405-407`: *"Pi sayıları ekstrapolasyondur, cihazda ölçüm yapılmamıştır"* (≈28 FPS tahmini) | README bilinen sınır #5 |
| CPU/RAM maliyeti (cihazda) | **HENÜZ ÖLÇÜLMEDİ** | — |
| Kare-arası işlem gecikmesi (WSL2) | ölçüldü: p50 2.54 ms, p95 5.33 ms, maks 15.93 ms (640×480) | bu oturumdaki G6 koşumu |
| Kamera gecikmesi (sensör→kare) | **HENÜZ ÖLÇÜLMEDİ** | — |
| Hareket bulanıklığı | **HENÜZ ÖLÇÜLMEDİ** — Gazebo render blur'suz; VisDrone'da doğal olarak var ama ayrıştırılmadı | — |
| Titreşim / jello | **HENÜZ ÖLÇÜLMEDİ** — repoda titreşim modeli yok | — |
| Yaw/pitch/roll | **KISMEN ÖLÇÜLDÜ (simülasyonda)** — Faz B G4/G5 aileleri; koparan kanal dönme (~120 °/s) | `BENCHMARK_GAZEBO_FAZB.md` |
| Kamera ötelemesi | ölçüldü — 80 m/s'ye kadar koparmıyor | Faz B |
| Gerçek kamera akışı | **HİÇ TEST EDİLMEDİ** — `kaynak.py` `camera` dalı ve `calistir.py --canli` var, gerçek kamerayla koşulmadı | — |
| Onboard çalıştırma | **HİÇ DENENMEDİ** | — |
| FC'ye veri akışı | **TASARLANMADI** — repoda uçuş kontrolüne hiçbir çıktı yok | — |

**Pi AI Camera notu:** modül sensör üstü hızlandırıcı taşır; teoride A5'in
detection yükünü CPU'dan alabilir. Bu projede **hiç denenmedi ve ölçülmedi**;
roadmap'te varsayım olarak kullanılmayacak.

### 2c. Kabul kuralı
> **Yeni bir çözüm, yalnızca güçlü masaüstü/GPU üzerinde çalıştığı için
> başarılı sayılmaz.** Her yeni yöntemin kabul kriterine, en azından
> *tahmini* CPU maliyeti ve ölçülmemiş kalemlerin açık listesi eklenecek.

Bu kural bu oturumda bir kez fiilen uygulandı: A3.9c'de aday E doğruluk
ölçütünden düşerken maliyeti de (**4.6–15.4 ms/kare**, Pi Zero 2 W'nin ≈36 ms
bütçesinin %13–43'ü) ayrıca raporlandı.

---

## 3. MİMARİ HEDEF — katman ayrımı

```
KAMERA
  ↓
FRAME
  ↓
DETECTION / USER SELECTION
  ↓
INDEPENDENT MEASUREMENT
  ↓
TRACKER
  ↓
RECOVERY
  ↓
OUTPUT / TELEMETRY
```

### 3a. Bu ayrımın bugünkü karşılığı

| katman | mevcut karşılık | durum |
|---|---|---|
| KAMERA → FRAME | `kaynak.py` `Kaynak`/`Kare` soyutlaması; `sim`, `gazebo`, `simkayit`, `visdrone`, `video`, `camera` | **HAZIR ve temiz** |
| DETECTION / USER SELECTION | `hedef_secici(adaylar, kare) -> aday \| None` sözleşmesi (`main.py:61-88`, `kos(..., hedef_secici=)`) | **sözleşme hazır**, fare uygulaması A4'te |
| INDEPENDENT MEASUREMENT | **BOŞ** — `D2_YENI_OLUM_ENVANTERI.md`: A sınıfı boş; `rafine_kutu` bağımsız değil | **AÇIK (P0.1)** |
| TRACKER | `takip/izleyici.py` + `cekirdekler.py` | hazır (Deney 2) |
| RECOVERY | `_arama_adimi` + `_kilidi_reddet` | hazır, A10'da genişleyecek |
| OUTPUT / TELEMETRY | `main.kos`'un kare başına ürettiği `sonuc` sözlüğü (`kutu`, `durum`, `psr`, `merkez`) | **tek çıkış noktası var**, köprü tasarlanmadı |

### 3b. Kural
> **Tracker çekirdeği gerçek kameraya ya da flight controller'a gereksiz
> biçimde bağlanmayacak.** `takip/` yalnızca `bgr` ndarray alır ve sözlük
> döndürür; kaynak ve telemetri katmanları dışarıda kalır. Bu ayrım bugün
> zaten geçerlidir ve korunacaktır.

---

## 4. A4 için sonuç

Bu kısıtlar **A4'te kod değişikliği gerektirmiyor**; A4'ün kapsamı
(`USER TARGET SELECTION / INITIALIZATION`) değişmedi ve **yeni özellik
eklenmeyecek**. Yalnızca A4'ün kabul kriterlerine iki not düşülüyor:

* **K7'ye ek:** seçici, `camera` kaynağıyla da aynı sözleşmede çalışmalı
  (gerçek kamera hattı bugün test edilmemiş olsa bile mimari olarak
  dışlanmamalı).
* **K9 (yeni, bilgi amaçlı):** fare seçimi hattının kare başına ek maliyeti
  raporlanacak; tracker döngüsüne ölçülebilir bir yük **eklememeli**
  (seçim yalnızca kilit öncesi çalışır).

Küçük hedef benchmark'ı A4'te **koşulmayacak**; A5/A6 ve sonraki
detector/tracker entegrasyonlarında **kabul kriteri** olarak korunacaktır.

**Bu belge kayıt amaçlıdır; kod, deney, commit/push içermez.**

---

## K6 — TETİKLEYİCİ SABİTİ, EYLEMİN YAZDIĞI DURUMDAN TÜRETİLEMEZ

**Eklendiği tarih:** 2026-09-03 (A10'un başarısızlığından sonra, A10.1/D2 ile).

> Bir tetikleyicinin eşiği, o tetikleyicinin **kendi eyleminin ürettiği** bir
> değerden türetilemez ve o değere eşit olamaz.

**Ölçülmüş karşı örnek (A10):** hakemin Mod A kuralı `iz(P) > 8.0` idi. Eşik
`Kalman.__init__`'in başlangıç kovaryansından (`diag(4,4)` → iz 8.0) alınmıştı.
Ama hakem LOST deyince takipçiyi ARAMA'ya itiyor, `_arama_adimi` yeniden
edinirken `Kalman.ata`'yı çağırıyor ve `ata` `P[:2,:2]`'yi **tam o değere**
sıfırlıyor. Bir sonraki `tahmin` adımı eşiği aşıyor → yeniden LOST.
Eşik, kendi kararının ürettiği değere eşitti. Sağlam bir hücre
(182/127·30×12) böyle yıkıldı: IoU 0.383 → 0.144.

**Kural üç şey ister:**

1. **Kaynak ayrımı.** Eşik, eylemin dokunmadığı bir ölçümden gelmeli
   (ör. hakem yokken alınmış açık çevrim dağılımı).
2. **Mesafe.** Eşik ile eylemin yazdığı değer arasında açık bir pay olmalı;
   pay raporda **sayıyla** verilmeli (A10.1'de giriş eşiği sıfırlama değerinin
   6.8 katı).
3. **Histerezis.** Giriş ve çıkış eşikleri ayrı olmalı; tek eşik, sınırın
   etrafında salınan bir büyüklükte kendi kendini tetikler.

**Genellemesi:** bu, projenin `A39_FAZ_C_KARAR_KAPANIS.md` ve
`DENEY_04U_BOYUT_KAPISI_AB.md`'de yazılmış "bir KAPI, kararının ETKİLEDİĞİ bir
büyüklüğü ölçüt yapamaz" dersinin **eşik seçimine** uzanan halidir. Ders
Deney 1, 3, 4A, 4U, A/B-2 ve A10'da olmak üzere **altı kez** tekrarlandı;
bu madde onu bir kısıt haline getirir.

**Uygulama:** her yeni tetikleyici için ön-kayıtta şu üç satır zorunludur —
eşiğin kaynağı · eylemin o büyüklüğe yazıp yazmadığı · yazıyorsa aradaki pay.
