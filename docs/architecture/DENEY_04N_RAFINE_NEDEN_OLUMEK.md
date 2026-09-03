# Deney 4N — `rafine_kutu` neden ölüyor?

**Salt okunur. `takip/` altında hiçbir dosya değiştirilmedi**, hiçbir eşik
gevşetilmedi, hiçbir düzeltme uygulanmadı, commit/push yok.
Ölçüm aracı (yeni, `takip/` dışında): `gazebo/tani_4n_rafine.py`.
Çıktı: `cikti/rafine_4n.json`.

**Yöntem.** `takip.tespit.rafine_kutu` **gerçek haliyle** çağrılır ve sonucu
aynen döndürülür; yanında aynı matematiğin satır satır işaretlenmiş bir
**kopyası** koşturulup hangi koşulun ilk kez kestiği okunur. `rafine_kutu` saf
bir fonksiyondur (durum tutmaz), bu yüzden ikinci kez çağrılması davranışı
değiştirmez. Her çağrıda kopyanın hükmü gerçekle karşılaştırıldı:
**274 çağrının 274'ünde sadakat ihlali yok (0).**

## 8. Baseline doğrulaması (önce yapıldı)

`takip/` md5'leri Deney 2 durumuyla **6/6 aynı** (deney öncesi = sonrası):

```
d41d8cd98f00b204e9800998ecf8427e  takip/__init__.py
c0fd7989d4e81219cd99447a12f8d78b  takip/cekirdekler.py
959da09ab43501a983629368a8f699b1  takip/egomotion.py
4257b94ce7f4978e172b8bb7c89816c1  takip/izleyici.py
874b3ccd540c8a6c783320c619a78f41  takip/mosse.py
3ff48dd869374d36937c18b640f2b21b  takip/tespit.py
```

Metrikler de birebir geldi:

| kaynak | IoU | kilit | drift | önceki tur |
|---|---|---|---|---|
| G6_agresif_durakli | 0.383 | %87.8 | 148 | 4L/4M ile aynı |
| G6_agresif | 0.618 | %100.0 | 294 | 4M ile aynı |
| 117/23 | 0.701 | %100.0 | yok | 4K ile aynı |
| 137/12 | 0.548 | %94.6 | 75 | 4K ile aynı |

---

# 1. `rafine_kutu`'nun None dönebileceği TÜM yollar

Kod yolu tek fonksiyondur: `takip/tespit.py:87–134`. Çağrı noktası
`izleyici.py:561` (`_boyut_tazele`), argümanlar:
`rafine_kutu(bgr, kf.konum, boyut, hedef_renk=self.imza.renk)` →
`buyutme=3.0`, `min_esik=16.0`, `renk_tol=60.0`.

| # | satır | koşul | sınıf |
|---|---:|---|---|
| **R1** | 108 | `n < 2` — eşik sonrası hiç bağlantılı bileşen yok | kontur/segmentasyon |
| **R2** | 114 | merkez boş **ve** `lbl` tümden boş | **ULAŞILAMAZ** (`n ≥ 2` iken `lbl` doludur) |
| **R3** | 117 | merkez boş, en yakın bileşen `(0.35·max(boyut))² + 4`'ten uzak | geometri |
| **R4** | 122 | `not (0.35 < mean(bw/W, bh/H) < 2.6)` | boyut/oran |
| **R5** | 129 | `sec.sum() < 1` | **ULAŞILAMAZ** (`et` bileşeninin kutusunda o etiketten piksel vardır) |
| **R6** | 132 | `‖bileşen_ort_renk − imza.renk‖ > 60` | **renk kapısı** |
| — | 100 | `cv2.getRectSubPix` istisnası | görüntü/yama |

**Kodda AÇI FİLTRESİ YOKTUR.** `rafine_kutu` açıya hiç bakmaz; bir kontur
uydurma (`minAreaRect`, `fitEllipse`) da yapmaz. Alan için ayrı bir filtre de
yoktur (`min_alan` başka bir fonksiyona, `HareketTespit.adaylar`'a aittir ve
bu yol onu çağırmaz). Yani hipotez **A** ve saf haliyle **C** kod okumasıyla
zaten elenir.

# 2–3. Ölçüm: hangi koşul, hangi karede? (durakli vs kontrol)

274 çağrının tamamı (dört kaynak, tüm koşumlar):

| koşul | çağrı | başarısızlıkların payı |
|---|---:|---:|
| OK | 182 | — |
| **R6_renk** | **79** | **%86** |
| R4_oran | 12 | %13 |
| R3_merkez_uzak | 1 | %1 |
| R1 / R2 / R5 / cv2 istisnası | **0** | **%0** |

