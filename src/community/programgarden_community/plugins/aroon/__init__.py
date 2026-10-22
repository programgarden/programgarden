"""
Aroon (아룬) 플러그인

추세 방향과 강도를 감지하는 지표.
Aroon Up은 최고가까지 경과일, Aroon Down은 최저가까지 경과일을 측정.
100에 가까울수록 강한 추세를 나타냅니다.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, ...}, ...]
- fields: {period, signal_type, threshold}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


AROON_SCHEMA = PluginSchema(
    id="Aroon",
    name="Aroon",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Aroon indicator identifies trend direction and strength. Aroon Up measures time since highest high, Aroon Down measures time since lowest low. Values near 100 indicate strong trends.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 25,
            "title": "Period",
            "description": "Aroon calculation period",
            "ge": 5,
            "le": 100,
        },
        "signal_type": {
            "type": "string",
            "default": "uptrend",
            "title": "Signal Type",
            "description": "Type of Aroon signal",
            "enum": ["uptrend", "downtrend", "cross_up", "cross_down"],
        },
        "threshold": {
            "type": "float",
            "default": 70.0,
            "title": "Threshold",
            "description": "Trend strength threshold",
            "ge": 50,
            "le": 100,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low"],
    optional_fields=["close", "open", "volume"],
    tags=["aroon", "trend", "direction", "strength"],
    output_fields={
        "aroon_up": {"type": "float", "description": "Aroon Up value (0-100)"},
        "aroon_down": {"type": "float", "description": "Aroon Down value (0-100)"},
        "aroon_oscillator": {"type": "float", "description": "Aroon Oscillator (Up - Down, -100 to 100)"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "아룬",
            "description": "아룬 지표는 추세 방향과 강도를 감지합니다. Aroon Up은 최고가까지 경과일, Aroon Down은 최저가까지 경과일을 측정합니다. 100에 가까울수록 강한 추세입니다.",
            "fields.period": "아룬 계산 기간",
            "fields.signal_type": "신호 유형 (상승추세, 하락추세, 상향돌파, 하향돌파)",
            "fields.threshold": "추세 강도 기준값",
        },
    },
)


def calculate_aroon(
    highs: List[float],
    lows: List[float],
    period: int = 25,
) -> List[Dict[str, float]]:
    """Aroon Up/Down/Oscillator 시계열 계산

    Returns:
        list of dict: {aroon_up, aroon_down, aroon_oscillator}
    """
    n = len(highs)
    if n != len(lows) or n < period + 1:
        return []

    result = []

    for i in range(n):
        if i < period:
            result.append({"aroon_up": 50.0, "aroon_down": 50.0, "aroon_oscillator": 0.0})
            continue

        window_highs = highs[i - period : i + 1]
        window_lows = lows[i - period : i + 1]

        # 최고가/최저가가 가장 최근인 인덱스 (뒤에서부터 찾기)
        max_val = max(window_highs)
        min_val = min(window_lows)

        # 가장 최근의 최고가 위치
        bars_since_high = period
        for j in range(period, -1, -1):
            if window_highs[j] == max_val:
                bars_since_high = period - j
                break

        bars_since_low = period
        for j in range(period, -1, -1):
            if window_lows[j] == min_val:
                bars_since_low = period - j
                break

        aroon_up = round((period - bars_since_high) / period * 100.0, 2)
        aroon_down = round((period - bars_since_low) / period * 100.0, 2)
        aroon_osc = round(aroon_up - aroon_down, 2)

        result.append({
            "aroon_up": aroon_up,
            "aroon_down": aroon_down,
            "aroon_oscillator": aroon_osc,
        })

    return result


async def aroon_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Aroon 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    period = fields.get("period", 25)
    signal_type = fields.get("signal_type", "uptrend")
    threshold = fields.get("threshold", 70.0)

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
        target_symbols = [
            {"symbol": s.get("symbol", "") if isinstance(s, dict) else str(s),
             "exchange": s.get("exchange", "UNKNOWN") if isinstance(s, dict) else "UNKNOWN"}
            for s in symbols
        ]
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
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "aroon_up": None, "aroon_down": None,
                "aroon_oscillator": None, "current_price": None,
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        highs, lows, closes = [], [], []
        for row in rows_sorted:
            try:
                highs.append(float(row.get(high_field, 0)))
                lows.append(float(row.get(low_field, 0)))
                closes.append(float(row.get(close_field, row.get(high_field, 0))))
            except (ValueError, TypeError):
                highs.append(0.0)
                lows.append(0.0)
                closes.append(0.0)

        current_price = closes[-1] if closes else None

        aroon_series = calculate_aroon(highs, lows, period)

        aroon_up_val = aroon_series[-1]["aroon_up"] if aroon_series else None
        aroon_down_val = aroon_series[-1]["aroon_down"] if aroon_series else None
        aroon_osc_val = aroon_series[-1]["aroon_oscillator"] if aroon_series else None

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "aroon_up": aroon_up_val, "aroon_down": aroon_down_val,
            "aroon_oscillator": aroon_osc_val, "current_price": current_price,
        })

        ts = []
        for i, row in enumerate(rows_sorted):
            if i < len(aroon_series):
                ts.append({
                    date_field: row.get(date_field, ""),
                    open_field: row.get(open_field),
                    high_field: row.get(high_field),
                    low_field: row.get(low_field),
                    close_field: row.get(close_field),
                    volume_field: row.get(volume_field),
                    "aroon_up": aroon_series[i]["aroon_up"],
                    "aroon_down": aroon_series[i]["aroon_down"],
                    "aroon_oscillator": aroon_series[i]["aroon_oscillator"],
                })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": ts})

        # 조건 평가
        condition_met = False
        if aroon_series and len(aroon_series) >= 2:
            curr = aroon_series[-1]
            prev = aroon_series[-2]

            if signal_type == "uptrend":
                condition_met = curr["aroon_up"] > threshold and curr["aroon_down"] < (100 - threshold)
            elif signal_type == "downtrend":
                condition_met = curr["aroon_down"] > threshold and curr["aroon_up"] < (100 - threshold)
            elif signal_type == "cross_up":
                condition_met = prev["aroon_up"] <= prev["aroon_down"] and curr["aroon_up"] > curr["aroon_down"]
            elif signal_type == "cross_down":
                condition_met = prev["aroon_down"] <= prev["aroon_up"] and curr["aroon_down"] > curr["aroon_up"]

        (passed if condition_met else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "Aroon",
            "period": period,
            "signal_type": signal_type,
            "threshold": threshold,
        },
    }


__all__ = ["aroon_condition", "calculate_aroon", "AROON_SCHEMA"]
