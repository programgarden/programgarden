"""
예제 16: 기본 매수매도 (Buy Sell Basic)

매수 조건 → 매수 + 매도 조건 → 매도 기본 흐름
"""

BUY_SELL_BASIC = {
    "id": "16-buy-sell-basic",
    "version": "1.0.0",
    "name": "기본 매수매도 예제",
    "description": "RSI 과매도 매수, 과매수 매도",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 0, "y": 300},
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "company": "ls",
            "product": "overseas_stock",
            "paper_trading": True,
            "position": {"x": 200, "y": 300},
        },
        {
            "id": "schedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 400, "y": 300},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL"],
            "position": {"x": 600, "y": 300},
        },
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 800, "y": 200},
        },
        {
            "id": "account",
            "type": "RealAccountNode",
            "category": "realtime",
            "fields": ["balance", "positions"],
            "position": {"x": 800, "y": 400},
        },
        # === 매수 조건 ===
        {
            "id": "buyCond",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 1000, "y": 150},
        },
        # === 매도 조건 ===
        {
            "id": "sellCond",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {"period": 14, "threshold": 70, "direction": "above"},
            "position": {"x": 1000, "y": 450},
        },
        # 주문
        {
            "id": "buyOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {"side": "buy", "amount_type": "percent_balance", "amount": 10},
            "position": {"x": 1200, "y": 150},
        },
        {
            "id": "sellOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {"side": "sell", "amount_type": "all"},
            "position": {"x": 1200, "y": 450},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "side", "quantity", "status"],
            "position": {"x": 1400, "y": 300},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "schedule.tick", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "broker.connection", "to": "account.broker"},
        # Buy flow
        {"from": "marketData.price", "to": "buyCond.price_data"},
        {"from": "buyCond.passed_symbols", "to": "buyOrder.trigger"},
        # Sell flow
        {"from": "marketData.price", "to": "sellCond.price_data"},
        {"from": "account.positions", "to": "sellCond.positions"},
        {"from": "sellCond.passed_symbols", "to": "sellOrder.trigger"},
        # Display
        {"from": "buyOrder.result", "to": "display.data"},
        {"from": "sellOrder.result", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(BUY_SELL_BASIC)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(BUY_SELL_BASIC)
        print(f"Job: {job}")
