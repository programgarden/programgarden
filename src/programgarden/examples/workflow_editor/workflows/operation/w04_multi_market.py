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
            # === Stock Trading Group ===
            {"id": "stockGroup", "type": "GroupNode", "category": "group", "name": "US Stock Trading", "color": "#2196F3", "child_nodes": ["stockSchedule", "stockHours", "stockWatchlist", "stockMarket", "stockCondition", "stockOrder"], "position": {"x": 400, "y": 50}},
            {"id": "stockSchedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 450, "y": 80}},
            {"id": "stockHours", "type": "TradingHoursFilterNode", "category": "trigger", "market": "NYSE", "session": "regular", "timezone": "America/New_York", "position": {"x": 600, "y": 80}},
            {"id": "stockWatchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL", "MSFT", "NVDA"], "position": {"x": 750, "y": 80}},
            {"id": "stockMarket", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 900, "y": 80}},
            {"id": "stockCondition", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 1050, "y": 80}},
            {"id": "stockOrder", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "buy"}, "position": {"x": 1200, "y": 80}},
            # === Futures Trading Group ===
            {"id": "futuresGroup", "type": "GroupNode", "category": "group", "name": "US Futures Trading", "color": "#FF9800", "child_nodes": ["futuresSchedule", "futuresWatchlist", "futuresMarket", "futuresCondition", "futuresOrder"], "position": {"x": 400, "y": 350}},
            {"id": "futuresSchedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 450, "y": 380}},
            {"id": "futuresWatchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["NQH26", "ESH26"], "position": {"x": 600, "y": 380}},
            {"id": "futuresMarket", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 750, "y": 380}},
            {"id": "futuresCondition", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 900, "y": 380}},
            {"id": "futuresOrder", "type": "NewOrderNode", "category": "order", "plugin": "FuturesLimitOrder", "fields": {"side": "buy", "quantity": 1}, "position": {"x": 1050, "y": 380}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["market", "symbol", "side", "quantity", "status"], "position": {"x": 1400, "y": 230}},
        ],
        "edges": [
            {"from": "start.start", "to": "stockBroker"},
            {"from": "start.start", "to": "futuresBroker"},
            # Stock flow
            {"from": "stockBroker.connection", "to": "stockSchedule"},
            {"from": "stockSchedule.tick", "to": "stockHours"},
            {"from": "stockHours.within_hours", "to": "stockWatchlist"},
            {"from": "stockWatchlist.symbols", "to": "stockMarket.symbols"},
            {"from": "stockMarket.price", "to": "stockCondition.price_data"},
            {"from": "stockCondition.passed_symbols", "to": "stockOrder.trigger"},
            {"from": "stockOrder.result", "to": "display.data"},
            # Futures flow
            {"from": "futuresBroker.connection", "to": "futuresSchedule"},
            {"from": "futuresSchedule.tick", "to": "futuresWatchlist"},
            {"from": "futuresWatchlist.symbols", "to": "futuresMarket.symbols"},
            {"from": "futuresMarket.price", "to": "futuresCondition.price_data"},
            {"from": "futuresCondition.passed_symbols", "to": "futuresOrder.trigger"},
            {"from": "futuresOrder.result", "to": "display.data"},
        ],
    }
