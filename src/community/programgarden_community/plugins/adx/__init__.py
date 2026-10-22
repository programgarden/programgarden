"""
ADX (Average Directional Index) 플러그인

추세의 강도를 측정합니다. 방향과 무관하게 추세가 얼마나 강한지를 판단합니다.
- ADX > 25: 강한 추세
- ADX < 20: 약한 추세 (횡보)
- +DI > -DI: 상승 추세
- -DI > +DI: 하락 추세

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {period, threshold, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


ADX_SCHEMA = PluginSchema(
    id="ADX",
    name="ADX (Average Directional Index)",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Measures trend strength regardless of direction. ADX above 25 indicates strong trend, below 20 indicates weak trend or consolidation. +DI above -DI signals uptrend, vice versa for downtrend.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 14,
            "title": "ADX Period",
            "description": "Period for ADX calculation",
            "ge": 5,
            "le": 50,
        },
        "threshold": {
            "type": "float",
            "default": 25.0,
            "title": "Trend Threshold",
            "description": "ADX value above this indicates strong trend",
            "ge": 15,
            "le": 50,
        },
        "direction": {
            "type": "string",
            "default": "strong_trend",
            "title": "Direction",
            "description": "strong_trend: ADX > threshold, uptrend: +DI > -DI with strong ADX, downtrend: -DI > +DI with strong ADX",
            "enum": ["strong_trend", "uptrend", "downtrend"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    optional_fields=["open", "volume"],
    tags=["trend", "momentum", "strength"],
    output_fields={
        "adx": {"type": "float", "description": "ADX value indicating trend strength (0-100)"},
        "plus_di": {"type": "float", "description": "Positive Directional Indicator (+DI)"},
        "minus_di": {"type": "float", "description": "Negative Directional Indicator (-DI)"},
    },
    locales={
        "ko": {
            "name": "ADX (평균방향지수)",
            "description": "방향과 무관하게 추세의 강도를 측정합니다. ADX가 25 이상이면 강한 추세, 20 이하면 약한 추세(횡보)입니다. +DI가 -DI보다 크면 상승 추세, 반대면 하락 추세입니다.",
            "fields.period": "ADX 계산 기간",
            "fields.threshold": "강한 추세 기준값 (ADX가 이 값 이상이면 강한 추세)",
            "fields.direction": "방향 (strong_trend: 강한 추세, uptrend: 상승 추세, downtrend: 하락 추세)",
        },
    },
)


def calculate_true_range(high: float, low: float, prev_close: float) -> float:
    """True Range 계산"""
    return max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close)
    )


def calculate_directional_movement(
    high: float, low: float, prev_high: float, prev_low: float
) -> tuple:
    """
    Directional Movement 계산

    Returns:
        (+DM, -DM)
    """
    up_move = high - prev_high
    down_move = prev_low - low

    plus_dm = up_move if up_move > down_move and up_move > 0 else 0
    minus_dm = down_move if down_move > up_move and down_move > 0 else 0

    return plus_dm, minus_dm


def calculate_adx(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> Dict[str, float]:
    """
    ADX, +DI, -DI 계산 (Wilder's Smoothing)

    Returns:
        {"adx": float, "plus_di": float, "minus_di": float}
    """
    min_required = period * 2  # ADX 계산에 충분한 데이터

    if len(highs) < min_required:
        return {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0}

    # TR, +DM, -DM 시리즈 계산
    tr_list = []
    plus_dm_list = []
    minus_dm_list = []

    for i in range(1, len(highs)):
        tr = calculate_true_range(highs[i], lows[i], closes[i-1])
        plus_dm, minus_dm = calculate_directional_movement(
            highs[i], lows[i], highs[i-1], lows[i-1]
        )
        tr_list.append(tr)
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)

    if len(tr_list) < period:
        return {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0}

    # 첫 번째 smoothed 값 (SMA)
    smoothed_tr = sum(tr_list[:period])
    smoothed_plus_dm = sum(plus_dm_list[:period])
    smoothed_minus_dm = sum(minus_dm_list[:period])

    # +DI, -DI, DX 시리즈
    dx_list = []

    # 첫 번째 DI 계산
    if smoothed_tr > 0:
        plus_di = (smoothed_plus_dm / smoothed_tr) * 100
        minus_di = (smoothed_minus_dm / smoothed_tr) * 100
    else:
        plus_di = 0.0
        minus_di = 0.0

    di_sum = plus_di + minus_di
    if di_sum > 0:
        dx = abs(plus_di - minus_di) / di_sum * 100
    else:
        dx = 0.0
    dx_list.append(dx)

    # Wilder's smoothing으로 나머지 계산
    for i in range(period, len(tr_list)):
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + tr_list[i]
        smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / period) + plus_dm_list[i]
        smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / period) + minus_dm_list[i]

        if smoothed_tr > 0:
            plus_di = (smoothed_plus_dm / smoothed_tr) * 100
            minus_di = (smoothed_minus_dm / smoothed_tr) * 100
        else:
            plus_di = 0.0
            minus_di = 0.0

        di_sum = plus_di + minus_di
        if di_sum > 0:
            dx = abs(plus_di - minus_di) / di_sum * 100
        else:
            dx = 0.0
        dx_list.append(dx)

    # ADX 계산 (DX의 Wilder's smoothed average)
    if len(dx_list) < period:
        adx = sum(dx_list) / len(dx_list) if dx_list else 0.0
    else:
        adx = sum(dx_list[:period]) / period
        for i in range(period, len(dx_list)):
            adx = (adx * (period - 1) + dx_list[i]) / period

    return {
        "adx": round(adx, 2),
        "plus_di": round(plus_di, 2),
        "minus_di": round(minus_di, 2),
    }


def calculate_adx_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> List[Dict[str, float]]:
    """
    ADX 시계열 계산

    Returns:
        [{"adx": float, "plus_di": float, "minus_di": float}, ...]
    """
    min_required = period * 2

    if len(highs) < min_required:
        return []

    results = []

    for i in range(min_required, len(highs) + 1):
        adx_val = calculate_adx(highs[:i], lows[:i], closes[:i], period)
        results.append(adx_val)

    return results


async def adx_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    ADX 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {period, threshold, direction}
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

    period = fields.get("period", 14)
    threshold = fields.get("threshold", 25.0)
    direction = fields.get("direction", "strong_trend")

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

    min_required = period * 2

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
                "adx": None,
                "plus_di": None,
                "minus_di": None,
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
                "adx": None,
                "plus_di": None,
                "minus_di": None,
                "error": f"Insufficient data: need {min_required}, got {len(highs)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # ADX 계산
        adx_series = calculate_adx_series(highs, lows, closes, period)

        if not adx_series:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "adx": None,
                "plus_di": None,
                "minus_di": None,
                "error": "Calculation failed",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        current_adx = adx_series[-1]
        adx_val = current_adx["adx"]
        plus_di = current_adx["plus_di"]
        minus_di = current_adx["minus_di"]

        # time_series 생성
        adx_start_idx = min_required - 1
        time_series = []

        for i, adx_entry in enumerate(adx_series):
            row_idx = adx_start_idx + i
            if row_idx < len(rows_sorted):
                original_row = rows_sorted[row_idx]

                signal = None
                side = "long"

                # 신호 생성
                is_strong = adx_entry["adx"] >= threshold
                is_uptrend = adx_entry["plus_di"] > adx_entry["minus_di"]

                if is_strong:
                    if is_uptrend:
                        signal = "buy"
                        side = "long"
                    else:
                        signal = "sell"
                        side = "long"

                time_series.append({
                    date_field: original_row.get(date_field, ""),
                    open_field: original_row.get(open_field),
                    high_field: original_row.get(high_field),
                    low_field: original_row.get(low_field),
                    close_field: original_row.get(close_field),
                    volume_field: original_row.get(volume_field),
                    "adx": adx_entry["adx"],
                    "plus_di": adx_entry["plus_di"],
                    "minus_di": adx_entry["minus_di"],
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
            "adx": adx_val,
            "plus_di": plus_di,
            "minus_di": minus_di,
        })

        # 조건 평가
        is_strong_trend = adx_val >= threshold
        is_uptrend = plus_di > minus_di

        if direction == "strong_trend":
            passed_condition = is_strong_trend
        elif direction == "uptrend":
            passed_condition = is_strong_trend and is_uptrend
        else:  # downtrend
            passed_condition = is_strong_trend and not is_uptrend

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
            "indicator": "ADX",
            "period": period,
            "threshold": threshold,
            "direction": direction,
        },
    }


__all__ = ["adx_condition", "calculate_adx", "calculate_adx_series", "ADX_SCHEMA"]
