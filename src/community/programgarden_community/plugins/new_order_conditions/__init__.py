"""
New Order Conditions - 신규 주문 플러그인

NewOrderNode에서 사용하는 주문 플러그인을 등록합니다.
"""


def register_new_order_plugins() -> None:
    """신규 주문 플러그인 등록"""
    from programgarden_core.registry import PluginRegistry
    
    from .market_order import market_order, MARKET_ORDER_SCHEMA
    from .limit_order import limit_order, LIMIT_ORDER_SCHEMA
    
    registry = PluginRegistry()
    
    registry.register(
        plugin_id="MarketOrder",
        plugin_callable=market_order,
        schema=MARKET_ORDER_SCHEMA,
    )
    
    registry.register(
        plugin_id="LimitOrder",
        plugin_callable=limit_order,
        schema=LIMIT_ORDER_SCHEMA,
    )


__all__ = ["register_new_order_plugins"]
