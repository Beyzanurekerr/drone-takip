# D1 — `HareketTespit.adaylar()` mutlak ve bağımsız bir boyut ölçümü veriyor mu?

**Salt okunur. `takip/` altında hiçbir dosya değiştirilmedi**; hiçbir eşik,
ağırlık, Kalman, DCF, şablon, padding veya kabul kuralı değişmedi;
`tespit.py` / `izleyici.py` dokunulmadı; commit/push yok.
Araç: `gazebo/tani_d1_adaylar.py`. Veri: `cikti/d1_adaylar.json`.
Kabul ölçütü koşumdan **önce** yazıldı: `docs/architecture/D1_kabul_olcutu.md`.

**Gözlemin davranışa etkisizliği iki bağımsız yolla gösterildi:**
1. `adaylar()`ın tek yan etkisi `self._son_maske = ikili` (`tespit.py:69`) ve
   `_son_maske` depoda **hiçbir yerde okunmuyor** (grep: yalnızca `tespit.py:32`
   ve `:69`).
2. Beş kaynağın baseline metrikleri **birebir** geldi: 117/23 `0.700953`,
   137/12 `0.547592`, 305/5 `0.501698`, G6_agresif `0.618242`,
   G6_agresif_durakli `0.383141`.

`takip/` md5'leri deney öncesi = sonrası, Deney 2 baseline'ı ile **6/6 aynı**.

---

## 1. `adaylar()` kod yolu (tespit.py:47–84) — ürettiği ölçümler

| satır | işlem | girdisi |
|---|---|---|
| 49–50 | `hazir()` değilse boş döner | `g1`, `g2` |
| 52–53 | `w1 = warpAffine(g1, M)` — önceki kare ego ile hizalanır | ego `M` |
| 54 | `d = absdiff(gri, w1)` | görüntü |
| 55–59 | `uc_kare=True` ise `d = min(d, |I_t − warp₂(I_{t−2})|)` *(varsayılan False)* | görüntü |
| 60 | `d = GaussianBlur(d, 5×5)` | — |
| 62–63 | kenardan **8 px** kırpılır (warp artefaktı) | mutlak |
| **65** | **`esik = max(min_esik=8.0, d.mean() + esik_k(4.0)·d.std())`** | **mutlak** |
| 66–68 | `threshold` → `MORPH_CLOSE(3×3)` → `dilate(3×3)` | mutlak |
| 71 | `connectedComponentsWithStats(ikili, 8)` | — |
| **75** | `alan < 3` **veya** `bw > 160` **veya** `bh > 160` → ele | **mutlak** |
| 77 | `max(bw,bh)/min(bw,bh) > 9` → ele | oransal (kendi içinde) |
| 79–82 | `kutu=(x,y,bw,bh)`, `merkez=centroid`, `alan`, `guc = d[...].mean()` | — |
| 83–84 | alana göre sırala, ilk 40 | — |

**`self.boyut`, `kf.konum`, `rafine_kutu` çıktısı ya da bunlardan türetilmiş
hiçbir büyüklük bu yolda okunmaz.** Bütün eşikler piksel/alan cinsinden
mutlaktır.

Seçim kuralları (ölçümün kendisi değil, ondan hangi adayın alınacağı):

| kural | ne kullanır | koşumda kullanılabilir mi |
|---|---|---|
| **S1** | takip **merkezini** içeren adaylardan en büyüğü | evet (boyut kullanmaz) |
| **S2** | merkeze en yakın merkezli aday | evet (boyut kullanmaz) |
| **S3** | GT ile IoU'su en yüksek aday | **hayır** — yalnızca ÜST SINIR |

---

## 2–4. Ölçüm sonuçları (KILITLI + GT olan kareler)

`w/GT` ve `h/GT` medyanı [p5..p95]; `yay` = p95−p5. `rafine` aynı koşumda,
aynı karelerde ölçülen mevcut `rafine_kutu` çıktısıdır (karşılaştırma tabanı).

