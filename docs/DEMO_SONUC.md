# Demo Sonuçları (v1) — 2026-09-07

`--mod demo` (N_TESPIT=2, dedektor_karar), GT ile ölçüldü. Kayıtlar:
`data/gazebo/Demo_kucul` (50→210 m, 1200 kare), `Demo_celdirici` (sabit
80 m, 1791 kare, 60 s), `Demo_kopus` (sabit 80 m, 1800 kare, 60 s). Ham +
HUD'lu videolar `cikti/demo/`, kare başına durum `cikti/demo/*.jsonl`.

**Kural (talimat gereği):** KALAN (geçemeyen) senaryo düzeltilmedi —
sonuç olduğu gibi raporlanıyor.

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
