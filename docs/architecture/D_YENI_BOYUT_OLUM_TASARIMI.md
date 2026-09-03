# D — Yeni boyut ölçümü: tasarım analizi

**Bu bir tasarım belgesidir. Kod değiştirilmedi, takipçi koşturulmadı, deney
yapılmadı, yeni eşik önerilmedi.** Mevcut `[0.60, 1.70]` / `[0.35, 2.6]`
bandlarına, `_boyut_tazele` ağırlığına, `rafine_kutu`'ya ve DCF yamasına
dokunulması **önerilmiyor**. `takip/` md5'leri Deney 2 baseline'ı ile 6/6 aynı.

## 0. Tasarımın dayandığı ölçülmüş kısıtlar

| kanıt | kısıt |
|---|---|
| 4R: boyut hatasını `_boyut_tazele` üretiyor (×0.890/×1.336/×1.807, artık 0.000) | Düzeltme, karıştırmanın **girdisinde** olmalı |
| 4S: `_boyut_sinirla`'nın çapası (`boyut_olculen`) aynı `rafine` ile besleniyor → ×1.000 | **Çapa bağımsız bir kaynaktan gelmeli** |
| 4T/4U: `bileşen/boyut` oranına bakan kapı kapalı çevrimde 137/12'yi yıktı (0.548→0.190) | **Z1/Z7**: karar, kararın etkilediği büyüklüğe bakamaz |
| D1: `adaylar()` bağımsız + mutlak ama h/GT 0.30, kullanılabilirlik %7 | Bağımsızlık yetmez; **doğruluk ve kullanılabilirlik** de ölçülmeli |
| D2: `p82` ve `μ+4σ` — ikisi de **sabit oranlı kontrast eşiği** → nesnenin parçası | Yeni ölçüm **kontrast eşiğine dayanmamalı** ya da eşiği veriden türetmeli |
| D2: depoda kontur/kenar/min-alan/yoğun akış/anahtar-nokta yolu yok; **hiçbir çekirdekte ölçek araması yok** | Yeni yol gerçekten yeni |
| Proje kısıtı (hafıza): Pi Zero hedefi → **derin öğrenme yok** | G ailesi kapsam dışı |

---

## 1. Aday ailelerinin değerlendirmesi

### A) Segmentasyon + morfolojik/geometrik ölçüm

| | |
|---|---|
| **prensip** | Yerel pencerede ikili maske → bağlantılı bileşen → sınırlayıcı kutu. Mevcut ikisinden farkı: eşiğin **sabit oranlı olmaması** (ör. iki-modlu histogram ayrımı gibi veriden türeyen bir kural) |
| doğrudan hedef mi | evet |
| takip kutusundan bağımsız mı | **HAYIR** — pencere bugün `boyut`tan geliyor; bağımsız bir pencere kaynağı tanımlanmadan olmaz |
| `rafine_kutu`'dan bağımsız mı | evet |
| mutlak w/h | evet |
| Gazebo + VisDrone | evet |
| yeni model / yeni etiket | hayır / hayır |
| maliyet | düşük (mevcut `rafine_kutu` mertebesinde) |
| **başarısızlık modu** | **Ölçülmüş**: düşük kontrastta parçalanma (117/23, kontrast 5.2), yüksek kontrastta çeldiriciyle birleşme (4N) |
| Z1–Z7 | Z1/Z7 **ancak pencere bağımsız kaynaktan gelirse**; Z2 ✓, Z3 ✓, Z4/Z5 ✓, Z6 eşik veriden türerse ✓ |
| entegrasyon | `boyut_olculen` çapası |
| **elenmeli mi** | Elenmemeli ama **birinci sıra değil**: aynı ailenin iki üyesi (4N, D1) zaten ölçülüp düştü; farkı yalnızca eşiğin türetilme biçimi |

### B) Edge / contour tabanlı araç silüeti

