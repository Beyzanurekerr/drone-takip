"""Deney 4P - `G6_agresif_durakli_celdiricisiz` sahnesini kaydeder.

MEVCUT HICBIR DOSYA DEGISMEZ. Senaryo, `senaryolar.G6_agresif_durakli()`
CAGRILARAK uretilir ve yalnizca `araclar` listesinden "celdirici" cikarilir;
kamera profili, hedef hiz/yaw profili, irtifa, baslangic konumlari, kare
sayisi ve `doku_seed` AYNI NESNEDEN gelir. Zemin dokusu seed'li ve
`data/gazebo/_doku/zemin_<seed>.png` onbellegine yazildigi icin zemin
bit duzeyinde ayni kalir.

Kullanim: python3 -m gazebo.kaydet_4p [--kok data/gazebo]
"""
import argparse
import copy

import gazebo.kaydet as kd
from gazebo.senaryolar import G6_agresif_durakli

AD = "G6_agresif_durakli_celdiricisiz"
AD_TEKRAR = "G6_agresif_durakli_tekrar"


def senaryo():
    s = copy.deepcopy(G6_agresif_durakli())
    once = [a.ad for a in s.araclar]
    s.araclar = [a for a in s.araclar if a.ad != "celdirici"]
    sonra = [a.ad for a in s.araclar]
    assert sonra == ["hedef"], f"beklenmeyen arac listesi: {sonra}"
    assert once == ["hedef", "celdirici"], f"beklenmeyen kaynak listesi: {once}"
    s.ad = AD
    s.aciklama = s.aciklama + " | CELDIRICI YOK (Deney 4P nedensellik testi)"
    s.amac = ("4O'daki DCF cekim noktasi kaymasi celdiriciden mi geliyor? "
              "Tek degisken: celdirici arac sahneden cikarildi.")
    s.etiketler = list(s.etiketler) + ["4P", "celdiricisiz"]
    return s


def senaryo_tekrar():
    """DEGISMEMIS sahne, yeni kayit: KAYIT GURULTUSU tabani.

    4P'nin farkinin kayit tekrarlanabilirliginden mi yoksa celdiriciden mi
    geldigini ayirmak icin zorunlu kontrol.
    """
    s = copy.deepcopy(G6_agresif_durakli())
    s.ad = AD_TEKRAR
    s.aciklama = s.aciklama + " | AYNI SAHNE, YENIDEN KAYIT (4P gurultu tabani)"
    s.etiketler = list(s.etiketler) + ["4P", "tekrar"]
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default="data/gazebo")
    ap.add_argument("--kare", type=int, default=0)
    ap.add_argument("--tekrar", action="store_true",
                    help="degismemis sahneyi yeniden kaydet (gurultu tabani)")
    a = ap.parse_args()
    ad = AD_TEKRAR if a.tekrar else AD
    kd.SENARYOLAR[ad] = senaryo_tekrar if a.tekrar else senaryo
    kd._tek(ad, a.kok, a.kare)


if __name__ == "__main__":
    main()
