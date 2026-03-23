"""
Engulfing (장악형 패턴) 플러그인

이전 캔들을 완전히 감싸는 반전 패턴. 가장 신뢰도 높은 캔들스틱 패턴.
- bullish: 음봉 후 큰 양봉 (상승 반전)
- bearish: 양봉 후 큰 음봉 (하락 반전)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, open, high, low, close, ...}, ...]
- fields: {pattern, min_body_ratio}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


ENGULFING_SCHEMA = PluginSchema(
    id="Engulfing",
    name="Engulfing Pattern",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Identifies bullish and bearish engulfing candlestick patterns. Most reliable reversal pattern where current candle completely engulfs the previous candle's body.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "pattern": {
            "type": "string",
            "default": "bullish",
            "title": "Pattern",
            "description": "bullish: reversal up, bearish: reversal down",
            "enum": ["bullish", "bearish"],
        },
        "min_body_ratio": {
            "type": "float",
            "default": 0.5,
            "title": "Min Body Ratio",
            "description": "Minimum body/range ratio for valid candle",
            "ge": 0.1,
            "le": 1.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "open", "high", "low", "close"],
    optional_fields=["volume"],
    tags=["candlestick", "pattern", "reversal", "engulfing"],
    output_fields={
        "pattern_detected": {"type": "bool", "description": "Whether the engulfing pattern was detected on the latest candle"},
        "confidence": {"type": "float", "description": "Pattern confidence score (0.0–1.0)"},
        "pattern_type": {"type": "str", "description": "Pattern direction: 'bullish' or 'bearish'"},
    },
    locales={
        "ko": {
            "name": "장악형 패턴",
            "description": "가장 신뢰도 높은 반전 캔들 패턴입니다. 현재 캔들이 이전 캔들의 몸통을 완전히 감쌉니다.",
            "fields.pattern": "패턴 방향 (bullish: 상승 반전, bearish: 하락 반전)",
            "fields.min_body_ratio": "최소 몸통/전체 비율",
        },
    },
)


def _body_ratio(o: float, h: float, l: float, c: float) -> float:
    rng = h - l
    if rng <= 0:
        return 0.0
    return abs(c - o) / rng


def detect_bullish_engulfing(candles: List[Dict[str, float]], min_body_ratio: float = 0.5) -> Dict[str, Any]:
    """Bullish Engulfing: 음봉 후 큰 양봉이 감싸는 패턴"""
    if len(candles) < 2:
        return {"detected": False, "confidence": 0, "details": "Insufficient candles"}
    prev, curr = candles[-2], candles[-1]

    # 이전: 음봉
    if prev["close"] >= prev["open"]:
        return {"detected": False, "confidence": 0, "details": "Previous not bearish"}
    # 현재: 양봉
    if curr["close"] <= curr["open"]:
        return {"detected": False, "confidence": 0, "details": "Current not bullish"}
    # 몸통 비율
    if _body_ratio(curr["open"], curr["high"], curr["low"], curr["close"]) < min_body_ratio:
        return {"detected": False, "confidence": 0, "details": "Body ratio too small"}
    # 감싸기: 현재 시가 <= 이전 종가, 현재 종가 >= 이전 시가
    if curr["open"] > prev["close"] or curr["close"] < prev["open"]:
        return {"detected": False, "confidence": 0, "details": "Not engulfing"}

    curr_body = abs(curr["close"] - curr["open"])
    prev_body = abs(prev["close"] - prev["open"])
    confidence = min(curr_body / prev_body, 3.0) / 3.0 if prev_body > 0 else 0.5

    return {"detected": True, "confidence": round(confidence, 2), "details": "Bullish Engulfing detected"}


def detect_bearish_engulfing(candles: List[Dict[str, float]], min_body_ratio: float = 0.5) -> Dict[str, Any]:
    """Bearish Engulfing: 양봉 후 큰 음봉이 감싸는 패턴"""
    if len(candles) < 2:
        return {"detected": False, "confidence": 0, "details": "Insufficient candles"}
    prev, curr = candles[-2], candles[-1]

    if prev["close"] <= prev["open"]:
        return {"detected": False, "confidence": 0, "details": "Previous not bullish"}
    if curr["close"] >= curr["open"]:
        return {"detected": False, "confidence": 0, "details": "Current not bearish"}
    if _body_ratio(curr["open"], curr["high"], curr["low"], curr["close"]) < min_body_ratio:
        return {"detected": False, "confidence": 0, "details": "Body ratio too small"}
    if curr["open"] < prev["close"] or curr["close"] > prev["open"]:
        return {"detected": False, "confidence": 0, "details": "Not engulfing"}

    curr_body = abs(curr["close"] - curr["open"])
    prev_body = abs(prev["close"] - prev["open"])
    confidence = min(curr_body / prev_body, 3.0) / 3.0 if prev_body > 0 else 0.5

    return {"detected": True, "confidence": round(confidence, 2), "details": "Bearish Engulfing detected"}


async def engulfing_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Engulfing 조건 평가"""
    mapping = field_mapping or {}
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    volume_field = mapping.get("volume_field", "volume")

    pattern = fields.get("pattern", "bullish")
    min_body_ratio = fields.get("min_body_ratio", 0.5)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [], "symbol_results": [],
            "values": [], "result": False, "analysis": {"error": "No data provided"},
        }

    detect_fn = detect_bullish_engulfing if pattern == "bullish" else detect_bearish_engulfing

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

        if not rows or len(rows) < 2:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "pattern_detected": False, "error": "Insufficient data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        candles = []
        for row in rows_sorted:
            try:
                candles.append({
                    "open": float(row.get(open_field, 0)), "high": float(row.get(high_field, 0)),
                    "low": float(row.get(low_field, 0)), "close": float(row.get(close_field, 0)),
                })
            except (ValueError, TypeError):
                pass

        time_series = []
        for i in range(len(rows_sorted)):
            original_row = rows_sorted[i]
            detected = False
            confidence = 0
            signal = None
            side = "long"

            if i >= 1:
                result = detect_fn(candles[i - 1:i + 1], min_body_ratio)
                detected = result["detected"]
                confidence = result["confidence"]
                if detected:
                    signal = "buy" if pattern == "bullish" else "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "pattern_detected": detected,
                "pattern_type": pattern if detected else None,
                "confidence": confidence,
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        last_result = detect_fn(candles[-2:], min_body_ratio)
        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "pattern_detected": last_result["detected"],
            "confidence": last_result["confidence"],
            "pattern_type": pattern,
        })

        (passed if last_result["detected"] else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "Engulfing", "pattern": pattern, "min_body_ratio": min_body_ratio},
    }


__all__ = ["engulfing_condition", "detect_bullish_engulfing", "detect_bearish_engulfing", "ENGULFING_SCHEMA"]
