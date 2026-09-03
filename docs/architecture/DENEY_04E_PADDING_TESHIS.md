# Deney 4E — DCF arka plan bulaşması / padding teşhisi

**Salt okunur. Kod değişikliği yok, commit/push yok.** `takip/` altındaki 6
dosyanın md5'i Deney 2 durumuyla birebir.

## Kod incelemesi — padding gerçekte nereden geliyor

| ne | nerede |
|---|---|
| parametre | `cekirdekler.py:99` `RenkDcfCekirdek.__init__(self, izgara=32, dolgu=2.0, lr=0.09, sigma=2.0, eps=1e-4, tolerans_px=1.0)` |
| saklanma | `cekirdekler.py:102` `self.dolgu = dolgu` |
| **uygulanma** | `cekirdekler.py:145-146` `_kanallar` içinde: `w = max(4, round(boyut[0] * self.dolgu))`, `h = max(4, round(boyut[1] * self.dolgu))` |
| sonra | yama `cv2.resize(p, (self.N, self.N))` ile 32×32'ye indirilir, Hann penceresi uygulanır |
| etkin arama yarıçapı | `0.5 × dolgu × boyut.min()` (Faz B'de tanımlandı, `gazebo/tani.py:361`) |

### Süpürme neden kod değiştirmeden yapılabildi

`izleyici.py:128`:
```python
self.cekirdek = CEKIRDEKLER[cekirdek]() if isinstance(cekirdek, str) else cekirdek
```
`HedefTakip` hazır bir çekirdek **örneği** kabul ediyor. Bu yüzden
`RenkDcfCekirdek(dolgu=p)` geçirerek **kapalı çevrim** koşum yapılabildi —
yani yalnızca açık çevrim tepe sapması değil, IoU / drift / kilit / kesinti gibi
davranış metrikleri de ölçüldü. Tek satır kod değişmedi.

Ölçüm aracı: `gazebo/tani_dolgu.py`.

## Sonuçlar — öncelikli senaryolar

### G3_agresif

| dolgu | IoU | @0.5 | merkez ort | **DCF dx** | DCF dy | PSR p50 | r_etkin | d_artık/r | kilit | kesinti | drift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.3 | 0.803 | 0.990 | 2.27 | **-2.44** | -0.52 | 54.5 | 24.2 | 0.08 | 100.0% | 0 | yok |
| 1.5 | 0.790 | 0.990 | 2.74 | **-2.90** | -0.93 | 54.4 | 28.0 | 0.07 | 100.0% | 0 | yok |
| 1.7 | 0.785 | 0.990 | 2.94 | **-3.18** | -0.68 | 56.5 | 31.6 | 0.06 | 100.0% | 0 | yok |
| **2.0** | 0.760 | 0.997 | 3.86 | **-4.17** | -0.97 | 54.3 | 37.2 | 0.05 | 100.0% | 0 | yok |
| 2.5 | 0.670 | 0.918 | 6.74 | **-7.23** | -0.86 | 58.1 | 50.9 | 0.04 | 100.0% | 0 | yok |

### G3_kritik

| dolgu | IoU | @0.5 | merkez ort | **DCF dx** | DCF dy | PSR p50 | r_etkin | d_artık/r | kilit | kesinti | drift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.3 | 0.741 | 0.946 | 3.79 | **-3.46** | -0.32 | 51.5 | 31.0 | 0.06 | 100.0% | 0 | yok |
| 1.5 | 0.736 | 0.946 | 3.98 | **-3.65** | -0.06 | 57.1 | 35.9 | 0.06 | 100.0% | 0 | yok |
| 1.7 | 0.721 | 0.935 | 4.47 | **-4.10** | -0.36 | 54.9 | 41.9 | 0.05 | 100.0% | 0 | yok |
| **2.0** | 0.704 | 0.922 | 5.23 | **-4.78** | -0.48 | 54.5 | 46.9 | 0.04 | 100.0% | 0 | yok |
| 2.5 | 0.637 | 0.874 | 7.68 | **-6.87** | -0.92 | 64.2 | 49.1 | 0.04 | 100.0% | 0 | yok |

### VisDrone 117/23

| dolgu | IoU | @0.5 | merkez ort | **DCF dx** | DCF dy | PSR p50 | r_etkin | d_artık/r | kilit | kesinti | drift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.3 | 0.679 | 0.936 | 7.04 | **-6.09** | -1.52 | 55.1 | 29.7 | — | 98.5% | 1 | yok |
| 1.5 | 0.692 | 0.959 | 6.58 | **-5.15** | -1.95 | 63.3 | 35.0 | — | 100.0% | 0 | yok |
| 1.7 | 0.688 | 0.980 | 7.49 | **-6.50** | -1.95 | 67.7 | 40.2 | — | 100.0% | 0 | yok |
| **2.0** | 0.701 | 0.974 | 6.14 | **-4.85** | -1.86 | 68.5 | 45.9 | — | 100.0% | 0 | yok |
| 2.5 | 0.439 | 0.571 | 82.34 | **-11.39** | +8.78 | 63.5 | 50.4 | — | 65.9% | 0 | 202 |

### VisDrone 182/127 ve 268/31

| dolgu | IoU | @0.5 | merkez ort | **DCF dx** | DCF dy | PSR p50 | r_etkin | d_artık/r | kilit | kesinti | drift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.3 | 0.067 | 0.000 | 211.98 | **-104.69** | +114.67 | 17.8 | 6.8 | — | 23.0% | 2 | 38 |
| 1.5 | 0.090 | 0.000 | 298.98 | **-50.54** | +8.59 | 9.8 | 7.8 | — | 13.4% | 1 | 36 |
| 1.7 | 0.052 | 0.000 | 257.93 | **-1.46** | +2.90 | 15.2 | 8.5 | — | 10.4% | 0 | 31 |
| **2.0** | 0.088 | 0.000 | 223.29 | **-125.76** | +140.11 | 31.2 | 10.8 | — | 30.7% | 2 | 39 |
| 2.5 | 0.075 | 0.000 | 87.09 | **+13.28** | +49.14 | 47.6 | 39.8 | — | 61.2% | 0 | 42 |

| dolgu | IoU | @0.5 | merkez ort | **DCF dx** | DCF dy | PSR p50 | r_etkin | d_artık/r | kilit | kesinti | drift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.3 | 0.000 | 0.000 | 477.07 | **-287.08** | +311.15 | 152.3 | 84.0 | — | 60.3% | 0 | 151 |
| 1.5 | 0.000 | 0.000 | 483.42 | **-312.92** | +317.52 | 115.1 | 82.7 | — | 59.9% | 0 | 151 |
| 1.7 | 0.000 | 0.000 | 466.17 | **-320.63** | +302.60 | 141.7 | 105.6 | — | 55.6% | 0 | 151 |
| **2.0** | 0.000 | 0.000 | 456.71 | **-180.51** | +299.27 | 106.4 | 123.7 | — | 71.0% | 0 | 151 |
| 2.5 | 0.000 | 0.000 | 467.63 | **-268.77** | +305.15 | 80.4 | 162.0 | — | 88.1% | 0 | 151 |

Her iki dizi de **her** padding değerinde kopuk (IoU 0.05–0.09 ve 0.000,
drift 31–42 ve 151). Bu soru için bilgi taşımıyorlar.

## Soruların cevapları

### 1. Padding azaldıkça DCF −x bias azalıyor mu?

**Gazebo'da EVET, kusursuz monoton.**

| dolgu | G3_agresif dx | G3_kritik dx |
|---|---|---|
| 1.3 | **−2.44** | **−3.46** |
| 1.5 | −2.90 | −3.65 |
| 1.7 | −3.18 | −4.10 |
| 2.0 | −4.17 | −4.78 |
| 2.5 | −7.23 | −6.87 |

Bias 1.3'te 2.0'a göre **%41 / %28** daha küçük; 2.5'te **%73 / %44** daha büyük.
IoU de aynı yönde monoton (0.803 → 0.670 ve 0.741 → 0.637). Bu, 4B'nin
"yamadaki arka plan bulaşması biası üretiyor" hipotezinin doğrudan
doğrulanmasıdır.

### 2. Gazebo'da mı kalıyor, VisDrone'da da görülüyor mu?

**Gazebo'da kalıyor. VisDrone'da ilişki TERSİNE dönüyor.**

117/23'te bias en küçük **2.0'da** (−4.85); 1.3'te −6.09'a *çıkıyor*. IoU de
2.0'da en yüksek (0.701) ve padding azaldıkça düşüyor (0.692 → 0.688 → 0.679).

### 3. Padding azalırken PSR düşüyor mu?

**Gazebo'da hayır** — G3_agresif 54.5 / 54.4 / 56.5 / 54.3 / 58.1 (düz).
**VisDrone'da EVET** — 117/23: 2.0'da 68.5 → 1.3'te 55.1 (−%20). Yani gerçek
görüntüde küçük yama ayırt ediciliği düşürüyor.

### 4. d_artık p95 Faz B gereksinimini ihlal ediyor mu?

**Hayır, geniş marjla.** Faz B ölçütü `d_artık/r_etkin < 1.0`. Ölçülen en yüksek
değer **0.08** (G3_agresif, dolgu 1.3). Etkin yarıçap 1.3'te bile 24–31 px ve
gereksinimin 12 katı üstünde. Arama menzili padding kısıtı değil.

### 5. Küçük padding yanlış kilit / drift riskini artırıyor mu?

**Evet, ölçülebilir biçimde.** G3 ailesinde hiçbir paddingde drift yok, ama
geniş kümede kilit/drift/kesinti bozulması:

| dolgu | bozulan senaryo sayısı (18 senaryo) |
|---|---|
| 1.3 | **12** |
| 1.5 | **8** |
| 1.7 | 7 |

Örnekler: 1.3'te G1_agresif kilit %100 → %95.9 (3 kesinti), G0 %100 → %98.3;
1.7'de G6_agresif kilit %100 → %82.3 ve **G6_agresif_hedef IoU 0.662 → 0.202**.
VisDrone 117/23'te 1.3 kilit %98.5 + 1 kesinti; 2.5 ise tam kopma
(drift@202, kilit %65.9).

### 6. Gazebo ile VisDrone'da aynı optimum padding var mı?

**HAYIR.** Gazebo G3 optimumu **1.3**, VisDrone 117/23 optimumu **2.0** —
yani mevcut değer. Optimumlar zıt uçlarda.

### 7. Padding ile bias arasında monoton ilişki var mı?

**Senaryo içinde Gazebo'da evet; senaryolar arasında hayır.** Geniş kümede
IoU tepkisi düzensiz:

| senaryo | 2.0 (taban) | 1.3 | 1.5 | 1.7 |
|---|---|---|---|---|
| G0 | 0.912 | 0.909 | 0.912 | 0.910 |
| G1_agresif | 0.897 | 0.860 | 0.898 | 0.879 |
| G2_agresif | 0.859 | 0.854 | 0.845 | 0.839 |
| G3_yumusak | 0.862 | 0.871 | 0.872 | 0.865 |
| G4_agresif | 0.871 | 0.897 | 0.891 | 0.862 |
| G4_kritik | 0.810 | 0.813 | 0.784 | 0.798 |
| G5_agresif | 0.883 | 0.894 | 0.893 | 0.872 |
| G5_kritik | 0.862 | 0.842 | 0.864 | 0.870 |
| G6_agresif | 0.618 | **0.564** | **0.577** | **0.559** |
| G6_agresif_hedef | 0.662 | **0.740** | **0.728** | **0.202** |
| G7_agresif | 0.847 | 0.842 | 0.867 | 0.870 |
| test1 | 0.925 | 0.918 | 0.919 | 0.914 |
| test2 | 0.435 | **0.563** | **0.573** | **0.500** |
| test3 | 0.560 | 0.573 | 0.572 | **0.667** |
| test4 | 0.866 | 0.854 | 0.880 | 0.893 |
| test5 | 0.897 | 0.885 | 0.889 | 0.893 |
| test6 | 0.747 | 0.763 | 0.769 | 0.753 |
| test7 | 0.764 | 0.748 | 0.768 | 0.785 |
| **IoU iyi/kötü** | — | **8/10** | **12/6** | **8/10** |

1.5 en iyi IoU dengesini veriyor (12/6) ama 1.3 ve 1.7 **8/10** ile taban
altında. Yani padding tek yönlü bir kaldıraç değil.

**Uyarı:** sim test2 (+0.138 @1.5) ve test3 (+0.107 @1.7) büyük görünüyor ama
Deney 1'de ölçüldü — bu iki senaryo **kaotik**: anlamca aynı bir işlem değişimi
test2'yi 0.435 → 0.686 oynatmıştı. Buradaki kazançlar kanıt sayılmamalıdır.

## Hüküm

**Mekanizma hipotezi: DESTEKLENDİ.** Yamadaki arka plan oranı DCF tepesinin
−x biasını gerçekten üretiyor; Gazebo'da ilişki monoton, PSR bedeli yok ve
arama menzili kısıtı devreye girmiyor. 4B'nin teşhisi doğruydu.

**Çözüm olarak padding: REDDEDİLDİ.** Kullanıcının kabul kuralı iki koşulluydu
("biası anlamlı azaltıyor **ve** diğer metrikleri kabul edilebilir tutuyorsa").
İkinci koşul sağlanmıyor:

* Etki **genellenmiyor** — çalışan tek gerçek dizide yön tersine dönüyor
  (117/23: her azaltma IoU'yu düşürüyor, en iyi değer mevcut 2.0).
* Her aday değer **kilit/drift davranışını bozuyor** (7–12 senaryo).
* Senaryolar arası tepki **monoton değil** (1.7, hem 1.5'ten hem 2.0'dan kötü).
* Gerçek görüntüde **PSR %20 düşüyor**.

Bu, Deney 4C'yi düşüren örüntünün aynısıdır: Gazebo'da ölçülen kazanç gerçek
veriye taşınmıyor. Bu kez tuzağa **düşmeden önce** ölçüldü.

**Bu yüzden padding değeri önerilmiyor ve başka bir optimizasyona geçilmiyor.**

## Biriken tablo

A3.9 Faz C'de beş aday denendi ya da ölçüldü:

| deney | fikir | sonuç |
|---|---|---|
| 1 | açı = ego entegrasyonu (açık çevrim) | geri alındı — sızıntı + örnekleyici yan etkisi |
| 2 | açı = kapalı çevrim arama | **korundu** — 30/32 birebir, G3_kritik drift kalktı |
| 3 | açı referansı = ego (kapılı) | geri alındı — açı 7.5× düzeldi ama IoU gelmedi |
| 4A | kutu şekli = açıdan analitik | geri alındı — kapalı çevrim oluştu |
| 4C | rafine ağırlığı = sabit 0.17 | geri alındı — VisDrone 117/23 çöktü |
| 4D | rafine ağırlığı = adaptif | elendi — ayırt edici sinyal yok |
| **4E** | **DCF padding** | **elendi — Gazebo'ya özgü, kilit/drift bozuyor** |

Üç bağımsız hattın (4C, 4D, 4E) hepsi aynı duvara çarptı: **Gazebo'da ölçülen
büyüklükler gerçek veriye genellenmiyor.** Faz B'nin kopma eşikleri ve K1–K8
eşlemesi de yalnızca Gazebo üzerinde kurulmuştu.
