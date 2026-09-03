# Deney 4D — adaptif r_carpan için sinyal teşhisi

**Salt okunur. Kod değişikliği yok, commit/push yok.** `takip/` altındaki 6
dosyanın md5'i Deney 2 durumuyla birebir. Ölçüm aracı:
`gazebo/tani_agirlik.py` — alt sınıf sarması + `rafine_kutu` saydam sarması.

## Soru

Deney 4C, `r_carpan`ı 1.0 → 0.17 sabitleyerek düştü: rafine merkezinin
doğruluğu sahneye göre değişiyor (Gazebo 0.76 px, VisDrone 117/23 4.78 px —
**6.3 kat**) ve tek bir sabit ağırlık ikisine birden uyamıyor. Bu tur, ağırlığın
o karede **mevcut sinyallerden türetilip türetilemeyeceğini** ölçer.

Karar anı `izleyici.py:567`. O anda bedelsiz erişilebilen sinyaller:

| sinyal | kaynak |
|---|---|
| `d_kf` = \|yeni_c − kf.konum\| | satır 568'de **zaten** hesaplanıyor |
| `oran_w`, `oran_h`, \|oran_ort−1\| | `rafine_kutu` içinde **zaten** deneniyor |
| `psr` | bu karenin DCF güveni |
| `ego_guven` | RANSAC iç oranı |
| kutu köşegeni | 4B'de merkez hatasıyla ilişkili çıktı |
| rafine tutarlılığı | ardışık rafine merkezlerinin ego-telafili hareketi (hafıza ister) |

Hedef değişken: \|rafine merkezi − GT merkezi\| (yalnızca ölçüm için).

## 1. Senaryo içi korelasyonlar

| senaryo | n | rafine hata p50/p95 | en güçlü sinyal (Pearson / Spearman) |
|---|---|---|---|
| G3_agresif | 62 | 0.75 / 1.23 px | tutarlılık −0.367 / −0.338 (**ters işaret**) |
| G3_kritik | 49 | 0.75 / 1.06 px | PSR −0.374 / −0.457 |
| 0000117/23 | 65 | **4.78 / 15.28 px** | d_kf +0.786 / **+0.548** |
| G0 | 72 | 0.48 / 1.27 px | d_kf +0.896 / +0.374 |
| G6_agresif | 49 | 0.95 / 37.57 px | d_kf +0.898 / +0.250 |
| 0000182/127 | 16 | 2.10 / 407.93 px | tutarlılık +0.805 / +0.875 |

İki gözlem:

* **G3 ailesinde hiçbir sinyal yok** — tüm \|Pearson\| ≤ 0.37, çoğu < 0.25. Zaten
  tahmin edilecek bir şey de yok: rafine orada p95 1.06–1.23 px.
* Yüksek Pearson'ların hepsinde **Spearman çok daha düşük** (0.786 → 0.548,
  0.896 → 0.374, 0.898 → 0.250). Yani ilişki birkaç uç değerden geliyor,
  monoton bir sıralama ilişkisi değil.

## 2. Havuzlanmış ayırt edicilik

313 rafine ölçümü, "kötü" = hata > 3 px (64 kare, %20):

| sinyal | AUC | okuma |
|---|---|---|
| **d_kf** | **0.852** | ayırt ediyor |
| kutu köşegeni | 0.762 | ayırt ediyor |
| rafine tutarlılığı | 0.693 | zayıf |
| \|oran_ort−1\| | 0.662 | zayıf |
| PSR | **0.360** | **şanstan kötü** |

Eşik tablosu ilk bakışta ikna edici:

| | n | rafine hata p50 |
|---|---|---|
| d_kf > 7 px | 74 | **4.64 px** |
| d_kf ≤ 7 px | 239 | **0.75 px** |

6.2 kat ayrım. **Ama bu sayı yanıltıcı.**

## 3. Çelişki: d_kf aslında neyi ölçüyor?

`d_kf = |yeni_c − kf.konum|` iki hatanın **farkıdır**; tek başına hangisinin
büyük olduğunu söylemez. Ayrıştırıldığında:

