"""
MorningEveningStar (샛별/석별형) 플러그인

3봉 반전 패턴. 샛별(하락→소형봉→상승), 석별(상승→소형봉→하락).
- morning_star: 하락 후 반전 상승 (매수)
- evening_star: 상승 후 반전 하락 (매도)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, open, high, low, close, ...}, ...]
- fields: {pattern, star_body_max, confirmation_ratio}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MORNING_EVENING_STAR_SCHEMA = PluginSchema(
    id="MorningEveningStar",
    name="Morning / Evening Star",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Identifies 3-candle reversal patterns. Morning Star: large bearish + small body + large bullish (buy). Evening Star: large bullish + small body + large bearish (sell).",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "pattern": {
            "type": "string",
            "default": "morning_star",
            "title": "Pattern",
            "description": "morning_star: bullish reversal, evening_star: bearish reversal",
            "enum": ["morning_star", "evening_star"],
        },
        "star_body_max": {
            "type": "float",
            "default": 0.3,
            "title": "Star Body Max",
            "description": "Maximum body ratio for the middle (star) candle",
            "ge": 0.05,
            "le": 0.5,
        },
        "confirmation_ratio": {
            "type": "float",
            "default": 0.5,
            "title": "Confirmation Ratio",
            "description": "3rd candle must recover N% of 1st candle body",
            "ge": 0.2,
            "le": 1.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "open", "high", "low", "close"],
    optional_fields=["volume"],
    tags=["candlestick", "pattern", "reversal", "morning_star", "evening_star"],
    locales={
        "ko": {
            "name": "샛별/석별형",
            "description": "3봉 반전 패턴입니다. 샛별(대음봉+소형봉+대양봉, 매수 반전), 석별(대양봉+소형봉+대음봉, 매도 반전).",
            "fields.pattern": "패턴 (morning_star: 샛별, evening_star: 석별)",
            "fields.star_body_max": "가운데 봉 최대 몸통 비율",
            "fields.confirmation_ratio": "3번째 봉이 1번째 봉 몸통의 N% 이상 회복",
        },
    },
)


def detect_morning_star(
    candles: List[Dict[str, float]],
    star_body_max: float = 0.3,
    confirmation_ratio: float = 0.5,
) -> Dict[str, Any]:
    """샛별: 대음봉 + 소형봉 + 대양봉"""
    if len(candles) < 3:
        return {"detected": False, "confidence": 0, "details": "Insufficient candles"}

    c1, c2, c3 = candles[-3], candles[-2], candles[-1]

    # 1번째: 음봉
    if c1["close"] >= c1["open"]:
        return {"detected": False, "confidence": 0, "details": "1st candle not bearish"}

    # 3번째: 양봉
    if c3["close"] <= c3["open"]:
        return {"detected": False, "confidence": 0, "details": "3rd candle not bullish"}

    # 2번째: 소형봉
    c2_range = c2["high"] - c2["low"]
    c2_body = abs(c2["close"] - c2["open"])
    if c2_range > 0 and c2_body / c2_range > star_body_max:
        return {"detected": False, "confidence": 0, "details": f"Star body ratio {c2_body/c2_range:.2f} > {star_body_max}"}

    # 3번째가 1번째 몸통의 confirmation_ratio 이상 회복
    c1_body = abs(c1["close"] - c1["open"])
    c3_recovery = c3["close"] - c3["open"]
    if c1_body > 0 and c3_recovery / c1_body < confirmation_ratio:
        return {"detected": False, "confidence": 0, "details": f"Confirmation {c3_recovery/c1_body:.2f} < {confirmation_ratio}"}

    star_body_ratio = c2_body / c2_range if c2_range > 0 else 0
    confirmation_pct = c3_recovery / c1_body if c1_body > 0 else 0
    confidence = min((1 - star_body_ratio) * confirmation_pct, 1.0)

    return {
        "detected": True,
        "confidence": round(confidence, 2),
        "details": "Morning Star detected",
        "star_body_ratio": round(star_body_ratio, 4),
        "confirmation_pct": round(confirmation_pct, 4),
    }


def detect_evening_star(
    candles: List[Dict[str, float]],
    star_body_max: float = 0.3,
    confirmation_ratio: float = 0.5,
) -> Dict[str, Any]:
    """석별: 대양봉 + 소형봉 + 대음봉"""
    if len(candles) < 3:
        return {"detected": False, "confidence": 0, "details": "Insufficient candles"}

    c1, c2, c3 = candles[-3], candles[-2], candles[-1]

    if c1["close"] <= c1["open"]:
        return {"detected": False, "confidence": 0, "details": "1st candle not bullish"}
    if c3["close"] >= c3["open"]:
        return {"detected": False, "confidence": 0, "details": "3rd candle not bearish"}

    c2_range = c2["high"] - c2["low"]
    c2_body = abs(c2["close"] - c2["open"])
    if c2_range > 0 and c2_body / c2_range > star_body_max:
        return {"detected": False, "confidence": 0, "details": f"Star body ratio {c2_body/c2_range:.2f} > {star_body_max}"}

    c1_body = abs(c1["close"] - c1["open"])
    c3_body = abs(c3["open"] - c3["close"])
    if c1_body > 0 and c3_body / c1_body < confirmation_ratio:
        return {"detected": False, "confidence": 0, "details": f"Confirmation {c3_body/c1_body:.2f} < {confirmation_ratio}"}

    star_body_ratio = c2_body / c2_range if c2_range > 0 else 0
    confirmation_pct = c3_body / c1_body if c1_body > 0 else 0
    confidence = min((1 - star_body_ratio) * confirmation_pct, 1.0)

    return {
        "detected": True,
        "confidence": round(confidence, 2),
        "details": "Evening Star detected",
        "star_body_ratio": round(star_body_ratio, 4),
        "confirmation_pct": round(confirmation_pct, 4),
    }


async def morning_evening_star_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """MorningEveningStar 조건 평가"""
    mapping = field_mapping or {}
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    volume_field = mapping.get("volume_field", "volume")

    pattern = fields.get("pattern", "morning_star")
    star_body_max = fields.get("star_body_max", 0.3)
    confirmation_ratio = fields.get("confirmation_ratio", 0.5)

    detect_fn = detect_morning_star if pattern == "morning_star" else detect_evening_star

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

        if not rows or len(rows) < 3:
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

            if i >= 2:
                result = detect_fn(candles[i - 2:i + 1], star_body_max, confirmation_ratio)
                detected = result["detected"]
                confidence = result["confidence"]
                if detected:
                    signal = "buy" if pattern == "morning_star" else "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field), high_field: original_row.get(high_field),
                low_field: original_row.get(low_field), close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "pattern_detected": detected, "pattern_type": pattern if detected else None,
                "confidence": confidence, "signal": signal, "side": "long",
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        last_result = detect_fn(candles[-3:], star_body_max, confirmation_ratio) if len(candles) >= 3 else {"detected": False, "confidence": 0}
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
        "analysis": {"indicator": "MorningEveningStar", "pattern": pattern, "star_body_max": star_body_max, "confirmation_ratio": confirmation_ratio},
    }


__all__ = ["morning_evening_star_condition", "detect_morning_star", "detect_evening_star", "MORNING_EVENING_STAR_SCHEMA"]