### `G6_agresif_durakli` — kare 120–179

| kare | neden | bileşen w/h | kutu w/h | GT w/h | oran ort | **renk mesafe** | bileşen ort. renk (BGR) |
|---:|---|---|---|---|---:|---:|---|
| 123 | OK | 56/39 | 64/34 | 59/40 | 1.02 | 42.9 | [200, 110, 110] |
| 127 | OK | 57/38 | 62/35 | 58/38 | 1.01 | 42.9 | [200, 110, 110] |
| 131 | OK | 56/39 | 60/36 | 57/35 | 1.01 | 44.2 | [200, 110, 110] |
| **135** | **R6_renk** | **101**/33 | 59/36 | 57/33 | 1.31 | **96.4** | **[133, 151, 158]** |
| 139 | R6_renk | 85/31 | 59/36 | 57/30 | 1.15 | 104.7 | [121, 154, 163] |
| 143 | R6_renk | 70/28 | 59/36 | 57/28 | 0.98 | 92.0 | [119, 146, 154] |
| 147 | R6_renk | 58/27 | 59/36 | 56/25 | 0.86 | 107.2 | [100, 155, 165] |
| 151–179 | R6_renk (8 çağrı) | 54–76/24–32 | 59/36 | 57–60/25–38 | 0.79–1.07 | 85.9–129.1 | [88–124, 147–173, 155–184] |

### `G6_agresif` (kontrol) — kare 120–179

| kare | neden | bileşen w/h | kutu w/h | GT w/h | oran ort | **renk mesafe** | bileşen ort. renk (BGR) |
|---:|---|---|---|---|---:|---:|---|
| 123–135 | **OK** (4 çağrı) | 56–57/33–38 | 59–63/35–36 | 57–59/33–39 | 0.94–1.00 | 46.0–51.4 | [204–207, 103–104, 103–104] |
| **139** | **R6_renk** | **99**/39 | 59/35 | 58/30 | 1.40 | **95.4** | **[133, 150, 157]** |
| 143–175 | R6_renk (9 çağrı) | 59–122/36–46 | 59/35 | 56–60/25–37 | 1.03–1.69 | 84.0–95.2 | [126–136, 146–151, 153–158] |
| 179 | R6_renk | 67/36 | 59/35 | 60/38 | 1.08 | 68.1 | [204, 109, 109] |
| **195–215** | **OK** (6 çağrı) | — | 59/35 | — | — | — | — |

**Kontrolde `rafine_kutu` AYNI koşulda, AYNI sayılarla, 4 kare sonra ölüyor.**
Bileşen ortalama rengi iki senaryoda da tam olarak aynı sıçramayı yapıyor:
mavi araç **[≈203, 106, 106]** → **[≈133, 150, 157]**.
Bileşen genişliği iki senaryoda da ~57 px'den **99–101 px**'e çıkıyor.

# 5. Hipotezlerin ayrıştırılması

| hipotez | hüküm | kanıt |
|---|---|---|
| **A) açı filtresi** | **ELENDİ** | `rafine_kutu`'da açı filtresi/kontur uydurma **yok** (kod okuması) |
| **B) şekil/geometri** | **ELENDİ** | tek geometri kapısı R3; 274 çağrıda **1** kez, o da kare 295'te (yanlış kilit çoktan başlamış) |
| **C) boyut/alan** | **İKİNCİL** | R4 12/92 (%13); her seferinde bileşen zaten bozuk (`bileşen_alanı/GT_alanı` 0.07–0.27) → sonuç, neden değil |
| **D) görüntü sınırı / yama** | **ELENDİ** | 0 `cv2` istisnası, 0 R1, 0 R2 — maske hiçbir çağrıda boş kalmadı (doluluk %9–20) |
| **E) kontur/segmentasyon** | **ÜST AKIŞTAKİ NEDEN** | bileşen artık hedef değil (birleşme ya da parçalanma) — ama bu hiçbir zaman "boş maske" olarak görünmüyor, **R6 üzerinden** çıkıyor |
| **F) başka koşul → renk kapısı R6** | **TERMİNAL KOŞUL** | tüm başarısızlıkların **%86'sı**; dört kaynağın dördünde de ilk başarısız koşul R6 |

# 6. R6 kök neden mi, zincirin sonucu mu?

**Sonucu.** Üç bağımsız ölçüm bunu gösteriyor.

