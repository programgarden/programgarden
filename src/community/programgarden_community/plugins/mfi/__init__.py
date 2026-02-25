"""
MFI (Money Flow Index, 자금흐름지수) 플러그인

거래량 가중 RSI. 자금의 유입/유출 강도를 측정합니다.
- Typical Price = (High + Low + Close) / 3
- Money Flow = Typical Price × Volume
- Positive/Negative MF 분리 → Money Flow Ratio → MFI = 100 - (100 / (1 + MFR))

참고: Gene Quong & Avrum Soudack, "Volume-weighted RSI"

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, [volume]}, ...]
- fields: {period, overbought, oversold, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MFI_SCHEMA = PluginSchema(
    id="MFI",
    name="Money Flow Index",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Volume-weighted RSI measuring money flow strength. Uses Typical Price × Volume to identify capital inflow/outflow. Similar to RSI but incorporates volume for higher reliability. Entry when MFI crosses overbought/oversold thresholds.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 14,
            "title": "MFI Period",
            "description": "Lookback period for MFI calculation",
            "ge": 2,
            "le": 100,
        },
        "overbought": {
            "type": "float",
            "default": 80.0,
            "title": "Overbought Level",
            "description": "MFI level indicating overbought condition",
            "ge": 50.0,
            "le": 99.0,
        },
        "oversold": {
            "type": "float",
            "default": 20.0,
            "title": "Oversold Level",
            "description": "MFI level indicating oversold condition",
            "ge": 1.0,
            "le": 50.0,
        },
        "direction": {
            "type": "string",
            "default": "below",
            "title": "Direction",
            "description": "below: buy when MFI < oversold, above: sell when MFI > overbought",
            "enum": ["below", "above"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["volume"],
    tags=["mfi", "money-flow", "volume", "oscillator", "overbought", "oversold"],
    locales={
        "ko": {
            "name": "자금흐름지수 (MFI)",
            "description": "거래량 가중 RSI. Typical Price × Volume으로 자금 유입/유출 분석. RSI와 유사하나 거래량 포함으로 신뢰도 향상.",
            "fields.period": "MFI 기간",
            "fields.overbought": "과매수 기준값",
            "fields.oversold": "과매도 기준값",
            "fields.direction": "방향 (below: MFI < 과매도 시 매수, above: MFI > 과매수 시 매도)",
        },
    },
)


def calculate_mfi(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    period: int = 14,
) -> Optional[float]:
    """
    MFI (Money Flow Index) 계산 (마지막 값)

    Args:
        highs: 고가 리스트
        lows: 저가 리스트
        closes: 종가 리스트
        volumes: 거래량 리스트 (없으면 1.0으로 가정)
        period: 기간

    Returns:
        MFI 값 (0~100) 또는 None
    """
    if len(closes) < period + 1:
        return None

    if len(volumes) < len(closes):
        volumes = [1.0] * len(closes)

    # Typical Price 계산
    typical_prices = [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]

    # Money Flow = TP × Volume
    money_flows = [tp * v for tp, v in zip(typical_prices, volumes)]

    # 마지막 period+1 개 사용
    tp_window = typical_prices[-(period + 1):]
    mf_window = money_flows[-(period + 1):]

    pos_mf = 0.0
    neg_mf = 0.0

    for i in range(1, len(tp_window)):
        if tp_window[i] > tp_window[i - 1]:
            pos_mf += mf_window[i]
        elif tp_window[i] < tp_window[i - 1]:
            neg_mf += mf_window[i]
        # 동일하면 neutral (둘 다 추가 안 함)

    if neg_mf == 0:
        return 100.0

    mfr = pos_mf / neg_mf
    return round(100.0 - (100.0 / (1.0 + mfr)), 4)


def calculate_mfi_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    period: int = 14,
) -> List[float]:
    """
    MFI 시계열 계산

    Returns:
        MFI 값 리스트 (period+1 이후부터 계산 가능)
    """
    if len(closes) < period + 1:
        return []

    if len(volumes) < len(closes):
        volumes = [1.0] * len(closes)

    typical_prices = [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]
    money_flows = [tp * v for tp, v in zip(typical_prices, volumes)]

    results = []
    for i in range(period + 1, len(closes) + 1):
        tp_window = typical_prices[i - period - 1:i]
        mf_window = money_flows[i - period - 1:i]

        pos_mf = 0.0
        neg_mf = 0.0
        for j in range(1, len(tp_window)):
            if tp_window[j] > tp_window[j - 1]:
                pos_mf += mf_window[j]
            elif tp_window[j] < tp_window[j - 1]:
                neg_mf += mf_window[j]

        if neg_mf == 0:
            results.append(100.0 if pos_mf > 0 else 50.0)
        else:
            mfr = pos_mf / neg_mf
            results.append(round(100.0 - (100.0 / (1.0 + mfr)), 4))

    return results


async def mfi_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    MFI 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {period, overbought, oversold, direction}
        field_mapping: 필드명 매핑
        symbols: 평가할 종목 리스트

    Returns:
        표준 플러그인 결과
    """
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")

    period = fields.get("period", 14)
    overbought = fields.get("overbought", 80.0)
    oversold = fields.get("oversold", 20.0)
    direction = fields.get("direction", "below")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
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
        target_symbols = [
            {"symbol": s.get("symbol", ""), "exchange": s.get("exchange", "UNKNOWN")}
            if isinstance(s, dict) else {"symbol": str(s), "exchange": "UNKNOWN"}
            for s in symbols
        ]
    else:
        target_symbols = [
            {"symbol": sym, "exchange": symbol_exchange_map.get(sym, "UNKNOWN")}
            for sym in symbol_data_map.keys()
        ]

    passed, failed, symbol_results, values = [], [], [], []
    min_required = period + 1

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])

        if not rows or len(rows) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "mfi": None,
                "error": f"Insufficient data: need {min_required}, got {len(rows)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        highs_list, lows_list, closes_list, vols_list = [], [], [], []
        for row in rows_sorted:
            try:
                highs_list.append(float(row.get(high_field, row.get(close_field, 0))))
                lows_list.append(float(row.get(low_field, row.get(close_field, 0))))
                closes_list.append(float(row.get(close_field, 0)))
                vols_list.append(float(row.get(volume_field, 1.0) or 1.0))
            except (ValueError, TypeError):
                pass

        if len(closes_list) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "mfi": None,
                "error": "Insufficient price data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # MFI 시계열 계산
        mfi_series = calculate_mfi_series(highs_list, lows_list, closes_list, vols_list, period)
        current_mfi = mfi_series[-1] if mfi_series else None

        # time_series 생성
        start_idx = period + 1
        time_series = []
        for i, mfi_val in enumerate(mfi_series):
            row_idx = start_idx + i - 1
            if row_idx >= len(rows_sorted):
                break
            original_row = rows_sorted[row_idx]

            signal = None
            if direction == "below" and mfi_val < oversold:
                signal = "buy"
            elif direction == "above" and mfi_val > overbought:
                signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                close_field: original_row.get(close_field),
                "mfi": mfi_val,
                "signal": signal,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "mfi": current_mfi,
            "overbought_level": overbought,
            "oversold_level": oversold,
            "current_price": closes_list[-1],
        })

        if current_mfi is not None:
            if direction == "below":
                passed_condition = current_mfi < oversold
            else:
                passed_condition = current_mfi > overbought
            (passed if passed_condition else failed).append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "MFI",
            "period": period,
            "overbought": overbought,
            "oversold": oversold,
            "direction": direction,
            "comparison": f"MFI {'< ' + str(oversold) if direction == 'below' else '> ' + str(overbought)}",
        },
    }


__all__ = ["mfi_condition", "calculate_mfi", "calculate_mfi_series", "MFI_SCHEMA"]
