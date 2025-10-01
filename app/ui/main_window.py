from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..automation import AutomationController
from ..config import AppConfig, Mode1Item, save_config
from ..coordinates import Point, Region
from ..recorder import ActionRecorder
from .setup_wizard import SetupWizard
from .widgets import CoordinateInput, Mode1ItemEditor, RegionInput


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, is_new_config: bool = False):
        super().__init__()
        self.setWindowTitle("游戏商城低价商品助手")
        self.resize(960, 720)
        self.config = config
        self._is_new_config = is_new_config
        self.automation = AutomationController(config)
        self.automation.message.connect(self._append_log)
        self.automation.price_checked.connect(self._on_price_checked)
        self.recorder = ActionRecorder()

        self._init_ui()
        QTimer.singleShot(2000, self._prompt_initial_setup)

    # ---------- UI setup ----------
    def _init_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_global_tab(), "全局设置")
        tabs.addTab(self._build_mode1_tab(), "模式1")
        tabs.addTab(self._build_mode2_tab(), "模式2")
        tabs.addTab(self._build_log_tab(), "日志")
        self.setCentralWidget(tabs)

        toolbar = QToolBar("控制")
        start_mode1_action = toolbar.addAction("启动模式1")
        start_mode1_action.triggered.connect(self.automation.start_mode1)
        stop_mode1_action = toolbar.addAction("停止模式1")
        stop_mode1_action.triggered.connect(self.automation.stop_mode1)
        toolbar.addSeparator()
        start_mode2_action = toolbar.addAction("启动模式2")
        start_mode2_action.triggered.connect(self.automation.start_mode2)
        stop_mode2_action = toolbar.addAction("停止模式2")
        stop_mode2_action.triggered.connect(self.automation.stop_mode2)
        toolbar.addSeparator()
        save_action = toolbar.addAction("保存配置")
        save_action.triggered.connect(self._save_config)
        self.addToolBar(toolbar)

    def _build_global_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.trade_input = CoordinateInput("交易行按钮:")
        self.trade_input.set_point(self.config.coordinates.trade_button)
        self.trade_input.on_change(lambda p: self._update_point("trade_button", p))
        layout.addWidget(self.trade_input)

        self.main_input = CoordinateInput("主界面按钮:")
        self.main_input.set_point(self.config.coordinates.main_interface)
        self.main_input.on_change(lambda p: self._update_point("main_interface", p))
        layout.addWidget(self.main_input)

        self.equip_input = CoordinateInput("配置装备按钮:")
        self.equip_input.set_point(self.config.coordinates.equipment_tab)
        self.equip_input.on_change(lambda p: self._update_point("equipment_tab", p))
        layout.addWidget(self.equip_input)

        self.purchase_input = CoordinateInput("购买按钮:")
        self.purchase_input.set_point(self.config.coordinates.purchase_button)
        self.purchase_input.on_change(lambda p: self._update_point("purchase_button", p))
        layout.addWidget(self.purchase_input)

        self.max_input = CoordinateInput("最高数量按钮:")
        self.max_input.set_point(self.config.coordinates.max_quantity_button)
        self.max_input.on_change(lambda p: self._update_point("max_quantity_button", p))
        layout.addWidget(self.max_input)

        self.price1_input = RegionInput("价格1区域:")
        self.price1_input.set_region(self.config.coordinates.price_primary_region)
        self.price1_input.on_change(lambda r: self._update_region("price_primary_region", r))
        layout.addWidget(self.price1_input)

        self.price2_input = RegionInput("价格2区域:")
        self.price2_input.set_region(self.config.coordinates.price_secondary_region)
        self.price2_input.on_change(lambda r: self._update_region("price_secondary_region", r))
        layout.addWidget(self.price2_input)

        layout.addStretch(1)
        return widget

    def _build_mode1_tab(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        self.item_list = QListWidget()
        layout.addWidget(self.item_list, 1)
        self.item_editor = Mode1ItemEditor()
        layout.addWidget(self.item_editor, 2)

        side_layout = QVBoxLayout()
        add_button = QPushButton("新增商品")
        add_button.clicked.connect(self._add_mode1_item)
        delete_button = QPushButton("删除选中")
        delete_button.clicked.connect(self._delete_mode1_item)
        save_button = QPushButton("保存修改")
        save_button.clicked.connect(self._save_mode1_item)
        side_layout.addWidget(add_button)
        side_layout.addWidget(delete_button)
        side_layout.addWidget(save_button)
        side_layout.addStretch(1)
        layout.addLayout(side_layout)

        for item in self.config.mode1_items.values():
            self._add_item_to_list(item)
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        return widget

    def _build_mode2_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.mode2_price_region = RegionInput("价格识别区域:")
        self.mode2_price_region.set_region(self.config.mode2.price_region)
        self.mode2_price_region.on_change(lambda r: self._set_mode2_region(r))
        layout.addWidget(self.mode2_price_region)

        self.mode2_price_spin = QDoubleSpinBox()
        self.mode2_price_spin.setRange(0, 1_000_000)
        self.mode2_price_spin.setDecimals(2)
        self.mode2_price_spin.setValue(self.config.mode2.min_price)
        self.mode2_price_spin.valueChanged.connect(self._set_mode2_price)
        layout.addWidget(self._wrap_with_label("最低价格:", self.mode2_price_spin))

        self.action1_button = QPushButton("录制操作1")
        self.action1_button.clicked.connect(lambda: self._record_action(1))
        layout.addWidget(self.action1_button)

        self.action2_button = QPushButton("录制操作2")
        self.action2_button.clicked.connect(lambda: self._record_action(2))
        layout.addWidget(self.action2_button)

        self.mode2_post_point = CoordinateInput("终止检测坐标:")
        self.mode2_post_point.set_point(self.config.mode2.post_check_point)
        self.mode2_post_point.on_change(lambda p: self._set_mode2_point(p))
        layout.addWidget(self.mode2_post_point)

        color_layout = QHBoxLayout()
        self.color_r = QSpinBox()
        self.color_r.setRange(0, 255)
        self.color_r.setValue(self.config.mode2.post_check_color[0])
        self.color_g = QSpinBox()
        self.color_g.setRange(0, 255)
        self.color_g.setValue(self.config.mode2.post_check_color[1])
        self.color_b = QSpinBox()
        self.color_b.setRange(0, 255)
        self.color_b.setValue(self.config.mode2.post_check_color[2])
        for spin in (self.color_r, self.color_g, self.color_b):
            spin.valueChanged.connect(self._set_mode2_color)
        color_label = QLabel("终止颜色:")
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_r)
        color_layout.addWidget(self.color_g)
        color_layout.addWidget(self.color_b)
        layout.addLayout(color_layout)
        layout.addStretch(1)
        return widget

    def _build_log_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)
        return widget

    # ---------- Handlers ----------
    def _update_point(self, key: str, point: Point) -> None:
        setattr(self.config.coordinates, key, point)

    def _update_region(self, key: str, region: Region) -> None:
        setattr(self.config.coordinates, key, region)

    def _add_item_to_list(self, item: Mode1Item) -> None:
        list_item = QListWidgetItem(item.name)
        list_item.setData(Qt.ItemDataRole.UserRole, item)
        self.item_list.addItem(list_item)

    def _add_mode1_item(self) -> None:
        new_item = Mode1Item("新商品", Point(0, 0), 0.0, 350)
        self.config.mode1_items[new_item.name] = new_item
        self._add_item_to_list(new_item)

    def _delete_mode1_item(self) -> None:
        item = self.item_list.currentItem()
        if not item:
            return
        name = item.text()
        self.item_list.takeItem(self.item_list.row(item))
        self.config.mode1_items.pop(name, None)

    def _on_item_selected(self, current: Optional[QListWidgetItem]) -> None:
        if not current:
            self.item_editor.set_item(Mode1Item("", Point(0, 0), 0.0, 350))
            return
        item = current.data(Qt.ItemDataRole.UserRole)
        if item:
            self.item_editor.set_item(item)

    def _save_mode1_item(self) -> None:
        list_item = self.item_list.currentItem()
        if not list_item:
            QMessageBox.information(self, "提示", "请先选择一个商品")
            return
        item = self.item_editor.to_item()
        if not item:
            QMessageBox.warning(self, "错误", "请完善商品信息")
            return
        self.config.mode1_items.pop(list_item.text(), None)
        self.config.mode1_items[item.name] = item
        list_item.setText(item.name)
        list_item.setData(Qt.ItemDataRole.UserRole, item)

    def _set_mode2_region(self, region: Optional[Region]) -> None:
        if region:
            self.config.mode2.price_region = region

    def _set_mode2_price(self, value: float) -> None:
        self.config.mode2.min_price = value

    def _set_mode2_point(self, point: Point) -> None:
        self.config.mode2.post_check_point = point

    def _set_mode2_color(self) -> None:
        self.config.mode2.post_check_color = (
            self.color_r.value(),
            self.color_g.value(),
            self.color_b.value(),
        )

    def _record_action(self, index: int) -> None:
        QMessageBox.information(
            self,
            "录制提示",
            "即将开始录制，按 ESC 结束。",
        )
        events = self.recorder.record()
        if index == 1:
            self.config.mode2.action1 = events
            QMessageBox.information(self, "录制完成", "操作1已保存")
        else:
            self.config.mode2.action2 = events
            QMessageBox.information(self, "录制完成", "操作2已保存")

    def _wrap_with_label(self, label: str, widget: QWidget) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(label))
        layout.addWidget(widget)
        return container

    def _set_mode2_region_from_capture(self, region: Region) -> None:
        self.config.mode2.price_region = region

    def _set_mode2_price_region(self) -> None:
        region = self.mode2_price_region.get_region()
        if region:
            self.config.mode2.price_region = region

    def _save_config(self) -> None:
        save_config(self.config)
        QMessageBox.information(self, "保存成功", "配置已保存")

    def closeEvent(self, event) -> None:
        save_config(self.config)
        return super().closeEvent(event)

    def _append_log(self, text: str) -> None:
        self.log_edit.append(text)

    def _on_price_checked(self, name: str, price1: float, price2: float) -> None:
        self._append_log(f"{name}: price1={price1:.2f} price2={price2:.2f}")

    def _prompt_initial_setup(self) -> None:
        if not self._is_new_config:
            return
        coords = self.config.coordinates
        steps: list[tuple[str, Callable[[Point], None]]] = []

        def add_step(label: str, attr: str, widget: CoordinateInput | RegionInput) -> None:
            value = getattr(coords, attr)
            if isinstance(widget, RegionInput):
                point = value.origin
            else:
                point = value
            if point.x or point.y:
                return

            def setter(p: Point, attr=attr, widget=widget):
                if isinstance(widget, RegionInput):
                    region = getattr(coords, attr)
                    region.origin = p
                    self._update_region(attr, region)
                    widget.set_region(region)
                else:
                    self._update_point(attr, p)
                    widget.set_point(p)

            steps.append((label, setter))

        add_step("点击交易行按钮", "trade_button", self.trade_input)
        add_step("点击主界面按钮", "main_interface", self.main_input)
        add_step("点击配置装备按钮", "equipment_tab", self.equip_input)
        add_step("点击购买按钮", "purchase_button", self.purchase_input)
        add_step("点击最高数量按钮", "max_quantity_button", self.max_input)
        add_step("点击价格1区域左上角", "price_primary_region", self.price1_input)
        add_step("点击价格2区域左上角", "price_secondary_region", self.price2_input)

        if not steps:
            return

        wizard = SetupWizard(steps, self)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return
        self._is_new_config = False
