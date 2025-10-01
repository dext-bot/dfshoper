from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Iterable

from PySide6.QtCore import QObject, Signal

from .config import AppConfig, Mode1Item
from .coordinates import Point, Region
from .input_actions import click, perform_actions
from .ocr import read_price
from .screenshot import grab_pixel

LOGGER = logging.getLogger(__name__)


class AutomationController(QObject):
    message = Signal(str)
    price_checked = Signal(str, float, float)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self._mode1_thread: threading.Thread | None = None
        self._mode1_stop = threading.Event()
        self._mode2_thread: threading.Thread | None = None
        self._mode2_stop = threading.Event()

    def start_mode1(self) -> None:
        if self._mode1_thread and self._mode1_thread.is_alive():
            self.message.emit("模式1已经运行中")
            return
        self._mode1_stop.clear()
        self._mode1_thread = threading.Thread(target=self._mode1_worker, daemon=True)
        self._mode1_thread.start()
        self.message.emit("模式1启动")

    def stop_mode1(self) -> None:
        self._mode1_stop.set()
        self.message.emit("模式1停止请求")

    def start_mode2(self) -> None:
        if self._mode2_thread and self._mode2_thread.is_alive():
            self.message.emit("模式2已经运行中")
            return
        self._mode2_stop.clear()
        self._mode2_thread = threading.Thread(target=self._mode2_worker, daemon=True)
        self._mode2_thread.start()
        self.message.emit("模式2启动")

    def stop_mode2(self) -> None:
        self._mode2_stop.set()
        self.message.emit("模式2停止请求")

    # ----------------- Mode 1 -----------------

    def _mode1_worker(self) -> None:
        while not self._mode1_stop.is_set():
            for item in list(self.config.mode1_items.values()):
                if self._mode1_stop.is_set():
                    break
                self._process_mode1_item(item)
            time.sleep(0.1)
        self.message.emit("模式1线程退出")

    def _process_mode1_item(self, item: Mode1Item) -> None:
        LOGGER.debug("Checking item %s", item.name)
        click(item.target_point)
        time.sleep(max(item.delay_ms, 0) / 1000)

        price1 = read_price(self.config.coordinates.price_primary_region)
        if price1 is None:
            self.message.emit(f"{item.name}: 未识别到价格1")
            return
        self.message.emit(f"{item.name}: 价格1={price1:.2f}")
        if price1 > item.min_price:
            return

        click(self.config.coordinates.max_quantity_button)
        time.sleep(0.05)

        price2 = read_price(self.config.coordinates.price_secondary_region)
        if price2 is None:
            self.message.emit(f"{item.name}: 未识别到价格2")
            return
        self.message.emit(f"{item.name}: 价格2={price2:.2f}")
        self.price_checked.emit(item.name, price1, price2)

        if price2 <= item.min_price:
            click(self.config.coordinates.purchase_button)
            self.message.emit(f"{item.name}: 已执行购买")
        else:
            self.message.emit(f"{item.name}: 价格2高于阈值")

    # ----------------- Mode 2 -----------------

    def _mode2_worker(self) -> None:
        settings = self.config.mode2
        while not self._mode2_stop.is_set():
            price = read_price(settings.price_region)
            if price is None:
                self.message.emit("模式2: 无法识别价格")
                time.sleep(0.5)
                continue
            if price > settings.min_price:
                self.message.emit(f"模式2: 价格{price:.2f} 高于阈值，执行操作1")
                perform_actions(settings.action1)
            else:
                self.message.emit(f"模式2: 价格{price:.2f} 低于阈值，执行操作2")
                perform_actions(settings.action2)
                color = grab_pixel(settings.post_check_point)
                if tuple(color) == tuple(settings.post_check_color):
                    self.message.emit("模式2: 终止条件满足，停止")
                    self._mode2_stop.set()
                    break
            time.sleep(0.1)
        self.message.emit("模式2线程退出")
