"""A10.1 - kapali cevrim hakem kosumu, TEMIZ TABANDA (D1) ve duzeltilmis
hakemle (D2 histerezis + D3 kapsama tabanli ROI).

Kollar, metrikler ve kabul olcutu A10 ile AYNI (gazebo/bench_a10_hakem.py'den
oldugu gibi alinir). Degisen uc sey:
    D1  taban: 339/49, 305/5, 182/127 dustu; 370/0 var  -> 4 dizi x 5 seviye
    D2  Mod A tetikleyicisi histerezisli (takip/hakem.py)
    D3  dogrulama ROI'si A8 §13 + kapsama tabani (takip/hakem.py)
ON-KAYIT: docs/architecture/A10_1_ONKAYIT.md - KOSUMDAN ONCE yazildi.
"""
import importlib.util as iu
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

sp = iu.spec_from_file_location("BM", os.path.join(HERE, "bench_a10_hakem.py"))
BM = iu.module_from_spec(sp)
sp.loader.exec_module(BM)

# D1 TEMIZ TABAN. Roller: 370/0 A10'un H0 kolunda 5 hucrenin 2'sinde kopus
# verdi -> A9 kuraliyla KOPAN.
BM.DIZILER = [("uav0000117_02622_v", 23, "KOPAN"),
              ("uav0000268_05773_v", 31, "KOPAN"),
              ("uav0000370_00001_v", 0, "KOPAN"),
              ("uav0000137_00458_v", 12, "saglam")]
BM.ARTEFAKT = set()                      # temiz yatak: artefaktli dizi kalmadi
BM.CIKTI_YOL = "cikti/a10_1_hakem.json"

if __name__ == "__main__":
    BM.main()
