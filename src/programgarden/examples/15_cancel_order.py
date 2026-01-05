"""
예제 15: 주문 취소 (Cancel Order)

시간 초과된 미체결 주문 취소
"""

CANCEL_ORDER = {
    "id": "15-cancel-order",
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
            "company": "ls",
            "product": "overseas_stock",
            "paper_trading": True,
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
            "params": {
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
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "schedule.tick", "to": "orderEvents"},
        {"from": "orderEvents.pending_orders", "to": "cancel.orders"},
        {"from": "cancel.result", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(CANCEL_ORDER)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(CANCEL_ORDER)
        print(f"Job: {job}")
