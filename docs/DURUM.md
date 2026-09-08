# Durum — demo-canli

Süreklilik dosyası: her alt-adım commit+push sonrası, her DUR'da güncellenir.

**Worktree / dal:** `~/dt_canli`, dal `demo-canli` (main'den `96d9c87`'de
ayrıldı; main'e D1/D2 ayrı sürüyor, buraya DOKUNULMAYACAK — merge kullanıcı
tarafından tetiklenecek).

**Son commit:** `2db8a7a` (main.py/kaynak.py entegrasyonu + RTF düzeltmesi).

**Yapılan:**
1. `336a261` — worktree kurulumu.
2. `ac2cd4c` — `veri/gazebo_canli.py`: `GazeboCanliKaynak` (canlı gz bridge,
   `arastirma-v1:gazebo/tani_a11_kol3.py` kalıbı), `canli_senaryo()`,
   klavye→Twist (`tus_isle`/`komut_ayarla`), `--gui` (`gz sim -g`, sessizce
   vazgeçer), `sure_sn` (sınırlı-süreli otomatik koşum).
3. `2db8a7a` — `main.py`: `goster()` artık `(durum, ham_tuş)` döndürüyor,
   `kos()` her karede `kaynak.tus_isle()` çağırıyor; `_hafif_ciz`
   mod/px/irtifa satırı; jsonl'deki irtifa `pozlar` yoksa `kaynak.irtifa`'ya
   düşüyor; `--gui`/`--sure` CLI bayrakları. `kaynak.py`: `"gazebo_canli"`
   dalı. **Ölçülmüş RTF/FPS bulgusu:** IMX500 tam çözünürlükte (2028×1520)
   canlı RTF~0.22, FPS~6.6 (FPS≥15 kriterini GEÇEMEZ) — 640×480'e
   (araştırma kamerası, odak 500px) düşürülünce RTF~0.54-0.57, FPS~16-17.
   `canli_senaryo()` bu yüzden 640×480 kullanıyor (IMX500 DEĞİL).
   `sure_sn` zamanlama hatası düzeltildi (dünya yükleme ~10-15s sürüyor,
   `_baglan()` bitmeden saymaya başlarsa ilk `oku()` 0 kare dönüyordu).

**Sıradaki adım:** `gazebo/kabul_canli.py` — scripted 60s tırmanış (50→200m)
kabul testi (`--mod demo` KaroArayici/YOLO edinmesiyle, GT yok, kilit oranı
kendi durum raporundan). Sonra `docs/DEMO_SONUC.md` "canlı (scripted)"
satırı + `docs/KURULUM.md` (komut + tuş tablosu + WSL2 gz GUI notu).

**Açık soru:** yok şu an; RTF<1 olduğu için "60 s duvar-saati" tırmanışın
gerçek sim-hızında mı yoksa telafi edilmiş (daha yüksek vz) komutla mı
karşılanacağı kabul testinde netleşecek — muhtemelen telafi gerekecek,
ölçülüp raporlanacak.

**Çalışan süreçler:** yok (smoke test'ler `kapat()` ile temiz kapatıldı,
`ps aux | grep "gz sim"` ile doğrulanabilir).
