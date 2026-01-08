"""02_condition/03_weighted_condition - 가중치 조합 조건"""


def get_workflow():
    return {
        "id": "08-weighted-condition",
        "version": "1.0.0",
        "name": "가중치 조합 조건",
        "description": "RSI 40% + MACD 30% + BB 30% >= 70%",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 100, "y": 200}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 300, "y": 200}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL", "TSLA"], "position": {"x": 500, "y": 200}},
            {"id": "realMarket", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price"], "position": {"x": 500, "y": 350}},
            {"id": "rsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 700, "y": 100}},
            {"id": "macd", "type": "ConditionNode", "category": "condition", "plugin": "MACD", "fields": {"signal": "bullish_cross"}, "position": {"x": 700, "y": 200}},
            {"id": "bb", "type": "ConditionNode", "category": "condition", "plugin": "BollingerBands", "fields": {"position": "below_lower"}, "position": {"x": 700, "y": 300}},
            {"id": "weightedLogic", "type": "LogicNode", "category": "condition", "operator": "weighted", "threshold": 0.7, "weights": [0.4, 0.3, 0.3], "position": {"x": 900, "y": 200}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "position": {"x": 1100, "y": 200}},
        ],
        "edges": [
            {"from": "start.start", "to": "schedule"},
            {"from": "schedule.tick", "to": "rsi"},
            {"from": "schedule.tick", "to": "macd"},
            {"from": "schedule.tick", "to": "bb"},
            {"from": "watchlist.symbols", "to": "realMarket.symbols"},
            {"from": "realMarket.price", "to": "rsi.price_data"},
            {"from": "realMarket.price", "to": "macd.price_data"},
            {"from": "realMarket.price", "to": "bb.price_data"},
            {"from": "rsi.result", "to": "weightedLogic.input"},
            {"from": "macd.result", "to": "weightedLogic.input"},
            {"from": "bb.result", "to": "weightedLogic.input"},
            {"from": "weightedLogic.passed_symbols", "to": "display.data"},
        ],
    }
