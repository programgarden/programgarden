"""05_operation/w02_pause_resume - 일시정지/재개"""


def get_workflow():
    return {
        "id": "operation-02-pause-resume",
        "version": "1.0.0",
        "name": "일시정지/재개 예제",
        "description": "24시간 자동매매 - 일시정지/재개 지원",
        "settings": {
            "snapshot_enabled": True,
            "snapshot_interval_seconds": 60,
            "graceful_shutdown": True,
        },
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 0, "y": 200}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 200}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 400, "y": 200}},
            {"id": "account", "type": "RealAccountNode", "category": "realtime", "fields": ["balance", "positions"], "position": {"x": 600, "y": 300}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL", "MSFT", "GOOGL"], "position": {"x": 600, "y": 100}},
            {"id": "marketData", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 800, "y": 100}},
            {"id": "buyCondition", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 1000, "y": 100}},
            {"id": "buyOrder", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "buy"}, "position": {"x": 1200, "y": 100}},
            {"id": "pauseHandler", "type": "EventHandlerNode", "category": "event", "event_type": "job_paused", "callback": "save_state", "position": {"x": 600, "y": 400}},
            {"id": "resumeHandler", "type": "EventHandlerNode", "category": "event", "event_type": "job_resumed", "callback": "restore_state", "position": {"x": 800, "y": 400}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["symbol", "status", "job_state"], "position": {"x": 1400, "y": 200}},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "schedule"},
            {"from": "broker", "to": "pauseHandler"},
            {"from": "broker", "to": "resumeHandler"},
            {"from": "schedule", "to": "watchlist"},
            {"from": "broker", "to": "account"},
            {"from": "watchlist", "to": "marketData"},
            {"from": "marketData", "to": "buyCondition"},
            {"from": "buyCondition", "to": "buyOrder"},
            {"from": "buyOrder", "to": "display"},
        ],
    }
