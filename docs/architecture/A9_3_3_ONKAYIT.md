# A9 Deney 3.3 — ZAMANSAL KALICILIK · ÖN-KAYIT

**Yazıldığı tarih:** 2026-09-03 · **Deney 3.3 KOŞULMADAN ÖNCE yazıldı.**
Sonuçlara bakılıp değiştirilmeyecek. Değişmesi gerekirse gerekçeli yeni bir sürüm
eklenir, bu sürüm silinmez. Precedent: `A9_3_2_SECIM_KURALI.md`,
`A9_KABUL_OLCUTU.md`, `A3.9C_KABUL_OLCUTU.md`, `D1_kabul_olcutu.md`.

> ### `AÇIK ÇEVRİM` · `TEŞHİS` · `GT YALNIZCA OFFLINE ETİKETLEME`
> Hakem yok · recovery state machine yok · kalıcı kod değişikliği yok ·
> `takip/` md5 6/6 aynı · commit/push yok · `A9_KABUL_OLCUTU.md` **sabit**.

---

## 1. Soru

3.2 ölçtü: `min_G` KOL V'de Mod B için bugüne kadarki en güçlü sinyal
(AUC 0.895), **ama** ön-kayıtlı `G ≤ 1.0` kapısı sağlam dizilerde %48 yanlış
alarm veriyor. 3.2 hükmü: *"bir ilkel, iki ayrı çalışma noktası"* — ve KOL V'nin
çalışma noktası **seçilmemiş** durumda.

3.3 bu çalışma noktasını **eşiği oynatarak değil, ZAMANSAL KALICILIK ile**
arıyor.

**Eşik sabittir: `G ≤ 1.0`.** 3.2'nin kuralı (`A9_3_2_SECIM_KURALI.md`) aynen
geçerlidir; `G`'nin tanımı, normalizasyon ölçekleri (`MAX_HIZ = 35`, `2.6`) ve
kapı değeri **değiştirilmemiştir**.

**Tek değişken:** `k` = kaç ardışık doğrulama noktasında ihlal görülmesi
gerektiği. `k ∈ {1, 2, 3, 5}` — dört değer burada, koşumdan önce sabitlendi.
`k = 1` 3.2'nin bildirdiği çalışma noktasıdır ve **kontrol kolu**dur.

## 2. Yatak — 3.2'nin KOL V yatağı, yeniden koşum YOK

3.3, 3.2'nin **saklanmış KOL V kayıtlarını** yeniden kullanır
(`cikti/a9_takipci_merkez_recovery.json` → `phase3_recovery.experiment_3_2.kol_v`).

**Dedektör yeniden koşturulmayacak.** Gerekçe: 3.3'ün değişkeni `k`, dedektör
çıktısı değil. Aynı `min_G` serisi üzerinde farklı bir sayaç uygulanıyor.
Yeniden koşum yalnızca gürültü ekler ve 3.2 ile bit düzeyinde aynılığı bozar.
Bu bir **kısıt olarak** kabul edilmiştir: 3.3, 3.2 yatağının dışına çıkamaz.

| | |
|---|---|
| diziler | 6 (kopan: 117/23 · 268/31 · 339/49 — sağlam: 137/12 · 305/5 · 182/127) |
| seviyeler | 30×12 · 20×10 · 15×7 · 10×5 · 8×5 |
| kareler | `N_KARE = 60` (t = 1…59) |
| noktalar | yalnızca `durum == KİLİTLİ` **ve** kutu var olan kareler |
| model | **birincil A5_baseline**; `A6_uavdt_visdrone` ayrıca raporlanır, karar A5 üzerinden |
| doğrulama periyodu | **N = 5** (birincil) ve **N = 10** (`t % 10 == 0` alt kümesi) — 3.2'nin iki değeri |
| ROI | 3.2'deki gibi A8 adaptif kuralı `R_sec(L_est)`, Δt = 0 |

Hücre başına doğrulama noktası: N = 5'te **en çok 11**, N = 10'da **en çok 5**.
Bu sayı yataktan gelir, sonuçtan değil; §5'teki eşik türetmesinde kullanılır.

## 3. Sayaç tanımı

Doğrulama noktaları `t` sırasına göre gezilir. Her noktada:

```
ihlal(t)  =  (min_G(t) > 1.0)            # kapı 3.2'den, DEĞİŞMEDİ
kanıt yok =  o noktada dedektör hiç aday üretmedi (min_G tanımsız)
```

