"""VisDrone adapter testleri.

    python3 test_visdrone.py      # bagimsiz kosar, pytest gerekmez
    pytest test_visdrone.py -q

Ayristirici testleri gecici dosyalarla kosar (veri kumesi gerekmez).
Veri kumesine baglı testler, `data/datasets/visdrone_vid` yoksa ATLANIR.
"""
import os
import shutil
import tempfile

import numpy as np

from kaynak import KaynakHatasi, kaynak_olustur
from veri.etiket import (ARAC_SINIFLARI, EtiketHatasi, det_oku,
                         en_uygun_arac_track, track_bul, track_ozeti,
                         track_yolu, vid_oku)
from veri.visdrone import VisDroneVidKaynak, diziler

KOK = "data/datasets/visdrone_vid"
DIZI = "uav0000305_00000_v"
VERI_VAR = os.path.isdir(os.path.join(KOK, "sequences", DIZI))


def _atla(neden):
    print(f"    (atlandi: {neden})")


def _gecici(icerik, ad="ann.txt"):
    klasor = tempfile.mkdtemp()
    yol = os.path.join(klasor, ad)
    with open(yol, "w") as f:
        f.write(icerik)
    return klasor, yol


# --------------------------------------------------------- annotation parse
def test_annotation_parse():
    klasor, yol = _gecici(
        "1,7,100,200,50,30,1,4,0,0\n"
        "2,7,105,202,50,30,1,4,0,1\n"
        "1,9,300,100,20,20,0,0,0,0\n")     # ignored (score=0, sinif=0)
    try:
        kareler = vid_oku(yol)
        assert set(kareler) == {1, 2}
        assert len(kareler[1]) == 2 and len(kareler[2]) == 1
        e = kareler[1][0]
        assert e.kare == 1 and e.track_id == 7 and e.sinif == 4
        assert e.arac_mi and e.sinif_adi == "car"
        assert not e.yoksayilan
        assert kareler[1][1].yoksayilan, "score=0 satiri ignored olmali"
        assert kareler[2][0].ortulme == 1
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def test_bbox_parse_ve_merkez():
    klasor, yol = _gecici("1,7,100,200,50,30,1,4,0,0\n")
    try:
        e = vid_oku(yol)[1][0]
        assert np.allclose(e.kutu, [100, 200, 50, 30])
        assert np.allclose(e.merkez, [125, 215])
        assert e.kutu.dtype == np.float32
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def test_bos_annotation():
    klasor, yol = _gecici("\n\n   \n")
    try:
        vid_oku(yol)
    except EtiketHatasi as e:
        assert "bos" in str(e)
        return
    finally:
        shutil.rmtree(klasor, ignore_errors=True)
    raise AssertionError("bos annotation icin EtiketHatasi beklendi")


def test_bozuk_annotation_eksik_kolon():
    klasor, yol = _gecici("1,7,100,200,50,30\n")
    try:
        vid_oku(yol)
    except EtiketHatasi as e:
        assert "10 kolon" in str(e) and ":1" in str(e), f"satir no yok: {e}"
        return
    finally:
        shutil.rmtree(klasor, ignore_errors=True)
    raise AssertionError("eksik kolon icin EtiketHatasi beklendi")


def test_bozuk_annotation_sayi_degil():
    klasor, yol = _gecici("1,7,100,200,50,30,1,4,0,0\n2,7,abc,202,50,30,1,4,0,0\n")
    try:
        vid_oku(yol)
    except EtiketHatasi as e:
        assert "sayi degil" in str(e) and ":2" in str(e)
        return
    finally:
        shutil.rmtree(klasor, ignore_errors=True)
    raise AssertionError("sayisal olmayan kolon icin EtiketHatasi beklendi")


def test_gecersiz_kutu_boyutu():
    klasor, yol = _gecici("1,7,100,200,0,30,1,4,0,0\n")
    try:
        vid_oku(yol)
    except EtiketHatasi as e:
        assert "gecersiz kutu boyutu" in str(e)
        return
    finally:
        shutil.rmtree(klasor, ignore_errors=True)
    raise AssertionError("sifir genislik icin EtiketHatasi beklendi")


def test_annotation_dosyasi_yok():
    try:
        vid_oku("/olmayan/klasor/ann.txt")
    except EtiketHatasi as e:
        assert "bulunamadi" in str(e)
        return
    raise AssertionError("olmayan dosya icin EtiketHatasi beklendi")


def test_det_parse():
    klasor, yol = _gecici("871,572,54,92,1,4,0,0\n976,794,19,38,1,2,0,1\n")
    try:
        e = det_oku(yol)
        assert len(e) == 2
        assert e[0].sinif == 4 and e[0].track_id == -1 and e[0].kare == 0
        assert np.allclose(e[0].kutu, [871, 572, 54, 92])
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


# ------------------------------------------------------------- track secimi
def test_track_secimi_hareketliyi_tercih_ediyor():
    """Park halindeki arac daha cok karede olsa bile hareketli olan secilmeli."""
    satirlar = []
    for k in range(1, 101):                       # track 1: park halinde
        satirlar.append(f"{k},1,500,500,40,20,1,4,0,0")
    for k in range(1, 81):                        # track 2: hareketli
        satirlar.append(f"{k},2,{100 + 5 * k},300,40,20,1,4,0,0")
    klasor, yol = _gecici("\n".join(satirlar) + "\n")
    try:
        kareler = vid_oku(yol)
        assert track_yolu(kareler, 1) == 0.0
        assert track_yolu(kareler, 2) > 300
        assert en_uygun_arac_track(kareler, min_kare=10) == 2
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def test_olmayan_track_id():
    klasor, yol = _gecici("1,7,100,200,50,30,1,4,0,0\n")
    try:
        track_bul(vid_oku(yol), 999)
    except EtiketHatasi as e:
        assert "999" in str(e) and "Mevcut id" in str(e)
        return
    finally:
        shutil.rmtree(klasor, ignore_errors=True)
    raise AssertionError("olmayan track_id icin EtiketHatasi beklendi")


