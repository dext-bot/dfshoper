from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

Coordinate = Tuple[int, int]
RGBColor = Tuple[int, int, int]


@dataclass
class AnchorConfig:
    trade_button: Optional[Coordinate] = None
    main_button: Optional[Coordinate] = None
    equipment_button: Optional[Coordinate] = None
    purchase_button: Optional[Coordinate] = None
    max_quantity_button: Optional[Coordinate] = None
    price_primary: Optional[Coordinate] = None
    price_secondary: Optional[Coordinate] = None


@dataclass
class ModeOneItem:
    name: str
    coordinate: Coordinate
    threshold: float
    poll_interval_ms: int
    active: bool = True


@dataclass
class ModeOneConfig:
    poll_interval_ms: int = 500
    items: List[ModeOneItem] = field(default_factory=list)


@dataclass
class TerminateColor:
    coordinate: Optional[Coordinate] = None
    rgb: RGBColor = (255, 255, 255)


@dataclass
class ModeTwoConfig:
    poll_interval_ms: int = 800
    price_anchor: Optional[Coordinate] = None
    threshold: float = 0.0
    operation_high: Optional[str] = None
    operation_low: Optional[str] = None
    terminate_color: TerminateColor = field(default_factory=TerminateColor)


@dataclass
class AppConfig:
    anchors: AnchorConfig = field(default_factory=AnchorConfig)
    mode_one: ModeOneConfig = field(default_factory=ModeOneConfig)
    mode_two: ModeTwoConfig = field(default_factory=ModeTwoConfig)


class ConfigManager:
    """线程安全的配置文件读写管理器。"""

    def __init__(self, config_path: Path, default_path: Optional[Path] = None) -> None:
        self._config_path = config_path
        self._default_path = default_path
        self._lock = threading.Lock()
        self._config = self._load()

    @property
    def config(self) -> AppConfig:
        return self._config

    def _load(self) -> AppConfig:
        if not self._config_path.exists():
            if self._default_path and self._default_path.exists():
                data = json.loads(self._default_path.read_text(encoding="utf-8"))
            else:
                data = {}
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
        return self._parse(data)

    def _parse(self, data: Dict[str, Any]) -> AppConfig:
        anchors = data.get("anchors", {})
        mode_one = data.get("mode_one", {})
        mode_two = data.get("mode_two", {})

        anchor_config = AnchorConfig(
            trade_button=self._tuple_or_none(anchors.get("trade_button")),
            main_button=self._tuple_or_none(anchors.get("main_button")),
            equipment_button=self._tuple_or_none(anchors.get("equipment_button")),
            purchase_button=self._tuple_or_none(anchors.get("purchase_button")),
            max_quantity_button=self._tuple_or_none(anchors.get("max_quantity_button")),
            price_primary=self._tuple_or_none(anchors.get("price_primary")),
            price_secondary=self._tuple_or_none(anchors.get("price_secondary")),
        )

        mode_one_items = []
        for item in mode_one.get("items", []):
            coordinate = self._tuple_or_none(item.get("coordinate"))
            if not coordinate:
                continue
            mode_one_items.append(
                ModeOneItem(
                    name=item.get("name", "商品"),
                    coordinate=coordinate,
                    threshold=float(item.get("threshold", 0)),
                    poll_interval_ms=int(item.get("poll_interval_ms", mode_one.get("poll_interval_ms", 500))),
                    active=bool(item.get("active", True)),
                )
            )

        terminate_color = mode_two.get("terminate_color", {})
        terminate_color_config = TerminateColor(
            coordinate=self._tuple_or_none(terminate_color.get("coordinate")),
            rgb=self._tuple_or_rgb(terminate_color.get("rgb", [255, 255, 255])),
        )

        mode_two_config = ModeTwoConfig(
            poll_interval_ms=int(mode_two.get("poll_interval_ms", 800)),
            price_anchor=self._tuple_or_none(mode_two.get("price_anchor")),
            threshold=float(mode_two.get("threshold", 0)),
            operation_high=mode_two.get("operation_high"),
            operation_low=mode_two.get("operation_low"),
            terminate_color=terminate_color_config,
        )

        return AppConfig(
            anchors=anchor_config,
            mode_one=ModeOneConfig(
                poll_interval_ms=int(mode_one.get("poll_interval_ms", 500)),
                items=mode_one_items,
            ),
            mode_two=mode_two_config,
        )

    def save(self) -> None:
        with self._lock:
            data = self.to_dict()
            self._config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def to_dict(self) -> Dict[str, Any]:
        anchors = self._config.anchors
        mode_one = self._config.mode_one
        mode_two = self._config.mode_two
        return {
            "anchors": {
                "trade_button": self._list_or_none(anchors.trade_button),
                "main_button": self._list_or_none(anchors.main_button),
                "equipment_button": self._list_or_none(anchors.equipment_button),
                "purchase_button": self._list_or_none(anchors.purchase_button),
                "max_quantity_button": self._list_or_none(anchors.max_quantity_button),
                "price_primary": self._list_or_none(anchors.price_primary),
                "price_secondary": self._list_or_none(anchors.price_secondary),
            },
            "mode_one": {
                "poll_interval_ms": mode_one.poll_interval_ms,
                "items": [
                    {
                        "name": item.name,
                        "coordinate": self._list_or_none(item.coordinate),
                        "threshold": item.threshold,
                        "poll_interval_ms": item.poll_interval_ms,
                        "active": item.active,
                    }
                    for item in mode_one.items
                ],
            },
            "mode_two": {
                "poll_interval_ms": mode_two.poll_interval_ms,
                "price_anchor": self._list_or_none(mode_two.price_anchor),
                "threshold": mode_two.threshold,
                "operation_high": mode_two.operation_high,
                "operation_low": mode_two.operation_low,
                "terminate_color": {
                    "coordinate": self._list_or_none(mode_two.terminate_color.coordinate),
                    "rgb": list(mode_two.terminate_color.rgb),
                },
            },
        }

    def update_anchor(self, name: str, coordinate: Coordinate) -> None:
        with self._lock:
            if not hasattr(self._config.anchors, name):
                raise AttributeError(f"Unknown anchor: {name}")
            setattr(self._config.anchors, name, coordinate)
            self.save()

    def add_mode_one_item(self, item: ModeOneItem) -> None:
        with self._lock:
            self._config.mode_one.items.append(item)
            self.save()

    def update_mode_two(self, **kwargs: Any) -> None:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._config.mode_two, key):
                    setattr(self._config.mode_two, key, value)
            self.save()

    @staticmethod
    def _tuple_or_none(value: Optional[List[int]]) -> Optional[Coordinate]:
        if value is None:
            return None
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return int(value[0]), int(value[1])
        return None

    @staticmethod
    def _tuple_or_rgb(value: Optional[List[int]]) -> RGBColor:
        if isinstance(value, (list, tuple)) and len(value) == 3:
            return int(value[0]), int(value[1]), int(value[2])
        return 255, 255, 255

    @staticmethod
    def _list_or_none(value: Optional[Coordinate]) -> Optional[List[int]]:
        if value is None:
            return None
        return [int(value[0]), int(value[1])]


__all__ = [
    "AppConfig",
    "AnchorConfig",
    "ConfigManager",
    "ModeOneConfig",
    "ModeOneItem",
    "ModeTwoConfig",
    "TerminateColor",
]
