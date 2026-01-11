"""02_condition/01_single_condition - RSI 단일 조건"""


def get_workflow():
    return {
        "id": "06-single-condition",
        "version": "1.0.0",
        "name": "RSI 단일 조건 예제",
        "description": "RSI가 30 이하일 때 통과",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "schedule",
                "type": "ScheduleNode",
                "category": "trigger",
                "cron": "*/30 * * * * *",
                "timezone": "America/New_York",
                "position": {"x": 300, "y": 100},
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": ["AAPL", "TSLA", "NVDA"],
                "position": {"x": 500, "y": 100},
            },
            {
                "id": "realMarket",
                "type": "RealMarketDataNode",
                "category": "realtime",
                "fields": ["price", "volume"],
                "position": {"x": 500, "y": 250},
            },
            {
                "id": "rsi",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {"period": 14, "threshold": 30, "direction": "below"},
                "position": {"x": 700, "y": 100},
            },
            {
                "id": "display",
                "type": "DisplayNode",
                "category": "display",
                "format": "table",
                "fields": ["symbol", "rsi_value", "passed"],
                "position": {"x": 900, "y": 100},
            },
        ],
        "edges": [
            {"from": "start", "to": "schedule"},
            {"from": "schedule", "to": "rsi"},
            {"from": "watchlist", "to": "realMarket"},
            {"from": "realMarket", "to": "rsi"},
            {"from": "rsi", "to": "display"},
        ],
    }
