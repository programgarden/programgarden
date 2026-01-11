"""10_futures/w01_futures_broker - 해외선물 브로커 연결 (모의투자)"""


def get_workflow():
    return {
        "id": "futures-01-broker",
        "version": "1.0.0",
        "name": "해외선물 브로커 연결",
        "description": "LS증권 해외선물 모의투자 연결",
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
                "product": "overseas_futures",  # 해외선물
                "paper_trading": True,  # 모의투자 (해외선물만 지원)
                "position": {"x": 300, "y": 100},
            },
            {
                "id": "account",
                "type": "AccountNode",
                "category": "realtime",
                "position": {"x": 500, "y": 100},
            },
            {
                "id": "display",
                "type": "DisplayNode",
                "category": "display",
                "format": "table",
                "position": {"x": 700, "y": 100},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "display"},
        ],
    }
