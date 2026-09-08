# Durum — demo-canli

Süreklilik dosyası: her alt-adım commit+push sonrası, her DUR'da güncellenir.

**Worktree / dal:** `~/dt_canli`, dal `demo-canli` (main'den `96d9c87`'de
ayrıldı; main'e D1/D2 ayrı sürüyor, buraya DOKUNULMADI — merge kullanıcı
tarafından tetiklenecek).

**Son commit:** bu tur icin asagida (yalnız docs — kullanıcı talimatı:
"kod değişikliği yok"). **DUR.**

**GÜNCELLEME (2026-09-08, kullanıcıdan) — bir önceki DUR'un "fiziksel
sınır" hükmü ERKENDİ, GERİ ÇEKİLDİ:** Plan B'nin regresyon KALDI'sını
("düşük nativ çözünürlükte gerçek piksel bilgisi kaybı, TUVAL_OLCEK ile
düzeltilemez") ben rapor etmiştim. Kullanıcı bunu sorguladı ve iki
kod-değişikliksiz teşhis istedi: (1) canlı döngü profili (gz render,
transport+decode, takipçi+YOLO, GPU/render-engine durumu), (2) çözünürlük
× RTF tablosu. İkisi de koşuldu (aşağıda) — sonuç, "fiziksel sınır"
iddiasını DOĞRULAMIYOR: gerçek darboğaz **render + YOLO'nun ikisi de
YAZILIMSAL (CPU) çalışması** — biri Gazebo'nun kendi ortamındaki bir GPU
render çökmesi yüzünden, diğeri kodun `device="cpu"` seçimi yüzünden.
Ayrıca Plan B'nin çökme deseni (bkz. `docs/DEMO_SONUC.md`ki kök neden)
**main'deki D1/D2 ile AYNI arıza** olabilir (kullanıcıdan) — bu yüzden
Plan B, D1/D2 `demo-canli`'ye merge edilene kadar YENİDEN KOŞULMAYACAK.

## Teşhis 1 — canlı döngü profili + GPU/render-engine durumu

**Yöntem (kod değişikliği YOK):** `python3 -m cProfile` ile
`gazebo/kabul_canli.py`'nin gerçek 60 s'lik canlı koşumu profillendi
(mevcut ayar: IMX500 nativ 2028×1520, kam_hz=15 — Plan A'nın bıraktığı
durum); GPU/render motoru `nvidia-smi`, `~/.gz/rendering/ogre2.log` ve
ayrı bir `gz sim` deney script'iyle (geçici, repo dışı `/tmp` scratchpad)
sınandı. `glxinfo` kurulu değildi, sudo/apt izni yok — GPU kanıtı
`nvidia-smi` + ogre2 log'undan alındı.

**GPU var, ama İKİ AYRI SEBEPLE hiç KULLANILMIYOR:**
- Donanım: NVIDIA GeForce RTX 3060 (6 GB) `nvidia-smi` ile GÖRÜNÜYOR ve
  CUDA çalışıyor (WSL2 GPU passthrough aktif) — bu makinede ayrıca bir
  Intel tümleşik GPU da var (`/usr/lib/wsl/drivers/iigd_dch...`).
- **Gazebo tarafı:** `gz sim` render motoru **ogre2** (`gazebo/
  dunya_uret.py` içinde sabit) ve ortamda `LIBGL_ALWAYS_SOFTWARE=1`
  (hem kabuk ortamında hem `gazebo/kaydet.py`/`veri/gazebo_canli.py`'nin
  `_sim_baslat()`'ında `setdefault` ile) zaten AYARLI — `~/.gz/rendering/
  ogre2.log`: `GL_RENDERER = llvmpipe` (yazılım/CPU render, GPU DEĞİL).
  **`LIBGL_ALWAYS_SOFTWARE`'i kaldırıp GPU render DENENDİĞİNDE `gz sim`
  ÇÖKÜYOR** (abort): D3D12/Mesa WSL katmanı Intel iGPU sürücüsünü
  seçiyor (`libigd12umd64.so`→`libigc.so`), onun gömülü LLVM-14'ü
  Mesa'nın kendi LLVM-15'iyle aynı komut satırı bayrağını
  (`spirv-expand-step`) iki kez kaydetmeye çalışıp LLVM'in global
  registry'sini fatal hataya düşürüyor (`CommandLine Error: Option
  'spirv-expand-step' registered more than once!`). **Sonuç:
  `LIBGL_ALWAYS_SOFTWARE=1` bir gözden kaçma DEĞİL, bu WSL2 (Intel+NVIDIA
  ikili GPU) ortamında ÇÖKMEYİ ÖNLEYEN GEREKLİ bir geçici çözüm** —
  basitçe kaldırılamaz; NVIDIA adaptörünü zorlamak (`MESA_D3D12_
  DEFAULT_ADAPTER_NAME` vb.) DENENMEDİ, ayrı bir teşhis/düzeltme turu
  ister.
- **YOLO/tracker tarafı — TAMAMEN BAĞIMSIZ bir bulgu:** `demo_ayar.py`
  `model.predict(..., device="cpu")` ile SABİT CPU'ya bağlanmış — bu
  Gazebo'nun render sorunuyla İLGİSİZ bir kod seçimi, CUDA/PyTorch
  Gazebo'nun OpenGL/D3D12 yoluna hiç girmez, `nvidia-smi`'nin zaten
  çalışıyor olması CUDA'nın bu ortamda erişilebilir olduğunu gösteriyor.
  **Denenmedi (kod değişikliği yasaktı bu turda) ama düşük riskli, yüksek
  potansiyelli bir sonraki adım:** `device="cuda"` denemek.

**Canlı döngü profili (60 s koşum, cProfile — mutlak sayılar cProfile
ek yüküyle şişmiş, ORANLAR güvenilir; "ort." = tottime/ncalls, gerçek p50
DEĞİL ama büyüklük mertebesi için yeterli):**

| Bileşen | Ölçüm | Yorum |
|---|---|---|
| Transport+decode (`_goruntu_cb`: protobuf→ndarray + `cv2.cvtColor`) | **~0.42 ms/kare** (508 çağrı, 0.211 s toplam) | İHMAL EDİLEBİLİR — darboğaz DEĞİL |
| `oku()` (yeni kareyi BEKLEME dahil) | ~23.6 ms/kare ort. (508 çağrı) | Çoğunlukla render'in kareyi YETİŞTİRMESİNİ bekleme |
| Takipçi + YOLO (`HedefTakip.guncelle`) | ~90.7 ms/kare ort. (500 çağrı, 45.3 s) | Kare başına en büyük TEK kalem |
| — bunun içinde yalnız YOLO `model.predict()` | ~48.6 ms/çağrı ort. (957 çağrı, 46.5 s toplam — guncelle'nin **~%85'i**) | `torch.conv2d` CPU'da 30.1 s (61248 çağrı) — GPU'ya taşınabilir, DENENMEDİ |

**Gz render (RTF, kamera açık/kapalı) — IMX500 nativ 2028×1520, mevcut
(zorunlu yazılım) render:**

| Durum | RTF | Yorum |
|---|---|---|
| Kamera KAPALI (yalnız fizik, sensor SDF'ten çıkarılmış) | **~0.82–1.00** | Fizik/dünya adımlaması TEK BAŞINA neredeyse gerçek zamanlı |
| Kamera AÇIK (aynı dünya, sensör var, gerçekten abone olunup akış tüketiliyorken ölçüldü) | **~0.03** | Render, RTF'yi ~30× DÜŞÜRÜYOR |

**Sonuç (Teşhis 1):** canlı modda gerçek-zamanlılığı asıl sınırlayan iki
BAĞIMSIZ, YAZILIMSAL/YAPILANDIRMA kaynaklı darboğaz var — (a) Gazebo'nun
kamera RENDER'i (CPU/llvmpipe'a ZORLANMIŞ, GPU'ya geçiş şu an ÇÖKÜYOR)
ve (b) YOLO ÇIKARIMI (CPU'ya SABİTLENMİŞ, GPU'nun kullanılıp
kullanılamayacağı hiç denenmemiş). Transport+decode İHMAL EDİLEBİLİR.
Bu ikisi "düşük nativ çözünürlükte bilgi kaybı" gibi fiziksel bir
sınırdan TAMAMEN FARKLI bir kategori — ikisi de (özellikle YOLO/CUDA)
potansiyel olarak DÜZELTİLEBİLİR sorunlar.

## Teşhis 2 — çözünürlük × RTF tablosu (kamera AÇIK, takipçi YOK, mevcut yazılım render)

Ayrı, minimal dünyalar (`gazebo.dunya_uret.dunya_yaz`, repo kodu
DEĞİŞTİRİLMEDEN, `/tmp` scratchpad'te) her çözünürlük için kuruldu, FOV
sabit tutuldu (`odak_px` orantılı), yalnız kamera konusuna abone olunup
kare sayıldı — YOLO/takip YOK:

| Çözünürlük | RTF (18 s pencerede örnekler) | Duvar-saati FPS |
|---|---|---|
| 2028×1520 (IMX500 nativ) | **~0.03, İSTİKRARLI DÜŞÜK** (9 örnek, 0.026–0.038 bandında) | 2.2–3.3 |
| 1352×1014 | **BİMODAL**: bazen ~1.0'a YAKIN, bazen ~0.05 (9 örnek: 0.05,0.06,1.00,0.97,0.055,0.55,1.00 karışık) | 3.0 |
| 1014×760 | **BİMODAL, yükselen eğilim**: pencere başında ~0.08–0.10, sonunda ~0.86–0.99 | 5.6 |

**Yorum:** 2028×1520'de render İSTİKRARLI şekilde çöküyor (hiç
toparlanmıyor); 1352×1014 ve 1014×760'ta render bazen gerçek-zamana
YETİŞEBİLİYOR (RTF→1.0), bazen düşüyor — bu, sabit/yumuşak bir
çözünürlük-performans eğrisinden çok bir EŞİK/tıkanıklık davranışına
işaret ediyor (18 s'lik tek pencere, DOĞRULAMA ister — daha uzun/çok
tekrarlı ölçüm YAPILMADI, kapsam dışı bırakıldı).

## Plan B ile D1/D2 ilişkisi — YENİDEN KOŞULMAYACAK

Kullanıcıya göre Plan B'nin regresyon KALDI'sındaki kopma deseni (kare
~535'te tek büyük ARAMA kopması, klip sonuna kadar toparlanmama) main
dalındaki D1/D2 ile AYNI arıza. D1/D2 şu an bu dal (`demo-canli`) için
erişilebilir DEĞİL (main hâlâ `96d9c87`'de, D1/D2 başka bir yerde/oturumda
sürüyor). **Bu yüzden Plan B'nin regresyonu/canlı kabulü D1/D2
`demo-canli`'ye merge EDİLENE KADAR yeniden koşulmayacak** — aksi halde
aynı bilinen arızayı tekrar tekrar ölçmüş oluruz.

**Önceki (GERİ ÇEKİLEN) iddia için düzeltme:** Plan B raporundaki "TUVAL_
OLCEK ile düzeltilemeyecek fiziksel bir sınır" ifadesi ERKENDİ — kanıt
(taban kayıtta da BENZER bir kopma var, kare 741→890, ama TOPARLANIYOR)
aslında bunun ölçek-bağımlı bir bilgi kaybından çok bir RE-EDİNME
SAĞLAMLIĞI hatası (D1/D2'nin hedeflediği tür) olduğuna işaret ediyor.
`docs/DEMO_SONUC.md`'deki ilgili paragraf bu güncellemeyle birlikte
okunmalı (orada henüz değiştirilmedi — kayıt tarihsel, bu dosya güncel
yorumu taşıyor).

**Sıradaki adım (bu turun kapsamı DIŞINDA — teşhis turuydu, kod
değişikliği YOK talimatıyla sınırlıydı):**
- **Düşük riskli, hızlı sınanabilir:** `demo_ayar.py`'de YOLO
  `device="cpu"` → `"cuda"` denemek (GPU zaten `nvidia-smi`'de görünüyor,
  Gazebo render sorunundan TAMAMEN bağımsız bir yol) — kare başı ~90 ms
  takipçi süresinin ~%85'i bununla düşebilir.
  YOLO`predict()` çağrılarının img boyutu (imgsz=640) ve model boyutu
  (a6_kucuk_hedef.pt) GPU'da ne kadar hızlanır ÖLÇÜLMEDİ.
- **Ayrı, daha riskli:** Gazebo/ogre2'nin GPU render çökmesini
  (Intel/NVIDIA WSL2 D3D12 adaptör seçimi) çözmek — `MESA_D3D12_
  DEFAULT_ADAPTER_NAME` ya da benzeri bir ortam değişkeniyle NVIDIA'yı
  zorlamak DENENMEDİ; kendi başına bir teşhis/düzeltme turu ister,
  başarısız olursa mevcut `LIBGL_ALWAYS_SOFTWARE=1` NET GEREKLİ kalır.
- Plan B'nin regresyonu/canlı kabulü: **D1/D2 merge edilene kadar
  ERTELENDİ.**
- **Elle klavye/fare sürüşü KULLANICI tarafından test edilecek** — yukarıdaki
  darboğazlardan en az biri çözülüp kabul testi GEÇENE kadar bunun bir
  anlamı yok.
- Merge: main'e **kullanıcı tetikleyecek**, ben yapmıyorum.

**Açık soru:** yok.

**Yeni KALICI altyapı (önceki turdan, hâlâ geçerli):**
`demo_ayar.ayarla_tuval_olcek(k)` / `demo_ayar.TUVAL_OLCEK` / `_R_MERDIVEN_1X`,
`takip.izleyici.HedefTakip(koruma_esik=, min_kenar=)`, `main.py --tuval-olcek`,
`veri/gazebo_canli.py:CANLI_TUVAL_OLCEK` — Plan B D1/D2 sonrası yeniden
koşulduğunda BUNLAR KULLANILACAK, yeniden yazılmayacak.

**Çalışan süreçler:** yok (`pgrep -a gz` ile doğrulandı, temiz — teşhis
script'lerinin başlattığı tüm `gz sim` süreçleri `killpg(SIGKILL)` ile
temizlendi).
