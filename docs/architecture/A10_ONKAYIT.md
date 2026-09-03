# A10 — KAPALI ÇEVRİM HAKEM PROTOTİPİ · ÖN-KAYIT

**Yazıldığı tarih:** 2026-09-03 · **A10 deneyleri KOŞULMADAN ÖNCE yazıldı.**
Sonuçlara bakılıp değiştirilmeyecek. Değişmesi gerekirse gerekçeli yeni sürüm
eklenir, bu sürüm silinmez. Precedent: `A9_KABUL_OLCUTU.md`,
`A9_3_2_SECIM_KURALI.md`, `A9_3_3_ONKAYIT.md`, `A3.9C_KABUL_OLCUTU.md`.

> **A9 KAPANDI. Bundan sonra açık çevrim deney yok.** A10'un her ölçümü
> **kapalı çevrimdir**: dedektör → hakem → takipçi, ve hakemin kararı takipçinin
> davranışını değiştirir.

## 0. Neden A10

A/B-3, 3.2 ve 3.3 aynı kökü gösterdi:

- **A/B-3:** bağımsız, mutlak boyut ölçümü **yok**; `_boyut_tazele`'nin çapası
  kendi bozduğu büyüklüğe bakıyor (kapalı çevrim, 4U dersinin altıncı tekrarı).
- **3.2:** operasyonel referansta ayakta kalan tek bileşen `d_norm` (AUC 0.951);
  `a_norm`/`r_norm` `bho` şişmesinden zarar görüyor.
- **3.3:** kanonik Mod B hücresinde `min_G` geçişten 29 kare **önce** zaten
  kronik ihlalde — çünkü `a_norm` bozuk boyuttan besleniyor.

Teşhis bitti. A10 bu kökü **bağımsız bir ölçümle** kapatmayı dener.

---

# 1. KARAR TABANI — genişletme kuralı (koşumdan önce)

**Amaç:** 3.3'ün LOSO bulgusunu kırmak. İki kırılganlık ölçülmüştü:
(i) 137/12 çıkınca çalışma noktası kalmıyor; (ii) Mod B tabanının 3/4'ü
339/49'dan geliyor.

**Depo gerçeği:** `data/datasets/visdrone_vid` yalnızca VisDrone2019-VID-**val**
setini (7 dizi) içeriyor ve 086'da araç track'i yok → kullanılabilir 6 dizinin
altısı da zaten tabanda. Bu yüzden yeni **diziler** VisDrone2019-MOT-**test-dev**
setinden eklenecek (17 dizi; VID ile aynı korpus, aynı etiket formatı).

## 1.1 Seçim ölçütleri (mekanik, takdir payı yok)

| ölçüt | tanım | kaynağı |
|---|---|---|
| **Ö-A** | Dizide araç sınıfından track olmalı; `veri/etiket.py:en_uygun_arac_track` bir hedef seçebilmeli | 4I Ö1 (veri gerçeği) |
| **Ö-B** | Seçilen track'in **ilk 60 görünür karesi ardışık** olmalı: gerçek span = 60, maks boşluk = 1 | A9 Aşama 1-EK yatak geçerlilik ölçütü |
| **Ö-C** | Kompozit yatak kurulabilmeli: native kare ≥ 1280×720 **ve** `arkaplan_hucresi` hedefi 60 karenin hiçbirinde içermeyen geçerli bir 1280×720 hücre bulabilmeli | A5.2 kompozit protokolü, A7 sensör tuvali |
| **Ö-D** | Aynı `uav#####` önekinden **en çok bir** dizi (aynı uçuş/sahne ailesi sayılmaz) | LOSO amacı |

**Sıralama:** Ö-A…Ö-D'yi geçen diziler **dizi adına göre artan** sıralanır ve
**ilk 3'ü** alınır. Skor yok, performans bakılmaz, takdir payı yok.

> **Seçim, takipçi/dedektör davranışına BAKMADAN yapılır.** Ö-A…Ö-D'nin hiçbiri
> IoU, kopuş, recall ya da herhangi bir başarı ölçüsü içermez. Yeni dizilerin
> "kopan mı sağlam mı" olduğu ancak taban donduktan **sonra** ölçülür ve
> raporlanır; seçimi etkileyemez.

## 1.2 Taban donuyor

