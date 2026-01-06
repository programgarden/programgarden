"""
Market Order (시장가 주문) 플러그인
"""

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MARKET_ORDER_SCHEMA = PluginSchema(
    id="MarketOrder",
    name="Market Order (시장가 주문)",
    category=PluginCategory.NEW_ORDER,
    version="1.0.0",
    description="시장가 주문 실행",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "side": {
            "type": "string",
            "title": "매수/매도",
            "enum": ["buy", "sell"],
            "required": True,
        },
        "amount_type": {
            "type": "string",
            "default": "fixed",
            "title": "수량 계산 방식",
            "enum": ["percent_balance", "fixed", "all"],
        },
        "amount": {
            "type": "float",
            "default": 10,
            "title": "수량 또는 비율",
        },
    },
    tags=["order", "market"],
)


async def market_order(symbols: list, quantities: dict, fields: dict, context: dict) -> dict:
    """시장가 주문 실행"""
    side = fields.get("side", "buy")
    amount_type = fields.get("amount_type", "fixed")
    amount = fields.get("amount", 10)
    
    orders = []
    
    for symbol in symbols:
        quantity = quantities.get(symbol, amount)
        
        order = {
            "order_id": f"MKT-{symbol}-{side.upper()[:1]}-001",
            "symbol": symbol,
            "side": side,
            "order_type": "market",
            "quantity": quantity,
            "status": "submitted",
        }
        orders.append(order)
    
    return {
        "orders": orders,
        "total_count": len(orders),
        "status": "submitted",
    }


__all__ = ["market_order", "MARKET_ORDER_SCHEMA"]
