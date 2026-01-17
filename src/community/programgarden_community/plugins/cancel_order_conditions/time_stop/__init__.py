"""
Time Stop (시간 초과 취소) 플러그인
"""

from datetime import datetime, timedelta
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


TIME_STOP_SCHEMA = PluginSchema(
    id="TimeStop",
    name="Time Stop",
    category=PluginCategory.CANCEL_ORDER,
    version="1.0.0",
    description="Automatically cancels orders if not filled within specified time. Example: Cancel if unfilled after 30 minutes.",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "timeout_minutes": {
            "type": "int",
            "default": 30,
            "title": "Timeout (minutes)",
            "ge": 1,
        },
    },
    tags=["cancel", "timeout"],
    locales={
        "ko": {
            "name": "시간 초과 취소 (Time Stop)",
            "description": "주문 후 일정 시간이 지나도 체결되지 않으면 자동으로 취소합니다. 예: 30분 내 미체결 시 취소.",
            "fields.timeout_minutes": "타임아웃 (분)",
        },
    },
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
