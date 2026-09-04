# Pi ölçüm şablonu

**Durum: Pi/IMX500 donanımı elde yok.** Bu belge, donanım gelip
`pi/olc_pi.py` (bkz. `docs/PI_KURULUM.md`) çalıştırıldıktan sonra elle
doldurulacak bir **şablondur**. Aşağıdaki tek istisna dışında her ölçüm
hücresi `TODO — Pi bekleniyor`.

> **Sayı disiplini** (bkz. `docs/architecture/KALICI_KISITLAR.md`): hiçbir
> hücreye tahmini/yuvarlanmış bir sayı **ölçülmüş gibi** yazılmaz. Pi'de
> ölçüm yapıldığında bu tablo `pi/sonuc.json` çıktısından elle doldurulur ve
> her satıra hangi koşumdan geldiği (tarih + `sonuc.json`'daki
> `git_commit`) eklenir.

## Kare bütçesi tablosu

Bütçe satırı: Pi Zero 2 W'nin klasik-hat ekstrapolasyonundan türetilen
**~36 ms/kare (~28 FPS)** — bkz. `docs/architecture/A5_INFERENCE_MIMARISI_KARSILASTIRMA.md`
§0 ve `docs/architecture/A10_ONKAYIT.md`. Bu bütçe **ölçülmedi**, aritmetik
türetimdir (`RAPOR.md`'deki masaüstü FPS × Pi Zero 2 W için ×12 kaba
katsayı); Pi elde olmadığı için hâlâ doğrulanmadı.

| bileşen | ortam | p50 (ms) | p95 (ms) | bütçe (ms) | sığıyor mu |
|---|---|---|---|---|---|
| ego-motion | **masaüstü CPU (referans)** | — | — | 36 | bkz. not ¹ |
| korelasyon çekirdeği (DCF) | **masaüstü CPU (referans)** | — | — | 36 | bkz. not ¹ |
| tespit / kutu rafine | **masaüstü CPU (referans)** | — | — | 36 | bkz. not ¹ |
| **toplam klasik hat** | **masaüstü CPU (referans)** | **2.96** ¹ | — | 36 | **EVET** (%8) |
| A6 dedektör (YOLOv8n, CPU) | **masaüstü CPU (referans)** | 34.8 ² | — | 36 | sınırda (%97), tek başına |
| ego-motion | Pi Zero 2 W | TODO — Pi bekleniyor | TODO | 36 | TODO |
| korelasyon çekirdeği (DCF) | Pi Zero 2 W | TODO — Pi bekleniyor | TODO | 36 | TODO |
| tespit / kutu rafine | Pi Zero 2 W | TODO — Pi bekleniyor | TODO | 36 | TODO |
| **toplam klasik hat** | Pi Zero 2 W | TODO — Pi bekleniyor | TODO | 36 | TODO |
| IMX500 tam kare (a6_640) | Pi + AI Camera | TODO — Pi bekleniyor | TODO | 36 | TODO |
| IMX500 sensör-ROI (a6_320) | Pi + AI Camera | TODO — Pi bekleniyor | TODO | 36 | TODO |

¹ `RAPOR.md` "Zaman profili (640×480)": ego-motion 1.07 ms + korelasyon
çekirdeği 1.15 ms + tespit/rafine 0.38 ms = toplam **2.96 ms** (338 FPS),
i7-11800H masaüstü, klasik hat (DCF+Kalman+ego-motion), model çalıştırmaz.
Bu depoda `pi/olc_pi.py --pc` ile bu oturumda **yeniden koşuldu** (bkz.
`pi/sonuc.json`, `mod: PC_KURU_KOSUM`); aynı büyüklük mertebesinde çıktı
(p50 toplam ~3.1 ms) — WSL2 sanallaştırma + farklı kare seti (VisDrone sim
yerine Gazebo G0) nedeniyle birebir aynı değil, ama tutarlı.

² `docs/architecture/A7_ROI_KUCUK_HEDEF_TESHIS.md`: "Tüm kollarda tek
çıkarım maliyeti aynı: ort **34.8 ms → 28.8 FPS** (masaüstü CPU)" — A6
YOLOv8n, imgsz=640, masaüstü CPU. **Pi Zero 2 W'de YOLOv8n CPU çıkarımı hiç
ölçülmedi**; `docs/architecture/A5_INFERENCE_MIMARISI_KARSILASTIRMA.md` §1
Seçenek 1, bu masaüstü değerin FLOP tabanına göre Pi'de "kare başına saniyeler
mertebesi" beklendiğini **büyüklük mertebesi tahmini** olarak işaretler
(ölçüm değil) — tam da bu yüzden IMX500'e (sensör üstü çıkarım, Pi CPU
yükü ~0) gidildi.