Seçim uygulandıktan sonra karar tabanı **9 dizi** olur (6 mevcut + 3 yeni) ve
A10 boyunca **değişmez**. Yeni dizi eklenmesi, dizi çıkarılması, seviye
değiştirilmesi yasaktır. Uygulanan taban bu dosyaya **EK-1** olarak yazılır.

Seviye merdiveni değişmiyor: **30×12 · 20×10 · 15×7 · 10×5 · 8×5**, `N_KARE = 60`.
→ **45 hücre**.

> *(Bu paragraftaki "9 dizi / 45 hücre" bir **beklentiydi**, kural değil. Ölçüt
> mekanik uygulandığında yalnızca 1 dizi geçti → taban **7 dizi / 35 hücre**.
> Ayrıntı **EK-1**. Ölçüt sonuca bakılarak gevşetilmedi.)*

---

# 2. SABİTLER — hepsi önceden, hepsi mevcut ölçümden

Yeni sayı uydurulmadı. Her sabit ya kod tabanında var ya da yayımlanmış bir
A9 ölçümünden geliyor.

| sabit | değer | kaynağı |
|---|---|---|
| **N** (doğrulama periyodu) | **10 kare** | 3.2 maliyet tablosu: N=10 → **4.14 ms/kare**, N=5 → 8.47. Pi Zero 2 W bütçesi ~36 ms; N=10 bütçenin %11.5'i, N=5 %23.5'i. **Maliyet tabanlı seçim.** N=5 koşulmayacak (kapsam). |
| **R merdiveni** | geçen kare 1–5 → **160** · 6–20 → **320** · 21+ → **640** | Deney 3.0 "gerekli yarıçap p95" tablosu; 3.2'de aynen kullanıldı |
| **G kapısı** | **1.0** | 3.2 kuralı (`A9_3_2_SECIM_KURALI.md`), normalizasyonun tanımı |
| **k** (ardışık ihlal) | **1** | 3.3 hükmü: ön-kayıtlı kural SIFIRLA kolunda k=1'i seçti; k>1 Mod B yakalamayı düşürüyor |
| **kanıt yok politikası** | **durum değişmez** | 3.3'ün DONDUR politikası; kanıt yokluğu arıza kanıtı değildir |
| **doğrulama sinyali** | **yalnızca `d_norm`** | 3.2 §9.3 (operasyonel referansta ayakta kalan tek bileşen, AUC 0.951 ≈ oracle 0.952) + 3.3 §5 (`a_norm` `bho`'dan kirleniyor) |
| **doğrulama ROI'si** | A8 adaptif kuralı `R_sec(L_est)`, Δt = 0 | A8'de yayımlanmış kural, 3.2 KOL V'de kullanıldı |
| **boyut çapası ağırlığı** | `boyut = 0.75·boyut + 0.25·ölçüm` · `boyut_olculen = ölçüm` (MUTLAK) | 0.75/0.25 `izleyici.py:_boyut_tazele`'nin mevcut sabiti; mutlak yazım çarpımsal biriktirmeyi (A9 tuzağı) dışlar |

`d_norm` tanımı 3.2'den **birebir**:
`d_norm = |c_aday − c_ref| / (MAX_HIZ·Δt + max(ref_w, ref_h)/2)`, `MAX_HIZ = 35`
(`izleyici.py:Kalman.MAX_HIZ`). `a_norm` ve `r_norm` **hesaplanmaz**.

---

# 3. BİLEŞENLER

## 3.1 DOĞRULAYICI

Her **N = 10** karede bir, dedektör takipçinin ROI'sinde koşar
(`R_sec(L_est)` merkezli, Δt = 0). Adaylar `d_norm` ile skorlanır; `min d_norm`
alınır.

| gözlem | karar |
|---|---|
| aday yok (**kanıt yok**) | **durum DEĞİŞMEZ** |
| `min d_norm ≤ 1.0` | **ONAY** → KİLİTLİ |
| `min d_norm > 1.0` (k = 1) | **SUSPECT** |
| Mod A sinyali: ölçüm kaybı (`kayip > 0`) **veya** P konum izi artışı | **LOST** |

**Mod A eşiği:** yeni sayı uydurulmaz. `kayip > 0` takipçinin kendi ölçüm-kaybı
sayacıdır. P artışı için ölçüt, Kalman'ın **kendi başlangıç kovaryansına**
görelidir: `iz(P[:2,:2]) > 8.0`, yani `Kalman.__init__`'teki
`diag([4.0, 4.0, …])` izinin (8.0) üstü. Mevcut sabit, yeni değil.

> **Takipçi kendi başına KİLİTLİ ilan edemez.** Takipçi KİLİTLİ dese bile hakem
> onaylamadıkça durum SUSPECT'te tutulur. **Bilinen yan etki:**
> `_bagimsiz_dogrula` (A3.8 imza + zemin denetimi) yalnızca KİLİTLİ durumda
> çalışır; SUSPECT'te tutulan karelerde bu denetim koşmaz. Bu bir davranış
> değişikliğidir, **ölçülecek ve K6 altında raporlanacaktır**.

## 3.2 BOYUT ÇAPASI

Doğrulama **ONAY** verdiğinde, seçilen dedektör kutusunun boyutu takipçiye
yazılır:

```
boyut_olculen = dedektor_kutu[2:]                      # MUTLAK - bagimsiz olcum
boyut         = 0.75*boyut + 0.25*dedektor_kutu[2:]    # mevcut sabit
```

- **Merkeze YAZMAZ.** `kf.duzelt` çağrılmaz. (A/B-1/4U dersi.)
- **Çarpımsal biriktirme yok.** Çapa her onayda mutlak ölçümle yeniden kurulur.
- `_boyut_sinirla`'nın bandı (`[0.60, 1.70]·boyut_olculen`) değişmez — ama
  artık çapası **bağımsız** bir ölçümdür. P0.1 tam olarak budur.

## 3.3 RECOVERY

**LOST**'ta: son güvenilir merkez etrafında, `R(geçen kare)` merdiveniyle
dedektör koşar. Adaylar `d_norm` ile skorlanır.

```
GECEN = { aday : d_norm <= 1.0 }
GECEN bos  -> CEKIMSER (hicbir sey yapma, takipcinin kendi aramasi surer)
degilse    -> argmin d_norm -> YENIDEN TOHUM -> SUSPECT
```

Yeniden tohumlanan kilit, doğrulayıcı **ONAY** verene kadar SUSPECT'te kalır.
"Herhangi bir nesneye kilitlendi" başarı sayılmaz (K5).

---

# 4. KOLLAR

| kol | içerik |
|---|---|
| **H0** | baseline — hakem yok, mevcut davranış (kontrol) |
| **H1** | yalnızca doğrulayıcı (§3.1) |
| **H2** | H1 + boyut çapası (§3.2) |
| **H3** | H2 + recovery (§3.3) |
| **H3-O-merkez** | H3, doğrulama/recovery referansı **GT merkezi** → **ÜST SINIR** |
| **H3-O-boyut** | H3, çapa **GT boyutu** → **ÜST SINIR** |

Oracle kollar **başarı sayılmaz**; yalnızca "bileşen mükemmel olsaydı tavan ne
olurdu" sorusunu yanıtlar (A8 precedent'i).

Bütün kollar **aynı** `takip/` dosyalarını kullanır; kollar arası fark yalnızca
hakem yapılandırmasıdır. **Her kol için `takip/*.py` md5 raporlanır ve altısı da
aynı olmalıdır.**

---

# 5. KABUL — `A9_KABUL_OLCUTU.md` AYNEN GEÇERLİ

K1–K6 değiştirilmemiştir. Hatırlatma ve A10'a uygulanışı:

- **K1** sağlam dizilerde regresyon yok: K1a yeni kopuş yok · K1b ortalama IoU
  0.03'ten fazla düşmez · K1c merkez hatası p95 %20'den fazla artmaz.
- **K2** güvenli yanlış kilit toplamı kontrol kolunu (H0) **aşmayacak**. **MUTLAK.**
- **K3** kopan dizilerde gerçek fayda: K3a kopuşlu hücre sayısı azalacak ·
  K3b en az iki AYRI kopan dizide ortalama IoU artacak · K3c merkez hatasının
  tek başına düşmesi fayda sayılmaz.
- **K4** K1–K3 birlikte sağlanmadıkça kalıcılaştırma yok.
- **K5** `false recovery` ve toplam güvenli yanlış kilit H0'ı **aşmayacak**. **MUTLAK.**
- **K6** recovery hiç tetiklenmeyen hücrelerde IoU ve merkez hatası K1
  sınırları içinde kalacak.

**A10'a özgü ekleme yok.** Yeni dizilerin tabana girmesi paydaları büyütür;
eşikler oran/mutlak tanımlarıyla aynen uygulanır.

**Beraberlik:** birden fazla kol K1–K6'yı geçerse `A9_KABUL_OLCUTU.md`'nin
beraberlik sırası uygulanır (daha düşük yanlış kilit → daha yüksek IoU →
daha az kopuşlu hücre → `takip/` üzerinde daha küçük değişiklik).

---

# 6. ZORUNLU METRİKLER (her kol, her hücre)

`A9_KABUL_OLCUTU.md`'nin tamamı:

IoU · merkez hatası p50/p95 · **güvenli yanlış kilit** (`durum == KİLİTLİ` **ve**
`IoU < 0.2` kare sayısı) · **kopuş** (`|merkez hatası| > 0.5·GT_L`, 5 ardışık kare)
sayısı · PSR p50/p05 · Kalman P konum izi p50/p95 · `bho = boyut.max()/GT_L`
p50/p95 · `_boyut_tazele` çağrı sayısı ve boyut güncellemesinin öncesi/sonrası
değerleri.

EK-1 tanımları (recovery): **stabil kilit** (5 ardışık karede KİLİTLİ ve
IoU ≥ 0.5) · **recovery epizodu** · **başarılı recovery** · **false recovery** ·
**recovery süresi** (dağılım olarak; üst sınır eşiği tanımlı DEĞİL).

**A10'un eklediği üç ölçüm:**

1. **Doğrulama maliyeti** — ms/kare (dedektör çağrı süresi ÷ toplam kare) ve
   çağrı başına ms. Pi Zero 2 W'ye **ekstrapolasyon yapılmayacak**
   (`KALICI_KISITLAR.md`).
2. **Açık çevrim / kapalı çevrim farkı — her bileşen için ayrı.** Raporun
   **ana sorusu** budur (4T/4U dersi: açık çevrim ROC bir ÜST SINIRDIR).
   Yanına yazılacak açık çevrim üst sınırları:

| bileşen | açık çevrim üst sınırı | kaynak |
|---|---|---|
| doğrulayıcı | `min_G` AUC **0.895** (N=5) / 0.878 (N=10); `G ≤ 1.0` kapısında sağlam dizilerde ihlal oranı **0.480** | 3.2 §7 · 3.3 §3 |
| doğrulayıcı (k=1, N=10) | Mod B yakalama **3/4**, gecikme p50 6.0 kare; yanlış tetikleme %8.5 | 3.3 §9 |
| boyut çapası | A/B-3 tanısal zincir testi (boyut düzeltilirse zincirin kırıldığı ölçüldü) | A/B-3 §3 |
| recovery seçimi | KOL R, operasyonel referans, R=320: doğru **0.254** / yanlış 0.355 / çekimser 0.391 | 3.2 §1 |
| recovery tavanı | doğru aday havuzda **0.274**; 8×5'te kanıt yok **0.509** | 3.2 |

3. **SUSPECT'te tutmanın yan etkisi** — `_bagimsiz_dogrula`'nın koşmadığı kare
   sayısı ve H0'a göre `yanlis_kilit` sayacındaki fark (§3.1 uyarısı).

---

# 7. DEĞİŞECEK DOSYALAR

| dosya | değişiklik |
|---|---|
| **`takip/hakem.py`** | **YENİ** modül. Doğrulayıcı + boyut çapası + recovery. |
| **`takip/izleyici.py`** | **yalnızca hakem arayüzü**: opsiyonel `hakem` alanı ve `guncelle` sonunda tek bir çağrı. Diff raporda **satır satır** verilecek. |
| `gazebo/bench_a10_hakem.py` | YENİ koşum betiği (deney yatağı, `takip/` dışında) |

`hakem=None` iken davranış **birebir** H0 olmalıdır; bu bir **eşdeğerlik testi**
ile sınanacak (A/B-2 precedent'i): H0 kolu ile hakemsiz koşum aynı sayıları
vermeli.

---

# 8. YASAKLAR

eğitim · ağırlık değişikliği · `imgsz` · SAHI · Pi optimizasyonu · 5×5 ·
**sonuca göre sabit değiştirme** · yeni dizi/seviye ekleme (taban donduktan
sonra) · eşik ayarı.

---

# 9. ÇIKTI VE COMMIT

- Rapor: `docs/architecture/A10_HAKEM_KAPALI_CEVRIM.md`
- Veri: `cikti/a10_hakem.json`
- **Commit 1:** bu ön-kayıt + EK-1 (donmuş taban) + yeni dizi verisi
- **Commit 2:** hakem kodu + koşum betiği + sonuç + rapor
- **push YOK.**

Sonunda **DUR**: K1–K6 birlikte sağlanmadıkça `takip/hakem.py` kalıcılaştırılmaz
ve varsayılan davranış değişmez.

---

# EK-1 — UYGULANAN TABAN (kural yazıldıktan SONRA, mekanik)

**Tarih:** 2026-09-03 · **Kod:** `veri/a10_taban_sec.py` ·
**Veri:** `cikti/a10_taban_secim.json` · **Kaynak:** VisDrone2019-MOT-test-dev
(HuggingFace `vanthanh/VisDrone2019-MOT`), 17 dizi. Zip'in tamamı indirilmedi;
HTTP Range ile yalnızca gereken üyeler çekildi — **toplam 145 MB** (zip 2.29 GB).

## Tarama sonucu

| ölçüt | eleme |
|---|---|
| **Ö-A** (araç track'i) | 1 dizi elendi (088_00290: araç sınıfından track yok) |
| **Ö-B** (ilk 60 görünür ardışık) | 1 dizi elendi (073_00600: yalnızca 13 görünür kare) |
| **Ö-C** (kompozit yatak) | **14 dizi elendi** |
| **geçen** | **1 dizi: `uav0000370_00001_v` (track 0, 2720×1530)** |

Ö-C üç sebeple eliyor: native < 1280×720 (161, 188, 306) ya da hedef 60 karenin
tamamında **her** 1280×720 hücreyi ziyaret ediyor (kalan 11 dizi; 1360×765 ve
1904×1071 gibi tuvale ancak bir-iki hücre sığdıran çözünürlükler).

## Kural uygulandı, DEĞİŞTİRİLMEDİ

Ön-kayıt "ilk **3**"ü alacaktı; ölçüt yalnızca **1** dizi geçirdi.
**Ö-C gevşetilmedi.** Sonuca bakıp ölçüt değiştirmek §8'in açık yasağıdır.

## BULGU — mevcut tabanın YARISI Ö-C'yi geçmiyor

Ö-C aynı ölçütle mevcut 6 diziye de uygulandı:

| dizi | native | geçerli boş hücre |
|---|---|---|
| 117/23 | 2720×1530 | **(1280, 360)** ✓ |
| 137/12 | 2688×1512 | **(1280, 360)** ✓ |
| 268/31 | 3840×2160 | **(1920, 720)** ✓ |
| **182/127** | 1344×756 | **YOK** |
| **305/5** | 1904×1071 | **YOK** |
| **339/49** | 1904×1071 | **YOK** |

`bench_a52_kucuk_hedef.py:arkaplan_hucresi` geçerli hücre bulamazsa
`(en_iyi or (0, 0))` ile **sessizce (0,0)'a düşer**. Yani bu üç dizide A5.2'den
beri kullanılan kompozit arkaplan, **gerçek hedefi native boyutuyla içeriyor** —
yapıştırılan yamanın yanında.

> **Bu, A9'un çeldirici bulgularını doğrudan ilgilendirir.** 339/49, Mod B
> hücrelerinin 4'ünden 3'ünü veren dizidir ve arkaplanında gerçek araç
> duruyor olabilir. 3.2/3.3'ün "çeldirici" gözlemleri bu artefaktı taşıyor
> olabilir. **A10 bunu düzeltmez** (yatak dondu, geriye dönük değişiklik
> yasak) ama her hükmün yanında **YATAK ARTEFAKTI** etiketiyle taşınır.

## DONMUŞ TABAN — 7 dizi × 5 seviye = 35 hücre

| dizi | track | native | Ö-C | A9 rolü |
|---|---|---|---|---|
| uav0000117_02622_v | 23 | 2720×1530 | ✓ | KOPAN |
| uav0000268_05773_v | 31 | 3840×2160 | ✓ | KOPAN |
| uav0000339_00001_v | 49 | 1904×1071 | **artefakt** | KOPAN |
| uav0000137_00458_v | 12 | 2688×1512 | ✓ | sağlam |
| uav0000305_00000_v | 5 | 1904×1071 | **artefakt** | sağlam |
| uav0000182_00000_v | 127 | 1344×756 | **artefakt** | sağlam |
| **uav0000370_00001_v** | **0** | **2720×1530** | ✓ | **rolü A10'da ölçülecek** |

Yeni dizinin rolü (kopan/sağlam) **seçimden sonra** ölçülür ve H0 kolunda
raporlanır; seçimi etkilemedi.

**Taban bu haliyle DONDU.** A10 boyunca dizi/seviye eklenmeyecek, çıkarılmayacak.

---

# EK-2 — §3.1 Mod A kuralının SÜRÜM 2'si (koşumdan önce, sonuç görülmeden)

**Tarih:** 2026-09-03 · **Hiçbir A10 ölçümü koşulmadan yazıldı.** Sürüm 1
silinmedi; §3.1'deki tablo olduğu gibi duruyor.

## Neden değişti

Sürüm 1: *"ölçüm kaybı (`kayip > 0`) **veya** P konum izi artışı → LOST"*.

Bu kural, **kodun kendi tanımıyla çelişiyor**. `izleyici.py`'de `kayip`, PSR
eşiğinin altında kalan **her** karede artar ve tek bir zayıf kare bile onu 1
yapar; takipçinin kendi kuralı ise ARAMA'ya ancak `kayip > coast_kare` (**8**)
olunca geçer. `kayip > 0`'da LOST ilan etmek, geçici bir PSR düşüşünü
kopuş saymak ve her seferinde recovery tetiklemek demektir — K6'yı ölçmeden
önce ihlal ederdi.

**Bu gerekçe hiçbir A10 sonucuna dayanmıyor**; `izleyici.py:coast_kare`
sabitinin okunmasından geliyor.

## Sürüm 2 kuralı

| gözlem | karar | dayanağı |
|---|---|---|
| `tak.durum ∈ {ARAMA, KAYIP}` | **LOST** | takipçinin **kendi** ölçüm-kaybı eşiği (`kayip > coast_kare = 8`) zaten aşılmış |
| `iz(P[:2,:2]) > 8.0` | **LOST** | `Kalman.__init__` başlangıç kovaryansı `diag(4,4)` → iz 8.0 (mevcut sabit). A9 Aşama 2'nin yayımlanmış dağılımı: sağlam **p95 = 4.17**, Mod A **p50 = 245.9** — eşik sağlam p95'in üstünde, Mod A medyanının 30 kat altında |
| `kayip > 0` | **SUSPECT** (LOST değil) | tek zayıf ölçüm onay için yeterli değil, ama kopuş kanıtı da değil |
| aday yok | **durum değişmez** | sürüm 1 ile aynı |
| `min d_norm ≤ 1.0` | **ONAY** | sürüm 1 ile aynı |
| `min d_norm > 1.0` | **SUSPECT** | sürüm 1 ile aynı (k = 1) |

## Ek: recovery denemesi hangi sıklıkta

Sürüm 1 bunu tanımsız bırakmıştı. **Recovery denemeleri de N = 10 kadansında
yapılır** — yeni sabit üretmemek için, doğrulayıcıyla aynı ve tek ön-kayıtlı
kadans. Maliyet böylece üst sınırdan bağlanır.

## Ek: "son güvenilir kare" tanımı

Recovery referansı = **hakemin son ONAY verdiği karedeki takipçi merkezi ve
boyutu**. GT değildir; operasyoneldir. (Oracle kollar bunun yerine GT kullanır
ve **ÜST SINIR** etiketlidir.)

---

# EK-3 — Model kolu (koşumdan önce, sonuç görülmeden)

Sürüm 1 hangi dedektör ağırlığının kullanılacağını yazmamıştı. **A5_baseline**
kullanılacak; `A6_uavdt_visdrone` A10'da koşulmayacak.

**Gerekçe (yayımlanmış A9 ölçümü, A10 sonucu değil):** 3.3 §7 ölçtü — A6 bu
görevde kör: sağlam hücrelerde 130 doğrulama noktasının yalnızca **6**'sında
kanıt var, dört Mod B hücresinde 44 noktanın **3**'ünde. Kör bir dedektörle
kapalı çevrim kurmak, hakemi ölçmek yerine körlüğü ölçmek olurdu.

Bu bir **kapsam** kararıdır; A6'nın A10 altında nasıl davranacağı **ölçülmemiş**
kalır ve öyle raporlanır.
