"""kaynak.py testleri.

    python3 test_kaynak.py        # bagimsiz kosar, pytest gerekmez
    pytest test_kaynak.py -q      # pytest ile de kosar

Video testleri gecici bir mp4 uretir (mock video); kamera testi gercek donanim
gerektirmez - yalnizca gecersiz index'te anlasilir hata verildigini dogrular.
"""
import os
import shutil
import tempfile

import cv2
import numpy as np

from kaynak import (Kare, KameraKaynak, KaynakHatasi, SimKaynak, VideoKaynak,
                    kaynak_olustur)

GENISLIK, YUKSEKLIK, FPS, KARE = 320, 240, 25.0, 40


def _mock_video(klasor, ad="mock.mp4"):
    """Kare numarasi degistikce degisen basit bir test videosu uretir."""
    yol = os.path.join(klasor, ad)
    yaz = cv2.VideoWriter(yol, cv2.VideoWriter_fourcc(*"mp4v"), FPS,
                          (GENISLIK, YUKSEKLIK))
    assert yaz.isOpened(), "test videosu yazilamadi (mp4v codec yok?)"
    for k in range(KARE):
        img = np.full((YUKSEKLIK, GENISLIK, 3), 30, np.uint8)
        cv2.rectangle(img, (10 + 4 * k, 100), (40 + 4 * k, 130), (40, 40, 200), -1)
        yaz.write(img)
    yaz.release()
    assert os.path.exists(yol) and os.path.getsize(yol) > 0
    return yol


# ---------------------------------------------------------------- VideoKaynak
def test_video_frame_geliyor_ve_index_artiyor():
    klasor = tempfile.mkdtemp()
    try:
        k = VideoKaynak(_mock_video(klasor))
        assert k.genislik == GENISLIK and k.yukseklik == YUKSEKLIK
        assert abs(k.fps - FPS) < 1.0
        assert k.kare_sayisi in (KARE, -1)

        indeksler = []
        for kare in k:
            assert isinstance(kare, Kare)
            assert kare.goruntu is not None and kare.goruntu.ndim == 3
            assert kare.goruntu.shape == (YUKSEKLIK, GENISLIK, 3)
            assert kare.kaynak_adi.startswith("video:")
            assert kare.gt is None            # video'da GT yok
            indeksler.append(kare.indeks)
        k.kapat()

        assert len(indeksler) > 0, "hic kare okunamadi"
        assert indeksler == list(range(len(indeksler))), "kare indeksi artmiyor"
        assert abs(len(indeksler) - KARE) <= 1, f"{len(indeksler)} kare okundu"
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def test_video_sonunda_duzgun_biter():
    klasor = tempfile.mkdtemp()
    try:
        k = VideoKaynak(_mock_video(klasor))
        while k.oku() is not None:
            pass
        assert k.oku() is None, "dosya sonundan sonra None donmuyor"
        k.kapat()
        k.kapat()                              # ikinci kapat patlamamali
        assert k.oku() is None
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def test_video_with_blogu_kapatir():
    klasor = tempfile.mkdtemp()
    try:
        with VideoKaynak(_mock_video(klasor)) as k:
            assert k.oku() is not None
        assert k.cap is None, "with blogu cikisinda kaynak kapanmadi"
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def test_video_bulunamadi():
    try:
        VideoKaynak("/olmayan/klasor/olmayan_video.mp4")
    except KaynakHatasi as e:
        assert "bulunamadi" in str(e)
        return
    raise AssertionError("olmayan dosya icin KaynakHatasi beklendi")


def test_video_acilamadi():
    klasor = tempfile.mkdtemp()
    try:
        sahte = os.path.join(klasor, "bozuk.mp4")
        with open(sahte, "w") as f:
            f.write("bu bir video degil")
        try:
            VideoKaynak(sahte)
        except KaynakHatasi as e:
            assert "acilamadi" in str(e)
            return
        raise AssertionError("bozuk dosya icin KaynakHatasi beklendi")
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


