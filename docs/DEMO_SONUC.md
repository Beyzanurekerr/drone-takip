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
