# Deney 4L — Karar verilebilir bir yanlış-kilit kaynağı var mı?

**Salt okunur. `takip/` hiç değiştirilmedi**, commit/push yok.
Ölçüm araçları (yeni, yalnızca gözlem): `gazebo/tani_yanliskilit.py`,
`gazebo/tani_yk_epizot.py`. Çıktılar: `cikti/yanliskilit.json`,
`cikti/yk_epizot.json`.

4K'nın bıraktığı tek soruyu yanıtlar:

> Yanlış kilidi ölçebilecek, metriği doygun **olmayan** ve kaotik **olmayan**
> bir kaynak var mı? Yoksa 4K'nın gerçek değeri (bias mı, yanlış kilit mi)
> ölçülemez.

**Cevap: EVET, tam olarak bir tane — `G6_agresif_durakli`.** Ama bulunan şey
beklenen şey değil: o senaryonun yanlış kilidi, kendi tanımında iddia edildiği
gibi "duran araç sınırı" **değil**. Ayrıca aramanın yan ürünü olarak Faz C'nin
**birincil karar dizisinin (117/23) 1 px'lik bir uçurumun kenarında** durduğu
ölçüldü.

## Tanım — eşik icat edilmedi

> Takipçi **KILITLI** diyor ama kutunun GT ile örtüşmesi **sıfır** olan kare =
> **yanlış kilit karesi (YK)**.

"Kilitliyim" iddiası ile "başka bir şeyi takip ediyorum" gerçeği arasındaki
çelişki doğrudan budur; yeni bir sabit gerektirmez. Takipçinin kendi
`yanlis_kilit` sayacı (`red`) **ayrı** raporlanır: o, savunmanın kaç kez
**ateşlediğidir**; YK ise savunmanın kaç kez **ateşlemediğidir**. İkisi farklı
şeyleri ölçer ve bu deneyde ayrıştıkları yer sonucun kendisidir.

## Kaos probu — 4I'ın Ö4'ünün yerine doğrudan ölçüm

4I bir dizinin kaotikliğini "IoU≈0 oranı" ile **vekilden** kestiriyordu.
Burada doğrudan ölçüldü: `main.kos`'un **zaten var olan** `hedef_secici`
kancasıyla ilk kilit kutusu ±1 px oynatılır (9 komşu: (0,0) ve 8 yön) ve aynı
dizi 9 kez koşulur. Takipçi bu müdahaleden habersizdir; hiçbir eşik
değişmez. ±1 px, gerçek kullanımda hedefi elle seçen bir operatörün gürültü
bandının altındadır — yani bu perturbasyon **meşru bir çalışma koşuludur**,
sentetik bir bozma değil.

# 1. Envanter (22 Gazebo senaryosu + 6 VisDrone track)

`gor` = kilit sonrası GT bulunan kare oranı. `red` = takipçinin kendi
`yanlis_kilit` sayacı.

| kaynak | kare | gor | KILITLI | **YK %** | epizot | en uzun | red | IoU |
|---|---|---|---|---|---|---|---|---|
| G0 … G7 (21 senaryo) | 300 | 0.98 | 294 | **0.0** | 0 | 0 | 0 | 0.618–0.912 |
| **G6_agresif_durakli** | 300 | 0.98 | 258 | **44.6** | 1 | 115 | 3 | 0.383 |
| G6_agresif_hedef | 300 | 0.98 | 286 | 0.0 | 0 | 0 | 1 | 0.662 |
| 117/23 | 349 | 0.98 | 343 | **0.0** | 0 | 0 | 0 | 0.701 |
| 137/12 | 233 | 0.95 | 209 | **0.5** | 1 | **1** | 1 | 0.548 |
| 182/127 | 363 | 0.92 | 103 | 61.2 | 1 | 63 | 2 | 0.088 |
| 268/31 | 978 | **0.26** | 179 | **100.0** | 1 | 179 | 8 | 0.000 |
| 305/5 | 184 | 0.77 | 117 | **9.4** | 1 | 11 | 0 | 0.502 |
| 339/49 | 275 | 0.97 | 198 | 59.1 | 1 | 117 | 4 | 0.064 |

