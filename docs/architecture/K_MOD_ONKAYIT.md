# K-MOD — Küçük Hedef Modu (8–20 px), Y1 dünyası (ön-kayıt + K1 sonucu)

Talimat (2026-09-04, birebir):

```
K-MOD — KÜÇÜK HEDEF MODU (8–20 px), Y1 dünyası.

K1 — Y2 seçim (açık çevrim, 1 oturum):
  KOL 2 adayları: S1 Kalman öngörüsüne yakınlık (d_norm),
  S2 S1 + zamansal kalıcılık (aynı hücrede ≥k/N biriktirme),
  S3 S2 + dedektör doğrulaması (adayda R=80 ROI, A6).
  Yatak: Y1_A7_kucuk (20 px) + yeni Y1_A8_cok_kucuk (8–10 px,
  hareketli hedef, 2 hareketli çeldirici). Ölç: doğru aday
  seçim oranı, yanlış seçim, çekimser, kanıt-yok.
  Kapı: 8×5'te doğru seçim ≥0.8, yanlış ≤0.05.

K2 — kapalı çevrim (1–2 oturum, yalnız K1 geçtiyse): [bu turda çalışılmadı]
K3 — demoya entegrasyon (yarım oturum): [bu turda çalışılmadı]

GÖRSEL ÇIKTI: [aşağıda, gazebo/gorsel_uret.py]
```

`takip/*.py` bu turda da DEĞİŞMEDİ (K1 açık çevrim, `gazebo/tani_kmod_k1.py`
+ `gazebo/kmod_k1_gorseller.py` içinde, hareket adayları
`takip/tespit.py:HareketTespit` üzerinden — mevcut, değişmeyen fonksiyon).

## Yataklar

`gazebo/senaryolar.py`: `Y1_A7_kucuk` (sabit 115.0 m → ~20 px), `Y1_A8_cok_kucuk`
(sabit 255.6 m → ~9 px, 8–10 px bandı). İrtifa formülü A11_IRTIFA0/1 ile
AYNI konvansiyon (`ODAK_PX·4.6/irtifa`) — A11 ailesiyle karşılaştırılabilir
kalsın diye, mesh'in gerçek 4.0011 m'sinden yeniden türetilmedi.

**Konum sorunu bulunup düzeltildi:** A1–A6'nın `HEDEF_X0=-24` civarındaki
konumu, Y1.2'de yama merkezinin operasyon alanından bilerek uzaklaştırılmış
olması yüzünden A7/A8'in (çok daha yüksek irtifa → çok daha büyük görüş
alanı) tamamen yama DIŞINA düşmesine yol açıyordu. K-MOD araç takımı bu
yüzden yamanın KENDİ merkezine ötelendi (`_K_MOD_OFSET_X/Y`) — göreceli
kinematik (araçlar arası mesafe/hız) A1–A6 ile birebir aynı kalır.

**Ayrı bir gerçek hata da bulunup düzeltildi:** `gazebo/kaydet.py`'nin
`_akil_denetimi` sağlık kontrolü, A11 ailesinin `zemin_m=560`'ı yerine modül
sabiti `ZEMIN_M=160`'ı kullanıyordu (Y1.1'de metadata alanında fark edilen
AYNI kök hata — ama bu sefer sadece metadata değil, gerçek bir RUNTIME
REDDİ üretti: K-MOD'un merkezi ~90 m, yanlışlıkla "zemin dışı" (±80 m
sınırı) sayılıp kayıt REDDEDİLDİ). `getattr(self.sen, "zemin_m", ZEMIN_M)`
ile düzeltildi — A1-A11 arşivi etkilenmedi (hepsi zaten ±80 m içinde kalan
konumlar kullanıyordu, bu yüzden hata şimdiye kadar hiç tetiklenmemişti).

Bile bu ötelemeyle bile **A8 hâlâ yamanın tamamen dışında** — 255.6 m
irtifada görüş alanı yarıçapı (~204 m) tek hücrenin yarı-genişliğini
(~170 m) aşıyor ve **fiziksel olarak** (560 m dünya + 2×2 ızgara + tek
hücrenin diğer üç sahneyle paylaştığı alan) daha büyütülemez. A8 bu yüzden
NEREDEYSE TAMAMEN prosedürel dokuda çalışıyor — bu, "Y1 dünyası" etiketinin
kısmi bir istisnası olarak açıkça not düşülüyor, gizlenmiyor.

## K1 sonucu

**Bir kova-etiketleme hatası bulunup düzeltildi (ölçümden SONRA, sonuca
BAKARAK değil — etiket hatasıydı, sınır değil):** `KOVALAR` listesindeki
0–10 px kovası ilk yazımda `"5x2_ve_alti"` adını taşıyordu ve kapı kodu
YANLIŞLIKLA `"8x5_10x5"` (10–15 px) anahtarını arıyordu — bu bant HİÇBİR
senaryonun üretmediği boş bir aralıktı, kapı n=0 ile hep KALDI veriyordu.
Kovalar yeniden adlandırıldı (SINIRLAR değişmedi, yalnız etiket), kapı artık
doğru anahtarı (`"8x5"`, 0–10 px) okuyor.

### 8×5 kovası (n=300, yalnızca Y1_A8_cok_kucuk buraya düşüyor)

