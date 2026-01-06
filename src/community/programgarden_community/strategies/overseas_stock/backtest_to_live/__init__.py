"""
백테스트 → 성과 검증 → 실전 배포 전략
======================================

전략 ID: backtest_to_live
버전: 1.0.0

설명
----
6개월 백테스트를 실행하고, 성과가 기준을 충족하면
자동으로 실계좌에 배포하는 전략입니다.

성과 기준
---------
- 총 수익률 > 0%
- 최대 낙폭(MDD) < 10%
- 승률 > 40%
- 샤프비율 > 0.3

배포 조건
---------
모든 성과 기준 충족 시 paper_trading=False로 배포

사용법
------
    from programgarden_community.strategies import get_strategy
    strategy = get_strategy("overseas_stock", "backtest_to_live")
"""

BACKTEST_TO_LIVE = {
    "id": "backtest-to-live-strategy",
    "version": "1.0.0",
    "name": "백테스트 검증 후 실전 배포",
    "description": "6개월 백테스트 → 성과 기준 충족 → 실계좌 자동 배포",
    "tags": ["backtest", "deploy", "automation", "validation"],
    "author": "ProgramGarden Team",
    "inputs": {
        "symbols": {
            "type": "symbol_list",
            "default": ["SOXS", "SQQQ", "FAZ"],
            "description": "백테스트 및 배포 대상 종목",
        },
        "backtest_months": {
            "type": "int",
            "default": 6,
            "description": "백테스트 기간 (개월)",
        },
        "min_return": {
            "type": "float",
            "default": 0,
            "description": "최소 수익률 (%)",
        },
        "max_mdd": {
            "type": "float",
            "default": 10,
            "description": "최대 MDD (%)",
        },
        "min_win_rate": {
            "type": "float",
            "default": 40,
            "description": "최소 승률 (%)",
        },
        "min_sharpe": {
            "type": "float",
            "default": 0.3,
            "description": "최소 샤프비율",
        },
    },
    "nodes": [
        # === PHASE A: 백테스트 ===
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 0, "y": 300},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": "$input.symbols",
            "position": {"x": 150, "y": 300},
        },
        {
            "id": "historicalData",
            "type": "HistoricalDataNode",
            "category": "data",
            "start_date": "dynamic:months_ago($input.backtest_months)",
            "end_date": "dynamic:today()",
            "interval": "1d",
            "position": {"x": 300, "y": 300},
        },
        
        # === 전략 조건 ===
        {
            "id": "rsiBuy",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {
                "period": 14,
                "threshold": 30,
                "direction": "below",
            },
            "position": {"x": 450, "y": 200},
        },
        {
            "id": "profitTarget",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "ProfitTarget",
            "fields": {"percent": 5},
            "position": {"x": 450, "y": 350},
        },
        {
            "id": "stopLoss",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "StopLoss",
            "fields": {"percent": -3},
            "position": {"x": 450, "y": 450},
        },
        {
            "id": "sellLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "or",
            "position": {"x": 600, "y": 400},
        },
        
        # === 백테스트 실행 ===
        {
            "id": "backtestExecutor",
            "type": "BacktestExecutorNode",
            "category": "backtest",
            "initial_capital": 200,  # $200 (약 28만원)
            "commission_rate": 0.001,
            "slippage": 0.001,
            "position": {"x": 750, "y": 300},
        },
        {
            "id": "backtestResult",
            "type": "BacktestResultNode",
            "category": "backtest",
            "benchmark": "SPY",
            "risk_free_rate": 0.02,
            "position": {"x": 900, "y": 300},
        },
        
        # === PHASE B: 성과 검증 ===
        {
            "id": "performanceCheck",
            "type": "PerformanceConditionNode",
            "category": "condition",
            "conditions": {
                "total_return": ">$input.min_return",
                "max_drawdown": "<$input.max_mdd",
                "win_rate": ">$input.min_win_rate",
                "sharpe_ratio": ">$input.min_sharpe",
            },
            "position": {"x": 1050, "y": 300},
        },
        
        # === PHASE C: 배포 결정 ===
        {
            "id": "deployLive",
            "type": "DeployNode",
            "category": "job",
            "mode": "live",
            "paper_trading": False,
            "position": {"x": 1200, "y": 200},
        },
        {
            "id": "deployPaper",
            "type": "DeployNode",
            "category": "job",
            "mode": "paper",
            "paper_trading": True,
            "position": {"x": 1200, "y": 400},
        },
        
        # === 알림 ===
        {
            "id": "successAlert",
            "type": "AlertNode",
            "category": "event",
            "channel": "slack",
            "template": "✅ 백테스트 통과! 실계좌 배포 완료\n수익률: {{total_return}}%\nMDD: {{max_drawdown}}%",
            "position": {"x": 1350, "y": 200},
        },
        {
            "id": "failAlert",
            "type": "AlertNode",
            "category": "event",
            "channel": "slack",
            "template": "⚠️ 백테스트 기준 미달\n수익률: {{total_return}}%\nMDD: {{max_drawdown}}%\n→ Paper Trading 유지",
            "position": {"x": 1350, "y": 400},
        },
        
        # === 결과 표시 ===
        {
            "id": "resultDisplay",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["total_return", "max_drawdown", "win_rate", "sharpe_ratio", "deploy_status"],
            "position": {"x": 1500, "y": 300},
        },
    ],
    "edges": [
        # Phase A: 백테스트
        {"from": "start.trigger", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "historicalData.symbols"},
        {"from": "historicalData.ohlcv_data", "to": "rsiBuy.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "profitTarget.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "stopLoss.price_data"},
        {"from": "profitTarget.result", "to": "sellLogic.input"},
        {"from": "stopLoss.result", "to": "sellLogic.input"},
        {"from": "rsiBuy.result", "to": "backtestExecutor.buy_signal"},
        {"from": "sellLogic.result", "to": "backtestExecutor.sell_signal"},
        {"from": "historicalData.ohlcv_data", "to": "backtestExecutor.historical_data"},
        {"from": "backtestExecutor.result", "to": "backtestResult.backtest_result"},
        
        # Phase B: 성과 검증
        {"from": "backtestResult.summary", "to": "performanceCheck.performance_data"},
        
        # Phase C: 배포 결정
        {"from": "performanceCheck.passed", "to": "deployLive.trigger"},
        {"from": "performanceCheck.failed", "to": "deployPaper.trigger"},
        
        # 알림
        {"from": "deployLive.result", "to": "successAlert.data"},
        {"from": "deployPaper.result", "to": "failAlert.data"},
        
        # 결과 표시
        {"from": "backtestResult.summary", "to": "resultDisplay.data"},
    ],
}


__all__ = ["BACKTEST_TO_LIVE"]
