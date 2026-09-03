# D2* — Yeni ölçüm envanteri (maliyet ölçümü ATLANDI)

> **Not:** Asıl D2 (maliyet ölçümü) kullanıcı kararıyla **atlandı**: D1,
> `adaylar()`ın bağımsız ve mutlak olmasına rağmen güvenilir bir w/h ölçümü
> vermediğini kanıtladı; ölçüm doğrulanmadan maliyet bir karar değişkeni
> değildir. Bu belge onun yerine geçen **salt okunur envanterdir**.

**`takip/` altında hiçbir dosya değiştirilmedi**, hiçbir eşik değiştirilmedi
ya da eklenmedi, yeni algoritma yazılmadı, commit/push yok. `takip/` md5'leri
Deney 2 baseline'ı ile **6/6 aynı**.
Veri: `cikti/yeni_olcum_envanteri.json`.

**Soru:** `boyut`tan ve `rafine_kutu`'dan bağımsız, **mutlak piksel** cinsinden
hedef w/h üretebilecek bir kod yolu ya da görüntü sinyali depoda **zaten var
mı?**

---

## 1. Depodaki tüm görüntü-geometri yolları (tam tarama)

`takip/`, `main.py`, `kaynak.py` üzerinde `cv2.*` çağrılarının tamamı tarandı.

### 1a. Var olanlar

| ölçüm | kaynağı | `boyut`/`rafine` bağımlılığı | mutlak mı? | doğrudan hedef mi? | mevcut eşik | kod yeri | 117/23 | 137/12 | sınıf |
|---|---|---|---|---|---|---|---|---|---|
| `HareketTespit.adaylar()` bileşen kutusu | ego-hizalı kare farkı → `connectedComponents` | **YOK** | **EVET (px)** | evet | `max(8.0, μ+4σ)`; alan≥3; kenar≤160; en/boy≤9 | `tespit.py:47-84` | S1 %7 kare | S1 %67 kare, h/GT 0.30 | **D** |
| `rafine_kutu()` bileşen kutusu | yerel renk-medyan uzaklığı → `connectedComponents` | **VAR** (pencere = 3·`boyut`, oran kapısı `boyut`a böler, renk kapısı `imza.renk`) | EVET (px) | evet | `p82`/16.0; oran 0.35–2.6; `renk_tol`=60 | `tespit.py:87-134` | kabul %76 | kabul %69 | **B + C** |
| `EgoMotion.M` (öteleme+dönme+**ölçek**) | 0.5× küçültülmüş gri kare; `goodFeaturesToTrack` + LK + RANSAC; **hedef kutusu maskelenir** | **YOK** | **HAYIR** — kare-arası **oran** | **hayır — arka plan** | 0.85<s<1.18; kayma<0.5·W; ≥6 nokta / ≥8 inlier | `egomotion.py:34-115` | güven>0 **%100**, med 0.949 | %100, med 0.920 | **A ama tip yanlış** |
| `RenkDcfCekirdek` yanıt/PSR/tepe | yama = `boyut`·`dolgu`(2.0) → 32×32 | **VAR** | hayır (yer değiştirme) | evet | 9.0 / 4.5 | `cekirdekler.py:95-225` | her KILITLI kare | her KILITLI kare | **B** |
| `MosseCekirdek` | yama = `boyut`·`dolgu` | VAR | hayır | evet | 5.5 / 3.2 | `mosse.py` | kullanılmıyor | kullanılmıyor | **B** |
| `NccCekirdek` (`matchTemplate`) | şablon `_sablon_boyut(boyut)` | VAR | hayır | evet | 3.2 / 2.0; `max_sablon`=48 | `cekirdekler.py:227-275` | kullanılmıyor | kullanılmıyor | **B** |
| `AkisCekirdek` (hedef içi LK) | 6×4 nokta ızgarası **kutunun içine** serpilir | VAR | hayır (yalnızca öteleme) | evet | ileri-geri hata<1.0; iyi≥4 | `cekirdekler.py:278-318` | kullanılmıyor | kullanılmıyor | **B** |
| `Imza` (renk + 12×12 şablon + boyut) | `kutu`dan kesilen yamalar | VAR | hayır (benzerlik skoru) | evet | `kimlik_esik`=0.45, periyot 6 | `tespit.py:137-181` | kimlik testi neredeyse hiç koşmuyor (4K) | aynı | **B** |
| Zemin/hareketlilik testi (ego artığı P90) | `kf.konum` ile ego öngörüsü arasındaki artık | **YOK** (konum tabanlı) | hayır | evet (konum) | `zemin_sabir`=20, `zemin_pencere` | `izleyici.py:392-402` | her kare | her kare | **A ama boyut bilgisi taşımıyor** |
| `veri/gazebo.py:izdusur()` | 3B araç boyutu + kamera iç/dış parametreleri | YOK | **EVET (px)** | evet | — | `veri/gazebo.py:46-56` | **YOK** | **YOK** | **A ama koşumda erişilemez** |

