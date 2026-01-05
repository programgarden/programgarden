"""
예제 26: 장시간 실행 (Long Running Job)

24시간 연속 운영 + 일별 리포트
"""

LONG_RUNNING = {
    "id": "26-long-running",
    "version": "1.0.0",
    "name": "장시간 실행 예제",
    "description": "24시간 연속 운영 + 일별 리포트",
    "settings": {
        "snapshot_enabled": True,
        "snapshot_interval_seconds": 60,
        "graceful_shutdown": True,
        "daily_report_enabled": True,
        "daily_report_time": "16:30",  # 장 마감 후
        "health_check_interval_seconds": 30,
    },
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
        # === 실시간 데이터 ===
        {
            "id": "account",
            "type": "RealAccountNode",
            "category": "realtime",
            "fields": ["balance", "positions", "daily_pnl"],
            "position": {"x": 400, "y": 400},
        },
        # === 매매 스케줄 ===
        {
            "id": "tradeSchedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 400, "y": 200},
        },
        {
            "id": "hours",
            "type": "TradingHoursFilterNode",
            "category": "trigger",
            "market": "NYSE",
            "session": "regular",
            "timezone": "America/New_York",
            "position": {"x": 600, "y": 200},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"],
            "position": {"x": 800, "y": 200},
        },
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 1000, "y": 200},
        },
        # === 매수 조건 ===
        {
            "id": "buyRsi",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "params": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 1200, "y": 100},
        },
        {
            "id": "buyMacd",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "MACD",
            "params": {"signal": "bullish_cross"},
            "position": {"x": 1200, "y": 200},
        },
        {
            "id": "buyLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "all",
            "position": {"x": 1400, "y": 150},
        },
        # === 리스크 관리 ===
        {
            "id": "riskGuard",
            "type": "RiskGuardNode",
            "category": "risk",
            "rules": [
                {"type": "daily_loss_percent", "threshold": -3, "action": "stop_trading"},
                {"type": "max_positions", "threshold": 10, "action": "no_new_orders"},
            ],
            "position": {"x": 1400, "y": 400},
        },
        {
            "id": "sizing",
            "type": "PositionSizingNode",
            "category": "risk",
            "method": "risk_percent",
            "params": {"risk_percent": 1},
            "position": {"x": 1600, "y": 150},
        },
        {
            "id": "buyOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "params": {"side": "buy"},
            "position": {"x": 1800, "y": 150},
        },
        # === 일별 리포트 스케줄 ===
        {
            "id": "reportSchedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "30 16 * * 1-5",  # 평일 16:30
            "timezone": "America/New_York",
            "position": {"x": 400, "y": 550},
        },
        {
            "id": "dailyReport",
            "type": "EventHandlerNode",
            "category": "event",
            "event_type": "schedule_tick",
            "callback": "generate_daily_report",
            "position": {"x": 600, "y": 550},
        },
        {
            "id": "reportAlert",
            "type": "AlertNode",
            "category": "event",
            "channel": "email",
            "template": "📊 일일 트레이딩 리포트\n━━━━━━━━━━━━━━━━━━\n📈 실현 손익: {{realized_pnl}}\n📉 미실현 손익: {{unrealized_pnl}}\n🔢 거래 횟수: {{trade_count}}\n✅ 성공률: {{win_rate}}%",
            "position": {"x": 800, "y": 550},
        },
        # === 헬스체크 ===
        {
            "id": "healthSchedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 400, "y": 700},
        },
        {
            "id": "healthCheck",
            "type": "EventHandlerNode",
            "category": "event",
            "event_type": "schedule_tick",
            "callback": "perform_health_check",
            "position": {"x": 600, "y": 700},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "status", "daily_pnl", "health_status"],
            "position": {"x": 2000, "y": 400},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "tradeSchedule"},
        {"from": "broker.connection", "to": "account.broker"},
        {"from": "broker.connection", "to": "reportSchedule"},
        {"from": "broker.connection", "to": "healthSchedule"},
        # Trading flow
        {"from": "tradeSchedule.tick", "to": "hours"},
        {"from": "hours.within_hours", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "marketData.price", "to": "buyRsi.price_data"},
        {"from": "marketData.price", "to": "buyMacd.price_data"},
        {"from": "buyRsi.result", "to": "buyLogic.conditions"},
        {"from": "buyMacd.result", "to": "buyLogic.conditions"},
        {"from": "buyLogic.result", "to": "sizing.trigger"},
        {"from": "account.balance", "to": "sizing.balance"},
        {"from": "sizing.quantity", "to": "buyOrder.quantity"},
        {"from": "riskGuard.allow", "to": "buyOrder.gate"},
        {"from": "account.data", "to": "riskGuard.account_data"},
        # Report flow
        {"from": "reportSchedule.tick", "to": "dailyReport"},
        {"from": "account.summary", "to": "dailyReport.data"},
        {"from": "dailyReport.processed", "to": "reportAlert.data"},
        # Health check flow
        {"from": "healthSchedule.tick", "to": "healthCheck"},
        # Display
        {"from": "buyOrder.result", "to": "display.data"},
        {"from": "reportAlert.sent", "to": "display.data"},
        {"from": "healthCheck.processed", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(LONG_RUNNING)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(LONG_RUNNING)
        print(f"Job: {job}")
