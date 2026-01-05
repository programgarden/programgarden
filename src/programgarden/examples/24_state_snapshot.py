"""
예제 24: 상태 스냅샷 (State Snapshot)

주기적 상태 저장 및 장애 복구
"""

STATE_SNAPSHOT = {
    "id": "24-state-snapshot",
    "version": "1.0.0",
    "name": "상태 스냅샷 예제",
    "description": "상태 스냅샷 저장 및 복구",
    "settings": {
        "snapshot_enabled": True,
        "snapshot_interval_seconds": 30,
        "snapshot_max_count": 10,  # 최근 10개 스냅샷 유지
        "auto_recovery": True,  # 장애 시 자동 복구
    },
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "restore_from_snapshot": True,  # 시작 시 마지막 스냅샷에서 복구
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
            "cron": "*/10 * * * * *",
            "timezone": "America/New_York",
            "position": {"x": 400, "y": 200},
        },
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
            "symbols": ["AAPL"],
            "position": {"x": 600, "y": 100},
        },
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 800, "y": 100},
        },
        {
            "id": "condition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "params": {"period": 14, "threshold": 30, "direction": "below"},
            "position": {"x": 1000, "y": 100},
        },
        {
            "id": "order",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "params": {"side": "buy"},
            "position": {"x": 1200, "y": 100},
        },
        # 에러 핸들러 - 장애 복구
        {
            "id": "recoveryHandler",
            "type": "ErrorHandlerNode",
            "category": "event",
            "retry_count": 3,
            "retry_delay_seconds": 10,
            "on_max_retry": "restore_snapshot",
            "position": {"x": 1000, "y": 350},
        },
        # 스냅샷 저장 이벤트
        {
            "id": "snapshotEvent",
            "type": "EventHandlerNode",
            "category": "event",
            "event_type": "snapshot_saved",
            "callback": "log_snapshot",
            "position": {"x": 600, "y": 450},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "status", "snapshot_id", "recovery_count"],
            "position": {"x": 1400, "y": 200},
        },
    ],
    "edges": [
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "broker.connection", "to": "account.broker"},
        {"from": "schedule.tick", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "marketData.price", "to": "condition.price_data"},
        {"from": "condition.passed_symbols", "to": "order.trigger"},
        {"from": "order.success", "to": "display.data"},
        {"from": "order.error", "to": "recoveryHandler.error"},
        {"from": "recoveryHandler.retry", "to": "order.trigger"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    result = pg.validate(STATE_SNAPSHOT)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    if result.is_valid:
        job = pg.run(STATE_SNAPSHOT)
        print(f"Job: {job}")
