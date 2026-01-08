"""
예제 25: 다중 시장 (Multi Market)

미국 주식 + 미국 선물 동시 운영
"""

MULTI_MARKET = {
    "id": "25-multi-market",
    "version": "1.0.0",
    "name": "다중 시장 예제",
    "description": "미국 주식 + 선물 동시 운영",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 0, "y": 300},
        },
        # === 주식 Broker ===
        {
            "id": "stockBroker",
            "type": "BrokerNode",
            "category": "infra",
            "company": "ls",
            "product": "overseas_stock",
            "paper_trading": True,
            "position": {"x": 200, "y": 150},
        },
        # === 선물 Broker ===
        {
            "id": "futuresBroker",
            "type": "BrokerNode",
            "category": "infra",
            "company": "ls",
            "product": "overseas_futures",
            "paper_trading": True,
            "position": {"x": 200, "y": 450},
        },
        # === Stock Trading Group ===
        {
            "id": "stockGroup",
            "type": "GroupNode",
            "category": "group",
            "name": "US Stock Trading",
            "color": "#2196F3",
            "child_nodes": ["stockSchedule", "stockHours", "stockWatchlist", "stockMarket", "stockCondition", "stockOrder"],
            "position": {"x": 400, "y": 50},
        },
        {
            "id": "stockSchedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 450, "y": 80},
        },
        {
            "id": "stockHours",
            "type": "TradingHoursFilterNode",
            "category": "trigger",
            "market": "NYSE",
            "session": "regular",
            "timezone": "America/New_York",
            "position": {"x": 600, "y": 80},
        },
        {
            "id": "stockWatchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL", "MSFT", "NVDA"],
            "position": {"x": 750, "y": 80},
        },
        {
            "id": "stockMarket",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 900, "y": 80},
        },
        {
            "id": "stockCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 1050, "y": 80},
        },
        {
            "id": "stockOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {"side": "buy"},
            "position": {"x": 1200, "y": 80},
        },
        # === Futures Trading Group ===
        {
            "id": "futuresGroup",
            "type": "GroupNode",
            "category": "group",
            "name": "US Futures Trading",
            "color": "#FF9800",
            "child_nodes": ["futuresSchedule", "futuresHours", "futuresWatchlist", "futuresMarket", "futuresCondition", "futuresOrder"],
            "position": {"x": 400, "y": 350},
        },
        {
            "id": "futuresSchedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/10 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 450, "y": 380},
        },
        {
            "id": "futuresHours",
            "type": "TradingHoursFilterNode",
            "category": "trigger",
            "market": "CME",
            "session": "extended",
            "timezone": "America/New_York",
            "position": {"x": 600, "y": 380},
        },
        {
            "id": "futuresWatchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["ESH5", "NQH5"],  # E-mini S&P, Nasdaq
            "position": {"x": 750, "y": 380},
        },
        {
            "id": "futuresMarket",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 900, "y": 380},
        },
        {
            "id": "futuresCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "MACD",
            "fields": {"signal": "bullish_cross"},
            "position": {"x": 1050, "y": 380},
        },
        {
            "id": "futuresOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {"side": "buy"},
            "position": {"x": 1200, "y": 380},
        },
        # === 공통 리스크 관리 ===
        {
            "id": "globalRisk",
            "type": "RiskGuardNode",
            "category": "risk",
            "rules": [
                {"type": "total_exposure_percent", "threshold": 50, "action": "no_new_orders"},
                {"type": "daily_loss_percent", "threshold": -5, "action": "stop_trading"},
            ],
            "position": {"x": 1000, "y": 550},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["market", "symbol", "side", "status"],
            "position": {"x": 1400, "y": 300},
        },
    ],
    "edges": [
        {"from": "start.start", "to": "stockBroker"},
        {"from": "start.start", "to": "futuresBroker"},
        # Stock flow
        {"from": "stockBroker.connection", "to": "stockSchedule"},
        {"from": "stockSchedule.tick", "to": "stockHours"},
        {"from": "stockHours.within_hours", "to": "stockWatchlist"},
        {"from": "stockWatchlist.symbols", "to": "stockMarket.symbols"},
        {"from": "stockMarket.price", "to": "stockCondition.price_data"},
        {"from": "stockCondition.passed_symbols", "to": "stockOrder.trigger"},
        {"from": "globalRisk.allow", "to": "stockOrder.gate"},
        # Futures flow
        {"from": "futuresBroker.connection", "to": "futuresSchedule"},
        {"from": "futuresSchedule.tick", "to": "futuresHours"},
        {"from": "futuresHours.within_hours", "to": "futuresWatchlist"},
        {"from": "futuresWatchlist.symbols", "to": "futuresMarket.symbols"},
        {"from": "futuresMarket.price", "to": "futuresCondition.price_data"},
        {"from": "futuresCondition.passed_symbols", "to": "futuresOrder.trigger"},
        {"from": "globalRisk.allow", "to": "futuresOrder.gate"},
        # Risk guard receives account data from both brokers
        {"from": "stockBroker.account", "to": "globalRisk.accounts"},
        {"from": "futuresBroker.account", "to": "globalRisk.accounts"},
        # Display
        {"from": "stockOrder.result", "to": "display.data"},
        {"from": "futuresOrder.result", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(MULTI_MARKET)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(MULTI_MARKET)
        print(f"Job: {job}")
