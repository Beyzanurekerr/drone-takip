# A10.1 / D1 — TEMİZ YATAK

> ### `YATAK DÜZELTMESİ` · `AÇIK ÇEVRİM` · `TEŞHİS`
> `arkaplan_hucresi`'nin `(0,0)` düşüşü **kaldırıldı**; geçerli boş arkaplan
> hücresi bulunamayan dizi artık **hata veriyor** ve tabandan **düşüyor**.
> Üç dizi düştü. A9'un üç ölçümü temiz yatakta yeniden koşuldu.
>
> **En sert sonuç: `G ≤ 1.0` kapısının "sağlam dizilerde %48 yanlış alarm"
> bulgusu YOK OLDU — temiz yatakta 51 kanıtlı noktanın 0'ında ihlal var.
> O %48 bir YATAK ARTEFAKTIYDI.** Deney 3.3'ün tamamı bu sayının üstüne
> kurulmuştu.

**Tarih:** 2026-09-03 · **Kod:** `gazebo/bench_a52_kucuk_hedef.py` (düzeltme),
`gazebo/tani_a10_1_temiz_yatak.py` (yeniden koşum) ·
**Veri:** `cikti/a10_1_temiz_yatak.json`
**A9'un kendi çıktısı değiştirilmedi:** `cikti/a9_takipci_merkez_recovery.json`
koşum öncesi yedeklendi, sonrasında geri yazıldı ve doğrulandı (30 hücre,
`experiment_3_3` yerinde).

---

## 1. Düzeltme

```diff
-    return (en_iyi or (0, 0)), round(en_uzak, 1)
+    if en_iyi is None:
+        raise YatakHatasi(
+            f"gecerli arkaplan hucresi yok: {cw}x{ch} hucrelerinin hepsi 60 karenin "
+            f"en az birinde hedefi iceriyor (kare {W}x{H}). Bu dizide kompozit "
+            f"yatak KURULAMAZ; taban disi birakilmalidir.")
+    return en_iyi, round(en_uzak, 1)
```

`gazebo/bench_a52_kucuk_hedef.py` md5: `45623cc5…` → **`6683af37…`**.
Bu dosya A7/A8/A9 boyunca "değişmedi" diye raporlanan bütünlük çıpasıydı;
**bilerek ve tek amaçla** değiştirildi.

## 2. Tabandan düşen diziler

| dizi | native | sebep |
|---|---|---|
| **uav0000339_00001_v/49** | 1904×1071 | 1280×720 hücrelerinin hepsi 60 karenin en az birinde hedefi içeriyor |
| **uav0000305_00000_v/5** | 1904×1071 | aynı |
| **uav0000182_00000_v/127** | 1344×756 | aynı |

Sebep geometrik: 1280×720'lik hücre 1904×1071'e yalnızca birkaç konumda
sığıyor ve hareketli hedef 60 karede hepsini ziyaret ediyor.

**TEMİZ TABAN — 4 dizi × 5 seviye = 20 hücre**

| dizi | native | hücre | rol |
|---|---|---|---|
| uav0000117_02622_v/23 | 2720×1530 | (1280, 360) | KOPAN |
| uav0000268_05773_v/31 | 3840×2160 | (1920, 720) | KOPAN |
| uav0000137_00458_v/12 | 2688×1512 | (1280, 360) | **sağlam** |
| uav0000370_00001_v/0 | 2720×1530 | (1280, 720) | KOPAN |

> **En ağır sınır: geriye TEK sağlam dizi kaldı (137/12).** 3.3'ün LOSO'su
> zaten "137/12 çıkarsa çalışma noktası yok" demişti; artık çıkarılacak başka
> sağlam dizi de yok. K1/K2/K6'nın sağlam-dizi ayağı tek diziye dayanıyor.

---

## 3. Aşama 2 (kopuş tespiti) — temiz yatak

**20 hücre**, kopuş 10 hücrede. Mod etiketlemesi A9 ile aynı ölçüt
(kopuş sonrası DCF kabul oranı ≥ 0.8 → Mod B).

| | kirli yatak (A9, 30 hücre) | **temiz yatak (20 hücre)** |
|---|---|---|
| Mod A hücresi | 9 | **8** |
| **Mod B hücresi** | **4** | **2** |
| Mod B'nin geldiği diziler | 339/49 (**3**), 117/23 (1) | **117/23 (1), 370/0 (1)** |

### Mod B HÂLÂ VAR — ve artık tek diziye dayanmıyor

- **`117/23 · 8×5`** — A9'da da Mod B'ydi, temiz yatakta da Mod B. **Sağ kaldı.**
- **`370/0 · 30×12`** — **yeni**, A9 geçmişinde hiç kullanılmamış dizi.
  Mod B'nin 117/23'e ya da 339/49'a özgü bir artefakt olmadığının **bağımsız
  doğrulaması**.
- 339/49'un üç Mod B hücresi **diziyle birlikte gitti** — çürütülmediler,
  **ölçülemez** hale geldiler (o dizide geçerli yatak kurulamıyor).

### Sinyal tablosu — neredeyse hepsi sağ kaldı, biri çöktü

| sinyal | AUC kirli | **AUC temiz** | durum |
|---|---|---|---|
| `psr` | 0.877 | **0.880** | sağ kaldı (en iyi tek ayırıcı) |
| `dcf_kf_ayrim` | 0.731 | 0.747 | sağ kaldı |
| `P_konum_iz` | 0.760 | 0.755 | sağ kaldı |
| `durum_disi` | 0.732 | 0.701 | sağ kaldı |
| `olcum_yok` | 0.620 | 0.609 | sağ kaldı |
| `boyut_orani` | 0.471 | 0.547 | ikisinde de ayırmıyor |
| **`benzerlik`** | 0.501 | **0.363** | **çöktü — şanstan belirgin kötü** |