### 117/23 — drift yok, 342 kare, ort 39.8 aday, ek maliyet 4.80 ms/kare

| faz | ölçüm | n | w/GT | h/GT | IoU_GT |
|---|---|---:|---|---|---:|
| tüm koşum | **S1** | **24** (%7) | 0.65 [0.44..1.04] yay 0.60 | 0.64 [0.40..0.79] yay 0.39 | 0.42 |
| | S2 | 342 | **0.21** [0.08..0.89] | **0.20** [0.09..0.79] | **0.01** |
| | S3 *(üst sınır)* | 199 | 0.28 [0.11..0.85] | 0.26 [0.13..0.79] | 0.05 |
| | **rafine** | 65 | **1.03** [0.85..1.51] yay 0.66 | **0.87** [0.63..1.01] yay 0.38 | — |

### 137/12 — drift 75, 206 kare, ort 40.0 aday, ek maliyet 5.53 ms/kare

| faz | ölçüm | n | w/GT | h/GT | IoU_GT |
|---|---|---:|---|---|---:|
| **drift öncesi** | **S1** | 37 | 0.64 [0.55..0.81] | **0.30** [0.12..0.50] | 0.19 |
| | S2 | 68 | 0.60 [0.30..0.80] | **0.31** [0.14..0.50] | 0.13 |
| | S3 *(üst sınır)* | 64 | 0.69 [0.31..0.79] | 0.44 [0.31..0.71] | 0.20 |
| | **rafine** | 17 | 1.47 [0.95..2.06] | 1.42 [1.01..1.64] | — |
| drift sonrası | S1 | 102 | 0.69 [0.32..1.01] | 0.55 [0.12..1.19] | 0.28 |
| | rafine | 19 | 1.00 [0.97..1.44] | 1.35 [1.00..2.10] | — |

### 305/5 — drift 110, 115 kare, 3.98 ms/kare

| faz | ölçüm | n | w/GT | h/GT | IoU_GT |
|---|---|---:|---|---|---:|
| drift öncesi | S1 | **15** (%15) | 0.87 [0.83..1.05] | **0.27** [0.18..0.37] | 0.18 |
| | S2 | 103 | 0.89 [0.81..1.01] | **0.31** [0.26..0.53] | 0.26 |
| | S3 | 103 | 0.95 [0.90..1.01] | 0.53 [0.41..0.61] | 0.48 |
| | rafine | 25 | 1.05 [0.96..2.39] | 0.93 [0.91..1.95] | — |
| drift sonrası | S1 | 10 | 0.38 | 0.48 | **0.00** |

### G6_agresif — drift 294, 293 kare, 2.27 ms/kare

| faz | ölçüm | n | w/GT | h/GT | IoU_GT |
|---|---|---:|---|---|---:|
| drift öncesi | S1 | 146 | 0.60 [0.15..1.57] yay **1.42** | 0.95 [0.54..1.51] yay 0.97 | 0.39 |
| | S2 | 287 | **0.17** [0.06..1.40] | 0.60 [0.11..1.34] | 0.09 |
| | **rafine** | 49 | **1.01** [0.96..2.07] | **1.01** [0.95..1.86] | — |

### G6_agresif_durakli — drift 148, 253 kare, 2.19 ms/kare

| faz | ölçüm | n | w/GT | h/GT | IoU_GT |
|---|---|---:|---|---|---:|
| drift öncesi | S1 | 42 | 0.65 [0.29..1.55] yay 1.27 | 0.87 [0.57..1.15] | 0.46 |
| | **rafine** | 31 | **0.98** [0.95..1.31] yay **0.36** | **0.98** [0.94..1.05] yay **0.11** | — |
| drift sonrası | S1 | 16 | 0.46 [0.07..2.46] | 0.25 [0.11..0.60] | **0.00** |

