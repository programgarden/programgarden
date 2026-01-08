"""
예제 13: 포지션 사이징 (Position Sizing)

1% 리스크 기반 포지션 수량 계산
"""

POSITION_SIZING = {
    "id": "13-position-sizing",
    "version": "1.0.0",
    "name": "포지션 사이징 예제",
    "description": "계좌 1% 리스크 기반 수량 계산",
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
            "position": {"x": 800, "y": 100},
        },
        {
            "id": "account",
            "type": "RealAccountNode",
            "category": "realtime",
            "fields": ["balance", "buying_power"],
            "position": {"x": 800, "y": 300},
        },
        {
            "id": "buySignal",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 1000, "y": 200},
        },
        {
            "id": "sizing",
            "type": "PositionSizingNode",
            "category": "risk",
            "method": "risk_percent",
            "fields": {
                "risk_percent": 1,  # 계좌의 1% 리스크
                "stop_loss_percent": 5,  # 손절 5% 기준
            },
            "position": {"x": 1200, "y": 200},
        },
        {
            "id": "buyOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {"side": "buy"},
            "position": {"x": 1400, "y": 200},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "calculated_qty", "risk_amount", "status"],
            "position": {"x": 1600, "y": 200},
        },
    ],
    "edges": [
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "schedule.tick", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "broker.connection", "to": "account.broker"},
        {"from": "marketData.price", "to": "buySignal.price_data"},
        {"from": "buySignal.passed_symbols", "to": "sizing.trigger"},
        {"from": "account.balance", "to": "sizing.balance"},
        {"from": "marketData.price", "to": "sizing.price"},
        {"from": "sizing.quantity", "to": "buyOrder.quantity"},
        {"from": "buyOrder.result", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(POSITION_SIZING)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(POSITION_SIZING)
        print(f"Job: {job}")
