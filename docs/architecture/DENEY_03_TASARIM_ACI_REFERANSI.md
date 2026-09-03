# Deney 3 tasarımı — açı için mutlak referans

**Kod değişikliği yapılmadı, commit/push yok.** Bu belge yalnızca tasarım ve
onu dayandırdığım ölçümlerdir.

Deney 2'nin teşhisi: seçilen açı gerçek dönmeyi birim kazançla (0.998) izliyor
ama arama adımı dönüş yönüne asimetrik bir DC yanlılık üretiyor
(−0.0497 °/kare), bu yanlılık mutlak çapa olmadığı için serbestçe birikiyor
(−0.0397 °/kare doğrusal kayma, 293 karede −11.8°) ve G3_agresif'teki −0.006
IoU kaybını tek başına açıklıyor.

Tasarımı yapmadan önce iki şeyi ölçtüm, çünkü ikisi de stratejileri doğrudan
eliyor.

---

## Ön ölçüm 1 — Korelasyon yüzeyi aslında YANSIZ

Sentetik, tam kontrollü: kilit kutusu 56×22, içerik +θ döndürülüyor, açı
±70° penceresinde 0.5° adımla taranıyor. **Örnekleme kutusu kilit en-boy
oranını koruduğu sürece kestirim tam doğru:**

| θ | −60° | −40° | −20° | 0° | +20° | +40° | +60° |
|---|---|---|---|---|---|---|---|
| tepe | −60.0 | −40.0 | −20.0 | +0.5 | +20.0 | +40.0 | +60.0 |
| hata | 0.0 | 0.0 | 0.0 | +0.5 | 0.0 | 0.0 | 0.0 |
| PSR | 145 | 148 | 148 | 117 | 144 | 145 | 147 |

Yani sorun "DCF dönmeyi ölçemiyor" değil.

## Ön ölçüm 2 — Sorun YAMA GEOMETRİSİ; en-boy oranı kayınca kestirim çöküyor

Aynı test, tek fark: örnekleme kutusunun en-boy oranı kilitten saptırılıyor
(gerçek dönme +20° sabit):

| örnekleme kutusu | en-boy | tepe açı | hata | PSR |
|---|---|---|---|---|
| 56×22 (kilitle aynı) | 2.55 | +20.0 | **0.0** | **144** |
| 58×26 (−%12) | 2.23 | +20.5 | +0.5 | **19.5** |
| 60×30 (−%22) | 2.00 | −70.0 | **−90.0** | 10.3 |
| 57×36 (−%38) | 1.58 | −52.0 | **−72.0** | 6.3 |
| 56×42 (−%48) | 1.33 | +25.0 | +5.0 | 5.4 |

%12'lik sapma tepeyi henüz kaçırmıyor ama **PSR'yi 7 kat düşürüyor**; %22'de
kestirim tamamen çöküyor. Bunun nedeni yamanın `boyut × dolgu` dikdörtgeni
olarak kesilip N×N kareye yeniden ölçeklenmesi: kilitteki ve şimdiki en-boy
oranları farklıysa bileşke dönüşüm artık saf dönme değildir.

**Gerçek veride bu sapma mevcut.** `boyut` eksen hizalı sınırlayıcı kutudur ve
hedef döndükçe büyür:

| | yama en-boy oranı | kilit oranından sapma p50 / p95 |
|---|---|---|
| G3_agresif | 1.34 … 1.72 | **%12.1 / %25.9** |
| G3_kritik | 0.89 … 1.42 | **%23.9 / %44.4** |

Bu, aşağıdaki A1 stratejisini doğrudan öldürür ve C'nin güven ölçütlerini
güvenilmez kılar.

## Ön ölçüm 3 — Dondurulmuş kilit şablonu ÇAPA OLAMIYOR

Salt okunur ölçüm: kilit anındaki filtre (A₀, B₀) dondurulur, hiç öğrenilmez;
her karede gerçek açının ±60° çevresinde 2° adımla taranır.

| | tepe ofseti (gerçek açıya göre) | \|ofset\| ≤ 2° olan kare | dondurulmuş PSR | uyarlanan PSR |
|---|---|---|---|---|
| G3_agresif | **−10.2°** (kararlı, büyümüyor) | **%17.1** | 16–27 | 49–68 |
| G3_kritik | **−20.3°** | **%6.5** | 10–22 | 44–71 |

