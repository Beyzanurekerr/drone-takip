# A11 KOL 3 — UÇUŞ GEOMETRİSİ (spesifikasyon deneyi)

> ### `KAPALI ÇEVRİM` · `CANLI gz sim` · `KOMPOZİT YATAK YOK`
> **Koruma modu bir kez bile tetiklenmedi — ama hedef karelerin %75'inde
> gerçekten 25 px'in altındaydı.** Kontrol yasası **takipçinin kendi
> boyut tahminine** bakıyordu ve o tahmin, gerçek hedef küçülmeye devam
> ederken **donup sonra 2.5 kat şişerek** gerçeklikten koptu. Bu,
> KOL 0'ın DCF-doku-kayması bulgusunun **canlı bir kontrol kararını
> tamamen geçersiz kıldığının** doğrudan kanıtıdır.

**Tarih:** 2026-09-03 · **Kod:** `gazebo/tani_a11_kol3.py`
**Veri:** `cikti/a11_kol3.json` · **Ön-kayıt:** `A11_ONKAYIT.md` §5 (+ EK-3)
**Bütünlük:** `takip/*.py` **değişmedi** — hakem kullanılmadı (EK-3 kapsam
kararı), yalnızca saf `HedefTakip()`.

---

## 1. Kurulum

**Canlı `gz sim`** (kayıt-sonra-oynat değil — bu kol offline oynatmayla
yapılamaz, ön-kayıt §5). Dünya **A2_kucul'un DEĞİŞMEMİŞ dünyası**
(SDF/araç/zemin aynı); tek fark `kam_profil`'in EK-3'ün kontrol yasasıyla
sarmalanması:

```
L_est = max(tak.boyut)                       # takipçinin KENDİ tahmini, GT DEĞİL
vz = -vz_taban  eğer L_est < 25 px  else  vz_taban
```

Takipçi, her kamera karesinde CANLI çalıştırıldı (`tak.guncelle(bgr)`),
`L_est` her karede güncellendi ve **bir sonraki poz örneğinde** yayınlanan
`cmd_vel`'i belirledi. **Hakem kullanılmadı** (EK-3: dedektör Gazebo'da
zaten kör, KOL 0). 500 kare toplandı (~11 saniye duvar saati — kayıt
modundan çok daha hızlı, disk yazımı yok).

---

## 2. Ana bulgu — koruma modu hiç tetiklenmedi

| ölçüt | değer |
|---|---|
| **koruma modu oranı** (L_est < 25, takipçinin kendi tahmini) | **%0.0** |
| **gerçek hedef < 25 px oranı** (irtifadan hesaplanan GT_L) | **%74.8** |
| **gerçek hedef < 20 px oranı** | **%63.6** |
| ARAMA/KAYIP benzeri epizot (≥5 ardışık kare) | **4** |

> **Gerçek hedef karelerin dörtte üçünde 25 px eşiğinin altındaydı ve
> kontrol yasası bunu bir kez bile fark etmedi.**

---

## 3. Kök neden — takipçinin boyut tahmini DONDU, sonra ŞİŞTİ

