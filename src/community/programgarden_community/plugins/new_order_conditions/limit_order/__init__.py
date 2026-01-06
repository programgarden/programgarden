"""
Limit Order (지정가 주문) 플러그인
"""

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


LIMIT_ORDER_SCHEMA = PluginSchema(
    id="LimitOrder",
    name="Limit Order (지정가 주문)",
    category=PluginCategory.NEW_ORDER,
    version="1.0.0",
    description="지정가 주문 실행",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "side": {
            "type": "string",
            "title": "매수/매도",
            "enum": ["buy", "sell"],
            "required": True,
        },
        "price_type": {
            "type": "string",
            "default": "fixed",
            "title": "가격 방식",
            "enum": ["fixed", "percent_from_current"],
        },
        "price": {
            "type": "float",
            "title": "주문 가격",
            "description": "fixed: 고정가격, percent: 현재가 대비 %",
        },
    },
    tags=["order", "limit"],
)


async def limit_order(symbols: list, quantities: dict, prices: dict, fields: dict, context: dict) -> dict:
    """지정가 주문 실행"""
    side = fields.get("side", "buy")
    price_type = fields.get("price_type", "fixed")
    default_price = fields.get("price", 0)
    
    orders = []
    
    for symbol in symbols:
        quantity = quantities.get(symbol, 10)
        price = prices.get(symbol, default_price)
        
        order = {
            "order_id": f"LMT-{symbol}-{side.upper()[:1]}-001",
            "symbol": symbol,
            "side": side,
            "order_type": "limit",
            "quantity": quantity,
            "price": price,
            "status": "submitted",
        }
        orders.append(order)
    
    return {
        "orders": orders,
        "total_count": len(orders),
        "status": "submitted",
    }


__all__ = ["limit_order", "LIMIT_ORDER_SCHEMA"]
