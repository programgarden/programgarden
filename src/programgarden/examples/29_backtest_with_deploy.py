"""
예제 29: 백테스트 → 성과 조건 → 자동 배포

백테스트 결과가 일정 기준(수익률>0, MDD<10%)을 충족하면
자동으로 paper_trading 모드로 배포합니다.

BacktestResultNode → PerformanceConditionNode → DeployNode 플로우

계획서의 backtest_with_deploy.py 구현
"""

BACKTEST_WITH_DEPLOY = {
    "id": "29-backtest-with-deploy",
    "version": "1.0.0",
    "name": "백테스트 성과 기반 자동 배포",
    "description": "백테스트 결과가 기준 충족 시 paper_trading 자동 배포",
    "tags": ["backtest", "deploy", "paper_trading", "automation"],
    "inputs": {
        "credential_id": {
            "type": "credential",
            "required": True,
            "description": "증권사 인증정보 (배포 시 사용)",
        },
        "symbols": {
            "type": "symbol_list",
            "default": ["AAPL", "MSFT", "GOOGL"],
            "description": "백테스트 및 배포 대상 종목",
        },
        "backtest_months": {
            "type": "integer",
            "default": 6,
            "description": "백테스트 기간 (개월)",
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
            "symbols": "$input.symbols",
            "position": {"x": 200, "y": 300},
        },

        # === DATA ===
        {
            "id": "historicalData",
            "type": "HistoricalDataNode",
            "category": "data",
            "start_date": "dynamic:months_ago($input.backtest_months)",
            "end_date": "dynamic:today()",
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
            "id": "macd",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "MACD",
            "fields": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "signal_type": "bullish_cross",
            },
            "position": {"x": 600, "y": 350},
        },
        {
            "id": "buyLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "and",
            "position": {"x": 800, "y": 275},
        },
        {
            "id": "profitTake",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "ProfitTarget",
            "fields": {"percent": 8},
            "position": {"x": 600, "y": 500},
        },
        {
            "id": "stopLoss",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "StopLoss",
            "fields": {"percent": -4},
            "position": {"x": 600, "y": 600},
        },
        {
            "id": "sellLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "or",
            "position": {"x": 800, "y": 550},
        },

        # === BACKTEST ===
        {
            "id": "backtestExecutor",
            "type": "BacktestExecutorNode",
            "category": "backtest",
            "initial_capital": 100000,
            "commission_rate": 0.001,
            "slippage": 0.0005,
            "position": {"x": 1000, "y": 400},
        },
        {
            "id": "backtestResult",
            "type": "BacktestResultNode",
            "category": "backtest",
            "benchmark": "SPY",
            "risk_free_rate": 0.02,
            "position": {"x": 1200, "y": 400},
        },

        # === PERFORMANCE CHECK ===
        {
            "id": "performanceCheck",
            "type": "PerformanceConditionNode",
            "category": "condition",
            "conditions": {
                "pnl_rate": ">0",           # 수익률 양수
                "max_drawdown": "<0.1",     # MDD 10% 미만
                "win_rate": ">0.4",         # 승률 40% 이상
                "sharpe_ratio": ">0.5",     # 샤프비율 0.5 이상
            },
            "position": {"x": 1400, "y": 400},
        },

        # === DEPLOY ===
        {
            "id": "deploy",
            "type": "DeployNode",
            "category": "job",
            "target_mode": "paper_trading",
            "auto_deploy": True,  # 조건 충족 시 자동 배포
            "auto_promote": {
                "enabled": True,            # paper_trading → live 자동 승격 활성화
                "after_days": 14,           # 14일 후
                "min_trades": 20,           # 최소 20회 거래
                "conditions": {
                    "pnl_rate": ">0",       # 실제 거래에서도 수익
                    "max_drawdown": "<0.1", # MDD 10% 미만 유지
                },
            },
            "position": {"x": 1600, "y": 400},
        },

        # === EVENT (알림) ===
        {
            "id": "deployAlert",
            "type": "AlertNode",
            "category": "event",
            "channel": "slack",
            "template": "🚀 전략 '{strategy_name}' 배포 완료\n모드: {mode}\nJob ID: {job_id}",
            "position": {"x": 1800, "y": 300},
        },
        {
            "id": "rejectAlert",
            "type": "AlertNode",
            "category": "event",
            "channel": "slack",
            "template": "⚠️ 전략 '{strategy_name}' 배포 거부\n사유: {reject_reason}",
            "position": {"x": 1800, "y": 500},
        },

        # === DISPLAY ===
        {
            "id": "resultDisplay",
            "type": "DisplayNode",
            "category": "display",
            "chart_type": "table",
            "title": "백테스트 결과 및 배포 상태",
            "position": {"x": 1600, "y": 600},
        },
    ],
    "edges": [
        # Start → Watchlist
        {"from": "start.trigger", "to": "watchlist"},

        # Watchlist → HistoricalData
        {"from": "watchlist.symbols", "to": "historicalData.symbols"},

        # HistoricalData → Conditions
        {"from": "historicalData.ohlcv_data", "to": "rsi.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "macd.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "profitTake.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "stopLoss.price_data"},

        # Buy Logic (AND)
        {"from": "rsi.result", "to": "buyLogic.input"},
        {"from": "macd.result", "to": "buyLogic.input"},

        # Sell Logic (OR)
        {"from": "profitTake.result", "to": "sellLogic.input"},
        {"from": "stopLoss.result", "to": "sellLogic.input"},

        # Conditions → BacktestExecutor
        {"from": "buyLogic.result", "to": "backtestExecutor.buy_signal"},
        {"from": "sellLogic.result", "to": "backtestExecutor.sell_signal"},
        {"from": "historicalData.ohlcv_data", "to": "backtestExecutor.historical_data"},

        # BacktestExecutor → BacktestResult
        {"from": "backtestExecutor.result", "to": "backtestResult.backtest_result"},

        # BacktestResult → PerformanceCheck
        {"from": "backtestResult.summary", "to": "performanceCheck.backtest_result"},

        # PerformanceCheck → Deploy
        {"from": "performanceCheck.passed", "to": "deploy.performance_check"},
        {"from": "backtestResult.summary", "to": "deploy.backtest_result"},

        # Deploy → Alerts
        {"from": "deploy.deployed_job_id", "to": "deployAlert.event"},
        {"from": "deploy.deploy_status.rejected", "to": "rejectAlert.event"},

        # Results → Display
        {"from": "backtestResult.summary", "to": "resultDisplay.data"},
        {"from": "deploy.deploy_status", "to": "resultDisplay.data"},
    ],
}


