"""01_infra/02_start_schedule - 스케줄 트리거 예제"""


def get_workflow():
    return {
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
            {"from": "start", "to": "schedule"},
        ],
    }
