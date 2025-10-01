from __future__ import annotations

import mss
import numpy as np
from dataclasses import dataclass
from typing import Tuple


@dataclass
class ScreenRegion:
    x: int
    y: int
    width: int
    height: int

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)


class ScreenCapture:
    def __init__(self) -> None:
        self._sct = mss.mss()

    def grab(self, region: ScreenRegion) -> np.ndarray:
        bbox = {
            "left": region.x,
            "top": region.y,
            "width": region.width,
            "height": region.height,
        }
        raw = self._sct.grab(bbox)
        return np.array(raw)


__all__ = ["ScreenCapture", "ScreenRegion"]
