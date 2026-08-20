# Drone Hedef Takip - Sonuc Raporu

Sentetik havadan goruntu simulasyonu uzerinde, her kare icin kusursuz
ground-truth ile olculmustur. Hedef ilk karede ELLE degil, sistemin kendi
hareket tespiti listesinden secilir (gercek kullanim boyle).

## Mimari

```
kare
 |- ego-motion  : seyrek LK + RANSAC benzerlik donusumu
 |                (arama daraltma + hareketli cisim ayirma + olcek)
 |- takip       : MOSSE korelasyon filtresi + Kalman (sabit hiz)
 |                olcek ego-motion'dan bedava gelir
 |- capa        : yerel renk kontrastiyla kutu rafinesi (surukleme onleme)
 |- yeniden     : ego-telafili kare farki -> aday lekeler
 |  tespit        -> renk + sablon + boyut imzasiyla eslestirme
```

## Test sonuclari

| test | amac | IoU | @0.5 | hassasiyet | merkez hata | kilit | ID switch |
|---|---|---|---|---|---|---|---|
| test1_yakin | Temel takip calisiyor mu? | 0.925 | 100% | 100% | 0.25 px | 100% | 0 |
| test2_uzaklasan | Piksel boyutu kuculurken hedef korunuyor mu? | 0.435 | 45% | 83% | 1.59 px | 98% | 0 |
| test3_cok_kucuk | Minimum takip edilebilen hedef boyutu kac px? | 0.560 | 61% | 85% | 1.75 px | 95% | 0 |
| test4_coklu | Kilitli arac yerine baskasina geciyor mu? (ID switch) | 0.866 | 100% | 100% | 0.57 px | 100% | 0 |
| test5_benzer | Gorunum ayirt edemez -> hareket modeli hedefi tutabiliyor mu? | 0.897 | 100% | 100% | 0.15 px | 100% | 0 |
| test6_okluzyon | Tekrar gorununce AYNI arac bulunabiliyor mu? | 0.747 | 81% | 92% | 0.99 px | 78% | 1 |
| test7_kamera | Kamera hareketine ragmen hedef tutuluyor mu? | 0.764 | 91% | 100% | 0.97 px | 100% | 0 |

**hassasiyet** = merkez hatasi hedef kosegeninin yarisindan kucuk olan kare orani.
Kucuk hedefte IoU 1 piksellik hatada cokerken bu olcu adil kalir.

## Test 3 - minimum takip edilebilen hedef boyutu

| hedef boyutu (px) | kare | IoU | hassasiyet | merkez hata | hukum |
|---|---|---|---|---|---|
| 52.2 x 21.6 | 201 | 0.943 | 100% | 0.44 px | BASARILI |
| 39.8 x 16.4 | 174 | 0.918 | 100% | 0.50 px | BASARILI |
| 31.4 x 13.0 | 153 | 0.910 | 100% | 0.44 px | BASARILI |
| 24.9 x 10.3 | 168 | 0.782 | 100% | 0.59 px | BASARILI |
| 19.9 x 8.2 | 138 | 0.673 | 100% | 0.81 px | BASARILI |
| 16.5 x 6.8 | 126 | 0.718 | 100% | 0.70 px | BASARILI |
| 13.5 x 5.6 | 156 | 0.555 | 94% | 1.14 px | KARARSIZ |
| 11.0 x 4.5 | 126 | 0.394 | 100% | 0.43 px | BASARILI |
| 9.0 x 3.7 | 153 | 0.348 | 99% | 0.37 px | BASARILI |
| 7.0 x 2.9 | 201 | 0.244 | 79% | 0.32 px | KARARSIZ |
| 5.4 x 2.2 | 141 | 0.172 | 67% | 0.37 px | KAYIP |

## Zaman profili (640x480)

| asama | ms | pay |
|---|---|---|
| ego-motion | 1.07 | 36% |
| korelasyon cekirdegi | 1.15 | 39% |
| tespit / kutu rafine | 0.38 | 13% |
| TOPLAM | 2.96 | 100% |

- bu makine: **338 FPS**
- Pi Zero 2 W kaba tahmin: **28.2 FPS** (x12)
- Pi Zero 1 kaba tahmin: **7.5 FPS** (x45)

Katsayilar tahmindir; kesin sonuc icin cihazda olculmelidir.

