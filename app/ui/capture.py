from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Optional

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
from pynput import mouse

from ..coordinates import Point


@contextmanager
def _temporary_hidden(widget: QWidget):
    was_visible = widget.isVisible()
    widget.hide()
    QApplication.processEvents()
    try:
        yield
    finally:
        if was_visible:
            widget.show()
            widget.activateWindow()
            widget.raise_()
            QApplication.processEvents()


def capture_point(parent: QWidget, prompt: str = "请在屏幕上点击目标位置") -> Optional[Point]:
    QMessageBox.information(parent, "坐标采集", prompt)
    with _temporary_hidden(parent):
        time.sleep(0.3)
        result: list[Point] = []

        def on_click(x: int, y: int, button, pressed: bool) -> Optional[bool]:
            if not pressed:
                result.append(Point(int(x), int(y)))
                return False
            return None

        listener = mouse.Listener(on_click=on_click)
        listener.start()
        listener.join()

    if not result:
        QMessageBox.warning(parent, "捕获失败", "未获取到坐标，请重试。")
        return None
    return result[0]
