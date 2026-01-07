"""
예제 23: 일시정지/재개 (Pause Resume)

Job 일시정지 후 상태 보존하여 재개
"""

PAUSE_RESUME = {
    "id": "23-pause-resume",
    "version": "1.0.0",
    "name": "일시정지/재개 예제",
    "description": "24시간 자동매매 - 일시정지/재개 지원",
    "settings": {
        "snapshot_enabled": True,
        "snapshot_interval_seconds": 60,  # 1분마다 상태 저장
        "graceful_shutdown": True,
    },
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
            "company": "ls",
            "product": "overseas_stock",
            "paper_trading": True,
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
        # 계좌 및 시장 데이터
        {
            "id": "account",
            "type": "RealAccountNode",
            "category": "realtime",
            "fields": ["balance", "positions"],
            "position": {"x": 600, "y": 300},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL", "MSFT", "GOOGL"],
            "position": {"x": 600, "y": 100},
        },
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 800, "y": 100},
        },
        # 매매 조건
        {
            "id": "buyCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 1000, "y": 100},
        },
        {
            "id": "buyOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {"side": "buy"},
            "position": {"x": 1200, "y": 100},
        },
        # 일시정지 이벤트 핸들러
        {
            "id": "pauseHandler",
            "type": "EventHandlerNode",
            "category": "event",
            "event_type": "job_paused",
            "callback": "save_state",
            "position": {"x": 600, "y": 400},
        },
        # 재개 이벤트 핸들러
        {
            "id": "resumeHandler",
            "type": "EventHandlerNode",
            "category": "event",
            "event_type": "job_resumed",
            "callback": "restore_state",
            "position": {"x": 800, "y": 400},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "status", "job_state"],
            "position": {"x": 1400, "y": 200},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "broker.connection", "to": "account.broker"},
        {"from": "schedule.tick", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "marketData.price", "to": "buyCondition.price_data"},
        {"from": "buyCondition.passed_symbols", "to": "buyOrder.trigger"},
        {"from": "buyOrder.result", "to": "display.data"},
        # Event handlers
        {"from": "pauseHandler.processed", "to": "display.data"},
        {"from": "resumeHandler.processed", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(PAUSE_RESUME)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(PAUSE_RESUME)
        print(f"Job: {job}")
