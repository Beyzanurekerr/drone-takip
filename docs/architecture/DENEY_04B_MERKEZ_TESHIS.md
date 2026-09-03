# Deney 4B — merkez hatası teşhisi

**Kod değişikliği yok, commit/push yok.** `takip/` altındaki 6 dosyanın md5'i
Deney 2 durumuyla birebir (`md5sum -c` 6/6 OK) ve 32 senaryonun tamamı Deney 2
sayılarıyla **birebir aynı** (alan alan karşılaştırma, farklı alan sayısı = **0**).

Ölçüm aracı: `gazebo/tani_merkez.py` — `HedefTakip` alt sınıfı + `rafine_kutu`
saydam sarması. Hiçbir eşik, karar veya parametre değişmedi; ölçer baseline
metriklerini birebir yeniden üretiyor (G3_agresif IoU 0.760 / merkez 3.81 px,
G3_kritik 0.704 / 5.07 px, G0 0.912 / 1.24 px).

## Aşama haritası — koddaki gerçek isimler

Tahmin yok; hepsi grep'lenerek doğrulandı. Merkezi hareket ettiren **tüm**
çağrı noktaları:

| istenen aşama | koddaki karşılık |
|---|---|
| 1 GT merkezi | `veri/gazebo.py:GazeboKaynak._kutu` → `Kare.gt` |
| 2 `rafine_kutu` merkezi | `tespit.py:rafine_kutu`; `izleyici.py:565` `yeni_c`, satır **567** `kf.duzelt(yeni_c, r_carpan=1.0)` |
| 3 DCF/template peak | `cekirdekler.py:RenkDcfCekirdek.ara` → `_tepe`; `izleyici.py:_takip_adimi` içinde `yeni` |
| 4 Kalman prediction | `izleyici.py:263` `kf.tahmin(M)` sonrası `kf.konum` |
| 5 Kalman update sonrası | `izleyici.py:312` / **327** `kf.duzelt(...)` sonrası `kf.konum` |
| 6 Ego uygulanmış merkez | `izleyici.py:253` `ongoru = M[:,:2] @ _onceki_merkez + M[:,2]` |
| 7 Final tracker merkezi | `HedefTakip.kutu` property → `kf.konum` |

**Kritik yapısal bulgu:** merkeze **iki** ölçüm enjekte ediliyor — DCF her
karede (312/327), `rafine_kutu` **4 karede bir** (567, `dogrulama_araligi=4`).
Bu ikisi ayrılmadan "Kalman kaydırdı" ile "rafine kaydırdı" ayırt edilemez.

## Aşama aşama hata dağılımı

Hata iki çerçevede: **görüntü** ve **şablon** (hata vektörü −açı ile
döndürülür). Şablonun öğrendiği tepe hedef merkezinden sabit bir vektör kadar
kaymışsa bu şablon çerçevesinde sabit görünür; görüntü koordinatlarında bir şey
sürüklüyorsa görüntü çerçevesinde sabit kalır.

### G3_agresif (IoU 0.760, merkez 3.81 px, 293 kare)

| aşama | n | \|e\| p50 | p95 | ort | dx ort | dy ort | dx ŞABLON | dy ŞABLON |
|---|---|---|---|---|---|---|---|---|
| 6 ego uygulanmış | 292 | 5.62 | 8.19 | 5.64 | -5.35 | -0.89 | -4.21 | -3.69 |
| 4 KF öngörü | 293 | 3.81 | 6.89 | 3.92 | -3.67 | -0.88 | -2.73 | -2.74 |
| **3 DCF tepesi** | 293 | 4.72 | 7.02 | 4.45 | -4.17 | -0.97 | -3.13 | -3.10 |
| 5 KF düzeltme sonrası | 293 | 4.35 | 6.83 | 4.24 | -3.97 | -0.94 | -2.97 | -2.96 |
| **2 rafine merkezi** | 62 | 0.75 | 1.23 | 0.76 | -0.56 | -0.37 | -0.27 | -0.58 |
| 2b tazele sonrası | 73 | 3.27 | 4.84 | 3.16 | -2.96 | -0.77 | -2.16 | -2.26 |
| 7 final | 293 | 3.82 | 6.37 | 3.87 | -3.63 | -0.88 | -2.70 | -2.71 |

### G3_kritik (IoU 0.704, merkez 5.07 px, 293 kare)

