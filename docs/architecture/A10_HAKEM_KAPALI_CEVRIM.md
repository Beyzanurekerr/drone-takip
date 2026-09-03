# A10 — KAPALI ÇEVRİM HAKEM PROTOTİPİ

> ### `KAPALI ÇEVRİM` · dedektör → hakem → takipçi
> **HÜKÜM: REDDEDİLDİ.** Altı kolun hiçbiri K1–K6'yı geçmiyor. `takip/hakem.py`
> **kalıcılaştırılmıyor**, varsayılan davranış değişmiyor.
> Kazanç yok, **net kayıp var**: ortalama IoU H0'da **0.4262**, en iyi hakem
> kolunda **0.3978**. Oracle referansla bile (**0.4090**) taban aşılamıyor.

**Tarih:** 2026-09-03 · **Ön-kayıt:** `A10_ONKAYIT.md` (+EK-1 donmuş taban,
EK-2 Mod A sürüm 2, EK-3 model kolu) — hepsi **koşumdan önce** yazıldı.
**Kod:** `takip/hakem.py` (yeni) · `takip/izleyici.py` (yalnızca arayüz) ·
`gazebo/bench_a10_hakem.py` · **Veri:** `cikti/a10_hakem.json`
**Bu turda:** eğitim yok · ağırlık/imgsz/SAHI yok · eşik ayarı yok · 5×5 yok ·
**sonuca göre hiçbir sabit değiştirilmedi** · push yok.

---

## 1. Bütünlük

**`takip/` md5, koşum öncesi = koşum sonrası** (`md5_degismedi: true`), altı kol
için **aynı dosyalar**; kollar arası tek fark hakem yapılandırmasıdır.

### `izleyici.py` diff — üç kanca, hepsi bu

```diff
-                 yasak_kare=30):
+                 yasak_kare=30, hakem=None):
+        self.hakem = hakem
-    def guncelle(self, bgr):
+    def guncelle(self, bgr, gt=None):     # gt YALNIZCA oracle kollari icin
         self._boyut_sinirla()
+        if self.hakem is not None:
+            self.hakem.adim(self, bgr, gt)      # A10: dedektor -> hakem -> takipci
```

### Eşdeğerlik testi (A/B-2 precedent'i) — **GEÇTİ**

A10 öncesi `izleyici.py` dosya olarak geri konup 3 dizi × 2 seviye = **6 hücre,
354 kare** koşuldu ve yeni dosyanın `hakem=None` koşumuyla karşılaştırıldı:
IoU, durum, Kalman merkezi ve boyut serileri **bit düzeyinde aynı**.
`hakem=None` iken davranış değişmiyor.

---

## 2. Karar tabanı — 7 dizi, dondu

Ön-kayıt §1'in kuralı mekanik uygulandı (`veri/a10_taban_sec.py`). 17 test-dev
dizisinden **1**'i geçti; ölçüt gevşetilmedi (ayrıntı: `A10_ONKAYIT.md` EK-1).

**Yeni dizinin rolü — seçimden SONRA, H0 kolunda ölçüldü:**

| 370/0 seviye | IoU | kopuş | YK | bho p50 |
|---|---|---|---|---|
| 30×12 | **0.062** | **3** | 44 | **7.05** |
| 20×10 | 0.377 | 0 | 0 | 1.87 |
| 15×7 | 0.322 | 0 | 8 | 1.94 |
| 10×5 | 0.303 | 0 | 11 | 1.85 |
| 8×5 | 0.131 | **1** | 10 | 2.11 |

