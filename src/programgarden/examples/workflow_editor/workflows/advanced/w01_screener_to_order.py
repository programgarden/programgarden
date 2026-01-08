"""04_advanced/w01_screener_to_order - 스크리너 → 주문"""


def get_workflow():
    return {
        "id": "advanced-01-screener",
        "version": "1.0.0",
        "name": "스크리너 → 주문 예제",
        "description": "나스닥100에서 RSI 과매도 종목 스크리닝 후 매수",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 0, "y": 200}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 200}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "0 9 * * 1-5", "timezone": "America/New_York", "position": {"x": 400, "y": 200}},
            {"id": "universe", "type": "MarketUniverseNode", "category": "symbol", "market": "nasdaq", "index": "ndx100", "position": {"x": 600, "y": 200}},
            {"id": "capFilter", "type": "SymbolFilterNode", "category": "symbol", "filter_type": "market_cap", "fields": {"min": 10_000_000_000}, "position": {"x": 800, "y": 200}},
            {"id": "screener", "type": "ScreenerNode", "category": "symbol", "plugin": "RSI", "fields": {"threshold": 30, "direction": "below"}, "limit": 5, "position": {"x": 1000, "y": 200}},
            {"id": "marketData", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 1200, "y": 200}},
            {"id": "sizing", "type": "PositionSizingNode", "category": "risk", "method": "equal_weight", "fields": {"max_positions": 5}, "position": {"x": 1400, "y": 200}},
            {"id": "buyOrder", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "buy"}, "position": {"x": 1600, "y": 200}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["symbol", "screener_rank", "quantity", "status"], "position": {"x": 1800, "y": 200}},
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "schedule"},
            {"from": "schedule.tick", "to": "universe"},
            {"from": "universe.symbols", "to": "capFilter.symbols"},
            {"from": "capFilter.passed_symbols", "to": "screener.symbols"},
            {"from": "screener.ranked_symbols", "to": "marketData.symbols"},
            {"from": "marketData.price", "to": "sizing.price_data"},
            {"from": "sizing.quantity", "to": "buyOrder.quantity"},
            {"from": "screener.ranked_symbols", "to": "buyOrder.trigger"},
            {"from": "buyOrder.result", "to": "display.data"},
        ],
    }
