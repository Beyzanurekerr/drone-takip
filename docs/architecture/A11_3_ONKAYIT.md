# A11.3 — T2 DCF Düzeltme A/B + Y1.2 Dikiş (ön-kayıt + sonuç)

Talimat (2026-09-04, birebir):

```
A11.3 — T2 DCF DÜZELTME A/B + Y1.2 DİKİŞ.

T2 (Y1_A1_taban_500k birincil, A2–A6 regresyon; K1–K6; takip/
md5 sabit, monkey-patch; ön-kayıtlı sabitler mevcut kod
sabitlerinden, yeni sayı yok):
  T2a şablon güncelleme kapısı: ikinci-tepe oranı (T1c) eşiği
      geçince güncelleme atlanır. Eşik T1c'nin kopuş-öncesi
      dağılımından ÖNCEDEN (p95 sağlıklı).
  T2b uzamsal güvenilirlik maskesi: renk modelinden
      hedef/arkaplan olasılık haritası, şablon güncellemesi
      yalnızca hedef olasılığı yüksek piksellerden (CSR-DCF
      ilkesi, öğrenme yok).
  T2c rafine_kutu bağımsız-bileşen kapısı (T1 önerisi aynen).
  T2d = a+b+c yalnızca üçü de tek başına K6'yı geçtiyse.
  Ölç: ilk yanlış-kilit karesi, yanlış-kilit oranı, en-boy
  serisi, IoU, PSR, ikinci-tepe. Hedef: A1'de ≥300 kare.

Y1.2: [bkz. bu belgenin ikinci yarısı]

Y2/Y3 ön-koşulu aynen: T2'den K6 geçen bir düzeltme + Y1 kapısı.
Commit her adım, push yok. DUR.
```

`takip/izleyici.py` ve `takip/cekirdekler.py` **DEĞİŞMEDİ** — tüm kollar
`gazebo/tani_a11_3_t2.py` içinde monkeypatch/instance-attribute ile.

**ÖNEMLİ BAĞLAM:** T1 (A11.2) `Y1_A1_taban_500k`'yı Y1.1'in yama
genişletmesinden ÖNCEKİ zeminle ölçmüştü (ilk yanlış-kilit t=8). Y1.1
zemini tamamen değiştirdiği için (4 sahneli bileşik) T2, sahneyi YENİDEN
kaydedilmiş (post-Y1.1) `Y1_A1_taban_500k` üzerinde, kendi TAZE H0
taban değeriyle karşılaştırıyor — H0 artık **t=106**'da kırılıyor, t=8
değil. Bu bir tutarsızlık değil: T2 hep AYNI (güncel) dünyanın H0'ına
karşı ölçüyor, mutlak sayı Y1.1 ile birlikte değişti.

## Eşik ön-kaydı (T2a)
T1c'nin **SAĞLIKLI** karelerinden (`durum==KİLİTLİ` ve `IoU≥0.5`,
A9_KABUL_OLCUTU.md EK-1 "doğru hedef" tanımı) toplanan ikinci-tepe oranı
dağılımı — A1(500k) + A2-A6 (yama-içi) havuzlanmış, **n=416**, **P95 =
0.1582**. Bu eşik T2a'yı koşmadan önce sabitlendi, sonucuna bakılmadı.

## Sonuçlar

### A1 birincil (Y1_A1_taban_500k, 500 kare)

| Kol | ilk yanlış-kilit | yk oranı | IoU ort | eb maks |
|---|---:|---:|---:|---:|
| H0 (taze taban) | 106 | 0.426 | 0.124 | 1.099 |
| T2a (şablon kapısı) | 112 | 0.163 | **0.535** | 0.966 |
| T2b (renk maskesi) | 106 | 0.269 | 0.235 | 0.914 |
| T2c (rafine oran kapısı) | 106 | 0.462 | 0.124 (=H0) | 1.099 (=H0) |

### K6 (H0'a karşı, 6 senaryonun TAMAMINDA geçmeli)

| Kol | K6 |
|---|---|
| T2a | **KALDI** — A4_irtifa'da IoU ort −0.041 düşüyor (sınır −0.03) |
| T2b | **GEÇTİ** (tümünde) |
| T2c | **KALDI** — A1/A3/A4/A6'da yanlış-kilit SAYISI ARTIYOR (+12,+29,+32,+12) |

**T2d KOŞULMADI** — üçünün hepsi K6'yı geçmedi (yalnız T2b geçti).

