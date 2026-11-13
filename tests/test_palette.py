import numpy as np
import pytest

from glamhack2026_photochrom.palette import build_codebook, color_shares, lab_to_hex, rgb_to_lab


def test_rgb_to_lab_white_and_black():
    lab = rgb_to_lab(np.array([[255, 255, 255], [0, 0, 0]], dtype=np.uint8))
    assert lab[0] == pytest.approx([100, 0, 0], abs=0.5)
    assert lab[1] == pytest.approx([0, 0, 0], abs=0.5)


def test_lab_to_hex_roundtrip():
    assert lab_to_hex(rgb_to_lab(np.array([[255, 0, 0]], dtype=np.uint8))[0]) == "#ff0000"


def test_build_codebook_shape_and_order():
    rng = np.random.default_rng(0)
    cb = build_codebook(rng.uniform([0, -50, -50], [100, 50, 50], (5000, 3)), k=28)
    assert cb.shape == (28, 3) and np.all(np.diff(cb[:, 0]) >= 0)


def test_color_shares_sums_to_one_and_prefers_chroma():
    cb = np.array([[50, 0, 0], [50, 60, 0]], dtype=float)  # 灰色, 赤
    px = np.array([[50, 0, 0]] * 50 + [[50, 60, 0]] * 50, dtype=float)
    s = color_shares(px, cb)
    assert s.sum() == pytest.approx(1)
    assert s[1] > s[0]  # 同じ画素数なら彩度の高い色が大きい
