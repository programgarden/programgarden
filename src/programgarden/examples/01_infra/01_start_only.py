"""
예제 01: StartNode만

가장 기본적인 워크플로우 - StartNode만 포함
"""

START_ONLY = {
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


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    # 검증
    result = pg.validate(START_ONLY)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")

    # 실행
    if result.is_valid:
        job = pg.run(START_ONLY)
        print(f"Job: {job}")
