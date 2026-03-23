"""
Parabolic SAR (파라볼릭 SAR) 플러그인

가격 위/아래에 점을 찍어 추세 방향과 반전점을 표시.
- bullish_reversal: SAR이 가격 아래로 전환 (매수)
- bearish_reversal: SAR이 가격 위로 전환 (매도)
- uptrend: 현재 상승 추세 (SAR < 가격)
- downtrend: 현재 하락 추세 (SAR > 가격)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {af_start, af_step, af_max, signal_type}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


PARABOLIC_SAR_SCHEMA = PluginSchema(
    id="ParabolicSAR",
    name="Parabolic SAR",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Tracks trend direction and reversal points using dots above/below price. Acceleration factor increases as trend strengthens. Useful for trailing stop and trend detection.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "af_start": {
            "type": "float",
            "default": 0.02,
            "title": "AF Start",
            "description": "Initial acceleration factor",
            "ge": 0.001,
            "le": 0.1,
        },
        "af_step": {
            "type": "float",
            "default": 0.02,
            "title": "AF Step",
            "description": "Acceleration factor increment",
            "ge": 0.001,
            "le": 0.1,
        },
        "af_max": {
            "type": "float",
            "default": 0.20,
            "title": "AF Max",
            "description": "Maximum acceleration factor",
            "ge": 0.05,
            "le": 0.5,
        },
        "signal_type": {
            "type": "string",
            "default": "bullish_reversal",
            "title": "Signal Type",
            "description": "Type of SAR signal",
            "enum": ["bullish_reversal", "bearish_reversal", "uptrend", "downtrend"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["open", "volume"],
    tags=["trend", "reversal", "parabolic", "trailing_stop"],
    output_fields={
        "sar": {"type": "float", "description": "Parabolic SAR value"},
        "trend": {"type": "str", "description": "Current trend direction (up/down)"},
        "current_close": {"type": "float", "description": "Current close price"},
    },
    locales={
        "ko": {
            "name": "파라볼릭 SAR",
            "description": "가격 위/아래에 점을 찍어 추세 방향과 반전점을 추적합니다. 추세가 강해질수록 가속인자가 증가합니다. 트레일링 스탑 및 추세 감지에 유용합니다.",
            "fields.af_start": "가속인자 초기값",
            "fields.af_step": "가속인자 증가분",
            "fields.af_max": "가속인자 최대값",
            "fields.signal_type": "시그널 유형 (상승/하락 반전, 상승/하락 추세)",
        },
    },
)


def calculate_parabolic_sar(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
) -> List[Dict[str, Any]]:
    """
    파라볼릭 SAR 시계열 계산

    Returns:
        [{"sar": float, "trend": "up"/"down"}, ...]
    """
    if len(highs) < 2:
        return []

    results = []
    # 초기화: 첫 봉은 하락 추세로 시작 (SAR = 첫 high)
    is_uptrend = lows[0] < lows[1] if closes[1] > closes[0] else False

    if is_uptrend:
        sar = lows[0]
        ep = highs[0]
    else:
        sar = highs[0]
        ep = lows[0]

    af = af_start

    results.append({
        "sar": round(sar, 4),
        "trend": "up" if is_uptrend else "down",
    })

    for i in range(1, len(highs)):
        prev_sar = sar

        # SAR 업데이트
        sar = prev_sar + af * (ep - prev_sar)

        if is_uptrend:
            # 상승 추세: SAR이 이전 두 봉의 저가보다 높으면 안 됨
            sar = min(sar, lows[i - 1])
            if i >= 2:
                sar = min(sar, lows[i - 2])

            if lows[i] <= sar:
                # 추세 전환: 하락으로
                is_uptrend = False
                sar = ep  # EP가 새 SAR
                ep = lows[i]
                af = af_start
            else:
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_step, af_max)
        else:
            # 하락 추세: SAR이 이전 두 봉의 고가보다 낮으면 안 됨
            sar = max(sar, highs[i - 1])
            if i >= 2:
                sar = max(sar, highs[i - 2])

            if highs[i] >= sar:
                # 추세 전환: 상승으로
                is_uptrend = True
                sar = ep  # EP가 새 SAR
                ep = highs[i]
                af = af_start
            else:
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_step, af_max)

        results.append({
            "sar": round(sar, 4),
            "trend": "up" if is_uptrend else "down",
        })

    return results


async def parabolic_sar_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """파라볼릭 SAR 조건 평가"""
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    af_start = fields.get("af_start", 0.02)
    af_step = fields.get("af_step", 0.02)
    af_max = fields.get("af_max", 0.20)
    signal_type = fields.get("signal_type", "bullish_reversal")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
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
        target_symbols = []
        for s in symbols:
            if isinstance(s, dict):
                target_symbols.append({"symbol": s.get("symbol", ""), "exchange": s.get("exchange", "UNKNOWN")})
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

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])
        if not rows or len(rows) < 2:
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

        if len(highs) < 2:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "Insufficient valid data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        sar_series = calculate_parabolic_sar(highs, lows, closes, af_start, af_step, af_max)

        time_series = []
        for i, sar_val in enumerate(sar_series):
            if i >= len(rows_sorted):
                break
            original_row = rows_sorted[i]

            signal = None
            side = "long"

            if i > 0:
                prev_trend = sar_series[i - 1]["trend"]
                curr_trend = sar_val["trend"]
                if prev_trend == "down" and curr_trend == "up":
                    signal = "buy"
                elif prev_trend == "up" and curr_trend == "down":
                    signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "sar": sar_val["sar"],
                "trend": sar_val["trend"],
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        # 조건 평가
        current = sar_series[-1]
        passed_condition = False

        if signal_type == "uptrend":
            passed_condition = current["trend"] == "up"
        elif signal_type == "downtrend":
            passed_condition = current["trend"] == "down"
        elif len(sar_series) >= 2:
            prev = sar_series[-2]
            if signal_type == "bullish_reversal":
                passed_condition = prev["trend"] == "down" and current["trend"] == "up"
            elif signal_type == "bearish_reversal":
                passed_condition = prev["trend"] == "up" and current["trend"] == "down"

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "sar": current["sar"],
            "trend": current["trend"],
            "current_close": closes[-1],
        })

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
            "indicator": "ParabolicSAR",
            "af_start": af_start,
            "af_step": af_step,
            "af_max": af_max,
            "signal_type": signal_type,
        },
    }


__all__ = ["parabolic_sar_condition", "calculate_parabolic_sar", "PARABOLIC_SAR_SCHEMA"]
