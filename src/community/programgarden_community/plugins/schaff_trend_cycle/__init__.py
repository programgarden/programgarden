"""
Schaff Trend Cycle (STC) 플러그인 (pure-Python, stdlib only)

STC applies a **double stochastic** to a MACD line (Schaff, 1999) to produce a fast,
0-100 bounded cycle oscillator that reacts sooner than a raw MACD:

1. MACD line = EMA(close, fast) - EMA(close, slow)
2. First stochastic of the MACD over ``cycle``, smoothed (factor 0.5) → PF
3. Second stochastic of PF over ``cycle``, smoothed (factor 0.5) → STC

STC rising through ``lower`` signals a bullish cycle turn; falling through ``upper``
signals a bearish turn.

입력 형식 (ConditionNode와 통일):
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {fast, slow, cycle, lower, upper, direction}
- field_mapping: {close_field, date_field, symbol_field, exchange_field}

pandas-ta/numpy 미사용 — CodeNode stdlib 샌드박스에 그대로 인라인 가능 (_ta_common.ema 재사용).
"""

from typing import List, Dict, Any, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._ta_common import sanitize, group_by_symbol, ema


SCHAFF_TREND_CYCLE_SCHEMA = PluginSchema(
    id="SchaffTrendCycle",
    name="Schaff Trend Cycle (STC)",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description=(
        "Schaff Trend Cycle — a double stochastic of a MACD line, bounded 0-100, that "
        "leads a raw MACD in signalling cycle turns. Bullish when STC rises through the "
        "lower band; bearish when it falls through the upper band."
    ),
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "fast": {
            "type": "int",
            "default": 23,
            "title": "Fast EMA",
            "description": "Fast EMA period of the underlying MACD line",
            "ge": 2,
            "le": 200,
        },
        "slow": {
            "type": "int",
            "default": 50,
            "title": "Slow EMA",
            "description": "Slow EMA period of the underlying MACD line",
            "ge": 3,
            "le": 400,
        },
        "cycle": {
            "type": "int",
            "default": 10,
            "title": "Cycle Length",
            "description": "Stochastic lookback applied twice to the MACD line",
            "ge": 2,
            "le": 100,
        },
        "lower": {
            "type": "float",
            "default": 25,
            "title": "Lower Band",
            "description": "Oversold band; a rise through it is bullish",
            "ge": 0,
            "le": 50,
        },
        "upper": {
            "type": "float",
            "default": 75,
            "title": "Upper Band",
            "description": "Overbought band; a fall through it is bearish",
            "ge": 50,
            "le": 100,
        },
        "direction": {
            "type": "string",
            "default": "long",
            "title": "Direction",
            "description": "long: pass when STC > 50 (bullish cycle), short: pass when STC < 50",
            "enum": ["long", "short"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["trend", "momentum", "oscillator"],
    output_fields={
        "stc": {"type": "float", "description": "Schaff Trend Cycle value (0-100)"},
    },
    locales={
        "ko": {
            "name": "샤프 트렌드 사이클 (STC)",
            "description": (
                "MACD 선에 이중 스토캐스틱을 적용한 0-100 오실레이터로, 원시 MACD보다 빠르게 "
                "사이클 전환을 포착합니다. STC가 하단 밴드를 상향 돌파하면 상승, 상단 밴드를 "
                "하향 돌파하면 하락 신호입니다."
            ),
            "fields.fast": "기반 MACD의 빠른 EMA 기간",
            "fields.slow": "기반 MACD의 느린 EMA 기간",
            "fields.cycle": "MACD 선에 두 번 적용하는 스토캐스틱 기간",
            "fields.lower": "과매도 밴드 (상향 돌파 시 상승)",
            "fields.upper": "과매수 밴드 (하향 돌파 시 하락)",
            "fields.direction": "방향 (long: STC>50 통과, short: STC<50 통과)",
        },
    },
)


def calculate_stc_series(
    closes: List[float],
    fast: int,
    slow: int,
    cycle: int,
    factor: float = 0.5,
) -> List[Optional[float]]:
    """Schaff Trend Cycle 시계열 aligned to ``closes`` (warmup → ``None``).

    Reuses ``_ta_common.ema`` for the MACD line, then applies two smoothed
    stochastics over ``cycle``. Flat stochastic windows forward-fill the previous
    value (standard STC behaviour) instead of dividing by zero.
    """
    n = len(closes)
    stc: List[Optional[float]] = [None] * n
    if n == 0:
        return stc

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd = [f - s for f, s in zip(ema_fast, ema_slow)]

    # First stochastic of the MACD line → smoothed PF
    pf_series: List[Optional[float]] = [None] * n
    pf: Optional[float] = None
    prev_stoch1: Optional[float] = None
    for i in range(n):
        if i < cycle - 1:
            continue
        window = macd[i - cycle + 1 : i + 1]
        lo = min(window)
        hi = max(window)
        if hi != lo:
            stoch1 = 100.0 * (macd[i] - lo) / (hi - lo)
        else:
            stoch1 = prev_stoch1
        if stoch1 is None:
            continue
        prev_stoch1 = stoch1
        pf = stoch1 if pf is None else pf + factor * (stoch1 - pf)
        pf_series[i] = pf

    # Second stochastic of PF → smoothed PFF = STC
    pff: Optional[float] = None
    prev_stoch2: Optional[float] = None
    for i in range(n):
        if pf_series[i] is None:
            continue
        window = [
            pf_series[j]
            for j in range(max(0, i - cycle + 1), i + 1)
            if pf_series[j] is not None
        ]
        if not window:
            continue
        lo = min(window)
        hi = max(window)
        if hi != lo:
            stoch2 = 100.0 * (pf_series[i] - lo) / (hi - lo)
        else:
            stoch2 = prev_stoch2
        if stoch2 is None:
            continue
        prev_stoch2 = stoch2
        pff = stoch2 if pff is None else pff + factor * (stoch2 - pff)
        stc[i] = pff
    return stc


async def schaff_trend_cycle_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """STC 조건 평가 → 표준 6-key 플러그인 결과."""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")

    fast = int(fields.get("fast", 23))
    slow = int(fields.get("slow", 50))
    cycle = int(fields.get("cycle", 10))
    lower = float(fields.get("lower", 25))
    upper = float(fields.get("upper", 75))
    direction = fields.get("direction", "long")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided", "indicator": "SchaffTrendCycle"},
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

    min_required = slow + cycle

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
                "stc": None,
                "error": f"insufficient_data: need {min_required} bars, got {len(closes)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        if max(closes) == min(closes):
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "stc": None,
                "error": "flat_series: close price is constant, STC undefined",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        stc_series = calculate_stc_series(closes, fast, slow, cycle)

        time_series: List[Dict[str, Any]] = []
        prev_stc: Optional[float] = None
        for i, stc_val in enumerate(stc_series):
            if stc_val is None:
                continue
            row = used_rows[i]
            signal = None
            side = "long"
            if prev_stc is not None:
                if prev_stc <= lower and stc_val > lower:
                    signal = "buy"
                elif prev_stc >= upper and stc_val < upper:
                    signal = "sell"
            time_series.append({
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field),
                high_field: row.get(high_field),
                low_field: row.get(low_field),
                close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "stc": sanitize(stc_val, 4),
                "signal": signal,
                "side": side,
            })
            prev_stc = stc_val

        latest_stc = None
        for i in range(len(stc_series) - 1, -1, -1):
            if stc_series[i] is not None:
                latest_stc = stc_series[i]
                break

        if latest_stc is None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "stc": None,
                "error": "stc_unavailable: double stochastic did not resolve (degenerate series)",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})
            continue

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "stc": sanitize(latest_stc, 4),
        })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        if direction == "short":
            passed_condition = latest_stc < 50.0
        else:
            passed_condition = latest_stc > 50.0
        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "SchaffTrendCycle",
            "fast": fast,
            "slow": slow,
            "cycle": cycle,
            "lower": lower,
            "upper": upper,
            "direction": direction,
        },
    }


__all__ = [
    "schaff_trend_cycle_condition",
    "calculate_stc_series",
    "SCHAFF_TREND_CYCLE_SCHEMA",
]
