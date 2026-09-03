# Deney 4J — DCF merkez biası cross-source doğrulama

## 1. Deney amacı

Deney 4B/4G'de bulunan şu hipotezi, artık 4I ile güvenilir sayılan **iki
bağımsız gerçek VisDrone dizisinde** sınamak:

> "DCF merkez biası, şablon öğrenmesiyle ilişkili olarak zaman içinde
> sistematik biçimde büyür ve bu ilişki gerçek veride de genellenebilir."

Optimizasyon yok, parametre taraması yok. `takip/` hiç değiştirilmedi
(md5 6/6 Deney 2 ile birebir, koşum öncesi ve sonrası). Commit/push yok.

**Baseline kontrolü:** ölçer, mevcut baseline'ı birebir üretti —
117/23 IoU 0.701 / merkez 5.51, G3_agresif IoU 0.760 / merkez 3.81 —
yani enstrümantasyon davranış-nötr.

## 2. Kullanılan veri dizileri

| rol | dizi | kare | IoU | kilit | drift | 4I hükmü |
|---|---|---|---|---|---|---|
| birincil | **117/23** | 342 | 0.701 | %100 | yok | GÜVENİLİR |
| birincil | **137/12** | 208 | 0.548 | %94.6 | 75 | GÜVENİLİR |
| destekleyici | 305/5 | 116 | 0.502 | %83.0 | 110 | SINIRDA |
| Gazebo referansı | G3_agresif | 293 | 0.760 | %100 | yok | — |

305/5 tek başına karar verdirici sayılmadı.

## 3. Kodda gözlemlenen gerçek pipeline noktaları

Hepsi grep ile doğrulandı; tahmin yok.

| ne | gerçek yer |
|---|---|
| DCF peak | `cekirdekler.py:175` `_yanit` → `_tepe(r, self.N, merkez, w, h)` (tanım `:321`); `ara` döndürür, `izleyici.py:_takip_adimi`'nda `yeni` |
| şablon durumu | `cekirdekler.py:168-169` (`baslat` → `self.A`, `self.B`), `:215` (`ogren` → `A = (1−lr)A + lr(G·conj F)`) |
| lr uygulama | `izleyici.py:315` `lr = 0.125 if self.boyut.max() > 18 else 0.04`; `:316` `cekirdek.ogren(..., lr)` — çağrı, çekirdeğin `self.lr`'sini **ezer** |
| GT kaynağı | `veri/visdrone.py:160` `Kare(gt=gt, gorunur=e is not None)` |
| ego / M | `izleyici.py:249` `cekirdek.ego_guncelle(M)` |
| hedef ↔ arka plan ayrımı | `izleyici.py:255` `ongoru = M[:,:2] @ _onceki_merkez + M[:,2]`; burada GT ile kuruldu: bağıl akış = `M(gt_önceki) − gt_şimdi`, hedef hareketi = `gt_şimdi − gt_önceki` |
| rafine merkezi | `izleyici.py:565` `yeni_c = r[:2] + r[2:]/2` |

**Gözlemlenemeyen nokta:** `lr` bir baseline koşumunda **sabittir** (ölçüldü:
dört kaynakta da 0.125). Bu yüzden **F testi (lr ↔ şablon değişim hızı)
gözlemsel olarak hesaplanamaz** — varyans yok. Bu ilişki yalnızca müdahaleyle
sınanabilir ve Deney 4H'de sınandı.

## 4. Ölçüm yöntemi

`gazebo/tani_crossbias.py` — `HedefTakip` alt sınıfı; `cekirdek.ara`,
`cekirdek.ogren`, `cekirdek.ego_guncelle` ve `_boyut_tazele` saydam sarılır.
Kare başına 16 alan yazılır (GT/DCF merkezleri, dx/dy, hata, PSR, lr,
kısa/kümülatif şablon değişimi, hedef hareketi, bağıl akış, ego, GT ve DCF
kutu boyutları, rafine hatası). Öğrenme sinyalleri koddan türetildi:

    kisa = ||A_t − A_{t−1}||_F / ||A_t||_F      (bir adım)
    kum  = ||A_t − A_0||_F   / ||A_0||_F        (kilitten bu yana)

## 5. 117/23 sonuçları

| | değer |
|---|---|
| \|e\| p50 / p95 / ort | 5.42 / 14.66 / 6.42 px |
| dx ort / dy ort | **−4.85** / −1.86 |
| dx çeyrekler (başlangıç→geç) | **−0.02 → −4.84 → −8.66 → −5.85** |
| A: kum ~ \|hata\| | **P +0.56 / S +0.55** |
| B: kum ~ dx | **P −0.53 / S −0.58** |
| D: bağıl akış ~ dx | P +0.28 / S +0.28 |
| E: PSR ~ \|hata\| | P +0.28 / S +0.37 |
| G: hedef hareketi ~ dx | P +0.02 / S −0.05 |

