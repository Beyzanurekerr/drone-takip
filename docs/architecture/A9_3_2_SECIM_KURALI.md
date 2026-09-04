# A9 Deney 3.2 — Geometrik aday seçim kuralı

**Yazıldığı tarih:** 2026-09-02 · **Deney 3.2 KOŞULMADAN ÖNCE yazıldı.**
Sonuçlara bakıp değiştirilmeyecek. Değişmesi gerekirse gerekçeli yeni sürüm
eklenir, bu sürüm silinmez.

## Neden bu kural

Deney 3.1 ölçtü: aday seçiminde **dedektör güveni kullanılamaz** (AUC 0.381,
şanstan kötü — doğru adaylar sistematik olarak *daha düşük* güvenli).
Ayrıştırıcı olan **geometrik tutarlılık**: merkez uzaklığı (AUC 0.982),
alan oranı (0.821), en-boy (0.808).

3.2 bu bulguyu bir seçim kuralına çevirip sınar.

## Ağırlık seçme problemi nasıl ortadan kaldırıldı

Üç bileşeni **ağırlıklı toplamak** ağırlık seçmeyi gerektirirdi ve ağırlıkları
3.1 verisinden okumak, sonucu veriye uydurmak olurdu (yasak).

Bunun yerine: **her bileşen kendi beklenen ölçeğine bölünür, sonra en kötüsü
alınır** (sonsuz-norm / bağlaç semantiği). Bir aday **bütün** bileşenlerde
tutarlı olmalıdır.

```
G = max( d_norm , a_norm , r_norm )
```

- **Seçilecek ağırlık yok.**
- **Eşik 1.0**, normalizasyonun *tanımıdır* ("her bileşen kendi beklenen ölçeği
  içinde"), veriden okunmuş bir sayı değildir.

## Bileşenler ve normalizasyon ölçekleri

Normalizasyon ölçeklerinin hepsi **kod tabanında zaten var olan** sabitlerdir.
Yeni sabit uydurulmadı.

### 1. Merkez uzaklığı

```
d       = |aday_merkezi − referans_merkezi|
d_beklenen = MAX_HIZ · Δt  +  max(ref_w, ref_h)/2
d_norm  = d / d_beklenen
```

- `MAX_HIZ = 35 px/kare` — `takip/izleyici.py` `Kalman.MAX_HIZ`, mevcut sabit.
  Anlamı: takipçinin kendi kabul ettiği azami hedef hızı. Hedef Δt karede
  bundan daha uzağa gidemez (takipçinin kendi varsayımına göre).
- `max(ref_w,ref_h)/2` terimi Δt=0 durumunu tanımlı kılar (aynı karede
  doğrulama): kutu yarı-genişliği kadar sapma normaldir.

### 2. Alan (doğrusal ölçek) tutarlılığı

```
s      = sqrt( (aday_w·aday_h) / (ref_w·ref_h) )      # DOGRUSAL olcek orani
a_norm = |log s| / log(2.6)
```

- `2.6` — `takip/tespit.py:122` `rafine_kutu` kabul kapısının üst sınırı
  (`0.35 < oran.mean() < 2.6`). Mevcut sabit. Anlamı: kod tabanının kendi
  "makul boyut oranı" tanımı.
- Log uzayı, çünkü ölçek **çarpımsal** bir büyüklüktür; 2× büyüme ile 2×
  küçülme aynı cezayı almalıdır.

### 3. En-boy tutarlılığı

```
r_norm = |log( (aday_w/aday_h) / (ref_w/ref_h) )| / log(2.6)
```

Aynı `2.6` toleransı kullanılır: en-boy için ayrı bir sabit **uydurmamak**
adına, boyut kapısıyla aynı ayarda tutulur. Bu bir seçim değil, yeni sabit
üretmemek için alınmış bilinçli bir kısıttır ve sonucu iyileştirmek üzere
ayarlanmayacaktır.

## Karar

```
GEÇEN ADAYLAR = { aday : G(aday) ≤ 1.0 }

if GEÇEN ADAYLAR boş:       -> ÇEKİMSER   (hiçbirini seçme)
else:                       -> argmin G   (EN TUTARLI aday; güven KULLANILMAZ)
```

**Çekimserlik zorunludur** ve 3.1'de yoktu. Gerekçesi K5: "herhangi bir nesneye
kilitlenmek" başarı değildir; kanıt yoksa seçim yapılmamalıdır. Bedeli
(geciken recovery, kare cinsinden) ayrıca ölçülecektir.

## İki referans AYRI ölçülür (4U tuzağı)

| referans | ref_merkez / ref_kutu | statü |
|---|---|---|
| **ORACLE** | son güvenilir karedeki **GT** kutusu | üst sınır, başarı sayılmaz |
| **OPERASYONEL** | son güvenilir karedeki **takipçi** kutusu (`kf.konum`, `self.boyut`) | gerçek sistemde kullanılabilecek olan |

**Ön hipotez (test edilecek, varsayılmayacak):** `d_norm` boyut bozulmasından
büyük ölçüde bağımsız kalır; `a_norm` ve `r_norm` kalmaz, çünkü ikisi de
`ref_w, ref_h`'ye bölünür ve 117/23'te `bho` 2–5 kat şişmiş durumdadır.

## Arama genişliği × zaman merdiveni

Kalman P **kullanılmaz** (Deney 3.0 S2: hatası yön değiştiriyor).
Merdiven, **3.0'ın "gerekli yarıçap p95" tablosundan** türetildi — 3.2
sonuçlarına bakmadan:

| geçen kare | 3.0 gerekli yarıçap p95 | seçilen R | R/2 kapsıyor mu |
|---|---|---|---|
| 1–5 | 42.8 px | **160** | ±80 ✓ |
| 6–20 | 87.2 / 148.9 px | **320** | ±160 ✓ |
| 21+ | 286.6 px | **640** | ±320 ✓ |

## KOL V (doğrulama) ROI'si

Takipçinin mevcut merkezinde, **A8'in adaptif kuralıyla** boyutlandırılır
(`R_sec(L_est)`, A8 merdiveni {640,320,160,80}). A8'de yayımlanmış mevcut
kuraldır; 3.2 için yeni bir kural üretilmemiştir. Δt = 0 (aynı kare).

Doğrulama aralığı **N = 5 ve N = 10** — iki değer önceden sabitlendi,
sonuca göre seçilmeyecek.

## Değişmeyecekler

`A9_KABUL_OLCUTU.md` (EK-1 dahil) aynen geçerlidir. 3.2 bir **teşhistir**;
hakem, recovery mekanizması, state machine ve kalıcı kod değişikliği
kapsam dışıdır.
