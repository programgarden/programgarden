"""
Keltner Channel (켈트너 채널) 플러그인

EMA + ATR 기반 채널. 볼린저밴드와 함께 사용하면 "스퀴즈" 전략 가능.
- above_upper: 가격이 상단 밴드 위 (강한 상승)
- below_lower: 가격이 하단 밴드 아래 (강한 하락)
- squeeze: 볼린저밴드가 켈트너 채널 내부 (변동성 축소)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {ema_period, atr_period, multiplier, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


KELTNER_CHANNEL_SCHEMA = PluginSchema(
    id="KeltnerChannel",
    name="Keltner Channel",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="EMA + ATR based channel. Price above upper band indicates strong uptrend, below lower band indicates strong downtrend. Squeeze detection with Bollinger Bands.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "ema_period": {
            "type": "int",
            "default": 20,
            "title": "EMA Period",
            "description": "EMA calculation period for middle band",
            "ge": 2,
            "le": 200,
        },
        "atr_period": {
            "type": "int",
            "default": 10,
            "title": "ATR Period",
            "description": "ATR calculation period for band width",
            "ge": 2,
            "le": 100,
        },
        "multiplier": {
            "type": "float",
            "default": 1.5,
            "title": "Multiplier",
            "description": "ATR multiplier",
            "ge": 0.5,
            "le": 5.0,
        },
        "direction": {
            "type": "string",
            "default": "above_upper",
            "title": "Direction",
            "description": "Signal direction",
            "enum": ["above_upper", "below_lower", "squeeze"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["open", "volume"],
    tags=["channel", "keltner", "atr", "ema", "squeeze"],
    output_fields={
        "middle": {"type": "float", "description": "Middle band (EMA of close)"},
        "upper": {"type": "float", "description": "Upper band (middle + multiplier * ATR)"},
        "lower": {"type": "float", "description": "Lower band (middle - multiplier * ATR)"},
        "current_close": {"type": "float", "description": "Current close price"},
    },
    locales={
        "ko": {
            "name": "켈트너 채널",
            "description": "EMA + ATR 기반 채널입니다. 가격이 상단 밴드 위면 강한 상승, 하단 밴드 아래면 강한 하락입니다. 볼린저밴드와 스퀴즈 전략에 활용합니다.",
            "fields.ema_period": "EMA 기간 (중간 밴드)",
            "fields.atr_period": "ATR 기간 (밴드 폭)",
            "fields.multiplier": "ATR 배수",
            "fields.direction": "방향 (above_upper: 상단 돌파, below_lower: 하단 돌파, squeeze: 변동성 축소)",
        },
    },
)


def _ema(values: List[float], period: int) -> List[float]:
    """EMA 시계열"""
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    ema_vals = [sum(values[:period]) / period]
    for i in range(period, len(values)):
        ema_vals.append(values[i] * k + ema_vals[-1] * (1 - k))
    return ema_vals


def _atr_series(highs: List[float], lows: List[float], closes: List[float], period: int) -> List[float]:
    """ATR 시계열"""
    if len(highs) < 2:
        return []
    trs = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    if len(trs) < period:
        return []
    first = sum(trs[:period]) / period
    atrs = [first]
    for i in range(period, len(trs)):
        atrs.append((atrs[-1] * (period - 1) + trs[i]) / period)
    return atrs


def calculate_keltner(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 1.5,
) -> List[Dict[str, float]]:
    """켈트너 채널 시계열"""
    ema_vals = _ema(closes, ema_period)
    atr_vals = _atr_series(highs, lows, closes, atr_period)

    if not ema_vals or not atr_vals:
        return []

    # 두 시리즈의 시작 인덱스 맞추기
    ema_start = ema_period
    atr_start = atr_period
    start = max(ema_start, atr_start)

    results = []
    for i in range(start, len(closes) + 1):
        ema_idx = i - ema_start
        atr_idx = i - atr_start
        if ema_idx < 0 or ema_idx >= len(ema_vals) or atr_idx < 0 or atr_idx >= len(atr_vals):
            continue
        mid = ema_vals[ema_idx]
        atr = atr_vals[atr_idx]
        results.append({
            "middle": round(mid, 4),
            "upper": round(mid + multiplier * atr, 4),
            "lower": round(mid - multiplier * atr, 4),
        })

    return results


async def keltner_channel_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """켈트너 채널 조건 평가"""
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    ema_period = fields.get("ema_period", 20)
    atr_period = fields.get("atr_period", 10)
    multiplier = fields.get("multiplier", 1.5)
    direction = fields.get("direction", "above_upper")

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
    min_required = max(ema_period, atr_period) + 1

    for sym_info in target_symbols:
        symbol, exchange = sym_info["symbol"], sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}
        rows = symbol_data_map.get(symbol, [])

        if not rows or len(rows) < min_required:
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

        kc_series = calculate_keltner(highs, lows, closes, ema_period, atr_period, multiplier)
        if not kc_series:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "Calculation failed"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        start_idx = len(rows_sorted) - len(kc_series)
        time_series = []

        for i, kc_val in enumerate(kc_series):
            row_idx = start_idx + i
            if row_idx < 0 or row_idx >= len(rows_sorted):
                continue
            original_row = rows_sorted[row_idx]
            current_close = closes[row_idx]

            signal = None
            side = "long"
            if current_close > kc_val["upper"]:
                signal = "buy"
            elif current_close < kc_val["lower"]:
                signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "middle": kc_val["middle"],
                "upper": kc_val["upper"],
                "lower": kc_val["lower"],
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        current_kc = kc_series[-1]
        current_close = closes[-1]

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "middle": current_kc["middle"], "upper": current_kc["upper"], "lower": current_kc["lower"],
            "current_close": current_close,
        })

        if direction == "above_upper":
            passed_condition = current_close > current_kc["upper"]
        elif direction == "below_lower":
            passed_condition = current_close < current_kc["lower"]
        else:  # squeeze - Bollinger Bands 내부에 있는지 (간이 체크: 가격이 채널 내부)
            passed_condition = current_kc["lower"] <= current_close <= current_kc["upper"]

        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "KeltnerChannel", "ema_period": ema_period, "atr_period": atr_period, "multiplier": multiplier, "direction": direction},
    }


__all__ = ["keltner_channel_condition", "calculate_keltner", "KELTNER_CHANNEL_SCHEMA"]
