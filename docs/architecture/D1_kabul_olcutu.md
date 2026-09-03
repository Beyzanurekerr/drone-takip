# D1 — KABUL ÖLÇÜTÜ (deney başlamadan önce yazıldı, sonuçlara göre değiştirilmeyecek)

**Soru:** `HareketTespit.adaylar()` KILITLI durumdayken hedefin gerçek
boyutunu, `boyut`tan ve `rafine_kutu`'dan **bağımsız** ve **mutlak** biçimde
ölçebiliyor mu?

## K1 — BAĞIMSIZLIK (kod okumasıyla, ikili)
`adaylar()`ın kod yolu `self.boyut`u, `rafine_kutu` çıktısını ya da bunlardan
türetilmiş hiçbir büyüklüğü okumamalı. Aday SEÇİMİ de `boyut` kullanmamalı;
yalnızca takipçinin MERKEZİ (`kf.konum`) kullanılabilir.

## K2 — MUTLAKLIK (kod okumasıyla, ikili)
Ölçüm doğrudan görüntüden piksel cinsinden w/h üretmeli; oran/hız değil.

## K3 — DOĞRULUK (ölçümle)
`boyut` kullanmayan seçim kuralıyla seçilen adayın GT'ye oranı için:
  a) `w/GT_w` ve `h/GT_h` **medyanı**, deponun kendi bandı **[0.60, 1.70]**
     içinde olmalı, ve
  b) p5–p95 yayılımı, AYNI kaynakta `rafine_kutu`'nun 4N/4R'de ölçülen
     yayılımından **dar** olmalı (daha kötüyse aday iyileştirme değildir).

## K4 — İKİ GERÇEK DİZİ
K3, **117/23 ve 137/12'nin İKİSİNDE birden** ve **aynı yönde** sağlanmalı.
Tek dizide sağlanması yeterli değildir (4C ve 4U dersi).

## K5 — DRIFT AYRIMI
Sonuçlar drift öncesi ve drift sonrası AYRI raporlanacak; çapa olarak
kullanılabilirlik **drift öncesi** performansla belirlenir. Ayrıca ilk hatalı
boyut üretimi ve sonraki 20 kare ayrıca incelenecek.

## HÜKÜM KURALI
* **GÜVENİLİR**: K1, K2, K3, K4 drift öncesinde hepsi sağlanır.
* **KISMEN**: K1+K2 sağlanır ama K3 ya da K4 sağlanmaz.
* **GÜVENİLİR DEĞİL**: K1 ya da K2 düşer, ya da K3 iki gerçek dizide de düşer.

**D1 yalnızca ölçümün VAR OLUP OLMADIĞINI belirler. Hüküm ne olursa olsun bu
turda hiçbir kod değişikliği yapılmaz.**
