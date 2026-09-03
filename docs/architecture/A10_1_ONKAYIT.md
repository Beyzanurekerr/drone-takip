# A10.1 — ÖN-KAYIT (D2 + D3)

**Yazıldığı tarih:** 2026-09-03 · **A10.1 kolları KOŞULMADAN ÖNCE yazıldı.**
D1 (yatak düzeltmesi) bitmiş ve `A10_1_D1_TEMIZ_YATAK.md`'de raporlanmıştır;
D2'nin sabitleri oradan alınır. Hiçbir A10.1 **kol** sonucu görülmedi.

> **Değişmeyenler:** `A9_KABUL_OLCUTU.md` (K1–K6) · A10'un kolları
> (H0 · H1 · H2 · H3 · H3-O-merkez · H3-O-boyut) · iki sütunlu yanlış kilit
> raporlaması · oracle kolların "ÜST SINIR" etiketi · yasaklar (eğitim,
> ağırlık, imgsz, SAHI, Pi optimizasyonu, 5×5, sonuca göre sabit değiştirme).
> **YENİ BİLEŞEN YOK.** Yalnızca iki mevcut bileşen düzeltiliyor.

---

## 1. Karar tabanı — D1'den, dondu

**4 dizi × 5 seviye = 20 hücre.** 117/23 (KOPAN) · 268/31 (KOPAN) ·
137/12 (**tek sağlam**) · 370/0 (KOPAN).

Düşen üç dizinin gerekçesi `A10_1_D1_TEMIZ_YATAK.md` §2'dedir.
**Tek sağlam dizi kalması K1/K2/K6'nın bilinen ve raporlanacak sınırıdır.**

---

## 2. D2 — Mod A tetikleyicisinde HİSTEREZİS

A10'un kuralı tek eşikti: `iz(P) > 8.0 → LOST`. İki ayrı sebeple geçersiz:

1. **Kendi kendini besliyordu.** LOST → ARAMA → `_arama_adimi` → `Kalman.ata`
   → `P[:2,:2] = diag(4,4)` → iz **tam 8.0** → sonraki `tahmin` eşiği aşar →
   yeniden LOST.
2. **Temiz yatakta sağlam p95 = 14.86** (A9'un kirli yatakta ölçtüğü 4.17
   değil). Eşik sağlıklı takipte de ateşlerdi.

### Yeni kural

```
CIKIS  = 14.86      # temiz yatak, saglam p95
GIRIS  = 54.08      # temiz yatak, kopus oncesi p95
mandal = False
her karede:
    if mandal and iz(P) < CIKIS:      mandal = False
    takipci_aramada = durum in (ARAMA, KAYIP) AND bunu HAKEM yazmadi
    if (not mandal) and (iz(P) > GIRIS or takipci_aramada):
        mandal = True ; LOST ; takipciyi BIR KEZ ARAMA'ya it
    elif mandal:
        LOST (yeni itme YOK)
    ONAY gelirse mandal = False
```

### `KALICI_KISITLAR.md` K6'nın istediği üç satır

| soru | cevap |
|---|---|
| **Eşiğin kaynağı** | A9 Aşama 2'nin **açık çevrim** P-izi dağılımı, D1'in temiz yatağında yeniden ölçülmüş hâli (`cikti/a10_1_temiz_yatak.json`). |
| **Eylem bu büyüklüğe yazıyor mu?** | **Evet** — `Kalman.ata` iz'i 8.0'a sıfırlıyor. Bu yüzden 8.0 eşik olarak **kullanılmıyor**; sınıfta yalnızca `P_SIFIRLAMA` adıyla belgeleniyor. |
| **Pay** | GİRİŞ / sıfırlama = 54.08 / 8.0 = **6.76×**. Sıfırlama sonrası iz'in eşiği kendiliğinden aşması imkânsız. ÇIKIŞ (14.86) sıfırlamanın **üstünde**, yani yeniden edinme mandalı **serbest bırakır** — istenen davranış. |

