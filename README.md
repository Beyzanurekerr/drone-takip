# Drone Hedef Takip

Havadan çekilen görüntüde **seçilen tek bir aracı**, araç görüntüde çok küçük hale gelse
bile, mümkün olduğunca uzun süre ve yüksek FPS ile takip etmek.

Problem klasik araç tespiti değil; şu dört kısıtın **aynı anda** sağlanması:
küçük nesne · hareketli kamera · benzer nesneler · düşük donanım.

## Kurulum

Sadece `opencv-python` ve `numpy` gerekir. Derin öğrenme bağımlılığı **yoktur**.

```bash
python3 calistir.py test6 --canli   # CANLI: ekranda pencere aç, takibi anlık izle
python3 calistir.py --hepsi --canli # 7 senaryoyu sırayla canlı izle
python3 kiyasla.py --video     # 7 testi koş, metrikleri bas, cikti/*.mp4 üret, RAPOR.md yaz
python3 calistir.py test6      # tek senaryo + video (pencere açmaz)
python3 minboyut.py            # minimum takip boyutu deneyi (çekirdek karşılaştırmalı)
python3 tarama.py              # çekirdek / parametre karşılaştırması (paralel)
```

Canlı pencerede: **boşluk** duraklat/devam · **n** duraklatılmışken tek kare ilerle ·
**q** veya **ESC** çık. WSL kullanıyorsan WSLg gerekir (Windows 11'de hazır gelir).

## Görüntü kaynakları

Takip hattı görüntünün nereden geldiğini bilmez. `main.py` üç kaynağı da aynı
boru hattına bağlar:

```bash
python3 main.py --source data/videos/drone_traffic_01.mp4   # MP4 drone videosu
python3 main.py --source sim                                # prosedürel simülatör
python3 main.py --source sim:test6                          # senaryo seçerek
python3 main.py --source camera                             # webcam (index 0)
python3 main.py --source camera:1                           # ikinci kamera
```

Eski biçim de çalışmaya devam eder: `--source video --input dosya.mp4`

Ek seçenekler: `--cekirdek mosse` · `--kaydet cikti/kayit.mp4` ·
`--max-kare 300` · `--penceresiz` (ekransız koşum).

Koşum sonunda gecikme özeti basılır:

```
  kaynak      : sim:test1  (sim)
  islenen kare: 80
  hedef       : KILITLENDI
  FPS         : 362.8
  gecikme     : ort 2.76 ms | p50 2.42 | p95 4.58 | max 5.28
```

### Veri klasörü

```
data/
├── videos/     # kendi drone/aerial mp4'lerin
└── datasets/   # UAV123 / UAVDT / DTB70 (ileride)
```

İkisi de `.gitignore`'da — depo şişmesin. `cikti/*.mp4` dosyaları **ham görüntü
değildir**, üzerlerine kutu ve yazı basılmıştır; kaynak videosu olarak
kullanılırsa ekranda iki kat yazı görünür.

Kod içinden:

```python
from kaynak import kaynak_olustur

with kaynak_olustur("video", girdi="data/ucus.mp4") as kaynak:
    for kare in kaynak:
        sonuc = tak.guncelle(kare.goruntu)   # kare.goruntu -> BGR ndarray
```

Her `Kare`: `goruntu`, `indeks`, `zaman`, `kaynak_adi`, `genislik`, `yukseklik`,
`fps` — ayrıca simülatörde `gt` (ground-truth kutusu) ve `gorunur`. Video ve
kamerada bu ikisi `None`'dır. Kaynaklarda ayrıca `acik_mi()`, `kapat()`,
`bilgi()` ve `tur` (`sim` / `video` / `kamera`) bulunur.

Hedef seçimi takılıp çıkarılabilir — ileride fare ile seçim aynı imzayı
kullanacak, döngü değişmeyecek:

```python
def secici(adaylar, kare):    # -> aday sözlüğü ya da None
    ...
main.kos(kaynak, hedef_secici=secici)
```

Kaynak testleri: `python3 test_kaynak.py` (pytest gerektirmez).

Ölçüm ve kıyaslama hâlâ `kiyasla.py` / `calistir.py` üzerinden yapılır;
`main.py` onların yerini almaz.

## Mimari

```
kare
 │
 ├─ [1] EGO-MOTION      seyrek LK optik akış + RANSAC benzerlik dönüşümü
 │                      → kameranın kayma / dönme / zoom hareketi
 │                      Tek hesap, üç kazanç:
 │                        · arama penceresini daraltır      (hız)
 │                        · hareketliyi arka plandan ayırır (yeniden tespit)
 │                        · ölçek katsayısı verir           (irtifa değişimi)
 │
 ├─ [2] TAKİP           renk kanallı DCF korelasyon filtresi + Kalman (sabit hız)
 │                      Kalman'a ego dönüşümü doğrudan uygulanır → hız vektörü
 │                      kameranın değil ARACIN gerçek hareketini temsil eder
 │
 ├─ [3] ÇAPA            yerel renk kontrastıyla kutu rafinesi (her 4 karede bir)
 │                      Korelasyon filtresi homojen yolda geriye sürüklenir;
 │                      bu adım kutuyu doğrudan ölçerek geri toplar
 │
 └─ [4] YENİDEN TESPİT  ego-telafili kare farkı → hareketli lekeler
        (kayıpta)       → renk + şablon + boyut imzasıyla eşleştirme
                        Arama yarıçapı büyüdükçe skor ağırlığı konumdan
                        GÖRÜNÜME kayar; belirsizlik kuralı yanlış araca
                        kilitlenmeyi engeller
```

Durum makinesi: `KİLİTLİ → ŞÜPHELİ (ölü hesap) → ARAMA → KAYIP (aramayı sürdürür)`

Şüpheli durumda **öğrenme durur**. Kritik: filtre kaybettiği anda öğrenmeye devam
ederse asfaltı öğrenir ve bir daha geri dönemez.

## Sonuçlar (7 test, kusursuz ground-truth)

| test | IoU | @0.5 | hassasiyet | merkez hata | kilit | ID switch |
|---|---|---|---|---|---|---|
| 1 yakın araç | 0.925 | 100% | 100% | 0.25 px | 100% | 0 |
| 2 uzaklaşan | 0.435 | 45% | 83% | 1.59 px | 100% | 0 |
| 3 çok küçük | 0.560 | 61% | 85% | 1.75 px | 100% | 0 |
| 4 çoklu araç | 0.866 | 100% | 100% | 0.57 px | 100% | 0 |
| 5 benzer araçlar | 0.897 | 100% | 100% | 0.15 px | 100% | 0 |
| 6 kısa kayıp | 0.747 | 81% | 92% | 0.99 px | 78% | 1 |
| 7 kamera hareketi | 0.764 | 91% | 100% | 0.97 px | 100% | 0 |

**hassasiyet** = merkez hatasının hedef köşegeninin yarısından küçük olduğu kare oranı.
Küçük hedefte IoU 1 piksellik kutu hatasında çökerken bu ölçü adil kalır — bu yüzden
ikisi birlikte raporlanır.

test6'da kilit oranının tavanı %76'dır (karelerin %24'ünde hedef üst geçit altındadır).

### Minimum takip boyutu (test 3, 3 gürültü tohumu)

| hedef | IoU | hassasiyet | merkez hata | hüküm |
|---|---|---|---|---|
| 52 × 22 px | 0.94 | 100% | 0.44 px | başarılı |
| 31 × 13 px | 0.91 | 100% | 0.44 px | başarılı |
| 20 × 8 px | 0.67 | 100% | 0.81 px | başarılı |
| 16 × 7 px | 0.72 | 100% | 0.70 px | başarılı |
| 13 × 6 px | 0.56 | 94% | 1.14 px | kararsız |
| 9 × 4 px | 0.35 | 99% | 0.37 px | başarılı |
| 7 × 3 px | 0.24 | 79% | 0.32 px | kararsız |
| 5 × 2 px | 0.17 | 67% | 0.37 px | kayıp |

İki ayrı sınır var, karıştırmamak gerekir:
- **konum kilidi** ~9 × 4 px'e kadar korunur (merkez hatası hâlâ 1 px altında)
- **kutu ölçüsü** ~25 × 10 px altında güvenilmez olur (IoU bu yüzden düşer)

Takip uygulaması için belirleyici olan birincisidir.

### Çekirdek karşılaştırması

Takip çekirdeği takılıp çıkarılabilir (`HedefTakip(cekirdek="...")`).

| çekirdek | 7 test skoru | en küçük hedef | not |
|---|---|---|---|
| **renk_dcf** | 0.892 | **9.0 × 3.7 px** | gri + renk kanalları; varsayılan |
| mosse | 0.888 | 16.5 × 6.8 px | tek kanal gri, en ucuzu |
| ncc | 0.770 | 16.5 × 6.8 px | `matchTemplate`, görünüm değişimine kırılgan |
| akis | 0.630 | — | Median Flow; küçük hedefte köşe bulamıyor |

Ana bulgu: **20×10 px altında doku diye bir şey kalmıyor, renk kalıyor.** Renk
kanallarını eklemek minimum takip boyutunu yarıya indiriyor — yani aynı araç için
iki katı irtifa.

## Hız

640×480'de kare başına ~2.0 ms (bu makinede ~500 FPS):

| aşama | pay |
|---|---|
| ego-motion (LK + RANSAC) | %38 |
| korelasyon çekirdeği | %34 |
| tespit / kutu rafinesi | %12 |

Pahalı olan yeniden tespit **sadece kayıpta** çalışır; kilitliyken kare başına iş
sabittir. Raspberry Pi tahminleri `kiyasla.py` çıktısındadır ve **tahmindir** —
kesin sayı için cihazda ölçülmelidir.

## Simülasyon

`sim/` prosedürel havadan sahne üretir: asfalt, şeritler, binalar, ağaçlar, park
halinde araçlar (statik çeldirici). Kamera dik bakar; irtifa → ölçek, yaw → dönme,
titreşim → gürültü. Her kare için **kusursuz ground-truth kutusu** bilinir — gerçek
videoda elle etiketleme gerekirdi.

Hedef ilk karede elle değil, sistemin **kendi hareket tespiti listesinden** seçilir.
GT kutusuyla kilitlemek ölçümü şişirirdi; burada gerçek kullanımdaki gibi tespit
kutusuyla kilitlenir.

Kuşbakışı görüntüde araç aracın önüne geçemez; test 6'daki oklüzyon bu yüzden üst
geçit / ağaç örtüsü olarak modellenmiştir.

## Bilinen sınırlar

1. **Yanlış güven**: hedef ~13 px altında kaybedildiğinde sistem hâlâ `KİLİTLİ`
   diyebiliyor. PSR düşmüyor çünkü filtre yol dokusuna kilitleniyor. Bağımsız bir
   doğrulama (periyodik imza kontrolü) gerekiyor.
2. **Ego ölçek yanlılığı**: kare kare ölçek kestirimi kısa vadede doğru, uzun vadede
   ~%8/300 kare yanlı. Bu yüzden ölçek **integre edilmiyor**; kutu boyutu doğrudan
   ölçümle çapalanıyor.
3. Sadece simülasyon. Gerçek veri (VisDrone / UAV123 / DTB70) üzerinde aynı harness
   koşulmadı.
4. Pi üzerinde gerçek ölçüm yapılmadı; sayılar ekstrapolasyon.

## Sonraki adımlar

- `KİLİTLİ` durumda periyodik bağımsız doğrulama → yanlış güven sorunu
- 320×240 giriş + ROI-only işleme ile Pi bütçesine inme
- Gerçek veri seti üzerinde aynı ölçüm harness'ı
- Referans üst sınır olarak `cv2.TrackerNano` / `TrackerVit` ile kıyas
