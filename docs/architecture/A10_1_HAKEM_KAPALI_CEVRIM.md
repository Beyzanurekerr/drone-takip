# A10.1 — KAPALI ÇEVRİM HAKEM, TEMİZ YATAK + HİSTEREZİS + KAPSAMA TABANI

> ### `KAPALI ÇEVRİM` · D1 temiz yatak · D2 histerezis · D3 kapsama tabanlı ROI
> **HÜKÜM: YİNE REDDEDİLDİ** — ama sebep değişti.
> **D3'ün birincil metriği TERS YÖNDE gitti: kanıt-yok %46 → %50.6.**
> Ön-kayıt §3'ün kuralı gereği hüküm burada başlar: *bu sayı düşmezse hakem
> beslenemez, gerisi anlamsızdır.*
>
> Buna karşılık **D2 çalıştı ve ölçüldü**: aynı 20 hücrede LOST **134 → 58**,
> yanlış kilit (takipçi durumu) **323 → 219**, IoU **0.3454 → 0.3718**.
> Kendi kendini besleyen çevrim kapandı. Ama H0 (**0.3860**) hâlâ aşılamadı.

**Tarih:** 2026-09-03 · **Ön-kayıt:** `A10_1_ONKAYIT.md` (koşumdan önce) ·
`A10_1_D1_TEMIZ_YATAK.md` (D1 raporu) · **Veri:** `cikti/a10_1_hakem.json`
**Bütünlük:** `takip/` md5 koşum öncesi = sonrası; altı kol aynı dosyalar.
`izleyici.py` **değişmedi**; eşdeğerlik testi tekrarlandı (6 hücre / 354 kare,
bit düzeyinde aynı). Yeni bileşen yok, K1–K6 değişmedi, push yok.

---

## 1. D3'ün birincil metriği — HÜKÜM BURADA BAŞLIYOR

| | kanıt yok |
|---|---|
| A10 (kirli yatak, `A8.R_sec`, kapalı çevrim) | **%46.4** |
| D1 (temiz yatak, `A8.R_sec`, açık çevrim) | %42.9 |
| **A10.1 (temiz yatak, A8 §13 + kapsama tabanı, kapalı çevrim)** | **%50.6** (40/79) |

**Kapsama tabanı, doğrulamayı besleyeceğine aç bıraktı.** Mekanizma A8'in kendi
gerilimidir, şimdi kapalı çevrimde ölçüldü: kapsama tabanı `u` (Kalman konum
belirsizliği) büyüdükçe R'yi **büyütüyor**; R büyüyünce hedef ağ girdisinde
**küçülüyor** ve A8'in ölçtüğü 40–130 px çalışma bandının altına düşüyor.
A8 §7 bunu "kapsama–büyütme gerilimi" diye adlandırmıştı ve "takipçi
tuttuğunda gerilim yok, koptuğunda her seviyede ihlal" demişti. **Doğrulayıcı
tam da takipçinin şüpheli olduğu anlarda çalışıyor** — yani gerilimin ihlal
tarafında.

> **Ön-kayıt §3'ün kuralı uygulanıyor:** bu sayı düşmedi, dolayısıyla hakem
> beslenemedi. Aşağıdaki bütün kol sonuçları **bu kısıt altında** okunmalıdır.

---

## 2. Ana tablo — 20 hücre (D1 temiz tabanı)

| kol | IoU ort | YK (hakem) | **YK (takipçi)** | kopuşlu | kilit | bho p50 | ms/kare |
|---|---|---|---|---|---|---|---|
| **H0** | **0.3860** | 125 | **125** | 10 | 0.64 | 1.982 | — |
| H1 | 0.3718 | 66 | 219 | 10 | 0.57 | 1.960 | 2.86 |
| **H2** | **0.3748** | 71 | **201** | 10 | 0.58 | **1.809** | 2.87 |
| H3 | 0.3748 | 71 | 201 | 10 | 0.58 | 1.809 | 2.70 |
| *H3-O-merkez* ⟂ | *0.3874* | *104* | *179* | *10* | *0.62* | *1.869* | *2.66* |
| *H3-O-boyut* ⟂ | *0.3736* | *66* | *221* | *10* | *0.57* | *2.017* | *2.61* |

⟂ = ÜST SINIR, başarı sayılmaz.

### Rol kırılımı

| | sağlam (5 hücre, **tek dizi**) | KOPAN (15 hücre) |
|---|---|---|
| H0 | 0.8405 | 0.2345 |
| H1 | 0.8405 (+0.0000) | 0.2155 (−0.019) |
| **H2** | **0.8466 (+0.0062)** | 0.2176 (−0.017) |
| H3-O-merkez ⟂ | 0.8473 (+0.0069) | 0.2341 (−0.0004) |

