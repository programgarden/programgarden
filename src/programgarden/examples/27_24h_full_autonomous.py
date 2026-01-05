"""
예제 27: 24시간 완전 자동 매매

RSI + 볼린저밴드 + 거래량 조건으로 매수
익절/손절 조건으로 매도
실시간 체결 이벤트 모니터링

계획서의 24h_full_autonomous.py 구현
"""

FULL_AUTONOMOUS_24H = {
    "id": "27-24h-full-autonomous",
    "version": "1.0.0",
    "name": "24시간 완전 자동 매매",
    "description": "RSI+BB+거래량 조건 매수, 익절/손절 매도, 24시간 자동 운영",
    "tags": ["24h", "autonomous", "rsi", "bollinger", "volume"],
    "inputs": {
        "credential_id": {
            "type": "credential",
            "required": True,
            "description": "증권사 인증정보",
        },
        "symbols": {
            "type": "symbol_list",
            "default": ["AAPL", "TSLA", "NVDA"],
            "description": "거래 대상 종목",
        },
    },
    "nodes": [
        # === INFRA ===
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 50, "y": 300},
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "provider": "ls-sec.co.kr",
            "product": "overseas_stock",
            "position": {"x": 200, "y": 300},
        },

        # === SYMBOL ===
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL", "TSLA", "NVDA"],
            "position": {"x": 200, "y": 500},
        },

        # === REALTIME ===
        {
            "id": "realAccount",
            "type": "RealAccountNode",
            "category": "realtime",
            "sync_interval_sec": 60,
            "position": {"x": 400, "y": 200},
        },
        {
            "id": "realMarket",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 400, "y": 400},
        },
        {
            "id": "realOrderEvent",
            "type": "RealOrderEventNode",
            "category": "realtime",
            "position": {"x": 400, "y": 600},
        },

        # === TRIGGER ===
        {
            "id": "buySchedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/5 * * * *",
            "timezone": "America/New_York",
            "position": {"x": 600, "y": 100},
        },
        {
            "id": "sellSchedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/1 * * * *",
            "timezone": "America/New_York",
            "position": {"x": 600, "y": 700},
        },
        {
            "id": "tradingHours",
            "type": "TradingHoursFilterNode",
            "category": "trigger",
            "start": "09:30",
            "end": "16:00",
            "timezone": "America/New_York",
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "position": {"x": 800, "y": 100},
        },
        {
            "id": "exchangeStatus",
            "type": "ExchangeStatusNode",
            "category": "trigger",
            "exchange": "NYSE",
            "check_holidays": True,
            "position": {"x": 1000, "y": 100},
        },

        # === CONDITION (매수) ===
        {
            "id": "rsi",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "params": {
                "period": 14,
                "threshold": 30,
                "direction": "below",
            },
            "position": {"x": 1200, "y": 50},
        },
        {
            "id": "bb",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "BollingerBands",
            "params": {
                "period": 20,
                "std": 2,
                "position": "below_lower",
            },
            "position": {"x": 1200, "y": 150},
        },
        {
            "id": "volume",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "VolumeSpike",
            "params": {
                "period": 20,
                "multiplier": 2,
            },
            "position": {"x": 1200, "y": 250},
        },
        {
            "id": "buyLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "all",
            "position": {"x": 1400, "y": 150},
        },

        # === CONDITION (매도) ===
        {
            "id": "profitTake",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "ProfitTarget",
            "params": {
                "percent": 5,
            },
            "position": {"x": 1200, "y": 650},
        },
        {
            "id": "stopLoss",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "StopLoss",
            "params": {
                "percent": -3,
            },
            "position": {"x": 1200, "y": 750},
        },
        {
            "id": "sellLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "any",
            "position": {"x": 1400, "y": 700},
        },

        # === RISK ===
        {
            "id": "riskGuard",
            "type": "RiskGuardNode",
            "category": "risk",
            "max_daily_loss": -500,
            "max_positions": 5,
            "max_consecutive_losses": 3,
            "position": {"x": 1600, "y": 150},
        },
        {
            "id": "positionSize",
            "type": "PositionSizingNode",
            "category": "risk",
            "method": "kelly",
            "max_percent": 10,
            "kelly_fraction": 0.25,
            "position": {"x": 1800, "y": 150},
        },

        # === ORDER ===
        {
            "id": "buyOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "params": {
                "side": "buy",
            },
            "position": {"x": 2000, "y": 150},
        },
        {
            "id": "sellOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "params": {
                "side": "sell",
                "amount_type": "all",
            },
            "position": {"x": 1600, "y": 700},
        },

        # === EVENT ===
        {
            "id": "onFilled",
            "type": "EventHandlerNode",
            "category": "event",
            "event": "filled",
            "actions": ["log"],
            "position": {"x": 600, "y": 800},
        },
        {
            "id": "alert",
            "type": "AlertNode",
            "category": "event",
            "channel": "slack",
            "on": ["order_filled", "risk_triggered"],
            "position": {"x": 800, "y": 800},
        },
    ],
    "edges": [
        # Infra 연결
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "realAccount"},
        {"from": "broker.connection", "to": "realMarket"},
        {"from": "broker.connection", "to": "realOrderEvent"},

        # Symbol 연결
        {"from": "watchlist.symbols", "to": "realMarket.symbols"},

        # 매수 트리거 플로우
        {"from": "buySchedule.trigger", "to": "tradingHours"},
        {"from": "tradingHours.passed", "to": "exchangeStatus"},
        {"from": "exchangeStatus.open", "to": "rsi"},
        {"from": "exchangeStatus.open", "to": "bb"},
        {"from": "exchangeStatus.open", "to": "volume"},

        # 매수 조건 데이터 연결
        {"from": "realMarket.price", "to": "rsi.price_data"},
        {"from": "realMarket.price", "to": "bb.price_data"},
        {"from": "realMarket.volume", "to": "volume.volume_data"},

        # 매수 조건 조합
        {"from": "rsi.result", "to": "buyLogic.input"},
        {"from": "bb.result", "to": "buyLogic.input"},
        {"from": "volume.result", "to": "buyLogic.input"},

        # 매수 리스크 체크
        {"from": "buyLogic.passed_symbols", "to": "riskGuard.symbols"},
        {"from": "realAccount.balance", "to": "riskGuard.account_state"},
        {"from": "riskGuard.approved_symbols", "to": "positionSize.symbols"},
        {"from": "realAccount.balance", "to": "positionSize.balance"},

        # 매수 주문
        {"from": "positionSize.quantity", "to": "buyOrder.quantity"},
        {"from": "positionSize.symbols", "to": "buyOrder.symbols"},
        {"from": "realAccount.held_symbols", "to": "buyOrder.held_symbols"},

        # 매도 트리거 플로우
        {"from": "sellSchedule.trigger", "to": "profitTake"},
        {"from": "sellSchedule.trigger", "to": "stopLoss"},

        # 매도 조건 데이터 연결
        {"from": "realAccount.positions", "to": "profitTake.position_data"},
        {"from": "realAccount.positions", "to": "stopLoss.position_data"},
        {"from": "realMarket.price", "to": "profitTake.price_data"},
        {"from": "realMarket.price", "to": "stopLoss.price_data"},

        # 매도 조건 조합
        {"from": "profitTake.result", "to": "sellLogic.input"},
        {"from": "stopLoss.result", "to": "sellLogic.input"},

        # 매도 주문
        {"from": "sellLogic.passed_symbols", "to": "sellOrder.symbols"},
        {"from": "realAccount.held_symbols", "to": "sellOrder.held_symbols"},

        # 이벤트 핸들링
        {"from": "realOrderEvent.filled", "to": "onFilled.event"},
        {"from": "onFilled.event", "to": "alert.event"},
        {"from": "riskGuard.blocked_reason", "to": "alert.event"},
    ],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    pg = ProgramGarden()

    # 검증
    result = pg.validate(FULL_AUTONOMOUS_24H)
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")

    # 노드 카테고리 통계
    from collections import Counter
    categories = Counter(n["category"] for n in FULL_AUTONOMOUS_24H["nodes"])
    print(f"\nNode categories: {dict(categories)}")
    print(f"Total nodes: {len(FULL_AUTONOMOUS_24H['nodes'])}")
    print(f"Total edges: {len(FULL_AUTONOMOUS_24H['edges'])}")
