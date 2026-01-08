"""04_advanced/w04_risk_guard - 리스크 가드"""


def get_workflow():
    return {
        "id": "advanced-04-risk-guard",
        "version": "1.0.0",
        "name": "리스크 가드 예제",
        "description": "일일 손실 3% 도달 시 거래 중단",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 0, "y": 250}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 250}},
            {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/30 * * * * *", "timezone": "America/New_York", "position": {"x": 400, "y": 250}},
            {"id": "account", "type": "RealAccountNode", "category": "realtime", "fields": ["balance", "daily_pnl", "positions"], "position": {"x": 600, "y": 350}},
            {"id": "riskGuard", "type": "RiskGuardNode", "category": "risk", "rules": [
                {"type": "daily_loss_percent", "threshold": -3, "action": "stop_trading"},
                {"type": "max_positions", "threshold": 10, "action": "no_new_orders"},
            ], "position": {"x": 800, "y": 350}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL"], "position": {"x": 600, "y": 150}},
            {"id": "marketData", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 800, "y": 150}},
            {"id": "condition", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 1000, "y": 150}},
            {"id": "order", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "buy"}, "position": {"x": 1200, "y": 150}},
            {"id": "riskAlert", "type": "AlertNode", "category": "event", "channel": "slack", "template": "⚠️ 리스크 경고: {{rule_type}} 임계치 도달 ({{current_value}})", "position": {"x": 1000, "y": 450}},
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["symbol", "status", "risk_status"], "position": {"x": 1400, "y": 250}},
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "schedule"},
            {"from": "broker.connection", "to": "account.broker"},
            {"from": "account.daily_pnl", "to": "riskGuard.pnl_data"},
            {"from": "account.positions", "to": "riskGuard.positions"},
            {"from": "schedule.tick", "to": "watchlist"},
            {"from": "watchlist.symbols", "to": "marketData.symbols"},
            {"from": "marketData.price", "to": "condition.price_data"},
            {"from": "condition.passed_symbols", "to": "order.trigger"},
            {"from": "riskGuard.allow_trading", "to": "order.gate"},
            {"from": "riskGuard.alert", "to": "riskAlert.data"},
            {"from": "order.result", "to": "display.data"},
        ],
    }
