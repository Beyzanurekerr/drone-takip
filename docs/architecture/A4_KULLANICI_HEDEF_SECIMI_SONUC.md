# A4 — Kullanıcı hedef seçimi (fare ile ROI): sonuç

**Kapsam:** yalnızca `USER TARGET SELECTION / INITIALIZATION`.
`takip/`, DCF, KF, EgoMotion, `rafine_kutu`, `_boyut_tazele`, `_boyut_sinirla`,
A3.9, A3.10, YOLO/MOT/ByteTrack/Optuna — **hiçbirine dokunulmadı**.
Commit/push yok. A3.9 staged checkpoint (154 dosya) ve A3.10 değişiklikleri
korundu.

## 1. Yapılan tek değişiklik

Tek dosya: **`main.py`**, üç ekleme — `kos()` gövdesi **bit-birebir aynı**.

| ekleme | yer | ne |
|---|---|---|
| `_roi_aday()` | `main.py:91` sonrası | saf geometri: iki fare noktası → aday sözlüğü |
| `_RoiSecim` | aynı blok | fare olaylarından ROI kuran durum makinesi (pencereden bağımsız) |
| `fare_hedef_sec()` | aynı blok | GUI döngüsü; mevcut `secici(adaylar, kare) -> aday \| None` sözleşmesini uygular |
| `--sec` bayrağı | `main.py:618` | argparse |
| `hedef_secici=` | `main.py:635` | `fare_hedef_sec() if a.sec else None` |

**`kos()` gövdesi değişmedi** — AST karşılaştırmasıyla doğrulandı:

| fonksiyon | AST md5 (önce/sonra) |
|---|---|
| `kos` | **BİREBİR AYNI** (`6c39bda7`) |
| `otomatik_hedef_sec` | BİREBİR AYNI (`6631b0e6`) |
| `gt_hedef_sec` | BİREBİR AYNI (`f246fc28`) |
| `ciz` | BİREBİR AYNI (`9f58aba9`) |
| `goster` | BİREBİR AYNI (`233d00cd`) |

### 2 px ön-telafi
`kos():382-384` hareket lekesi için `kutu[2:] -= 2` uygular ve kutuyu `merkez`e
göre yeniden konumlandırır. Elle çizilen ROI dilate edilmiş değildir; bu yüzden
`_roi_aday` kutuyu **2 px büyük** (`x−1, y−1, w+2, h+2`) döndürür ve telafi
**tam olarak sadeleşir**. `kos()` gövdesine dokunulmadı.

## 2. K1–K9 sonuçları

### K1 — fare ile seçim
**GEÇTİ.** `cv2.setMouseCallback` ile bağlanan geri çağırım sentetik fare
olaylarıyla sürüldü (LBUTTONDOWN → MOUSEMOVE → LBUTTONUP): seçici
`kutu [299.0, 219.0, 54.0, 26.0]`, `merkez [326.0, 232.0]`, `alan 1248`
döndürdü. Pencere `kare.kaynak_adi` ile kuruluyor; `kos()` bilgilendirilmiyor.

### K2 — sözleşme
**GEÇTİ.** Anahtarlar tam olarak `{kutu, merkez, alan}`, `kutu` `float32`
`(x,y,w,h)`, `w,h > 0`.

### K3 — kilit kutusu ↔ çizilen ROI
**A4 sınırında GEÇTİ, `kilitle()` içinde KALDI.** İki ayrı ölçüm:

| kaynak | çizilen ROI | `kos()` sonrası kutu (A4 sınırı) | `kilitle()` çıkışı | A4 farkı | son fark |
|---|---|---|---|---:|---:|
| sim:test1 | 300,220,52,24 | **300,220,52,24** | 334.5,228.5,51,23 | **0.00 px** | 34.50 |
| simkayit:hizli_hedef | 290,215,55,25 | **290,215,55,25** | 235,217,165,6 | **0.00 px** | 110.00 |
| gazebo:G0 | 290,215,55,25 | **290,215,55,25** | 256,236,53,29 | **0.00 px** | 34.00 |
| visdrone 117/23 | 400,250,55,50 | **400,250,55,50** | **400,250,55,50** | **0.00 px** | **0.00** |

* **A4'ün ürettiği kutu dört kaynakta da çizilen ROI ile tam olarak aynı
  (0.00 px).** Ön-telafi çalışıyor.