# DeployNode 응답 예시
DEPLOY_RESPONSE_EXAMPLES = {
    "success": {
        "deployed_job_id": "job-paper-2026-001",
        "deploy_status": {
            "status": "deployed",
            "mode": "paper_trading",
            "strategy_name": "29-backtest-with-deploy",
            "deployed_at": "2026-01-06T09:00:00Z",
            "auto_promote": {
                "enabled": True,
                "scheduled_date": "2026-01-20T09:00:00Z",
                "conditions_to_meet": ["pnl_rate>0", "max_drawdown<0.1", "min_trades>=20"],
            },
        },
    },
    "rejected": {
        "deployed_job_id": None,
        "deploy_status": {
            "status": "rejected",
            "reject_reason": "성과 조건 미충족: max_drawdown=12.5% (기준: <10%)",
            "backtest_summary": {
                "pnl_rate": 8.5,
                "max_drawdown": 0.125,
                "win_rate": 0.52,
                "sharpe_ratio": 0.8,
            },
        },
    },
}


if __name__ == "__main__":
    import json
    print("=== 예제 29: 백테스트 → 성과 조건 → 자동 배포 ===")
    print(json.dumps(BACKTEST_WITH_DEPLOY, indent=2, ensure_ascii=False))
    print("\n=== 배포 성공 예시 ===")
    print(json.dumps(DEPLOY_RESPONSE_EXAMPLES["success"], indent=2, ensure_ascii=False))
    print("\n=== 배포 거부 예시 ===")
    print(json.dumps(DEPLOY_RESPONSE_EXAMPLES["rejected"], indent=2, ensure_ascii=False))
