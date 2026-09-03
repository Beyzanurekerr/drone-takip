# Deney 2 teşhisi — G3_agresif'teki −0.006 IoU kaybı

**Sonuç: kayıp marjinal bir açı seçme hatası DEĞİL.** Seçilen açı gerçek dönmeyi
**birim kazançla** (0.998) izliyor, ama arama adımında düzeltilmeyen bir DC
yanlılık var; bu yanlılık zamanda doğrusal olarak birikiyor ve IoU kaybını
tek başına açıklıyor. Çözüm implement edilmedi.

Ölçüm aracı: `gazebo/tani_aci.py` — çekirdeğin `_yanit`/`ara` metotlarını
dışarıdan sarar, üç adayın (açı, PSR) çiftlerini, ego tohumunu ve seçileni
kare kare yazar. Takipçiye dokunmaz, hiçbir eşiği değiştirmez.

## 1. Kayıp gerçekten açı hatasından mı geliyor? — EVET

Eşleştirilmiş kare farkı (`dIoU = D2 − A3.8`) ile açı hatası arasındaki ilişki:

| | G3_agresif | G3_kritik |
|---|---|---|
| korelasyon(\|hata\|, dIoU) | **−0.729** | −0.380 |
| korelasyon(\|hata\|, Δmerkez hata) | **+0.848** | +0.391 |
| \|hata\| alt üçte bir → dIoU | **+0.0233** | +0.1597 |
| \|hata\| üst üçte bir → dIoU | **−0.0303** | +0.0561 |

**Açı doğru olduğunda Deney 2 G3_agresif'i de +0.023 iyileştiriyor.** Net
−0.006, hatanın büyüdüğü karelerden geliyor.

> Yöntem notu: ham IoU ile korelasyon ≈ 0 çıkıyor (−0.006) çünkü ham IoU
> GT kutusunun dönmeyle büyümesi tarafından domine ediliyor. Doğru değişken
> eşleştirilmiş fark `dIoU`; o da ilişkiyi net gösteriyor.

## 2. Hatanın biçimi: kazanç değil, zaman içinde doğrusal kayma

Üç model, aynı veriye:

| model | G3_agresif artık std | G3_kritik artık std |
|---|---|---|
| kazanç: `seçilen = k·gerçek + c` | 3.85° (k = **0.998**) | 3.07° (k = **1.000**) |
| sabit kayma: `hata = ortalama` | 3.85° | 3.07° |
| **zaman kayması: `hata = a·kare + b`** | **1.89°** (a = **−0.0397 °/kare**) | 2.65° (a = −0.0183) |

* korelasyon(hata, gerçek açı) = **−0.012** → hata açının büyüklüğünden bağımsız
* korelasyon(hata, kare no) = **−0.871** → hata zamanla doğrusal büyüyor

Yani **açı takibi ölçek olarak kusursuz** (kazanç 0.998); sorun sabit hızlı bir
kaymanın birikmesi. Zaman seyri (50 karelik pencereler, G3_agresif):

    hata:  −2.5  −4.3  −7.8  −11.0  −11.6  −10.8  derece
    dIoU:  +0.030 +0.017 −0.001 −0.020 −0.034 −0.029

## 3. Kayma nereden geliyor? — Bütçe kapanıyor

293 aktif kare, G3_agresif (adım 1.618°):

| bileşen | toplam | kare başına |
|---|---|---|
| gerçek toplam dönme | −22.20° | — |
| ego tohumu (`dteta` toplamı) | −22.08° | ego yanlılığı **+0.11°** (293 karede) |
| yuvarlama (`n·adım − tohum`) | **+2.66°** | +0.0091 |
| **arama adımı (`seçilen − n·adım`)** | **−14.57°** | **−0.0497** |
| birikmiş hata | **−11.79°** | −0.0406 ≈ ölçülen kayma −0.0397 ✔ |

