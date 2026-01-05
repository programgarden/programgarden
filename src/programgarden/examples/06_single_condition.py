"""
예제 06: 단일 조건 (Single Condition)

RSI < 30 단일 조건 평가
"""

SINGLE_CONDITION = {
    "id": "06-single-condition",
    "version": "1.0.0",
    "name": "RSI 단일 조건 예제",
    "description": "RSI가 30 이하일 때 통과",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 100, "y": 100},
        },
        {
            "id": "schedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 300, "y": 100},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL", "TSLA", "NVDA"],
            "position": {"x": 500, "y": 100},
        },
        {
            "id": "realMarket",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 500, "y": 250},
        },
        {
            "id": "rsi",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "params": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 700, "y": 100},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "rsi_value", "passed"],
            "position": {"x": 900, "y": 100},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "schedule"},
        {"from": "schedule.tick", "to": "rsi"},
        {"from": "watchlist.symbols", "to": "realMarket.symbols"},
        {"from": "realMarket.price", "to": "rsi.price_data"},
        {"from": "rsi.passed_symbols", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(SINGLE_CONDITION)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(SINGLE_CONDITION)
        print(f"Job: {job}")