**Sağlam dizide hakem artık zarar vermiyor, hatta H2 küçük bir kazanç veriyor.**
Zarar tümüyle kopan dizilerde.

---

## 3. D2 ÇALIŞTI — aynı 20 hücrede A10 ile karşılaştırma

Bu, **kontrollü** bir karşılaştırmadır: aynı hücreler, aynı kollar, aynı
metrikler; değişen yalnızca D2 + D3.

| kol | IoU (A10 → A10.1) | YK takipçi | LOST |
|---|---|---|---|
| H0 | 0.3860 → 0.3860 | 125 → 125 | 0 → 0 |
| H1 | **0.3454 → 0.3718** | **323 → 219** | **134 → 58** |
| H2 | 0.3482 → 0.3748 | 326 → 201 | 135 → 58 |
| H3 | 0.3482 → 0.3748 | 326 → 201 | 135 → 58 |

- **LOST %57 azaldı**, KİLİTLİ ilanının düşürüldüğü kare oranı **%41 → %13.5**.
- **Kendi kendini besleyen çevrim yapısal olarak imkânsız:** giriş eşiği
  (54.08) `Kalman.ata`'nın yazdığı iz'in (8.0) **6.76 katı**; sıfırlamadan
  sonra eşik kendiliğinden aşılamaz. Çıkış eşiği (14.86) sıfırlamanın
  üstünde olduğu için yeniden edinme mandalı **serbest bırakıyor**.
- H0 satırının değişmemesi (0.3860, 125, 0) **kolların birbirinden
  yalıtıldığını** doğrular.

> **D2, A10 raporunun §5'inde teşhis edilen arızayı kapattı ve kapanışı
> sayıyla gösterdi.** Bu, A10.1'in tek net kazancıdır.

---

## 4. Boyut çapası — ilk kez ölçülebilir etki

| kol | bho p50 | bho p95 | YK takipçi |
|---|---|---|---|
| H1 (çapa yok) | 1.960 | 2.472 | 219 |
| **H2 (dedektör boyutu)** | **1.809** | **2.379** | **201** |
| H3-O-boyut ⟂ (**GT boyutu**) | 2.017 | 2.537 | 221 |

**Çapa `bho`'yu gerçekten düşürüyor** (1.960 → 1.809) ve yanlış kilidi azaltıyor
(219 → 201). A10'da bu etki ölçülemeyecek kadar küçüktü (ΔIoU +0.0022);
burada ΔIoU +0.0030 ve **bho'da açık bir yön var**.

**Ama GT boyutuyla çapalamak DAHA KÖTÜ** (bho 2.017, YK 221). Bu, A8 §7'nin
"`oracle_boyut` hiçbir şey kurtarmıyor, hatta kötüleştiriyor" bulgusunun
kapalı çevrimde doğrulanmasıdır: doğru boyut, bozuk merkezle birleşince ROI'yi
gereğinden çok daraltıyor. **Boyut ikincil kanaldır — üçüncü kez.**

---

## 5. Kabul ölçütü

| | K1a | K1b | K1c | **K2** (takipçi durumu) | K3a | K3b | K5 | **hüküm** |
|---|---|---|---|---|---|---|---|---|
| H1 | ✔ 0 | ✔ 0 | ✔ 0 | 125→**219** ✗ | 10→10 ✗ | 1 ✗ | SINANMADI | **RED** |
| H2 | ✔ 0 | ✔ 0 | ✔ 0 | 125→**201** ✗ | 10→10 ✗ | **2 ✔** | SINANMADI | **RED** |
| H3 | ✔ 0 | ✔ 0 | ✔ 0 | 125→**201** ✗ | 10→10 ✗ | **2 ✔** | SINANMADI | **RED** |
| H3-O-merkez ⟂ | ✔ 0 | ✔ 0 | ✔ 0 | 125→179 ✗ | 10→10 ✗ | 2 ✔ | SINANMADI | **RED** |
| H3-O-boyut ⟂ | ✔ 0 | ✔ 0 | ✔ 0 | 125→221 ✗ | 10→10 ✗ | 2 ✔ | SINANMADI | **RED** |

**K1 ilk kez GEÇİYOR** — A10'da her kol sağlam bir hücreyi yıkıyordu.
İki sebebi var ve ikisi de yazılmalıdır:
1. D2 histerezisi (kontrollü karşılaştırma §3 bunu destekliyor);
2. **K1'i bozan hücre (182/127·30×12) D1'de tabandan düştü.** K1 artık
   **tek dizinin 5 hücresi** üzerinden ölçülüyor.

