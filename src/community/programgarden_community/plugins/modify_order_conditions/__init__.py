"""
Modify Order Conditions - 정정 주문 플러그인

ModifyOrderNode에서 사용하는 정정 플러그인을 등록합니다.
"""


def register_modify_order_plugins() -> None:
    """정정 주문 플러그인 등록"""
    from programgarden_core.registry import PluginRegistry
    
    from .trailing_stop import tracking_price_modifier, TRAILING_STOP_SCHEMA
    
    registry = PluginRegistry()
    
    registry.register(
        plugin_id="TrailingStop",
        plugin_callable=tracking_price_modifier,
        schema=TRAILING_STOP_SCHEMA,
    )


__all__ = ["register_modify_order_plugins"]
