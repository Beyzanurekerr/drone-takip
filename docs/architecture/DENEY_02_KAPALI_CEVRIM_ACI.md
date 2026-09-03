# Deney 2 — Kapalı çevrim açı kestirimi

**Sonuç: KORUNDU.** Commit/push yapılmadı.

32 senaryonun **30'u alan alan bit-birebir değişmedi**; değişen iki senaryo
(G3_agresif, G3_kritik) tam olarak gerçek kamera dönmesinin eşiği aştığı iki
senaryodur. Kazanç G3_kritik'te yoğunlaşıyor: drift kalktı, kilit %100'e çıktı.

## Tasarım

Deney 1'in iki kusuru vardı; ikisi de burada kapatıldı.

**1. Açı biriktirilmiyor.** Ego M'si artık yalnızca iki iş yapar: dönme
şüphesi kapısı ve arama tohumu. Seçim her karede **şablon yanıtıyla** yapılır:
üç aday açı (`n−1`, `n`, `n+1` adım) denenir, PSR'si en yüksek olan seçilir ve
şablon o açıda öğrenilir. Ölçüt kendi çapasına geri döndüğü için ego yanlılık
üretse bile arama onu her karede geri çeker — deney 1'de G4_kritik'te −9.4°
biriken sahte açı burada **hiç oluşmuyor** (aşağıdaki tabloda G4 satırları).

**2. Örnekleyici değişkeni deneyden çıktı.** Ayrım `self.aktif` üzerinden
yapılır, `açı != 0` üzerinden değil. Dönme şüphesi yokken tek aday (açı 0)
denenir ve **eski `getRectSubPix` yolu aynen** kullanılır. Arama açıkken üç
adayın hepsi aynı örnekleyiciyle kesilir — yoksa seçim örnekleyici farkından
yanlılık kapardı.

### Tek yeni sabit

`tolerans_px = 1.0`. Adım ve eşik kilit anındaki kutudan **türetilir**:

    aci_adim   = derece(tolerans_px / kutu_yarı_köşegeni)
    dteta_esik = aci_adim / 2

Bir adımlık hata kutu kenarında 1 px kayma yapar. Küçük hedefte yarı köşegen
küçüktür, adım büyür, eşik yükselir — yani 12×5 px'lik bir hedefte dönme
telafisi kendiliğinden devreye girmez. Doğru davranış: o boyutta zaten dönmeyi
taşıyacak doku yok.

Ölçülen değerler: 56×22 px kutu → adım 1.90°, eşik 0.95 °/kare.
12×5 px kutu → adım 8.82°, eşik 4.41 °/kare.

## Sonuçlar

### Gazebo (22 kayıt)

| senaryo | IoU ö→y | @0.5 ö→y | merkez px ö→y | kilit ö→y | kesinti ö→y | kurtarma max ö→y | IDsw ö→y | drift ö→y | açı aktif | durum |
|---|---|---|---|---|---|---|---|---|---|---|
| G0 | 0.912→0.912 | 1.000→1.000 | 1.24→1.24 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G1_yumusak | 0.899→0.899 | 1.000→1.000 | 1.40→1.40 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G1_agresif | 0.897→0.897 | 1.000→1.000 | 1.24→1.24 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G2_yumusak | 0.862→0.862 | 1.000→1.000 | 2.28→2.28 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G2_agresif | 0.859→0.859 | 1.000→1.000 | 1.63→1.63 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G3_yumusak | 0.862→0.862 | 1.000→1.000 | 1.85→1.85 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G3_agresif | 0.766→0.760 | 0.990→0.997 | 3.47→3.81 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 100% (293 kare) | **kayıp** |
| G4_yumusak | 0.885→0.885 | 1.000→1.000 | 1.44→1.44 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G4_agresif | 0.871→0.871 | 1.000→1.000 | 1.72→1.72 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G5_yumusak | 0.888→0.888 | 1.000→1.000 | 1.68→1.68 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G5_agresif | 0.883→0.883 | 1.000→1.000 | 1.62→1.62 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G6_yumusak | 0.807→0.807 | 1.000→1.000 | 2.81→2.81 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G6_agresif | 0.618→0.618 | 0.684→0.684 | 8.40→8.40 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | 294→294 | 0% (0 kare) | **birebir aynı** |
| G7_yumusak | 0.893→0.893 | 1.000→1.000 | 1.29→1.29 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G7_agresif | 0.847→0.847 | 1.000→1.000 | 1.66→1.66 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G1_kritik | 0.890→0.890 | 1.000→1.000 | 1.43→1.43 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G3_kritik | 0.579→0.704 | 0.721→0.922 | 9.25→5.07 | 96.9%→100.0% | 1→0 | 9→0 | 0→0 | 133→yok | 100% (293 kare) | **KAZANÇ** |
| G4_kritik | 0.810→0.810 | 1.000→1.000 | 1.57→1.57 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G5_kritik | 0.862→0.862 | 1.000→1.000 | 1.70→1.70 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G7_kritik | 0.865→0.865 | 1.000→1.000 | 2.27→2.27 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G6_agresif_hedef | 0.662→0.662 | 0.915→0.915 | 7.54→7.54 | 97.3%→97.3% | 1→1 | 8→8 | 0→0 | yok→yok | 0% (0 kare) | **birebir aynı** |
| G6_agresif_durakli | 0.383→0.383 | 0.469→0.469 | 61.53→61.53 | 87.8%→87.8% | 0→0 | 0→0 | 1→1 | 148→148 | 0% (0 kare) | **birebir aynı** |