| t | L_est (takipçi) | GT_L (gerçek, irtifadan) | irtifa | durum |
|---|---|---|---|---|
| 81 | 43.80 | 32.25 | 71.3 m | KİLİTLİ |
| 106 | **43.80** (aynı) | 28.19 | 81.6 m | KİLİTLİ |
| 131 | **43.80** (aynı) | 25.03 | 91.9 m | KİLİTLİ |
| **132** | **43.80** | **24.91 — eşiği GEÇTİ** | 92.3 m | KİLİTLİ (koruma **tetiklenmedi**) |
| 156 | **43.80** (aynı) | 22.51 | 102.2 m | KİLİTLİ |
| 181–206 | **43.80** (aynı) | 20.46 → 18.72 | 112–123 m | KİLİTLİ |
| **231** | **121.08** (+2.5×, ANİ SIÇRAMA) | 17.29 | 133.0 m | KİLİTLİ |
| 256–481 | 55–112 (şişkin, GT'nin 5–10 katı) | 16.05 → 9.75 | 143–236 m | KİLİTLİ/ARAMA karışık |

**İki ayrı arıza aşaması:**

1. **t=81–206: `L_est` tam olarak DONDU** (`43.80000305175781`, bit
   düzeyinde aynı, 5 ayrı ölçüm noktasında) — takipçinin boyut güncelleme
   mekanizması (`_boyut_tazele` / `_boyut_sinirla`) gerçek küçülmeyi takip
   etmeyi bıraktı. **Gerçek hedef tam bu pencerede (t=132) 25 px eşiğini
   geçti** ve takipçi hâlâ 43.8 px raporluyordu.
2. **t≈231: ani +2.5× sıçrama** (43.8 → 121.1) — KOL 0 §3'te görsel olarak
   teşhis edilen **DCF'nin statik bir doku özelliğine kayması** ile aynı
   imza (ani, büyük, kalıcı boyut şişmesi + PSR'nin buna rağmen "kilitli"
   kalması). Takipçi bu şişkin tahminle **koşumun sonuna kadar** devam
   ediyor; 4 ARAMA epizodu (10, 22, 19, 10 kare) geçici toparlanma
   girişimleri ama hep aynı şişkin ölçeğe geri dönüyor.

> **Kontrol yasası doğru yazılmıştı (EK-3) ama beslendiği sinyal —
> takipçinin kendi `boyut` tahmini — KOL 0'da zaten teşhis edilen aynı
> arızayı taşıyordu.** Bu, "spesifikasyon" ile "algı" arasındaki ayrımı
> keskin biçimde gösteriyor: kural (`<25px → yaklaş`) kusursuz olsa bile,
> **algı katmanı kuralın referans aldığı büyüklüğü doğru ölçemezse kural
> hiç işlemez.**

---

## 4. Bu, "algı deneyi değil spesifikasyon deneyi" çerçevesine ne yapıyor

Ön-kayıt KOL 3'ü bilerek bir **algı** deneyi değil **spesifikasyon** deneyi
olarak çerçeveledi. Sonuç bu çerçeveyi **doğruluyor ama ters yönden**:
spesifikasyonun kendisi (eşik, tetikleme, yön) hiçbir sorun çıkarmadı —
**spesifikasyonun VARSAYDIĞI bir girdinin (güvenilir boyut tahmini)
gerçek dünyada (Gazebo'da) bulunmadığı** ortaya çıktı. Bu, ilerideki her
spesifikasyonun (KOL 3'ün kuralı dahil) **bağımsız, doğrulanmış bir
büyüklüğe** dayanması gerektiğini gösteren somut bir örnektir — tıpkı
`KALICI_KISITLAR.md` K6'nın "tetikleyici sabiti eylemin yazdığı durumdan
türetilemez" ilkesinin bir varyasyonu: **burada sorun eylemin kendi
yazdığı bir durum değil, ALGININ kendi hatasıydı — ama sonuç aynı: kural
kendi girdisine güvenemedi.**

---

## 5. Sınırlar

**GT kutusu yaklaşıktır** — canlı koşum offline enterpolasyon
kullanmıyor (Kayitci'nin senkron mantığı burada yok), `GT_L_yaklasik`
yalnızca irtifadan (`500·4.6/irtifa`) hesaplandı, gerçek projeksiyon
kutusu değil · **tek koşum** (RTF/timing canlı bağlantıya bağlı, tekrar
edilmedi) · yalnızca **A2_kucul** dünyası (A5_kucul_yaw ile birlikte
denenmedi) · "koruma modu"nda hakem yokluğunun etkisi (EK-3 kapsam
daralması) ayrı ölçülmedi · kontrol yasasının **kendisi** hiçbir zaman
gerçek anlamda sınanamadı (tetiklenmediği için "yaklaşma çalışıyor mu"
sorusu **açık kaldı**) · ilk kilit kaba bir kutuyla yapıldı (görüntü
merkezi + irtifa-türetilmiş boyut), rafine_kutu'ya güvenildi.

---

## 6. DUR

Kalıcı değişiklik yok.

**Sıradaki aday (sınanmadı, iki ayrı yön):**
1. **Kontrol yasasını GT_L_yaklasik'in kendisiyle (irtifa üzerinden,
   takipçiden bağımsız) tetiklemek** — gerçek drone'da irtifa barometre/
   IMU'dan gelir, takipçiden değil; bu KOL 1'in "rotasyon IMU'dan doğru"
   bulgusuyla da uyumlu bir sonraki adım olurdu.
2. **KOL 0'ın DCF-doku-kayması arızasını önce düzeltmek** — KOL 3'ün
   gösterdiği gibi, bu arıza yalnızca açık-çevrim IoU'yu değil, **üzerine
   kurulacak her canlı kontrol kararını** sessizce geçersiz kılıyor.
