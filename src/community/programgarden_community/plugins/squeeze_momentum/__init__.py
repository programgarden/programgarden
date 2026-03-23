"""
Squeeze Momentum (스퀴즈 모멘텀) 플러그인

BB(볼린저밴드)가 KC(켈트너채널) 안쪽 = squeeze on → 밖으로 나가면 = squeeze fire + 선형회귀 모멘텀 방향.
BB/KC와 차별: 두 채널의 상호작용(스퀴즈 발화) 분석.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {bb_period, bb_std, kc_period, kc_atr_period, kc_multiplier, momentum_period, direction}
"""

import math
from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


SQUEEZE_MOMENTUM_SCHEMA = PluginSchema(
    id="SqueezeMomentum",
    name="Squeeze Momentum",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Detects Bollinger Band squeeze inside Keltner Channel. When BB contracts inside KC, volatility is compressed (squeeze on). When BB expands outside KC, a squeeze fires with momentum direction from linear regression. Combines volatility contraction and momentum for high-probability entries.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "bb_period": {
            "type": "int",
            "default": 20,
            "title": "BB Period",
            "description": "Bollinger Bands period",
            "ge": 5,
            "le": 100,
        },
        "bb_std": {
            "type": "float",
            "default": 2.0,
            "title": "BB Std Dev",
            "description": "Bollinger Bands standard deviation multiplier",
            "ge": 1.0,
            "le": 4.0,
        },
        "kc_period": {
            "type": "int",
            "default": 20,
            "title": "KC Period",
            "description": "Keltner Channel EMA period",
            "ge": 5,
            "le": 100,
        },
        "kc_atr_period": {
            "type": "int",
            "default": 10,
            "title": "KC ATR Period",
            "description": "Keltner Channel ATR period",
            "ge": 2,
            "le": 50,
        },
        "kc_multiplier": {
            "type": "float",
            "default": 1.5,
            "title": "KC Multiplier",
            "description": "Keltner Channel ATR multiplier",
            "ge": 0.5,
            "le": 4.0,
        },
        "momentum_period": {
            "type": "int",
            "default": 12,
            "title": "Momentum Period",
            "description": "Linear regression momentum lookback",
            "ge": 3,
            "le": 50,
        },
        "direction": {
            "type": "string",
            "default": "squeeze_fire_long",
            "title": "Direction",
            "description": "Signal direction",
            "enum": ["squeeze_fire_long", "squeeze_fire_short", "squeeze_on", "squeeze_off"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["open", "volume"],
    tags=["squeeze", "momentum", "bollinger", "keltner", "volatility"],
    output_fields={
        "squeeze_on": {"type": "bool", "description": "Whether Bollinger Band is inside Keltner Channel (volatility compression)"},
        "squeeze_fire": {"type": "bool", "description": "Whether a squeeze just fired (previous squeeze_on → current squeeze_off)"},
        "momentum": {"type": "float", "description": "Linear regression momentum value (positive = bullish, negative = bearish)"},
        "momentum_direction": {"type": "str", "description": "Momentum direction: 'long' or 'short'"},
        "current_close": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "스퀴즈 모멘텀",
            "description": "볼린저밴드가 켈트너채널 안쪽으로 들어가면 변동성 축소(스퀴즈 온), 밖으로 나가면 스퀴즈 발화 + 선형회귀 모멘텀 방향으로 진입합니다. 변동성 축소와 모멘텀을 결합한 고확률 진입 전략입니다.",
            "fields.bb_period": "볼린저밴드 기간",
            "fields.bb_std": "볼린저밴드 표준편차 배수",
            "fields.kc_period": "켈트너채널 EMA 기간",
            "fields.kc_atr_period": "켈트너채널 ATR 기간",
            "fields.kc_multiplier": "켈트너채널 ATR 배수",
            "fields.momentum_period": "선형회귀 모멘텀 기간",
            "fields.direction": "방향 (squeeze_fire_long/short: 발화+방향, squeeze_on/off: 스퀴즈 상태)",
        },
    },
)


def _sma(values: List[float], period: int) -> float:
    """단순 이동평균"""
    if len(values) < period:
        return sum(values) / len(values) if values else 0.0
    return sum(values[-period:]) / period


def _std(values: List[float], period: int) -> float:
    """표준편차 (모집단)"""
    if len(values) < period:
        subset = values
    else:
        subset = values[-period:]
    if len(subset) < 2:
        return 0.0
    mean = sum(subset) / len(subset)
    variance = sum((x - mean) ** 2 for x in subset) / len(subset)
    return math.sqrt(variance)


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


def _linear_regression_value(values: List[float]) -> float:
    """선형회귀 최종값 (순수 Python, numpy 없이)"""
    n = len(values)
    if n < 2:
        return 0.0

    sum_x = n * (n - 1) / 2
    sum_y = sum(values)
    sum_xy = sum(i * v for i, v in enumerate(values))
    sum_x2 = n * (n - 1) * (2 * n - 1) / 6

    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    return slope * (n - 1) + intercept


def calculate_squeeze_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    bb_period: int = 20,
    bb_std: float = 2.0,
    kc_period: int = 20,
    kc_atr_period: int = 10,
    kc_multiplier: float = 1.5,
    momentum_period: int = 12,
) -> List[Dict[str, Any]]:
    """
    스퀴즈 모멘텀 시계열 계산

    Returns:
        [{"squeeze_on": bool, "momentum": float, "bb_upper/lower": float, "kc_upper/lower": float}, ...]
    """
    min_required = max(bb_period, kc_period, kc_atr_period, momentum_period) + 1
    if len(closes) < min_required:
        return []

    # KC 계산
    ema_vals = _ema(closes, kc_period)
    atr_vals = _atr_series(highs, lows, closes, kc_atr_period)

    if not ema_vals or not atr_vals:
        return []

    # 시작 인덱스 결정 (모든 시리즈가 유효한 첫 인덱스)
    ema_start = kc_period  # ema_vals[0] corresponds to index kc_period
    atr_start = kc_atr_period  # atr_vals[0] corresponds to index kc_atr_period
    start = max(ema_start, atr_start, bb_period, momentum_period)

    results = []
    for i in range(start, len(closes) + 1):
        # BB 계산
        bb_window = closes[i - bb_period:i]
        bb_mean = sum(bb_window) / bb_period
        bb_variance = sum((x - bb_mean) ** 2 for x in bb_window) / bb_period
        bb_std_val = math.sqrt(bb_variance)
        bb_upper = bb_mean + bb_std * bb_std_val
        bb_lower = bb_mean - bb_std * bb_std_val

        # KC 계산
        ema_idx = i - ema_start
        atr_idx = i - atr_start
        if ema_idx < 0 or ema_idx >= len(ema_vals) or atr_idx < 0 or atr_idx >= len(atr_vals):
            continue
        kc_mid = ema_vals[ema_idx]
        kc_atr = atr_vals[atr_idx]
        kc_upper = kc_mid + kc_multiplier * kc_atr
        kc_lower = kc_mid - kc_multiplier * kc_atr

        # Squeeze 판정: BB가 KC 안쪽이면 squeeze on
        squeeze_on = bb_lower > kc_lower and bb_upper < kc_upper

        # 모멘텀: 선형회귀
        mom_window = closes[i - momentum_period:i]
        momentum = _linear_regression_value(mom_window) - closes[i - 1]

        results.append({
            "squeeze_on": squeeze_on,
            "momentum": round(momentum, 4),
            "bb_upper": round(bb_upper, 4),
            "bb_lower": round(bb_lower, 4),
            "kc_upper": round(kc_upper, 4),
            "kc_lower": round(kc_lower, 4),
            "bb_mean": round(bb_mean, 4),
            "kc_mid": round(kc_mid, 4),
        })

    return results