### (a) Gazebo'da birleşme ortağı GT ile kimliklendirildi: **ÇELDİRİCİ ARAÇ**

`veri/gazebo.py:celdiriciler` ile çeldiricinin GT kutusu okunup seçilen
bileşenin kutusuyla karşılaştırıldı (`G6_agresif_durakli`):

| kare | hedef GT | çeldirici GT | seçilen bileşen | IoU(bileşen, hedef) | **IoU(bileşen, çeldirici)** | hedef–çeldirici mesafe |
|---:|---|---|---|---:|---:|---:|
| 131 | [293, 215, 57, 35] | [353, 216, 54, 22] | [303, 208, 56, 39] | 0.55 | **0.04** | 60 px |
| **135** | [252, 223, 57, 33] | [296, 226, 53, 22] | [262, 224, **101**, 33] | 0.41 | **0.35** | **44 px** |
| 139 | [217, 198, 57, 30] | [245, 202, 54, 22] | [225, 206, 85, 31] | 0.33 | 0.33 | 28 px |
| 147 | [189, 113, 56, 25] | [187, 114, 56, 25] | [187, 120, 58, 27] | 0.54 | **0.58** | 2 px |
| 151 | [197, 94, 57, 30] | [184, 97, 56, 26] | [183, 95, 67, 28] | 0.70 | **0.77** | 14 px |

Çeldirici, hedefe görüntüde yaklaşıyor (60 → 44 → 28 → **2 px**) ve `buyutme=3.0`
ile açılan **177×109 px**'lik rafine penceresine giriyor. 82. persentil eşiği +
3×3 `MORPH_CLOSE` iki aracı **tek bağlantılı bileşende birleştiriyor** (bileşen
genişliği 57 → 101 px). Birleşmiş bileşenin ortalama rengi mavi araç ile
çeldiricinin karışımıdır → imzaya uzaklık 92–107, tolerans 60 → **R6 ateşler**.

