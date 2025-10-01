from __future__ import annotations

import threading
import time
from typing import Optional, Tuple

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from pynput import mouse

Coordinate = Tuple[int, int]


class CoordinatePicker(QWidget):
    coordinateSelected = Signal(int, int)

    def __init__(self) -> None:
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowFullScreen)
        self._pos: Optional[QPoint] = None
        self._listener: Optional[mouse.Listener] = None
        self._capturing = False
        self._hint = QLabel("按住并拖拽到目标位置后松开鼠标", self)
        self._hint.setStyleSheet("color: white; font-size: 24px; background-color: rgba(0,0,0,150); padding: 8px;")
        self._hint.adjustSize()
        self._hint.move(50, 50)

    def start_capture(self, delay: float = 0.5) -> None:
        if self._capturing:
            return
        self._capturing = True
        self.show()
        QApplication.processEvents()
        threading.Thread(target=self._capture_thread, args=(delay,), daemon=True).start()

    def _capture_thread(self, delay: float) -> None:
        time.sleep(delay)

        def on_release(x: int, y: int, button: mouse.Button, pressed: bool) -> bool:
            if not pressed and button == mouse.Button.left:
                self.coordinateSelected.emit(int(x), int(y))
                return False
            return True

        with mouse.Listener(on_click=on_release) as listener:
            self._listener = listener
            listener.join()
        QGuiApplication.postEvent(self, QEvent(QEvent.User))

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.User:
            self._capturing = False
            self.hide()
            return True
        return super().event(event)

    def paintEvent(self, event):  # type: ignore[override]
        if self._pos:
            painter = QPainter(self)
            pen = QPen(Qt.red, 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawEllipse(self._pos, 20, 20)
        super().paintEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        self._pos = event.position().toPoint()
        self.update()


__all__ = ["CoordinatePicker"]
