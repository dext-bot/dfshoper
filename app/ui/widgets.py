from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from ..config import Mode1Item
from ..coordinates import Point, Region
from .capture import capture_point


class CoordinateInput(QWidget):
    def __init__(self, label: str, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(label)
        self.edit = QLineEdit()
        self.edit.setReadOnly(True)
        self.capture_button = QPushButton("选取")
        layout.addWidget(self.label)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.capture_button)
        self.capture_button.clicked.connect(self._on_capture)
        self._point: Optional[Point] = None
        self._callbacks: list[Callable[[Point], None]] = []

    def _on_capture(self) -> None:
        point = capture_point(self.window())
        if point:
            self.set_point(point)
            for callback in self._callbacks:
                callback(point)

    def set_point(self, point: Point) -> None:
        self._point = point
        self.edit.setText(f"({point.x}, {point.y})")

    def get_point(self) -> Optional[Point]:
        return self._point

    def on_change(self, callback: Callable[[Point], None]) -> None:
        self._callbacks.append(callback)


class RegionInput(QWidget):
    def __init__(self, label: str, parent=None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)
        self.coordinate_input = CoordinateInput("左上角坐标:")
        layout.addRow(label, self.coordinate_input)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 1920 * 2)
        self.width_spin.setValue(120)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 1080 * 2)
        self.height_spin.setValue(40)
        layout.addRow("宽度:", self.width_spin)
        layout.addRow("高度:", self.height_spin)

    def set_region(self, region: Region) -> None:
        self.coordinate_input.set_point(region.origin)
        self.width_spin.setValue(region.width)
        self.height_spin.setValue(region.height)

    def get_region(self) -> Optional[Region]:
        point = self.coordinate_input.get_point()
        if not point:
            return None
        return Region(point, self.width_spin.value(), self.height_spin.value())

    def on_change(self, callback: Callable[[Region], None]) -> None:
        def _wrapper(point: Point) -> None:
            region = self.get_region()
            if region:
                callback(region)

        self.coordinate_input.on_change(_wrapper)
        self.width_spin.valueChanged.connect(lambda _: callback(self.get_region()))
        self.height_spin.valueChanged.connect(lambda _: callback(self.get_region()))


class Mode1ItemEditor(QGroupBox):
    def __init__(self, parent=None) -> None:
        super().__init__("商品配置", parent)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.point_input = CoordinateInput("商品位置:")
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 1_000_000)
        self.price_spin.setDecimals(2)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10_000)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.setValue(350)

        layout.addRow("商品名称:", self.name_edit)
        layout.addRow(self.point_input)
        layout.addRow("最低价格:", self.price_spin)
        layout.addRow("识别延迟:", self.delay_spin)

    def set_item(self, item: Mode1Item) -> None:
        self.name_edit.setText(item.name)
        self.point_input.set_point(item.target_point)
        self.price_spin.setValue(item.min_price)
        self.delay_spin.setValue(item.delay_ms)

    def to_item(self) -> Optional[Mode1Item]:
        point = self.point_input.get_point()
        name = self.name_edit.text().strip()
        if not point or not name:
            return None
        return Mode1Item(
            name=name,
            target_point=point,
            min_price=self.price_spin.value(),
            delay_ms=self.delay_spin.value(),
        )