### P konum izi dağılımı DEĞİŞTİ — D2'yi doğrudan ilgilendirir

| | kirli (A9) | **temiz** |
|---|---|---|
| sağlam p95 | **4.17** | **14.86** |
| Mod B p95 | 11.97 | 29.52 |
| kopuş öncesi p95 | 54.13 | 54.08 |
| Mod A p50 | 245.90 | 243.52 |

> A10'un `iz(P) > 8.0` eşiği yalnızca **kendi kendini besliyor** olmakla kalmıyor;
> temiz yatakta ölçülen **sağlam p95 = 14.86**'nın da altında. Yani sağlıklı
> takipte de ateşlerdi. D2'nin eşikleri bu yüzden **temiz yatak** sayılarından
> alındı (giriş 54.08, çıkış 14.86).

---

## 4. Deney 3.0 (olay tabanı) — temiz yatak

| | kirli (A9) | **temiz** |
|---|---|---|
| toplam epizot | 17 | **12** |
| kopan dizilerde | 14 | 8 |
| sağlam dizilerde | 3 | **4** |
| KİLİTLİ-başlangıçlı | 5 | **3** |

3.0'ın yapısal hükmü ("KİLİTLİ-başlangıçlı epizotları `durum != KİLİTLİ`
tetikleyicisi kaçırır") **sağ kaldı**: 12 epizodun 3'ü hâlâ KİLİTLİ başlıyor.

---

## 5. Deney 3.2 KOL V — temiz yatak (A5_baseline)

3.2'nin bütün ayarları birebir korundu (N=5, `A8.R_sec`, tam
`G = max(d_norm, a_norm, r_norm)`, kapı 1.0). **Değişen tek şey yatak.**

| | kirli (A9) | **temiz** |
|---|---|---|
| doğrulama noktası | 246 | 140 |
| **kanıt yok** | ~%46 | **%42.9** (60/140) |
| **sağlam dizide `G > 1.0` ihlali** (kanıt taşıyan payda) | **%48.0** (49/102) | **%0.0 (0/51)** |

### Seviye bazında kanıt yok

| seviye | 30×12 | 20×10 | 15×7 | 10×5 | 8×5 |
|---|---|---|---|---|---|
| kanıt yok | 6/29 | 9/24 | 15/29 | 14/27 | 16/31 |

**Dedektör körlüğü sağ kaldı** — bu bir yatak artefaktı değil, dedektörün
kendi sınırı. 8×5'te noktaların yarısında hâlâ kanıt yok.

**Ama %48 sağ kalmadı.** Kirli yatakta kompozit arkaplan **gerçek hedefi
native boyutuyla** taşıyordu; dedektör onu buluyor, `G` takipçinin kutusuna
göre büyük çıkıyor ve kapı ihlal ediliyordu. Temiz yatakta bu ikinci araç yok
ve 51 kanıtlı noktanın hiçbirinde ihlal yok.

> **Uyarı — bu sıfır tek diziden geliyor.** Temiz tabanda tek sağlam dizi
> 137/12'dir. "%0" ifadesi "yanlış alarm çözüldü" demek değil,
> **"o %48'in kanıtı ortadan kalktı"** demektir.

---

## 6. Hangi A9 bulgusu sağ kalmadı

Aşağıdakiler **silinmedi**; A9 raporunda `KİRLİ YATAK` etiketiyle işaretlendi.

| A9 bulgusu | durum |
|---|---|
| `G ≤ 1.0`, sağlam dizilerde **%48 yanlış alarm** (3.2 §7a) | **SAĞ KALMADI** (temiz: %0) |
| Deney **3.3**'ün tamamı — X türetmesi, k taraması, "%48 aynen duruyor" | **DAYANAĞI ÇÖKTÜ** (X, 5.8 kare + %48 üstüne kuruluydu) |
| 3.3'ün kanonik Mod B örneği **339/49 · 15×7** | **ÖLÇÜLEMEZ** (dizi tabandan düştü) |
| "Mod B tabanının 3/4'ü 339/49'dan" | **KONUSUZ** |
| `P_konum_iz` sağlam p95 = **4.17** | **SAĞ KALMADI** (temiz: 14.86) |
| `benzerlik` Mod B'nin tek kalıcı sinyali | **SAĞ KALMADI** (AUC 0.363) |
| A10'un `iz(P) > 8.0` eşiği | **İKİ AYRI SEBEPLE GEÇERSİZ** (kendi kendini besliyor + sağlam p95'in altında) |

**Sağ kalanlar:** Mod A / Mod B ayrımının varlığı · Mod B'nin gerçekliği
(2 bağımsız dizi) · `psr`'nin en iyi tek ayırıcı olması · dedektör körlüğü
(%43) · KİLİTLİ-başlangıçlı epizotların tetikleyici kör noktası ·
`boyut_orani`'nın haberci olarak işe yaramaması.

## 7. Sınırlar

Tek sağlam dizi (137/12) · 20 hücre (A9'da 30) · Mod B örneklemi **2 hücre** ·
KOL V yalnızca A5_baseline · temiz yatak da 60 kareyle sınırlı ·
düşen üç dizi **çürütülmedi**, yalnızca bu protokolde ölçülemez oldular —
başka bir tuval boyutuyla (ör. 960×540 sensör) yeniden ölçülebilirler,
bu **yapılmadı**.