### sim (test1–test7)

| senaryo | IoU ö→y | @0.5 ö→y | merkez px ö→y | kilit ö→y | kesinti ö→y | kurtarma max ö→y | IDsw ö→y | drift ö→y | açı aktif | durum |
|---|---|---|---|---|---|---|---|---|---|---|
| test1 | 0.925→0.925 | 1.000→1.000 | 0.25→0.25 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% * | **birebir aynı** |
| test2 | 0.435→0.435 | 0.447→0.447 | 1.59→1.59 | 98.0%→98.0% | 0→0 | 0→0 | 0→0 | 210→210 | 0% * | **birebir aynı** |
| test3 | 0.560→0.560 | 0.612→0.612 | 1.75→1.75 | 94.6%→94.6% | 1→1 | 1→1 | 0→0 | 458→458 | 0% * | **birebir aynı** |
| test4 | 0.866→0.866 | 1.000→1.000 | 0.57→0.57 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% * | **birebir aynı** |
| test5 | 0.897→0.897 | 1.000→1.000 | 0.15→0.15 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% * | **birebir aynı** |
| test6 | 0.747→0.747 | 0.806→0.806 | 0.99→0.99 | 78.1%→78.1% | 3→3 | 30→30 | 1→1 | 282→282 | 0% * | **birebir aynı** |
| test7 | 0.764→0.764 | 0.907→0.907 | 0.97→0.97 | 100.0%→100.0% | 0→0 | 0→0 | 0→0 | yok→yok | 0% * | **birebir aynı** |

### VisDrone

| senaryo | IoU ö→y | @0.5 ö→y | merkez px ö→y | kilit ö→y | kesinti ö→y | kurtarma max ö→y | IDsw ö→y | drift ö→y | açı aktif | durum |
|---|---|---|---|---|---|---|---|---|---|---|
| 0000117/23 | 0.701→0.701 | 0.974→0.974 | 5.51→5.51 | 100.0%→100.0% | 0→0 | 0→0 | 0 | yok→yok | 0% * | **birebir aynı** |
| 0000268/31 | 0.000→0.000 | 0.000→0.000 | 383.61→383.61 | 71.0%→71.0% | 0→0 | 0→0 | 0 | 151→151 | 0% * | **birebir aynı** |
| 0000182/127 | 0.088→0.088 | 0.000→0.000 | 265.66→265.66 | 30.7%→30.7% | 2→2 | 2→2 | 0 | 39→39 | 0% * | **birebir aynı** |

\* VisDrone'da çekirdek içi sayaç `main.kos` üzerinden loglanmıyor; devreye
girmediği ayrıca ölçüldü (aşağıda) ve zaten metriklerin birebir aynı olması
tek başına kanıt: arama açılsaydı örnekleyici değişir, sayılar kayardı.

