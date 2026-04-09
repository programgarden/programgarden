"""
HurstExponent (허스트 지수) 플러그인

R/S 분석으로 시계열의 장기 기억 특성을 측정합니다.
H > 0.5: 추세 지속, H < 0.5: 평균회귀, H ≈ 0.5: 랜덤워크

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {min_window, max_window, num_windows, signal_type, h_threshold}
"""

import math
from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


HURST_EXPONENT_SCHEMA = PluginSchema(
    id="HurstExponent",
    name="Hurst Exponent",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Hurst exponent via R/S analysis measures long-term memory of time series. H > 0.5 indicates trending (persistent), H < 0.5 indicates mean-reverting (anti-persistent), H ≈ 0.5 indicates random walk.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "min_window": {
            "type": "int",
            "default": 10,
            "title": "Min Window",
            "description": "Minimum window size for R/S analysis",
            "ge": 5,
            "le": 50,
        },
        "max_window": {
            "type": "int",
            "default": 100,
            "title": "Max Window",
            "description": "Maximum window size for R/S analysis",
            "ge": 20,
            "le": 500,
        },
        "num_windows": {
            "type": "int",
            "default": 10,
            "title": "Number of Windows",
            "description": "Number of different window sizes to test",
            "ge": 5,
            "le": 20,
        },
        "signal_type": {
            "type": "string",
            "default": "trending",
            "title": "Signal Type",
            "description": "Market regime to detect",
            "enum": ["trending", "mean_reverting", "any"],
        },
        "h_threshold": {
            "type": "float",
            "default": 0.55,
            "title": "H Threshold",
            "description": "Hurst threshold for trending classification",
            "ge": 0.50,
            "le": 0.80,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["hurst", "fractal", "regime", "mean-reversion", "trend"],
    output_fields={
        "hurst": {"type": "float", "description": "Hurst exponent value (0-1)"},
        "regime": {"type": "str", "description": "Market regime: trending, mean_reverting, or random_walk"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "허스트 지수",
            "description": "R/S 분석으로 시계열의 장기 기억 특성을 측정합니다. H > 0.5이면 추세 지속, H < 0.5이면 평균회귀, H ≈ 0.5이면 랜덤워크입니다.",
            "fields.min_window": "최소 윈도우 크기",
            "fields.max_window": "최대 윈도우 크기",
            "fields.num_windows": "테스트할 윈도우 수",
            "fields.signal_type": "감지할 시장 레짐 (trending: 추세, mean_reverting: 평균회귀, any: 모두)",
            "fields.h_threshold": "추세 판별 허스트 임계값",
        },
    },
)


def _rs_for_window(returns: List[float], window: int) -> float:
    """특정 윈도우 크기의 평균 R/S 계산"""
    n = len(returns)
    if n < window or window < 2:
        return 0.0

    num_segments = n // window
    if num_segments == 0:
        return 0.0

    rs_values = []
    for seg in range(num_segments):
        start = seg * window
        segment = returns[start : start + window]

        mean_val = sum(segment) / len(segment)
        deviations = [x - mean_val for x in segment]

        cumulative = []
        cumsum = 0.0
        for d in deviations:
            cumsum += d
            cumulative.append(cumsum)

        r = max(cumulative) - min(cumulative)
        s = math.sqrt(sum(d * d for d in deviations) / len(deviations))

        if s > 1e-10:
            rs_values.append(r / s)

    return sum(rs_values) / len(rs_values) if rs_values else 0.0


def calculate_hurst(
    prices: List[float],
    min_window: int = 10,
    max_window: int = 100,
    num_windows: int = 10,
) -> Optional[float]:
    """Hurst 지수 계산 (R/S 분석)

    Returns:
        Hurst 지수 (0-1) 또는 None
    """
    if len(prices) < max_window + 1:
        max_window = len(prices) - 1
    if max_window < min_window + 2:
        return None

    # 로그 수익률
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0 and prices[i] > 0:
            returns.append(math.log(prices[i] / prices[i - 1]))
        else:
            returns.append(0.0)

    if len(returns) < min_window:
        return None

    # 여러 윈도우 크기에서 R/S 계산
    step = max(1, (max_window - min_window) // max(num_windows - 1, 1))
    windows = list(range(min_window, max_window + 1, step))
    if not windows:
        return None

    log_n = []
    log_rs = []

    for w in windows:
        rs = _rs_for_window(returns, w)
        if rs > 0:
            log_n.append(math.log(w))
            log_rs.append(math.log(rs))

    if len(log_n) < 3:
        return None

    # 선형 회귀: log(R/S) = H * log(n) + c
    n_pts = len(log_n)
    sum_x = sum(log_n)
    sum_y = sum(log_rs)
    sum_xy = sum(x * y for x, y in zip(log_n, log_rs))
    sum_x2 = sum(x * x for x in log_n)

    denom = n_pts * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        return None

    h = (n_pts * sum_xy - sum_x * sum_y) / denom
    return round(max(0.0, min(1.0, h)), 4)


def classify_regime(h: float, h_threshold: float) -> str:
    """허스트 지수로 시장 레짐 분류"""
    if h > h_threshold:
        return "trending"
    elif h < (1.0 - h_threshold):
        return "mean_reverting"
    else:
        return "random_walk"


async def hurst_exponent_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Hurst Exponent 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    min_window = fields.get("min_window", 10)
    max_window = fields.get("max_window", 100)
    num_windows = fields.get("num_windows", 10)
    signal_type = fields.get("signal_type", "trending")
    h_threshold = fields.get("h_threshold", 0.55)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False, "analysis": {"error": "No data provided"},
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
            {"symbol": s.get("symbol", "") if isinstance(s, dict) else str(s),
             "exchange": s.get("exchange", "UNKNOWN") if isinstance(s, dict) else "UNKNOWN"}
            for s in symbols
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

        if not rows:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "hurst": None, "regime": "unknown", "current_price": None})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = []
        for row in rows_sorted:
            try:
                prices.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                prices.append(0.0)

        current_price = prices[-1] if prices else None
        h = calculate_hurst(prices, min_window, max_window, num_windows)
        regime = classify_regime(h, h_threshold) if h is not None else "unknown"

        symbol_results.append({"symbol": symbol, "exchange": exchange, "hurst": h, "regime": regime, "current_price": current_price})
        values.append({"symbol": symbol, "exchange": exchange, "time_series": []})

        condition_met = False
        if h is not None:
            if signal_type == "trending":
                condition_met = h > h_threshold
            elif signal_type == "mean_reverting":
                condition_met = h < (1.0 - h_threshold)
            elif signal_type == "any":
                condition_met = h > h_threshold or h < (1.0 - h_threshold)

        (passed if condition_met else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "HurstExponent", "min_window": min_window, "max_window": max_window, "signal_type": signal_type, "h_threshold": h_threshold},
    }


__all__ = ["hurst_exponent_condition", "calculate_hurst", "classify_regime", "HURST_EXPONENT_SCHEMA"]
