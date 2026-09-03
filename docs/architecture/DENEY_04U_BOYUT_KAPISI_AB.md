# Deney 4U — `rafine_kutu` oran kapısı: A/B

**Tek değişiklik, A/B koşumu, sonra GERİ ALINDI.** Kalman, DCF, lr, şablon,
ego, geometri, hiçbir eşik optimizasyonu yok; Optuna yok; commit/push yok.

```diff
--- takip/tespit.py:121-123
     oran = np.array([bw, bh], np.float32) / np.maximum(boyut, 1.0)
-    if not (0.35 < oran.mean() < 2.6):
+    if not (0.60 < oran[0] < 1.70 and 0.60 < oran[1] < 1.70):
         return None
```

`[0.60, 1.70]` deponun kendi bandıdır (`izleyici.py:549`); yeni sabit yok.
Ölçüm aracı: `gazebo/tani_4u_ab.py` (takipçiyi değiştirmez, yalnızca gözler).
Veri: `cikti/boyut_kapisi_4u.json`.

## 1. md5 denetimi

| an | durum |
|---|---|
| deney öncesi | Deney 2 baseline'ı ile **6/6 aynı** |
| A koşumu | değişiklik yok |
| B koşumu | yalnızca `tespit.py` (yukarıdaki tek satır) |
| **geri alma sonrası** | **6/6 yeniden aynı** — `git diff` içinde `tespit.py` yok |

