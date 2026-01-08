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
            {"from": "start.start", "to": "schedule"},
            {"from": "schedule.tick", "to": "rsi"},
            {"from": "schedule.tick", "to": "macd"},
            {"from": "schedule.tick", "to": "volume"},
            {"from": "watchlist.symbols", "to": "realMarket.symbols"},
            {"from": "realMarket.price", "to": "rsi.price_data"},
            {"from": "realMarket.price", "to": "macd.price_data"},
            {"from": "realMarket.volume", "to": "volume.volume_data"},
            {"from": "rsi.result", "to": "atLeast2.input"},
            {"from": "macd.result", "to": "atLeast2.input"},
            {"from": "volume.result", "to": "atLeast2.input"},
            {"from": "atLeast2.passed_symbols", "to": "display.data"},
        ],
    }
