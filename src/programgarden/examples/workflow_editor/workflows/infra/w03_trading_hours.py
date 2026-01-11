"""01_infra/03_trading_hours - 거래시간 필터 예제"""


def get_workflow():
    return {
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
            {"from": "start", "to": "schedule"},
            {"from": "schedule", "to": "tradingHours"},
        ],
    }
