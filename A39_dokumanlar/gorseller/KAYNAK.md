# A3.9 gorsel kanit paketi - kaynak dokumu

Bu klasordeki 11 gorsel **mevcut kayitlardan** uretildi.
Takipci yeniden kosturulmadi, yeni olcum yapilmadi, `takip/` ve
diger kaynak dosyalar degistirilmedi. Uretici: `_gorsel_uret.py` (salt okunur).

Cizim sozlesmesi:
- **YESIL kutu = GT** (kayitli dogru kutu)
- **MAGENTA kutu = TAKIPCI** (kayitli takipci ciktisi)
- Sag ust kose = kayitli **durum** (KILITLI / SUPHELI / ARAMA / KAYIP)
- Ust bantta kare numarasi + kayitli IoU / merkez hata / PSR

## 1. Gazebo - G6_agresif_durakli (t_drift = 148)

Goruntu: `data/gazebo/G6_agresif_durakli/kareler/%06d.png` (640x480, 2x buyutuldu)
Kutu + durum + olcum: `cikti/g6_cift.json` -> `G6_agresif_durakli.satir[kare]`
alanlari `gt_x, gt_y, gt_w, gt_h` (GT) ve `final_x, final_y, w, h` (takipci),
`durum`, `iou`, `final_hata`, `psr`.

| dosya | kare | durum | IoU | merkez hata |
|---|---|---|---|---|
| 01_gazebo_G6_kare106_normal.jpg | 106 | KILITLI | 0.911 | 1.5 px |
| 02_gazebo_G6_kare141.jpg | 141 | KILITLI | 0.613 | 8.8 px |
| 03_gazebo_G6_kare142.jpg | 142 | KILITLI | 0.581 | 9.8 px |
| 04_gazebo_G6_kare147.jpg | 147 | SUPHELI | 0.387 | 18.4 px |
| 05_gazebo_G6_kare148.jpg | 148 | SUPHELI | 0.251 | 30.0 px |
| 06_gazebo_G6_kare151.jpg | 151 | KILITLI | 0.000 | 58.3 px |
| 07_gazebo_G6_kare170_drift_sonrasi.jpg | 170 | KILITLI | 0.000 | 90.0 px |

Not: 141-151 araliginda sahnedeki SARI arac celdiricidir; bu araliktaki
yakinlasma zaten 4P/4Q kayitlarinda belgelenmis sahne artefaktidir.

## 2. VisDrone

Goruntu: `data/datasets/visdrone_vid/sequences/<dizi>/%07d.jpg`
(960 px genislige indirildi - kosumdaki `hedef_genislik=960` ile ayni olcek;
kayitlardaki `kare` 0-tabanli, dosya adi `kare+1`).
GT kutusu: `cikti/a39a_h123.json` -> `<anahtar>.satir[kare]`
(`gt_x, gt_y, gt_w, gt_h`, `iou`, `psr`).
Takipci kutusu: `cikti/dcf_4o.json` -> `<anahtar>.satir[kare]`
(`final_x, final_y, w, h`, `durum`).

| dosya | dizi | kare | durum | IoU | merkez hata |
|---|---|---|---|---|---|
| 08_visdrone_117-23_kare31_normal.jpg | uav0000117_02622_v / track 23 | 31 | KILITLI | 0.902 | 1.2 px |
| 09_visdrone_117-23_kare348_problemli.jpg | uav0000117_02622_v / track 23 | 348 | KILITLI | 0.429 | 8.0 px |
| 10_visdrone_137-12_kare10_normal.jpg | uav0000137_00458_v / track 12 | 10 | KILITLI | 0.986 | 0.3 px |
| 11_visdrone_137-12_kare108_problemli.jpg | uav0000137_00458_v / track 12 | 108 | ARAMA | 0.032 | 70.5 px |

## Iki kaydin ayni kosuma ait oldugunun dogrulanmasi

VisDrone gorsellerinde GT bir dosyadan, takipci kutusu baska bir dosyadan
okundugu icin tutarlilik ayrica sinandi:

- Iki kutudan yeniden hesaplanan IoU, `a39a_h123.json` icinde kayitli `iou`
  degeriyle **max 1e-6** farkla ortusuyor (342 + 220 kare).
- Iki kayitta `gt_x/gt_y` ve kutu boyutlari (`w/h` vs `boyut_w/boyut_h`)
  bit duzeyinde ayni.
- `a39a_h123.json` GT'si, ham VisDrone annotation dosyasindan
  (`annotations/<dizi>.txt`, `merkez * 960/ham_genislik`) birebir uretiliyor.

Gazebo tarafinda `g6_cift.json` GT'si `pozlar.csv` + `meta.json` ic
parametreleriyle bagimsiz yeniden izdusurulup birebir dogrulandi
(kare 7, 106, 141, 151); kayitli `iou` da kutulardan max 1.2e-6 farkla
yeniden hesaplandi.
