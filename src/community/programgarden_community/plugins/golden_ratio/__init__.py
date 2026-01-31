"""
Golden Ratio (피보나치 되돌림) 플러그인

피보나치 비율을 이용해 지지/저항 레벨을 계산합니다.
- 되돌림 레벨: 0.236, 0.382, 0.5, 0.618, 0.786
- 가격이 레벨 근처에서 반등: 지지 신호
- 가격이 레벨 근처에서 저항: 저항 신호

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {lookback, level, direction, tolerance}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


GOLDEN_RATIO_SCHEMA = PluginSchema(
    id="GoldenRatio",
    name="Golden Ratio (Fibonacci Retracement)",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Identifies support and resistance levels using Fibonacci ratios. Common retracement levels are 23.6%, 38.2%, 50%, 61.8%, and 78.6%. Price bouncing off these levels can signal entry/exit points.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 50,
            "title": "Lookback Period",
            "description": "Period to find swing high/low for Fibonacci calculation",
            "ge": 10,
            "le": 200,
        },
        "level": {
            "type": "string",
            "default": "0.618",
            "title": "Fibonacci Level",
            "description": "Target Fibonacci retracement level",
            "enum": ["0.236", "0.382", "0.5", "0.618", "0.786"],
        },
        "direction": {
            "type": "string",
            "default": "support",
            "title": "Direction",
            "description": "support: price near level from above, resistance: price near level from below",
            "enum": ["support", "resistance"],
        },
        "tolerance": {
            "type": "float",
            "default": 0.02,
            "title": "Tolerance",
            "description": "Tolerance for level proximity (as percentage)",
            "ge": 0.005,
            "le": 0.1,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    optional_fields=["open", "volume"],
    tags=["fibonacci", "support", "resistance", "retracement"],
    locales={
        "ko": {
            "name": "황금비율 (피보나치 되돌림)",
            "description": "피보나치 비율을 이용해 지지/저항 레벨을 찾습니다. 주요 되돌림 레벨은 23.6%, 38.2%, 50%, 61.8%, 78.6%입니다. 가격이 이 레벨에서 반등하면 진입/청산 신호가 될 수 있습니다.",
            "fields.lookback": "스윙 고/저점 탐색 기간",
            "fields.level": "피보나치 레벨",
            "fields.direction": "방향 (support: 지지, resistance: 저항)",
            "fields.tolerance": "레벨 근접 허용 범위 (퍼센트)",
        },
    },
)


FIB_LEVELS = {
    "0.236": 0.236,
    "0.382": 0.382,
    "0.5": 0.5,
    "0.618": 0.618,
    "0.786": 0.786,
}


def calculate_fibonacci_levels(
    swing_high: float,
    swing_low: float,
    is_uptrend: bool = True
) -> Dict[str, float]:
    """
    피보나치 되돌림 레벨 계산

    Args:
        swing_high: 스윙 고점
        swing_low: 스윙 저점
        is_uptrend: True면 상승 후 되돌림, False면 하락 후 반등

    Returns:
        각 피보나치 레벨의 가격
    """
    diff = swing_high - swing_low

    if is_uptrend:
        # 상승 후 되돌림: 고점에서 아래로
        return {
            level: round(swing_high - diff * ratio, 4)
            for level, ratio in FIB_LEVELS.items()
        }
    else:
        # 하락 후 반등: 저점에서 위로
        return {
            level: round(swing_low + diff * ratio, 4)
            for level, ratio in FIB_LEVELS.items()
        }


def find_swing_points(
    highs: List[float],
    lows: List[float],
    lookback: int = 50
) -> tuple:
    """
    스윙 고점과 저점 찾기

    Returns:
        (swing_high, swing_low, is_uptrend)
    """
    if len(highs) < lookback or len(lows) < lookback:
        return None, None, None

    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]

    swing_high = max(recent_highs)
    swing_low = min(recent_lows)

    high_idx = recent_highs.index(swing_high)
    low_idx = recent_lows.index(swing_low)

    # 고점이 저점보다 먼저면 상승 후 되돌림
    is_uptrend = high_idx > low_idx

    return swing_high, swing_low, is_uptrend


async def golden_ratio_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Golden Ratio 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {lookback, level, direction, tolerance}
        field_mapping: 필드명 매핑
        symbols: 평가할 종목 리스트

    Returns:
        {passed_symbols, failed_symbols, symbol_results, values, result}
    """
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    lookback = fields.get("lookback", 50)
    level = fields.get("level", "0.618")
    direction = fields.get("direction", "support")
    tolerance = fields.get("tolerance", 0.02)

    fib_ratio = FIB_LEVELS.get(level, 0.618)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
        }

    # 종목별 데이터 그룹화
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

    # 평가할 종목 결정
    if symbols:
        target_symbols = []
        for s in symbols:
            if isinstance(s, dict):
                target_symbols.append({
                    "symbol": s.get("symbol", ""),
                    "exchange": s.get("exchange", "UNKNOWN"),
                })
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

    min_required = lookback

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])

        if not rows:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "fib_level": None,
                "fib_price": None,
                "error": "No data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        highs = []
        lows = []
        closes = []

        for row in rows_sorted:
            try:
                h = float(row.get(high_field, 0))
                l = float(row.get(low_field, 0))
                c = float(row.get(close_field, 0))
                highs.append(h)
                lows.append(l)
                closes.append(c)
            except (ValueError, TypeError):
                pass

        if len(highs) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "fib_level": None,
                "fib_price": None,
                "error": f"Insufficient data: need {min_required}, got {len(highs)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 스윙 포인트 찾기
        swing_high, swing_low, is_uptrend = find_swing_points(highs, lows, lookback)

        if swing_high is None or swing_low is None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "fib_level": None,
                "fib_price": None,
                "error": "Cannot find swing points",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 피보나치 레벨 계산
        fib_levels = calculate_fibonacci_levels(swing_high, swing_low, is_uptrend)
        target_price = fib_levels[level]
        current_close = closes[-1]

        # time_series 생성
        time_series = []
        start_idx = max(0, len(rows_sorted) - lookback)

        for i in range(start_idx, len(rows_sorted)):
            original_row = rows_sorted[i]
            close_price = closes[i]

            # 레벨 근접 여부
            distance_pct = abs(close_price - target_price) / target_price if target_price > 0 else 1
            near_level = distance_pct <= tolerance

            signal = None
            side = "long"

            if near_level:
                if direction == "support" and close_price >= target_price:
                    signal = "buy"
                    side = "long"
                elif direction == "resistance" and close_price <= target_price:
                    signal = "sell"
                    side = "long"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "fib_level": level,
                "fib_price": target_price,
                "swing_high": swing_high,
                "swing_low": swing_low,
                "distance_pct": round(distance_pct * 100, 2),
                "near_level": near_level,
                "signal": signal,
                "side": side,
            })

        values.append({
            "symbol": symbol,
            "exchange": exchange,
            "time_series": time_series,
        })

        # 현재 가격과 레벨 근접 여부
        current_distance = abs(current_close - target_price) / target_price if target_price > 0 else 1
        is_near = current_distance <= tolerance

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "fib_level": level,
            "fib_price": target_price,
            "swing_high": swing_high,
            "swing_low": swing_low,
            "current_price": current_close,
            "distance_pct": round(current_distance * 100, 2),
            "is_uptrend": is_uptrend,
        })

        # 조건 평가
        if direction == "support":
            passed_condition = is_near and current_close >= target_price
        else:  # resistance
            passed_condition = is_near and current_close <= target_price

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
            "indicator": "GoldenRatio",
            "lookback": lookback,
            "level": level,
            "direction": direction,
            "tolerance": tolerance,
        },
    }


__all__ = ["golden_ratio_condition", "calculate_fibonacci_levels", "find_swing_points", "GOLDEN_RATIO_SCHEMA"]
