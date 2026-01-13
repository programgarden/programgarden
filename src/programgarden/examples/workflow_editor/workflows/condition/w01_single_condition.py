"""02_condition/01_single_condition - RSI 단일 조건"""


def get_workflow():
    return {
        "id": "06-single-condition",
        "version": "1.0.0",
        "name": "RSI 단일 조건 예제",
        "description": "RSI가 30 이하일 때 통과 → 신규 매수 주문 실행",
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
                "position": {"x": 200, "y": 100},
            },
            {
                "id": "schedule",
                "type": "ScheduleNode",
                "category": "trigger",
                "cron": "*/30 * * * * *",
                "timezone": "America/New_York",
                "position": {"x": 350, "y": 100},
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NASDAQ", "symbol": "TSLA"}, {"exchange": "NASDAQ", "symbol": "NVDA"}],
                "position": {"x": 350, "y": 250},
            },
            {
                "id": "realMarket",
                "type": "RealMarketDataNode",
                "category": "realtime",
                # 바인딩: symbols 필드에 바인딩 표현식
                "symbols": "{{ nodes.watchlist.symbols }}",
                "fields": ["price", "volume"],
                "position": {"x": 550, "y": 175},
            },
            {
                "id": "rsi",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {"period": 14, "threshold": 30, "direction": "below"},
                # 바인딩: price_data 필드에 바인딩 표현식
                "price_data": "{{ nodes.realMarket.price }}",
                "position": {"x": 750, "y": 100},
            },
            {
                "id": "sizing",
                "type": "PositionSizingNode",
                "category": "risk",
                "method": "equal_weight",
                "max_percent": 10,
                # 바인딩: symbols, balance 필드
                "symbols": "{{ nodes.rsi.passed_symbols }}",
                "balance": "{{ nodes.account.balance }}",
                "position": {"x": 950, "y": 100},
            },
            {
                "id": "order",
                "type": "NewOrderNode",
                "category": "order",
                # 새로운 주문 노드 필드
                "product": "overseas_stock",
                "side": "buy",
                "order_type": "limit",
                "market_code": "NASDAQ",
                "price_type": "limit",
                # 바인딩: symbols, quantities, prices 필드
                "symbols": "{{ nodes.rsi.passed_symbols }}",
                "quantities": "{{ nodes.sizing.quantities }}",
                "prices": "{{ nodes.realMarket.price }}",
                "position": {"x": 1150, "y": 100},
            },
            {
                "id": "display",
                "type": "DisplayNode",
                "category": "display",
                "format": "table",
                "fields": ["symbol", "rsi_value", "passed"],
                "position": {"x": 1350, "y": 100},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "schedule"},
            {"from": "broker", "to": "realMarket"},
            {"from": "schedule", "to": "rsi"},
            {"from": "watchlist", "to": "realMarket"},
            {"from": "realMarket", "to": "rsi"},
            {"from": "rsi", "to": "sizing"},
            {"from": "sizing", "to": "order"},
            {"from": "order", "to": "display"},
        ],
    }
