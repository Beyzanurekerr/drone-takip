# Araştırma Özeti

Bu dosya, demo dalı temizliğinde (`chore: demo dalı temizliği`) silinen
`docs/architecture/` altındaki ~75 rapor dosyasının **tek sayfalık indeksidir**.
Her satır bir araştırma aşamasını özetler. Tam rapor metinleri **kayıp
değildir** — `arastirma-v1` etiketi/dalında bulunuyorlar:

```bash
git show arastirma-v1:docs/architecture/<dosya>.md
# ya da
git checkout arastirma-v1 -- docs/architecture/
```

| Aşama | Soru | Hüküm (özet) | Rapor (arastirma-v1) |
|---|---|---|---|
| **A3.9** (Faz A–C, Deney 1–4U) | Hızlı hedef hareketi + hareket kestirimi; DCF dönme-değişmez mi? | Kapalı çevrim açı kestirimi (Deney 2) kabul edildi — tohum verir, biriktirmez. Diğer tüm müdahaleler (1,3,4A,4C,4E,4H,4K,4U) reddedildi. Ana bulgu: kamera ÖTELEMESİ kopmuyor, DÖNME koparıyor; 117/23'ün "sahte-ego"su yatak artefaktıydı. | `A3.9_KAPANIS.md`, `A39_FAZ_C_KARAR_KAPANIS.md`, `DENEY_01..04U_*.md` |
| **A3.10** | Kontrollü senaryoları `sim/` tarafında tekrarlanabilir genişletmek | Hızlı/duran hedef senaryoları `sim/world.py`+`sim/senaryolar.py`'ye eklendi, `takip/` değişmedi. | `A3.10_KAPANIS.md` |
| **A4** | Kullanıcının fare ile hedef seçmesi (ROI init) | Tek dosya (`main.py`) üç saf-geometri ekleme, `kos()` gövdesi bit-birebir korundu. | `A4_KULLANICI_HEDEF_SECIMI_SONUC.md` |
| **A5 / A5.2** | COCO-pretrained YOLOv8n küçük hedefte nerede kırılıyor? | Güvenilir taban 57 px (tam kare); altında recall hızla sıfıra iniyor. Kabul ölçütü koşumdan önce yazıldı, gevşetilmedi. | `A5_KUCUK_HEDEF_BENCHMARK.md`, `A5.2_KABUL_OLCUTU.md`, `A5_YOLO_INTEGRATION.md` |
| **A6** | UAVDT→VisDrone fine-tune küçük hedefi iyileştirir mi? | Kısmen: belirli bantta (117/23 30×12) belirgin kazanç ama bedelli; güvenilir taban 57 px'te KALDI, aşağı inmedi. | `A6_KUCUK_HEDEF_FINAL_BENCHMARK.md`, `A6_VERI_HAZIRLAMA_UAVDT_VISDRONE.md`, `A6_UAVDT_VERI_STRATEJISI.md` |
| **A7** | ROI (kırp+büyüt) tam kareye göre kazandırır mı? | Evet, belirgin: edinme tabanı tam-kare 40 px → ROI (doğru büyütmeyle) 20 px'e indi. | `A7_ROI_KUCUK_HEDEF_TESHIS.md` |
| **A8** | Sürekliliği önsel (konum+boyut) ile adaptif ROI korur mu? | Süreklilik/yeniden-tespit teşhisi (edinme değil) — adaptif ROI merdiveni (R_sec) burada tasarlandı, K-MOD'un R_MERDIVEN'i buradan miras. | `A8_ADAPTIF_ROI_TASARIM_TESHIS.md` |
| **A9** (Aşama 1–3, Deney 3.1–3.3) | Merkez güveni, kopuş tespiti, yeniden edinme, aday seçim kuralı | Dedektör güveni aday seçiminde TERS çalışıyor (AUC 0.381); geometrik tutarlılık (`d_norm`/G kuralı) çalışıyor. **KİRLİ YATAK UYARISI**: `arkaplan_hucresi`'nin (0,0) düşüşü 30 hücrenin 15'ini kirletmişti — A10.1/D1 düzeltti. | `A9_KABUL_OLCUTU.md`, `A9_3_2_SECIM_KURALI.md`, `A9_3_3_ONKAYIT.md`, `A9_TAKIPCI_MERKEZ_RECOVERY.md` |
| **A10** | Kapalı çevrim hakem (dedektör doğrulamalı) K1–K6'yı geçer mi? | REDDEDİLDİ. Eşik-kendi-kararını-besliyor tuzağı (`iz(P)>8.0` LOST kuralı) + yatak artefaktı. | `A10_ONKAYIT.md`, `A10_HAKEM_KAPALI_CEVRIM.md` |
| **A10.1** | Yatak düzeltmesi (D1) + histerezis (D2) + kapsama tabanı (D3) hakemi kurtarır mı? | Yine REDDEDİLDİ (K2 geçmedi). D1 gerçek düzeltmeydi (339/49·305/5·182/127 tabandan düştü), D2 histerezis GERÇEKTEN çalıştı, D3 ters yöne gitti. | `A10_1_ONKAYIT.md`, `A10_1_D1_TEMIZ_YATAK.md`, `A10_1_HAKEM_KAPALI_CEVRIM.md` |
| **A11** (KOL0–3) | Kompozit (VisDrone) yataktaki bulgular Gazebo'da (gerçek kamera hareketi) sağ kalıyor mu? | Kompozit yatak arşivlendi. **Yeni bulgu: DCF doku-kayması** — bozulmasız kamerada bile erken kopuyor (Gazebo prosedürel dokusuna özgü sanılmıştı). Dedektör Gazebo'da (o zamanki kutu-araçla) tamamen kördü. | `A11_ONKAYIT.md`, `A11_KOL0..3_*.md` |
| **A11.1 (Y1)** | Gerçekçi mesh + gerçek VisDrone dokusu "yatak sadakati" kapısını geçer mi? | KALDI. COCO tam kör (gerçekçi mesh'le bile); A6 40px'te 0.693 (eşik 0.80'in altında, yakın); 20px ROI kapısı hiç ölçülemedi (yama o irtifaya uzanmıyordu). TEXEL_PM konum hatası bulunup düzeltildi. | `A11_1_ONKAYIT.md` |
| **A11.2 (T1 + Y1.1)** | DCF kaymasının kökü ne? Yamayı büyütmek yardımcı olur mu? | T1: kayma DCF'nin kendi zaafı (rafine_kutu amplifikatör, kök değil). Y1.1: yama 4 sahneye genişletildi ama **2×2 ızgara dikişleri operasyon alanının ortasından geçip "çifte pozlama" artefaktı** yarattı — tam-kare recall çöktü (0.089). | `A11_2_ONKAYIT.md` |
| **A11.3 (T2 + Y1.2)** | Üç DCF düzeltmesi K6'yı geçer mi? Dikişi kaydırmak Y1.1'in artefaktını çözer mi? | T2: yalnız renk-güvenilirlik maskesi (T2b) K6 geçti ama A1'i 300 kareye taşımadı. Y1.2: ızgara operasyon alanının dışına kaydırılınca **tam-kare recall 0.089→0.733'e sıçradı, GEÇTİ** — dikiş teşhisi doğrulandı. ROI hâlâ "yukarı" kalıyor (gürültü/bulanıklık modeli önerisi, uygulanmadı). | `A11_3_ONKAYIT.md` |
| **K-MOD / K1** | KOL2 aday seçim kuralları (S1 d_norm / S2 +kalıcılık / S3 +dedektör doğrulama) 8×5'te ≥0.80 doğru seçim sağlıyor mu? | KALDI (üçünde de). S1/S2 ~%43 doğru (kapının çok altında, "belirsiz" oranı çok yüksek — 8-9px'te 1-2px hata IoU'yu çökertiyor). S3 neredeyse tamamen çekimser — A8 yatağı fiziksel olarak gerçek dokuya sığmadığı için dedektör kör kaldı, S3 gerçekte ölçülemedi. K2/K3 koşulmadı. | `K_MOD_ONKAYIT.md` |

---

**Genel ders zinciri:** A9'un kirli-yatak dersi → A10/A10.1'in "eşik kendi
kararını besleyemez" dersi → A11'in DCF doku-kayması bulgusu → A11.1-3'ün bu
kaymanın kökünün (rafine_kutu + kendi zaafı) ve yatak artefaktlarının (TEXEL_PM,
ızgara dikişi) katman katman ayrıştırılması → K-MOD/K1'in küçük hedefte (8-9px)
hem seçimin hem ölçümün kendi fiziksel sınırına dayandığının gösterilmesi.

Demo dalı bu araştırmanın SONUCU değil, ondan **öğrenilenlerle** kurulan ayrı
bir ürün dalıdır — araştırma dalındaki hiçbir kapı (K1-K6, 8×5, ±0.10 vb.)
demo dalına taşınmaz (bkz. `README.md` §7 "bilinen sınırlar").
