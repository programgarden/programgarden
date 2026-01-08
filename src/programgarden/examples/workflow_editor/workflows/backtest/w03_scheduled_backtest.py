"""06_backtest/w03_scheduled_backtest - 주간 백테스트 기반 Job 제어"""


def get_workflow():
    return {
        "id": "backtest-03-scheduled",
        "version": "1.0.0",
        "name": "주간 백테스트 기반 Job 자동 제어",
        "description": "매주 백테스트 후 성과 불량 시 Job 일시정지",
        "tags": ["backtest", "job_control", "scheduled", "risk_management"],
        "inputs": {
            "target_job_id": {"type": "string", "required": True, "description": "모니터링 대상 Job ID"},
            "symbols": {"type": "symbol_list", "default": ["AAPL", "TSLA", "NVDA"], "description": "백테스트 대상 종목"},
        },
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra", "position": {"x": 50, "y": 300}},
            # 매주 일요일 오전 6시
            {"id": "weeklySchedule", "type": "ScheduleNode", "category": "trigger", "cron": "0 0 6 * * 0", "timezone": "America/New_York", "position": {"x": 200, "y": 300}},
            {"id": "watchlist", "type": "WatchlistNode", "category": "symbol", "symbols": "{{ input.symbols }}", "position": {"x": 400, "y": 200}},
            # 최근 4주 데이터
            {"id": "historicalData", "type": "HistoricalDataNode", "category": "data", "start_date": "dynamic:weeks_ago(4)", "end_date": "dynamic:yesterday()", "interval": "1d", "position": {"x": 400, "y": 400}},
            # 전략 로직
            {"id": "rsi", "type": "ConditionNode", "category": "condition", "plugin": "RSI", "fields": {"period": 14, "threshold": 30, "direction": "below"}, "position": {"x": 600, "y": 300}},
            {"id": "profitTake", "type": "ConditionNode", "category": "condition", "plugin": "ProfitTarget", "fields": {"percent": 5}, "position": {"x": 600, "y": 450}},
            {"id": "stopLoss", "type": "ConditionNode", "category": "condition", "plugin": "StopLoss", "fields": {"percent": -3}, "position": {"x": 600, "y": 550}},
            {"id": "sellLogic", "type": "LogicNode", "category": "condition", "operator": "or", "position": {"x": 800, "y": 500}},
            # 백테스트 (통합 노드)
            {"id": "backtest", "type": "BacktestEngineNode", "category": "backtest", "initial_capital": 100000, "commission_rate": 0.001, "slippage": 0.0005, "benchmark": "SPY", "risk_free_rate": 0.02, "position": {"x": 1000, "y": 350}},
            # 성과 체크
            {"id": "performanceCheck", "type": "PerformanceConditionNode", "category": "condition", "conditions": {"pnl_rate": ">-5", "max_drawdown": "<0.15", "sharpe_ratio": ">-0.5"}, "position": {"x": 1250, "y": 350}},
            # 성과 양호: 알림만
            {"id": "performanceOkAlert", "type": "AlertNode", "category": "event", "channel": "slack", "template": "✅ 주간 백테스트 통과\n기간: {{period}}\n수익률: {{pnl_rate}}%\nMDD: {{max_drawdown}}%", "position": {"x": 1500, "y": 200}},
            # 성과 불량: Job 일시정지
            {"id": "pauseJob", "type": "JobControlNode", "category": "job", "action": "pause", "target_job_id": "{{ input.target_job_id }}", "require_confirmation": False, "position": {"x": 1500, "y": 400}},
            {"id": "pauseAlert", "type": "AlertNode", "category": "event", "channel": "slack", "template": "⚠️ 주간 백테스트 기준 미달로 Job 일시정지\nJob ID: {{job_id}}\n수익률: {{pnl_rate}}%\nMDD: {{max_drawdown}}%\n재개하려면 resume_job 호출 필요", "position": {"x": 1700, "y": 400}},
            {"id": "weeklyReport", "type": "DisplayNode", "category": "display", "chart_type": "table", "title": "주간 백테스트 리포트", "position": {"x": 1500, "y": 600}},
        ],
        "edges": [
            {"from": "start.start", "to": "weeklySchedule"},
            {"from": "weeklySchedule.trigger", "to": "watchlist"},
            {"from": "weeklySchedule.trigger", "to": "historicalData"},
            {"from": "watchlist.symbols", "to": "historicalData.symbols"},
            {"from": "historicalData.ohlcv_data", "to": "rsi.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "profitTake.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "stopLoss.price_data"},
            {"from": "profitTake.result", "to": "sellLogic.input1"},
            {"from": "stopLoss.result", "to": "sellLogic.input2"},
            {"from": "rsi.passed_symbols", "to": "backtest.signals"},
            {"from": "historicalData.ohlcv_data", "to": "backtest.ohlcv_data"},
            {"from": "backtest.metrics", "to": "performanceCheck.performance_data"},
            {"from": "performanceCheck.passed", "to": "performanceOkAlert.data"},
            {"from": "performanceCheck.failed", "to": "pauseJob.trigger"},
            {"from": "pauseJob.success", "to": "pauseAlert.data"},
            {"from": "backtest.metrics", "to": "weeklyReport.data"},
        ],
    }
