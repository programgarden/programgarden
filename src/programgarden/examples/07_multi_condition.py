"""
예제 07: 복합 조건 (Multi Condition)

RSI AND MACD 복합 조건 (LogicNode로 조합)
"""

MULTI_CONDITION = {
    "id": "07-multi-condition",
    "version": "1.0.0",
    "name": "RSI AND MACD 복합 조건",
    "description": "RSI < 30 AND MACD bullish cross",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 100, "y": 200},
        },
        {
            "id": "schedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 300, "y": 200},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL", "TSLA", "NVDA"],
            "position": {"x": 500, "y": 200},
        },
        {
            "id": "realMarket",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 500, "y": 350},
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
            "id": "macd",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "MACD",
            "params": {"fast": 12, "slow": 26, "signal": 9, "cross": "bullish"},
            "position": {"x": 700, "y": 300},
        },
        {
            "id": "logic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "all",
            "position": {"x": 900, "y": 200},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "position": {"x": 1100, "y": 200},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "schedule"},
        {"from": "schedule.tick", "to": "rsi"},
        {"from": "schedule.tick", "to": "macd"},
        {"from": "watchlist.symbols", "to": "realMarket.symbols"},
        {"from": "realMarket.price", "to": "rsi.price_data"},
        {"from": "realMarket.price", "to": "macd.price_data"},
        {"from": "rsi.result", "to": "logic.input"},
        {"from": "macd.result", "to": "logic.input"},
        {"from": "logic.passed_symbols", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(MULTI_CONDITION)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(MULTI_CONDITION)
        print(f"Job: {job}")