Yani **R6 hatalı davranmıyor; tam da belgelendiği işi yapıyor**
(`tespit.py:124-126`: *"hedefin bilinen rengine uymayan lekeyi kabul
etmektense rafine etmemek daha iyidir"*). Yanlış bir ölçümü reddediyor.

### (b) Nedensellik testi: çeldirici çekilince rafine KENDİLİĞİNDEN düzeliyor

`G6_agresif` (kontrol), hiçbir müdahale olmadan:

| kare | hedef–çeldirici mesafe | takip merkezi hedef GT'sinin içinde mi | rafine |
|---:|---:|---|---|
| 175 | 56.9 px | evet | R6_renk |
| 187 | 80.9 px | evet | R6_renk |
| 191 | 90.1 px | evet | R6_renk |
| **195** | **98.9 px** | evet | **OK** |
| 199–215 | 108–156 px | evet | OK (5/5) |

Çeldirici pencere yarı-genişliğinin (≈89 px) dışına çıktığı anda R6 susuyor.
**Kapının açılıp kapanmasını belirleyen değişken, çeldiricinin pencere içinde
olup olmamasıdır.**

### (c) `durakli` neden düzelmiyor? — çünkü bu bir SONUÇ

`G6_agresif_durakli`'de çeldirici de uzaklaşıyor (195'te 86 px, 215'te 142 px)
ama rafine düzelmiyor. Nedeni ölçüldü: **takip merkezi artık hedef GT
kutusunun içinde değil** (175'ten itibaren "hayır"), yani pencerede hedef
yok. Bu, yanlış kilidin sonucudur, sebebi değil.

### (d) Gerçek veride üst akış farklı, terminal koşul aynı

| kaynak | R6 anında bileşen–GT IoU | bileşen alanı / GT alanı | üst akıştaki gerçek arıza |
|---|---:|---:|---|
| G6 (iki senaryo) | 0.33–0.41 | 0.87–1.33 | **birleşme** (çeldirici) |
| 117/23 | 0.10–0.62 | **0.07–0.33** | **parçalanma** — kontrast yalnızca 5.2 (4I), 82. persentil aracı bölüyor |
| 137/12 | **0.93–0.97** | 0.52–0.65 | bileşen **DOĞRU**; kusurlu olan **referans renk** — ilk kutu GT'den çok büyük (76×85 vs 52×65) olduğu için `imza.renk` yola bulanmış |

Üçü de aynı kapıdan (R6) çıkıyor ama üç ayrı üst akış nedeniyle. **R6, farklı
arızaların ortak çıkış kapısıdır — kendisi arıza değildir.**

---

# Zorunlu tablo

| Kaynak/senaryo | İlk None frame | İlk başarısız koşul | Değişmeye başlayan değişken | Kontrolde durum | Kök neden adayı |
|---|---:|---|---|---|---|
| **G6_agresif_durakli** | **135** (sürekli seri 135–267) | **R6_renk** (renk mesafesi 44.2 → 96.4) | bileşen ort. rengi [200,110,110] → [133,151,158]; bileşen genişliği 56 → **101 px**; IoU(bileşen, çeldirici) 0.04 → 0.35 | **kontrolde de aynı ölüm, 4 kare sonra** | çeldirici aracın 177 px'lik rafine penceresine girip hedefle tek bileşende birleşmesi (mesafe 60 → 44 px) |
| **G6_agresif** (kontrol) | **139** (sürekli seri 139–191) | **R6_renk** (51.4 → 95.4) | bileşen ort. rengi [207,104,104] → [133,150,157]; bileşen genişliği 57 → **99 px** | — (kontrolün kendisi); **çeldirici 99 px'e uzaklaşınca kare 195'te KENDİLİĞİNDEN düzeliyor** | aynı çeldirici birleşmesi |
| **117/23** | 15 (izole); sürekli seri 311–347 | **R6_renk** (60.1–129.9), sonra R4_oran | bileşen alanı GT'nin yalnızca **%7–33'ü** (parçalanma), bIoU 0.10–0.15'e iniyor | — (karar dışı, yalnızca kontrol) | düşük kontrast (4I: 5.2) → 82. persentil eşiği aracı parçalara bölüyor |
| **137/12** | 83 (sürekli seri 83–151) | **R6_renk** (64.8–134.8) | bileşen GT ile **bIoU 0.93–0.97** (doğru!), değişen şey referans: kutu 76×85 iken GT 52×65 | — (karar dışı, yalnızca kontrol) | `imza.renk` aşırı büyük ilk kutuda yol pikselleriyle bulandığı için **doğru bileşen** reddediliyor |

---

# KARAR: **MEKANİZMA REDDEDİLDİ**

4M'nin bıraktığı aday kök neden — *"`rafine_kutu`'nun kopuştan önce ölmesi"* —
**yanlış kilidin kök nedeni değildir.** Yeni bir optimizasyona geçilmiyor.

**Neden reddedildi:**

1. **Kontrol tam olarak aynı ölümü yaşıyor ve kopmuyor.** `G6_agresif`'te
   `rafine_kutu` kare 139'da, aynı koşuldan (R6), aynı sayılarla
   (renk mesafesi ≈95, bileşen genişliği ≈99 px, aynı [133,150,157] rengi)
   ölüyor; 14 çağrı boyunca ölü kalıyor; senaryo 300 karede **hiç yanlış kilit
   üretmiyor** (kilit %100). Aynı arıza, zıt sonuç → arıza ayırt edici değil.
2. **Ölümün nedeni takipçide değil, sahnede.** Ölümü tetikleyen değişken
   çeldirici aracın görüntüdeki mesafesidir (60 → 44 px girişte, 99 px'te
   çıkışta) ve bu iki senaryoda **birebir aynıdır**, çünkü çeldirici sabittir
   ve kamera 0.01 px içinde özdeştir (4M §0).
3. **R6 bir hata değil, doğru çalışan bir korumadır.** Birleşmiş bileşen
   gerçekten hedef değildir; `rafine_kutu` onu kabul etseydi kutu çeldiriciyi
   de kapsayacak biçimde şişerdi. Kapıyı gevşetmek arızayı çözmez, **yanlış
   ölçümü içeri alır.**
4. **`durakli`'nin düzelmemesi bir sonuçtur.** Çeldirici uzaklaştıktan sonra
   kontrol düzeliyor; `durakli` düzelmiyor çünkü takip merkezi artık hedefin
   GT kutusunun içinde değil (kare 175'ten itibaren ölçüldü). Bu, yanlış
   kilidin ardılıdır.

**Bunun 4M için anlamı:** 4M'de ölçülen gerçek ayrışma — **kare 142'de DCF
along-track artığının işaret değiştirmesi** — hâlâ açıklanmamıştır.
4N bu ayrışmaya dokunmadı; yalnızca 4M'nin önerdiği adayı eledi. Rafine ölümü
**iki senaryonun ORTAK ön koşuludur**, ayırt edici değişkeni değildir.

**Bu turda hiçbir optimizasyon, hiçbir eşik değişikliği, hiçbir düzeltme
uygulanmadı; `takip/` md5 6/6 aynı.**
