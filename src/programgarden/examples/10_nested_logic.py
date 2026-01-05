"""
예제 10: 중첩 논리 (Nested Logic)

(A AND B) OR (C AND D) 형태의 중첩 논리 조합
(RSI과매도 AND MACD골든) OR (BB하단 AND 거래량급증)
"""

NESTED_LOGIC = {
    "id": "10-nested-logic",
    "version": "1.0.0",
    "name": "중첩 논리 조건",
    "description": "(RSI AND MACD) OR (BB AND Volume)",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 100, "y": 250},
        },
        {
            "id": "schedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 300, "y": 250},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL"],
            "position": {"x": 500, "y": 250},
        },
        {
            "id": "realMarket",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 500, "y": 400},
        },
        # Group A: RSI + MACD
        {
            "id": "rsi",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "params": {"threshold": 30},
            "position": {"x": 700, "y": 100},
        },
        {
            "id": "macd",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "MACD",
            "params": {"signal": "bullish_cross"},
            "position": {"x": 700, "y": 200},
        },
        {
            "id": "groupA",
            "type": "LogicNode",
            "category": "condition",
            "operator": "all",
            "position": {"x": 900, "y": 150},
        },
        # Group B: BB + Volume
        {
            "id": "bb",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "BollingerBands",
            "params": {"position": "below_lower"},
            "position": {"x": 700, "y": 300},
        },
        {
            "id": "volume",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "VolumeSpike",
            "params": {"multiplier": 2},
            "position": {"x": 700, "y": 400},
        },
        {
            "id": "groupB",
            "type": "LogicNode",
            "category": "condition",
            "operator": "all",
            "position": {"x": 900, "y": 350},
        },
        # Final OR
        {
            "id": "finalOr",
            "type": "LogicNode",
            "category": "condition",
            "operator": "any",
            "position": {"x": 1100, "y": 250},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "position": {"x": 1300, "y": 250},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "schedule"},
        {"from": "schedule.tick", "to": "rsi"},
        {"from": "schedule.tick", "to": "macd"},
        {"from": "schedule.tick", "to": "bb"},
        {"from": "schedule.tick", "to": "volume"},
        {"from": "watchlist.symbols", "to": "realMarket.symbols"},
        {"from": "realMarket.price", "to": "rsi.price_data"},
        {"from": "realMarket.price", "to": "macd.price_data"},
        {"from": "realMarket.price", "to": "bb.price_data"},
        {"from": "realMarket.volume", "to": "volume.volume_data"},
        # Group A
        {"from": "rsi.result", "to": "groupA.input"},
        {"from": "macd.result", "to": "groupA.input"},
        # Group B
        {"from": "bb.result", "to": "groupB.input"},
        {"from": "volume.result", "to": "groupB.input"},
        # Final OR
        {"from": "groupA.result", "to": "finalOr.input"},
        {"from": "groupB.result", "to": "finalOr.input"},
        {"from": "finalOr.passed_symbols", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(NESTED_LOGIC)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(NESTED_LOGIC)
        print(f"Job: {job}")
