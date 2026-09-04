# A11.1 — Yatak Kapısı + KOL 2 Seçim (ön-kayıt)

Talimat (2026-09-04, birebir):

```
A11.1 — YATAK KAPISI + KOL 2 SEÇİM.

Y1 — YATAK SADAKATİ (kapı, ön-kayıtlı):
Hedef: Fuel'den gerçekçi dokulu araç mesh'i. Zemin: gerçek hava
görüntüsü dokusu (VisDrone karesi, hedefsiz kırpım). 6 senaryo
yeniden üretilir. Kapı: dedektör tam kare recall 40 px'te ≥0.8,
ROI ile 20 px'te ≥0.8 (A7/A8 bandı). Geçmezse DUR, hiçbir kol
koşma. Ayrıca raporla: renk_dcf'in doku kayması yeni yatakta
kaldı mı (A1_taban, 500 kare, IoU zaman serisi).

Y2 — KOL 2 SEÇİM (açık çevrim, takipçiye yazmaz):
Seçim kuralları ön-kayıtlı, sonuca göre değil:
  S0 en büyük blob (mevcut, kontrol)
  S1 Kalman öngörüsüne en yakın blob (d_norm)
  S2 S1 + zamansal kalıcılık: son N biriktirmenin ≥k'sında
     aynı hücrede (k ∈ {2,3}, ön-kayıtlı)
  oracle: GT'ye en yakın (üst sınır)
Ölç: merkez hatası p50/p95 seviye bazında, aday sayısı,
8×5'te kanıt oranı, yanlış aday seçimi. Çeldirici senaryolarında
ayrı tablo (K5).

Y3 — KOL 3 tekrarı yalnızca Y1 geçtiyse ve boyut girdisi olarak
dedektör kutusu kullanılarak (takipçi tahmini değil).

Yasaklar aynen. Her adım commit. DUR.
```

Sıra kesin: **Y1 geçmeden Y2/Y3 koşulmaz.** Bu belge yalnızca Y1'in
tasarım/altyapı kısmını kapsar (ölçüm henüz yapılmadı — bkz. Durum).

---

## Y1 tasarım kararları

