# Durum — demo-canli

Süreklilik dosyası: her alt-adım commit+push sonrası, her DUR'da güncellenir.

**Worktree / dal:** `~/dt_canli`, dal `demo-canli` (main'den `96d9c87`'de
ayrıldı; main'e D1/D2 ayrı sürüyor, buraya DOKUNULMADI — merge kullanıcı
tarafından tetiklenecek).

**Son commit:** bu tur icin asagida. **DUR.**

**GÜNCELLEME (2026-09-08, kullanıcıdan) — GPU ETKİNLEŞTİRİLDİ, iki yerde:**
önceki turda "render + YOLO CPU'ya zorlanmış" teşhisi konmuştu (bkz. bir
önceki DUR bölümü, aşağıda saklı). Bu turda kullanıcı iki somut
YAPILANDIRMA değişikliği istedi — ikisi de uygulandı, ölçüldü, İKİSİ DE
BAŞARILI:

## 1. YOLO device="cuda" + half (fp16)

`demo_ayar.py`: `YOLO_DEVICE = "cuda" if torch.cuda.is_available() else
"cpu"`, `YOLO_HALF = YOLO_DEVICE == "cuda"` — iki `model.predict(...,
device="cpu")` çağrısı `device=YOLO_DEVICE, half=YOLO_HALF` oldu.

Kayıtlı `Demo_kucul` (geçici olarak yeniden kaydedilip test sonrası
`git checkout` ile geri alındı — kalıcı değişiklik yok) üzerinde önce/sonra:

| | FPS | Kilit oranı |
|---|---|---|
| Önce (CPU) | 32.9 | %93.8 |
| Sonra (CUDA+fp16) | **43.6** (+%32) | %94.0 (**Δ+0.2pp, ±%1 kriteri GEÇTİ**) |

`half=True` ultralytics'te deprecation uyarısı veriyor ama çalışıyor —
kapsam dışı, ilerde `quantize`'a geçiş gerekebilir.

## 2. Gazebo GPU render

`veri/gazebo_canli.py:_sim_baslat()`: `LIBGL_ALWAYS_SOFTWARE` AÇIKÇA
kaldırıldı (`pop()` — ambiyan kabukta zaten "1" ayarlıydı, `setdefault`
yetmezdi), `MESA_D3D12_DEFAULT_ADAPTER_NAME="NVIDIA"` `setdefault` ile
eklendi.

**Sonuç: ÇÖKMEDİ, İKİ deneme de çalıştı** (IMX500 nativ 2028×1520,
kamera açık, 18 s pencere):

| Deneme | Sonuç | RTF | Kamera FPS |
|---|---|---|---|
| NVIDIA zorlanmış, ogre2 (varsayılan) | ÇÖKMEDİ, `GL_RENDERER = D3D12 (NVIDIA GeForce RTX 3060 Laptop GPU)` | ~0.97 | 30.7 |
| NVIDIA zorlanmış, `--render-engine ogre` | ÇÖKMEDİ | ~0.99 | 36.5 |

Önceki teşhis (bir önceki tur) zaten kök nedeni bulmuştu: adaptör
zorlanmadığında D3D12/Mesa WSL katmanı Intel iGPU'yu seçip LLVM
double-registration ile çöküyordu; NVIDIA'ya zorlayınca çökme YOK.
`--render-engine ogre` denemesine (talimattaki "çökerse" dalı) GEREK
KALMADI ama yine de koşuldu (bonus doğrulama, ikisi de iyi).

**KURULUM.md'ye "çalışmazsa" notu EKLENMEDİ** (çünkü çalıştı) — bunun
yerine §5b'ye GPU render'ın nasıl etkinleştirildiği + genelleştirilemezlik
uyarısı (bu düzeltme bu makineye/WSL2-Intel+NVIDIA kombinasyonuna özgü,
başka ortamda yine çökebilir) eklendi.

## Sonuç: canlı mod IMX500 nativine (TUVAL_OLCEK=1.0) GERİ DÖNDÜRÜLDÜ

GPU render artık IMX500 nativ çözünürlükte (2028×1520) neredeyse gerçek
zamanlı (RTF~0.97-0.99) olduğu için Plan B'nin 1014×760 + ölçekleme
ayarına ARTIK GEREK YOK. `veri/gazebo_canli.py`:
`CANLI_GEN/YUK=IMX500_GEN/YUK` (2028×1520), `CANLI_ODAK_PX=IMX500_ODAK_PX`
(1561), `CANLI_TUVAL_OLCEK=1.0`, `CANLI_HZ=IMX500_HZ` (30, GPU render
bunu rahat karşılıyor). Plan B'nin ölçekleme altyapısı
(`demo_ayar.ayarla_tuval_olcek`, `HedefTakip(koruma_esik=, min_kenar=)`,
`main.py --tuval-olcek`) KALICI bırakıldı — kullanılmıyor ama silinmedi.

