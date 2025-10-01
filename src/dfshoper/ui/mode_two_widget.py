from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from dfshoper.config import ModeTwoConfig, TerminateColor
from dfshoper.ui.coordinate_picker import CoordinatePicker


class ModeTwoWidget(QWidget):
    configChanged = Signal(ModeTwoConfig)
    recordHighRequested = Signal()
    recordLowRequested = Signal()
    startRequested = Signal()
    stopRequested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._picker = CoordinatePicker()
        self._price_coordinate: Optional[tuple[int, int]] = None
        self._terminate_coordinate: Optional[tuple[int, int]] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        form = QFormLayout()

        self._threshold_input = QLineEdit(self)
        self._poll_input = QSpinBox(self)
        self._poll_input.setRange(100, 10000)
        self._poll_input.setValue(800)
        self._threshold_input.editingFinished.connect(self._emit_config)
        self._poll_input.valueChanged.connect(lambda _: self._emit_config())

        self._price_label = QLabel("未选择")
        price_btn = QPushButton("价格取点")
        price_btn.pressed.connect(lambda: self._start_capture("price"))

        price_layout = QHBoxLayout()
        price_layout.addWidget(self._price_label)
        price_layout.addWidget(price_btn)

        self._terminate_label = QLabel("未选择")
        terminate_btn = QPushButton("终止颜色取点")
        terminate_btn.pressed.connect(lambda: self._start_capture("terminate"))

        terminate_layout = QHBoxLayout()
        terminate_layout.addWidget(self._terminate_label)
        terminate_layout.addWidget(terminate_btn)

        self._color_input = QLineEdit(self)
        self._color_input.setPlaceholderText("例如: 255,255,255")
        self._color_input.editingFinished.connect(self._emit_config)

        form.addRow("阈值价格", self._threshold_input)
        form.addRow("轮询间隔(ms)", self._poll_input)
        form.addRow("价格坐标", price_layout)
        form.addRow("终止颜色坐标", terminate_layout)
        form.addRow("终止颜色RGB", self._color_input)

        layout.addLayout(form)

        op_layout = QHBoxLayout()
        record_high = QPushButton("录制操作1")
        record_low = QPushButton("录制操作2")
        record_high.clicked.connect(self.recordHighRequested.emit)
        record_low.clicked.connect(self.recordLowRequested.emit)
        op_layout.addWidget(record_high)
        op_layout.addWidget(record_low)
        layout.addLayout(op_layout)

        control_layout = QHBoxLayout()
        start_btn = QPushButton("开始执行")
        stop_btn = QPushButton("停止执行")
        start_btn.clicked.connect(self.startRequested.emit)
        stop_btn.clicked.connect(self.stopRequested.emit)
        control_layout.addWidget(start_btn)
        control_layout.addWidget(stop_btn)
        layout.addLayout(control_layout)

    def _start_capture(self, target: str) -> None:
        self._capture_target = target
        self._picker.coordinateSelected.connect(self._on_coordinate_selected)
        self._picker.start_capture()

    def _on_coordinate_selected(self, x: int, y: int) -> None:
        self._picker.coordinateSelected.disconnect(self._on_coordinate_selected)
        coordinate = (x, y)
        if self._capture_target == "price":
            self._price_label.setText(f"({x}, {y})")
            self._price_coordinate = coordinate
        else:
            self._terminate_label.setText(f"({x}, {y})")
            self._terminate_coordinate = coordinate
        self._emit_config()

    def _emit_config(self) -> None:
        threshold_text = self._threshold_input.text().strip()
        threshold = float(threshold_text) if threshold_text else 0.0
        rgb = self._parse_color(self._color_input.text())
        config = ModeTwoConfig(
            poll_interval_ms=self._poll_input.value(),
            price_anchor=getattr(self, "_price_coordinate", None),
            threshold=threshold,
            operation_high=str(self._operation_high) if getattr(self, "_operation_high", None) else None,
            operation_low=str(self._operation_low) if getattr(self, "_operation_low", None) else None,
            terminate_color=TerminateColor(
                coordinate=getattr(self, "_terminate_coordinate", None),
                rgb=rgb,
            ),
        )
        self.configChanged.emit(config)

    def _parse_color(self, text: str) -> tuple[int, int, int]:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if len(parts) == 3:
            try:
                return tuple(int(p) for p in parts)  # type: ignore[return-value]
            except ValueError:
                pass
        return 255, 255, 255

    def load_config(self, config: ModeTwoConfig) -> None:
        self._threshold_input.setText(str(config.threshold))
        self._poll_input.setValue(config.poll_interval_ms)
        if config.price_anchor:
            self._price_label.setText(str(config.price_anchor))
            self._price_coordinate = config.price_anchor
        if config.terminate_color.coordinate:
            self._terminate_label.setText(str(config.terminate_color.coordinate))
            self._terminate_coordinate = config.terminate_color.coordinate
        if config.terminate_color.rgb:
            self._color_input.setText(
                ",".join(str(v) for v in config.terminate_color.rgb)
            )
        self._operation_high = Path(config.operation_high) if config.operation_high else None
        self._operation_low = Path(config.operation_low) if config.operation_low else None

    def set_operation_paths(self, high: Optional[Path], low: Optional[Path]) -> None:
        self._operation_high = Path(high) if high else None
        self._operation_low = Path(low) if low else None
        self._emit_config()


__all__ = ["ModeTwoWidget"]
