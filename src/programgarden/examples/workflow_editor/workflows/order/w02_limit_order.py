"""03_order/w02_limit_order - 지정가 주문"""


def get_workflow():
    return {
        "id": "order-02-limit",
        "version": "1.0.0",
        "name": "지정가 주문 예제",
        "description": "현재가 -1% 지정가 매수",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 0, "y": 200},
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "category": "infra",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "position": {"x": 200, "y": 200},
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": ["NVDA"],
                "position": {"x": 400, "y": 100},
            },
            {
                "id": "account",
                "type": "RealAccountNode",
                "category": "realtime",
                "fields": ["balance"],
                "position": {"x": 400, "y": 300},
            },
            {
                "id": "marketData",
                "type": "RealMarketDataNode",
                "category": "realtime",
                "fields": ["price"],
                "position": {"x": 600, "y": 100},
            },
            {
                "id": "order",
                "type": "NewOrderNode",
                "category": "order",
                "plugin": "LimitOrder",
                "fields": {
                    "side": "buy",
                    "quantity": 1,
                    "price_offset_percent": -1.0,  # 현재가 대비 -1%
                },
                "position": {"x": 800, "y": 200},
            },
            {
                "id": "display",
                "type": "DisplayNode",
                "category": "display",
                "format": "table",
                "fields": ["symbol", "side", "price", "quantity", "status"],
                "position": {"x": 1000, "y": 200},
            },
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "watchlist"},
            {"from": "broker.connection", "to": "account.broker"},
            {"from": "watchlist.symbols", "to": "marketData.symbols"},
            {"from": "marketData.price", "to": "order.price_data"},
            {"from": "account.balance", "to": "order.account_info"},
            {"from": "order.result", "to": "display.data"},
        ],
    }
