"""
예제 30: 주간 백테스트 → 성과 불량 시 Job 일시정지

매주 일요일에 자동으로 백테스트를 실행하고,
성과가 기준 미달이면 실행 중인 Job을 일시정지합니다.
(사용자가 확인 후 재개하도록)

ScheduleNode → BacktestExecutorNode → PerformanceConditionNode → JobControlNode 플로우

계획서의 scheduled_backtest_job_control.py 구현
"""

SCHEDULED_BACKTEST_JOB_CONTROL = {
    "id": "30-scheduled-backtest-job-control",
    "version": "1.0.0",
    "name": "주간 백테스트 기반 Job 자동 제어",
    "description": "매주 백테스트 후 성과 불량 시 Job 일시정지",
    "tags": ["backtest", "job_control", "scheduled", "risk_management"],
    "inputs": {
        "credential_id": {
            "type": "credential",
            "required": True,
            "description": "증권사 인증정보",
        },
        "target_job_id": {
            "type": "string",
            "required": True,
            "description": "모니터링 대상 Job ID",
        },
        "symbols": {
            "type": "symbol_list",
            "default": ["AAPL", "TSLA", "NVDA"],
            "description": "백테스트 대상 종목",
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

        # === TRIGGER ===
        {
            "id": "weeklySchedule",
            "type": "ScheduleNode",
            "category": "trigger",
            # 매주 일요일 오전 6시 (장 시작 전)
            "cron": "0 0 6 * * 0",
            "timezone": "America/New_York",
            "position": {"x": 200, "y": 300},
        },

        # === SYMBOL ===
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": "{{ input.symbols }}",
            "position": {"x": 400, "y": 200},
        },

        # === DATA ===
        {
            "id": "historicalData",
            "type": "HistoricalDataNode",
            "category": "data",
            # 최근 4주 데이터로 롤링 백테스트
            "start_date": "dynamic:weeks_ago(4)",
            "end_date": "dynamic:yesterday()",
            "interval": "1d",
            "position": {"x": 400, "y": 400},
        },

        # === CONDITION (전략 로직 - target_job과 동일해야 함) ===
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
            "position": {"x": 600, "y": 300},
        },
        {
            "id": "profitTake",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "ProfitTarget",
            "fields": {"percent": 5},
            "position": {"x": 600, "y": 450},
        },
        {
            "id": "stopLoss",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "StopLoss",
            "fields": {"percent": -3},
            "position": {"x": 600, "y": 550},
        },
        {
            "id": "sellLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "or",
            "position": {"x": 800, "y": 500},
        },

        # === BACKTEST ===
        {
            "id": "backtestExecutor",
            "type": "BacktestExecutorNode",
            "category": "backtest",
            "initial_capital": 100000,
            "commission_rate": 0.001,
            "slippage": 0.0005,
            "position": {"x": 900, "y": 350},
        },
        {
            "id": "backtestResult",
            "type": "BacktestResultNode",
            "category": "backtest",
            "benchmark": "SPY",
            "risk_free_rate": 0.02,
            "position": {"x": 1100, "y": 350},
        },

        # === PERFORMANCE CHECK ===
        {
            "id": "performanceCheck",
            "type": "PerformanceConditionNode",
            "category": "condition",
            # 주간 백테스트 기준 (더 엄격한 기준)
            "conditions": {
                "pnl_rate": ">-5",          # 손실 5% 이내
                "max_drawdown": "<0.15",    # MDD 15% 미만
                "sharpe_ratio": ">-0.5",    # 샤프비율 -0.5 이상
            },
            "position": {"x": 1300, "y": 350},
        },

        # === JOB CONTROL ===
        # 성과 양호: 아무것도 안 함
        {
            "id": "performanceOkAlert",
            "type": "AlertNode",
            "category": "event",
            "channel": "slack",
            "template": "✅ 주간 백테스트 통과\n기간: {period}\n수익률: {pnl_rate}%\nMDD: {max_drawdown}%",
            "position": {"x": 1500, "y": 200},
        },
        # 성과 불량: Job 일시정지
        {
            "id": "pauseJob",
            "type": "JobControlNode",
            "category": "job",
            "action": "pause",
            "target_job_id": "{{ input.target_job_id }}",
            "require_confirmation": False,  # 자동으로 일시정지 (확인 불필요)
            "position": {"x": 1500, "y": 400},
        },
        {
            "id": "pauseAlert",
            "type": "AlertNode",
            "category": "event",
            "channel": "slack",
            "template": "⚠️ 주간 백테스트 기준 미달로 Job 일시정지\nJob ID: {job_id}\n수익률: {pnl_rate}%\nMDD: {max_drawdown}%\n재개하려면 resume_job 호출 필요",
            "position": {"x": 1700, "y": 400},
        },

        # === DISPLAY ===
        {
            "id": "weeklyReport",
            "type": "DisplayNode",
            "category": "display",
            "chart_type": "table",
            "title": "주간 백테스트 리포트",
            "position": {"x": 1500, "y": 600},
        },
    ],
    "edges": [
        # Start → Schedule
        {"from": "start.start", "to": "weeklySchedule"},

        # Schedule → Data & Symbols
        {"from": "weeklySchedule.trigger", "to": "watchlist"},
        {"from": "weeklySchedule.trigger", "to": "historicalData"},
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

        # BacktestResult → PerformanceCheck
        {"from": "backtestResult.summary", "to": "performanceCheck.backtest_result"},

        # PerformanceCheck 결과에 따른 분기
        # passed=True → 성과 양호 알림
        {"from": "performanceCheck.passed", "to": "performanceOkAlert.event"},
        # passed=False → Job 일시정지
        {"from": "performanceCheck.failed", "to": "pauseJob.trigger"},

        # PauseJob → Alert
        {"from": "pauseJob.result", "to": "pauseAlert.event"},

        # Results → Display
        {"from": "backtestResult.summary", "to": "weeklyReport.data"},
        {"from": "performanceCheck.metrics", "to": "weeklyReport.data"},
    ],
}


