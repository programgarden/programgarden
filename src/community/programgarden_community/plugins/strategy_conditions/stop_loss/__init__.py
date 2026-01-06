"""
Stop Loss (손절) 플러그인

손절 조건을 평가합니다.
"""

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


STOP_LOSS_SCHEMA = PluginSchema(
    id="StopLoss",
    name="Stop Loss (손절)",
    category=PluginCategory.STRATEGY_CONDITION,
    version="1.0.0",
    description="손절 조건",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "percent": {
            "type": "float",
            "default": -3.0,
            "title": "손절 비율 (%)",
            "description": "음수 값 (예: -3은 3% 손실시 손절)",
            "le": 0,
        },
    },
    required_data=["position_data", "price_data"],
    tags=["exit", "risk"],
)


async def stop_loss_condition(symbols: list, position_data: dict, price_data: dict, fields: dict) -> dict:
    """손절 조건 평가"""
    stop_percent = fields.get("percent", -3.0)
    
    passed = []
    failed = []
    values = {}
    
    for symbol in symbols:
        position = position_data.get(symbol, {})
        avg_price = position.get("avg_price", 100)
        current_price = price_data.get(symbol, {}).get("current_price", 100)
        
        pnl_rate = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
        values[symbol] = {"pnl_rate": round(pnl_rate, 2)}
        
        if pnl_rate <= stop_percent:
            passed.append(symbol)
        else:
            failed.append(symbol)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "StopLoss",
            "stop_percent": stop_percent,
        },
    }


__all__ = ["stop_loss_condition", "STOP_LOSS_SCHEMA"]
