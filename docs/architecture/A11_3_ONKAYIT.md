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

(Bu bölüm aşağıda, aynı turda tamamlandı.)