| aşama | n | \|e\| p50 | p95 | ort | dx ort | dy ort | dx ŞABLON | dy ŞABLON |
|---|---|---|---|---|---|---|---|---|
| 6 ego uygulanmış | 292 | 6.89 | 11.24 | 7.04 | -5.73 | -0.45 | -3.70 | -5.92 |
| 4 KF öngörü | 293 | 5.12 | 9.57 | 5.29 | -4.34 | -0.44 | -2.71 | -4.46 |
| **3 DCF tepesi** | 293 | 5.84 | 9.65 | 5.85 | -4.78 | -0.48 | -3.01 | -4.91 |
| 5 KF düzeltme sonrası | 293 | 5.57 | 9.57 | 5.63 | -4.61 | -0.46 | -2.89 | -4.73 |
| **2 rafine merkezi** | 49 | 0.75 | 1.06 | 0.76 | -0.53 | -0.48 | +0.02 | -0.58 |
| 2b tazele sonrası | 73 | 3.88 | 9.30 | 4.52 | -3.71 | -0.40 | -2.27 | -3.83 |
| 7 final | 293 | 5.09 | 9.42 | 5.25 | -4.30 | -0.44 | -2.68 | -4.42 |

## 1. Hata hangi aşamada başlıyor?

**`rafine_kutu` merkezi neredeyse kusursuz: 0.76 px** (p95 1.23 / 1.06). Diğer
her aşama 3.8–7.0 px. Kontrol senaryolarında da aynı — rafine her yerde en
doğru aşama:

| senaryo | aktif açı araması | ego \|e\| | KF öngörü | DCF \|e\| | **rafine \|e\|** |
|---|---|---|---|---|---|
| G0 | 0 | 2.81 | 1.38 | 1.49 | **0.85** |
| G3_yumusak | 0 | 3.72 | 2.03 | 2.23 | **0.91** |
| G4_kritik | 0 | 3.74 | 2.33 | 1.85 | **1.19** |
| G3_agresif | 293 | 5.64 | 3.92 | 4.45 | **0.76** |
| G3_kritik | 293 | 7.04 | 5.29 | 5.85 | **0.76** |
| G6_agresif | 0 | 10.59 | 9.10 | 9.68 | 5.78 |

**DCF tepesi ile rafine merkezi doğrudan karşılaştırıldığında** (rafine'nin
ateşlediği karelerde):

| senaryo | n | rafine−GT | DCF−GT | **DCF−rafine** | dx | dy |
|---|---|---|---|---|---|---|
| G0 | 72 | 0.85 | 1.52 | 1.54 | **−0.94** | −0.04 |
| G3_yumusak | 72 | 0.91 | 2.32 | 1.99 | **−1.77** | −0.23 |
| G4_kritik | 73 | 1.19 | 1.88 | 1.89 | **−1.47** | −0.10 |
| G3_agresif | 62 | 0.76 | 4.91 | 4.32 | **−4.02** | −0.75 |
| G3_kritik | 49 | 0.76 | 6.07 | 5.61 | **−4.43** | −0.36 |
| G6_agresif | 49 | 5.78 | 9.11 | 12.86 | **−11.49** | +2.74 |

Hata **DCF tepesinde** başlıyor. Ve DCF, kendisini besleyen KF öngörüsünden
**daha kötü** (4.45 vs 3.92 / 5.85 vs 5.29) — yani ölçüm düzeltmiyor, bozuyor.

## 2. En büyük katkıyı yapan aşama — kare başına bütçe

Ortalama |e| ile kapalı bir bütçe (G3_agresif):

    final(t-1)          3.87
      + ego taşıma      +1.77   -> 5.64   (arka planın kareye 1.78 px kayması)
      + KF hızı         -1.72   -> 3.92   (hız bu kaymayı öğrenmiş, soğuruyor)
      + DCF ölçümü      +0.53   -> 4.45   <-- TEK HATA ENJEKTE EDEN AŞAMA
      + KF harmanı      -0.21   -> 4.24
      + rafine (73/293) -0.37   -> 3.87   (ateşlediğinde -1.49, amortize -0.37)
    ------------------------------------
    final(t)            3.87   (denge)

G3_kritik'te aynı yapı: ego +1.79, DCF **+0.55**, KF −0.22, rafine −1.52
(amortize −0.38).

