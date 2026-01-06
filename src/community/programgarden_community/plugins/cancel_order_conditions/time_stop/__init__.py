"""
Time Stop (시간 초과 취소) 플러그인
"""

from datetime import datetime, timedelta
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


TIME_STOP_SCHEMA = PluginSchema(
    id="TimeStop",
    name="Time Stop (시간 초과 취소)",
    category=PluginCategory.CANCEL_ORDER,
    version="1.0.0",
    description="지정 시간 초과 시 미체결 주문 취소",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "timeout_minutes": {
            "type": "int",
            "default": 30,
            "title": "타임아웃 (분)",
            "ge": 1,
        },
    },
    tags=["cancel", "timeout"],
)


async def time_stop_canceller(target_orders: list, fields: dict) -> dict:
    """시간 초과 취소"""
    timeout_minutes = fields.get("timeout_minutes", 30)
    
    cancelled = []
    not_cancelled = []
    
    for order in target_orders:
        order_time_str = order.get("order_time")
        
        if order_time_str:
            try:
                order_time = datetime.fromisoformat(order_time_str)
                elapsed = datetime.now() - order_time
                if elapsed > timedelta(minutes=timeout_minutes):
                    cancelled.append({
                        "order_id": order.get("order_id"),
                        "status": "cancelled",
                        "reason": "timeout",
                    })
                    continue
            except:
                pass
        
        not_cancelled.append(order)
    
    return {
        "cancelled_orders": cancelled,
        "remaining_orders": not_cancelled,
        "total_cancelled": len(cancelled),
    }


__all__ = ["time_stop_canceller", "TIME_STOP_SCHEMA"]
