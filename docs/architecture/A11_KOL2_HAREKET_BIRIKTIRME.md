# A11 KOL 2 — ZAMANSAL HAREKET BİRİKTİRME

> ### `AÇIK ÇEVRİM` · `TAKİPÇİYE YAZMAZ` · `KOMPOZİT YATAK YOK` · Gazebo
> **Sinyal var ve mükemmel; seçim yok.** 8×5 bandında (dedektörün Gazebo'da
> **%100 kör** olduğu bant — KOL 0) hareket biriktirme **her checkpoint'te**
> bir aday üretiyor (**kanıt oranı %100**) ve en yakın adayın GT'ye uzaklığı
> **oracle p50 = 1.2–3.0 px** — şaşırtıcı derecede iyi. Ama **"en büyük
> blob" seçim kuralı bu adayı neredeyse hiç seçmiyor**: operasyonel hata
> p50 **106–328 px** — checkpoint başına ortalama **~50–66 aday** arasında
> boğuluyor.

**Tarih:** 2026-09-03 · **Kod:** `gazebo/tani_a11_kol2.py`
**Veri:** `cikti/a11_kol2.json` · **Ön-kayıt:** `A11_ONKAYIT.md` §4
**Bütünlük:** `takip/*.py` md5 koşum öncesi = sonrası — **hiçbir dosya
değişmedi**, takipçiye hiç yazılmadı (açık çevrim, ön-kayıt gereği).

---

## 1. Yöntem

`takip/tespit.py:HareketTespit`'in mevcut mekanizmasının **genellenmiş**
hali: N∈{3,5,8} kareyi ego-telafili olarak SON karenin çerçevesine taşıyıp
ardışık farkları **toplar** (mevcut kod 2–3 kare için **min** = mantıksal
VE, hayalet silme kullanır; KOL 2 **sum** kullanır — gerekçe: A11
senaryolarının kendi tasarımı gereği hedef hızı = kamera baz hızı
(`_kam()`: *"böylece hedef görüntüde nominal olarak sabit kalır"*), yani
ego-telafisi sonrası hedef **aynı yerde durur** — N kare boyunca aynı
konumda biriken fark bir hayalet değil, **aranan sinyalin ta kendisi**).

**İki ayrı ölçüm — A9/A10'un oracle/operasyonel ayrımıyla aynı ilke:**
- **operasyonel**: gerçek kullanımda seçilecek aday (**en büyük bağlı
  bileşen**) — GT bilgisi kullanılmaz.
- **oracle**: üretilen adaylar arasında **GT'ye en yakın olan** — "sinyal
  doğru bölgede var mı" sorusuna cevap, **seçim** sorunundan ayrı
  (üst sınır, başarı sayılmaz).

Doğrulama noktaları hakemin **N=10 kadansıyla aynı** karelerde alındı
(doğrudan karşılaştırılabilirlik için).

---

## 2. Ana tablo