# --------------------------------------------------------------- KameraKaynak
def test_kamera_gecersiz_index_anlasilir_hata():
    try:
        KameraKaynak(99)
    except KaynakHatasi as e:
        assert "kamera acilamadi" in str(e)
        assert "99" in str(e)
        return
    raise AssertionError("gecersiz kamera index'i icin KaynakHatasi beklendi")


def test_kamera_kaynagi_olusturulabiliyor():
    """Gercek kamera varsa acilir ve kare verir; yoksa test atlanir."""
    try:
        k = KameraKaynak(0)
    except KaynakHatasi:
        print("    (kamera yok - atlandi)")
        return
    try:
        kare = k.oku()
        assert kare is not None and kare.goruntu.ndim == 3
        assert kare.kaynak_adi == "kamera:0"
        assert k.kare_sayisi == -1             # surekli akis
    finally:
        k.kapat()


# ------------------------------------------------------------------ SimKaynak
def test_sim_mevcut_davranisi_koruyor():
    """SimKaynak, calistir.kos()'un dongusuyle BIREBIR ayni kareyi uretmeli."""
    from sim.senaryolar import TUM_TESTLER

    n = 12
    sen = TUM_TESTLER["test1"]()               # referans: mevcut dongu sirasi
    beklenen = []
    for k in range(n):
        sen.kamera_fn(sen.sahne, k, sen.dt)
        sen.sahne.step(sen.dt)
        beklenen.append((sen.sahne.render(), sen.sahne.gt_box(sen.hedef)))

    kaynak = SimKaynak("test1")
    for k in range(n):
        kare = kaynak.oku()
        img, gt = beklenen[k]
        assert np.array_equal(kare.goruntu, img), f"kare {k} goruntusu farkli"
        assert np.allclose(kare.gt, gt), f"kare {k} GT kutusu farkli"
        assert kare.indeks == k
        assert kare.gorunur is not None
    kaynak.kapat()


def test_sim_senaryo_sonunda_biter():
    kaynak = SimKaynak("test1")
    assert kaynak.kare_sayisi == 300
    kaynak._k = kaynak.kare_sayisi - 1
    assert kaynak.oku() is not None
    assert kaynak.oku() is None, "senaryo sonunda None donmedi"


def test_sim_bilinmeyen_senaryo():
    try:
        SimKaynak("test99")
    except KaynakHatasi as e:
        assert "bilinmeyen senaryo" in str(e)
        return
    raise AssertionError("bilinmeyen senaryo icin KaynakHatasi beklendi")


# --------------------------------------------------------------------- fabrika
def test_fabrika_desteklenmeyen_kaynak():
    try:
        kaynak_olustur("hologram")
    except KaynakHatasi as e:
        assert "desteklenmeyen kaynak" in str(e) and "sim" in str(e)
        return
    raise AssertionError("desteklenmeyen kaynak icin KaynakHatasi beklendi")


def test_fabrika_video_girdisiz():
    try:
        kaynak_olustur("video")
    except KaynakHatasi as e:
        assert "--input" in str(e)
        return
    raise AssertionError("girdisiz video icin KaynakHatasi beklendi")


def test_dogrudan_dosya_yolu():
    """--source data/videos/x.mp4  ->  VideoKaynak"""
    klasor = tempfile.mkdtemp()
    try:
        yol = _mock_video(klasor, "drone_traffic_01.mp4")
        k = kaynak_olustur(yol)
        assert isinstance(k, VideoKaynak)
        assert k.tur == "video"
        assert k.oku() is not None
        k.kapat()
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def test_dogrudan_yol_olmayan_dosya():
    try:
        kaynak_olustur("data/videos/olmayan.mp4")
    except KaynakHatasi as e:
        assert "bulunamadi" in str(e)
        return
    raise AssertionError("olmayan yol icin KaynakHatasi beklendi")


def test_kisa_bicim_sim():
    k = kaynak_olustur("sim:test6")
    assert k.ad == "sim:test6" and k.tur == "sim"
    assert k.kare_sayisi == 340
    k.kapat()