**Ego suçlu değil** (293 karede +0.11° yanlılık — Deney 1'in aksine kusursuz).
**Yuvarlama suçlu değil** (ters işaretli, +2.66°). **Suçlu arama adımı.**

## 4. Marjinal seçim hatası mı? — HAYIR

Skor ayrımını `(birinci − ikinci)/birinci` olarak ölçtüm:

| | kare | ortalama arama adımı | toplam katkı |
|---|---|---|---|
| **beraberliğe yakın** (ayrım < %2) | 110/293 | **−0.0000°** | **−0.00°** |
| **net kazanan** (ayrım ≥ %2) | 183/293 | −0.0796° | **−14.57°** |

Beraberliğe yakın karelerin toplam katkısı **tam sıfır** — dengeli bir rastgele
yürüyüş, hiç birikmiyor. Kaymanın **tamamı**, bir adayın açık farkla kazandığı
karelerden geliyor. Yani korelasyon yüzeyi gerçekten yanlış açıda tepe yapıyor;
bu gürültü ya da eşitlik bozma sorunu değil.

Aday seçim dağılımı da simetrik: n−1 %20.8 · n %61.4 · n+1 %17.7
(G3_kritik: %18.8 · %63.8 · %17.4). Sistematik bir "hep alt adayı seç"
davranışı yok.

## 5. Yanlılığın imzası: dönüş yönüne göre asimetrik

| | G3_agresif | G3_kritik |
|---|---|---|
| `dteta < 0` (negatife dönerken) | **+0.0000 °/kare** | +0.0414 |
| `dteta > 0` (pozitife dönerken) | **−0.0966 °/kare** | −0.0670 |

Arama, **dönüşün geri geldiği yönde direniyor**; gitmekte olduğu yönde hiç
düzeltme yapmıyor. G3'ün açısı salınımlı olduğu için bu asimetri her salınımda
biraz daha negatife biriktiriyor.

Bu, şablonun **geçmiş duruşların kayan ortalaması** olmasının doğal sonucudur:
korelasyon tepesi anlık duruşun değil, şablonun hafızasının bulunduğu yerin
yakınında oluşur. Ve **mutlak çapa yok**: şablon seçilen açıda öğrenildiği için
herhangi bir sapma kendi kendini tutarlı hale getirir, geri getirici kuvvet
kalmaz. Ölçüldü — hata büyüdükçe arama onu geri çekmiyor, ittiriyor:

| hatanın bandı | kare | ortalama arama adımı |
|---|---|---|
| \|hata\| ≤ 3° | 31 | **+0.157** (geri çekiyor) |
| −8° … −3° | 87 | −0.130 (uzaklaştırıyor) |
| < −8° | 175 | −0.046 (uzaklaştırıyor) |

Hata −11° civarında durağanlaşıyor; sınırsız büyümemesinin nedeni şablonun
sonlu hafızasının sonunda direnç göstermesi.

## 6. G3_kritik neden aynı kusurdan etkilenmiyor?

Aynı yanlılık orada da var ama **kare başına 2.4 kat küçük** (−0.021 vs −0.050)
ve gerçek dönme 2.2 kat büyük. Ego tohumu hareketin çok daha büyük kısmını
taşıdığı için aramanın göreli payı düşüyor:

| | G3_agresif | G3_kritik |
|---|---|---|
| gerçek toplam dönme | −22.2° | −48.0° |
| arama katkısı | −14.6° | −6.2° |
| **arama / gerçek** | **%66** | **%13** |
| hata p50 | −8.90° | −1.85° |
| dIoU | −0.006 | **+0.125** |

## 7. Özet

* Kayıp **açı hatasından** geliyor (korelasyon −0.729), açı hatası **merkez
  hatasına** dönüşüyor (+0.848).
* Açı takibi **ölçek olarak doğru** (kazanç 0.998, R² 0.957); sorun sabit
  hızlı bir kayma (−0.0397 °/kare).
* Kayma **ego'dan değil** (+0.11° / 293 kare), **yuvarlamadan değil** (+2.66°),
  **aramadan** (−14.57°).
* **Marjinal/beraberlik hatası değil**: beraberliğe yakın 110 karenin katkısı
  tam 0.00°; kaymanın tamamı net kazananlı 183 kareden.
* Yanlılık **dönüş yönüne göre asimetrik** ve **mutlak çapa olmadığı için**
  serbestçe birikiyor.
* Açı doğruyken Deney 2 G3_agresif'i de **iyileştiriyor** (+0.023).

Bir sonraki deneyin konusu, açı için mutlak bir çapa (ör. şablonun kilit
anındaki duruşuna periyodik geri referans) olmalıdır — ama bu deneyin kapsamı
dışında ve **implement edilmedi**.
