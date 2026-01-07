"""
예제 04: Broker 연결

Start → Broker → RealAccount
"""

BROKER_CONNECTION = {
    "id": "04-broker-connection",
    "version": "1.0.0",
    "name": "증권사 연결 예제",
    "description": "LS증권 해외주식 연결",
    "inputs": {
        "credential_id": {
            "type": "credential",
            "required": True,
            "description": "증권사 인증정보 ID",
        },
    },
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 100, "y": 100},
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "provider": "ls-sec.co.kr",
            "product": "overseas_stock",
            "position": {"x": 300, "y": 100},
        },
        {
            "id": "realAccount",
            "type": "RealAccountNode",
            "category": "realtime",
            "sync_interval_sec": 60,
            "position": {"x": 500, "y": 100},
        },
    ],
    "edges": [
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "realAccount"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(BROKER_CONNECTION)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    # 실제 실행은 credential_id 필요
    # if result.is_valid:
    #     job = pg.run(BROKER_CONNECTION, context={"credential_id": "cred-001"})
