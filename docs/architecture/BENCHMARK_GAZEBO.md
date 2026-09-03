# Benchmark Baseline — GAZEBO (A3.9 Faz A)

Aşama 3.9 Faz A'da dondurulan referans değerler (24 Ağustos 2026).

> **Bu dosya yalnızca Gazebo kontrollü senaryo sonuçlarını içerir.**
> `BENCHMARK_BASELINE.md` (sim) ve `RAPOR_VISDRONE.md` (gerçek veri)
> tablolarıyla **birleştirilmemelidir**. Üçü farklı şeyleri ölçer:
> sim → hedef boyutunun kontrollü süpürülmesi; VisDrone → gerçek kamera
> hareketi ve gerçek gürültü; Gazebo → **kamera hareketinin kontrollü
> süpürülmesi**, kusursuz ground-truth ile.

**Bu dosyanın amacı:** A3.9'un çözüm fazında (Faz C) yapılacak her değişiklik
bu sayılarla karşılaştırılacak. Bu tablo **A3.8 takipçisiyle**, `takip/`
altındaki beş dosyanın hiçbirine dokunulmadan alınmıştır.

## Ölçüm ortamı

| | |
|---|---|
| Makine | WSL2 Ubuntu 22.04, Linux 6.6.114.1 |
| Gazebo | gz sim 8.14.0 (Harmonic), `-s -r --headless-rendering` |
| Render | llvmpipe (yazılım, `LIBGL_ALWAYS_SOFTWARE=1`) |
| Python | 3.10, opencv-python 4.11.0, numpy 1.26.4 |
| Çözünürlük | 640 × 480 |
| Çekirdek | `renk_dcf` (varsayılan) |
| Takipçi | **A3.8** (`9a058c7` sonrası, `takip/` değişmedi) |
| Kayıt | `python3 -m gazebo.kaydet G0` |
| Ölçüm | `python3 main.py --source gazebo --dataset data/gazebo --sequence G0 --penceresiz` |

Kamera parametreleri bilerek `sim/world.py` ile hizalandı: odak 500 px,
irtifa 45 m → 11.1 px/m → hedef ~56 × 22 px. Bu, sim `test1_yakin`'in hedef
boyutuyla aynı banttadır.

## G0 — kontrol senaryosu

**Sabit nadir kamera (45 m) + sabit hızla düz ilerleyen hedef (4.8 m/s).**
Kamera hiç hareket etmez; `e_ego = 0` ucu. Amaç Gazebo'nun kendisinin
takipçiye regresyon getirip getirmediğini ölçmektir.

| metrik | değer |
|---|---|
| IoU | **0.912** |
| @0.5 | 100.0% |
| @0.3 | 100.0% |
| merkez hata (medyan) | 1.24 px |
| hassasiyet | 100.0% |
| kilit oranı | 100.0% |
| hedef kayıp | 0.0% |
| kurtarma | 0 kesinti |
| **drift karesi** | **yok** |
| ID switch | 0 |
| FPS | 341.7 |
| gecikme p50 / p95 / max | 2.55 / 4.66 / 18.22 ms |
| ölçülen kare | 294 (kilit sonrası) |
| hedef boyutu | 56.5 × 22.3 px |

**Kabul kriteri IoU > 0.85 — geçti (0.912).**

### Sim baseline ile yan yana

Aynı büyüklük bandındaki sim senaryosuyla karşılaştırma. İki hat ayrı kalır;
bu tablo yalnızca "Gazebo bir regresyon getirdi mi" sorusunu yanıtlar.

| | sim `test1_yakin` | Gazebo `G0` | fark |
|---|---|---|---|
| IoU | 0.925 | 0.912 | −0.013 |
| @0.5 | 100.0% | 100.0% | — |
| hassasiyet | 100.0% | 100.0% | — |
| merkez hata | 0.25 px | 1.24 px | +0.99 px |
| kilit | 100.0% | 100.0% | — |
| ID switch | 0 | 0 | — |
| FPS | 338 | 342 | +4 |

**Sonuç: Gazebo takipçiye anlamlı bir regresyon getirmiyor.** Merkez
hatasındaki +0.99 px'lik farkın kaynağı takipçi değil, **GT tanımı**: Gazebo
GT'si aracın 3B kutusunun sekiz köşesinin izdüşümüdür, yani araç yüksekliği
(1.5 m) nadir olmayan bakış açısıyla kutuyu biraz büyütür. Sim GT'si ise
düzlemsel dört köşedir. İki tanım aynı fiziksel aracı ölçer ama Gazebo kutusu
sistematik olarak birkaç piksel daha büyüktür.

## Kayıt sağlığı

| | |
|---|---|
| Kaydedilen kare | 300 / 300 |
| Düşen kare | **0** |
| Çözünürlük | 640 × 480 (`/camera_info` ile doğrulandı) |
| Kare aralığı | 0.0333 s (min 0.0292, maks 0.0333) |
| Senkron boşluğu | ort **2.67 ms**, maks **4.17 ms** (tolerans 20 ms) |
| Gazebo RTF | **1.01** |
| Kayıt süresi | 12.4 s |

