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

## Sıradaki adaylar (SINANMADI) — bkz. EK aşağıda, ilk aday sınandı ve GEÇTİ

- ROI-4x'i SABİT 4x yerine hedefin native boyutuna göre ADAPTİF ölçekleyip
  girdiyi hep ~150–160 px bandına oturtmak (A7/A8'in "adaptif ROI" fikrinin
  bir varyantı — [[drone-takip-a9]]'da zaten kısmen kurulu).
  ya da
- Demo irtifa aralığını (80→160 m yerine) bu doğrulanmış native ~35–45 m
  bandına daraltmak/ölçeklemek.

---

## EK: A8 merdiveniyle (adaptif ROI) yeniden ölçüm — 2026-09-07

**Betik:** `gazebo/teshis_2e_merdiven.py` (hiçbir mevcut dosya değişmedi,
yeni kayıt gerekmedi — mevcut 3 veri seti tekrar kullanıldı). Yukarıdaki
ölçüm SABİT ROI-4x (R=160 her irtifada) kullanmıştı ve 80/120 m'de girdi
211–319 px'e şişip çökmüştü. Bu tur, A8'in orijinal tasarımının (silinmiş
`gazebo/tani_a8_adaptif_roi.py`, git geçmişi `03c15f5~1`) `R_sec`
mantığını AYNEN taşıyor: merdivenden ({640,320,160,80} sensör-px ROI
genişliği) hedefi ağ girdisinde bant ortasına (log uzayında) en yakın
getiren basamak seçilir. **Bant burada [55,110] px** (eski A8'in [60,90]'ı
DEĞİL — bu tur için verilen yeni bant), `NET_HEDEF=82.5`.

| İrtifa | Model | Yol | Seçilen R | girdi L p50 | recall |
|---|---|---|---|---|---|
| 80 m | A5 | tam kadraj | — | 25.1 px | 0.000 |
| 80 m | A5 | merdiven-ROI | **640** | 79.6 px | **1.000** |
| 80 m | A6 | tam kadraj | — | 25.1 px | 0.000 |
| 80 m | A6 | merdiven-ROI | **640** | 79.6 px | **1.000** |
| 120 m | A5 | tam kadraj | — | 16.6 px | 0.000 |
| 120 m | A5 | merdiven-ROI | **320** | 105.5 px | **1.000** |
| 120 m | A6 | tam kadraj | — | 16.6 px | 0.000 |
| 120 m | A6 | merdiven-ROI | **320** | 105.5 px | **1.000** |
| 160 m | A5 | tam kadraj | — | 12.4 px | 0.000 |
| 160 m | A5 | merdiven-ROI | **320** | 78.8 px | **1.000** |
| 160 m | A6 | tam kadraj | — | 12.4 px | 0.000 |
| 160 m | A6 | merdiven-ROI | **320** | 78.8 px | **1.000** |

### Kapı: **GEÇTİ** (her irtifada merdiven-ROI recall ≥ 0.65)

Her üç irtifada da recall tam **1.000** — kapının 0.65 eşiğini büyük
farkla geçiyor. **A5 ve A6 BİREBİR AYNI** (12/12 hücrede özdeş recall) —
kullanıcının önceki turdaki "A5=A6 aynı davranıyor" gözlemi burada da
doğrulandı. **Sonuç: A6 tek model olarak yeterli, A5'i demoya eklemeye
gerek yok.**

### `R_MERDIVEN` kalibrasyonu (Adım 3a için)

```
MERDIVEN = [640, 320, 160, 80]   # sensor-px ROI genisligi (A8 ile AYNI)
BANT = (55.0, 110.0)
NET_HEDEF = 82.5                 # bant ortasi (log-simetrik secim icin)
R_sec(L_native) = min(MERDIVEN, key=R -> |log((L_native*640/R)/NET_HEDEF)|)
```

**Dürüstlük notu:** bu 3 irtifada (80/120/160 m, native 39–80 px) merdiven
YALNIZCA R=640 ve R=320 basamaklarını seçti; **R=160 ve R=80 basamakları
bu turda HİÇ tetiklenmedi** (daha küçük/yakın hedefler gerekirdi — ör.
~200 m'nin üstü). O basamaklar kalibre edilmiş SAYILMAZ, yalnızca A8'in
orijinal tasarımından miras alındı. "1×/tam kadraj kaçışı" (merdivenin en
yakın basamağı da banda girmiyorsa tam kadraja düş) da bu 3 irtifada HİÇ
tetiklenmedi (`tam_kacis=0` her hücrede) — kod yolu var ama sınanmadı.

**Adım 3'e geçiş:** kapı geçti, önerilen üretim modeli A6 tek başına.
Adaptif ROI'nin gerçek demo boru hattına (Demo_kucul/Demo_celdirici/
Demo_kopus) entegrasyonu (Adım 3) henüz YAPILMADI — bu ek yalnızca ölçüm
ve kalibrasyondur.
