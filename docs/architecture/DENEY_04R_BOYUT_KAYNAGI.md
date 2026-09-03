# Deney 4R — `boyut` hatasını üreten aşama hangisi?

**Salt okunur. `takip/` altında hiçbir dosya değiştirilmedi**, hiçbir parametre /
eşik / lr / Kalman / DCF / şablon değişmedi, optimizasyon yapılmadı,
commit/push yok. Araç: `gazebo/tani_4r_boyut.py`. Veri: `cikti/boyut_4r.json`.

## 1. md5 sonucu

Deney **öncesi** ve **sonrası** alınan md5'ler birebir aynı; Deney 2 baseline'ı
ile **6/6**:

```
d41d8cd98f00b204e9800998ecf8427e  takip/__init__.py
c0fd7989d4e81219cd99447a12f8d78b  takip/cekirdekler.py
959da09ab43501a983629368a8f699b1  takip/egomotion.py
4257b94ce7f4978e172b8bb7c89816c1  takip/izleyici.py
874b3ccd540c8a6c783320c619a78f41  takip/mosse.py
3ff48dd869374d36937c18b640f2b21b  takip/tespit.py
```

## 2. Baseline sonucu

| kaynak | IoU | kilit | merkez | drift | önceki turlarla |
|---|---|---|---|---|---|
| 182/127 | 0.087714 | %30.75 | 265.66 | 39 | 4I / 4L ile aynı |
| 305/5 | 0.501698 | %82.98 | 9.12 | 110 | 4I / 4L ile aynı |
| G6_agresif | 0.618242 | %100.00 | 8.40 | 294 | 4M / 4O / 4P ile aynı |
| G6_agresif_durakli | 0.383141 | %87.76 | 61.53 | 148 | 4L…4Q ile aynı |

## 3. Yakalama noktaları

`self.boyut`u yazan **tüm** noktalar (grep ile doğrulandı):

| satır | yer | işlem |
|---|---|---|
| 198 | `kilitle()` | ilk kutu |
| **264** | `guncelle()` | `boyut = max(boyut · olc, min_kenar)`, `olc = clip(ego.olcek_katsayisi, 0.90, 1.10)` |
| **563** | `_boyut_tazele()` | `boyut = max(0.75·boyut + 0.25·rafine, min_kenar)` |
| **549** | `_boyut_sinirla()` | `boyut = clip(boyut, 0.60·b, 1.70·b)`, `b = max(boyut_olculen, min_kenar)` |
| 522 | `_arama_adimi()` | `boyut = max(0.5·boyut + 0.5·rafine, min_kenar)` (yalnızca ARAMA/KAYIP) |
| 564 | `_boyut_tazele()` | `boyut_olculen = 0.85·boyut_olculen + 0.15·rafine` |

Kaydedilen aşamalar: **A0** kare girişi · **A1** ego ölçeği sonrası ·
**A2/A3** `_boyut_tazele` öncesi/sonrası · **A4/A5** `_boyut_sinirla`
öncesi/sonrası. Her aşamada `w`, `h`, `w/GT_w`, `h/GT_h`, IoU, tavan IoU,
merkez hatası, `rafine_kutu` çıktısı, kırpma miktarı ve sınır bandı yazıldı.

## 4. Aşama ayrıştırması — log toplamı (kilit → drift)

`log(boyut_son / boyut_ilk)` üç aşamanın katkısına ayrıldı. **Artık her
kaynakta 0.000** — yani üç aşama toplam değişimin **%100'ünü** açıklıyor.

| kaynak | eksen | toplam | ego (264) | **tazeleme (563)** | sınırlama (549) | arama (522) | artık |
|---|---|---:|---:|---:|---:|---:|---:|
| 182/127 | w | −0.095 | +0.021 | **−0.116** | **0.000** | 0.000 | −0.000 |
| 182/127 | h | −0.225 | +0.021 | **−0.246** | **0.000** | 0.000 | 0.000 |
| 305/5 | w | +0.452 | +0.162 | **+0.289** | **0.000** | 0.000 | 0.000 |
| 305/5 | h | +0.048 | +0.162 | −0.114 | **0.000** | 0.000 | −0.000 |
| G6_agresif | w | +0.606 | +0.014 | **+0.592** | **0.000** | 0.000 | 0.000 |
| G6_agresif | h | +0.255 | +0.014 | **+0.241** | **0.000** | 0.000 | −0.000 |
| G6_agresif_durakli | w | +0.037 | −0.019 | +0.056 | **0.000** | 0.000 | 0.000 |
| G6_agresif_durakli | h | +0.128 | −0.019 | +0.146 | **0.000** | 0.000 | 0.000 |

Çarpan biçiminde (1.000 = etkisiz), genişlik ekseni:

| kaynak | ilk kutu/GT | drift kutu/GT | ego | **tazeleme** | sınırlama |
|---|---:|---:|---:|---:|---:|
| 182/127 | **0.62** | 0.53 | ×1.021 | **×0.890** | ×1.000 |
| 305/5 | 0.95 | 1.46 | ×1.176 | **×1.336** | ×1.000 |
| G6_agresif | 0.97 | **1.88** | ×1.014 | **×1.807** | ×1.000 |
| G6_agresif_durakli | 0.97 | 1.06 | ×0.981 | ×1.057 | ×1.000 |

## 5. `_boyut_tazele`'nin girdisi: `rafine_kutu` gerçekten ne döndürüyor?

Boyutu 3 px'ten fazla oynatan **her** tazeleme çağrısı:

**G6_agresif** (GT ≈ 57×30 px):

| kare | boyut önce → sonra | rafine w/h |
|---:|---|---|
| 246 | 60.8/34.6 → **72.1/41.9** | **106**/64 |
| 250 | 72.2/42.0 → **85.7/50.8** | **126**/77 |
| 254 | 85.8/50.8 → **101.4/61.4** | **148**/93 |
| 258 | 101.6/61.5 → **119.7/55.1** | **174**/36 |
| 262 | 119.9/55.2 → 104.2/50.2 | 57/35 |

Dört ardışık çağrıda `rafine_kutu` 106 → 174 px genişlik döndürüyor (GT 57);
her çağrı bunun %25'ini karıştırıyor ve kutu 1.85×'e yerleşiyor. Sonra
(4N: R6 renk kapısı) rafine ölüyor ve kutu **104.5/50.3'te donuyor** — 264–299
arasında A0 = A1 = A3 = A5, hiçbir aşama kıpırdamıyor.

**305/5** (GT ≈ 26×32–57 px):

