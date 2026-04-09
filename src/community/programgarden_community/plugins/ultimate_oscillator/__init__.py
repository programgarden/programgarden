"""
UltimateOscillator (얼티밋 오실레이터) 플러그인

Larry Williams의 3기간(7,14,28) 가중 오실레이터.
다중 기간의 매수 압력을 종합하여 허위 신호를 줄입니다.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {period1, period2, period3, overbought, oversold, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


ULTIMATE_OSCILLATOR_SCHEMA = PluginSchema(
    id="UltimateOscillator",
    name="Ultimate Oscillator",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Larry Williams' Ultimate Oscillator combines three timeframes (7, 14, 28) into a single weighted oscillator. Reduces false signals by considering buying pressure across multiple periods.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period1": {
            "type": "int",
            "default": 7,
            "title": "Short Period",
            "description": "Short-term period",
            "ge": 2,
            "le": 50,
        },
        "period2": {
            "type": "int",
            "default": 14,
            "title": "Medium Period",
            "description": "Medium-term period",
            "ge": 5,
            "le": 100,
        },
        "period3": {
            "type": "int",
            "default": 28,
            "title": "Long Period",
            "description": "Long-term period",
            "ge": 10,
            "le": 200,
        },
        "overbought": {
            "type": "float",
            "default": 70.0,
            "title": "Overbought Level",
            "description": "Overbought threshold",
            "ge": 50,
            "le": 90,
        },
        "oversold": {
            "type": "float",
            "default": 30.0,
            "title": "Oversold Level",
            "description": "Oversold threshold",
            "ge": 10,
            "le": 50,
        },
        "direction": {
            "type": "string",
            "default": "below",
            "title": "Direction",
            "description": "below: oversold signal, above: overbought signal",
            "enum": ["below", "above"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["open", "volume"],
    tags=["oscillator", "momentum", "multi-timeframe", "larry-williams"],
    output_fields={
        "uo": {"type": "float", "description": "Ultimate Oscillator value (0-100)"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "얼티밋 오실레이터",
            "description": "Larry Williams의 3기간(7,14,28) 가중 오실레이터입니다. 다중 기간의 매수 압력을 종합하여 허위 신호를 줄입니다.",
            "fields.period1": "단기 기간",
            "fields.period2": "중기 기간",
            "fields.period3": "장기 기간",
            "fields.overbought": "과매수 기준선",
            "fields.oversold": "과매도 기준선",
            "fields.direction": "방향 (below: 과매도, above: 과매수)",
        },
    },
)


def calculate_ultimate_oscillator(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period1: int = 7,
    period2: int = 14,
    period3: int = 28,
) -> List[Optional[float]]:
    """Ultimate Oscillator 시계열 계산

    Returns:
        UO 값 리스트 (첫 period3개는 None)
    """
    n = len(closes)
    if n < 2 or n != len(highs) or n != len(lows):
        return []

    bp_list = []
    tr_list = []

    for i in range(1, n):
        prev_close = closes[i - 1]
        bp = closes[i] - min(lows[i], prev_close)
        tr = max(highs[i], prev_close) - min(lows[i], prev_close)
        bp_list.append(bp)
        tr_list.append(max(tr, 1e-10))

    result = [None]  # 첫 번째 값은 계산 불가

    for i in range(len(bp_list)):
        if i + 1 < period3:
            result.append(None)
            continue

        bp_sum1 = sum(bp_list[i + 1 - period1 : i + 1])
        tr_sum1 = sum(tr_list[i + 1 - period1 : i + 1])
        bp_sum2 = sum(bp_list[i + 1 - period2 : i + 1])
        tr_sum2 = sum(tr_list[i + 1 - period2 : i + 1])
        bp_sum3 = sum(bp_list[i + 1 - period3 : i + 1])
        tr_sum3 = sum(tr_list[i + 1 - period3 : i + 1])

        avg1 = bp_sum1 / max(tr_sum1, 1e-10)
        avg2 = bp_sum2 / max(tr_sum2, 1e-10)
        avg3 = bp_sum3 / max(tr_sum3, 1e-10)

        uo = 100.0 * (4 * avg1 + 2 * avg2 + avg3) / 7.0
        result.append(round(max(0.0, min(100.0, uo)), 2))

    return result


async def ultimate_oscillator_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Ultimate Oscillator 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    period1 = fields.get("period1", 7)
    period2 = fields.get("period2", 14)
    period3 = fields.get("period3", 28)
    overbought = fields.get("overbought", 70.0)
    oversold = fields.get("oversold", 30.0)
    direction = fields.get("direction", "below")

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
                "uo": None, "current_price": None,
            })
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
                highs.append(0.0)
                lows.append(0.0)
                closes.append(0.0)

        current_price = closes[-1] if closes else None

        uo_series = calculate_ultimate_oscillator(highs, lows, closes, period1, period2, period3)
        uo_value = None
        for v in reversed(uo_series):
            if v is not None:
                uo_value = v
                break

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "uo": uo_value, "current_price": current_price,
        })

        ts = []
        for i, row in enumerate(rows_sorted):
            if i < len(uo_series) and uo_series[i] is not None:
                signal = None
                side = "long"
                if direction == "below" and uo_series[i] < oversold:
                    signal = "buy"
                elif direction == "above" and uo_series[i] > overbought:
                    signal = "sell"
                ts.append({
                    date_field: row.get(date_field, ""),
                    open_field: row.get(open_field),
                    high_field: row.get(high_field),
                    low_field: row.get(low_field),
                    close_field: row.get(close_field),
                    volume_field: row.get(volume_field),
                    "uo": uo_series[i],
                    "signal": signal,
                    "side": side,
                })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": ts})

        if uo_value is not None:
            if direction == "below":
                cond = uo_value < oversold
            else:
                cond = uo_value > overbought
            (passed if cond else failed).append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "UltimateOscillator",
            "period1": period1,
            "period2": period2,
            "period3": period3,
            "overbought": overbought,
            "oversold": oversold,
            "direction": direction,
            "comparison": f"UO {'<' if direction == 'below' else '>'} {oversold if direction == 'below' else overbought}",
        },
    }


__all__ = [
    "ultimate_oscillator_condition",
    "calculate_ultimate_oscillator",
    "ULTIMATE_OSCILLATOR_SCHEMA",
]
