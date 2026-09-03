# Benchmark — GAZEBO FAZ B (A3.9)

G1–G7 kontrollü senaryo ailesi, her biri **yumuşak** ve **agresif** olmak üzere
iki şiddette; artı eşiği kuşatmak için 7 ek koşum. **Takipçi A3.8, hiç
değişmedi** — `takip/izleyici.py`, `egomotion.py`, `cekirdekler.py`,
`tespit.py`, `mosse.py` dosyalarının hiçbirine dokunulmadı. Bu faz yalnızca
teşhistir; çözüm Faz C'de.

> Faz A tabanı için `BENCHMARK_GAZEBO.md`. Sim (`BENCHMARK_BASELINE.md`) ve
> VisDrone (`RAPOR_VISDRONE.md`) tablolarıyla **birleştirilmemelidir**.

## Ölçüm ortamı

Faz A ile aynı: WSL2 Ubuntu 22.04, gz sim 8.14.0 (Harmonic), llvmpipe yazılım
render, `-s -r --headless-rendering`, 640×480, `renk_dcf` çekirdeği, Python
3.10 / OpenCV 4.11.0 / NumPy 1.26.4. Her senaryo 300 kare (10 s), 30 Hz.

    python3 -m gazebo.kaydet --hepsi      # 14 senaryoyu kaydet
    python3 -m gazebo.tani                # ölç + K1-K8 eşle -> cikti/fazb_tani.json

Kayıt sağlığı 22 koşumun **hepsinde** aynı: 300/300 kare, düşen kare **0**,
RTF 0.95–1.00, senkron boşluğu ort 2.67 ms / maks 4.17 ms (tolerans 20 ms).

## Senaryo tasarımı

### Ortak baz — neden kamera hedefi takip ediyor

G1–G7'de kamera sabit 4.8 m/s ile dünya +X yönünde süzülür ve hedefin
başlangıç noktasının tam üstünden başlar. Sonuç: hedef görüntüde **nominal
olarak sabit** kalır (u≈320, v≈264), yani

* görüntüdeki **hedef** hareketi = yalnızca hedef bozulması,
* **arka plandaki** akış = yalnızca kamera bozulması,
* 300 kare boyunca hedef kadraj dışına çıkmaz (kenar payı ~267 px).

