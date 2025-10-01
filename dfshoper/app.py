"""Application entry point."""
from __future__ import annotations

import sys
import time

from PySide6 import QtWidgets

from .config import Config
from .gui.main_window import MainWindow


def ensure_config(config: Config) -> None:
    """Ensure mandatory coordinates are present, otherwise prompt the user."""
    required_points = [
        config.coordinates.trade_button,
        config.coordinates.main_tab,
        config.coordinates.equipment_tab,
        config.coordinates.purchase_button,
        config.coordinates.max_quantity_button,
        config.coordinates.price_regions.price_primary,
        config.coordinates.price_regions.price_secondary,
    ]
    if all(required_points):
        return
    # Wait a few seconds then notify the user via dialog to capture coordinates
    time.sleep(3)


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    config = Config.load()
    ensure_config(config)
    window = MainWindow(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
