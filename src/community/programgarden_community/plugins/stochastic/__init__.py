"""
Stochastic Oscillator 플러그인

%K와 %D 라인의 교차를 통해 과매수/과매도 상태를 판단합니다.
- %K가 20 이하에서 %D를 상향 돌파: 매수 신호
- %K가 80 이상에서 %D를 하향 돌파: 매도 신호

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {k_period, d_period, threshold, direction}
- field_mapping: {high_field, low_field, close_field, ...}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


STOCHASTIC_SCHEMA = PluginSchema(
    id="Stochastic",
    name="Stochastic Oscillator",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Identifies overbought/oversold conditions using %K and %D crossovers. Buy signal when %K crosses above %D below 20, sell signal when %K crosses below %D above 80.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "k_period": {
            "type": "int",
            "default": 14,
            "title": "%K Period",
            "description": "Period for %K calculation",
            "ge": 1,
            "le": 100,
        },
        "d_period": {
            "type": "int",
            "default": 3,
            "title": "%D Period",
            "description": "Period for %D smoothing (SMA of %K)",
            "ge": 1,
            "le": 50,
        },
        "threshold": {
            "type": "float",
            "default": 20,
            "title": "Threshold",
            "description": "Oversold threshold (overbought is 100 - threshold)",
            "ge": 0,
            "le": 50,
        },
        "direction": {
            "type": "string",
            "default": "oversold",
            "title": "Direction",
            "description": "oversold: buy signal, overbought: sell signal",
            "enum": ["oversold", "overbought"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    optional_fields=[],
    tags=["momentum", "oscillator"],
    locales={
        "ko": {
            "name": "스토캐스틱 오실레이터",
            "description": "%K와 %D 라인의 교차를 통해 과매수/과매도 상태를 판단합니다. %K가 20 이하에서 %D를 상향 돌파하면 매수 신호, 80 이상에서 하향 돌파하면 매도 신호입니다.",
            "fields.k_period": "%K 계산 기간",
            "fields.d_period": "%D 평활화 기간 (%K의 이동평균)",
            "fields.threshold": "과매도 기준값 (과매수는 100 - 기준값)",
            "fields.direction": "방향 (oversold: 매수 신호, overbought: 매도 신호)",
        },
    },
)


def calculate_stochastic_k(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """
    %K 계산: (현재 종가 - N일 최저가) / (N일 최고가 - N일 최저가) * 100
    """
    if len(highs) < period or len(lows) < period or len(closes) < period:
        return 50.0

    recent_highs = highs[-period:]
    recent_lows = lows[-period:]
    current_close = closes[-1]

    highest_high = max(recent_highs)
    lowest_low = min(recent_lows)

    if highest_high == lowest_low:
        return 50.0

    k = (current_close - lowest_low) / (highest_high - lowest_low) * 100
    return round(k, 2)


def calculate_stochastic_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    k_period: int = 14,
    d_period: int = 3
) -> List[Dict[str, float]]:
    """
    스토캐스틱 시계열 계산

    Returns:
        [{"k": float, "d": float}, ...]
    """
    if len(highs) < k_period + d_period - 1:
        return []

    k_values = []

    # %K 시계열 계산
    for i in range(k_period, len(highs) + 1):
        sub_highs = highs[:i]
        sub_lows = lows[:i]
        sub_closes = closes[:i]
        k = calculate_stochastic_k(sub_highs, sub_lows, sub_closes, k_period)
        k_values.append(k)

    # %D 시계열 계산 (K의 SMA)
    results = []
    for i in range(d_period, len(k_values) + 1):
        k_for_d = k_values[:i]
        d = sum(k_for_d[-d_period:]) / d_period
        results.append({
            "k": k_values[i - 1],
            "d": round(d, 2),
        })

    return results


async def stochastic_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    스토캐스틱 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {k_period, d_period, threshold, direction}
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

    k_period = fields.get("k_period", 14)
    d_period = fields.get("d_period", 3)
    threshold = fields.get("threshold", 20)
    direction = fields.get("direction", "oversold")

    overbought_threshold = 100 - threshold

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

    min_required = k_period + d_period - 1

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
                "k": None,
                "d": None,
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
                "k": None,
                "d": None,
                "error": f"Insufficient data: need {min_required}, got {len(highs)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 스토캐스틱 계산
        stoch_series = calculate_stochastic_series(highs, lows, closes, k_period, d_period)

        if not stoch_series:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "k": None,
                "d": None,
                "error": "Calculation failed",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        current_k = stoch_series[-1]["k"]
        current_d = stoch_series[-1]["d"]

        # time_series 생성
        stoch_start_idx = k_period + d_period - 2
        time_series = []

        for i, stoch_val in enumerate(stoch_series):
            row_idx = stoch_start_idx + i
            if row_idx < len(rows_sorted):
                original_row = rows_sorted[row_idx]

                signal = None
                side = "long"
                k_val = stoch_val["k"]
                d_val = stoch_val["d"]

                # 크로스 감지
                if i > 0:
                    prev_k = stoch_series[i - 1]["k"]
                    prev_d = stoch_series[i - 1]["d"]

                    # 골든 크로스: K가 D를 상향 돌파 + 과매도 구간
                    if prev_k < prev_d and k_val >= d_val and k_val < threshold:
                        signal = "buy"
                        side = "long"
                    # 데드 크로스: K가 D를 하향 돌파 + 과매수 구간
                    elif prev_k > prev_d and k_val <= d_val and k_val > overbought_threshold:
                        signal = "sell"
                        side = "long"

                time_series.append({
                    date_field: original_row.get(date_field, ""),
                    open_field: original_row.get(open_field),
                    high_field: original_row.get(high_field),
                    low_field: original_row.get(low_field),
                    close_field: original_row.get(close_field),
                    volume_field: original_row.get(volume_field),
                    "k": k_val,
                    "d": d_val,
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
            "k": current_k,
            "d": current_d,
        })

        # 조건 평가
        if direction == "oversold":
            # 과매도 구간에서 K가 D를 상향 돌파
            if len(stoch_series) >= 2:
                prev_k = stoch_series[-2]["k"]
                prev_d = stoch_series[-2]["d"]
                passed_condition = (prev_k < prev_d and current_k >= current_d and current_k < threshold)
            else:
                passed_condition = current_k < threshold
        else:  # overbought
            # 과매수 구간에서 K가 D를 하향 돌파
            if len(stoch_series) >= 2:
                prev_k = stoch_series[-2]["k"]
                prev_d = stoch_series[-2]["d"]
                passed_condition = (prev_k > prev_d and current_k <= current_d and current_k > overbought_threshold)
            else:
                passed_condition = current_k > overbought_threshold

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
            "indicator": "Stochastic",
            "k_period": k_period,
            "d_period": d_period,
            "threshold": threshold,
            "direction": direction,
        },
    }


__all__ = ["stochastic_condition", "calculate_stochastic_k", "calculate_stochastic_series", "STOCHASTIC_SCHEMA"]
