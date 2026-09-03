# A3.9 Faz C — Karar kapanışı (4A–4U sentezi)

**Salt okunur. Hiçbir kod değişikliği, optimizasyon, eşik taraması, Optuna ya
da yeni müdahale yok; commit/push yok.** `takip/` md5'leri Deney 2 baseline'ı
ile **6/6 aynı**. Bu belge yeni ölçüm üretmez; 4A–4U'nun ölçtüklerini karara
bağlar.

---

## 1. Kanıtlanan mekanizmalar

Her satır, en az bir kontrollü karşılaştırmayla ya da artıksız ayrıştırmayla
gösterilmiştir.

| # | mekanizma | kanıt | deney |
|---|---|---|---|
| M1 | **Yanlış kilit tek bir arıza değil, iki ayrı ailedir.** `tavan_iou` (takipçinin kendi boyutu GT merkezine oturtulunca çıkan IoU) ayırıyor: `tavan ≈ IoU` ise kayıp **boyuttan**, `tavan ≫ IoU` ise **merkezden**. | 182/127 0.295/0.295 · G6_agresif 0.288/0.288 · 305/5 0.229/0.256 · G6_agresif_durakli 0.251/**0.687** | 4Q, 4R |
| M2 | **Boyut hatasını ÜRETEN aşama `_boyut_tazele` (izleyici.py:563).** Log ayrıştırması artıksız (0.000). | tazeleme ×0.890 / ×1.336 / ×1.807 · ego ×1.014–×1.176 · `_boyut_sinirla` **×1.000** | 4R |
| M3 | **`_boyut_sinirla` yapısal olarak inerttir**, çünkü çapası `boyut_olculen` aynı `rafine_kutu` ile beslenir (satır 564): koruma, bozduğu kaynağa bağlı. | kırpma 0/293, 0/140, 0/293, 4/334 | 4R, 4S |
| M4 | **`rafine_kutu`'nun çıktısı düzenli olarak bozuktur.** | GT 57 px iken 106→174 px; GT 26×32 iken 26×134; GT 21 px iken 3×5 | 4R |
| M5 | **Mevcut oran kapısı ([0.35, 2.6]) bu arıza kipi için inerttir:** bozuk kutuların **37/37'sini (%100)** geçirir, iyi kutuların 0/188'ini reddeder. | 225 çağrı, 6 kaynak | 4T |
| M6 | **`rafine_kutu`'nun ölüm nedeni tek bir kapıdır: R6 renk kapısı** (başarısızlıkların %86'sı). R1/R2/R5/cv2 istisnası hiç ateşlemez; kodda açı filtresi yoktur. | 274 çağrı, sadakat ihlali 0 | 4N |
| M7 | **R6 bir arıza değil, doğru çalışan bir korumadır**; üst akıştaki gerçek arıza kaynağa göre değişir: G6'da **birleşme** (çeldirici), 117/23'te **parçalanma** (kontrast 5.2), 137/12'de **referans rengin bulanması**. | bileşen–GT IoU 0.33–0.41 vs 0.10–0.33 vs 0.93–0.97 | 4N |
| M8 | **`G6_agresif_durakli`'nin yanlış kilidi bir SAHNE ARTEFAKTIDIR.** Çeldirici aynı görüntü satırında 1.5 px'e kadar yaklaşıyor; sahneden çıkarılınca DCF çekim noktası düzleşiyor ve kopuş kayboluyor. | çekim−GT: 141'de her ikisinde −8.23 → çeldiricisiz **−3.9 düz**; SUPHELI/YK hiç oluşmuyor | 4P |
| M9 | **DCF ölçümü karelerin %81–91'inde tamamen alt-piksel terimdir** (tamsayı argmax harita merkezinde); 1 ızgara hücresi 3.5–4.8 px. | dört kaynakta | 4O |
| M10 | **Kopuş DCF ÖLÇÜM aşamasında doğar**, ego ya da KF'de değil: `final − dcf` ≈ −0.4 px; ego uygulanmış öngörü her karede ego'suzdan iyi. | 2×2 çapraz çözümleme: değişimin %94'ü **yamadan**, %0.5'i şablondan | 4O |
| M11 | **Bir KAPI, kararının etkilediği bir büyüklüğü ölçüt yapamaz.** `bileşen/boyut` oranına bakan kapı, kutu kayınca doğru rafineleri de reddeder; düzeltme kesilir, kayma hızlanır. | 137/12: açık çevrim TPR 0.45/FPR 0.04 → kapalı çevrimde IoU 0.548 → **0.190**, drift 75 → **58** | 4T + 4U |

---

## 2. Reddedilen hipotezler

| hipotez | nasıl düştü | deney |
|---|---|---|
| Açı = ego entegrasyonu (açık çevrim) | sızıntı + örnekleyici yan etkisi | 1 |
| Açı referansı ego'ya bağlansın | açı hatası 7.5× düzeldi ama **IoU gelmedi** (0.704 → 0.702) | 3 |
| Kutu şekli açıdan analitik türetilsin | kapalı çevrim; G3_agresif 0.760 → **0.540** | 4A |
| Rafine ağırlığı sabit 0.17 olsun | 117/23 çöktü | 4C |
| Rafine ağırlığı **adaptif** olsun | **ayırt edici sinyal yok** | 4D |
| DCF padding (`dolgu`) ayarı | Gazebo'ya özgü; kilit/drift bozuyor | 4E |
| Öğrenme **hızı** (lr) bias'ı yönetir | gerçek veride **ters** yönde etki | 4H |
| Öğrenme **zamanı** kapısı bias'ı yönetir | sağlıklı takipte kapı **hiç kapanmıyor** (0/342) | 4K |
| Rafine ölümü yanlış kilidin kök nedenidir | kontrol **aynı ölümü** yaşıyor ve kopmuyor | 4N |
| Çeldirici mekanizması yanlış kilitleri açıklar | 6 epizottan **1'i** (%23.7); türetildiği epizot | 4Q |
| `_boyut_sinirla`'nın çapası kök nedendir | sabit çapa 182/127'de **sıfır etki**; diğerlerinde tek eksenli kısmi | 4S |
| Mevcut sinyallerle rafine kabul kapısı kurulur | kapalı çevrimde 137/12 yıkıldı; G3_kritik regresyonu | 4T, 4U |
| `G6_agresif_durakli` duran-araç sınırını gösterir | kopuş araç **3.84 m/s**'de başlıyor; ilk duruş sorunsuz geçiliyor | 4M |
| 4L: "karar verilebilir tek yanlış-kilit kaynağı" | o kaynak **sahne artefaktı** çıktı | 4P |

> **Beş kez tekrarlanan tek ders:** türetilmiş bir büyüklük bağımsız bir
> ölçümün yerine geçtiğinde ya da bir kapı kendi etkilediği büyüklüğe
> baktığında çevrim kapanır ve hata birikir (Deney 1, 3, 4A, 4S/4R, 4U).

---

## 3. Hâlâ açıklanamayan performans kaybı

| # | açıklanamayan | bilinen sınırlar |
|---|---|---|
| A1 | **DCF merkez bias'ının kökü.** 4O ayrışmanın yamadan geldiğini gösterdi; **yamanın neden o yöne çektiği** açıklanmadı (4P yalnızca G6'daki tetikleyiciyi kanıtladı). 4B'nin notu: `dolgu = 2.0` ile yamanın ~%75'i arka plan. | 4E padding'i denedi ve elendi |
| A2 | **`rafine_kutu`'nun çıktı kalitesi neden bu kadar değişken.** 4N üç ayrı üst akış arızası buldu (birleşme / parçalanma / referans renk) ama ortak bir öngörücü yok. | 4T: mevcut sinyallerin hiçbiri boyuttan bağımsız değil |
| A3 | **117/23'ün başlangıç koşuluna kırılganlığı.** ±1 px'lik ilk kutu kayması IoU'yu **0.701 → 0.111**'e düşürüyor (havza sınırı 0.5–1 px arasında). Neden bu dizide bir havza sınırı var, ölçülmedi. | 4L |
| A4 | **İlk kilit kutusunun hatası.** 182/127'de kilit kutusu daha başta GT'nin **0.62**'si (tespit adayından); bu, dört boyut aşamasının hiçbirine ait değil. | 4R (beşinci katkı olarak kaydedildi) |
| A5 | **Gazebo↔VisDrone tersine dönüşü.** 4C/4D/4E/4H'de Gazebo'da ölçülen büyüklükler gerçek veriye genellenmedi; 4I kontrast ekseninin bunu açıklayıp açıklamadığını ayırt edilebilir kıldı ama **ölçüm yapılmadı**. | 4I, 4_SENTEZ |

---

## 4. 117/23 ve 137/12 üzerinde güvenilir ölçebildiklerimiz

**Tekrarlanabilirlik:** VisDrone tarafı kayıt üzerinden oynatıldığı için
**deterministiktir** — bu oturumdaki her yeniden koşum 6 basamağa kadar aynı
değerleri verdi (117/23 `0.700953`, 137/12 `0.547592`).

| değişken | araç | 117/23 | 137/12 |
|---|---|---|---|
| IoU, merkez hatası, kilit oranı, `t_drift` | `main.kos` | ✓ | ✓ |
| Yanlış-kilit karesi (4L tanımı) | `tani_yanliskilit` | ✓ (%0) | ✓ (%0.5) |
| PSR medyan / p5 | 4O, 4U | ✓ | ✓ |
| DCF atomları: `ix, iy, dx, dy`, tepe, ikinci tepe, PSR | `tani_4o_dcf` | ✓ | ✓ |
| DCF çekim noktası (sabit nokta) | 4O/4P yöntemi | ✓ | ✓ |
| Boyut serisi + `boyut/GT` oranı + aşama ayrıştırması | `tani_4r_boyut` | ✓ | ✓ |
| `tavan_iou` → boyut/merkez katkı ayrımı | 4Q/4R | ✓ | ✓ |
| `rafine_kutu` kabul/red + iç büyüklükler (R1–R6) | `tani_4n_rafine` | ✓ | ✓ |
| Boyut donması (ardışık değişmeyen kare) | 4U | ✓ | ✓ |
| Hedef dışı nesnelerin görüntü mesafesi | `kare_etiketleri` | ✓ | ✓ |
| **Ego GT'si (kamera pozu)** | — | ✗ | ✗ (yalnızca Gazebo) |

**İki zorunlu uyarı:**

* **117/23 sonuçları havza-özgüdür (4L).** Değerler tekrarlanabilir ama
  **dayanıklı değil**: ilk kutu (−1, +1) px oynayınca IoU 0.701 → 0.111.
  Bu dizide ölçülen küçük IoU farkları tek bir havzanın özelliğidir.
* **137/12 yüksek kazançlı bir regresyon dedektörüdür (4U).** Tek kapı
  değişikliği IoU'yu −0.358 oynattı. Bu, onu *ince ayar* hedefi olarak değil,
  **regresyon çapası** olarak değerli kılar.

---

## 5. Bir sonraki optimizasyon adayının sağlaması ZORUNLU özellikler

| # | koşul | hangi başarısızlıktan geliyor |
|---|---|---|
| Z1 | Kararının girdisi, kararından **etkilenmemeli** (açık çevrim olmalı). | 4U (137/12 çöküşü) |
| Z2 | Bağımsız bir ölçümün **yerine geçmemeli**; ölçümü hızlandırmalı/ağırlıklandırmalı. | Deney 1, 3, 4A |
| Z3 | **İki bağımsız gerçek dizide birden** doğrulanmalı — 4C 117/23'te, 4U 137/12'de düştü. Tek dizi yeterli değil. | 4C, 4U |
| Z4 | Yalnızca Gazebo kanıtı yeterli değil; Gazebo↔VisDrone tersine dönüşü belgelidir. | 4C, 4D, 4E, 4H |
| Z5 | Eşiği **tek bir kaynakta** seçilmemeli: LOSO aktarımında TPR eğitim kaynağına göre 0.00–1.00 arasında değişiyor. | 4T |
| Z6 | Kabul ölçütü koşumdan **önce** yazılmalı; çapalarda (G3_agresif, G3_kritik, G0) regresyon olmamalı. | 4U (uygulandı) |
| Z7 | Ölçtüğü büyüklük **mutlak** olmalı — sadece oran/hız değil — çünkü mevcut hata **birikmiş mutlak** bir hatadır (kutu/GT 0.53…1.88). | 4R, 4S |

---

## 6–7. Mevcut kodda bu koşulları sağlayan bağımsız bir sinyal var mı?

Kilitli daldaki (`KILITLI`) tüm sinyaller tarandı:

| sinyal | `boyut`tan bağımsız mı? | mutlak mı? | hüküm |
|---|---|---|---|
| DCF `PSR`, tepe, ikinci tepe | **hayır** — yama `boyut × dolgu` ile kesilir | — | Z1/Z7 düşer |
| `rafine` oranı (`bileşen/boyut`) | **hayır** — tanım gereği | hayır | 4U'da ölçüldü, çöktü |
| `imza.benzerlik`, `imza_ref` | **hayır** — yamalar `kutu`dan | — | Z1 düşer |
| `_hareketli` / zemin artığı | evet (konum tabanlı) | — | **boyut hakkında bilgi taşımıyor** |
| `ego.olcek_katsayisi` | **EVET** — `sqrt(|det M|)`, hedef kutusu maskelenerek arka plandan kestirilir (`egomotion.py:107-115`) | **HAYIR — orandır, çapa değil** | Z7 düşer; ayrıca satır 264'te **zaten tüketiliyor** ve 4R'ye göre katkısı ×1.014–×1.176 |
| `HareketTespit.adaylar()` bileşen boyutu | **EVET** — eşikleri mutlaktır (`min_alan=3`, `max_kenar=160`, `esik_k=4.0`) | **EVET** | ama **KILITLI dalda hiç çağrılmıyor**: yalnızca `tarama` (satır 186) ve `_arama_adimi` (satır 476) |

> **Sonuç: mevcut akışta, kilitliyken hem `boyut`tan bağımsız hem MUTLAK olan
> tek bir sinyal YOKTUR.** En yakın aday (`ego.olcek_katsayisi`) bir orandır
> ve zaten kullanılıyor; birikmiş mutlak hatayı düzeltemez.
>
> **→ Madde 7 geçerlidir: yeni ölçüm gerekiyor.** Ama bu "yeni algoritma"
> değildir: gereken bağımsız ölçüm deponun içinde zaten yazılıdır
> (`HareketTespit.adaylar`, `tespit.py:47-84`); eksik olan, onun kilitli
> durumda **çağrılması ve doğrulanmasıdır**. Belgelenmiş engeli maliyettir
> (kodun kendi yorumu: *"Pahalı adım: sadece gerektiğinde çağır"*).

---

## 8. Optimizasyona geçmek için gereken MİNİMUM deney seti

| # | deney | tür | çıktısı |
|---|---|---|---|
| **D1** | `HareketTespit.adaylar()`ı **KILITLI karelerde de çalıştır ama SONUCU KULLANMA**; hedefin konumundaki bileşenin boyutunu GT ile karşılaştır. Kaynaklar: 117/23, 137/12, 305/5, G3_agresif, G3_kritik, G0, G6_agresif. | salt okunur | Bağımsız ölçüm **yeterince doğru mu?** (`bileşen/GT` dağılımı, `rafine`ninkiyle yan yana) |
| **D2** | D1'in **maliyeti**: kare başına ek süre, dönüşümlü koşum ya da mikro-benchmark ile (FPS makine yüküyle 2× oynuyor — hafıza notu). | salt okunur | Pi Zero hedefiyle uyumlu mu? |
| **D3** | Yalnızca D1 "yeterince doğru" derse: **tek değişkenli** A/B — bağımsız ölçüm `_boyut_tazele`'ye **ek** girdi olarak (yerine değil, Z2) verilir; kabul ölçütü önceden yazılır, çapalar korunur. | müdahale | DESTEKLENDİ / REDDEDİLDİ |

D1 olumsuz çıkarsa optimizasyon hattı boyut tarafında kapanır ve açık kalan
tek yol A1'dir (DCF yamasındaki arka plan bulaşması) — ki 4B/4E onun `ara()`'nın
tamamını etkilediğini ve ayrı bir tasarım turu gerektirdiğini kaydetmiştir.

---

# KARAR: **C) MEVCUT PIPELINE İLE GÜVENİLİR OPTİMİZASYON MÜMKÜN DEĞİL; YENİ ÖLÇÜM GEREKİYOR**

Gerekçe, iki bağımsız hattın **aynı duvara** çarpmış olmasıdır:

* **4D** (rafine ağırlığını adaptif yapmak) → *ayırt edici sinyal yok*.
* **4T + 4U** (rafine kabul kapısı) → sinyal var ama **kararın etkilediği**
  büyüklük olduğu için kapalı çevrimde yıkıldı (137/12: IoU 0.548 → 0.190).

Aradaki ortak kısıt Z1 + Z7'dir: kilitli durumda `boyut`tan bağımsız **ve**
mutlak bir ölçüm yoktur. Bu ölçüm eklenmeden yapılacak her kabul/ağırlık
ayarı, ölçtüğü büyüklüğü kendisi bozan bir çevrimin içinde kalır — Faz C'de
beş kez gösterilen kip budur.

**Bu "başka bir aday deneyin" demek değildir:** D1 tanımlıdır, salt okunurdur
ve deponun içindeki mevcut bir fonksiyonu ölçer. Optimizasyona ancak D1 ve D2
olumlu sonuçlanırsa geçilmelidir.

**Bu turda hiçbir kod değişikliği yapılmadı; `takip/` md5 6/6 aynı.**