## İstenen kanıtlar

### G0 / dönme olmayan senaryolarda eski yol ile aynı kalıyor mu? — EVET

Alan alan karşılaştırma (IoU, @0.5, @0.3, merkez hata, kilit, kesinti,
kurtarma ort/max, ID switch, drift karesi):

    32 senaryodan 30'u FARKSIZ (fark toleransı 1e-12)
    değişen: G3_agresif (iou, @0.5, merkez), G3_kritik (9 alan)

Taban determinizmi ayrıca doğrulandı: `deney_once.json` ile geri alma sonrası
`deney_geri_al.json` arasında **0 farklı alan**.

### G3 iyileşiyor mu? — EVET (kritik seviyede), agresifte nötr

| | G3_agresif önce | sonra | G3_kritik önce | sonra |
|---|---|---|---|---|
| IoU | 0.766 | 0.760 | 0.579 | **0.704** |
| tavan IoU | 0.836 | 0.836 | 0.791 | 0.791 |
| **açık (tavan−IoU)** | 0.070 | 0.076 | **0.212** | **0.087** |
| @0.5 | 0.990 | **0.997** | 0.721 | **0.922** |
| @0.3 | 1.000 | 1.000 | 0.969 | **1.000** |
| merkez hata | 3.47 px | 3.81 px | 9.25 px | **5.07 px** |
| kilit | 100% | 100% | 96.9% | **100%** |
| kesinti | 0 | 0 | 1 | **0** |
| kurtarma max | 0 | 0 | 9 kare | **0** |
| **drift karesi** | yok | yok | **133** | **yok** |
| PSR p50 | 24.6 | **54** | 21.4 | **54** |

G3_agresif'te IoU 0.006 geriledi ama @0.5 yükseldi ve PSR ikiye katlandı;
net etki nötr sayılmalı. Nedeni açı aşımı (aşağıda).

### G4/G6'daki regresyon düzeliyor mu? — EVET, kökten

Deney 1'de G4_agresif −0.015, G4_kritik −0.012, G6_agresif −0.029 kaybetmişti.
Deney 2'de bu senaryolarda açı araması **hiç devreye girmiyor**, dolayısıyla
sayılar A3.8 ile birebir aynı:

| senaryo | ego dönme p95 | eşik | aktif kare | kullanılan açı | deney 1 Δ IoU | deney 2 Δ IoU |
|---|---|---|---|---|---|---|
| G4_agresif | 0.10 °/kare | 0.94 | 0/300 | 0.0° | −0.015 | **0.000** |
| G4_kritik | 0.30 °/kare | 0.84 | 0/300 | 0.0° | −0.012 | **0.000** |
| G6_agresif | 0.02 °/kare | 0.83 | 0/300 | 0.0° | −0.029 | **0.000** |
| G5_kritik | 0.04 °/kare | 0.92 | 0/300 | 0.0° | +0.007 | **0.000** |
| G1_kritik | 0.01 °/kare | 0.91 | 0/300 | 0.0° | −0.005 | **0.000** |

Deney 1'in sahte açı birikimi (G4_kritik'te −9.4°) burada **sıfır**.

### VisDrone'da regresyon oluşuyor mu? — HAYIR

Üç dizide de metrikler birebir aynı; açı araması hiç açılmadı:

| dizi | \|dθ\| p50 / p95 / maks (°/kare) | eşik | aktif kare | IoU ö→y |
|---|---|---|---|---|
| 117/23 | 0.041 / 0.185 / 0.326 | 0.813 | 0/342 | 0.701→0.701 |
| 268/31 | 0.012 / 0.035 / 0.073 | 0.182 | 0/971 | 0.000→0.000 |
| 182/127 | 0.034 / 0.426 / 0.558 | 3.272 | 0/356 | 0.088→0.088 |

Bu üç dizide kamera dönmesi yavaş (en fazla 0.56 °/kare); değişiklik onlara
dokunmuyor. Regresyon yok, ama fayda da yok — dürüst okuma budur.

## Kullanılan açı ve açı kestirim hatası