# JobControlNode 응답 예시
JOB_CONTROL_RESPONSE_EXAMPLES = {
    "pause_success": {
        "result": {
            "action": "pause",
            "target_job_id": "job-live-2026-001",
            "success": True,
            "previous_status": "running",
            "current_status": "paused",
            "timestamp": "2026-01-05T06:00:00Z",
            "state_snapshot_id": "snapshot-2026-001",
            "message": "Job 일시정지 완료. resume_job으로 재개 가능.",
        },
    },
    "resume_success": {
        "result": {
            "action": "resume",
            "target_job_id": "job-live-2026-001",
            "success": True,
            "previous_status": "paused",
            "current_status": "running",
            "timestamp": "2026-01-05T10:30:00Z",
            "restored_from_snapshot": "snapshot-2026-001",
            "message": "Job 재개 완료. 이전 상태에서 계속 실행.",
        },
    },
}


# 실제 운영 시나리오 예시
OPERATION_SCENARIO = """
=== 주간 백테스트 기반 리스크 관리 시나리오 ===

1. 평일 (월~금):
   - Job (job-live-2026-001) 정상 실행
   - RSI 전략으로 자동 매매

2. 일요일 오전 6시:
   - 이 Definition이 스케줄에 따라 실행
   - 최근 4주 데이터로 동일 전략 백테스트

3-A. 성과 양호 (기준 충족):
   - Slack 알림: "✅ 주간 백테스트 통과"
   - Job 계속 실행

3-B. 성과 불량 (기준 미달):
   - Job 자동 일시정지
   - Slack 알림: "⚠️ Job 일시정지됨. 확인 필요"

4. 사용자 확인 후:
   - 시장 상황 분석
   - 전략 조정 또는 그대로 재개 결정
   - AI 챗봇: "job-live-2026-001 재개해줘"
   - resume_job() 호출

=== 자동화 레벨 조절 ===

require_confirmation: false (현재)
  → 자동으로 일시정지, 재개는 수동

require_confirmation: true로 변경 시
  → 일시정지 전에 사용자 확인 요청
  → "⚠️ 성과 불량. Job을 일시정지할까요?"
  → 사용자가 승인해야 실제 일시정지
"""


if __name__ == "__main__":
    import json
    print("=== 예제 30: 주간 백테스트 → 성과 불량 시 Job 일시정지 ===")
    print(json.dumps(SCHEDULED_BACKTEST_JOB_CONTROL, indent=2, ensure_ascii=False))
    print("\n=== Job 일시정지 응답 예시 ===")
    print(json.dumps(JOB_CONTROL_RESPONSE_EXAMPLES["pause_success"], indent=2, ensure_ascii=False))
    print("\n=== Job 재개 응답 예시 ===")
    print(json.dumps(JOB_CONTROL_RESPONSE_EXAMPLES["resume_success"], indent=2, ensure_ascii=False))
    print(OPERATION_SCENARIO)
