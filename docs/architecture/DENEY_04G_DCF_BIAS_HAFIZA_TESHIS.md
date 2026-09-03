# Deney 4G — DCF biası / template hafızası genelleme teşhisi

**Salt okunur. Kod değişikliği yok, commit/push yok.** `takip/` altındaki 6
dosyanın md5'i Deney 2 durumuyla birebir (`md5sum -c` 6/6 OK).
Ölçüm aracı: `gazebo/tani_hafiza.py` — alt sınıf + wrapper.

## Mimari — gerçek isimler (grep ile doğrulandı, tahmin yok)

| istenen | koddaki karşılık |
|---|---|
| 1. öğrenme oranı | `cekirdekler.py:103` `self.lr` (varsayılan 0.09) — **ama çağrı anında ezilir**: `izleyici.py:315` `lr = 0.125 if self.boyut.max() > 18 else 0.04`, `:316` `cekirdek.ogren(..., lr)` |
| 2. template güncellemesi | `cekirdekler.py:214-215` `ogren` içinde `self.A = (1-lr)*self.A + lr*(G*conj(F))`, `self.B = (1-lr)*self.B + lr*(F*conj(F)).sum(0)` → şablon durumu **(A, B)** |
| 3. DCF response / peak | `cekirdekler.py:175` `_yanit` → `_tepe(r, self.N, merkez, w, h)`; `izleyici.py:_takip_adimi`'nda `yeni` |
| 4. peak'in GT'ye dx/dy biası | boru hattında **yok** — burada dışarıdan ölçüldü |
| 5. arka plan hareketi sinyali | ego matrisi `M` (`izleyici.py:249` `cekirdek.ego_guncelle(M)`); hedefteki akış = `M(c) − c`, aynı ifade `izleyici.py:255` `ongoru` olarak zaten var |
| 6. ego/hedef ayrımı | `gazebo/tani.py:354` `d_artik` — **poz gerektirir, yalnızca Gazebo**. VisDrone'daki karşılığı `ongoru` artığı (kestirilen M ile) |

### Türetilen öğrenme sinyalleri (sabit formül varsayılmadı)

    kisa_degisim = ||A_t − A_{t−1}||_F / ||A_t||_F      bir adımlık güncelleme
    kum_degisim  = ||A_t − A_0||_F   / ||A_0||_F        kilitten bu yana
    lr           = o karede geçirilen değer

## TEST 3 — Bias zamanla büyüyor mu?

DCF dx, kilitten sonraki kareye göre:

| kaynak | k+0 | k+10 | k+20 | k+40 | k+80 | k+160 | lr p50 |
|---|---|---|---|---|---|---|---|
| G0 (kontrol) | −1.66 | −1.13 | −0.89 | −1.62 | −2.47 | −1.78 | 0.125 |
| G3_agresif | −0.78 | −1.16 | −1.33 | −3.28 | **−5.57** | −5.26 | 0.125 |
| G3_kritik | −0.42 | −0.66 | −0.46 | −2.16 | **−5.99** | −7.11 | 0.125 |
| **117/23** | **−0.72** | +0.72 | +1.00 | +0.98 | **−3.43** | **−9.03** | 0.125 |

30 karelik pencerelerde:

    G3_agresif  −1.28 −4.10 −5.20 −5.30 −6.40 −5.49 −4.22 −3.77 −2.76
    G3_kritik   −0.59 −3.44 −4.93 −4.78 −7.43 −7.85 −5.84 −5.22 −3.84
    117/23      +0.07 +0.60 −0.98 −3.07 −5.72 −7.34 −3.54 −11.09 −14.21 −9.93

**EVET, ve gerçek veride de.** 4B'nin Gazebo bulgusu (~0.8 → ~5.6 px)
117/23'te tekrarlanıyor ve daha da büyüyor (−0.72 → −14.2 px).

**268/31 dışlandı:** kilit anından itibaren dx = −540 px ve 151. karede drift;
takipçi orada hiç kilitlenmiyor (kontrast −36.9, hedef 12×6 px). Sayıları bu
soru için bilgi taşımıyor.

## TEST 1 — Hafıza ilişkisi

`|dx|` ile öğrenme geçmişi korelasyonu (senaryo içi):

