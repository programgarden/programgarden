"""01_infra/01_start_only - StartNode 기본 예제"""


def get_workflow():
    return {
        "id": "01-start-only",
        "version": "1.0.0",
        "name": "StartNode 기본 예제",
        "description": "워크플로우 시작점 테스트",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 100, "y": 100},
            }
        ],
        "edges": [],
    }
