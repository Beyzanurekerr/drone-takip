# A11.2 — Önce Takipçi, Sonra Yatak Genişletme (ön-kayıt + sonuç)

Talimat (2026-09-04, birebir):

```
A11.2 — ÖNCE TAKİPÇİ, SONRA YATAK GENİŞLETME.

T1 — renk_dcf DOKU KAYMASI (Y1_A1_taban_500k, kapalı çevrim saf DCF,
tek değişkenli A/B, ön-kayıtlı, K1–K6):
  T1a boyut güncellemesi DONDURULMUŞ (kilitle() boyutu sabit) —
      kayma boyut zincirinden mi geliyor?
  T1b rafine_kutu devre dışı, _boyut_tazele açık
  T1c DCF tepki haritasında hedef-dışı ikinci tepe oranı
      (PSR tek başına değil) — kaymayı görüyor mu, teşhis
  Ölç: ilk yanlış-kilit karesi, yanlış-kilit oranı, kutunun
  en-boy zaman serisi (dikey şişme imzası), IoU. A2–A6'da da
  koş, taşma dışı. Hangi bileşen kaymayı üretiyorsa raporla;
  düzeltme önerisi, uygulama değil. DUR.

Y1.1 — YAMA GENİŞLETME: [ayrı belgede, bkz. A11_1_ONKAYIT.md güncellemesi]

Y2/Y3 yalnızca T1 sonucu takipçiyi A1'de ≥300 kare tutan bir düzeltme
gösterdiyse — ve o düzeltme kendi A/B'sini geçtiyse. Aksi halde takipçi
sorunu önce. Commit her adım, push yok.
```

Bu belge yalnızca **T1**'i kapsar. Y1.1 (yama genişletme + kapı yeniden
ön-kaydı) `A11_1_ONKAYIT.md`'ye eklendi (Y1'in doğrudan devamı olduğu için).

`takip/izleyici.py` ve `takip/cekirdekler.py` **DEĞİŞMEDİ** — tüm kollar
`gazebo/tani_a11_2_t1.py` içinde subclass/monkeypatch ile, çalışma bitince
orijinal fonksiyonlar geri yükleniyor.

---

## Kollar

