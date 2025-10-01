from __future__ import annotations

import threading
import time
from typing import Optional, Tuple

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from pynput import mouse, keyboard

Coordinate = Tuple[int, int]


class CoordinatePicker(QWidget):
    coordinateSelected = Signal(int, int)

    def __init__(self) -> None:
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowFullScreen)
        self._pos: Optional[QPoint] = None
        self._listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._capturing = False
        self._hint = QLabel(
            "按住并拖拽到目标位置后松开鼠标，或移动鼠标后按 F8 捕获坐标",
            self,
        )
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

        completed = threading.Event()

        def finish(position: Optional[Tuple[int, int]]) -> None:
            if completed.is_set():
                return
            completed.set()
            if position is not None:
                self.coordinateSelected.emit(int(position[0]), int(position[1]))
            QGuiApplication.postEvent(self, QEvent(QEvent.User))

        def on_release(x: int, y: int, button: mouse.Button, pressed: bool) -> bool:
            if not pressed and button == mouse.Button.left:
                finish((int(x), int(y)))
                return False
            return not completed.is_set()

        def on_key_press(key: keyboard.Key | keyboard.KeyCode) -> bool:
            if key == keyboard.Key.f8:
                position = mouse.Controller().position
                finish((int(position[0]), int(position[1])))
                return False
            if key == keyboard.Key.esc:
                finish(None)
                return False
            return not completed.is_set()

        with mouse.Listener(on_click=on_release) as mouse_listener:
            self._listener = mouse_listener
            with keyboard.Listener(on_press=on_key_press) as keyboard_listener:
                self._keyboard_listener = keyboard_listener
                completed.wait()

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.User:
            self._capturing = False
            self.hide()
            self._listener = None
            self._keyboard_listener = None
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
