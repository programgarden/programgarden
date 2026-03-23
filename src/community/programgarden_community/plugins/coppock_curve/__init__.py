"""
CoppockCurve (코폭 커브) 플러그인

장기 ROC + 단기 ROC의 WMA (가중이동평균)로 시장 바닥 매수 신호 감지.
원래 월봉 기준 장기 바닥 전용이었으나, 일봉으로도 활용 가능.
- CoppockCurve = WMA(ROC(long_roc) + ROC(short_roc), wma_period)
- 음수 → 양수 전환 시 강력한 매수 신호

참고: Edwin Coppock (1962), Barron's Magazine

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {long_roc, short_roc, wma_period, signal_mode, use_daily}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


COPPOCK_CURVE_SCHEMA = PluginSchema(
    id="CoppockCurve",
    name="Coppock Curve",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Long-term market bottom detector. Combines Rate of Change over two lookback periods with Weighted Moving Average. Originally designed for monthly data to identify major market bottoms. Zero-line crossover from below is the buy signal. Based on Edwin Coppock (1962).",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "long_roc": {
            "type": "int",
            "default": 14,
            "title": "Long ROC Period",
            "description": "Long-term Rate of Change period (months or days)",
            "ge": 5,
            "le": 30,
        },
        "short_roc": {
            "type": "int",
            "default": 11,
            "title": "Short ROC Period",
            "description": "Short-term Rate of Change period (months or days)",
            "ge": 3,
            "le": 20,
        },
        "wma_period": {
            "type": "int",
            "default": 10,
            "title": "WMA Period",
            "description": "Weighted Moving Average smoothing period",
            "ge": 3,
            "le": 20,
        },
        "signal_mode": {
            "type": "string",
            "default": "zero_cross",
            "title": "Signal Mode",
            "description": "zero_cross: only zero-line upward cross, direction: rising from negative also signals",
            "enum": ["zero_cross", "direction"],
        },
        "use_daily": {
            "type": "bool",
            "default": False,
            "title": "Use Daily",
            "description": "If True, treat periods as days (not months). ROC periods get scaled by 21.",
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["coppock", "momentum", "roc", "wma", "long-term", "market-bottom"],
    output_fields={
        "coppock_value": {"type": "float", "description": "Current Coppock Curve value"},
        "prev_coppock_value": {"type": "float", "description": "Previous period's Coppock Curve value"},
        "zero_cross_up": {"type": "bool", "description": "Whether the curve crossed zero from below (buy signal)"},
        "direction_up": {"type": "bool", "description": "Whether the curve is rising"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "코폭 커브",
            "description": "장기 ROC의 WMA로 시장 바닥 매수 신호 감지 (Coppock 1962). 음수→양수 전환 시 강력한 매수 신호.",
            "fields.long_roc": "장기 ROC 기간",
            "fields.short_roc": "단기 ROC 기간",
            "fields.wma_period": "WMA 기간",
            "fields.signal_mode": "신호 모드 (zero_cross: 0선 돌파만, direction: 상승 전환도 포함)",
            "fields.use_daily": "일봉 모드 (True면 기간을 일 단위로 처리)",
        },
    },
)


def _calc_roc(closes: List[float], period: int) -> Optional[float]:
    """Rate of Change 계산: (current - past) / past * 100"""
    if len(closes) < period + 1:
        return None
    past = closes[-(period + 1)]
    if past == 0:
        return None
    return round((closes[-1] - past) / past * 100.0, 4)


def _calc_wma(values: List[float], period: int) -> Optional[float]:
    """Weighted Moving Average 계산 (선형 가중)"""
    if len(values) < period:
        return None
    window = values[-period:]
    total_weight = period * (period + 1) / 2
    weighted_sum = sum((i + 1) * v for i, v in enumerate(window))
    return round(weighted_sum / total_weight, 4)


def calculate_coppock_curve(
    closes: List[float],
    long_roc: int = 14,
    short_roc: int = 11,
    wma_period: int = 10,
    use_daily: bool = False,
) -> Optional[float]:
    """
    Coppock Curve 현재값 계산

    Args:
        closes: 종가 리스트 (오래된→최신)
        long_roc: 장기 ROC 기간
        short_roc: 단기 ROC 기간
        wma_period: WMA 기간
        use_daily: True면 기간을 일 단위로 처리 (월봉 기간 × 21)

    Returns:
        Coppock Curve 값 또는 None
    """
    if use_daily:
        long_roc_adj = long_roc * 21
        short_roc_adj = short_roc * 21
    else:
        long_roc_adj = long_roc
        short_roc_adj = short_roc

    min_required = long_roc_adj + wma_period + 1
    if len(closes) < min_required:
        return None

    # ROC 시계열 생성 (wma_period 개 필요)
    roc_series = []
    for i in range(wma_period, 0, -1):
        subset = closes[:len(closes) - i + wma_period]
        if len(subset) < max(long_roc_adj, short_roc_adj) + 1:
            return None
        r_long = _calc_roc(subset, long_roc_adj)
        r_short = _calc_roc(subset, short_roc_adj)
        if r_long is None or r_short is None:
            return None
        roc_series.append(r_long + r_short)

    # 현재 ROC 추가
    r_long_now = _calc_roc(closes, long_roc_adj)
    r_short_now = _calc_roc(closes, short_roc_adj)
    if r_long_now is None or r_short_now is None:
        return None
    roc_series.append(r_long_now + r_short_now)

    return _calc_wma(roc_series, wma_period)


def calculate_coppock_series(
    closes: List[float],
    long_roc: int = 14,
    short_roc: int = 11,
    wma_period: int = 10,
    use_daily: bool = False,
) -> List[float]:
    """
    Coppock Curve 시계열 계산

    Returns:
        Coppock Curve 값 리스트
    """
    if use_daily:
        long_roc_adj = long_roc * 21
        short_roc_adj = short_roc * 21
    else:
        long_roc_adj = long_roc
        short_roc_adj = short_roc

    min_required = long_roc_adj + wma_period + 1
    if len(closes) < min_required:
        return []

    results = []
    for i in range(min_required, len(closes) + 1):
        val = calculate_coppock_curve(
            closes[:i], long_roc, short_roc, wma_period, use_daily
        )
        if val is not None:
            results.append(val)

    return results


async def coppock_curve_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Coppock Curve 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {long_roc, short_roc, wma_period, signal_mode, use_daily}
        field_mapping: 필드명 매핑
        symbols: 평가할 종목 리스트

    Returns:
        표준 플러그인 결과
    """
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    long_roc = fields.get("long_roc", 14)
    short_roc = fields.get("short_roc", 11)
    wma_period = fields.get("wma_period", 10)
    signal_mode = fields.get("signal_mode", "zero_cross")
    use_daily = fields.get("use_daily", False)

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

    long_roc_adj = long_roc * 21 if use_daily else long_roc
    short_roc_adj = short_roc * 21 if use_daily else short_roc
    min_required = long_roc_adj + wma_period + 2  # 이전값 비교를 위해 +2

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])

        if not rows or len(rows) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "coppock_value": None,
                "error": f"Insufficient data: need {min_required}, got {len(rows)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        closes = []
        for row in rows_sorted:
            try:
                closes.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                pass

        if len(closes) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "coppock_value": None,
                "error": "Insufficient price data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # Coppock Curve 시계열 계산
        coppock_series = calculate_coppock_series(closes, long_roc, short_roc, wma_period, use_daily)

        if len(coppock_series) < 2:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "coppock_value": None,
                "error": "Insufficient series for signal detection",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        current_val = coppock_series[-1]
        prev_val = coppock_series[-2]

        # 신호 판정
        zero_cross_up = prev_val < 0 and current_val >= 0
        direction_up = current_val > prev_val and current_val < 0  # 음수에서 상승

        # time_series 생성
        start_idx = len(closes) - len(coppock_series)
        time_series = []
        for i, cop_val in enumerate(coppock_series):
            row_idx = start_idx + i
            if row_idx >= len(rows_sorted):
                break
            original_row = rows_sorted[row_idx]
            prev_cop = coppock_series[i - 1] if i > 0 else cop_val
            is_zero_cross = prev_cop < 0 and cop_val >= 0

            time_series.append({
                date_field: original_row.get(date_field, ""),
                close_field: original_row.get(close_field),
                "coppock_value": cop_val,
                "zero_cross_up": is_zero_cross,
                "signal": "buy" if is_zero_cross else None,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "coppock_value": current_val,
            "prev_coppock_value": prev_val,
            "zero_cross_up": zero_cross_up,
            "direction_up": direction_up,
            "current_price": closes[-1],
        })

        # 조건 평가
        if signal_mode == "zero_cross":
            passed_condition = zero_cross_up
        else:  # direction
            passed_condition = zero_cross_up or direction_up

        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "CoppockCurve",
            "long_roc": long_roc,
            "short_roc": short_roc,
            "wma_period": wma_period,
            "signal_mode": signal_mode,
            "use_daily": use_daily,
        },
    }


__all__ = [
    "coppock_curve_condition",
    "calculate_coppock_curve",
    "calculate_coppock_series",
    "_calc_roc",
    "_calc_wma",
    "COPPOCK_CURVE_SCHEMA",
]