- **H0** — kontrol, değiştirilmemiş `HedefTakip` (Y1'deki aynı protokol:
  kapalı çevrim, `hakem=None`, ilk kilit GT'den).
- **T1a** — boyut TAMAMEN donuk: `kilitle()`'de ölçülen boyut, `guncelle()`'nin
  her çağrısından ÖNCE ve SONRA zorla geri yazılır — ego-ölçek çarpımı,
  `_boyut_tazele`, `_boyut_sinirla` HİÇBİRİ boyutu değiştiremez.
- **T1b** — `rafine_kutu` üç çağrı noktasında da (kilitle/arama/`_boyut_tazele`)
  `None` döner; `_boyut_tazele`'in kendi zamanlaması (`dogrulama_araligi`
  tetikleyicisi) dokunulmadan açık kalıyor (zaten `rafine_kutu=None` ile
  no-op'a düşüyor). T1a'dan FARKI: ego-ölçek çarpımı serbest — boyut hâlâ
  irtifa/ölçek değişimine tepki verebilir, yalnız renk-kontrast tabanlı
  ölçüm devre dışı.
- **T1c** — teşhis, davranışı DEĞİŞTİRMEZ: `cekirdekler._tepe`'ye sarmalayıcı,
  yanıt haritasının (r) birincil tepe civarının (yarıçap N//6) DIŞINDAKİ en
  yüksek "ikinci tepe"yi çıkarır. `oran = (ikinci_tepe − yan_ort)/(tepe − yan_ort)`.
  PSR yalnız ortalama yan-lob istatistiğine bakar; güçlü ama dar bir ikinci
  tepe (şerit çizgisi gibi) PSR'yi düşürmeyebilir — bu oran onu yakalamak için.

## Sonuçlar — Y1_A1_taban_500k (ana hedef, 500 kare, tamamı yama-içi)

| Kol | ilk yanlış-kilit | yanlış-kilit oranı | eb (h/w) p50 | eb maks |
|---|---:|---:|---:|---:|
| H0 (kontrol) | **8** | 0.459 | 0.334 | **2.969** |
| T1a (boyut donuk) | **103** | 0.402 | 1.648 (sabit) | 1.648 |
| T1b (rafine kapalı) | **111** | 0.396 | 0.547 (sabit) | 0.547 |
| T1c (teşhis, H0 ile aynı) | 8 | 0.459 | 0.334 | 2.969 |

**T1c ikinci-tepe oranı:** genel p50 0.048, p90 0.180 — ama kopuş öncesi/sonrası
ayrımı çarpıcı: **kopuş öncesi p50 0.069 → kopuş sonrası p50 0.529 (7.7×)**.

## Yorum — hangi bileşen kaymayı üretiyor

**Boyut zinciri kaymanın KÖKÜ değil, AMPLİFİKATÖRÜ.** İki kanıt:

1. **Aspect-ratio (dikey şişme) tamamen `rafine_kutu`'dan geliyor.** T1a'da
   (boyut donuk) ve T1b'de (yalnız `rafine_kutu` kapalı) `eb_maks == eb_p50`
   — yani boyut hiç ORANTISIZ değişmiyor. Ego-ölçek çarpımı `boyut`'un HER
   İKİ bileşenini de AYNI skaler ile çarpıyor (en-boy oranı matematiksel
   olarak korunuyor); yalnız `rafine_kutu` genişlik/yüksekliği BAĞIMSIZ
   ölçtüğü için orantısızlık (H0'da 2.97'ye varan dikey şişme) YALNIZ o
   ölçüm yanlış olduğunda ortaya çıkabilir. Görsel teşhis (Y1 raporu):
   `rafine_kutu`, aracın etrafındaki hareket lekesini değil, şerit çizgisinin
   yüksek kontrastlı hattını "kutu" sanıyor ve boyutu o çizgi boyunca şişiriyor.
2. **Ama kayma boyut donduğunda da SONUNDA oluyor** (frame 8 → 103, sıfıra
   inmiyor). Yani DCF'nin kendi korelasyon aramasında (`RenkDcfCekirdek.ara`)
   şerit çizgisine karşı bağımsız, daha yavaş işleyen bir çekim VAR — boyut
   şişmesi bunu ATEŞLEMİYOR, sadece frame 8'de ~13× hızlandırıyor ve (T1c'nin
   gösterdiği gibi) bir kez tetiklendiğinde yanıt haritasındaki ikinci tepeyi
   7.7× büyüterek kilidi tam koparıyor.

**Zincir:** DCF'nin kendi öğrenen şablonu (`ogren`, lr=0.04–0.125/kare) zamanla
şerit çizgisine bir miktar kayar (yavaş, temel zaaf) → `_boyut_tazele` (4
karede bir) o anki (hafifçe kaymış) merkez etrafında `rafine_kutu` çağırır →
`rafine_kutu` şeridi "kutu" ölçer, boyutu dikey şişirir → şişmiş boyut hem
korelasyon arama penceresini hem şablonu büyütür → şerit artık şablonun
BÜYÜK bir parçası, öğrenme onu pekiştirir → kilit tam kopar (frame 8).
Boyut donmuşken bu geri-besleme YOK, ama temel zaaf (yavaş kayma) yalnız
kendi öğrenme hızıyla ilerleyip ~100 karede aynı yere varıyor.

**A2-A6 doğrulaması (yalnız yama-içi kareler) — KARIŞIK, dürüstçe rapor
edilmeli:** T1a/T1b, A1'in aksine, A2-A6'da HER ZAMAN daha iyi değil:

| Senaryo (n yama-içi) | H0 yk oranı | T1a yk oranı | T1b yk oranı |
|---|---:|---:|---:|
| A2_kucul (54) | 0.170 | 0.491 (KÖTÜ) | 0.000 (İYİ) |
| A3_yaw (300) | 0.399 | 0.462 (kötü) | 0.470 (kötü) |
| A4_irtifa (120) | 0.576 | 0.621 (kötü) | 0.438 (iyi) |
| A5_kucul_yaw (54) | 0.000 | 0.170 (KÖTÜ) | 0.000 (aynı) |
| A6_celdirici (300) | 0.459 | 0.463 (~aynı) | 0.396 (iyi) |

**T1a (tam donma) A2/A5'te belirgin biçimde KÖTÜLEŞTİRİYOR** — beklenen:
bu senaryolarda hedef GERÇEKTEN küçülüyor (60→8px), boyutu dondurmak
doğru davranışı da engelliyor. T1a bu yüzden bir DÜZELTME ADAYI DEĞİL,
yalnızca A1'e özel bir teşhis aracıydı. **T1b daha tutarlı**: A2/A4/A6'da
iyileştiriyor, A3'te hafif kötüleştiriyor, A5'te nötr — net yönü olumlu
ama evrensel değil.

## Sonuç ve düzeltme ÖNERİSİ (uygulanmadı — talimat gereği)

Kayma iki katmanlı: (a) DCF'nin kendisinde şerit-çizgisi tipi yüksek-kontrast
hatlara karşı temel bir zaaf var (yavaş, ~100 karede kilit koparır), (b)
`rafine_kutu`'nun periyodik boyut-yeniden-ölçümü bunu ~13× hızlandıran ve
kutuyu orantısız şişiren bir pozitif geri-besleme döngüsü kuruyor.

**Önerilen düzeltme (uygulanmadı):**
1. `rafine_kutu`'nun `_boyut_tazele` içindeki sonucuna bir **en-boy oranı
   kapısı** eklenmeli: yeni ölçülen `h/w`, mevcut `boyut`'un `h/w`'sinden
   makul bir bandın (örn. ±40%) dışındaysa reddedilmeli — T1a/T1b'nin
   kanıtladığı "orantısız şişme" spesifik olarak buradan giriyor. Bu, A2/A5
   için gereken GERÇEK boyut küçülmesini (orantılı) bozmadan, `rafine_kutu`'nun
   şerit-çizgisi tipi orantısız ölçümünü eler.
2. T1c'nin ikinci-tepe oranı (kopuş sonrası 7.7× sıçrama) canlı bir
   **erken uyarı sinyali** olabilir: `_bagimsiz_dogrula`'daki PSR/imza/
   zemine-çakılma denetleyicilerine üçüncü bir denetleyici olarak eklenip
   oran belirgin yükseldiğinde kilit reddedilebilir. Bu oranın kopuştan
   ÖNCEKİ birkaç karede zaten yükselip yükselmediği (öngörü değeri) bu
   turda ölçülmedi — sıradaki adım budur.
3. Her iki öneri de kendi A/B'sini geçmeden (Y2/Y3'ün ön-koşulu olan
   "takipçiyi A1'de ≥300 kare tutan ve kendi A/B'sini geçen düzeltme")
   uygulanmamalı.

**Y2 (KOL 2 seçim) ve Y3 bu turda KOŞULMADI** — hiçbir öneri henüz
uygulanıp sınanmadı, talimatın ön-koşulu karşılanmıyor.

Ham veri: `cikti/a11_2_t1.json`.
