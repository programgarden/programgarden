"""06_backtest/w02_backtest_with_deploy - 백테스트 → 자동 배포"""


def get_workflow():
    return {
        "id": "backtest-02-with-deploy",
        "version": "1.0.0",
        "name": "백테스트 성과 기반 자동 배포",
        "description": "백테스트 결과가 기준 충족 시 paper_trading 자동 배포",
        "tags": ["backtest", "deploy", "paper_trading", "automation"],
        "inputs": {
            "symbols": {"type": "symbol_list", "default": ["AAPL", "MSFT", "GOOGL"], "description": "백테스트 및 배포 대상 종목"},
            "backtest_months": {"type": "integer", "default": 6, "description": "백테스트 기간 (개월)"},
        },
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 50, "y": 300}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": "{{ input.symbols }}", "position": {"x": 200, "y": 300}},
            {"id": "historicalData", "type": "HistoricalDataNode", "category": "data", "start_date": "{{ months_ago(input.backtest_months) }}", "end_date": "{{ today() }}", "interval": "1d", "position": {"x": 400, "y": 300}},
            # 매수 조건
            {"id": "rsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 600, "y": 200}},
            {"id": "macd", "type": "ConditionNode", "category": "condition", "plugin": "MACD", "fields": {"fast_period": 12, "slow_period": 26, "signal_period": 9, "signal_type": "bullish_cross"}, "position": {"x": 600, "y": 350}},
            {"id": "buyLogic", "type": "LogicNode", "category": "condition", "operator": "and", "position": {"x": 800, "y": 275}},
            # 매도 조건
            {"id": "profitTake", "type": "ConditionNode", "category": "condition", "plugin": "ProfitTarget", "fields": {"percent": 8}, "position": {"x": 600, "y": 500}},
            {"id": "stopLoss", "type": "ConditionNode", "category": "condition", "plugin": "StopLoss", "fields": {"percent": -4}, "position": {"x": 600, "y": 600}},
            {"id": "sellLogic", "type": "LogicNode", "category": "condition", "operator": "or", "position": {"x": 800, "y": 550}},
            # 백테스트 (통합 노드)
            {"id": "backtest", "type": "BacktestEngineNode", "category": "backtest", "initial_capital": 100000, "commission_rate": 0.001, "slippage": 0.0005, "benchmark": "SPY", "risk_free_rate": 0.02, "position": {"x": 1000, "y": 400}},
            # 성과 조건
            {"id": "performanceCheck", "type": "PerformanceConditionNode", "category": "condition", "conditions": {"pnl_rate": ">0", "max_drawdown": "<0.1", "sharpe_ratio": ">0.5"}, "position": {"x": 1250, "y": 400}},
            # 배포
            {"id": "deploy", "type": "DeployNode", "category": "job", "mode": "paper_trading", "auto_start": True, "position": {"x": 1500, "y": 300}},
            {"id": "deployAlert", "type": "AlertNode", "category": "event", "channel": "slack", "template": "✅ 백테스트 통과!\n수익률: {{pnl_rate}}%\nMDD: {{max_drawdown}}%\n자동 배포 완료", "position": {"x": 1700, "y": 300}},
            {"id": "rejectAlert", "type": "AlertNode", "category": "event", "channel": "slack", "template": "❌ 백테스트 기준 미달\n수익률: {{pnl_rate}}%\nMDD: {{max_drawdown}}%", "position": {"x": 1500, "y": 550}},
            {"id": "display", "type": "DisplayNode", "category": "display", "chart_type": "table", "title": "배포 결과", "position": {"x": 1900, "y": 400}},
        ],
        "edges": [
            {"from": "start", "to": "watchlist"},
            {"from": "watchlist", "to": "historicalData"},
            {"from": "historicalData", "to": "rsi"},
            {"from": "historicalData", "to": "macd"},
            {"from": "rsi", "to": "buyLogic"},
            {"from": "macd", "to": "buyLogic"},
            {"from": "historicalData", "to": "profitTake"},
            {"from": "historicalData", "to": "stopLoss"},
            {"from": "profitTake", "to": "sellLogic"},
            {"from": "stopLoss", "to": "sellLogic"},
            {"from": "buyLogic", "to": "backtest"},
            {"from": "historicalData", "to": "backtest"},
            {"from": "backtest", "to": "performanceCheck"},
            {"from": "performanceCheck", "to": "deploy"},
            {"from": "deploy", "to": "deployAlert"},
            {"from": "performanceCheck", "to": "rejectAlert"},
            {"from": "deploy", "to": "display"},
        ],
    }
