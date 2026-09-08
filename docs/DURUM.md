# Durum — demo-canli

Süreklilik dosyası: her alt-adım commit+push sonrası, her DUR'da güncellenir.

**Worktree / dal:** `~/dt_canli`, dal `demo-canli` (main'den `96d9c87`'de
ayrıldı; main'e D1/D2 ayrı sürüyor, buraya DOKUNULMADI — merge kullanıcı
tarafından tetiklenecek).

**Son commit:** bu tur icin asagida. **DUR.**

**GÜNCELLEME (2026-09-08, kullanıcıdan) — tur KAPANMAMIŞTI:** önceki DUR'da
"kabul testi KALDI, düzeltme kapsam dışı" olarak bırakılmıştı, ama kök neden
(640×480 araştırma kamerası) kullanıcı tarafından KABUL EDİLEMEZ bulundu —
IMX500 DIŞI bir kamera demo'nun donanım hedefine aykırı. Kullanıcı iki
somut düzeltme planı verdi (A, geçmezse B); ikisi de yürütüldü ve
ÖLÇÜLDÜ, ikisi de KALDI (ayrıntı `docs/DEMO_SONUC.md` "Canlı (scripted)"
Plan A / Plan B bölümleri).

**Yapılan (bu tur):**
1. **Plan A** — kamera IMX500 tam çözünürlüğe (2028×1520, odak_px=1561)
   geri döndürüldü, `kam_hz` 30→15 (`veri/gazebo_canli.py:CANLI_GEN/YUK/
   ODAK_PX/HZ`). Kabul testi tekrar koşuldu: **FPS 4.65, kilit %2.5 —
   KALDI.** Kök neden: render/YOLO maliyeti update_rate'e değil
   çözünürlüğe bağlıymış; update_rate yarılanması FPS'i DÜŞÜRDÜ.
2. **Plan B** — kamera IMX500'ün TAM YARISI (1014×760, odak_px=780.5,
   FOV aynı) + sensor-px sabitlerinin (`demo_ayar.R_MERDIVEN`,
   `takip.izleyici.HedefTakip.koruma_esik`/`.min_kenar`) `TUVAL_OLCEK=0.5`
   ile yeniden ölçeklenmesi. Yeni KALICI altyapı: `demo_ayar.
   ayarla_tuval_olcek(k)`, `HedefTakip(koruma_esik=, min_kenar=)` kwargs,
   `main.py --tuval-olcek K` CLI bayrağı — hepsi `k`/kwarg verilmezse
   (varsayılan) davranış BİREBİR eskisi gibi, ağ-girdisi bandı (BANT/
   NET_HEDEF) BİLEREK ölçeklenmedi (talimat: resize SONRASI sabit AG
   kanvasında ölçer).
3. **Regresyon (talimat: canlı kabulden ÖNCE sınandı):** kayıtlı
   `Demo_kucul` `gazebo/kaydet.py` ile geçici olarak yeniden kaydedilip
   (kareler/ diski tasarrufu için gitignore'lu, silinmişti) 1014×760 +
   TUVAL_OLCEK=0.5 ile taban (aynı yeniden-kayıt, ölçeksiz) karşısında
   koşuldu: **kilit %93.0 (taban) → %43.1 (1014×760) — KALDI**
   (≥%95 gerekliydi). Test SONRASI orijinal kayıt dosyaları
   (`pozlar.csv`/`meta.json`/`dunya.sdf`/`imu.csv`) `git checkout` ile
   GERİ ALINDI — kalıcı bir değişiklik YOK, yalnız ölçüm için geçiciydi.
   Kök neden: gradüel değil TEK BÜYÜK bir ARAMA kopması (kare ~535,
   irtifa ~121 m) klip sonuna kadar (650 kare) hiç toparlanmıyor — sabit
   ölçekleme MATEMATİKSEL OLARAK doğru çalışıyor (R seçim oranı
   değişmiyor, hedef boyutu tam yarıya düşüyor) ama düşük nativ
   çözünürlükte GERÇEK piksel bilgisi yarıya iniyor, dijital upscale bunu
   geri getirmiyor — TUVAL_OLCEK gibi bir sabit-ölçekleme ile
   DÜZELTİLEMEYECEK fiziksel bir sınır. **Canlı kabul bu nedenle
   KOŞULMADI** (regresyon kapısı geçmedi).

**Sıradaki adım (bu turun kapsamı DIŞINDA, gelecek iş — üçüncü bir yol
gerekir, A/B ikisi de tükendi):**
- IMX500 tam çözünürlükte kalıp render/YOLO maliyetini GERÇEKTEN
  düşürecek bir optimizasyon (ONNX/int8, GPU, ROI-öncelikli render) —
  Plan A'nın update_rate denemesi bunu YAPMADIĞI için başarısız oldu.
- YA DA düşük-çözünürlük rejiminde re-edinme stratejisini (KaroArayici
  tarama/eşik) native piksel yoğunluğuna göre YENİDEN TASARLAMAK (basit
  sabit ölçekleme yetmiyor, ölçüldü) — kendi teşhis turu ister.
- YA DA daha güçlü/GPU'lu donanım beklemek.
- **Elle klavye/fare sürüşü KULLANICI tarafından test edilecek** (bu
  ortamda gerçek insan-klavye etkileşimi yok, yalnız scripted test
  yapılabildi) — yukarıdaki üç yoldan biri çözülüp kabul testi GEÇENE
  kadar bunun bir anlamı yok (sistem şu an canlıda güvenilir kilitlenmiyor).
- Merge: main'e **kullanıcı tetikleyecek**, ben yapmıyorum.

**Açık soru:** yok — her iki plan da koşuldu, ölçüldü, belgelendi
(`docs/DEMO_SONUC.md`).

**Yeni KALICI altyapı (ileride tekrar kullanılabilir):**
`demo_ayar.ayarla_tuval_olcek(k)` / `demo_ayar.TUVAL_OLCEK` / `_R_MERDIVEN_1X`,
`takip.izleyici.HedefTakip(koruma_esik=, min_kenar=)`, `main.py --tuval-olcek`,
`veri/gazebo_canli.py:CANLI_TUVAL_OLCEK`.

**Çalışan süreçler:** yok (`pgrep -a gz` ile doğrulandı, temiz).