Tek satırda özet: **22 Gazebo senaryosunun 21'inde yanlış kilit hiç yok**, ve
4I'ın "güvenilir" ilan ettiği iki gerçek dizinin biri (117/23) sıfır, diğeri
(137/12) tek kare veriyor. Yani yanlış kilit üzerinde çalışmak isteyen bir
deneyin **karar dizilerinde ölçecek hiçbir şeyi yoktu** — 4K'nın "kapı hiç
kapanmıyor" sonucu bunun aynı madalyonun öbür yüzüdür.

# 2. Kaos probu sonuçları (±1 px, 9 koşum)

| kaynak | YK % aralığı | YK aralık | **IoU aralığı** | IoU aralık |
|---|---|---|---|---|
| G0, G1_kritik, G1_yumusak, G2_agresif, G2_yumusak, G3_agresif, G3_kritik, G3_yumusak, G4_kritik, G5_agresif, G5_kritik, G6_agresif, G6_agresif_hedef, G6_yumusak, G7_agresif, G7_kritik, G7_yumusak (**17 senaryo**) | 0.0 | **0.000** | tek değer | **0.000** |
| G1_agresif | 0.0 | 0.000 | 0.889–0.897 | 0.008 |
| G5_yumusak | 0.0 | 0.000 | 0.886–0.900 | 0.015 |
| G4_yumusak | 0.0 | 0.000 | 0.870–0.891 | 0.021 |
| G4_agresif | 0.0 | 0.000 | 0.849–0.871 | 0.023 |
| **G6_agresif_durakli** | **44.6–44.6** | **0.000** | 0.383–0.384 | **0.001** |
| **117/23** | **0.0–8.0** | 0.080 | **0.111–0.701** | **0.590** |
| 137/12 | 0.5–0.5 | 0.000 | 0.548 (tek değer) | 0.000 |
| 305/5 | 9.4–9.4 | 0.000 | 0.502 (tek değer) | 0.000 |
| 182/127 | 61.2–61.5 | 0.003 | 0.063–0.088 | 0.024 |
| 339/49 | 59.1–61.8 | 0.027 | 0.063–0.078 | 0.015 |

# 3. Beklenmedik bulgu — 117/23 bir uçurumun 1 px yanında duruyor

Faz C'nin **birincil karar dizisi** 9 komşunun 8'inde 0.693–0.701 verir,
birinde (**−1, +1** px) **0.111**'e çöker. Bu tek koşumluk bir gürültü değil,
bir **havza sınırı** — yön taranınca kararlı bir bölge çıkıyor:

| ilk kutu ofseti | IoU | kilit | drift karesi |
|---|---|---|---|
| (0, 0) *taban* | **0.701** | %100 | yok |
| (−0.5, +0.5) | 0.694 | %100 | yok |
| (−1, +0.5) | **0.092** | %90.4 | **6** |
| (−1, +1) | **0.111** | %65.6 | **6** |
| (−1, +2) | 0.112 | %65.6 | **6** |
| (−2, +1) | 0.148 | %100 | **6** |
| (−2, +2) | 0.161 | %100 | **6** |

Sınır 0.5 px ile 1 px arasında; ötesinde davranış **tutarlı** (hepsi 6. karede
drift). Yani sonuç deterministik ve tekrarlanabilir ama **dayanıklı değil**:
117/23 üzerinde ölçülen her şey **tek bir havzanın** özelliğidir.

Bunun doğrudan sonucu: 117/23'te ölçülen küçük IoU farkları (Faz C'de
0.002'lik farkla deney geri alınmıştı — bkz. `DENEY_03_SONUC.md`) sistemin
kalitesinden çok başlangıç koşulunun hangi havzada olduğuna duyarlı bir
büyüklüğün üstünde okunuyor. **Bu bir geri alma çağrısı değildir** — o
kararlar sabit bir başlangıçla verildi ve kendi içinde tutarlıdır — ama
bundan sonraki her 117/23 karşılaştırmasının yanına **kaç px'lik komşulukta
geçerli olduğu** yazılmalıdır.

Karşılaştırma için: **Gazebo tarafı bu hastalığa yakalanmıyor.** 22 senaryonun
**17'si ±1 px altında bit düzeyinde aynı**; kıpırdayan beşinin en kötüsü
0.023 (G4_agresif) oynuyor.

# 4. `G6_agresif_durakli`: iddia edilen sınır değil

Senaryo `gazebo/senaryolar.py:399`'da şu gerekçeyle ayrı tutulmuştu:

> *"takipçinin duran-araç sınırının Gazebo'da da tekrarlanabildiğini gösterir"*

Ölçüm bunu **desteklemiyor**. Yanlış kilit epizodu: **kare 151–293**, 115 YK
karesi (aralık 143 kare; arada KILITLI olmayan kareler var).

**a) Araç epizot başladığında durmuş değil.** Epizottan önceki 11 karede hedef
hızı: 6.39 → 6.14 → 5.89 → 5.63 → 5.37 → 5.11 → 4.86 → 4.62 → 4.35 → 4.10 →
**3.84 m/s**. Yavaşlıyor ama 3.84 m/s'de. Araç ancak 17 kare sonra (kare 168:
0.53 m/s, kare 172: 0.01 m/s) gerçekten duruyor.

**b) Aynı dizide daha önceki duruş SORUNSUZ geçildi.** Hedef ilk kez kare
46'da 0.5 m/s'nin altına iniyor ve orada 21 kare kalıyor. O aralıkta IoU:

```
kare 46..66:  0.80 0.83 0.84 0.87 0.95 0.91 0.87 0.84 0.87 0.85
              0.82 0.80 0.86 0.85 0.84 0.82 0.86 0.84 0.82 0.81 0.84
```

Kusursuz takip. Yani aynı uyaran (duran araç) bir kez sunuldu ve **geçildi**;
ikincisinde kopuş duruştan **önce** başladı.

**c) Kopuş kademeli bir kayma, ani bir yanlış kilit değil.**

```
kare  145   146   147      148      149   150   151
IoU  0.45  0.42  0.39     0.25     0.09  0.03  0.00
     KIL   KIL   SUPHELI  SUPHELI  KIL   KIL   KIL
```

**d) Kutu 115 YK karesinin 115'inde de ZEMIN üzerinde** — çeldirici aracın
üzerinde değil (ölçüt `gazebo/tani.py:290` ile birebir aynı: en çok örtüşen
araç, IoU > 0.2; hiçbiri değilse "zemin"). Yani bu bir kimlik karışması (ID
switch) değil, zemine kayma.

**e) Zemin savunması çalışmıyor değil — yanlış cevap veriyor.** Epizodun
%95'inde `_hareketli = True`, yani "zemine çakılma" testi kutunun **zeminden
bağımsız hareket ettiğini** söylüyor. PSR medyanı **78.2** — DCF son derece
emin. Benzerlik medyanı 1.00 (sıfırlama değeri; kimlik testi
`not _hareketli_guclu` koşulu yüzünden neredeyse hiç çalışmıyor — 4K'nın
bulduğu yapısal durum). Savunma epizot içinde yine de **3 kez** ateşliyor
(`red+3`) ama her seferinde arama tekrar zemine kilitleniyor.

Özet: kamera 32 m/s çapraz giderken hedef yavaşlarken kutu kayıyor, ve
kaydığı yerde ego telafisinden **artakalan** hareket, zemin testine "bu cisim
hareketli" dedirtecek kadar büyük kalıyor. Bu, belgelenmiş "duran araç yanlış
kilit sanılır" sınırının **tersi** bir hata: orada doğru takip yanlış sanılıyor,
burada yanlış kilit doğru sanılıyor.

# 5. Karar verilebilirlik hükmü

Bir kaynağın yanlış-kilit deneyine **karar dayanağı** olabilmesi için:

| # | ölçüt | gerekçe |
|---|---|---|
| K1 | GT görünürlüğü ≥ 0.70 | GT yoksa ölçüm yok (4I Ö2) |
| K2 | 0 < YK oranı < 1 | 0 ise düzeltilecek şey yok, 1 ise doygun |
| K3 | ±1 px altında YK aralığı ≪ beklenen etki | kaotikse ölçüm karar veremez |
| K4 | ±1 px altında IoU aralığı küçük | yan metrik de okunabilmeli |

