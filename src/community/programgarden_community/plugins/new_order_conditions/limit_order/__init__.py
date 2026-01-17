"""
Limit Order (지정가 주문) 플러그인
"""

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


LIMIT_ORDER_SCHEMA = PluginSchema(
    id="LimitOrder",
    name="Limit Order",
    category=PluginCategory.NEW_ORDER,
    version="1.0.0",
    description="Places order at a specified price. Only executes when the price is reached, allowing you to buy/sell at your desired price.",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "side": {
            "type": "string",
            "title": "Buy/Sell",
            "enum": ["buy", "sell"],
            "required": True,
        },
        "price_type": {
            "type": "string",
            "default": "fixed",
            "title": "Price Type",
            "enum": ["fixed", "percent_from_current"],
        },
        "price": {
            "type": "float",
            "title": "Order Price",
            "description": "fixed: absolute price, percent: % from current",
        },
    },
    tags=["order", "limit"],
    locales={
        "ko": {
            "name": "지정가 주문 (Limit Order)",
            "description": "원하는 가격을 지정하여 주문합니다. 해당 가격에 도달해야 체결되므로 원하는 가격에 매수/매도할 수 있습니다.",
            "fields.side": "매수/매도",
            "fields.price_type": "가격 방식",
            "fields.price": "주문 가격",
        },
    },
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