def test_arac_olmayan_dizide_hata():
    klasor, yol = _gecici("1,7,100,200,50,30,1,1,0,0\n")   # sinif 1 = pedestrian
    try:
        en_uygun_arac_track(vid_oku(yol))
    except EtiketHatasi as e:
        assert "arac sinifindan hic track yok" in str(e)
        return
    finally:
        shutil.rmtree(klasor, ignore_errors=True)
    raise AssertionError("araci olmayan dizi icin EtiketHatasi beklendi")


def test_downscale_bbox_tutarli():
    klasor, yol = _gecici("1,7,100,200,50,30,1,4,0,0\n")
    try:
        e = vid_oku(yol)[1][0]
        yarim = e.olcekli(0.5)
        assert np.allclose(yarim.kutu, [50, 100, 25, 15])
        assert e.olcekli(1.0) is e, "olcek 1.0'da kopya uretilmemeli"
        assert np.allclose(e.kutu, [100, 200, 50, 30]), "orijinal degismemeli"
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


# ---------------------------------------------------- veri kumesine bagli
def test_sequence_discovery():
    if not VERI_VAR:
        return _atla("veri kumesi yok")
    d = diziler(KOK)
    assert len(d) == 7, f"7 dizi bekleniyordu, {len(d)} bulundu"
    assert DIZI in d
    assert d == sorted(d), "dizi listesi sirali degil"


def test_olmayan_veri_kumesi():
    try:
        diziler("/olmayan/veri/kumesi")
    except KaynakHatasi as e:
        assert "bulunamadi" in str(e)
        return
    raise AssertionError("olmayan kok icin KaynakHatasi beklendi")


def test_ilk_kare_okuma():
    if not VERI_VAR:
        return _atla("veri kumesi yok")
    k = VisDroneVidKaynak(KOK, DIZI, track_id=30, hedef_genislik=960)
    kare = k.oku()
    assert kare is not None and kare.goruntu.shape == (540, 960, 3)
    assert kare.indeks == 0 and kare.kaynak_adi.startswith("visdrone:")
    assert k.tur == "visdrone" and k.acik_mi()


def test_frame_gt_senkronizasyonu():
    if not VERI_VAR:
        return _atla("veri kumesi yok")
    k = VisDroneVidKaynak(KOK, DIZI, track_id=30, olcek=1.0)
    ham = vid_oku(os.path.join(KOK, "annotations", f"{DIZI}.txt"))
    for _ in range(25):
        kare = k.oku()
        beklenen = [e for e in ham[kare.indeks + 1] if e.track_id == 30]
        if beklenen:
            assert kare.gt is not None and kare.gorunur
            assert np.allclose(kare.gt, beklenen[0].kutu), \
                f"kare {kare.indeks}: GT kutusu annotation ile uyusmuyor"
        else:
            assert kare.gt is None


def test_gt_downscale_ile_olcekleniyor():
    if not VERI_VAR:
        return _atla("veri kumesi yok")
    tam = VisDroneVidKaynak(KOK, DIZI, track_id=30, olcek=1.0).oku()
    yari = VisDroneVidKaynak(KOK, DIZI, track_id=30, olcek=0.5).oku()
    assert yari.genislik == tam.genislik // 2
    assert np.allclose(yari.gt, tam.gt * 0.5, atol=1e-3), \
        "kare kuculdu ama GT kutusu ayni oranda kuculmedi"


def test_kaynak_fabrikasi_visdrone():
    if not VERI_VAR:
        return _atla("veri kumesi yok")
    k = kaynak_olustur("visdrone", veri_kok=KOK, dizi=DIZI, track_id=30,
                       hedef_genislik=960)
    assert isinstance(k, VisDroneVidKaynak) and k.track_id == 30
    assert k.oku() is not None


def test_olmayan_dizi_hatasi():
    if not VERI_VAR:
        return _atla("veri kumesi yok")
    try:
        VisDroneVidKaynak(KOK, "uav9999999_00000_v")
    except KaynakHatasi as e:
        assert "dizi bulunamadi" in str(e) and "mevcut diziler" in str(e)
        return
    raise AssertionError("olmayan dizi icin KaynakHatasi beklendi")


def test_gercek_veride_track_ozeti():
    if not VERI_VAR:
        return _atla("veri kumesi yok")
    kareler = vid_oku(os.path.join(KOK, "annotations", f"{DIZI}.txt"))
    ozet = track_ozeti(kareler)
    assert len(ozet) > 10
    arac = [t for t, o in ozet.items() if o["arac_mi"]]
    assert len(arac) > 5
    for t in arac:
        assert ozet[t]["sinif"] in ARAC_SINIFLARI


def test_sim_kaynagi_gt_ile_kilitleniyor():
    """GT tabanli secici sim kaynaginda da calismali (kaynak-bagimsizlik)."""
    import main
    m = main.kos(kaynak_olustur("sim", senaryo="test1"), pencere=False,
                 max_kare=40)
    assert m["kilitli"] and m["gt_kare"] > 0
    assert m["ort_iou"] > 0.5, f"sim IoU beklenenden dusuk: {m['ort_iou']}"


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
