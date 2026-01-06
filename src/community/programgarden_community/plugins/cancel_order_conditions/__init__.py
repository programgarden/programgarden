"""
Cancel Order Conditions - 취소 주문 플러그인

CancelOrderNode에서 사용하는 취소 플러그인을 등록합니다.
"""


def register_cancel_order_plugins() -> None:
    """취소 주문 플러그인 등록"""
    from programgarden_core.registry import PluginRegistry
    
    from .time_stop import time_stop_canceller, TIME_STOP_SCHEMA
    
    registry = PluginRegistry()
    
    registry.register(
        plugin_id="TimeStop",
        plugin_callable=time_stop_canceller,
        schema=TIME_STOP_SCHEMA,
    )


__all__ = ["register_cancel_order_plugins"]
