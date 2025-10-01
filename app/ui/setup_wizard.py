from __future__ import annotations

from typing import Callable, Iterable, List, Tuple

import mss
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from ..coordinates import Point


def _capture_screen() -> QPixmap:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
    rgb = img.rgb
    image = QImage(rgb, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image.copy())


class SetupWizard(QDialog):
    def __init__(self, steps: Iterable[Tuple[str, Callable[[Point], None]]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("初始坐标采集")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.steps: List[Tuple[str, Callable[[Point], None]]] = list(steps)
        self._current = 0

        layout = QVBoxLayout(self)
        self.instruction_label = QLabel("请点击截图中的位置：")
        layout.addWidget(self.instruction_label)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        pixmap = _capture_screen()
        self.image_label.setPixmap(pixmap)
        self.resize(pixmap.width(), pixmap.height())
        self.move(0, 0)
        self._update_instruction()

    def _update_instruction(self) -> None:
        if self._current >= len(self.steps):
            self.accept()
            return
        text, _ = self.steps[self._current]
        self.instruction_label.setText(f"第 {self._current + 1} 步：{text}")

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._current >= len(self.steps):
            return
        step = self.steps[self._current]
        pos = event.globalPosition()
        point = Point(int(pos.x()), int(pos.y()))
        step[1](point)
        self._current += 1
        self._update_instruction()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        return super().keyPressEvent(event)
