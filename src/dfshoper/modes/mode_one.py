from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from dfshoper.config import AnchorConfig, ModeOneItem
from dfshoper.services.actions import ActionExecutor
from dfshoper.services.ocr import OcrEngine
from dfshoper.services.screen import CaptureRegion, ScreenCapture

LOGGER = logging.getLogger(__name__)


@dataclass
class ModeOneTask:
    item: ModeOneItem
    active: bool = False
    thread: Optional[threading.Thread] = None


class ModeOneController:
    def __init__(
        self,
        anchors: AnchorConfig,
        capture: ScreenCapture,
        ocr: OcrEngine,
        executor: ActionExecutor,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._anchors = anchors
        self._capture = capture
        self._ocr = ocr
        self._executor = executor
        self._status_callback = status_callback or (lambda msg: LOGGER.info(msg))
        self._tasks: List[ModeOneTask] = []
        self._running = False

    def load_items(self, items: List[ModeOneItem]) -> None:
        self._tasks = [ModeOneTask(item=item) for item in items]

    def add_item(self, item: ModeOneItem) -> None:
        self._tasks.append(ModeOneTask(item=item))

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        for task in self._tasks:
            task.active = task.item.active
            if task.active:
                thread = threading.Thread(target=self._run_task, args=(task,), daemon=True)
                task.thread = thread
                thread.start()
        self._status("模式一已启动")

    def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.active = False
        self._status("模式一已停止")

    def _run_task(self, task: ModeOneTask) -> None:
        while self._running and task.active:
            try:
                self._tick(task)
            except Exception as exc:  # pragma: no cover - safety
                LOGGER.exception("模式一任务异常: %s", exc)
                self._status(f"任务 {task.item.name} 异常: {exc}")
            time.sleep(task.item.poll_interval_ms / 1000)

    def _tick(self, task: ModeOneTask) -> None:
        region = CaptureRegion.around(task.item.coordinate, 160, 70)
        image = self._capture.grab_region(region)
        price = self._ocr.read_digits(image)
        LOGGER.debug("%s OCR price=%s", task.item.name, price)
        if price is None:
            return
        if price <= task.item.threshold:
            self._status(f"{task.item.name} 价格 {price} 低于阈值 {task.item.threshold}")
            if not self._anchors.max_quantity_button or not self._anchors.purchase_button:
                self._status("缺少购买按钮坐标，无法执行操作")
                return
            self._executor.move_and_click(self._anchors.max_quantity_button)
            time.sleep(0.05)
            if self._anchors.price_secondary:
                region2 = CaptureRegion.around(self._anchors.price_secondary, 160, 70)
                image2 = self._capture.grab_region(region2)
                price2 = self._ocr.read_digits(image2)
            else:
                price2 = price
            if price2 is not None and price2 <= task.item.threshold:
                self._executor.move_and_click(self._anchors.purchase_button)
                self._status(f"已执行购买 {task.item.name}")
            else:
                self._status(f"二次确认价格 {price2} 未满足条件")

    def _status(self, message: str) -> None:
        self._status_callback(message)


__all__ = ["ModeOneController"]
