"""
동전주 RSI 과매도 매수 전략
============================

전략 ID: penny_stock_rsi
버전: 1.0.0

설명
----
예수금 1~2만원($15)으로 저가 레버리지 ETF를 
RSI 과매도 시 자동 매수하는 전략입니다.

대상 종목
---------
- SOXS: 반도체 3x 인버스 (~$15)
- SQQQ: 나스닥 3x 인버스 (~$10)
- FAZ: 금융 3x 인버스 (~$15)

매수 조건
---------
- RSI(14) < 30 (과매도)
- 미국 정규장 시간 내

매도 조건
---------
- 익절: +5%
- 손절: -3%

사용법
------
    from programgarden_community.strategies import get_strategy
    from programgarden import ProgramGarden
    
    strategy = get_strategy("overseas_stock", "penny_stock_rsi")
    
    pg = ProgramGarden()
    result = pg.validate(strategy)
    if result.is_valid:
        job = pg.run(strategy)
"""

PENNY_STOCK_RSI = {
    "id": "penny-stock-rsi-strategy",
    "version": "1.0.0",
    "name": "동전주 RSI 과매도 매수 전략",
    "description": "예수금 1~2만원으로 저가 ETF RSI 과매도 시 매수, 익절/손절 자동화",
    "tags": ["penny_stock", "rsi", "etf", "low_budget"],
    "author": "ProgramGarden Team",
    "inputs": {
        "symbols": {
            "type": "symbol_list",
            "default": ["SOXS", "SQQQ", "FAZ"],
            "description": "대상 종목 (저가 레버리지 ETF)",
        },
        "rsi_period": {
            "type": "int",
            "default": 14,
            "description": "RSI 계산 기간",
        },
        "rsi_threshold": {
            "type": "float",
            "default": 30,
            "description": "과매도 기준 RSI",
        },
        "profit_target": {
            "type": "float",
            "default": 5.0,
            "description": "익절 목표 (%)",
        },
        "stop_loss": {
            "type": "float",
            "default": -3.0,
            "description": "손절 기준 (%)",
        },
        "balance_percent": {
            "type": "float",
            "default": 90,
            "description": "예수금 사용 비율 (%)",
        },
    },
    "nodes": [
        # === INFRA ===
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
            "paper_trading": False,  # 실계좌
            "position": {"x": 150, "y": 300},
        },
        
        # === TRIGGER ===
        {
            "id": "schedule",
            "type": "ScheduleNode",
            "category": "trigger",
            "cron": "*/30 * * * * *",  # 30초마다
            "timezone": "America/New_York",
            "position": {"x": 300, "y": 300},
        },
        {
            "id": "tradingHours",
            "type": "TradingHoursFilterNode",
            "category": "trigger",
            "market": "US",
            "session": "regular",  # 정규장만
            "position": {"x": 450, "y": 300},
        },
        
        # === SYMBOL ===
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": "$input.symbols",
            "position": {"x": 600, "y": 300},
        },
        
        # === REALTIME DATA ===
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 750, "y": 200},
        },
        {
            "id": "account",
            "type": "RealAccountNode",
            "category": "realtime",
            "fields": ["balance", "positions"],
            "position": {"x": 750, "y": 400},
        },
        
        # === BUY CONDITION ===
        {
            "id": "rsiBuy",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {
                "period": "$input.rsi_period",
                "threshold": "$input.rsi_threshold",
                "direction": "below",
            },
            "position": {"x": 900, "y": 150},
        },
        
        # === SELL CONDITIONS ===
        {
            "id": "profitTarget",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "ProfitTarget",
            "fields": {
                "percent": "$input.profit_target",
            },
            "position": {"x": 900, "y": 350},
        },
        {
            "id": "stopLoss",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "StopLoss",
            "fields": {
                "percent": "$input.stop_loss",
            },
            "position": {"x": 900, "y": 450},
        },
        {
            "id": "sellLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "or",
            "position": {"x": 1050, "y": 400},
        },
        
        # === POSITION SIZING ===
        {
            "id": "sizing",
            "type": "PositionSizingNode",
            "category": "risk",
            "method": "percent_balance",
            "percent": "$input.balance_percent",
            "max_per_symbol": 15,  # 종목당 최대 $15
            "position": {"x": 1050, "y": 150},
        },
        
        # === ORDERS ===
        {
            "id": "buyOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {
                "side": "buy",
                "amount_type": "calculated",
            },
            "position": {"x": 1200, "y": 150},
        },
        {
            "id": "sellOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {
                "side": "sell",
                "amount_type": "all",
            },
            "position": {"x": 1200, "y": 400},
        },
        
        # === EVENT HANDLER ===
        {
            "id": "orderEvent",
            "type": "EventHandlerNode",
            "category": "event",
            "event_type": "order_filled",
            "position": {"x": 1350, "y": 275},
        },
        
        # === DISPLAY ===
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "side", "quantity", "price", "status", "pnl"],
            "position": {"x": 1500, "y": 275},
        },
    ],
    "edges": [
        # Infra flow
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "schedule.tick", "to": "tradingHours"},
        {"from": "tradingHours.passed", "to": "watchlist"},
        
        # Data flow
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "broker.connection", "to": "account.broker"},
        
        # Buy flow
        {"from": "marketData.price", "to": "rsiBuy.price_data"},
        {"from": "rsiBuy.passed_symbols", "to": "sizing.symbols"},
        {"from": "account.balance", "to": "sizing.balance"},
        {"from": "sizing.quantities", "to": "buyOrder.quantities"},
        {"from": "rsiBuy.passed_symbols", "to": "buyOrder.trigger"},
        
        # Sell flow
        {"from": "account.positions", "to": "profitTarget.position_data"},
        {"from": "marketData.price", "to": "profitTarget.price_data"},
        {"from": "account.positions", "to": "stopLoss.position_data"},
        {"from": "marketData.price", "to": "stopLoss.price_data"},
        {"from": "profitTarget.passed_symbols", "to": "sellLogic.input"},
        {"from": "stopLoss.passed_symbols", "to": "sellLogic.input"},
        {"from": "sellLogic.passed_symbols", "to": "sellOrder.trigger"},
        
        # Event & Display
        {"from": "buyOrder.result", "to": "orderEvent.event"},
        {"from": "sellOrder.result", "to": "orderEvent.event"},
        {"from": "orderEvent.processed", "to": "display.data"},
    ],
}


__all__ = ["PENNY_STOCK_RSI"]