Bias sıfıra yakın başlıyor, büyüyor, geç dönemde bir miktar geri geliyor.
Drift yok, bu yüzden tüm 342 kare geçerli.

## 6. 137/12 sonuçları

| | değer |
|---|---|
| \|e\| p50 / p95 / ort | 5.21 / 57.90 / 13.85 px |
| dx ort / dy ort | **−10.27** / −3.16 |
| A: kum ~ \|hata\| (tüm) | **P +0.83 / S +0.68** |
| **A (drift öncesi, n=68)** | **P +0.73 / S +0.71** |
| B: kum ~ dx (tüm) | **P −0.82 / S −0.49** |
| **B (drift öncesi)** | **P −0.68 / S −0.58** |
| D: bağıl akış ~ dx | **P −0.40 / S −0.58** |
| E: PSR ~ \|hata\| | P −0.24 / S −0.39 |
| G: hedef hareketi ~ dx | P +0.26 / S +0.49 |
| dx çeyrekler (**drift öncesi**) | **+0.66 → +1.92 → −3.95 → −18.23** |

**Aykırı dönem kontrolü:** tüm koşumda dx çeyrekleri −0.60 / −35.17 / −4.51 /
−0.78 ile tek bir sıçrama içeriyordu ve o dönem 75. karedeki drift'e denk
geliyor. Drift sonrası kareler atıldığında ilişki **ayakta kalıyor**
(A +0.83 → +0.73, B −0.82 → −0.68) ve dx serisi 68 karede **tekdüze**
büyüyor. Yani ilişki tek aykırı dönem tarafından taşınmıyor.

## 7. 305/5 destekleyici sonuç

| | tüm | drift öncesi (n=103) |
|---|---|---|
| A: kum ~ \|hata\| | P +0.23 / S −0.22 | **P −0.93 / S −0.70** |
| B: kum ~ dx | P −0.33 / S −0.91 | **P −0.81 / S −0.89** |
| dx çeyrekler (drift öncesi) | — | +0.69 → +0.10 → −1.10 → −2.00 |

**Karışık:** B birincillerle aynı yönde ve güçlü (−0.81), ama **A işaret
değiştiriyor** (−0.93). 4I'da zaten "sınırda" işaretlenmişti (DCF karesi oranı
0.63, yalnızca 116 kare). Karar verdirici sayılmadı.

## 8. Cross-source karşılaştırma

| test | 117/23 | 137/12 | aynı yön? | 305/5 | G3_agresif |
|---|---|---|---|---|---|
| **A** kum ~ \|hata\| | **+0.56** | **+0.73** | ✅ | −0.93 ✗ | +0.67 |
| **B** kum ~ dx | **−0.53** | **−0.68** | ✅ | −0.81 ✅ | −0.67 |
| C kum ~ dy | −0.19 | −0.58 | zayıf | +0.39 | −0.06 |
| D bağıl akış ~ dx | **+0.28** | **−0.40** | ❌ **ters** | +0.72 | +0.33 |
| E PSR ~ \|hata\| | **+0.28** | **−0.24** | ❌ **ters** | +0.15 | −0.19 |
| G hedef hareketi ~ dx | +0.02 | +0.26 | zayıf/tutarsız | −0.85 | +0.13 |
| F lr ~ kısa değişim | — | — | **ölçülemez** (lr sabit) | — | — |

Ve dx zaman serisi (drift öncesi) her üç gerçek dizide de **sıfıra yakın
başlayıp negatife büyüyor**.

### Zaman-lag analizi

`d(kum)` ile `d|hata|` arasında çapraz korelasyon (lag −3…+3):

| kaynak | en güçlü değer |
|---|---|
| 117/23 | +0.04 (lag +3) — düz |
| 137/12 | +0.23 (lag −3) |
| 305/5 | −0.20 (lag +3) |
| G3_agresif | +0.18 (lag 0) |

**Belirgin bir öncelik yok.** İlişki eşzamanlı; "şablon değişimi önce gelir,
bias sonra artar" **gösterilemedi**. Bu açıkça belirtilmelidir.

## 9. 4G hipotezinin yeniden değerlendirilmesi

4G, kümülatif şablon değişimi ↔ bias ilişkisini dört kaynakta pozitif bulmuş ve
"Faz C'nin ilk genellenen ilişkisi" demişti. 4H'nin müdahalesi bunu 117/23'te
**çürütmüştü** (lr düşürünce bias büyüdü).

Bu tur ikisini uzlaştırıyor:

* **İlişki (asosiyasyon) gerçekten genelleniyor** — iki bağımsız gerçek dizide
  aynı yön, drift sonrası kareler atıldığında da ayakta.
* **Ama nedensel okuma hâlâ geçersiz.** 4H'de `lr` düşürüldüğünde 117/23'te
  kümülatif değişim neredeyse aynı kaldı (0.868 vs 0.942) ama bias **büyüdü**
  (−6.52 vs −4.85). Yani `kum` ile `lr` gerçek veride birbirinden ayrışıyor;
  `kum` üzerinden kurulan ilişki `lr` koluyla hareket ettirilemiyor.
