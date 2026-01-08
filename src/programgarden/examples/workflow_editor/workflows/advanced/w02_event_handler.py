"""04_advanced/w02_event_handler - 이벤트 핸들러"""


def get_workflow():
    return {
        "id": "advanced-02-event-handler",
        "version": "1.0.0",
        "name": "이벤트 핸들러 예제",
        "description": "체결 이벤트 시 Slack/Telegram 알림",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 0, "y": 200}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 200}},
            {"id": "orderEvents", "type": "RealOrderEventNode", "category": "realtime", "event_types": ["filled", "partial_filled"], "position": {"x": 400, "y": 200}},
            {"id": "fillHandler", "type": "EventHandlerNode", "category": "event", "event_type": "order_filled", "callback": "process_fill", "position": {"x": 600, "y": 200}},
            {"id": "alert", "type": "AlertNode", "category": "event", "channel": "slack", "template": "🎯 체결: {{symbol}} {{side}} {{quantity}}주 @ {{price}}", "position": {"x": 800, "y": 200}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["event_type", "symbol", "side", "quantity", "price"], "position": {"x": 1000, "y": 200}},
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "orderEvents"},
            {"from": "orderEvents.filled", "to": "fillHandler.event"},
            {"from": "fillHandler.processed", "to": "alert.data"},
            {"from": "alert.sent", "to": "display.data"},
        ],
    }