| senaryo | N | kanıt oranı | operasyonel p50 | **oracle p50** |
|---|---|---|---|---|
| A1_taban | 3/5/8 | 1.00 | 161/161/126 | 8.5/7.1/**5.2** |
| A2_kucul | 3/5/8 | 1.00 | 203/199/148 | 3.5/2.2/**1.8** |
| A3_yaw | 3/5/8 | 1.00 | 161/171/170 | 8.4/7.1/**5.4** |
| A4_irtifa | 3/5/8 | 1.00 | 106/155/234 | 3.6/5.0/3.6 |
| A5_kucul_yaw | 3/5/8 | 1.00 | 145/169/328 | 3.3/3.3/**2.5** |
| A6_celdirici | 3/5/8 | 1.00 | 161/161/121 | 8.5/7.1/**5.2** |

**Kanıt oranı 6 senaryonun 3 N'inin TAMAMINDA %100** — dedektörün Gazebo'da
ölçülen **%0**'ının (KOL 0) tam tersi.

**Oracle hata her yerde tek haneli/düşük çift haneli px** — mevcut
takipçinin kendi süreklilik performansıyla (KOL 0/1'de IoU 0.05–0.29
aralığında, merkez hatası çoğu zaman **çok yüz px**) kıyaslanınca bu kanal
**GT'ye çok daha yakın** bir sinyal taşıyor.

---

## 3. 8×5 bandı — asıl soruya doğrudan cevap

Yalnızca küçültme içeren A2/A5'te bu bant var (diğer 4 senaryo GT_L'yi
10 px'in altına hiç düşürmüyor):

| senaryo | nokta | kanıt oranı | operasyonel p50 | **oracle p50** |
|---|---|---|---|---|
| A2_kucul · 8×5 | 13 | **1.00** | 235 px | **1.222 px** |
| A5_kucul_yaw · 8×5 | 10 | **1.00** | 147 px | **2.954 px** |

> **Ön-kayıtta sorulan soruya cevap: EVET, bu kanal dedektörün Gazebo'da
> tamamen kör olduğu bantta (KOL 0: kanıt yok %100) doğru bölgede güçlü bir
> sinyal üretiyor.** 8×5'te oracle hata (1.2–3.0 px), 30×12'deki oracle
> hatadan (5.2–8.5 px) bile **daha iyi** — çünkü ego-telafisi sonrası kalan
> tek büyük "hareketli" leke küçük hedefte celdiricilerle daha az
> karışıyor (nicelik olarak gösterilmedi, ama aday sayısı dağılımıyla
> tutarlı, §4).

---

## 4. Darboğaz: seçim, algılama değil

Checkpoint başına ortalama aday sayısı (A2_kucul):

| N | ort. aday | min | max |
|---|---|---|---|
| 3 | 65.9 | 17 | 126 |
| 5 | 54.6 | 19 | 113 |
| 8 | 49.7 | 18 | 102 |

**"En büyük alan" adayı, ~50–66 adaydan biri.** Doğru aday neredeyse
her zaman **listede var** (oracle'ın %100 kanıt oranı bunu doğruluyor) ama
**en büyük değil** — Gazebo'nun prosedürel zemin dokusu (KOL 0 §3'te
görsel olarak teşhis edilen aynı doku: yol çizgileri, ağaç desenleri) ego
telafisinden sonra da **büyük, tutarlı fark blokları** üretiyor ve bunlar
hedeften daha büyük kalıyor.

> **Bu, KOL 0'ın DCF-doku-kayması bulgusuyla AYNI kök nedeni paylaşıyor:**
> Gazebo'nun prosedürel dokusu, hem korelasyon filtresini (KOL 0) hem
> hareket-biriktirme blob seçimini (KOL 2) **aynı şekilde** aldatıyor —
> her ikisi de "en güçlü/en büyük sinyal" heuristiğine dayanıyor ve
> Gazebo'nun dokusu bu heuristiği hedeften daha iyi tatmin ediyor.

**N'nin etkisi karışık:** çoğu senaryoda N=8 operasyoneli **iyileştiriyor**
(A1: 161→126, A6: 161→121) ama irtifa/yaw içeren senaryolarda
**kötüleştiriyor** (A4: 106→234, A5: 145→328) — muhtemelen 8 karelik
pencerede ego-telafisinin (benzerlik dönüşümü, ölçek/dönme değişimi altında)
kümülatif hatası büyüyor ve blok sınırları bulanıklaşıp büyüyor.

---

## 5. Hüküm

1. **Sinyal kalitesi mükemmele yakın** (oracle p50 tek haneli px, 8×5'te
   dahi) — hareket biriktirme, dedektörün göremediği yerde **doğru
   bölgede** güçlü kanıt üretiyor. Bu, hakemin **kanıt-yok %100**'üne
   (KOL 0) doğrudan ve olumlu bir cevaptır.
2. **Ama mevcut "en büyük blob" seçim kuralı bu sinyali kullanılamaz hale
   getiriyor** — 50+ rakip aday arasında doğru olan neredeyse hiç
   kazanmıyor. **Bu kolun bulduğu asıl şey, gelecek bir seçim/ayırt etme
   mekanizmasının ihtiyacıdır**, algılama mekanizmasının kendisi değil.
3. **Kök neden KOL 0 ile aynı**: Gazebo'nun prosedürel zemin dokusu, hem
   korelasyon-filtresi hem blob-büyüklüğü heuristiklerini aynı şekilde
   yanıltıyor.

---

## 6. Sınırlar

Yalnızca "en büyük" (operasyonel) ve "en yakın" (oracle) — aradaki (ör.
önceki konuma yakınlık, boyut/en-boy tutarlılığı gibi bir seçim kuralı)
**sınanmadı** · N=8'in altimetre/yaw senaryolarındaki kötüleşmesinin kök
nedeni derinlemesine incelenmedi · eşik (`min_esik`, `esik_k`)
`HareketTespit`in mevcut mertebesinden alındı, Gazebo'ya göre **ayrıca
kalibre edilmedi** · tek koşum · Pi Zero 2 W maliyeti ölçülmedi (N arttıkça
`warpAffine`+`absdiff` çağrı sayısı da artar, doğrusal).

---

## 7. DUR

Kalıcı değişiklik yok (`takip/` hiç değişmedi, açık çevrim).

**Sıradaki aday (sınanmadı):** en büyük yerine **önceki bilinen konuma
en yakın** blob'u seçmek (basit bir mesafe-öncelikli kural, GT kullanmadan)
— oracle'ın gösterdiği sinyal kalitesini operasyonel hale getirmenin en
ucuz yolu budur ve kendi ön-kayıtlı ölçütünü ister.
