from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

try:
    import easyocr
except ImportError as exc:  # pragma: no cover - runtime dependency
    raise RuntimeError(
        "easyocr is required for GPU based OCR. Install dependencies first."
    ) from exc

from .coordinates import Region
from .screenshot import grab_region

LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_reader() -> "easyocr.Reader":
    try:
        reader = easyocr.Reader(["ch_sim", "en"], gpu=True)
    except Exception as exc:  # pragma: no cover - hardware specific
        raise RuntimeError(
            "Failed to create EasyOCR reader with GPU support. Ensure a GPU is available and supported drivers are installed."
        ) from exc
    return reader


def read_price(region: Region) -> Optional[float]:
    """Read a price value from the supplied screen region.

    Parameters
    ----------
    region:
        The screen region that contains the numeric price string.

    Returns
    -------
    Optional[float]
        A floating point representation of the detected price, or ``None``
        when recognition fails.
    """

    img = grab_region(region)
    reader = _get_reader()
    results = reader.readtext(img)
    if not results:
        return None
    # Use the text with the highest confidence that resembles a number
    candidates = []
    for (_, text, confidence) in results:
        cleaned = (
            text.replace(",", "")
            .replace("¥", "")
            .replace("$", "")
            .replace(" ", "")
            .strip()
        )
        if not cleaned:
            continue
        try:
            value = float(cleaned)
        except ValueError:
            continue
        candidates.append((confidence, value))
    if not candidates:
        LOGGER.debug("No numeric OCR results for region %s", region)
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]
