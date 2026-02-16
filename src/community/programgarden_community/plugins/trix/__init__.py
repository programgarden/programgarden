"""
TRIX (삼중지수이동평균) 플러그인

EMA를 3번 적용하여 노이즈 제거. TRIX 값과 시그널선 교차로 추세 판단.
- bullish_cross: TRIX가 시그널선 상향 돌파
- bearish_cross: TRIX가 시그널선 하향 돌파
- above_zero: TRIX > 0 (상승 추세)
- below_zero: TRIX < 0 (하락 추세)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {period, signal_period, signal_type}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


TRIX_SCHEMA = PluginSchema(
    id="TRIX",
    name="TRIX",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Triple exponential moving average oscillator. Filters noise through triple EMA smoothing. TRIX-signal line crossovers and zero line crossings provide trend signals.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 15,
            "title": "Period",
            "description": "EMA period for triple smoothing",
            "ge": 2,
            "le": 100,
        },
        "signal_period": {
            "type": "int",
            "default": 9,
            "title": "Signal Period",
            "description": "Signal line EMA period",
            "ge": 2,
            "le": 50,
        },
        "signal_type": {
            "type": "string",
            "default": "bullish_cross",
            "title": "Signal Type",
            "description": "Type of TRIX signal",
            "enum": ["bullish_cross", "bearish_cross", "above_zero", "below_zero"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["trend", "momentum", "trix", "ema"],
    locales={
        "ko": {
            "name": "삼중지수이동평균 (TRIX)",
            "description": "EMA를 3번 적용하여 노이즈를 제거합니다. TRIX-시그널선 교차 및 제로라인 교차로 추세를 판단합니다.",
            "fields.period": "EMA 기간 (3중 평활화)",
            "fields.signal_period": "시그널선 EMA 기간",
            "fields.signal_type": "시그널 유형 (교차, 제로라인)",
        },
    },
)


def _ema(values: List[float], period: int) -> List[float]:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    result = [sum(values[:period]) / period]
    for i in range(period, len(values)):
        result.append(values[i] * k + result[-1] * (1 - k))
    return result


def calculate_trix(closes: List[float], period: int = 15) -> Optional[float]:
    """TRIX 단일 값: 3중 EMA의 1일 변화율"""
    ema1 = _ema(closes, period)
    if len(ema1) < period:
        return None
    ema2 = _ema(ema1, period)
    if len(ema2) < period:
        return None
    ema3 = _ema(ema2, period)
    if len(ema3) < 2:
        return None

    if ema3[-2] == 0:
        return 0.0
    return round((ema3[-1] - ema3[-2]) / ema3[-2] * 100, 4)


def calculate_trix_series(
    closes: List[float],
    period: int = 15,
    signal_period: int = 9,
) -> List[Dict[str, Any]]:
    """TRIX 시계열 + 시그널선 + 히스토그램"""
    ema1 = _ema(closes, period)
    if len(ema1) < period:
        return []
    ema2 = _ema(ema1, period)
    if len(ema2) < period:
        return []
    ema3 = _ema(ema2, period)
    if len(ema3) < 2:
        return []

    # TRIX values (변화율)
    trix_values = []
    for i in range(1, len(ema3)):
        if ema3[i - 1] == 0:
            trix_values.append(0.0)
        else:
            trix_values.append((ema3[i] - ema3[i - 1]) / ema3[i - 1] * 100)

    if len(trix_values) < signal_period:
        return [{"trix": round(t, 4), "signal_line": None, "histogram": None} for t in trix_values]

    # 시그널선 = TRIX의 EMA
    signal_line = _ema(trix_values, signal_period)

    results = []
    signal_start = signal_period
    for i, trix in enumerate(trix_values):
        sig_idx = i - signal_start + 1
        if sig_idx >= 0 and sig_idx < len(signal_line):
            sig = signal_line[sig_idx]
            results.append({
                "trix": round(trix, 4),
                "signal_line": round(sig, 4),
                "histogram": round(trix - sig, 4),
            })
        else:
            results.append({"trix": round(trix, 4), "signal_line": None, "histogram": None})

    return results


async def trix_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """TRIX 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")

    period = fields.get("period", 15)
    signal_period = fields.get("signal_period", 9)
    signal_type = fields.get("signal_type", "bullish_cross")

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

        min_required = period * 3 + signal_period
        if not rows or len(rows) < min_required:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "Insufficient data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        closes = []
        for row in rows_sorted:
            try:
                closes.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                pass

        trix_series = calculate_trix_series(closes, period, signal_period)
        if not trix_series:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "Calculation failed"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        start_idx = len(rows_sorted) - len(trix_series)
        time_series = []

        for i, t_val in enumerate(trix_series):
            row_idx = start_idx + i
            if row_idx < 0 or row_idx >= len(rows_sorted):
                continue
            original_row = rows_sorted[row_idx]

            signal = None
            side = "long"
            if t_val["signal_line"] is not None and i > 0:
                prev = trix_series[i - 1]
                if prev["signal_line"] is not None:
                    if prev["trix"] <= prev["signal_line"] and t_val["trix"] > t_val["signal_line"]:
                        signal = "buy"
                    elif prev["trix"] >= prev["signal_line"] and t_val["trix"] < t_val["signal_line"]:
                        signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "trix": t_val["trix"],
                "signal_line": t_val["signal_line"],
                "histogram": t_val["histogram"],
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        current = trix_series[-1]
        passed_condition = False

        if signal_type == "above_zero":
            passed_condition = current["trix"] > 0
        elif signal_type == "below_zero":
            passed_condition = current["trix"] < 0
        elif current["signal_line"] is not None and len(trix_series) >= 2:
            prev = trix_series[-2]
            if prev["signal_line"] is not None:
                if signal_type == "bullish_cross":
                    passed_condition = prev["trix"] <= prev["signal_line"] and current["trix"] > current["signal_line"]
                elif signal_type == "bearish_cross":
                    passed_condition = prev["trix"] >= prev["signal_line"] and current["trix"] < current["signal_line"]

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "trix": current["trix"], "signal_line": current["signal_line"], "histogram": current["histogram"],
        })
        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "TRIX", "period": period, "signal_period": signal_period, "signal_type": signal_type},
    }


__all__ = ["trix_condition", "calculate_trix", "calculate_trix_series", "TRIX_SCHEMA"]