### 1b. Depoda **hiç bulunmayanlar** (grep, `takip/` + `main.py` + `kaynak.py`)

`findContours` 0 · `Canny` 0 · `minAreaRect` 0 · `fitEllipse` 0 ·
`boundingRect` 0 · `Farneback` (yoğun akış) 0 · `HoughLines` 0 · `watershed` 0 ·
`grabCut` 0 · `Sobel` 0 · `Laplacian` 0 · `pyrDown` 0 · `SIFT` 0 · `ORB` 0

> Yani depoda **kontur, kenar, minimum-alan dikdörtgeni, elips uydurma, yoğun
> optik akış, gradyan operatörü ve anahtar-nokta betimleyicisi hiç yoktur.**
> Tek segmentasyon yolu iki `connectedComponentsWithStats` çağrısıdır
> (`adaylar` ve `rafine_kutu`) ve **ikisi de eşik tabanlıdır**.

### 1c. Yapısal boşluk: **hiçbir çekirdekte ÖLÇEK ARAMASI yok**

Dört çekirdeğin `ara()` imzası da `boyut`u **verili** alır ve yalnızca bir
**merkez** (+ Deney 2'den beri bir **açı**) döndürür. `NccCekirdek.olcek`
yalnızca şablonu küçülten bir çarpandır, ölçek araması değildir.
Korelasyon takipçilerinin boyutu ölçmekte kullandığı standart mekanizma
(ölçek-uzayı araması) **depoda yoktur**.

---

## 2. A / B / C / D / E sınıflandırması

| sınıf | tanım | depodaki üyeler |
|---|---|---|
| **A** — gerçekten yeni ve bağımsız | `boyut`/`rafine`den bağımsız **ve** mutlak **ve** doğrudan hedefi ölçen | **BOŞ.** En yakın üç aday da düşüyor: `EgoMotion` (bağımsız ama **oran**, hedefi değil arka planı ölçer), zemin testi (bağımsız ama **boyut bilgisi taşımaz**), `izdusur()` (mutlak ama **koşumda erişilemez**) |
| **B** — mevcut boyuttan türetilmiş | girdisi `boyut` olan her şey | RenkDcf, Mosse, Ncc, Akis, Imza, `rafine_kutu`'nun pencere ve oran kapıları |
| **C** — `rafine_kutu`'dan türetilmiş | `boyut_olculen` ve dolayısıyla `_boyut_sinirla` bandı | `izleyici.py:549, 564` (4S'te ölçüldü: çevrim kapalı) |
| **D** — hareket farkının ölçümü | `adaylar()` | D1: bağımsız + mutlak **ama yanlış** (medyan w/GT 0.17–0.89, h/GT 0.20–0.95) — talimat gereği yeniden önerilmiyor |
| **E** — doğrudan ölçen ama çeldirici/zemin yüzünden güvenilmez | `rafine_kutu` | 4N: birleşme (çeldirici), parçalanma (düşük kontrast), referans renk bulanması |

---

## 3. `ego.olcek_katsayisi` — ayrı inceleme (talep edildiği gibi)

