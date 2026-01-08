"""
예제 28: 단순 백테스트 실행

과거 데이터를 사용하여 RSI 전략을 백테스트합니다.
HistoricalDataNode → BacktestExecutorNode → BacktestResultNode 플로우

계획서의 backtest_simple.py 구현
"""

BACKTEST_SIMPLE = {
    "id": "28-backtest-simple",
    "version": "1.0.0",
    "name": "단순 RSI 백테스트",
    "description": "과거 1년 데이터로 RSI 전략 성과 검증",
    "tags": ["backtest", "rsi", "historical"],
    "inputs": {
        "symbols": {
            "type": "symbol_list",
            "default": ["AAPL", "TSLA", "NVDA"],
            "description": "백테스트 대상 종목",
        },
        "start_date": {
            "type": "date",
            "default": "2025-01-01",
            "description": "백테스트 시작일",
        },
        "end_date": {
            "type": "date",
            "default": "2025-12-31",
            "description": "백테스트 종료일",
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

        # === SYMBOL ===
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": "{{ input.symbols }}",
            "position": {"x": 200, "y": 300},
        },

        # === DATA ===
        {
            "id": "historicalData",
            "type": "HistoricalDataNode",
            "category": "data",
            "start_date": "{{ input.start_date }}",
            "end_date": "{{ input.end_date }}",
            "interval": "1d",
            "position": {"x": 400, "y": 300},
        },

        # === CONDITION (전략 로직) ===
        {
            "id": "rsi",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {
                "period": 14,
                "threshold": 30,
                "direction": "below",
            },
            "position": {"x": 600, "y": 200},
        },
        {
            "id": "profitTake",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "ProfitTarget",
            "fields": {"percent": 5},
            "position": {"x": 600, "y": 400},
        },
        {
            "id": "stopLoss",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "StopLoss",
            "fields": {"percent": -3},
            "position": {"x": 600, "y": 500},
        },
        {
            "id": "sellLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "or",
            "position": {"x": 800, "y": 450},
        },

        # === BACKTEST ===
        {
            "id": "backtestExecutor",
            "type": "BacktestExecutorNode",
            "category": "backtest",
            "initial_capital": 100000,
            "commission_rate": 0.001,
            "slippage": 0.0005,
            "position": {"x": 1000, "y": 300},
        },
        {
            "id": "backtestResult",
            "type": "BacktestResultNode",
            "category": "backtest",
            "benchmark": "SPY",
            "risk_free_rate": 0.02,
            "position": {"x": 1200, "y": 300},
        },

        # === DISPLAY ===
        {
            "id": "equityCurveChart",
            "type": "DisplayNode",
            "category": "display",
            "chart_type": "line",
            "title": "Equity Curve",
            "position": {"x": 1400, "y": 200},
        },
        {
            "id": "performanceTable",
            "type": "DisplayNode",
            "category": "display",
            "chart_type": "table",
            "title": "Performance Summary",
            "position": {"x": 1400, "y": 400},
        },
    ],
    "edges": [
        # Start → Watchlist
        {"from": "start.start", "to": "watchlist"},

        # Watchlist → HistoricalData
        {"from": "watchlist.symbols", "to": "historicalData.symbols"},

        # HistoricalData → Conditions
        {"from": "historicalData.ohlcv_data", "to": "rsi.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "profitTake.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "stopLoss.price_data"},

        # Sell Logic (OR)
        {"from": "profitTake.result", "to": "sellLogic.input"},
        {"from": "stopLoss.result", "to": "sellLogic.input"},

        # Conditions → BacktestExecutor
        {"from": "rsi.result", "to": "backtestExecutor.buy_signal"},
        {"from": "sellLogic.result", "to": "backtestExecutor.sell_signal"},
        {"from": "historicalData.ohlcv_data", "to": "backtestExecutor.historical_data"},

        # BacktestExecutor → BacktestResult
        {"from": "backtestExecutor.result", "to": "backtestResult.backtest_result"},

        # BacktestResult → Display
        {"from": "backtestResult.equity_curve", "to": "equityCurveChart.data"},
        {"from": "backtestResult.summary", "to": "performanceTable.data"},
    ],
}


# 예상 결과 예시
EXPECTED_OUTPUT = {
    "backtest_summary": {
        "total_return_percent": 15.3,
        "annualized_return": 12.8,
        "max_drawdown_percent": -8.5,
        "sharpe_ratio": 1.42,
        "win_rate": 0.58,
        "total_trades": 47,
        "avg_trade_duration_days": 5.2,
        "profit_factor": 1.85,
    },
    "equity_curve": [
        {"date": "2025-01-01", "equity": 100000},
        {"date": "2025-03-15", "equity": 108500},
        {"date": "2025-06-01", "equity": 105200},
        {"date": "2025-09-15", "equity": 112800},
        {"date": "2025-12-31", "equity": 115300},
    ],
    "trade_analysis": {
        "best_trade": {"symbol": "NVDA", "return_percent": 12.5},
        "worst_trade": {"symbol": "TSLA", "return_percent": -5.2},
        "avg_win_percent": 4.2,
        "avg_loss_percent": -2.8,
    },
}


if __name__ == "__main__":
    import json
    print("=== 예제 28: 단순 백테스트 실행 ===")
    print(json.dumps(BACKTEST_SIMPLE, indent=2, ensure_ascii=False))
    print("\n=== 예상 결과 ===")
    print(json.dumps(EXPECTED_OUTPUT, indent=2, ensure_ascii=False))
