"""
Stop Loss (손절) 플러그인

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


STOP_LOSS_SCHEMA = PluginSchema(
    id="StopLoss",
    name="Stop Loss",
    category=PluginCategory.STRATEGY_CONDITION,
    version="2.0.0",
    description="Sells when losses exceed the set threshold to prevent larger losses. Example: Auto-sell at -3% loss.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "percent": {"type": "float", "default": -3.0, "title": "Stop Loss (%)"},
    },
    required_data=["data"],
    tags=["exit", "risk"],
    locales={
        "ko": {
            "name": "손절 라인 (Stop Loss)",
            "description": "보유 종목의 손실이 설정한 기준을 넘으면 매도하여 더 큰 손실을 방지합니다. 예: -3% 손실 시 자동 매도.",
            "fields.percent": "손절 비율 (%)",
        },
    },
)


async def stop_loss_condition(
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
    
    stop_percent = fields.get("percent", -3.0)
    
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
        
        if pnl_rate <= stop_percent:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)
    
    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "StopLoss", "stop_percent": stop_percent},
    }


__all__ = ["stop_loss_condition", "STOP_LOSS_SCHEMA"]
