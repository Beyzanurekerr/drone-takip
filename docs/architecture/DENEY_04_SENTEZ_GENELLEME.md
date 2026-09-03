# Deney 4A–4E sentezi — Gazebo → VisDrone genelleme problemi

**Salt okunur teşhis/planlama. Kod değişikliği yok, commit/push yok.**
`takip/` altındaki 6 dosyanın md5'i Deney 2 durumuyla birebir.

## Mevcut kayıtların envanteri (yeni havuz kurmadan önce)

| dosya | içerik | Gazebo | VisDrone |
|---|---|---|---|
| `deney_*.json` (9 adet) | 32-senaryo metrik demeti | ✓ | ✓ |
| `fazb_tani.json` | Faz B tanı alanları (e_ego, d_artık, K1–K8…) | ✓ | ✗ |
| `geometri.json` | kare-kare kutu geometrisi, `boyut` aşama ayrıştırması | 5 | 3 |
| `merkez.json` | kare-kare **aşama aşama merkezler** (ego/KF/DCF/rafine/final) | 6 | **✗** |
| `agirlik.json` | kare-kare rafine karar-anı sinyalleri + `rafine_hata` | 4 | 3 |
| `dolgu.json` | padding × senaryo, **`dcf_dx` dahil** | 2 | 3 |
| `dolgu_genis.json` | padding × 18 senaryo (Gazebo + sim) | ✓ | ✗ |

Yani DCF biası (`dolgu.json`) ve rafine hatası (`agirlik.json`) **her iki
kaynakta da** zaten kayıtlı. Eksik olan tek şey görüntü içeriği özellikleriydi;
onun için tek bir ek ölçüm yapıldı (aşağıda), takipçi hiç koşturulmadan.

---

## 1. Gazebo ile VisDrone arasındaki temel fark

`rafine_kutu` (tespit.py:87) tek bir varsayıma dayanır:

> "hedefin pikselleri yerel arka plan **medyanından** belirgin biçimde uzaktır"

Eşik `max(16, p82(d))`, `d = |piksel − yerel medyan|`. Bu varsayım GT kutusu
kullanılarak doğrudan ölçüldü (takipçi koşmadan, 40 kare/kaynak):

| kaynak | **AUC(iç/dış)** | hedef yakalanma | arka plan yanlış | **kontrast** | hedef px |
|---|---|---|---|---|---|
| G0 | **0.959** | 0.98 | 0.08 | **146.4** | 57×22 |
| G6_agresif | 0.790 | 0.59 | 0.09 | 91.5 | 58×34 |
| G3_agresif | 0.738 | 0.56 | 0.09 | 79.8 | 57×37 |
| G3_kritik | 0.699 | 0.47 | 0.10 | 47.7 | 54×50 |
| **117/23** | **0.598** | **0.30** | 0.16 | **4.8** | 53×54 |
| 182/127 | 0.678 | 0.45 | 0.15 | 43.9 | 21×19 |
| **268/31** | **0.262** | **0.00** | 0.20 | **−36.9** | 12×6 |

**Kontrast Gazebo'da 48–146, VisDrone 117/23'te 4.8 — 10 kat uçurum.**
268/31'de kontrast **negatif**: hedef, yerel medyandan arka plandan bile daha
az ayrılıyor; renk-lekesi varsayımı orada tersine dönmüş durumda.

Sebep açık: Gazebo hedefleri **tek renkli SDF kutuları**, zemin ise üretilmiş
dokulu bir düzlem. Gerçek hava görüntüsünde araç gölgeli, çok tonlu ve çevresi
benzer renkte.

---

## 2. DCF biası iki kaynakta nasıl değişiyor?

**Şaşırtıcı biçimde AYNI.** (dolgu 2.0, taban)

| kaynak | dcf dx | dcf dy | \|bias\| | hedef genişliği | **bias / genişlik** |
|---|---|---|---|---|---|
| G3_agresif | −4.17 | −0.97 | 4.29 | 57 px | **0.073** |
| G3_kritik | −4.78 | −0.48 | 4.81 | 54 px | **0.089** |
| **117/23** | **−4.85** | −1.86 | 5.19 | 53 px | **0.091** |

İki farklı veri kaynağı, üç senaryo: bias **hedef genişliğinin %7–9'u**, yönü
görüntü −x (bağıl arka plan akışı yönü). 182/127 (5.99) ve 268/31 zaten kopuk
takipler, bilgi taşımıyor.

Ve takipçinin **son** merkez hatası da benzer: G3_agresif 5.25, G3_kritik 5.94,
117/23 5.19 px.

---

