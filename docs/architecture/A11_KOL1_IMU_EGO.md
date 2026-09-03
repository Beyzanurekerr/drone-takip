# A11 KOL 1 — IMU EGO

> ### `KOMPOZİT YATAK YOK` · Gazebo · tek değişken: ego telafisi kaynağı
> **Rotasyon kanalı doğru; ötelenme dışlandığı için tam boru hattı her
> senaryoda daha kötü — beklenen ve ön-kayıtlı sonuç.**
> Görsel-tabanlı ego kapalı, IMU'dan **yalnızca rotasyon** telafisi
> (EK-2, ötelenme kasıtlı sıfır) 6 senaryonun **6'sında da** IoU'yu
> düşürdü (K3b **0/6**). En sert düşüş, ötelenmenin baskın olduğu
> **A4_irtifa**'da: IoU 0.293 → **0.021**, PSR p50 46.2 → **1.6**
> (fiilen rastgele). Ama rotasyonun **kendisi** — ayrı bir tamamlayıcı
> ölçümle — alt-piksel doğrulukta ve merkeze uzaklıktan bağımsız.

**Tarih:** 2026-09-03 · **Kod:** `gazebo/tani_a11_kol1.py`, `gazebo/a11_ortak.py:ImuEgo`
**Veri:** `cikti/a11_kol1.json` · **Ön-kayıt:** `A11_ONKAYIT.md` §3 (+ EK-2)
**Bütünlük:** `takip/*.py` md5 koşum öncesi = sonrası — **`izleyici.py`
değişmedi**; `tak.ego` örnek düzeyinde değiştirildi (`tak.ego = ImuEgo(...)`),
tıpkı A9'un `tak.kf` sarmalamasıyla aynı, invaziv olmayan enstrümantasyon.

---

## 1. Tasarım (EK-2'nin uygulanışı)

`ImuEgo`, `EgoMotion` ile **birebir arayüz** sağlar
(`guncelle(gri, hedef_kutu=None) -> (M, guven)`, `olcek_katsayisi` özelliği).
Farkı: `gri` **hiç kullanılmaz** — M tamamen IMU'dan kurulur.

1. **Bağlantı kalibrasyonu (bir kez, frame 0):**
   `R_kam_sabit = R_govde_imu(t0)⁻¹ · R_kamera_gerçek(t0)` — gerçek bir
   drondaki kamera-IMU dış kalibrasyonunun tek seferlik ölçümüne karşılık
   gelir. **Çalışma zamanında GT kullanılmaz.**
2. Kamera konumu **frame 0'ın konumunda sabitlenir** (öteleme dışlanıyor).
3. Her karede `R_cam_imu(t) = R_govde_imu(t)·R_kam_sabit` (IMU'nun en yakın
   200 Hz örneği, enterpolasyonsuz).
4. 3×3 örnekleme ızgarası `(C_sabit,R(t-1))→(C_sabit,R(t))` zemine
   düşürülüp geri izdüşürülür, görsel ego ile **aynı model sınıfına**
   (benzerlik dönüşümü, `cv2.estimateAffinePartial2D`+RANSAC) fit edilir.

---

## 2. Sahte hareket — rotasyon doğru, kalan neredeyse tamamen ötelenme

| senaryo | IMU sahte-ego p50 (px) | p95 (px) | güven ort |
|---|---|---|---|
| A1_taban (yalnız BAZ_HIZ, dönme yok) | **2.089** | **2.089** | 1.0 |
| A2_kucul | 0.484 | 1.495 | 1.0 |
| **A3_yaw** (BAZ_HIZ + ±30° yaw) | **2.089** | **2.089** | 1.0 |
| A4_irtifa (BAZ_HIZ + irtifa salınımı) | 1.086 | 2.034 | 1.0 |
| A5_kucul_yaw | 0.484 | 1.495 | 1.0 |
| A6_celdirici | 2.089 | 2.089 | 1.0 |

**A1 (dönme YOK) ile A3 (±30° dönme VAR) birebir aynı sonucu veriyor
(2.089 px, ondalığına kadar).** Bunun sebebi geometrik: görüntü merkezi,
kameranın kendi optik ekseni etrafındaki YAW dönüşünün **sabit noktasıdır**
— saf yaw, merkez noktasını **hiç kaydırmaz**. Yani merkez-noktası ölçütü
(KOL 0 ile karşılaştırılabilirlik için aynen korundu) **rotasyon kalitesine
kör**, neredeyse tamamen **dışlanan ötelenmeyi** ölçüyor.

**Ek doğrulama (merkez-dışı nokta, A3_yaw, x=0.15·W):** p50 **1.986 px**,
p95 **2.191 px** — merkezdekiyle (2.089/2.089) **neredeyse aynı**. Eğer
rotasyon telafisi kötü olsaydı, merkezden uzaklaştıkça hata **büyürdü**
(rotasyon hatası merkeze uzaklıkla ölçeklenir). Büyümedi.

> **Rotasyon kanalı IMU'dan doğru geliyor.** ~2 px'lik kalıntı, hemen hemen
> tamamen **kasıtlı dışlanan ötelenmedir**, rotasyon hatası değil.

