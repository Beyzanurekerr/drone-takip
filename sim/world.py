"""Havadan (drone) goruntu simulatoru.

Dunya duz bir zemin (metre biriminde). Kamera nadir (dik asagi) bakiyor,
yukseklik -> olcek, yaw -> donme, x/y -> kaydirma uretiyor.
Araclar dunya koordinatlarinda hareket eder, her karede goruntuye izdusurulur.
Boylece her kare icin kusursuz ground-truth kutusu bilinir.
"""
import math

import cv2
import numpy as np

TPM = 3  # zemin dokusunda metre basina texel
FOCAL = 500.0  # px*m  ->  px_per_m = FOCAL / irtifa


def _noise(h, w, cell, rng):
    small = rng.random((max(2, h // cell), max(2, w // cell))).astype(np.float32)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)


class Ground:
    """Prosedurel zemin dokusu: asfalt, seritler, cim, binalar, agaclar.

    Doku bilerek bol detayli: optik akis (ego-motion) icin koseye ihtiyac var.
    """

    def __init__(self, extent_m=700, seed=1):
        self.extent = extent_m
        n = int(extent_m * TPM)
        self.n = n
        rng = np.random.default_rng(seed)

        g = _noise(n, n, 96, rng) * 0.55 + _noise(n, n, 24, rng) * 0.30 + _noise(n, n, 5, rng) * 0.15
        img = np.empty((n, n, 3), np.float32)
        img[..., 0] = 55 + 45 * g
        img[..., 1] = 85 + 65 * g
        img[..., 2] = 50 + 50 * g
        img = img.astype(np.uint8)
        del g

        def m2t(v):  # metre -> texel
            return int(round(v * TPM))

        # --- ana yol (y = 0 ekseninde, dunya merkezi extent/2) ---
        c = extent_m / 2.0
        self.road_y = c
        road_w = 9.0
        y0, y1 = m2t(c - road_w / 2), m2t(c + road_w / 2)
        cv2.rectangle(img, (0, y0), (n, y1), (68, 68, 70), -1)
        # asfalt grenli olsun
        asf = rng.integers(-9, 9, (y1 - y0, n, 1), dtype=np.int16)
        img[y0:y1] = np.clip(img[y0:y1].astype(np.int16) + asf, 0, 255).astype(np.uint8)
        # orta kesikli serit
        ym = m2t(c)
        for x in range(0, n, m2t(9)):
            cv2.rectangle(img, (x, ym - 1), (x + m2t(3), ym + 1), (215, 215, 215), -1)
        # kenar cizgileri
        cv2.line(img, (0, y0 + 2), (n, y0 + 2), (200, 200, 200), 1)
        cv2.line(img, (0, y1 - 2), (n, y1 - 2), (200, 200, 200), 1)

        # --- dikey yan yollar ---
        for xm in range(60, extent_m, 130):
            x0, x1 = m2t(xm - 3.5), m2t(xm + 3.5)
            cv2.rectangle(img, (x0, 0), (x1, n), (66, 66, 68), -1)

        # --- binalar / park alanlari / agaclar ---
        for _ in range(160):
            bx, by = rng.integers(0, extent_m, 2)
            if abs(by - c) < 14:
                continue
            w_, h_ = rng.integers(8, 26, 2)
            col = tuple(int(v) for v in rng.integers(70, 190, 3))
            cv2.rectangle(img, (m2t(bx), m2t(by)), (m2t(bx + w_), m2t(by + h_)), col, -1)
            cv2.rectangle(img, (m2t(bx), m2t(by)), (m2t(bx + w_), m2t(by + h_)),
                          tuple(int(v * 0.6) for v in col), max(1, TPM // 2))
        for _ in range(500):
            tx, ty = rng.integers(0, extent_m, 2)
            if abs(ty - c) < 8:
                continue
            cv2.circle(img, (m2t(tx), m2t(ty)), int(rng.integers(2, 5) * TPM), (30, 70, 35), -1)

        # kucuk olcekli detay: optik akis kose bulabilsin diye (calilar, taslar)
        for _ in range(4000):
            tx, ty = rng.integers(0, extent_m, 2)
            if abs(ty - c) < 7:
                continue
            r = int(rng.integers(1, 3) * TPM // 2)
            col = (int(rng.integers(25, 60)), int(rng.integers(60, 110)), int(rng.integers(25, 60)))
            cv2.circle(img, (m2t(tx), m2t(ty)), max(1, r), col, -1)
        # tarla sinirlari
        for _ in range(70):
            tx, ty = rng.integers(0, extent_m, 2)
            L = int(rng.integers(20, 70))
            if rng.random() < 0.5:
                cv2.line(img, (m2t(tx), m2t(ty)), (m2t(tx + L), m2t(ty)), (60, 95, 75), TPM // 2 + 1)
            else:
                cv2.line(img, (m2t(tx), m2t(ty)), (m2t(tx), m2t(ty + L)), (60, 95, 75), TPM // 2 + 1)

        # otopark + park halinde araclar: STATIK celgiciler
        # (hareket tabanli tespit bunlari elemek zorunda -> gercekci zorluk)
        for px, py in [(120, c + 26), (300, c - 34), (470, c + 30)]:
            cv2.rectangle(img, (m2t(px), m2t(py)), (m2t(px + 40), m2t(py + 20)), (72, 72, 74), -1)
            for i in range(8):
                for j in range(3):
                    cx_, cy_ = px + 3 + i * 4.6, py + 3 + j * 6.0
                    col = tuple(int(v) for v in rng.integers(45, 210, 3))
                    cv2.rectangle(img, (m2t(cx_), m2t(cy_)),
                                  (m2t(cx_ + 4.4), m2t(cy_ + 1.9)), col, -1)

        self.tex = img


class Vehicle:
    """Basit arac modeli: sabit hiz, sabit/degisken donus orani."""

    def __init__(self, x, y, heading, speed, color, length=4.6, width=1.9,
                 turn_rate=0.0, wobble=0.0, name=""):
        self.x, self.y = float(x), float(y)
        self.h = math.radians(heading)
        self.speed = speed
        self.color = color
        self.L, self.W = length, width
        self.turn_rate = math.radians(turn_rate)
        self.wobble = wobble
        self.name = name
        self.t = 0.0

    def step(self, dt):
        self.t += dt
        self.h += self.turn_rate * dt
        hh = self.h + self.wobble * math.sin(self.t * 1.3)
        self.x += math.cos(hh) * self.speed * dt
        self.y += math.sin(hh) * self.speed * dt

    def corners(self):
        ca, sa = math.cos(self.h), math.sin(self.h)
        hl, hw = self.L / 2, self.W / 2
        pts = [(+hl, +hw), (+hl, -hw), (-hl, -hw), (-hl, +hw)]
        return np.array([[self.x + px * ca - py * sa, self.y + px * sa + py * ca] for px, py in pts],
                        np.float32)


class Camera:
    """Nadir bakan drone kamerasi."""

    def __init__(self, w=640, h=480, alt=60.0, yaw=0.0):
        self.w, self.h = w, h
        self.alt = alt
        self.yaw = yaw
        self.x = self.y = 0.0
        self.jit_x = self.jit_y = self.jit_yaw = 0.0

    @property
    def ppm(self):
        return FOCAL / self.alt

    def matrix(self):
        s = self.ppm
        th = self.yaw + self.jit_yaw
        ct, st = math.cos(th), math.sin(th)
        A = s * np.array([[ct, st], [-st, ct]], np.float32)
        t = np.array([self.w / 2, self.h / 2], np.float32) - A @ np.array(
            [self.x + self.jit_x, self.y + self.jit_y], np.float32)
        return np.hstack([A, t.reshape(2, 1)]).astype(np.float32)

    def project(self, pts_world):
        M = self.matrix()
        p = np.asarray(pts_world, np.float32).reshape(-1, 2)
        return p @ M[:, :2].T + M[:, 2]


class Scene:
    def __init__(self, ground, camera, vehicles, occluders=(), noise=4.0, seed=7):
        self.ground = ground
        self.cam = camera
        self.vehicles = list(vehicles)
        self.occluders = list(occluders)  # (x, y, w, h) metre, araclarin USTUNE cizilir
        self.noise = noise
        self.rng = np.random.default_rng(seed)

    def step(self, dt):
        for v in self.vehicles:
            v.step(dt)

    def render(self):
        cam = self.cam
        M = cam.matrix()
        Mt = M.copy()
        Mt[:, :2] /= TPM  # texel -> metre
        img = cv2.warpAffine(self.ground.tex, Mt, (cam.w, cam.h),
                             flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        SH = 3  # sabit noktali cizim (1/8 px) -> kucuk araclarda duzgun gorunum
        for v in self.vehicles:
            pc = cam.project(v.corners())
            if pc[:, 0].max() < -20 or pc[:, 0].min() > cam.w + 20:
                continue
            if pc[:, 1].max() < -20 or pc[:, 1].min() > cam.h + 20:
                continue
            golge = (pc + np.array([2.0, 2.5], np.float32) * cam.ppm / 10.0)
            cv2.fillConvexPoly(img, (golge * (1 << SH)).astype(np.int32),
                               (25, 30, 30), cv2.LINE_AA, SH)
            cv2.fillConvexPoly(img, (pc * (1 << SH)).astype(np.int32),
                               v.color, cv2.LINE_AA, SH)
            if cam.ppm * v.L > 14:  # yeterince buyukse cam/tavan detayi
                cab = pc.mean(0) + (pc[[0, 1]].mean(0) - pc.mean(0)) * 0.35
                r = max(1.0, cam.ppm * v.W * 0.32)
                cv2.circle(img, tuple((cab * (1 << SH)).astype(np.int32)), int(r * (1 << SH)),
                           tuple(int(c * 0.45) for c in v.color), -1, cv2.LINE_AA, SH)

        for (ox, oy, ow, oh) in self.occluders:
            pts = np.array([[ox, oy], [ox + ow, oy], [ox + ow, oy + oh], [ox, oy + oh]], np.float32)
            pc = cam.project(pts)
            cv2.fillConvexPoly(img, (pc * (1 << SH)).astype(np.int32), (120, 118, 115), cv2.LINE_AA, SH)

        if self.noise > 0:
            n = self.rng.normal(0, self.noise, img.shape[:2]).astype(np.int16)
            img = np.clip(img.astype(np.int16) + n[..., None], 0, 255).astype(np.uint8)
        return img

    def gt_box(self, vehicle):
        """Hedefin eksen-hizali ground-truth kutusu (x, y, w, h)."""
        pc = self.cam.project(vehicle.corners())
        x0, y0 = pc.min(0)
        x1, y1 = pc.max(0)
        return np.array([x0, y0, x1 - x0, y1 - y0], np.float32)

    def visible(self, vehicle):
        b = self.gt_box(vehicle)
        cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
        if not (0 <= cx < self.cam.w and 0 <= cy < self.cam.h):
            return False
        for (ox, oy, ow, oh) in self.occluders:  # kapatici altinda mi?
            if ox <= vehicle.x <= ox + ow and oy <= vehicle.y <= oy + oh:
                return False
        return True