- **ihlal** → `sayaç += 1`
- **ihlal değil** → `sayaç = 0`
- **kanıt yok** → **politikaya bağlı** (§4)

`tetikleme` (yükselen kenar) = sayacın **ilk kez** `k`'ya ulaştığı nokta.
Sayaç `k`'nın üstünde kaldığı sürece **alarm durumu** sürer ama yeni tetikleme
sayılmaz; sayaç sıfırlanıp yeniden `k`'ya ulaşırsa yeni tetiklemedir.

## 4. "Kanıt yok" politikası — ikisi de ölçülecek

3.2 ölçtü: 8×5'te doğrulama noktalarının yarısına yakınında hiç aday yok.
Sayacın bunu nasıl işlediği bir **tasarım kararıdır** ve sonuca bakılarak
seçilemez. İki politika **koşumdan önce** tanımlandı, **ikisi de** raporlanacak:

| politika | kural | arkasındaki varsayım |
|---|---|---|
| **SIFIRLA** | kanıt yok → `sayaç = 0` | kanıt yokluğu, arıza kanıtı değildir; şüpheyi temizler |
| **DONDUR** | kanıt yok → sayaç **değişmez** (noktayı atla) | kanıt yokluğu nötrdür; ihlal serisini kesmez |

Üçüncü bir olasılık (kanıt yok → ihlal say) **bilerek kapsam dışıdır**: bu,
dedektör körlüğünü takipçi arızası saymak olurdu ve `G ≤ 1.0` kapısının
tanımına aykırıdır. Sonuçlara bakılıp eklenmeyecektir.

## 5. Kabul — sağlam dizilerde yanlış alarm ≤ **%X**

### 5.1 X nereden geliyor (K6 mantığı, sonuçtan değil)

`A9_KABUL_OLCUTU.md` **K6**: *"Recovery hiç tetiklenmeyen hücrelerde (sağlam
diziler dahil) IoU ve merkez hatası K1'deki sınırlar içinde kalacak."*
Sağlam bir hücrede yanlış tetikleme, o hücreyi K6'nın koruma alanının **dışına**
çıkarır. Dolayısıyla X, "kaç yanlış tetikleme K1'i hâlâ sağlar" sorusunun
cevabıdır. Zincirin her halkası **var olan** bir sabit ya da **yayımlanmış** bir
ölçümdür; yeni sabit uydurulmadı:

| halka | değer | kaynak |
|---|---|---|
| hücre başına izin verilen ortalama IoU düşüşü | **0.03** | `A9_KABUL_OLCUTU.md` K1b |
| hücre uzunluğu | **59 kare** | yatak, `N_KARE = 60` |
| bir yanlış recovery'nin süresi (p95) | **5.8 kare** | 3.2 §5, ölçülmüş |
| recovery sırasında kare başına kaybedilen IoU | **≥ 0.5** | `DOGRU_IOU`, mevcut sabit — doğru kilitli kare tanımı gereği en az bu kadardır |

```
hücre başına izin verilen IoU-kare kaybı = 0.03 × 59            = 1.77
bir yanlış tetiklemenin bedeli            = 5.8 × 0.5           = 2.90
hücre başına izin verilen yanlış tetikleme = 1.77 / 2.90        = 0.61
```

Oran biçimi, hücre başına nokta sayısına bölünerek elde edilir:

| | nokta/hücre | **X** |
|---|---|---|
| **N = 5** (birincil) | 11 | **%5.5** |
| N = 10 | 5 | **%12.2** |

X'in N ile değişmesi bir tutarsızlık değildir: sabitlenen büyüklük **hücre
başına 0.61 yanlış tetiklemedir**; yüzde onun okunabilir biçimidir.

### 5.2 Ölçüm tanımı

- **yanlış tetikleme** = sağlam dizi hücresinde, `takipci_iou ≥ 0.5` olan bir
  noktada gerçekleşen tetikleme (yükselen kenar).
  *Takipçinin zaten bozuk olduğu noktada alarm yanlış değildir.*
- **yanlış alarm oranı** = yanlış tetikleme sayısı ÷ sağlam dizilerdeki
  `takipci_iou ≥ 0.5` olan doğrulama noktası sayısı.
- **Kabul:** yanlış alarm oranı **≤ X**.

