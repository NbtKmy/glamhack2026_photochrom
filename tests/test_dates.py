import pytest

from glamhack2026_photochrom.dates import year_weights


@pytest.mark.parametrize(
    "s,expected",
    [
        ("1897", {1897: 1.0}),
        ("1902/1904", {1902: 1 / 3, 1903: 1 / 3, 1904: 1 / 3}),
        ("1891/1914", None),
        ("104 /1914", None),
        ("", None),
    ],
)
def test_year_weights(s, expected):
    assert year_weights(s) == (pytest.approx(expected) if expected else None)
