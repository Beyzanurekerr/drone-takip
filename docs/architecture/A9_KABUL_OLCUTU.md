# A9 — Kabul ölçütü (A/B deneyleri için)

**Yazıldığı tarih:** 2026-09-02 · **Durum:** A/B-1, A/B-2, A/B-3 **koşulmadan önce** yazıldı.
Bu dosya deney sonuçlarına göre değiştirilmez. Değiştirilmesi gerekirse
gerekçesiyle birlikte yeni bir sürüm eklenir, eskisi silinmez.

## Neden ayrı dosya

Proje precedent'i: `A3.9C_KABUL_OLCUTU.md`, `A5.2_KABUL_OLCUTU.md`, `D1_kabul_olcutu.md`.
Eşik sonuçlar görüldükten sonra seçilirse eşik iyimserliği tuzağına düşülür.

## Karar tabanı (6 dizi, Aşama 1-EK'te belirlendi)

| rol | diziler |
|---|---|
| **sağlam** | 137/12 · 305/5 · 182/127 |
| **kopan** | 117/23 · 268/31 · 339/49 |

Seviyeler: 30×12, 20×10, 15×7, 10×5, 8×5 → dizi başına 5 hücre, toplam **30 hücre**.
**Sonuçlar yalnızca 117/23 üzerinden değerlendirilmez.**

## Zorunlu metrikler (her A/B, her hücre)

IoU · merkez hatası p50/p95 · güvenli yanlış kilit sayısı · toplam kopuş sayısı ·
PSR p50/p05 · Kalman P konum izi p50/p95 · boyut oranı `bho = boyut.max()/GT_L` p50/p95 ·
`_boyut_tazele` çağrı sayısı ve **boyut güncellemesinin öncesi/sonrası değerleri**.

**Tanımlar**
- `güvenli yanlış kilit` = `durum == KİLİTLİ` **ve** `IoU < 0.2` olan kare sayısı.
  (Aşama 1b'de bu metrik, yalnızca merkez hatasına bakan bir ölçütün yanlış
  "başarı" ilan edeceğini gösterdi. Birincil metriktir.)
- `kopuş` = `|merkez hatası| > 0.5·GT_L`, **5 ardışık kare**.

## Kabul koşulları — HEPSİ birden sağlanmalı

### K1 — Sağlam dizilerde regresyon yok (137/12, 305/5, 182/127)
- **K1a** Hiçbir hücrede **yeni kopuş** oluşmayacak.
- **K1b** Ortalama IoU hiçbir hücrede **0.03 mutlak**tan fazla düşmeyecek.
- **K1c** Merkez hatası p95 hiçbir hücrede **%20**'den fazla artmayacak.

### K2 — Yanlış kilit artışı kabul edilmez (6 dizinin tamamı)
- **K2** 30 hücrenin **toplam** güvenli yanlış kilit kare sayısı kontrol kolunu
  **aşmayacak**. Bu koşul mutlaktır; başka hiçbir kazanç bunu telafi etmez.

### K3 — Kopan dizilerde gerçek fayda (117/23, 268/31, 339/49)
- **K3a** Kopuşlu hücre sayısı kontrol kolundan **az** olacak.
- **K3b** En az **iki AYRI kopan dizide** ortalama IoU artacak.
- **K3c** **Merkez hatasının tek başına düşmesi fayda sayılmaz.** IoU artışı
  eşlik etmeyen p95 düşüşü, arızanın gizlenmesi olarak yorumlanır (Aşama 1b bulgusu).

### K4 — Üst sınır ve kalıcılaştırma
- Bütün ölçümler **açık çevrimdir**; sonuç bir üst sınırdır.
- K1–K3 birlikte sağlanmadıkça değişiklik **kalıcılaştırılmaz**;
  `takip/` dosyaları değiştirilmez.
- Sağlansa bile, kalıcılaştırma **kapalı çevrimde ayrıca sınanmadan** yapılmaz;
  A/B sonucu yalnızca "aday" statüsü verir.

## Beraberlik durumu

Birden fazla A/B K1–K3'ü geçerse, aralarında şu sırayla seçilir:
1. daha düşük toplam güvenli yanlış kilit
2. daha yüksek ortalama IoU (kopan diziler)
3. daha az kopuşlu hücre
4. `takip/` üzerinde daha küçük değişiklik

## Kapsam dışı (bu turda optimize edilmeyecek)

Recovery mekanizması · kopuş tespiti eşikleri · dedektör · ROI · model · veri seti.

---

# EK-1 — Aşama 3 (yeniden edinme) tanımları

**Eklendiği tarih:** 2026-09-02 · **Aşama 3 deneyleri KOŞULMADAN ÖNCE yazıldı.**
Bu bir **ekleme**dir, yukarıdaki K1–K4 koşulları **değiştirilmemiştir**.

**Gerekçe:** Aşama 3'ün başarı ölçümü "stabil kilit" kavramına dayanıyor, ama bu
kavram bu dosyada tanımlı değildi (Aşama 1'de eksik olarak işaretlenmişti).
Sonuçlara bakıp tanımlamak eşik iyimserliği olurdu.

**İlke:** yeni sabit uydurulmadı. Tanımlar bu dosyada **zaten var olan**
ilkellerden türetildi: `durum == KİLİTLİ`, `IoU ≥ 0.5`, `IoU < 0.2` ve
`kopuş`un kullandığı **5 ardışık kare** konvansiyonu.

| terim | tanım |
|---|---|
| **doğru hedef** | GT track'i ile `IoU ≥ 0.5` |
| **yanlış hedef** | `IoU < 0.2` (mevcut `güvenli yanlış kilit` eşiğiyle aynı) |
| **stabil kilit** | **5 ardışık karede** `durum == KİLİTLİ` **ve** `IoU ≥ 0.5` |
| **recovery epizodu** | `IoU < 0.2` olan, uzunluğu ≥ 5 kare olan azami ardışık dizi |
| **başarılı recovery** | epizot içinde **stabil kilit** sağlanır **ve** aynı epizotta yanlış hedefe stabil kilit oluşmaz |
| **false recovery** | 5 ardışık karede `durum == KİLİTLİ` **ve** `IoU < 0.2` — yani yanlış hedefe "stabil" kilit |
| **recovery süresi** | tetikleme karesinden stabil kilidin ilk karesine kadar kare sayısı |

**recovery süresi için üst sınır eşiği TANIMLANMAMIŞTIR** — bilerek. Süre bir
**dağılım olarak** raporlanacak; "kaç kare içinde toparlamalı" sorusu ölçüm
görülmeden yanıtlanmaz.

**Aşama 3 için ek kabul koşulu (K1–K3'e EK, onların yerine değil):**

### K5 — Recovery yanlış hedefe kilitlenmeyi ARTIRMAZ
`false recovery` sayısı ve toplam `güvenli yanlış kilit` kontrol kolunu
**aşmayacak**. "Herhangi bir nesneye yeniden kilitlendi" başarı sayılmaz.

### K6 — Normal tracking regresyonu yok
Recovery hiç tetiklenmeyen hücrelerde (sağlam diziler dahil) IoU ve merkez
hatası K1'deki sınırlar içinde kalacak.
