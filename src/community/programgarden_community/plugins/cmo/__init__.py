"""
CMO (Chande Momentum Oscillator) 플러그인 (pure-Python, stdlib only)

CMO = 100 * (sum(up moves) - sum(down moves)) / (sum(up moves) + sum(down moves))
over a rolling ``period`` of close-to-close changes. Ranges in [-100, 100]:
readings above +threshold are overbought, below -threshold are oversold. Unlike RSI,
CMO uses the *net* momentum over the window without Wilder smoothing.

입력 형식 (ConditionNode와 통일):
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {period, threshold, direction}
- field_mapping: {close_field, date_field, symbol_field, exchange_field}

pandas-ta/numpy 미사용 — CodeNode stdlib 샌드박스에 그대로 인라인 가능.
"""

from typing import List, Dict, Any, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._ta_common import sanitize, group_by_symbol


CMO_SCHEMA = PluginSchema(
    id="CMO",
    name="CMO (Chande Momentum Oscillator)",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description=(
        "Chande Momentum Oscillator: 100 * (sum of up moves - sum of down moves) / "
        "(sum of up moves + sum of down moves) over the period. Bounded in [-100, 100]; "
        "readings below -threshold are oversold (buy), above +threshold are overbought (sell)."
    ),
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 9,
            "title": "Period",
            "description": "Number of close-to-close changes in the CMO window",
            "ge": 2,
            "le": 200,
        },
        "threshold": {
            "type": "float",
            "default": 50,
            "title": "Threshold",
            "description": "Overbought/oversold magnitude (0-100)",
            "ge": 0,
            "le": 100,
        },
        "direction": {
            "type": "string",
            "default": "oversold",
            "title": "Direction",
            "description": "oversold: buy when CMO < -threshold, overbought: sell when CMO > threshold",
            "enum": ["oversold", "overbought"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["momentum", "oscillator"],
    output_fields={
        "cmo": {"type": "float", "description": "Chande Momentum Oscillator value (-100 to 100)"},
    },
    locales={
        "ko": {
            "name": "CMO (샹데 모멘텀 오실레이터)",
            "description": (
                "샹데 모멘텀 오실레이터: 기간 내 상승폭 합과 하락폭 합의 차를 그 합으로 나눈 "
                "값(×100)입니다. [-100,100] 범위이며 -기준값 미만이면 과매도(매수), "
                "+기준값 초과이면 과매수(매도) 신호입니다."
            ),
            "fields.period": "CMO 계산에 사용할 종가 변화 개수",
            "fields.threshold": "과매수/과매도 크기 기준값 (0-100)",
            "fields.direction": "방향 (oversold: CMO<-기준값 매수, overbought: CMO>기준값 매도)",
        },
    },
)


def calculate_cmo(closes: List[float], period: int) -> Optional[float]:
    """Latest CMO over the trailing ``period`` close changes.

    Returns ``None`` when there are too few closes or the window has zero total
    movement (flat), so the caller can surface an explicit reason.
    """
    if len(closes) < period + 1:
        return None
    up = 0.0
    down = 0.0
    for i in range(len(closes) - period, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            up += diff
        else:
            down += -diff
    total = up + down
    if total == 0:
        return None
    return 100.0 * (up - down) / total


def calculate_cmo_series(closes: List[float], period: int) -> List[Optional[float]]:
    """CMO 시계열 aligned to ``closes`` (indices < ``period`` are ``None``)."""
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    if n < period + 1:
        return out
    for c in range(period, n):
        up = 0.0
        down = 0.0
        for i in range(c - period + 1, c + 1):
            diff = closes[i] - closes[i - 1]
            if diff > 0:
                up += diff
            else:
                down += -diff
        total = up + down
        out[c] = None if total == 0 else 100.0 * (up - down) / total
    return out


async def cmo_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """CMO 조건 평가 → 표준 6-key 플러그인 결과."""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")

    period = int(fields.get("period", 9))
    threshold = float(fields.get("threshold", 50))
    direction = fields.get("direction", "oversold")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided", "indicator": "CMO"},
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

    min_required = period + 1

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
                "cmo": None,
                "error": f"insufficient_data: need {min_required} bars, got {len(closes)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        if max(closes) == min(closes):
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "cmo": None,
                "error": "flat_series: close price is constant, CMO undefined (zero total movement)",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        cmo_series = calculate_cmo_series(closes, period)

        time_series: List[Dict[str, Any]] = []
        for i, cmo_val in enumerate(cmo_series):
            if cmo_val is None:
                continue
            row = used_rows[i]
            signal = None
            side = "long"
            if direction == "oversold" and cmo_val < -threshold:
                signal = "buy"
            elif direction == "overbought" and cmo_val > threshold:
                signal = "sell"
            time_series.append({
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field),
                high_field: row.get(high_field),
                low_field: row.get(low_field),
                close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "cmo": sanitize(cmo_val, 4),
                "signal": signal,
                "side": side,
            })

        latest_cmo = None
        for i in range(len(cmo_series) - 1, -1, -1):
            if cmo_series[i] is not None:
                latest_cmo = cmo_series[i]
                break

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "cmo": sanitize(latest_cmo, 4),
        })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        if latest_cmo is None:
            failed.append(sym_dict)
            continue
        if direction == "overbought":
            passed_condition = latest_cmo > threshold
        else:
            passed_condition = latest_cmo < -threshold
        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "CMO",
            "period": period,
            "threshold": threshold,
            "direction": direction,
        },
    }


__all__ = [
    "cmo_condition",
    "calculate_cmo",
    "calculate_cmo_series",
    "CMO_SCHEMA",
]
