"""05_operation/w04_multi_market - 다중 시장"""


def get_workflow():
    return {
        "id": "operation-04-multi-market",
        "version": "1.0.0",
        "name": "다중 시장 예제",
        "description": "미국 주식 + 선물 동시 운영",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 0, "y": 300}},
            # === 주식 Broker ===
            {"id": "stockBroker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 150}},
            # === 선물 Broker ===
            {"id": "futuresBroker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_futures", "paper_trading": True, "position": {"x": 200, "y": 450}},
            # === Stock Trading Flow ===
            {"id": "stockSchedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 450, "y": 80}},
            {"id": "stockHours", "type": "TradingHoursFilterNode", "category": "trigger", "market": "NYSE", "session": "regular", "timezone": "America/New_York", "position": {"x": 600, "y": 80}},
            {"id": "stockWatchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL", "MSFT", "NVDA"], "position": {"x": 750, "y": 80}},
            {"id": "stockMarket", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 900, "y": 80}},
            {"id": "stockCondition", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 1050, "y": 80}},
            {"id": "stockOrder", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "buy"}, "position": {"x": 1200, "y": 80}},
            # === Futures Trading Flow ===
            {"id": "futuresSchedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 450, "y": 380}},
            {"id": "futuresWatchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["NQH26", "ESH26"], "position": {"x": 600, "y": 380}},
            {"id": "futuresMarket", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 750, "y": 380}},
            {"id": "futuresCondition", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 900, "y": 380}},
            {"id": "futuresOrder", "type": "NewOrderNode", "category": "order", "plugin": "FuturesLimitOrder", "fields": {"side": "buy", "quantity": 1}, "position": {"x": 1050, "y": 380}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["market", "symbol", "side", "quantity", "status"], "position": {"x": 1400, "y": 230}},
        ],
        "edges": [
            {"from": "start", "to": "stockBroker"},
            {"from": "start", "to": "futuresBroker"},
            {"from": "stockBroker", "to": "stockSchedule"},
            {"from": "stockSchedule", "to": "stockHours"},
            {"from": "stockHours", "to": "stockWatchlist"},
            {"from": "stockWatchlist", "to": "stockMarket"},
            {"from": "stockMarket", "to": "stockCondition"},
            {"from": "stockCondition", "to": "stockOrder"},
            {"from": "stockOrder", "to": "display"},
            {"from": "futuresBroker", "to": "futuresSchedule"},
            {"from": "futuresSchedule", "to": "futuresWatchlist"},
            {"from": "futuresWatchlist", "to": "futuresMarket"},
            {"from": "futuresMarket", "to": "futuresCondition"},
            {"from": "futuresCondition", "to": "futuresOrder"},
            {"from": "futuresOrder", "to": "display"},
        ],
    }
