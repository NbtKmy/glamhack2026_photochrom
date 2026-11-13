import numpy as np
import pytest

from glamhack2026_photochrom.features import image_features


def _half_red_half_blue():
    return np.array([[200, 30, 30]] * 600 + [[40, 60, 200]] * 400, dtype=np.uint8)


def test_own_palette_finds_both_colours_with_pixel_shares():
    f = image_features(_half_red_half_blue(), n_colours=2)
    pal = sorted(f["palette"], key=lambda c: -c["share"])
    assert [c["hex"] for c in pal] == ["#c81e1e", "#283cc8"]
    assert [c["share"] for c in pal] == pytest.approx([0.6, 0.4], abs=0.001)


def test_summary_statistics():
    f = image_features(_half_red_half_blue(), n_colours=2)
    assert set(f) == {"palette", "mean_lab", "lightness_std", "mean_chroma", "colourfulness", "hue_hist"}
    assert len(f["mean_lab"]) == 3
    assert f["mean_chroma"] > 40 and f["colourfulness"] > 50


def test_hue_histogram_has_12_bins_and_ignores_greys():
    px = np.array([[200, 30, 30]] * 100 + [[128, 128, 128]] * 900, dtype=np.uint8)
    hist = image_features(px, n_colours=2)["hue_hist"]
    assert len(hist) == 12 and sum(hist) == pytest.approx(1)
    assert max(hist) == pytest.approx(1)  # only the red pixels count


def test_grey_image_has_empty_hue_histogram():
    px = np.full((500, 3), 128, dtype=np.uint8)
    f = image_features(px, n_colours=3)
    assert f["hue_hist"] == [0.0] * 12
    assert len(f["palette"]) >= 1