### 5.3 X'in iyimser olduğunun peşinen kabulü

Bedel hesabı, yanlış recovery'nin **5.8 karede toparlandığını** varsayar. 3.1/3.2
ölçtü ki epizotların **%75'i hiç toparlanmıyor**; toparlamayan bir yanlış
tetiklemenin bedeli sınırsızdır. Bu yüzden X **iyimser bir üst sınırdır** ve
yanına **katı eşlikçi ölçüt** raporlanır:

> **Katı ölçüt:** sağlam dizilerde **hiçbir** hücrede yanlış tetikleme olmaması
> (hücre düzeyi, sıfır tolerans). K6'nın harfi harfine okunuşu budur.

İki ölçüt ayrı ayrı raporlanır; biri diğerinin yerine geçmez.

### 5.4 k seçim kuralı (koşumdan önce)

1. Yanlış alarm oranı ≤ X koşulunu sağlayan `k`'lar aday havuzudur.
2. Havuzdaki en yüksek **Mod B yakalama oranı**.
3. Eşitlik → daha küçük **medyan yakalama gecikmesi**.
4. Eşitlik → daha küçük `k` (daha az gecikme riski).

**Havuz boş çıkarsa sonuç "çalışma noktası YOK"tur.** Bu meşru bir sonuçtur;
X, k listesi ya da kapı bu durumda **ayarlanmayacaktır**.

## 6. Mod B yakalama ve gecikme tanımları

**Mod B hücreleri** `phase2_break_detection.mode_b.hucreler`'den alınır
(Aşama 2'de, 3.3'ten bağımsız olarak etiketlendi) — 4 hücre.

| terim | tanım |
|---|---|
| **geçiş karesi** | GT'ye göre yanlış hedefe geçilen kare = o hücredeki **ilk recovery epizodunun** `bas_t`'si (EK-1: `IoU < 0.2`, ≥ 5 ardışık kare). Aşama 2'nin `kopus_karesi` değeri karşılaştırma için ayrıca yazılır. |
| **yakalama** | geçiş karesinde **veya sonrasında** gerçekleşen tetikleme |
| **yakalama gecikmesi** | `ilk kalıcı ihlal karesi − geçiş karesi` (kare) |
| **erken uyarı** | geçiş karesinden **önce** gerçekleşen tetikleme; ayrı sayılır, yanlış alarm sayılmaz (o hücre gerçekten kopuyor) |
| **kaçırma** | hücrede hiç tetikleme yok |

Gecikme için **üst sınır eşiği TANIMLANMAMIŞTIR** — bilerek, EK-1'deki aynı
gerekçeyle: süre bir **dağılım olarak** raporlanacak.

## 7. Ölçülecekler (hepsi her `k` × politika × N için)

1. Mod B yakalama oranı · gecikme dağılımı (kare)
2. Sağlam dizilerde yanlış alarm oranı + katı ölçüt (hücre düzeyi)
3. "Kanıt yok" noktalarının sayacı nasıl etkilediği — **SIFIRLA vs DONDUR farkı**
4. 3.0'ın **5 KİLİTLİ-başlangıçlı epizodu**: hangi `k`'da ilk uyarı, hangi karede
5. **339/49 · 15×7** (kanonik Mod B, geçiş `bas_t = 34`): `k`'ya göre gecikme
6. **LOSO**: her dizi teker teker çıkarılıp `k` seçimi tekrarlanır; seçim tek
   diziye bağlıysa açıkça yazılır (3.1/3.2'de 117/23 bağımlılığı çıkmıştı)

## 8. Geçerlilik denetimi (koşumun ilk adımı)

3.2 kayıtlarının epizot tabanıyla aynı takipçi izlerinden geldiği **sınanacak**:
bir epizodun içine düşen KOL V noktalarının `takipci_iou` değerleri `< 0.2`
olmalıdır. Sağlanmazsa 3.3 **durur** ve sonuç raporlanmaz.

## 9. Değişmeyecekler

`A9_KABUL_OLCUTU.md` (EK-1 dahil) ve `A9_3_2_SECIM_KURALI.md` aynen geçerlidir.
3.3 bir **teşhistir**; hakem, recovery mekanizması, state machine, eşik ayarı ve
kalıcı `takip/` değişikliği kapsam dışıdır. Çıktı anahtarı:
`phase3_recovery.experiment_3_3`.