Gerçek referans kamera pozlarından türetiliyor (optik eksen etrafındaki
birikimli bileşen), çekirdeğin `aci` alanıyla aynı işaret sözleşmesinde.

| senaryo | aktif | ilk kare | kullanılan açı | gerçek açı | hata p50 / p95 |
|---|---|---|---|---|---|
| G3_agresif | 300/300 | 7 | −63.1 … +1.6° | −49.6 … +1.5° | 8.90° / 13.01° |
| G3_kritik | 300/300 | 7 | −112.5 … +4.6° | −106.6 … +3.2° | **2.40° / 7.69°** |
| diğer 20 kayıt | 0 | — | 0.0° | — | 0.00° |

G3_kritik'te takip iyi: 106° dönmenin p50 hatası 2.4°, yani adımın (1.54°)
1.5 katı. G3_agresif'te **aşım var**: 49.6°'lik gerçek dönmeye karşı 63.1°
kullanılmış. IoU'daki 0.006'lık gerilemenin nedeni bu. Kapalı çevrim tohumu
(`aci + dteta`) hareket yönünde bir adım fazla seçme eğiliminde; bir sonraki
deneyin konusu olabilir, bu deneyin kapsamında değil.

## Performans

**Kapalı karelerde ek maliyet sıfırdır** — aynı kod yolu, aynı örnekleyici,
tek korelasyon. 32 senaryonun 30'u bu durumda.

Açık karelerde `ara()` mikro-benchmark'ı (tek çekirdek, 56×22 kutu):

| | süre |
|---|---|
| kapalı (A3.8 yolu, 1 aday) | 256 µs |
| açık (3 aday + warpAffine) | 826 µs |
| **fark** | **+570 µs/kare** |

Tipik kare bütçesi 2600–3000 µs → açık karelerde **~%20 kare süresi**.
Dönüşümlü tam koşumda (4 tur, a38/d2 sırayla) G3_kritik p50 medyanı
2.98 → 4.36 ms; G0'da fark yok (2.70 vs 3.01 ms, ikisi de gürültü bandında).

## Kazanç / zarar dökümü

**Kazanç**
* G3_kritik — kopma tamamen ortadan kalktı: drift 133 → yok, kilit %96.9 → %100,
  kesinti 1 → 0, kurtarma max 9 kare → 0, IoU 0.579 → 0.704, @0.5 0.721 → 0.922,
  merkez hata 9.25 → 5.07 px. Tavana olan açık 0.212 → 0.087.
* G3_agresif — PSR p50 24.6 → 54 (filtre artık hedefi güvenle buluyor),
  @0.5 0.990 → 0.997.

**Zarar**
* G3_agresif — IoU 0.766 → 0.760 (−0.006), merkez hata 3.47 → 3.81 px. Nedeni
  açı aşımı (63.1° vs gerçek 49.6°).
* Açık karelerde ~%20 kare süresi. Yalnızca 2/32 senaryoda.

**Değişmeyen (30 senaryo)** — G0, G1×3, G2×2, G3_yumusak, G4×3, G5×3, G6×4,
G7×3, sim test1–7, VisDrone 117/23 · 268/31 · 182/127.

## Bilinen sınır

`G3_yumusak` gerçek −16° dönme yaşıyor ama kare-arası hızı (0.66 °/kare) eşiğin
(0.92) altında kaldığı için telafi hiç açılmıyor. Zarar yok (IoU değişmedi) ama
kazanç da yok. Eşiği düşürmek G4_kritik'i (0.30 °/kare) de açar ve deney 1'in
regresyonunu geri getirme riski taşır; bu yüzden dokunulmadı.

## Değişen dosyalar

Takipçi: `takip/cekirdekler.py` (RenkDcfCekirdek + `_Cekirdek` no-op tabanı),
`takip/izleyici.py` (tek satır: `self.cekirdek.ego_guncelle(M)`).
Ego-motion, Kalman, durum makinesi ve A3.8 bağımsız doğrulama mekanizması
**değişmedi**.

Ölçüm altyapısı (takipçi dışı): `gazebo/tani.py`'ye açı gözlem alanları,
`deney.py`'ye o alanların taşınması.
