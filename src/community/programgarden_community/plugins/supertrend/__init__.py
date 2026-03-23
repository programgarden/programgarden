"""
Supertrend (슈퍼트렌드) 플러그인

ATR 기반 추세 추종 지표. 상승/하락 밴드와 가격 교차로 추세 판단.
- bullish: 하락→상승 전환
- bearish: 상승→하락 전환
- uptrend: 현재 상승 추세
- downtrend: 현재 하락 추세

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {period, multiplier, signal_type}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


SUPERTREND_SCHEMA = PluginSchema(
    id="Supertrend",
    name="Supertrend",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="ATR-based trend following indicator. Clear buy/sell signals with upper and lower bands. Supertrend flips when price crosses the band.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 10,
            "title": "ATR Period",
            "description": "ATR calculation period",
            "ge": 2,
            "le": 100,
        },
        "multiplier": {
            "type": "float",
            "default": 3.0,
            "title": "Multiplier",
            "description": "ATR multiplier for band width",
            "ge": 0.5,
            "le": 10.0,
        },
        "signal_type": {
            "type": "string",
            "default": "bullish",
            "title": "Signal Type",
            "description": "Type of supertrend signal",
            "enum": ["bullish", "bearish", "uptrend", "downtrend"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["open", "volume"],
    tags=["trend", "atr", "supertrend"],
    output_fields={
        "supertrend": {"type": "float", "description": "Supertrend line value"},
        "trend": {"type": "str", "description": "Current trend direction (up/down)"},
    },
    locales={
        "ko": {
            "name": "슈퍼트렌드",
            "description": "ATR 기반 추세 추종 지표입니다. 명확한 매수/매도 시그널과 상/하 밴드를 제공합니다.",
            "fields.period": "ATR 계산 기간",
            "fields.multiplier": "ATR 배수 (밴드 폭)",
            "fields.signal_type": "시그널 유형 (상승/하락 전환, 상승/하락 추세)",
        },
    },
)


def _calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int) -> List[float]:
    """ATR 시계열 계산"""
    if len(highs) < 2:
        return []

    true_ranges = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    atrs = []
    if len(true_ranges) < period:
        return []

    # 첫 ATR = SMA
    first_atr = sum(true_ranges[:period]) / period
    atrs = [0.0] * (period - 1) + [first_atr]

    # 이후 EMA 방식
    for i in range(period, len(true_ranges)):
        atr = (atrs[-1] * (period - 1) + true_ranges[i]) / period
        atrs.append(atr)

    return atrs


def calculate_supertrend(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 10,
    multiplier: float = 3.0,
) -> List[Dict[str, Any]]:
    """슈퍼트렌드 시계열 계산"""
    atrs = _calculate_atr(highs, lows, closes, period)
    if not atrs or len(atrs) < period:
        return []

    results = []
    upper_band = 0.0
    lower_band = 0.0
    supertrend = 0.0
    is_uptrend = True
    prev_upper = 0.0
    prev_lower = 0.0

    for i in range(len(highs)):
        hl2 = (highs[i] + lows[i]) / 2
        atr = atrs[i] if i < len(atrs) else 0

        basic_upper = hl2 + multiplier * atr
        basic_lower = hl2 - multiplier * atr

        if i == 0:
            upper_band = basic_upper
            lower_band = basic_lower
            is_uptrend = closes[i] > hl2
            supertrend = lower_band if is_uptrend else upper_band
        else:
            # 상단 밴드: 현재 basic이 이전보다 낮거나, 이전 종가가 이전 상단 위면 basic 사용
            if basic_upper < prev_upper or closes[i - 1] > prev_upper:
                upper_band = basic_upper
            else:
                upper_band = prev_upper

            # 하단 밴드: 현재 basic이 이전보다 높거나, 이전 종가가 이전 하단 아래면 basic 사용
            if basic_lower > prev_lower or closes[i - 1] < prev_lower:
                lower_band = basic_lower
            else:
                lower_band = prev_lower

            # 추세 결정
            if closes[i] > upper_band:
                is_uptrend = True
            elif closes[i] < lower_band:
                is_uptrend = False

            supertrend = lower_band if is_uptrend else upper_band

        prev_upper = upper_band
        prev_lower = lower_band

        results.append({
            "supertrend": round(supertrend, 4),
            "trend": "up" if is_uptrend else "down",
            "upper_band": round(upper_band, 4),
            "lower_band": round(lower_band, 4),
        })

    return results


async def supertrend_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """슈퍼트렌드 조건 평가"""
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    period = fields.get("period", 10)
    multiplier = fields.get("multiplier", 3.0)
    signal_type = fields.get("signal_type", "bullish")

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

        if not rows or len(rows) < period + 1:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "Insufficient data"})
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

        st_series = calculate_supertrend(highs, lows, closes, period, multiplier)
        if not st_series:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "Calculation failed"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        time_series = []
        for i, st_val in enumerate(st_series):
            if i >= len(rows_sorted):
                break
            original_row = rows_sorted[i]
            signal = None
            side = "long"
            if i > 0:
                prev_trend = st_series[i - 1]["trend"]
                if prev_trend == "down" and st_val["trend"] == "up":
                    signal = "buy"
                elif prev_trend == "up" and st_val["trend"] == "down":
                    signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "supertrend": st_val["supertrend"],
                "trend": st_val["trend"],
                "upper_band": st_val["upper_band"],
                "lower_band": st_val["lower_band"],
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        current = st_series[-1]
        passed_condition = False
        if signal_type == "uptrend":
            passed_condition = current["trend"] == "up"
        elif signal_type == "downtrend":
            passed_condition = current["trend"] == "down"
        elif len(st_series) >= 2:
            prev = st_series[-2]
            if signal_type == "bullish":
                passed_condition = prev["trend"] == "down" and current["trend"] == "up"
            elif signal_type == "bearish":
                passed_condition = prev["trend"] == "up" and current["trend"] == "down"

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "supertrend": current["supertrend"], "trend": current["trend"],
        })
        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "Supertrend", "period": period, "multiplier": multiplier, "signal_type": signal_type},
    }


__all__ = ["supertrend_condition", "calculate_supertrend", "SUPERTREND_SCHEMA"]
