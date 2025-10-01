from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from dfshoper.config import ModeTwoConfig
from dfshoper.services.actions import ActionExecutor, OperationScript
from dfshoper.services.ocr import OcrEngine
from dfshoper.services.screen import CaptureRegion, ScreenCapture

LOGGER = logging.getLogger(__name__)


class ModeTwoController:
    def __init__(
        self,
        capture: ScreenCapture,
        ocr: OcrEngine,
        executor: ActionExecutor,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._capture = capture
        self._ocr = ocr
        self._executor = executor
        self._status_callback = status_callback or (lambda msg: LOGGER.info(msg))
        self._config: Optional[ModeTwoConfig] = None
        self._high_script: Optional[OperationScript] = None
        self._low_script: Optional[OperationScript] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def configure(self, config: ModeTwoConfig) -> None:
        self._config = config

    def load_scripts(self, high: Optional[Path], low: Optional[Path]) -> None:
        if isinstance(high, str):
            high = Path(high)
        if isinstance(low, str):
            low = Path(low)
        try:
            self._high_script = OperationScript.from_path(high) if high else None
        except FileNotFoundError:
            self._high_script = None
            LOGGER.warning("未找到高价脚本: %s", high)
        try:
            self._low_script = OperationScript.from_path(low) if low else None
        except FileNotFoundError:
            self._low_script = None
            LOGGER.warning("未找到低价脚本: %s", low)

    def start(self) -> None:
        if self._running:
            return
        if not self._config or not self._config.price_anchor:
            self._status("模式二缺少价格坐标")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._status("模式二已启动")

    def stop(self) -> None:
        self._running = False
        self._status("模式二已停止")

    def _run(self) -> None:
        assert self._config
        interval = self._config.poll_interval_ms / 1000
        while self._running:
            try:
                self._loop()
            except Exception as exc:  # pragma: no cover
                LOGGER.exception("模式二异常: %s", exc)
                self._status(f"模式二异常: {exc}")
            time.sleep(interval)

    def _loop(self) -> None:
        assert self._config and self._config.price_anchor
        region = CaptureRegion.around(self._config.price_anchor, 160, 70)
        price_img = self._capture.grab_region(region)
        price = self._ocr.read_digits(price_img)
        if price is None:
            return
        self._status(f"模式二价格识别: {price}")
        if price > self._config.threshold:
            if self._high_script:
                self._executor.execute(self._high_script)
                self._status("执行录制操作1")
        else:
            if self._low_script:
                self._executor.execute(self._low_script)
                self._status("执行录制操作2")
                self._check_terminate()

    def _check_terminate(self) -> None:
        assert self._config
        terminate = self._config.terminate_color
        if not terminate.coordinate:
            return
        pixel = self._capture.pixel_color(terminate.coordinate)
        if tuple(pixel) == tuple(terminate.rgb):
            self._status("终止颜色命中，停止模式二")
            self.stop()

    def _status(self, message: str) -> None:
        self._status_callback(message)


__all__ = ["ModeTwoController"]