| kaynak | n | \|dx\| ~ **kümülatif template değişimi** | \|dx\| ~ kilitten kare | \|dx\| ~ kısa değişim |
|---|---|---|---|---|
| G0 | 293 | P **+0.795** / S +0.793 | −0.548 / −0.534 | +0.550 / +0.707 |
| G3_agresif | 293 | P **+0.673** / S +0.601 | −0.025 / −0.114 | +0.464 / +0.450 |
| G3_kritik | 293 | P **+0.350** / S +0.326 | +0.334 / +0.239 | +0.228 / +0.240 |
| **117/23** | 342 | P **+0.582** / S +0.614 | +0.585 / +0.631 | −0.054 / −0.065 |
| **POOLED** | 1221 | P **+0.637** / S +0.642 | — | — |

**Kümülatif template değişimi, dört kaynağın DÖRDÜNDE de pozitif** — VisDrone
dahil. Ve pooled değer senaryo-içi değerlerle **aynı işarette ve aynı
büyüklükte**: **Simpson etkisi yok**.

Buna karşılık "kilitten geçen kare" işaret değiştiriyor (−0.548 … +0.585) —
yani mekanizma **zamanın kendisi değil, öğrenmenin miktarı**.

Kümülatif değişimin seyri:

| kaynak | k+10 | k+40 | k+80 | k+160 | son |
|---|---|---|---|---|---|
| G0 | 0.162 | 0.359 | 0.326 | 0.159 | 0.154 |
| G3_agresif | 0.085 | 0.360 | 0.713 | 0.331 | 0.264 |
| G3_kritik | 0.091 | 0.448 | 0.713 | 0.437 | 0.242 |
| 117/23 | 0.370 | 0.478 | 0.487 | **0.984** | 0.942 |

117/23'te şablon kilit halinden **%98** uzaklaşmış — Gazebo'nun 3–4 katı.

## TEST 2 — Bias yönü ile arka plan akışı

