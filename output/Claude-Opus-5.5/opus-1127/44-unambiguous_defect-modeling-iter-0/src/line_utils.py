"""Helpers for matching subway line names written in different styles.

For example "Line 1", "line1", "1号线" and "地铁1号线" all map to the same
canonical key ``line1``.
"""

import re
import unicodedata

# Ordered list: more specific keywords must come first.
_NAMED_LINES = [
    ("daxingairport", ("大兴机场", "daxingairport")),
    ("airport", ("首都机场", "机场线", "airport")),
    ("changping", ("昌平", "changping")),
    ("yizhuang", ("亦庄", "yizhuang")),
    ("fangshan", ("房山", "fangshan")),
    ("batong", ("八通", "batong")),
    ("xijiao", ("西郊", "xijiao")),
    ("yanfang", ("燕房", "yanfang")),
]

_cache = {}


def canonical_line_key(name):
    """Return a canonical key for a line name (used for loose matching)."""
    if name is None:
        return ""
    if name in _cache:
        return _cache[name]
    s = unicodedata.normalize("NFKC", str(name)).strip().lower()
    s = re.sub(r"[\s_\-]+", "", s)
    for noise in ("beijingsubway", "subway", "地铁", "metro"):
        s = s.replace(noise, "")
    key = s
    match = re.fullmatch(r"(?:line)?(\d+)(?:号线|line|号)?", s)
    if match:
        key = "line" + str(int(match.group(1)))
    else:
        for canonical, keywords in _NAMED_LINES:
            if any(k in s for k in keywords):
                key = canonical
                break
    _cache[name] = key
    return key


def lines_match(a, b):
    """Return True when two line names refer to the same line."""
    return canonical_line_key(a) == canonical_line_key(b)
