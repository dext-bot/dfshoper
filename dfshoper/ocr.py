"""GPU accelerated OCR utilities."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import numpy as np

try:
    import easyocr
except ImportError as exc:  # pragma: no cover - dependency optional
    raise RuntimeError("easyocr is required for OCR functionality") from exc


@lru_cache(maxsize=1)
def _reader(language: str = "en") -> "easyocr.Reader":
    # easyocr leverages PyTorch GPU when gpu=True.
    return easyocr.Reader([language], gpu=True)


def read_number(image: np.ndarray, language: str = "en") -> Optional[float]:
    """Return the first numeric value detected in the image."""
    reader = _reader(language)
    results = reader.readtext(image)
    for _bbox, text, _confidence in results:
        cleaned = text.replace(",", "").replace("$", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            continue
    return None
