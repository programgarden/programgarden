"""
HammerShootingStar (망치/유성형) 플러그인

긴 아래꼬리의 망치형(하락 후 반전)과 긴 위꼬리의 유성형(상승 후 반전).
- hammer: 긴 아래꼬리 (매수 반전)
- shooting_star: 긴 위꼬리 (매도 반전)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, open, high, low, close, ...}, ...]
- fields: {pattern, shadow_ratio, body_position}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


HAMMER_SHOOTING_STAR_SCHEMA = PluginSchema(
    id="HammerShootingStar",
    name="Hammer / Shooting Star",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Identifies hammer (long lower shadow, bullish reversal) and shooting star (long upper shadow, bearish reversal) candlestick patterns.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "pattern": {
            "type": "string",
            "default": "hammer",
            "title": "Pattern",
            "description": "hammer: bullish reversal, shooting_star: bearish reversal",
            "enum": ["hammer", "shooting_star"],
        },
        "shadow_ratio": {
            "type": "float",
            "default": 2.0,
            "title": "Shadow Ratio",
            "description": "Minimum shadow/body ratio",
            "ge": 1.0,
            "le": 10.0,
        },
        "body_position": {
            "type": "float",
            "default": 0.3,
            "title": "Body Position",
            "description": "Body must be within top/bottom N% of total range",
            "ge": 0.1,
            "le": 0.5,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "open", "high", "low", "close"],
    optional_fields=["volume"],
    tags=["candlestick", "pattern", "reversal", "hammer", "shooting_star"],
    output_fields={
        "pattern_detected": {"type": "bool", "description": "Whether the pattern was detected on the latest candle"},
        "confidence": {"type": "float", "description": "Pattern confidence score (0.0–1.0)"},
        "pattern_type": {"type": "str", "description": "Pattern type: 'hammer' or 'shooting_star'"},
    },
    locales={
        "ko": {
            "name": "망치/유성형",
            "description": "망치형(긴 아래꼬리, 매수 반전)과 유성형(긴 위꼬리, 매도 반전)을 식별합니다.",
            "fields.pattern": "패턴 (hammer: 망치형, shooting_star: 유성형)",
            "fields.shadow_ratio": "꼬리/몸통 최소 비율",
            "fields.body_position": "몸통 위치 (상단/하단 N% 이내)",
        },
    },
)


def detect_hammer(candle: Dict[str, float], shadow_ratio: float = 2.0, body_position: float = 0.3) -> Dict[str, Any]:
    """망치형: 몸통이 상단에, 긴 아래꼬리"""
    o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
    total_range = h - l
    if total_range <= 0:
        return {"detected": False, "confidence": 0, "details": "No range"}

    body = abs(c - o)
    body_top = max(o, c)
    body_bottom = min(o, c)
    lower_shadow = body_bottom - l
    upper_shadow = h - body_top

    if body == 0:
        body = total_range * 0.01  # 도지에 가까운 경우

    # 아래꼬리가 몸통의 shadow_ratio 배 이상
    if lower_shadow / body < shadow_ratio:
        return {"detected": False, "confidence": 0, "details": f"Lower shadow ratio {lower_shadow/body:.1f} < {shadow_ratio}"}

    # 몸통이 전체 범위 상단 body_position% 이내
    body_pos = (body_top - l) / total_range
    if body_pos < (1 - body_position):
        return {"detected": False, "confidence": 0, "details": f"Body not in upper {body_position*100}%"}

    confidence = min(lower_shadow / body / shadow_ratio, 2.0) / 2.0
    return {
        "detected": True,
        "confidence": round(confidence, 2),
        "details": "Hammer detected",
        "body_ratio": round(body / total_range, 4),
        "shadow_ratio_actual": round(lower_shadow / body, 2),
    }


def detect_shooting_star(candle: Dict[str, float], shadow_ratio: float = 2.0, body_position: float = 0.3) -> Dict[str, Any]:
    """유성형: 몸통이 하단에, 긴 위꼬리"""
    o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
    total_range = h - l
    if total_range <= 0:
        return {"detected": False, "confidence": 0, "details": "No range"}

    body = abs(c - o)
    body_top = max(o, c)
    body_bottom = min(o, c)
    upper_shadow = h - body_top

    if body == 0:
        body = total_range * 0.01

    if upper_shadow / body < shadow_ratio:
        return {"detected": False, "confidence": 0, "details": f"Upper shadow ratio {upper_shadow/body:.1f} < {shadow_ratio}"}

    body_pos = (body_bottom - l) / total_range
    if body_pos > body_position:
        return {"detected": False, "confidence": 0, "details": f"Body not in lower {body_position*100}%"}

    confidence = min(upper_shadow / body / shadow_ratio, 2.0) / 2.0
    return {
        "detected": True,
        "confidence": round(confidence, 2),
        "details": "Shooting Star detected",
        "body_ratio": round(body / total_range, 4),
        "shadow_ratio_actual": round(upper_shadow / body, 2),
    }


async def hammer_shooting_star_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Hammer/ShootingStar 조건 평가"""
    mapping = field_mapping or {}
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    volume_field = mapping.get("volume_field", "volume")

    pattern = fields.get("pattern", "hammer")
    shadow_ratio = fields.get("shadow_ratio", 2.0)
    body_position = fields.get("body_position", 0.3)

    detect_fn = detect_hammer if pattern == "hammer" else detect_shooting_star

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
        for i, row in enumerate(rows_sorted):
            try:
                candle = {
                    "open": float(row.get(open_field, 0)), "high": float(row.get(high_field, 0)),
                    "low": float(row.get(low_field, 0)), "close": float(row.get(close_field, 0)),
                }
            except (ValueError, TypeError):
                continue

            result = detect_fn(candle, shadow_ratio, body_position)
            signal = None
            if result["detected"]:
                signal = "buy" if pattern == "hammer" else "sell"

            time_series.append({
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field), high_field: row.get(high_field),
                low_field: row.get(low_field), close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "pattern_detected": result["detected"],
                "pattern_type": pattern if result["detected"] else None,
                "confidence": result["confidence"],
                "signal": signal, "side": "long",
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
                last_result = detect_fn(last_candle, shadow_ratio, body_position)
            except (ValueError, TypeError):
                last_result = {"detected": False, "confidence": 0}
        else:
            last_result = {"detected": False, "confidence": 0}

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
        "analysis": {"indicator": "HammerShootingStar", "pattern": pattern, "shadow_ratio": shadow_ratio, "body_position": body_position},
    }


__all__ = ["hammer_shooting_star_condition", "detect_hammer", "detect_shooting_star", "HAMMER_SHOOTING_STAR_SCHEMA"]
