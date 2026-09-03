# Deney 4H — template öğrenme hafızası nedensellik testi (lr kontrollü)

**`takip/` hiç değiştirilmedi — geri alınacak bir şey yok.** md5'ler koşum
boyunca ve sonunda Deney 2 durumuyla birebir (`md5sum -c` 6/6 OK).
Commit/push yok.

## `lr`'nin gerçek kullanımı (doğrulandı)

```
izleyici.py:315   lr = 0.125 if self.boyut.max() > 18 else 0.04
izleyici.py:316   self.cekirdek.ogren(bgr, gri, self.kf.konum, self.boyut, lr)
cekirdekler.py:212  lr = self.lr if lr is None else lr        # ← çağrı ezer
cekirdekler.py:214  self.A = (1-lr)*self.A + lr*(G*conj(F))
cekirdekler.py:215  self.B = (1-lr)*self.B + lr*(F*conj(F)).sum(0)
```

Yani çekirdeğin `self.lr`'si (satır 103, 0.09) **kullanılmıyor**; etkin değer
her karede izleyici'den geliyor ve ölçüldü: **beş kaynakta da 0.125**
(kutu her yerde 18 px'ten büyük).

### Kod değiştirmeden nasıl kontrol edildi

`izleyici.py:128` çekirdek **örneği** kabul ediyor. Bu yüzden `izleyici.py`
düzenlenmedi; geçirilen `lr`'yi bir çarpanla ölçekleyen teşhis alt sınıfı
(`LrCekirdek`) örnek olarak geçirildi. Tek deney değişkeni `carpan`.
Ölçüm aracı: `gazebo/tani_lr.py`.

### Kontrol koşumu — `carpan = 1.0` Deney 2 ile birebir mi?

| kaynak | IoU (beklenen) | merkez (beklenen) | sonuç |
|---|---|---|---|
| G3_agresif | 0.760 (0.760) | 3.81 (3.81) | **OK** |
| G3_kritik | 0.704 (0.704) | 5.07 (5.07) | **OK** |
| G0 | 0.912 (0.912) | 1.24 (1.24) | **OK** |
| 117/23 | 0.701 (0.701) | 5.51 (5.51) | **OK** |
| 268/31 | 0.000 (0.000) | 383.61 (383.61) | **OK** |

Beş kaynakta da birebir → gözlenen her fark **yalnızca deneysel `lr`
değerinden** kaynaklanıyor.

---

## Sonuçlar

### Ana tablo

| kaynak | lr | template kısa değişim p50 | kümülatif (son) | **DCF dx** | \|dx\| p50 | IoU | merkez | drift |
|---|---|---|---|---|---|---|---|---|
| **G3_agresif** | 0.0625 | 0.0097 | 0.245 | **−2.30** | 2.40 | **0.808** | 2.24 | yok |
| | 0.1250 | 0.0135 | 0.264 | −4.17 | 4.31 | 0.760 | 3.81 | yok |
| | 0.2500 | 0.0213 | 0.452 | **−7.10** | 7.00 | 0.684 | 6.15 | yok |
| **G3_kritik** | 0.0625 | 0.0102 | 0.206 | **−2.28** | 2.37 | **0.776** | 2.51 | yok |
| | 0.1250 | 0.0148 | 0.242 | −4.78 | 4.89 | 0.704 | 5.07 | yok |
| | 0.2500 | 0.0203 | 1.023 | **−9.82** | 12.65 | 0.452 | 20.38 | **266** |
| **G0** | 0.0625 | 0.0073 | 0.142 | **−0.10** | 0.81 | **0.923** | 0.83 | yok |
| | 0.1250 | 0.0092 | 0.154 | −1.08 | 1.38 | 0.912 | 1.24 | yok |
| | 0.2500 | 0.0131 | 0.181 | **−1.63** | 2.05 | 0.893 | 1.82 | yok |
| **117/23** | 0.0625 | 0.0177 | 0.868 | **−6.52** | 5.22 | **0.684** | 5.44 | yok |
| | 0.1250 | 0.0270 | 0.942 | −4.85 | 4.58 | 0.701 | 5.51 | yok |
| | 0.2500 | 0.0415 | 0.982 | **−3.87** | 4.56 | **0.715** | 5.73 | yok |
| 268/31 | 0.0625 | 0.0038 | 0.548 | −223.88 | 207.71 | 0.000 | 401.01 | 151 |
| | 0.1250 | 0.0075 | 0.514 | −180.51 | 155.14 | 0.000 | 383.61 | 151 |
| | 0.2500 | 0.0120 | 0.882 | −288.76 | 325.49 | 0.000 | 401+ | 151 |

### Monotonluk

| kaynak | yön |
|---|---|
| G3_agresif | **ARTAN** — lr ↑ → \|bias\| ↑ (2.30 → 4.17 → 7.10) |
| G3_kritik | **ARTAN** (2.28 → 4.78 → 9.82) |
| G0 | **ARTAN** (0.10 → 1.08 → 1.63) |
| **117/23** | **AZALAN** — lr ↑ → \|bias\| **↓** (6.52 → 4.85 → 3.87) |
| 268/31 | monoton değil (kopuk takip, 151. karede drift; karar dışı) |

---

# Altı sorunun cevabı

### 1. lr değişince template öğrenme miktarı değişti mi?
**Evet, beş kaynakta da monoton.** Kısa dönem değişim p50 lr ile birlikte
ölçekleniyor (G3_agresif 0.0097 → 0.0135 → 0.0213; 117/23 0.0177 → 0.0270 →
0.0415). Müdahale hedeflenen değişkeni gerçekten hareket ettirdi.

### 2. lr değişince DCF biası değişti mi?
**Evet, her kaynakta belirgin biçimde.** Gazebo'da 3 kat aralık
(G3_kritik: 2.28 → 9.82 px), VisDrone'da 1.7 kat (6.52 → 3.87 px).

### 3. İlişki monoton mu?
**Evet — ama işareti kaynağa göre değişiyor.** Gazebo'da üç senaryoda da
artan, VisDrone 117/23'te azalan.

### 4. Gazebo'da görülen ilişki VisDrone'da da var mı?
**HAYIR — tam tersi.** Gazebo'da öğrenmeyi azaltmak biası küçültüyor ve IoU'yu
yükseltiyor (0.760 → 0.808); VisDrone'da öğrenmeyi azaltmak biası **büyütüyor**
ve IoU'yu düşürüyor (0.701 → 0.684). Artırmak ise iyileştiriyor (→ 0.715).

### 5. 4G korelasyonu nedensel olarak desteklendi mi?
**Gazebo'da evet, VisDrone'da HAYIR — ve bu, 4G'nin en önemli düzeltmesidir.**

4G'de kümülatif template değişimi ↔ \|bias\| korelasyonu 117/23'te de
**pozitifti** (P +0.58). Bu turda aynı korelasyon her çarpanda pozitif kalmaya
devam ediyor (P +0.61 / +0.58 / +0.42) — **ama müdahale ters yönde sonuç
veriyor.** Yani 117/23'teki gözlemsel korelasyon **sahte**: ikisi de birlikte
artıyor ama biri diğerinin nedeni değil.

Bu, nedensellik testinin neden gerekli olduğunun doğrudan kanıtıdır; 4G'nin
"ilk genellenen ilişki" sonucu **geri alınmalıdır**.

### 6. Alternatif açıklamalar kaldı mı?
**Evet ve tersine dönüş onu işaret ediyor.** Öğrenmenin iki karşıt etkisi var:

* **(a) arka planı soğurmak** — zararlı, biası büyütür
* **(b) hedefin gerçek görünüm değişimine uyum** — yararlı

Gazebo'da hedef tek renkli sabit bir SDF kutusu (kontrast 48–146), görünümü
neredeyse hiç değişmiyor → yalnızca (a) çalışıyor → az öğrenmek iyi.
Gerçek hava görüntüsünde hedefin görünümü gerçekten değişiyor → (b) baskın →
çok öğrenmek iyi.

Ölçülen destek: `carpan 1.0`'da kümülatif template değişimi Gazebo G3'te
0.24–0.26 iken **117/23'te 0.94** — gerçek hedefin görünümü ~4 kat daha fazla
kayıyor.

---

## Hüküm

Karar kuralı: *"Hipotez ancak aynı yönde en az Gazebo + 117/23 üzerinde
görülürse desteklenmiş kabul edilecek. Sadece Gazebo'da görülürse genellenmedi
kabul et."*

> **Gazebo'da nedensel olarak DESTEKLENDİ (3/3 senaryo, doz-yanıt ilişkisiyle),
> ama GENELLENMEDİ — VisDrone'da işaret ters. Kural gereği hipotez
> REDDEDİLMİŞTİR.**

Ayrıca bu deney, ileride "biası öldürmek için öğrenmeyi azalt" biçiminde
gelebilecek her fikri **önden çürütüyor**: gerçek veride tam olarak zararlı.

## Faz C'nin biriken tablosu

| deney | Gazebo | VisDrone | sonuç |
|---|---|---|---|
| 4C rafine ağırlığı | +%52 merkez | 117/23 çöktü | ters |
| 4D adaptif ağırlık | sinyal yok | sinyal yok | elendi |
| 4E padding | monoton ↓ | ters | ters |
| 4G öğrenme korelasyonu | pozitif | pozitif | *genellendi sanıldı* |
| **4H öğrenme nedenselliği** | **artan** | **azalan** | **ters** |

Beş bağımsız hat, aynı sonuç: **Gazebo'dan türetilen ilişkiler gerçek veriye
taşınmıyor, hatta işaret değiştiriyor.** 4G bunun tek istisnası gibi
görünüyordu; müdahale onun da gözlemsel bir yanılsama olduğunu gösterdi.

## Sıradaki tek aday — takipçi değişikliği değil

Yeni bir optimizasyon önerilmiyor. Beş turun ortak dersi, sorunun takipçide
değil **karar tabanında** olduğunu gösteriyor: Faz C boyunca her karar
Gazebo'nun 22 kaydı üzerinden verildi, gerçek veri tarafında ise fiilen
**tek** kullanılabilir dizi var (117/23). 182/127 ve 268/31 hiçbir
yapılandırmada takip edilemiyor (kontrast 43.9 ve **−36.9**, hedef 21×19 ve
12×6 px).

Depoda **7 VisDrone dizisi** var, koşum takımında yalnızca 3'ü. Bir sonraki
adım bir takipçi değişikliği değil, **karar tabanının genişletilmesi**
olmalıdır: kalan 4 dizinin takip edilebilirliğini (kontrast, hedef boyutu,
kilitlenme) salt okunur ölçmek ve gerçek veri tarafını tek diziden çıkarmak.
Bu yapılmadan hiçbir gelecek deney güvenilir biçimde karara bağlanamaz —
4C, 4E ve 4H'nin üçü de tek dizinin sonucuyla yön değiştirdi.

**Bu bir öneridir, uygulanmadı.**
