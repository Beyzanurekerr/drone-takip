# Demo Sonuçları (v1) — 2026-09-07

`--mod demo` (N_TESPIT=2, dedektor_karar), GT ile ölçüldü. Kayıtlar:
`data/gazebo/Demo_kucul` (50→210 m, 1200 kare), `Demo_celdirici` (sabit
80 m, 1791 kare, 60 s), `Demo_kopus` (sabit 80 m, 1800 kare, 60 s). Ham +
HUD'lu videolar `cikti/demo/`, kare başına durum `cikti/demo/*.jsonl`.

**Kural (talimat gereği):** KALAN (geçemeyen) senaryo düzeltilmedi —
sonuç olduğu gibi raporlanıyor.

## v1.1 denemesi (2026-09-08) — KALDI, v1 KOD OLARAK BIRAKILDI

Kullanıcının Demo_kopus/Demo_celdirici'yi düzeltmek için önerdiği tek
değişken: `takip/izleyici.py:_dedektor_karar_adimi`'nin ARAMA/KAYIP
dalında (1) arama merkezi artık DONMUŞ "son güvenilir merkez" değil,
Kalman'ın HER KAREDE güncellenen coast öngörüsü, yarıçap
`r = gecen_kare × |Kalman hızı| + R_ZAMAN` ile büyüyor; (2)
`demo_ayar.KaroArayici.adim()`'in aday puanı artık salt D_NORM değil,
adayın son 3 karelik hareket vektörünün Kalman hızıyla (yön+büyüklük)
tutarlılığıyla karışık, ve Kalman hızı belirginken (>3 px/kare) ust
üste durgun kalan (statik) bir aday doğrudan reddediliyor. Üç senaryo
da bu değişiklikle yeniden koşuldu (`--mod demo --source gazebo
--sequence <ad>`), sonra **kod v1'e geri alındı** (`git checkout --
demo_ayar.py takip/izleyici.py`) — aşağıdaki üç ölçüm net bir fayda
göstermedi ve bir tanesinde gerileme var:

| Senaryo | v1 | v1.1 | Sonuç |
|---|---|---|---|
| Demo_kucul | kilit %96.4, IoU 0.793, hassasiyet %100.0 | kilit %96.9, IoU 0.793, hassasiyet %100.0, FPS daha iyi (paylaşımsız CPU) | ~parite, ölçülebilir fark yok |
| Demo_celdirici | yanlış hedef 0/1791 (GEÇTİ); genel kilit oranı %59.3 (bilgi amaçlı, çalkalanarak kısmen toparlanıyordu) | yanlış hedef **hâlâ 0/1791 (GEÇTİ)**; genel kilit oranı **%38.1'e GERİLEDİ** — kare 686'da KILITLI→SUPHELI→ARAMA→KAYIP'a düşüyor ve klip sonuna kadar (1030 kare) **bir daha hiç toparlanmıyor** (v1'in çalkalanıp kısmen geri dönmesinin aksine) | asıl ölçüt etkilenmedi, ikincil kararlılık metriği KÖTÜLEŞTİ |
| Demo_kopus | IoU sürekli 0.000 (1786/1786) | IoU **hâlâ sürekli 0.000** (1786/1786) — DEĞİŞMEDİ | KALDI, beklenen sonuç |

**Demo_kopus neden değişmedi (tasarım gereği, sürpriz değil):** asıl
arıza `demo_ayar.demo_hedef_sec` içindeki İLK KİLİT seçiminde (kare 14,
henüz `HedefTakip`/Kalman nesnesi YOK) — v1.1'in hız-tutarlılığı ve
statik-aday reddi Kalman hızına muhtaç, ilk edinmede Kalman olmadığı
için bu yol `merkez=None, r=None, hiz=None` ile çağrılıp DAVRANIŞ
DEĞİŞMEDEN eskisi gibi çalışıyor (bkz. `demo_ayar.py` modül başlığındaki
kasıtlı not). Yani bu deneme Demo_kopus'un asıl arızasını hiç
hedeflemedi — ilk edinmeye dokunmadan yalnızca kilit-SONRASI
ARAMA/KAYIP kurtarmasını değiştirdi.

**Demo_celdirici neden geriledi (hipotez, doğrulanmadı):** kayıp anında
Kalman hızı `sondur()` ile SÖNDÜRÜLMÜYOR (yalnız KILITLI/SUPHELI
dalında çağrılır) — ARAMA/KAYIP boyunca son bilinen hız SABİT kalıp
sürükleniyor. Uzun bir KAYIP'tan sonra gerçek hedefin o anki hareketi bu
BAYAT hız tahminiyle uyuşmayınca hız-tutarlılık terimi geçerli adayı
düşük puanlıyor, gerekirse statik-reddi de yanlışlıkla tetikleyebilir —
sonuç, v1'in "çalkalanarak parçalı toparlanma"sı yerine kalıcı KAYIP.

**Sonuç:** kod v1 olarak bırakıldı (yukarıdaki üç madde net fayda
göstermedi, biri geriledi). Demo_kopus'un asıl düzeltmesi
`demo_hedef_sec`'in ilk-kilit seçimine (Kalman öncesi, ör. birden çok
ardışık kare üzerinde adayın KENDİ hareketine bakan bir tutarlılık
kontrolü) dokunmayı gerektirir — bu denemenin kapsamı DIŞINDA kaldı.

## v1 + GT-ilk-kilit teşhisi (2026-09-08) — Demo_kopus'un GERÇEK arıza yeri bulundu

`--hedef-gt-ilk` (main.py, yeni CLI bayrağı, **KALICI teşhis aracı**):
`--mod demo`'da ilk kilit `demo_hedef_sec` (soğuk edinme, YOLO+karo
tarama) YERİNE kayıtlı GT kutusuyla yapılır (VisDrone `--yolo-gt-esle`
ile aynı ilke — tıkla-seç'in kayıt karşılığı); kilit-SONRASI davranış
(`kayip_dedektor=karayici`, `dedektor_karar`) DEĞİŞMEZ. Amaç: Demo_kopus'un
"ilk kilit zaten yanlış" sorununu ölçüm dışı bırakıp asıl soruyu (1.3 s'lik
örtülme sonrası doğru hedefe dönüş var mı) İLK KEZ ölçmek.

| Senaryo | v1 (demo_hedef_sec) | v1 + GT-ilk-kilit |
|---|---|---|
| Demo_kucul | kilit %96.4–96.9, IoU 0.793 | kilit %96.9, IoU 0.793 — fark yok (ilk kilit zaten doğruydu) |
| Demo_celdirici | kilit %59.3 | kilit %53.6, IoU 0.329 — aynı büyüklük mertebesi |
| Demo_kopus | IoU sürekli 0.000 | IoU ort **0.112** (@0.5 %13.2), kilit oranı **%17.9** — ARTIK SIFIR DEĞİL, ama hâlâ çok düşük |

**Asıl bulgu (Demo_kopus, DOĞRU ilk kilitle bile):** sistem kare ~388'de —
örtülme penceresinden (kare 1405–1445) yaklaşık **34 saniye ÖNCE** —
KORUMA'ya giriyor ve kare 1419'a kadar (1031 kare, ~34 s) orada KALIYOR.
Asıl örtülme (t=46.82–48.18 s) bu KORUMA süresinin İÇİNDE geçiyor —
sistem onu hiç "görmüyor" çünkü zaten dedektörsüz coast modunda
(`_koruma_adimi`, arama YOK). KORUMA'dan çıkınca (kare 1419→KAYIP→1426
KILITLI) IoU klip sonuna kadar neredeyse hep 0 kalıyor — "dönüş" hâlâ
YOK. **Sonuç: Demo_kopus'un sorunu yalnızca ilk-edinme hatası DEĞİL**
(o da var, ayrı) — GT ile doğru başlasa bile iz, örtülmeden çok önce,
muhtemelen bir boyut/ölçek tahmini sapmasıyla KORUMA'ya kilitleniyor
(GT hedef boyutu klip ortalaması 79.6×42.6 px, KORUMA_ESIK'in [25 px]
çok üstünde — demek ki KORUMA'yı tetikleyen *tahmin edilen* boyut,
gerçek GT boyutu değil) ve dedektör devre dışı kaldığı için bir daha
çıkamıyor. Kök neden (tahmini boyut neden kare 388'de 25 px altına
düşüyor) araştırılmadı — kapsam dışı bırakıldı.

## v1.1b denemesi (2026-09-08) — yalnız `kf.sondur()`, KALDI, v1'de bırakıldı

Yukarıdaki bulgudan sonra "bayat hız" hipotezi (ARAMA/KAYIP'ta Kalman
hızı hiç söndürülmüyor — `kf.sondur()` yalnız KILITLI/SUPHELI dalında
çağrılıyor) TEK DEĞİŞKEN olarak test edildi: `_dedektor_karar_adimi`'nin
ARAMA/KAYIP dalına `self.kf.sondur()` eklendi (v1.1'in geri kalanı —
Kalman-merkezli arama, hız-tutarlılık, statik-aday reddi — YOK),
standart `demo_hedef_sec` ile (GT-ilk DEĞİL) üç senaryo koşuldu:

| Senaryo | v1 | v1.1b (yalnız `sondur()`) |
|---|---|---|
| Demo_kucul | kilit %96.9, IoU 0.793 | kilit %96.9, IoU 0.792 — fark yok |
| Demo_celdirici | yanlış hedef 0/1791, kilit %59.3 | yanlış hedef **hâlâ 0/1791**, kilit oranı **%46.8'e GERİLEDİ** (v1.1'in tam hali kadar kötü değil — %38.1 — ama v1'den yine de kötü) |
| Demo_kopus | IoU sürekli 0.000, kilit %3.5 | **BİREBİR AYNI** — IoU 0.000, kilit %3.5 |

**Demo_kopus neden birebir aynı kaldı:** `sondur()` yalnız ARAMA/KAYIP
dalında çalışıyor; Demo_kopus'un asıl sorunu (kare ~388'deki erken KORUMA
girişi) `_koruma_adimi` içinde — ayrı bir fonksiyon, bu değişikliğin hiç
uğramadığı bir dal. Yani hipotez YANLIŞ değil ama YANLIŞ MEKANİZMAYI
hedefliyordu.

**Sonuç:** `sondur()` Demo_kopus'u hiç etkilemedi ve Demo_celdirici'yi
v1'den kötüleştirdi. Net fayda yok → kod v1'e geri alındı (`git checkout
-- takip/izleyici.py`). `--hedef-gt-ilk` (main.py) KALICI kaldı — "ilk
kilit mi, kilit-sonrası mı" ayrımını yapan bir teşhis aracı.

## Demo_kucul — **GEÇTİ**

| Ölçüt | Sonuç | Durum |
|---|---|---|
| Hassasiyet ≥%95 (merkez hatası ≤ köşegen/2) | **%100.0** (1194/1194 GT karesi) | GEÇTİ |
| Kilit kesintisiz | 1 kısa ARAMA epizotu (kare 138, 60–70 m bandında, ~24 kare, kendiliğinden toparlandı) — tam anlamıyla kesintisiz değil ama kilit oranı %96.4 | KISMEN |
| KORUMA'ya geçiş | Bu klipte (210 m'ye kadar) **hiç tetiklenmedi** — native px hiç 25'in altına inmedi (bkz. §3 düzeltmesi) | bilgi |

**50→210 m irtifa × kilit oranı (10 m basamak, N=2):**

| İrtifa | Kilit oranı | İrtifa | Kilit oranı |
|---|---|---|---|
| 50–60 m | %91.5 | 130–140 m | %100.0 |
| 60–70 m | %53.9 (ARAMA epizotu burada) | 140–160 m | %100.0 |
| 70–80 m | %97.4 | 160–190 m | %100.0 |
| 80–130 m | %100.0 | 190–210 m | %100.0 |

## Demo_celdirici — **KISMEN GEÇTİ** (asıl ölçüt geçti, genel kararlılık ayrı sorun)

| Ölçüt | Sonuç | Durum |
|---|---|---|
| Yanlış hedefe geçiş = 0 | **0/1791 kare** — KİLİTLİ iken hiçbir karede celdirici/celdirici2 GT'siyle IoU≥0.3 yok (gerçek konumları `pozlar.csv`'den projekte edilip doğrulandı) | **GEÇTİ** |
| En yakın geçişteki durum | Çeldiriciler ~t=4–4.5 s'de (kare ~120–135) geçiyor; durum o pencerede **KİLİTLİ** kalıyor, hiç bozulmuyor (bir sonraki durum değişikliği kare 686'ya kadar yok) | GEÇTİ |
| Genel kilit oranı | %59.3 — kare ~686'dan itibaren (decoy geçişinden ~19 s SONRA, geçişle **ilgisiz**) sık SUPHELI/ARAMA/KILITLI çalkalanması başlıyor, kare 1528'de KAYIP'a düşüyor, 1635-1665 arası kısa toparlanma, sonda KORUMA | bilgi amaçlı — test edilen kriter değil, düzeltilmedi |

## Demo_kopus — **KALDI**

| Ölçüt | Sonuç | Durum |
|---|---|---|
| Yanlış kilit = 0 | Ölçülemez/anlamsız — sistem **hiçbir karede doğru hedefe kilitlenmedi** | — |
| Örtülme (t=46.82–48.18 s, kare ~1405–1445) sonrası doğru hedefe dönüş | **ÖLÇÜLEMEDİ** — IoU klip boyunca sürekli **0.000** (1786/1786 GT karesi), ilk edinme (kare 14) zaten YANLIŞ nesneye kilitlendi; kare 104'te KORUMA'ya girip 1223'e kadar (1119 kare, ~37 s) orada kalıyor | **KALDI** |

Kök neden araştırılmadı (talimat: "düzeltmeye girme"). Gözlem: soğuk edinme
(`demo_hedef_sec`, kadraj merkezine çapalı karo taraması) bu senaryoda
hiç doğru nesneyi bulamadı; `Demo_celdirici`/`Demo_kucul`'da aynı mekanizma
sorunsuz çalıştı, yani `Demo_kopus`'a özgü bir koşul (kamera/hedef
başlangıç konumu, sahne) var. **Görsel doğrulama** (`docs/gorseller/
kopus_ornek.png`, kare 50): KİLİTLİ kutusu gerçek araçta DEĞİL, yakındaki
bir **ağaç tepesinin (canopy) kenarında** duruyor — asıl beyaz araç
karede görünür halde, otoparkta, kutunun ~150 px güneybatısında. Sahne
`Demo_kopus` için yoğun ağaç örtüsü içeriyor (senaryonun kendi konusu -
örtülme testi); soğuk edinme büyük ihtimalle bir ağaç/gölge lekesini araç
sanmış. Bu bir HİPOTEZ, doğrulanmadı.

**Güncelleme (2026-09-08):** yukarıdaki sayılar standart `demo_hedef_sec`
(soğuk edinme) iledir. `--hedef-gt-ilk` ile (doğru ilk kilit) yeniden
ölçüldüğünde sorunun ilk-edinmeyle SINIRLI OLMADIĞI bulundu — bkz. "v1 +
GT-ilk-kilit teşhisi" bölümü: sistem örtülmeden ~34 s önce (kare ~388)
zaten KORUMA'ya kilitleniyor ve bir daha çıkamıyor.

## Ortak

| Senaryo | FPS | ARAMA epizot sayısı (KİLİTLİ/ŞÜPHELİ→ARAMA) |
|---|---|---|
| Demo_kucul | 23.8 | 1 |
| Demo_celdirici | 29.5 | 4 |
| Demo_kopus | 82.1 (çoğu kare KORUMA'da, YOLO çağrılmıyor — yanıltıcı yüksek, GERÇEK performans değil) | 0 (ama sürekli KAYIP↔KORUMA döngüsü var, bkz. yukarı) |

## Özet

| Senaryo | Sonuç |
|---|---|
| Demo_kucul | **GEÇTİ** |
| Demo_celdirici | **KISMEN GEÇTİ** (asıl test edilen "yanlış hedef" kriteri geçti) |
| Demo_kopus | **KALDI** |

## Canlı (scripted) — `demo-canli` dalı, 2026-09-08 — **KALDI**

`--source gazebo_canli` (`veri/gazebo_canli.py`) ile gerçek zamanlı `gz sim`
bağlantısı + `gazebo/kabul_canli.py` (klavye YERİNE geri-beslemeli scripted
tırmanış kontrolcüsü: `vz = clip((200 − irtifa)/kalan_süre, 0, 8)`). Elle
klavye/fare sürüşü **KULLANICI test edecek** (bkz. `docs/KURULUM.md`) — bu
satır yalnız otomatik/scripted kabul koşumunu raporlar.

| Ölçüt | Sonuç | Durum |
|---|---|---|
| FPS ≥ 15 | **24.5** | GEÇTİ |
| Kilit oranı ≥ %90 | **%3.1** (770 kareden 24'ü KILITLI; 334 KORUMA, 251 KAYIP, 85 ARAMA, 76 ŞÜPHELİ) | **KALDI** |
| 50→200 m / 60 s tırmanış | Yalnız **164.4 m**'ye ulaşıldı (60 s'de) | KALDI (bilgi) |

**Kök neden (ölçüldü, tasarım tuzağı):** RTF/FPS'i canlı-uyumlu kılmak için
kamera IMX500 (2028×1520, fx=1561) yerine araştırma kamerasına (640×480,
fx=500) düşürüldü (bkz. `veri/gazebo_canli.py` — bağlantı-testinde IMX500
RTF~0.22/FPS~6.6, 640×480 RTF~0.54-0.57/FPS~16-17). **Ama bu, FOV'u neredeyse
AYNI tutarken (66°↔65°, `genislik`/`odak_px` orantılı küçüldüğü için) native
piksel YOĞUNLUĞUNU ~3.1× DÜŞÜRÜYOR** — aynı gerçek mesafedeki hedef artık
~3× daha az piksel kaplıyor (ölçülen: takip kutusu ort. 24.7px, min 12.5,
maks 61.5 — DEMO'nun IMX500 kalibrasyonunun [55,110]px hedef bandının
ÇOĞUNLUKLA ALTINDA). `demo_ayar.py`'nin `R_MERDIVEN=(640,320,160,80)` /
`BANT`/`NET_HEDEF` sabitleri MUTLAK piksel değerleridir ve özellikle
2028px-genişlikte bir sensöre göre kalibre edilmiştir — 640px-genişlikte bir
sensörde R=320 artık karenin YARISI (2028'de ~%16'sı yerine), yani ROI
merdiveni de aynı zamanda BOZULUYOR. Sonuç: sistem çoğu zaman KORUMA/KAYIP'ta
kalıyor (hedef gerçekten küçük + ROI merdiveni yanlış ölçekli).

**GÜNCELLEME (2026-09-08, kullanıcıdan): bu deney REDDEDİLDİ** — 640×480
araştırma kamerası IMX500 DIŞI bir donanım, kabul edilemez. Aşağıdaki
Plan A / Plan B bu KALDI'nın düzeltmesi olarak yürütüldü; ikisi de ayrı
ayrı KALDI (ayrıntı aşağıda). Bu bölüm yalnız TARİHSEL kayıt olarak
bırakıldı (üstteki `cikti/canli/kabul.*` kanıtı Plan A'nın koşumuyla
ÜZERİNE YAZILDI, ayrıca saklanmadı).

### Plan A — IMX500 tam çözünürlük (2028×1520), kam_hz 30→15 — **KALDI**

Fikir: render maliyeti çözünürlükten değil kamera `update_rate`'inden
gelsin varsayımıyla, kamera IMX500 nativine geri döndürüldü
(`veri/gazebo_canli.py:canli_senaryo`, `odak_px=1561`) ve `kam_hz`
30'dan 15'e düşürüldü (`CANLI_HZ`) — takip sabitleri (R_MERDIVEN,
KORUMA_ESIK) DEĞİŞTİRİLMEDİ (IMX500 nativ için zaten kalibreler).

| Ölçüt | Sonuç | Durum |
|---|---|---|
| FPS ≥ 15 | **4.65** (236 kare, 60 s) | **KALDI** |
| Kilit oranı ≥ %90 | **%2.5** | **KALDI** |
| 50→200 m / 60 s tırmanış | Yalnız **130.9 m**'ye ulaşıldı | KALDI (bilgi) |

**Kök neden (ölçüldü):** `update_rate` yarılanması FPS'i DÜŞÜRDÜ,
YÜKSELTMEDİ — önceki "bağlantı-testi" RTF/FPS ölçümü (IMX500 kam_hz=30
için ~6.6 FPS) yalnız gz-sim↔bridge bağlantısını ölçüyordu, YOLO +
takip CPU yükü YOKTU. Tam takip hattıyla (bu script) IMX500 tam
çözünürlükte kare başına render+kırpma+YOLO maliyeti o kadar yüksek ki
düşük update_rate ile "daha az kare işlensin, her biri aynı hızda
işlensin" beklentisi gerçekleşmedi — render/CPU maliyeti update_rate'e
DEĞİL çözünürlüğe bağlıymış (deneyle doğrulandı, hipotez ÇÜRÜTÜLDÜ).

Kanıt: `cikti/canli/kabul.json` (özet), `cikti/canli/kabul.jsonl` (kare
başına durum/px/irtifa), `cikti/canli/kabul.mp4` (ham görüntü) — bu
dosyalar Plan A'nın sonucunu taşır (640×480 denemesinin kanıtı Plan
A'nın kaydıyla ÜZERİNE YAZILDI).

### Plan B — yarı-doğrusal çözünürlük (1014×760) + TUVAL_OLCEK ölçekleme — **KALDI (regresyon kapısında)**

Fikir: IMX500'ün TAM YARISI (2028/2×1520/2=1014×760, odak_px=1561/2=
780.5 — FOV AYNI kalır) + sensor-px sabitlerini (`demo_ayar.R_MERDIVEN`,
`takip.izleyici.HedefTakip.koruma_esik`, `.min_kenar`) bu kameraya göre
`TUVAL_OLCEK=0.5` ile yeniden ölçeklemek. Altyapı eklendi (KALICI,
davranışı TUVAL_OLCEK verilmezse BİREBİR eskisi gibi):

- `demo_ayar.ayarla_tuval_olcek(k)`: `R_MERDIVEN`'i `_R_MERDIVEN_1X`
  tabanından `k` ile yeniden hesaplar. `BANT`/`NET_HEDEF` (ağ-girdisi
  bandı, resize SONRASI sabit `AG` kanvasında ölçer) BİLEREK
  DEĞİŞTİRİLMEZ (talimat).
- `HedefTakip(koruma_esik=..., min_kenar=...)` — yeni, isteğe bağlı
  kwargs (`takip/izleyici.py`); `None` ise (varsayılan) davranış
  BİREBİR eskisi gibi.
- `main.py --tuval-olcek K` (varsayılan 1.0) — `--mod demo`'da yukarıdaki
  ikisini otomatik uygular.
- `gazebo/kabul_canli.py` bunları CANLI kaynak için `CANLI_TUVAL_OLCEK`
  (=0.5) ile doğrudan uygular (CLI argparse'a girmez, `kos()`'a doğrudan
  geçirilir).

**Regresyon (talimat: canlı kabule geçmeden ÖNCE koşulmalı):** kayıtlı
`Demo_kucul` `gazebo/kaydet.py` ile YENİDEN kaydedildi (deterministik,
`kareler/` diski tasarrufu için gitignore'lu ve silinmişti — orijinal
kayıt dosyaları [`pozlar.csv`/`meta.json`/`dunya.sdf`/`imu.csv`] test
SONRASI `git checkout` ile GERİ ALINDI, kalıcı bir değişiklik YOK), sonra
`--hedef-genislik 1014 --tuval-olcek 0.5` ile taban (`--tuval-olcek 1.0`,
aynı yeniden-kayıt üzerinde adil kıyas için) ile karşılaştırıldı:

| Ölçüt | Taban (2028×1520, ölçeksiz) | 1014×760 + TUVAL_OLCEK=0.5 |
|---|---|---|
| Kilit oranı | %93.0 | **%43.1** |
| IoU | 0.749 (@0.5 %95.8) | 0.505 (@0.5 %60.8) |
| Hassasiyet (merkez hatası) | %96.2 | %64.7 |
| Hedef boyut (ort.) | 62.6×45.7 px | 31.3×22.8 px (tam yarı, beklenen) |
| Durum dağılımı (1185 kare) | KILITLI 969, ARAMA 100, KAYIP 68, ŞÜPHELİ 48 | KILITLI 448, ARAMA 388, KAYIP 281, ŞÜPHELİ 68 |

**Kabul ölçütü (kilit ≥%95) KALDI — canlı kabul bu nedenle KOŞULMADI**
(talimat: regresyon geçmeden canlıya geçilmeyecek).

**Kök neden (ölçüldü, ölçeklenebilir bir sabit HATASI DEĞİL):** durum
geçiş izini incelendiğinde (`cikti/regresyon_1014/Demo_kucul.jsonl`)
hata GRADÜEL bir bozulma değil TEK BÜYÜK bir kopma: kare ~535'te
(irtifa ~121 m, hedef ~29px) ARAMA'ya giriyor ve klip sonuna kadar (650
kare, irtifa 121→210 m) BİR DAHA HİÇ KİLİTLENEMİYOR. Taban kayıtta AYNI
tür bir kopma var (kare 741, irtifa ~152 m) ama kare 890'da (irtifa
~183 m) TOPARLANIYOR. `R_MERDIVEN`/`koruma_esik`/`min_kenar` ölçeklemesi
DOĞRU çalışıyor (hedef boyutu tam yarıya düşüyor, R seçim oranı
`L_native*AG[0]/R` matematiksel olarak DEĞİŞMİYOR) — sorun kalibrasyon
DEĞİL, GERÇEK bilgi kaybı: 1014px genişlikte bir kırpma, aynı sahne
alanını 2028px'e göre YARI SAYIDA gerçek örnekle (piksel) yakalıyor;
dijital upscale (AG=640'a resize) bu eksik bilgiyi geri getirmiyor.
Hedef irtifa arttıkça (native px küçüldükçe) bu bilgi açığı büyüyor ve
bir eşikten sonra (~120 m/~29px bu klipte) YOLO/A6 modeli hedefi bir
daha GÜVENİLİR bulamıyor. Bu, düşük nativ sensör çözünürlüğünün fiziksel
bir sınırı — TUVAL_OLCEK gibi bir sabit-yeniden-ölçekleme ile
DÜZELTİLEMEZ (aynı kısıt zaten Plan A/B'nin var olma nedeniydi).

**Düzeltilmedi (kapsam dışı bırakıldı — bu turun ikisi de kapsamıydı,
üçüncü bir yol DENENMEDİ):** olası yönler (1) IMX500 tam çözünürlükte
kalıp render/YOLO maliyetini GERÇEKTEN düşürecek bir optimizasyon
(ONNX/int8, GPU, ROI-öncelikli render vb. — Plan A'nın update_rate
denemesi bunu YAPMADIĞI için başarısız oldu), (2) düşük-çözünürlük
rejiminde re-edinme stratejisini (KaroArayici tarama/eşik) native
piksel yoğunluğuna göre YENİDEN TASARLAMAK (basit sabit ölçekleme değil
— kendi teşhis turu ister), (3) daha güçlü/GPU'lu donanım beklemek. Bu
turun kapsamı yalnız kullanıcının verdiği A/B planını yürütüp ölçmekti.

Kanıt: `cikti/regresyon_1014/Demo_kucul.jsonl` (1014×760 koşumu, kare
başına durum/px), `cikti/regresyon_1014/Demo_kucul.mp4` (aynı koşumun
görüntüsü). Taban koşumun (2028×1520, aynı yeniden-kayıt) kanıtı
saklanmadı (yalnız bu tablodaki özet sayılar) — kaynak kareler zaten
`git checkout` ile geri alınan geçici bir yeniden-kayıttı.

**GÜNCELLEME (2026-09-08) — yukarıdaki "fiziksel sınır" hükmü GERİ
ÇEKİLDİ:** ayrı bir teşhis turunda (bkz. `docs/DURUM.md`) render'ın
CPU/llvmpipe'a ZORUNLU kalmasının GPU sürücü çökmesinden kaynaklandığı
bulundu, düzeltildi (aşağıya bkz.) — Plan B'nin regresyon kopması da
muhtemelen main'deki D1/D2 ile aynı re-edinme sağlamlığı arızası
(TUVAL_OLCEK'ten bağımsız). Bu yüzden canlı mod artık **IMX500 nativ
çözünürlüğe (2028×1520, TUVAL_OLCEK=1.0) geri döndürüldü** — Plan B'nin
1014×760 + ölçekleme ayarı ARTIK KULLANILMIYOR (altyapısı kalıcı
bırakıldı, ihtiyaç olursa).

### GPU etkinleştirme — YOLO cihazı + Gazebo render (2026-09-08)

**1) YOLO `device="cuda"` + `half=True` (fp16):** `demo_ayar.py`'de
`model.predict(..., device="cpu")` → `device=YOLO_DEVICE, half=YOLO_HALF`
(`YOLO_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"`).
Kayıtlı `Demo_kucul` (2028×1520, yeniden kaydedilip test sonrası geri
alındı) üzerinde önce/sonra:

