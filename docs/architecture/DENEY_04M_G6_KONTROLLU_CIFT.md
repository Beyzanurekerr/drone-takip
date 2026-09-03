# Deney 4M — G6 kontrollü çifti: `G6_agresif_durakli` vs `G6_agresif`

**Salt okunur. `takip/` hiç değiştirilmedi** (md5 6/6 sabit), hiçbir eşik,
Kalman, DCF, şablon öğrenmesi, ego hesabı, açı/şekil/padding/`rafine_kutu`
ayarı değiştirilmedi, commit/push yok. Ölçüm aracı (yeni, yalnızca gözlem):
`gazebo/tani_g6_cift.py`. Çıktı: `cikti/g6_cift.json`.

4L'nin önerdiği tek teşhis adımı: *"kare 140–155 penceresinde ego kestirimini,
DCF tepesini ve KF artığını kare kare çıkar; `G6_agresif` ile aynı pencerede
karşılaştır."*

## 0. Kontrolün geçerliliği önce kanıtlandı

İki senaryo `senaryolar.py:_G6`'da **yalnızca hedef hız modülasyonunda**
farklıdır (3.0 vs 5.0 m/s); kamera, sahne, zemin, çeldirici aynıdır. Ölçümle
doğrulandı — ego'nun GT konumundaki ötelemesi (`ego_gt`) 10'ar karelik her
pencerede **0.01 px içinde aynı**:

| pencere | 10–19 | 40–49 | 90–99 | 120–129 | 130–139 | 140–149 | 150–159 |
|---|---|---|---|---|---|---|---|
| durakli | 6.80 | 9.68 | 13.41 | 15.10 | 13.59 | 11.02 | 8.26 |
| agresif | 6.79 | 9.68 | 13.40 | 15.09 | 13.58 | 11.02 | 8.25 |

GT kutu yüksekliği de birebir aynı (aracın görüntüdeki dönmesi ortak).
**Kamera kanalı bir değişken değil; çift gerçekten tek değişkenli.**

## 1. Boru hattı sırası (kod, grep ile doğrulandı)

```
1  ego.guncelle(gri, kutu)         -> M, ego_guven          izleyici.py:242
2  cekirdek.ego_guncelle(M)                                 izleyici.py:248
3  ongoru = M[:,:2] @ onceki + M[:,2]                       izleyici.py:255
4  kf.tahmin(M)                    -> KF ÖNGÖRÜSÜ           izleyici.py:264
5  boyut *= olcek                                           izleyici.py:265
6  cekirdek.ara(...)               -> DCF TEPESİ + PSR      izleyici.py:305
   kf.duzelt(yeni) | kf.sondur()   -> FİNAL                 izleyici.py:311/321/326
   cekirdek.ogren(...)             -> ŞABLON                izleyici.py:316
7  _bagimsiz_dogrula               -> _hareketli, benzerlik izleyici.py:276
```

Eşikler (`RenkDcfCekirdek`): `psr_kilit = 9.0`, `psr_supheli = 4.5`.

## 2. Hata **yön ayrıştırması** — sonucu belirleyen ölçüm

Ham merkez hatası yanıltıcıdır, çünkü görüntüdeki toplam akışın (13–17 px)
neredeyse tamamı kameradır. Hata, **hedefin KENDİ görüntü hareketi** ekseninde
ayrıştırıldı (birim vektör = `gt_şimdi − M(gt_önceki)`, yani `−ego_artik`):

* `ileri` < 0 → kutu hedefin **arkasında** (kendi hareket ekseninde geride)
* `yan` → o eksene dik bileşen

**Yan bileşen iki senaryoda da ±2 px içinde kalıyor. Hata tamamen
ALONG-TRACK (geride kalma).**

## 3. Kare kare çekirdek tablo (kare 136–152)

`ileri(x)` = x'in GT'ye göre along-track hatası. `artik` = DCF tepesi − KF
öngörüsü (along-track). Negatif artık = **DCF kutuyu daha da geriye çekiyor**.

### `G6_agresif_durakli`