| soru | yanıt | kanıt |
|---|---|---|
| Gerçekten hedef boyutundan bağımsız mı? | **EVET.** Hedef kutusu 6 px payla maskelenip köşe seçiminin dışında bırakılıyor. | `egomotion.py:105-110` (`_maske`) |
| Hangi görüntüden hesaplanıyor? | Gri karenin **0.5× küçültülmüşünden**; `goodFeaturesToTrack` + iki yönlü LK + `estimateAffinePartial2D` (RANSAC). | `egomotion.py:57, 50, 76-84` |
| Neyin geometrisini temsil ediyor? | **Arka planın** kare-arası benzerlik dönüşümü. `s = sqrt(|det A|)` → nadir kamerada **irtifa değişimi**. | `egomotion.py:113-115` |
| Doğrudan hedef w/h'ye çevrilebilir mi? | **HAYIR.** Birimsiz bir **kare-arası orandır** (üstelik 0.85–1.18'e kırpılır). Mutlak w/h ancak bir çapa ile **çarpılarak biriktirilirse** çıkar. | `egomotion.py:87-91` |
| Biriktirme neden yol değil? | Kodun **kendi yorumu**: noktalar yenilenmezse ölçekte yanlılık oluşur ve *"sabit irtifada bile kare kare %0.4 → 300 karede 3× şişme"*. Aynı tuzak proje hafızasında da kayıtlı. | `egomotion.py:68-72` |
| Zaten kullanılıyor mu? | **EVET** — `izleyici.py:264`: `boyut = max(boyut · olc, min_kenar)`. | 4R'de katkısı ölçüldü: ×1.014 (G6_agresif) … ×1.176 (305/5) |
| Kullanılabilirliği | 117/23 ve 137/12'de **karelerin %100'ünde** güven>0 (medyan 0.949 / 0.920). | 4O kaydı |

> **Sonuç:** `ego.olcek_katsayisi` **bağımsızdır ama ölçüm tipi yanlıştır** —
> bir *hız/oran*, bir *çapa* değil. Zaten tüketiliyor ve tek başına birikmiş
> mutlak hatayı (kutu/GT 0.53…1.88) düzeltemez.

---

## 4. İki gerçek dizide kullanılabilirlik özeti

| ölçüm | 117/23 | 137/12 |
|---|---|---|
| `rafine_kutu` (mevcut) | 85 çağrının 65'i kabul (%76) | 52'nin 36'sı (%69) |
| `adaylar()` S1 | **24/342 kare (%7)** | 139/206 (%67) — ama h/GT 0.30 |
| `EgoMotion` güveni | %100, medyan 0.949 | %100, medyan 0.920 |
| DCF PSR / tepe | her KILITLI kare | her KILITLI kare |
| Açı araması aktif oranı | **%0.0** | %9.8 |

---

# SONUÇ: **2) MEVCUT KODDA UYGUN ÖLÇÜM YOK, YENİ ÖLÇÜM TASARLANMALI**

**Gerekçe — A sınıfı boştur.** Depodaki on geometri yolu tarandı; üçü
`boyut`tan bağımsız, ama hiçbiri aynı anda **mutlak + doğrudan hedefi ölçen**
değil:

* `EgoMotion` → bağımsız ve doğru çalışıyor (%100 kullanılabilir) ama
  **arka planı** ölçüyor ve çıktısı bir **orandır**; biriktirme yolu kodun
  kendi yorumuyla kapalı.
* Zemin/hareketlilik testi → bağımsız ama **boyut bilgisi taşımıyor**.
* `izdusur()` → mutlak ama **kamera pozu + 3B araç boyutu** gerektiriyor;
  gerçek videoda yok.
* `adaylar()` → bağımsız + mutlak ama **yanlış** (D1, kabul edildi).
* Geri kalan altı yolun tamamı girdisini `boyut`tan alıyor (**B sınıfı**),
  yani Z1'i (kararın girdisini etkilememesi) yapısal olarak ihlal ediyor.

Ayrıca envanterin en somut bulgusu **bir yokluktur**: depoda kontur, kenar,
min-alan dikdörtgeni, elips uydurma, yoğun akış, gradyan ve anahtar-nokta
yolu **hiç yok**; dört çekirdeğin hiçbirinde **ölçek araması yok**. Boyut
bugün yalnızca iki eşik tabanlı segmentasyondan geliyor (`p82` ve `μ+4σ`) ve
D1 ile 4N ikisinin de aynı kök nedeni paylaştığını gösterdi: **sabit oranlı
kontrast eşiği nesnenin kendisini değil parçasını veriyor.**

**Bu turda hiçbir kod değişikliği, eşik önerisi ya da yeni algoritma
yazılmadı.** Bir sonraki adım tasarım turudur ve kapsamı bu envanterle
belirlenmiştir; hangi ölçümün tasarlanacağı ayrı bir karardır ve bu belgede
verilmemiştir.
