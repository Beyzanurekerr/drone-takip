# Benchmark Baseline — WINDOWS

Windows ortamında alınan ilk referans ölçüm (20 Ağustos 2026).

> **Bu dosya WSL/Linux benchmark'ının YERİNE GEÇMEZ.**
> Simülasyon referansı `BENCHMARK_BASELINE.md`, WSL üzerindeki VisDrone
> referansı `RAPOR_VISDRONE.md` dosyasındadır. Bu üç kayıt
> **birleştirilmemeli**, tabloları tek tabloya toplanmamalıdır.
>
> Özellikle **FPS ve gecikme değerleri WSL sonuçlarıyla doğrudan
> karşılaştırılamaz.** İşletim sistemi, OpenCV GUI arka ucu, Python ortamı ve
> makinedeki anlık yük farklı; ölçülen şey aynı algoritma olsa bile aynı
> koşul değildir.

## Bu baseline'ın amacı

1. Windows üzerinde gerçek video test ortamının çalıştığını doğrulamak
2. OpenCV görüntüleme (pencere / HUD) davranışını doğrulamak
3. Sonraki **Windows** testleri için karşılaştırma referansı oluşturmak

Yani bu bir algoritma iyileştirmesi kaydı değil, **ortam doğrulaması**dır.

## Hedef nasıl belirlendi (önemli)

Bu testte hedef **kullanıcı tarafından manuel olarak seçilmedi.**

- Hedef, VisDrone annotation dosyasındaki `track_id = 23` üzerinden
  belirlendi (`--track-id 23`).
- Takipçi, bu track'in ilk göründüğü karedeki GT kutusuyla kilitlenir;
  sonraki karelerde GT yalnızca **ölçüm** için kullanılır, takipçiye
  beslenmez.
- **Fare ile kullanıcı hedef seçimi henüz yapılmadı.** Gerçek kullanıcı
  etkileşimli target selection henüz ayrı bir test olarak koşulmadı.

Bu yüzden bu rapor için doğru ifade şudur:

> Windows ortamında, önceden belirlenmiş VisDrone `track_id=23` hedefi
> üzerinde mevcut klasik takip hattının performansı ölçüldü.

"Manuel hedef seçimi başarılı oldu" ya da "kullanıcının seçtiği aracı takip
etti" **denemez** — o özellik henüz test edilmedi.

Bu ölçüm şunlar için referanstır:

- tespit + takipçi (detection + tracker) performansı
- GT kutusu ile takip kutusunun karşılaştırılması (IoU / merkez hata)
- gecikme ve FPS

## Ölçüm ortamı

| | |
|---|---|
| OS | Windows |
| Çalıştırma ortamı | Windows Python / VS Code |
| Veri kümesi | VisDrone2019-VID-val |
| Dizi | `uav0000117_02622_v` |
| Track ID | 23 (annotation'dan, elle seçim değil) |
| Çekirdek | `renk_dcf` (varsayılan) |
| Pencere | OpenCV `WINDOW_NORMAL`, 960 × 540 kutusuna sığdırılmış |

## Sonuçlar

| metrik | değer |
|---|---|
| İşlenen kare | 349 |
| FPS | 53.8 |
| Ortalama gecikme | 18.59 ms |
| p50 gecikme | 12.57 ms |
| p95 gecikme | 43.87 ms |
| max gecikme | 110.75 ms |
| IoU | 0.643 |
| @0.5 | 91.5% |
| @0.3 | 100.0% |
| Merkez hata | 11.67 px |
| Hassasiyet (precision) | 100% |
| Kilit oranı | 100% |
| Hedef kayıp | 0% |
| Kurtarma | 0 kesinti |
| Hedef boyutu | 161.5 × 148.3 px |

## Çözünürlük notu

Hedef boyutunun **161.5 × 148.3 px** çıkması, karelerin **ham çözünürlükte**
(2720 × 1530) işlendiğini gösterir — yani `--hedef-genislik` verilmemiştir.
`RAPOR_VISDRONE.md` tablosundaki aynı dizi 960 px genişliğe indirilerek
koşulduğu için hedef orada 57.0 × 52.3 px'tir (161.5 × 0.353 = 57.0).

Bu, iki kaydın neden aynı satıra yazılamayacağının **ikinci** sebebidir:
sadece işletim sistemi değil, **işlenen çözünürlük de farklıdır.**

## Tekrarlama komutu

```bash
python main.py --source visdrone --sequence uav0000117_02622_v --track-id 23
```

(`--hedef-genislik` **verilmez** — ham çözünürlük bu baseline'ın parçasıdır.)

Veri kümesi kurulumu için `README.md` → "Veri kümesini kurma".

## Windows regresyon kuralları

Bir sonraki Windows koşumu bu tabloyla karşılaştırılır, WSL tablosuyla değil.

**Regresyon sayılan:**

- IoU'nun 0.643'ün altına düşmesi (> 0.01 fark)
- Kilit oranının %100'ün altına düşmesi
- Merkez hatanın belirgin artması
- Kesinti (kurtarma olayı) sayısının 0'ın üstüne çıkması

**Regresyon sayılmayan:**

- FPS ve gecikme oynamaları. Pencere açık koşumda çizim, GUI olay döngüsü ve
  makine yükü bu sayıları belirgin biçimde değiştirir.

## Not: doğruluk taşınır, hız taşınmaz

Aynı dizi, aynı track, aynı ham çözünürlük WSL2 üzerinde de koşuldu.
Aşağıdaki satır **karşılaştırma tablosu değildir** ve iki baseline'ı
birleştirmez; yalnızca hangi metriğin ortamdan bağımsız olduğunu gösterir:

| | IoU | merkez hata | hedef boyutu | FPS | ort gecikme |
|---|---|---|---|---|---|
| Windows | 0.643 | 11.67 px | 161.5 × 148.3 px | 53.8 | 18.59 ms |
| WSL2 (aynı komut) | 0.646 | 11.59 px | 161.5 × 148.3 px | 85.5 | 11.70 ms |

- **Doğruluk metrikleri ortamlar arasında taşınıyor** (IoU farkı 0.003 —
  OpenCV sürüm farkından gelen sayısal gürültü mertebesinde).
- **Hız metrikleri taşınmıyor** — bu yüzden Windows FPS/gecikme değerleri
  yalnızca başka bir Windows koşumuyla kıyaslanır.

Buradan çıkan pratik kural: bir değişikliğin doğruluğa etkisi tek ortamda
ölçülebilir, hıza etkisi **hedef ortamda** ölçülmelidir.