## IMX500 paketleme

| | değer | kaynak |
|---|---|---|
| `a6_640` boyut (MB) | **YOK — paketleme bu PC'de tamamlanamadı** (OOM, aşağıya bakın) | `weights/imx500/DURUM.md` |
| `a6_320` boyut (MB) | **YOK — paketleme bu PC'de tamamlanamadı** (OOM, aşağıya bakın) | `weights/imx500/DURUM.md` |
| Kuantizasyon sonrası mAP değişimi | **Denenmedi** — hiçbir kuantize model/dosya üretilemediği için karşılaştırılacak çıktı yok (ONNX int8 yaklaşık yolu da dahil) | `weights/imx500/DURUM.md` |
| IMX500 sensör→metadata gecikmesi | TODO — Pi bekleniyor | `docs/architecture/KALICI_KISITLAR.md` §2b: "kamera gecikmesi ölçülmedi" — bu proje boyunca hiç ölçülmedi, ilk kez burada ölçülecek |

**Paketleme neden yok:** `imx500-converter[pt]` + `model-compression-toolkit`
kurulumu ve ONNX export + PTQ kuantizasyon (200 VisDrone DET kalibrasyon
karesi, hatasız tamamlandı) çalıştı; ama hem 640 hem 320 girdide, sdspconv'un
bellek/katman atama çözücüsü ("Optimal solution found") bitirdikten hemen
sonra, dosya yazılmadan **işletim sistemi OOM-killer'ı süreci öldürdü**
(`dmesg` ile doğrulandı; bu 7.6 GiB RAM'li WSL2 makinesinde 3 ayrı denemede
hep aynı noktada, tekrarlanabilir). Converter hiçbir op/katmanı reddetmedi —
bu bir model uyumsuzluğu değil, PC kaynak yetersizliği. Kurulum (venv +
taşınabilir JDK 21 + kalibrasyon seti) `~/drone_takip/.venv_imx500` ve
`~/drone_takip/.jdk/` altında hazır duruyor; ≥16 GB RAM'li bir makinede
tekrar denenebilir. Ayrıntı: `weights/imx500/DURUM.md`.

## CPU sıcaklık / throttle (5 dk sürekli koşum)

| | değer |
|---|---|
| Başlangıç sıcaklık (°C) | TODO — Pi bekleniyor |
| 5 dk sonunda sıcaklık (°C) | TODO — Pi bekleniyor |
| `vcgencmd get_throttled` (5 dk boyunca hiç 0x0 dışına çıktı mı?) | TODO — Pi bekleniyor |
| Throttle tetiklendi mi? | TODO — Pi bekleniyor |

## Pi Zero 2 W için bilinen ekstrapolasyon uyarısı

`RAPOR.md`: *"Pi Zero 2 W kaba tahmin: 28.2 FPS (×12)"* — bu bir **ÖLÇÜM
DEĞİL**, masaüstü FPS'in mimari farkına göre kaba bir çarpanla
bölünmesidir (×12, `README.md` içinde de aynı çekince ile tekrarlanır:
*"ekstrapolasyondur, cihazda ölçüm yapılmamıştır"*). Bu tabloyu dolduran
kişi Pi'de gerçek p50/p95 ölçünce, bu ekstrapolasyonun ne kadar isabetli
çıktığı (gerçek/tahmin oranı) ayrıca **bir cümleyle** not edilmeli — proje
tarihinde ekstrapolasyonların ne kadar saptığını izlemek, gelecekteki
tahminlerin güvenilirliğini kalibre eder.

## Doldurma prosedürü (Pi'den `sonuc.json` gelince)

1. `pi/sonuc.json`'daki `takip_cekirdek.bilesen_ms` → yukarıdaki "Pi Zero 2 W"
   satırlarının p50/p95 sütunları.
2. `imx500.640.tam_kare.gecikme_ms` ve `.fps_yaklasik` → "IMX500 tam kare"
   satırı; `imx500.320_sensor_roi.sensor_roi.*` → "IMX500 sensör-ROI" satırı.
3. `termal` bloğundaki `kayitlar` dizisinin ilk/son `sicaklik_c`'si ve
   `throttled_hex` değerlerinin `0x0` dışına çıkıp çıkmadığı → termal tablo.
4. Her `{"durum": "HATA", ...}` veya `{"durum": "ATLANDI", ...}` alanı,
   ilgili hücreye **sayı yerine** o durumun kısa açıklamasıyla yazılır —
   boş bırakılmaz, TODO da kalmaz.
5. "sığıyor mu" sütunu yalnızca p95 (p50 değil — kötü durumun bütçeyi aşıp
   aşmadığı sorulur) 36 ms bütçesiyle karşılaştırılarak doldurulur.