def test_eski_bicim_hala_calisiyor():
    """Geriye uyumluluk: --source video --input <dosya>"""
    klasor = tempfile.mkdtemp()
    try:
        k = kaynak_olustur("video", girdi=_mock_video(klasor))
        assert isinstance(k, VideoKaynak) and k.oku() is not None
        k.kapat()
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


# ------------------------------------------------------------------- acik_mi()
def test_acik_mi_video():
    klasor = tempfile.mkdtemp()
    try:
        k = VideoKaynak(_mock_video(klasor))
        assert k.acik_mi() is True
        k.kapat()
        assert k.acik_mi() is False
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def test_acik_mi_sim():
    k = SimKaynak("test1")
    assert k.acik_mi() is True
    k._k = k.kare_sayisi
    assert k.acik_mi() is False


# ------------------------------------------------------------------ gecikmeler
def test_gecikme_olcumu_uretiliyor():
    import main

    m = main.kos(kaynak_olustur("sim", senaryo="test1"), pencere=False, max_kare=40)
    for alan in ("fps", "gecikme_ort", "gecikme_p50", "gecikme_p95",
                 "gecikme_max", "tur", "kaynak"):
        assert alan in m, f"olcumde {alan} yok"
    assert m["kare"] == 40
    assert m["gecikme_ort"] > 0
    assert m["gecikme_p50"] <= m["gecikme_p95"] <= m["gecikme_max"]
    assert m["tur"] == "sim"


def test_hedef_secici_takilip_cikarilabiliyor():
    """Fare ile secim ayni imzayi kullanacak; dongu degismemeli."""
    import main

    cagrildi = []

    def en_kucugu_sec(adaylar, kare):
        cagrildi.append(kare.indeks)
        return min(adaylar, key=lambda a: a["alan"]) if adaylar else None

    m = main.kos(kaynak_olustur("sim", senaryo="test1"), pencere=False,
                 max_kare=30, hedef_secici=en_kucugu_sec)
    assert cagrildi, "ozel hedef secici hic cagrilmadi"
    assert m["kare"] == 30


def test_kare_alanlari_tam():
    kaynak = kaynak_olustur("sim", senaryo="test4")
    kare = kaynak.oku()
    for alan in ("goruntu", "indeks", "zaman", "kaynak_adi", "genislik",
                 "yukseklik", "fps"):
        assert hasattr(kare, alan), f"Kare.{alan} yok"
    assert kare.fps == 30.0 and kare.genislik == 640 and kare.yukseklik == 480
    assert kare.zaman == 0.0
    kaynak.kapat()


# ----------------------------------------------- takip hatti kaynagi bilmiyor
def test_ayni_hat_iki_kaynakta_calisiyor():
    """Ayni takip hatti hem sim hem video karesiyle, dallanma olmadan kosmali."""
    import main

    m1 = main.kos(kaynak_olustur("sim", senaryo="test1"), pencere=False, max_kare=25)
    assert m1["kare"] == 25 and m1["kilitli"], "sim kaynagiyla kilit kurulamadi"

    klasor = tempfile.mkdtemp()
    try:
        m2 = main.kos(VideoKaynak(_mock_video(klasor)), pencere=False)
        assert m2["kare"] > 0, "video kaynagindan kare islenmedi"
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


# ---------------------------------------------------------------------- kosum
def _kosum():
    testler = [(ad, f) for ad, f in sorted(globals().items())
               if ad.startswith("test_") and callable(f)]
    gecti = basarisiz = 0
    print(f"{len(testler)} test\n" + "-" * 62)
    for ad, f in testler:
        try:
            f()
            print(f"  GECTI    {ad}")
            gecti += 1
        except Exception as e:
            print(f"  KALDI    {ad}\n           {type(e).__name__}: {e}")
            basarisiz += 1
    print("-" * 62)
    print(f"{gecti} gecti, {basarisiz} kaldi")
    return 1 if basarisiz else 0


if __name__ == "__main__":
    raise SystemExit(_kosum())
