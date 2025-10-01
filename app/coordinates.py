from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}


@dataclass
class Region:
    origin: Point
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            "origin": self.origin.to_dict(),
            "width": self.width,
            "height": self.height,
        }

    @property
    def bbox(self) -> dict:
        return {
            "top": self.origin.y,
            "left": self.origin.x,
            "width": self.width,
            "height": self.height,
        }
