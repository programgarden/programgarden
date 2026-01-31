"""
Breakout Retest (돌파 후 되돌림) 플러그인

가격이 주요 레벨을 돌파한 후 되돌림(retest)할 때 진입 신호를 생성합니다.
- 상향 돌파 후 되돌림: 저항이 지지로 전환 (매수)
- 하향 돌파 후 되돌림: 지지가 저항으로 전환 (매도)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {lookback, retest_threshold, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


BREAKOUT_RETEST_SCHEMA = PluginSchema(
    id="BreakoutRetest",
    name="Breakout Retest",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Identifies retest opportunities after price breaks through key levels. After bullish breakout, wait for price to retest the broken resistance (now support). After bearish breakout, wait for retest of broken support (now resistance).",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 20,
            "title": "Lookback Period",
            "description": "Period to identify the breakout level",
            "ge": 5,
            "le": 100,
        },
        "retest_threshold": {
            "type": "float",
            "default": 0.02,
            "title": "Retest Threshold",
            "description": "How close price needs to be to breakout level (as percentage)",
            "ge": 0.005,
            "le": 0.1,
        },
        "direction": {
            "type": "string",
            "default": "bullish",
            "title": "Direction",
            "description": "bullish: buy on retest after upward breakout, bearish: sell on retest after downward breakout",
            "enum": ["bullish", "bearish"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    optional_fields=["open", "volume"],
    tags=["breakout", "retest", "support", "resistance"],
    locales={
        "ko": {
            "name": "돌파 후 되돌림",
            "description": "가격이 주요 레벨을 돌파한 후 되돌림(리테스트) 시 진입 기회를 찾습니다. 상향 돌파 후에는 돌파된 저항선(이제 지지선)에서 되돌림을 확인하고, 하향 돌파 후에는 돌파된 지지선(이제 저항선)에서 되돌림을 확인합니다.",
            "fields.lookback": "돌파 레벨 탐색 기간",
            "fields.retest_threshold": "되돌림 인식 범위 (퍼센트)",
            "fields.direction": "방향 (bullish: 상향 돌파 후 매수, bearish: 하향 돌파 후 매도)",
        },
    },
)


def find_breakout_level(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    lookback: int = 20
) -> Dict[str, Any]:
    """
    돌파 레벨과 상태 찾기

    Returns:
        {
            "resistance": float,  # 과거 저항선
            "support": float,     # 과거 지지선
            "breakout_type": str, # "bullish", "bearish", or None
            "breakout_level": float,
        }
    """
    if len(highs) < lookback + 5:
        return {
            "resistance": None,
            "support": None,
            "breakout_type": None,
            "breakout_level": None,
        }

    # lookback 기간의 고점/저점 (현재 5일 제외)
    past_highs = highs[-(lookback + 5):-5]
    past_lows = lows[-(lookback + 5):-5]

    resistance = max(past_highs)
    support = min(past_lows)

    # 최근 5일 종가
    recent_closes = closes[-5:]
    current_close = closes[-1]

    # 돌파 감지
    breakout_type = None
    breakout_level = None

    # 상향 돌파: 현재 종가가 과거 저항선 위
    if current_close > resistance:
        # 과거에 저항선 아래였다가 현재 위로 올라옴
        if any(c <= resistance for c in recent_closes[:-1]):
            breakout_type = "bullish"
            breakout_level = resistance

    # 하향 돌파: 현재 종가가 과거 지지선 아래
    if current_close < support:
        if any(c >= support for c in recent_closes[:-1]):
            breakout_type = "bearish"
            breakout_level = support

    return {
        "resistance": resistance,
        "support": support,
        "breakout_type": breakout_type,
        "breakout_level": breakout_level,
    }


def detect_retest(
    current_close: float,
    breakout_level: float,
    breakout_type: str,
    threshold: float = 0.02
) -> bool:
    """
    되돌림(리테스트) 감지

    Args:
        current_close: 현재 종가
        breakout_level: 돌파 레벨
        breakout_type: "bullish" or "bearish"
        threshold: 근접 허용 범위

    Returns:
        되돌림 여부
    """
    if breakout_level is None or breakout_level == 0:
        return False

    distance_pct = abs(current_close - breakout_level) / breakout_level

    if breakout_type == "bullish":
        # 상향 돌파 후: 가격이 돌파 레벨 근처에서 위에 있어야 함
        return distance_pct <= threshold and current_close >= breakout_level
    elif breakout_type == "bearish":
        # 하향 돌파 후: 가격이 돌파 레벨 근처에서 아래에 있어야 함
        return distance_pct <= threshold and current_close <= breakout_level

    return False


async def breakout_retest_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Breakout Retest 조건 평가
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

    lookback = fields.get("lookback", 20)
    retest_threshold = fields.get("retest_threshold", 0.02)
    direction = fields.get("direction", "bullish")

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

    min_required = lookback + 5

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
                "breakout_level": None,
                "breakout_type": None,
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
                "breakout_level": None,
                "breakout_type": None,
                "error": f"Insufficient data: need {min_required}, got {len(highs)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 돌파 레벨 찾기
        breakout_info = find_breakout_level(highs, lows, closes, lookback)
        current_close = closes[-1]

        # 되돌림 감지
        is_retest = detect_retest(
            current_close,
            breakout_info["breakout_level"],
            breakout_info["breakout_type"],
            retest_threshold
        )

        # time_series 생성
        time_series = []
        start_idx = max(0, len(rows_sorted) - lookback - 5)

        for i in range(start_idx, len(rows_sorted)):
            original_row = rows_sorted[i]

            signal = None
            side = "long"

            # 마지막 날에서 리테스트 신호
            if i == len(rows_sorted) - 1:
                if is_retest:
                    if direction == "bullish" and breakout_info["breakout_type"] == "bullish":
                        signal = "buy"
                    elif direction == "bearish" and breakout_info["breakout_type"] == "bearish":
                        signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "resistance": breakout_info["resistance"],
                "support": breakout_info["support"],
                "breakout_level": breakout_info["breakout_level"],
                "breakout_type": breakout_info["breakout_type"],
                "signal": signal,
                "side": side,
            })

        values.append({
            "symbol": symbol,
            "exchange": exchange,
            "time_series": time_series,
        })

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "resistance": breakout_info["resistance"],
            "support": breakout_info["support"],
            "breakout_level": breakout_info["breakout_level"],
            "breakout_type": breakout_info["breakout_type"],
            "current_price": current_close,
            "is_retest": is_retest,
        })

        # 조건 평가
        if direction == "bullish":
            passed_condition = is_retest and breakout_info["breakout_type"] == "bullish"
        else:  # bearish
            passed_condition = is_retest and breakout_info["breakout_type"] == "bearish"

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
            "indicator": "BreakoutRetest",
            "lookback": lookback,
            "retest_threshold": retest_threshold,
            "direction": direction,
        },
    }


__all__ = ["breakout_retest_condition", "find_breakout_level", "detect_retest", "BREAKOUT_RETEST_SCHEMA"]
