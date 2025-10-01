from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG = {
    "coordinates": {
        "trade_button": None,
        "main_interface": None,
        "equipment_config": None,
        "buy_button": None,
        "max_quantity_button": None,
        "price_slot_1": None,
        "price_slot_2": None,
    },
    "mode_1": {
        "scan_price": 0.0,
        "delay_ms": 200,
    },
    "mode_2": {
        "scan_price": 0.0,
        "price_button": None,
        "recording_1": [],
        "recording_2": [],
        "stop_color": [0, 0, 0],
        "stop_color_position": None,
        "tolerance": 10,
    },
}


class ConfigManager:
    """Thread-safe configuration loader and writer."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._config: Dict[str, Any] = {}
        self._ensure_exists()
        self.reload()

    def _ensure_exists(self) -> None:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")

    def reload(self) -> None:
        with self._lock:
            self._config = json.loads(self._path.read_text(encoding="utf-8"))

    def save(self) -> None:
        with self._lock:
            self._path.write_text(json.dumps(self._config, indent=2, ensure_ascii=False), encoding="utf-8")

    @property
    def data(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._config))

    def update(self, path: str, value: Any) -> None:
        with self._lock:
            keys = path.split(".")
            current: Dict[str, Any] = self._config
            for key in keys[:-1]:
                if key not in current or not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
            self.save()


__all__ = ["ConfigManager", "DEFAULT_CONFIG"]
