"""10_futures/w03_futures_order - 해외선물 주문 예제"""


def get_workflow():
    return {
        "id": "futures-03-order",
        "version": "1.0.0",
        "name": "해외선물 주문 예제",
        "description": "나스닥선물 RSI 기반 조건부 주문",
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
                "product": "overseas_futures",
                "paper_trading": True,  # 모의투자
                "position": {"x": 200, "y": 200},
            },
            {
                "id": "schedule",
                "type": "ScheduleNode",
                "category": "trigger",
                "cron": "*/5 * * * *",  # 5분마다
                "timezone": "America/New_York",
                "position": {"x": 400, "y": 200},
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": [{"exchange": "CME", "symbol": "NQH26"}],  # 나스닥 선물 2026년 3월물
                "position": {"x": 600, "y": 100},
            },
            {
                "id": "account",
                "type": "RealAccountNode",
                "category": "realtime",
                "stay_connected": True,
                "position": {"x": 600, "y": 300},
            },
            {
                "id": "historicalData",
                "type": "HistoricalDataNode",
                "category": "data",
                "start_date": "dynamic:months_ago(1)",
                "end_date": "dynamic:today()",
                "interval": "1d",
                "position": {"x": 800, "y": 100},
            },
            {
                "id": "rsiCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {"period": 14, "threshold": 30, "direction": "below"},
                "position": {"x": 1000, "y": 200},
            },
            {
                "id": "buyOrder",
                "type": "NewOrderNode",
                "category": "order",
                "plugin": "FuturesLimitOrder",
                "fields": {
                    "side": "buy",  # 매수
                    "price_type": "limit",
                    "quantity": 1,
                },
                "position": {"x": 1200, "y": 200},
            },
            {
                "id": "display",
                "type": "DisplayNode",
                "category": "display",
                "format": "table",
                "fields": ["symbol", "side", "price", "quantity", "status"],
                "position": {"x": 1400, "y": 200},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "schedule"},
            {"from": "broker", "to": "account"},
            {"from": "schedule", "to": "historicalData"},
            {"from": "watchlist", "to": "historicalData"},
            {"from": "historicalData", "to": "rsiCondition"},
            {"from": "rsiCondition", "to": "buyOrder"},
            {"from": "account", "to": "buyOrder"},
            {"from": "buyOrder", "to": "display"},
        ],
    }
