from __future__ import annotations

import time
import mss
import numpy as np

from .coordinates import Point, Region


def grab_region(region: Region) -> np.ndarray:
    with mss.mss() as sct:
        monitor = region.bbox
        raw = sct.grab(monitor)
        img = np.array(raw)[:, :, :3]
        return img


def grab_pixel(point: Point) -> tuple[int, int, int]:
    region = Region(point, 1, 1)
    img = grab_region(region)
    r, g, b = img[0, 0]
    return int(r), int(g), int(b)