**Gerçek koda uygulanmış haliyle uçtan uca doğrulandı** (`GazeboCanliKaynak`
üzerinden, TAKİPÇİ/YOLO OLMADAN — yalnız bağlantı+kare okuma, bu canlı
KABUL testi DEĞİL): **28.81 gerçek FPS, IMX500 nativ 2028×1520, 15 s
pencere, 433 kare** — nominal 30 FPS'e çok yakın.

## Canlı kabul testi HÂLÂ KOŞULMADI

Kullanıcı talimatı: main'deki D1/D2, Plan B'nin regresyon kopmasıyla
(kare ~535'te tek büyük ARAMA kopması, toparlanmama) AYNI arıza olabilir
— bu yüzden `gazebo/kabul_canli.py` (tam takipçi+YOLO+kilit-oranı
kriteri) **D1/D2 `demo-canli`'ye merge edilene kadar KOŞULMAYACAK**. Bu
turda yapılan GPU değişiklikleri yalnız ALTYAPI/YAPILANDIRMA olarak
hazır — render/YOLO hızının artık darboğaz OLMADIĞI gösterildi, ama
kilit ORANI kriteri (D1/D2'nin hedeflediği re-edinme sağlamlığı) hâlâ
AYRI, çözülmemiş bir soru.

**Sıradaki adım (bu turun kapsamı DIŞINDA):**
- Merge: main'deki D1/D2 → main → `demo-canli` (kullanıcı tetikleyecek).
- D1/D2 merge sonrası: `gazebo/kabul_canli.py` YENİDEN koşulmalı (artık
  GPU render + CUDA YOLO ile, IMX500 nativ çözünürlükte) — FPS kriteri
  (≥15) bu turun ölçümleriyle (28.8 FPS bağlantı, YOLO GPU'da çok daha
  hızlı) RAHATLIKLA geçmesi beklenir; kilit kriteri (≥%90) D1/D2'nin
  düzeltmesine bağlı, ÖLÇÜLMEDİ.
- Elle klavye/fare sürüşü: **KULLANICI test edecek** — kabul testi
  GEÇENE kadar bunun pratik bir anlamı sınırlı olsa da GPU render
  sayesinde artık en azından akıcı (28+ FPS) bir görüntü ile denenebilir.
- `gazebo/kaydet.py` (offline kayıt) aynı GPU render düzeltmesinden
  YARARLANABİLİR ama bu turun kapsamı dışında bırakıldı (yalnız
  `veri/gazebo_canli.py` değiştirildi, talimat "canlı mod" idi).

**Açık soru:** yok.

**Yeni KALICI altyapı (bu tur):**
`demo_ayar.YOLO_DEVICE` / `demo_ayar.YOLO_HALF` (CUDA varsa otomatik),
`veri/gazebo_canli.py:_sim_baslat()`'ta `MESA_D3D12_DEFAULT_ADAPTER_NAME`
zorlaması. Önceki turdan hâlâ KULLANILMIYOR ama duran altyapı:
`demo_ayar.ayarla_tuval_olcek(k)` / `TUVAL_OLCEK` / `_R_MERDIVEN_1X`,
`takip.izleyici.HedefTakip(koruma_esik=, min_kenar=)`, `main.py
--tuval-olcek`, `veri/gazebo_canli.py:CANLI_TUVAL_OLCEK` (şu an 1.0).

**Çalışan süreçler:** yok (`pgrep -a gz` ile doğrulandı, temiz — hem
teşhis script'lerinin hem gerçek `GazeboCanliKaynak` sanity-check'inin
`gz sim` süreçleri temiz kapatıldı).

---

## (Önceki tur, saklı) — Teşhis: render+YOLO CPU'ya zorlanmış

Bu bölüm bir önceki turun teşhis bulgularının ÖZETİDİR — GPU artık
etkinleştirildiği için tarihsel referans olarak bırakıldı (ayrıntı git
geçmişinde `14ab64e` commit'inde):

- NVIDIA RTX 3060 `nvidia-smi`'de görünüyordu ama (a) Gazebo GPU render'i
  bu WSL2'de çöküyordu (Intel adaptör + LLVM double-registration), (b)
  YOLO `device="cpu"`'ya sabitti — iki BAĞIMSIZ neden.
- Kamera KAPALI/AÇIK RTF karşılaştırması: fizik tek başına ~0.82-1.00,
  kamera açılınca (CPU render) ~0.03'e çöküyordu.
- Çözünürlük × RTF tablosu (CPU render): 2028×1520 istikrarlı ~0.03;
  1352×1014/1014×760 bimodal (~0.05-1.0 arası).
- Sonuç o turda: "fiziksel sınır" hükmü ERKENDİ, GERİ ÇEKİLDİ — darboğaz
  YAZILIMSAL/YAPILANDIRMA. Bu turda ikisi de GİDERİLDİ (yukarı bkz.).
