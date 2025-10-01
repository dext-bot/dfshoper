from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from dfshoper.config import ModeOneItem
from dfshoper.ui.coordinate_picker import CoordinatePicker


@dataclass
class ModeOneItemState:
    item: ModeOneItem
    widget_item: QListWidgetItem


class ModeOneWidget(QWidget):
    addItemRequested = Signal(ModeOneItem)
    startMonitorRequested = Signal()
    stopMonitorRequested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._picker = CoordinatePicker()
        self._states: List[ModeOneItemState] = []
        self._coordinate: Optional[tuple[int, int]] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        form = QFormLayout()
        self._name_input = QLineEdit(self)
        self._threshold_input = QLineEdit(self)
        self._threshold_input.setPlaceholderText("最低扫货价格")
        self._poll_input = QSpinBox(self)
        self._poll_input.setRange(100, 10000)
        self._poll_input.setValue(500)

        coord_layout = QHBoxLayout()
        self._coord_label = QLabel("未选择")
        capture_btn = QPushButton("拖动取点")
        capture_btn.pressed.connect(self._on_capture)
        coord_layout.addWidget(self._coord_label)
        coord_layout.addWidget(capture_btn)

        form.addRow("商品名称", self._name_input)
        form.addRow("最低价格", self._threshold_input)
        form.addRow("轮询间隔(ms)", self._poll_input)
        form.addRow("坐标", coord_layout)

        layout.addLayout(form)

        add_btn = QPushButton("添加商品")
        add_btn.clicked.connect(self._on_add_item)
        layout.addWidget(add_btn)

        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self._list)

        action_layout = QHBoxLayout()
        start_btn = QPushButton("开始监控")
        start_btn.clicked.connect(self.startMonitorRequested.emit)
        stop_btn = QPushButton("停止监控")
        stop_btn.clicked.connect(self.stopMonitorRequested.emit)
        action_layout.addWidget(start_btn)
        action_layout.addWidget(stop_btn)
        layout.addLayout(action_layout)

    def _on_capture(self) -> None:
        self._picker.coordinateSelected.connect(self._on_coordinate_selected)
        self._picker.start_capture()

    def _on_coordinate_selected(self, x: int, y: int) -> None:
        self._picker.coordinateSelected.disconnect(self._on_coordinate_selected)
        self._coordinate = (x, y)
        self._coord_label.setText(f"({x}, {y})")

    def _on_add_item(self) -> None:
        name = self._name_input.text() or "商品"
        threshold_text = self._threshold_input.text().strip()
        threshold = float(threshold_text) if threshold_text else 0.0
        poll = self._poll_input.value()
        coordinate = getattr(self, "_coordinate", None)
        if not coordinate:
            self._coord_label.setText("请先拖动取点")
            return
        item = ModeOneItem(name=name, coordinate=coordinate, threshold=threshold, poll_interval_ms=poll)
        list_item = QListWidgetItem(f"{name} @ {coordinate} <= {threshold}")
        self._list.addItem(list_item)
        self._states.append(ModeOneItemState(item=item, widget_item=list_item))
        self.addItemRequested.emit(item)

    def load_items(self, items: List[ModeOneItem]) -> None:
        self._list.clear()
        self._states.clear()
        for item in items:
            list_item = QListWidgetItem(f"{item.name} @ {item.coordinate} <= {item.threshold}")
            self._list.addItem(list_item)
            self._states.append(ModeOneItemState(item=item, widget_item=list_item))


__all__ = ["ModeOneWidget"]
