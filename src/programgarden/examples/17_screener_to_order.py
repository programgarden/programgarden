"""
예제 17: 스크리너 → 주문 (Screener to Order)

시장 유니버스에서 조건 필터링 후 주문
"""

SCREENER_TO_ORDER = {
    "id": "17-screener-to-order",
    "version": "1.0.0",
    "name": "스크리너 → 주문 예제",
    "description": "나스닥100에서 RSI 과매도 종목 스크리닝 후 매수",
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
        # 시장 유니버스 (나스닥 100)
        {
            "id": "universe",
            "type": "MarketUniverseNode",
            "category": "symbol",
            "market": "nasdaq",
            "index": "ndx100",
            "position": {"x": 600, "y": 200},
        },
        # 1차 필터: 시가총액 10B 이상
        {
            "id": "capFilter",
            "type": "SymbolFilterNode",
            "category": "symbol",
            "filter_type": "market_cap",
            "fields": {"min": 10_000_000_000},
            "position": {"x": 800, "y": 200},
        },
        # 스크리너: RSI < 30
        {
            "id": "screener",
            "type": "ScreenerNode",
            "category": "symbol",
            "plugin": "RSI",
            "fields": {"threshold": 30, "direction": "below"},
            "limit": 5,  # 상위 5개
            "position": {"x": 1000, "y": 200},
        },
        # 실시간 데이터
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 1200, "y": 200},
        },
        # 포지션 사이징
        {
            "id": "sizing",
            "type": "PositionSizingNode",
            "category": "risk",
            "method": "equal_weight",
            "fields": {"max_positions": 5},
            "position": {"x": 1400, "y": 200},
        },
        # 매수 주문
        {
            "id": "buyOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {"side": "buy"},
            "position": {"x": 1600, "y": 200},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "screener_rank", "quantity", "status"],
            "position": {"x": 1800, "y": 200},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "schedule.tick", "to": "universe"},
        {"from": "universe.symbols", "to": "capFilter.symbols"},
        {"from": "capFilter.passed_symbols", "to": "screener.symbols"},
        {"from": "screener.screened_symbols", "to": "marketData.symbols"},
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

    result = pg.validate(SCREENER_TO_ORDER)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(SCREENER_TO_ORDER)
        print(f"Job: {job}")
