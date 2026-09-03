# Deney 4S — `_boyut_sinirla`'nın çapası bozuk olduğu için mi işlemiyor?

**Tamamen salt okunur. Takipçi KOŞTURULMADI**; yalnızca `cikti/boyut_4r.json`
kayıtlı serisi kullanıldı. `takip/` altında hiçbir dosya değiştirilmedi,
hiçbir eşik / lr / Kalman / DCF / şablon / geometri parametresi değişmedi,
commit/push yok. Araç: `gazebo/tani_4s_capa.py`. Çıktı: `cikti/capa_4s.json`.

`takip/` md5'leri deney öncesi = sonrası, Deney 2 baseline'ı ile **6/6 aynı**.

## 0. Test edilen tek şey

`izleyici.py:549`'un **kendi bandı** ([0.60, 1.70]) korunarak yalnızca
**çapa** değiştirildi:

| | çapa `b` |
|---|---|
| **A) MEVCUT** | `max(boyut_olculen, min_kenar)` — satır 564'te `rafine_kutu` ile güncellenir |
| **B) KARŞIT-OLGU** | `max(kilit_boyutu, min_kenar)` — sabit |

İki test ayrı raporlanır:

* **S1 — açık çevrim (kesin):** her karede **kayıtlı** `A4` değerine iki band
  da uygulanır. "Band bu kaçışı *görür* müydü?" sorusunu geri besleme olmadan
  yanıtlar.
* **S2 — kapalı çevrim (yaklaşık):** boyut özyinelemesi kayıtlı
  `olcek_katsayisi` ve kayıtlı `rafine` kutularıyla yeniden koşturulur,
  yalnızca çapa değişir.
  > **Yaklaşıklık uyarısı:** `rafine_kutu` girdi olarak `boyut`u alır
  > (pencere = 3 × boyut). Kutu değişseydi rafine çıktısı da değişirdi.
  > Bu yüzden S2, **çapanın tek başına sağlayabileceği iyileşmenin ÜST
  > SINIRIDIR**, bir tahmin değil.

**Sadakat denetimi (S2, mevcut çapa → kayıtlı seri):**

| kaynak | drift öncesi maks sapma | drift sonrası |
|---|---|---|
| 182/127 | **0.0000 px** | 0.0000 px |
| 305/5 | **< 0.0001 px** | 5.84 px (kare 117–153 GT boşluğundan sonra) |
| G6_agresif | **0.0000 px** | 0.0000 px |
| G6_agresif_durakli | **0.0000 px** | 0.0000 px |

Karar drift öncesine dayandığı için dört kaynakta da S2 **birebir sadıktır**.

## 1. Sonuçlar — karar kaynakları

| kaynak | kilit boyut | kilit GT | **GT / kilit GT aralığı (w · h)** |
|---|---|---|---|
| 182/127 | 12.0 / 11.0 | 19.3 / 15.7 | **0.96–2.37** · **1.00–2.68** |
| 305/5 | 23.0 / 81.0 | 24.2 / 47.4 | **0.98–2.56** · **0.31**–1.20 |
| G6_agresif | 57.0 / 39.0 | 59.0 / 32.8 | 0.90–1.04 · 0.67–1.24 |

### S1 — sınır ihlali kaç karede oluşur?

| kaynak | kare | ihlal (MEVCUT çapa) | **ihlal (SABİT çapa)** | ilk ihlal karesi | **drift öncesi ihlal** | drift |
|---|---:|---:|---:|---:|---:|---:|
| **182/127** | 334 | 4 | 145 | **196** | **0** | **39** |
| **305/5** | 140 | 0 | 40 | 90 | **20** | 110 |
| **G6_agresif** | 293 | 0 | 46 | 254 | **41** | 294 |

### S2 — kaçış düzeliyor mu? (kutu / GT oranı)

| kaynak | | drift karesinde w · h | koşum maks w · h | ort \|log oran\| | kırpma karesi |
|---|---|---|---|---:|---:|
| **182/127** | mevcut | 0.53 · 0.56 | 0.65 · 0.70 | 0.441 | 4 |
| | **sabit çapa** | **0.53 · 0.56** | **0.65 · 0.70** | **0.441** | 113 |
| **305/5** | mevcut | 1.46 · 2.68 | 1.95 · 2.68 | 0.174 | 0 |
| | **sabit çapa** | **1.29** · **2.68** | **1.46** · **2.68** | **0.155** | 10 |
| **G6_agresif** | mevcut | 1.88 · 1.84 | 2.10 · 1.94 | 0.145 | 0 |
| | **sabit çapa** | **1.57** · **1.84** | **1.70** · **1.94** | **0.133** | 8 |

## 2. Okuma

**a) Mevcut çapa fiilen ölüdür.** Üç karar kaynağında toplam **4** kırpma
karesi (hepsi 182/127'de, yükseklikte −1.0…−1.8 px). 4R'nin bulgusu doğrulandı.

**b) Ama sabit çapa da kaçışları DÜZELTMİYOR.**

* **182/127 — hiç etkisi yok.** Sabit çapa 145 karede ihlal görürdü ama
  ilki **kare 196**'da; arıza **kare 39**'da. **Drift öncesi 0 yakalama.**
  Drift karesindeki oran her iki çapada da **birebir aynı** (0.53 · 0.56).
  Nedeni yapısal: kaçış bir **küçülme**dir ve alt sınır
  `0.60 × 12.0 = 7.2 px`, kutu ise 9.0–10.9 px — bandın **içinde**. Çapanın
  kendisi (kilit kutusu 12.0) zaten GT'nin **0.62**'si olduğu için sabit çapa
  hatayı çapaya *gömüyor*.
