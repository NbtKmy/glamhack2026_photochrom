import pytest
from PIL import Image, ImageDraw

from glamhack2026_photochrom.crop import crop_print


def _scan(w=400, h=340, print_box=(20, 10, 380, 250), chart_y=(270, 320)):
    img = Image.new("RGB", (w, h), (58, 58, 58))  # 背景グレー
    d = ImageDraw.Draw(img)
    d.rectangle(print_box, fill=(120, 160, 200))  # プリント
    d.rectangle((40, chart_y[0], 360, chart_y[1]), fill=(220, 220, 220))  # チャート
    return img


def test_crop_print_finds_print_and_excludes_chart():
    out, box = crop_print(_scan())
    assert box == pytest.approx((20 / 400, 10 / 340, 381 / 400, 251 / 340), abs=0.02)


def test_crop_print_fallback_when_print_matches_background():
    img = Image.new("RGB", (400, 300), (58, 58, 58))
    out, box = crop_print(img)
    assert box == pytest.approx((0.1, 0.1, 0.9, 0.9)) and out.size[0] > 0


def test_crop_print_chart_touching_bottom_and_sides():
    # 実スキャン: チャートが下端・左右端まで届き、プリントとの隙間は約10px
    img = Image.new("RGB", (400, 340), (58, 58, 58))
    d = ImageDraw.Draw(img)
    d.rectangle((15, 10, 385, 290), fill=(120, 160, 200))
    d.rectangle((0, 300, 399, 339), fill=(170, 150, 100))
    out, box = crop_print(img)
    assert box == pytest.approx((15 / 400, 10 / 340, 386 / 400, 291 / 340), abs=0.02)


def test_crop_print_vertical_chart_on_right():
    # 縦長スキャン: チャートがプリントの右側に縦向きで置かれる
    img = Image.new("RGB", (340, 400), (58, 58, 58))
    d = ImageDraw.Draw(img)
    d.rectangle((10, 15, 290, 385), fill=(120, 160, 200))
    d.rectangle((300, 0, 339, 399), fill=(170, 150, 100))
    out, box = crop_print(img)
    assert box == pytest.approx((10 / 340, 15 / 400, 291 / 340, 386 / 400), abs=0.02)