| | |
|---|---|
| **prensip** | Kenar operatörü → kontur → sınırlayıcı geometri |
| doğrudan hedef mi | evet |
| bağımsızlık | pencere sorunu A ile aynı |
| mutlak w/h | evet |
| **başarısızlık modu** | Kenar yoğunluğu kontrastla doğru orantılı; 117/23'te kontrast **5.2** (4I) — A'nın parçalanma kipinin **daha keskin** hali. Ayrıca gölge kenarları araç kenarından ayırt edilemez |
| yeni model/etiket | hayır / hayır |
| maliyet | düşük–orta |
| Z uyumu | A ile aynı, doğruluk riski **daha yüksek** |
| **elenmeli mi** | **ELENMELİ.** A'nın tüm zayıflıklarını taşıyor, hiçbir yeni bilgi kaynağı getirmiyor; depoda kenar altyapısı da yok |

### C) Çoklu ölçekli template / object extent (ölçek-uzayı araması)

| | |
|---|---|
| **prensip** | Yamayı `boyut`×{s₋, 1, s₊} ile kesip yanıt/PSR karşılaştırarak ölçek seçmek |
| doğrudan hedef mi | evet |
| takip kutusundan bağımsız mı | **HAYIR — arama aralığı mevcut `boyut` etrafında tanımlı** |
| mutlak w/h | hayır — **mevcut boyuta göreli** |
| **Z1/Z7** | **İHLAL.** Kararın girdisi kendi önceki kararıdır |
| **Deney 2 ile farkı (kritik)** | Deney 2'nin açı araması kabul edildi çünkü açı **sınırlı bir manifoldda** yaşar, adaylar **mutlak bir ızgaraya** (`aci_adim`) oturtulur ve referans her karede ego'dan yeniden türetilir. Ölçek ise **çarpımsal ve sınırsızdır**: her kare bir öncekinin katı olur → rastgele yürüyüş. 4R'de ölçülen ×1.807 tam olarak bu kipin sonucudur |
| maliyet | orta (kare başına 3× DCF) |
| **elenmeli mi** | **ELENMELİ.** Z1 ve Z7'yi tanım gereği ihlal ediyor; 4U'nun düşürdüğü kipin aynısı |

### D) Optical-flow hareket bölgesi + geometrik extent

| | |
|---|---|
| **prensip** | Ego `M` ile telafi edilmiş **akış artığı** alanı; artığı arka planınkinden ayrışan bölgenin uzamı |
| doğrudan hedef mi | evet — hareket eden cismi ölçer |
| takip kutusundan bağımsız mı | **EVET** — ayrım ölçütü akış artığıdır, kutu değil |
| `rafine_kutu`'dan bağımsız mı | evet |
| mutlak w/h | evet |
| Gazebo + VisDrone | evet (ego `M` ikisinde de %100 güvenle mevcut — D2 envanteri) |
| yeni model / etiket | hayır / hayır |
| maliyet | **yüksek** — yoğun akış depoda yok; pencereye sınırlanırsa pencere sorunu geri gelir |
| **başarısızlık modu** | Hedef durunca artık kaybolur (**belgelenmiş** duran-araç sınırı, 4P kare 174–186); kamera dönerken artık gürültüsü büyür |
| Z uyumu | Z1 ✓ Z2 ✓ Z3 ✓ Z4/Z5 ✓ Z6 (eşik arka planın **kendi** artık dağılımından türetilirse) ✓ Z7 ✓ |
| entegrasyon | `boyut_olculen` çapası |
| **elenmeli mi** | Elenmemeli — ama maliyeti ve duran-hedef kipi nedeniyle **ikinci sıra** |

### E) Keypoint / feature cluster + robust bounding geometry