**Genellenebilirlik sınırı (koşum sonrası fark edildi, ön-kayıt sonucuna
göre değiştirilmedi):** A11 ailesindeki **her** senaryo `_kam()`'ın
eklediği sabit `BAZ_HIZ` ötelenmesini taşır — yani "rotasyon-only" hipotezi
**hiçbir zaman tamamen ötelenmesiz bir senaryoda** sınanamadı. A1 ile A3'ün
birebir aynı çıkması bunu doğruluyor: fark yaratan şey dönme değil,
**her ikisinde de aynı olan BAZ_HIZ**. Saf-dönme izolasyonu için ötelenmesiz
(BAZ_HIZ=0) bir senaryo gerekir — **bu turda yok, sonraki tur adayı**.

---

## 3. Takipçi karşılaştırması — 1a (görsel) vs 1b (IMU)

| senaryo | 1a IoU | 1b IoU | 1a kopuş | 1b kopuş | 1a PSR p50 | 1b PSR p50 |
|---|---|---|---|---|---|---|
| A1_taban | 0.066 | 0.049 | 2 | 1 | 25.1 | 36.4 |
| A2_kucul | 0.090 | 0.028 | 1 | 2 | 60.0 | 25.0 |
| A3_yaw | 0.242 | 0.146 | 2 | 2 | 33.7 | 40.2 |
| **A4_irtifa** | **0.293** | **0.021** | 9 | 1 | **46.2** | **1.6** |
| A5_kucul_yaw | 0.055 | 0.048 | 1 | 2 | 41.2 | 64.4 |
| A6_celdirici | 0.066 | 0.049 | 2 | 1 | 9.3 | 36.2 |
| **toplam YK** | **1354** | **1167** | | | | |
| **toplam kopuş** | **17** | **9** | | | | |

**A4'te çöküş tam:** IMU'nun ihmal ettiği irtifa-kaynaklı ölçek/öteleme
kanalı burada baskın; PSR **1.6**'ya düşmesi (fiilen ayırt etmiyor) ve
kopuşun 9'dan 1'e düşmesi **iyileşme değil** — takipçi çoğu zaman
KAYIP/ARAMA'da kalıp bir daha güvenle "kilitli" görünmüyor (§4).

---

## 4. K-muhasebesi — okuma UYARISIYLA

**K3a** (kopuşlu azalma): 17 → 9, **geçer görünüyor**.
**K3b** (≥2 dizide IoU artışı): **0/6 — hiçbir dizide artış yok, açıkça
GEÇMİYOR.**
**K2** (toplam YK): 1354 → 1167, **toplamda azaldı**.

> **K2/K3a'nın "geçmesi" yanıltıcıdır.** A4'te YK'nin 100'den 5'e düşmesi,
> takipçinin DAHA İYİ kilitlenmesinden değil, **PSR çökmesi nedeniyle
> çoğu karede hiç "kilitli" bile diyememesinden** kaynaklanıyor (KİLİTLİ
> etiketi az düşünce o etikete bağlı sayaçlar da düşer — A10'da teşhis
> edilen ETİKET CONFOUND'unun bir başka görünümü). **IoU'nun her senaryoda
> düşmesi (K3b: 0/6) asıl hükümdür; K2/K3a'ya güvenilmemelidir.**

**K1/K6:** KOL 0'daki gibi **ölçülemez** — post-hoc sağlam referans yok
(1a'da da 6 senaryonun 6'sı KOPAN).

---

## 5. Hüküm

1. **Rotasyon kanalı (A3.9'un "koparan tek kanal" bulgusunun hedefi)
   IMU'dan doğru geliyor** — merkez-dışı doğrulama bunu gösterdi. Bu,
   KOL 1'in tek gerçek pozitif sonucudur.
2. **Ama ötelenmenin tamamen dışlanması, tam boru hattını HER senaryoda
   kötüleştirdi** — beklenen ve ön-kayıtlı (EK-2: "beklenen sonuç görsel
   egodan belirgin kötü"). Bu bir sürpriz değil, IMU'nun genel olarak kötü
   olduğunun kanıtı da değil — **rotasyon-only kapsamının doğal sonucu**.
3. **A11 ailesinin hiçbir senaryosu saf-dönme değil** (hepsi BAZ_HIZ
   taşıyor) — "rotasyon-only IMU" hipotezi tam izole edilmiş halde
   **sınanamadı**. §2'deki merkez-dışı nokta karşılaştırması bunun
   **dolaylı** bir kanıtıdır, kesin değil.
4. **K-muhasebesi kör kullanılırsa yanıltır** (§4) — durum-etiketine
   dayanan sayaçlar (K2, K3a), PSR çöktüğünde "iyileşme" gibi görünür;
   IoU (K3b) doğrudan ölçülen tek güvenilir sinyaldir ve **0/6**.

---

## 6. Sınırlar

Saf-dönme (BAZ_HIZ=0) senaryosu yok · IMU gürültüsüz (ön-kayıt notu) ·
tek koşum · yalnızca H0-tarzı (hakemsiz) takipçi — hakemli kollarla
etkileşimi ölçülmedi · `estimateAffinePartial2D`'nin RANSAC eşiği
varsayılan bırakıldı, ayarlanmadı · Pi Zero 2 W'ye ekstrapolasyon yok.

---

## 7. DUR

Kalıcı değişiklik yok. **Sıradaki aday (sınanmadı):** BAZ_HIZ=0 (yalnız
dönme) bir A7 senaryosu ekleyip rotasyon-only IMU'yu **temiz** izole
etmek — mevcut A1–A6 tabanı donduğu için bu **ayrı bir tur** gerektirir.
