# Drone Hedef Takip — Demo

Havadan çekilen görüntüde **seçilen tek bir aracı**, kamera irtifası arttıkça
görüntüdeki boyutu küçülse bile kesintisiz takip etmek.

## 1. Amaç

Sistem; YOLOv8n, DCF + Kalman ve adaptif ROI yaklaşımını birlikte kullanarak farklı irtifa, hedef boyutu ve hareket koşullarında araç takibini amaçlar. Küçük hedeflerde performansı artırmak için gerçek veri setleriyle eğitim ve Gazebo tabanlı çoklu test senaryoları kullanılmıştır.

Adaptif ROI yaklaşımıyla 80–160 m irtifa aralığında hedefin native boyutu 79.6 → 39.4 px seviyelerine inerken ölçülen 12/12 hücrede recall 1.000 elde edilmiştir.

## 2. Donanım

### Hedef donanım
| Bileşen | Model |
|---|---|
| Tek kart bilgisayar | Raspberry Pi Zero 2 W |
| Kamera | Raspberry Pi AI Camera (Sony IMX500, sensör-üstü çıkarım) |

> `pi/olc_pi.py` ve `docs/PI_KURULUM.md` / `docs/PI_OLCUM.md` bu donanım için
> yazıldı ama **hiçbiri gerçek donanımla denenmedi** (donanım elde yok).
> Pi Zero 2 W için verilen tüm FPS sayıları (bkz. §7) **ekstrapolasyondur**.

Fiziksel donanım doğrulaması henüz yapılmamıştır. Simülasyon tarafında Gazebo kamera modeli, hedeflenen IMX500 donanımı referans alınarak yapılandırılmıştır.

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
Gazebo ortamında farklı irtifa seviyelerinde hedefin görüntüdeki native piksel boyutu ölçülmüştür. Kullanılan senaryolarda 38.3 m–287.5 m aralığında farklı irtifa koşulları bulunmaktadır.

| Senaryo | İrtifa | Hedef boyutu | Amaç |
|---|---:|---:|---|
| A11 taban / A3 / A6 | 38.3 m | ~56×22 px* | Temel takip |
| A4 irtifa salınımı | 38.3–108.3 m | Değişken | İrtifa değişiminde takip |
| Demo_celdirici / Demo_kopus | 80 m | 79.6 px | Çeldirici ve hedef kaybı testi |
| K-MOD küçük hedef | 115 m | ~20 px | Küçük hedef testi |
| Teshis 2e | 120 m | 52.7 px | Piksel ve ROI testi |
| Teshis 2e | 160 m | 39.4 px | Küçülen hedef testi |
| Demo_kucul | 50–210 m | 79.6 → 32.9 px | İrtifa ile küçülen hedef takibi |
| K-MOD çok küçük hedef | 255.6 m | ~9 px | Çok küçük hedef testi |
| A11 A2 / A5 | 38.3–287.5 m | Değişken | Geniş irtifa aralığı testi |


### Ölçülen hedef boyutları

| İrtifa | Hedef native boyutu (p50) |
|---|---|
| 80 m | 79.6 px |
| 120 m | 52.7 px |
| 160 m | 39.4 px |
| 200–210 m | **32.9 px** |

Demo_kucul koşumunda hedef boyutu 200–210 m bandında 32.9 px olarak ölçülmüştür.

Tam kadrajda hedef küçüldükçe YOLO performansı düşerken, adaptif ROI ile hedef dedektöre daha yüksek piksel boyutunda aktarılmaktadır.

## 4. Mimari

```
          Kare (Gazebo / simülasyon)
                      │
                      ▼
              [1] EGO-MOTION
                  LK + RANSAC
                  benzerlik dönüşümü
                      │
                      ▼
              [2] TAKİP
                  Renk kanallı DCF
                  + Kalman (sabit hız)
                      │
                      ▼
              [3] KUTU / BOYUT GÜNCELLEME
                  Doğrulanmış A6 tespitinden
                  hedef kutusu ve boyutu güncellenir
                      │
                      ▼
              [4] KAYIP → ADAPTİF ROI ARAMA
                  ROI merdiveni:
                  640 / 320 / 160 / 80 px
                  + A6 YOLO
                  kare başına ≤2 karo
                      │
                      ▼
              [5] DURUM MAKİNESİ
                  KİLİTLİ → ŞÜPHELİ
                           → ARAMA → KAYIP
                                  │
                                  ▼
                              KORUMA
                           boyut <25 px:
                        dedektör güvenilirliği düşük,
                          komut = "YAKLAŞ"
```

Katman ayrıntısı: `takip/izleyici.py` (durum makinesi + false-lock
doğrulama), `demo_ayar.py` (adaptif ROI + karo tarayıcı), `main.py:kos()`
(kaynaktan bağımsız koşum döngüsü).

## 5. Demo Senaryoları

Demo senaryoları, sistemin farklı irtifa, çeldirici ve hedef kaybı koşullarındaki
davranışını göstermek amacıyla oluşturulmuştur.

Tam sonuç dökümü → **[docs/DEMO_SONUC.md](docs/DEMO_SONUC.md)**

