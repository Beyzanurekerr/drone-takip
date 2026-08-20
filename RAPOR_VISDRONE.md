# VisDrone Gercek Hava Goruntusu - Sonuc Raporu

Bu rapor SIMULASYON baseline'indan bagimsizdir; `RAPOR.md` ile
karistirilmamalidir. Olculen sistem ayni klasik takip hattidir
(ego-motion + renk_dcf + Kalman + durum makinesi); tek fark girdi.

> **Bu tablo Asama 3.8 ONCESINDE uretildi (19 Agustos 2026).** IoU ve merkez
> hatasi degerleri gecerli; ancak `kilit` sutunu A3.8'in bagimsiz yanlis-kilit
> dogrulamasindan ONCEKI davranisi gosteriyor. A3.8 sonrasi yanlis kilit orani
> uav0000268_05773_v'de %98.4 -> %44.0, uav0000182_00000_v'de %47.8 -> %11.3
> indi; kilit oranlari da buna bagli olarak dustu. Guncel karsilastirma icin
> `docs/architecture/CHANGELOG.md`, Asama 3.8. Bu dosyayi yeniden uretmek icin:
> `python3 visdrone_kiyasla.py --hepsi --rapor`

- Veri kumesi: VisDrone2019-VID-val
- Kareler 960 px genislige indirildi, GT kutulari ayni oranda olceklendi
- Hedef, track'in ilk karesindeki GT kutusuyla kilitlenir; sonraki
  karelerde GT yalnizca OLCUM icin kullanilir, takipciye beslenmez
- Hedef track otomatik secilir: en uzun sure gorunen ve HAREKET EDEN arac
- ID switch olculmez (sistemde henuz MOT yok)

## Sonuclar

| dizi | track | kare | IoU | @0.5 | @0.3 | hassasiyet | merkez hata | kilit | p50 ms | p95 ms | FPS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| uav0000117_02622_v | 23 | 343 | 0.701 | 97% | 100% | 100% | 5.51 px | 100% | 2.59 | 5.90 | 311 |
| uav0000137_00458_v | 12 | 221 | 0.215 | 26% | 30% | 34% | 82.90 px | 83% | 3.09 | 16.35 | 183 |
| uav0000182_00000_v | 127 | 335 | 0.095 | 0% | 10% | 34% | 266.30 px | 34% | 7.90 | 18.62 | 114 |
| uav0000268_05773_v | 31 | 252 | 0.000 | 0% | 0% | 0% | 408.84 px | 96% | 4.11 | 28.62 | 101 |
| uav0000305_00000_v | 5 | 141 | 0.502 | 65% | 74% | 77% | 9.12 px | 83% | 3.91 | 15.75 | 147 |
| uav0000339_00001_v | 49 | 266 | 0.172 | 0% | 0% | 32% | 28.72 px | 100% | 2.51 | 5.69 | 321 |

**Ortalama:** IoU 0.281 | @0.5 31% | hassasiyet 46% | kilit 83% | 196 FPS

## Hedef boyutlari ve kurtarma

| dizi | ham cozunurluk | islenen | hedef boyut (px) | kesinti | ort kurtarma |
|---|---|---|---|---|---|
| uav0000117_02622_v | 2720x1530 | 960x540 | 57.0 x 52.3 | 0 | 0 kare |
| uav0000137_00458_v | 2688x1512 | 960x540 | 73.5 x 67.0 | 0 | 0 kare |
| uav0000182_00000_v | 1344x756 | 960x540 | 23.7 x 21.4 | 2 | 2 kare |
| uav0000268_05773_v | 3840x2160 | 960x540 | 15.0 x 7.1 | 0 | 0 kare |
| uav0000305_00000_v | 1904x1071 | 960x540 | 31.5 x 49.6 | 0 | 0 kare |
| uav0000339_00001_v | 1904x1071 | 960x540 | 50.0 x 24.5 | 8 | 12 kare |

hassasiyet = merkez hatasinin hedef kosegeninin yarisindan kucuk
oldugu kare orani.