* **305/5 — kısmi, tek eksende.** Genişlik 1.46 → 1.29 düzeliyor,
  **yükseklik 2.68'de hiç değişmiyor**; ort \|log\| 0.174 → 0.155.
* **G6_agresif — kısmi, tek eksende.** Genişlik 1.88 → 1.57 (band tavanı
  1.70'e dayanıyor), **yükseklik 1.84'te hiç değişmiyor**; 0.145 → 0.133.

Yani **üst sınır** koşulunda bile kutu hâlâ GT'nin 1.3–1.6 katı (w) ve
1.8–2.7 katı (h). Kaçış sönümleniyor, **ortadan kalkmıyor**.

**c) `[0.60, 1.70]` bandı sabit çapayla YETERSİZDİR — üstelik zararlıdır.**
GT boyutu koşum boyunca kilit GT'sinin şu katlarına gidiyor:

* 182/127: **2.37×** (w), **2.68×** (h) → tavan 1.70 **meşru büyümeyi keser**
* 305/5: **0.31×** (h) → taban 0.60 **meşru küçülmeyi keser**

Yani sabit çapa yalnızca yetersiz değil, iki kaynakta doğru davranışı
engellerdi. Sabit çapanın 113 / 10 / 8 karede kırpma yapması bunun ölçüsüdür.

## 3. `G6_agresif_durakli` — ayrı rapor

4R'ye göre burada baskın sorun boyut değil merkezdir; 4S bunu doğruluyor:

| | ihlal (mevcut) | ihlal (sabit çapa) | drift kutu/GT | GT/kilit GT aralığı |
|---|---:|---:|---|---|
| G6_agresif_durakli | 0 | **0** | 1.06 · 1.37 → **1.06 · 1.37** | 0.90–1.05 · 0.67–1.26 |

İki çapa da **hiç** ihlal görmüyor ve seri birebir aynı kalıyor. Kutu zaten
GT'nin 1.06 katı; sınırlamanın yapacağı bir şey yok. Bu kaynak 4Q/4R'deki
**merkez** ailesindedir ve 4S'in konusu dışındadır.

---

# HÜKÜM: **TAZELEME_KAYNAK**

Çapa hipotezi **desteklenmedi**:

1. Sabit çapa, üç karar kaynağının **birinde (182/127) hiçbir şey
   değiştirmiyor** — drift öncesi 0 yakalama, drift oranı birebir aynı.
2. Diğer ikisinde etki **kısmi ve tek eksenli**: genişlikte 1.88 → 1.57 ve
   1.46 → 1.29, **yükseklikte sıfır** (1.84 ve 2.68 aynen kalıyor). Ve bu,
   geri besleme yokmuş gibi hesaplanan **üst sınırdır**.
3. Mevcut bandın kendisi sabit çapayla **yanlış**: GT meşru olarak 2.37–2.68×
   büyüyor (182/127) ve 0.31×'e küçülüyor (305/5); `[0.60, 1.70]` bunları
   keserdi.
4. Buna karşılık 4R'nin log ayrıştırması artıksızdı: boyut değişiminin
   tamamını `_boyut_tazele` üretiyor (×0.890 / ×1.336 / ×1.807), sınırlama
   ×1.000.

> Hata `_boyut_sinirla`'nın çapasında değil, `_boyut_tazele`'nin **girdisinde
> ve karıştırma kuralında**dır: `rafine_kutu`, GT 57 px iken 106–174 px,
> GT 21 px iken 3–5 px kutular döndürüyor ve `_boyut_tazele` bunları
> **koşulsuz** %25 ağırlıkla karıştırıyor. Sınırlama katmanı bu hatayı ne
> üretiyor ne de durdurabiliyor.

### Sonraki TEK aday (yine salt okunur, yeni ölçüm koşturmadan)

> **Bozuk rafine kutuları, o an ZATEN hesaplanmış büyüklüklerden ayırt
> edilebiliyor mu?**
> Elde iki kayıt var: `cikti/rafine_4n.json` (her `rafine_kutu` çağrısının
> bileşen sayısı, maske doluluğu, p82 eşiği, oran, **renk mesafesi**,
> bileşen–GT IoU'su, bileşen alanı / GT alanı) ve `cikti/boyut_4r.json`
> (aynı çağrıların döndürdüğü kutu + o karenin GT'si). İkisi kare numarasıyla
> eşleştirilip, rafine kutusunun **GT'ye göre bağıl hatası**
> (`|rafine_wh − GT_wh| / GT_wh`) ile bu mevcut büyüklükler arasındaki
> ayırt edicilik ölçülür.
> * Ayırt edici bir büyüklük varsa: müdahale **yeni bir ölçüm gerektirmeyen**
>   bir kabul kuralıdır ve tek noktada uygulanır.
> * Yoksa: sorun doğrudan `rafine_kutu`'nun çıktı kalitesindedir ve
>   sınırlama/karıştırma katmanında çözülemez.
>
> Bu, takipçiyi hiç koşturmadan yapılabilen ve iki şıkkı ayıran tek ölçümdür.

**Bu turda hiçbir optimizasyon uygulanmadı; `takip/` md5 6/6 aynı.**
