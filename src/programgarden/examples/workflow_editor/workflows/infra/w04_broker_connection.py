"""01_infra/04_broker_connection - 증권사 연결 예제"""


def get_workflow():
    return {
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
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "realAccount"},
        ],
    }
