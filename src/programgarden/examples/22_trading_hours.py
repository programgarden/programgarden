"""
예제 22: 거래시간 필터 (Trading Hours Filter)

미국 정규장 시간에만 거래
"""

TRADING_HOURS = {
    "id": "22-trading-hours",
    "version": "1.0.0",
    "name": "거래시간 필터 예제",
    "description": "NYSE 정규장 시간(09:30-16:00 ET)에만 거래",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 0, "y": 200},
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "company": "ls",
            "product": "overseas_stock",
            "paper_trading": True,
            "position": {"x": 200, "y": 200},
        },
        {
            "id": "schedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 400, "y": 200},
        },
        # 거래시간 필터
        {
            "id": "hoursFilter",
            "type": "TradingHoursFilterNode",
            "category": "trigger",
            "market": "NYSE",
            "session": "regular",  # regular, pre, post, extended
            "timezone": "America/New_York",
            "position": {"x": 600, "y": 100},
        },
        # 거래소 상태 확인
        {
            "id": "exchangeStatus",
            "type": "ExchangeStatusNode",
            "category": "trigger",
            "exchange": "NYSE",
            "check_holidays": True,
            "position": {"x": 600, "y": 300},
        },
        # 정상 흐름
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL"],
            "position": {"x": 800, "y": 200},
        },
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 1000, "y": 200},
        },
        {
            "id": "condition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "params": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 1200, "y": 200},
        },
        {
            "id": "order",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "params": {"side": "buy"},
            "position": {"x": 1400, "y": 200},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "trading_hours", "exchange_status", "status"],
            "position": {"x": 1600, "y": 200},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "schedule.tick", "to": "hoursFilter"},
        {"from": "schedule.tick", "to": "exchangeStatus"},
        # Only proceed if within trading hours AND exchange is open
        {"from": "hoursFilter.within_hours", "to": "watchlist.trigger"},
        {"from": "exchangeStatus.is_open", "to": "watchlist.gate"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "marketData.price", "to": "condition.price_data"},
        {"from": "condition.passed_symbols", "to": "order.trigger"},
        {"from": "order.result", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(TRADING_HOURS)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(TRADING_HOURS)
        print(f"Job: {job}")
