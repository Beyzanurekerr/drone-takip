# Drone Hedef Takip — Demo

Havadan çekilen görüntüde **seçilen tek bir aracı**, kamera irtifası arttıkça
görüntüdeki boyutu küçülse bile kesintisiz takip etmek.

## 1. Amaç

Adaptif ROI merdiveni (Adım 3a — `demo_ayar.py:r_sec`) ile **80–160 m irtifa
aralığında** (hedefin kadraj-içi native boyutu **79.6 → 39.4 px**'e küçülüyor)
YOLO tabanlı yeniden-edinme başarı oranı ölçülen **12/12 hücrede recall
1.000**'dır — bkz. `docs/TESHIS_2E_PX_BANDI.md` EK'i. Bu depo bu ölçümün
üzerine kurulu **ürün/demo dalıdır**; araştırma dalındaki hiçbir kabul kapısı
(K1–K6, 8×5 senaryo matrisi vb.) buraya taşınmadı — bkz. §8 "Bilinen
sınırlar".

## 2. Donanım

### Hedef donanım (fiziksel doğrulama **yapılmadı**)

| Bileşen | Model |
|---|---|
| Tek kart bilgisayar | Raspberry Pi Zero 2 W |
| Kamera | Raspberry Pi AI Camera (Sony IMX500, sensör-üstü çıkarım) |

> `pi/olc_pi.py` ve `docs/PI_KURULUM.md` / `docs/PI_OLCUM.md` bu donanım için
> yazıldı ama **hiçbiri gerçek donanımla denenmedi** (donanım elde yok).
> Pi Zero 2 W için verilen tüm FPS sayıları (bkz. §7) **ekstrapolasyondur**.

Simülasyondaki (Gazebo) kamera modeli IMX500'ün yayınlanmış özellikleriyle
birebir eşleşecek şekilde kalibre edildi (tek sayı kaynağı
`gazebo/kamera_imx500.sdf`):

| Parametre | Değer |
|---|---|
| Sensör çözünürlüğü (4:3 binned) | 2028 × 1520 px |
| Görüş açısı (yatay × dikey) | 66° × 52° (`horizontal_fov` 1.1519 rad) |
| Odak (türetilmiş) | 1561 px |
| Kare hızı | 30 fps |
| Distorsiyon (fıçı, k1) | −0.02 (makul başlangıç değeri — gerçek donanımda kalibre edilmeli) |

### Geliştirme / simülasyon ortamı

- Ubuntu 22.04/24.04 (WSL2 dahil) + Gazebo Sim **Harmonic**
- Python 3.10+, `opencv-python`, `numpy`
- Hedef tespiti: YOLOv8n, UAVDT→VisDrone fine-tune (`weights/a6_kucuk_hedef.pt`,
  "A6") — CPU çıkarım gecikmesi ölçüldü: **34.8 ms/kare** (masaüstü CPU,
  imgsz=640) — bkz. `docs/PI_OLCUM.md` dipnot ².
- Derin öğrenme çalışma zamanı: `ultralytics` + `torch` (CPU tekerleği yeterli,
  GPU **gerekmez**)

Kurulum adımları için → **[docs/KURULUM.md](docs/KURULUM.md)**.

## 3. Px – İrtifa

Aşağıdaki tablo `data/gazebo/Teshis2e_120m` / `Teshis2e_160m` ve
`data/gazebo/Demo_celdirici` (80 m) kayıtlarından **ölçülmüştür** (100 kare/
irtifa, `gazebo/teshis_2e_px_bandi.py`) — tahmin/enterpolasyon değildir:

| İrtifa | Hedef native boyutu (p50) |
|---|---|
| 80 m | 79.6 px |
| 120 m | 52.7 px |
| 160 m | 39.4 px |

Tam kadrajda (640 px girdi) bu üç irtifada da YOLO recall **0.000**'dır —
demo bu yüzden ham kareyi değil, **adaptif ROI'yi** (aşağıdaki merdiven)
dedektöre verir:

| İrtifa | Seçilen ROI (R, sensör-px) | Ağ girdisinde px (p50) | Recall |
|---|---|---|---|
| 80 m | 640 (tam kadraj) | 79.6 px | **1.000** |
| 120 m | 320 | 105.5 px | **1.000** |
| 160 m | 320 | 78.8 px | **1.000** |

`R_MERDIVEN = (640, 320, 160, 80)` basamaklarından yalnızca **640 ve 320**
bu üç irtifada tetiklendi; **160 ve 80 basamakları bu ölçümde hiç
tetiklenmedi** ve kalibre edilmiş sayılmaz (bkz. §8). Ağ girdisinde hedeflenen
bant `[55, 110] px` (orta nokta 82.5 px, log-simetrik seçim) —
`docs/TESHIS_2E_PX_BANDI.md` EK'i.

## 4. Mimari

```
                    Kare  (Gazebo/IMX500 sim → gelecekte gerçek Pi AI Camera)
                      │
                      ▼
              [1] EGO-MOTION            LK + RANSAC benzerlik dönüşümü
                      │
                      ▼
              [2] TAKİP                 renk kanallı DCF + Kalman (sabit hız)
                      │
                      ▼
              [3] KUTU RAFİNESİ         DEDEKTÖR BOYUT OTORİTESİ (demo):
                      │                 boyut yalnız doğrulanmış A6 tespitinde
                      │                 yazılır, klasik rafine araya karışmaz
                      ▼
              [4] KAYIP → KARO ARAMA    adaptif ROI merdiveni (r_sec:
                      │                 640/320/160/80 sensör-px) + A6
                      │                 (YOLOv8n fine-tune), kare başına
                      │                 ≤2 karo — maliyet kare başına SABİT
                      ▼
              [5] DURUM MAKİNESİ
                  KİLİTLİ → ŞÜPHELİ (öğrenme durur) → ARAMA → KAYIP
                                                          │
                                                          ▼
                                                       KORUMA (boyut <25 px:
                                                       dedektör güvenilmez,
                                                       komut="YAKLAŞ")
```

Katman ayrıntısı: `takip/izleyici.py` (durum makinesi + false-lock
doğrulama), `demo_ayar.py` (adaptif ROI + karo tarayıcı), `main.py:kos()`
(kaynaktan bağımsız koşum döngüsü).

## 5. Demo senaryoları

Kaynak: `gazebo/senaryolar.py:DEMO_AILE`. Üçü de sabit `--mod demo`
(`main.py --mod demo --source gazebo --sequence <ad>`) ile koşulur; kayıttan
HUD'lu video üretimi → `gazebo/demo_hud_uret.py`.

| Senaryo | Açıklama | Kabul beklentisi | Sonuç | mp4 |
|---|---|---|---|---|
| `Demo_kucul` | İrtifa rampası 50→200 m, hedef 2 viraj alır | Kilit kesintisiz, KORUMA'ya (20 px) geçiş görünür, hassasiyet ≥%95 | *(doldurulacak)* | *(doldurulacak)* |
| `Demo_celdirici` | Sabit 80 m, 2 çeldirici hedefin ≤10 m yanından ters yönde geçer | Yanlış hedefe geçiş **sıfır** | *(doldurulacak)* | *(doldurulacak)* |
| `Demo_kopus` | Sabit 80 m, hedef ~1 s ağaç/yapı altında kalır | ≤2 s içinde doğru hedefe dönüş, yanlış kilit 0 | *(doldurulacak)* | *(doldurulacak)* |

## 6. Kurulum

Sıfırdan, temiz bir Ubuntu 22.04/24.04 (ya da WSL2) üzerinde
`python3 main.py --mod demo --source gazebo --sequence Demo_kucul` açılana
kadar adım adım → **[docs/KURULUM.md](docs/KURULUM.md)**.

## 7. Bilinen sınırlar

1. **R=160 ve R=80 basamakları kalibre edilmedi.** §3'teki 3 ölçüm noktası
   (80/120/160 m) yalnızca R=640/320'i tetikledi; daha küçük basamaklar kod
   yolunda var ama hiç sınanmadı.
2. **Tam kadraj kaçışı yok.** Merdivenin en yakın basamağı bandın dışında
   kalsa bile tam kadraja düşülmez (bilinçli tasarım — `demo_ayar.py`
   docstring'i) — bu durum bu üç irtifada hiç tetiklenmedi.
3. **KAYIP/edinme eşikleri gevşek** (`esik=0.0`) — Adım 5'te sıkılaştırılması
   planlanıyor, henüz kabul ölçütü yok.
4. **`DEDEKTOR_BOYUT_OTORITESI`** (2026-09-07 eklendi) henüz kendi kabul
   testinden geçmedi — yalnızca kare ~698 sıçramasını (commit `2ab78a7`)
   kapattığı doğrulandı.
5. **`Demo_kopus`'un örtülme konumu görsel doğrulanmadı** — rota/süre kuruldu,
   ağaç/binanın hedefi gerçekten kapattığı henüz teyit edilmedi.
6. **Raspberry Pi'de hiçbir ölçüm yapılmadı** — §2'deki tüm Pi sayıları
   ekstrapolasyondur (bkz. `docs/PI_OLCUM.md`). IMX500 model paketleme bu
   makinede OOM nedeniyle tamamlanamadı (bkz. `weights/imx500/DURUM.md`).
7. **Araştırma dalının kabul kapıları buraya taşınmadı** — bu depo
   araştırmanın *sonucu* değil, ondan öğrenilenlerle kurulmuş ayrı bir demo
   dalıdır (bkz. §9).
8. HUD'da (`gazebo/demo_hud_uret.py`) gösterilen "mesafe" ve "≈m boyut"
   değerleri düz-zemin + nadir-kamera varsayımıyla pinhole geometriden
   **türetilir** — GPS/lazer gibi bağımsız bir ölçümle doğrulanmadı.

## 8. Araştırma özeti

Bu demo dalının dayandığı ~15 araştırma aşamasının (A3.9 → K-MOD) tek
sayfalık özeti ve tam rapor arşivine erişim → **[docs/ARASTIRMA_OZETI.md](docs/ARASTIRMA_OZETI.md)**.

## 9. Ekip

| | |
|---|---|
| Geliştirici | Beyzanur Eker ([@Beyzanurekerr](https://github.com/Beyzanurekerr)) |

Tek kişilik bir depo/proje; katkı veya soru için GitHub issue açılabilir.

---

Commit mesaj biçimi: `feat:` · `fix:` · `docs:` · `test:` · `refactor:`