Alternatif (G0'daki gibi sabit kamera) denendi ve elendi: hedefin kadraj payı
53 px'e iniyor, kamera salınım genliği 3.6 m'yi geçemiyor ve agresif seviye
kurulamıyordu. Bazın kendi ego yükü **1.78 px/kare**'dir; bu yüzden G1–G7
tabloları G0 ile değil, **kendi yumuşak seviyeleriyle** karşılaştırılmalıdır.

### Kamera yerleşimi

Drone modeli dik durur; nadir dönüşü **kamera sensörünün kendi `<pose>`'una**
taşındı. Böylece gövde `wz` = görüntü düzlemi dönmesi, gövde `wy` = pitch,
gövde `vx` = görüntüde sağa. Nadir dönüşü model pozunda kalsaydı gövde +X'i
dünya −Z olurdu ve "ileri git" komutu kamerayı aşağı sürerdi. Kameranın dünya
pozu = model pozu ∘ sensör pozu; bileşke `gazebo/kaydet.py` içinde alınıp
`pozlar.csv`'ye `kam_*` olarak yazılır, yani `veri/gazebo.py` etkilenmez.

### Zamana bağlı hareket

SDF'teki `initial_linear/angular` yalnızca sabit hız verir. `Surucu` her poz
örneğinde (120 Hz, **sim** zamanı damgalı) senaryo profilini değerlendirip
`/model/<ad>/cmd_vel` üzerine Twist yayınlar. Duvar saatiyle yayın yapmak
RTF dalgalandığında sim zamanında düzensiz bir profil üretirdi — G0'da aynı
tuzak `real_time_factor` üzerinden yaşanmıştı.

### Şiddet seviyeleri

| Aile | Değişken | yumuşak | agresif | *kritik* (ek) |
|---|---|---|---|---|
| G1 kamera ileri | dünya X ötelemesi | 12 m/s @ 0.40 Hz | 40 m/s @ 0.50 Hz | 80 m/s @ 0.70 Hz |
| G2 kamera yanal | dünya Y ötelemesi | 12 m/s @ 0.40 Hz | 40 m/s @ 0.50 Hz | — |
| G3 kamera yaw | görüntü düzlemi dönmesi | 0.35 rad/s @ 0.35 Hz (±9°) | 1.40 rad/s @ 0.50 Hz (±26°) | 3.00 rad/s @ 0.50 Hz (±55°) |
| G4 kamera pitch | nadirden sapma | 0.20 rad/s @ 0.30 Hz (±6°) | 0.80 rad/s @ 0.45 Hz (±16°) | 2.00 rad/s @ 0.80 Hz (±23°) |
| G5 çapraz | Lissajous (fy = 2fx) | 10 m/s @ 0.35 Hz | 32 m/s @ 0.45 Hz | 70 m/s @ 0.70 Hz |
| G6 birleşik | G5 kamera + hedef manevrası | 10 m/s + (±0.25 rad/s, ±2 m/s) | 32 m/s + (±0.60 rad/s, ±3 m/s) | — |
| G7 hedef ivmesi | yamuk hız darbesi | 4.8→16 m/s, 3.0 s | 4.8→30 m/s, 1.75 s | 4.8→45 m/s, 1.0 s |

**Profiller kosinüstür, sinüs değil.** Profil bir *hız* verir; görüntüde
görülen şey onun integralidir. Hız sinüs olursa konum (1−cos) biçimini alır:
tek yönlü ve genliğin **iki katı** kadar sapar. Ölçüldü — G4 agresifin sinüs
sürümünde pitch açısı hedeflenen ±16.2° yerine 0..32.4° gitti ve hedef 3
saniyede kadrajın sağ kenarına dayandı (u = 639).

## Yöntem — teşhis nasıl ölçüldü

`gazebo/tani.py` takipçiye dokunmaz. Standart metrikler (IoU, @0.5, merkez
hata, kilit, kurtarma, FPS, gecikme, drift karesi) `main.kos()`'tan **olduğu
gibi** alınır; `main.HedefTakip` geçici olarak yalnızca iç durumu yazan bir
alt sınıfla değiştirilir. Hiçbir eşik, hiçbir karar değişmez — G0 bu koşum
altında Faz A'nın sayısını birebir tekrarlıyor (IoU 0.912, kilit %100).

### Bağımsız ego referansı

"Takipçinin M'si doğru mu" sorusunu takipçiye sormak anlamsızdır. Referans
kayıtlı **kamera pozundan** üretilir: (k−1). karenin görüntü noktaları zemin
düzlemine (z=0) geri izdüşürülür, k. karenin kamerasına ileri izdüşürülür. Bu,
arka planın gerçek kare-arası eşleşmesidir. Üç sayı ayrılır:

* **e_model** — gerçek eşleşmeye en iyi *benzerlik* dönüşümünün artığı. Modelin
  kendi sınırı. Nadir kamerada 0; pitch'te büyür. → K6 (ego yüzü)
* **e_ego** — takipçinin M'sinin artığı. e_model bunun alt sınırıdır.
* **e_kest** = e_ego − e_model — kestirimin kendi hatası. → K1

Bu ayrım olmadan K1 ile K6 birbirinden ayrılamaz.

### Tavan IoU

GT kutusu aracın 3B kutusunun **eksen hizalı** izdüşümüdür. Araç görüntüde
dönünce (kamera yaw'ı ya da hedefin kendi manevrası) bu kutu büyür; sabit
en-boy oranlı hiçbir takipçi onu dolduramaz. `tavan_iou` = GT merkezine tam
oturmuş, kilit anındaki boyutta kutunun IoU'su. Kopma ölçütü mutlak IoU değil,
**tavan − gerçek açığıdır**; G0'da bu açık 0.025'tir ve sağlıklı tabanı verir.

Kopma ölçütü: `açık > 0.10` **veya** drift karesi var **veya** kilit < %98.

## Sonuçlar

| Senaryo | Şiddet | IoU | Lock | Drift | e_ego p50/p95 | d/r_etkin | KF hız hatası | Ana hipotez |
|---|---|---|---|---|---|---|---|---|
| **G0**<br>kontrol | - | 0.912 | 100.0% | yok | 0.07 / 0.09 | 0.08 | 0.41 | - |
| **G1_yumusak**<br>kamera ileri | yumusak | 0.899 | 100.0% | yok | 0.07 / 0.13 | 0.20 | 0.45 | - |
| **G1_agresif**<br>kamera ileri | agresif | 0.897 | 100.0% | yok | 0.07 / 0.15 | 0.66 | 0.51 | - |
| **G2_yumusak**<br>kamera yanal | yumusak | 0.862 | 100.0% | yok | 0.08 / 0.12 | 0.20 | 0.64 | - |
| **G2_agresif**<br>kamera yanal | agresif | 0.859 | 100.0% | yok | 0.09 / 0.17 | 0.63 | 0.44 | - |
| **G3_yumusak**<br>kamera yaw | yumusak | 0.862 | 100.0% | yok | 0.07 / 0.10 | 0.01 | 0.51 | K6 (0.67) *gizli* |
| **G3_agresif**<br>kamera yaw | agresif | 0.766 | 100.0% | yok | 0.09 / 0.15 | 0.03 | 0.84 | K6 (2.66) *gizli* |
| **G4_yumusak**<br>kamera pitch | yumusak | 0.885 | 100.0% | yok | 0.27 / 0.46 | 0.14 | 0.56 | K6 (0.77) *gizli* |
| **G4_agresif**<br>kamera pitch | agresif | 0.871 | 100.0% | yok | 1.07 / 1.57 | 0.56 | 1.26 | K6 (3.09) *gizli* |
| **G5_yumusak**<br>çapraz kamera | yumusak | 0.888 | 100.0% | yok | 0.08 / 0.15 | 0.23 | 0.46 | - |
| **G5_agresif**<br>çapraz kamera | agresif | 0.883 | 100.0% | yok | 0.10 / 0.19 | 0.70 | 0.47 | - |
| **G6_yumusak**<br>kamera + hedef | yumusak | 0.807 | 100.0% | yok | 0.08 / 0.14 | 0.18 | 1.07 | K5 (0.54) *gizli* |
| **G6_agresif**<br>kamera + hedef | agresif | 0.618 | 100.0% | 294 | 0.09 / 0.19 | 0.49 | 2.12 | K5 (1.06) |
| **G7_yumusak**<br>ani hedef ivmesi | yumusak | 0.893 | 100.0% | yok | 0.07 / 0.11 | 0.18 | 0.77 | - |
| **G7_agresif**<br>ani hedef ivmesi | agresif | 0.847 | 100.0% | yok | 0.07 / 0.12 | 0.38 | 1.88 | K5 (0.94) |

*gizli* = hipotez göstergesi yüklü ama senaryo henüz kopmuyor. Puan
0.5'in altındaysa hiçbir hipotez yüklenmemiştir ve `-` yazılır (G0'ın kendi en
yüksek puanı 0.21).

### Ek tarama — eşiği kuşatmak için

G1–G5'in agresif seviyesinde **hiçbiri kopmadı**; kamera eşiği ancak bir alt
sınır olarak bilinebiliyordu. `_kritik` seviyeler eşiği kuşatır.
`G6_agresif_hedef` ise G6'nın hedef profilini bozulmasız kamerayla koşarak
2×2 ayrıştırmanın eksik hücresini doldurur (kamera-tek eşi zaten
`G5_agresif`'tir).

| Senaryo | Şiddet | IoU | Lock | Drift | e_ego p50/p95 | d/r_etkin | KF hız hatası | Ana hipotez |
|---|---|---|---|---|---|---|---|---|
| **G1_kritik**<br>kamera ileri | kritik | 0.890 | 100.0% | yok | 0.08 / 0.22 | 1.32 | 0.72 | - |
| **G3_kritik**<br>kamera yaw | kritik | 0.579 | 96.9% | 133 | 0.12 / 0.25 | 0.05 | 1.21 | K6 (5.71) |
| **G4_kritik**<br>kamera pitch | kritik | 0.810 | 100.0% | yok | 2.74 / 4.21 | 1.31 | 5.62 | K6 (7.7) *gizli* |
| **G5_kritik**<br>çapraz kamera | kritik | 0.862 | 100.0% | yok | 0.16 / 0.33 | 1.47 | 0.69 | K1 (0.56) *gizli* |
| **G7_kritik**<br>ani hedef ivmesi | kritik | 0.865 | 100.0% | yok | 0.07 / 0.12 | 0.65 | 1.70 | K5 (0.85) *gizli* |
| **G6_agresif_hedef**<br>kamera + hedef | agresif (hedef-tek) | 0.662 | 97.3% | yok | 0.05 / 0.10 | 0.04 | 1.71 | K5 (0.86) |
| **G6_agresif_durakli**<br>kamera + hedef | agresif (duraklamali) | 0.383 | 87.8% | 148 | 0.10 / 0.26 | 0.49 | 4.19 | K7 (19.97) |

### Tam metrik tablosu

| senaryo | IoU | tavan IoU | @0.5 | @0.3 | merkez px | kilit % | kesinti | kurtarma max | FPS | gecikme p50/p95 ms | drift kare | e_ego p50/p95 | e_model p95 | e_kest p95 | d_görüntü p95 | r_etkin | d/r p95 | d_artık/r p95 | sıçrama p95 | ego birim % | sıçrama red % | yanlış kilit % | kf hız p50/p95 | kamera açısal p50/p95 °/s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G0 | 0.912 | 0.938 | 1.000 | 1.000 | 1.24 | 100.0 | 0 | 0 | 452 | 1.86/3.52 | yok | 0.07/0.09 | 0.00 | 0.09 | 1.84 | 23.1 | 0.08 | 0.08 | 1.05 | 0.0 | 0.0 | 0.0 | 0.11/0.41 | 0.0/0.0 |
| G1_yumusak | 0.899 | 0.973 | 1.000 | 1.000 | 1.40 | 100.0 | 0 | 0 | 445 | 1.96/3.50 | yok | 0.07/0.13 | 0.00 | 0.13 | 4.57 | 23.0 | 0.20 | 0.09 | 1.04 | 0.0 | 0.0 | 0.0 | 0.11/0.45 | 0.0/0.0 |
| G1_agresif | 0.897 | 0.963 | 1.000 | 1.000 | 1.24 | 100.0 | 0 | 0 | 420 | 2.08/3.77 | yok | 0.07/0.15 | 0.00 | 0.15 | 15.26 | 23.0 | 0.66 | 0.09 | 1.14 | 0.0 | 0.0 | 0.0 | 0.17/0.51 | 0.0/0.0 |
| G2_yumusak | 0.862 | 0.944 | 1.000 | 1.000 | 2.28 | 100.0 | 0 | 0 | 442 | 1.90/3.70 | yok | 0.08/0.12 | 0.00 | 0.12 | 4.50 | 22.8 | 0.20 | 0.08 | 1.98 | 0.0 | 0.0 | 0.0 | 0.15/0.64 | 0.0/0.0 |
| G2_agresif | 0.859 | 0.906 | 1.000 | 1.000 | 1.63 | 100.0 | 0 | 0 | 452 | 1.87/3.54 | yok | 0.09/0.17 | 0.00 | 0.17 | 15.04 | 24.1 | 0.63 | 0.08 | 0.89 | 0.0 | 0.0 | 0.0 | 0.18/0.44 | 0.0/0.0 |
| G3_yumusak | 0.862 | 0.908 | 1.000 | 1.000 | 1.85 | 100.0 | 0 | 0 | 426 | 2.00/3.91 | yok | 0.07/0.10 | 0.00 | 0.10 | 0.29 | 26.8 | 0.01 | 0.07 | 1.47 | 0.0 | 0.0 | 0.0 | 0.12/0.51 | 13.9/20.1 |
| G3_agresif | 0.766 | 0.836 | 0.990 | 1.000 | 3.47 | 100.0 | 0 | 0 | 413 | 2.07/4.05 | yok | 0.09/0.15 | 0.00 | 0.15 | 1.18 | 33.3 | 0.03 | 0.05 | 2.70 | 0.0 | 0.0 | 0.0 | 0.19/0.84 | 55.9/79.9 |
| G4_yumusak | 0.885 | 0.876 | 1.000 | 1.000 | 1.44 | 100.0 | 0 | 0 | 442 | 1.93/3.61 | yok | 0.27/0.46 | 0.46 | 0.05 | 3.32 | 23.3 | 0.14 | 0.10 | 1.24 | 0.0 | 0.0 | 0.0 | 0.12/0.56 | 7.9/11.8 |
| G4_agresif | 0.871 | 0.949 | 1.000 | 1.000 | 1.72 | 100.0 | 0 | 0 | 438 | 1.91/3.72 | yok | 1.07/1.57 | 1.85 | 0.07 | 13.32 | 24.6 | 0.56 | 0.15 | 1.27 | 0.0 | 0.0 | 0.0 | 0.47/1.26 | 32.2/45.6 |
| G5_yumusak | 0.888 | 0.887 | 1.000 | 1.000 | 1.68 | 100.0 | 0 | 0 | 450 | 1.97/3.51 | yok | 0.08/0.15 | 0.00 | 0.15 | 5.17 | 23.0 | 0.23 | 0.08 | 1.18 | 0.0 | 0.0 | 0.0 | 0.12/0.46 | 0.0/0.0 |
| G5_agresif | 0.883 | 0.939 | 1.000 | 1.000 | 1.62 | 100.0 | 0 | 0 | 465 | 1.84/3.53 | yok | 0.10/0.19 | 0.00 | 0.19 | 16.47 | 23.5 | 0.70 | 0.09 | 1.06 | 0.0 | 0.0 | 0.0 | 0.20/0.47 | 0.0/0.0 |
| G6_yumusak | 0.807 | 0.856 | 1.000 | 1.000 | 2.81 | 100.0 | 0 | 0 | 437 | 1.90/3.80 | yok | 0.08/0.14 | 0.00 | 0.14 | 5.36 | 27.5 | 0.18 | 0.08 | 3.15 | 0.0 | 0.0 | 0.0 | 0.23/1.07 | 0.0/0.0 |
| G6_agresif | 0.618 | 0.830 | 0.684 | 0.959 | 8.40 | 100.0 | 0 | 0 | 411 | 2.02/4.42 | 294 | 0.09/0.19 | 0.00 | 0.19 | 16.47 | 50.3 | 0.49 | 0.09 | 5.34 | 0.0 | 0.0 | 0.0 | 0.45/2.12 | 0.0/0.0 |
| G7_yumusak | 0.893 | 0.938 | 1.000 | 1.000 | 1.29 | 100.0 | 0 | 0 | 447 | 1.92/3.62 | yok | 0.07/0.11 | 0.00 | 0.11 | 4.22 | 21.0 | 0.18 | 0.26 | 1.37 | 0.0 | 0.0 | 0.0 | 0.14/0.77 | 0.0/0.0 |
| G7_agresif | 0.847 | 0.972 | 1.000 | 1.000 | 1.66 | 100.0 | 0 | 0 | 433 | 1.97/3.72 | yok | 0.07/0.12 | 0.00 | 0.12 | 9.49 | 22.9 | 0.38 | 0.45 | 2.33 | 0.0 | 0.0 | 0.0 | 0.16/1.88 | 0.0/0.0 |
| G1_kritik | 0.890 | 0.943 | 1.000 | 1.000 | 1.43 | 100.0 | 0 | 0 | 455 | 1.86/3.52 | yok | 0.08/0.22 | 0.00 | 0.22 | 30.36 | 23.0 | 1.32 | 0.10 | 1.09 | 0.0 | 0.0 | 0.0 | 0.29/0.72 | 0.0/0.0 |
| G3_kritik | 0.579 | 0.791 | 0.721 | 0.969 | 9.25 | 96.9 | 1 | 9 | 400 | 1.95/4.32 | 133 | 0.12/0.25 | 0.00 | 0.25 | 2.51 | 41.8 | 0.05 | 0.04 | 3.48 | 0.0 | 0.0 | 0.0 | 0.61/1.21 | 119.8/171.2 |
| G4_kritik | 0.810 | 0.842 | 1.000 | 1.000 | 1.57 | 100.0 | 0 | 0 | 440 | 1.89/3.75 | yok | 2.74/4.21 | 4.62 | 0.13 | 33.30 | 26.4 | 1.31 | 0.24 | 3.89 | 0.0 | 0.0 | 0.0 | 1.84/5.62 | 79.4/114.1 |
| G5_kritik | 0.862 | 0.909 | 1.000 | 1.000 | 1.70 | 100.0 | 0 | 0 | 470 | 1.83/3.43 | yok | 0.16/0.33 | 0.00 | 0.33 | 35.83 | 24.1 | 1.47 | 0.10 | 1.13 | 0.0 | 0.0 | 0.0 | 0.45/0.69 | 0.0/0.0 |
| G7_kritik | 0.865 | 0.961 | 1.000 | 1.000 | 2.27 | 100.0 | 0 | 0 | 453 | 1.89/3.52 | yok | 0.07/0.12 | 0.00 | 0.12 | 15.15 | 22.5 | 0.65 | 0.73 | 1.90 | 0.0 | 0.0 | 0.0 | 0.13/1.70 | 0.0/0.0 |
| G6_agresif_hedef | 0.662 | 0.866 | 0.915 | 1.000 | 7.54 | 97.3 | 1 | 8 | 419 | 1.93/4.01 | yok | 0.05/0.10 | 0.00 | 0.10 | 1.25 | 34.3 | 0.04 | 0.09 | 5.31 | 0.0 | 0.0 | 0.0 | 0.60/1.71 | 0.0/0.0 |
| G6_agresif_durakli | 0.383 | 0.855 | 0.469 | 0.483 | 61.53 | 87.8 | 0 | 0 | 388 | 2.12/4.31 | 148 | 0.10/0.26 | 0.00 | 0.26 | 16.59 | 42.4 | 0.49 | 0.11 | 3.30 | 0.0 | 0.0 | 39.9 | 0.66/4.19 | 0.0/0.0 |

### K1–K8 puanları

Puan = gösterge / max(G0 tabanı, fiziksel döşeme). "Taban davranışın kaç katı".

| senaryo | kopma | K1 | K2 | K3 | K4 | K5 | K6 | K7 | K8 | ana | ikincil |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G0 | – | 0.15 | 0.00 | 0.08 | 0.00 | 0.21 | 0.00 | 0.00 | 0.00 | **-** | - |
| G1_yumusak | – | 0.21 | 0.00 | 0.09 | 0.00 | 0.22 | 0.00 | 0.00 | 0.00 | **-** | - |
| G1_agresif | – | 0.25 | 0.00 | 0.09 | 0.00 | 0.26 | 0.00 | 0.00 | 0.00 | **-** | - |
| G2_yumusak | – | 0.21 | 0.00 | 0.08 | 0.00 | 0.32 | 0.00 | 0.00 | 0.00 | **-** | - |
| G2_agresif | – | 0.28 | 0.00 | 0.08 | 0.00 | 0.22 | 0.00 | 0.00 | 0.00 | **-** | - |
| G3_yumusak | – | 0.17 | 0.00 | 0.07 | 0.00 | 0.25 | 0.67 | 0.00 | 0.00 | **K6** | - |
| G3_agresif | – | 0.24 | 0.00 | 0.05 | 0.00 | 0.42 | 2.66 | 0.00 | 0.00 | **K6** | - |
| G4_yumusak | – | 0.08 | 0.00 | 0.10 | 0.00 | 0.28 | 0.77 | 0.00 | 0.00 | **K6** | - |
| G4_agresif | – | 0.11 | 0.00 | 0.15 | 0.00 | 0.63 | 3.09 | 0.00 | 0.00 | **K6** | K5 |
| G5_yumusak | – | 0.25 | 0.00 | 0.08 | 0.00 | 0.23 | 0.00 | 0.00 | 0.00 | **-** | - |
| G5_agresif | – | 0.32 | 0.00 | 0.09 | 0.00 | 0.24 | 0.00 | 0.00 | 0.00 | **-** | - |
| G6_yumusak | – | 0.24 | 0.00 | 0.08 | 0.00 | 0.54 | 0.00 | 0.00 | 0.00 | **K5** | - |
| G6_agresif | **EVET** | 0.32 | 0.00 | 0.09 | 0.00 | 1.06 | 0.00 | 0.00 | 0.00 | **K5** | - |
| G7_yumusak | – | 0.19 | 0.00 | 0.26 | 0.00 | 0.39 | 0.00 | 0.00 | 0.00 | **-** | - |
| G7_agresif | **EVET** | 0.19 | 0.00 | 0.45 | 0.00 | 0.94 | 0.00 | 0.00 | 0.00 | **K5** | - |
| G1_kritik | – | 0.36 | 0.00 | 0.10 | 0.00 | 0.36 | 0.00 | 0.00 | 0.00 | **-** | - |
| G3_kritik | **EVET** | 0.41 | 0.00 | 0.04 | 0.00 | 0.61 | 5.71 | 0.00 | 0.45 | **K6** | K5 |
| G4_kritik | – | 0.22 | 0.00 | 0.24 | 0.00 | 2.81 | 7.70 | 0.00 | 0.00 | **K6** | K5 |
| G5_kritik | – | 0.56 | 0.00 | 0.10 | 0.00 | 0.35 | 0.00 | 0.00 | 0.00 | **K1** | - |
| G7_kritik | – | 0.19 | 0.00 | 0.73 | 0.00 | 0.85 | 0.00 | 0.00 | 0.00 | **K5** | K3 |
| G6_agresif_hedef | **EVET** | 0.17 | 0.00 | 0.09 | 0.00 | 0.86 | 0.00 | 0.00 | 0.40 | **K5** | - |
| G6_agresif_durakli | **EVET** | 0.44 | 0.00 | 0.11 | 0.00 | 2.10 | 0.00 | 19.97 | 0.00 | **K7** | K5 |

## Bulgular

### 1. Ego-motion katmanı sorun değil — K1, K2, K3, K4 ölü

Test edilen **hiçbir** senaryoda:

* `ego_birim_orani` = **%0.0** (M hiçbir karede birim matrise düşmedi) → **K2 ölü**
* `sicrama_red_orani` = **%0.0** (PSR yeterliyken hiçbir ölçüm kapıda atılmadı) → **K4 ölü**
* `e_kest_p95` ≤ **0.33 px** (en kötü: G5_kritik, 70 m/s Lissajous) → **K1 ölü**

K3 de ateşlenmiyor ama **nedeni ölçüldü ve şaşırtıcı**: G1_kritik'te ham
`d_görüntü/r_etkin = 1.32`, yani kare-arası ham kayma etkin yarıçapı %32
aşıyor. Buna rağmen sıçrama kapısına gelen **gerçek artık 1.09 px** (yarıçapın
%5'i). Ham kaymanın tamamını önce ego M'si, sonra KF hızı soğuruyor. Ham oranla
puanlamak "arama yarıçapı yetmedi" der; oysa hiçbir şey kaçmamıştır. Bu yüzden
K3'ün göstergesi `d_artık/r_etkin`'dir (ego sonrası bağımsız hedef hareketi) ve
o da 0.73'ü hiç geçmedi.

**Sonuç: A3.9'da ego-motion katmanına dokunmak yanlış olur.**

### 2. Kamera ötelemesi hiç koparmıyor

G1/G2/G5, **80 m/s**'ye (29.6 px/kare ham arka plan kayması) kadar:
IoU açığı ≤ 0.074, drift yok, kilit %100, kurtarma gerekmedi. Çapraz (G5)
hareket eksen hizalıdan **daha kolay** çıktı — Lissajous akış yönünü sürekli
döndürüyor ama seyrek LK + RANSAC bundan etkilenmiyor.

### 3. Kamera dönmesi koparıyor — ve suç ego'da değil, DCF şablonunda

G3 (yaw) tek başına bir kopma üretti:

| yaw genliği | açısal hız p95 | IoU | tavan | açık | drift | @0.5 | PSR p50 |
|---|---|---|---|---|---|---|---|
| ±9° | 20 °/s | 0.862 | 0.908 | 0.046 | yok | 1.000 | 45.6 |
| ±26° | 80 °/s | 0.766 | 0.836 | 0.070 | yok | 0.990 | 24.6 |
| **±55°** | **171 °/s** | **0.579** | 0.791 | **0.213** | **133** | **0.721** | 21.4 |

Kritik ayrım: **e_model = 0.00 px**. Benzerlik dönüşümü görüntü düzlemi
dönmesini **tam** temsil ediyor, ego katmanı dönmeyi doğru ölçüp KF'ye
aktarıyor (`kf.tahmin` konumu *ve hızı* döndürüyor). Ama **DCF şablonu
döndürülmüyor**: `cekirdekler.py:RenkDcfCekirdek` yamayı her zaman eksen
hizalı kesiyor. Şablon her karede 5.7°'ye kadar (G3_kritik, `ego_donme_p95`)
uyumsuzlaşıyor, PSR 113'ten 21'e düşüyor, kutu sürükleniyor.

Bu yüzden K6 puanlaması **iki yüzlüdür**: ego yüzü (`e_model`, yalnızca
pitch'te) ve görünüm yüzü (`kamera_acisal_hiz`, yaw'da). Tek göstergeyle
puanlansaydı G3'ün kopması yanlışlıkla K5'e yazılırdı.

### 4. Kamera pitch'i en yüksek gizli yükü taşıyor ama koparmıyor

G4_kritik'te `e_ego_p95` **4.21 px** — G0'ın 47 katı. Ve bunun **tamamı model
hatası**: `e_model_p95` 4.62, `e_kest_p95` yalnızca 0.13. Yani LK/RANSAC
kusursuz çalışıyor, benzerlik dönüşümü perspektifi temsil edemiyor. KF hız
hatası 5.62 px'e çıkıyor. **Buna rağmen IoU açığı 0.032, drift yok.** K6 puanı
7.70 ile tablodaki en yüksek değer ama henüz kopmaya dönüşmemiş.

### 5. Hedef ivmesi tek başına koparmıyor

G7, 4.8 → **45 m/s**'ye 0.15 s'lik rampayla (14.9 px/kare bağıl hız): IoU açığı
0.096, drift yok, kilit %100. KF sabit-hız modeli ivmeyi 2 px altı hatayla
soğuruyor. G7_agresif (0.126) ile G7_kritik (0.096) arasındaki tersinme
gürültü seviyesindedir; G7 ailesi kopma eşiğinin **kenarında** ama üstünde
değil.

### 6. Birleşik durumda kamera katkısı toplamsal DEĞİL

2×2 ayrıştırma (hepsi agresif seviyede):

| | hedef manevrası yok | hedef manevrası var |
|---|---|---|
| **kamera bozulması yok** | G0: açık 0.025 | `G6_agresif_hedef`: açık **0.205**, kilit %97.3, 1 kesinti (8 karede kurtarıldı) |
| **kamera bozulması var** | `G5_agresif`: açık 0.056 | `G6_agresif`: açık **0.212**, **drift 294** |

Birleşik açık ≈ hedef-tek açığı. Kamera hareketi kopmayı **derinleştirmiyor**
ama **geri dönüşü engelliyor**: hedef-tek durumda tek kesinti 8 karede
kurtarılıyor, birleşikte kurtarma hiç olmuyor ve son karelerde kalıcı drift
başlıyor. Baskın bileşen **hedef manevrasıdır**.

### 7. Tasarım hatası olarak bulunan ve ayrılan bir tuzak

G6_agresif'in ilk sürümünde hız modülasyonu ±5.0 m/s'ydi: hedefin dünya hızı
4.8 ± 5.0, yani 299 karenin **69'unda 1 m/s'nin altına, tepe noktasında tam
0'a** iniyordu. Araç duruyor demektir ve bu, takipçinin **belgelenmiş** bir
sınırını tetikler (`izleyici.py:_bagimsiz_dogrula`: "gerçekten 20 kare boyunca
duran bir araç bu testle yanlış kilit sanılır"). Ölçüldü: yanlış kilit oranı
**%39.9**, IoU açığı **0.472**, K7 puanı **19.97**.

Bu, "manevra eşiği" değil bilinen bir sınırın yeniden gösterilmesidir. G6
agresif ±3.0 m/s'ye çekildi (hız 1.8–7.8 m/s, araç hiç durmuyor) ve duraklamalı
sürüm `G6_agresif_durakli` olarak **ayrı tutuldu** — iki farklı soruyu ayrı
ayrı yanıtlıyorlar.

## Kopma eşikleri

### 1. Kamera hareketi kaynaklı kopma eşiği

| kamera hareketi | test edilen en yüksek | kopma | eşik |
|---|---|---|---|
| öteleme (ileri / yanal / çapraz) | 80 m/s = 29.6 px/kare | **hayır** | test aralığının üstünde (> 30 px/kare) |
| **yaw (görüntü düzlemi dönmesi)** | 171 °/s, ±55° | **evet, kare 133** | **80–171 °/s arası; enterpolasyonla ~120 °/s (±40° genlik, ~4 °/kare)** |
| pitch (nadirden sapma) | 114 °/s, ±23° | hayır | test aralığının üstünde; e_ego 4.2 px'e çıkmasına rağmen |

**Kamera hareketinin koparttığı tek kanal dönmedir**, ve bunun ölçüsü çizgisel
hız değil **açısal hızdır**. Pratik eşik: kare başına **~4°** görüntü dönmesi.

### 2. Hedef hareketi kaynaklı kopma eşiği

| hedef hareketi | test edilen en yüksek | kopma | eşik |
|---|---|---|---|
| saf ivme (düz çizgi) | 4.8→45 m/s, 0.15 s rampa | **hayır** (açık 0.096) | test aralığının üstünde |
| manevra (yön + hız) | ±18° başlık, 1.8–7.8 m/s | **evet** (açık 0.205, kilit %97.3) | **±18° başlık salınımı + ±3 m/s civarı** |
| duraklama (hız → 0) | 0–9.8 m/s | **evet** (açık 0.472, y.kilit %39.9) | bilinen sınır, ivme eşiği değil |

**Hedef tarafında eşik ivmede değil, görünüm/yön değişimindedir.** KF sabit-hız
modeli 45 m/s'lik bir fırlamayı soğuruyor; aracı görüntüde 18° döndüren bir
manevra soğuramıyor — çünkü sorun tahmin değil, **şablonun aracın yeni
görünümüne uymaması**.

### 3. İkisinin birlikte olduğu durumda kopma eşiği

Birleşik eşik, **hedef eşiğiyle aynı noktadadır** (açık 0.205 → 0.212); kamera
bozulması eşiği aşağı çekmiyor. Ama kopmanın **karakteri** değişiyor:

* hedef-tek: kilit %97.3, 1 kesinti, **8 karede kurtarma**, kalıcı drift yok
* birleşik: kilit %100 (!), kesinti yok, ama **294. karede kalıcı drift**

Yani kamera hareketi kopmayı gizliyor: takipçi kendini KİLİTLİ sanmaya devam
ediyor, yeniden tespit hiç tetiklenmiyor, kutu sessizce sürükleniyor. Kamera
hareketi bağımsız doğrulayıcıların (zemine çakılma testi) **duyarlılığını
düşürüyor** — hareketli arka plan, sürüklenen kutuyu da "zeminden bağımsız
hareket ediyor" gibi gösteriyor.

## Faz C için önerilen ilk tek değişiklik

**DCF şablonunu ego M'sinin ölçtüğü dönme ile hizalamak** — yani
`RenkDcfCekirdek._kanallar` içindeki `getRectSubPix` çağrısını, birikimli
görüntü dönmesini geri alan bir `warpAffine`'e çevirmek.

Gerekçe, tablodan:

1. **Kopan iki senaryodan birinin doğrudan nedeni bu** (G3_kritik, K6 = 5.71).
   Ego katmanı dönmeyi zaten doğru ölçüyor — `e_model = 0.00 px`. Bilgi
   mevcut, kullanılmıyor.
2. **Diğer kopan senaryonun da payı burada.** G6/G7'de hedefin kendisi
   görüntüde dönüyor; aynı hizalama mekanizması hedef başlığı için de
   çalıştırılabilir (KF hız yönünden türetilerek).
3. **En düşük riskli değişiklik.** `takip/cekirdekler.py` içinde tek bir
   fonksiyonu etkiler, ego katmanına ve durum makinesine dokunmaz. G0 taban
   davranışı korunmalıdır (dönme sıfırken `warpAffine` birim dönüşümdür).
4. **Rakiplerinden daha yüksek getirili.** K1/K2/K3/K4 ölü — oralara yapılacak
   iş sıfır kazanç getirir. K6'nın pitch yüzü (homografi) daha büyük bir
   değişiklik ve henüz kopma üretmiyor. K7 yalnızca duran araçta ateşleniyor,
   o da zaten belgelenmiş bir sınır.

**Beklenen ölçülebilir etki:** G3_kritik'te PSR p50 21 → 60+ bandına, IoU açığı
0.213 → 0.08 altına, drift karesi ortadan kalkmalı. G0'da IoU 0.912 **düşmemeli**
— düşerse taban davranış bozulmuş demektir ve değişiklik geri alınmalıdır.

## Üretilen / değişen dosyalar

```
gazebo/senaryolar.py   G1-G7 x 2 şiddet + 7 ek senaryo, profil altyapısı
gazebo/dunya_uret.py   dinamik drone (sensör pozunda nadir dönüşü), doku önbelleği
gazebo/kaydet.py       Surucu (sim zamanında cmd_vel), kamera pozu bileşkesi,
                       kamera hareketi akıl denetimi, --hepsi
gazebo/tani.py         YENİ - teşhis koşucusu, bağımsız ego referansı, K1-K8
```

`takip/` · `sim/` · `veri/gazebo.py` · `main.py` · `kaynak.py` · `calistir.py` ·
`kiyasla.py` · `visdrone_kiyasla.py` **değişmedi**.

## Kayıt sırasında bulunan tuzaklar

1. **Nadir dönüşü model pozunda bırakmak.** VelocityControl komutları gövde
   çerçevesindedir; gövde +X'i dünya −Z olduğu için "ileri git" kamerayı aşağı
   sürer, "yaw" komutu görüntüde pitch üretir. Dönüş sensör pozuna taşındı.
2. **Sinüs hız profili.** Konum integrali (1−cos) olduğu için tek yönlü ve
   genliğin iki katı sapma verir (§ Şiddet seviyeleri).
3. **Hedefin kazara durması.** ±5 m/s modülasyon aracı 0 m/s'ye indiriyordu
   (§ Bulgular 7).
4. **`d_görüntü/r_etkin` ham oranına bakmak.** Ego ve KF soğurmasını
   yok sayar; 1.32'lik oran gerçekte 1.09 px artık demekti (§ Bulgular 1).
5. **`pkill -f "gz sim"`.** Kendi kabuğunun komut satırıyla eşleşip oturumu
   öldürüyor. Kaçak süreç temizliği için kullanılmamalı.
