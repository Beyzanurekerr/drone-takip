"""A6 veri hazirligi dogrulamasi (D1-D10). SALT OKUNUR."""
import glob, hashlib, json, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

A6 = "data/a6"
VID = "data/datasets/visdrone_vid/sequences"
BENCH = ["uav0000117_02622_v", "uav0000137_00458_v"]
SEV = [("57x21", 57), ("40x15", 40), ("30x12", 30), ("20x10", 20),
       ("15x7", 15), ("10x5", 10), ("8x5", 8), ("5x5", 5)]


def kova(u, hedef):
    k = [10**9, 57, 40, 30, 20, 15, 10, 8, 5]
    for i, (ad, v) in enumerate(SEV):
        if v < u <= k[i]:
            hedef[ad] = hedef.get(ad, 0) + 1
            return
    hedef["<=5"] = hedef.get("<=5", 0) + 1


def imza(p, n=48):
    im = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    z = cv2.resize(im, (n, n), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
    z -= z.mean()
    return z / (np.linalg.norm(z) + 1e-9)


def havuz(kok, grup_fn):
    """Bir havuzu tarar: split basina goruntu/kutu, grup-split capraz kontrolu,
    A5 seviyelerinde kutu dagilimi (native ve ag girdisi)."""
    r = {"split": {}, "grup_split": {}, "kova_nat": {}, "kova_ag": {},
         "uzun_ag": [], "sinif": {}}
    for b in ("train", "val", "test"):
        imgs = sorted(glob.glob(f"{kok}/images/{b}/*.jpg"))
        nk = 0
        for ip in imgs:
            ad = os.path.splitext(os.path.basename(ip))[0]
            r["grup_split"].setdefault(grup_fn(ad), set()).add(b)
            H, W = cv2.imread(ip).shape[:2]
            lb = 640.0 / max(W, H)
            lp = f"{kok}/labels/{b}/{ad}.txt"
            for s in open(lp).read().split("\n"):
                if not s.strip():
                    continue
                c, _cx, _cy, w, h = s.split()
                r["sinif"][c] = r["sinif"].get(c, 0) + 1
                u = max(float(w) * W, float(h) * H)
                kova(u, r["kova_nat"]); kova(u * lb, r["kova_ag"])
                r["uzun_ag"].append(u * lb)
                nk += 1
        r["split"][b] = {"goruntu": len(imgs), "kutu": nk}
    r["cakisan_grup"] = sorted(g for g, v in r["grup_split"].items() if len(v) > 1)
    r["grup_sayisi"] = len(r["grup_split"])
    ua = np.array(r["uzun_ag"])
    r["ag_uzun_med"] = round(float(np.median(ua)), 2)
    r["ag_57_alti_yuzde"] = round(float(100 * (ua <= 57).mean()), 2)
    del r["uzun_ag"], r["grup_split"]
    return r


def main():
    out = {}
    out["asama_A"] = havuz(f"{A6}/uavdt_pretrain", lambda a: a.split("_")[0])
    out["asama_B"] = havuz(f"{A6}/visdrone_finetune", lambda a: a.split("_")[0])

    # ---- D7: leakage, uc yontem ----
    a6 = sorted(glob.glob(f"{A6}/*/images/*/*.jpg"))
    bench = [p for v in BENCH for p in sorted(glob.glob(f"{VID}/{v}/*.jpg"))]
    h6 = {}
    for p in a6:
        h6.setdefault(hashlib.md5(open(p, "rb").read()).hexdigest(), []).append(p)
    hb = {hashlib.md5(open(p, "rb").read()).hexdigest() for p in bench}
    ortak = set(h6) & hb
    ad6 = {os.path.basename(p) for p in a6}
    adb = {os.path.basename(p) for p in bench}
    grup6 = {os.path.basename(p).split("_")[0] for p in a6}
    grupb = {"0000117", "0000086", "uav0000117", "uav0000137"}

    B = np.stack([z for z in (imza(p) for p in bench) if z is not None])
    en = 0.0; enp = None; ust95 = 0; ust80 = 0
    blok = 512
    for i in range(0, len(a6), blok):
        Z = []
        adlar = []
        for p in a6[i:i + blok]:
            z = imza(p)
            if z is not None:
                Z.append(z); adlar.append(p)
        if not Z:
            continue
        C = np.stack(Z) @ B.T
        mx = C.max(1)
        ust95 += int((mx > 0.95).sum()); ust80 += int((mx > 0.80).sum())
        j = int(mx.argmax())
        if float(mx[j]) > en:
            en = float(mx[j]); enp = (adlar[j], bench[int(C[j].argmax())])
    out["D7_leakage"] = {
        "a6_goruntu": len(a6), "benchmark_kare": len(bench),
        "exact_hash_cakismasi": len(ortak),
        "a6_ici_tekrar": sum(1 for v in h6.values() if len(v) > 1),
        "dosya_adi_cakismasi": len(ad6 & adb),
        "videoID_cakismasi": sorted(grup6 & grupb),
        "piksel_en_yuksek_korelasyon": round(en, 4),
        "en_yakin_cift": [os.path.basename(enp[0]), enp[1]] if enp else None,
        "r_095_ustu": ust95, "r_080_ustu": ust80}
    json.dump(out, open(f"{A6}/manifest/a6_dogrulama.json", "w"),
              indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