* Sonraki fark `kilitle()`'nin **kendi içindeki** `rafine_kutu` çağrısından
  geliyor (`izleyici.py:195-197`, *"hareket lekesi kaba bir kutudur → renk
  kontrastıyla keskinleştir"*). 117/23'te `rafine_kutu` `None` döndü ve kutu
  **aynen korundu**.
* **Bu bir A4 regresyonu değildir** — mevcut `otomatik_hedef_sec` ile de aynı
  şey oluyor (A4 kapalıyken ölçüldü): sim:test1 **3.89 px**, gazebo:G0
  **1.68 px**, visdrone 117/23 **6.59 px**.
* Elle çizilen ROI'nin `rafine_kutu` tarafından değiştirilmesi tasarım gereği
  tartışmalıdır ama düzeltmesi `kilitle()`'ye dokunmayı gerektirir ve
  `rafine_kutu` bu turda **dokunulmaz** listesindedir. Ayrıca bu tam olarak
  A3.9'un açık **P0.1 boyut ölçümü** borcudur (`A3.9_KAPANIS.md` §8.2):
  `simkayit:hizli_hedef`'te rafine 55×25 ROI'yi **165×6**'ya çevirdi.

> **Karar gerekiyor:** K3 kelimesi kelimesine (`kilitle()` sonrası ≤2 px)
> ancak `kilitle()`'de `rafine_kutu` çağrısı kullanıcı seçimi için atlanırsa
> sağlanır. Bu, A4'ün yasak listesindeki bir değişikliktir; **yapılmadı** ve
> karar kullanıcıya bırakıldı.

### K4 — Deney 2 tracker'ı
**GEÇTİ.** `takip/` md5 **6/6** aynı; `git diff -- takip/` boş; `kos()` AST'si
birebir.

### K5 — ESC ile güvenli iptal
**GEÇTİ.** ESC → 1. çağrı `None`, `iptal` bayrağı `True`, 2. çağrı **bloke
olmadan** `None`. Koşum kilitsiz devam ediyor, çökme yok.

### K6 — geçersiz ROI'de çökme yok
**GEÇTİ.** 10 geometri + 5 durum-makinesi vakasının hiçbirinde istisna yok:

| durum | sonuç |
|---|---|
| tek tık · sıfır genişlik · sıfır yükseklik · 1×1 px · 3×3 px (min_kenar altı) | **None** (güvenli) |
| tamamen kadraj dışı · tamamen negatif | **None** (güvenli) |
| ters sürükleme (300,250)→(240,200) | normalize edildi → 60×50 ROI |
| kadraj dışı sol-üst (−50,−40)→(60,50) | **kırpıldı** → 60×50 ROI |
| kadraj dışı sağ-alt (600,450)→(900,700) | kırpıldı → 40×30 ROI |
| bırakmadan hareket | None |

*(Kırpılan kutuların `kutu` alanı `x−1, y−1` ile başlar; bu ön-telafinin
parçasıdır ve `kos()` telafisinden sonra tam olarak kırpılmış ROI'ye döner.)*

### K7 — kaynaklar arası ortaklık
**GEÇTİ.** Aynı seçici dört kaynakta değişmeden çalıştı ve kilit kurdu:
`sim:test1`, `simkayit:hizli_hedef`, `gazebo:G0`, `visdrone 117/23`.
`camera` kaynağı mimari olarak aynı `Kare` + pencere adını üretir; **gerçek
kamerayla test edilmedi** (`KALICI_KISITLAR.md` §2b: gerçek kamera akışı
hiç test edilmedi).

### K8 — `--sec` yokken regresyon
**GEÇTİ.**
* test1–test7: 7 metrik × 7 senaryo, **0 fark**.
* A3.10 senaryoları (9 basamak, iki ayrı koşum birebir):
  `hizli_hedef` IoU **0.914798558**, merkez 0.482954592, kilit 1.0, drift yok;
  `duran_hedef` IoU **0.572938979**, merkez 0.989084423, kilit 0.651877133,
  drift 176. A3.10 kapanışında 4 basamakla raporlanan 0.9148 / 0.5729 ile
  tutarlı.

### K9 — seçim maliyeti
**GEÇTİ.** `sim:test1`, 300 kare, sabit ROI seçicisiyle:

| | |
|---|---|
| seçici çağrı sayısı | **1** (ISINMA=6 sonrası ilk kare) |
| kilit karesi | 6 |
| **kilit sonrası çağrı** | **0** |
| seçicinin tüm koşumdaki CPU süresi | **0.023 ms** |
| kare başına ortalama | **0.000078 ms** |

`main.py:377` `if not kilitli` → kilit kurulduktan sonra seçici **hiç
çağrılmıyor**; takip döngüsüne sürekli maliyet **eklenmiyor**. GUI döngüsünün
ölçülen 57.7 ms'si tamamen `waitKey(20)` beklemesidir (kullanıcı girdisi süresi,
CPU değil) ve yalnızca kilit öncesi yaşar.

## 3. Donanım / performans kısıtları

`KALICI_KISITLAR.md` uyarınca A4'te donanıma yönelik **yeni özellik
eklenmedi**. İlgili tek nokta K9'dur: seçim hattı takip döngüsüne ölçülebilir
yük eklemiyor (kare başına 0.000078 ms), dolayısıyla Pi Zero 2 W bütçesine
etkisi yok. Küçük hedef benchmark'ı A4'te koşulmadı; A5/A6'ya bırakıldı.

## 4. Kullanım

```bash
python3 main.py --source sim --scenario test1 --sec
python3 main.py --source gazebo --dataset data/gazebo --sequence G0 --sec
```
Sol tuşla sürükle → bırak = seçim · ESC = iptal (koşum kilitsiz devam eder).
`--sec` verilmezse **mevcut `otomatik_hedef_sec` aynen** çalışır.

## 5. Hüküm

**K1, K2, K4, K5, K6, K7, K8, K9 geçti (8/9).**
**K3, A4'ün sınırında (0.00 px) geçti; `kilitle()` içindeki `rafine_kutu`
nedeniyle kelimesi kelimesine sağlanmadı** — bu davranış A4 öncesinde de
mevcut, yasak listesindeki bir dosyadan kaynaklanıyor ve A3.9'un açık P0.1
borcunun bir görünümü. Değişiklik **geri alınmadı**, çünkü geri almak K3'ü
düzeltmez; aynı sapma varsayılan seçicide de var.

**Kod, commit ya da push yapılmadı; `takip/` md5 6/6 aynı.**
