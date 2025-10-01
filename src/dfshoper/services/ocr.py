from __future__ import annotations

import logging
from typing import Iterable, Optional

import cv2
import numpy as np

try:
    import easyocr
except ImportError as exc:  # pragma: no cover - runtime dependency
    raise RuntimeError("easyocr 未安装，请先执行 pip install easyocr") from exc

LOGGER = logging.getLogger(__name__)


class OcrEngine:
    """封装 EasyOCR，默认启用 GPU。"""

    def __init__(self, languages: Optional[Iterable[str]] = None, gpu: bool = True) -> None:
        langs = list(languages) if languages else ["en", "ch_sim"]
        self._reader = easyocr.Reader(langs, gpu=gpu)

    def read_digits(self, image: np.ndarray) -> Optional[float]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        result = self._reader.readtext(thresh, detail=0, paragraph=False)
        LOGGER.debug("OCR raw result: %s", result)
        for text in result:
            price = self._parse_price(str(text))
            if price is not None:
                return price
        return None

    @staticmethod
    def _parse_price(text: str) -> Optional[float]:
        cleaned = "".join(ch for ch in text if ch.isdigit() or ch in {".", ","})
        if not cleaned:
            return None
        cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return None


__all__ = ["OcrEngine"]
