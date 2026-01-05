"""
예제 20: 리스크 가드 (Risk Guard)

일일 최대 손실 도달 시 거래 중단
"""

RISK_GUARD = {
    "id": "20-risk-guard",
    "version": "1.0.0",
    "name": "리스크 가드 예제",
    "description": "일일 손실 3% 도달 시 거래 중단",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 0, "y": 250},
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "company": "ls",
            "product": "overseas_stock",
            "paper_trading": True,
            "position": {"x": 200, "y": 250},
        },
        {
            "id": "schedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 400, "y": 250},
        },
        # 실시간 계좌 정보
        {
            "id": "account",
            "type": "RealAccountNode",
            "category": "realtime",
            "fields": ["balance", "daily_pnl", "positions"],
            "position": {"x": 600, "y": 350},
        },
        # 리스크 가드
        {
            "id": "riskGuard",
            "type": "RiskGuardNode",
            "category": "risk",
            "rules": [
                {"type": "daily_loss_percent", "threshold": -3, "action": "stop_trading"},
                {"type": "max_positions", "threshold": 10, "action": "no_new_orders"},
            ],
            "position": {"x": 800, "y": 350},
        },
        # 정상 흐름
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL"],
            "position": {"x": 600, "y": 150},
        },
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 800, "y": 150},
        },
        {
            "id": "condition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "params": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 1000, "y": 150},
        },
        {
            "id": "order",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "params": {"side": "buy"},
            "position": {"x": 1200, "y": 150},
        },
        # 리스크 초과 알림
        {
            "id": "riskAlert",
            "type": "AlertNode",
            "category": "event",
            "channel": "slack",
            "template": "⚠️ 리스크 경고: {{rule_type}} 임계치 도달 ({{current_value}})",
            "position": {"x": 1000, "y": 450},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "status", "risk_status"],
            "position": {"x": 1400, "y": 250},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "broker.connection", "to": "account.broker"},
        {"from": "account.data", "to": "riskGuard.account_data"},
        # Risk guard gates the normal flow
        {"from": "schedule.tick", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "marketData.price", "to": "condition.price_data"},
        {"from": "condition.passed_symbols", "to": "order.trigger"},
        {"from": "riskGuard.allow", "to": "order.gate"},
        # Risk exceeded
        {"from": "riskGuard.exceeded", "to": "riskAlert.data"},
        {"from": "order.result", "to": "display.data"},
        {"from": "riskAlert.sent", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(RISK_GUARD)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(RISK_GUARD)
        print(f"Job: {job}")
