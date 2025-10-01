from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QLabel, QWidget

Coordinate = Tuple[int, int]


class CoordinatePicker(QWidget):
    coordinateSelected = Signal(int, int)

    def __init__(self) -> None:
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowFullScreen)
        self._pos: Optional[QPoint] = None
        self._capturing = False
        self._ready = False
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._activate_capture)
        hint = QLabel(
            "按住并拖拽到目标位置后松开鼠标，或移动鼠标后按 F8 捕获坐标",
            self,
        )
        hint.setStyleSheet(
            "color: white; font-size: 24px; background-color: rgba(0,0,0,150); padding: 8px;"
        )
        hint.adjustSize()
        hint.move(50, 50)
        self.setMouseTracking(True)

    def start_capture(self, delay: float = 0.5) -> None:
        if self._capturing:
            return
        self._capturing = True
        self._ready = False
        self._pos = None
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)
        QApplication.processEvents()
        if delay <= 0:
            self._activate_capture()
        else:
            self._delay_timer.start(int(delay * 1000))

    def _activate_capture(self) -> None:
        if not self._capturing:
            return
        self._ready = True
        self.grabMouse()
        self.grabKeyboard()

    def _finish(self, point: Optional[QPoint]) -> None:
        if not self._capturing:
            return
        self._capturing = False
        self._ready = False
        self._delay_timer.stop()
        self.releaseMouse()
        self.releaseKeyboard()
        self.hide()
        if point is not None:
            self.coordinateSelected.emit(point.x(), point.y())

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

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        if not self._ready:
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            global_pos = event.globalPosition().toPoint()
            self._finish(global_pos)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):  # type: ignore[override]
        if not self._ready:
            event.ignore()
            return
        if event.key() == Qt.Key_F8:
            self._finish(QCursor.pos())
            event.accept()
            return
        if event.key() == Qt.Key_Escape:
            self._finish(None)
            event.accept()
            return
        super().keyPressEvent(event)


__all__ = ["CoordinatePicker"]
