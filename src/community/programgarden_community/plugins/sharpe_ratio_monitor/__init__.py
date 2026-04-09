"""
SharpeRatioMonitor (샤프비율 모니터) 플러그인

실시간 샤프비율 추적 + 임계치 알림.
Sharpe = (mean(excess_return) / std(excess_return)) × sqrt(252)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {lookback, risk_free_rate, threshold, direction}
"""

import math
from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


SHARPE_RATIO_MONITOR_SCHEMA = PluginSchema(
    id="SharpeRatioMonitor",
    name="Sharpe Ratio Monitor",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Monitors annualized Sharpe ratio in real-time. Alerts when Sharpe falls below or exceeds threshold. Uses daily returns and risk-free rate adjustment.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int", "default": 60, "title": "Lookback Period",
            "description": "Number of periods for Sharpe calculation", "ge": 20, "le": 500,
        },
        "risk_free_rate": {
            "type": "float", "default": 0.04, "title": "Risk-Free Rate",
            "description": "Annual risk-free rate", "ge": 0.0, "le": 0.20,
        },
        "threshold": {
            "type": "float", "default": 1.0, "title": "Threshold",
            "description": "Sharpe ratio threshold", "ge": -5.0, "le": 10.0,
        },
        "direction": {
            "type": "string", "default": "above", "title": "Direction",
            "description": "above: good performance, below: poor performance",
            "enum": ["above", "below"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["sharpe", "performance", "risk-adjusted", "monitoring"],
    output_fields={
        "sharpe_ratio": {"type": "float", "description": "Annualized Sharpe ratio"},
        "annualized_return": {"type": "float", "description": "Annualized return (%)"},
        "annualized_volatility": {"type": "float", "description": "Annualized volatility (%)"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "샤프비율 모니터",
            "description": "연율화 샤프비율을 실시간으로 추적합니다. 임계치 초과/미달 시 알림을 발생시킵니다.",
            "fields.lookback": "룩백 기간 (일)",
            "fields.risk_free_rate": "무위험이자율 (연율)",
            "fields.threshold": "샤프비율 임계치",
            "fields.direction": "방향 (above: 양호, below: 부진)",
        },
    },
)


def calculate_sharpe(prices: List[float], lookback: int = 60, risk_free_rate: float = 0.04) -> Dict[str, Optional[float]]:
    """샤프비율 계산"""
    if len(prices) < lookback + 1:
        return {"sharpe_ratio": None, "annualized_return": None, "annualized_volatility": None}

    recent = prices[-(lookback + 1):]
    returns = [(recent[i] - recent[i - 1]) / recent[i - 1] for i in range(1, len(recent)) if recent[i - 1] != 0]

    if len(returns) < 2:
        return {"sharpe_ratio": None, "annualized_return": None, "annualized_volatility": None}

    daily_rf = risk_free_rate / 252
    excess = [r - daily_rf for r in returns]

    mean_excess = sum(excess) / len(excess)
    variance = sum((r - mean_excess) ** 2 for r in excess) / (len(excess) - 1)
    std_excess = math.sqrt(variance) if variance > 0 else 1e-10

    sharpe = (mean_excess / std_excess) * math.sqrt(252)
    ann_return = sum(returns) / len(returns) * 252 * 100
    ann_vol = std_excess * math.sqrt(252) * 100

    return {
        "sharpe_ratio": round(sharpe, 4),
        "annualized_return": round(ann_return, 2),
        "annualized_volatility": round(ann_vol, 2),
    }


async def sharpe_ratio_monitor_condition(
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
    risk_free_rate = fields.get("risk_free_rate", 0.04)
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
            symbol_results.append({"symbol": symbol, "exchange": exchange, "sharpe_ratio": None, "annualized_return": None, "annualized_volatility": None, "current_price": None})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = []
        for row in rows_sorted:
            try: prices.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError): prices.append(0.0)

        current_price = prices[-1] if prices else None
        metrics = calculate_sharpe(prices, lookback, risk_free_rate)

        symbol_results.append({"symbol": symbol, "exchange": exchange, **metrics, "current_price": current_price})
        values.append({"symbol": symbol, "exchange": exchange, "time_series": []})

        if metrics["sharpe_ratio"] is not None:
            cond = metrics["sharpe_ratio"] > threshold if direction == "above" else metrics["sharpe_ratio"] < threshold
            (passed if cond else failed).append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "SharpeRatioMonitor", "lookback": lookback, "risk_free_rate": risk_free_rate, "threshold": threshold, "direction": direction},
    }


__all__ = ["sharpe_ratio_monitor_condition", "calculate_sharpe", "SHARPE_RATIO_MONITOR_SCHEMA"]