---

## 5. A / B / C ayrımı

| | tanım | `adaylar()` |
|---|---|---|
| **A** | gerçekten bağımsız **ve** mutlak **ve** doğru | **HAYIR** — bağımsız ve mutlak ama **doğru değil** |
| **B** | bağımsız görünen ama takipçi boyutundan türeyen | hayır — kod yolunda `boyut` hiç okunmuyor |
| **C** | boyuttan bağımsız fakat **mutlak olmayan / taşınamayan** | — bu, `ego.olcek_katsayisi`nin durumuydu (kapanış §6) |

> `adaylar()` **yeni bir dördüncü sınıftır:** bağımsız (K1 ✓) ve mutlak
> (K2 ✓) ama **sistematik olarak yanlış** — ölçtüğü kutu hedefin
> tamamı değil, hareket farkının en yüksek kontrastlı **parçasıdır**.
> `esik = mean + 4·std` bir *sabit oran* eşiğidir: farkın yalnızca en üst
> yüzdelik dilimini geçirir, o da aracın tamamı değil bir bölümüdür.
> Bu, 4N'in `rafine_kutu` için bulduğu **parçalanma** kipinin aynısıdır
> (orada `p82` eşiği, burada `mean + 4σ`). İki ölçüm de aynı kök nedeni
> paylaşıyor: **sabit-oranlı kontrast eşiği nesneyi değil parçasını
> veriyor.**

---

## 6. İki gerçek dizide aynı yönde mi?

**Hayır.** `boyut`suz seçim kuralı S1 ile:

| | 117/23 | 137/12 | fark |
|---|---|---|---|
| w/GT medyan | 0.65 | 0.64 | benzer |
| **h/GT medyan** | **0.64** | **0.30** | **2.1×** |
| S1'in mevcut olduğu kare oranı | **%7** (24/342) | %67 (139/206) | **10×** |
| IoU_GT medyan | 0.42 | 0.19 | 2.2× |

117/23'te ölçüm karelerin **%93'ünde yok**; 137/12'de var ama yüksekliği
**3 kat küçük** ölçüyor.

---

## 7. Hata ne zaman başlıyor? — ilk kare + sonraki 20

Ölçüm "bir yerden sonra bozulmuyor"; **ilk mevcut kareden itibaren bozuk**:

| dizi | kural | ilk mevcut kare | ilk band dışı kare | band dışı oran |
|---|---|---:|---:|---:|
| 117/23 | S1 | **288** | **288** | 14/24 (%58) |
| 117/23 | S2 | 7 | **7** | 304/342 (%89) |
| 137/12 | S1 | 7 | **7** | 102/139 (%73) |
| 137/12 | S2 | 7 | **7** | 174/206 (%84) |

137/12, kare 7'den itibaren (S1) — takipçinin kendi IoU'su hâlâ 0.93–0.99 iken:

```
kare   7  w/GT 0.80  h/GT 0.45  IoU_GT 0.36   (takip IoU 0.93)
kare  10  w/GT 0.78  h/GT 0.50  IoU_GT 0.38   (takip IoU 0.99)
kare  13  w/GT 0.64  h/GT 0.30  IoU_GT 0.19   (takip IoU 0.93)
kare  16  w/GT 0.62  h/GT 0.29  IoU_GT 0.18   (takip IoU 0.83)
```

Yani takip sağlıklıyken bile `adaylar()` yüksekliği yarıdan az ölçüyor.

---

## 8/9. Kabul ölçütüne göre hüküm