| kare | ivme | ileri(final) | ileri(dcf) | ileri(kf) | **artık** | kf_hız | öz_hız | şablon | PSR | durum | IoU |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 136 | −6.3 | −6.50 | −6.59 | −6.31 | −0.29 | 2.10 | 2.82 | 0.050 | 19.8 | KILITLI | 0.68 |
| 137 | −6.6 | −7.19 | −7.30 | −6.95 | −0.35 | 1.99 | 2.62 | 0.054 | 20.7 | KILITLI | 0.66 |
| 138 | −7.1 | −7.92 | −7.92 | −7.91 | −0.02 | 1.98 | 2.65 | 0.050 | 23.9 | KILITLI | 0.64 |
| 139 | −6.9 | −8.33 | −8.32 | −8.35 | +0.04 | 2.00 | 2.46 | 0.047 | 26.0 | KILITLI | 0.64 |
| 140 | −7.1 | −8.57 | −8.52 | −8.66 | +0.13 | 2.04 | 2.36 | 0.045 | 27.6 | KILITLI | 0.63 |
| 141 | −7.6 | −8.77 | −8.72 | −8.88 | +0.15 | 2.09 | 2.32 | 0.045 | 27.3 | KILITLI | 0.61 |
| **142** | −7.4 | −9.76 | −10.13 | −8.99 | **−1.14** | 1.74 | 2.33 | 0.047 | 25.7 | KILITLI | 0.58 |
| **143** | −7.5 | −11.39 | −11.98 | −10.19 | **−1.78** | **1.21** | 2.12 | 0.058 | 24.8 | KILITLI | 0.54 |
| **144** | −7.9 | −13.26 | −13.65 | −12.45 | **−1.20** | 0.89 | 2.17 | 0.071 | **19.2** | KILITLI | 0.50 |
| **145** | −7.7 | −15.45 | −15.87 | −14.58 | **−1.29** | 0.64 | 2.03 | 0.097 | **15.7** | KILITLI | 0.45 |
| 146 | −7.7 | −17.03 | −17.05 | −17.01 | −0.04 | 0.52 | 1.86 | **0.127** | **10.5** | KILITLI | 0.42 |
| **147** | −8.7 | −18.34 | −18.04 | −18.44 | +0.40 | 0.51 | 1.67 | — | **6.7** | **SUPHELI** | 0.39 |
| **148** | −7.1 | −29.99 | **−45.39** | −19.82 | **−25.56** | 3.87 | 1.79 | — | 7.9 | SUPHELI | 0.25 |
| 149 | −8.1 | −46.09 | −48.07 | −35.53 | −12.54 | 7.61 | 1.64 | 0.124 | 11.1 | KILITLI | **0.09** |
| 150 | −7.7 | −53.66 | −52.95 | −55.20 | +2.24 | 6.92 | 1.58 | 0.113 | 13.4 | KILITLI | 0.03 |
| **151** | −7.6 | −58.04 | −56.20 | −61.88 | +5.68 | 5.06 | 1.46 | 0.105 | 13.4 | KILITLI | **0.00** |

### `G6_agresif` (kontrol)

