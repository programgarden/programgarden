"""05_operation/w01_trading_hours - 거래시간 필터"""


def get_workflow():
    return {
        "id": "operation-01-trading-hours",
        "version": "1.0.0",
        "name": "거래시간 필터 예제",
        "description": "NYSE 정규장 시간(09:30-16:00 ET)에만 거래",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 0, "y": 200}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 200}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 400, "y": 200}},
            {"id": "hoursFilter", "type": "TradingHoursFilterNode", "category": "trigger", "market": "NYSE", "session": "regular", "timezone": "America/New_York", "position": {"x": 600, "y": 100}},
            {"id": "exchangeStatus", "type": "ExchangeStatusNode", "category": "trigger", "exchange": "NYSE", "check_holidays": True, "position": {"x": 600, "y": 300}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL"], "position": {"x": 800, "y": 200}},
            {"id": "marketData", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 1000, "y": 200}},
            {"id": "condition", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 1200, "y": 200}},
            {"id": "order", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "buy"}, "position": {"x": 1400, "y": 200}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["symbol", "trading_hours", "exchange_status", "status"], "position": {"x": 1600, "y": 200}},
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "schedule"},
            {"from": "schedule.tick", "to": "hoursFilter"},
            {"from": "schedule.tick", "to": "exchangeStatus"},
            {"from": "hoursFilter.within_hours", "to": "watchlist"},
            {"from": "exchangeStatus.is_open", "to": "watchlist.gate"},
            {"from": "watchlist.symbols", "to": "marketData.symbols"},
            {"from": "marketData.price", "to": "condition.price_data"},
            {"from": "condition.passed_symbols", "to": "order.trigger"},
            {"from": "order.result", "to": "display.data"},
        ],
    }