| kaynak | K1 | K2 | K3 | K4 | **hüküm** |
|---|---|---|---|---|---|
| G0–G7 (21 senaryo) | ✓ | **✗** (YK = 0) | ✓ | ✓ | ölçecek şey yok |
| **G6_agresif_durakli** | ✓ 0.98 | ✓ 0.446 | ✓ **0.000** | ✓ 0.001 | **KARAR VERILEBILIR** |
| 117/23 | ✓ 0.98 | **✗** (YK = 0) | ✗ 0.080 | **✗ 0.590** | ölçecek şey yok + uçurum |
| 137/12 | ✓ 0.95 | **✗** (1 kare) | ✓ | ✓ | çözünürlük yok |
| **305/5** | ✓ 0.77 | ✓ 0.094 | ✓ **0.000** | ✓ 0.000 | **DESTEKLEYICI** |
| 182/127 | ✓ 0.92 | ~ 0.612 | ✓ 0.003 | ✓ 0.024 | doygun (103/363 KILITLI) |
| 268/31 | **✗ 0.26** | **✗** (1.000) | — *(prob atlandı)* | — | kullanılamaz |
| 339/49 | ✓ 0.97 | ~ 0.591 | ✓ 0.027 | ✓ 0.015 | doygun |

> **Birincil: `G6_agresif_durakli`. Destekleyici: `305/5`.**
> 182/127 ve 339/49 "çökmedi mi" kontrolü olarak okunur — YK oranları
> ±1 px altında şaşırtıcı biçimde **kararlı** (0.3 ve 2.7 puan), ama %60
> civarında doygun oldukları için bir iyileştirmeyi ancak çok büyükse
> gösterirler.

Bir sürpriz: 4I'ın IoU üzerinden "kaotik" ilan ettiği diziler **YK metriği
bakımından kaotik değil**. Kaos IoU'ya özgü; YK ikili ve epizodik olduğu için
±1 px'ten etkilenmiyor. Yani 4I'ın hükmü IoU için doğru, yanlış kilit için
fazla katıydı.

# 6. 4K'nın açık sorusu — artık yanıtlanabilir mi?

4K, öğrenme kapısının **bias** düzeltmesi mi **yanlış kilit dayanıklılığı**
düzeltmesi mi olduğunu ölçemiyordu, çünkü kapının ateşlediği dizilerin hepsi
karar dışıydı. Şimdi:

* `G6_agresif_durakli` karar verilebilir bir yanlış-kilit kaynağıdır **ve**
  4K'da kapının ateşlediği dizilerden biriydi (öğrenme karelerinin %7.4'ünde
  kapandı) — ama orada metrikleri **hiç kıpırdatmamıştı** (IoU 0.3831 →
  0.3831, merkez 61.53 → 61.53).
* Yani 4K'nın müdahalesi, **karar verilebilir tek kaynakta bit düzeyinde
  etkisizdir**. 4K'nın "belki bir yanlış kilit düzeltmesidir" hipotezi
  böylece **karar verilebilir veride desteklenmiyor**.

Bu, 4K'nın bıraktığı soruyu kapatır: hipotez artık ölçülemez değil,
**ölçüldü ve geçmedi**.

# 7. Bu tur ne yapıldı, ne yapılmadı

* Yapıldı: 28 kaynakta yanlış-kilit envanteri (28 koşum), 27 kaynakta ±1 px
  kaos probu (216 ek koşum; 268/31 görünürlük 0.26 ile atlandı), 117/23'ün
  uçurumunda 5 ek yön taraması, 5 kaynakta epizot anatomisi.
* Yapılmadı: **hiçbir optimizasyon, hiçbir eşik değişikliği, `takip/`'te tek
  satır değişiklik.**

# 8. Sonraki tek aday

`G6_agresif_durakli`'nin kopuşu **kare 145–151** arasında, hedef 6.6 → 3.8 m/s
yavaşlarken ve kamera 32 m/s çaprazken oluyor; kopuş anında iki kare
**SUPHELI**. Aynı dizinin ilk duruşu (kare 46–66) sorunsuz geçildiğine göre
ayırt edici değişken duruş değil, **duruş + çapraz kamera birleşimi**.

> **Sonraki tek aday — yine takipçi değişikliği değil.**
> Kare 140–155 penceresinde ego kestirimini, DCF tepesini ve KF artığını kare
> kare çıkar; `G6_agresif` (aynı kamera, duraklama YOK, YK %0) ile **aynı
> pencerede** karşılaştır. İki senaryo yalnızca hedef hız profilinde farklı
> olduğu için bu, kopuşun **tek değişkenli** bir teşhisidir — Faz C'de ilk kez
> böyle bir kontrol çifti mevcut.

**Bu bir öneridir, uygulanmadı.**
