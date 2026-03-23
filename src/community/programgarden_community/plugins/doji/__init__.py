"""
Doji (도지) 플러그인

시가와 종가가 거의 같은 십자형 캔들. 추세 전환 경고 신호.
- standard: 일반 도지 (십자형)
- long_legged: 장다리 도지 (긴 위아래 꼬리)
- dragonfly: 잠자리 도지 (긴 아래꼬리, 위꼬리 없음)
- gravestone: 비석 도지 (긴 위꼬리, 아래꼬리 없음)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, open, high, low, close, ...}, ...]
- fields: {doji_type, body_threshold}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


DOJI_SCHEMA = PluginSchema(
    id="Doji",
    name="Doji",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Identifies doji candlestick patterns where open and close are nearly equal. Signals market indecision and potential trend reversal. Supports standard, long-legged, dragonfly, and gravestone variants.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "doji_type": {
            "type": "string",
            "default": "standard",
            "title": "Doji Type",
            "description": "Type of doji pattern",
            "enum": ["standard", "long_legged", "dragonfly", "gravestone"],
        },
        "body_threshold": {
            "type": "float",
            "default": 0.1,
            "title": "Body Threshold",
            "description": "Maximum body/range ratio to qualify as doji (10%)",
            "ge": 0.01,
            "le": 0.3,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "open", "high", "low", "close"],
    optional_fields=["volume"],
    tags=["candlestick", "pattern", "doji", "reversal", "indecision"],
    output_fields={
        "pattern_detected": {"type": "bool", "description": "Whether the doji pattern was detected on the latest candle"},
        "doji_type": {"type": "str", "description": "Doji variant: 'standard', 'long_legged', 'dragonfly', or 'gravestone'"},
        "body_ratio": {"type": "float", "description": "Body-to-range ratio of the candle"},
        "confidence": {"type": "float", "description": "Pattern confidence score (0.0–1.0)"},
    },
    locales={
        "ko": {
            "name": "도지",
            "description": "시가와 종가가 거의 같은 십자형 캔들입니다. 시장 불확실성과 추세 전환 가능성을 나타냅니다. 일반, 장다리, 잠자리, 비석 도지를 지원합니다.",
            "fields.doji_type": "도지 유형 (standard, long_legged, dragonfly, gravestone)",
            "fields.body_threshold": "최대 몸통/전체범위 비율 (도지 기준)",
        },
    },
)


def detect_doji(candle: Dict[str, float], body_threshold: float = 0.1) -> Dict[str, Any]:
    """도지 감지 및 유형 분류"""
    o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
    total_range = h - l
    if total_range <= 0:
        return {"detected": False, "doji_type": None, "body_ratio": 0, "confidence": 0}

    body = abs(c - o)
    body_ratio = body / total_range

    if body_ratio > body_threshold:
        return {"detected": False, "doji_type": None, "body_ratio": round(body_ratio, 4), "confidence": 0}

    body_mid = (max(o, c) + min(o, c)) / 2
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - l

    # 유형 분류
    upper_pct = upper_shadow / total_range
    lower_pct = lower_shadow / total_range

    if lower_pct > 0.4 and upper_pct < 0.15:
        doji_type = "dragonfly"
    elif upper_pct > 0.4 and lower_pct < 0.15:
        doji_type = "gravestone"
    elif upper_pct > 0.35 and lower_pct > 0.35:
        doji_type = "long_legged"
    else:
        doji_type = "standard"

    confidence = 1.0 - (body_ratio / body_threshold)
    return {
        "detected": True,
        "doji_type": doji_type,
        "body_ratio": round(body_ratio, 4),
        "confidence": round(max(confidence, 0.1), 2),
    }


async def doji_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Doji 조건 평가"""
    mapping = field_mapping or {}
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    volume_field = mapping.get("volume_field", "volume")

    doji_type = fields.get("doji_type", "standard")
    body_threshold = fields.get("body_threshold", 0.1)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [], "symbol_results": [],
            "values": [], "result": False, "analysis": {"error": "No data provided"},
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
            {"symbol": s.get("symbol", ""), "exchange": s.get("exchange", "UNKNOWN")} if isinstance(s, dict)
            else {"symbol": str(s), "exchange": "UNKNOWN"} for s in symbols
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
            symbol_results.append({"symbol": symbol, "exchange": exchange, "pattern_detected": False, "error": "No data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        time_series = []

        for row in rows_sorted:
            try:
                candle = {
                    "open": float(row.get(open_field, 0)), "high": float(row.get(high_field, 0)),
                    "low": float(row.get(low_field, 0)), "close": float(row.get(close_field, 0)),
                }
            except (ValueError, TypeError):
                continue

            result = detect_doji(candle, body_threshold)
            signal = None
            if result["detected"] and (doji_type == "standard" or result["doji_type"] == doji_type):
                signal = "caution"

            time_series.append({
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field), high_field: row.get(high_field),
                low_field: row.get(low_field), close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "pattern_detected": result["detected"] and (doji_type == "standard" or result["doji_type"] == doji_type),
                "doji_type": result["doji_type"],
                "body_ratio": result["body_ratio"],
                "confidence": result["confidence"],
                "signal": signal,
                "side": "long",
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        # 마지막 캔들 결과
        if rows_sorted:
            try:
                last_candle = {
                    "open": float(rows_sorted[-1].get(open_field, 0)),
                    "high": float(rows_sorted[-1].get(high_field, 0)),
                    "low": float(rows_sorted[-1].get(low_field, 0)),
                    "close": float(rows_sorted[-1].get(close_field, 0)),
                }
                last_result = detect_doji(last_candle, body_threshold)
                detected = last_result["detected"] and (doji_type == "standard" or last_result["doji_type"] == doji_type)
            except (ValueError, TypeError):
                last_result = {"detected": False, "doji_type": None, "body_ratio": 0, "confidence": 0}
                detected = False
        else:
            last_result = {"detected": False, "doji_type": None, "body_ratio": 0, "confidence": 0}
            detected = False

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "pattern_detected": detected,
            "doji_type": last_result["doji_type"],
            "body_ratio": last_result["body_ratio"],
            "confidence": last_result["confidence"],
        })
        (passed if detected else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "Doji", "doji_type": doji_type, "body_threshold": body_threshold},
    }


__all__ = ["doji_condition", "detect_doji", "DOJI_SCHEMA"]
