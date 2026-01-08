"""05_operation/w03_state_snapshot - 상태 스냅샷"""


def get_workflow():
    return {
        "id": "operation-03-state-snapshot",
        "version": "1.0.0",
        "name": "상태 스냅샷 예제",
        "description": "상태 스냅샷 저장 및 복구",
        "settings": {
            "snapshot_enabled": True,
            "snapshot_interval_seconds": 30,
            "snapshot_max_count": 10,
            "auto_recovery": True,
        },
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "restore_from_snapshot": True, "position": {"x": 0, "y": 200}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 200}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/10 * * * * *", "timezone": "America/New_York", "position": {"x": 400, "y": 200}},
            {"id": "account", "type": "RealAccountNode", "category": "realtime", "fields": ["balance", "positions"], "position": {"x": 600, "y": 300}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL"], "position": {"x": 600, "y": 100}},
            {"id": "marketData", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 800, "y": 100}},
            {"id": "condition", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 1000, "y": 100}},
            {"id": "order", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "buy"}, "position": {"x": 1200, "y": 100}},
            {"id": "recoveryHandler", "type": "ErrorHandlerNode", "category": "event", "retry_count": 3, "retry_delay_seconds": 10, "on_max_retry": "restore_snapshot", "position": {"x": 1000, "y": 350}},
            {"id": "snapshotEvent", "type": "EventHandlerNode", "category": "event", "event_type": "snapshot_saved", "callback": "log_snapshot", "position": {"x": 600, "y": 450}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["symbol", "status", "snapshot_id"], "position": {"x": 1400, "y": 200}},
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "schedule"},
            {"from": "schedule.tick", "to": "watchlist"},
            {"from": "broker.connection", "to": "account.broker"},
            {"from": "watchlist.symbols", "to": "marketData.symbols"},
            {"from": "marketData.price", "to": "condition.price_data"},
            {"from": "condition.passed_symbols", "to": "order.trigger"},
            {"from": "order.error", "to": "recoveryHandler.error"},
            {"from": "broker.connection", "to": "snapshotEvent"},
            {"from": "order.result", "to": "display.data"},
        ],
    }
