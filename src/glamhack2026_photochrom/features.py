"""Per-image colour features, independent of the shared codebook."""

import numpy as np
from sklearn.cluster import KMeans

from .palette import lab_to_hex, rgb_to_lab

_HUE_BINS = 12
_MIN_CHROMA = 10  # below this a pixel has no meaningful hue


def _r(x: float, nd: int = 2) -> float:
    return round(float(x), nd)


def image_features(rgb_pixels: np.ndarray, n_colours: int = 6, seed: int = 0) -> dict:
    """Own palette (k-means in Lab, shares by pixel count) and summary statistics."""
    lab = rgb_to_lab(rgb_pixels)
    k = min(n_colours, len(np.unique(rgb_pixels, axis=0)))
    km = KMeans(n_clusters=k, random_state=seed, n_init=2).fit(lab)
    counts = np.bincount(km.labels_, minlength=k) / len(lab)
    palette = [
        {"hex": lab_to_hex(c), "lab": [_r(v, 1) for v in c], "share": _r(s, 3)}
        for c, s in sorted(zip(km.cluster_centers_, counts), key=lambda t: -t[1])
    ]

    chroma = np.hypot(lab[:, 1], lab[:, 2])
    coloured = chroma >= _MIN_CHROMA
    hue = np.degrees(np.arctan2(lab[coloured, 2], lab[coloured, 1])) % 360
    hist = np.bincount((hue // (360 / _HUE_BINS)).astype(int), weights=chroma[coloured], minlength=_HUE_BINS)
    hist = hist / hist.sum() if hist.sum() > 0 else hist

    # Hasler & Süsstrunk (2003) colourfulness on sRGB
    rgb = rgb_pixels.astype(float)
    rg = rgb[:, 0] - rgb[:, 1]
    yb = 0.5 * (rgb[:, 0] + rgb[:, 1]) - rgb[:, 2]
    colourfulness = np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean())

    return {
        "palette": palette,
        "mean_lab": [_r(v) for v in lab.mean(axis=0)],
        "lightness_std": _r(lab[:, 0].std()),
        "mean_chroma": _r(chroma.mean()),
        "colourfulness": _r(colourfulness),
        "hue_hist": [_r(v, 3) for v in hist],
    }
