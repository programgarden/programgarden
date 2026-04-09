"""
SortinoRatio (소르티노 비율) 플러그인

하방 리스크만 고려하는 성과지표.
Sortino = (mean(r) - MAR) / downside_deviation × sqrt(252)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {lookback, mar, threshold, direction}
"""

import math
from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


SORTINO_RATIO_SCHEMA = PluginSchema(
    id="SortinoRatio",
    name="Sortino Ratio",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Sortino ratio measures risk-adjusted return using only downside deviation. Better than Sharpe for asymmetric return distributions as it only penalizes harmful volatility.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {"type": "int", "default": 60, "title": "Lookback Period", "description": "Number of periods", "ge": 20, "le": 500},
        "mar": {"type": "float", "default": 0.0, "title": "Minimum Acceptable Return", "description": "Daily MAR (annualized / 252)", "ge": -0.10, "le": 0.20},
        "threshold": {"type": "float", "default": 1.5, "title": "Threshold", "description": "Sortino ratio threshold", "ge": -5.0, "le": 10.0},
        "direction": {"type": "string", "default": "above", "title": "Direction", "description": "above: good, below: poor", "enum": ["above", "below"]},
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["sortino", "downside-risk", "performance", "monitoring"],
    output_fields={
        "sortino_ratio": {"type": "float", "description": "Annualized Sortino ratio"},
        "downside_deviation": {"type": "float", "description": "Annualized downside deviation (%)"},
        "annualized_return": {"type": "float", "description": "Annualized return (%)"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "소르티노 비율",
            "description": "하방 편차만 사용하는 위험 조정 수익률입니다. 비대칭 수익 분포에서 샤프비율보다 정확합니다.",
            "fields.lookback": "룩백 기간 (일)",
            "fields.mar": "최소 허용 수익률 (일간)",
            "fields.threshold": "소르티노 비율 임계치",
            "fields.direction": "방향 (above: 양호, below: 부진)",
        },
    },
)


def calculate_sortino(prices: List[float], lookback: int = 60, mar: float = 0.0) -> Dict[str, Optional[float]]:
    if len(prices) < lookback + 1:
        return {"sortino_ratio": None, "downside_deviation": None, "annualized_return": None}

    recent = prices[-(lookback + 1):]
    returns = [(recent[i] - recent[i - 1]) / recent[i - 1] for i in range(1, len(recent)) if recent[i - 1] != 0]

    if len(returns) < 2:
        return {"sortino_ratio": None, "downside_deviation": None, "annualized_return": None}

    daily_mar = mar / 252
    downside = [min(r - daily_mar, 0) for r in returns]
    downside_var = sum(d * d for d in downside) / len(downside)
    dd = math.sqrt(downside_var) if downside_var > 0 else 1e-10

    mean_return = sum(returns) / len(returns)
    sortino = ((mean_return - daily_mar) / dd) * math.sqrt(252)
    ann_return = mean_return * 252 * 100
    ann_dd = dd * math.sqrt(252) * 100

    return {
        "sortino_ratio": round(sortino, 4),
        "downside_deviation": round(ann_dd, 2),
        "annualized_return": round(ann_return, 2),
    }


async def sortino_ratio_condition(
    data: List[Dict[str, Any]], fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    lookback = fields.get("lookback", 60)
    mar = fields.get("mar", 0.0)
    threshold = fields.get("threshold", 1.5)
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
            symbol_results.append({"symbol": symbol, "exchange": exchange, "sortino_ratio": None, "downside_deviation": None, "annualized_return": None, "current_price": None})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = []
        for row in rows_sorted:
            try: prices.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError): prices.append(0.0)

        current_price = prices[-1] if prices else None
        metrics = calculate_sortino(prices, lookback, mar)

        symbol_results.append({"symbol": symbol, "exchange": exchange, **metrics, "current_price": current_price})
        values.append({"symbol": symbol, "exchange": exchange, "time_series": []})

        if metrics["sortino_ratio"] is not None:
            cond = metrics["sortino_ratio"] > threshold if direction == "above" else metrics["sortino_ratio"] < threshold
            (passed if cond else failed).append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "SortinoRatio", "lookback": lookback, "mar": mar, "threshold": threshold, "direction": direction},
    }


__all__ = ["sortino_ratio_condition", "calculate_sortino", "SORTINO_RATIO_SCHEMA"]