| | FPS | Kilit oranı | IoU | Hassasiyet |
|---|---|---|---|---|
| Önce (CPU) | 32.9 | %93.8 | 0.754 | %97.3 |
| Sonra (CUDA+fp16) | **43.6** (+%32) | %94.0 (**Δ+0.2pp, ±%1 içinde**) | 0.757 | %97.4 |

Kilit oranı kriteri (±%1) karşılandı. `half=True` ultralytics'te
"deprecated, `quantize` kullanın" uyarısı veriyor ama ÇALIŞIYOR (fp16
uygulanıyor) — ileride ultralytics güncellendiğinde `quantize`'a
geçilmesi gerekebilir, kapsam dışı bırakıldı.

**2) Gazebo GPU render:** `veri/gazebo_canli.py:_sim_baslat()`'ta
`LIBGL_ALWAYS_SOFTWARE` AÇIKÇA kaldırıldı (ambiyan kabukta zaten "1"
ayarlıydı — `setdefault` yetmez), `MESA_D3D12_DEFAULT_ADAPTER_NAME=
"NVIDIA"` eklendi. IMX500 nativ (2028×1520), kamera açık, ayrı deneyler
(`/tmp` scratchpad, repo kodu değiştirilmeden):

| Deneme | Render motoru | Sonuç | RTF (18 s pencere) | Kamera FPS |
|---|---|---|---|---|
| NVIDIA zorlanmış, varsayılan (ogre2) | ogre2, `GL_RENDERER = D3D12 (NVIDIA GeForce RTX 3060 Laptop GPU)` | **ÇÖKMEDİ** | **~0.97** (29 örnek, 1 aykırı değer 0.28 hariç istikrarlı ~0.95-1.02) | 30.7 |
| NVIDIA zorlanmış, `--render-engine ogre` (legacy) | ogre1 | **ÇÖKMEDİ** | **~0.99** (32 örnek, 0.93-1.03 bandı) | 36.5 |

