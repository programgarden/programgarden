"""
Williams %R (윌리엄스 %R) 플러그인

Stochastic과 유사하나 역전된 스케일(-100~0). -80 이하 과매도, -20 이상 과매수.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {period, threshold, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


WILLIAMS_R_SCHEMA = PluginSchema(
    id="WilliamsR",
    name="Williams %R",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Williams %R oscillator with inverted scale (-100 to 0). Below -80 indicates oversold, above -20 indicates overbought. Similar to Stochastic but inverted.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 14,
            "title": "Period",
            "description": "Lookback period",
            "ge": 2,
            "le": 100,
        },
        "threshold": {
            "type": "float",
            "default": -80,
            "title": "Threshold",
            "description": "Oversold threshold (overbought = threshold + 100, e.g. -80 → -20)",
            "ge": -99,
            "le": -1,
        },
        "direction": {
            "type": "string",
            "default": "oversold",
            "title": "Direction",
            "description": "oversold: buy signal, overbought: sell signal",
            "enum": ["oversold", "overbought"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["open", "volume"],
    tags=["momentum", "oscillator", "williams"],
    locales={
        "ko": {
            "name": "윌리엄스 %R",
            "description": "역전된 스케일(-100~0)의 오실레이터입니다. -80 이하 과매도(매수 신호), -20 이상 과매수(매도 신호)입니다.",
            "fields.period": "계산 기간",
            "fields.threshold": "과매도 기준값 (과매수 = 기준값 + 100)",
            "fields.direction": "방향 (oversold: 매수, overbought: 매도)",
        },
    },
)


def calculate_williams_r(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> Optional[float]:
    """
    Williams %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
    """
    if len(highs) < period or len(lows) < period or len(closes) < period:
        return None

    highest = max(highs[-period:])
    lowest = min(lows[-period:])

    if highest == lowest:
        return -50.0

    wr = (highest - closes[-1]) / (highest - lowest) * -100
    return round(wr, 2)


def calculate_williams_r_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> List[Dict[str, float]]:
    """Williams %R 시계열 계산"""
    if len(highs) < period:
        return []

    results = []
    for i in range(period, len(highs) + 1):
        wr = calculate_williams_r(highs[:i], lows[:i], closes[:i], period)
        if wr is not None:
            results.append({"williams_r": wr})

    return results


async def williams_r_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Williams %R 조건 평가"""
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    period = fields.get("period", 14)
    threshold = fields.get("threshold", -80)
    direction = fields.get("direction", "oversold")

    overbought_threshold = threshold + 100  # -80 → -20

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
        }

    symbol_data_map: Dict[str, List[Dict]] = {}
    symbol_exchange_map: Dict[str, str] = {}

    for row in data:
        if not isinstance(row, dict):
            continue
        sym = row.get(symbol_field, "")
        if not sym:
            continue
        if sym not in symbol_data_map:
            symbol_data_map[sym] = []
            symbol_exchange_map[sym] = row.get(exchange_field, "UNKNOWN")
        symbol_data_map[sym].append(row)

    if symbols:
        target_symbols = []
        for s in symbols:
            if isinstance(s, dict):
                target_symbols.append({"symbol": s.get("symbol", ""), "exchange": s.get("exchange", "UNKNOWN")})
            else:
                target_symbols.append({"symbol": str(s), "exchange": "UNKNOWN"})
    else:
        target_symbols = [
            {"symbol": sym, "exchange": symbol_exchange_map.get(sym, "UNKNOWN")}
            for sym in symbol_data_map.keys()
        ]

    passed = []
    failed = []
    symbol_results = []
    values = []

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "williams_r": None, "error": "No data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        highs, lows, closes = [], [], []
        for row in rows_sorted:
            try:
                highs.append(float(row.get(high_field, 0)))
                lows.append(float(row.get(low_field, 0)))
                closes.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                pass

        if len(highs) < period:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange, "williams_r": None,
                "error": f"Insufficient data: need {period}, got {len(highs)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        wr_series = calculate_williams_r_series(highs, lows, closes, period)

        if not wr_series:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "williams_r": None, "error": "Calculation failed"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        start_idx = period - 1
        time_series = []

        for i, wr_val in enumerate(wr_series):
            row_idx = start_idx + i
            if row_idx >= len(rows_sorted):
                break
            original_row = rows_sorted[row_idx]

            signal = None
            side = "long"
            if wr_val["williams_r"] <= threshold:
                signal = "buy"
            elif wr_val["williams_r"] >= overbought_threshold:
                signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "williams_r": wr_val["williams_r"],
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        current_wr = wr_series[-1]["williams_r"]
        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "williams_r": current_wr,
        })

        if direction == "oversold":
            passed_condition = current_wr <= threshold
        else:
            passed_condition = current_wr >= overbought_threshold

        if passed_condition:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "WilliamsR",
            "period": period,
            "threshold": threshold,
            "direction": direction,
        },
    }


__all__ = ["williams_r_condition", "calculate_williams_r", "calculate_williams_r_series", "WILLIAMS_R_SCHEMA"]
