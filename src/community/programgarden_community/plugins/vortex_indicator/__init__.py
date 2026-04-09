"""
VortexIndicator (보텍스 지표) 플러그인

+VI/-VI 크로스로 추세 방향을 판단합니다.
+VI > -VI → 상승 추세, 반대 → 하락 추세.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {period, signal_type}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


VORTEX_INDICATOR_SCHEMA = PluginSchema(
    id="VortexIndicator",
    name="Vortex Indicator",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Vortex Indicator identifies trend direction using +VI and -VI lines. Bullish when +VI crosses above -VI, bearish when -VI crosses above +VI.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 14,
            "title": "Period",
            "description": "Vortex calculation period",
            "ge": 5,
            "le": 100,
        },
        "signal_type": {
            "type": "string",
            "default": "bullish_cross",
            "title": "Signal Type",
            "description": "Type of Vortex signal",
            "enum": ["bullish_cross", "bearish_cross", "bullish_trend", "bearish_trend"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    optional_fields=["open", "volume"],
    tags=["vortex", "trend", "direction"],
    output_fields={
        "plus_vi": {"type": "float", "description": "+VI (positive vortex indicator)"},
        "minus_vi": {"type": "float", "description": "-VI (negative vortex indicator)"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "보텍스 지표",
            "description": "+VI/-VI 크로스로 추세 방향을 판단합니다. +VI가 -VI를 상향 돌파하면 상승 추세, 반대면 하락 추세입니다.",
            "fields.period": "보텍스 계산 기간",
            "fields.signal_type": "신호 유형 (상승 크로스, 하락 크로스, 상승 추세, 하락 추세)",
        },
    },
)


def calculate_vortex(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> List[Dict[str, Optional[float]]]:
    """Vortex Indicator 시계열 계산"""
    n = len(closes)
    if n < 2 or n != len(highs) or n != len(lows):
        return []

    plus_vm_list = []
    minus_vm_list = []
    tr_list = []

    result = [{"plus_vi": None, "minus_vi": None}]

    for i in range(1, n):
        plus_vm = abs(highs[i] - lows[i - 1])
        minus_vm = abs(lows[i] - highs[i - 1])
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        plus_vm_list.append(plus_vm)
        minus_vm_list.append(minus_vm)
        tr_list.append(max(tr, 1e-10))

        if len(plus_vm_list) < period:
            result.append({"plus_vi": None, "minus_vi": None})
        else:
            sum_plus_vm = sum(plus_vm_list[-period:])
            sum_minus_vm = sum(minus_vm_list[-period:])
            sum_tr = sum(tr_list[-period:])
            result.append({
                "plus_vi": round(sum_plus_vm / sum_tr, 4),
                "minus_vi": round(sum_minus_vm / sum_tr, 4),
            })

    return result


async def vortex_indicator_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Vortex Indicator 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    volume_field = mapping.get("volume_field", "volume")

    period = fields.get("period", 14)
    signal_type = fields.get("signal_type", "bullish_cross")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False, "analysis": {"error": "No data provided"},
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

    passed, failed, symbol_results, values = [], [], [], []

    for sym_info in target_symbols:
        symbol, exchange = sym_info["symbol"], sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}
        rows = symbol_data_map.get(symbol, [])

        if not rows:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "plus_vi": None, "minus_vi": None, "current_price": None})
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
                highs.append(0.0); lows.append(0.0); closes.append(0.0)

        current_price = closes[-1] if closes else None
        vi_series = calculate_vortex(highs, lows, closes, period)

        plus_vi = None
        minus_vi = None
        for v in reversed(vi_series):
            if v["plus_vi"] is not None:
                plus_vi = v["plus_vi"]
                minus_vi = v["minus_vi"]
                break

        symbol_results.append({"symbol": symbol, "exchange": exchange, "plus_vi": plus_vi, "minus_vi": minus_vi, "current_price": current_price})

        ts = []
        for i, row in enumerate(rows_sorted):
            if i < len(vi_series) and vi_series[i]["plus_vi"] is not None:
                ts.append({
                    date_field: row.get(date_field, ""),
                    close_field: row.get(close_field),
                    volume_field: row.get(volume_field),
                    "plus_vi": vi_series[i]["plus_vi"],
                    "minus_vi": vi_series[i]["minus_vi"],
                })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": ts})

        condition_met = False
        if vi_series and len(vi_series) >= 2:
            curr = vi_series[-1]
            prev = vi_series[-2]
            if curr["plus_vi"] is not None and prev["plus_vi"] is not None:
                if signal_type == "bullish_cross":
                    condition_met = prev["plus_vi"] <= prev["minus_vi"] and curr["plus_vi"] > curr["minus_vi"]
                elif signal_type == "bearish_cross":
                    condition_met = prev["minus_vi"] <= prev["plus_vi"] and curr["minus_vi"] > curr["plus_vi"]
                elif signal_type == "bullish_trend":
                    condition_met = curr["plus_vi"] > curr["minus_vi"]
                elif signal_type == "bearish_trend":
                    condition_met = curr["minus_vi"] > curr["plus_vi"]

        (passed if condition_met else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "VortexIndicator", "period": period, "signal_type": signal_type},
    }


__all__ = ["vortex_indicator_condition", "calculate_vortex", "VORTEX_INDICATOR_SCHEMA"]
