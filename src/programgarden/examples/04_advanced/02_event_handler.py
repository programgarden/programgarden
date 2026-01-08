"""
예제 18: 이벤트 핸들러 (Event Handler)

체결 이벤트 시 알림 발송
"""

EVENT_HANDLER = {
    "id": "18-event-handler",
    "version": "1.0.0",
    "name": "이벤트 핸들러 예제",
    "description": "체결 이벤트 시 Slack/Telegram 알림",
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
        # 실시간 주문 이벤트
        {
            "id": "orderEvents",
            "type": "RealOrderEventNode",
            "category": "realtime",
            "event_types": ["filled", "partial_filled"],
            "position": {"x": 400, "y": 200},
        },
        # 이벤트 핸들러
        {
            "id": "fillHandler",
            "type": "EventHandlerNode",
            "category": "event",
            "event_type": "order_filled",
            "callback": "process_fill",
            "position": {"x": 600, "y": 200},
        },
        # 알림 발송
        {
            "id": "alert",
            "type": "AlertNode",
            "category": "event",
            "channel": "slack",
            "template": "🎯 체결: {{symbol}} {{side}} {{quantity}}주 @ {{price}}",
            "position": {"x": 800, "y": 200},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["event_type", "symbol", "side", "quantity", "price"],
            "position": {"x": 1000, "y": 200},
        },
    ],
    "edges": [
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "orderEvents"},
        {"from": "orderEvents.filled", "to": "fillHandler.event"},
        {"from": "fillHandler.processed", "to": "alert.data"},
        {"from": "alert.sent", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(EVENT_HANDLER)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(EVENT_HANDLER)
        print(f"Job: {job}")