**A1 hedefi (≥300 kare):** hiçbiri başaramadı (H0 106, T2a 112, T2b 106,
T2c 106 — hepsi 300'ün çok altında).

## Yorum — üç önlemin GERÇEK YENİ dünyada davranışı T1'den FARKLI

- **T2a genel kaliteyi çarpıcı biçimde iyileştiriyor** (A1 IoU ort
  0.124→0.535, yk oranı 0.426→0.163) ama **ilk kırılmayı ERTELEMİYOR**
  (106→112, ihmal edilebilir) — şablon güncellemesini durdurmak,
  KOPTUKTAN SONRA daha az kötüleşmeyi sağlıyor (muhtemelen yanlış şeyi
  öğrenmeyi engelliyor) ama kopuşun KENDİSİNİ önlemiyor. A4_irtifa'da net
  bir regresyon var, K6'yı düşürüyor.
- **T2b tek başına en güvenli seçenek** — her yerde K6 geçiyor, A1'de
  gerçek (küçük ama tutarlı) bir iyileşme var. Ama etkisi mütevazı: ilk
  kırılma zamanı DEĞİŞMİYOR (106=106), yalnızca kırıldıktan SONRAKI
  davranış biraz düzeliyor.
- **T2c bu turda NEREDEYSE ETKİSİZ, hatta ZARARLI.** A1'de H0 ile
  BİREBİR aynı (ilk kırılma, IoU ort, eb maks — hepsi özdeş) — yani bu
  YENİ dünyada `rafine_kutu`'nun orantısız ölçümü artık A1'in birincil
  kırılma nedeni DEĞİL (T1'in eski-dünya bulgusunun aksine). Dahası,
  A1/A3/A4/A6'da yanlış-kilit SAYISINI ARTIRIYOR — reddedilen rafine
  sonuçları yerine daha bayat/kötü boyut tahminleriyle devam etmek bazı
  durumlarda daha kötü.
- **Genel sonuç: hiçbir tekli önlem A1'i 300 kareye taşımıyor.** T1'in
  eski-dünya teşhisi (rafine_kutu → dikey şişme → kayma) bu YENİ, çok-
  sahneli dünyada baskın mekanizma değil; muhtemelen Y1.1'in kendi bulduğu
  "dikiş/çifte-pozlama" artefaktı (bkz. Y1.2 bölümü) burada da rol
  oynuyor — hedef sık sık gerçek-doku dikişlerinin yakınından geçiyor ve
  DCF orada zaten bozuk bir görüntüyle karşılaşıyor, üç düzeltme de bunu
  hedef almıyor.

**Y2/Y3 KOŞULMADI** — T2b K6'yı geçti ama A1'i 300 kareye TAŞIMADI, ve Y1
kapısı (aşağıda) zaten KALDI durumda. Talimatın çift koşulu ("T2'den K6
geçen bir düzeltme + Y1 kapısı") sağlanmıyor.

Ham veri: `cikti/a11_3_t2.json`.

---

## Y1.2 — DİKİŞ (ön-kayıt + sonuç)

Talimat (birebir): *"Izgarayı operasyon alanı tek karo içinde kalacak
şekilde kaydır; dikiş_yakini bayrağı; feather genişliği ∈ {dar, mevcut}
ölç. Kapı İKİ YÖNLÜ: |Gazebo − gerçek| ≤ 0.10, aşağı ve yukarı. Yukarı
kalırsa Y1.2'ye gürültü/bulanıklık modeli eklenir (ön-kayıt, sonra)."*

### Izgara kaydırıldı
Operasyon zarfı (`gazebo/senaryolar.py:Y1_AILE` entegrasyonu ile ölçüldü):
`x∈[−68.8, 72.0]`, `y∈[−9.0, 29.1]`. 15 m pay eklenip `x∈[−84,87]`
(171 m), `y∈[−24,44]` (68 m) hedef alındı. Hücre boyutu büyütüldü
(`gazebo/y1_yama_uret.py`: `1300×750 px` = 177.7×102.5 m/hücre, önceki
1100×650) ki bu zarf **TEK hücreye** sığsın. Izgara kesişimi
(`GERCEK_ZEMIN_MERKEZ_M`) operasyon alanının merkezinden **bir yarım-
hücre kadar** kaydırıldı: `(16, −2) → (90.35, −41.25)`. Sonuç: 4 sahne
hâlâ var (300.8→**355.5×205.1 m**, ≥300×170 m talimatı hâlâ geçiliyor),
ama artık hepsi operasyon alanının **dışında**.

**Kaynak-dosya kendine-referans hatası bulundu ve düzeltildi:**
`y1_yama_uret.py`, sol-üst hücreyi `zemin_gercek_kirpim.png`'den
okuyordu — ama script HER KOŞUMDA aynı dosyanın ÜZERİNE yazıyor. İkinci
koşum (Y1.2) kendi ÖNCEKİ (2×2 bileşik) çıktısını girdi olarak
okuyup yeniden gömecekti (sessiz bozulma — "bileşik içinde bileşik").
Orijinal tek-sahne dosyası git geçmişinden (`0947aa4`) kurtarılıp
`zemin_gercek_kirpim_v1_tek.png` olarak **değişmez** bir girdi haline
getirildi; `zemin_gercek_kirpim.png` artık YALNIZ çıktı.

### dikiş_yakini bayrağı ve kontrol ölçümü
`gazebo/y1_ortak.py:dikis_yakini_mi()` — kamera GERÇEKTEN yamayı
görüyorken (kendisi yama sınırları içindeyken, aksi hâlde yüksek irtifada
yarıçap devasa büyüyüp dikişi anlamsızca "uzaktan" kapsıyordu — bu ilk
sürümde bulunup düzeltildi), görüş alanının iç dikişlerden birine
yarıçap kadar yakın olup olmadığını döner.

**Ölçüldü (6 senaryo, 2400 kare):** yama-içi karelerin (n=1159) yalnızca
**%10.2'si (118 kare)** artık dikişe yakın — Y1.1'de bu oran fiilen
operasyon alanının TAMAMIYDI (kesişim tam merkezdeydi). Kaydırma
niyet edilen etkiyi yapıyor, sıfıra indirmese de.

### Kapı yeniden ölçüldü (A6, ±0.10, aynı gerçek-veri referansı)

| Ölçüt | Y1.1 (kaymamış) | **Y1.2 (kaydırılmış)** | referans | Y1.2 sonuç |
|---|---:|---:|---:|---|
| tam-kare @40px | 0.089 | **0.733** | 0.750 | fark −0.017 → **GEÇTİ** |
| ROI-4× @40px | 0.970 | 0.970 | 0.750 | fark +0.220 → KALDI (yukarı) |
| ROI-4× @20px | 0.754 (n=122) | ölçülemedi (n=0) | 0.2125 | KALDI (veri yok) |

**Tam-kare @40px, dikiş düzeltmesiyle 0.089 → 0.733'e sıçradı ve ARTIK
GEÇİYOR** — bu, Y1.1'in "dikiş = çifte pozlama" teşhisinin doğru
olduğunun doğrudan kanıtı: sorunu çözen şey ne modelin ne de gerçek-veri
referansının değişmesiydi, yalnızca dikişlerin operasyon alanının
dışına taşınmasıydı.

**ROI hâlâ KALDI, ama YUKARI yönde** (Gazebo 0.970 ≫ gerçek 0.750) —
talimatın öngördüğü tam bu durum: *"Yukarı kalırsa Y1.2'ye gürültü/
bulanıklık modeli eklenir (ön-kayıt, sonra)."* **ÖN-KAYIT (uygulanmadı,
sıradaki adım):** ROI'nin gerçek veriden bu kadar iyi çıkmasının en
olası nedeni, Gazebo render'ının VisDrone'un gerçek kamera/sıkıştırma
zincirinde bulunan hareket bulanıklığı, sensör gürültüsü ve JPEG
sıkıştırma artefaktlarından ARINMIŞ olması — ROI'nin 4× büyütmesi bu
"temiz" görüntüde neredeyse mükemmel çalışıyor, gerçek dünyada
bulanıklaşan kenarlar üzerinde çalışamayacağı kadar iyi. Öneri: kareye
hafif Gaussian bulanıklık + sensör gürültüsü (mevcut `sim/world.py` ya
da SDF `<noise>` bloğundaki ZATEN VAR OLAN gürültü mekanizması
büyütülerek) eklenip ROI recall'ünün gerçek referansa yaklaşıp
yaklaşmadığı ölçülmeli.

**20px verisi hâlâ yok** — ızgara kaydırması, kapsamı ~%48'e düşürdü
(Y1.1'in %58.5'inden) ve özellikle en yüksek irtifa (20px hedef boyutu)
aralığını yama dışına itti. Dikiş ile kapsam arasında bir ödünleşim var;
bu turda dikiş önceliklendirildi (talimatın açık isteği).

### Feather genişliği (dar vs mevcut) — BU TURDA ÖLÇÜLMEDİ
Zaman kısıtı nedeniyle yalnız `T=60` (mevcut) tam ölçüldü. `T=20` (dar)
karşılaştırması için altyapı hazır (`y1_yama_uret.py:uret(t=...)` ve
`yaz(cikti_adi=..., t=...)` parametrik) ama Gazebo'da yeniden kayıt
gerektirdiği için (yalnız statik doku değil, gerçek render) bu turda
koşulmadı. **Sıradaki adım (ön-kaydedildi, sonra):** `Y1_A2_kucul`'u
(dikişe en yakın geçen senaryolardan biri) hem T=60 hem T=20 ile
yeniden kaydedip yalnız `dikis_yakini` alt kümesinde recall kıyaslamak.

### Genel kapı: hâlâ KALDI, ama nitelik değişti
Y1.1'de üç alt-ölçütün hepsi ciddi biçimde kalıyordu (özellikle tam-kare
çökmüştü). Y1.2'de **tam-kare artık geçiyor**; kalan iki açık madde
(ROI'nin gerçek-üstü performansı, 20px veri boşluğu) farklı, daha dar
kapsamlı sorunlar — her ikisi de yukarıda somut, ön-kayıtlı bir sıradaki
adımla eşleşiyor.

**Y2/Y3 KOŞULMADI.** Talimatın çift koşulu ("T2'den K6 geçen bir
düzeltme + Y1 kapısı") sağlanmıyor: Y1 kapısı hâlâ genel olarak KALDI
(yalnız bir alt-ölçütü geçti), ve T2'nin K6 geçen tek kolu (T2b) A1'i
300 kareye taşımadı. **DUR.**

Ham veri: `cikti/a11_2_y11_kapi.json` (bu ölçümle üzerine yazıldı —
Y1.1'in eski sonucu artık yalnız bu belgenin Y1.1 bölümünde/git
geçmişinde duruyor).
