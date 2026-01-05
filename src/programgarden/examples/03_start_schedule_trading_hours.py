"""
예제 03: Start → Schedule → TradingHours

거래시간 필터 적용
"""

START_SCHEDULE_TRADING_HOURS = {
    "id": "03-start-schedule-trading-hours",
    "version": "1.0.0",
    "name": "거래시간 필터 예제",
    "description": "NYSE 거래시간(09:30-16:00 ET)에만 실행",
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
            "cron": "*/5 * * * *",
            "timezone": "America/New_York",
            "position": {"x": 300, "y": 100},
        },
        {
            "id": "tradingHours",
            "type": "TradingHoursFilterNode",
            "category": "trigger",
            "start": "09:30",
            "end": "16:00",
            "timezone": "America/New_York",
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "position": {"x": 500, "y": 100},
        },
    ],
    "edges": [
        {"from": "start.start", "to": "schedule"},
        {"from": "schedule.trigger", "to": "tradingHours"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(START_SCHEDULE_TRADING_HOURS)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(START_SCHEDULE_TRADING_HOURS)
        print(f"Job: {job}")