Ek kural: **hakemin kendi ittiği ARAMA, Mod A kanıtı sayılmaz**
(`_kendi_itti` bayrağı). Aksi hâlde eylem yine kendi kanıtını üretirdi.

---

## 3. D3 — Doğrulayıcı ROI'si: A8 §13 (merdiven + KAPSAMA TABANI)

A10 yalnızca `A8.R_sec`'i (büyütme adayı) kullanıyordu; A8'in **zorunlu**
saydığı kapsama tabanı yoktu. A8 §13'ün kuralı aynen uygulanıyor:

```
1. GUVEN KAPISI : durum != KILITLI ya da PSR < psr_kilit -> L_est'e guvenme;
                  son guvenilir R korunur ve bir basamak BUYUTULUR
2. BUYUTME      : R_buyutme = L_est * 640 / 75
3. KAPSAMA      : R_kapsama = (32/9) * (2*u + L_est/2),   u = sqrt(iz P)
4. SECIM        : ag_px = L_est*640/R degeri [55,110] bandinda OLAN ve
                  R >= R_kapsama olan EN KUCUK basamak; yoksa EN BUYUK
MERDIVEN : {640, 320, 160, 80}
```

Bütün sabitler A8'de yayımlanmış: `640` (ağ genişliği) · `75` (`NET_HEDEF`) ·
`[55, 110]` (A8 §15 operasyonel bant) · `32/9` (16:9 dikey darlık) ·
`k = 2` (p95 karşılığı). `u`'nun tanımı `tani_a9_recovery.py:100`'deki mevcut
`kf_belirsizlik_px` ile birebir aynıdır.

### D3'ün BİRİNCİL METRİĞİ

> **H1 kolunda `kanıt yok` oranı.** A10'da **%46** idi.
> Bu sayı düşmezse hakem beslenemez ve diğer bütün sonuçlar anlamsızdır.
> Hüküm bu metrikle **başlar**.

Karşılaştırma tabanı ikilidir ve ikisi de raporlanır:
- A10'un kapalı çevrim değeri: **%46** (kirli yatak, `A8.R_sec`)
- D1'in açık çevrim değeri: **%42.9** (temiz yatak, `A8.R_sec`)

---

## 4. Recovery — K5 için önceden yazılmış kural

A10'da recovery 35 hücrede **1** kez denendi; "geçti/geçmedi" denemezdi.

> **Kural: toplam recovery denemesi < 5 ise K5 "SINANMADI" yazılır** —
> geçti ya da geçmedi **değil**. Bu eşik koşumdan önce sabitlendi ve
> sonuca göre değiştirilmeyecektir.

---

## 5. Değişecek dosyalar

| dosya | değişiklik |
|---|---|
| `takip/hakem.py` | D2 histerezis + `_kendi_itti`; D3 `R_dogrulama` (A8 §13); `kanit_yok_orani` sayacı |
| `gazebo/bench_a10_hakem.py` | yalnızca **taban ve çıktı yolu parametreleştirildi**; kol tanımları ve metrikler AYNEN |
| `gazebo/bench_a10_1_hakem.py` | YENİ ince sarmalayıcı: temiz taban + `cikti/a10_1_hakem.json` |
| `docs/architecture/KALICI_KISITLAR.md` | **K6** maddesi eklendi (D2'nin genel kuralı) |

`takip/izleyici.py` **değişmiyor** (A10'un üç kancası yeterli).
Eşdeğerlik testi tekrarlanacak: `hakem=None` davranışı değişmemeli.

---

## 6. Çıktı ve commit

- Rapor: `docs/architecture/A10_1_HAKEM_KAPALI_CEVRIM.md`
- Veri: `cikti/a10_1_hakem.json`
- **Commit 1 (bitti):** D1 · **Commit 2:** D2 + D3 (bu ön-kayıt + kod) ·
  **Commit 3:** sonuç
- **push YOK.** Sonunda **DUR**.