| senaryo | corr(d_kf, **rafine** hatası) | corr(d_kf, **Kalman** hatası) |
|---|---|---|
| **G3_agresif** | P **−0.142** / S −0.157 | P **+0.971** / S +0.966 |
| **G3_kritik** | P **−0.222** / S −0.091 | P **+0.981** / S +0.954 |
| G0 | +0.896 / +0.374 | +0.537 / +0.923 |
| G6_agresif | +0.898 / +0.250 | +0.401 / +0.772 |
| 0000117/23 | +0.786 / +0.548 | +0.233 / +0.295 |

**G3 ailesinde d_kf, Kalman'ın kendi hatasını ölçüyor (P ≈ 0.97–0.98), rafine'nin
hatasını değil (P ≈ −0.15…−0.22, üstelik ters işaretli).**

Nedeni 4B'den biliniyor: G3'te Kalman merkezi DCF biası yüzünden ~4 px kaymış
durumda. Rafine kusursuz olduğunda bile `|yeni_c − kf.konum|` büyük çıkar —
çünkü büyük olan rafine'nin sapması değil, Kalman'ın sapması.

Rafine'nin **doğru** olduğu karelerde d_kf:

| senaryo | doğru kare (hata<1.5px) | rafine hata | d_kf p50 | d_kf p95 |
|---|---|---|---|---|
| G0 | 69/72 | 0.46 px | 1.50 | 2.50 |
| **G3_agresif** | **61/62** | 0.75 px | **4.61** | 6.71 |
| **G3_kritik** | **49/49** | 0.75 px | **5.59** | 9.22 |
| 0000117/23 | 7/65 | 1.16 px | 4.12 | 8.86 |

G3'te rafine **her karede** doğru ama d_kf 4.6–5.6 px. Ağırlığı d_kf'e bağlamak,
rafine'ye **tam olarak en çok ihtiyaç duyulan karelerde** güveni azaltırdı —
istenenin tersi.

### Havuzlanmış AUC 0.852 neden yanıltıcı

Senaryo içi AUC'ler:

| senaryo | kötü kare | senaryo içi AUC |
|---|---|---|
| G3_agresif | **0/62** | ölçülemez (kötü kare yok) |
| G3_kritik | **0/49** | ölçülemez |
| G6_agresif | 11/49 | 0.713 |
| 0000117/23 | 44/65 | 0.738 |
| G0 | 3/72 | 1.000 (n=3) |
| 0000182/127 | 6/16 | 1.000 (n=6) |

Havuzlanmış 0.852, **karışım etkisidir**: G3 ailesi 111 "iyi" kare katıyor ve
hiç "kötü" kare katmıyor. Anlamlı ölçülebilen iki senaryoda AUC 0.713 ve 0.738
— "zayıf".

## 4. Belirleyici test: senaryolar arası ayrım

4C'yi öldüren şey buydu. Sinyal, "Gazebo'da rafine 0.76 px — güven" ile
"117/23'te 4.78 px — güvenme" arasını **GT görmeden** ayırabilmeli.

| senaryo | GERÇEK hata | d_kf | \|oran−1\| | PSR | köşegen | tutarlılık |
|---|---|---|---|---|---|---|
| G0 | 0.48 | 1.50 | 0.013 | 124.2 | 62.0 | 1.81 |
| G3_agresif | 0.75 | 4.57 | 0.091 | 64.8 | 67.7 | 0.51 |
| G3_kritik | 0.75 | 5.59 | 0.058 | 71.2 | 71.9 | 1.08 |
| G6_agresif | 0.95 | 7.02 | 0.090 | 35.4 | 69.1 | 9.44 |
| 0000182/127 | 2.10 | 2.15 | 0.216 | 28.2 | 16.3 | 2.20 |
| **0000117/23** | **4.78** | **6.96** | **0.071** | **76.6** | 73.8 | 2.21 |

Senaryo sıralaması Spearman:

| sinyal | Spearman | hüküm |
|---|---|---|
| \|oran_ort−1\| | +0.600 | doğru yön, zayıf |
| rafine tutarlılığı | +0.600 | doğru yön, zayıf |
| d_kf | **+0.486** | **ayırt edemiyor** |
| kutu köşegeni | +0.257 | ayırt edemiyor |
| PSR | **−0.429** | **TERS yön** |

Belirleyici çiftler:

