"""
CalmarRatio (칼마 비율) 플러그인

CAGR / 최대낙폭(MDD) 비율.
높을수록 위험 대비 수익이 좋은 것을 의미합니다.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {lookback, threshold, direction}
"""

import math
from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


CALMAR_RATIO_SCHEMA = PluginSchema(
    id="CalmarRatio",
    name="Calmar Ratio",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Calmar ratio measures CAGR divided by maximum drawdown. Higher values indicate better risk-adjusted returns. Useful for evaluating strategies over longer periods.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {"type": "int", "default": 252, "title": "Lookback Period", "description": "Number of periods (typically 1 year)", "ge": 60, "le": 756},
        "threshold": {"type": "float", "default": 1.0, "title": "Threshold", "description": "Calmar ratio threshold", "ge": -5.0, "le": 20.0},
        "direction": {"type": "string", "default": "above", "title": "Direction", "description": "above: good, below: poor", "enum": ["above", "below"]},
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["calmar", "cagr", "mdd", "performance", "drawdown"],
    output_fields={
        "calmar_ratio": {"type": "float", "description": "Calmar ratio (CAGR / MDD)"},
        "cagr": {"type": "float", "description": "Compound Annual Growth Rate (%)"},
        "max_drawdown": {"type": "float", "description": "Maximum Drawdown (%)"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "칼마 비율",
            "description": "CAGR을 최대낙폭(MDD)으로 나눈 비율입니다. 높을수록 위험 대비 수익이 좋습니다.",
            "fields.lookback": "룩백 기간 (일, 보통 252 = 1년)",
            "fields.threshold": "칼마 비율 임계치",
            "fields.direction": "방향 (above: 양호, below: 부진)",
        },
    },
)


def calculate_calmar(prices: List[float], lookback: int = 252) -> Dict[str, Optional[float]]:
    if len(prices) < lookback + 1:
        return {"calmar_ratio": None, "cagr": None, "max_drawdown": None}

    recent = prices[-(lookback + 1):]
    p_first, p_last = recent[0], recent[-1]

    if p_first <= 0 or p_last <= 0:
        return {"calmar_ratio": None, "cagr": None, "max_drawdown": None}

    # CAGR
    cagr = (p_last / p_first) ** (252 / lookback) - 1

    # MDD
    peak = recent[0]
    max_dd = 0.0
    for p in recent:
        if p > peak:
            peak = p
        dd = (peak - p) / peak
        if dd > max_dd:
            max_dd = dd

    if max_dd < 1e-10:
        calmar = 0.0 if abs(cagr) < 1e-10 else float("inf") if cagr > 0 else float("-inf")
    else:
        calmar = cagr / max_dd

    return {
        "calmar_ratio": round(calmar, 4),
        "cagr": round(cagr * 100, 2),
        "max_drawdown": round(max_dd * 100, 2),
    }


async def calmar_ratio_condition(
    data: List[Dict[str, Any]], fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    lookback = fields.get("lookback", 252)
    threshold = fields.get("threshold", 1.0)
    direction = fields.get("direction", "above")

    if not data or not isinstance(data, list):
        return {"passed_symbols": [], "failed_symbols": [], "symbol_results": [], "values": [], "result": False, "analysis": {"error": "No data provided"}}

    symbol_data_map: Dict[str, List[Dict]] = {}
    symbol_exchange_map: Dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict): continue
        sym = row.get(symbol_field, "")
        if not sym: continue
        if sym not in symbol_data_map:
            symbol_data_map[sym] = []
            symbol_exchange_map[sym] = row.get(exchange_field, "UNKNOWN")
        symbol_data_map[sym].append(row)

    if symbols:
        target_symbols = [{"symbol": s.get("symbol", "") if isinstance(s, dict) else str(s), "exchange": s.get("exchange", "UNKNOWN") if isinstance(s, dict) else "UNKNOWN"} for s in symbols]
    else:
        target_symbols = [{"symbol": sym, "exchange": symbol_exchange_map.get(sym, "UNKNOWN")} for sym in symbol_data_map.keys()]

    passed, failed, symbol_results, values = [], [], [], []

    for sym_info in target_symbols:
        symbol, exchange = sym_info["symbol"], sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}
        rows = symbol_data_map.get(symbol, [])

        if not rows:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "calmar_ratio": None, "cagr": None, "max_drawdown": None, "current_price": None})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = []
        for row in rows_sorted:
            try: prices.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError): prices.append(0.0)

        current_price = prices[-1] if prices else None
        metrics = calculate_calmar(prices, lookback)

        symbol_results.append({"symbol": symbol, "exchange": exchange, **metrics, "current_price": current_price})
        values.append({"symbol": symbol, "exchange": exchange, "time_series": []})

        if metrics["calmar_ratio"] is not None and math.isfinite(metrics["calmar_ratio"]):
            cond = metrics["calmar_ratio"] > threshold if direction == "above" else metrics["calmar_ratio"] < threshold
            (passed if cond else failed).append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "CalmarRatio", "lookback": lookback, "threshold": threshold, "direction": direction},
    }


__all__ = ["calmar_ratio_condition", "calculate_calmar", "CALMAR_RATIO_SCHEMA"]
