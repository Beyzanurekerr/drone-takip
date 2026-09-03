# A9 — Takipçi merkez güveni, kopuş tespiti ve yeniden edinme

> ## ⚠ KİRLİ YATAK UYARISI (2026-09-03, A10.1/D1'den sonra eklendi)
>
> A9'un bütün ölçümleri, `arkaplan_hucresi`'nin geçerli boş hücre bulamayınca
> sessizce **(0,0)**'a düştüğü bir yatakta yapıldı. Üç dizide (**339/49 ·
> 305/5 · 182/127**) o hücre hedefi içeriyor: kompozit arkaplan **gerçek
> hedefi native boyutuyla** taşıyor. 30 hücrenin **15'i** bu koşulda ölçüldü.
>
> D1 yatağı düzeltip A9'un üç ölçümünü yeniden koştu
> (`A10_1_D1_TEMIZ_YATAK.md`). **Sağ kalmayan bulgular aşağıda
> `KİRLİ YATAK` etiketiyle işaretlendi; hiçbiri silinmedi.**
> En önemlisi: `G ≤ 1.0` kapısının **%48 yanlış alarmı** temiz yatakta
> **%0**'dır — Deney 3.3'ün tamamı o sayının üstüne kuruluydu.

**Kod:** `gazebo/tani_a9_merkez.py` (yeni, salt okunur) · **Veri:** `cikti/a9_takipci_merkez_recovery.json`

Bu belge aşamalı yazılır. Her aşamanın sonunda DUR uygulanır.

| aşama | durum |
|---|---|
| **1 — Merkez güveni teşhisi** | **TAMAMLANDI** (2026-09-02) · 1-EK, 1b, A/B-1, A/B-2, A/B-3 dahil — **beş A/B de reddedildi** |
| **2 — Kopuş tespiti** | **TAMAMLANDI** (2026-09-02) · teşhis; eşik seçilmedi |
| **3 — Yeniden edinme** | **Deney 3.0 · 3.1 · 3.2 · 3.3 koşuldu** · state machine **KURULMADI** (3.1 önermenin çalışmadığını gösterdi) |
| 4 — Adaptif ROI kapalı çevrim | başlanmadı |
| 5 — Boyut tahmini | başlanmadı |

*(Bu tablo 2026-09-03'te güncellendi; 3.2 sonrası bayat kalmıştı — gövdedeki
bölümler tabloyla çelişiyordu.)*

---

# 0. İstem denetimi — eklenen maddeler

A9 istemi uygulanmadan önce denetlendi. Bulunan eksikler ve kapsama eklenenler:

**E1 — Aşama 1 ile Aşama 5 ayrılabilir değil.** İstem "önce merkez, sonra boyut"
sıralaması öngörüyordu. Ama `izleyici.py:566-567`:

```python
if norm(yeni_c - self.kf.konum) < 0.6 * self.boyut.max():
    self.kf.duzelt(yeni_c, r_carpan=1.0)      # _boyut_tazele MERKEZE tam ağırlıkla yazıyor
```

Boyut yolu merkeze **tam ağırlıkla** yazıyor ve kapısı `self.boyut`'a — yani kendi
bozduğu büyüklüğe — bakıyor (4U dersinin altıncı tekrarı). Aşama 1 bu yüzden merkeze
yazan **üç yolu birden** ayrıştıracak biçimde tasarlandı. *(Aşama 1 sonucu bu maddeyi
haklı çıkardı — §5.)*

**E2 — Ego kanalı bu yatakta ölçülemez sanılıyordu.** A5.2 kompoziti arkaplan penceresini
sabit tutar, yani gerçek ego = 0. Bu iddia edilmedi, **ölçülüp sınandı** — ve sonuç
beklenenin tersi çıktı (§6).

**E3 — Kabul ölçütü yok.** Projede precedent var (`A3.9C_KABUL_OLCUTU.md`,
`D1_kabul_olcutu.md`). Eşik, sonuçlar görüldükten sonra seçilirse eşik iyimserliği
tuzağına düşülür. **Aşama 2'ye geçmeden önce ayrı bir kabul ölçütü bölümü yazılacak.**

