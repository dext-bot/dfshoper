"""Screen capture and coordinate selection utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import mss
import numpy as np

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover - UI dependencies are optional at runtime
    QtCore = QtGui = QtWidgets = None


@dataclass
class CaptureResult:
    point: Optional[Tuple[int, int]] = None
    region: Optional[Tuple[int, int, int, int]] = None


class ScreenCapture:
    """Helper to grab screenshots and expose them to Qt."""

    def __init__(self) -> None:
        self._sct = mss.mss()

    def grab_region(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        monitor = self._sct.monitors[0]
        if region is not None:
            monitor = {
                "left": region[0],
                "top": region[1],
                "width": region[2],
                "height": region[3],
            }
        img = np.array(self._sct.grab(monitor))
        return img


class CaptureDialog(QtWidgets.QDialog):  # type: ignore[misc]
    """Dialog that lets the user pick a point or region from a screenshot."""

    selection_made = QtCore.Signal(object)  # type: ignore[attr-defined]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:  # type: ignore[misc]
        super().__init__(parent)
        self.setWindowTitle("选择坐标或区域")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self._capture = ScreenCapture()
        self._pixmap_item: Optional[QtWidgets.QGraphicsPixmapItem] = None  # type: ignore[name-defined]
        self._scene = QtWidgets.QGraphicsScene(self)
        self._view = QtWidgets.QGraphicsView(self._scene)
        self._view.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._view)

        self._rubber_band = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self._view)
        self._origin: Optional[QtCore.QPoint] = None
        self._capture_image()

        self._view.viewport().installEventFilter(self)

    def _capture_image(self) -> None:
        img = self._capture.grab_region()
        img = img[:, :, :3]
        height, width, _ = img.shape
        image = QtGui.QImage(img.data, width, height, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(image)
        if self._pixmap_item is None:
            self._pixmap_item = self._scene.addPixmap(pixmap)
        else:
            self._pixmap_item.setPixmap(pixmap)
        self.resize(width, height)

    def eventFilter(self, obj, event):  # type: ignore[override]
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            self._origin = event.position().toPoint()  # type: ignore[attr-defined]
            self._rubber_band.setGeometry(QtCore.QRect(self._origin, QtCore.QSize()))
            self._rubber_band.show()
            return True
        if event.type() == QtCore.QEvent.MouseMove and self._origin:
            rect = QtCore.QRect(self._origin, event.position().toPoint()).normalized()  # type: ignore[attr-defined]
            self._rubber_band.setGeometry(rect)
            return True
        if event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton and self._origin:
            rect = self._rubber_band.geometry()
            self._rubber_band.hide()
            if rect.width() < 5 and rect.height() < 5:
                self.selection_made.emit(CaptureResult(point=(rect.x(), rect.y())))
            else:
                self.selection_made.emit(
                    CaptureResult(
                        region=(rect.x(), rect.y(), rect.width(), rect.height())
                    )
                )
            self.accept()
            return True
        return super().eventFilter(obj, event)