## 3. Bias ile ilişkili ölçülebilir özellikler

| özellik | Gazebo | VisDrone | bias ile ilişki |
|---|---|---|---|
| bağıl arka plan akışı yönü | −x (1.78 px/kare, tasarım gereği) | −x (ölçülen bias yönü) | **yönü belirliyor** |
| öğrenme süresi | k+0 ~0.8 px → k+80 ~5.6 px | — | **büyüklüğü belirliyor** (4B) |
| yama içi arka plan oranı (`dolgu`) | monoton ↑ | **ters** | Gazebo'ya özgü |
| hedef/arka plan kontrastı | 48–146 | 4.8 | rafine'yi belirliyor, biası değil |
| hedef boyutu | 54–58 px | 53 px | bias ölçekleniyor (%7–9) |
| PSR | biastan bağımsız (34–282'de bias sürüyor) | aynı | **ilişkisiz** |

---

## 4. Gazebo'da güçlü, VisDrone'da çöken ilişkiler

| ilişki | Gazebo | VisDrone | nerede kullanıldı |
|---|---|---|---|
| rafine ≫ DCF doğruluğu | **5.9–7.7×** | **1.13×** | 4C (çöktü) |
| rafine hatası ≈ 0.76 px | ✓ | **4.78 px** | 4C, 4D |
| `d_kf` rafine kalitesini gösterir | zayıf (Kalman'ı ölçüyor) | zayıf | 4D (elendi) |
| \|oran−1\| rafine kalitesini gösterir | 0.091 | **0.071 (daha iyi görünüyor!)** | 4D (elendi) |
| PSR ↑ = güven ↑ | — | 117/23 **en yüksek PSR, en kötü rafine** | 4D (ters) |
| padding ↓ = bias ↓ | monoton ✓ | **ters** | 4E (elendi) |
| padding ↓ = PSR sabit | ✓ | **−%20** | 4E |

**Ortak payda: hepsi `rafine_kutu`'nun renk-lekesi kalitesine ya da yamanın
arka plan bileşimine dayanıyordu** — ikisi de Gazebo'nun sentetik renk
ayrımından besleniyor.

---

## 5. Her iki kaynakta AYNI yönde davranan tek şey

**DCF peak biası.** Yönü (−x, bağıl arka plan akışı), büyüklüğü (hedef
genişliğinin %7–9'u) ve öğrenmeyle büyümesi (4B: k+0 → k+80) her iki kaynakta
da aynı. Sentetik doğrulama da bunu destekliyor: öğrenmesiz aynı-kare testinde
koordinat dönüşümü **tam** (dx = +0.000), arka plan kayarken öğrenme ise tam o
yönde bias üretiyor.

Buna karşılık PSR, rafine doğruluğu, padding tepkisi, `d_kf` ve oran sinyalleri
kaynağa göre yön değiştiriyor.

---

## 6. Parametre optimizasyonu yerine hangi mekanizma test edilmeli?

4C (sabit ağırlık), 4D (adaptif ağırlık) ve 4E (padding) üçü de **parametre**
denemesiydi ve üçü de aynı duvara çarptı. Bilimsel olan, genellenen tek
büyüklüğü (bias) üreten **mekanizmayı** doğrudan sınamaktır.

4B iki şeyi kanıtladı: (a) bias öğrenmeyle büyüyor, (b) öğrenme yokken sıfır.
O halde mekanizmanın doğrudan kolu **şablonun etkin hafızasıdır** (≈ 1/lr),
padding değil.

---

# Sonuç

## Ana genelleme problemi

> **Boru hattının doğruluğu Gazebo'da, hedefin arka plandan RENK olarak
> ayrılabilmesi varsayımına dayanıyor. Bu varsayım Gazebo'da neredeyse
> kusursuz, gerçek hava görüntüsünde ise geçersiz. Gazebo'da ölçülen her
> "düzeltici referans" ilişkisi bu varsayımdan besleniyor ve gerçek veriye
> taşınmıyor.**

Takipçinin **hatası** genelleniyor (son merkez hatası 5.2–5.9 px, DCF biası
hedef genişliğinin %7–9'u — her iki kaynakta). Genellenmeyen şey, hatayı
düzeltecek **bağımsız referansın kalitesi**.

## Kanıtı

1. Hedef/arka plan kontrastı: Gazebo 47.7–146.4 · VisDrone 117/23 **4.8** ·
   268/31 **−36.9**. Ayırt edicilik AUC 0.70–0.96 vs 0.60 vs 0.26.
2. `rafine_kutu` hatası: Gazebo 0.48–0.76 px · VisDrone 117/23 **4.78 px**.
3. 4C: `r_carpan` 1.0 → 0.17 Gazebo'da merkez hatasını %52 düşürdü,
   117/23'ü 10 karede kopardı (IoU 0.701 → 0.011).
4. 4D: rafine kalitesini gösterecek hiçbir mevcut sinyal iki kaynağı ayıramadı;
   PSR **ters** yönlü (117/23 en yüksek PSR + en kötü rafine).
5. 4E: padding–bias ilişkisi Gazebo'da monoton, 117/23'te tersine dönüyor;
   optimumlar zıt uçlarda (1.3 vs 2.0).

## Şu anda güvenebileceğimiz ölçümler

* **DCF peak biası** — yön, büyüklük (hedef genişliğinin %7–9'u) ve öğrenmeyle
  büyümesi her iki kaynakta tutarlı.
* **Alan alan 32-senaryo değişmezlik denetimi** — kaynak bağımsız, tolerans 1e-12.
* **Mikro-benchmark gecikme ölçümleri** — kod düzeyinde, veriden bağımsız.
* **Sentetik kontrollü testler** (koordinat dönüşümü, arka plan kaydırma) —
  varsayımı doğrudan izole ediyor.
* **Gazebo GT'sinden türetilen büyüklükler yalnızca Gazebo içi karşılaştırmada**
  (tavan IoU, poz kaynaklı gerçek ego, gerçek görüntü dönmesi).

## Güvenemeyeceğimiz ölçümler

* **`rafine_kutu`'nun doğruluğu ve ondan türetilen her oran** — Gazebo'nun renk
  ayrımına özgü (4C, 4D bunun üzerine kuruluydu).
* **Padding tepkisinin yönü** — kaynağa göre ters.
* **PSR'nin güven göstergesi olarak kullanılması** — 117/23'te ters yönlü.
* **Faz B'nin K1–K8 puanları ve kopma eşikleri** — yalnızca Gazebo'da kuruldu;
  gerçek veriye taşındığı hiç sınanmadı.
* **sim test2 / test3 ve VisDrone 182/127 IoU'su** — kaotik (Deney 1: anlamca
  aynı işlem değişimi test2'yi 0.435 → 0.686 oynattı).
* **VisDrone 268/31'e dair her şey** — kontrast negatif, hedef 12×6 px;
  takipçi orada hiçbir yapılandırmada çalışmıyor.

## Bir sonraki deney için TEK hipotez

> **H:** DCF merkez biası, şablonun **öğrenme adımında** bağıl olarak akan arka
> planı soğurmasından kaynaklanır. Bu doğruysa bias, şablonun **etkin
> hafızasıyla** (≈ 1/lr) birlikte **her iki veri kaynağında da aynı yönde**
> ölçeklenir.

Neden bu hipotez:

* Genellenen **tek** büyüklüğü (bias) hedef alıyor; genellemeyen hiçbir
  büyüklüğe (rafine kalitesi, padding tepkisi, PSR) dayanmıyor.
* 4B onu zaten kısmen kanıtladı: öğrenmesiz bias yok (dx = +0.000), öğrenmeyle
  büyüyor (k+0 ~0.8 px → k+80 ~5.6 px), ve sentetikte kayan arka plan +
  öğrenme tam o yönde bias üretiyor.
* **Parametre araması değil, mekanizma sınaması**: tahmin ediliyor ki
  \|bias\| ∝ etkin hafıza. Tahmin iki kaynakta da tutarsa mekanizma
  doğrulanmış ve nihayet genellenen bir ilişki elde edilmiş olur; VisDrone'da
  tutmazsa **hipotez ölür ve bu hat kapanır** — 4E'de olduğu gibi, uygulamadan
  önce.
* **Sıfır kod değişikliğiyle ölçülebilir.** Dikkat: `izleyici.py:_takip_adimi`
  öğrenme oranını çağrı anında geçiyor
  (`lr = 0.125 if boyut.max() > 18 else 0.04`), yani `RenkDcfCekirdek(lr=…)`
  yapıcı parametresi **atlanıyor**. Ölçüm, geçirilen `lr`yi yok sayan bir teşhis
  alt sınıfıyla yapılmalı — 4E'deki örnek-geçirme tekniğinin aynısı,
  `takip/` yine hiç değişmez.

Ölçülecekler: `dcf_dx`, DCF merkez hatası, PSR, IoU, kilit/drift — **G3_agresif,
G3_kritik ve VisDrone 117/23'te birlikte**, ve tahmin edilen monotonluk iki
kaynakta ayrı ayrı sınanmalı.

**Henüz uygulanmadı.**