| Kol | doğru | yanlış | çekimser | belirsiz | kanıt-yok | Kapı (≥0.80 doğru, ≤0.05 yanlış) |
|---|---:|---:|---:|---:|---:|---|
| S1 | 0.430 | 0.023 | 0.090 | 0.453 | 0.003 | **KALDI** |
| S2 | 0.423 | 0.023 | 0.123 | 0.427 | 0.003 | **KALDI** |
| S3 | 0.000 | 0.000 | 0.997 | 0.000 | 0.003 | **KALDI** |

### 15–20 px kovası (n=300, yalnızca Y1_A7_kucuk)

| Kol | doğru | yanlış |
|---|---:|---:|
| S1 | 0.760 | 0.000 |
| S2 | 0.753 | 0.000 |
| S3 | 0.000 | 0.000 |

## Yorum

- **S1/S2 8×5'te ~%43 doğru — kapının (≥0.80) çok altında.** "Belirsiz"
  (IoU 0.2–0.5) oranı ÇOK YÜKSEK (%43–45): bu, yanlış nesneyi seçmekten
  çok, DOĞRU nesneyi seçip yeterince HASSAS konumlayamamaktan kaynaklanıyor
  — 8–9 px'lik bir hedefte 1–2 pikseli lik konum hatası bile IoU'yu
  0.5'in altına düşürür. Ham hareket lekesi + `rafine_kutu` bu ölçekte
  fiziksel çözünürlük sınırına yakın.
- **S2, S1'e göre iyileştirmiyor** (0.430→0.423, hatta hafif düşüş) —
  zamansal kalıcılık filtresi bu boyutta ya doğru adayı da bazen eleyecek
  kadar sıkı (çekimser oranı 0.090→0.123 arttı) ya da katkısı ölçülemeyecek
  kadar küçük.
- **S3 tamamen çöküyor (0.0 doğru, %99.7 çekimser)** — ama bu bir seçim
  kuralı başarısızlığı DEĞİL, dedektörün (A6) A7/A8'in NEREDEYSE TAMAMEN
  prosedürel dokuda çalışması yüzünden bu sahnede kör kalması. Görsel
  doğrulama (`cikti/gorsel/kmod_k1/`): R=80 ROI'de hedef gözle net
  seçiliyor ama A6 hiçbir kutu döndürmüyor — A11 KOL0'ın "COCO Gazebo'da
  tamamen kör" bulgusunun bir varyantı, bu sefer A6 ve prosedürel dokuda.
  **S3'ün gerçek performansı bu yatakla ölçülemedi** — dedektör
  doğrulamasını anlamlı test etmek gerçek dokulu bir 8-20px yatak
  gerektirir (bkz. Y1.1/Y1.2'nin fiziksel sınırı yukarıda).
- **A7 (15-20px, kısmen gerçek dokuda) S1'de %76 doğru** — 8×5 kapısının
  hedefi olmasa da (bu kova 15x20px), gösterge niteliğinde: boyut arttıkça
  seçim kalitesi belirgin iyileşiyor, beklenen yön.

## HÜKÜM: K1 kapısı KALDI (üç kolda da). **K2 bu yüzden KOŞULMADI.**

Talimatın kendi ön-koşulu ("K2... yalnız K1 geçtiyse") gereği kapalı-çevrim
uygulaması ve demo entegrasyonu (K3) bu turda çalışılmadı.

**Sıradaki adaylar (sınanmadı):**
1. 8×5'te "belirsiz" oranının yüksekliği — `rafine_kutu`'nun bu ölçekteki
   hassasiyeti ayrı ölçülmeli (K1'in kendi sorunu değil, ölçüm tabanı).
   Alternatif: bu ölçekte IoU yerine MERKEZ MESAFESİ tabanlı bir
   doğru/yanlış kriteri denenebilir (ön-kayıtla).
2. S3'ü gerçekten test edebilmek için ya A8'i (fiziksel olarak imkansız)
   ya da YENİ bir 8-10px'lik GERÇEK-doku yatağı (farklı bir yerleşim
   stratejisiyle — örn. tek büyük fotoğraf yerine gerçek yüksek-irtifa
   drone görüntüsü) kurmak gerekir.
3. S2'nin hücre/k/N parametreleri (8px, k=2/N=3) hiç taranmadı — küçük bir
   ızgara taraması S2'nin S1'e göre gerçek bir kazanç sağlayıp
   sağlamadığını netleştirebilir.

## Görsel çıktılar

`gazebo/gorsel_uret.py` — tüm deneylerin ORTAK çağıracağı tek modül (video/
zaman-serisi/kare-ızgarası/özet-tablo). `gazebo/kmod_k1_gorseller.py` bu
turun görsellerini üretti: `cikti/gorsel/kmod_k1/` altında Y1_A7_kucuk ve
Y1_A8_cok_kucuk için S1 ve S3 kollarının video+seri+ızgara dosyaları,
"yalnız hareket haritası" videosu, ve `kmod_k1_ozet_tablo.png` (K1'in 8×5
kapı sonucu, GEÇTİ/KALDI renkli). Zaman kısıtı nedeniyle S2 için ayrı
görsel üretilmedi (sayısal sonuç `cikti/kmod_k1.json`'da tam).
