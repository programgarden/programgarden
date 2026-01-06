"""
Profit Target (익절) 플러그인

목표 수익률 도달 조건을 평가합니다.
"""

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


PROFIT_TARGET_SCHEMA = PluginSchema(
    id="ProfitTarget",
    name="Profit Target (익절)",
    category=PluginCategory.STRATEGY_CONDITION,
    version="1.0.0",
    description="목표 수익률 도달 조건",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "percent": {
            "type": "float",
            "default": 5.0,
            "title": "목표 수익률 (%)",
            "description": "이 수익률 이상이면 익절",
            "ge": 0.1,
        },
    },
    required_data=["position_data", "price_data"],
    tags=["exit", "profit"],
)


async def profit_target_condition(symbols: list, position_data: dict, price_data: dict, fields: dict) -> dict:
    """익절 조건 평가"""
    target_percent = fields.get("percent", 5.0)
    
    passed = []
    failed = []
    values = {}
    
    for symbol in symbols:
        position = position_data.get(symbol, {})
        avg_price = position.get("avg_price", 100)
        current_price = price_data.get(symbol, {}).get("current_price", 100)
        
        pnl_rate = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
        values[symbol] = {
            "pnl_rate": round(pnl_rate, 2),
            "avg_price": avg_price,
            "current_price": current_price,
        }
        
        if pnl_rate >= target_percent:
            passed.append(symbol)
        else:
            failed.append(symbol)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "ProfitTarget",
            "target_percent": target_percent,
        },
    }


__all__ = ["profit_target_condition", "PROFIT_TARGET_SCHEMA"]
