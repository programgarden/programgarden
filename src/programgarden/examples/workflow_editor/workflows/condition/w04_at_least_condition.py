"""02_condition/04_at_least_condition - N개 이상 조건"""


def get_workflow():
    return {
        "id": "09-at-least-condition",
        "version": "1.0.0",
        "name": "N개 이상 조건",
        "description": "3개 조건 중 2개 이상 만족 시 통과",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 100, "y": 200}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "0 * * * *", "timezone": "America/New_York", "position": {"x": 300, "y": 200}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL", "GOOGL"], "position": {"x": 500, "y": 200}},
            {"id": "realMarket", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 500, "y": 350}},
            {"id": "rsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"threshold": 30}, "position": {"x": 700, "y": 100}},
            {"id": "macd", "type": "ConditionNode", "category": "condition", "plugin": "MACD", "fields": {"signal": "bullish_cross"}, "position": {"x": 700, "y": 200}},
            {"id": "volume", "type": "ConditionNode", "category": "condition", "plugin": "VolumeSpike", "fields": {"multiplier": 2}, "position": {"x": 700, "y": 300}},
            {"id": "atLeast2", "type": "LogicNode", "category": "condition", "operator": "at_least", "min_count": 2, "position": {"x": 900, "y": 200}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "position": {"x": 1100, "y": 200}},
        ],
        "edges": [
            {"from": "start", "to": "schedule"},
            {"from": "schedule", "to": "rsi"},
            {"from": "schedule", "to": "macd"},
            {"from": "schedule", "to": "volume"},
            {"from": "watchlist", "to": "realMarket"},
            {"from": "realMarket", "to": "rsi"},
            {"from": "realMarket", "to": "macd"},
            {"from": "realMarket", "to": "volume"},
            {"from": "rsi", "to": "atLeast2"},
            {"from": "macd", "to": "atLeast2"},
            {"from": "volume", "to": "atLeast2"},
            {"from": "atLeast2", "to": "display"},
        ],
    }
