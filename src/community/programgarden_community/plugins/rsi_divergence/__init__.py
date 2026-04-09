"""
RSIDivergence (RSI 다이버전스) 플러그인

가격과 RSI 사이의 강세/약세 다이버전스를 감지합니다.
- Bullish: 가격 Lower Low + RSI Higher Low → 반등 신호
- Bearish: 가격 Higher High + RSI Lower High → 하락 반전 신호

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {rsi_period, lookback, pivot_window, divergence_type}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


RSI_DIVERGENCE_SCHEMA = PluginSchema(
    id="RSIDivergence",
    name="RSI Divergence",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Detects bullish and bearish divergence between price and RSI. Bullish divergence (price lower low + RSI higher low) signals potential reversal up. Bearish divergence (price higher high + RSI lower high) signals potential reversal down.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "rsi_period": {
            "type": "int",
            "default": 14,
            "title": "RSI Period",
            "description": "RSI calculation period",
            "ge": 2,
            "le": 100,
        },
        "lookback": {
            "type": "int",
            "default": 50,
            "title": "Lookback",
            "description": "Number of bars to search for divergence",
            "ge": 20,
            "le": 200,
        },
        "pivot_window": {
            "type": "int",
            "default": 5,
            "title": "Pivot Window",
            "description": "Window size for local peak/trough detection",
            "ge": 2,
            "le": 20,
        },
        "divergence_type": {
            "type": "string",
            "default": "bullish",
            "title": "Divergence Type",
            "description": "Type of divergence to detect",
            "enum": ["bullish", "bearish", "both"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["divergence", "rsi", "reversal", "momentum"],
    output_fields={
        "rsi": {"type": "float", "description": "Current RSI value"},
        "divergence": {"type": "str", "description": "Divergence type detected: bullish, bearish, or none"},
        "divergence_strength": {"type": "float", "description": "Divergence strength (price-RSI gap ratio)"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "RSI 다이버전스",
            "description": "가격과 RSI 사이의 강세/약세 다이버전스를 감지합니다. 강세 다이버전스(가격 저점↓ RSI 저점↑)는 반등 신호, 약세 다이버전스(가격 고점↑ RSI 고점↓)는 하락 반전 신호입니다.",
            "fields.rsi_period": "RSI 계산 기간",
            "fields.lookback": "다이버전스 탐색 기간 (봉 수)",
            "fields.pivot_window": "피크/트로프 감지 윈도우",
            "fields.divergence_type": "다이버전스 유형 (bullish: 강세, bearish: 약세, both: 둘 다)",
        },
    },
)


def _calculate_rsi_series(prices: List[float], period: int = 14) -> List[float]:
    """RSI 시계열 계산 (prices 길이와 동일한 길이 반환, 초기값은 50.0)"""
    if len(prices) < period + 1:
        return [50.0] * len(prices)

    rsi_values = [50.0] * period

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(round(100 - (100 / (1 + rs)), 2))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(round(100 - (100 / (1 + rs)), 2))

    return rsi_values


def find_local_minima(values: List[float], window: int) -> List[int]:
    """로컬 최저점 인덱스 반환"""
    minima = []
    for i in range(window, len(values) - window):
        is_min = True
        for j in range(1, window + 1):
            if values[i] > values[i - j] or values[i] > values[i + j]:
                is_min = False
                break
        if is_min:
            minima.append(i)
    return minima


def find_local_maxima(values: List[float], window: int) -> List[int]:
    """로컬 최고점 인덱스 반환"""
    maxima = []
    for i in range(window, len(values) - window):
        is_max = True
        for j in range(1, window + 1):
            if values[i] < values[i - j] or values[i] < values[i + j]:
                is_max = False
                break
        if is_max:
            maxima.append(i)
    return maxima


def detect_divergence(
    prices: List[float],
    rsi_values: List[float],
    pivot_window: int,
    lookback: int,
    divergence_type: str,
) -> Dict[str, Any]:
    """다이버전스 감지

    Returns:
        {"divergence": "bullish"|"bearish"|"none", "strength": float}
    """
    n = len(prices)
    if n < lookback or n != len(rsi_values):
        return {"divergence": "none", "strength": 0.0}

    start = max(0, n - lookback)
    check_bullish = divergence_type in ("bullish", "both")
    check_bearish = divergence_type in ("bearish", "both")

    # Bullish: 가격 LL + RSI HL
    if check_bullish:
        price_lows = find_local_minima(prices, pivot_window)
        rsi_lows = find_local_minima(rsi_values, pivot_window)

        price_lows = [i for i in price_lows if i >= start]
        rsi_lows = [i for i in rsi_lows if i >= start]

        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            pl1, pl2 = price_lows[-2], price_lows[-1]
            rl1_idx = min(rsi_lows, key=lambda x: abs(x - pl1))
            rl2_idx = min(rsi_lows, key=lambda x: abs(x - pl2))

            if (
                rl1_idx != rl2_idx
                and prices[pl2] < prices[pl1]
                and rsi_values[rl2_idx] > rsi_values[rl1_idx]
            ):
                price_diff = abs(prices[pl1] - prices[pl2]) / max(prices[pl1], 1e-10)
                rsi_diff = abs(rsi_values[rl2_idx] - rsi_values[rl1_idx])
                strength = round(price_diff * rsi_diff, 4)
                return {"divergence": "bullish", "strength": strength}

    # Bearish: 가격 HH + RSI LH
    if check_bearish:
        price_highs = find_local_maxima(prices, pivot_window)
        rsi_highs = find_local_maxima(rsi_values, pivot_window)

        price_highs = [i for i in price_highs if i >= start]
        rsi_highs = [i for i in rsi_highs if i >= start]

        if len(price_highs) >= 2 and len(rsi_highs) >= 2:
            ph1, ph2 = price_highs[-2], price_highs[-1]
            rh1_idx = min(rsi_highs, key=lambda x: abs(x - ph1))
            rh2_idx = min(rsi_highs, key=lambda x: abs(x - ph2))

            if (
                rh1_idx != rh2_idx
                and prices[ph2] > prices[ph1]
                and rsi_values[rh2_idx] < rsi_values[rh1_idx]
            ):
                price_diff = abs(prices[ph2] - prices[ph1]) / max(prices[ph1], 1e-10)
                rsi_diff = abs(rsi_values[rh1_idx] - rsi_values[rh2_idx])
                strength = round(price_diff * rsi_diff, 4)
                return {"divergence": "bearish", "strength": strength}

    return {"divergence": "none", "strength": 0.0}


async def rsi_divergence_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """RSI 다이버전스 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")

    rsi_period = fields.get("rsi_period", 14)
    lookback = fields.get("lookback", 50)
    pivot_window = fields.get("pivot_window", 5)
    divergence_type = fields.get("divergence_type", "bullish")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
        }

    # 종목별 그룹화
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

    # 평가 대상 결정
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
                "rsi": None, "divergence": "none",
                "divergence_strength": 0.0, "current_price": None,
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = []
        for row in rows_sorted:
            price = row.get(close_field)
            if price is not None:
                try:
                    prices.append(float(price))
                except (ValueError, TypeError):
                    pass

        current_price = prices[-1] if prices else None

        if len(prices) < rsi_period + 1:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "rsi": None, "divergence": "none",
                "divergence_strength": 0.0, "current_price": current_price,
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rsi_series = _calculate_rsi_series(prices, rsi_period)
        rsi_value = rsi_series[-1] if rsi_series else None

        div_result = detect_divergence(prices, rsi_series, pivot_window, lookback, divergence_type)

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "rsi": rsi_value,
            "divergence": div_result["divergence"],
            "divergence_strength": div_result["strength"],
            "current_price": current_price,
        })

        # time_series
        ts = []
        for i in range(rsi_period, len(rows_sorted)):
            if i < len(rsi_series):
                row = rows_sorted[i]
                entry = {
                    date_field: row.get(date_field, ""),
                    open_field: row.get(open_field),
                    high_field: row.get(high_field),
                    low_field: row.get(low_field),
                    close_field: row.get(close_field),
                    volume_field: row.get(volume_field),
                    "rsi": rsi_series[i],
                }
                ts.append(entry)
        values.append({"symbol": symbol, "exchange": exchange, "time_series": ts})

        if div_result["divergence"] != "none":
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
            "indicator": "RSIDivergence",
            "rsi_period": rsi_period,
            "lookback": lookback,
            "pivot_window": pivot_window,
            "divergence_type": divergence_type,
        },
    }


__all__ = [
    "rsi_divergence_condition",
    "detect_divergence",
    "find_local_minima",
    "find_local_maxima",
    "RSI_DIVERGENCE_SCHEMA",
]
