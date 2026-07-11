"""
QQE (Quantitative Qualitative Estimation) 플러그인 (pure-Python, stdlib only)

QQE builds a smoothed RSI trailing-stop line:

1. Wilder RSI over ``rsi_period``
2. Smooth the RSI with a Wilder RMA (smoothing factor ``sf``) → RSI-MA
3. ATR-of-RSI = |RSI-MA change|, double-smoothed with a Wilder RMA over
   ``2*rsi_period - 1`` and scaled by ``factor`` → dynamic band (DAR)
4. A trailing band (long/short) around RSI-MA yields the **fast QQE line** and a
   +1/-1 trend. Trend flipping up is a long signal; flipping down is a short signal.

입력 형식 (ConditionNode와 통일):
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {rsi_period, smoothing, factor, direction}
- field_mapping: {close_field, date_field, symbol_field, exchange_field}

pandas-ta/numpy 미사용 — CodeNode stdlib 샌드박스에 그대로 인라인 가능 (_ta_common.rma 재사용).
"""

from typing import List, Dict, Any, Optional, Tuple

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._ta_common import sanitize, group_by_symbol, rma


QQE_SCHEMA = PluginSchema(
    id="QQE",
    name="QQE (Quantitative Qualitative Estimation)",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description=(
        "Quantitative Qualitative Estimation — a Wilder-smoothed RSI wrapped in an "
        "ATR-of-RSI trailing band. The fast QQE line and its +1/-1 trend filter RSI "
        "whipsaws: a trend flip up is a long signal, a flip down is a short signal."
    ),
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "rsi_period": {
            "type": "int",
            "default": 14,
            "title": "RSI Period",
            "description": "Wilder RSI lookback",
            "ge": 2,
            "le": 200,
        },
        "smoothing": {
            "type": "int",
            "default": 5,
            "title": "RSI Smoothing",
            "description": "Wilder RMA smoothing factor applied to the RSI (SF)",
            "ge": 1,
            "le": 50,
        },
        "factor": {
            "type": "float",
            "default": 4.236,
            "title": "QQE Factor",
            "description": "Multiplier applied to the ATR-of-RSI band (DAR)",
            "ge": 0.1,
            "le": 20,
        },
        "direction": {
            "type": "string",
            "default": "long",
            "title": "Direction",
            "description": "long: pass when trend is +1 (bullish), short: pass when trend is -1",
            "enum": ["long", "short"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["momentum", "oscillator", "trend"],
    output_fields={
        "qqe": {"type": "float", "description": "Fast QQE trailing line (RSI units, 0-100)"},
        "rsi_ma": {"type": "float", "description": "Wilder-smoothed RSI (0-100)"},
        "trend": {"type": "int", "description": "QQE trend direction: +1 bullish, -1 bearish"},
    },
    locales={
        "ko": {
            "name": "QQE (정량적 정성 추정)",
            "description": (
                "와일더 평활 RSI를 ATR-of-RSI 추적 밴드로 감싼 지표입니다. 빠른 QQE선과 "
                "+1/-1 추세가 RSI 휩쏘를 걸러냅니다. 추세가 +1로 전환하면 매수, -1로 전환하면 "
                "매도 신호입니다."
            ),
            "fields.rsi_period": "와일더 RSI 기간",
            "fields.smoothing": "RSI에 적용하는 와일더 RMA 평활 계수 (SF)",
            "fields.factor": "ATR-of-RSI 밴드(DAR)에 곱하는 배수",
            "fields.direction": "방향 (long: 추세 +1 통과, short: 추세 -1 통과)",
        },
    },
)


def _wilder_rsi(closes: List[float], period: int) -> List[Optional[float]]:
    """Wilder RSI aligned to ``closes`` (index 0 → ``None``)."""
    n = len(closes)
    rsi: List[Optional[float]] = [None] * n
    if n < 2:
        return rsi
    gains = [0.0] * (n - 1)
    losses = [0.0] * (n - 1)
    for k in range(1, n):
        d = closes[k] - closes[k - 1]
        if d > 0:
            gains[k - 1] = d
        else:
            losses[k - 1] = -d
    ag = rma(gains, period)
    al = rma(losses, period)
    for k in range(1, n):
        g = ag[k - 1]
        l = al[k - 1]
        if l == 0 and g == 0:
            rsi[k] = 50.0
        elif l == 0:
            rsi[k] = 100.0
        else:
            rs = g / l
            rsi[k] = 100.0 - 100.0 / (1.0 + rs)
    return rsi


def calculate_qqe_series(
    closes: List[float],
    rsi_period: int = 14,
    sf: int = 5,
    factor: float = 4.236,
) -> Tuple[List[Optional[float]], List[Optional[int]], List[Optional[float]]]:
    """QQE 시계열.

    Returns ``(qqe_line, trend, rsi_ma)`` each aligned to ``closes`` with ``None``
    during warmup. ``trend`` is +1/-1.
    """
    n = len(closes)
    qqe: List[Optional[float]] = [None] * n
    trend_out: List[Optional[int]] = [None] * n
    rsima_out: List[Optional[float]] = [None] * n
    if n < rsi_period + 2:
        return qqe, trend_out, rsima_out

    wilders = 2 * rsi_period - 1
    warmup = rsi_period + sf

    rsi = _wilder_rsi(closes, rsi_period)
    rsi_vals = [rsi[k] for k in range(1, n)]  # aligned to close index k = j + 1
    rsima_vals = rma(rsi_vals, sf)
    for k in range(1, n):
        rsima_out[k] = rsima_vals[k - 1]

    atr_rsi = [0.0] * len(rsima_vals)
    for j in range(1, len(rsima_vals)):
        atr_rsi[j] = abs(rsima_vals[j] - rsima_vals[j - 1])
    ma_atr = rma(atr_rsi, wilders)
    dar = [v * factor for v in rma(ma_atr, wilders)]

    longband_prev = 0.0
    shortband_prev = 0.0
    trend = 1
    for j in range(len(rsima_vals)):
        close_idx = j + 1
        rm = rsima_vals[j]
        band = dar[j]
        newlong = rm - band
        newshort = rm + band
        if j == 0:
            longband = newlong
            shortband = newshort
        else:
            rm_prev = rsima_vals[j - 1]
            if rm_prev > longband_prev and rm > longband_prev:
                longband = max(longband_prev, newlong)
            else:
                longband = newlong
            if rm_prev < shortband_prev and rm < shortband_prev:
                shortband = min(shortband_prev, newshort)
            else:
                shortband = newshort
            crossed_up = rm_prev <= shortband_prev and rm > shortband_prev
            crossed_down = rm_prev >= longband_prev and rm < longband_prev
            if crossed_up:
                trend = 1
            elif crossed_down:
                trend = -1
        fast_tl = longband if trend == 1 else shortband
        longband_prev = longband
        shortband_prev = shortband
        if close_idx >= warmup:
            qqe[close_idx] = fast_tl
            trend_out[close_idx] = trend
    return qqe, trend_out, rsima_out


async def qqe_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """QQE 조건 평가 → 표준 6-key 플러그인 결과."""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")

    rsi_period = int(fields.get("rsi_period", 14))
    sf = int(fields.get("smoothing", 5))
    factor = float(fields.get("factor", 4.236))
    direction = fields.get("direction", "long")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided", "indicator": "QQE"},
        }

    groups = group_by_symbol(
        data,
        symbol_field=symbol_field,
        exchange_field=exchange_field,
        date_field=date_field,
    )

    passed: List[Dict[str, str]] = []
    failed: List[Dict[str, str]] = []
    symbol_results: List[Dict[str, Any]] = []
    values: List[Dict[str, Any]] = []

    min_required = 2 * rsi_period + sf

    for group in groups:
        symbol = group["symbol"]
        exchange = group["exchange"]
        rows_sorted = group["rows"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        closes: List[float] = []
        used_rows: List[Dict[str, Any]] = []
        for row in rows_sorted:
            c = row.get(close_field)
            if c is None:
                continue
            try:
                closes.append(float(c))
                used_rows.append(row)
            except (TypeError, ValueError):
                continue

        if len(closes) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "qqe": None,
                "rsi_ma": None,
                "trend": None,
                "error": f"insufficient_data: need {min_required} bars, got {len(closes)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        if max(closes) == min(closes):
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "qqe": None,
                "rsi_ma": None,
                "trend": None,
                "error": "flat_series: close price is constant, QQE trend undefined",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        qqe_series, trend_series, rsima_series = calculate_qqe_series(
            closes, rsi_period, sf, factor
        )

        time_series: List[Dict[str, Any]] = []
        prev_trend: Optional[int] = None
        for i, qqe_val in enumerate(qqe_series):
            if qqe_val is None:
                continue
            row = used_rows[i]
            tr = trend_series[i]
            signal = None
            side = "long"
            if prev_trend is not None and tr is not None and tr != prev_trend:
                if tr == 1:
                    signal = "buy"
                elif tr == -1:
                    signal = "sell"
            time_series.append({
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field),
                high_field: row.get(high_field),
                low_field: row.get(low_field),
                close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "qqe": sanitize(qqe_val, 4),
                "rsi_ma": sanitize(rsima_series[i], 4),
                "trend": tr,
                "signal": signal,
                "side": side,
            })
            prev_trend = tr

        latest_qqe = None
        latest_trend = None
        latest_rsima = None
        for i in range(len(qqe_series) - 1, -1, -1):
            if qqe_series[i] is not None:
                latest_qqe = qqe_series[i]
                latest_trend = trend_series[i]
                latest_rsima = rsima_series[i]
                break

        if latest_qqe is None or latest_trend is None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "qqe": None,
                "rsi_ma": None,
                "trend": None,
                "error": "qqe_unavailable: trailing band did not resolve (degenerate series)",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})
            continue

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "qqe": sanitize(latest_qqe, 4),
            "rsi_ma": sanitize(latest_rsima, 4),
            "trend": latest_trend,
        })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        if direction == "short":
            passed_condition = latest_trend == -1
        else:
            passed_condition = latest_trend == 1
        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "QQE",
            "rsi_period": rsi_period,
            "smoothing": sf,
            "factor": factor,
            "direction": direction,
        },
    }


__all__ = [
    "qqe_condition",
    "calculate_qqe_series",
    "QQE_SCHEMA",
]