async def squeeze_momentum_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """스퀴즈 모멘텀 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    bb_period = fields.get("bb_period", 20)
    bb_std = fields.get("bb_std", 2.0)
    kc_period = fields.get("kc_period", 20)
    kc_atr_period = fields.get("kc_atr_period", 10)
    kc_multiplier = fields.get("kc_multiplier", 1.5)
    momentum_period = fields.get("momentum_period", 12)
    direction = fields.get("direction", "squeeze_fire_long")

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
    min_required = max(bb_period, kc_period, kc_atr_period, momentum_period) + 1

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

        sq_series = calculate_squeeze_series(
            highs, lows, closes, bb_period, bb_std, kc_period, kc_atr_period, kc_multiplier, momentum_period,
        )

        if not sq_series:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "Calculation failed"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # squeeze fire 감지: 이전 squeeze_on → 현재 squeeze_off (+ 모멘텀 방향)
        start_idx = len(rows_sorted) - len(sq_series)
        time_series = []

        for i, sq_val in enumerate(sq_series):
            row_idx = start_idx + i
            if row_idx < 0 or row_idx >= len(rows_sorted):
                continue
            original_row = rows_sorted[row_idx]

            # squeeze fire 판정
            prev_squeeze = sq_series[i - 1]["squeeze_on"] if i > 0 else False
            squeeze_fire = prev_squeeze and not sq_val["squeeze_on"]

            signal = None
            side = "long"
            if squeeze_fire:
                if sq_val["momentum"] > 0:
                    signal = "buy"
                    side = "long"
                else:
                    signal = "sell"
                    side = "short"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "squeeze_on": sq_val["squeeze_on"],
                "squeeze_fire": squeeze_fire,
                "momentum": sq_val["momentum"],
                "bb_upper": sq_val["bb_upper"],
                "bb_lower": sq_val["bb_lower"],
                "kc_upper": sq_val["kc_upper"],
                "kc_lower": sq_val["kc_lower"],
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        # 현재 상태
        current = sq_series[-1]
        prev = sq_series[-2] if len(sq_series) > 1 else {"squeeze_on": False}
        current_fire = prev["squeeze_on"] and not current["squeeze_on"]

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "squeeze_on": current["squeeze_on"],
            "squeeze_fire": current_fire,
            "momentum": current["momentum"],
            "momentum_direction": "long" if current["momentum"] > 0 else "short",
            "current_close": closes[-1],
        })

        # 조건 평가
        if direction == "squeeze_fire_long":
            passed_condition = current_fire and current["momentum"] > 0
        elif direction == "squeeze_fire_short":
            passed_condition = current_fire and current["momentum"] < 0
        elif direction == "squeeze_on":
            passed_condition = current["squeeze_on"]
        else:  # squeeze_off
            passed_condition = not current["squeeze_on"]

        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "SqueezeMomentum",
            "bb_period": bb_period,
            "bb_std": bb_std,
            "kc_period": kc_period,
            "kc_atr_period": kc_atr_period,
            "kc_multiplier": kc_multiplier,
            "momentum_period": momentum_period,
            "direction": direction,
        },
    }


__all__ = ["squeeze_momentum_condition", "calculate_squeeze_series", "SQUEEZE_MOMENTUM_SCHEMA"]
