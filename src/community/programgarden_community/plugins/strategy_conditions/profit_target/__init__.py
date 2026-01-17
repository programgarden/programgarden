"""
Profit Target (익절) 플러그인

입력 형식 (ConditionNode와 통일):
- data: 평탄화된 배열 [{date, close, symbol, exchange, ...}, ...]
- fields: {percent}
- field_mapping: {close_field, symbol_field, exchange_field}
- symbols: [{exchange, symbol}, ...]
- position_data: 포지션 정보 (선택)
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


PROFIT_TARGET_SCHEMA = PluginSchema(
    id="ProfitTarget",
    name="Profit Target",
    category=PluginCategory.STRATEGY_CONDITION,
    version="2.0.0",
    description="Checks if holdings have reached the target profit rate. Example: Sell to realize profit when gain exceeds 5%.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "percent": {"type": "float", "default": 5.0, "title": "Target Profit (%)"},
    },
    required_data=["data"],
    tags=["exit", "profit"],
    locales={
        "ko": {
            "name": "목표 수익률 (Profit Target)",
            "description": "보유 종목이 목표 수익률에 도달했는지 확인합니다. 예: 5% 이상 수익이 나면 매도하여 수익 실현.",
            "fields.percent": "목표 수익률 (%)",
        },
    },
)


async def profit_target_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    position_data: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> dict:
    if field_mapping is None:
        field_mapping = {}
    if position_data is None:
        position_data = {}
    
    close_field = field_mapping.get("close_field", "close")
    symbol_field = field_mapping.get("symbol_field", "symbol")
    exchange_field = field_mapping.get("exchange_field", "exchange")
    
    target_percent = fields.get("percent", 5.0)
    
    if not data:
        return {"passed_symbols": [], "failed_symbols": symbols or [], "symbol_results": [], "values": [], "result": False}
    
    grouped_data: Dict[str, List[Dict[str, Any]]] = {}
    symbol_exchange_map: Dict[str, str] = {}
    
    for row in data:
        sym = row.get(symbol_field, "UNKNOWN")
        if sym not in grouped_data:
            grouped_data[sym] = []
            symbol_exchange_map[sym] = row.get(exchange_field, "UNKNOWN")
        grouped_data[sym].append(row)
    
    if not symbols:
        symbols = [{"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")} for s in grouped_data.keys()]
    
    passed, failed, symbol_results, values = [], [], [], []
    
    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else symbol_exchange_map.get(symbol, "UNKNOWN")
        sym_dict = {"exchange": exchange, "symbol": symbol}
        
        position = position_data.get(symbol, {})
        avg_price = position.get("avg_price", 100)
        
        symbol_data = grouped_data.get(symbol, [])
        if symbol_data:
            current_price = float(symbol_data[-1].get(close_field, 100))
        else:
            current_price = 100
        
        pnl_rate = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
        symbol_results.append({"symbol": symbol, "exchange": exchange, "pnl_rate": round(pnl_rate, 2), "current_price": current_price})
        values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
        
        if pnl_rate >= target_percent:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)
    
    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "ProfitTarget", "target_percent": target_percent},
    }


__all__ = ["profit_target_condition", "PROFIT_TARGET_SCHEMA"]
