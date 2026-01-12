"""03_order/w03_position_sizing - 포지션 사이징"""


def get_workflow():
    return {
        "id": "order-03-position-sizing",
        "version": "1.0.0",
        "name": "포지션 사이징 예제",
        "description": "1% 리스크 기반 포지션 크기 결정",
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
                "id": "schedule",
                "type": "ScheduleNode",
                "category": "trigger",
                "cron": "*/30 * * * * *",
                "timezone": "America/New_York",
                "position": {"x": 400, "y": 200},
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NASDAQ", "symbol": "NVDA"}],
                "position": {"x": 600, "y": 100},
            },
            {
                "id": "account",
                "type": "RealAccountNode",
                "category": "realtime",
                "fields": ["balance"],
                "position": {"x": 600, "y": 300},
            },
            {
                "id": "marketData",
                "type": "RealMarketDataNode",
                "category": "realtime",
                "fields": ["price", "volume", "atr"],
                "position": {"x": 800, "y": 100},
            },
            {
                "id": "rsiCond",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {"period": 14, "threshold": 30, "direction": "below"},
                "position": {"x": 1000, "y": 200},
            },
            {
                "id": "positionSize",
                "type": "PositionSizingNode",
                "category": "risk",
                "plugin": "RiskPercentage",
                "fields": {
                    "risk_percent": 1.0,  # 계좌의 1% 리스크
                    "stop_loss_type": "atr",
                    "atr_multiplier": 2.0,
                },
                "position": {"x": 1000, "y": 350},
            },
            {
                "id": "order",
                "type": "NewOrderNode",
                "category": "order",
                "plugin": "MarketOrder",
                "fields": {"side": "buy"},
                "position": {"x": 1200, "y": 200},
            },
            {
                "id": "display",
                "type": "DisplayNode",
                "category": "display",
                "format": "table",
                "fields": ["symbol", "quantity", "entry_price", "stop_loss", "risk_amount"],
                "position": {"x": 1400, "y": 200},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "schedule"},
            {"from": "schedule", "to": "watchlist"},
            {"from": "watchlist", "to": "marketData"},
            {"from": "broker", "to": "account"},
            {"from": "marketData", "to": "rsiCond"},
            {"from": "account", "to": "positionSize"},
            {"from": "marketData", "to": "positionSize"},
            {"from": "rsiCond", "to": "order"},
            {"from": "positionSize", "to": "order"},
            {"from": "order", "to": "display"},
        ],
    }
