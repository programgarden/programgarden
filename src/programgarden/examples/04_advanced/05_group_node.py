"""
예제 21: 그룹 노드 (Group Node)

매수/매도 전략을 그룹으로 묶어 관리
"""

GROUP_NODE = {
    "id": "21-group-node",
    "version": "1.0.0",
    "name": "그룹 노드 예제",
    "description": "매수/매도 전략을 그룹으로 조직화",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 0, "y": 300},
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "company": "ls",
            "product": "overseas_stock",
            "paper_trading": True,
            "position": {"x": 200, "y": 300},
        },
        {
            "id": "schedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 400, "y": 300},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL", "MSFT"],
            "position": {"x": 600, "y": 300},
        },
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 800, "y": 200},
        },
        {
            "id": "account",
            "type": "RealAccountNode",
            "category": "realtime",
            "fields": ["balance", "positions"],
            "position": {"x": 800, "y": 400},
        },
        # === Buy Strategy Group ===
        {
            "id": "buyGroup",
            "type": "GroupNode",
            "category": "group",
            "name": "Buy Strategy",
            "color": "#4CAF50",
            "child_nodes": ["buyRsi", "buyMacd", "buyLogic", "buyOrder"],
            "position": {"x": 1000, "y": 100},
        },
        {
            "id": "buyRsi",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 1050, "y": 80},
        },
        {
            "id": "buyMacd",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "MACD",
            "fields": {"signal": "bullish_cross"},
            "position": {"x": 1050, "y": 150},
        },
        {
            "id": "buyLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "all",
            "position": {"x": 1200, "y": 115},
        },
        {
            "id": "buyOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {"side": "buy"},
            "position": {"x": 1350, "y": 115},
        },
        # === Sell Strategy Group ===
        {
            "id": "sellGroup",
            "type": "GroupNode",
            "category": "group",
            "name": "Sell Strategy",
            "color": "#f44336",
            "child_nodes": ["sellProfit", "sellStop", "sellLogic", "sellOrder"],
            "position": {"x": 1000, "y": 350},
        },
        {
            "id": "sellProfit",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "ProfitTarget",
            "fields": {"percent": 5},
            "position": {"x": 1050, "y": 330},
        },
        {
            "id": "sellStop",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "StopLoss",
            "fields": {"percent": -3},
            "position": {"x": 1050, "y": 400},
        },
        {
            "id": "sellLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "any",
            "position": {"x": 1200, "y": 365},
        },
        {
            "id": "sellOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {"side": "sell", "amount_type": "all"},
            "position": {"x": 1350, "y": 365},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["group", "symbol", "side", "status"],
            "position": {"x": 1500, "y": 240},
        },
    ],
    "edges": [
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "schedule.tick", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "broker.connection", "to": "account.broker"},
        # Buy group
        {"from": "marketData.price", "to": "buyRsi.price_data"},
        {"from": "marketData.price", "to": "buyMacd.price_data"},
        {"from": "buyRsi.result", "to": "buyLogic.conditions"},
        {"from": "buyMacd.result", "to": "buyLogic.conditions"},
        {"from": "buyLogic.result", "to": "buyOrder.trigger"},
        # Sell group
        {"from": "account.positions", "to": "sellProfit.positions"},
        {"from": "account.positions", "to": "sellStop.positions"},
        {"from": "marketData.price", "to": "sellProfit.price_data"},
        {"from": "marketData.price", "to": "sellStop.price_data"},
        {"from": "sellProfit.result", "to": "sellLogic.conditions"},
        {"from": "sellStop.result", "to": "sellLogic.conditions"},
        {"from": "sellLogic.result", "to": "sellOrder.trigger"},
        # Display
        {"from": "buyOrder.result", "to": "display.data"},
        {"from": "sellOrder.result", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(GROUP_NODE)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(GROUP_NODE)
        print(f"Job: {job}")
