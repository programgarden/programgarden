"""03_order/w05_cancel_order - 주문 취소"""


def get_workflow():
    return {
        "id": "order-05-cancel",
        "version": "1.0.0",
        "name": "주문 취소 예제",
        "description": "30분 이상 미체결 주문 취소",
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
                "cron": "0 * * * * *",  # 매 분 0초
                "timezone": "America/New_York",
                "position": {"x": 400, "y": 200},
            },
            {
                "id": "orderEvents",
                "type": "RealOrderEventNode",
                "category": "realtime",
                "event_types": ["pending"],
                "position": {"x": 600, "y": 200},
            },
            {
                "id": "cancel",
                "type": "CancelOrderNode",
                "category": "order",
                "plugin": "TimeStopCanceller",
                "fields": {
                    "timeout_minutes": 30,  # 30분 초과 시 취소
                },
                "position": {"x": 800, "y": 200},
            },
            {
                "id": "display",
                "type": "DisplayNode",
                "category": "display",
                "format": "table",
                "fields": ["order_id", "elapsed_minutes", "cancel_status"],
                "position": {"x": 1000, "y": 200},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "schedule"},
            {"from": "schedule", "to": "orderEvents"},
            {"from": "orderEvents", "to": "cancel"},
            {"from": "cancel", "to": "display"},
        ],
    }
