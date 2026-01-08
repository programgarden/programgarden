"""05_operation/w06_24h_autonomous - 24시간 완전 자동 매매"""


def get_workflow():
    return {
        "id": "operation-06-24h-autonomous",
        "version": "1.0.0",
        "name": "24시간 완전 자동 매매",
        "description": "RSI+BB+거래량 조건 매수, 익절/손절 매도, 24시간 자동 운영",
        "tags": ["24h", "autonomous", "rsi", "bollinger", "volume"],
        "inputs": {
            "symbols": {
                "type": "symbol_list",
                "default": ["AAPL", "TSLA", "NVDA"],
                "description": "거래 대상 종목",
            },
        },
        "nodes": [
            # === INFRA ===
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 50, "y": 300}},
            {"id": "broker", "type": "BrokerNode", "category": "infra", "provider": "ls-sec.co.kr", "product": "overseas_stock", "position": {"x": 200, "y": 300}},
            # === SYMBOL ===
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": ["AAPL", "TSLA", "NVDA"], "position": {"x": 200, "y": 500}},
            # === REALTIME ===
            {"id": "realAccount", "type": "RealAccountNode", "category": "realtime", "sync_interval_sec": 60, "position": {"x": 400, "y": 200}},
            {"id": "realMarket", "type": "RealMarketDataNode", "category": "realtime", "fields": ["price", "volume"], "position": {"x": 400, "y": 400}},
            {"id": "realOrderEvent", "type": "RealOrderEventNode", "category": "realtime", "position": {"x": 400, "y": 600}},
            # === TRIGGER ===
            {"id": "buySchedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/5 * * * *", "timezone": "America/New_York", "position": {"x": 600, "y": 100}},
            {"id": "sellSchedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/1 * * * *", "timezone": "America/New_York", "position": {"x": 600, "y": 700}},
            {"id": "tradingHours", "type": "TradingHoursFilterNode", "category": "trigger", "start": "09:30", "end": "16:00", "timezone": "America/New_York", "days": ["mon", "tue", "wed", "thu", "fri"], "position": {"x": 800, "y": 100}},
            {"id": "exchangeStatus", "type": "ExchangeStatusNode", "category": "trigger", "exchange": "NYSE", "check_holidays": True, "position": {"x": 1000, "y": 100}},
            # === CONDITION (매수) ===
            {"id": "rsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 1200, "y": 50}},
            {"id": "bb", "type": "ConditionNode", "category": "condition", "plugin": "BollingerBands", "fields": {"period": 20, "std": 2, "position": "below_lower"}, "position": {"x": 1200, "y": 150}},
            {"id": "volume", "type": "ConditionNode", "category": "condition", "plugin": "VolumeSpike", "fields": {"period": 20, "multiplier": 2}, "position": {"x": 1200, "y": 250}},
            {"id": "buyLogic", "type": "LogicNode", "category": "condition", "operator": "all", "position": {"x": 1400, "y": 150}},
            # === CONDITION (매도) ===
            {"id": "profitTake", "type": "ConditionNode", "category": "condition", "plugin": "ProfitTarget", "fields": {"percent": 5}, "position": {"x": 1200, "y": 650}},
            {"id": "stopLoss", "type": "ConditionNode", "category": "condition", "plugin": "StopLoss", "fields": {"percent": -3}, "position": {"x": 1200, "y": 750}},
            {"id": "sellLogic", "type": "LogicNode", "category": "condition", "operator": "any", "position": {"x": 1400, "y": 700}},
            # === RISK ===
            {"id": "riskGuard", "type": "RiskGuardNode", "category": "risk", "max_daily_loss": -500, "max_positions": 5, "max_consecutive_losses": 3, "position": {"x": 1600, "y": 150}},
            {"id": "positionSize", "type": "PositionSizingNode", "category": "risk", "method": "kelly", "position": {"x": 1600, "y": 300}},
            # === ORDER ===
            {"id": "buyOrder", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "buy"}, "position": {"x": 1800, "y": 200}},
            {"id": "sellOrder", "type": "NewOrderNode", "category": "order", "plugin": "MarketOrder", "fields": {"side": "sell", "amount_type": "all"}, "position": {"x": 1800, "y": 700}},
            # === DISPLAY ===
            {"id": "display", "type": "DisplayNode", "category": "display", "format": "table", "fields": ["symbol", "side", "quantity", "status", "pnl"], "position": {"x": 2000, "y": 400}},
        ],
        "edges": [
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "realAccount.broker"},
            {"from": "watchlist.symbols", "to": "realMarket.symbols"},
            {"from": "broker.connection", "to": "realOrderEvent"},
            {"from": "broker.connection", "to": "buySchedule"},
            {"from": "broker.connection", "to": "sellSchedule"},
            {"from": "buySchedule.tick", "to": "tradingHours"},
            {"from": "tradingHours.within_hours", "to": "exchangeStatus"},
            {"from": "exchangeStatus.is_open", "to": "rsi.gate"},
            {"from": "realMarket.price", "to": "rsi.price_data"},
            {"from": "realMarket.price", "to": "bb.price_data"},
            {"from": "realMarket.volume", "to": "volume.volume_data"},
            {"from": "rsi.result", "to": "buyLogic.input1"},
            {"from": "bb.result", "to": "buyLogic.input2"},
            {"from": "volume.result", "to": "buyLogic.input3"},
            {"from": "buyLogic.passed_symbols", "to": "riskGuard.trigger"},
            {"from": "riskGuard.allow_trading", "to": "positionSize.trigger"},
            {"from": "realAccount.balance", "to": "positionSize.account_info"},
            {"from": "positionSize.quantity", "to": "buyOrder.quantity"},
            {"from": "buyLogic.passed_symbols", "to": "buyOrder.trigger"},
            {"from": "sellSchedule.tick", "to": "profitTake.trigger"},
            {"from": "realAccount.positions", "to": "profitTake.positions"},
            {"from": "realAccount.positions", "to": "stopLoss.positions"},
            {"from": "profitTake.result", "to": "sellLogic.input1"},
            {"from": "stopLoss.result", "to": "sellLogic.input2"},
            {"from": "sellLogic.passed_symbols", "to": "sellOrder.trigger"},
            {"from": "buyOrder.result", "to": "display.data"},
            {"from": "sellOrder.result", "to": "display.data"},
        ],
    }