* Bu turun lag analizi de zamansal öncelik göstermiyor.

Sonuç: 4G'nin **korelasyon bulgusu doğrulandı**, **mekanizma iddiası
doğrulanmadı**.

## 10. Elenen alternatif açıklamalar

| açıklama | durum | kanıt |
|---|---|---|
| bağıl arka plan akışı yönü belirliyor | **ELENDİ** | D: 117/23 +0.28, 137/12 **−0.40** — iki birincilde ters |
| PSR / güven düşüşü | **ELENDİ** | E: +0.28 vs −0.24 — ters |
| hedefin kendi görüntü hareketi | **ELENDİ** | G: +0.02 vs +0.26, 305/5'te −0.85 — tutarsız ve 117/23'te sıfıra yakın |
| dy ekseni (dikey bileşen) | **elendi** | C: −0.19 / −0.58 / +0.39 — tutarsız |
| tek aykırı dönemin taşıması | **elendi** | 137/12 drift öncesi 68 karede ilişki ayakta (+0.73) |

Ayakta kalan tek tutarlı ilişki: **kümülatif şablon değişimi ↔ dx** (dört
kaynakta da negatif, −0.53 … −0.81).

## 11. Sonuç

Karar kuralının dört koşulu, hipotezin **asosiyasyon** biçimi için:

| koşul | durum |
|---|---|
| 117/23 ve 137/12 aynı temel ilişkiyi gösteriyor | ✅ A +0.56/+0.73, B −0.53/−0.68 |
| ilişkinin yönü aynı | ✅ |
| tek aykırı dönem tarafından taşınmıyor | ✅ 137/12 drift öncesi n=68'de ayakta |
| hedef hareketi / PSR daha güçlü açıklama sunmuyor | ✅ ikisi de işaret tutarsız |

> ## **ASOSİYASYON: GENELLENDİ**
> ## **MEKANİZMA: GENELLENMEDİ**

Bias'ın kümülatif şablon değişimiyle birlikte büyümesi artık **iki bağımsız
gerçek dizide** doğrulanmış durumdadır — Faz C'de ilk kez. Ancak:

* zamansal öncelik gösterilemedi (lag ≈ 0),
* 4H'nin müdahalesi nedensel yönü gerçek veride **çürütmüştü**,
* destekleyici dizi (305/5) A testinde ters işaret veriyor.

Bu yüzden "gerçek veride güvenilir **mekanizma**" henüz kurulamadı; kurulan şey
güvenilir bir **ilişkidir**.

## 12. Bir sonraki deney için TEK aday

`lr` kolu 4H'de kapandı. Ama bu tur, kodda **ölçülmüş bir asimetriyi** açığa
çıkardı:

```
izleyici.py:316   self.cekirdek.ogren(bgr, gri, self.kf.konum, self.boyut, lr)
                  ^^^ KOSULSUZ

izleyici.py:325   if self._hareketli and self.benzerlik >= self.kimlik_esik:
izleyici.py:326       self.imza.guncelle(bgr, gri, self.kutu, lr=0.03)
                  ^^^ KAPILI
```

Aynı `KILITLI` dalında **imza** güncellemesi iki koşulla kapılı, **DCF şablonu**
güncellemesi ise koşulsuz. Kodun kendi yorumu bu kapının neden konduğunu
söylüyor: *"bu kapı olmadan 182/127'de yanlış kilit oranı %43.6, kapıyla %9'a
iniyor"*.

> ### Tek aday müdahale
> **`izleyici.py:316`'daki DCF şablon güncellemesini, satır 325'te imza için
> zaten kullanılan kapının aynısına bağla.**

Neden bu:

* **Yeni eşik yok** — `self._hareketli`, `self.benzerlik`, `self.kimlik_esik`
  hepsi mevcut ve zaten her karede hesaplanıyor.
* **`lr`'ye dokunmuyor** — 4H'de çürütülen kolu kullanmıyor. Öğrenmenin
  *hızını* değil, *ne zaman* olacağını değiştiriyor; yani "arka planı soğurma"
  ile "gerçek görünüm değişimine uyum" ayrımını (4H'nin işaret ettiği ikilem)
  doğrudan hedefliyor.
* **Depo içi kanıt var** — aynı kapı imza tarafında yanlış kilit oranını
  %43.6 → %9'a indirmiş.
* Tek satırlık koşul; patlama yarıçapı `KILITLI` dalıyla sınırlı.

**Uygulanmadı.** Uygulanırsa: karar **117/23 + 137/12 birlikte** verilmeli;
`lr` gibi bu da tüm senaryoları etkiler, dolayısıyla "30/32 birebir" ölçütü
uygulanamaz ve tasarımda baştan "regresyon yok" biçiminde tanımlanmalıdır;
182/127, 268/31, 339/49 ve sim test2/test3 karar dışı tutulmalıdır (4I ve
Deney 1).