## Ego-motion sağlığı

Sabit kamerada `M` birim matrise yakın olmalı. Ölçülen (299 kare):

| | p50 | p95 | maks |
|---|---|---|---|
| ego güveni (içerik oranı) | 1.000 | 1.000 | 1.000 |
| kayma \|t\| | 0.120 px | 0.303 px | 0.339 px |
| ölçek \|s−1\| | 0.0003 | 0.0007 | 0.0008 |
| dönme | 0.004° | 0.006° | 0.008° |
| LK nokta sayısı | 100 | 100 | 100 |

- `M` birim matrise **hiç düşmedi** (0/299)
- ego güveni hiçbir karede 0.5'in altına inmedi

**Render/doku riski gerçekleşmedi.** llvmpipe yazılım render'ıyla üretilen
zemin dokusu ego-motion'a fazlasıyla yetiyor: her karede azami nokta sayısı
(100) bulunuyor ve RANSAC içerik oranı %100. Faz A öncesinde bu en büyük
teşhis riski olarak işaretlenmişti; G0 onu kapatıyor.

## Üretilen dosyalar

```
gazebo/dunya_uret.py   zemin dokusu (2048²) + SDF üretici
gazebo/senaryolar.py   G0 tanımı (araç + kamera yörüngeleri)
gazebo/kaydet.py       başsız sim + gz.transport kaydı -> diske
veri/gazebo.py         GazeboKaynak: kayıt -> Kare (GT dahil)
```

`kaynak.py`'ye tek dal (`"gazebo:<senaryo>"`), `main.py`'ye tek metrik
(`t_drift`) eklendi. `takip/` · `sim/` · `calistir.py` · `kiyasla.py` ·
`visdrone_kiyasla.py` **değişmedi**.

## Kayıt sırasında bulunan ve düzeltilen dört tuzak

Hepsi **sessiz** hatalardı: kare sayısı ve senkron boşluğu sağlıklı
görünürken GT anlamsız oluyordu. G1–G7'de tekrarlanmaması için kayıt
altına alındı.

1. **Poz damgası yanlış yerden okunuyordu.** `Pose_V`'de damga dış header'da
   değil, her `Pose`'un kendi header'ındadır. Dış header sıfır geldiği için
   tüm kareler senkron toleransının dışında sayılıp düşüyordu (20/20).
2. **Araçlar yerçekimiyle düşüyordu.** `VelocityControl`'ün `initial_linear`'ı
   dikey hızı her adımda bastırmıyor; 14 s'de z = −22.9 m. Çözüm: link
   düzeyinde `<gravity>false</gravity>` (araçlar kinematik).
3. **`real_time_factor 0` sim zamanını uçuruyordu.** Render (llvmpipe)
   fiziğin çok gerisinde kaldığı için 14 s duvar saatinde 579 s sim
   ilerliyordu; kameranın 30 Hz'i sim zamanında tutmuyor, kareler arası
   mesafe devasa oluyordu. Çözüm: `real_time_factor 1.0`.
4. **Kaçak `gz sim` süreçleri veriyi karıştırıyordu.** Önceki bir koşumdan
   kalan sim aynı konulara yayın yapmaya devam ediyor, kaydedici iki simin
   verisini karıştırıyordu (hedef x = 5334 m). Çözüm: her koşuma
   `GZ_PARTITION` ile kendi ad alanı + kayıt yazılmadan önce akıl denetimi
   (başlangıç pozu SDF ile uyuşuyor mu, araç zemine oturuyor mu, zemin
   sınırları içinde mi).

Ek olarak iki tasarım hatası düzeltildi:

5. **Kamera yaw = 0'da hedefin yolu kadrajın yarım yüksekliğiyle
   sınırlanıyordu** (21.6 m), yarım genişliğiyle değil (28.8 m); hedef ilk 19
   karede kadraj dışında kalıyordu. `kam_yaw = +90°` ile dünya +X görüntüde
   sağa düşürüldü — yerleşim `sim/world.py` ile de örtüşüyor.
6. **Zemin dokusunun UV yönü devrikti**; yol dünyada `x = sabit` bandına
   düşüyor, yani hedef asfaltta değil çimende ilerliyordu. Gazebo'nun `<box>`
   üst yüzey eşlemesi ampirik olarak ölçüldü ve doku devriği alındı.

## Sonraki adım

G0 geçtiği için Faz A'nın kalanı (G1–G7 kaydı) açılabilir. Faz C'de
(çözüm) yapılacak her değişiklik bu tabloyla karşılaştırılacak; **G0'da
düşüş olursa raporlanmak zorundadır** — G0 kamera hareketi içermediği için
orada bir düşüş, çözümün taban davranışı bozduğu anlamına gelir.
