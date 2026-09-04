"""A3.9 gorsel kaniti uretici (SALT OKUNUR).

Yeni olcum URETMEZ, takipciyi CALISTIRMAZ. Tum kutular/durumlar
cikti/*.json icindeki mevcut kayitlardan okunur; goruntuler
data/ altindaki mevcut karelerden alinir.
"""
import json, os
import cv2
import numpy as np

KOK = os.path.expanduser("~/drone_takip")
CIKIS = os.path.join(KOK, "A39_dokumanlar", "gorseller")
os.makedirs(CIKIS, exist_ok=True)

YESIL = (80, 220, 80)      # GT
MAGENTA = (235, 60, 235)   # takipci
DURUM_RENK = {"KILITLI": (80, 220, 80), "SUPHELI": (0, 190, 255),
              "ARAMA": (60, 90, 250), "KAYIP": (60, 60, 240)}

F = cv2.FONT_HERSHEY_SIMPLEX


def kutu(im, merkez_x, merkez_y, w, h, renk, etiket, kalinlik, ust=True):
    x1, y1 = int(round(merkez_x - w / 2)), int(round(merkez_y - h / 2))
    x2, y2 = int(round(merkez_x + w / 2)), int(round(merkez_y + h / 2))
    cv2.rectangle(im, (x1, y1), (x2, y2), renk, kalinlik, cv2.LINE_AA)
    (tw, th), _ = cv2.getTextSize(etiket, F, 0.5, 1)
    ty = y1 - 4 if ust else y2 + th + 6
    ty = max(th + 4, min(im.shape[0] - 4, ty))
    cv2.rectangle(im, (x1, ty - th - 4), (x1 + tw + 8, ty + 3), renk, -1)
    cv2.putText(im, etiket, (x1 + 4, ty), F, 0.5, (15, 15, 15), 1, cv2.LINE_AA)
    # merkez isareti
    cv2.drawMarker(im, (int(round(merkez_x)), int(round(merkez_y))), renk,
                   cv2.MARKER_CROSS, 11, kalinlik)


def pano(im, satirlar, durum):
    """Ust bant: senaryo / kare / durum / olcum."""
    g = im.shape[1]
    bant = np.full((78, g, 3), 22, np.uint8)
    cv2.putText(bant, satirlar[0], (12, 27), F, 0.62, (240, 240, 240), 1, cv2.LINE_AA)
    cv2.putText(bant, satirlar[1], (12, 52), F, 0.52, (185, 185, 185), 1, cv2.LINE_AA)
    cv2.putText(bant, satirlar[2], (12, 71), F, 0.46, (140, 140, 140), 1, cv2.LINE_AA)
    r = DURUM_RENK.get(durum, (150, 150, 150))
    (tw, _), _ = cv2.getTextSize(durum, F, 0.66, 2)
    cv2.rectangle(bant, (g - tw - 34, 16), (g - 14, 50), r, -1)
    cv2.putText(bant, durum, (g - tw - 24, 41), F, 0.66, (15, 15, 15), 2, cv2.LINE_AA)
    # alt lejant
    alt = np.full((34, g, 3), 22, np.uint8)
    cv2.rectangle(alt, (12, 11), (40, 25), YESIL, 2)
    cv2.putText(alt, "GT (kayitli dogru kutu)", (48, 24), F, 0.46, (215, 215, 215), 1, cv2.LINE_AA)
    cv2.rectangle(alt, (270, 11), (298, 25), MAGENTA, 2)
    cv2.putText(alt, "TAKIPCI (kayitli cikti)", (306, 24), F, 0.46, (215, 215, 215), 1, cv2.LINE_AA)
    return np.vstack([bant, im, alt])