**Denge, DCF'in kare başına +0.53 px enjekte etmesi ile rafine'nin 4 karede bir
1.49 px geri çekmesi arasındaki dengedir.** DCF 4 kat daha sık çalıştığı için
denge noktası rafine'nin kendi doğruluğunun (0.76 px) 5 katında oturuyor.

## 3. Sistematik bias: yön ve büyüklük

**Görüntü çerçevesinde −x**, dy ihmal edilebilir:

| senaryo | GÖRÜNTÜ dx ± sd | GÖRÜNTÜ dy ± sd | ŞABLON dx ± sd | ŞABLON dy ± sd |
|---|---|---|---|---|
| G3_agresif | **−4.17 ± 1.54** | −0.97 ± 1.34 | −3.13 ± 1.43 | −3.10 ± 1.05 |
| G3_kritik | **−4.78 ± 2.30** | −0.48 ± 3.55 | −3.01 ± 1.56 | −4.91 ± 2.32 |
| G3_yumusak | −2.09 ± 1.09 | −0.68 ± 0.23 | (açı 0, aynı) | (aynı) |
| G0 | −1.08 ± 1.30 | −0.36 ± 0.11 | (açı 0, aynı) | (aynı) |

Görüntü çerçevesi biası **tek eksende** topluyor (dx/dy oranı 4.3:1); şablon
çerçevesi iki eksene **dağıtıyor** (1:1). Yani bias **görüntü koordinatlarına
çapalı**, şablonun duruşuna değil.