| Senaryo | Açıklama | Kabul beklentisi | Sonuç | Görsel |
|---|---|---|---|---|
| `Demo_kucul` | 50–210 m irtifa rampası, hedef 2 viraj alır | Kilit sürekliliği ≥ %95 | **GEÇTİ** — hassasiyet %100.0 (1194/1194); kilit oranı %96.4 | [MP4](cikti/gorsel/demo/demo_kucul_mod_demo.mp4) · [örnek kare](docs/gorseller/kucul_ornek.png) |
| `Demo_celdirici` | 80 m, iki çeldirici hedef ≤10 m yakınından ters yönde geçer | Yanlış hedefe geçiş = 0 | **KISMEN GEÇTİ** — yanlış hedefe geçiş 0/1791; genel kilit oranı %59.3 | [MP4](cikti/gorsel/demo/demo_celdirici_mod_demo.mp4) · [örnek kare](docs/gorseller/celdirici_ornek.png) |
| `Demo_kopus` | 80 m, hedef yaklaşık 1 s süreyle ağaç altında kalır | ≤2 s içinde doğru yeniden edinme | **GELİŞTİRİLİYOR** — mevcut koşumda doğru hedefe yeniden kilitlenme sağlanamadı | [MP4](cikti/gorsel/demo/demo_kopus_mod_demo.mp4) · [örnek kare](docs/gorseller/kopus_ornek.png) |

### FPS

`N_TESPIT=2` ile ölçülen demo FPS değerleri:

| Senaryo | FPS |
|---|---:|
| `Demo_kucul` | 23.8 |
| `Demo_celdirici` | 29.5 |
| `Demo_kopus` | 82.1 |

## 6. Kurulum

Sıfırdan, temiz bir Ubuntu 22.04/24.04 (ya da WSL2) üzerinde
`python3 main.py --mod demo --source gazebo --sequence Demo_kucul` açılana
kadar adım adım → **[docs/KURULUM.md](docs/KURULUM.md)**.

## 7. Geliştirme Yaklaşımı

Sistem, yalnızca hazır bir video üzerinde çalışacak şekilde değil, farklı hedef
boyutları ve hareket koşullarında test edilecek şekilde geliştirilmiştir.

- **Gerçek veri ile eğitim:** Küçük hedef probleminin kapsamını genişletmek
  amacıyla yaklaşık **13 GB'lık UAVDT** veri seti kullanılmış, ardından
  **VisDrone** verileri ile fine-tuning uygulanmıştır.
- **Küçük hedef testleri:** Hedef boyutları farklı piksel seviyelerinde
  sistematik olarak test edilmiş ve adaptif ROI yaklaşımı ile küçük hedef
  performansı geliştirilmiştir.
- **Gazebo doğrulaması:** Farklı irtifa, hedef hareketi, kamera hareketi ve
  çeldirici koşullarını test etmek için Gazebo tabanlı simülasyon senaryoları
  kullanılmıştır.
- **Donanım geçişi:** Hedef donanım Raspberry Pi Zero 2 W + Raspberry Pi AI
  Camera olmakla birlikte fiziksel donanım henüz mevcut olmadığından,
  gerçek zamanlı donanım doğrulaması sonraki aşama olarak planlanmaktadır.
- **Gerçek zamanlı çalışma:** Sistem mimarisi, kamera → tespit → takip → ROI
  → yeniden edinme akışını gerçek zamanlı çalışmaya uygun olacak şekilde
  yapılandırılmıştır.

## 8. Geliştirilecek Alanlar

1. **Adaptif ROI:** Daha küçük hedef boyutlarında R=160 ve R=80 basamaklarının
   farklı irtifa ve hareket koşullarında geliştirilmesi.

2. **Yeniden edinme:** Hedef kaybı sonrası doğru hedefe yeniden ulaşma sürecinin
   daha kararlı hale getirilmesi.

3. **Takip kararlılığı:** Küçük hedeflerde merkez, boyut ve takip sürekliliğinin
   iyileştirilmesi.

4. **Aktif Gazebo:** İrtifa, yönelim, hız ve hedef hareketlerinin bulunduğu
   gerçek zamanlı etkileşimli uçuş simülasyonunun geliştirilmesi.

5. **Gerçek donanım:** Raspberry Pi Zero 2 W ve Raspberry Pi AI Camera üzerinde
   FPS, gecikme ve kaynak kullanımının doğrulanması.

6. **IMX500 entegrasyonu:** Modelin IMX500 çalışma ortamına uygun şekilde
   paketlenmesi ve çalıştırılmasının geliştirilmesi.

7. **Gerçek uçuş koşulları:** Kamera hareketi, titreşim, hareket bulanıklığı ve
   farklı görüş koşullarında sistem kararlılığının artırılması.
   
## 9. Araştırma Özeti

Projenin geliştirme sürecinde gerçekleştirilen araştırma ve test aşamalarının
(A3.9 → K-MOD) özeti ve ilgili raporlar →
**[docs/ARASTIRMA_OZETI.md](docs/ARASTIRMA_OZETI.md)**

