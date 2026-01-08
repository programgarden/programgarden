"""
예제 12: 지정가 주문 (Limit Order)

현재가 대비 -1% 지정가 매수 주문
"""

LIMIT_ORDER = {
    "id": "12-limit-order",
    "version": "1.0.0",
    "name": "지정가 주문 예제",
    "description": "현재가 대비 -1% 지정가 매수",
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
            "cron": "0 9 * * 1-5",  # 평일 9시
            "timezone": "America/New_York",
            "position": {"x": 400, "y": 200},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL", "MSFT"],
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
            "fields": {"period": 14, "threshold": 35, "direction": "below"},
            "position": {"x": 1000, "y": 200},
        },
        {
            "id": "limitBuy",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "LimitOrder",
            "fields": {
                "side": "buy",
                "price_type": "percent_from_current",
                "price": -1,  # 현재가 -1%
                "amount_type": "fixed",
                "amount": 10,  # 10주
            },
            "position": {"x": 1200, "y": 200},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "side", "price", "quantity", "status"],
            "position": {"x": 1400, "y": 200},
        },
    ],
    "edges": [
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "schedule.tick", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "marketData.price", "to": "rsiCondition.price_data"},
        {"from": "rsiCondition.passed_symbols", "to": "limitBuy.trigger"},
        {"from": "limitBuy.result", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(LIMIT_ORDER)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(LIMIT_ORDER)
        print(f"Job: {job}")
