"""01_infra/05_watchlist_realmarket - 관심종목 실시간 시세"""


def get_workflow():
    return {
        "id": "05-watchlist-realmarket",
        "version": "1.0.0",
        "name": "관심종목 실시간 시세 예제",
        "description": "AAPL, TSLA, NVDA 실시간 시세 구독",
        "inputs": {
            "credential_id": {
                "type": "credential",
                "required": True,
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
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": ["AAPL", "TSLA", "NVDA"],
                "position": {"x": 300, "y": 250},
            },
            {
                "id": "realMarket",
                "type": "RealMarketDataNode",
                "category": "realtime",
                "fields": ["price", "volume"],
                "position": {"x": 500, "y": 175},
            },
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "realMarket"},
            {"from": "watchlist.symbols", "to": "realMarket.symbols"},
        ],
    }