Dondurulmuş şablonun tepesi gerçek açıdan sistematik olarak sapıyor ve
ayırt ediciliği uyarlanan filtrenin 1/3'ü. Nedeni ön ölçüm 2: dondurulmuş
şablonun en-boy oranı kilit oranıdır, koşum ortasında güncel örnekleme
geometrisinden %12–44 sapmıştır.

**Sonuç: DCF görünüm modeli — ne uyarlanan ne dondurulmuş hâli — mutlak açı
referansı sağlayamaz.**

## Ön ölçüm 4 — Ego entegrasyonu, gerçek dönme varken 10–16 kat daha doğru

Deney 1 tam olarak açık çevrim ego entegrasyonunu ölçmüştü; Deney 2 de DCF
aramasını. İkisi yan yana (kare başına açı kayması, °/kare):

| senaryo | gerçek dönme | **ego entegrasyonu** (Deney 1) | **DCF araması** (Deney 2) |
|---|---|---|---|
| G3_agresif | var (−22.2°) | **−0.0031** | −0.0497 |
| G3_kritik | var (−48.0°) | **−0.0050** | −0.0210 |
| G4_kritik | **yok** (0°) | **−0.0313** ← ego uyduruyor | 0 (kapı kapalı) |
| G5_kritik | yok | −0.0089 | 0 (kapı kapalı) |
| G1_kritik | yok | −0.0039 | 0 (kapı kapalı) |
| G6_agresif | yok | −0.0059 | 0 (kapı kapalı) |

İki hata kaynağı **birbirini tamamlayıcı ve ayrık**:
* Ego yalnızca **perspektif** olduğunda yanılır (pitch → benzerlik dönüşümü
  perspektifi sahte dönme olarak soğurur; G4_kritik `e_model_p95` 4.62 px).
* DCF araması **her çalıştığında** yanılır, ego'nun 10–16 katı hızda.

Ve Deney 2'nin açma kapısı **tam olarak ego'nun yanıldığı durumları dışarıda
bırakıyor** — ölçüldü:

| senaryo | ego dönme p95 | eşik | kapı | marj |
|---|---|---|---|---|
| G4_kritik | 0.30 °/kare | 0.84 | kapalı | 2.8× |
| G5_kritik | 0.04 | 0.92 | kapalı | 23× |
| G6_agresif | 0.02 | 0.83 | kapalı | 41× |
| VisDrone 117/23 | 0.33 (maks) | 0.81 | kapalı | 2.5× |
| VisDrone 268/31 | 0.07 (maks) | 0.18 | kapalı | 2.6× |
| VisDrone 182/127 | 0.56 (maks) | 3.27 | kapalı | 5.8× |
| G3_agresif | 2.66 | 0.81 | **açık** | — |
| G3_kritik | 5.68 | 0.77 | **açık** | — |

---

# Üç referans stratejisi

## A) Kilit anındaki referans sabit

İki farklı uygulaması var ve ölçümler bunları zıt yönlere ayırıyor.

### A1 — referans = dondurulmuş DCF şablonu

* **Referans ne zaman alınır:** `baslat()` anında (kilit ve yeniden kilit).
* **Ne zaman güncellenir:** hiçbir zaman.
* **Hangi veriye güvenir:** kilit anındaki görünüm (A₀, B₀), açı = 0.
* **Ne zaman güncellenmez:** her zaman. (A3.8'in `imza_ref` tasarımıyla aynı
  mantık: "güncellenirse doğrulama kendi kendini onaylayan bir ölçüye döner".)
* **G3_agresif'te beklenen davranış:** **çalışmaz.** Ön ölçüm 3: dondurulmuş
  şablonun tepesi gerçek açıdan −10.2° sapmalı ve karelerin yalnızca %17'sinde
  ±2° içinde. Referans olarak kullanılsaydı açıyı −11.8°'lik mevcut kaymadan
  −10.2°'lik yeni bir sabit sapmaya taşırdı — kazanç yok.
