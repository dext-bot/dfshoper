from __future__ import annotations

import json
import threading
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, Tuple

from .coordinates import Point, Region

CONFIG_PATH = Path("config/config.json")
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class GlobalCoordinates:
    trade_button: Point = Point(0, 0)
    main_interface: Point = Point(0, 0)
    equipment_tab: Point = Point(0, 0)
    purchase_button: Point = Point(0, 0)
    max_quantity_button: Point = Point(0, 0)
    price_primary_region: Region = Region(Point(0, 0), width=120, height=40)
    price_secondary_region: Region = Region(Point(0, 0), width=120, height=40)


@dataclass
class Mode1Item:
    name: str
    target_point: Point
    min_price: float
    delay_ms: int = 350


@dataclass
class Mode2Settings:
    price_region: Region = Region(Point(0, 0), width=120, height=40)
    min_price: float = 0.0
    action1: list = field(default_factory=list)
    action2: list = field(default_factory=list)
    post_check_point: Point = Point(0, 0)
    post_check_color: Tuple[int, int, int] = (0, 0, 0)


@dataclass
class AppConfig:
    coordinates: GlobalCoordinates = field(default_factory=GlobalCoordinates)
    mode1_items: Dict[str, Mode1Item] = field(default_factory=dict)
    mode2: Mode2Settings = field(default_factory=Mode2Settings)

    def to_dict(self) -> dict:
        data = asdict(self)
        for key, item in list(self.mode1_items.items()):
            data["mode1_items"][key] = asdict(item)
        return data


_config_lock = threading.Lock()


def _point_from_data(data: dict) -> Point:
    return Point(data.get("x", 0), data.get("y", 0))


def _region_from_data(data: dict) -> Region:
    return Region(
        origin=_point_from_data(data.get("origin", {})),
        width=data.get("width", 120),
        height=data.get("height", 40),
    )


def _mode1_item_from_data(name: str, data: dict) -> Mode1Item:
    return Mode1Item(
        name=name,
        target_point=_point_from_data(data.get("target_point", {})),
        min_price=float(data.get("min_price", 0.0)),
        delay_ms=int(data.get("delay_ms", 350)),
    )


def _mode2_settings_from_data(data: dict) -> Mode2Settings:
    return Mode2Settings(
        price_region=_region_from_data(data.get("price_region", {})),
        min_price=float(data.get("min_price", 0.0)),
        action1=data.get("action1", []),
        action2=data.get("action2", []),
        post_check_point=_point_from_data(data.get("post_check_point", {})),
        post_check_color=tuple(data.get("post_check_color", (0, 0, 0))),
    )


def load_config() -> tuple[AppConfig, bool]:
    with _config_lock:
        if not CONFIG_PATH.exists():
            cfg = AppConfig()
            save_config(cfg)
            return cfg, True
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        coords = data.get("coordinates", {})
        config = AppConfig(
            coordinates=GlobalCoordinates(
                trade_button=_point_from_data(coords.get("trade_button", {})),
                main_interface=_point_from_data(coords.get("main_interface", {})),
                equipment_tab=_point_from_data(coords.get("equipment_tab", {})),
                purchase_button=_point_from_data(coords.get("purchase_button", {})),
                max_quantity_button=_point_from_data(coords.get("max_quantity_button", {})),
                price_primary_region=_region_from_data(coords.get("price_primary_region", {})),
                price_secondary_region=_region_from_data(coords.get("price_secondary_region", {})),
            ),
            mode1_items={
                name: _mode1_item_from_data(name, item)
                for name, item in data.get("mode1_items", {}).items()
            },
            mode2=_mode2_settings_from_data(data.get("mode2", {})),
        )
        return config, False


def save_config(config: AppConfig) -> None:
    with _config_lock:
        CONFIG_PATH.write_text(json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
