"""Cut the photochrom print out of a scan (drop the grey backdrop and colour chart)."""

import numpy as np
from PIL import Image

_FALLBACK = (0.1, 0.1, 0.9, 0.9)


def _runs(mask: np.ndarray, max_gap: int) -> list[tuple[int, int]]:
    """Runs of True as (start, end_exclusive), bridging gaps up to max_gap."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    runs, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > max_gap + 1:
            runs.append((start, prev + 1))
            start = i
        prev = i
    runs.append((start, prev + 1))
    return runs


def crop_print(img: Image.Image) -> tuple[Image.Image, tuple[float, float, float, float]]:
    """Return the cropped print and its box relative to the scan (x0, y0, x1, y1 in 0..1)."""
    a = np.asarray(img.convert("RGB"), dtype=float)
    h, w, _ = a.shape
    # The colour chart can reach a corner of the scan; the backdrop is the most neutral
    # (then darkest) of the four corner colours.
    corners = [np.median(c.reshape(-1, 3), axis=0) for c in
               (a[:10, :10], a[:10, -10:], a[-10:, :10], a[-10:, -10:])]
    background = min(corners, key=lambda c: (round(c.max() - c.min()), c.sum()))
    fg = np.linalg.norm(a - background, axis=2) > 25

    # The print is the longest band of foreground rows/columns; the chart is a separate band
    # (below or beside it) with only a narrow strip of backdrop in between.
    def longest(mask: np.ndarray) -> tuple[int, int]:
        return max(_runs(mask, max_gap=2), key=lambda r: r[1] - r[0], default=(0, 0))

    y0, y1 = longest(fg.mean(axis=1) > 0.5)
    x0, x1 = longest(fg[y0:y1].mean(axis=0) > 0.5) if y1 > y0 else (0, 0)
    if x1 > x0:
        y0, y1 = longest(fg[:, x0:x1].mean(axis=1) > 0.5)
    if y1 - y0 < 0.2 * h or x1 - x0 < 0.2 * w:
        box = _FALLBACK
    else:
        box = (x0 / w, y0 / h, x1 / w, y1 / h)

    x0, y0p, x1, y1p = box
    out = img.crop((round(x0 * w), round(y0p * h), round(x1 * w), round(y1p * h)))
    return out, box
