"""
예제 11: 시장가 주문 (Market Order)

조건 충족 시 시장가 매수 주문 실행
"""

MARKET_ORDER = {
    "id": "11-market-order",
    "version": "1.0.0",
    "name": "시장가 주문 예제",
    "description": "RSI 과매도 시 시장가 매수",
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
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL"],
            "position": {"x": 600, "y": 200},
        },
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 800, "y": 200},
        },
        {
            "id": "rsiCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "params": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 1000, "y": 200},
        },
        {
            "id": "buyOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "params": {
                "side": "buy",
                "amount_type": "percent_balance",
                "amount": 10,  # 잔고의 10%
            },
            "position": {"x": 1200, "y": 200},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "side", "quantity", "status"],
            "position": {"x": 1400, "y": 200},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "schedule.tick", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "marketData.price", "to": "rsiCondition.price_data"},
        {"from": "rsiCondition.passed_symbols", "to": "buyOrder.trigger"},
        {"from": "buyOrder.result", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(MARKET_ORDER)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(MARKET_ORDER)
        print(f"Job: {job}")
