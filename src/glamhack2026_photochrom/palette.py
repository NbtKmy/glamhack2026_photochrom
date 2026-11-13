"""CIELAB conversion, shared colour codebook and per-image colour shares."""

import numpy as np
from sklearn.cluster import KMeans

# D65 reference white
_WHITE = np.array([0.95047, 1.0, 1.08883])
_RGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)
_XYZ_TO_RGB = np.linalg.inv(_RGB_TO_XYZ)
_EPS = 216 / 24389
_KAPPA = 24389 / 27


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """(N,3) uint8 sRGB -> (N,3) float CIELAB (D65)."""
    c = np.asarray(rgb, dtype=float) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = lin @ _RGB_TO_XYZ.T / _WHITE
    f = np.where(xyz > _EPS, np.cbrt(xyz), (_KAPPA * xyz + 16) / 116)
    return np.stack(
        [116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1
    )


def lab_to_hex(lab: np.ndarray) -> str:
    """(3,) CIELAB -> '#rrggbb'."""
    L, a, b = lab
    fy = (L + 16) / 116
    f = np.array([fy + a / 500, fy, fy - b / 200])
    xyz = np.where(f**3 > _EPS, f**3, (116 * f - 16) / _KAPPA) * _WHITE
    lin = np.clip(_XYZ_TO_RGB @ xyz, 0, 1)
    c = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)
    r, g, bl = np.clip(np.round(c * 255), 0, 255).astype(int)
    return f"#{r:02x}{g:02x}{bl:02x}"


def build_codebook(
    lab_samples: np.ndarray, k: int = 28, seed: int = 0, chroma_weighted: bool = True
) -> np.ndarray:
    """k-means in Lab; returns (k,3) centres sorted by lightness.

    Photochroms are mostly cream and ochre, so unweighted k-means spends almost every
    centre on browns. Weighting samples by chroma gives the blues, greens and reds a centre.
    """
    weights = None
    if chroma_weighted:
        chroma = np.hypot(lab_samples[:, 1], lab_samples[:, 2])
        weights = (0.1 + np.minimum(chroma, 40) / 40) ** 3
    km = KMeans(n_clusters=k, random_state=seed, n_init=4).fit(lab_samples, sample_weight=weights)
    centres = km.cluster_centers_
    return centres[np.argsort(centres[:, 0], kind="stable")]


def color_shares(lab_pixels: np.ndarray, codebook: np.ndarray) -> np.ndarray:
    """Chroma-weighted share of each codebook colour in the pixels; sums to 1."""
    nearest = ((lab_pixels[:, None, :] - codebook[None, :, :]) ** 2).sum(-1).argmin(1)
    chroma = np.hypot(lab_pixels[:, 1], lab_pixels[:, 2])
    weights = 0.3 + np.minimum(chroma, 60) / 60
    shares = np.bincount(nearest, weights=weights, minlength=len(codebook))
    return shares / shares.sum()
