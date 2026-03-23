"""
ElderRay (엘더 레이) 플러그인

Bull Power = High - EMA(close, period)
Bear Power = Low - EMA(close, period)
EMA 방향 + Bull/Bear Power 조합으로 매매 신호.

매수 신호: EMA 상승 + Bear Power 음수에서 상승 (과매도에서 반등)
매도 신호: EMA 하락 + Bull Power 양수에서 하락 (과매수에서 하락)

참고: Alexander Elder (1993), "Trading for a Living"

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {ema_period, signal_mode}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


ELDER_RAY_SCHEMA = PluginSchema(
    id="ElderRay",
    name="Elder Ray",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Measures bull and bear power relative to EMA. Bull Power = High - EMA, Bear Power = Low - EMA. Conservative mode requires EMA trend confirmation + power divergence. Aggressive mode uses power direction only. Based on Alexander Elder (1993).",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "ema_period": {
            "type": "int",
            "default": 13,
            "title": "EMA Period",
            "description": "EMA period for Bull/Bear Power calculation",
            "ge": 5,
            "le": 50,
        },
        "signal_mode": {
            "type": "string",
            "default": "conservative",
            "title": "Signal Mode",
            "description": "conservative: EMA direction + power divergence, aggressive: power direction only",
            "enum": ["conservative", "aggressive"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["open", "volume"],
    tags=["elder-ray", "ema", "bull-power", "bear-power", "trend", "divergence"],
    output_fields={
        "bull_power": {"type": "float", "description": "Bull Power = High - EMA (positive means bulls above EMA)"},
        "bear_power": {"type": "float", "description": "Bear Power = Low - EMA (negative means bears below EMA)"},
        "ema": {"type": "float", "description": "Exponential Moving Average of the close price"},
        "ema_direction": {"type": "str", "description": "EMA trend direction: 'up', 'down', or 'flat'"},
        "signal": {"type": "str", "description": "Trading signal: 'buy', 'sell', or 'neutral'"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "엘더 레이",
            "description": "Bull/Bear Power로 매수/매도 세력 분석. EMA 방향 + Power 다이버전스 조합 (Elder 1993).",
            "fields.ema_period": "EMA 기간",
            "fields.signal_mode": "신호 모드 (conservative: EMA 확인, aggressive: Power 방향만)",
        },
    },
)


def _calc_ema_series(closes: List[float], period: int) -> List[float]:
    """EMA 시계열 계산"""
    if len(closes) < period:
        return []
    k = 2.0 / (period + 1)
    ema_vals = [sum(closes[:period]) / period]
    for i in range(period, len(closes)):
        ema_vals.append(closes[i] * k + ema_vals[-1] * (1 - k))
    return ema_vals


def calculate_elder_ray_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    ema_period: int = 13,
) -> List[Dict[str, Any]]:
    """
    Elder Ray 시계열 계산

    Args:
        highs: 고가 리스트
        lows: 저가 리스트
        closes: 종가 리스트
        ema_period: EMA 기간

    Returns:
        [{"bull_power": float, "bear_power": float, "ema": float, "ema_direction": str}, ...]
    """
    if len(closes) < ema_period + 1:
        return []

    ema_vals = _calc_ema_series(closes, ema_period)
    if not ema_vals:
        return []

    # ema_vals[0]는 closes[ema_period-1]에 해당
    ema_start = ema_period - 1
    results = []

    for i in range(1, len(ema_vals)):
        close_idx = ema_start + i
        if close_idx >= len(closes):
            break

        ema_cur = ema_vals[i]
        ema_prev = ema_vals[i - 1]

        bull_power = highs[close_idx] - ema_cur
        bear_power = lows[close_idx] - ema_cur

        # EMA 방향
        if ema_cur > ema_prev * 1.0001:
            ema_direction = "up"
        elif ema_cur < ema_prev * 0.9999:
            ema_direction = "down"
        else:
            ema_direction = "flat"

        results.append({
            "bull_power": round(bull_power, 4),
            "bear_power": round(bear_power, 4),
            "ema": round(ema_cur, 4),
            "ema_direction": ema_direction,
        })

    return results


def _determine_signal(
    series: List[Dict[str, Any]],
    signal_mode: str,
) -> str:
    """
    Elder Ray 신호 결정

    Args:
        series: Elder Ray 시계열 (최소 2개 필요)
        signal_mode: "conservative" or "aggressive"

    Returns:
        "buy" / "sell" / "neutral"
    """
    if len(series) < 2:
        return "neutral"

    current = series[-1]
    prev = series[-2]

    if signal_mode == "conservative":
        # 매수: EMA 상승 + Bear Power 음수에서 상승 (과매도 반등)
        buy_signal = (
            current["ema_direction"] == "up"
            and current["bear_power"] < 0
            and current["bear_power"] > prev["bear_power"]
        )
        # 매도: EMA 하락 + Bull Power 양수에서 하락 (과매수 하락)
        sell_signal = (
            current["ema_direction"] == "down"
            and current["bull_power"] > 0
            and current["bull_power"] < prev["bull_power"]
        )
    else:  # aggressive
        # 매수: Bear Power가 음수에서 양수로, 또는 Bull Power 상승
        buy_signal = (
            current["bear_power"] > prev["bear_power"]
            and current["ema_direction"] != "down"
        )
        # 매도: Bull Power가 양수에서 음수로, 또는 Bear Power 하락
        sell_signal = (
            current["bull_power"] < prev["bull_power"]
            and current["ema_direction"] != "up"
        )

    if buy_signal:
        return "buy"
    elif sell_signal:
        return "sell"
    return "neutral"


async def elder_ray_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Elder Ray 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {ema_period, signal_mode}
        field_mapping: 필드명 매핑
        symbols: 평가할 종목 리스트

    Returns:
        표준 플러그인 결과
    """
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    ema_period = fields.get("ema_period", 13)
    signal_mode = fields.get("signal_mode", "conservative")

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
    min_required = ema_period + 2  # EMA 안정화 + 이전값 비교

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])

        if not rows or len(rows) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "bull_power": None, "bear_power": None,
                "ema_direction": "flat", "signal": "neutral",
                "error": f"Insufficient data: need {min_required}, got {len(rows)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        highs_list, lows_list, closes_list = [], [], []
        for row in rows_sorted:
            try:
                highs_list.append(float(row.get(high_field, row.get(close_field, 0))))
                lows_list.append(float(row.get(low_field, row.get(close_field, 0))))
                closes_list.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                pass

        if len(closes_list) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "bull_power": None, "bear_power": None,
                "ema_direction": "flat", "signal": "neutral",
                "error": "Insufficient price data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        er_series = calculate_elder_ray_series(highs_list, lows_list, closes_list, ema_period)

        if len(er_series) < 2:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "bull_power": None, "bear_power": None,
                "ema_direction": "flat", "signal": "neutral",
                "error": "Insufficient series for signal",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        current_signal = _determine_signal(er_series, signal_mode)

        # time_series 생성
        start_idx = ema_period  # ema_vals[1]부터 er_series 시작 (index ema_period)
        time_series = []
        for i, er_val in enumerate(er_series):
            row_idx = start_idx + i
            if row_idx >= len(rows_sorted):
                break
            original_row = rows_sorted[row_idx]

            # 개별 신호
            ts_signal = _determine_signal(er_series[:i + 1], signal_mode) if i > 0 else "neutral"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                close_field: original_row.get(close_field),
                "bull_power": er_val["bull_power"],
                "bear_power": er_val["bear_power"],
                "ema": er_val["ema"],
                "ema_direction": er_val["ema_direction"],
                "signal": ts_signal,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        current = er_series[-1]
        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "bull_power": current["bull_power"],
            "bear_power": current["bear_power"],
            "ema": current["ema"],
            "ema_direction": current["ema_direction"],
            "signal": current_signal,
            "current_price": closes_list[-1],
        })

        passed_condition = current_signal == "buy"
        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "ElderRay",
            "ema_period": ema_period,
            "signal_mode": signal_mode,
        },
    }


__all__ = [
    "elder_ray_condition",
    "calculate_elder_ray_series",
    "_calc_ema_series",
    "_determine_signal",
    "ELDER_RAY_SCHEMA",
]
