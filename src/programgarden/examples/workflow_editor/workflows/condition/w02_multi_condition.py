"""02_condition/02_multi_condition - RSI AND MACD 복합 조건"""


def get_workflow():
    return {
        "id": "07-multi-condition",
        "version": "1.0.0",
        "name": "RSI AND MACD 복합 조건",
        "description": "RSI < 30 AND MACD bullish cross",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 100, "y": 200}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 300, "y": 200}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL", "TSLA", "NVDA"], "position": {"x": 500, "y": 200}},
            {"id": "realMarket", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 500, "y": 350}},
            {"id": "rsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 700, "y": 100}},
            {"id": "macd", "type": "ConditionNode", "category": "condition", "plugin": "MACD", "fields": {"fast": 12, "slow": 26, "signal": 9, "cross": "bullish"}, "position": {"x": 700, "y": 300}},
            {"id": "logic", "type": "LogicNode", "category": "condition", "operator": "all", "position": {"x": 900, "y": 200}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "position": {"x": 1100, "y": 200}},
        ],
        "edges": [
            {"from": "start", "to": "schedule"},
            {"from": "schedule", "to": "rsi"},
            {"from": "schedule", "to": "macd"},
            {"from": "watchlist", "to": "realMarket"},
            {"from": "realMarket", "to": "rsi"},
            {"from": "realMarket", "to": "macd"},
            {"from": "rsi", "to": "logic"},
            {"from": "macd", "to": "logic"},
            {"from": "logic", "to": "display"},
        ],
    }