| ölçüt | sonuç |
|---|---|
| **K1 bağımsızlık** | **GEÇTİ** — kod yolunda `boyut`/`kf`/`rafine` okunmuyor; S1/S2 yalnızca merkezi kullanıyor |
| **K2 mutlaklık** | **GEÇTİ** — piksel cinsinden doğrudan w/h; tüm eşikler mutlak |
| **K3a medyan [0.60, 1.70] içinde** | **KALDI** — 137/12 h/GT **0.30**, 305/5 h/GT **0.27** |
| **K3b yayılım rafineden dar** | **KALDI** — 117/23'te h yay 0.39 vs rafine 0.38; G6_agresif'te S1 w yay **1.42** vs rafine 1.11; durakli'de S1 1.27/0.58 vs rafine **0.36/0.11** |
| **K4 iki gerçek dizide aynı yönde** | **KALDI** — h/GT 0.64 vs 0.30; kullanılabilirlik %7 vs %67 |
| **K5 drift ayrımı** | raporlandı; drift sonrası daha da kötü (IoU_GT medyan 0.00) |

**K3 iki gerçek dizide de düştüğü için, önceden yazılan kurala göre hüküm:
GÜVENİLİR DEĞİL.**

Ek olarak — kabul ölçütünde yer almayan ama belirleyici bir gözlem:
**mevcut `rafine_kutu`, aynı karelerde `adaylar()`ten belirgin biçimde daha
iyidir** (117/23 w/GT 1.03 vs 0.65; durakli 0.98/0.98 yayılım 0.36/0.11 vs
0.65/0.87 yayılım 1.27/0.58). Yani `adaylar()` mevcut ölçümün yerine geçemez;
onu iyileştirmez.

Maliyet (yalnızca kayıt, D2'nin konusu): kare başına **2.19–5.53 ms** ek yük.

---

# SONUÇ

1. **`adaylar()` gerçekten bağımsız mı?** **EVET.** Kod yolu `boyut`,
   `kf.konum` ya da `rafine_kutu` çıktısını hiç okumaz; bütün eşikleri
   mutlaktır (`min_esik=8.0`, `mean + 4·std`, `min_alan=3`, `max_kenar=160`).
2. **Mutlak w/h ölçüyor mu?** **EVET, mutlak ölçüyor — ama DOĞRU ölçmüyor.**
   Medyan `w/GT` 0.17–0.89, `h/GT` 0.20–0.95; ölçtüğü şey aracın tamamı değil,
   hareket farkının en yüksek kontrastlı parçası.
3. **İki bağımsız gerçek dizide çalışıyor mu?** **HAYIR.** h/GT 0.64 (117/23)
   vs 0.30 (137/12); kullanılabilirlik %7 vs %67.
4. **Drift öncesinde çalışıyor mu?** **HAYIR.** İlk mevcut kareden itibaren
   band dışında (137/12 kare 7: h/GT 0.45, takipçinin kendi IoU'su 0.93).
5. **Drift sonrası güvenilir mi?** **HAYIR** — daha da kötü; 305/5 ve
   G6_agresif_durakli'de IoU_GT medyanı **0.00**.
6. **Minimum müdahale noktası neresi olur?** **Yok.** Ölçüm doğru olmadığı
   için `_boyut_tazele`'ye ek girdi olarak bağlanacak bir nokta önerilmiyor;
   böyle bir öneri Z2/Z3'ü ihlal ederdi.
7. **Kod değişikliği yapılmalı mı?** **HAYIR.**

**Karar kapanışının "yeni ölçüm gerekiyor" hükmü GEÇERLİLİĞİNİ KORUYOR — ve
D1 onu daraltıyor:** eksik olan "bağımsız bir ölçüm" değil (`adaylar()` zaten
bağımsız ve mutlak), **DOĞRU** bir ölçümdür. Deponun iki boyut ölçümü de
(`rafine_kutu`'nun `p82` eşiği ve `adaylar()`in `mean + 4σ` eşiği) aynı kök
nedeni paylaşıyor: sabit-oranlı kontrast eşiği nesnenin kendisini değil bir
parçasını veriyor.

**Bu turda hiçbir kod değişikliği ya da eşik önerisi yapılmadı; `takip/`
md5 6/6 aynı.**