* **Riskler:** G4/G6/VisDrone'da kapı kapalı olduğu için etkisiz (risk yok),
  ama G3'te de fayda yok. Ayrıca ek maliyet: aktif karede bir korelasyon daha.

**A1 elenmiştir — ölçülerek.**

### A2 — referans = kilide çapalı EGO ENTEGRASYONU (önerilen)

* **Referans ne zaman alınır:** `baslat()` anında `aci_ref = 0`.
* **Ne zaman güncellenir:** her aktif karede `aci_ref += dteta`
  (ego'nun ölçtüğü kare-arası dönme). Kapı kapalıyken **hiç** güncellenmez.
* **Hangi veriye güvenir:** ego-motion'ın benzerlik dönmesine. Ölçülen doğruluk:
  293 karede toplam yanlılık **+0.11°** (G3_agresif) / **+0.76°** (G3_kritik).
* **Ne zaman güncellenmez:** kapı kapalıyken (`|dteta| < eşik` ve `aci = 0`);
  KILITLI/SUPHELI dışındaki durumlarda `ara` zaten çağrılmaz; yeniden kilitte
  `baslat` sıfırlar.
* **DCF'in rolü:** hafızasız düzeltici. Kullanılan açı
  `aci = aci_ref + delta`, `delta ∈ {−adım, 0, +adım}` her karede DCF
  aramasıyla seçilir ve **bir sonraki kareye taşınmaz**. Böylece DCF'in
  −0.05 °/kare yanlılığı birikemez; yalnızca ego referansının etrafında
  ±1 adımlık bir salınıma dönüşür.
* **G3_agresif'te beklenen davranış:** kayma hızı DCF'inkinden ego'nunkine
  düşer: −0.0397 → **−0.0031 °/kare**. 293 karede birikmiş hata
  −11.8° → **≈ −0.9°**. Ölçülen `dIoU` – `|hata|` ilişkisinden
  (|hata| ≤ 4.8° → dIoU **+0.023**) beklenen IoU **0.766 → ≈ 0.789**.
* **G3_kritik'te beklenen:** birikmiş hata −2.9° → ≈ −1.5°; IoU ≥ 0.704
  (korunması şart, iyileşmesi olası).
* **Riskler:**
  * *Kapı açılırsa ego yalanı geri gelir.* Ölçülen en dar marj 2.5×
    (VisDrone 117/23) ve 2.8× (G4_kritik). Bu ikisi izlenmeli.
  * Açık kalan senaryoda ego yanlılığı pitch varsa −0.031 °/kare'ye çıkar
    (G4_kritik ölçümü) — G3'tekinin 10 katı. Yani "kamera hem yaw hem pitch
    yapıyor" bir senaryo bu tasarımın kör noktasıdır; mevcut G1–G7 ailesinde
    böyle bir senaryo **yok** (her senaryo tek eksen).
  * VisDrone'da hiç açılmadığı için ne fayda ne zarar beklenir.

## B) Periyodik referans yenileme

* **Ne zaman alınır:** kilitte; sonra her N karede bir.
* **Ne zaman güncellenir:** koşulsuz, takvimle.
* **Hangi veriye güvenir:** o anki şablon ve o anki `aci`.
* **Ne zaman güncellenmez:** (tanımı gereği hiç atlanmaz).
* **G3_agresif'te beklenen davranış:** **kaymayı gidermez.** Kayma sürekli ve
  kendi kendine tutarlıdır (−0.0397 °/kare, korelasyon(hata, kare) = −0.871);
  referansı zaten kaymış olan güncel durumdan yenilemek hatayı silmez, onu
  yeni taban kabul eder. Beklenen sonuç Deney 2 ile aynı, N ne olursa olsun.
* **Riskler:** Yeni bir eşik (N) getirir, karşılığında ölçülebilir bir fayda
  yok. Ayrıca `izleyici.py`'nin `imza_ref` için belgelediği hatanın aynısıdır:
  kendi kendini onaylayan referans.
* Eğer B "periyodik olarak ego'dan yeniden türet" diye okunursa, A2'ye
  indirgenir — sadece N kare gecikmeyle, yani A2'nin daha kötü bir hâli.

**B elenmiştir — hem ölçüm hem tasarım gerekçesiyle.**

## C) Sadece güvenli koşullarda referans yenileme

* **Ne zaman alınır:** kilitte.
* **Ne zaman güncellenir:** yalnızca "güvenli" karelerde — doğal adaylar:
  yüksek PSR, adaylar arası net skor ayrımı, yüksek ego güveni, orta adayın
  (ego tohumunun) kazanması.
* **Hangi veriye güvenir:** DCF yanıtının güvenilirlik göstergelerine.
* **Ne zaman güncellenmez:** koşullardan biri düşünce; SUPHELI/ARAMA/KAYIP'ta;
  yanlış kilit reddinden sonra.
* **G3_agresif'te beklenen davranış:** **ters teper.** Kaymanın kaynağını
  ölçtüm:

  | | kare | ort. arama adımı | toplam katkı |
  |---|---|---|---|
  | beraberliğe yakın (skor ayrımı < %2) | 110/293 | −0.0000° | **−0.00°** |
  | net kazanan (skor ayrımı ≥ %2) | 183/293 | −0.0796° | **−14.57°** |

  Kaymanın **tamamı** net kazananlı karelerden geliyor; beraberliğe yakın
  karelerin katkısı tam sıfır. Güven tabanlı bir "güvenli" kapısı tam olarak
  yanlılığı taşıyan kareleri seçer. PSR de ayırt etmiyor: G3_agresif'te
  PSR p50 = 54, yani kayma boyunca filtre "güvenli" görünüyor.
* **Riskler:** 3–5 yeni eşik (Deney 2'nin tek sabitlik disiplinini bozar) ve
  ölçüme göre yanlış işaretli bir seçicilik.
* Tek savunulabilir "güvenli" tanımı **"arama ego tohumunu onayladı"** (orta
  aday kazandı, karelerin %61.4'ü) olurdu — ama o zaman referans fiilen ego
  entegrasyonudur, yani yine A2.

**C elenmiştir — ölçülerek.**

---

# Referans nereden üretilmeli? (ölçülebilir tartışma)

| kaynak | mutlak çapa sağlar mı | ölçülen kayma / sapma | ne zaman yanılır |
|---|---|---|---|
| **DCF, uyarlanan** | hayır — kendi seçtiği açıda öğrendiği için sapma kendi kendine tutarlı | −0.0397 °/kare, 293 karede −11.8° | her çalıştığında |
| **DCF, dondurulmuş** | hayır — ölçüldü | tepe ofseti −10.2° / −20.3°, ±2° içindelik %17 / %6.5, PSR 1/3 | yama en-boy oranı kilitten %12+ sapınca |
| **Ego entegrasyonu** | evet, kilide çapalı ve bağımsız | **−0.0031 / −0.0050 °/kare** (gerçek dönme varken) | yalnızca perspektifte (pitch): −0.031 °/kare |
| **Birleşim (A2)** | evet | ego'nunki + DCF'in hafızasız ±1 adımı | ego'nun yanıldığı yerde — ama kapı orayı zaten kapatıyor |

Sayısal karar: gerçek dönme varken **ego, DCF'ten 10–16 kat daha doğru**;
gerçek dönme yokken **ego yalancı, DCF ise susturulmuş**. Kapı ikisini ayıran
ölçüttür ve Deney 2'de ölçülerek doğru tarafta çalıştığı gösterildi (22
Gazebo kaydının 20'sinde kapalı, 3 VisDrone dizisinin hepsinde kapalı,
en dar marj 2.5×).

Bu yüzden referans **ego entegrasyonundan** üretilmeli; DCF referans üretmemeli,
yalnızca referansın etrafında **hafızasız** bir düzeltme yapmalıdır. Saf DCF
referansı ölçülerek elendi; saf ego referansı (Deney 1) kapısız hâliyle
elendi — kapıyla birlikte geri geliyor.

---

# Öneri: Deney 3 = A2

**Kilide çapalı, kapıyla korunan ego entegrasyonu referans; DCF araması
hafızasız düzeltici.**

Tek değişiklik prensibi korunur: Deney 2'ye göre değişen tek şey `aci`nın
nasıl taşındığıdır (`aci_prev` yerine `aci_ref`). Yeni eşik **eklenmez** —
`tolerans_px`, `aci_adim`, `dteta_esik` aynen kalır. Ego-motion, Kalman,
durum makinesi ve A3.8 yanlış-kilit mekanizması yine değişmez.

## Neden seçildi

1. Kaymayı kaynağında keser: ölçülen ego kayması DCF'inkinin **1/16'sı**.
2. Deney 2'nin bit-birebir eşleşme özelliğini **aynen korur** — kapı mantığı
   değişmediği için 30/32 senaryoda kod yolu yine dokunulmamış kalır.
3. Yeni parametre getirmez; A1/B/C'nin üçü de ya ölçüyle eleniyor ya da
   parametre ekliyor.
4. Deney 1'in tek gerçek kusuru (kapısız ego) zaten Deney 2'de ölçülerek
   kapatıldı; A2 bu iki deneyin doğrulanmış yarılarını birleştirir.

## Hangi testlerde doğrulanacak

`python3 deney.py --etiket deney3` ve `--kiyas deney2 deney3`, artı
`python3 -m gazebo.tani_aci G3_agresif G3_kritik`.

**Birincil (öncelikli):** G3_agresif, G3_kritik, G4_agresif, G4_kritik,
G6_agresif, VisDrone 117/23 · 268/31 · 182/127.
**Tam kapsam:** 22 Gazebo kaydı + sim test1–7 + 3 VisDrone dizisi (32 senaryo).

## Başarı kriterleri

**Geçmesi ZORUNLU olanlar**

| # | ölçüt | eşik | şu anki değer |
|---|---|---|---|
| 1 | değişmeyen senaryo sayısı (alan alan, tol 1e-12) | **≥ 30/32** | 30/32 |
| 2 | G3_kritik drift karesi | **yok** | yok |
| 3 | G3_kritik kilit oranı | **%100** | %100 |
| 4 | G3_kritik IoU | **≥ 0.704** | 0.704 |
| 5 | G3_agresif IoU | **≥ 0.766** (A3.8 tabanı) | 0.760 |
| 6 | VisDrone üç dizide açı araması aktif kare | **0** | 0 |
| 7 | G4/G5/G6 ailelerinde aktif kare | **0** | 0 |

**Hedeflenen (başarı ölçüsü)**

| # | ölçüt | hedef | şu anki değer |
|---|---|---|---|
| 8 | G3_agresif IoU | **≈ 0.789** | 0.760 |
| 9 | G3_agresif açı kayma hızı \|a\| | **≤ 0.010 °/kare** | 0.0397 |
| 10 | G3_agresif \|açı hatası\| p95 | **≤ 3°** | 13.01° |
| 11 | G3_kritik \|açı hatası\| p95 | **≤ 5°** | 7.69° |
| 12 | korelasyon(hata, kare no) mutlak | **≤ 0.30** | 0.871 |
| 13 | aktif karede `ara()` süresi | **≤ 900 µs** | 826 µs |

**Başarısızlık = tamamen geri al.** Özellikle 1., 5., 6. veya 7. maddenin
düşmesi doğrudan geri alma sebebidir: ilki tek değişkenliliği, diğerleri
Deney 1'in regresyonunun geri geldiğini gösterir.

## Deney 3 başarılı olsa bile açık kalacak konu

Ön ölçüm 2, asıl kırılganlığın **yama geometrisi** olduğunu gösteriyor:
örnekleme kutusu eksen hizalı sınırlayıcı kutu olduğu için hedef döndükçe
en-boy oranı kilitten %12–44 sapıyor ve PSR 7 kata kadar düşüyor. A2 bunu
çözmez, yalnızca etkisini ego referansıyla maskeler. Kalıcı çözüm, örnekleme
kutusunun kilit en-boy oranını koruyup açıyla birlikte dönmesidir — ölçüldü:
o durumda kestirim −60°…+60° arasında **tam doğru** (hata 0.0°, PSR ~146).
Ama bu `boyut` semantiğini, `rafine_kutu`'yu ve `_boyut_sinirla`'yı birden
etkiler; tek değişiklik değildir. **Deney 4 adayı olarak not edilmiştir.**
