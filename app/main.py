from __future__ import annotations

import sys
import time

from PySide6.QtWidgets import QApplication

from .config import load_config
from .ui.main_window import MainWindow


def main() -> None:
    config, is_new = load_config()
    app = QApplication(sys.argv)
    window = MainWindow(config, is_new_config=is_new)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
