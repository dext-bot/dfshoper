from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QWidget,
)

from dfshoper.config import ConfigManager, ModeOneItem, ModeTwoConfig
from dfshoper.ui.mode_one_widget import ModeOneWidget
from dfshoper.ui.mode_two_widget import ModeTwoWidget


class MainWindow(QMainWindow):
    operationRecordRequested = Signal(str, str)

    def __init__(self, manager: ConfigManager) -> None:
        super().__init__()
        self._manager = manager
        self._mode_two_operations: dict[str, Optional[Path]] = {"high": None, "low": None}
        self.setWindowTitle("DFShoper 自动化助手")
        self.resize(800, 600)
        self._setup_ui()
        self._load_config()

    def _setup_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QGridLayout(central)

        self._mode_stack = QStackedWidget(self)

        # Mode 1
        self._mode_one_widget = ModeOneWidget(self)
        self._mode_one_widget.addItemRequested.connect(self._on_add_mode_one_item)
        self._mode_one_widget.startMonitorRequested.connect(self._start_mode_one)
        self._mode_one_widget.stopMonitorRequested.connect(self._stop_mode_one)
        self._mode_stack.addWidget(self._mode_one_widget)

        # Mode 2
        self._mode_two_widget = ModeTwoWidget(self)
        self._mode_two_widget.configChanged.connect(self._on_mode_two_config)
        self._mode_two_widget.recordHighRequested.connect(lambda: self._record_operation("high"))
        self._mode_two_widget.recordLowRequested.connect(lambda: self._record_operation("low"))
        self._mode_two_widget.startRequested.connect(self._start_mode_two)
        self._mode_two_widget.stopRequested.connect(self._stop_mode_two)
        self._mode_stack.addWidget(self._mode_two_widget)

        layout.addWidget(self._mode_stack, 0, 0, 1, 3)

        mode_one_btn = QPushButton("模式一")
        mode_two_btn = QPushButton("模式二")
        mode_one_btn.clicked.connect(lambda: self._mode_stack.setCurrentIndex(0))
        mode_two_btn.clicked.connect(lambda: self._mode_stack.setCurrentIndex(1))
        layout.addWidget(mode_one_btn, 1, 0)
        layout.addWidget(mode_two_btn, 1, 1)

        self._status_label = QLabel("准备就绪")
        layout.addWidget(self._status_label, 2, 0, 1, 3)

        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn, 1, 2)

    def _load_config(self) -> None:
        config = self._manager.config
        self._mode_one_widget.load_items(config.mode_one.items)
        self._mode_two_widget.load_config(config.mode_two)

    # ----- Mode one -----
    def _on_add_mode_one_item(self, item: ModeOneItem) -> None:
        self._manager.add_mode_one_item(item)
        self._status_label.setText(f"添加模式一项目: {item.name}")

    def _start_mode_one(self) -> None:
        self._status_label.setText("模式一监控启动")
        # 业务逻辑由控制器负责

    def _stop_mode_one(self) -> None:
        self._status_label.setText("模式一监控停止")

    # ----- Mode two -----
    def _on_mode_two_config(self, config: ModeTwoConfig) -> None:
        self._manager.update_mode_two(
            poll_interval_ms=config.poll_interval_ms,
            price_anchor=config.price_anchor,
            threshold=config.threshold,
            terminate_color=config.terminate_color,
        )
        self._status_label.setText("模式二配置已更新")

    def _record_operation(self, key: str) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "保存录制", str(Path("records") / f"operation_{key}.json"), "JSON Files (*.json)")
        if not path:
            return
        self._mode_two_operations[key] = Path(path)
        self._status_label.setText(f"准备录制操作 {key}")
        self.operationRecordRequested.emit(key, path)

    def _start_mode_two(self) -> None:
        self._status_label.setText("模式二执行中")

    def _stop_mode_two(self) -> None:
        self._status_label.setText("模式二已停止")

    def _save_config(self) -> None:
        self._manager.save()
        QMessageBox.information(self, "配置", "配置保存成功")

    def load_operations(self, high: Optional[Path], low: Optional[Path]) -> None:
        self._mode_two_operations["high"] = high
        self._mode_two_operations["low"] = low
        self._mode_two_widget.set_operation_paths(high, low)

    def show_missing_anchor_warning(self, missing: list[str]) -> None:
        QMessageBox.warning(
            self,
            "缺少坐标",
            "\n".join(["以下关键坐标未配置，请尽快取点：", *missing]),
        )


__all__ = ["MainWindow"]