| kare | ivme | ileri(final) | ileri(dcf) | ileri(kf) | **artık** | kf_hız | öz_hız | şablon | PSR | durum | IoU |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 136 | −3.8 | −4.67 | −4.89 | −4.23 | −0.66 | 1.77 | 2.39 | 0.024 | 31.3 | KILITLI | 0.79 |
| 138 | −4.2 | −6.42 | −6.58 | −6.08 | −0.50 | 1.50 | 2.37 | 0.026 | 26.0 | KILITLI | 0.71 |
| 140 | −4.3 | −8.18 | −8.24 | −8.08 | −0.16 | 1.35 | 2.09 | 0.034 | 20.2 | KILITLI | 0.65 |
| **141** | −4.6 | −8.72 | −8.63 | −8.92 | **+0.29** | 1.44 | 2.08 | 0.036 | 20.4 | KILITLI | 0.63 |
| **142** | −4.4 | −8.99 | −8.82 | −9.35 | **+0.53** | 1.61 | 2.11 | 0.035 | 22.2 | KILITLI | 0.61 |
| **143** | −4.5 | −9.01 | −8.84 | −9.35 | **+0.51** | 1.78 | 1.96 | 0.035 | 24.0 | KILITLI | 0.60 |
| **144** | −4.8 | −9.02 | −8.90 | −9.26 | **+0.36** | 1.89 | 2.04 | 0.035 | 24.6 | KILITLI | 0.59 |
| 145 | −4.6 | −9.14 | −9.20 | −9.01 | −0.19 | 1.83 | 1.92 | 0.034 | 25.6 | KILITLI | 0.57 |
| 146 | −4.6 | −9.54 | −9.75 | −9.11 | −0.65 | 1.62 | 1.81 | 0.036 | 24.8 | KILITLI | 0.55 |
| 147 | −5.2 | −9.74 | −9.94 | −9.34 | −0.60 | 1.42 | 1.64 | 0.037 | 24.4 | KILITLI | 0.53 |
| 148 | −4.3 | −10.62 | −10.76 | −10.33 | −0.43 | 1.28 | 1.83 | 0.038 | 23.0 | KILITLI | 0.53 |
| 150 | −4.6 | −11.21 | −11.13 | −11.37 | +0.23 | 1.31 | 1.70 | 0.049 | 18.2 | KILITLI | **0.56** |
| 151 | −4.6 | −10.86 | −10.60 | −11.38 | +0.78 | 1.56 | 1.61 | 0.055 | 16.3 | KILITLI | **0.58** |

**Kare 141'de iki senaryo neredeyse aynı yerdedir: gecikme −8.77 vs −8.72 px.**
Ayrışma bir sonraki karede başlar.

DCF artığının pencere ortalaması (along-track):

| pencere | durakli | agresif |
|---|---|---|
| 120–135 | −0.514 ± 0.585 | −0.735 ± 0.950 |
| 136–141 | −0.055 ± 0.196 | −0.277 ± 0.299 |
| **142–146** | **−1.090 ± 0.572** | **+0.111 ± 0.461** |

142–146 penceresinde dağılımlar **örtüşmüyor**: durakli'de DCF ölçümü kutuyu
her karede ~1.1 px daha **geriye** çekiyor, agresif'te ~0.1 px **ileriye**.

## 4. Sorulara tek tek yanıt

### A) Aynı kamera altında hangi değişken ayrışıyor?
**DCF artığının işareti** (kare 142). Ondan önce ego (`ego_gt` 0.01 px içinde
aynı, `ego_artik` 2.0–2.9 px ve **azalıyor**), gecikme (−8.7/−8.8), GT kutu
geometrisi ve kutu boyutu iki senaryoda da aynı.
Daha yavaş bir **öncül** de var: durakli kare ~120'den itibaren sistematik
olarak daha dar PSR marjıyla ve ~2× şablon çalkantısıyla ilerliyor
(130–139 pencere ortalaması: PSR 23.6 vs 35.0, şablon 0.04 vs 0.02). Bu bir
tetikleyici değil, **marj farkı**.

### B) DCF tepe hatası kopuştan ÖNCE mi büyüyor?
**Evet, ama tek başına ayırt edici değil.** `ileri(dcf)` her iki senaryoda da
kare 126'dan itibaren büyüyor (−2.8 → −8.7). Ayırt edici olan büyüklük değil,
**142'den sonra DCF'in düzeltme yönü**: durakli'de geriye, agresif'te ileriye.

### C) KF artığı kopuştan önce olağandışı büyüyor mu?
**Evet — 5 kare önce.** 136–141'de |artık| ≤ 0.35 px; 142–145'te 1.14–1.78 px
(3–5×) ve **hepsi aynı işaretli**. Kontrolde aynı pencerede 0.19–0.53 px ve
işaret ters. Bu, kopuşun (147) ve YK'nın (151) öncesindedir.

### D) Ego uygulanmış / uygulanmamış merkez farkı kopuşta sıçrıyor mu?
**Hayır.** `ego_artik` (ego telafisinden artakalan) 136→147 arasında durakli'de
2.65 → 1.67 px, yani **azalıyor**; agresif'te 2.37 → 1.64. Ego'nun taşıdığı
öngörü hatası (`ego_ongoru_hata`) her karede ego'suz hatadan (`egosuz_hata`)
**küçüktür** (ör. kare 145: 15.29 vs 17.25) — ego telafisi doğru yönde
çalışıyor. Kopuşta ego kaynaklı bir sıçrama **yok**.