| kare | boyut önce → sonra | rafine w/h |
|---:|---|---|
| 86 | 28.1/53.2 → **35.1**/52.9 | **56**/52 |
| 90 | 35.1/53.0 → **42.9**/53.3 | **66**/54 |
| 94 | 42.9/53.4 → **51.9**/53.5 | **79**/54 |
| 106 | 42.7/55.3 → 39.3/**68.2** | 29/**107** |
| 110 | 39.5/68.6 → 36.1/**85.0** | 26/**134** |

**182/127** (GT ≈ 21×21 px) — ters yönde:

| kare | boyut önce → sonra | rafine w/h |
|---:|---|---|
| 22–42 | 12.0/11.0 → **9.0/7.9** (adım adım) | 11/11, 11/7, 10/7, **3/5** |
| 202–210 | 21.4/18.3 → **47.6/24.2** | 54/16, 61/19, **75/41** |
| 246–250 | 70.2/45.8 → **75.7/81.4** | 96/**125**, 72/**128** |

Yani `rafine_kutu` **çalıştığında da** hedefin 3–6 katı ya da yarısı kadar
kutular döndürüyor; `_boyut_tazele` bunları koşulsuz %25 ağırlıkla karıştırıyor.

## 6. `_boyut_sinirla` neden hiç devreye girmiyor?

Kırpma sayacı: **0/293** (G6_agresif), **0/140** (305/5), **0/293**
(G6_agresif_durakli), **4/334** (182/127 — yalnızca yükseklikte −1.0…−1.8 px).

Yapısal nedeni ölçüldü: bandın çapası `boyut_olculen`, `_boyut_tazele`'nin
**aynı satırında** (564) yine `rafine_kutu` ile güncelleniyor
(`0.85·olculen + 0.15·rafine`). Yani koruma, koruduğu değeri bozan kaynağın
kendisine bağlı: `boyut` bozulurken `boyut_olculen` de onunla birlikte
bozuluyor ve `[0.60, 1.70]` bandı **bozulmayı takip ediyor**. Çevrim kapalı.

> Bu, Faz C'nin üç kez tekrarlanan dersinin dördüncü örneğidir: *türetilmiş bir
> büyüklük bağımsız bir ölçümün yerine geçince çevrim kapanıyor.*

## 7. Boyut hatası ile merkez hatasının kesin ayrımı (4Q yeniden üretildi)

`tavan IoU` = takipçinin **kendi boyutu**, GT merkezine tam oturtulduğunda.
`boyut katkısı = 1 − tavan`; `merkez katkısı = tavan − gerçek IoU`.

Drift penceresi ortalaması (drift−30 … drift):

| kaynak | IoU | tavan | **boyut katkısı** | **merkez katkısı** |
|---|---:|---:|---:|---:|
| 182/127 | 0.414 | 0.416 | **0.584** | 0.002 |
| 305/5 | 0.570 | 0.611 | **0.389** | 0.041 |
| G6_agresif | 0.397 | 0.397 | **0.603** | 0.000 |
| G6_agresif_durakli | 0.681 | 0.819 | 0.181 | **0.138** |

Drift karesinde:

| kaynak | kare | IoU | tavan | boyut kat. | merkez kat. | merkez hata | kutu/GT (w, h) |
|---|---:|---:|---:|---:|---:|---:|---|
| 182/127 | 39 | 0.295 | 0.295 | **0.705** | 0.000 | **2.52** | 0.53, 0.56 |
| 305/5 | 110 | 0.229 | 0.256 | **0.744** | 0.027 | 29.34 | 1.46, **2.68** |
| G6_agresif | 294 | 0.288 | 0.288 | **0.712** | −0.000 | 11.20 | **1.88**, 1.84 |
| G6_agresif_durakli | 148 | 0.251 | **0.687** | 0.313 | **0.436** | **30.05** | 1.06, 1.37 |

4Q'nun sonucu birebir doğrulandı: üç kaynakta `tavan = IoU` (kayıp tamamen
boyuttan, merkez hatası 182/127'de yalnızca **2.5 px**), yalnızca
`G6_agresif_durakli`'de merkez baskın.

## 8. Kaynak kaynak hüküm

| kaynak | A) ham kutu (ego) | B) tazeleme | C) sınırlama | D) taşıma | **HÜKÜM** |
|---|---|---|---|---|---|
| **182/127** | ×1.021 (ihmal) | **×0.890 — üretici** | ×1.000 (4 karede −1.8 px) | — | **TAZELEME_KAYNAK** |
| **305/5** | ×1.176 (ikincil) | **×1.336 — üretici** | ×1.000 | — | **TAZELEME_KAYNAK** |
| **G6_agresif** | ×1.014 (ihmal) | **×1.807 — üretici** | ×1.000 | — | **TAZELEME_KAYNAK** |
| **G6_agresif_durakli** | ×0.981 | ×1.057 | ×1.000 | kutu/GT 1.06 — boyut sorun değil, arıza **merkezde** | **UPSTREAM_TASIMA** |

**İki bağımsız GERÇEK dizide aynı mekanizma:** 182/127 ve 305/5 — ikisi de
gerçek VisDrone dizisi, ikisinde de üretici `_boyut_tazele`, ikisinde de
`_boyut_sinirla` katkısı tam olarak 0.000. Gazebo tarafından G6_agresif üçüncü
bağımsız örnek. **İşaret farklı** (182/127 küçültüyor, 305/5 ve G6_agresif
büyütüyor) ama **aşama aynı** — 4N'in bulduğu iki üst akış arızasıyla
(parçalanma / birleşme) tutarlı.

Ek not: 182/127'de hata tazelemeden **önce de** var — ilk kilit kutusu zaten
GT'nin **0.62**'si (`kilitle`, satır 198; tespit adayından geliyor). Tazeleme
bunu 0.53'e derinleştiriyor. Bu, dört kategoriye girmeyen beşinci bir katkıdır
ve ayrıca kaydedilmiştir.

---

# SONUÇ

**1. md5:** deney öncesi = deney sonrası, Deney 2 baseline'ı ile **6/6 aynı**.

**2. Baseline:** dört kaynağın IoU / kilit / merkez / drift değerleri önceki
turlarla **birebir** üretildi.

**3. Hatayı üreten aşama: `_boyut_tazele` (izleyici.py:563).**
Log ayrıştırması artıksızdır (0.000): ölçülen dört kaynağın **üçünde**
`_boyut_tazele` toplam boyut değişiminin tamamını ya da fazlasını üretiyor
(×0.890 / ×1.336 / ×1.807), ego ölçeği ikincil (×1.014–×1.176) ve
`_boyut_sinirla` **tam olarak etkisiz** (×1.000, 0–4 kare kırpma).
Dördüncü kaynak (`G6_agresif_durakli`) bir boyut vakası değil; orada boyut
1.06× ile doğru, arıza merkezdedir (4Q/4P ile tutarlı) → UPSTREAM_TASIMA.
Üreticinin girdisi bozuk: `rafine_kutu`, GT 57 px iken 106–174 px, GT 21 px
iken 3–5 px kutular döndürüyor ve `_boyut_tazele` bunları **koşulsuz** %25
ağırlıkla karıştırıyor.

**4. Bundan sonra test edilmesi gereken TEK aday** (yine salt okunur, yeni
eşik yok):

> **`_boyut_sinirla`'nın çapası `boyut_olculen` yerine KİLİT ANINDAKİ boyut
> olsaydı, mevcut `[0.60, 1.70]` bandı bu üç kaçışı yakalar mıydı?**
> Tamamen `cikti/boyut_4r.json`'daki kayıtlı seriden hesaplanır — takipçi
> koşturulmaz, hiçbir sabit değişmez, mevcut band aynen kullanılır.
> * Yakalıyorsa: arıza `_boyut_tazele`'nin kendisi değil, **korumanın
>   çapasının bozuk ölçüme bağlı olması**dır ve müdahale tek satırlıktır.
> * Yakalamıyorsa: koruma yapısal olarak yetersizdir ve sorun doğrudan
>   `rafine_kutu`'nun çıktı kalitesindedir.
>
> Bu iki şıkkı ayırmadan hiçbir düzeltme doğru yere uygulanamaz.

**Bu turda hiçbir optimizasyon uygulanmadı; `takip/` md5 6/6 aynı.**
