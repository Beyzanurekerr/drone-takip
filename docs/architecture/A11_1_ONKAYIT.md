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

**Bilinçli kapsam sınırı:** yama 150×69 m kaplıyor. A1/A3/A4/A6 ve A2/A5'in
düşük-orta irtifa kareleri tamamen gerçek dokuda kalır (kamera 38.3 m'de
~49 m, A4'ün en yüksek noktası 108.3 m'de ~106 m görür — hâlâ yama içinde).
A2/A5'in rampanın ÜST UCUNDA (287.5 m, ~369 m görüş) kamera yamanın dışına
taşar ve prosedürel dokuyu görür — bu ölçülüp raporlanacak, gizlenmeyecek.
Doku önizlemesinde (tam tuval, gz sim render değil) yama merkezinin HEMEN
dışında prosedürel bina/ağaç kalabalığı yamayla keskince kontrast oluşturuyor
(feather bandının genişliği bunu tam gizlemiyor) — çünkü prosedürel
bina/ağaç üretimi de aynı `TEXEL_PM=12.8` ile tuvalin merkezine yakın bir
bantta yoğunlaşıyor, tam yamanın oturduğu yerde. Bu sınır A1_taban'ın normal
görüş alanının (kamera hedefe kilitli, ~49 m, yamanın çekirdeğinde) çok
dışında kalıyor; gz sim'in gerçekten render ettiği tek-kare smoke testte
(bkz. Durum) bu kalabalık kadrajda GÖRÜNMEDİ. Yüksek irtifa karelerinde
(A2/A5 rampasının üst ucu) görünmesi beklenir — ölçülüp raporlanacak.

**TEXEL_PM tutarsızlığı (yeni gözlem, DÜZELTİLMEDİ — kapsam dışı):**
`gazebo/dunya_uret.py`'deki `TEXEL_PM = DOKU_PX/ZEMIN_M` MODÜL sabitidir
(2048/160=12.8), `zemin_dokusu()` içindeki içerik yerleşimi (yol, bina, ağaç)
bunu kullanır — ama SDF'teki `<box><size>{zemin_m}...` A11 ailesinde
`sen.zemin_m=560` yazıyor. Yani içerik "12.8 texel/m" varsayımıyla
YERLEŞTİRİLİYOR, Gazebo ise dokuyu fiilen 4096/560=7.31 texel/m yoğunlukta
GÖSTERİYOR — içerik göründüğünden ~1.75× daha küçük ölçekte render oluyor
(9 m'lik yol fiilen ~15.8 m genişlikte görünür). Bu, A1-A11'in TÜM önceki
prosedürel koşumlarında da vardı (benim değişikliğim DEĞİL); mevcut A11
bulgularının hiçbiri bu ölçek farkına bağlı değildi (görece karşılaştırmalar
hep aynı tabanla yapıldı) ama mutlak metre iddiaları (`px_kare` tablolarındaki
metre-cinsi büyüklükler) bundan etkilenmiş olabilir. Y1'in kendi yama
yerleşimi de AYNI (12.8) kuralı kullanır — tutarlı ama "doğru" değil.
Düzeltmek A11'in TÜM sonuçlarını yeniden ölçmeyi gerektirir; Y1'in kapsamı
DIŞINDA bırakıldı, yalnızca not düşülüyor.

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

---

## Durum (2026-09-04)

**Tamamlanan:** mesh+doku altyapısı yazıldı, 6 senaryo + 500-kare varyantı
SDF üretimi hatasız (`dunya_yaz` tüm 7 çağrıda başarılı), mevcut A1-A6
prosedürel dokusu BİREBİR aynı kaldı (md5 doğrulandı — regresyon yok).
`Y1_A1_taban` 5 karelik gz sim smoke testi koşuldu (düşen kare 0, RTF 0.96):
mesh doğru yönde, düz zeminde, gerçek dokunun üzerinde net görünüyor; GT
`meta.json`'da hedefin L/W/H'si doğru (4.0011/2.1405/1.5679).

**YAPILMADI (Y1 kapısı henüz ÖLÇÜLMEDİ):**
- 6 senaryonun tam kaydı (300-600 kare × 6).
- Dedektör tam kare recall (40 px) + ROI recall (20 px) ölçümü.
- `Y1_A1_taban_500k` renk_dcf IoU zaman serisi (doku-kayması hâlâ var mı?).

Kapı ölçülüp GEÇMEDEN Y2/Y3'e geçilmeyecek (talimat: "Geçmezse DUR, hiçbir
kol koşma").
