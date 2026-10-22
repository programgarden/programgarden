"""
RegimeDetection (시장 상태 분류) 플러그인

MA 기울기 + ADX + 변동성 백분위로 시장 상태(bull/bear/sideways) 분류.
IfNode 분기와 결합하면 적응형 전략 구축 가능.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {ma_period, adx_period, adx_threshold, vol_lookback}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


REGIME_DETECTION_SCHEMA = PluginSchema(
    id="RegimeDetection",
    name="Market Regime Detection",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Classifies market state as bull, bear, or sideways using MA slope, ADX trend strength, and volatility percentile. Use with IfNode for adaptive strategy routing.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "ma_period": {
            "type": "int",
            "default": 50,
            "title": "MA Period",
            "description": "Moving average period for trend direction",
            "ge": 10,
            "le": 200,
        },
        "adx_period": {
            "type": "int",
            "default": 14,
            "title": "ADX Period",
            "description": "ADX period for trend strength measurement",
            "ge": 5,
            "le": 50,
        },
        "adx_threshold": {
            "type": "float",
            "default": 25.0,
            "title": "ADX Threshold",
            "description": "ADX above this = trending, below = sideways",
            "ge": 10,
            "le": 50,
        },
        "vol_lookback": {
            "type": "int",
            "default": 60,
            "title": "Volatility Lookback",
            "description": "Lookback period for volatility percentile calculation",
            "ge": 20,
            "le": 252,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=[],
    tags=["regime", "trend", "classification", "adaptive"],
    output_fields={
        "regime": {"type": "str", "description": "Market regime classification (bull/bear/sideways)"},
        "confidence": {"type": "float", "description": "Regime classification confidence (0-100)"},
        "adx": {"type": "float", "description": "ADX trend strength value"},
        "ma_slope": {"type": "float", "description": "Moving average slope (% change over 5 periods)"},
        "vol_percentile": {"type": "float", "description": "Current volatility percentile (0-100)"},
    },
    locales={
        "ko": {
            "name": "시장 상태 분류 (Regime Detection)",
            "description": "이동평균 기울기, ADX 추세 강도, 변동성 백분위를 종합하여 시장 상태(강세/약세/횡보)를 분류합니다. IfNode와 결합하면 시장 상태에 따라 다른 전략을 적용할 수 있습니다.",
            "fields.ma_period": "이동평균 기간 (추세 방향 판단)",
            "fields.adx_period": "ADX 기간 (추세 강도 측정)",
            "fields.adx_threshold": "ADX 임계값 (이상=추세, 이하=횡보)",
            "fields.vol_lookback": "변동성 계산 기간",
        },
    },
)


def _calculate_sma(prices: List[float], period: int) -> List[float]:
    """단순 이동평균 시계열"""
    if len(prices) < period:
        return []
    result = []
    for i in range(period - 1, len(prices)):
        avg = sum(prices[i - period + 1:i + 1]) / period
        result.append(avg)
    return result


def _calculate_adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    """ADX 시계열 계산"""
    if len(highs) < period + 1:
        return []

    tr_list = []
    plus_dm_list = []
    minus_dm_list = []

    for i in range(1, len(highs)):
        high_diff = highs[i] - highs[i - 1]
        low_diff = lows[i - 1] - lows[i]

        plus_dm = high_diff if high_diff > low_diff and high_diff > 0 else 0
        minus_dm = low_diff if low_diff > high_diff and low_diff > 0 else 0

        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)

    if len(tr_list) < period:
        return []

    # Wilder smoothing
    atr = sum(tr_list[:period]) / period
    plus_dm_smooth = sum(plus_dm_list[:period]) / period
    minus_dm_smooth = sum(minus_dm_list[:period]) / period

    adx_values = []
    dx_list = []

    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
        plus_dm_smooth = (plus_dm_smooth * (period - 1) + plus_dm_list[i]) / period
        minus_dm_smooth = (minus_dm_smooth * (period - 1) + minus_dm_list[i]) / period

        plus_di = (plus_dm_smooth / atr * 100) if atr > 0 else 0
        minus_di = (minus_dm_smooth / atr * 100) if atr > 0 else 0

        di_sum = plus_di + minus_di
        dx = abs(plus_di - minus_di) / di_sum * 100 if di_sum > 0 else 0
        dx_list.append(dx)

        if len(dx_list) >= period:
            if len(dx_list) == period:
                adx = sum(dx_list) / period
            else:
                adx = (adx_values[-1] * (period - 1) + dx) / period
            adx_values.append(adx)

    return adx_values


def _calculate_volatility_percentile(prices: List[float], lookback: int) -> float:
    """현재 변동성의 백분위 (0~100)"""
    if len(prices) < lookback + 1:
        return 50.0

    returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices)) if prices[i - 1] > 0]
    if len(returns) < lookback:
        return 50.0

    # 20일 롤링 변동성들의 백분위
    vol_window = 20
    if len(returns) < vol_window + 1:
        return 50.0

    vol_series = []
    for i in range(vol_window, len(returns) + 1):
        window = returns[i - vol_window:i]
        mean_r = sum(window) / len(window)
        variance = sum((r - mean_r) ** 2 for r in window) / len(window)
        vol_series.append(variance ** 0.5)

    if not vol_series:
        return 50.0

    current_vol = vol_series[-1]
    below_count = sum(1 for v in vol_series if v <= current_vol)
    return round(below_count / len(vol_series) * 100, 1)


async def regime_detection_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """시장 상태 분류 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    ma_period = fields.get("ma_period", 50)
    adx_period = fields.get("adx_period", 14)
    adx_threshold = fields.get("adx_threshold", 25.0)
    vol_lookback = fields.get("vol_lookback", 60)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False, "analysis": {"error": "No data provided"},
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

    if not symbols:
        symbols = [{"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")} for s in symbol_data_map]

    passed, failed, symbol_results, values = [], [], [], []

    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "No data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        closes = [float(r.get(close_field, 0)) for r in rows_sorted if r.get(close_field) is not None]
        highs = [float(r.get(high_field, 0)) for r in rows_sorted if r.get(high_field) is not None]
        lows = [float(r.get(low_field, 0)) for r in rows_sorted if r.get(low_field) is not None]

        min_required = max(ma_period, adx_period * 2, vol_lookback)
        if len(closes) < min_required:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "insufficient_data", "required": min_required, "got": len(closes)})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 1) MA 기울기 (최근 5일 MA 변화율)
        ma_series = _calculate_sma(closes, ma_period)
        if len(ma_series) >= 5:
            ma_slope = (ma_series[-1] - ma_series[-5]) / ma_series[-5] * 100 if ma_series[-5] > 0 else 0
        else:
            ma_slope = 0

        # 2) ADX
        adx_series = _calculate_adx(highs, lows, closes, adx_period)
        current_adx = adx_series[-1] if adx_series else 0

        # 3) 변동성 백분위
        vol_percentile = _calculate_volatility_percentile(closes, vol_lookback)

        # 레짐 분류
        is_trending = current_adx >= adx_threshold
        trend_direction = "up" if ma_slope > 0 else "down"

        if is_trending and trend_direction == "up":
            regime = "bull"
            confidence = min(current_adx / 50 * 100, 100)
        elif is_trending and trend_direction == "down":
            regime = "bear"
            confidence = min(current_adx / 50 * 100, 100)
        else:
            regime = "sideways"
            confidence = min((adx_threshold - current_adx) / adx_threshold * 100, 100) if current_adx < adx_threshold else 30

        confidence = round(confidence, 1)

        # passed = bull 또는 bear (추세가 있는 상태)
        if regime in ("bull", "bear"):
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "regime": regime, "confidence": confidence,
            "adx": round(current_adx, 2), "ma_slope": round(ma_slope, 4),
            "vol_percentile": vol_percentile,
        })

        # time_series
        time_series = []
        if rows_sorted:
            last_row = rows_sorted[-1]
            signal = "buy" if regime == "bull" else ("sell" if regime == "bear" else None)
            side = "long"
            time_series.append({
                date_field: last_row.get(date_field, ""),
                close_field: last_row.get(close_field),
                "regime": regime,
                "adx": round(current_adx, 2),
                "ma_slope": round(ma_slope, 4),
                "vol_percentile": vol_percentile,
                "confidence": confidence,
                "signal": signal,
                "side": side,
            })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "RegimeDetection",
            "ma_period": ma_period, "adx_period": adx_period,
            "adx_threshold": adx_threshold, "vol_lookback": vol_lookback,
        },
    }


__all__ = ["regime_detection_condition", "REGIME_DETECTION_SCHEMA"]
