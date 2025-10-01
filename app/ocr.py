from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)


@dataclass
class OCRConfig:
    use_angle_cls: bool = False
    lang: str = "ch"
    enable_gpu: bool = True


class OCREngine:
    """Wrapper around PaddleOCR enforcing GPU usage."""

    def __init__(self, config: Optional[OCRConfig] = None) -> None:
        self.config = config or OCRConfig()
        if not self.config.enable_gpu:
            raise RuntimeError("GPU usage is mandatory for OCR operations.")
        try:
            self._ocr = PaddleOCR(use_angle_cls=self.config.use_angle_cls, lang=self.config.lang, use_gpu=True)
        except Exception as exc:  # pragma: no cover - depends on environment
            logger.exception("Failed to initialize PaddleOCR with GPU support")
            raise RuntimeError("Unable to initialize PaddleOCR with GPU support") from exc

    def recognize_number(self, image: np.ndarray) -> Optional[float]:
        """Recognize numeric text from the provided image."""
        result = self._ocr.ocr(image, cls=False)
        best_score = -1.0
        best_text: Optional[str] = None
        for line in result:
            if not line:
                continue
            text, score = line[0][1][0], line[0][1][1]
            if score > best_score:
                best_score = score
                best_text = text
        if best_text is None:
            return None
        filtered = "".join(ch for ch in best_text if ch.isdigit() or ch in {".", ","})
        filtered = filtered.replace(",", ".")
        try:
            return float(filtered)
        except ValueError:
            logger.debug("OCR result not numeric: %s", best_text)
            return None


__all__ = ["OCREngine", "OCRConfig"]