Her ikisi de ÇALIŞTI — `--render-engine ogre` denemesine gerek kalmadı
ama talimat gereği yine de koşuldu (bonus doğrulama). **Kök neden
(önceki teşhiste bulunan):** `LIBGL_ALWAYS_SOFTWARE` kaldırılıp adaptör
ZORLANMADIĞINDA D3D12/Mesa WSL katmanı varsayılan olarak Intel iGPU'yu
seçiyor, Intel'in gömülü LLVM-14 sürücüsü Mesa'nın kendi LLVM-15'iyle
aynı komut satırı bayrağını (`spirv-expand-step`) çakışan şekilde
kaydedip `abort()` ediyordu — `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA`
bu seçimi NVIDIA'ya zorlayıp çökmeyi ortadan kaldırdı.

**Gerçek koda uygulandı, gerçek bağlantıyla doğrulandı** (`GazeboCanliKaynak`
üzerinden, takipçi/YOLO OLMADAN, yalnız bağlantı+kare okuma — bu, canlı
KABUL testi DEĞİL, D1/D2 merge'ine kadar o koşulmuyor):
**28.81 gerçek FPS, IMX500 nativ 2028×1520, 15 s pencere, 433 kare.**

**Genelleştirilebilirlik uyarısı:** bu düzeltme (`MESA_D3D12_DEFAULT_
ADAPTER_NAME=NVIDIA`) bu makineye (WSL2, Intel iGPU + NVIDIA RTX 3060
ikili GPU) özgü ölçüldü — başka bir GPU/sürücü/WSL2 sürümünde YENİDEN
ÇÖKEBİLİR. Ayrıntı ve geri-dönüş talimatı `docs/KURULUM.md` §5b.

**Canlı kabul testi (`gazebo/kabul_canli.py`) HÂLÂ KOŞULMADI** —
kullanıcı talimatı: main'deki D1/D2 `demo-canli`'ye merge edilene kadar
ertelendi (Plan B'nin regresyon arızasıyla AYNI kök neden olabileceği
için). GPU değişiklikleri yalnız YAPILANDIRMA/ALTYAPI olarak hazır
bekliyor.