Bağıl akış = `M(gt_önceki) − gt_şimdi` (hedefin kendi görüntü hareketi
çıkarılmış; Gazebo'da hedef görüntüde sabit olduğu için mutlak akışa eşit,
VisDrone'da **farklı** ve doğru ölçüt budur):

| kaynak | bias dx | bias dy | bağıl dx | bağıl dy | **açı farkı** | \|bias\|/\|akış\| |
|---|---|---|---|---|---|---|
| G0 | −1.08 | −0.36 | −1.831 | −0.002 | **18.3°** | 0.62 |
| G3_agresif | −4.17 | −0.97 | −1.715 | −0.013 | **12.7°** | 2.50 |
| G3_kritik | −4.78 | −0.48 | −1.423 | −0.014 | **5.2°** | 3.38 |
| **117/23** | **−4.85** | −1.86 | **+0.217** | +0.104 | **175.3°** | 21.61 |

**Gazebo'da hizalı (5–18°), VisDrone'da neredeyse tam TERS (175.3°).**
Üstelik 117/23'te bağıl akış çok küçük (0.22 px/kare) ve bias/akış oranı 21.6 —
akış biası açıklayacak büyüklükte değil.

## TEST 5 — Alternatif açıklamaların ayrıştırılması

| # | hipotez | durum | kanıt |
|---|---|---|---|
| **A** | template öğrenmesi bias üretiyor | **DESTEKLENDİ (tek genellenen)** | kümülatif değişim ↔ \|dx\| dört kaynakta da pozitif (+0.35…+0.80), Simpson yok; bias öğrenmeyle büyüyor (TEST 3) |
| B | bias yalnızca Kalman/arama merkezi kaynaklı | **kısmen — kaynağa göre değişiyor** | DCF hatası − KF öngörü hatası: G3_agresif **+0.54**, G3_kritik **+0.55**, ama 117/23 **+0.09**, G0 +0.11. Gazebo'da DCF hata *enjekte ediyor*, gerçek veride neredeyse hiç |
| C | bias yalnızca arka plan hareketinden | **ELENDİ** | VisDrone'da yön 175.3° ters, akış 22 kat küçük |
| D | gerçek görüntüdeki hedef/arka plan görünümü | **doğrudan test edilmedi; dolaylı destek** | 4-sentez: kontrast Gazebo 48–146 vs 117/23 **4.8**; şablonun %98 uzaklaşması bununla tutarlı |
| E | padding / yama geometrisi | **ELENDİ** | 4E: padding–bias ilişkisi iki kaynakta ters yönlü |

Ayrıca elenen sürücüler (işaret tutarsız → nedensel olamaz):

| sürücü | G0 | G3_agresif | G3_kritik | 117/23 |
|---|---|---|---|---|
| \|dx\| ~ PSR | −0.836 | −0.190 | +0.055 | **+0.308** |
| \|dx\| ~ kutu genişliği | −0.017 | −0.551 | **+0.692** | +0.525 |
| \|dx\| ~ \|açı\| | — | −0.031 | +0.001 | — |

---

# Altı sorunun cevabı

### 1. DCF bias zamanla büyüyor mu?
**Evet, her iki veri kaynağında da.** Gazebo −0.8 → −5.6 px; VisDrone 117/23
−0.7 → −9.0 px (pencere ortalamalarında −14.2'ye kadar).

### 2. Büyüyorsa template öğrenmesiyle ilişkisi var mı?
**Evet ve bu ilişki genelleniyor.** Kümülatif template değişimi ile \|dx\|
korelasyonu dört kaynağın dördünde de pozitif (P +0.35…+0.80, S +0.33…+0.79),
pooled +0.637, Simpson etkisi yok. "Kilitten geçen kare" ise işaret değiştiriyor
— yani sürücü zaman değil, **öğrenme miktarı**.

### 3. Bias yönü arka plan akışıyla hizalı mı?
**Gazebo'da evet (5–18°), VisDrone'da hayır (175.3°, neredeyse tam ters).**
Yön bileşeni genellenmiyor.

### 4. Aynı mekanizma Gazebo ve VisDrone'da görülüyor mu?
**Yarısı evet, yarısı hayır.** Öğrenme–bias bağı genelleniyor; akış–yön bağı
genellenmiyor. Ayrıca DCF'in *taze enjeksiyonu* Gazebo'da +0.54 px/kare iken
gerçek veride +0.09 — yani gerçek veride bias tek bir aşamada üretilmiyor,
döngüde birikiyor.

### 5. Alternatiflerden hangileri elenebiliyor?
**C (yalnızca arka plan hareketi) ve E (padding/yama geometrisi) elendi.**
PSR, kutu boyutu ve açı da işaret tutarsızlığı nedeniyle sürücü olamaz.
**A (öğrenme) tek genellenen açıklama.** B kısmen ayakta (kaynağa göre
değişiyor), D doğrudan test edilmedi.

### 6. Bir sonraki adım için tek bir aday var mı?
**Evet, ama henüz deney değil — ve uygulanması davranış değişikliği gerektirir.**

---

## Hüküm

Hipotez şuydu:

> "DCF merkez biası, template'in etkin öğrenme hafızası **ile arka plan
> akışının birleşiminden** öngörülebilir biçimde oluşuyor **ve bu ilişki
> gerçek görüntü verisine genelleniyor**."

Bileşik haliyle **REDDEDİLDİ**: iki bileşenden biri (arka plan akışı → yön)
VisDrone'da tam ters çıkıyor, dolayısıyla "birleşiminden öngörülebilir" iddiası
kaynaklar arası kurulamıyor.

**Ama öğrenme bileşeni ayakta ve bu, Faz C'nin tamamındaki İLK genellenen
ilişkidir.** 4C (rafine oranı), 4D (güven sinyalleri) ve 4E (padding tepkisi)
üçü de kaynak değiştirince yön değiştirmişti; kümülatif template değişimi ↔
bias ilişkisi değiştirmiyor.

## Sıradaki tek aday (öneri, uygulama değil)

> Yalnızca **öğrenme bileşenini** mekanizma olarak sına: şablonun etkin
> hafızası değiştirildiğinde bias **her iki kaynakta da aynı yönde** ölçekleniyor
> mu?

Bu bir parametre araması değil, tahmin sınamasıdır: gözlemsel ilişki
(kümülatif değişim ↔ bias) nedenselse, hafıza kısaldığında bias iki kaynakta da
küçülmelidir; küçülmezse ilişki eşzamanlılıktan ibarettir ve hat kapanır.

**Bunun için `lr` değiştirilmesi gerekir ve `lr` çağrı anında
`izleyici.py:315`'te üretiliyor — yani bu bir DAVRANIŞ DEĞİŞİKLİĞİDİR.**
Salt okunur olarak yapılamaz. Bu turun kuralları gereği uygulanmadı; yapılıp
yapılmayacağı ayrı bir karardır.

Uygulanırsa dikkat edilmesi gerekenler (önceki turların dersleri):
* karar **Gazebo + 117/23 birlikte** verilmeli; yalnız Gazebo yeterli değil
* `lr` her senaryoyu etkiler → "30/32 birebir" ölçütü yapısal olarak
  uygulanamaz, tasarımda **baştan** "regresyon yok" biçiminde tanımlanmalı
* sim test2/test3 ve VisDrone 182/127 kaotik, karar dışı tutulmalı
* 268/31 hiçbir yapılandırmada çalışmıyor, karar dışı tutulmalı
