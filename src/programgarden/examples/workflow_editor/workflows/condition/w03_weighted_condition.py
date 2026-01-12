"""02_condition/03_weighted_condition - 가중치 조합 조건"""


def get_workflow():
    return {
        "id": "08-weighted-condition",
        "version": "1.0.0",
        "name": "가중치 조합 조건",
        "description": "RSI 40% + MACD 30% + BB 30% >= 70%",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 100, "y": 200}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 200}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 350, "y": 200}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NASDAQ", "symbol": "TSLA"}], "position": {"x": 350, "y": 350}},
            {"id": "realMarket", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price"], "position": {"x": 550, "y": 275}},
            {"id": "rsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 750, "y": 100}},
            {"id": "macd", "type": "ConditionNode", "category": "condition", "plugin": "MACD", "fields": {"signal": "bullish_cross"}, "position": {"x": 750, "y": 200}},
            {"id": "bb", "type": "ConditionNode", "category": "condition", "plugin": "BollingerBands", "fields": {"position": "below_lower"}, "position": {"x": 750, "y": 300}},
            {"id": "weightedLogic", "type": "LogicNode", "category": "condition", "operator": "weighted", "threshold": 0.7, "weights": [0.4, 0.3, 0.3], "position": {"x": 950, "y": 200}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "position": {"x": 1150, "y": 200}},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "schedule"},
            {"from": "broker", "to": "realMarket"},
            {"from": "schedule", "to": "rsi"},
            {"from": "schedule", "to": "macd"},
            {"from": "schedule", "to": "bb"},
            {"from": "watchlist", "to": "realMarket"},
            {"from": "realMarket", "to": "rsi"},
            {"from": "realMarket", "to": "macd"},
            {"from": "realMarket", "to": "bb"},
            {"from": "rsi", "to": "weightedLogic"},
            {"from": "macd", "to": "weightedLogic"},
            {"from": "bb", "to": "weightedLogic"},
            {"from": "weightedLogic", "to": "display"},
        ],
    }