**K2 hâlâ geçmiyor** (davranışsal okuma): +%61 yanlış kilit. Hakem
durumuyla okunduğunda 125 → 66 "iyileşme" görünür; bu, A10'da teşhis edilen
**etiket confound'unun** aynısıdır ve iki sütun bu yüzden birlikte veriliyor.

**K5: SINANMADI.** Toplam recovery denemesi 0–1 (< 5); ön-kayıt §4'ün kuralı
gereği "geçti/geçmedi" yazılmaz. Recovery yine ONAY kıtlığından aç kaldı
(ONAY 33/79).

**K4 gereği kalıcılaştırma YOK.** `HedefTakip(hakem=None)` varsayılanı değişmedi.

---

## 6. Zincirin durumu

| sayaç (H1, 20 hücre = 1180 kare) | A10 (aynı 20 hücre) | **A10.1** |
|---|---|---|
| doğrulama fırsatı | 100 | 100 |
| gerçekleşen doğrulama | 92 | **79** |
| **kanıt yok** | %46.4 | **%50.6** |
| ONAY | 33 | **33** |
| LOST | 134 | **58** |
| KİLİTLİ ilanı düşürülen kare | 483 | **159** |
| çapa yazımı (H2) | 33 | **34** |
| recovery denemesi | 0 | **0** |

**ONAY sayısı değişmedi (33).** D2 gürültüyü azalttı ama **besleme artmadı** —
çünkü besleme dedektör kanıtına bağlı ve D3 onu iyileştirmedi, kötüleştirdi.

---

## 7. Hüküm

1. **D2 başarılı.** Kendi kendini besleyen tetikleyici çevrimi kapandı;
   kontrollü karşılaştırmada LOST −%57, YK −%32, IoU +0.026.
   `KALICI_KISITLAR.md` K6 maddesi bu deneyimden yazıldı.
2. **D3 başarısız.** Kapsama tabanı, doğrulama recall'ünü **düşürdü**
   (%46 → %50.6 kanıt yok). A8'in kapsama–büyütme gerilimi, doğrulayıcının
   çalıştığı rejimde **büyütme aleyhine** çözülüyor.
3. **Hakem hâlâ tabanı geçemiyor** (0.3748 < 0.3860) ve oracle merkez kolu
   ancak +0.0014 ile başa baş (A10'da taban altındaydı — bu da bir ilerleme).
4. **Boyut çapası ilk kez ölçülebilir**: bho 1.960 → 1.809. Ama GT boyutu
   daha kötü — boyut ikincil kanal.
5. **Karar tabanı tek sağlam diziye indi.** K1'in geçmesi bu daralmadan
   bağımsız değildir ve tek başına kanıt sayılamaz.

---

## 8. Sınırlar

**Tek sağlam dizi (137/12, 5 hücre)** — K1/K2/K6'nın sağlam ayağı tek diziden ·
20 hücre · Mod B örneklemi 2 hücre (D1) · recovery sınanmadı (0–1 deneme) ·
yalnızca A5_baseline · N = 5 koşulmadı · düşen üç dizi çürütülmedi, bu
protokolde ölçülemez oldu · tek koşum, tekrar yok · Pi Zero 2 W'ye
ekstrapolasyon **yapılmadı** (doğrulama 2.6–2.9 ms/kare, masaüstü CPU).

---

## 9. DUR

Kalıcı değişiklik yok; varsayılan davranış H0'dır.

**Ölçüme dayalı üç sonraki aday (hiçbiri sınanmadı):**

1. **Kapsama tabanını doğrulama ile recovery için AYIRMAK.** D3 ölçtü ki
   kapsama tabanı doğrulamada recall'e mal oluyor. Doğrulama Δt = 0'da yapılır
   (hedef kaçmış olamaz) — kapsama kısıtı orada belki gereksizdir; recovery'de
   (Δt > 0) gereklidir. Bu ayrım **ölçülmedi**.
2. **Karar tabanını yeniden genişletmek.** Tek sağlam dizi ile K1/K2/K6
   ölçülemez hale geliyor. Düşen üç dizi **daha küçük bir sensör tuvaliyle**
   (ör. 960×540) geçerli yatak verebilir; bu, seviye tanımını değiştirir ve
   kendi ön-kayıtlı geçerlilik testini ister.
3. **Dedektör recall'ü — yedinci kez.** Doğrulamanın yarısında kanıt yok.
   Çapa da recovery de bundan aç. Bu tavan kırılmadan hakemin hiçbir sürümü
   K2'yi geçemez.