### Araç mesh'i
**OpenRobotics / Hatchback** (Fuel, `fuel.gazebosim.org/openrobotics/models/hatchback`,
sürüm 3, ~1 MB, CC0). Gerekçe: gerçekçi gövde+cam+teker dokusu, hafif (WSL2
llvmpipe yazılım render bütçesine uygun), nadir görünümden tanınabilir siluet
(A1_taban'daki tek-kare render ile doğrulandı — bkz. Durum).

Mesh dosyaları `data/gazebo/_assets/hatchback/` altına KOPYALANDI (obj+mtl+2
doku, `model://` referansları düz dosya adına çevrildi) — Fuel'e ağ bağımlılığı
YOK, sim çalışırken tekrar indirme gerekmez, tekrarlanabilirlik için commit
edildi (küçük, ~900 KB).

**GT kutusu hizası (kritik detay):** `veri/gazebo.py:_kutu_koseleri` GT'yi
meshin render'ından DEĞİL, `Arac.L/W/H` + pose'dan analitik kurar. Mesh kendi
ekseninde SİMETRİK DEĞİL (gövde burun ağırlıklı, bbox merkezi geometrik
merkezden 0.34 m kaymış — ölçüldü: ham obj bbox X±1.070, Y[-2.344,+1.657],
Z[-0.011,+1.557]). Görsel poz `(x=-0.34355, y=0, z=-0.77261, yaw=90°)` bu
kaymayı telafi eder ki linkin kökeni (== `x0,y0` == GT kutusunun merkezi)
meshin GERÇEK bbox merkeziyle çakışsın. Telafisiz bırakılsaydı GT kutusu
render'lanan aracın ~34 cm yanında dururdu — sessiz bir GT hatası olurdu.
`Arac.L=4.0011, W=2.1405, H=1.5679` bu yüzden meshin ÖLÇÜLMÜŞ bbox'ından
alındı (kutu vasıtasıyla varsayılan `L=4.6` DEĞİL).

Kapsam: yalnız **hedef** mesh alıyor (talimat "Hedef: ... mesh'i" diyor).
Çeldiriciler kutu kalıyor — kapsam genişletilmedi.

### Zemin dokusu
Kaynak: **VisDrone2019-DET** `0000283_01001_d_0000679.jpg` (otoyol, nadire
yakın açı, 1920×1080). Kırpım `[y 200:1080, x 0:1920]` (880×1920) — üstteki
gökyüzü/ufuk şeridi atıldı. Kırpımda TEK araç kutusu vardı (1131,323,110,120,
orijinal koordinatlarda); `cv2.inpaint` (Navier-Stokes, r=15, 20 px dolgu) ile
temizlendi. Diğer 4 kutunun hepsi y<175'te, kırpımın dışında kaldı — kalan
görüntüde hiç araç YOK. Kaynak dosya ve temizlenmiş yama
`data/gazebo/_assets/zemin_gercek_kaynak.jpg` / `zemin_gercek_kirpim.png`
olarak commit edildi.

**Mozaikleme DENENDİ ve REDDEDİLDİ.** 560 m'lik tam alanı tek bir VisDrone
karesiyle kaplamak gerekiyordu (kare native çözünürlükte ~150×69 m'ye denk
düşüyor, `TEXEL_PM=12.8` — bkz. aşağıdaki not). İki mozaikleme denendi:

1. **Ayna-tekrar (2×2 flip blok + tile):** simetrik bir "kaleydoskop-X"
   deseni üretti — kırpımdaki tek baskın diyagonal yol/bariyer çizgisi, ayna
   eksenlerinde birleşip yapay, çok belirgin bir X-deseni oluşturdu. Bu,
   test etmek istediğimiz "gerçek görüntü istatistiği" değil, KENDİ ayna
   simetrimiz olurdu — DCF'nin buna kilitlenmesi gerçek bir bulgu SAYILMAZDI.
2. **Düz tekrar (tile, aynasız):** kaleydoskop yok ama net bir IZGARA deseni
   (aynı kare periyodik tekrarlıyor, beyaz şerit çizgileri düzenli aralıklarla
   yapay bir periyodik-çizgi ağı oluşturuyor) — bu da kendi başına yeni bir
   "yüksek kontrastlı statik çizgi ailesi" üretir, DCF'yi gerçek görüntüden
   değil bizim döşeme artefaktımızdan etkiler.

**Kabul edilen çözüm:** TEK, tekrarsız, aynasız yama; hedef+çeldirici
operasyon alanının merkezine (`GERCEK_ZEMIN_MERKEZ_M = (16.0, -2.0)` — hedefin
500-kare rotasının [-24, +56] orta noktası) yerleştirilir, kenarda prosedürel
tabana **60 texel (~4.7 m) feather (yumuşak alfa)** ile karışır. Prosedürel
taban (mevcut, doğrulanmış, LK köşe kaynağı olarak zaten çalışıyor) sınırın
dışında ve yüksek irtifada devam eder.

**TEXEL_PM DÜZELTİLDİ (2026-09-04, kullanıcı talimatı — "yan bulgu değil, Y1'in
özü").** `gazebo/dunya_uret.py:_zemin_dokusu_ham` artık `texel_pm`/
`icerik_zemin_m` parametreleri alıyor; verilmezse (A1-A11 arşivinin TÜM
çağrıları) davranış birebir eskisi gibi kalıyor (md5 doğrulandı, DEĞİŞMEDİ).
Y1 (`zemin_dokusu_hibrit`, `dunya_yaz`) artık `zemin_m=sen.zemin_m` (560)
üzerinden **fiili** `n/zemin_m=7.31 texel/m`'i hem prosedürel tabana HEM
yamanın kendi yerleşimine geçiriyor — ikisi artık AYNI (doğru) ölçekte.
Sonuç: yama'nın gerçek dünya kapsamı **150×69 m değil, 262.6×120.4 m**
(1920×880 px / 7.31 texel/m) — önceki ölçüm yanlış ölçekle hesaplanmıştı.
Ayrıca bu düzeltme olmadan yamanın KENDİSİ de dünyada yanlış konumda
render olurdu (istenen x=16 m yerine fiilen ~x=28 m'de çıkardı) — yani bu
yalnızca "doku ne kadar kalın görünüyor" meselesi değil, doğrudan konum
hatasıydı. **A9-A11 arşivine DOKUNULMADI** (`texel_pm`/`icerik_zemin_m`
verilmezse eski davranış), **bu yüzden Y1 sonuçları A11 ile DOĞRUDAN
KARŞILAŞTIRILAMAZ** (A11'in tüm ölçümleri hâlâ eski/tutarsız ölçekte).

`gazebo/dunya_uret.py:yama_dunya_sinirlari()` / `inpaint_dunya_bolgesi()`
bu doğru ölçekle dünya-metre AABB'leri hesaplıyor (Y2 (2) talebindeki
"inpaint konumu" ve "yama_ici" bayrağı bunları kullanıyor).

**Kapsam ölçüldü (talimat maddesi 2 — "gizleme"):** 6 senaryo × ilgili kare
sayısı = 2400 kare kaydedildi; `yama_ici_mi()` (kamera görüş alanının
köşegen yarıçapı, feather bandı HARİÇ saf gerçek piksel sınırına göre)
**1128/2400 (%47) yama-içi, 1272/2400 (%53) taşma** çıktı — A2/A5'in irtifa
rampasının büyük kısmı (kamera görüş alanı yamadan büyüdüğü andan itibaren)
taşıyor. Kapı ölçümü ve DCF zaman serisi YALNIZ yama-içi karelerden
hesaplandı (`gazebo/tani_a11_1_y1.py`, `gazebo/tani_a11_1_dcf_kayma.py`).

**`meta.json`'daki `zemin_m` alanı hâlâ 160.0 yazıyor** (`gazebo/kaydet.py:458`
`ZEMIN_M` modül sabitini yazıyor, `sen.zemin_m`'i DEĞİL) — GT hesaplamasını
ETKİLEMİYOR (`veri/gazebo.py` yalnızca araç `L/W/H` okuyor, `zemin_m`'i hiç
kullanmıyor), yalnızca metadata alanı yanlış. Pre-existing, Y1 kapsamı
dışında, yalnızca not (bu turda düzeltilmedi — kaydet.py'ye dokunmak ayrı
bir onay ister).

**`meta.json`'daki `zemin_m` alanı da hep 160.0 yazıyor** (`gazebo/kaydet.py:458`
`ZEMIN_M` modül sabitini yazıyor, `sen.zemin_m`'i DEĞİL) — GT hesaplamasını
ETKİLEMİYOR (`veri/gazebo.py` yalnızca araç `L/W/H` okuyor, `zemin_m`'i hiç
kullanmıyor), yalnızca metadata alanı yanlış. Bu da pre-existing, Y1 kapsamı
dışında, yalnızca not.

### Yeni senaryo ailesi
`gazebo/senaryolar.py`: `Y1_A1_taban` .. `Y1_A6_celdirici` — A1-A6 ile BİREBİR
aynı kinematik (kamera profili, araç hızları, çeldirici yerleşimi), TEK fark
`zemin_tipi="gercek"` + hedefin `mesh="hatchback"`. Ayrı isim/dizin kullanıldı
(`data/gazebo/Y1_*`) — arşivlenmiş A1-A6 kompozit sonuçları ÜZERİNE YAZILMADI.
`Y1_A1_taban(kare=500)` → `Y1_A1_taban_500k`, DCF-kayma raporu için.

### İki model + ROI protokolü (talimat ekleri)
`gazebo/y1_ortak.py`: **COCO** (`weights/yolov8n.pt`, sınıf [2,3,5,7]) ve
**A6** (`runs/a6/asamaB/weights/best.pt`, sınıf [0,1,2,3] — UAVDT→VisDrone
fine-tune, `A6_KUCUK_HEDEF_FINAL_BENCHMARK.md`'deki nihai ağırlık) ayrı ayrı
ölçülüyor. Protokol A6 raporuyla AYNI: `conf=0.25, imgsz=640`,
`recall@IoU>=0.5`. **ROI 4×:** `gazebo/a11_ortak.py:roi_tespit_g` (A7/A8 ile
BİREBİR kırp→büyüt→YOLO→geri-dönüştür geometrisi), `R=160` — A7'nin
1280px'lik VisDrone sensör tuvalindeki "roi320" (4×) katmanının bizim 640px'lik
Gazebo karemize ORANSAL karşılığı (`R = 640 × 320/1280 = 160`). ROI merkezi
**GT'den** alınıyor (izleyicinin Kalman öngörüsünden DEĞİL) — Y1 kapısı
dedektör+ROI'nin KENDİ yeteneğini ölçüyor, izleyici zincirinin robustluğunu
değil; bu kısıt bilinçli ve Y2'nin konusu.

### Inpaint edilen aracın konumu (talimat maddesi — KOL 2 için)
`gazebo/dunya_uret.py:INPAINT_PIKSEL_KUTUSU` + `inpaint_dunya_bolgesi()`:
dünya koordinatlarında **x∈[36.6, 57.1] m, y∈[22.1, 44.0] m** (A11 doğru
ölçekle). KOL 2'nin hareket biriktirmesi bu bölgede statik bir "hayalet"
bulursa kaynağı budur (inpaint kalıntısı, gerçek nesne değil).

---

## Durum (2026-09-04) — Y1 KAPISI ÖLÇÜLDÜ: **KALDI**

6 senaryo (300-600 kare × 6 = 2400 kare, 0 düşen kare) + 500 karelik DCF
varyantı kaydedildi (`data/gazebo/Y1_*`). Ölçüm: `gazebo/tani_a11_1_y1.py`
→ `cikti/a11_1_y1_kapi.json`, `gazebo/tani_a11_1_dcf_kayma.py` →
`cikti/a11_1_dcf_kayma_500k.json`.

**Kapsam:** 2400 karenin 1128'i (%47) yama-içi, 1272'si (%53) taşma (A2/A5
irtifa rampasının üst kısmı). Kapı + DCF ölçümü yalnız yama-içi karelerden.

**Dedektör kapısı (@40px±5 tam-kare, @20px±5 ROI-4×, eşik ≥0.80):**

| Model | tam-kare @40px (n) | ROI-4× @20px (n) | Kapı |
|---|---:|---:|---|
| COCO | **0.000** (n=101) | ölçülemedi (n=0) | **KALDI** |
| A6 | 0.693 (n=101) | ölçülemedi (n=0) | **KALDI** |

- **COCO tam kör** — gerçekçi mesh'e ve gerçek dokuya rağmen 40px bandında
  0/101 doğru tespit. A11 KOL0'ın "COCO Gazebo'da tamamen kör" bulgusunu
  DOĞRULUYOR — bu sefer kutu değil gerçekçi mesh'le bile.
- **A6 40px'te 0.693 — eşiğin altında ama yakın.** Geniş kova tablosunda
  A6: 60px kovası (n=958) tam-kare 0.880/ROI 0.884; 40px kovası (n=149)
  tam-kare 0.711/ROI 0.913; 30px kovası (n=21) tam-kare 0.762/ROI 1.000.
  **ROI 4× büyütme A6'da tutarlı biçimde kazandırıyor** (A7/A8 bulgusuyla
  aynı yönde).
- **20px ROI kapısı hiç ÖLÇÜLEMEDİ (n=0) — "kaldı" değil "veri yok".**
  Yama (gerçek doku) hedefin 20px'e küçüldüğü irtifaya (~115 m) kadar
  uzanmıyor; kamera o irtifada yamanın çoktan dışına taşmış oluyor. Bu,
  yama boyutunun (düzeltilmiş ölçekte bile) A2/A5'in tam irtifa aralığını
  kapsamadığının doğrudan kanıtı — kapsam sınırı sadece teorik değil,
  ölçülebilir bir veri boşluğu yarattı.

**renk_dcf doku-kayması — Y1_A1_taban_500k (tamamı yama-içi, 500/500 kare):**
Kapalı çevrim (hakem=None, saf DCF, A11 KOL0'ın H0'ıyla aynı protokol).
**Kayma VAR ve HIZLI:** ilk "KİLİTLİ ama IoU<0.2" karesi **t=8** (frame 8,
~0.27 saniye). IoU zaten t=4'te 0.20'ye, t=8'de 0.12'ye düşüyor. Kilitli
kareler arasında yanlış-kilit oranı **%45.9** (84/183); dizi sonunda durum
KAYIP'a düşüyor. Görsel doğrulama (kare 8, `/tmp/dcf_kare_8.png` mantığıyla
üretildi — kalıcı dosya değil, tekrar üretmek için `tani_a11_1_dcf_kayma.py`
sonrası elle kare çekilebilir): takipçinin kutusu (kırmızı) aracın (yeşil GT)
üstünden geçen **şerit çizgisi boyunca dikey olarak şişiyor** — DCF gerçek
görüntüdeki şerit çizgisine (yüksek kontrastlı statik çizgi) kilitleniyor,
tıpkı A11'in prosedürel dokuda bulduğu mekanizmanın AYNISI. **Sonuç: doku-
kayması Gazebo'nun prosedürel dokusuna özgü bir zaaf DEĞİL — gerçek VisDrone
görüntüsünde de, hatta DAHA HIZLI ortaya çıkıyor.**

**HÜKÜM: Y1 kapısı KALDI.** Talimat gereği Y2/Y3 KOŞULMADI, DUR.

**Kapıyı geçmek için olası sonraki adaylar (SINANMADI, öneri):**
1. A6 modelini 40px'te 0.80'e çıkarmak (0.693'ten farkı küçük — eşik/NMS
   ayarı veya ek fine-tune denenebilir).
2. Yamayı büyütmek (daha geniş bir VisDrone karesi/mozaik — bu sefer
   TEXEL_PM doğru olduğu için mozaikleme daha az repetitif olur) ki A2/A5
   20px'e inene kadar yama-içi kalsın, ROI kapısı gerçekten ölçülebilsin.
3. renk_dcf'in şerit-çizgisi tipi doku-kaymasına karşı sertleştirilmesi
   (A11'in "sıradaki adaylar" listesindeki "DCF-doku-kaymasını önlemek"
   maddesiyle AYNI, artık gerçek görüntüyle de doğrulanmış durumda).

---

## Y1.1 — YAMA GENİŞLETME + KAPI YENİDEN ÖN-KAYDI (2026-09-04, A11.2'nin parçası)

Talimat (birebir): *"3–4 hedefsiz VisDrone karesi, feather birleşim,
tekrarsız; ≥300×170 m. Kapıyı YENİDEN ÖN-KAYITLA: 'Gazebo recall, A6'nın
gerçek veri recall'ünün ±0.10 içinde' (40 px tam kare ve ROI; 20 px ROI).
Eski 0.80 kapısının neden hatalı olduğunu belgede yaz. COCO düşer, A6 tek
model."*

### Eski 0.80 kapısı neden hatalıydı — ölçülmüş kanıt
`A6_KUCUK_HEDEF_FINAL_BENCHMARK.md`'nin **gerçek VisDrone verisi** üzerinde
ölçülmüş recall@IoU≥0.5 tablosu (A6 UAVDT+VisDrone sütunu, iki birincil dizi):

| boyut | 117/23 (gerçek) | 137/12 (gerçek) | ortalama |
|---|---:|---:|---:|
| 40×15 px | 0.900 | 0.600 | **0.750** |
| 20×10 px | 0.050 | 0.375 | **0.2125** |

Yani modelin **kendi gerçek doğrulama verisinde bile** 20px'te recall
%5–37.5 bandında — "Gazebo'da 20px'te ≥0.80" sabit kapısı, model gerçek
dünyada bunu hiçbir zaman başaramadığı için **ulaşılamaz bir bardı.** Doğru
soru "simülasyon gerçek veriyle tutarlı mı" idi, "mutlak sayı ne kadar
yüksek" değil. Yeni kapı: Gazebo recall'ü, aynı modelin gerçek veri
recall'ünün ±0.10'u içinde mi (referans: 40px→0.750, 20px→0.2125).

### Yama genişletildi
`gazebo/y1_yama_uret.py`: **4 farklı, hedefsiz VisDrone karesi** (mevcut
otoyol yaması + 3 yeni: nadire-yakın yol/çatlak dokusu, ağaç/duvar/tarla,
ağaç/kaldırım), 2×2 ızgarada feather (60px) ile birleştirildi — hiçbiri
tekrarlanmıyor/aynalanmıyor (Y1'in ayna/tekrar reddi burada da geçerli).
Sonuç: **2200×1300 px = 300.8×177.7 m** (talimat ≥300×170 m — geçti).
İnpaint edilen aracın bileşik uzaydaki konumu otomatik hesaplandı
(`INPAINT_PIKSEL_KUTUSU=(701,83,822,212)`, `inpaint_konum_v2.json`).
6 senaryo + 500k varyantı **yeniden kaydedildi** (yeni zemin ile, eski
kayıtların üzerine). Kapsam iyileşti: **%47 → %58.5 yama-içi**
(1405/2400 kare) — artık 20px sıklet aralığında da örneklem var (n=122).

### Yeni kapı sonucu (A6 tek model, `gazebo/tani_a11_2_y11_kapi.py`)

| Ölçüt | Gazebo recall (n) | gerçek-veri referans | fark | ±0.10 kapı |
|---|---:|---:|---:|---|
| tam-kare @40px | 0.089 (101) | 0.750 | −0.661 | **KALDI** |
| ROI-4× @40px | 0.970 (101) | 0.750 | +0.220 | **KALDI** |
| ROI-4× @20px | 0.754 (122) | 0.2125 | +0.542 | **KALDI** |

**HÜKÜM: Y1.1 kapısı da KALDI** — ama önceki turdan ÇOK FARKLI bir
biçimde: tam-kare @40px **düştü** (0.693→0.089), ROI'ler ise gerçek
veriden ÇOK DAHA İYİ çıktı (Gazebo'da ROI @20px 0.754, gerçek veride
0.05–0.375). Kova tablosunun tamamı:

| kova | tam-kare (n) | ROI-4× (n) |
|---|---:|---:|
| 60×22 | 0.887 (958) | 0.689 (958) |
| 40×15 | 0.208 (149) | 0.933 (149) |
| 30×12 | **0.000** (176) | 0.864 (176) |
| 20×10 | **0.000** (122) | 0.754 (122) |

### Neden düştü — YENİ bir metodolojik kusur bulundu: "hayalet" dikiş bölgeleri
Görsel teşhis (30×12 kovasından örnek kare, `Y1_A2_kucul`): küçük hedefin
etrafında **iki farklı gerçek fotoğrafın feather ile üst üste bindiği bir
"çifte pozlama" bölgesi** var — yarı saydam yeşil ve sarı hayalet
dikdörtgenler, iki farklı yol dokusunun birbirine karışması, çim ile kaldırım
dokusunun aynı anda görünmesi. **2×2 ızgaranın iç dikişleri (4 hücre arası,
toplamda bir "+" şekli) tam operasyon alanının MERKEZİNDEN geçiyor**
(`GERCEK_ZEMIN_MERKEZ_M=(16,-2)` ızgaranın kesişim noktasına yakın) — yani
hedef küçüldükçe (irtifa arttıkça) kamera tam bu dikiş bölgesinden geçme
olasılığı yüksek, ve küçük hedefler için bu "çifte pozlama" gerçek bir
görsel bozulmadır, dedektörü gerçekten şaşırtır. Bu, Y1'in tek-yama
sürümünde YOKTU (tek fotoğraf, iç dikiş yok) — **büyütme kendi yeni
artefaktını getirdi.** ROI'nin buna rağmen güçlü çıkması (0.75–0.97)
tutarlı: ROI dar bir pencereyi büyütüp veriyor, dikiş bölgesinin geniş
"çifte pozlama" alanının çoğu kırpılıp atılıyor.

**Sonuç — iki ayrı, birbirinden bağımsız bulgu:**
1. **Eski 0.80 sabit kapısı gerçekten hatalıydı** (gerçek veriyle
   karşılaştırma kanıtladı) — bu düzeltme doğruydu ve kalıcı olmalı.
2. **Yamayı 2×2 ızgarayla büyütme yöntemi kendi başına bir kusur getirdi**
   (dikiş "çifte pozlama"sı) — bu, ±0.10 kapısının GEÇMEMESİNİN başlıca
   nedeni ve yama genişletmenin UYGULANIŞIYLA ilgili, ölçüm metodolojisiyle
   değil. Sıradaki adım (sınanmadı): ızgara merkezini operasyon alanının
   ORTASINDAN kaydırmak (dikişler kenarlara düşsün) ya da feather yerine
   hücreleri KESKİN (dikişsiz, örtüşmesiz) sınırlarla ayırmak — çifte
   pozlama yerine düz bir kenar, en azından dedektör için daha az kafa
   karıştırıcı olabilir.

**Y2/Y3 bu turda da KOŞULMADI** — ne T1'in önerisi ne Y1.1'in yeni kapısı
"uygulanıp kendi A/B'sini geçmiş bir düzeltme" değil; talimatın ön-koşulu
karşılanmıyor. Ham veri: `cikti/a11_2_y11_kapi.json`.