def yaz(ad, im):
    yol = os.path.join(CIKIS, ad)
    cv2.imwrite(yol, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print("yazildi:", yol, im.shape)


# ---------------------------------------------------------------- GAZEBO
G6 = json.load(open(os.path.join(KOK, "cikti/g6_cift.json")))["G6_agresif_durakli"]
G6S = {r["kare"]: r for r in G6["satir"]}
G6_DIZIN = os.path.join(KOK, "data/gazebo/G6_agresif_durakli/kareler")

GAZEBO_SET = [
    ("01_gazebo_G6_kare106_normal.jpg", 106, "DRIFT ONCESI - normal takip"),
    ("02_gazebo_G6_kare141.jpg", 141, "kayma basliyor (boyut/merkez ayrisiyor)"),
    ("03_gazebo_G6_kare142.jpg", 142, "kayma buyuyor"),
    ("04_gazebo_G6_kare147.jpg", 147, "PSR dusuyor -> SUPHELI"),
    ("05_gazebo_G6_kare148.jpg", 148, "t_drift = 148 (drift baslangici)"),
    ("06_gazebo_G6_kare151.jpg", 151, "IoU = 0 - kutu hedeften koptu"),
    ("07_gazebo_G6_kare170_drift_sonrasi.jpg", 170, "DRIFT SONRASI - yanlis kilit suruyor (kutu hedefin disinda)"),
]

for ad, k, not_ in GAZEBO_SET:
    r = G6S[k]
    im = cv2.imread(os.path.join(G6_DIZIN, "%06d.png" % k))
    assert im is not None, k
    im = cv2.resize(im, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    kutu(im, r["gt_x"] * 2, r["gt_y"] * 2, r["gt_w"] * 2, r["gt_h"] * 2, YESIL, "GT", 2, True)
    kutu(im, r["final_x"] * 2, r["final_y"] * 2, r["w"] * 2, r["h"] * 2, MAGENTA, "TAKIPCI", 2, False)
    s = ["Gazebo  G6_agresif_durakli   kare %d" % k,
         "IoU %.3f   merkez hata %.1f px   PSR %.1f   |  %s" % (
             r["iou"], r["final_hata"], r["psr"], not_),
         "kaynak: data/gazebo/G6_agresif_durakli/kareler/%06d.png  +  cikti/g6_cift.json" % k]
    yaz(ad, pano(im, s, r["durum"]))


# -------------------------------------------------------------- VISDRONE
H = json.load(open(os.path.join(KOK, "cikti/a39a_h123.json")))
O = json.load(open(os.path.join(KOK, "cikti/dcf_4o.json")))
VD_DIZI = {"117/23": ("uav0000117_02622_v", 2720), "137/12": ("uav0000137_00458_v", 2688)}

VISDRONE_SET = [
    ("08_visdrone_117-23_kare31_normal.jpg", "117/23", 31, "normal takip - kararli kilit"),
    ("09_visdrone_117-23_kare348_problemli.jpg", "117/23", 348, "kutu buyumesi - IoU dusuyor (kilit devam ediyor)"),
    ("10_visdrone_137-12_kare10_normal.jpg", "137/12", 10, "normal takip - kararli kilit"),
    ("11_visdrone_137-12_kare108_problemli.jpg", "137/12", 108, "drift sonrasi (t_drift=75) - hedef kayip, ARAMA"),
]

for ad, key, k, not_ in VISDRONE_SET:
    dizi, ham_g = VD_DIZI[key]
    hr = {r["kare"]: r for r in H[key]["satir"]}[k]
    orr = {r["kare"]: r for r in O[key]["satir"]}[k]
    olcek = 960.0 / ham_g
    yol = os.path.join(KOK, "data/datasets/visdrone_vid/sequences", dizi, "%07d.jpg" % (k + 1))
    im = cv2.imread(yol)
    assert im is not None, yol
    im = cv2.resize(im, (960, int(round(im.shape[0] * olcek))), interpolation=cv2.INTER_AREA)
    kutu(im, hr["gt_x"], hr["gt_y"], hr["gt_w"], hr["gt_h"], YESIL, "GT", 2, True)
    kutu(im, orr["final_x"], orr["final_y"], orr["w"], orr["h"], MAGENTA, "TAKIPCI", 2, False)
    hata = ((orr["final_x"] - hr["gt_x"]) ** 2 + (orr["final_y"] - hr["gt_y"]) ** 2) ** 0.5
    s = ["VisDrone  %s  (%s, track %s)   kare %d" % (key, dizi, key.split("/")[1], k),
         "IoU %.3f   merkez hata %.1f px   PSR %.1f   |  %s" % (
             hr["iou"], hata, hr["psr"], not_),
         "kaynak: %s/%07d.jpg  +  cikti/a39a_h123.json (GT) + cikti/dcf_4o.json (takip kutusu)" % (dizi, k + 1)]
    yaz(ad, pano(im, s, orr["durum"]))