**E4 — Karar tabanı fiilen tek dizi.** 117/23 patolojik (Deney 4L: "bir uçurumun 1 px
yanında"), 305/5 A5 kolunda baştan sona ölü (A7 ve A8 aynı sonucu verdi). Geriye 137/12
kalıyor. **Açık soru: "yeni veri seti ekleme yok" yasağı, VisDrone VID içinden yeni
DİZİ eklemeyi de kapsıyor mu?** Aşama 1 buna bağlı değildi; Aşama 3'ün kabul ölçütünden
önce karara bağlanmalı.

**E5 — Recovery'de yanlış-kilit ölçümü zorunlu değildi.** 117/23'te çeldirici araç aynı
görüntü satırında 1.5 px'e kadar yaklaşıyor (Deney 4P). Başarı ölçütü "kilide döndü"
değil **"DOĞRU hedefe döndü"** olmalı. *(Aşama 1 bunun ne kadar kritik olduğunu
gösterdi — §7.)*

**Küçük eklemeler:** "stabil kilit" sayısal tanımı · salt-okunur enstrümantasyon yöntemi
(§1) · her yeni yöntem için CPU maliyeti + ölçülmemiş kalemler (KALICI_KISITLAR.md kuralı) ·
her tabloya açık/kapalı çevrim etiketi · aşama başına ayrı JSON anahtarı · Kalman
kovaryansı `P` durum sözlüğünde dönmüyor, `kf.P` üzerinden okunuyor.

---

# AŞAMA 1 — Takipçi merkez güveni teşhisi

**Tarih:** 2026-09-02 · **Bu turda:** eşik değişmedi · takipçi davranışı değişmedi ·
yeni mekanizma eklenmedi · YOLO hiç koşmadı · commit/push yok.

**Bütünlük:** `takip/*.py` **6/6 md5 aynı** · `gazebo/bench_a52_kucuk_hedef.py`
`45623cc5…` değişmedi. Değişen tek şey yeni salt-okunur dosya `gazebo/tani_a9_merkez.py`.

**Tüm ölçümler AÇIK ÇEVRİMDİR** — dedektör yok, takipçi kendi başına koşuyor.

## 1. Enstrümantasyon — `takip/` neden değişmedi

Merkeze yazan her yol `Kalman` üzerinden geçtiği için, takipçinin `kf` nesnesi
kilitlemeden sonra **kayıt yapan bir sarmalayıcıyla** değiştirildi. Sarmalayıcı hiçbir
değeri değiştirmez; yalnızca her `tahmin` / `duzelt` / `ata` / `sondur` çağrısında
çağıran fonksiyonun adını yığından okuyup merkez değişimini kaynağına atfeder.

**Atfetme ölçütü:** `katkı = |konum_sonra − GT| − |konum_önce − GT|`.
Pozitif = o aşama merkezi GT'den uzaklaştırdı.

## 2. Merkeze yazan yollar (kodda okundu)

| kaynak | yer | ne yapar |
|---|---|---|
| `guncelle:tahmin` | `izleyici.py:263` | ego dönüşümü + sabit-hız yayılımı |
| `_takip_adimi:duzelt` | `izleyici.py:312 / 327` | DCF tepesi (tam / zayıf güven) |
| `_takip_adimi:sondur` | `izleyici.py:332` | ölçüm reddedildi, hız söndürüldü |
| `_boyut_tazele:duzelt` | `izleyici.py:567` | rafine kutu merkezi, **tam ağırlık** |
| `_arama_adimi:ata` | `izleyici.py:525` | yeniden yakalama, doğrudan atama |

## 3. Ana tablo — merkez hatası ve mevcut sinyaller

*(açık çevrim · 59 kare · sensör 1280×720)*

| dizi | seviye | hata p50 | hata p95 | PSR p50 | **P konum izi p95** | DCF kabul/red | kopuş karesi |
|---|---|---|---|---|---|---|---|
| **117/23** | 40×15 | 6.8 | 13.9 | 29.7 | 14.6 | 59/0 | — |
| | 30×12 | 9.9 | 21.0 | 21.4 | 10.5 | 59/0 | — |
| | 20×10 | **210.3** | **380.5** | **4.5** | **36 259** | 14/5 | **13** |
| | 15×7 | **139.0** | **434.9** | **2.7** | **30 632** | 15/6 | **12** |
| | 10×5 | **143.7** | **607.2** | **3.8** | **68 985** | 18/19 | **12** |
| | 8×5 | **110.6** | **150.6** | *31.2* | *58.7* | 51/3 | **12** |
| | 5×5 | **116.6** | **189.0** | 3.9 | 732 | 19/29 | **11** |
| **137/12** | 20×10 | 1.1 | 5.1 | 76.2 | 3.41 | 59/0 | — |
| | 10×5 | 0.8 | 2.6 | 76.9 | 3.41 | 59/0 | — |
| | 5×5 | 0.7 | 1.3 | 51.3 | 3.41 | 59/0 | — |
| **305/5** | 20×10 | 8.2 | 14.0 | 46.4 | 3.41 | 59/0 | — |
| | 5×5 | 0.6 | 1.4 | 46.9 | 3.41 | 59/0 | — |

**137/12 ve 305/5 hiçbir seviyede kopmuyor** — 5×5'te bile merkez hatası p95 = 1.3–1.4 px.
Tüm çöküş 117/23'e ait ve **30×12 ile 20×10 arasında keskin bir eşikten** geçiyor.

## 4. Nedensel zincir — 117/23 · 20×10, kare kare

| t | hata | Δhata | PSR | durum | boyut | bho | P izi | olaylar (katkı px) |
|---|---|---|---|---|---|---|---|---|
| 10 | 5.0 | −2.0 | 13.8 | KİLİTLİ | 50.4 | 1.26 | 3.3 | tahmin(−0.8) · DCF(−1.2) |
| 11 | 5.4 | +0.1 | 7.5 | ŞÜPHELİ | 50.4 | 1.26 | 7.7 | tahmin(+0.8) · DCF(−0.7) |
| **12** | **19.2** | **+13.8** | 5.9 | ŞÜPHELİ | **72.6** | **1.82** | 3.5 | tahmin(+5.6) · DCF(−3.7) · **`_boyut_tazele`(+11.9)** |
| 13 | 26.8 | +7.2 | 2.9 | ŞÜPHELİ | 72.9 | 1.82 | 10.1 | tahmin(**+7.2**) · **söndür** |
| 14 | 34.9 | +9.8 | 1.9 | ŞÜPHELİ | 73.1 | 1.83 | 24.9 | tahmin(**+9.8**) · **söndür** |
| 15 | 44.8 | +11.6 | 2.6 | ŞÜPHELİ | 73.4 | 1.84 | 51.5 | tahmin(**+11.6**) · **söndür** |
| 16 | 55.1 | +11.7 | 4.1 | ŞÜPHELİ | 73.7 | 1.84 | 93.3 | tahmin(**+11.7**) · **söndür** |
| 18 | 81.2 | +12.9 | 4.3 | ŞÜPHELİ | 74.2 | 1.86 | 42.1 | tahmin(**+12.9**) · **söndür** |
| 19 | 110.4 | +30.4 | 4.5 | ARAMA | 74.6 | 1.86 | 21.1 | tahmin(+12.8) · DCF(+17.6) |
| 20 | 126.3 | +17.6 | 4.5 | ARAMA | 74.9 | 1.87 | 37.4 | tahmin(**+17.6**) |

**Zincir:**

1. **t=12 — `_boyut_tazele` yaralıyor.** Boyutu 50.4 → 72.6'ya (bho 1.26 → 1.82) şişiriyor
   **ve merkezi 11.9 px kaydırıyor.** O karenin tek büyük katkısı bu.
2. **Şişmiş kutu DCF'yi bozuyor** — PSR 7.5 → 2.9'a çöküyor.
3. **Ölçüm reddediliyor** (`söndür`), Kalman ölü hesaba düşüyor.
4. **`guncelle:tahmin` her kare +7…+18 px ekliyor, tekdüze.** Düzeltecek ölçüm yok.
5. Hata kaçıyor, takipçi ARAMA'ya giriyor.

> **İlk neden `_boyut_tazele`'dir, merkez değil.** İstemin "önce merkez, sonra boyut"
> sıralaması ölçümle ters düşüyor: merkez arızası boyut arızasının **sonucudur**.
> Bu, `_boyut_tazele`'nin A3.9'da boyut hatasının kaynağı olarak tespit edilmesiyle
> aynı yönde — ama A9 aynı fonksiyonun **merkezi de** bozduğunu gösteriyor.

**Sınanan hipotez H1 (sıçrama kapısı gevşemesi) — 20×10'da DOĞRULANMADI.**
`maks_sicrama = max(6.0, 0.9·boyut.max())` (izleyici.py:309) bozuk boyuta bakıyor, ama
20×10'da gevşek kapı sayısı **0**; kopuş kapıdan değil ölçüm kaybından geliyor.
*(8×5'te durum farklı — §5.)*

## 5. İki AYRI arıza modu

| | **Mod A — ölçüm kaybı** | **Mod B — güvenli yanlış kilit** |
|---|---|---|
| seviyeler | 20×10, 15×7, 10×5, 5×5 | **8×5** |
| PSR | **çöküyor** (2.7–4.5) | *yüksek* (31.2, kilit anında **99**) |
| P konum izi | **patlıyor** (30 632 – 68 985) | *düşük* (58.7) |
| DCF kabul/red | 14/5 … 19/29 | 51/3 |
| gevşek kapı | 0–5 | **37 / 51** |
| mekanizma | ölçüm yok → ölü hesap → kaçış | şişmiş kapı yanlış tepeleri kabul ediyor |

**Mod B'nin kritik karesi** (117/23 · 8×5, t=24): `_arama_adimi:ata` GT'den **151 px**
uzağa kilitleniyor — **PSR = 99** (doygun), **benzerlik = 1.00**, **yanlış_kilit = 0**.
Yani en yüksek güvenle yanlış hedefte.

> **PSR bu modda yalnızca işe yaramıyor, aktif olarak YANILTIYOR.**

## 6. Ego kanalı — beklenenin tersi çıktı

Yatakta arkaplan penceresi sabit, yani **gerçek ego = 0**. Ölçülen:

| dizi | \|t\| p50 | \|t\| p95 | \|A−I\| p95 | saf ego p95 |
|---|---|---|---|---|
| **117/23** | **5.50** | **16.91** | 0.0079 | **18.62** |
| 137/12 | 2.87 | 3.58 | 0.0019 | 2.92 |
| 305/5 | 1.91 | 2.22 | 0.0023 | 1.38 |

**Ego katmanı 117/23'ün arkaplanında kare başına ~17–19 px sahte hareket üretiyor**
(doğru cevap 0), diğer iki dizide 1.4–2.9 px. Ve bu **her seviyede sabit** — 40×15'te de
aynı. Sağlıklı seviyelerde zararsız, çünkü DCF her kare düzeltiyor (59/59 kabul).
Ölçüm kesildiği anda **aynı sahte ego kaçışın yakıtı oluyor** (§4, adım 4).

> Bu, A8'de ego kolunu "yatakta ego yok" diye düşürmemi kısmen çürütüyor: ego **yok
> değil, YANLIŞ**. Faz B'nin "ego-motion katmanı sağlam" bulgusu Gazebo'da alınmıştı;
> VisDrone kompozit arkaplanında 117/23 için geçerli değil.

## 7. Mevcut savunmaların durumu

| dizi | seviye | KİLİTLİ | ŞÜPHELİ | ARAMA | KAYIP | benzerlik min | yanlış_kilit |
|---|---|---|---|---|---|---|---|
| 117/23 | 40×15 (sağlam) | 48 | 11 | 0 | 0 | **1.00** | 0 |
| 117/23 | 20×10 (kopuk) | 6 | 12 | 27 | 14 | **1.00** | 0 |
| 117/23 | 8×5 (kopuk) | 42 | 12 | 5 | 0 | **1.00** | 0 |
| 137/12 | hepsi | **59** | 0 | 0 | 0 | 0.50–0.91 | 0 |
| 305/5 | hepsi | **59** | 0 | 0 | 0 | 0.42–1.00 | 0 |

İki bulgu:

1. **`yanlış_kilit` sayacı hiçbir yerde ateşlemiyor** — 151 px uzaktaki güvenli yanlış
   kilitte bile 0.
2. **`benzerlik` tersine dönmüş:** kopan dizide sabit **1.00**, sağlıklı dizilerde
   0.42–0.91. Sebebi mekanik — `_bagimsiz_dogrula` yalnızca `durum == KILITLI` iken
   çağrılıyor (`izleyici.py:277`); 117/23 hemen ŞÜPHELİ'ye düştüğü için kimlik denetimi
   **hiç çalışmıyor** ve `benzerlik` başlangıç değeri 1.0'da kalıyor.
   **Kimlik denetimi tam da en çok gerektiği anda devre dışı.**

## 8. Aşama 2 için sinyal ayrılabilirliği (yalnızca teşhis — eşik ÖNERİLMİYOR)

| sinyal | Mod A'yı ayırıyor mu | Mod B'yi ayırıyor mu | not |
|---|---|---|---|
| PSR | **evet** (2.7–4.5 vs 51–77) | **hayır** (99 — ters yönde) | tek başına yetersiz |
| P konum izi | **evet, çok keskin** (3.41 vs 3·10⁴) | **hayır** (58.7) | 4 kat büyüklük ayrımı |
| `durum ≠ KİLİTLİ` | evet ama **erken/aşırı ateşliyor** | evet | 117/23'te sağlıklı 40×15'te de t=1'de ateşliyor |
| ARAMA+KAYIP sayısı | evet (0 vs 5–41) | evet (5) | **geç** — hasar olduktan sonra |
| benzerlik | **hayır** (ters) | **hayır** | KİLİTLİ dışında hiç değerlendirilmiyor |
| yanlış_kilit | **hayır** | **hayır** | hiç ateşlemiyor |

**Hiçbir mevcut tek sinyal iki modu birden kapsamıyor.** P konum izi Mod A için
neredeyse kusursuz bir ayırıcı; Mod B için ayrı bir sinyal gerekiyor ve mevcut
savunmalar (benzerlik, yanlış_kilit) o rolü **oynamıyor**.

## 9. Aşama 1 hükmü

- **Merkez arızasının ilk nedeni `_boyut_tazele`'dir** — boyutu şişiriyor *ve* merkeze
  tam ağırlıkla yazıyor. Kare düzeyinde nedensel iz kayıtlı (§4).
- **İstemin öncelik sıralaması ölçümle ters düşüyor.** "Önce merkez, sonra boyut"
  yerine: boyut yolu merkez arızasının kaynağı olduğu için **Aşama 5, Aşama 2/3'ten
  önce ele alınmalı** — ya da en azından Aşama 2'nin kopuş ölçütü boyut sinyalini
  içermeli.
- **İki farklı arıza modu var** ve tek bir kopuş ölçütü ikisini birden yakalayamaz.
- **Ego katmanı 117/23'te sahte hareket üretiyor** (17–19 px/kare, doğrusu 0); kaçışın
  yakıtı bu.
- **Mevcut yanlış-kilit savunmaları çalışmıyor**; kimlik denetimi KİLİTLİ dışında hiç
  koşmuyor.
- **H1 (kapı gevşemesi) kısmen doğrulandı**: 20×10'da rol oynamıyor (gevşek kapı 0),
  8×5'te baskın (37/51).
- Karar tabanı hâlâ ince: **kopan tek dizi 117/23**, ve o dizi 4L'de patolojik
  işaretlenmişti. E4 kararı Aşama 3'ten önce verilmeli.

**Bu bir teşhistir. Hiçbir eşik, hiçbir davranış değiştirilmedi.**

## 10. DUR

Aşama 2'ye geçilmedi. Geçmeden önce gereken iki karar:

1. **E4** — VisDrone VID içinden yeni dizi eklenebilir mi? (Karar tabanı şu an tek dizi.)
2. **Sıralama** — §9'daki bulgu ışığında Aşama 5 (boyut) öne alınsın mı?

Ayrıca Aşama 2'ye başlamadan **kabul ölçütü belgesi** yazılacak (E3).

---

# AŞAMA 1-EK — Karar tabanı taraması

**Karar:** Kullanıcı, VisDrone VID içinden yeni **dizi** eklenmesine izin verdi
("yeni veri seti yok" yasağı yeni korpus içindi; VisDrone VID zaten depoda ve
benchmark'ın kaynağı).

## Deney 4I'nın hükmü neden yeniden sınandı

4I envanteri 086/182/268/339'u **native diziler** üzerinde Ö1–Ö5 ölçütleriyle
eledi. Gerekçe çoğunlukla *"metrik başarısızlıkta doygun, bir değişikliği ayırt
edemez"* (IoU≈0 oranı %67/%100/%65) idi. A9'un yatağı **farklıdır**: kompozit,
kontrollü seviye, 60 kare. O yüzden hüküm geçersiz kılınmadı — **A9'un kendi
yatağında yeniden ölçüldü** ve sonuç 4I ile yan yana raporlanıyor.

**Yeni yatak geçerlilik ölçütü:** `kareleri_topla` görünmeyen kareleri atlar.
Düşük görünürlükte 60 "ardışık" kare gerçekte zamanda sıçrar ve sahte büyük
hareket üretir. Bu yüzden ilk 60 görünür karenin **gerçek kare aralığı** ölçüldü.

| dizi/track | kare | görünür 60 | gerçek span | maks boşluk | yatak |
|---|---|---|---|---|---|
| 117/23 | 2720×1530 | 60 | 60 | 1 | TAMAM |
| 137/12 | 2688×1512 | 60 | 60 | 1 | TAMAM |
| 305/5 | 1904×1071 | 60 | 60 | 1 | TAMAM |
| 182/127 | 1344×756 | 60 | 60 | 1 | TAMAM |
| 268/31 | 3840×2160 | 60 | 60 | 1 | TAMAM |
| 339/49 | 1904×1071 | 60 | 60 | 1 | TAMAM |

Altısında da ilk 60 görünür kare **ardışık** — 268/31'in düşük native görünürlüğü
(0.26) dizinin ilerisinden geliyor, ilk 60 kareyi etkilemiyor. 086 taranmadı:
araç sınıfından track yok (4I Ö1, veri gerçeği, değişmedi).

## A9 yatağında kopuş davranışı

| dizi | 30×12 | 20×10 | 15×7 | 10×5 | 8×5 | **rol** | 4I hükmü |
|---|---|---|---|---|---|---|---|
| **117/23** | — | **13** | **12** | **12** | **12** | **KOPAN** | GÜVENİLİR |
| **268/31** | **6** | **1** | — | **20** | **24** | **KOPAN** | KULLANILAMAZ |
| **339/49** | **43** | **34** | **34** | **1** | **33** | **KOPAN** | KULLANILAMAZ |
| 137/12 | — | — | — | — | — | sağlam | GÜVENİLİR |
| 305/5 | — | — | — | — | — | sağlam | SINIRDA |
| 182/127 | — | — | — | — | — | sağlam | KULLANILAMAZ |

*(hücre = kopuş karesi; "—" = 60 karede kopuş yok)*

**Karar tabanı artık 3 kopan + 3 sağlam.** Aşama 1'in tek diziye dayanma sorunu
çözüldü.

> **⚠ KİRLİ YATAK (A10.1/D1).** Bu tablodaki **339/49, 305/5 ve 182/127**
> satırları geçersiz yatakta ölçüldü ve temiz yatakta tabandan **düştüler**.
> "3 kopan + 3 sağlam" temiz yatakta **2 kopan + 1 sağlam**'a iner
> (370/0 eklenince 3 kopan + 1 sağlam). Tek diziye dayanma sorunu
> **çözülmemiştir**.

## Arıza modları bağımsız dizilerde doğrulandı

| dizi | seviye | hata p95 | PSR p50 | P izi p95 | DCF kabul/red | saf ego p95 | mod |
|---|---|---|---|---|---|---|---|
| 117/23 | 20×10 | 380.5 | 4.5 | 36 259 | 14/5 | **18.4** | **A** |
| 268/31 | 20×10 | 579.8 | 3.0 | 3 380 | 2/7 | 3.0 | **A** |
| 339/49 | 15×7 | 58.1 | **36.1** | 3.9 | **59/0** | 4.2 | **B** |
| 339/49 | 10×5 | 60.7 | **40.2** | 3.4 | **59/0** | 4.2 | **B** |
| 117/23 | 8×5 | 150.6 | 31.2 | 58.6 | 51/3 | 18.5 | **B** |

Üç yeni sonuç:

1. **Mod B, 117/23 artefaktı değil.** 339/49 saf bir Mod B örneği: PSR 36–40,
   DCF'nin **59/59 karesi kabul ediliyor**, P izi sağlıklı (3.4) — ve yine de
   kopuş var (hata p95 58–61 px). Takipçi kendinden emin, ve yanılıyor.
2. **Mod A için sahte ego GEREKLİ DEĞİL.** 268/31'de saf ego yalnızca 2.3–3.0 px
   (117/23'te 18.4) ama Mod A yine oluşuyor. Ölçüm kaybı tek başına yeterli.
   Aşama 1 §6'daki ego bulgusu **117/23'e özgü bir ağırlaştırıcı**, genel neden değil.
3. **P konum izi evrensel bir Mod A dedektörü DEĞİL.** 117/23'te 3·10⁴ (kusursuz
   ayrım), 268/31'de 3.4·10³ (zayıf), 339/49'da 3.4 (hiç ayırmıyor).
   Aşama 1 §8'in "neredeyse kusursuz ayırıcı" ifadesi **tek diziye dayanıyormuş**;
   genişletilmiş tabanda düzeltildi.

## Yeni dizilere ilişkin uyarı

4I ölçtü: 268/31 kontrast **−37.0**, rafine ayrım AUC **0.272** · 339/49 kontrast
**−1.9**, AUC **0.464** (ikisi de şanstan kötü) · 117/23 kontrast 5.2, AUC 0.612.
Yani `rafine_kutu` varsayımı **kopan üç dizide de zayıf ya da tersine dönmüş**;
sağlam dizilerde güçlü (137/12: 57.3 / 0.764 · 305/5: 58.7 / 0.861).

Bu, Aşama 1'in `_boyut_tazele` bulgusuyla aynı yöne işaret ediyor ama bir
**karıştırıcı** da yaratıyor: kopan diziler aynı zamanda rafine'nin en kötü
olduğu diziler. Sonuçlar **dizi bazında** raporlanacak, havuzlanmayacak.

---

# AŞAMA 1b — KABUL ÖLÇÜTÜ (sonuç görülmeden yazıldı)

**Sınanan tek değişken:** `_boyut_tazele`'nin merkeze yazması
(`izleyici.py:567`, `kf.duzelt(yeni_c, r_carpan=1.0)`).

- **Kol A (kontrol):** mevcut davranış, değişiklik yok.
- **Kol B:** yalnızca o `duzelt` çağrısı atlanır. Boyut güncellemesi
  (`self.boyut`, `self.boyut_olculen`) **aynen devam eder**. Başka hiçbir şey
  değişmez.

Uygulama: Aşama 1'in Kalman sarmalayıcısı çağıranı zaten tanıyor; Kol B'de
`_boyut_tazele` kaynaklı `duzelt` çağrısı yutulur. **`takip/` dosyalarına
dokunulmaz, md5 donuk kalır.** Yalnızca A/B kazanırsa gerçek dosya değişikliği
önerilecek.

## Kabul koşulları — hepsi birden sağlanmalı

1. **Zarar vermeme (birincil).** Sağlam üç dizide (137/12, 305/5, 182/127)
   hiçbir seviyede yeni kopuş oluşmayacak **ve** merkez hatası p95 %20'den fazla
   kötüleşmeyecek.
2. **Fayda (birincil).** Kopan üç dizide (117/23, 268/31, 339/49) kopuşlu
   hücre sayısı **azalacak** ve en az **iki AYRI dizide** merkez hatası p95
   düşecek.
3. **Tek dizi yeterli değil.** Yalnızca 117/23'te düzelme gösteren sonuç
   **reddedilir**.
4. **Üst sınır uyarısı.** Ölçüm açık çevrimdir; sonuç bir üst sınırdır ve
   kapalı çevrimde tekrar sınanmadan gerçek dosyaya uygulanmaz.

Bu ölçüt A/B koşulmadan **önce** yazılmıştır.

---

# AŞAMA 1b — SONUÇ: A/B REDDEDİLDİ

**Kod:** `gazebo/tani_a9b_ab.py` · **Veri:** `cikti/a9b_ab_boyut_merkez.json`
**Bütünlük:** `takip/*.py` 6/6 md5 Aşama 1 ile aynı — müdahale yalnızca Kalman
sarmalayıcısında yapıldı. *(açık çevrim üst sınırı)*

## Sonuç tablosu — merkez hatası p95 (A→B) ve yan etkiler

| dizi | rol | seviye | A | B | Δ | IoU A→B | kopuş A→B | **güvenli yanlış A→B** |
|---|---|---|---|---|---|---|---|---|
| 117/23 | KOPAN | 30×12 | 20.9 | 14.4 | **−31%** | 0.494→0.469 | —→— | 0→0 |
| | | 20×10 | 380.5 | 147.9 | **−61%** | 0.136→0.154 | 13→14 | **0→41** |
| | | 15×7 | 434.9 | 151.7 | **−65%** | 0.112→0.122 | 12→13 | **4→43** |
| | | 10×5 | 607.2 | 137.7 | **−77%** | 0.131→0.145 | 12→13 | **4→39** |
| | | 8×5 | 150.6 | 147.0 | −2% | 0.155→0.155 | 12→12 | 36→29 |
| 268/31 | KOPAN | 15×7 | 12.8 | 24.2 | **+89%** | 0.463→0.363 | **—→8** | 0→0 |
| | | 10×5 | 37.7 | 279.1 | **+641%** | 0.466→0.202 | 20→21 | 0→5 |
| | | 8×5 | 424.0 | 32.5 | **−92%** | 0.259→0.537 | 24→25 | 8→0 |
| 339/49 | KOPAN | 30×12 | 121.6 | 51.8 | **−57%** | 0.320→0.237 | 43→36 | 0→0 |
| | | 15×7 | 58.1 | 56.7 | −2% | 0.207→0.218 | 34→34 | 26→6 |
| | | 10×5 | 60.7 | 62.1 | +2% | 0.082→0.102 | 1→1 | 55→35 |
| **137/12** | sağlam | 20×10 | 5.1 | 8.4 | **+63%** | 0.891→0.866 | —→— | 0→0 |
| | | 15×7 | 3.9 | 5.9 | **+49%** | 0.887→0.861 | —→— | 0→0 |
| | | 10×5 | 2.6 | 3.8 | **+44%** | 0.884→0.860 | —→— | 0→0 |
| | | 8×5 | 2.2 | 3.4 | **+57%** | 0.873→0.850 | —→— | 0→0 |
| **182/127** | sağlam | 30×12 | 22.2 | 80.7 | **+263%** | 0.383→**0.085** | **—→11** | 3→11 |
| 305/5 | sağlam | 20×10 | 14.0 | 16.9 | +20% | 0.398→0.380 | —→— | 0→0 |

## Kabul ölçütüne göre hüküm

| koşul | sonuç |
|---|---|
| **1. Zarar vermeme** | **İHLAL.** 182/127 · 30×12'de **yeni kopuş** (IoU 0.383 → 0.085). 137/12'de beş seviyenin beşinde p95 %21–63 kötüleşti. |
| **2. Fayda** | **İHLAL.** Kopuşlu hücre sayısı **13 → 15** (azalmadı, arttı: 268/31·15×7 ve 182/127·30×12 yeni). |
| **3. Tek dizi yeterli değil** | **İHLAL.** Tutarlı düzelme yalnızca 117/23'te. 268/31 karışık (+641% / −92%), 339/49 çoğunlukla nötr. |
| **4. Üst sınır** | Geçerli — sonuç açık çevrimdir. |

> ### `_boyut_tazele`'nin merkez yazması KALDIRILMAMALI. `takip/izleyici.py` değişmeyecek.

## Neden reddedildi — asıl bulgu

117/23'te merkez hatası **%61–77 düştü** ama **IoU hiç düzelmedi** (0.136 → 0.154).
Buna karşılık **güvenli yanlış kare sayısı 0 → 41 / 4 → 43 / 4 → 39** fırladı.

Yani merkez yazması kaldırılınca takipçi hedefe yaklaşmıyor — sadece **daha az
uzaklaşıyor** ve bu sayede `durum = KİLİTLİ` kalmayı sürdürüyor. Toplam güvenli
yanlış kare **194 → 269 (+39%)**.

> **Müdahale, GÜRÜLTÜLÜ bir arızayı (kaçış → ARAMA, sistem farkında)
> SESSİZ bir arızaya (kendinden emin yanlış kilit) çeviriyor.** Operasyonel
> olarak bu daha kötüdür: kaçan takipçiyi bir recovery mekanizması kurtarabilir,
> kendinden emin yanlış kilidi kurtaramaz — çünkü kimse yanlış olduğunu bilmez.
> Mod A → Mod B dönüşümü.

**Metodolojik not:** kabul ölçütü yalnızca merkez hatası p95 ve kopuşa dayansaydı
117/23'ün −%77'si "büyük başarı" sayılabilirdi. Yanlış sonuca **IoU ve güvenli
yanlış kare sayacı** engel oldu. Bundan sonraki bütün A/B'ler bu iki sütunu
zorunlu içerecek.

## `_boyut_tazele` hakkında güncellenmiş görüş

Aşama 1 onu kopuş zincirinin **tetikleyicisi** olarak gösterdi (kare düzeyinde iz,
§4). Aşama 1b bunun **kaldırılarak çözülemeyeceğini** gösterdi. İkisi çelişmiyor:
`_boyut_tazele` hem yaralıyor hem de yaralanmayı görünür kılıyor.

Dolayısıyla aday çözüm "kaldır" değil, şunlardan biri — **hiçbiri henüz sınanmadı**:

1. **Ağırlığı düzelt.** Şu an `r_carpan=1.0`, yani gürültülü bir rafineye Kalman'ın
   verebileceği **en yüksek güven**. Rafine gürültülü ama yansız olduğu için
   (`izleyici.py:545` yorumu) düşük güvenle girmesi gerekir.
2. **Kapıyı bağımsızlaştır.** Kapı `0.6 * self.boyut.max()`'a bakıyor — kendi
   bozduğu büyüklüğe (4U dersi). Bağımsız bir ölçekle değiştirilmeli.
3. **Boyut ile merkezi ayır.** Boyut güncellensin, merkez yazması ayrı ve daha
   katı bir kapıdan geçsin.

## DUR

Aşama 2'ye geçilmedi. Aşama 1b'nin `takip/` üzerinde hiçbir değişiklik önerisi
**yoktur** — A/B reddedildi, kod olduğu gibi kalıyor.

**Aşama 2'ye girdi olarak taşınanlar:**
- Kopuş ölçütü **iki modu birden** kapsamalı; P konum izi tek başına yetmiyor
  (117/23'te 3·10⁴, 339/49'da 3.4).
- **Güvenli yanlış kilit** (durum=KİLİTLİ ∧ IoU<0.2) birincil metrik olmalı —
  339/49'da kontrol kolunda bile 105 kare.
- Sağlam dizilerde `_boyut_tazele` merkez yazması **fayda sağlıyor** (137/12'de
  kaldırılınca p95 %44–63 kötüleşti); kopuş ölçütü bunu bozmamalı.

---

# A/B-1 — `_boyut_tazele` merkez düzeltmesinde `r_carpan`: 1.0 → 6.0

**Kod:** `gazebo/tani_a9_ab_boyut.py` · **Veri:** `cikti/a9_ab1_rcarpan6.json`
**Ölçüt:** `docs/architecture/A9_KABUL_OLCUTU.md` (koşumdan önce yazıldı)
**Bütünlük:** `takip/*.py` 6/6 md5 değişmedi. *(açık çevrim üst sınırı)*

## Tek değişken ve neden 6.0

Değişen tek şey: `izleyici.py:567`'deki `kf.duzelt(yeni_c, r_carpan=1.0)` çağrısının
`r_carpan`'ı. Boyut güncellemesi, kapı, sıklık — hepsi aynı.

**6.0 yeni bir sabit değil:** kod tabanının "zayıf ölçüm, az güven" için zaten
kullandığı değer (`izleyici.py:327`). Rafine, kodun kendi yorumunda *"gürültülü
ama yansız"* diye tanımlanıyor (`izleyici.py:545`); böyle bir ölçümün Kalman'a
verilebilecek **en yüksek güvenle** (1.0) girmesi tutarsızdı. Yeni bir eşik
uydurmamak için projenin mevcut düşük-güven sabiti seçildi.

## Dizi düzeyinde sonuç

| dizi | rol | ort IoU A→B | ΔIoU | güv. yanlış A→B | kopuşlu hücre A→B |
|---|---|---|---|---|---|
| 117/23 | KOPAN | 0.2056 → 0.2012 | −0.0044 | **44 → 115** | 4 → 4 |
| 268/31 | KOPAN | 0.2590 → **0.3148** | **+0.0558** | **8 → 0** | 4 → 4 |
| 339/49 | KOPAN | 0.2418 → 0.2406 | −0.0012 | **105 → 52** | 5 → 5 |
| 137/12 | sağlam | 0.8406 → 0.7992 | **−0.0414** | 0 → 0 | 0 → 0 |
| 305/5 | sağlam | 0.5966 → 0.5950 | −0.0016 | 10 → 11 | 0 → 0 |
| 182/127 | sağlam | 0.6014 → 0.5458 | **−0.0556** | 27 → 35 | **0 → 1** |

**Toplam güvenli yanlış kilit (30 hücre): 194 → 213 (+19).**
**Kopan dizilerde kopuşlu hücre: 13 → 13 (değişmedi).**

## Kabul ölçütüne göre hüküm

| koşul | sonuç |
|---|---|
| **K1a** sağlamda yeni kopuş yok | **İHLAL** — 182/127 · 30×12: yok → 11. kare |
| **K1b** IoU düşüşü ≤ 0.03 | **İHLAL** — 137/12·30×12 −0.137 · 182/127·30×12 −0.298 |
| **K1c** p95 artışı ≤ %20 | **İHLAL** — 137/12'de dört seviyede +30…+38% · 182/127 +258% |
| **K2** güvenli yanlış kilit artmayacak | **İHLAL** — 194 → 213 |
| **K3a** kopuşlu hücre azalacak | **İHLAL** — 13 → 13 (eşit, azalma yok) |
| **K3b** ≥2 kopan dizide IoU artacak | **İHLAL** — yalnızca 268/31 |
| **K3c** yalnız merkez hatası yetmez | uygulandı |

> ### A/B-1 REDDEDİLDİ. `r_carpan` sabit olarak 6.0'a çekilmeyecek. `takip/` değişmiyor.

## Ama reddedilme deseni bir kural gösteriyor

Zarar ve fayda rastgele dağılmıyor. 4I envanterinin ölçtüğü **rafine ayrım AUC**'siyle
yan yana konunca:

| dizi | 4I kontrast | 4I rafine AUC | A/B-1 ΔIoU |
|---|---|---|---|
| 268/31 | **−37.0** | **0.272** (şanstan kötü) | **+0.056** ✔ |
| 339/49 | −1.9 | **0.464** (şans) | −0.001 ≈ |
| 117/23 | 5.2 | 0.612 | −0.004 ≈ |
| 182/127 | 41.9 | 0.685 | −0.056 ✘ |
| 137/12 | 57.3 | 0.764 | −0.041 ✘ |
| 305/5 | 58.7 | **0.861** | −0.002 ≈ |

**Desen:** rafine ayrım AUC'si şans düzeyinde ya da altında olan dizilerde
(268/31) güveni düşürmek **kazandırıyor**; rafine güvenilir olan dizilerde
(137/12, 182/127) **kaybettiriyor**. Aradakiler nötr.

Bu, Aşama 1b ile de tutarlı: orada merkez yazmasını tamamen kaldırmak 137/12 ve
182/127'yi bozmuştu. İki bağımsız deney aynı yöne işaret ediyor:

> **`r_carpan`'ın doğru değeri sabit değildir. Rafine'nin o sahnedeki
> güvenilirliğine bağlıdır.** 1.0 kötü-kontrastlı sahneler için fazla yüksek,
> 6.0 iyi-kontrastlı sahneler için fazla düşük.

**Bu bir gözlemdir, kanıtlanmış bir yasa değil:** n=6, ve 182/127'nin kaybı tek
bir hücreden (30×12) geliyor. Ama A/B-2 ve A/B-3'ün yönünü belirliyor.

## Öne çıkan tek hücre

268/31 · 8×5: IoU **0.259 → 0.598**, merkez p95 **424 → 15.0** (−96.5%),
güvenli yanlış **8 → 0**, bho50 1.27 → 1.00. Üç metrik birden aynı yönde —
bu bir gürültü değil. Rafine'nin en kötü olduğu dizide (AUC 0.272) güveni
düşürmenin ne kadar kazandırabileceğini gösteriyor.

## 117/23'te Mod A → Mod B dönüşümü TEKRARLANDI

20×10 ve 10×5'te merkez p95 %61–77 düştü ama güvenli yanlış kilit **0 → 41** ve
**4 → 39**. Aşama 1b'deki bulgunun aynısı: merkez düzeltmesinin ağırlığını
azaltmak, kaçışı durdurmuyor — **kaçışı sessizleştiriyor.** K2'nin neden mutlak
bir koşul olduğunu bir kez daha doğruluyor.

## DUR

`takip/` üzerinde hiçbir değişiklik önerisi yoktur. Bir sonraki deney: **A/B-2**,
kabul kapısının kendi ürettiği `self.boyut`'a bağımlılığı
(`izleyici.py:566`: `norm(yeni_c - kf.konum) < 0.6 * self.boyut.max()`).

A/B-1'in deseni A/B-2'yi doğrudan ilgilendiriyor: kapı da bozuk boyuta bakıyor,
yani rafine'nin kötü olduğu sahnelerde hem güven hem kapı aynı anda yanlış.

---

# A/B-2 — Kabul kapısının `self.boyut` bağımlılığı

**Kod:** `gazebo/tani_a9_ab2_kapi.py` · **Veri:** `cikti/a9_ab2_kapi.json`
**Ölçüt:** `A9_KABUL_OLCUTU.md` (değiştirilmedi) · **`r_carpan` her kolda 1.0**
(A/B-1'in 6.0'ı kullanılmadı) · **`takip/*.py` md5 6/6 değişmedi.**
*(açık çevrim üst sınırı)*

## Geçerlilik: eşdeğerlik testi

Reddedilen kararları da görebilmek için `_boyut_tazele` birebir yeniden yazıldı.
Yeniden yazımın kontrol kolu, **gerçek metodun** kontrol koluyla 9 metrikte,
30 hücrede karşılaştırıldı: **0 fark.** Deney geçerli.

## Tek değişken

`izleyici.py:566` kapı ifadesi:
`0.6 * self.boyut.max()` → **`0.6 * max(r[2:])`** (rafine'nin o kareye ait taze
ölçümü). Aynı 0.6 sabiti; yeni eşik yok. `r[2:]` kapının geçmiş kararlarından
etkilenmez, `self.boyut` etkilenir.

**Tanısal ek kol (başarı değil, üst sınır):** `oracle_kapi` — kapı GT'ye bakar,
`|yeni_c − GT| < |kf.konum − GT|` ise kabul eder. Mükemmel kapı.

## BULGU 1 — Kapı zaten bir kapı değil

| ölçüm | değer |
|---|---|
| `_boyut_tazele` çağrısı (30 hücre) | 273 |
| `d / eşik` oranı p50 | **0.152** |
| `d / eşik` oranı p95 | 0.696 |
| `d / eşik` maksimum | 1.270 |
| **red oranı** | **%0.37 (273'te 1)** |

Kapı **273 çağrının 272'sini kabul ediyor.** `self.boyut` bağımlılığını kaldırmak
sonucu değiştirmiyor, çünkü **kapı hiçbir zaman bağlayıcı değil.**

**Nedeni yapısal:** `rafine_kutu(bgr, kf.konum, self.boyut, …)` arama penceresini
`self.boyut` ile ölçekliyor, dolayısıyla döndürdüğü merkezin sapması `d` zaten
kabaca `boyut/2` ile sınırlı. Eşik ise `0.6·boyut`. **Eşitsizliğin iki tarafı da
aynı büyüklükle ölçekleniyor** → oran boyutsuz ve neredeyse hep 1'in altında.

> Bu, 4U dersinin daha derin bir biçimi: bir kapı, eşiğini ve ölçtüğü büyüklüğü
> **aynı** niceliğe bağlarsa yalnızca kendi kararlarını kirletmez — **hiçbir şey
> ölçmez.**

## BULGU 2 — Kapı kabul ettiklerinin %45'i zararlı

Kapı kararları, GT ile etiketlenip 2×2 matrise dökülünce (273 çağrı):

| kol | kabul-iyi | kabul-kötü | red-iyi | red-kötü | kabul oranı | kabul edilen zarar | kaçan kazanç |
|---|---|---|---|---|---|---|---|
| **kontrol** | 149 | **123** | 1 | **0** | %99.6 | **697 px** | 24 px |
| **ab2 bağımsız** | 147 | 122 | 3 | 0 | %98.9 | 672 px | 49 px |
| *oracle (üst sınır)* | *140* | *0* | *0* | *137* | *%50.5* | *0* | *0* |

Ölçümlerin **yarısı zararlı** (137/277) ve mevcut kapı bunların **hiçbirini**
yakalamıyor: `red_kötü = 0`. Bağımsızlaştırılmış kapı da yakalamıyor (0).

## BULGU 3 — Mükemmel kapı bile tek bir kopuşu önlemiyor

| kol | ort IoU 117/23 | ort IoU 268/31 | ort IoU 339/49 | **güvenli yanlış (30 hücre)** | **KOPAN kopuşlu hücre** |
|---|---|---|---|---|---|
| kontrol | 0.2056 | 0.2590 | 0.2418 | **194** | **13** |
| ab2 bağımsız | 0.2056 | 0.2590 | 0.2420 | 195 | **13** |
| *oracle kapı* | *0.2474* | *0.2490* | *0.2486* | ***223*** | ***13*** |

Oracle kapı — GT'ye bakan, zararlı ölçümlerin **tamamını** reddeden kapı —
IoU'yu 117/23'te 0.206 → 0.247 çıkarıyor, ama:

- **kopuşlu hücre 13 → 13. Tek bir kopuş bile önlenmiyor.**
- **güvenli yanlış kilit 194 → 223 (+15%)**; 117/23'te **44 → 117**.

> **Kapı, sorunun bulunduğu yer değildir.** Kapıyı mükemmelleştirmenin tavanı
> ölçüldü ve tavan yetersiz.

## Kabul ölçütüne göre hüküm

| koşul | sonuç |
|---|---|
| K1 sağlamda regresyon | geçti (182/127 IoU −0.0016, kopuş yok) |
| **K2** yanlış kilit artmayacak | **İHLAL** — 194 → 195 |
| **K3a** kopuşlu hücre azalacak | **İHLAL** — 13 → 13 |
| **K3b** ≥2 kopan dizide IoU artışı | **İHLAL** — hiçbirinde anlamlı artış yok |

> ### A/B-2 REDDEDİLDİ. Kapı bağımsızlaştırılmayacak. `takip/` değişmiyor.
> Reddedilme nedeni A/B-1'den farklı: **zarar vermiyor, hiçbir şey yapmıyor.**

## Üç deneyin birleşik sonucu

`_boyut_tazele`'nin merkez yoluna yapılan **üç bağımsız müdahale**:

| deney | müdahale | kopuş önlendi mi | güvenli yanlış |
|---|---|---|---|
| Aşama 1b | merkez yazmasını tamamen **kaldır** | hayır (13 → 15) | 194 → **269** |
| A/B-1 | güveni **düşür** (r_carpan 1→6) | hayır (13 → 13) | 194 → **213** |
| A/B-2 | kapıyı **mükemmelleştir** (oracle) | hayır (13 → 13) | 194 → **223** |

**Üçü de aynı sonucu veriyor: hiçbiri tek bir kopuşu önlemiyor, üçü de güvenli
yanlış kilidi artırıyor.**

Aşama 1 `_boyut_tazele`'yi kopuş zincirinin **tetikleyicisi** olarak göstermişti
(t=12'de boyutu şişirip merkezi 11.9 px kaydırıyor). Üç deney gösteriyor ki
**tetikleyiciyi kontrol etmek zinciri kırmıyor.** Zinciri sürdüren şey sonraki
adımlar: PSR çöküşü → ölçüm kaybı → bozuk hız/ego ile ölü hesap.

> **`_boyut_tazele`'nin MERKEZ yolu bir kaldıraç değildir. Bu yol kapandı.**

## DUR

`takip/` üzerinde değişiklik önerisi **yoktur**.

**A/B-3 hakkında not:** istemde tanımlandığı hâliyle ("boyut güncellensin, merkez
etkisi ayrı kontrol edilsin") A/B-3, aynı merkez yoluna yapılacak **dördüncü**
müdahaledir; yukarıdaki üç sonuç aynı çıkmasını bekletiyor. Henüz sınanmamış olan
**boyut tarafıdır**: 117/23'te `bho` 1.0 → 8.85'e tırmanıyor ve hiçbir deney bunu
çapalamayı denemedi. A/B-3'ün bu yönde tanımlanması daha bilgilendirici olur —
karar kullanıcınındır.

---

# A/B-3 — Boyut çapası: bağımsızlık denetimi + tanısal zincir testi

**Kod:** `gazebo/tani_a9_ab3_boyut.py` · **Veri:** `cikti/a9_ab3_boyut_capasi.json`
**`takip/*.py` md5 6/6 değişmedi.** Kabul ölçütü değiştirilmedi.

## 1. Bağımsız, mutlak boyut ölçümü var mı? — **YOK**

### `rafine_kutu` (`tespit.py:87`) — bağımsız DEĞİL, üç ayrı yerden

| # | satır | bağımlılık |
|---|---|---|
| 1 | 98–99 | arama penceresi `boyut × 3.0` |
| 2 | 117 | yedek bileşen mesafe kapısı `0.35 × max(boyut)` |
| 3 | **121–122** | **kabul oranı kapısı** `oran = [bw,bh]/boyut`, `0.35 < oran.mean() < 2.6` |

Üçüncüsü belirleyici: ölçüm, **mevcut (bozuk olabilen) boyutun [0.35, 2.6] katı
bandına kırpılıyor.** Yani `rafine_kutu` bir ölçüm değil, mevcut boyutun etrafında
bir **düzeltmedir**; tanımı gereği mutlak olamaz.

### Diğer adaylar ve bağımsızlık durumları

| kaynak | boyut üretir | takipçi boyutundan bağımsız | **mutlak** | gerekçe |
|---|---|---|---|---|
| `rafine_kutu` | evet | **HAYIR** | — | yukarıdaki 3 bağımlılık |
| `HareketTespit.adaylar` (`tespit.py:47`) | evet | **EVET** — filtreleri (`min_alan`, `max_kenar`, en-boy) `boyut`'a bakmaz | **HAYIR** | leke `t−1 ∪ t` birleşimi, hareket yönünde uzar, `dilate` ile şişer (`rafine_kutu` docstring'i bunu açıkça söylüyor); ayrıca hareket şart |
| `ego.olcek_katsayisi` (`egomotion.py:113`) | oran | **EVET** | **HAYIR** | bağıl ölçek; çarpımsal biriktirme A3.9'da üstel hata nedeniyle terk edildi, kare başına [0.90,1.10]'a kırpılıyor |
| DCF çekirdekleri (`cekirdekler.py`) | **hayır** | — | — | `ara()` yalnızca (merkez, PSR) döner; `_kanallar` yamayı `boyut × dolgu` ile boyutlandırır, ölçek kestirmez |
| `kilitle()` başlangıç kutusu | tek nokta | evet (t=0) | evet | ama akan bir ölçüm değil; ego ile taşımak A3.9 4S'te denendi (182/127'de sıfır etki) |

> ### **Mevcut sistemde bağımsız, mutlak, takipçi boyutundan türetilmemiş bir boyut ölçümü YOKTUR.**
> Bağımsız olanlar mutlak değil (`adaylar` yanlı, `ego` bağıl); mutlak olabilecek
> olan (`rafine_kutu`) bağımsız değil. Bu, mimarideki boş **INDEPENDENT
> MEASUREMENT** katmanının (P0.1) tam karşılığıdır.

## 2. Yeni bulgu — boyut hatası KENDİNİ KİLİTLİYOR

`rafine_kutu` oran kapısı `0.35 < oran.mean() < 2.6`. Boyut **2.86 kattan fazla**
şişmişse gerçek hedefin oranı 0.35'in altına düşer → **rafine reddedilir** →
boyut bir daha düzelemez. Ölçüldü (kontrol kolu, 358 çağrı):

| `bho` bandı | çağrı | `None` döndü | **red oranı** |
|---|---|---|---|
| 0.00–1.50 | 295 | 57 | 19.3% |
| 1.50–2.00 | 28 | 6 | 21.4% |
| 2.00–2.86 | 20 | 9 | **45.0%** |
| **2.86–4.00** | 10 | 6 | **60.0%** |
| 4.00+ | 5 | 2 | 40.0% |

Red oranı, **öngörülen 2.86 eşiğine doğru tekdüze artıyor**. Yüksek bantlarda
örneklem küçük (10 ve 5 çağrı), ama yön ve eşik konumu mekanizmayla birebir
uyuşuyor. Aşama 1'de gözlenen *"tahmin 106–131 px'e çakılı kalıyor, gerçek 12 px'e
inerken"* olgusunun açıklaması budur.

## 3. Tanısal zincir testi — boyut düzelirse zincir kırılıyor mu?

**`oracle_capa`: her karenin başında `boyut` ve `boyut_olculen` GT'ye çapalanır.
Başka hiçbir şey değişmez** (merkez yolu, `r_carpan`=1.0, kapı, PSR, KF, ROI —
hepsi baseline). **Bu bir aday mekanizma DEĞİL, tanısal ÜST SINIRDIR.**

### 117/23 · 20×10 — kare kare zincir

| t | **kontrol** bho / PSR / DCF k-r / hata / IoU | **oracle** bho / PSR / DCF k-r / hata / IoU |
|---|---|---|
| 6 | 0.99 / 25.2 / 1-0 / 4.2 / 0.77 | 1.00 / 24.8 / 1-0 / 4.3 / 0.76 |
| 9 | 1.26 / 12.0 / 1-0 / 6.3 / 0.60 | 1.00 / 24.0 / 1-0 / 5.7 / 0.68 |
| **12** | **1.82** / **5.9** / 1-0 / 19.2 / 0.24 | 1.04 / 10.3 / 1-0 / 4.3 / 0.75 |
| 15 | 1.84 / **2.6** / **0-1** / 44.8 / 0.06 | 1.00 / 19.1 / 1-0 / 4.6 / 0.73 |
| 18 | 1.86 / 4.3 / **0-1** / 81.2 / 0.00 | 1.00 / 28.3 / 1-0 / 2.7 / 0.83 |
| 24 | 1.89 / 4.5 / **0-0** | 171.6 / 0.00 | 1.24 / 11.1 / 1-0 / 10.8 / 0.53 |
| 33 | 1.89 / 4.5 / **0-0** / 235.3 / 0.00 | 1.00 / 27.2 / 1-0 / 8.8 / 0.54 |

**Zincirin her halkası değişiyor.** Kontrolde bho 1.89'a çakılıyor, PSR 4.5'e
düşüp orada kalıyor, DCF ölçümü tamamen kesiliyor (0-0 = takipçi ARAMA'da),
hata 235 px'e çıkıyor. Oracle'da bho 1.00, PSR 11–28, **DCF her karede kabul
ediliyor**, hata 2.7–10.8 px'te kalıyor.

Aynı hücrenin toplamı: IoU 0.136 → **0.662**, merkez p95 380.5 → **11.5**,
kopuş 13. kare → **yok**.

> **Soru 4'ün cevabı: EVET. Boyut hatası sıfırlandığında DCF → PSR → ölçüm kaybı
> → Kalman coast → merkez kaçışı zincirinin tamamı kırılıyor.**

### Dizi düzeyi (6 dizi, 30 hücre)

| dizi | rol | bho50 | PSR50 | ort IoU | güv. yanlış | kopuşlu hücre |
|---|---|---|---|---|---|---|
| 117/23 | KOPAN | 2.82→1.00 | 12.7→20.7 | 0.206→**0.260** | **44→114** | 4→4 |
| 268/31 | KOPAN | 1.15→1.00 | 7.2→7.2 | 0.259→**0.303** | 8→**2** | 4→**3** |
| 339/49 | KOPAN | 1.39→1.00 | 30.3→14.8 | 0.242→**0.261** | 105→**20** | 5→5 |
| 137/12 | sağlam | 0.99→1.00 | 67.9→69.3 | 0.841→0.847 | 0→0 | 0→0 |
| 305/5 | sağlam | 1.12→1.00 | 52.2→67.1 | 0.597→**0.752** | 10→**0** | 0→0 |
| 182/127 | sağlam | 0.81→1.00 | 24.6→29.2 | 0.601→**0.801** | 27→**0** | 0→0 |

**Toplam güvenli yanlış kilit: 194 → 136.** **Kopan dizilerde kopuşlu hücre: 13 → 12.**

### A9 serisindeki dört müdahalenin karşılaştırması

| deney | müdahale | ort IoU | güvenli yanlış | kopuşlu hücre |
|---|---|---|---|---|
| Aşama 1b | merkez yazmasını kaldır | karışık | 194 → **269** ✘ | 13 → **15** ✘ |
| A/B-1 | merkez güvenini düşür | −0.004…+0.056 | 194 → **213** ✘ | 13 → 13 ✘ |
| A/B-2 | kapıyı mükemmelleştir (oracle) | +0.04 (1 dizi) | 194 → **223** ✘ | 13 → 13 ✘ |
| **A/B-3 tanısal** | **boyutu çapala (oracle)** | **6 dizinin 6'sında arttı** | 194 → **136** ✔ | 13 → **12** ✔ |

> **Kaldıraç MERKEZ değil, BOYUTTUR.** Merkez yoluna yapılan üç müdahale hiçbir
> kopuşu önlemedi ve üçü de güvenli yanlış kilidi artırdı. Boyutu çapalamak, altı
> dizinin altısında IoU'yu artıran ve yanlış kilidi **azaltan** tek müdahale.

### Karşı örnek — gizlenmiyor

**117/23 · 30×12** oracle altında çöküyor: IoU 0.494 → **0.035**, merkez p95
20.9 → **492**, güvenli yanlış 0 → **38**, kopuş yok → 4. kare. bho zaten 1.05'ti,
yani çapa bir şeyi düzeltmedi, sağlıklı bir hücreyi bozdu. 117/23'ün toplam
güvenli yanlışı bu yüzden 44 → 114'e çıkıyor — **IoU'su artarken.**

117/23, Deney 4L'de "bir uçurumun 1 px yanında" diye işaretlenen dizidir
(kontrast 5.2, rafine AUC 0.612). Diğer beş dizinin beşinde çapa tutarlı biçimde
kazandırıyor. **Ama bu, çapanın evrensel bir çözüm olmadığını gösteriyor.**

## 4. Hüküm — madde 8 uygulanıyor

**A/B-3 aday mekanizma olarak KOŞULMADI ve zorlanmadı.** Gerekçe:

1. Mevcut sistemde bağımsız, mutlak boyut ölçümü **yok** (§1, kod kanıtlarıyla).
2. Kullanıcı talimatı: yeni ölçüm **icat edilmeyecek** ve icat edilmiş bir ölçümle
   başarı değerlendirmesi **yapılmayacak**.
3. Elde olan tek "çapa" GT'dir; GT operasyonel değildir. Tanısal olarak
   kullanıldı, kabul ölçütüne **sokulmadı**.

`takip/` üzerinde hiçbir değişiklik önerisi yoktur.

## 5. Ama teşhis yönü değiştiriyor

A/B-3 tanısal sonucu, "boyut çapası peşini bırak" demiyor — **"boyut çapası doğru
kaldıraç, ama onu besleyecek ölçüm sistemde yok"** diyor. Eksik parça tam olarak
**P0.1 / INDEPENDENT MEASUREMENT katmanıdır.**

Ve A8 bu katmanın nasıl doldurulabileceğini zaten ölçmüştü: doğru büyütmedeki ROI
dedektörü, takipçiden türetilmemiş bir kutu döndürüyor — **hem merkez hem boyut** —
ve 137/12'de 8×5 seviyesinde recall 1.000 veriyor. İki fazın bulguları aynı
noktada buluşuyor.

Bu bir öneri değil, gözlemdir; kapalı çevrimde sınanmadan hiçbir şey iddia edilemez.

## 6. DUR

Kullanıcının 8. maddesi uyarınca sıradaki aday **boyut çapası değil**,
**PSR + Kalman + merkez tutarlılığı üzerinden erken kopuş tespiti** (Aşama 2).

Aşama 2'ye taşınan, A/B-3'ten çıkan iki girdi:
- **`bho` artışı kopuşun en erken habercisi:** 117/23·20×10'da bho t=9'da 1.26,
  t=12'de 1.82 — PSR çöküşünden (t=15) ve kopuştan (t=13) **önce**. Ama `bho`
  operasyonel olarak ölçülemez (GT gerekir); yerine geçecek bir vekil aranmalı.
- **`rafine_kutu`'nun `None` dönme oranı** operasyonel olarak ölçülebilir ve
  `bho` ile birlikte artıyor (%19 → %60). Erken kopuş tespiti için **aday sinyal**.

---

# AŞAMA 2 — ERKEN KOPUŞ TESPİTİ

> ### `AÇIK ÇEVRİM` · `TEŞHİS` · `GT YALNIZCA OFFLINE ETİKETLEME`
> A/B yok · eşik seçilmedi · tracker davranışı değişmedi · `takip/` değişmedi.

**Kod:** `gazebo/tani_a9_kopus.py` (tek yeni dosya) ·
**Veri:** `cikti/a9_takipci_merkez_recovery.json` → `phase2_break_detection`
**Bütünlük:** `takip/*.py` md5 koşum öncesi == sonrası, 6/6 aynı.

## 1. Ölçüm konvansiyonları

Bunlar **önerilen çalışma eşikleri değil**, sinyalleri kıyaslanabilir kılan
tanısal kurallardır:

- **K1 · ilk bozulma karesi:** sinyalin, o hücrenin ilk 5 karesinden hesaplanan
  kendi tabanına göre bozulma yönünde 3σ saptığı ilk kare (t>5).
- **K2 · önceleme (lead)** = `kopuş_karesi − ilk_bozulma_karesi`. Pozitif = erken uyarı.
- **K3 · ayırma gücü, EŞİKSİZ:** ROC AUC. Pozitif = kopan hücrelerde kopuştan
  önceki 10 kare; negatif = sağlam dizilerin tüm kareleri.
  **AUC bozulma yönüne göre yönlendirildi** (0.5 = ayırmıyor, 1.0 = kusursuz).
- **K4 · yanlış alarm:** sağlam 15 hücrenin kaçında K1 ateşliyor.

## 2. Mod etiketleme (offline)

Ölçüt: kopuş sonrası DCF kabul oranı ≥ 0.8 → **Mod B**, aksi **Mod A**.
Gözlenen dağılım belirgin biçimde iki uçlu:
`[0.00, 0.04, 0.08, 0.10, 0.17, 0.25, 0.30, 0.39, 0.68, 0.83, 1.00, 1.00, 1.00]`

| mod | hücre sayısı | hücreler |
|---|---|---|
| **A** (ölçüm kaybı) | 9 | 117/23 · 20×10, 15×7, 10×5 · 268/31 · 30×12, 20×10, 10×5, 8×5 · 339/49 · 30×12, 8×5 |
| **B** (güvenli yanlış kilit) | 4 | 117/23 · 8×5 · 339/49 · 20×10, 15×7, 10×5 |

## 3. Sinyal tablosu

| sinyal | **AUC** | FPR@TPR.5 | lead p50 | lead>0 oranı | **yanlış alarm** | A\|B AUC | türetilmiş? |
|---|---|---|---|---|---|---|---|
| **psr** | **0.877** | **0.023** | 4.5 | 0.67 | 8/15 | **0.930** | tracker içi |
| P_konum_iz | 0.760 | 0.055 | **0.0** | 0.27 | **2/15** | 0.924 | tracker içi |
| durum_disi | 0.732 | — | 0.5 | 0.50 | **2/15** | 0.898 | tracker içi |
| kayip | 0.731 | — | −1.0 | 0.33 | **2/15** | 0.918 | tracker içi |
| **dcf_kf_ayrim** | 0.731 | 0.158 | **22.0** | **0.80** | 8/15 | 0.869 | tracker içi |
| dcf_sicrama | 0.723 | 0.190 | −4.5 | 0.40 | 9/15 | 0.798 | tracker içi |
| olcum_yok | 0.620 | — | 1.0 | 0.63 | **2/15** | 0.865 | tracker içi |
| rafine_none_kosan | 0.566 | 1.000 | −3.0 | 0.22 | 4/15 | 0.500 | tracker içi |
| psr_norm | 0.538 | 0.417 | 9.0 | 0.57 | 10/15 | 0.718 | **TÜRETİLMİŞ** |
| benzerlik | 0.501 | — | 10.0 | 0.75 | 11/15 | **0.268** ⇒ B yönünde **0.732** | tracker içi |
| **boyut_orani** | **0.471** | 0.631 | 4.0 | 0.67 | 11/15 | 0.615 | tracker içi |
| ego_guven | 0.282 (ters) | 0.680 | hiç | 0/15 | 0.453 | tracker içi |
| ego_olcek_sapma | 0.199 (ters) | 0.933 | 6.0 | 0.69 | 10/15 | 0.618 | tracker içi |

*FPR@TPR sütunu ayrık sinyallerde (`kayip`, `durum_disi`, `olcum_yok`, `benzerlik`)
dejenere olur — o satırlarda anlamlı sayı hücre düzeyi yanlış alarmıdır.*

## 4. En önemli sonuç — hiçbir sinyal iki işi birden yapmıyor

| rol | en iyi sinyal | bedeli |
|---|---|---|
| **en erken uyarı** | `dcf_kf_ayrim` — lead **22 kare**, hücrelerin %80'inde pozitif | yanlış alarm **8/15** |
| **en iyi ayrım** | `psr` — AUC **0.877**, FPR@TPR0.5 = **%2.3** | lead yalnızca **4.5 kare** |
| **en düşük yanlış alarm** | `P_konum_iz`, `kayip`, `durum_disi`, `olcum_yok` — **2/15** | lead ≈ **0** — kopuşla **aynı anda** ateşliyorlar |

> **Takas keskin: yanlış alarmı düşük olan sinyallerin öncelemesi yok; öncelemesi
> olanların yanlış alarmı yüksek.** Mevcut sinyallerle "erken VE güvenilir" tespit
> tek bir sinyalden çıkmıyor.

## 5. `boyut_orani` — A/B-3'ün habercisi operasyonele TAŞINMIYOR

A/B-3'te `bho` (GT'ye göre) kopuştan önce yükseliyordu. Operasyonel karşılığı
`boyut_orani = tak.boyut.max() / kilit boyutu` **ayırt etmiyor: AUC 0.471.**

| | p05 | p50 | p95 |
|---|---|---|---|
| sağlam | 0.66 | 1.04 | 1.76 |
| kopuş öncesi | 0.80 | 1.00 | 1.70 |

Dağılımlar neredeyse çakışık. **Sağlıklı dizilerde de takipçinin kutu boyutu
±%70 sürükleniyor**; kilit boyutuna göre bağıl sürüklenme kopuşa özgü değil.

> **Kayıt:** "bho erken habercidir" ifadesi **yalnızca GT ile hesaplandığında
> doğrudur** ve operasyonel bir tespit sinyali olarak kullanılamaz. A/B-3'ün
> gözlemi bu haliyle taşınamaz.

## 6. Zincirler — ölçüm sırasına göre, varsayım değil

### Mod A · 117/23 · 20×10 (kopuş t=13)

| t | psr | boyut_orani | P izi | kayıp | ölçüm yok | rafine None | hata | IoU |
|---|---|---|---|---|---|---|---|---|
| 6 | 25.2 | 1.13 | 3.4 | 0 | 0 | 0.00 | 4.2 | 0.77 |
| 9 | 12.0 | 1.44 | 3.0 | 0 | 0 | 0.00 | 6.3 | 0.60 |
| **12** | **5.9** | **2.08** | 3.5 | 2 | 0 | 0.00 | 19.2 | 0.24 |
| 15 | **2.6** | 2.10 | **51.5** | 5 | **1** | 0.00 | 44.8 | 0.06 |
| 18 | 4.3 | 2.12 | 42.1 | 8 | 1 | 0.25 | 81.2 | 0.00 |
| 24 | 4.5 | 2.16 | **260** | 15 | 1 | 0.25 | 171.6 | 0.00 |
| 30 | 4.5 | 2.16 | **1418** | 21 | 1 | 0.25 | 210.3 | 0.00 |

**Ölçülen sıra:** `boyut_orani` yükselir (t=9: 1.44) → `psr` düşer (t=12: 5.9) →
`ölçüm yok` = 1 (t=15) → `P izi` patlar (t=15: 51 → t=30: 1418) → hata kaçar.
Aşama 1'de kurulan zincir **bağımsız bir koşumda, sinyal sırasıyla doğrulandı.**

### Mod B · 339/49 · 15×7 (kopuş t=34)

| t | psr | P izi | kayıp | durum dışı | ayrım | **benzerlik** | hata | IoU |
|---|---|---|---|---|---|---|---|---|
| 21 | 46.7 | 3.0 | 0 | 0 | 0.02 | 1.00 | 5.3 | 0.39 |
| 30 | 30.8 | 3.3 | 0 | 0 | 0.05 | 0.73 | 3.1 | 0.42 |
| **33** | **6.0** | 5.9 | 1 | **1** | **0.42** | 0.73 | 12.3 | 0.22 |
| 36 | 12.8 | 3.4 | 0 | 0 | 0.03 | **0.50** | **57.5** | **0.00** |
| 42 | 23.5 | 3.4 | 0 | 0 | 0.00 | **0.48** | 58.2 | 0.00 |
| 45 | **36.7** | 3.4 | 0 | 0 | 0.01 | **0.48** | 57.9 | 0.00 |

**Mod B tamamen farklı bir imza:** tek karelik bir olay (t=33 — `ayrım` 0.02'den
**0.42**'ye sıçrıyor, PSR anlık 6.0'a düşüyor) takipçiyi yanlış hedefe devrediyor.
Sonrasında **bütün iç sinyaller normale dönüyor** — PSR 36.7'ye çıkıyor, P izi 3.4,
kayıp 0, durum KİLİTLİ — ama hata 58 px ve **IoU 0.00**.

**Geriye kalan tek kalıcı iz `benzerlik`:** 1.00 → 0.73 → 0.50 → 0.48.

### Aşama 1'in `benzerlik` hükmüne düzeltme

Aşama 1'de `benzerlik`i "tersine dönmüş, işe yaramaz" diye kaydetmiştim. Genişletilmiş
tabanla bu **eksik bir okumaymış**: `benzerlik` Mod A'da **ölçülmüyor** (yalnızca
`durum == KİLİTLİ` iken `_bagimsiz_dogrula` çağrılıyor, Mod A hemen ŞÜPHELİ'ye
düşüyor) — ama Mod B'de takipçi KİLİTLİ kaldığı için denetim çalışmaya devam ediyor
ve **yanlış hedefi kaydediyor** (Mod ayrımı AUC **0.732**, B yönünde).

> **`benzerlik`, Mod A için kör; Mod B için mevcut TEK kalıcı sinyal.**

## 7. Döngüsellik uyarısı

Mod etiketi **kopuş sonrası DCF kabul oranından** türetildi. Bu yüzden
`olcum_yok`, `kayip`, `durum_disi`'nin yüksek Mod A|B AUC'si **kısmen
döngüseldir** ve bağımsız kanıt sayılmaz.

**Döngüsel olmayan mod ayırıcıları:** `psr` (0.930), `P_konum_iz` (0.924),
`dcf_kf_ayrim` (0.869), `benzerlik` (0.732 · B yönünde).

## 8. Sınırlar

- Açık çevrim; dedektör yok. Sonuçlar **üst sınırdır**.
- 30 hücre, 13 kopan hücre. **İstatistiksel güç düşük.**
- **Mod B örneklerinin 3'ü 4'ü 339/49'dan** geliyor; Mod B bulguları tek diziye yaslanıyor.
- 117/23 Deney 4L'de patolojik işaretli (1 px uçurumu, kontrast 5.2).
- K1'in 3σ kuralı **tanısal konvansiyondur**, önerilen eşik değildir.
- `bho_gt` yalnızca offline etikettir; aday sinyal `boyut_orani`'dır ve **başarısız oldu**.
- DCF ham tepe değeri çekirdek dışına çıkmıyor; **PSR tek erişilebilir vekildir**.
- Ayrık sinyallerde FPR@TPR nitelemesi dejeneredir.

## 9. Aşama 2 hükmü

1. **İki mod ölçümle ayrıştı** ve imzaları farklı: Mod A'da bütün sinyaller
   bozulur ve bozuk kalır; Mod B'de **tek karelik** bir olaydan sonra hepsi
   normale döner, yalnızca `benzerlik` iz bırakır.
2. **Kopuşu yalnızca PSR ile tanımlamak yetersiz** — doğrulandı: `psr` en iyi
   tek ayırıcı (AUC 0.877) ama Mod B'de kopuştan sonra **yükseliyor** (t=45: 36.7).
3. **Tek sinyal iki işi birden yapmıyor**: erken uyarı (`dcf_kf_ayrim`, 22 kare)
   ile düşük yanlış alarm (`P_konum_iz`/`durum_disi`, 2/15) farklı sinyallerde.
4. **`boyut_orani` operasyonel haberci olarak başarısız** (AUC 0.471).
5. **`benzerlik` Mod B için tek kalıcı sinyal**, ama Mod A'da hiç ölçülmüyor —
   bu bir kod yapısı sonucudur, veri sonucu değil.

> **⚠ KİRLİ YATAK — 5. madde SAĞ KALMADI.** Temiz yatakta `benzerlik`in
> ayrım AUC'si **0.363**, yani şanstan belirgin **kötü**. Mod B hücresi de
> 4'ten 2'ye indi (339/49'un üçü diziyle birlikte gitti); kalan ikisi
> **117/23 · 8×5** (A9'da da Mod B'ydi, sağ kaldı) ve **370/0 · 30×12**
> (yeni dizi — Mod B'nin bağımsız doğrulaması). 1–4. maddeler sağ kaldı.

**Hiçbir eşik seçilmedi, hiçbir davranış değiştirilmedi.**

## 10. DUR

Aşama 3'e (yeniden edinme) geçilmedi.

**Aşama 3'e taşınan girdiler:**
- Recovery tetikleyicisi **tek sinyal olamaz**; en azından bir Mod A yolu
  (ölçüm kaybı / P artışı) ve bir Mod B yolu (`benzerlik` düşüşü) gerekir.
- Mod B'de recovery'yi tetikleyecek hiçbir "yüksek" sinyal yok — takipçi
  kendini sağlıklı sanıyor. Bu, recovery tasarımının en zor kısmıdır.
- `benzerlik`in Mod A'da ölçülmemesi, `_bagimsiz_dogrula`'nın yalnızca KİLİTLİ
  durumda çalışmasından kaynaklanıyor (`izleyici.py:277`). Bunu değiştirmek bir
  davranış değişikliğidir ve ayrı bir A/B gerektirir.

---

# AŞAMA 3 — YENİDEN EDİNME · Deney 3.0: olay tabanı + tetikleyici teşhisi

> ### `AÇIK ÇEVRİM` · `TEŞHİS` · `GT YALNIZCA OFFLINE ETİKETLEME`
> Recovery mekanizması **kurulmadı** · dedektör **koşmadı** · eşik **seçilmedi**
> · tracker davranışı **değişmedi** · `takip/` md5 6/6 aynı.

**Kod:** `gazebo/tani_a9_recovery.py` · **Veri:** `phase3_recovery` (mod_a / mod_b ayrı)
**Tanımlar:** `A9_KABUL_OLCUTU.md` **EK-1** — bu deneyden **önce** yazıldı.

**Ölçüt dosyasına ek:** "stabil kilit" tanımlı değildi. Uydurmak yerine mevcut
ilkellerden türetilip EK-1 olarak eklendi (K1–K4 değişmedi; K5 yanlış-kilit ve
K6 regresyon koşulları eklendi). `recovery süresi` için üst sınır **bilerek
tanımlanmadı** — dağılım olarak raporlanacak.

## S1 — Olay tabanı: recovery ne zaman gerekli?

17 epizot (`IoU < 0.2`, ≥5 kare): **14 kopan** dizilerde, **3 sağlam** dizilerde.

| hücre | rol | baş t | uzunluk | başta KİLİTLİ | PSR | benzerlik | ölçüm yok |
|---|---|---|---|---|---|---|---|
| 117/23 · 10×5 | KOPAN | 12 | 48 | — | 3.0 | 1.00 | 1 |
| 117/23 · 15×7 | KOPAN | 12 | 48 | — | 3.5 | 1.00 | 1 |
| 117/23 · 20×10 | KOPAN | 13 | 47 | — | 2.9 | 1.00 | 1 |
| 117/23 · 8×5 | KOPAN | 12 | 48 | — | 4.1 | 1.00 | 1 |
| 268/31 · 20×10 | KOPAN | 1 | 26 | — | 6.1 | 1.00 | 0 |
| 268/31 · 30×12 | KOPAN | 6 | 12 | — | 5.5 | 1.00 | 0 |
| 268/31 · 8×5 | KOPAN | 24 | 36 | — | 4.8 | 1.00 | 0 |
| 268/31 · 10×5 | KOPAN | 21 | 11 | — | 3.4 | 1.00 | 1 |
| **339/49 · 10×5** | KOPAN | 4 | 12 | **EVET** | **42.4** | **1.00** | 0 |
| **339/49 · 10×5** | KOPAN | 17 | 43 | **EVET** | **27.0** | **1.00** | 0 |
| **339/49 · 15×7** | KOPAN | 34 | 26 | **EVET** | 10.4 | 0.73 | 0 |
| 339/49 · 20×10 | KOPAN | 34 | 26 | — | 7.3 | 0.79 | 0 |
| 339/49 · 30×12 | KOPAN | 43 | 17 | — | 4.9 | 0.44 | 1 |
| 339/49 · 8×5 | KOPAN | 33 | 27 | — | 4.0 | 1.00 | 1 |
| **182/127 · 20×10** | **sağlam** | 36 | 24 | **EVET** | **33.6** | 0.87 | 0 |
| 182/127 · 30×12 | **sağlam** | 11 | 9 | — | 5.4 | 1.00 | 0 |
| **305/5 · 15×7** | **sağlam** | 44 | 8 | **EVET** | **33.7** | **1.00** | 0 |

**İki sonuç:**

1. **"Sağlam" dizi ≠ hiç yanılmayan dizi.** 182/127 ve 305/5'te de recovery
   gerektiren epizotlar var. Kopuş tanımı (merkez hatası) ile epizot tanımı
   (IoU) çakışmıyor; ikisi farklı şeyler ölçüyor.
2. **5/17 epizot `durum == KİLİTLİ` iken başlıyor.** `durum != KİLİTLİ`
   tetikleyicisi bunların **%29'unu kaçırır**. Bu beşinin:
   - **0/5**'inde `ölçüm yok` = 1 → **Mod A sinyal kümesi hiçbirini yakalamıyor**
   - **2/5**'inde `benzerlik < 1.0` → benzerlik yalnızca %40'ını yakalıyor
   - PSR'leri **42.4 / 27.0 / 10.4 / 33.6 / 33.7** — hepsi sağlıklı görünüyor

> **İki ayrı recovery yolu gerektiği ölçümle doğrulandı**, varsayım değil.

## S2 — Arama yarıçapı: Kalman P bunu ÖNGÖRMÜYOR

Son güvenilir merkeze göre gereken yarıçap ile Kalman'ın kendi belirsizliği
(`√tr(P_konum)`):

| geçen kare | n | gerekli p50 | **gerekli p95** | KF belirsizlik p50 | **oran p50** |
|---|---|---|---|---|---|
| 1–5 | 17 | 9.2 | 42.8 | 3.8 | **1.92** |
| 5–10 | 40 | 11.4 | 87.2 | 6.8 | **2.78** |
| 10–20 | 84 | 23.9 | 148.9 | 10.3 | **4.29** |
| 20–40 | 128 | 27.7 | **286.6** | 21.8 | **2.43** |
| 40+ | 45 | 18.1 | 29.3 | **168.3** | **0.14** |

**Kalman P iki yönde birden yanlış:** ilk 20 karede gerekli yarıçapı
**1.9–4.3 kat küçük** tahmin ediyor; 40 kareden sonra **~7 kat büyük**.
Yön tersine dönüyor.

> **`P`, arama alanı boyutlandırması için olduğu gibi kullanılamaz.**
> Aşama 3A'nın "son güvenilir merkez ve belirsizlik alanını al" adımı, mevcut
> belirsizlik kestirimiyle çalışmaz.

### A8 ile çatışma — nicelendi

Gerekli yarıçap p95 **287 px**'e çıkıyor. A8'de 10×5 seviyesinde hedefi ağda
60–90 px'e getiren ROI genişliği **171 px** idi. Yani **doğru büyütme veren ROI,
recovery'nin ihtiyaç duyduğu arama alanını KAPSAYAMAZ.** A8'in kapsama–büyütme
gerilimi recovery için de geçerli ve burada sayısallaştı.

## S3 — `benzerlik` operasyonel tetikleyici olmaya YETMİYOR

| koşul | doğru hedef | yanlış hedef | **AUC** |
|---|---|---|---|
| tüm kareler | n=854, p50=1.00 | n=473, p50=1.00 | **0.525** (şans) |
| **`durum == KİLİTLİ` iken** | n=807, p05=0.87 p25=0.94 p50=1.00 | n=194, p05=0.47 p25=0.55 **p50=0.73 p95=1.00** | **0.722** |

PSR aynı koşulda: doğru p50 43.9 · yanlış p50 35.0 → **AUC 0.637** (daha zayıf).

**Kritik sayı:** `benzerlik == 1.00` oranı — doğru hedefte %66, **yanlış hedefte %40**.
Yani **yanlış kilitli karelerin %40'ı azami değerde oturuyor** ve doğru kilitten
ayırt edilemiyor. Dağılımlar [0.87, 1.00] aralığında ağır biçimde örtüşüyor.

> **Cevap: HAYIR.** `benzerlik`, Mod B için mevcut **en iyi** sinyal (AUC 0.722,
> PSR'nin 0.637'sinden iyi) ama **tek başına yeterli değil**: yanlış kilitli
> karelerin %40'ında hiçbir iz bırakmıyor. Yeni sinyal uydurulmadı; mevcut
> sinyaller arasında bunu kapatan başka bir aday **bulunamadı**.

## Deney 3.0 hükmü

1. **İki ayrı recovery yolu zorunlu** — ölçümle doğrulandı: Mod A sinyalleri
   (ölçüm kaybı) KİLİTLİ-başlangıçlı epizotların **0/5**'ini yakalıyor.
2. **Kalman P arama alanı için kullanılamaz** — hatası yön değiştiriyor.
3. **`benzerlik` Mod B tetikleyicisi olarak yetersiz** — %40 kör nokta.
4. **Recovery arama yarıçapı (p95 287 px), doğru büyütme veren ROI'ye (171 px)
   sığmıyor** — A8'in gerilimi recovery'de de var.
5. **Sağlam dizilerde de epizot var** (3/17); recovery tasarımı bunları da
   kapsamalı, yoksa K6 (regresyon yok) ölçülemez.

**Hiçbir eşik seçilmedi, hiçbir davranış değiştirilmedi, dedektör koşmadı.**

## DUR

Bir sonraki deney (**3.1**), henüz ölçülmemiş asıl soruyu ölçmeli:
**recovery, doğru hedefi bulabiliyor mu?** Yani son güvenilir merkez etrafında
kontrollü geniş arama yapıldığında bağımsız dedektör (a) doğru hedefi
adaylar arasına koyabiliyor mu, (b) çeldiriciyi mi seçiyor.

S2 bu deneyi baştan kısıtlıyor: arama alanı 287 px'e kadar gerekebiliyor ve
Kalman P bunu öngörmüyor — yani arama alanı **başka bir şeyle** boyutlandırılmalı
(örneğin geçen kare sayısına göre), ve o boyutta dedektörün büyütmesi düşecek.
Bu takas ölçülmeden recovery prototipi kurulamaz.

**Gazebo senaryoları bu deneyde kullanılmadı**; gerçek dinamik davranış için
ayrı etiketli bir yatak olarak saklı tutuluyor (final doğrulama ortamı).

---

# Deney 3.1 — Saf aday tarama

> ### `AÇIK ÇEVRİM` · `TEŞHİS` · `GT YALNIZCA OFFLINE ETİKETLEME`
> Recovery tracker'a **entegre edilmedi** · state machine **yok** · eşik **seçilmedi**
> · `takip/` md5 6/6 aynı · commit yok.

**Kod:** `gazebo/tani_a9_31_aday.py` · **Veri:** `phase3_recovery.phase3_1_candidate_search`
17 epizot × 468 kare × 4 arama genişliği × 2 model.

**Başarı tanımı (kullanıcı talimatı):** "kilide döndü" başarı değildir.
Başarı = **doğru GT hedef seçildi ve yanlış hedef seçilmedi.**

**ÜST SINIR UYARISI:** "son güvenilir kare"nin hangisi olduğu GT ile etiketlendi.
Gerçek sistemde bunu tetikleyici seçer ve Deney 3.0 tetikleyicilerin zayıf
olduğunu gösterdi (`benzerlik` AUC 0.722, %40 kör nokta). **Buradaki merkezleme
kalitesi bir üst sınırdır.**

## 1. Arama genişliği ile üç oranın ilişkisi

### A5 baseline (468 kare)

| genişlik | doğru bulundu | **SEÇİM DOĞRU** | seçim yanlış | hiçbiri | aday/kare |
|---|---|---|---|---|---|
| R=160 | 0.186 | 0.184 | 0.047 | **0.767** | 0.4 |
| **R=320** | 0.274 | **0.256** | 0.374 | 0.370 | 1.6 |
| R=640 | 0.124 | 0.073 | **0.654** | 0.274 | 4.0 |
| tam kare | 0.028 | 0.013 | **0.972** | 0.015 | 6.0 |

### A6 UAVDT→VisDrone

| genişlik | doğru bulundu | **SEÇİM DOĞRU** | seçim yanlış | hiçbiri |
|---|---|---|---|---|
| R=160 | 0.145 | **0.145** | 0.038 | 0.816 |
| R=320 | 0.047 | 0.047 | 0.021 | 0.929 |
| R=640 | 0.000 | **0.000** | 0.248 | 0.752 |
| tam kare | 0.000 | **0.000** | 0.350 | 0.650 |

**Takas keskin ve iki uçlu:**
- **Dar arama (R=160):** hedef alanın dışında kalıyor → **%77 hiçbir aday yok**
- **Geniş arama (R=640, tam kare):** büyütme düşüyor *ve* çeldirici sayısı artıyor
  → **%65–97 yanlış seçim**

> **En iyi çalışma noktası R=320'de %25.6 doğru seçim, %37.4 yanlış seçim.**
> Yanlış seçim oranı doğru seçimi **aşıyor**. Kullanıcının tanımladığı başarı
> ölçütüne göre bu bir başarısızlıktır.

A6 daha da kötü: R=640 ve tam karede **doğru seçim 0.000**, hiçbiri %65–93.
A8 §8'in "A6 büyük hedef yeteneğini kaybediyor" bulgusuyla tutarlı — geniş ROI'nin
içeriği çoğunlukla arkaplan.

## 2. Yakın çeldirici testi — güven YANILTIYOR

Doğru hedef ve çeldirici **aynı arama alanına girdiğinde** (A5):

| genişlik | n | doğru seçildi | skor farkı p50 | skor farkı p05 |
|---|---|---|---|---|
| R=160 | 5 | 0.800 | **+0.075** | −0.004 |
| R=320 | 11 | **0.273** | **−0.159** | −0.360 |
| R=640 | 34 | **0.294** | **−0.116** | −0.498 |
| tam kare | 12 | 0.417 | **−0.288** | −0.491 |

**Skor farkı negatif:** çeldirici, doğru hedeften **daha yüksek güvenle** tespit
ediliyor. İkisi birden bulunduğunda dedektör **yaklaşık %70 oranında yanlışını
seçiyor.**

## 3. Aday seçimi için hangi ölçümler ayrıştırıcı? (AUC, bozulma yönüne göre)

| ölçüm | A5 AUC | A6 AUC | doğru p50 | yanlış p50 |
|---|---|---|---|---|
| **merkez uzaklığı** (küçük = doğru) | **0.982** | **0.986** | 23.2 px | 221.6 px |
| **alan oranı** (son güvenilir kutuya göre) | **0.821** | **0.978** | 0.68 | 3.40 |
| **en-boy oranı** | **0.808** | — | 0.94 | 1.21 |
| **dedektör güveni** | **0.381** ✗ | 0.578 | 0.402 | **0.468** |

> ### Dedektör güveni doğru adayı seçmek için KULLANILAMAZ — AUC 0.381, yani şanstan KÖTÜ.
> Doğru adaylar sistematik olarak **daha düşük** güvenle geliyor (0.402 vs 0.468).
>
> Ayrıştırıcı olan şey **geometrik tutarlılık**: son güvenilir merkeze uzaklık
> (AUC 0.982), alan oranı (0.821), en-boy (0.808).

Bu, mevcut seçim mantığının (en yüksek güven) **yanlış olduğunu** ölçümle gösteriyor.

## 4. Dizi bazında (R=320, A5) — recovery yalnızca bir dizide çalışıyor

| dizi | kare | doğru bulundu | **SEÇİM DOĞRU** | seçim yanlış | hiçbiri |
|---|---|---|---|---|---|
| **117/23** | 191 | 0.618 | **0.618** | **0.000** | 0.382 |
| 339/49 | 151 | 0.020 | 0.013 | **0.940** | 0.046 |
| 182/127 | 33 | 0.212 | **0.000** | **1.000** | 0.000 |
| 268/31 | 85 | 0.000 | 0.000 | 0.000 | **1.000** |
| 305/5 | 8 | 0.000 | 0.000 | 0.000 | **1.000** |

- **117/23'te recovery çalışıyor** (%62 doğru seçim, **sıfır** yanlış seçim).
- **339/49 ve 182/127'de tam tersi:** neredeyse her karede yanlış hedef seçiliyor.
  339/49 zaten Mod B (yakın çeldirici) dizisiydi — korkulan sonuç gerçekleşti.
- **268/31 ve 305/5'te dedektör hiçbir şey bulamıyor** (%100 hiçbiri).

## 5. Geçen kare ile ilişki (R=320, A5)

| geçen kare | n | doğru bulundu | SEÇİM DOĞRU | gerekli yarıçap p95 |
|---|---|---|---|---|
| 1–5 | 22 | 0.182 | 0.182 | 69.7 |
| 5–10 | 54 | 0.241 | 0.241 | 216.0 |
| 10–20 | 120 | 0.258 | 0.250 | **424.2** |
| 20–40 | 167 | 0.365 | 0.323 | 333.0 |
| 40+ | 105 | 0.181 | 0.181 | 26.6 |

Gerekli yarıçap 10–20 karede **424 px**'e çıkıyor — R=640 ROI'si bile (±320 px)
bunu kapsamıyor. Ve **zaman geçtikçe doğru seçim oranı iyileşmiyor**; recovery'nin
"biraz bekle, sonra ara" gibi bir kaçış yolu yok.

## 6. Deney 3.1 hükmü

1. **Recovery önermesi bu boyutlarda ÇALIŞMIYOR.** En iyi çalışma noktasında
   doğru seçim %25.6, yanlış seçim %37.4 — yanlış, doğruyu aşıyor.
2. **Kapsama–büyütme gerilimi belirleyici:** dar arama hedefi kaçırıyor (%77
   hiçbiri), geniş arama çeldiriciye kilitleniyor (%65–97 yanlış). A8'in
   gerilimi recovery'de daha da sert.
3. **Dedektör güveni aday seçimi için kullanılamaz** (AUC 0.381, ters yönde).
   **Geometrik tutarlılık kullanılabilir** (merkez uzaklığı AUC 0.982).
4. **Sonuç tek diziye bağımlı:** 117/23'te çalışıyor (%62, sıfır yanlış),
   diğer beşinde çalışmıyor. 117/23 ayrıca 4L'de patolojik işaretli dizi.
5. **A6 modeli recovery için A5'ten kötü** — geniş aramada doğru seçim 0.000.

**Hiçbir eşik seçilmedi, hiçbir kod değiştirilmedi, state machine yazılmadı.**

## 7. DUR

Aşama 3'ün recovery state machine'i **kurulmadı ve kurulmamalı** — 3.1 önermenin
kendisinin çalışmadığını gösterdi. Kalıcı `takip/` değişikliği önerisi **yoktur**.

**Ölçüme dayalı iki sonraki aday (hiçbiri sınanmadı):**
- **Adayları güvene göre değil GEOMETRİK TUTARLILIĞA göre seçmek.** 3.1'in en
  güçlü tek bulgusu bu (AUC 0.982 vs 0.381). Ama bu yeni bir seçim kuralıdır ve
  kendi A/B'sini gerektirir; K5 (yanlış kilit artmayacak) ile sınanmalıdır.
- **Adaptif arama genişliği** — sabit R hiçbir noktada iyi değil: R=160 kaçırıyor,
  R=640 yanlış seçiyor. A8'in adaptif merdiveni burada da gerekli, ama 3.0
  gösterdi ki Kalman P onu boyutlandıramıyor.

---

# Deney 3.2 — Geometrik aday seçimi

> ### `AÇIK ÇEVRİM` · `TEŞHİS` · `GT YALNIZCA OFFLINE ETİKETLEME`
> Hakem yok · recovery state machine yok · kalıcı kod değişikliği yok ·
> `takip/` md5 6/6 aynı · commit yok.

**Kural:** `docs/architecture/A9_3_2_SECIM_KURALI.md` — **koşumdan önce** yazıldı.
`G = max(d_norm, a_norm, r_norm)`, kapı `G ≤ 1.0`, seçim `argmin G`, geçen yoksa
**çekimser**. Ağırlık seçilmedi (sonsuz-norm), eşik normalizasyonun tanımı.
Ölçekler mevcut sabitler: `MAX_HIZ=35` (`izleyici.py`), `2.6` (`tespit.py:122`).

**Dedektör neden yeniden koşuldu:** 3.1 yalnızca operasyonel-göreli öznitelikleri
sakladı; **mutlak aday kutuları yok**, dolayısıyla ORACLE referansı ve en-boy
*tutarlılığı* hesaplanamıyordu. KOL V zaten yeni koşum gerektiriyordu.
*Doğrulama:* `doğru havuzda` R=320'de **0.274** — 3.1'in değeriyle birebir aynı,
yani yeniden koşum 3.1'in aday havuzunu yeniden üretti.

**ÜST SINIR:** KOL R'de "son güvenilir kare" GT ile belirlendi (3.1 ile aynı).

## 1. KOL R — seçim sonucu (A5 baseline)

| genişlik | n | DOĞRU | YANLIŞ | ÇEKİMSER | doğru havuzda | kaçırılan |
|---|---|---|---|---|---|---|
| R=160 | 468 | 0.186 | **0.043** | 0.769 | 0.186 | 0.000 |
| **R=320** | 468 | **0.254** | 0.355 | 0.391 | 0.274 | 0.070 |
| R=640 | 468 | 0.113 | 0.440 | 0.447 | 0.124 | 0.086 |
| merdiven | 468 | 0.152 | 0.382 | 0.466 | 0.162 | 0.066 |

**3.1 ile aynı genişlikte (R=320) karşılaştırma:**

| | 3.1 (güven) | 3.2 (geometrik) |
|---|---|---|
| doğru seçim | 0.256 | 0.254 |
| **yanlış seçim** | 0.374 | **0.355** |
| çekimser / hiçbiri | 0.370 | 0.391 |

> **K5 (yanlış kilit artmayacak): sağlandı ama marjinal** — yanlış seçim
> 0.374 → 0.355. Doğru seçim değişmedi.

### Neden kural işe yaramadı — darboğaz yer değiştirdi

`doğru havuzda` R=320'de yalnızca **0.274**. ORACLE referansında `kaçırılan`
**%1.6** — yani **seçici neredeyse optimal çalışıyor**; tavan, doğru hedefin
aday havuzunda hiç olmaması.

> 3.1: *"seçim bozuk"* (güven AUC 0.381). **3.2: seçim düzeltildi (G AUC 0.944)
> ve sonuç değişmedi — çünkü bağlayıcı kısıt artık DEDEKTÖR RECALL'ü.**

## 2. Bileşen ayrım gücü — ön hipotez DOĞRULANDI

| bileşen | **operasyonel AUC** | oracle AUC | yorum |
|---|---|---|---|
| **d** (merkez uzaklığı) | **0.951** | 0.952 | **boyut bozulmasından bağımsız** ✓ |
| a (alan) | 0.806 | **0.959** | operasyonelde **−0.153** ✗ |
| r (en-boy) | 0.823 | 0.930 | operasyonelde **−0.107** ✗ |
| G (bileşik) | 0.944 | 0.998 | |
| **güven** | **0.421** | — | 3.1'deki 0.381 ile tutarlı, hâlâ şans altı |

Kural dosyasında yazılı hipotez birebir gerçekleşti: `a_norm` ve `r_norm`
`ref_w, ref_h`'ye bölündüğü için 117/23'ün şişmiş `bho`'sundan zarar görüyor;
`d_norm` görmüyor.

> **Operasyonel referansta ayakta kalan tek bileşen MERKEZ UZAKLIĞIDIR.**

## 3. Dizi-bırak-dışarı — sonuç tek diziye bağlı

| dışarıda bırakılan | n | DOĞRU | YANLIŞ | ÇEKİMSER |
|---|---|---|---|---|
| **117/23** | 277 | **0.000** | 0.599 | 0.401 |
| 182/127 | 435 | 0.163 | 0.336 | 0.501 |
| 268/31 | 383 | 0.185 | 0.467 | 0.347 |
| 305/5 | 460 | 0.154 | 0.389 | 0.457 |
| 339/49 | 317 | 0.224 | 0.145 | 0.631 |

**117/23 çıkarıldığında doğru seçim 0.000.** Dizi bazında: 117/23 → 0.372 doğru /
0.068 yanlış; 339/49 → 0.000 doğru / **0.881 yanlış**; 182/127 → 0.000 / **1.000**;
268/31 ve 305/5 → **%100 çekimser** (dedektör hiçbir şey bulamıyor).

> **Bütün doğru seçimler tek diziden geliyor — 3.1 ile aynı sonuç, LOSO ile
> tartışmasız hale geldi.**

## 4. Yakın çeldirici — 3.2'nin tek net kazancı

Havuzda doğru **ve** yanlış aday birlikteyken (operasyonel, merdiven):

| | 3.1 (güven) | **3.2 (geometrik)** |
|---|---|---|
| doğru seçildi | 0.273 | **0.737** |
| n | 11 | 19 |

**Çeldirici varken doğru seçim %27 → %74.** A6'da n=2, ikisi de doğru.
Küçük örneklem, ama yön güçlü ve 3.1'in "güven yanıltıyor" bulgusuyla tutarlı.

## 5. Çekimserliğin bedeli

16 epizodun **yalnızca 4'ünde** hiç doğru seçim gerçekleşiyor. Gerçekleştiğinde
gecikme p50 **3.5 kare**, p95 5.8 kare. Yani çekimserlik ucuz — ama epizotların
%75'i zaten hiç toparlanmıyor.

## 6. A6 modeli — hata yerine çekimserlik

| genişlik | DOĞRU | YANLIŞ | ÇEKİMSER |
|---|---|---|---|
| R=160 | 0.145 | **0.009** | 0.846 |
| R=640 | 0.000 | 0.162 | 0.838 |
| merdiven | 0.038 | 0.132 | 0.825 |

A6 neredeyse hiçbir şey bulamıyor (%83–93 çekimser) ama **yanlış seçimi de çok
düşük**. Geometrik kapı A6'da bileşik G AUC **1.000** veriyor — ayırt ediyor,
ama ayıracak aday yok.

## 7. KOL V — doğrulama: 3.2'nin en güçlü sonucu

Takipçi KİLİTLİ iken, her N karede takipçinin ROI'sinde dedektör koşup
`min G` hesaplandı.

| | n | kanıt yok | doğru p50 | yanlış p50 | **AUC(min_G)** | ek maliyet/kare |
|---|---|---|---|---|---|---|
| **N=5** | 246 | 0.309 | 0.285 | **4.606** | **0.895** | 8.47 ms |
| N=10 | 112 | 0.330 | 0.281 | 4.551 | 0.878 | 4.14 ms |

**Karşılaştırma (Aşama 2/3.0, aynı KİLİTLİ koşulu):**
`benzerlik` 0.722 · `PSR` 0.637 · **`min_G` 0.895**

> **`min_G`, Mod B için bugüne kadar ölçülen EN GÜÇLÜ sinyaldir.**
> Doğru/yanlış ayrımı 16 kat (0.285 vs 4.606).

### Ama üç ciddi sınır

**a) Eşik doğrulama için uygun değil.** Önceden yazılmış `G ≤ 1.0` kapısıyla
**sağlam dizilerde yanlış alarm %48** (takipçi doğruyken min_G>1.0). AUC iyi
ama bu çalışma noktası kullanılamaz. *Eşik yeniden ayarlanmadı — yasak.*

> **⚠ KİRLİ YATAK — SAĞ KALMADI.** Temiz yatakta (A10.1/D1) aynı kapı, aynı
> ayarlarla **51 kanıtlı noktanın 0'ında** ihlal veriyor: **%48 → %0**.
> O %48, kompozit arkaplandaki **gerçek hedefin** dedektör tarafından
> bulunmasından geliyordu. Ayrıntı: `A10_1_D1_TEMIZ_YATAK.md` §5.

**b) Dedektör körlüğü küçük hedefte doğrulamayı da kör ediyor:**

| seviye | kanıt yok |
|---|---|
| 30×12 | 0.064 |
| 20×10 | 0.222 |
| 15×7 | 0.373 |
| 10×5 | 0.340 |
| **8×5** | **0.509** |

8×5'te doğrulama noktalarının **yarısında hiç kanıt yok**.

**c) Kanonik Mod B örneğinde tam kritik anda kör.** 339/49 · 15×7, geçiş t=33:

| t | takipçi IoU | min_G |
|---|---|---|
| 20 | 0.42 | 5.067 |
| 25 | 0.37 | **kanıt yok** |
| 30 | 0.42 | **kanıt yok** |
| **35** | **0.00** | **kanıt yok** |
| 40 | 0.00 | kanıt yok |
| 45 | 0.00 | 5.751 |

Geçişin gerçekleştiği pencerede dedektör hiçbir aday üretmiyor; ilk kanıt
**12 kare sonra** geliyor.

## 8. Tek ilkel mi, iki kural mı?

**Tek ilkel yeterli:** aynı `G` iki kolda da güçlü bir **sıralama** sinyali —
seçimde AUC 0.944, doğrulamada 0.895.

**Ama tek çalışma noktası yeterli değil:** `G ≤ 1.0` seçim için uygun
(çekimser-ağırlıklı, yanlış seçim düşük), doğrulama için fazla katı
(%48 yanlış alarm). **Bir ilkel, iki ayrı çalışma noktası.**

## 9. Deney 3.2 hükmü

1. **Geometrik seçim, güven tabanlı seçimden ölçülebilir biçimde iyi** —
   G AUC 0.944 vs güven 0.421; yakın çeldiricide %27 → %74.
2. **Ama recovery'yi çalışır hale GETİRMİYOR.** Darboğaz seçimden **dedektör
   recall'üne** kaydı: doğru havuzda %27, oracle referansta kaçırılan %1.6.
3. **Operasyonel referansta ayakta kalan tek bileşen merkez uzaklığıdır**
   (0.951 ≈ oracle 0.952); alan ve en-boy `bho` şişmesinden zarar görüyor.
   Ön hipotez doğrulandı.
4. **LOSO: 117/23 çıkınca doğru seçim 0.000.** Sonuç tek diziye bağlı.
5. **KOL V en güçlü sonuç:** `min_G` Mod B için 0.895 — `benzerlik` (0.722) ve
   `PSR`'yi (0.637) açık farkla geçiyor. Ama önceden yazılmış eşik %48 yanlış
   alarm veriyor, 8×5'te %51 kanıt yok, ve kanonik Mod B geçişinde 12 kare kör.
6. **Maliyet:** N=10'da 4.14 ms/kare, N=5'te 8.47 ms/kare (masaüstü CPU).
   Pi Zero 2 W'ye **extrapolasyon yapılmadı**.

**Hiçbir eşik ayarlanmadı, hiçbir kod değiştirilmedi.**

## 10. Sınırlar

13 kopan hücre · Mod B yalnızca 4 örnek · yakın çeldirici n=19 · KOL R'de
"son güvenilir kare" GT ile tanımlı (üst sınır) · 117/23 Deney 4L'de patolojik
işaretli · Gazebo kullanılmadı (final doğrulama ortamı olarak ayrı).

## 11. DUR

Hakem, recovery mekanizması ve kalıcı değişiklik yapılmadı.

**Ölçüme dayalı iki sonraki aday (hiçbiri sınanmadı):**
- **KOL V için ayrı çalışma noktası** — `min_G` bir Mod B doğrulayıcısı olarak
  en güçlü sinyal, ama eşiği seçilmemiş durumda. Bu, kendi ön-kayıtlı ölçütüyle
  ayrı bir deney gerektirir.
- **Dedektör recall'ü** artık hem recovery'nin hem doğrulamanın tavanı
  (%27 havuz, 8×5'te %51 kanıt yok). A8'in adaptif ROI'si bu tavanı yükseltmek
  için var olan tek ölçülmüş araç; ama A8 da açık çevrimdi.

---

# AŞAMA 3 — Deney 3.3: ZAMANSAL KALICILIK

> **⚠ KİRLİ YATAK — DAYANAĞI ÇÖKTÜ (A10.1/D1).** 3.3'ün bütün kurgusu iki
> sayının üstüne kuruluydu: sağlam dizilerdeki **%48 ihlal oranı** (X eşiğinin
> ve "nokta düzeyi hiç iyileşmiyor" hükmünün tabanı) ve **339/49 · 15×7**
> kanonik Mod B hücresi (§5'in tamamı). Temiz yatakta ihlal oranı **%0**,
> 339/49 ise tabandan **düştü** — o dizide geçerli kompozit yatak kurulamıyor.
> **Bu bölüm çürütülmedi, ölçüm tabanı geçersizleşti.** Sayıları yeni bir
> karara dayanak yapılamaz. Sağ kalan tek yapısal iddia: kanıt-yok deseninin
> sayacı sürüklemesi (temiz yatakta kanıt yok hâlâ %43).

> ### `AÇIK ÇEVRİM` · `TEŞHİS` · `GT YALNIZCA OFFLINE ETİKETLEME`
> **Cevap: HAYIR.** Zamansal kalıcılık, KOL V'nin çalışma noktası problemini
> çözmüyor. Ön-kayıtlı seçim kuralı SIFIRLA kolunda **k = 1**'i, yani 3.2'nin
> zaten bildirdiği çalışma noktasını seçiyor; DONDUR kolunda **k = 3**'ü seçiyor
> ve iki kol arasında seçim yapacak bir kural ön-kayıtta **yok**. Katı K6
> okumasında (sağlam hücrelerde sıfır yanlış tetikleme) **hiçbir k geçmiyor**.

**Tarih:** 2026-09-03 · **Kod:** `gazebo/tani_a9_3_3.py` (yeni, salt okunur)
**Ön-kayıt:** `docs/architecture/A9_3_3_ONKAYIT.md` — **koşumdan önce** yazıldı.
**Bu turda:** eşik değişmedi (`G ≤ 1.0`) · takipçi davranışı değişmedi · yeni
mekanizma eklenmedi · **YOLO hiç koşmadı** · commit/push yok.
**Bütünlük:** `takip/*.py` **6/6 md5 aynı**. Değişen tek şey yeni salt-okunur
dosya `gazebo/tani_a9_3_3.py`.

## 1. Yatak — dedektör neden yeniden koşmadı

3.3'ün değişkeni `k`, dedektör çıktısı değil. Bu yüzden 3.2'nin **saklanmış KOL V
kayıtları** (`experiment_3_2.kol_v`) yeniden kullanıldı; aynı `min_G` serisi
üzerinde farklı bir sayaç işletildi. Böylece 3.2 ile yatak **bit düzeyinde**
aynıdır. Bedeli açıktır ve kabul edilmiştir: **3.3, 3.2 yatağının dışına
çıkamaz** — yeni dizi, yeni seviye, daha sık örnekleme yok.

**Geçerlilik denetimi (ön-kayıt §8):** epizotların içine düşen 37 KOL V
noktasının **37/37**'sinde `takipci_iou < 0.2`. Kayıtlar epizot tabanıyla aynı
takipçi izlerinden geliyor. **GEÇTİ.**

**3.2'nin yeniden üretimi:** sağlam dizilerde, takipçi doğruyken, kanıt taşıyan
noktalarda ihlal oranı **0.4804** — 3.2'nin bildirdiği **%48** birebir çıktı.
Yatak doğru bağlandı.

## 2. Ana tablo — A5 baseline · N = 5 (birincil)

Yanlış alarm ölçütü **yükselen kenar** sayar (ön-kayıt §5.2); nokta düzeyi
oranlar 3.2 ile kıyaslanabilsin diye **betimleyici olarak** yanına yazıldı.

**SIFIRLA** (kanıt yok → sayaç sıfırlanır)

| k | yanlış alarm (kenar) | kirli hücre | nokta düzeyi ihlal | alarm durumu | Mod B yakalama | gecikme p50 / p95 |
|---|---|---|---|---|---|---|
| **1** | **0.054** (7/130) | 6/15 | 0.480 | 0.377 | **4/4** | **8.5** / 16.95 |
| 2 | 0.046 (6/130) | 5/15 | 0.480 | 0.323 | 3/4 | 11.0 / 21.80 |
| 3 | 0.039 (5/130) | 4/15 | 0.480 | 0.277 | 2/4 | 19.5 / 27.15 |
| 5 | 0.039 (5/130) | 5/15 | 0.480 | 0.200 | 1/4 | 21.0 / 21.0 |

**DONDUR** (kanıt yok → sayaç dondurulur)

| k | yanlış alarm (kenar) | kirli hücre | Mod B yakalama | gecikme p50 |
|---|---|---|---|---|
| 1 | 0.054 (7/130) | 6/15 | 2/4 | 9.5 |
| 2 | 0.046 (6/130) | 5/15 | 2/4 | 14.5 |
| **3** | **0.039** (5/130) | 4/15 | **3/4** | 11.0 |
| 5 | 0.039 (5/130) | 5/15 | 3/4 | 21.0 |

X = **%5.5** (N = 5). **Dört k da X'i geçiyor** — ve bu, ölçütün bu yatakta
ayırt etmediği anlamına gelir, k'ların iyi olduğu anlamına değil (§4).

**Kirli hücre sayısı k ile monoton değil** (SIFIRLA'da 6→5→4→**5**): büyük k'da
yükselen kenar başka bir karede oluşur ve o kare `takipci_iou ≥ 0.5` olabilir.
Bu bir ölçüt artefaktıdır, sinyalin özelliği değil.

## 3. Nokta düzeyi HİÇ İYİLEŞMİYOR — ölçütün ne ölçtüğü

| | k=1 | k=2 | k=3 | k=5 |
|---|---|---|---|---|
| ihlal oranı (kanıt taşıyan payda) | 0.480 | 0.480 | 0.480 | 0.480 |
| **alarm durumundaki nokta oranı** | 0.377 | 0.323 | 0.277 | **0.200** |
| yanlış alarm (yükselen kenar) | 0.054 | 0.046 | 0.039 | 0.039 |

> **3.2'nin %48'i, 3.3'te de %48'dir.** `k` ihlal oranını değiştirmez — ihlaller
> **uzun kesintisiz seriler** halinde gelir. `k = 5`'te bile sağlam dizilerdeki
> noktaların **%20'si** alarm durumundadır. %5.4 → %3.9 düşüşü, farklı bir
> büyüklüğün (kenar sayısı) ölçülmesinden gelir; sinyalin ayırt ediciliğinin
> artmasından değil.

**Ölçüt duyarlılığı — hüküm kenarda:** ön-kayıt §5.2 yanlış tetiklemeyi yalnızca
`takipci_iou ≥ 0.5` olan noktalarda sayar. Sağlam hücrelerdeki **bütün** yükselen
kenarlar sayılırsa (payda 163):

| k | ölçüte göre | hepsi sayılsa | X = %5.5 |
|---|---|---|---|
| 1 | 0.054 | **0.068** | **kalırdı** |
| 2 | 0.046 | 0.061 | kalırdı |
| 3 | 0.039 | 0.055 | kıl payı |
| 5 | 0.039 | 0.043 | geçerdi |

k = 1'in geçmesi, ön-kayıtta seçilmiş bir dışlamaya bağlıdır. **Eşik
ayarlanmadı**; bu duyarlılık sonuç olarak raporlanıyor.

## 4. Katı ölçüt — hiçbir k geçmiyor

Ön-kayıt §5.3'ün katı eşlikçisi: sağlam dizilerde **hiçbir** hücrede yanlış
tetikleme olmaması. Sonuç: **15 sağlam hücrenin 4–6'sı her k'da kirli.**

> **K6'nın harfi harfine okunuşunda 3.3'ün çalışma noktası YOKTUR.**
> Gevşek ölçüt (X = %5.5) dört k'yı da geçiriyor, katı ölçüt dördünü de
> reddediyor. Aradaki fark, X'in "yanlış recovery 5.8 karede toparlanır"
> varsayımıdır — 3.1/3.2 epizotların %75'inin **hiç** toparlanmadığını ölçmüştü.

## 5. Kanonik Mod B — yakalama bir yanılsama (en önemli sonuç)

339/49 · 15×7, geçiş `bas_t = 34` (Aşama 2'nin `kopus_karesi` değeri de 34;
3.2 metninde t ≈ 33 diye anılmıştı).

| t | min_G | kanıt | takipçi IoU |
|---|---|---|---|
| 5 | **6.81** | var | 0.323 |
| 10 | **7.28** | var | 0.327 |
| 15 | — | **yok** | 0.374 |
| 20 | **5.07** | var | 0.418 |
| 25 / 30 | — | **yok** | 0.374 / 0.415 |
| **35 / 40** | — | **yok** | **0.000** |
| 45 | **5.75** | var | 0.000 |
| 50 | — | **yok** | 0.000 |
| 55 | **5.80** | var | 0.000 |

**`min_G` bu hücrede kanıt taşıyan HER noktada kapıyı ihlal ediyor — geçişten
29 kare önce, t = 5'ten itibaren.** Kopuş anında sinyalde bir *değişiklik* yok;
zaten sürekli ihlal halinde.

Sonuç: SIFIRLA · k = 1'in "11 kare gecikmeyle yakaladı" satırı, t = 45'teki
tetiklemedir — ve o tetikleme, t = 25–40 arasındaki **kanıt yok** noktalarının
sayacı sıfırlamasıyla yeniden kurulmuş bir kenardır.

> **Tetikleme zamanını belirleyen şey takipçinin kopması değil, dedektörün
> körleşme deseni.** Aynı seride DONDUR · k = 1 hiç yakalamıyor (t = 5'te
> tetikliyor, alarm hiç düşmediği için geçişten sonra yeni kenar yok);
> DONDUR · k = 5 t = 55'te "yakalıyor" (gecikme 21).

**Yakalamanın k ile monoton olmaması** (DONDUR: 2 → 2 → 3 → 3) bunun ikinci
belirtisidir: küçük k'da alarm **geçişten önce** kalkıp bir daha inmiyor, hücre
"yalnızca erken" sayılıyor. Bu, "yakalama = geçişten sonraki yükselen kenar"
tanımının bir artefaktıdır.

**Neden kronik ihlal:** `G = max(d_norm, a_norm, r_norm)` ve bu hücrede takipçi
kutusu `bho` şişmesiyle bozuk; `a_norm`/`r_norm` `ref_w, ref_h`'ye bölündüğü için
3.2 §9.3'te ölçülen bozulmayı taşıyor. **Boyut arızası, merkez doğrulayıcısını
da kirletiyor** — A/B-3'ün ve 4U'nun aynı zinciri.

## 6. KİLİTLİ-başlangıçlı 5 epizot (3.0'ın kör noktası)

| epizot | rol | bas_t | ilk uyarı (SIFIRLA) | ilk uyarı (DONDUR) |
|---|---|---|---|---|
| 339/49 · 15×7 | KOPAN | 34 | k=1 → t=45 (+11); k≥2 **yok** | yalnızca k=5 → t=55 (+21) |
| 339/49 · 10×5 | KOPAN | 4 | k=1 → +1 · k=2 → +6 · k=3 → +11 · k=5 **yok** | aynı |
| 339/49 · 10×5 | KOPAN | 17 | k=1 → +18 · k=2 → +23 · k=3 → +28 · k=5 → +8 | yalnızca k=5 → +8 |
| 305/5 · 15×7 | **sağlam** | 44 | k=2 → +1 · k=3 → +6 | aynı |
| 182/127 · 20×10 | **sağlam** | 36 | k=1 → +19 · k=5 → +4 | yalnızca k=5 → +4 |

**Hiçbir k beş epizodun hepsini yakalamıyor.** k = 1 dördünü görüyor (biri
+19 kare gecikmeli), k = 5 üçünü. Gecikmenin k ile monoton artmaması (üçüncü
satırda k=5 → +8, k=3 → +28) yine kanıt-yok deseninin sayacı sürüklemesidir.

## 7. A6 modeli — sıfır yanlış alarm, çünkü kör

A6 kolunda yanlış alarm k = 5'te tam **0.000** ve Mod B yakalama her k'da
**0/4**. Sebep ölçüldü:

| A6 | kanıt taşıyan nokta |
|---|---|
| sağlam hücreler (takipçi doğru) | **6 / 130** |
| 4 Mod B hücresi | **3 / 44** |
| 339/49 · 15×7 ve 10×5 | **0 / 22** |

Kanıt taşıyan 6 noktanın **6'sı da** kapıyı ihlal ediyor (oran 1.000).
**A6'nın temiz görünmesi doğruluk değil, körlüktür** — A7 §8'in "A6 ROI altında
farklı davranıyor" bulgusunun doğrulanması. A6 bu görevde doğrulayıcı olarak
kullanılamaz.

## 8. LOSO — seçim tek diziye dayanıyor

| çıkarılan | SIFIRLA seçim | DONDUR seçim | not |
|---|---|---|---|
| 137/12 | **YOK** (havuz boş) | **YOK** (havuz boş) | hiçbir k X'i sağlamıyor |
| 305/5 | 1 | 3 | |
| 182/127 | 1 | 3 | |
| 117/23 | 1 | **5** | Mod B tabanı 3 hücreye iner |
| 268/31 | 1 | 3 | |
| 339/49 | 1 | 1 | **Mod B tabanı 1 hücreye iner** |

İki ayrı kırılganlık:

1. **137/12 çıkınca çalışma noktası kalmıyor.** Yanlış alarm paydasının büyük
   kısmını o dizi taşıyor; çıkarılınca oran %6.5–9.1'e çıkıp X'i aşıyor.
2. **Mod B tabanının 4 hücresinin 3'ü 339/49'dan geliyor.** O dizi çıkarılınca
   geriye 117/23 · 8×5 kalıyor — tek hücre. 3.1/3.2'de bağımlılık 117/23'teydi,
   burada 339/49'a kaydı; **tek diziye bağımlılık devam ediyor.**

DONDUR kolunun seçimi foldlar arasında 1 / 3 / 5 diye savruluyor; SIFIRLA kolu
k = 1'de sabit — ama k = 1 kontrol kolunun ta kendisidir.

## 9. N = 10 kolu

X = %12.2 (aynı bütçe, hücre başına 5 nokta). Dört k da geçiyor.
SIFIRLA: k=1 → 3/4 yakalama (gecikme p50 **6.0**), k=3 ve k=5 → **0/4**.
DONDUR: k=1 → 2/4, k=2 → 3/4 (p50 16.0), k=5 → 0/4.
Seyreltme yakalamayı hızlandırmıyor, yalnızca kanıt-yok deseninin sayaç
üzerindeki etkisini büyütüyor.

## 10. Deney 3.3 hükmü

1. **Zamansal kalıcılık KOL V'nin çalışma noktasını üretmiyor.** Ön-kayıtlı
   kural SIFIRLA'da `k = 1`'i — 3.2'nin zaten bildirdiği noktayı — seçiyor.
2. **Nokta düzeyi ayırt edicilik hiç değişmiyor:** ihlal oranı dört k'da da
   **0.480**. `k = 5`'te bile sağlam noktaların %20'si alarmda.
3. **Katı K6 okumasında hiçbir k geçmiyor** (15 sağlam hücrenin 4–6'sı kirli).
   Gevşek X ise dördünü de geçiriyor; ölçüt bu yatakta **ayırt etmiyor**.
4. **Yakalama bir yanılsama:** kanonik Mod B hücresinde `min_G` geçişten
   29 kare önce zaten sürekli ihlalde. Tetikleme zamanını **dedektörün körleşme
   deseni** belirliyor, takipçinin kopması değil.
5. **Kanıt-yok politikası sonucu belirliyor:** SIFIRLA ile DONDUR aynı k'da
   farklı hücreleri yakalıyor; yakalama k ile monoton değil. Bu, sinyalin değil
   dedektör körlüğünün ölçüldüğünün üçüncü kanıtıdır.
6. **A6 bu görevde kör:** sağlam hücrelerde 130 noktanın 6'sında kanıt var.
7. **LOSO iki yerden kırılıyor:** 137/12 çıkınca çalışma noktası yok;
   Mod B tabanının 3/4'ü 339/49'dan.
8. **Ön-kayıt eksiği (kendi payıma):** iki politika arasında seçim yapacak kural
   yazılmamıştı. SIFIRLA k=1 ile DONDUR k=3 arasında **sonuca bakarak** seçim
   yapılmayacaktır; bu eksik, sonucun kendisi olarak raporlanır.

**Hiçbir eşik ayarlanmadı, hiçbir kod değiştirilmedi, dedektör koşmadı.**

## 11. Sınırlar

3.2 yatağının dışına çıkılmadı (yeni dizi/seviye yok) · Mod B tabanı 4 hücre,
3'ü tek diziden · doğrulama çözünürlüğü N = 5 kare (kopuş anını ±5 kareden iyi
göremez) · hücre başına en çok 11 nokta, k = 5 bunun yarısını tüketiyor ·
yanlış alarm ölçütü yükselen kenar sayar ve `takipci_iou ≥ 0.5` dışlaması
hükmü kenarda değiştiriyor (§3) · bütün ölçümler **açık çevrim** · Gazebo
kullanılmadı · Pi Zero 2 W'ye ekstrapolasyon **yapılmadı** (3.3 ek hesap
maliyeti getirmez: aynı `min_G` üzerine bir tamsayı sayaç).

## 12. DUR

Hakem, recovery mekanizması, state machine ve kalıcı `takip/` değişikliği
yapılmadı.

**Ölçüme dayalı sonraki adaylar (hiçbiri sınanmadı):**

- **`min_G`'yi boyuttan arındırmak.** §5 ölçtü: kanonik Mod B hücresinde ihlal
  kronik ve kaynağı `a_norm`/`r_norm`'un `ref_w, ref_h`'ye bölünmesi. Yalnızca
  `d_norm` ile kurulan bir doğrulayıcı (3.2 §9.3: operasyonel referansta ayakta
  kalan tek bileşen, AUC 0.951) bu kirlenmeden bağımsız olabilir. Kendi
  ön-kayıtlı ölçütünü gerektirir.
- **Doğrulama çözünürlüğünü artırmak.** N = 5 kare, 5 karelik "stabil kilit"
  konvansiyonuyla aynı mertebede; kopuş anını göremiyor. N = 1–2 ölçümü
  3.2'nin maliyet tablosuyla (8.47 ms/kare @ N=5) birlikte değerlendirilmeli.
- **Dedektör körlüğü hâlâ tavan.** 3.2'nin hükmü 3.3'te doğrulandı: yalnızca
  körlük deseni değişse tetikleme zamanı da değişiyor.

---

# EK-2 — "57 px" ile "20 px" çelişmiyor: hangi sayı hangi bağlamda

**Eklendiği tarih:** 2026-09-03 · **Yeni ölçüm YAPILMADI** — üç yayımlanmış
raporun (A5.2, A6, A7) kendi tabloları karşılaştırıldı.

Projede **birbirine karıştırılabilecek üç ayrı taban** var. Üçü de doğru; üçü
farklı şeyi ölçüyor.

| sayı | ne | yatak / girdi yolu | ölçüt | kaynak |
|---|---|---|---|---|
| **57 px** | dedektör **edinme** tabanı | A5.2 tuvali **640×360**, **tam kare** | Y8-D **tam bataryası**: recall@0.5 ≥ 0.80 **her iki birincil dizide** + IoU + kilit + drift yok | `A5_KUCUK_HEDEF_BENCHMARK.md` (Y8-D), `A6_..._FINAL_BENCHMARK.md` §11 |
| **40 px** | dedektör edinme tabanı | A7 tuvali **1280×720 sensör**, **tam kare** | yalnız recall@0.5 ≥ 0.80, her iki dizide | `A7_ROI_KUCUK_HEDEF_TESHIS.md` §3 |
| **20 px** | dedektör edinme tabanı | A7 tuvali, **ROI kırpma + doğru büyütme** (A5'te 4×, A6'da 2×) | aynı recall ölçütü | `A7…` §3 |
| **14–20 px** | **takipçi süreklilik** sınırı | dedektör **yok**; takipçi 0. karede kilitli, hedef küçülüyor | ort. IoU / kilit oranı çöküşü | `A7…` §4 |

## Neden farklı çıkıyorlar

1. **Tuval.** A5.2'nin 640×360 tuvalinde "10 px hedef", 146 px'lik gerçek yamanın
   küçültülmüş halidir; **bilgi orada yoktur**. A7'nin ilk denemesi tam bu yüzden
   **reddedildi** (A7 §1): o tuvalde ROI oracle bile recall 0.000 veriyor.
   Düzeltilmiş yatak sensör çözünürlüğündedir.
2. **Girdi yolu.** 57 ve 40 **tam kare** sayılarıdır; 20, ROI kırpıp doğru
   büyütmeyle elde edilir. A7 §2 ölçtü: dedektör hedefi ağ girdisinde **~40–130
   px**'e düştüğünde çalışıyor, en iyisi 60–90 px. Büyütme bunu ayarlayan şeydir.
3. **Ölçüt bataryası.** 57, Y8-D'nin **tam bataryasından** çıkar; 40 ve 20
   yalnız recall'dendir. Aynı yatakta bile daha katı ölçüt daha büyük taban verir.
4. **Merdiven granülerliği.** A5.2'nin basamaklarında **40 yoktu** (57'nin altı
   30'du). A6'da 40×15 vardı ve 117/23'te 0.925'e çıktı, ama 137/12'de 0.700'de
   kaldı; kural **her iki dizide birden** 0.80 istediği için A6 de 57'de kaldı.

## A9'u hangisi bağlıyor

A9'un KOL V'si dedektörü **A8'in adaptif ROI kuralıyla, sensör tuvalinde**
koşturur. Dolayısıyla A9 için geçerli edinme tabanı **A7'nin 20 px'i**dir;
**57 px bu bağlamda geçerli değildir.**

Bu, 3.2/3.3'teki "kanıt yok" oranlarını da açıklıyor: 30×12 seviyesinde %6.4,
8×5 seviyesinde %50.9. 20 px'in **üstünde** dedektör çalışıyor, altında körleşiyor
— aynı sınır, aynı yatak.

**Not:** A9'un daha önceki metinlerinde "minimum güvenilir tespit 57 px" ifadesi
geçtiyse, o A5.2/A6'nın **tam kare** sayısıdır ve ROI'li A9 yatağına doğrudan
taşınamaz. Bu ek, o taşımayı yasaklamak için yazıldı.