* **d_kf:** 117/23 = 6.96 (hata 4.78) vs G6_agresif = 7.02 (hata **0.95**).
  Neredeyse aynı sinyal, **5 kat** farklı gerçek. G3_kritik 5.59 (hata 0.75) ile
  aralıklar tamamen örtüşüyor.
* **\|oran−1\|:** 117/23 = 0.071, G3_agresif = 0.091. Sinyal 117/23'ü **daha iyi**
  gösteriyor, oysa gerçekte 6.4 kat kötü.
* **PSR:** 117/23'ün PSR'si **en yüksek** (76.6) ve rafine'si **en kötü**.
  Ağırlığı PSR'a bağlamak 4C'nin hatasını daha da büyütürdü.

## 5. Cevap: "Bu sinyaller rafine'nin kötü olduğu kareleri ayırt edebiliyor mu?"

**Kısmen — ama işe yaramaz biçimde.**

* **Katastrofik** kareleri (hata > 7–10 px) d_kf yakalıyor; ama kodda **zaten**
  bir kapı var (satır 568, `< 0.6 × boyut.max()`) ve bu tür kareler zaten
  nadir.
* **Sistematik orta düzey** bozulmayı — 117/23'ün her karesinde 4.78 px —
  **hiçbir sinyal görmüyor.** 4C'yi öldüren tam olarak buydu.
* G3 ailesinde en güçlü aday sinyal (d_kf) rafine'nin değil **Kalman'ın**
  hatasını ölçüyor ve ağırlığı ters yöne sürerdi.

## 6. KARAR: **B — sinyal zayıf**

Adaptif `r_carpan` fikri **elendi**. Mevcut pipeline'da, rafine merkez ölçümünün
o karedeki güvenilirliğini GT görmeden kestirebilecek bir sinyal yok. Ölçülen
her aday ya karışım etkisiyle şişmiş (d_kf), ya ters yönlü (PSR), ya da
belirleyici çiftte başarısız (\|oran−1\|).

### Sonraki teşhis önerisi: DCF arka plan bulaşması, kaynağında

4B'nin bulgusu duruyor ve hâlâ en büyük tek kaldıraç: DCF tepesi görüntü −x
yönünde sistematik kayıyor (G3_agresif −4.17 px), bu yön bağıl arka plan
akışının yönü, ve sapma öğrenmeyle büyüyor (k+0'da ~0.8 px, k+80'de −5.6 px).
Sentetik doğrulama: koordinat dönüşümü kusursuz (dx = +0.000), kayan arka
planla öğrenme ise tam o yönde bias üretiyor.

Yapısal neden ölçülü: yama `boyut × dolgu`, `dolgu = 2.0` → alanın **~%75'i
arka plan**.

**Önerilen salt okunur teşhis — `dolgu` süpürmesi:**

Kaydedilmiş karelerde, takipçinin **gerçek** kutu/merkez yörüngesini sabit
tutarak, her karede DCF yanıtını `dolgu ∈ {1.3, 1.5, 1.7, 2.0, 2.5}` için ayrı
ayrı hesapla ve şunları ölç:

1. tepe konumunun GT'ye hatası (dx, dy, \|e\|) — bias `dolgu` ile azalıyor mu?
2. PSR — pencere küçülünce ayırt edicilik düşüyor mu?
3. etkin arama yarıçapı `0.5 × dolgu × boyut.min()` ile Faz B'de ölçülen
   `d_artık` (p95 ≤ 0.73) karşılaştırması — arama menzili yetmeye devam ediyor mu?
4. aynı süpürme **hem Gazebo hem VisDrone**'da — 4C'nin dersi: tek hatta
   ölçülen oran genellenmiyor.

Bu teşhis, bir sonraki tek değişikliği (`dolgu` değeri) doğrudan besler ve
uygulanmadan önce hem kazancı hem riski (arama menzili daralması) sayısallaştırır.

**Uyarı:** `dolgu` değişikliği `ara()`'nın tamamını etkiler, yani 32 senaryonun
hepsini değiştirir. "30/32 birebir" ölçütü o deney için yapısal olarak
uygulanamaz — 4C'de olduğu gibi. Deney tasarımında bu ölçüt baştan
"regresyon yok" biçiminde yeniden tanımlanmalıdır, sonradan gevşetilerek değil.
