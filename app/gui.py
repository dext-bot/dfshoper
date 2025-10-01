from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pyautogui
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .automation import Action, Automation
from .config_manager import ConfigManager
from .ocr import OCREngine
from .screen_capture import ScreenCapture, ScreenRegion


REQUIRED_COORDS = [
    "trade_button",
    "main_interface",
    "equipment_config",
    "buy_button",
    "max_quantity_button",
    "price_slot_1",
    "price_slot_2",
]


def ndarray_to_qpixmap(array: np.ndarray) -> QPixmap:
    if array.shape[2] == 4:
        fmt = QImage.Format_RGBA8888
        bytes_per_line = 4 * array.shape[1]
    else:
        fmt = QImage.Format_RGB888
        bytes_per_line = 3 * array.shape[1]
    h, w, _ = array.shape
    image = QImage(array.data, w, h, bytes_per_line, fmt)
    return QPixmap.fromImage(image)


class CoordinateCaptureDialog(QDialog):
    def __init__(self, screenshot: np.ndarray, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("请选择坐标")
        self.setModal(True)
        layout = QVBoxLayout(self)
        self._label = QLabel()
        self._pixmap = ndarray_to_qpixmap(screenshot)
        self._label.setPixmap(self._pixmap)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)
        self._coords: Optional[QPoint] = None
        self._label.installEventFilter(self)
        self.setFixedSize(self._pixmap.size())

    def eventFilter(self, source, event):  # type: ignore[override]
        if source is self._label and event.type() == QEvent.Type.MouseButtonPress:
            self._coords = event.position().toPoint()
            self.accept()
            return True
        return super().eventFilter(source, event)

    def coords(self) -> Optional[QPoint]:
        return self._coords


@dataclass
class Mode1Config:
    threshold: float
    delay_ms: int


@dataclass
class Mode2Config:
    threshold: float
    stop_color: tuple[int, int, int]
    tolerance: int


