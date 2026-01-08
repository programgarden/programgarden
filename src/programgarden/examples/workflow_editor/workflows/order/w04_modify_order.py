"""03_order/w04_modify_order - 주문 정정"""


def get_workflow():
    return {
        "id": "order-04-modify",
        "version": "1.0.0",
        "name": "주문 정정 예제",
        "description": "미체결 주문 가격 추적 정정",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 0, "y": 200},
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "category": "infra",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "position": {"x": 200, "y": 200},
            },
            {
                "id": "schedule",
                "type": "ScheduleNode",
                "category": "trigger",
                "cron": "*/10 * * * * *",  # 10초마다 미체결 주문 체크
                "timezone": "America/New_York",
                "position": {"x": 400, "y": 200},
            },
            {
                "id": "orderEvents",
                "type": "RealOrderEventNode",
                "category": "realtime",
                "event_types": ["pending", "partial_filled"],
                "position": {"x": 600, "y": 200},
            },
            {
                "id": "modify",
                "type": "ModifyOrderNode",
                "category": "order",
                "plugin": "TrackingPriceModifier",
                "fields": {
                    "price_gap_percent": 0.5,  # 현재가와 0.5% 이상 차이나면 정정
                    "max_modifications": 5,  # 최대 5회 정정
                },
                "position": {"x": 800, "y": 200},
            },
            {
                "id": "display",
                "type": "DisplayNode",
                "category": "display",
                "format": "table",
                "fields": ["order_id", "original_price", "new_price", "modify_count"],
                "position": {"x": 1000, "y": 200},
            },
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "schedule"},
            {"from": "schedule.tick", "to": "orderEvents"},
            {"from": "orderEvents.pending_orders", "to": "modify.orders"},
            {"from": "modify.result", "to": "display.data"},
        ],
    }