5 hücrenin 2'sinde kopuş → A9'un kuralıyla **KOPAN**. Dikkat çekici:
**en büyük seviye en kötüsü** (30×12'de bho 7.05) — merdivenin diğer ucunda
görülen desenin tersi; nedeni A10'da ölçülmedi.

### YATAK ARTEFAKTI (EK-1 bulgusu, her hükme iliştirilir)

35 hücrenin **15'i** (339/49 · 305/5 · 182/127) geçerli boş arkaplan hücresi
olmayan dizilerden geliyor; `arkaplan_hucresi` sessizce `(0,0)`'a düşüyor ve
kompozit arkaplan **gerçek hedefi native boyutuyla içeriyor**.
Ölçülen etki: H0'da artefaktlı hücrelerin ortalama IoU'su **0.4798**, temiz
hücrelerin **0.3860** — yani artefakt hücreleri *kolaylaştırıyor*, sonuçları
karamsar yönde saptırmıyor. Yine de bütün 339/49 hükümleri bu etiketi taşır.

---

## 3. Ana tablo — 35 hücre, 6 kol, kapalı çevrim

| kol | IoU ort | **YK (hakem durumu)** | **YK (takipçi durumu)** | kopuşlu hücre | kilit oranı | bho p50 | doğrulama ms/kare |
|---|---|---|---|---|---|---|---|
| **H0** (kontrol) | **0.4262** | 267 | **267** | 15 | 0.76 | 1.606 | — |
| H1 doğrulayıcı | 0.3956 | 73 | **490** | 15 | 0.43 | 1.550 | 2.59 |
| H2 +boyut çapası | 0.3978 | 73 | **493** | 15 | 0.43 | 1.535 | 2.79 |
| H3 +recovery | 0.3978 | 83 | **512** | 15 | 0.43 | 1.542 | 2.84 |
| *H3-O-merkez* ⟂ | *0.4090* | *110* | *456* | *15* | *0.46* | *1.471* | *2.85* |
| *H3-O-boyut* ⟂ | *0.3975* | *75* | *505* | *15* | *0.43* | *1.506* | *2.90* |

⟂ = **ÜST SINIR**, başarı sayılmaz.

### Rol kırılımı (IoU, H0'a göre)

| | sağlam (15) | KOPAN (15) | yeni 370/0 (5) |
|---|---|---|---|
| H0 | 0.6794 | 0.2354 | 0.2390 |
| H1 | 0.6621 **(−0.017)** | 0.1678 **(−0.068)** | 0.2797 **(+0.041)** |
| H3 | 0.6642 (−0.015) | 0.1706 (−0.065) | 0.2802 (+0.041) |
| H3-O-merkez ⟂ | 0.6644 (−0.015) | 0.1888 (−0.047) | 0.3033 (+0.064) |

Hakem **kopan dizilerde en çok zarar veriyor** — yani tam da yardım etmesi
gereken yerde. Tek istisna, A9 geçmişinde hiç kullanılmamış **yeni dizi**dir.

---

## 4. ÖLÇÜM CONFOUND'U — "yanlış kilit düştü" bir etiket değişikliğidir

`A9_KABUL_OLCUTU.md`, güvenli yanlış kilidi `durum == KİLİTLİ ve IoU < 0.2`
diye tanımlar. Hakem, takipçi KİLİTLİ dese bile durumu SUSPECT'te tutar —
dolayısıyla **"KİLİTLİ demeyerek" bu sayacı düşürebilir.**

| | H0 | H1 |
|---|---|---|
| YK, **hakemin** durumuyla | 267 | **73** (−73%) |
| YK, **takipçinin kendi** durumuyla | 267 | **490** (+84%) |
| KİLİTLİ ilanı düşürülen kare | — | **850 / 2065** |

> Aynı koşumda aynı büyüklük, tanıma göre %73 iyileşiyor ya da %84 kötüleşiyor.
> **Davranış kötüleşti; iyileşen yalnızca etikettir.** Bu yüzden hükümde
> takipçi durumu esas alınır ve iki sütun birlikte raporlanır.

---

## 5. ASIL BULGU — hakem kendi kendini tetikleyen bir çevrim kuruyor

`182/127 · 30×12` **sağlam** bir hücredir: H0'da IoU 0.383, kopuş yok, kilit
%80. H1'de IoU **0.144**, **1 kopuş**, kilit %15. Kare kare izi:

| t | takipçi durumu | Kalman P izi | hakem kararı | sonuç durum | IoU |
|---|---|---|---|---|---|
| 9 | KILITLI | 2.98 | — | KILITLI | 0.234 |
| 10 | SUPHELI | 7.47 | — | SUPHELI | 0.205 |
| **11** | SUPHELI | **11.87** | **LOST** (P>8) | **ARAMA** | 0.180 |
| 12 | KILITLI | **8.00** | — | SUPHELI | 0.212 |
| **13** | SUPHELI | **15.86** | **LOST** (P>8) | **ARAMA** | 0.212 |
| 14 | KILITLI | **8.00** | — | SUPHELI | 0.175 |
| **17** | SUPHELI | **8.92** | **LOST** (P>8) | **ARAMA** | 0.109 |
| 18 | KILITLI | **8.00** | — | SUPHELI | 0.088 |
| **19** | SUPHELI | **13.37** | **LOST** (P>8) | **ARAMA** | 0.071 |
| 20+ | KILITLI | 3.3–4.4 | — | SUPHELI (onay hiç gelmedi) | 0.084 → 0.060 |

Mekanizma, satırlardaki **8.00** değerinde görünüyor:

1. Hakem `iz(P) > 8.0` görüp **LOST** der ve takipçiyi ARAMA'ya iter.
2. `_arama_adimi` hedefi yeniden bulur ve `Kalman.ata`'yı çağırır;
   `ata`, `P[:2,:2]`'yi **`diag(4, 4)`**'e, yani **izi tam 8.0** olan değere sıfırlar.
3. Bir sonraki `tahmin` adımı Q'yu ve ego dönüşümünü ekler → iz **8.0'ın üstüne
   çıkar** → hakem yeniden **LOST** der.

> **Eşik, kendi kararının ürettiği değere eşittir.** Bu, projenin beş kez
> yazdığı dersin **yedinci** tekrarıdır: *bir kapı, kararının ETKİLEDİĞİ bir
> büyüklüğü ölçüt yapamaz* (Deney 1, 3, 4A, 4U, A/B-2'den sonra A10).
> Eşik yayımlanmış **açık çevrim** dağılımından seçilmişti (sağlam p95 = 4.17,
> Mod A p50 = 245.9) ve o dağılımda kusursuz görünüyordu. Kapalı çevrimde
> dağılımın kendisi hakemin kararına bağımlı hale geliyor.

t ≥ 20'de ikinci arıza görünüyor: P sağlıklıya dönüyor (3.3–4.4) ama
**ONAY hiç gelmediği için** takipçi kalıcı olarak SUSPECT'te kalıyor ve
IoU 0.084'ten 0.060'a sızıyor.

---

## 6. Zincir yukarıdan aç kalıyor — ONAY %21.6

| sayaç (H1, 35 hücre = 2065 kare) | değer |
|---|---|
| doğrulama fırsatı (t = 10…50) | 175 |
| gerçekleşen doğrulama | **153** (%87) |
| → **kanıt yok** | **71 (%46)** |
| → SUSPECT (`d_norm > 1.0`) | 78 |
| → **ONAY** | **33 (%21.6)** |
| LOST | 194 kare (%9.4) |
| boyut çapası yazımı | **33** (2065 karede) |
| recovery denemesi | **0** |

**Sonuçlar üst üste biniyor:**

- **Dedektör körlüğü hâlâ tavan.** Doğrulama noktalarının **%46'sında hiç aday
  yok** — 3.2/3.3'ün açık çevrimde ölçtüğü sınır kapalı çevrimde aynen çıktı.
- **Boyut çapası aç kaldı.** Çapa yalnızca ONAY'da yazılır; 2065 karede **33**
  yazım, **10/35 hücrede en az bir yazım**. Etkisi ölçülebilir ama küçük:
  H1 → H2 ortalama IoU **+0.0022**, en iyi hücre +0.036 (117/23·30×12),
  en kötü −0.014. **P0.1'in kapatıldığı söylenemez** — mekanizma kuruldu,
  ama besleme yok.
- **Recovery hiç çalışmadı.** H3'te 35 hücrede **1** deneme (oracle kolunda 2).
  Recovery üç koşulun aynı anda sağlanmasını istiyor: LOST + `t % 10 == 0` +
  daha önce en az bir ONAY. ONAY %21.6 olunca kesişim boşalıyor.
  **K5 geçmedi, SINANMADI.**

---

## 7. Kabul ölçütü — kol kol hüküm

| | K1a yeni kopuş | K1b IoU −0.03 | K1c p95 +%20 | K2 (takipçi durumu) | K3a kopuşlu | K3b ≥2 dizide IoU↑ | K5 | **hüküm** |
|---|---|---|---|---|---|---|---|---|
| H1 | **1 hücre** | **2 hücre** | **1 hücre** | 267→**490** ✗ | 13→13 ✗ | 1 ✗ | sınanmadı | **RED** |
| H2 | **1** | **2** | **1** | 267→**493** ✗ | 13→13 ✗ | 1 ✗ | sınanmadı | **RED** |
| H3 | **1** | **2** | **1** | 267→**512** ✗ | 13→13 ✗ | 1 ✗ | sınanmadı | **RED** |
| H3-O-merkez ⟂ | **1** | **2** | **1** | 267→456 ✗ | 13→13 ✗ | 2 | — | **RED** (üst sınır) |
| H3-O-boyut ⟂ | **1** | **2** | **1** | 267→505 ✗ | 13→13 ✗ | 1 ✗ | — | **RED** (üst sınır) |

K1'i bozan hücre her kolda aynı: **182/127 · 30×12** (§5).
K1b'nin ikinci hücresi 305/5 · 30×12 (−0.0345).
**K6** ayrıca ölçülemez durumda: recovery zaten tetiklenmediği için "recovery
tetiklenmeyen hücreler" bütün taban demektir ve orada K1 sınırları ihlal
edilmiştir.

> **K4 gereği: K1–K3 birlikte sağlanmadı → kalıcılaştırma YOK.**
> `takip/hakem.py` depoda kalır ama **hiçbir varsayılan yolda kullanılmaz**;
> `HedefTakip(hakem=None)` varsayılanı değişmemiştir.

---

## 8. Açık çevrim → kapalı çevrim farkı (raporun ana sorusu)

| bileşen | açık çevrim üst sınırı (A9) | kapalı çevrimde ölçülen (A10) | fark |
|---|---|---|---|
| doğrulayıcı, ayırt edicilik | `min_G` AUC **0.895** (N=5) / 0.878 (N=10) | net IoU **−0.031**, bir sağlam hücrede kopuş | **taşınmadı** |
| doğrulayıcı, çalışma noktası | `G ≤ 1.0`'da sağlam dizilerde ihlal %48 | ONAY yalnızca **%21.6**; kalan kareler SUSPECT'te asılı | daha kötü |
| Mod A tetikleyici | P izi: sağlam p95 **4.17**, Mod A p50 **245.9** (kusursuza yakın ayrım) | eşik kendi kararının ürettiği değere eşit → **kendi kendini tetikleyen çevrim** | **ters döndü** |
| boyut çapası | A/B-3: boyut düzeltilince tanısal zincir kırılıyordu | 33 yazım, ΔIoU **+0.0022** | ölçülebilir, **anlamsız derecede küçük** |
| recovery seçimi | KOL R, R=320: doğru 0.254 / yanlış 0.355 / çekimser 0.391 | **1 deneme** — seçim kuralı hiç sınanamadı | **sınanmadı** |
| dedektör recall tavanı | doğru havuzda 0.274; 8×5'te kanıt yok 0.509 | doğrulamada **kanıt yok %46** | **aynen taşındı** |

**Tek satırda:** açık çevrimde ölçülen ayırt edicilik kapalı çevrime
taşınmadı; taşınan tek şey **dedektör körlüğü** oldu.

---

## 9. Oracle kollar — sorun referansta değil, EYLEMDE

`H3-O-merkez` doğrulama ve recovery referansını **GT merkezine** çeker, yani
3.2'nin "operasyonel vs oracle" ayrımındaki üst sınırdır. Sonuç:

**IoU 0.4090 — H0'ın 0.4262'sinin ALTINDA.**

> Referans kusursuz olsa bile hakem tabanı geçemiyor. Demek ki kayıp,
> `d_norm`'un referansının kalitesinden değil, hakemin **eylem politikasından**
> geliyor: LOST'ta ARAMA'ya itmek ve onay gelmeyince SUSPECT'te asılı bırakmak.
> Bu, A10'un en keskin sonucudur: **sinyali iyileştirmek bu tasarımı
> kurtarmaz.**

---

## 10. Maliyet

| kol | doğrulama ms/kare (ort) | p95 | çağrı başına |
|---|---|---|---|
| H1 | **2.59** | 3.45 | 33.5 ms |
| H2 | 2.79 | 4.46 | 35.9 ms |
| H3 | 2.84 | 3.93 | 37.0 ms |

3.2'nin N=10 için verdiği **4.14 ms/kare** üst sınırının altında; sebebi
doğrulamanın yalnızca KİLİTLİ/SUPHELİ karelerde koşması (%87 kullanım).
**Pi Zero 2 W'ye ekstrapolasyon YAPILMADI** (`KALICI_KISITLAR.md`); masaüstü
CPU ölçümüdür.

---

## 11. Sınırlar

Karar tabanı **7 dizi** — ön-kayıt 3 yeni dizi öngörmüştü, ölçüt 1 geçirdi;
LOSO bağımlılığı **kırılmadı** · 35 hücrenin 15'i **yatak artefaktı** taşıyor
(§2) · yalnızca **A5_baseline** koşuldu (EK-3); A6'nın kapalı çevrim davranışı
**ölçülmedi** · N = 5 koşulmadı · recovery fiilen sınanmadı (1 deneme) ·
`kilitli_ilani_dusurulen_kare` sayacı `_bagimsiz_dogrula`'nın kaç kez
atlandığının **vekilidir**, doğrudan ölçümü değildir · bütün sayılar tek
koşumdur, tekrar edilmedi · Gazebo kullanılmadı.

---

## 12. DUR

Kalıcı değişiklik yapılmadı; varsayılan davranış H0'dır.

**Ölçüme dayalı üç sonraki aday (hiçbiri sınanmadı):**

1. **Hakemin eylem politikasını değiştirmek — sinyalini değil.** §9 gösterdi ki
   oracle referansla bile taban aşılamıyor. LOST'ta ARAMA'ya itmek yerine
   *hiçbir şey yapmayan* (yalnızca raporlayan) bir kol, kapalı çevrimin
   zararını sinyalin faydasından ayırırdı. Kendi ön-kayıtlı ölçütünü ister.
2. **Mod A tetikleyicisini takipçiden BAĞIMSIZ bir büyüklüğe bağlamak.**
   §5'in çevrimi, `iz(P)`'nin hakemin kararıyla sıfırlanmasından doğuyor.
   Aday: yalnızca dedektör kanıtına dayanan bir tetikleyici (P hiç kullanılmaz).
3. **Dedektör recall'ü — altıncı kez.** Doğrulamanın %46'sında kanıt yok;
   çapa da recovery de bu yüzden aç. A8'in adaptif ROI'si bu tavanı yükseltmek
   için ölçülmüş tek araçtır ve **kapalı çevrimde hiç sınanmadı** (A10'un
   Aşama 4'ü olarak duruyordu, koşulmadı).
