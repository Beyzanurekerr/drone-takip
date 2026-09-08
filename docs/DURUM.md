# Durum — demo-canli

Süreklilik dosyası: her alt-adım commit+push sonrası, her DUR'da güncellenir.

**Worktree / dal:** `~/dt_canli`, dal `demo-canli` (main'den `96d9c87`'de
ayrıldı; main'e D1/D2 ayrı sürüyor, buraya DOKUNULMADI — merge kullanıcı
tarafından tetiklenecek).

**Son commit:** `be0969d` (kabul testi + docs, plan tamamlandı). **DUR.**

**Yapılan (tüm plan tamamlandı):**
1. `336a261` — worktree kurulumu.
2. `ac2cd4c` — `veri/gazebo_canli.py`: `GazeboCanliKaynak` (canlı gz bridge,
   `arastirma-v1:gazebo/tani_a11_kol3.py` kalıbı), `canli_senaryo()`,
   klavye→Twist (`tus_isle`/`komut_ayarla`), `--gui`, `sure_sn`.
3. `2db8a7a` — `main.py`/`kaynak.py` entegrasyonu (`goster()` artık ham tuşu
   da döndürüyor, `_hafif_ciz` mod/px/irtifa, `--gui`/`--sure` bayrakları).
   **RTF/FPS ölçümü:** IMX500 tam çözünürlük canlı modda RTF~0.22/FPS~6.6
   (FPS≥15'i geçemez) — 640×480 (araştırma kamerası) RTF~0.54-0.57/FPS~16-17
   veriyor, `canli_senaryo()` bu yüzden 640×480 kullanıyor.
4. `be0969d` — `gazebo/kabul_canli.py` (scripted 60s tırmanış kabul testi,
   klavye yerine geri-beslemeli `vz` kontrolcüsü) + `docs/DEMO_SONUC.md`
   "Canlı (scripted)" bölümü + `docs/KURULUM.md` §5b (komut, tuş tablosu,
   WSL2 `--gui` notu).

**Kabul testi SONUCU — KALDI:** FPS 24.5 (≥15 GEÇTİ), kilit oranı **%3.1**
(≥%90 KALDI, 770 kareden 24'ü KILITLI, çoğu KORUMA/KAYIP), 60 s'de 164.4 m'ye
ulaşıldı (200 hedef). **Kök neden (ölçüldü):** RTF için düşürülen kamera
çözünürlüğü/fx'i (2028×1520,fx=1561 → 640×480,fx=500) FOV'u korurken native
piksel yoğunluğunu ~3.1× düşürüyor — hedef artık ort. 24.7px (demo'nun
[55,110]px kalibrasyon bandının çoğunlukla altında), üstelik
`R_MERDIVEN=(640,320,160,80)` gibi MUTLAK piksel sabitleri 2028px'e göre
kalibre edildiği için 640px'de ROI merdiveni de orantısız çalışıyor.
Ayrıntı: `docs/DEMO_SONUC.md` "Canlı (scripted)".

**Sıradaki adım (bu turun kapsamı DIŞINDA, gelecek iş):**
- 640×480 için `R_MERDIVEN`/`BANT`/A6 modelinin yeniden kalibrasyonu
  (kendi teşhis turu ister, `docs/TESHIS_2E_PX_BANDI.md`'nin küçük-kamera
  karşılığı) — YA DA IMX500 çözünürlüğünde kalıp FPS≥15'ten vazgeçmek/daha
  güçlü donanım beklemek.
- **Elle klavye/fare sürüşü KULLANICI tarafından test edilecek** (bu ortamda
  gerçek insan-klavye etkileşimi yok, yalnız scripted test yapılabildi).
- Merge: main'e **kullanıcı tetikleyecek**, ben yapmıyorum.

**Açık soru:** yok — kabul testi koşuldu ve sonuç (KALDI) nedeniyle
belgelendi, talimatın "sonucu DEMO_SONUC.md'ye satır" kısmı yerine getirildi.

**Çalışan süreçler:** yok (`ps aux | grep "gz sim"` ile doğrulandı, temiz).
