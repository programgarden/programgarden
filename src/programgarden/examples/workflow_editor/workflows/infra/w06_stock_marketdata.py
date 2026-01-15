"""
해외주식 현재가 조회 워크플로우

MarketDataNode로 해외주식 종목의 현재가/거래량/OHLCV를 조회합니다.
g3101 API를 사용합니다.

테스트 종목:
- AAPL: 애플
- NVDA: 엔비디아
- TSLA: 테슬라
"""

workflow = {
    "id": "stock-marketdata-test",
    "name": "해외주식 현재가 조회",
    "description": "MarketDataNode로 해외주식 현재가/거래량/OHLCV 조회 (g3101)",
    "nodes": [
        {
            "id": "start_1",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 50, "y": 200},
            "description": "워크플로우 시작"
        },
        {
            "id": "broker_2",
            "type": "BrokerNode",
            "category": "infra",
            "position": {"x": 350, "y": 200},
            "description": "해외주식 브로커 연결",
            "provider": "ls-sec.co.kr",
            "product": "overseas_stock",
            "credential_id": "broker-stock-cred"
        },
        {
            "id": "marketdata_3",
            "type": "MarketDataNode",
            "category": "market",
            "position": {"x": 700, "y": 200},
            "description": "해외주식 현재가 조회 (g3101)",
            "connection": "{{nodes.broker_2.connection}}",
            "symbols": [
                {"exchange": "NASDAQ", "symbol": "AAPL"},
                {"exchange": "NASDAQ", "symbol": "NVDA"},
                {"exchange": "NASDAQ", "symbol": "TSLA"}
            ],
            "fields": ["price", "volume", "ohlcv"]
        },
        {
            "id": "display_4",
            "type": "DisplayNode",
            "category": "analysis",
            "position": {"x": 1050, "y": 100},
            "description": "현재가 데이터 표시",
            "size": {"width": 400, "height": 300}
        },
        {
            "id": "display_5",
            "type": "DisplayNode",
            "category": "analysis",
            "position": {"x": 1050, "y": 450},
            "description": "OHLCV 데이터 표시",
            "size": {"width": 400, "height": 250}
        }
    ],
    "edges": [
        {"from": "start_1", "to": "broker_2"},
        {"from": "broker_2", "to": "marketdata_3"},
        {"from": "marketdata_3", "to": "display_4"},
        {"from": "marketdata_3", "to": "display_5"}
    ],
    "credentials": [
        {
            "id": "broker-stock-cred",
            "type": "broker_ls",
            "name": "LS증권 해외주식",
            "data": {
                "appkey": "",
                "appsecret": "",
                "paper_trading": False
            }
        }
    ]
}