### E) DCF tepesi doğruyken hata ego/KF sonrasında mı oluşuyor?
**Hayır — tam tersi.** `final − dcf` farkı kopuş penceresinde −0.4 px
düzeyinde; KF, DCF'in verdiği yeri neredeyse aynen kabul ediyor
(kazanç ~0.67). Hata **DCF ölçüm aşamasında doğuyor**, KF ve ego yalnızca
taşıyor. (Kare 148'in tek istisnası: KF, 25.6 px'lik sıçramanın yalnızca
%40'ını geçiriyor — SUPHELI dalının `r_carpan=6` frenlemesi.)

### F) Yavaşlama miktarı ile merkez hatası arasında ilişki var mı?
Pencere düzeyinde **var**: 140–149'da ivme −7.68 vs −4.61 m/s², along-track
hata −17.86 vs −9.40 px. **Ama nedensel değil** — bkz. (H) altındaki senaryo
içi kontrol: aynı dizide aynı büyüklükte (−7…−10 m/s²) bir yavaşlama sorunsuz
geçiliyor.

### G) `G6_agresif`'te neden aynı kopuş olmuyor?
Aynı gecikme orada da birikiyor (−8.7 px) ama **kendini düzeltiyor**: kare
141'den itibaren DCF artığı pozitif (+0.29…+0.51), KF hızı 1.35 → 1.89'a
toparlıyor, gecikme −9…−11 px'te **doyuyor**, PSR 20.2 → 25.6'ya yükseliyor.
IoU 0.79 → 0.53'e iner ve **geri toparlar** (150–151'de 0.56 → 0.58); kilit hiç
kaybolmuyor (tüm koşumda kilit %100, YK %0).

### H) "Duruş + çapraz kamera" hipotezi destekleniyor mu?
**Hayır — üç bağımsız gerekçeyle reddedildi.**

1. **Kamera aynı ve kontrolde kopuş yok.** `ego_gt` iki senaryoda 0.01 px
   içinde aynı; `G6_agresif` aynı kamerayla 300 karede hiç yanlış kilit
   üretmiyor.
2. **Kopuş anında araç durmuş değil.** 142–148 arasında hedef hızı
   6.1 → 4.6 m/s. Araç ancak kare 168'de 0.5 m/s'nin altına iniyor —
   **kopuştan 26 kare sonra**, IoU zaten 0 olduktan 17 kare sonra.
3. **SENARYO İÇİ KONTROL — belirleyici olan bu.** Aynı dizide **ilk**
   yavaşlama (kare 20–50) en az bu kadar serttir (−7…−10 m/s²) ve araç
   **0.07 m/s'ye kadar tam duruyor** — yine aynı çapraz kamerayla. Sonuç:

   | kare | hız | ivme | ileri | artık | PSR | IoU | kutu h / GT h |
   |---|---|---|---|---|---|---|---|
   | 22 | 5.83 | −8.5 | −7.65 | −1.14 | 28.1 | 0.73 | 36 / 39 |
   | 30 | 3.77 | −8.0 | −2.75 | +0.09 | 36.5 | 0.87 | 35 / 35 |
   | 36 | 2.34 | −10.2 | −3.29 | −1.17 | 35.4 | 0.82 | 35 / 31 |
   | 44 | 0.78 | −5.0 | −2.21 | −0.88 | 31.8 | 0.76 | 32 / 26 |
   | 50 | **0.07** | −2.7 | **+1.06** | −0.10 | 31.2 | **0.95** | 29 / 29 |
   | 62 | **0.01** | −1.4 | **+0.97** | +0.16 | 36.3 | 0.86 | 32 / 35 |

   Gecikme −1…−7.7 px arasında **sınırlı kalıyor ve işaret değiştirerek
   düzeliyor**; artık ortalaması ≈ 0. Duruş ve sert yavaşlama **birlikte**
   sunuldu ve **geçildi**.

Yani hipotezin her iki bileşeni de tek tek ve birlikte yanlışlandı.

## 5. Kopuşun ZAMANSAL sırası (kare kare)

