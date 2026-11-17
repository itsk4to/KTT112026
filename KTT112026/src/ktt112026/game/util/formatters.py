"""Display helpers — 1000 → 1k, etc."""
from __future__ import annotations


def fmt_num(n: int | float, *, digits: int = 1) -> str:
    try:
        v = float(n)
    except (TypeError, ValueError):
        return str(n)
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v < 1000:
        return sign + str(int(v)) if v == int(v) else sign + f"{v:.{digits}f}".rstrip("0").rstrip(".")
    units = [
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "k"),
    ]
    for thresh, suffix in units:
        if v >= thresh:
            x = v / thresh
            if x >= 100:
                return f"{sign}{int(x)}{suffix}"
            if x >= 10:
                s = f"{x:.1f}".rstrip("0").rstrip(".")
                return f"{sign}{s}{suffix}"
            s = f"{x:.{digits}f}".rstrip("0").rstrip(".")
            return f"{sign}{s}{suffix}"
    return sign + str(int(v))


def fmt_stones(n: int) -> str:
    return f"{fmt_num(n)} LS"
