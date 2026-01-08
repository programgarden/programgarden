"""06_backtest/w01_backtest_simple - 단순 백테스트"""


def get_workflow():
    return {
        "id": "backtest-01-simple",
        "version": "1.0.0",
        "name": "단순 RSI 백테스트",
        "description": "과거 1년 데이터로 RSI 전략 성과 검증",
        "tags": ["backtest", "rsi", "historical"],
        "inputs": {
            "symbols": {"type": "symbol_list", "default": ["AAPL", "TSLA", "NVDA"], "description": "백테스트 대상 종목"},
            "start_date": {"type": "date", "default": "2025-01-01", "description": "백테스트 시작일"},
            "end_date": {"type": "date", "default": "2025-12-31", "description": "백테스트 종료일"},
        },
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 50, "y": 300}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": "{{ input.symbols }}", "position": {"x": 200, "y": 300}},
            {"id": "historicalData", "type": "HistoricalDataNode", "category": "data", "start_date": "{{ input.start_date }}", "end_date": "{{ input.end_date }}", "interval": "1d", "position": {"x": 400, "y": 300}},
            {"id": "rsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 600, "y": 200}},
            {"id": "profitTake", "type": "ConditionNode", "category": "condition", "plugin": "ProfitTarget", "fields": {"percent": 5}, "position": {"x": 600, "y": 400}},
            {"id": "stopLoss", "type": "ConditionNode", "category": "condition", "plugin": "StopLoss", "fields": {"percent": -3}, "position": {"x": 600, "y": 500}},
            {"id": "sellLogic", "type": "LogicNode", "category": "condition", "operator": "or", "position": {"x": 800, "y": 450}},
            # BacktestEngineNode: 실행 + 결과 분석 통합
            {"id": "backtest", "type": "BacktestEngineNode", "category": "backtest", "initial_capital": 100000, "commission_rate": 0.001, "slippage": 0.0005, "benchmark": "SPY", "risk_free_rate": 0.02, "position": {"x": 1000, "y": 300}},
            {"id": "display", "type": "DisplayNode", "category": "display", "chart_type": "equity_curve", "title": "백테스트 결과", "position": {"x": 1250, "y": 300}},
        ],
        "edges": [
            {"from": "start.start", "to": "watchlist"},
            {"from": "watchlist.symbols", "to": "historicalData.symbols"},
            {"from": "historicalData.ohlcv_data", "to": "rsi.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "profitTake.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "stopLoss.price_data"},
            {"from": "profitTake.result", "to": "sellLogic.input1"},
            {"from": "stopLoss.result", "to": "sellLogic.input2"},
            {"from": "rsi.passed_symbols", "to": "backtest.signals"},
            {"from": "historicalData.ohlcv_data", "to": "backtest.ohlcv_data"},
            {"from": "backtest.metrics", "to": "display.data"},
        ],
    }