| # | kare | olay | kanıt |
|---|---|---|---|
| 0 | ~120–141 | **öncül**: durakli daha dar PSR marjı ve ~2× şablon çalkantısıyla ilerliyor | 130–139 ort. PSR 23.6 vs 35.0; şablon 0.04 vs 0.02 |
| 0b | 126–141 | along-track gecikme **iki senaryoda da** birikiyor | 141'de −8.77 vs −8.72 |
| 0c | 134–138 | `rafine_kutu` **iki senaryoda da** ölüyor (son başarı: durakli kare 130, agresif kare 134); kutu yüksekliği 36.3/35.1'de donuyor, GT 30.6 → 26.1'e iniyor | tazele başarısı 120–139: 3/5 ve 4/5 → **140–179: 0/10 ve 0/10** |
| **1** | **142** | **İLK AYRIŞMA — DCF artığı işaret değiştiriyor**: −1.14 px (geri) vs +0.53 px (ileri) | 142–146 ort. −1.090 ± 0.572 vs +0.111 ± 0.461 |
| 2 | 143 | KF hızı kontrolün altına düşüyor (1.21 vs 1.78) ve çöküyor | hedefin öz görüntü hızı hâlâ ~2.1 px/kare |
| 3 | 143–146 | şablon çalkantısı fırlıyor 0.058 → 0.127 (kontrol düz 0.035) | `‖ΔA‖/‖A‖` |
| 4 | 144 | PSR kontrolün altına iniyor (19.2 vs 24.6) ve çöküyor | 146'da 10.5 |
| 5 | **147** | PSR 6.7 < `psr_kilit` 9.0 → **SUPHELI** | `r_carpan` 1.0 → 6.0 |
| 6 | **148** | DCF tepesi **25.6 px geriye sıçrıyor** (yol yamasına) | `ileri(dcf)` −45.4 |
| 7 | 149 | PSR 11.1 ≥ 9.0 → yanlış yerde yeniden **KILITLI** | hata 46 px |
| 8 | **151** | **IoU = 0 → yanlış kilit başlıyor** | 4L: 115 karelik epizot |

Sıra nettir: **ölçüm yönü → KF hızı → şablon → PSR → durum → sıçrama → YK.**
Aradaki mesafe: ilk ayrışma ile kilidin kaybı arasında **5 kare**, YK'nın
başlamasına **9 kare** var.

## 6. Ne kanıtlandı, ne kanıtlanmadı

**Kanıtlandı**
* Hata **DCF ölçüm aşamasında** doğuyor; ego ve KF yalnızca taşıyor (D, E).
* Kopuştan **önce** ve kontrolde **bulunmayan** bir boru hattı ayrışması var:
  DCF artığının işareti, kare 142 (C).
* Hata **along-track**; yanal bileşen ±2 px'te kalıyor.
* Kamera bir değişken değil (ego kanalı 0.01 px içinde özdeş).
* "Duruş" bir neden değil (senaryo içi kontrol).

**Kanıtlanmadı**
* Yavaşlama büyüklüğünün **nedensel** olduğu. Pencere düzeyinde ilişkili
  (F) ama senaryo içi kontrol (H.3) bunu tek başına yeterli olmaktan
  çıkarıyor. İki senaryo, tek bir eksende nedensellik kurmaya yetmez.
* Donmuş/büyük kutunun (0c) tetikleyici olduğu. **Gerekli görünen bir ön
  koşul** — iki senaryoda da tam olarak kopuş penceresinden önce oluşuyor —
  ama kontrolde de var ve kontrol kopmuyor, yani **yeterli değil**.
* DCF artığının neden işaret değiştirdiği. Ölçüldü, **açıklanmadı**.

**Yan gözlem (zayıf, karar dayanağı değil):** `G6_yumusak` aynı pencerede
hızlanma fazındadır (ivme +1.8), gecikmesi −3…−6.5 px arasında salınıp
düzelir, PSR 35–44, şablon 0.016–0.022, hiç kopmaz. Faz farklı olduğu için
kare-kare karşılaştırılamaz; yalnızca "sınırlı gecikme + sağlıklı PSR"
tablosunun üçüncü bir örneği olarak kaydedildi.

