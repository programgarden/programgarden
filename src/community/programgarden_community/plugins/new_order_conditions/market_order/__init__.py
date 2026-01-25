"""
Market Order (시장가 주문) 플러그인
"""

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MARKET_ORDER_SCHEMA = PluginSchema(
    id="MarketOrder",
    name="Market Order",
    category=PluginCategory.NEW_ORDER,
    version="1.0.0",
    description="Executes buy/sell immediately at current market price. Use when fast execution is important.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "side": {
            "type": "string",
            "title": "Buy/Sell",
            "enum": ["buy", "sell"],
            "required": True,
        },
        "amount_type": {
            "type": "string",
            "default": "fixed",
            "title": "Amount Type",
            "enum": ["percent_balance", "fixed", "all"],
        },
        "amount": {
            "type": "float",
            "default": 10,
            "title": "Amount or Ratio",
        },
    },
    tags=["order", "market"],
    locales={
        "ko": {
            "name": "시장가 주문 (Market Order)",
            "description": "현재 시장 가격으로 즉시 매수/매도합니다. 빠른 체결이 중요할 때 사용합니다.",
            "fields.side": "매수/매도",
            "fields.amount_type": "수량 계산 방식",
            "fields.amount": "수량 또는 비율",
        },
    },
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
