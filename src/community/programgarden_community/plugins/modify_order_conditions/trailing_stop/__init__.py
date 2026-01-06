"""
Trailing Stop (가격 추적 정정) 플러그인
"""

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


TRAILING_STOP_SCHEMA = PluginSchema(
    id="TrailingStop",
    name="Trailing Stop (가격 추적 정정)",
    category=PluginCategory.MODIFY_ORDER,
    version="1.0.0",
    description="현재가를 추적하여 지정가 정정",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "price_gap_percent": {
            "type": "float",
            "default": 0.5,
            "title": "가격 차이 (%)",
            "description": "현재가 대비 주문가 차이",
        },
        "max_modifications": {
            "type": "int",
            "default": 5,
            "title": "최대 정정 횟수",
        },
    },
    tags=["modify", "tracking"],
)


async def tracking_price_modifier(target_orders: list, price_data: dict, fields: dict) -> dict:
    """가격 추적 정정"""
    gap_percent = fields.get("price_gap_percent", 0.5)
    max_mods = fields.get("max_modifications", 5)
    
    modified = []
    
    for order in target_orders:
        symbol = order.get("symbol")
        current_price = price_data.get(symbol, {}).get("current_price", order.get("price", 100))
        
        if order.get("side") == "buy":
            new_price = current_price * (1 - gap_percent / 100)
        else:
            new_price = current_price * (1 + gap_percent / 100)
        
        modified.append({
            "order_id": order.get("order_id"),
            "old_price": order.get("price"),
            "new_price": round(new_price, 2),
            "status": "modified",
        })
    
    return {
        "modified_orders": modified,
        "total_count": len(modified),
    }


__all__ = ["tracking_price_modifier", "TRAILING_STOP_SCHEMA"]
