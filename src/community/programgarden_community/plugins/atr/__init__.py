"""
ATR (Average True Range) 플러그인

변동성을 측정하여 진입/청산 타이밍을 판단합니다.
- ATR 밴드 상단 돌파: 강한 상승 모멘텀
- ATR 밴드 하단 이탈: 강한 하락 모멘텀

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {period, multiplier, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


ATR_SCHEMA = PluginSchema(
    id="ATR",
    name="ATR (Average True Range)",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Measures volatility using True Range. ATR bands help identify breakout opportunities and set stop-loss levels.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 14,
            "title": "ATR Period",
            "description": "Period for ATR calculation",
            "ge": 1,
            "le": 100,
        },
        "multiplier": {
            "type": "float",
            "default": 2.0,
            "title": "Multiplier",
            "description": "ATR multiplier for band calculation",
            "ge": 0.5,
            "le": 5.0,
        },
        "direction": {
            "type": "string",
            "default": "breakout_up",
            "title": "Direction",
            "description": "breakout_up: price above upper band, breakout_down: price below lower band",
            "enum": ["breakout_up", "breakout_down"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    optional_fields=[],
    tags=["volatility", "breakout"],
    output_fields={
        "atr": {"type": "float", "description": "Average True Range value"},
        "ma": {"type": "float", "description": "Moving average used as ATR band center"},
        "upper_band": {"type": "float", "description": "Upper ATR band (MA + ATR * multiplier)"},
        "lower_band": {"type": "float", "description": "Lower ATR band (MA - ATR * multiplier)"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "ATR (평균진폭)",
            "description": "True Range를 이용해 변동성을 측정합니다. ATR 밴드를 통해 돌파 기회를 포착하고 손절 수준을 설정할 수 있습니다.",
            "fields.period": "ATR 계산 기간",
            "fields.multiplier": "ATR 배수 (밴드 폭 결정)",
            "fields.direction": "방향 (breakout_up: 상단 돌파, breakout_down: 하단 이탈)",
        },
    },
)


def calculate_true_range(high: float, low: float, prev_close: float) -> float:
    """
    True Range 계산
    TR = max(H-L, |H-PC|, |L-PC|)
    """
    return max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close)
    )


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """
    ATR 계산 (Simple Moving Average 방식)
    """
    if len(highs) < period + 1:
        return 0.0

    true_ranges = []
    for i in range(1, len(highs)):
        tr = calculate_true_range(highs[i], lows[i], closes[i - 1])
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

    recent_tr = true_ranges[-period:]
    return round(sum(recent_tr) / period, 4)


def calculate_atr_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> List[float]:
    """
    ATR 시계열 계산
    """
    if len(highs) < period + 1:
        return []

    # 전체 True Range 계산
    true_ranges = []
    for i in range(1, len(highs)):
        tr = calculate_true_range(highs[i], lows[i], closes[i - 1])
        true_ranges.append(tr)

    # ATR 시계열
    atr_values = []
    for i in range(period, len(true_ranges) + 1):
        atr = sum(true_ranges[i - period:i]) / period
        atr_values.append(round(atr, 4))

    return atr_values


async def atr_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    ATR 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {period, multiplier, direction}
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
    multiplier = fields.get("multiplier", 2.0)
    direction = fields.get("direction", "breakout_up")

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

    min_required = period + 1

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
                "atr": None,
                "upper_band": None,
                "lower_band": None,
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
                "atr": None,
                "upper_band": None,
                "lower_band": None,
                "error": f"Insufficient data: need {min_required}, got {len(highs)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # ATR 계산
        atr_series = calculate_atr_series(highs, lows, closes, period)

        if not atr_series:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "atr": None,
                "upper_band": None,
                "lower_band": None,
                "error": "Calculation failed",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        current_atr = atr_series[-1]
        current_close = closes[-1]

        # MA 계산 (ATR 밴드의 중심선)
        ma_period = period
        if len(closes) >= ma_period:
            ma = sum(closes[-ma_period:]) / ma_period
        else:
            ma = current_close

        upper_band = round(ma + (current_atr * multiplier), 4)
        lower_band = round(ma - (current_atr * multiplier), 4)

        # time_series 생성
        atr_start_idx = period
        time_series = []

        for i, atr_val in enumerate(atr_series):
            row_idx = atr_start_idx + i
            if row_idx < len(rows_sorted):
                original_row = rows_sorted[row_idx]
                close_price = closes[row_idx]

                # 해당 시점 MA 계산
                if row_idx >= ma_period:
                    point_ma = sum(closes[row_idx - ma_period + 1:row_idx + 1]) / ma_period
                else:
                    point_ma = close_price

                point_upper = round(point_ma + (atr_val * multiplier), 4)
                point_lower = round(point_ma - (atr_val * multiplier), 4)

                signal = None
                side = "long"

                # 밴드 돌파 감지
                if close_price > point_upper:
                    signal = "buy"
                    side = "long"
                elif close_price < point_lower:
                    signal = "sell"
                    side = "long"

                time_series.append({
                    date_field: original_row.get(date_field, ""),
                    open_field: original_row.get(open_field),
                    high_field: original_row.get(high_field),
                    low_field: original_row.get(low_field),
                    close_field: original_row.get(close_field),
                    volume_field: original_row.get(volume_field),
                    "atr": atr_val,
                    "ma": round(point_ma, 4),
                    "upper_band": point_upper,
                    "lower_band": point_lower,
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
            "atr": current_atr,
            "ma": round(ma, 4),
            "upper_band": upper_band,
            "lower_band": lower_band,
            "current_price": current_close,
        })

        # 조건 평가
        if direction == "breakout_up":
            passed_condition = current_close > upper_band
        else:  # breakout_down
            passed_condition = current_close < lower_band

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
            "indicator": "ATR",
            "period": period,
            "multiplier": multiplier,
            "direction": direction,
        },
    }


__all__ = ["atr_condition", "calculate_atr", "calculate_atr_series", "ATR_SCHEMA"]
