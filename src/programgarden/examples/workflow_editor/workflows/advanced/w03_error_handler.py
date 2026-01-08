"""04_advanced/w03_error_handler - 에러 핸들러"""


def get_workflow():
    return {
        "id": "advanced-03-error-handler",
        "version": "1.0.0",
        "name": "에러 핸들러 예제",
        "description": "주문 실패 시 3회 재시도 후 알림",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 0, "y": 200}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 200}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 400, "y": 200}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL"], "position": {"x": 600, "y": 200}},
            {"id": "marketData", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 800, "y": 200}},
            {"id": "condition", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 1000, "y": 200}},
            {"id": "order", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "buy"}, "position": {"x": 1200, "y": 200}},
            {"id": "errorHandler", "type": "ErrorHandlerNode", "category": "event", "retry_count": 3, "retry_delay_seconds": 5, "on_max_retry": "alert", "position": {"x": 1400, "y": 300}},
            {"id": "alert", "type": "AlertNode", "category": "event", "channel": "telegram", "template": "❌ 주문 실패: {{symbol}} - {{error_message}}", "position": {"x": 1600, "y": 300}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["symbol", "status", "retry_count", "error_message"], "position": {"x": 1600, "y": 200}},
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "schedule"},
            {"from": "schedule.tick", "to": "watchlist"},
            {"from": "watchlist.symbols", "to": "marketData.symbols"},
            {"from": "marketData.price", "to": "condition.price_data"},
            {"from": "condition.passed_symbols", "to": "order.trigger"},
            {"from": "order.error", "to": "errorHandler.error"},
            {"from": "errorHandler.retry", "to": "order.trigger"},
            {"from": "errorHandler.max_retry_exceeded", "to": "alert.data"},
            {"from": "order.result", "to": "display.data"},
        ],
    }