## 7. Bu turda ne yapılmadı

Hiçbir optimizasyon, hiçbir eşik/Kalman/DCF/şablon/ego/açı/şekil/padding/
`rafine_kutu` değişikliği, hiçbir commit veya push. `takip/` dosyalarının
md5'leri deney öncesi ve sonrası aynıdır.

---

# SONUÇ

**1. Kopuştan önce ilk bozulan değişken**
**DCF artığının along-track işareti**, kare **142** — kilidin kaybından
(147) 5, yanlış kilidin başlamasından (151) 9 kare önce. 142–146'da durakli
−1.090 ± 0.572 px (kutuyu geriye çekiyor), kontrol +0.111 ± 0.461 px (ileriye
çekiyor); dağılımlar örtüşmüyor. Kare 141'e kadar iki senaryo aynı yerdedir
(gecikme −8.77 vs −8.72 px).
*Daha yavaş bir öncül:* kare ~120'den beri durakli daha dar PSR marjıyla
(23.6 vs 35.0) ve ~2× şablon çalkantısıyla ilerliyor.

**2. Hatanın başladığı boru hattı aşaması**
**DCF ölçümü** (`cekirdekler.py` → `ara`, izleyici.py:305). Ego değil:
`ego_artik` kopuşta azalıyor ve ego uygulanmış öngörü her karede ego'suzdan
daha iyi. KF değil: `final − dcf` ≈ −0.4 px, KF ölçümü neredeyse aynen kabul
ediyor. Ön koşul, kopuş penceresinden hemen önce **`rafine_kutu`'nun iki
senaryoda da ölmesi** (son başarı kare 130 / 134; 140–179 arasında 0/10) ve
kutu yüksekliğinin
36.3'te donarken GT'nin 26.1'e inmesi.

**3. `G6_agresif` ile temel fark**
Aynı gecikme orada da birikiyor ama **kendini düzeltiyor**: DCF artığı kare
141'den itibaren pozitif, KF hızı 1.35 → 1.89 toparlıyor, gecikme −9…−11
px'te doyuyor, PSR 20.2 → 25.6 yükseliyor, IoU 0.53'te dip yapıp 0.58'e
toparlıyor, kilit hiç kaybolmuyor. Fark
"kopar/kopmaz" değil, **düzeltme yönünün işareti**.

**4. "Duruş + çapraz kamera" hipotezi: REDDEDİLDİ**
Kamera iki senaryoda 0.01 px içinde özdeş ve kontrol kopmuyor; kopuş anında
araç 4.6–6.1 m/s'de; ve aynı dizinin **ilk** duruşu (kare 20–50, ivme
−7…−10 m/s², hız 0.07 m/s'ye kadar) aynı kamerayla IoU 0.76–0.95 ile sorunsuz
geçiliyor. Buna karşılık, 4L'nin asıl sorusu olan *"kopuştan önce kontrolde
bulunmayan bir boru hattı ayrışması var mı?"* sorusunun yanıtı **evet**
(madde 1) — yani kopuş teşhis edilebilir, ama nedeni duruş değil.

**5. Bir sonraki TEK aday**

> **`rafine_kutu`'nun kare 134–179 arasında neden her çağrıda başarısız
> olduğunu salt okunur teşhis et** (iki senaryoda da 0/10; `tespit.py`
> `rafine_kutu`'nun `None` döndürdüğü dal kare kare çıkarılır ve GT kutusuyla
> karşılaştırılır).
> Gerekçe: bu, açıdan ve şekilden **bağımsız tek geometri ölçümüdür** ve
> kopuş penceresinden hemen önce ölmektedir; öldükten sonra kutu bir daha
> küçülemez ve DCF penceresi giderek yola dolar. Deney 1/3/4A'nın ortak
> dersi de aynı yeri gösteriyor: *bir sonraki aday ölçümün YERİNE geçmemeli,
> ölçümü HIZLANDIRMALI.* Bu teşhis olmadan "DCF artığı neden işaret
> değiştiriyor" sorusu açıklanamaz — şu an yalnızca ölçülmüş durumda.

**Bu bir öneridir, uygulanmadı. Bu turda hiçbir optimizasyon yapılmadı.**