class MainWindow(QMainWindow):
    def __init__(self, config: ConfigManager, ocr: OCREngine) -> None:
        super().__init__()
        self.config = config
        self.ocr = ocr
        self.automation = Automation()
        self.screen_capture = ScreenCapture()
        self.setWindowTitle("游戏商城助手")
        self._hotkey = "F8"
        self._init_ui()
        QTimer.singleShot(2000, self._verify_coordinates)

    def _verify_coordinates(self) -> None:
        data = self.config.data
        missing = [name for name in REQUIRED_COORDS if data["coordinates"].get(name) is None]
        if not missing:
            return
        screenshot = pyautogui.screenshot()
        screenshot_np = np.array(screenshot)
        dialog = CoordinateCaptureDialog(screenshot_np, self)
        collected: Dict[str, tuple[int, int]] = {}
        for name in missing:
            dialog.setWindowTitle(f"点击选择 {name} 坐标")
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.coords():
                point = dialog.coords()
                assert point is not None
                collected[name] = (point.x(), point.y())
        for key, value in collected.items():
            self.config.update(f"coordinates.{key}", list(value))
        if collected:
            QMessageBox.information(self, "完成", "已更新坐标配置。")

    def _init_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self._build_coordinate_section())
        layout.addWidget(self._build_mode1_section())
        layout.addWidget(self._build_mode2_section())
        layout.addStretch(1)
        self.setCentralWidget(central)

    def _build_coordinate_section(self) -> QWidget:
        box = QGroupBox("基础坐标配置")
        layout = QGridLayout(box)
        self.coord_fields: Dict[str, QLineEdit] = {}
        data = self.config.data
        for row, key in enumerate(REQUIRED_COORDS):
            label = QLabel(key)
            field = QLineEdit()
            coords = data["coordinates"].get(key)
            field.setText(json.dumps(coords) if coords else "")
            button = QPushButton("采集")
            button.clicked.connect(lambda _, name=key: self._capture_coordinate(name))
            layout.addWidget(label, row, 0)
            layout.addWidget(field, row, 1)
            layout.addWidget(button, row, 2)
        self.coord_fields[key] = field
        save_button = QPushButton("保存配置")
        save_button.clicked.connect(self._save_coordinates)
        layout.addWidget(save_button, len(REQUIRED_COORDS), 1)
        return box

    def _has_required_coords(self, keys: list[str]) -> bool:
        coords = self.config.data["coordinates"]
        for key in keys:
            value = coords.get(key)
            if not value or len(value) != 2:
                return False
        return True

    def _capture_coordinate(self, key: str) -> None:
        QMessageBox.information(self, "提示", f"请在 3 秒内移动鼠标到 {key}，时间到后将自动记录位置")
        time.sleep(3)
        current = pyautogui.position()
        self.config.update(f"coordinates.{key}", [current.x, current.y])
        self.coord_fields[key].setText(json.dumps([current.x, current.y]))

    def _save_coordinates(self) -> None:
        for key, field in self.coord_fields.items():
            text = field.text().strip()
            if not text:
                continue
            try:
                coords = json.loads(text)
                if isinstance(coords, list) and len(coords) == 2:
                    self.config.update(f"coordinates.{key}", coords)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "错误", f"坐标格式错误: {key}")
        QMessageBox.information(self, "成功", "坐标已保存。")

    def _build_mode1_section(self) -> QWidget:
        box = QGroupBox("模式 1")
        layout = QGridLayout(box)
        layout.addWidget(QLabel("最低价格"), 0, 0)
        self.mode1_price = QLineEdit(str(self.config.data["mode_1"]["scan_price"]))
        layout.addWidget(self.mode1_price, 0, 1)
        layout.addWidget(QLabel("延迟 (ms)"), 1, 0)
        self.mode1_delay = QSpinBox()
        self.mode1_delay.setRange(0, 10_000)
        self.mode1_delay.setValue(int(self.config.data["mode_1"]["delay_ms"]))
        layout.addWidget(self.mode1_delay, 1, 1)
        start_button = QPushButton("启动模式1")
        start_button.clicked.connect(self._start_mode1)
        layout.addWidget(start_button, 2, 0, 1, 2)
        return box

    def _build_mode2_section(self) -> QWidget:
        box = QGroupBox("模式 2")
        layout = QGridLayout(box)
        layout.addWidget(QLabel("最低价格"), 0, 0)
        self.mode2_price = QLineEdit(str(self.config.data["mode_2"]["scan_price"]))
        layout.addWidget(self.mode2_price, 0, 1)
        layout.addWidget(QLabel("停止颜色 (R,G,B)"), 1, 0)
        self.mode2_color = QLineEdit(
            ",".join(str(c) for c in self.config.data["mode_2"]["stop_color"])
        )
        layout.addWidget(self.mode2_color, 1, 1)
        layout.addWidget(QLabel("容差"), 2, 0)
        self.mode2_tolerance = QSpinBox()
        self.mode2_tolerance.setRange(0, 255)
        self.mode2_tolerance.setValue(int(self.config.data["mode_2"]["tolerance"]))
        layout.addWidget(self.mode2_tolerance, 2, 1)
        record1_button = QPushButton("导入录制1")
        record1_button.clicked.connect(lambda: self._load_recording("mode_2.recording_1"))
        record2_button = QPushButton("导入录制2")
        record2_button.clicked.connect(lambda: self._load_recording("mode_2.recording_2"))
        layout.addWidget(record1_button, 3, 0)
        layout.addWidget(record2_button, 3, 1)
        start_button = QPushButton("启动模式2")
        start_button.clicked.connect(self._start_mode2)
        layout.addWidget(start_button, 4, 0, 1, 2)
        return box

    def _load_recording(self, key: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择动作文件", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.config.update(key, data)
        QMessageBox.information(self, "完成", "动作已导入。")

    def _start_mode1(self) -> None:
        try:
            price_threshold = float(self.mode1_price.text())
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入正确的价格")
            return
        delay_ms = int(self.mode1_delay.value())
        self.config.update("mode_1.scan_price", price_threshold)
        self.config.update("mode_1.delay_ms", delay_ms)
        if not self._has_required_coords(["price_slot_1", "price_slot_2", "max_quantity_button", "buy_button"]):
            QMessageBox.warning(self, "错误", "请先配置模式1所需的坐标")
            return
        worker = threading.Thread(target=self._run_mode1, args=(Mode1Config(price_threshold, delay_ms),), daemon=True)
        worker.start()

    def _run_mode1(self, config: Mode1Config) -> None:
        coordinates = self.config.data["coordinates"]
        price_region1 = ScreenRegion(int(coordinates["price_slot_1"][0]), int(coordinates["price_slot_1"][1]), 120, 60)
        price_region2 = ScreenRegion(int(coordinates["price_slot_2"][0]), int(coordinates["price_slot_2"][1]), 120, 60)
        max_button = (int(coordinates["max_quantity_button"][0]), int(coordinates["max_quantity_button"][1]))
        buy_button = (int(coordinates["buy_button"][0]), int(coordinates["buy_button"][1]))
        delay = config.delay_ms / 1000.0
        while True:
            time.sleep(delay)
            image1 = self.screen_capture.grab(price_region1)[..., :3]
            price1 = self.ocr.recognize_number(image1)
            if price1 is None or price1 > config.threshold:
                continue
            self.automation.execute(Action(type="click", params={"position": max_button}))
            time.sleep(0.1)
            image2 = self.screen_capture.grab(price_region2)[..., :3]
            price2 = self.ocr.recognize_number(image2)
            if price2 is None or price2 > config.threshold:
                continue
            self.automation.execute(Action(type="click", params={"position": buy_button}))

    def _start_mode2(self) -> None:
        try:
            price_threshold = float(self.mode2_price.text())
            color_tuple = tuple(int(c.strip()) for c in self.mode2_color.text().split(","))
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入正确的参数")
            return
        tolerance = int(self.mode2_tolerance.value())
        self.config.update("mode_2.scan_price", price_threshold)
        self.config.update("mode_2.stop_color", list(color_tuple))
        self.config.update("mode_2.tolerance", tolerance)
        if not self._has_required_coords(["trade_button"]):
            QMessageBox.warning(self, "错误", "请先配置基础坐标")
            return
        worker = threading.Thread(
            target=self._run_mode2,
            args=(Mode2Config(price_threshold, color_tuple, tolerance),),
            daemon=True,
        )
        worker.start()

    def _run_mode2(self, config: Mode2Config) -> None:
        coordinates = self.config.data["coordinates"]
        mode2 = self.config.data["mode_2"]
        price_button_source = mode2.get("price_button") or coordinates.get("trade_button")
        if price_button_source is None:
            QMessageBox.critical(self, "错误", "缺少价格按钮坐标")
            return
        price_button = (int(price_button_source[0]), int(price_button_source[1]))
        price_region = ScreenRegion(price_button[0], price_button[1], 160, 60)
        stop_pos_raw = mode2.get("stop_color_position")
        stop_pos = (int(stop_pos_raw[0]), int(stop_pos_raw[1])) if stop_pos_raw else None
        recording1 = [Action(type=item["type"], params=item["params"]) for item in mode2.get("recording_1", [])]
        recording2 = [Action(type=item["type"], params=item["params"]) for item in mode2.get("recording_2", [])]
        while True:
            image = self.screen_capture.grab(price_region)[..., :3]
            price = self.ocr.recognize_number(image)
            if price is None:
                time.sleep(0.1)
                continue
            if price >= config.threshold:
                self.automation.execute_many(recording1)
            else:
                self.automation.execute_many(recording2)
                if stop_pos:
                    screenshot = pyautogui.screenshot(region=(stop_pos[0], stop_pos[1], 1, 1))
                    color = screenshot.getpixel((0, 0))
                    if all(abs(color[i] - config.stop_color[i]) <= config.tolerance for i in range(3)):
                        break


def run_app(config_path: Path) -> None:
    app = QApplication(sys.argv)
    manager = ConfigManager(config_path)
    ocr = OCREngine()
    window = MainWindow(manager, ocr)
    window.resize(640, 720)
    window.show()
    sys.exit(app.exec())


__all__ = ["run_app"]