Geri alma doğrulaması: 137/12 yeniden **IoU 0.547592, merkez 7.5063, drift 75**
(baseline'ın birebir aynısı).

## 2. Kabul ölçütü (deneyden ÖNCE yazıldı)

> **K1 BİRİNCİL** (117/23 + 137/12) — en az biri: (a) ikisinde de IoU
> ≥ +0.010 ve hiçbirinde düşüş yok; (b) ya da birinde drift kalkıyor /
> yanlış-kilit azalıyor ve diğerinde IoU düşüşü ≤ 0.005.
> **K2 ÇAPALAR** (G3_agresif, G3_kritik, G0) — hepsi: IoU düşüşü ≤ 0.005,
> kilit oranı düşmüyor, yeni drift yok.
> **K3** Boyut donması yeni baskın arıza olmamalı.
> **K4** Tek dizideki iyileşme genel başarı sayılmaz.

## 3. Sonuçlar

| kaynak | rol | IoU A → B | ΔIoU | merkez A → B | drift A → B | YK karesi A → B | rafine kabul A → B | boyut donması A → B |
|---|---|---|---:|---|---|---|---|---|
| **117/23** | birincil | 0.7010 → 0.6944 | **−0.0066** | 5.51 → 5.80 | yok → yok | 0 → 0 | 0.76 → 0.65 | 1 → 1 |
| **137/12** | birincil | 0.5476 → **0.1896** | **−0.3580** | 7.51 → **99.32** | 75 → **58** | **1 → 139** | 0.69 → 0.42 | 1 → 1 |
| 305/5 | destek | 0.5017 → 0.6004 | **+0.0987** | 9.12 → 4.23 | 110 → 152 | 11 → **30** | 0.93 → 0.76 | 0 → 0 |
| G3_agresif | çapa | 0.7600 → 0.7600 | 0.0000 | 3.81 → 3.81 | yok → yok | 0 → 0 | 0.85 → 0.85 | 2 → 2 |
| **G3_kritik** | çapa | 0.7039 → 0.6959 | **−0.0080** | 5.07 → 5.22 | yok → yok | 0 → 0 | 0.67 → 0.62 | 3 → 3 |
| G0 | çapa | 0.9122 → 0.9243 | +0.0121 | 1.24 → 1.24 | yok → yok | 0 → 0 | 0.99 → 0.97 | 3 → 3 |
| G6_agresif | ayrı soru | 0.6182 → **0.6627** | **+0.0444** | 8.40 → 8.05 | **294 → yok** | 0 → 0 | 0.67 → 0.75 | 2 → 1 |

Boyut/GT oranının ortalama \|log\| değeri (küçük = iyi):

| kaynak | A | B |
|---|---:|---:|
| 117/23 | 0.114 | 0.110 |
| 137/12 | 0.235 | **0.179** |
| 305/5 | 0.267 | 0.135 |
| G3_agresif | 0.082 | 0.082 |
| G3_kritik | 0.122 | 0.121 |
| G0 | 0.030 | 0.022 |
| G6_agresif | 0.155 | **0.084** |

## 4. Ölçüt ölçüt hüküm

| ölçüt | sonuç |
|---|---|
| **K1 birincil** | **KALDI.** 137/12 çöküyor: IoU −0.358, merkez 7.5 → 99.3 px, yanlış kilit **1 → 139 kare** (%0.5 → %66.5), drift 75 → 58 (**erkene** çekiliyor). 117/23'te de küçük düşüş (−0.0066). Ne (a) ne (b) sağlanıyor. |
| **K2 çapalar** | **KALDI.** G3_kritik −0.0080 (sınır 0.005). G3_agresif birebir aynı, G0 +0.0121 iyileşiyor — ama üçünün *hepsi* sağlanmalıydı. |
| **K3 boyut donması** | **GEÇTİ.** Hiçbir kaynakta donma serisi uzamadı (1→1, 0→0, 2→2, 3→3, 3→3, 2→**1**); boyut/GT \|log\| **her kaynakta iyileşti ya da aynı kaldı**. |
| **K4 tek dizi** | 305/5'teki +0.0987 ve G6_agresif'teki +0.0444 tek başına başarı sayılmaz — K4 gereği. |

## 5. G6_agresif'in ayrı sorusu — yanıt

> *"Bozuk rafine kutuyu reddetmek, 104 px civarında boyutun donmasına neden
> olup takip performansını daha fazla mı bozuyor?"*

**Hayır — tam tersi.** Reddetme, 4R'de ölçülen şişmeyi **hiç oluşturmuyor**:

* boyut/GT ort \|log\| **0.155 → 0.084**
* en uzun boyut donması **2 → 1 kare** (donma azaldı, artmadı)
* rafine kabul oranı 0.67 → 0.75 (kutu doğru kaldığı için sonraki rafineler de
  kapıdan geçiyor — pozitif geri besleme)
* **drift 294 → hiç yok**, IoU 0.618 → 0.663

Yani "reddetme → donma → daha kötü" korkusu bu senaryoda **ölçümle
yanlışlandı**. 4R'nin 106→174 px'lik rafine dizisi reddedilince kutu 1.88×'e
hiç şişmiyor.

## 6. Peki 137/12 neden çöktü?

Ölçülen: rafine kabul oranı **0.69 → 0.42** — 53 çağrının 31'i reddediliyor.
4T'nin **açık çevrim** tahmini bu dizide TPR 0.45 / FPR 0.04 idi; kapalı
çevrimde gerçekleşen çok daha kötü. Nedeni yapısal: kapı `bileşen/boyut`
oranına bakar; kutu bir kez kaymaya başladığında oran bozulur, kapı **doğru**
rafineleri de reddetmeye başlar, düzeltme kesilir ve kayma hızlanır — kendi
kendini besleyen bir döngü. Drift'in **erkene** çekilmesi (75 → 58) bunun
imzasıdır.

> **Ders:** 4T'nin açık çevrim ROC'u (AUC 0.89, TPR 0.59 / FPR 0.03) bir
> **üst sınırdır**; kapı takipçinin içine konduğunda ölçtüğü büyüklüğün
> kendisi kapının kararından etkilendiği için performans o sınırın çok
> altına düşebilir. Bu, Faz C'nin "türetilmiş büyüklük ölçümün yerine geçince
> çevrim kapanıyor" dersinin beşinci örneğidir — burada kapının **girdisi**
> kapının **çıktısına** bağlı.

---

# HÜKÜM: **REDDEDİLDİ**

Değişiklik **geri alındı**; `takip/` md5 6/6 Deney 2 baseline'ı ile aynı ve
baseline metrikleri birebir geri geldi.

K1 ve K2'nin ikisi de kaldı: birincil dizilerden birinde (137/12) yıkıcı
regresyon (IoU −0.358, yanlış kilit %0.5 → %66.5), diğerinde küçük düşüş; bir
çapada (G3_kritik) sınırın üstünde kayıp. K3 geçti ve G6_agresif'te belirgin
iyileşme var (+0.0444, drift kalktı) — ama K4 gereği bunlar tek başına başarı
sayılmaz.

**Yeni optimizasyon önerilmiyor.** Bu turda öğrenilen kısıt, bir sonraki
adayın karşılaması gereken koşulu netleştiriyor:

> Kapı, kararının **etkilediği** bir büyüklüğü (`bileşen/boyut` oranı) ölçüt
> olarak kullanamaz — çevrim kapanıyor. Kabul edilebilir bir sonraki aday,
> kararı **boyuttan bağımsız** bir büyüklüğe dayandırmalıdır. 4T'nin ölçtüğü
> aday havuzunda böyle bir büyüklük **yoktu** (`renk_mesafe` AUC 0.594,
> `n_bilesen` 0.678, `maske_doluluk` 0.800 — hepsi oran sinyalinin altında ve
> hiçbiri boyuttan bağımsız değil).

Bu nedenle **tek değişkenli yeni bir aday önerilmiyor**; sıradaki iş, aday
üretmek değil, bu kısıtı karşılayan bir ölçüt olup olmadığına karar vermektir.

**Bu turda kalıcı hiçbir değişiklik yapılmadı.**
