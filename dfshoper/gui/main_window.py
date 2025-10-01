"""Main PySide6 UI for dfshoper."""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..automation import MacroEvent, MacroRecorder, capture_color, click_point, execute_macro
from ..capture import CaptureDialog, CaptureResult, ScreenCapture
from ..config import Config, Point, Region
from ..ocr import read_number


class DragButton(QtWidgets.QPushButton):
    """Button that captures screen coordinate when dragged and released."""

    coordinate_selected = QtCore.Signal(Point)

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if event.buttons() & QtCore.Qt.LeftButton:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CrossCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        QtWidgets.QApplication.restoreOverrideCursor()
        if event.button() == QtCore.Qt.LeftButton:
            global_pos = event.globalPosition().toPoint()
            self.coordinate_selected.emit(Point(global_pos.x(), global_pos.y()))
        super().mouseReleaseEvent(event)


class MainWindow(QtWidgets.QMainWindow):
    """Main application window."""

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.setWindowTitle("DF Shopper 自动工具")
        self.config = config
        self.screen_capture = ScreenCapture()

        self._recorder_a: Optional[MacroRecorder] = None
        self._recorder_b: Optional[MacroRecorder] = None

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        layout.addWidget(self._build_coordinates_group())
        layout.addWidget(self._build_mode_one_group())
        layout.addWidget(self._build_mode_two_group())
        layout.addWidget(self._build_macro_group())

        save_btn = QtWidgets.QPushButton("保存配置", self)
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn)

        self._mode_one_timer = QtCore.QTimer(self)
        self._mode_one_timer.timeout.connect(self._tick_mode_one)

        self._mode_two_timer = QtCore.QTimer(self)
        self._mode_two_timer.timeout.connect(self._tick_mode_two)

        self._initial_prompt_timer = QtCore.QTimer(self)
        self._initial_prompt_timer.setSingleShot(True)
        self._initial_prompt_timer.timeout.connect(self._prompt_for_missing_coordinates)
        self._initial_prompt_timer.start(3000)

    # Coordinate group ------------------------------------------------
    def _build_coordinates_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("坐标配置", self)
        layout = QtWidgets.QFormLayout(group)

        self.trade_button_btn = DragButton("交易行按钮")
        self.trade_button_btn.coordinate_selected.connect(self._set_trade_button)
        layout.addRow("交易行按钮", self.trade_button_btn)

        self.main_tab_btn = DragButton("主界面选项")
        self.main_tab_btn.coordinate_selected.connect(lambda pt: self._set_point("main_tab", pt))
        layout.addRow("主界面选项", self.main_tab_btn)

        self.equipment_tab_btn = DragButton("配置装备选项")
        self.equipment_tab_btn.coordinate_selected.connect(lambda pt: self._set_point("equipment_tab", pt))
        layout.addRow("配置装备选项", self.equipment_tab_btn)

        self.purchase_button_btn = DragButton("购买按钮")
        self.purchase_button_btn.coordinate_selected.connect(lambda pt: self._set_point("purchase_button", pt))
        layout.addRow("购买按钮", self.purchase_button_btn)

        self.max_quantity_btn = DragButton("最高购买数量按钮")
        self.max_quantity_btn.coordinate_selected.connect(lambda pt: self._set_point("max_quantity_button", pt))
        layout.addRow("最高购买数量按钮", self.max_quantity_btn)

        region_btn1 = QtWidgets.QPushButton("设置商品价格1区域")
        region_btn1.clicked.connect(lambda: self._capture_region("price_primary"))
        layout.addRow("商品价格1", region_btn1)

        region_btn2 = QtWidgets.QPushButton("设置商品价格2区域")
        region_btn2.clicked.connect(lambda: self._capture_region("price_secondary"))
        layout.addRow("商品价格2", region_btn2)

        return group

    def _set_trade_button(self, point: Point) -> None:
        self._set_point("trade_button", point)

    def _set_point(self, attr: str, point: Point) -> None:
        setattr(self.config.coordinates, attr, point)

    def _capture_region(self, attr: str) -> None:
        dialog = CaptureDialog(self)
        dialog.selection_made.connect(lambda result: self._assign_region(attr, result))
        dialog.exec()

    def _assign_region(self, attr: str, result: CaptureResult) -> None:
        if not result.region:
            return
        region = Region(*result.region)
        setattr(self.config.coordinates.price_regions, attr, region)

    def _prompt_for_missing_coordinates(self) -> None:
        missing_items = []
        coords = self.config.coordinates
        if coords.trade_button is None:
            missing_items.append(("交易行按钮", "trade_button", "point"))
        if coords.main_tab is None:
            missing_items.append(("主界面选项", "main_tab", "point"))
        if coords.equipment_tab is None:
            missing_items.append(("配置装备选项", "equipment_tab", "point"))
        if coords.purchase_button is None:
            missing_items.append(("购买按钮", "purchase_button", "point"))
        if coords.max_quantity_button is None:
            missing_items.append(("最高购买数量按钮", "max_quantity_button", "point"))
        if coords.price_regions.price_primary is None:
            missing_items.append(("商品价格1区域", "price_primary", "region"))
        if coords.price_regions.price_secondary is None:
            missing_items.append(("商品价格2区域", "price_secondary", "region"))

        for label, attr, kind in missing_items:
            QtWidgets.QMessageBox.information(self, "配置缺失", f"请在截图中选择 {label}")
            dialog = CaptureDialog(self)
            if kind == "point":
                dialog.selection_made.connect(lambda result, a=attr: self._assign_point(a, result))
            else:
                dialog.selection_made.connect(lambda result, a=attr: self._assign_region(a, result))
            dialog.exec()

    def _assign_point(self, attr: str, result: CaptureResult) -> None:
        if not result.point:
            return
        point = Point(*result.point)
        setattr(self.config.coordinates, attr, point)

    # Mode one --------------------------------------------------------
    def _build_mode_one_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("模式1：自动扫货", self)
        layout = QtWidgets.QFormLayout(group)

        self.mode_one_price = QtWidgets.QDoubleSpinBox()
        self.mode_one_price.setMaximum(99999999)
        self.mode_one_price.setValue(self.config.mode_one.min_price)
        self.mode_one_price.valueChanged.connect(lambda v: setattr(self.config.mode_one, "min_price", v))
        layout.addRow("扫货最低价格", self.mode_one_price)

        self.mode_one_delay = QtWidgets.QSpinBox()
        self.mode_one_delay.setRange(50, 10000)
        self.mode_one_delay.setValue(self.config.mode_one.poll_delay_ms)
        self.mode_one_delay.valueChanged.connect(lambda v: setattr(self.config.mode_one, "poll_delay_ms", v))
        layout.addRow("识别间隔(毫秒)", self.mode_one_delay)

        self.mode_one_toggle = QtWidgets.QPushButton("启动模式1")
        self.mode_one_toggle.setCheckable(True)
        self.mode_one_toggle.toggled.connect(self._toggle_mode_one)
        layout.addRow(self.mode_one_toggle)

        return group

    def _toggle_mode_one(self, checked: bool) -> None:
        if checked:
            self.mode_one_toggle.setText("停止模式1")
            self._mode_one_timer.start(self.config.mode_one.poll_delay_ms)
        else:
            self.mode_one_toggle.setText("启动模式1")
            self._mode_one_timer.stop()

    def _tick_mode_one(self) -> None:
        regions = self.config.coordinates.price_regions
        if not regions.price_primary or not regions.price_secondary:
            return

        img1 = self.screen_capture.grab_region(regions.price_primary.as_tuple)
        price1 = read_number(img1)
        if price1 is None:
            return
        if price1 > self.config.mode_one.min_price:
            return

        if self.config.coordinates.max_quantity_button:
            click_point(self.config.coordinates.max_quantity_button)

        img2 = self.screen_capture.grab_region(regions.price_secondary.as_tuple)
        price2 = read_number(img2)
        if price2 is not None and price2 <= self.config.mode_one.min_price:
            if self.config.coordinates.purchase_button:
                click_point(self.config.coordinates.purchase_button)

    # Mode two --------------------------------------------------------
    def _build_mode_two_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("模式2：价格监控", self)
        layout = QtWidgets.QFormLayout(group)

        self.mode_two_price = QtWidgets.QDoubleSpinBox()
        self.mode_two_price.setMaximum(99999999)
        self.mode_two_price.setValue(self.config.mode_two.trigger_price)
        self.mode_two_price.valueChanged.connect(lambda v: setattr(self.config.mode_two, "trigger_price", v))
        layout.addRow("触发价格", self.mode_two_price)

        self.mode_two_region_btn = QtWidgets.QPushButton("设置价格识别区域")
        self.mode_two_region_btn.clicked.connect(lambda: self._capture_mode_two_region())
        layout.addRow("价格区域", self.mode_two_region_btn)

        self.mode_two_color_btn = QtWidgets.QPushButton("设置终止判断坐标")
        self.mode_two_color_btn.clicked.connect(self._capture_mode_two_color)
        layout.addRow("终止坐标颜色", self.mode_two_color_btn)

        self.mode_two_toggle = QtWidgets.QPushButton("启动模式2")
        self.mode_two_toggle.setCheckable(True)
        self.mode_two_toggle.toggled.connect(self._toggle_mode_two)
        layout.addRow(self.mode_two_toggle)

        return group

    def _capture_mode_two_region(self) -> None:
        dialog = CaptureDialog(self)
        dialog.selection_made.connect(lambda result: self._assign_mode_two_region(result))
        dialog.exec()

    def _assign_mode_two_region(self, result: CaptureResult) -> None:
        if not result.region:
            return
        self.config.mode_two.price_trigger_point = Region(*result.region)

    def _capture_mode_two_color(self) -> None:
        dialog = CaptureDialog(self)

        def on_selection(result: CaptureResult) -> None:
            if not result.point:
                return
            point = Point(*result.point)
            screenshot = self.screen_capture.grab_region()
            color = capture_color(point, screenshot)
            self.config.mode_two.macro_success_point = point
            self.config.mode_two.macro_success_color = color

        dialog.selection_made.connect(on_selection)
        dialog.exec()

    def _toggle_mode_two(self, checked: bool) -> None:
        if checked:
            self.mode_two_toggle.setText("停止模式2")
            self._mode_two_timer.start(self.config.mode_one.poll_delay_ms)
        else:
            self.mode_two_toggle.setText("启动模式2")
            self._mode_two_timer.stop()

    def _tick_mode_two(self) -> None:
        region = self.config.mode_two.price_trigger_point
        if not region:
            return
        img = self.screen_capture.grab_region(region.as_tuple if hasattr(region, "as_tuple") else (region.left, region.top, region.width, region.height))
        price = read_number(img)
        if price is None:
            return
        if price > self.config.mode_two.trigger_price:
            execute_macro(self.config.recorder.macro_a)
        else:
            execute_macro(self.config.recorder.macro_b)
            self._check_mode_two_completion()

    def _check_mode_two_completion(self) -> None:
        point = self.config.mode_two.macro_success_point
        if not point:
            return
        screenshot = self.screen_capture.grab_region()
        color = capture_color(point, screenshot)
        if tuple(color) == tuple(self.config.mode_two.macro_success_color):
            self._mode_two_timer.stop()
            self.mode_two_toggle.setChecked(False)

    # Macro group -----------------------------------------------------
    def _build_macro_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("宏录制", self)
        layout = QtWidgets.QHBoxLayout(group)

        self.macro_a_btn = QtWidgets.QPushButton("录制操作1")
        self.macro_a_btn.setCheckable(True)
        self.macro_a_btn.toggled.connect(lambda state: self._toggle_recording("a", state))
        layout.addWidget(self.macro_a_btn)

        self.macro_b_btn = QtWidgets.QPushButton("录制操作2")
        self.macro_b_btn.setCheckable(True)
        self.macro_b_btn.toggled.connect(lambda state: self._toggle_recording("b", state))
        layout.addWidget(self.macro_b_btn)

        return group

    def _toggle_recording(self, key: str, checked: bool) -> None:
        if checked:
            recorder = MacroRecorder(on_complete=lambda events: self._save_macro(key, events))
            recorder.start()
            if key == "a":
                self._recorder_a = recorder
            else:
                self._recorder_b = recorder
        else:
            if key == "a" and self._recorder_a:
                self.config.recorder.macro_a = self._recorder_a.stop()
                self._recorder_a = None
            elif key == "b" and self._recorder_b:
                self.config.recorder.macro_b = self._recorder_b.stop()
                self._recorder_b = None

    def _save_macro(self, key: str, events: list[MacroEvent]) -> None:
        if key == "a":
            self.config.recorder.macro_a = events
        else:
            self.config.recorder.macro_b = events

    def save_config(self) -> None:
        self.config.mode_one.min_price = self.mode_one_price.value()
        self.config.mode_one.poll_delay_ms = self.mode_one_delay.value()
        self.config.mode_two.trigger_price = self.mode_two_price.value()
        self.config.save()
        QtWidgets.QMessageBox.information(self, "成功", "配置已保存")
