"""Turn standardised catalogue dates into per-year weights."""

import re

_MAX_SPAN = 9  # ranges wider than this (e.g. 1891/1914) count as undated


def year_weights(std: str) -> dict[int, float] | None:
    """'1897' -> {1897: 1.0}; '1902/1904' -> 1/3 each; wide or unparseable -> None."""
    s = std.strip()
    if re.fullmatch(r"\d{4}", s):
        return {int(s): 1.0}
    m = re.fullmatch(r"(\d{4})/(\d{4})", s)
    if not m:
        return None
    start, end = int(m[1]), int(m[2])
    if end < start or end - start > _MAX_SPAN:
        return None
    n = end - start + 1
    return {y: 1 / n for y in range(start, end + 1)}
