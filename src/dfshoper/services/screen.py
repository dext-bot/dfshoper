from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Tuple

import numpy as np
from mss import mss

Coordinate = Tuple[int, int]


@dataclass
class CaptureRegion:
    left: int
    top: int
    width: int
    height: int

    @classmethod
    def around(cls, center: Coordinate, width: int, height: int) -> "CaptureRegion":
        half_w = width // 2
        half_h = height // 2
        return cls(
            left=max(center[0] - half_w, 0),
            top=max(center[1] - half_h, 0),
            width=width,
            height=height,
        )

    def as_dict(self) -> dict:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


class ScreenCapture:
    """线程安全的屏幕截图器。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mss = mss()

    def grab_region(self, region: CaptureRegion) -> np.ndarray:
        with self._lock:
            shot = self._mss.grab(region.as_dict())
        img = np.array(shot)
        # MSS 返回 BGRA，去掉 Alpha 并转为 BGR
        return img[:, :, :3]

    def pixel_color(self, coordinate: Coordinate) -> Tuple[int, int, int]:
        region = CaptureRegion(left=coordinate[0], top=coordinate[1], width=1, height=1)
        pixel = self.grab_region(region)
        b, g, r = pixel[0, 0]
        return int(r), int(g), int(b)


__all__ = ["ScreenCapture", "CaptureRegion"]
