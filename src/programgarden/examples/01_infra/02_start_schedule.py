"""
예제 02: Start → Schedule

StartNode에서 ScheduleNode로 연결
"""

START_SCHEDULE = {
    "id": "02-start-schedule",
    "version": "1.0.0",
    "name": "스케줄 트리거 예제",
    "description": "5분마다 트리거 발생",
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
    ],
    "edges": [
        {"from": "start.start", "to": "schedule"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(START_SCHEDULE)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(START_SCHEDULE)
        print(f"Job: {job}")