| | |
|---|---|
| **prensip** | Kare genelinde köşe noktaları izlenir; ego `M` ile **uyuşmayan** noktalar (RANSAC'ın kendi outlier kümesi) bağımsız hareket eden cisme aittir. Takip merkezine en yakın outlier kümesinin **dayanıklı uzamı** (yüzdelik yayılımı) w/h verir |
| doğrudan hedef mi | evet |
| takip kutusundan bağımsız mı | **EVET** — kutu hiçbir yerde kullanılmaz; takip **merkezi** yalnızca *hangi küme* sorusunda (ilişkilendirme), ölçekte değil. D1'de S1/S2 aynı gerekçeyle K1'i geçmişti |
| `rafine_kutu`'dan bağımsız mı | evet |
| mutlak w/h | evet (piksel) |
| Gazebo + VisDrone | evet — `goodFeaturesToTrack` + çift yönlü LK + `estimateAffinePartial2D` **zaten her karede koşuyor** (`egomotion.py:34-115`), iki dizide de güven %100 |
| yeni model / etiket | **hayır / hayır** |
| maliyet | **düşük–orta**: LK boru hattı zaten var; eklenen şey maskesiz ikinci bir nokta kümesi ve outlier kümeleme |
| **başarısızlık modu** | (i) dokusuz/küçük hedefte köşe bulunamaz — deponun kendi notu: *"10×5 px hedefte köşe bulamaz → orada çöker"* (`cekirdekler.py:281-283`); (ii) hedef durunca ego ile uyuşur ve outlier olmaktan çıkar (duran-araç sınırı); (iii) yalnızca **dokulu kısımlar** noktalanır → uzam eksik ölçülebilir (D1'in parçalanma riskiyle **aynı sınıf**, ama farklı kestirimci) |
| Z uyumu | **Z1 ✓ Z2 ✓ Z3 ✓ Z4 ✓ Z5 ✓ Z6 ✓ (ayrım ölçütü RANSAC'ın zaten verdiği inlier/outlier kararı — yeni sabit yok) Z7 ✓** |
| entegrasyon | `boyut_olculen` çapası |
| **elenmeli mi** | **Hayır — birinci sıra** |

### F) Kamera geometrisi / monoküler ölçek

| | |
|---|---|
| **prensip** | `izdusur()` tersine: irtifa + iç parametreler + aracın 3B boyutu → piksel w/h |
| bağımsızlık | evet |
| mutlak w/h | evet |
| **engel** | Gerçek videoda **kamera pozu yok, iç parametreler yok, aracın 3B boyutu yok**. İrtifayı ego ölçeğinden biriktirmek yasak (kodun kendi notu: 300 karede 3× şişme). Nominal araç boyu varsaymak bir **ölçüm değil, önsel**dir ve Z6'yı ihlal eder |
| **elenmeli mi** | **ELENMELİ** — Z4/Z5 sağlanamaz (yalnızca Gazebo'da mümkün) |

### G) Detector tabanlı bağımsız bbox

| | |
|---|---|
| **prensip** | Bağımsız bir araç dedektörünün kutusu |
| bağımsızlık / mutlaklık | evet / evet — **kavramsal olarak ideal** |
| **engel** | Proje kısıtı: hedef donanım Pi Zero, **derin öğrenme yok**; ayrıca soru açıkça "yeni model eğitmeden" diyor. Hazır model kullanmak da aynı kısıtı ihlal eder |
| **elenmeli mi** | **ELENMELİ (kapsam dışı)** — ama *referans üst sınır* olarak kaydedilmeli: doğruluk tavanının ne olduğunu bilmek ileride yararlı |

### H) Hibrit ölçüm

| | |
|---|---|
| **prensip** | E varken E, yoksa D/A'ya düşmek |
| **engel** | Düşme kuralı **yeni bir karardır** ve 4T/4U tam olarak "karar kuralı" katmanında yıkıldı. Bileşenlerin tek tek doğruluğu bilinmeden birleştirme, hatanın hangi bileşenden geldiğini ölçülemez kılar |
| **elenmeli mi** | **Şimdilik ELENMELİ** — ancak bileşenler ayrı ayrı doğrulandıktan **sonra** gündeme gelebilir |

---

## 2. "Yeni model eğitmeden, mevcut görüntü ve etiketlerle en düşük riskli yöntem hangisi?"

**E — ego RANSAC outlier kümesinin dayanıklı uzamı.** Gerekçe, risk kalemleri
tek tek:

| risk kalemi | E'nin durumu |
|---|---|
| yeni model / yeni etiket | **yok** |
| yeni kütüphane / yeni algoritma sınıfı | **yok** — `goodFeaturesToTrack` + LK + RANSAC zaten her karede koşuyor |
| yeni eşik | **yok** — ayrım, RANSAC'ın zaten verdiği inlier/outlier kararı |
| pencere/ölçek bağımlılığı | **yok** — kare geneli çalışır, kutu kullanılmaz |
| iki gerçek dizide erişilebilirlik | ego güveni **%100 / %100** (D2 envanteri) |
| doğrulanabilirlik | **D1 protokolüyle birebir aynı**: gözlemci olarak koş, GT ile karşılaştır, hiçbir şey besleme |
| başarısızlık modunun bilinirliği | **belgeli** (dokusuz hedef, duran hedef) — sürpriz değil, ölçülebilir |

Karşılaştırma: D yeni bir yoğun-akış hattı gerektirir (maliyet + Pi Zero
riski); A/B eşik tabanlı segmentasyon ailesinde kalır ve o ailenin iki üyesi
zaten ölçülüp düşmüştür; C Z1'i tanım gereği ihlal eder; F gerçek veride
imkânsız; G proje kısıtı dışı.

---

## 3. Kalan üç aday — tasarım

### ADAY 1 (önerilen) — E: ego-outlier kümesinin dayanıklı uzamı

| | |
|---|---|
| **1. girdiler** | (a) gri kare (mevcut, 0.5× küçültülmüş kopya zaten var); (b) `EgoMotion`'ın **zaten hesapladığı** nokta çiftleri (`a`, `b`) ve RANSAC inlier maskesi; (c) yalnızca **ilişkilendirme** için `kf.konum`. **`boyut`, `boyut_olculen`, `rafine` HİÇ okunmaz.** |
| **2. çıktı formatı** | `(w_px, h_px, n_nokta, guven)` — mutlak piksel; nokta sayısı ve dağılım kalitesi **ölçümle birlikte** raporlanır ki tüketici tarafta "yok" ile "belirsiz" ayrılabilsin |
| **3. bağlanacağı nokta** | **`boyut_olculen`** (`izleyici.py:564`) — yani `_boyut_sinirla`'nın **çapası**. `boyut`a doğrudan yazılmaz. Gerekçe: 4S bandın işlemediğini, 4R ise çapanın bozuk kaynakla beslendiğini ölçtü; bağımsız çapa tam olarak eksik olan parçadır. **Mevcut band ve karıştırma ağırlıkları değişmez.** |
| **4. geri besleme önleme** | Üç kural: (i) ölçüm hiçbir boyut değişkenini okumaz; (ii) ilişkilendirme **mesafe** ile yapılır, **örtüşme ile değil** (örtüşme kutuyu kullanır → çevrim); (iii) çıktı yalnızca çapaya gider, `boyut`a değil — böylece `boyut` hâlâ mevcut band tarafından kırpılır ama band artık bozulmayı takip etmez |
| **5. doğrulama** | **Gözlemci koşumu** (D1 protokolü): ölçüm hesaplanır, takipçiye verilmez, GT ile karşılaştırılır. Kaynaklar: 117/23, 137/12 (birincil), 305/5 (destek), G3_agresif, G3_kritik, G0, G6_agresif (çapa). Baseline metriklerinin birebir gelmesi, gözlemin etkisizliğinin kanıtı olarak raporlanır |
| **6. kabul kriterleri** *(koşumdan önce yazılacak)* | **A1** kod okumasıyla bağımsızlık (ikili). **A2** mutlaklık (ikili). **A3** `w/GT` ve `h/GT` **medyanı** deponun kendi bandı içinde **ve** p5–p95 yayılımı aynı karelerde `rafine_kutu`'nunkinden dar — **117/23 ve 137/12'nin ikisinde de**. **A4 kullanılabilirlik**: ölçümün mevcut olduğu kare oranı, o dizide `rafine_kutu`'nun mevcut kabul oranından (%76 / %69) **düşük olmamalı** — D1 tam da burada düştü (%7). **A5** Gazebo çapalarında da A3 sağlanmalı. Dördü birden sağlanmadan A/B'ye geçilmez |

### ADAY 2 (yedek) — D: ego-telafili akış artığı bölgesinin uzamı

| | |
|---|---|
| **1. girdiler** | gri kare + `M`; ayrım ölçütü **arka planın kendi artık dağılımı** (aynı karede ölçülür) |
| **2. çıktı** | `(w_px, h_px, alan, guven)` |
| **3. bağlanacağı nokta** | Aynı: `boyut_olculen` çapası |
| **4. geri besleme önleme** | Aynı üç kural; ek olarak bölge **tohumsuz** (kare geneli) hesaplanmalı, aksi halde pencere `boyut`tan gelir |
| **5. doğrulama** | Aynı gözlemci protokolü + **maliyet ölçümü zorunlu** (yoğun akış Pi Zero için gerçek risk) |
| **6. kabul** | Aday 1 ile aynı A1–A5, **artı** kare başına ek sürenin mevcut `adaylar()` maliyetini (2.2–5.5 ms) aşmaması |

### ADAY 3 (yedek-2) — A′: eşiği veriden türeyen segmentasyon, bağımsız pencereyle

| | |
|---|---|
| **1. girdiler** | Pencere `boyut`tan **değil**, Aday 1/2'nin verdiği bağımsız uzamdan ya da kare genelinden gelir; eşik sabit oranlı olmayan, iki-modluluk temelli bir kuralla veriden türetilir |
| **2. çıktı** | `(w_px, h_px, maske_kalitesi)` |
| **3. bağlanacağı nokta** | `boyut_olculen` çapası |
| **4. geri besleme önleme** | Pencere kaynağı kutu olmamalı — bu sağlanmazsa aday **düşer** |
| **5. doğrulama** | Aynı gözlemci protokolü; 4N'in ölçtüğü üç üst-akış arızası (birleşme / parçalanma / referans renk) ayrı ayrı raporlanmalı |
| **6. kabul** | A1–A5; ayrıca **117/23'te (kontrast 5.2) parçalanmadığı** gösterilmeli — bu dizide düşerse aday biter |

> Aday 3 bilinçli olarak sona konmuştur: aynı ailenin iki üyesi (4N'de
> `rafine_kutu`, D1'de `adaylar()`) zaten ölçülüp düşmüştür. Yalnızca
> Aday 1 ve 2 de düşerse sıraya girer.

---

## 4. Bu tasarım neden 4M–4U döngüsünü tekrar etmiyor?

| 4M–4U'nun yaptığı | burada yapılan |
|---|---|
| **Mevcut** bir sinyali yeniden **ağırlıklandırmak / kapılamak** (4C ağırlık, 4D adaptif ağırlık, 4T/4U kapı) | **Yeni ve bağımsız bir ölçüm** eklemek; mevcut ağırlık, band ve kapılar **değişmiyor** |
| Karar değişkeni, kararın etkilediği büyüklüktü (`bileşen/boyut`) → kapalı çevrim (4U) | Karar değişkeni **kutuyu hiç okumuyor**; ilişkilendirme mesafeyle, ölçüm kare geneli (**Z1/Z7 tanım gereği**) |
| Türetilmiş büyüklük **bağımsız ölçümün yerine geçti** (Deney 1, 3, 4A) | Yeni ölçüm hiçbir şeyin **yerine geçmiyor**; `boyut`a değil **çapaya** bağlanıyor, mevcut ölçüm yerinde kalıyor |
| Müdahale doğrudan A/B ile sınandı; negatif sonuç bir regresyon riski taşıdı (4U: 137/12 0.548→0.190) | İlk sınav **gözlemci koşumudur**: ölçüm hesaplanır ama **beslenmez**; negatif sonucun takipçiye maliyeti **sıfırdır** (D1'de kanıtlandı) |
| Kabul ölçütü bazen sonradan tartışıldı | Ölçüt **koşumdan önce** yazılacak ve D1'in düştüğü **kullanılabilirlik** kalemi (A4) baştan ölçüte konuldu |
| Bulgular tek dizide iyi, ötekinde yıkıcı çıktı (4C 117/23, 4U 137/12) | A3/A4 **iki gerçek dizide birden** aranıyor; tek dizide başarı yeterli sayılmıyor |

Kısacası: 4M–4U mevcut boru hattının **iç düzenlemeleriydi** ve hepsi aynı
kapalı çevrime çarptı; buradaki iş boru hattına **dışarıdan bağımsız bir
ölçüm** eklemek ve onu önce **beslemeden** doğrulamaktır.

---

# KARAR

**Önerilen aday:** **E — ego RANSAC outlier kümesinin dayanıklı uzamı.**
Yeni model yok, yeni etiket yok, yeni eşik yok, yeni algoritma sınıfı yok;
kullandığı boru hattı (`goodFeaturesToTrack` + çift yönlü LK +
`estimateAffinePartial2D`) **zaten her karede koşuyor** ve iki gerçek dizide
de %100 güvenle çalışıyor. Kutuyu hiç okumadığı için Z1/Z7'yi **tanım gereği**
sağlar.

**Yedek aday:** **D — ego-telafili akış artığı bölgesinin uzamı.** Aynı
bağımsızlık gerekçesi, ama yeni bir yoğun-akış hattı ve gerçek bir maliyet
riski getiriyor. (İkinci yedek: A′.)

**Neden:** D2 envanteri A sınıfını boş bulmuştu; bu tasarım A sınıfını
**kurmayı** hedefliyor. E, mevcut kodda **zaten var olan bağımsız bir
kestirimin (ego RANSAC) atılan yan ürününü** — outlier kümesini — ölçüme
çevirir. Yani en düşük riskli hamle, yeni bir şey hesaplamak değil, hâlihazırda
hesaplanıp **çöpe atılan** bilgiyi okumaktır.

**İlk kez hangi tek deneyle sınanacak:**

> **Tek deney — "E gözlemci koşumu" (salt okunur, takipçiye hiçbir şey
> beslenmez).** Her KILITLI karede ego RANSAC'ın outlier noktaları toplanır,
> takip merkezine en yakın küme seçilir, kümenin dayanıklı uzamı `(w, h)`
> olarak kaydedilir ve GT ile karşılaştırılır. Kaynaklar: 117/23, 137/12
> (birincil), 305/5, G3_agresif, G3_kritik, G0, G6_agresif.
> Kabul ölçütü (**A1–A5**) koşumdan önce ayrı bir dosyaya yazılır ve
> sonuçlara göre değiştirilmez. Baseline metriklerinin birebir gelmesi,
> gözlemin davranışa etkisizliğinin kanıtı olarak raporlanır.
>
> Bu deney **tek bir soruyu** yanıtlar: *ölçüm var mı ve doğru mu?*
> Entegrasyon, ancak A1–A5 geçilirse ayrı bir turda tartışılır.

**Bu belgede hiçbir kod değişikliği, eşik önerisi ya da deney koşumu yoktur.**
