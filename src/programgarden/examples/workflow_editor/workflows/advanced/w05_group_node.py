"""04_advanced/w05_group_node - 그룹 노드"""


def get_workflow():
    return {
        "id": "advanced-05-group-node",
        "version": "1.0.0",
        "name": "그룹 노드 예제",
        "description": "매수/매도 전략을 그룹으로 조직화",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 0, "y": 300}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 300}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 400, "y": 300}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL", "MSFT"], "position": {"x": 600, "y": 300}},
            {"id": "marketData", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 800, "y": 200}},
            {"id": "account", "type": "RealAccountNode", "category": "realtime", "fields": ["balance", "positions"], "position": {"x": 800, "y": 400}},
            # === Buy Strategy Group ===
            {"id": "buyGroup", "type": "GroupNode", "category": "group", "name": "Buy Strategy", "color": "#4CAF50", "child_nodes": ["buyRsi", "buyMacd", "buyLogic", "buyOrder"], "position": {"x": 1000, "y": 100}},
            {"id": "buyRsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 1050, "y": 80}},
            {"id": "buyMacd", "type": "ConditionNode", "category": "condition", "plugin": "MACD", "fields": {"signal": "bullish_cross"}, "position": {"x": 1050, "y": 150}},
            {"id": "buyLogic", "type": "LogicNode", "category": "condition", "operator": "all", "position": {"x": 1200, "y": 115}},
            {"id": "buyOrder", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "buy"}, "position": {"x": 1350, "y": 115}},
            # === Sell Strategy Group ===
            {"id": "sellGroup", "type": "GroupNode", "category": "group", "name": "Sell Strategy", "color": "#F44336", "child_nodes": ["sellRsi", "sellMacd", "sellLogic", "sellOrder"], "position": {"x": 1000, "y": 400}},
            {"id": "sellRsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 70, "direction": "above"}, "position": {"x": 1050, "y": 380}},
            {"id": "sellMacd", "type": "ConditionNode", "category": "condition", "plugin": "MACD", "fields": {"signal": "bearish_cross"}, "position": {"x": 1050, "y": 450}},
            {"id": "sellLogic", "type": "LogicNode", "category": "condition", "operator": "all", "position": {"x": 1200, "y": 415}},
            {"id": "sellOrder", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "sell", "amount_type": "all"}, "position": {"x": 1350, "y": 415}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["symbol", "group", "side", "status"], "position": {"x": 1500, "y": 265}},
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "schedule"},
            {"from": "schedule.tick", "to": "watchlist"},
            {"from": "watchlist.symbols", "to": "marketData.symbols"},
            {"from": "broker.connection", "to": "account.broker"},
            # Buy flow
            {"from": "marketData.price", "to": "buyRsi.price_data"},
            {"from": "marketData.price", "to": "buyMacd.price_data"},
            {"from": "buyRsi.result", "to": "buyLogic.input1"},
            {"from": "buyMacd.result", "to": "buyLogic.input2"},
            {"from": "buyLogic.passed_symbols", "to": "buyOrder.trigger"},
            # Sell flow
            {"from": "marketData.price", "to": "sellRsi.price_data"},
            {"from": "marketData.price", "to": "sellMacd.price_data"},
            {"from": "account.positions", "to": "sellRsi.positions"},
            {"from": "sellRsi.result", "to": "sellLogic.input1"},
            {"from": "sellMacd.result", "to": "sellLogic.input2"},
            {"from": "sellLogic.passed_symbols", "to": "sellOrder.trigger"},
            # Display
            {"from": "buyOrder.result", "to": "display.data"},
            {"from": "sellOrder.result", "to": "display.data"},
        ],
    }
