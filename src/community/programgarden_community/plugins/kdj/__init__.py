"""
KDJ 플러그인

한중일 시장에서 인기 있는 KDJ 지표. 스토캐스틱 확장판으로
J라인(3K-2D)이 더 민감한 매매 신호를 제공합니다.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {n_period, k_smooth, d_smooth, signal_type, overbought, oversold}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


KDJ_SCHEMA = PluginSchema(
    id="KDJ",
    name="KDJ",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="KDJ indicator popular in Asian markets. Extended Stochastic with J line (3K-2D) for sharper signals. Golden/death cross and overbought/oversold detection.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "n_period": {
            "type": "int",
            "default": 9,
            "title": "N Period",
            "description": "RSV calculation period (highest/lowest lookback)",
            "ge": 2,
            "le": 100,
        },
        "k_smooth": {
            "type": "int",
            "default": 3,
            "title": "K Smoothing",
            "description": "K line smoothing period",
            "ge": 1,
            "le": 20,
        },
        "d_smooth": {
            "type": "int",
            "default": 3,
            "title": "D Smoothing",
            "description": "D line smoothing period",
            "ge": 1,
            "le": 20,
        },
        "signal_type": {
            "type": "string",
            "default": "golden_cross",
            "title": "Signal Type",
            "description": "Type of KDJ signal",
            "enum": ["golden_cross", "death_cross", "oversold", "overbought"],
        },
        "overbought": {
            "type": "float",
            "default": 80.0,
            "title": "Overbought Level",
            "description": "J line overbought threshold",
            "ge": 50,
            "le": 100,
        },
        "oversold": {
            "type": "float",
            "default": 20.0,
            "title": "Oversold Level",
            "description": "J line oversold threshold",
            "ge": 0,
            "le": 50,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["open", "volume"],
    tags=["kdj", "stochastic", "oscillator", "asian-market"],
    output_fields={
        "k": {"type": "float", "description": "K line value"},
        "d": {"type": "float", "description": "D line value"},
        "j": {"type": "float", "description": "J line value (3K-2D)"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "KDJ",
            "description": "한중일 시장에서 인기 있는 KDJ 지표입니다. 스토캐스틱 확장판으로 J라인(3K-2D)이 더 민감한 신호를 제공합니다.",
            "fields.n_period": "RSV 계산 기간 (최고가/최저가 룩백)",
            "fields.k_smooth": "K선 스무딩 기간",
            "fields.d_smooth": "D선 스무딩 기간",
            "fields.signal_type": "신호 유형 (골든크로스, 데드크로스, 과매도, 과매수)",
            "fields.overbought": "J선 과매수 기준",
            "fields.oversold": "J선 과매도 기준",
        },
    },
)


def calculate_kdj(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    n_period: int = 9,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> List[Dict[str, float]]:
    """KDJ 시계열 계산

    Returns:
        list of dict: {k, d, j} for each bar
    """
    n = len(closes)
    if n < n_period or n != len(highs) or n != len(lows):
        return []

    result = []
    k_val = 50.0
    d_val = 50.0

    for i in range(n):
        if i < n_period - 1:
            result.append({"k": 50.0, "d": 50.0, "j": 50.0})
            continue

        window_highs = highs[i - n_period + 1 : i + 1]
        window_lows = lows[i - n_period + 1 : i + 1]

        highest = max(window_highs)
        lowest = min(window_lows)

        if highest == lowest:
            rsv = 50.0
        else:
            rsv = (closes[i] - lowest) / (highest - lowest) * 100.0

        # EMA-style smoothing: K = (K_prev * (smooth-1) + RSV) / smooth
        k_val = (k_val * (k_smooth - 1) + rsv) / k_smooth
        d_val = (d_val * (d_smooth - 1) + k_val) / d_smooth
        j_val = 3 * k_val - 2 * d_val

        result.append({
            "k": round(k_val, 2),
            "d": round(d_val, 2),
            "j": round(j_val, 2),
        })

    return result


async def kdj_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """KDJ 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    n_period = fields.get("n_period", 9)
    k_smooth = fields.get("k_smooth", 3)
    d_smooth = fields.get("d_smooth", 3)
    signal_type = fields.get("signal_type", "golden_cross")
    overbought = fields.get("overbought", 80.0)
    oversold = fields.get("oversold", 20.0)

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

    passed = []
    failed = []
    symbol_results = []
    values = []

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "k": None, "d": None, "j": None, "current_price": None,
            })
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
                highs.append(0.0)
                lows.append(0.0)
                closes.append(0.0)

        current_price = closes[-1] if closes else None

        kdj_series = calculate_kdj(highs, lows, closes, n_period, k_smooth, d_smooth)

        k_val = kdj_series[-1]["k"] if kdj_series else None
        d_val = kdj_series[-1]["d"] if kdj_series else None
        j_val = kdj_series[-1]["j"] if kdj_series else None

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "k": k_val, "d": d_val, "j": j_val,
            "current_price": current_price,
        })

        ts = []
        for i, row in enumerate(rows_sorted):
            if i < len(kdj_series):
                entry = {
                    date_field: row.get(date_field, ""),
                    open_field: row.get(open_field),
                    high_field: row.get(high_field),
                    low_field: row.get(low_field),
                    close_field: row.get(close_field),
                    volume_field: row.get(volume_field),
                    "k": kdj_series[i]["k"],
                    "d": kdj_series[i]["d"],
                    "j": kdj_series[i]["j"],
                }
                ts.append(entry)
        values.append({"symbol": symbol, "exchange": exchange, "time_series": ts})

        # 조건 평가
        condition_met = False
        if kdj_series and len(kdj_series) >= 2:
            curr = kdj_series[-1]
            prev = kdj_series[-2]

            if signal_type == "golden_cross":
                condition_met = prev["k"] <= prev["d"] and curr["k"] > curr["d"]
            elif signal_type == "death_cross":
                condition_met = prev["k"] >= prev["d"] and curr["k"] < curr["d"]
            elif signal_type == "oversold":
                condition_met = curr["j"] < oversold
            elif signal_type == "overbought":
                condition_met = curr["j"] > overbought

        (passed if condition_met else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "KDJ",
            "n_period": n_period,
            "k_smooth": k_smooth,
            "d_smooth": d_smooth,
            "signal_type": signal_type,
            "overbought": overbought,
            "oversold": oversold,
        },
    }


__all__ = ["kdj_condition", "calculate_kdj", "KDJ_SCHEMA"]
