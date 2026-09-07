# 2e-teşhis: A6'nin baylands 80 m'de 0 tespitinin sebebi px bandı mı?

**Tarih:** 2026-09-07 · **Betik:** `gazebo/teshis_2e_px_bandi.py` (hiçbir
mevcut dosya değiştirilmedi, fine-tune yok, mesh değiştirme yok) ·
**Kayıtlar:** `data/gazebo/Demo_celdirici` (mevcut, 2026-09-04'ten), yeni
`data/gazebo/Teshis2e_120m`, `data/gazebo/Teshis2e_160m` (resmi
`SENARYOLAR` kaydına eklenmedi, `kareler/` diğerleri gibi gitignore'da).

## Hipotez (ön-kayıtlı)

A5 (UAVDT ön-eğitim, `runs/a6/asamaA`) ≥40 px'te görür, A6 (nihai fine-tune,
`runs/a6/asamaB`) 20–40 px bandında görür → demo modu hedefin px bandına
göre model seçer (eğitim gerekmez). **Tutmazsa DUR, tabloyu göster.**

## Sonuç: HÜKÜM = **DUR**. Hipotez tutmadı — ama sebep farklı ve daha net.

| İrtifa | Native L p50 | Model | Yol | girdi L p50 | n | recall |
|---|---|---|---|---|---|---|
| 80 m | 79.6 px | COCO | tam | 25.1 px | 100 | 0.000 |
| 80 m | 79.6 px | COCO | roi-4x | 318.5 px | 100 | 0.000 |
| 80 m | 79.6 px | A5 (UAVDT) | tam | 25.1 px | 100 | 0.000 |
| 80 m | 79.6 px | A5 (UAVDT) | roi-4x | 318.5 px | 100 | 0.000 |
| 80 m | 79.6 px | A6 (final) | tam | 25.1 px | 100 | 0.000 |
| 80 m | 79.6 px | A6 (final) | roi-4x | 318.5 px | 100 | 0.000 |
| 120 m | 52.7 px | COCO | tam | 16.6 px | 100 | 0.000 |
| 120 m | 52.7 px | COCO | roi-4x | 210.9 px | 100 | 0.000 |
| 120 m | 52.7 px | A5 (UAVDT) | tam | 16.6 px | 100 | 0.000 |
| 120 m | 52.7 px | A5 (UAVDT) | roi-4x | 210.9 px | 100 | **0.010** |
| 120 m | 52.7 px | A6 (final) | tam | 16.6 px | 100 | 0.000 |
| 120 m | 52.7 px | A6 (final) | roi-4x | 210.9 px | 100 | 0.000 |
| 160 m | 39.4 px | COCO | tam | 12.4 px | 100 | 0.000 |
| 160 m | 39.4 px | COCO | roi-4x | 157.7 px | 100 | **0.010** |
| 160 m | 39.4 px | A5 (UAVDT) | tam | 12.4 px | 100 | 0.000 |
| 160 m | 39.4 px | A5 (UAVDT) | roi-4x | 157.7 px | 100 | **1.000** |
| 160 m | 39.4 px | A6 (final) | tam | 12.4 px | 100 | 0.000 |
| 160 m | 39.4 px | A6 (final) | roi-4x | 157.7 px | 100 | **0.940** |

## Neden hipotez tutmadı

Beklenti "A5 geniş bantta görür, A6 dar bantta görür — model seçimi
yeterli" idi. Ölçülen: **A5 ve A6 neredeyse ÖZDEŞ davranıyor** — ikisi de
YALNIZCA 160 m'de (native 39.4 px, ROI-zoomlu girdide 157.7 px) çalışıyor,
ikisi de 80 m ve 120 m'de (native 52.7–79.6 px, girdide 211–319 px)
çöküyor. Model değişimi bunu çözmüyor; **asıl değişken model değil,
ROI-4x'in ZOOM ÇIKTISI px'i** — daha önce Y1.1/Y1.2'de doğrulanmış dar
pencere (~150–165 px'lik girdi, yani ~35–40 px native) dışına çıkınca
(daha BÜYÜK görünse bile) recall sıfırlanıyor. Önceki ROI-4x kalibrasyonu
hiç bu kadar büyük (210–319 px) bir girdi görmemişti — bu 2e-teşhis o
ölçülmemiş üst bandı ilk kez ölçtü ve orada bozulduğunu gösterdi.

Tam kadraj (640) yolunda üç irtifada da recall 0 — bu SÜRPRİZ DEĞİL:
girdi boyutu (12–25 px) daha önce belgelenen 57 px güvenilir tabanın
(A5.2/A6 benchmark) çok altında, mevcut bulguyla tutarlı.

## Işık/tuval elendi, mesh/render elenmedi

Kare parlaklığı üç irtifada pratik olarak SABİT (80 m: ort 96.1, 120 m:
91.5, 160 m: 91.2 — std'ler 0.1–1.5 arası) → **aydınlatma açıklayıcı
değişken DEĞİL**. Görsel karşılaştırma (`teshis_2e_karsilastirma.png`,
commit'e eklenmedi — 640×360 4 panel: DEMO 80/120/160 m + Y1.2 gerçek
VisDrone L≈54 px) üç DEMO karesinde de hedef net, net sınırlı, tıkanmasız
görünüyor — DCF/GT/render kalitesinde görünür bir kusur yok. Yani ne
aydınlatma ne tuval/render kusuru; **sorumlu değişken ROI-zoom sonrası px
büyüklüğü** — ama "küçüklük" değil, bu kez **büyüklük** (80 m'de 318 px,
neredeyse yarı-kare) daha önce hiç sınanmamış bir üst uç.

## Talimatın kendi kuralı gereği: Adım 3'e geçilmedi, hiçbir kod
değiştirilmedi, hiçbir model fine-tune edilmedi, mesh değiştirilmedi.

## Sıradaki adaylar (SINANMADI)

- ROI-4x'i SABİT 4x yerine hedefin native boyutuna göre ADAPTİF ölçekleyip
  girdiyi hep ~150–160 px bandına oturtmak (A7/A8'in "adaptif ROI" fikrinin
  bir varyantı — [[drone-takip-a9]]'da zaten kısmen kurulu).
  ya da
- Demo irtifa aralığını (80→160 m yerine) bu doğrulanmış native ~35–45 m
  bandına daraltmak/ölçeklemek.
