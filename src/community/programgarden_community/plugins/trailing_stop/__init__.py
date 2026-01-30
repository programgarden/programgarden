"""
Trailing Stop (가격 추적 정정) 플러그인
"""

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


TRAILING_STOP_SCHEMA = PluginSchema(
    id="TrailingStop",
    name="Trailing Stop",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Automatically adjusts unfilled order prices to track current price. Increases execution probability even when price moves.",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "price_gap_percent": {
            "type": "float",
            "default": 0.5,
            "title": "Price Gap (%)",
            "description": "Difference from current price",
        },
        "max_modifications": {
            "type": "int",
            "default": 5,
            "title": "Max Modifications",
        },
    },
    tags=["modify", "tracking"],
    locales={
        "ko": {
            "name": "가격 추적 정정 (Trailing Stop)",
            "description": "미체결 주문의 가격을 현재가에 맞춰 자동 정정합니다. 주가가 움직여도 체결 확률을 높일 수 있습니다.",
            "fields.price_gap_percent": "가격 차이 (%)",
            "fields.max_modifications": "최대 정정 횟수",
        },
    },
)


async def trailing_stop_condition(target_orders: list, ohlcv_data: dict, fields: dict) -> dict:
    """가격 추적 정정"""
    gap_percent = fields.get("price_gap_percent", 0.5)
    max_mods = fields.get("max_modifications", 5)
    
    modified = []
    
    for order in target_orders:
        symbol = order.get("symbol")
        
        # OHLCV 데이터에서 현재가 추출
        symbol_data = ohlcv_data.get(symbol, {})
        if isinstance(symbol_data, list) and symbol_data:
            current_price = symbol_data[-1].get("close", order.get("price", 100))
        elif isinstance(symbol_data, dict):
            current_price = symbol_data.get("close", symbol_data.get("current_price", order.get("price", 100)))
        else:
            current_price = order.get("price", 100)
        
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


__all__ = ["trailing_stop_condition", "TRAILING_STOP_SCHEMA"]
