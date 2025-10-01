"""Configuration management for dfshoper."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional, Tuple
import json

CONFIG_PATH = Path("config.json")


@dataclass
class Point:
    x: int
    y: int


@dataclass
class Region:
    left: int
    top: int
    width: int
    height: int

    @property
    def as_tuple(self) -> Tuple[int, int, int, int]:
        return self.left, self.top, self.width, self.height


@dataclass
class PriceRegions:
    price_primary: Optional[Region] = None
    price_secondary: Optional[Region] = None


@dataclass
class Coordinates:
    trade_button: Optional[Point] = None
    main_tab: Optional[Point] = None
    equipment_tab: Optional[Point] = None
    purchase_button: Optional[Point] = None
    max_quantity_button: Optional[Point] = None
    price_regions: PriceRegions = field(default_factory=PriceRegions)


@dataclass
class ModeOneSettings:
    min_price: float = 0.0
    poll_delay_ms: int = 500


@dataclass
class ModeTwoSettings:
    price_trigger_point: Optional[Region] = None
    trigger_price: float = 0.0
    macro_success_color: Tuple[int, int, int] = (0, 0, 0)
    macro_success_point: Optional[Point] = None


@dataclass
class RecorderSettings:
    macro_a: list = field(default_factory=list)
    macro_b: list = field(default_factory=list)


@dataclass
class Config:
    coordinates: Coordinates = field(default_factory=Coordinates)
    mode_one: ModeOneSettings = field(default_factory=ModeOneSettings)
    mode_two: ModeTwoSettings = field(default_factory=ModeTwoSettings)
    recorder: RecorderSettings = field(default_factory=RecorderSettings)

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Config":
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict) -> "Config":
        coordinates = data.get("coordinates", {})
        price_regions = coordinates.get("price_regions", {})
        mode_one = data.get("mode_one", {})
        mode_two = data.get("mode_two", {})
        recorder = data.get("recorder", {})

        config = cls(
            coordinates=Coordinates(
                trade_button=_point_from_dict(coordinates.get("trade_button")),
                main_tab=_point_from_dict(coordinates.get("main_tab")),
                equipment_tab=_point_from_dict(coordinates.get("equipment_tab")),
                purchase_button=_point_from_dict(coordinates.get("purchase_button")),
                max_quantity_button=_point_from_dict(coordinates.get("max_quantity_button")),
                price_regions=PriceRegions(
                    price_primary=_region_from_dict(price_regions.get("price_primary")),
                    price_secondary=_region_from_dict(price_regions.get("price_secondary")),
                ),
            ),
            mode_one=ModeOneSettings(
                min_price=mode_one.get("min_price", 0.0),
                poll_delay_ms=mode_one.get("poll_delay_ms", 500),
            ),
            mode_two=ModeTwoSettings(
                price_trigger_point=_region_from_dict(mode_two.get("price_trigger_point")),
                trigger_price=mode_two.get("trigger_price", 0.0),
                macro_success_color=tuple(mode_two.get("macro_success_color", (0, 0, 0))),
                macro_success_point=_point_from_dict(mode_two.get("macro_success_point")),
            ),
            recorder=RecorderSettings(
                macro_a=recorder.get("macro_a", []),
                macro_b=recorder.get("macro_b", []),
            ),
        )
        return config

    def save(self, path: Path = CONFIG_PATH) -> None:
        data = asdict(self)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def _point_from_dict(data: Optional[Dict]) -> Optional[Point]:
    if not data:
        return None
    return Point(x=int(data["x"]), y=int(data["y"]))


def _region_from_dict(data: Optional[Dict]) -> Optional[Region]:
    if not data:
        return None
    return Region(
        left=int(data["left"]),
        top=int(data["top"]),
        width=int(data["width"]),
        height=int(data["height"]),
    )