Yön anlamlı: bütün senaryolarda ortak baz gereği **arka plan hedefe göre −x
yönünde 1.78 px/kare akıyor** (G0'da hedef +x'e gidiyor, G1–G7'de kamera
+X'e gidiyor — ikisinde de bağıl akış −x). Bias tam o yönde.

## 4. Açı / şekil / PSR / Kalman / ego ile ilişki

| ilişki | G3_agresif | G3_kritik | okuma |
|---|---|---|---|
| corr(dx, \|açı\|) | **−0.021** | **−0.077** | açıyla ilişkisi **yok** |
| corr(dx, kutu alanı) | 0.379 | **0.641** | kutu büyüdükçe değişiyor |
| corr(dx, kutu h) | 0.323 | **0.670** | özellikle yükseklikle |
| corr(dx, PSR) | 0.318 | 0.134 | zayıf |

PSR düşük/yüksek üçte birler: G3_agresif −4.72 / −3.68; G3_kritik −4.50 /
−4.23. **PSR 282'ye çıktığında bile bias sürüyor.**

Ego: aşama 6 en büyük |e|'ye sahip (5.64 / 7.04) ama bu hata **üretimi değil,
taşıma**: önceki karenin biası + o karenin arka plan kayması. Ego'nun kendi
doğruluğu Faz B'de ölçülmüştü (`e_ego_p95` = 0.15 px). KF hızı taşımanın
%97'sini geri alıyor (+1.77 → −1.72).

## 5. Hipotezlerin durumu

| # | hipotez | sonuç | kanıt |
|---|---|---|---|
| A | Merkez hatası sistematik bir yöne mi kayıyor? | **EVET** | görüntü −x, −4.17 / −4.78 px ort |
| B | Hata DCF peak aşamasında mı başlıyor? | **EVET** | tek hata enjekte eden aşama, +0.53 px/kare |
| C | DCF doğruyken Kalman mı kaydırıyor? | **HAYIR** | Kalman hatayı −0.21 px azaltıyor |
| D | Ego-motion dönüşümü mü kaydırıyor? | **HAYIR** | taşıyor, üretmiyor; hız %97'sini geri alıyor |
| E | `rafine_kutu` merkezi zaten hatalı mı? | **HAYIR** | 0.76 px — en doğru aşama, 5× fark |
| F | Kutu resize / koordinat dönüşümü mü? | **REDDEDİLDİ** | sentetik: öğrenmesiz, aynı karede dx = **+0.000 px** (3 farklı kutu oranında) |
| G | PSR yüksekken de aynı yanlış bölge mi? | **EVET** | PSR 34–282 aralığında bias −3.7…−4.7 px |
| H | Merkez hatası ↔ açı hatası korelasyonu | **YOK** | corr ≈ −0.02 / −0.08 |
| I | Merkez hatası ↔ kutu boyutu/oranı | **VAR** | corr(h) 0.32 / 0.67; corr(alan) 0.38 / 0.64 |

### Ana hipotez: "DCF güvenilir bir peak buluyor fakat peak konumu sistematik olarak GT merkezinden sapıyor"

**DESTEKLENDİ.** PSR yüksek ve kararlı (p50 54, max 282), sıçrama küçük, ama
tepe görüntü −x yönünde 4–4.8 px kaymış ve orada kalıyor.

### Sapmanın kaynağı: öğrenme, koordinat dönüşümü değil

Kilit sonrası zaman seyri (DCF dx):

| senaryo | k+0 | k+1 | k+3 | k+8 | k+20 | k+40 | k+80 |
|---|---|---|---|---|---|---|---|
| G0 | −1.66 | −1.73 | −1.67 | −1.12 | −0.89 | −1.62 | −2.47 |
| G3_agresif | −0.78 | −0.87 | −1.04 | −1.15 | −1.33 | −3.28 | **−5.57** |
| G3_kritik | −0.42 | −0.50 | −0.68 | −0.79 | −0.46 | −2.16 | **−5.99** |

Kilitte ~0.5–1.7 px, onlarca kare boyunca **büyüyor**. Bir koordinat hatası
anında ve sabit olurdu.

Sentetik doğrulama (`RenkDcfCekirdek`, gerçek kod):

| durum | dx | dy | PSR |
|---|---|---|---|
| öğrenme yok, aynı kare, kutu 56×22 / 56×42 / 50×55 | **+0.000** | +0.000 | 716 |
| arka plan −2 px/kare kayarken 12 kare öğrenme, kutu 56×22 | **−1.065** | 0.000 | 23 |
| aynı, kutu 56×42 | −0.780 | 0.000 | 37 |
| aynı, kutu 50×55 | −0.498 | 0.000 | 37 |

Dönüşüm **birebir doğru**; kayan arka planla öğrenme ise tam olarak bağıl arka
plan hareketi yönünde bir bias üretiyor. Mekanizma: yama `boyut × dolgu`
(dolgu = 2.0), yani alanın ~%75'i arka plandır; arka plan hedefe göre tutarlı
biçimde aktığı için filtre onun bir kısmını öğreniyor ve tepe o yöne çekiliyor.

## 6. Sonraki optimizasyon için TEK aday

**`rafine_kutu` merkez düzeltmesinin Kalman ağırlığını ölçülmüş doğruluğuna
göre ayarla** — `izleyici.py:567`, `kf.duzelt(yeni_c, r_carpan=1.0)`.

Gerekçe, doğrudan ölçümden:

* rafine 0.76 px, DCF 4.45 px doğrulukta — **5.9 kat fark**, ama ikisi de
  `r_carpan = 1.0` ile **eşit ağırlıkta** Kalman'a giriyor.
* Denge şu an DCF'in +0.53 px/kare enjeksiyonu ile rafine'nin amortize
  −0.37 px/kare çekişi arasında; ağırlığı ölçülen varyans oranına yaklaştırmak
  dengeyi rafine'nin kendi doğruluğuna doğru kaydırır.
* **Gecikme maliyeti sıfır** — tek bir sayı, ek hesap yok.
* Patlama yarıçapı dar: yalnızca `_boyut_tazele`'nin ateşlediği karelerde
  (73/293) ve yalnızca merkez düzeltmesinde etkili.

**Reddedilen alternatif — rafine'yi daha sık koştur (`dogrulama_araligi` 4→1).**
Ölçüldü, çok pahalı:

| kutu | `rafine_kutu` | `ara()` | oran |
|---|---|---|---|
| 56×22 | 1442 µs | 405 µs | 3.6× |
| 56×42 | 2471 µs | 421 µs | 5.9× |
| 50×55 | 3108 µs | 497 µs | 6.3× |

Her karede koşmak kare başına +1080…+2330 µs ekler; ~2600–3000 µs'lik bütçede
**%30–45 FPS kaybı**. Aynı etkiyi sıfır maliyetle veren ağırlık ayarı varken
kabul edilemez.

**Not:** Bias'ın kökü DCF yamasındaki arka plan bulaşmasıdır (`dolgu = 2.0`
ile yamanın ~%75'i arka plan). Onu doğrudan hedefleyen bir değişiklik
(pencereleme / dolgu / bağlam bastırma) daha temel bir çözüm olurdu ama
`ara()`'nın tamamını etkiler ve 32 senaryonun hepsini değiştirir — tek
değişiklik disiplinine ve 30/32 birebir kalma ölçütüne uymaz. Ağırlık ayarı
önce denenmelidir.
