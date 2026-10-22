"""
CCI (Commodity Channel Index, 상품채널지수) 플러그인

전형적인 가격(TP)의 이동평균으로부터의 편차. +100 이상 과매수, -100 이하 과매도.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {period, threshold, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


CCI_SCHEMA = PluginSchema(
    id="CCI",
    name="Commodity Channel Index",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Measures price deviation from its statistical mean using Typical Price. Above +100 indicates overbought, below -100 indicates oversold. Popular for futures trading.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 20,
            "title": "Period",
            "description": "CCI calculation period",
            "ge": 2,
            "le": 200,
        },
        "threshold": {
            "type": "float",
            "default": 100,
            "title": "Threshold",
            "description": "Overbought/oversold threshold",
            "ge": 50,
            "le": 300,
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
    tags=["momentum", "oscillator", "cci", "futures"],
    output_fields={
        "cci": {"type": "float", "description": "CCI value (above +100 overbought, below -100 oversold)"},
        "typical_price": {"type": "float", "description": "Typical price (High + Low + Close) / 3"},
    },
    locales={
        "ko": {
            "name": "상품채널지수 (CCI)",
            "description": "전형적인 가격(TP)의 이동평균으로부터의 편차를 측정합니다. +100 이상 과매수, -100 이하 과매도입니다. 선물 트레이더의 핵심 지표입니다.",
            "fields.period": "CCI 계산 기간",
            "fields.threshold": "과매수/과매도 기준값",
            "fields.direction": "방향 (oversold: 매수, overbought: 매도)",
        },
    },
)


def calculate_cci(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 20,
) -> Optional[float]:
    """
    CCI = (TP - SMA(TP)) / (0.015 * Mean Deviation)
    TP = (High + Low + Close) / 3
    """
    if len(highs) < period or len(lows) < period or len(closes) < period:
        return None

    tp_values = []
    for i in range(len(highs)):
        tp = (highs[i] + lows[i] + closes[i]) / 3
        tp_values.append(tp)

    recent_tp = tp_values[-period:]
    tp_mean = sum(recent_tp) / period

    # Mean Deviation
    mean_dev = sum(abs(tp - tp_mean) for tp in recent_tp) / period

    if mean_dev == 0:
        return 0.0

    cci = (recent_tp[-1] - tp_mean) / (0.015 * mean_dev)
    return round(cci, 2)


def calculate_cci_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 20,
) -> List[Dict[str, Any]]:
    """CCI 시계열 계산"""
    if len(highs) < period:
        return []

    results = []
    for i in range(period, len(highs) + 1):
        cci = calculate_cci(highs[:i], lows[:i], closes[:i], period)
        tp = (highs[i - 1] + lows[i - 1] + closes[i - 1]) / 3
        if cci is not None:
            results.append({"cci": cci, "typical_price": round(tp, 4)})

    return results


async def cci_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """CCI 조건 평가"""
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    period = fields.get("period", 20)
    threshold = fields.get("threshold", 100)
    direction = fields.get("direction", "oversold")

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
            symbol_results.append({"symbol": symbol, "exchange": exchange, "cci": None, "error": "No data"})
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
                "symbol": symbol, "exchange": exchange, "cci": None,
                "error": f"Insufficient data: need {period}, got {len(highs)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        cci_series = calculate_cci_series(highs, lows, closes, period)

        if not cci_series:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "cci": None, "error": "Calculation failed"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        start_idx = period - 1
        time_series = []

        for i, cci_val in enumerate(cci_series):
            row_idx = start_idx + i
            if row_idx >= len(rows_sorted):
                break
            original_row = rows_sorted[row_idx]

            signal = None
            side = "long"
            if cci_val["cci"] <= -threshold:
                signal = "buy"
            elif cci_val["cci"] >= threshold:
                signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "cci": cci_val["cci"],
                "typical_price": cci_val["typical_price"],
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        current_cci = cci_series[-1]["cci"]
        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "cci": current_cci,
            "typical_price": cci_series[-1]["typical_price"],
        })

        if direction == "oversold":
            passed_condition = current_cci <= -threshold
        else:
            passed_condition = current_cci >= threshold

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
            "indicator": "CCI",
            "period": period,
            "threshold": threshold,
            "direction": direction,
        },
    }


__all__ = ["cci_condition", "calculate_cci", "calculate_cci_series", "CCI_SCHEMA"]
