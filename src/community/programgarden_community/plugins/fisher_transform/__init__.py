"""
Fisher Transform 플러그인 (pure-Python, stdlib only)

Ehlers' Fisher Transform converts the (high+low)/2 median price into a Gaussian-like
oscillator. The median is normalized to [-1, 1] over a lookback window, lightly
smoothed, clamped to avoid the ``ln`` domain edge, then passed through
``0.5 * ln((1 + x) / (1 - x))`` with a recursive 0.5 smoothing. Sharp turning points
in the transformed series lead price reversals.

입력 형식 (ConditionNode와 통일):
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {lookback, direction}
- field_mapping: {high_field, low_field, close_field, date_field, symbol_field, exchange_field}

pandas-ta/numpy 미사용 — CodeNode stdlib 샌드박스에 그대로 인라인 가능.
"""

import math
from typing import List, Dict, Any, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._ta_common import sanitize, group_by_symbol


FISHER_TRANSFORM_SCHEMA = PluginSchema(
    id="FisherTransform",
    name="Fisher Transform",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description=(
        "Ehlers' Fisher Transform of the (high+low)/2 median price. Normalizes price "
        "to [-1, 1] over a lookback, then applies 0.5*ln((1+x)/(1-x)) with recursive "
        "smoothing to sharpen turning points. Bullish when the Fisher line crosses "
        "above zero, bearish when it crosses below."
    ),
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 9,
            "title": "Lookback",
            "description": "Window used to normalize the median price",
            "ge": 2,
            "le": 200,
        },
        "direction": {
            "type": "string",
            "default": "long",
            "title": "Direction",
            "description": "long: pass when Fisher > 0 (bullish), short: pass when Fisher < 0 (bearish)",
            "enum": ["long", "short"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low"],
    optional_fields=["close", "open", "volume"],
    tags=["momentum", "oscillator", "reversal"],
    output_fields={
        "fisher": {"type": "float", "description": "Fisher Transform value (unbounded, centered on 0)"},
        "trigger": {"type": "float", "description": "Trigger line — Fisher value lagged by one bar"},
    },
    locales={
        "ko": {
            "name": "피셔 변환",
            "description": (
                "고저 중앙값((고가+저가)/2)을 되돌림 구간에서 [-1,1]로 정규화한 뒤 "
                "0.5*ln((1+x)/(1-x)) 재귀 평활화로 전환점을 뾰족하게 만드는 오실레이터입니다. "
                "피셔선이 0을 상향 돌파하면 매수, 하향 돌파하면 매도 신호입니다."
            ),
            "fields.lookback": "중앙값 정규화에 사용할 되돌림 구간",
            "fields.direction": "방향 (long: 피셔>0 통과, short: 피셔<0 통과)",
        },
    },
)


def calculate_fisher_series(medians: List[float], lookback: int) -> List[Optional[float]]:
    """Fisher Transform 시계열.

    Returns a full-length list aligned to ``medians``; warmup indices
    (< ``lookback`` - 1) are ``None``. Flat windows (max == min) normalize to the
    neutral midpoint (x = 0) rather than dividing by zero.
    """
    n = len(medians)
    fishers: List[Optional[float]] = [None] * n
    val_prev = 0.0
    fish_prev = 0.0
    for i in range(n):
        if i < lookback - 1:
            continue
        window = medians[i - lookback + 1 : i + 1]
        hi = max(window)
        lo = min(window)
        if hi == lo:
            x = 0.0
        else:
            raw = (medians[i] - lo) / (hi - lo)  # 0..1
            x = 2.0 * raw - 1.0  # -1..1
        val = 0.33 * x + 0.67 * val_prev
        # clamp to avoid ln domain error at +-1
        val = max(min(val, 0.999), -0.999)
        fish = 0.5 * math.log((1.0 + val) / (1.0 - val)) + 0.5 * fish_prev
        val_prev = val
        fish_prev = fish
        fishers[i] = fish
    return fishers


async def fisher_transform_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """Fisher Transform 조건 평가.

    Returns the standard 6-key plugin dict: passed_symbols / failed_symbols /
    symbol_results / values / result / analysis. Insufficient or flat series are
    reported with an explicit ``error`` reason (no silent drop).
    """
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    lookback = int(fields.get("lookback", 9))
    direction = fields.get("direction", "long")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided", "indicator": "FisherTransform"},
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

    min_required = lookback + 1

    for group in groups:
        symbol = group["symbol"]
        exchange = group["exchange"]
        rows_sorted = group["rows"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        medians: List[float] = []
        used_rows: List[Dict[str, Any]] = []
        for row in rows_sorted:
            h = row.get(high_field)
            low_v = row.get(low_field)
            if h is None or low_v is None:
                continue
            try:
                medians.append((float(h) + float(low_v)) / 2.0)
                used_rows.append(row)
            except (TypeError, ValueError):
                continue

        if len(medians) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "fisher": None,
                "trigger": None,
                "error": f"insufficient_data: need {min_required} bars, got {len(medians)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        if max(medians) == min(medians):
            # Constant price → Fisher is undefined/degenerate. Report explicitly.
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "fisher": None,
                "trigger": None,
                "error": "flat_series: median price is constant, Fisher Transform undefined",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        fishers = calculate_fisher_series(medians, lookback)

        time_series: List[Dict[str, Any]] = []
        prev_fish: Optional[float] = None
        for i, fish in enumerate(fishers):
            if fish is None:
                continue
            row = used_rows[i]
            signal = None
            side = "long"
            if prev_fish is not None:
                if prev_fish <= 0.0 and fish > 0.0:
                    signal = "buy"
                elif prev_fish >= 0.0 and fish < 0.0:
                    signal = "sell"
            time_series.append({
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field),
                high_field: row.get(high_field),
                low_field: row.get(low_field),
                close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "fisher": sanitize(fish),
                "trigger": sanitize(prev_fish),
                "signal": signal,
                "side": side,
            })
            prev_fish = fish

        latest_fisher = None
        latest_trigger = None
        for i in range(len(fishers) - 1, -1, -1):
            if fishers[i] is not None:
                latest_fisher = fishers[i]
                for j in range(i - 1, -1, -1):
                    if fishers[j] is not None:
                        latest_trigger = fishers[j]
                        break
                break

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "fisher": sanitize(latest_fisher),
            "trigger": sanitize(latest_trigger),
        })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        if latest_fisher is None:
            failed.append(sym_dict)
            continue
        if direction == "short":
            passed_condition = latest_fisher < 0.0
        else:
            passed_condition = latest_fisher > 0.0
        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "FisherTransform",
            "lookback": lookback,
            "direction": direction,
        },
    }


__all__ = [
    "fisher_transform_condition",
    "calculate_fisher_series",
    "FISHER_TRANSFORM_SCHEMA",
]
