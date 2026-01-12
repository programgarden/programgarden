"""02_condition/05_nested_logic - 중첩 논리 조건"""


def get_workflow():
    return {
        "id": "10-nested-logic",
        "version": "1.0.0",
        "name": "중첩 논리 조건",
        "description": "(RSI AND MACD) OR (BB AND Volume)",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 100, "y": 250}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 250}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 350, "y": 250}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}], "position": {"x": 350, "y": 400}},
            {"id": "realMarket", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 550, "y": 325}},
            # Group A: RSI + MACD
            {"id": "rsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"threshold": 30}, "position": {"x": 750, "y": 100}},
            {"id": "macd", "type": "ConditionNode", "category": "condition", "plugin": "MACD", "fields": {"signal": "bullish_cross"}, "position": {"x": 750, "y": 200}},
            {"id": "groupA", "type": "LogicNode", "category": "condition", "operator": "all", "position": {"x": 950, "y": 150}},
            # Group B: BB + Volume
            {"id": "bb", "type": "ConditionNode", "category": "condition", "plugin": "BollingerBands", "fields": {"position": "below_lower"}, "position": {"x": 750, "y": 300}},
            {"id": "volume", "type": "ConditionNode", "category": "condition", "plugin": "VolumeSpike", "fields": {"multiplier": 2}, "position": {"x": 750, "y": 400}},
            {"id": "groupB", "type": "LogicNode", "category": "condition", "operator": "all", "position": {"x": 950, "y": 350}},
            # Final OR
            {"id": "finalOr", "type": "LogicNode", "category": "condition", "operator": "any", "position": {"x": 1150, "y": 250}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "position": {"x": 1350, "y": 250}},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "schedule"},
            {"from": "broker", "to": "realMarket"},
            {"from": "schedule", "to": "rsi"},
            {"from": "schedule", "to": "macd"},
            {"from": "schedule", "to": "bb"},
            {"from": "schedule", "to": "volume"},
            {"from": "watchlist", "to": "realMarket"},
            {"from": "realMarket", "to": "rsi"},
            {"from": "realMarket", "to": "macd"},
            {"from": "realMarket", "to": "bb"},
            {"from": "realMarket", "to": "volume"},
            {"from": "rsi", "to": "groupA"},
            {"from": "macd", "to": "groupA"},
            {"from": "bb", "to": "groupB"},
            {"from": "volume", "to": "groupB"},
            {"from": "groupA", "to": "finalOr"},
            {"from": "groupB", "to": "finalOr"},
            {"from": "finalOr", "to": "display"},
        ],
    }
