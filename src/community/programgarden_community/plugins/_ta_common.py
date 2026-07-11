"""
Shared pure-Python technical-analysis helpers (stdlib only).

Leading-underscore module name → excluded from plugin auto-registration
(``register_all_plugins`` only imports concrete ``<name>/__init__.py`` packages).

These helpers are deliberately **stdlib-only** (``math`` / ``statistics``) so that
the indicator plugins built on top of them (FisherTransform / CMO / SchaffTrendCycle
/ QQE) are *dual-use*: they run as community plugins **and** can be inlined verbatim
into the CodeNode stdlib-only sandbox. Introducing any third-party import here
(numpy / pandas / scipy) would break that guarantee — do not add one.

No-silent-failure contract: every helper returns explicit sentinels (``None`` for
non-finite / undefined results) rather than absorbing errors. Callers are expected
to surface an explicit reason when a helper yields ``None``.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence


def sanitize(x: Any, ndigits: Optional[int] = 6) -> Optional[float]:
    """Coerce a numeric value to a finite, JSON-serializable float.

    NaN / +-inf / non-numeric → ``None`` (no silent NaN leaking into JSON).
    Finite values are rounded to ``ndigits`` decimals (pass ``None`` to skip rounding).
    """
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    if ndigits is not None:
        return round(v, ndigits)
    return v


def group_by_symbol(
    data: Sequence[Dict[str, Any]],
    symbol_field: str = "symbol",
    exchange_field: str = "exchange",
    date_field: str = "date",
) -> List[Dict[str, Any]]:
    """Group a flat row array by (symbol, exchange), each group sorted by date asc.

    Returns a **list** of ``{"symbol", "exchange", "rows": [...]}`` (never a
    symbol-keyed dict — mandated symbol-array format). First-seen order of the
    (symbol, exchange) pair is preserved for deterministic output.
    """
    order: List = []
    groups: Dict = {}
    for row in data or []:
        if not isinstance(row, dict):
            continue
        sym = row.get(symbol_field)
        if not sym:
            continue
        exch = row.get(exchange_field, "UNKNOWN")
        key = (sym, exch)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)

    result: List[Dict[str, Any]] = []
    for sym, exch in order:
        rows_sorted = sorted(groups[(sym, exch)], key=lambda r: r.get(date_field, ""))
        result.append({"symbol": sym, "exchange": exch, "rows": rows_sorted})
    return result


def ema(seq: Sequence[float], n: int) -> List[float]:
    """Exponential moving average — full-length series (adjust=False convention).

    Seeded with ``seq[0]`` then recursively smoothed with ``k = 2/(n+1)``. Output
    length equals input length so two EMA series can be subtracted element-wise
    (e.g. MACD line = ema(fast) - ema(slow)).
    """
    if not seq:
        return []
    k = 2.0 / (n + 1.0)
    out = [float(seq[0])]
    prev = out[0]
    for x in seq[1:]:
        prev = (float(x) - prev) * k + prev
        out.append(prev)
    return out


def rma(seq: Sequence[float], n: int) -> List[float]:
    """Wilder's smoothing (RMA / SMMA) — full-length series.

    Equivalent to an EMA with ``alpha = 1/n`` (``rma[i] = rma[i-1] + (x - rma[i-1])/n``),
    seeded with ``seq[0]``. Used for Wilder RSI and QQE band smoothing.
    """
    if not seq:
        return []
    if n <= 0:
        n = 1
    alpha = 1.0 / n
    out = [float(seq[0])]
    prev = out[0]
    for x in seq[1:]:
        prev = alpha * float(x) + (1.0 - alpha) * prev
        out.append(prev)
    return out


def rolling(seq: Sequence[float], n: int) -> List[List[float]]:
    """Trailing windows of length ``n``.

    Returns ``[seq[i-n+1 : i+1] for i in range(n-1, len(seq))]`` — a list of
    ``len(seq) - n + 1`` windows (empty when the series is shorter than ``n``).
    """
    if n <= 0 or len(seq) < n:
        return []
    return [list(seq[i - n + 1 : i + 1]) for i in range(n - 1, len(seq))]


def stochastic(values: Sequence[float], period: int) -> List[Optional[float]]:
    """Raw %K stochastic of a **single** series over ``period``.

    ``%K = 100 * (v - min_window) / (max_window - min_window)``. Full-length list:
    warmup indices (< ``period`` - 1) and flat windows (max == min, undefined) yield
    ``None`` so the caller decides how to handle them (forward-fill, skip, ...).
    """
    out: List[Optional[float]] = []
    for i in range(len(values)):
        if i < period - 1:
            out.append(None)
            continue
        window = values[i - period + 1 : i + 1]
        lo = min(window)
        hi = max(window)
        if hi == lo:
            out.append(None)
        else:
            out.append((float(values[i]) - lo) / (hi - lo) * 100.0)
    return out


__all__ = [
    "sanitize",
    "group_by_symbol",
    "ema",
    "rma",
    "rolling",
    "stochastic",
]
