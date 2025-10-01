from __future__ import annotations

import logging
import sys
import threading
import time
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtWidgets import QApplication, QLabel

from dfshoper.config import AppConfig, ConfigManager
from dfshoper.modes.mode_one import ModeOneController
from dfshoper.modes.mode_two import ModeTwoController
from dfshoper.services.actions import ActionExecutor, ActionRecorder
from dfshoper.services.ocr import OcrEngine
from dfshoper.services.screen import ScreenCapture
from dfshoper.ui.coordinate_picker import CoordinatePicker
from dfshoper.ui.main_window import MainWindow
from pynput import keyboard

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
LOGGER = logging.getLogger(__name__)


class _StatusBridge(QObject):
    statusChanged = Signal(str)

    def __init__(self, label: QLabel) -> None:
        super().__init__()
        self._label = label
        self.statusChanged.connect(label.setText, Qt.QueuedConnection)


class Application:
    def __init__(self, config: AppConfig, manager: ConfigManager) -> None:
        self._config = config
        self._manager = manager
        self._capture = ScreenCapture()
        self._ocr = OcrEngine(gpu=True)
        self._executor = ActionExecutor()
        self._recorder = ActionRecorder()
        self._mode_one = ModeOneController(config.anchors, self._capture, self._ocr, self._executor, self._status)
        self._mode_two = ModeTwoController(self._capture, self._ocr, self._executor, self._status)
        self._app = QApplication(sys.argv)
        self._window = MainWindow(manager)
        self._window.show()
        self._status_bridge = _StatusBridge(self._window._status_label)  # type: ignore[attr-defined]
        self._anchor_picker = CoordinatePicker()
        self._window._mode_one_widget.startMonitorRequested.connect(self._mode_one.start)  # type: ignore[attr-defined]
        self._window._mode_one_widget.stopMonitorRequested.connect(self._mode_one.stop)  # type: ignore[attr-defined]
        self._window._mode_one_widget.addItemRequested.connect(self._mode_one.add_item)  # type: ignore[attr-defined]
        self._mode_one.load_items(config.mode_one.items)

        self._window._mode_two_widget.startRequested.connect(self._mode_two.start)  # type: ignore[attr-defined]
        self._window._mode_two_widget.stopRequested.connect(self._mode_two.stop)  # type: ignore[attr-defined]
        self._window._mode_two_widget.configChanged.connect(self._mode_two.configure)  # type: ignore[attr-defined]
        self._window.operationRecordRequested.connect(self._on_record_requested)
        self._mode_two.configure(config.mode_two)
        self._mode_two.load_scripts(config.mode_two.operation_high, config.mode_two.operation_low)

        missing = self._find_missing_anchors()
        if missing:
            QTimer.singleShot(3000, lambda: self._prompt_missing_anchors(missing))

    def _status(self, message: str) -> None:
        LOGGER.info(message)
        self._status_bridge.statusChanged.emit(message)

    def _find_missing_anchors(self) -> List[str]:
        anchors = self._config.anchors
        missing = []
        for name, coord in vars(anchors).items():
            if coord is None:
                missing.append(name)
        return missing

    def _prompt_missing_anchors(self, missing: List[str]) -> None:
        self._window.show_missing_anchor_warning(missing)
        self._missing_anchor_iter = iter(missing)
        self._anchor_picker.coordinateSelected.connect(self._on_anchor_selected)
        self._request_next_anchor()

    def _request_next_anchor(self) -> None:
        try:
            self._current_anchor = next(self._missing_anchor_iter)
        except StopIteration:
            self._anchor_picker.coordinateSelected.disconnect(self._on_anchor_selected)
            self._status("关键坐标配置完成")
            return
        anchor_name = self._current_anchor
        friendly = {
            "trade_button": "交易行按钮",
            "main_button": "主界面按钮",
            "equipment_button": "配置装备按钮",
            "purchase_button": "购买按钮",
            "max_quantity_button": "最高数量按钮",
            "price_primary": "价格框1",
            "price_secondary": "价格框2",
        }.get(anchor_name, anchor_name)
        self._status(f"请拖动取点：{friendly}")
        self._anchor_picker.start_capture()

    def _on_anchor_selected(self, x: int, y: int) -> None:
        coordinate = (x, y)
        anchor = getattr(self, "_current_anchor", None)
        if anchor:
            self._manager.update_anchor(anchor, coordinate)
            self._status(f"{anchor} 已更新为 {coordinate}")
        self._request_next_anchor()

    def _on_record_requested(self, key: str, path: str) -> None:
        threading.Thread(target=self._record_operation, args=(key, Path(path)), daemon=True).start()

    def _record_operation(self, key: str, path: Path) -> None:
        self._status(f"录制操作 {key} 将在 3 秒后开始，请准备...")
        time.sleep(3)
        self._recorder.start()
        stop_event = threading.Event()

        def on_press(k: keyboard.Key | keyboard.KeyCode) -> bool:
            if k == keyboard.Key.f9:
                stop_event.set()
                return False
            return True

        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        self._status("录制中，按 F9 结束")
        stop_event.wait()
        script = self._recorder.stop()
        listener.stop()
        script.save(path)
        operations = getattr(self._window, "_mode_two_operations", {})
        self._mode_two.load_scripts(operations.get("high"), operations.get("low"))
        self._window.load_operations(operations.get("high"), operations.get("low"))
        self._status(f"操作 {key} 已保存: {path}")

    def run(self) -> int:
        return self._app.exec()


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    config_path = base / ".." / "config" / "config.json"
    default_path = base / ".." / "config" / "default_config.json"
    manager = ConfigManager(config_path=config_path.resolve(), default_path=default_path.resolve())
    app = Application(manager.config, manager)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
