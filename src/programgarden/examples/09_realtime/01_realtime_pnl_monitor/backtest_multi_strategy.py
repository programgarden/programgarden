"""
예제: 멀티 전략 백테스트 비교

5가지 전략을 백테스트하고 성과를 비교합니다:

개별 전략 (3개):
1. RSI 역추세: RSI < 30 매수, RSI > 70 매도
2. 골든크로스: MA5 > MA20 매수, MA5 < MA20 매도
3. 듀얼모멘텀: 12개월 수익률 > 0 & 벤치마크 대비 상승

전략 조합 (2개):
4. RSI AND 골든크로스: 두 조건 모두 만족 시 매수
5. RSI OR MACD: 둘 중 하나 만족 시 매수

시각화 (Option B - 레벨별 DisplayNode):
- Level 1 (필수): 포트폴리오 레벨
  - equityCurveDisplay: Line Chart (5개 전략 Equity Curve)
  - performanceRadar: Radar Chart (성과 지표 비교)
  - returnDistribution: Bar Chart (수익률 분포 히스토그램)
- Level 2 (선택): 종목 기여도
  - symbolContribution: Bar Chart (Top/Bottom 종목)
  - tradeSummary: Table (거래 통계)

사전 준비:
1. .env 파일에 LS증권 API 키 설정
   APPKEY=your_appkey
   APPSECRET=your_appsecret
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
project_root = Path(__file__).resolve().parents[5]
load_dotenv(project_root / ".env")

# 환경변수에서 API 키 읽기
APPKEY = os.getenv("APPKEY", "")
APPSECRET = os.getenv("APPSECRET", "")


# =============================================================================
# 워크플로우 정의
# =============================================================================

BACKTEST_MULTI_STRATEGY = {
    "id": "backtest-multi-strategy-comparison",
    "version": "1.0.0",
    "name": "멀티 전략 백테스트 비교",
    "description": "5가지 전략(개별3+조합2)의 1년 백테스트 성과 비교",
    "tags": ["backtest", "multi-strategy", "comparison", "visualization"],
    
    "inputs": {
        "symbols": {
            "type": "symbol_list",
            "default": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
            "description": "백테스트 대상 종목 (5개)",
        },
        "start_date": {
            "type": "string",
            "default": "2025-01-01",
            "description": "백테스트 시작일 (YYYY-MM-DD)",
        },
        "end_date": {
            "type": "string",
            "default": "2025-12-31",
            "description": "백테스트 종료일 (YYYY-MM-DD)",
        },
        "initial_capital": {
            "type": "number",
            "default": 100000,
            "description": "초기 자본금 ($)",
        },
    },
    
    "nodes": [
        # =====================================================================
        # INFRA Layer
        # =====================================================================
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 50, "y": 400},
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "provider": "ls-sec.co.kr",
            "product": "overseas_stock",
            "paper_trading": False,
            "position": {"x": 200, "y": 400},
        },
        
        # =====================================================================
        # SYMBOL Layer
        # =====================================================================
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": "{{ input.symbols }}",
            "position": {"x": 400, "y": 400},
        },
        
        # =====================================================================
        # DATA Layer
        # =====================================================================
        {
            "id": "historicalData",
            "type": "HistoricalDataNode",
            "category": "data",
            "start_date": "{{ input.start_date }}",
            "end_date": "{{ input.end_date }}",
            "interval": "1d",
            "position": {"x": 600, "y": 400},
        },
        
        # =====================================================================
        # CONDITION Layer - 개별 전략 (3개)
        # =====================================================================
        
        # 전략 1: RSI 역추세 (매수)
        {
            "id": "rsiBuyCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {
                "period": 14,
                "threshold": 30,
                "direction": "below",  # RSI < 30 → 과매도 → 매수
            },
            "position": {"x": 850, "y": 150},
        },
        # 전략 1: RSI 역추세 (매도)
        {
            "id": "rsiSellCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {
                "period": 14,
                "threshold": 70,
                "direction": "above",  # RSI > 70 → 과매수 → 매도
            },
            "position": {"x": 850, "y": 250},
        },
        
        # 전략 2: 골든크로스 (매수)
        {
            "id": "goldenCrossCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "MovingAverageCross",
            "fields": {
                "short_period": 5,
                "long_period": 20,
                "cross_type": "golden",  # 골든크로스 → 매수
            },
            "position": {"x": 850, "y": 350},
        },
        # 전략 2: 데드크로스 (매도)
        {
            "id": "deadCrossCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "MovingAverageCross",
            "fields": {
                "short_period": 5,
                "long_period": 20,
                "cross_type": "dead",  # 데드크로스 → 매도
            },
            "position": {"x": 850, "y": 450},
        },
        
        # 전략 3: 듀얼모멘텀
        {
            "id": "dualMomentumCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "DualMomentum",
            "fields": {
                "lookback_period": 252,
                "absolute_threshold": 0,
                "use_relative": True,
                "relative_benchmark": "SHY",
            },
            "position": {"x": 850, "y": 550},
        },
        
        # 전략 5용: MACD (조합용)
        {
            "id": "macdCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "MACD",
            "fields": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "signal_type": "bullish_cross",
            },
            "position": {"x": 850, "y": 650},
        },
        
        # =====================================================================
        # CONDITION Layer - 전략 조합 (2개)
        # =====================================================================
        
        # 전략 4: RSI AND 골든크로스
        {
            "id": "rsiAndGoldenLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "all",  # AND: 두 조건 모두 만족
            "position": {"x": 1100, "y": 250},
        },
        
        # 전략 5: RSI OR MACD
        {
            "id": "rsiOrMacdLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "any",  # OR: 둘 중 하나 만족
            "position": {"x": 1100, "y": 600},
        },
        
        # =====================================================================
        # BACKTEST Layer - 전략별 백테스트 실행 (5개)
        # =====================================================================
        
        # 백테스트 1: RSI 역추세
        {
            "id": "rsiBacktest",
            "type": "BacktestEngineNode",
            "category": "backtest",
            "initial_capital": "{{ input.initial_capital }}",
            "commission_rate": 0.001,
            "slippage": 0.0005,
            "strategy_name": "RSI 역추세",
            "position": {"x": 1350, "y": 200},
        },
        
        # 백테스트 2: 골든크로스
        {
            "id": "goldenCrossBacktest",
            "type": "BacktestEngineNode",
            "category": "backtest",
            "initial_capital": "{{ input.initial_capital }}",
            "commission_rate": 0.001,
            "slippage": 0.0005,
            "strategy_name": "골든크로스",
            "position": {"x": 1350, "y": 350},
        },
        
        # 백테스트 3: 듀얼모멘텀
        {
            "id": "dualMomentumBacktest",
            "type": "BacktestEngineNode",
            "category": "backtest",
            "initial_capital": "{{ input.initial_capital }}",
            "commission_rate": 0.001,
            "slippage": 0.0005,
            "strategy_name": "듀얼모멘텀",
            "position": {"x": 1350, "y": 500},
        },
        
        # 백테스트 4: RSI AND 골든크로스
        {
            "id": "combinedAndBacktest",
            "type": "BacktestEngineNode",
            "category": "backtest",
            "initial_capital": "{{ input.initial_capital }}",
            "commission_rate": 0.001,
            "slippage": 0.0005,
            "strategy_name": "RSI+골든(AND)",
            "position": {"x": 1350, "y": 650},
        },
        
        # 백테스트 5: RSI OR MACD
        {
            "id": "combinedOrBacktest",
            "type": "BacktestEngineNode",
            "category": "backtest",
            "initial_capital": "{{ input.initial_capital }}",
            "commission_rate": 0.001,
            "slippage": 0.0005,
            "strategy_name": "RSI|MACD(OR)",
            "position": {"x": 1350, "y": 800},
        },
        
        # =====================================================================
        # DISPLAY Layer - Level 1: 포트폴리오 레벨 (3개)
        # =====================================================================
        
        # 1️⃣ Line Chart: 5개 전략 Equity Curve 비교
        {
            "id": "equityCurveDisplay",
            "type": "DisplayNode",
            "category": "display",
            "chart_type": "line",
            "title": "📈 전략별 Equity Curve 비교",
            "x_label": "날짜",
            "y_label": "포트폴리오 가치 ($)",
            "options": {
                "x_axis": "date",
                "y_axis": "value",
                "multi_series": True,
                "series_names": [
                    "RSI 역추세",
                    "골든크로스",
                    "듀얼모멘텀",
                    "RSI+골든(AND)",
                    "RSI|MACD(OR)",
                ],
                "colors": ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444"],
                "show_legend": True,
            },
            "position": {"x": 1600, "y": 300},
        },
        
        # 2️⃣ Radar Chart: 성과 지표 비교
        {
            "id": "performanceRadar",
            "type": "DisplayNode",
            "category": "display",
            "chart_type": "radar",
            "title": "🕸️ 전략별 성과 지표 비교",
            "options": {
                "metrics": [
                    "total_return",
                    "sharpe_ratio",
                    "max_drawdown",
                    "win_rate",
                    "profit_factor",
                ],
                "labels": ["수익률", "샤프비율", "MDD", "승률", "손익비"],
                "normalize": True,  # 0~1 정규화
                "show_values": True,
            },
            "position": {"x": 1600, "y": 500},
        },
        
        # 3️⃣ Bar Chart: 수익률 분포 (히스토그램)
        {
            "id": "returnDistribution",
            "type": "DisplayNode",
            "category": "display",
            "chart_type": "bar",
            "title": "📊 일별 수익률 분포 (히스토그램)",
            "x_label": "일별 수익률 (%)",
            "y_label": "빈도",
            "options": {
                "histogram": True,
                "bins": 30,
                "show_normal_curve": True,
                "show_statistics": True,  # 평균, 표준편차, 왜도, 첨도
            },
            "position": {"x": 1600, "y": 700},
        },
        
        # =====================================================================
        # DISPLAY Layer - Level 2: 종목 기여도 (2개)
        # =====================================================================
        
        # 4️⃣ Bar Chart: 종목별 기여도 Top/Bottom
        {
            "id": "symbolContribution",
            "type": "DisplayNode",
            "category": "display",
            "chart_type": "bar",
            "title": "📊 종목별 수익 기여도 (Top 10 / Bottom 10)",
            "options": {
                "top_n": 10,
                "bottom_n": 10,
                "metric": "pnl_contribution",  # 수익 기여도
                "colors": {
                    "positive": "#22c55e",
                    "negative": "#ef4444",
                },
                "horizontal": True,
            },
            "position": {"x": 1850, "y": 400},
        },
        
        # 5️⃣ Table: 거래 통계 요약
        {
            "id": "tradeSummary",
            "type": "DisplayNode",
            "category": "display",
            "chart_type": "table",
            "title": "📋 전략별 거래 통계",
            "options": {
                "columns": [
                    "strategy_name",
                    "total_trades",
                    "win_rate",
                    "total_return",
                    "max_drawdown",
                    "sharpe_ratio",
                ],
                "column_labels": [
                    "전략",
                    "총 거래",
                    "승률",
                    "총 수익률",
                    "MDD",
                    "샤프비율",
                ],
                "sort_by": "total_return",
                "sort_order": "desc",
            },
            "position": {"x": 1850, "y": 600},
        },
    ],
    
    "edges": [
        # =====================================================================
        # 기본 연결: Start → Broker → Watchlist → HistoricalData
        # =====================================================================
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "historicalData.symbols"},
        
        # =====================================================================
        # HistoricalData → 모든 Condition 노드
        # =====================================================================
        {"from": "historicalData.ohlcv_data", "to": "rsiBuyCondition.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "rsiSellCondition.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "goldenCrossCondition.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "deadCrossCondition.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "dualMomentumCondition.price_data"},
        {"from": "historicalData.ohlcv_data", "to": "macdCondition.price_data"},
        
        # =====================================================================
        # 전략 조합: LogicNode 입력
        # =====================================================================
        # RSI AND 골든크로스
        {"from": "rsiBuyCondition.result", "to": "rsiAndGoldenLogic.input"},
        {"from": "goldenCrossCondition.result", "to": "rsiAndGoldenLogic.input"},
        
        # RSI OR MACD
        {"from": "rsiBuyCondition.result", "to": "rsiOrMacdLogic.input"},
        {"from": "macdCondition.result", "to": "rsiOrMacdLogic.input"},
        
        # =====================================================================
        # Condition → BacktestEngine (매수/매도 시그널)
        # =====================================================================
        {"from": "rsiBuyCondition.signals", "to": "rsiBacktest.buy_signal"},
        {"from": "rsiSellCondition.signals", "to": "rsiBacktest.sell_signal"},
        {"from": "historicalData.ohlcv_data", "to": "rsiBacktest.ohlcv_data"},
        
        {"from": "goldenCrossCondition.signals", "to": "goldenCrossBacktest.buy_signal"},
        {"from": "deadCrossCondition.signals", "to": "goldenCrossBacktest.sell_signal"},
        {"from": "historicalData.ohlcv_data", "to": "goldenCrossBacktest.ohlcv_data"},
        
        {"from": "dualMomentumCondition.signals", "to": "dualMomentumBacktest.buy_signal"},
        {"from": "historicalData.ohlcv_data", "to": "dualMomentumBacktest.ohlcv_data"},
        
        {"from": "rsiAndGoldenLogic.result", "to": "combinedAndBacktest.buy_signal"},
        {"from": "historicalData.ohlcv_data", "to": "combinedAndBacktest.ohlcv_data"},
        
        {"from": "rsiOrMacdLogic.result", "to": "combinedOrBacktest.buy_signal"},
        {"from": "historicalData.ohlcv_data", "to": "combinedOrBacktest.ohlcv_data"},
        
        # =====================================================================
        # BacktestEngine → Display (Level 1: 포트폴리오)
        # 각 백테스트 결과를 직접 DisplayNode에 연결
        # =====================================================================
        {"from": "rsiBacktest.equity_curve", "to": "equityCurveDisplay.data"},
        {"from": "goldenCrossBacktest.equity_curve", "to": "equityCurveDisplay.data"},
        {"from": "dualMomentumBacktest.equity_curve", "to": "equityCurveDisplay.data"},
        {"from": "combinedAndBacktest.equity_curve", "to": "equityCurveDisplay.data"},
        {"from": "combinedOrBacktest.equity_curve", "to": "equityCurveDisplay.data"},
        
        {"from": "rsiBacktest.metrics", "to": "performanceRadar.data"},
        {"from": "goldenCrossBacktest.metrics", "to": "performanceRadar.data"},
        {"from": "dualMomentumBacktest.metrics", "to": "performanceRadar.data"},
        {"from": "combinedAndBacktest.metrics", "to": "performanceRadar.data"},
        {"from": "combinedOrBacktest.metrics", "to": "performanceRadar.data"},
        
        {"from": "rsiBacktest.summary", "to": "returnDistribution.data"},
        {"from": "goldenCrossBacktest.summary", "to": "returnDistribution.data"},
        {"from": "dualMomentumBacktest.summary", "to": "returnDistribution.data"},
        {"from": "combinedAndBacktest.summary", "to": "returnDistribution.data"},
        {"from": "combinedOrBacktest.summary", "to": "returnDistribution.data"},
        
        # =====================================================================
        # BacktestEngine → Display (Level 2: 종목 기여도)
        # =====================================================================
        {"from": "rsiBacktest.trades", "to": "symbolContribution.data"},
        {"from": "rsiBacktest.summary", "to": "tradeSummary.data"},
        {"from": "goldenCrossBacktest.summary", "to": "tradeSummary.data"},
        {"from": "dualMomentumBacktest.summary", "to": "tradeSummary.data"},
        {"from": "combinedAndBacktest.summary", "to": "tradeSummary.data"},
        {"from": "combinedOrBacktest.summary", "to": "tradeSummary.data"},
    ],
}


# =============================================================================
# 헬퍼 함수
# =============================================================================

def print_workflow_info():
    """워크플로우 정보 출력"""
    print("\n" + "=" * 70)
    print("📊 멀티 전략 백테스트 비교")
    print("=" * 70)
    
    print("\n=== 전략 구성 (5개) ===")
    strategies = [
        ("1️⃣", "RSI 역추세", "RSI < 30 매수, RSI > 70 매도"),
        ("2️⃣", "골든크로스", "MA5 > MA20 매수, MA5 < MA20 매도"),
        ("3️⃣", "듀얼모멘텀", "12개월 수익률 > 0 & 벤치마크 상회"),
        ("4️⃣", "RSI+골든(AND)", "RSI과매도 AND 골든크로스"),
        ("5️⃣", "RSI|MACD(OR)", "RSI과매도 OR MACD골든"),
    ]
    for num, name, desc in strategies:
        print(f"  {num} {name}: {desc}")
    
    print("\n=== 시각화 구성 ===")
    print("  [Level 1 - 포트폴리오 레벨]")
    print("    📈 equityCurveDisplay: 5개 전략 Equity Curve (Line)")
    print("    🕸️ performanceRadar: 성과 지표 비교 (Radar)")
    print("    📊 returnDistribution: 수익률 분포 (Histogram)")
    print("  [Level 2 - 종목 기여도]")
    print("    📊 symbolContribution: Top/Bottom 종목 (Bar)")
    print("    📋 tradeSummary: 거래 통계 (Table)")
    
    print("\n=== 대상 종목 ===")
    symbols = BACKTEST_MULTI_STRATEGY["inputs"]["symbols"]["default"]
    print(f"  {', '.join(symbols)}")
    
    print("\n=== 백테스트 기간 ===")
    print(f"  {BACKTEST_MULTI_STRATEGY['inputs']['start_date']['default']} ~ "
          f"{BACKTEST_MULTI_STRATEGY['inputs']['end_date']['default']}")


# =============================================================================
# 예상 결과 샘플
# =============================================================================

EXPECTED_OUTPUT_SAMPLE = {
    "equity_curves": {
        "RSI 역추세": [
            {"date": "2025-01-01", "value": 100000},
            {"date": "2025-06-01", "value": 108500},
            {"date": "2025-12-31", "value": 115300},
        ],
        "골든크로스": [
            {"date": "2025-01-01", "value": 100000},
            {"date": "2025-06-01", "value": 105200},
            {"date": "2025-12-31", "value": 112800},
        ],
    },
    "metrics": {
        "RSI 역추세": {
            "total_return": 15.3,
            "sharpe_ratio": 1.42,
            "max_drawdown": -8.5,
            "win_rate": 0.58,
            "profit_factor": 1.85,
        },
        "골든크로스": {
            "total_return": 12.8,
            "sharpe_ratio": 1.25,
            "max_drawdown": -10.2,
            "win_rate": 0.52,
            "profit_factor": 1.65,
        },
    },
}


# =============================================================================
# 메인 실행
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    
    from programgarden import ProgramGarden
    
    # API 키 확인
    if not APPKEY or not APPSECRET:
        print("⚠️  LS증권 API 키가 설정되지 않았습니다.")
        print("   프로젝트 루트의 .env 파일에 APPKEY, APPSECRET을 설정하세요.")
        print("\n   예시:")
        print("   APPKEY=your_appkey")
        print("   APPSECRET=your_appsecret")
        sys.exit(1)
    
    print(f"✅ API 키 로드 완료: APPKEY={APPKEY[:8]}...")
    
    pg = ProgramGarden()
    
    # DSL 검증
    print("\n=== DSL 검증 ===")
    result = pg.validate(BACKTEST_MULTI_STRATEGY)
    print(f"Valid: {result.is_valid}")
    if result.errors:
        print(f"Errors:")
        for e in result.errors[:5]:
            print(f"  - {e}")
    if result.warnings:
        print(f"Warnings:")
        for w in result.warnings[:5]:
            print(f"  - {w}")
    
    # 워크플로우 정보 출력
    print_workflow_info()
    
    # ========================================
    # 실행
    # ========================================
    print("\n=== 백테스트 실행 ===")
    print("백테스트를 실행하시겠습니까? (y/n): ", end="")
    
    user_input = input().strip().lower()
    if user_input != "y":
        print("취소되었습니다.")
        sys.exit(0)
    
    secrets = {
        "credential_id": {
            "appkey": APPKEY,
            "appsecret": APPSECRET,
        }
    }
    
    async def run_backtest():
        print("\n🚀 백테스트 시작...")
        job = await pg.run_async(BACKTEST_MULTI_STRATEGY, secrets=secrets)
        print(f"Job ID: {job.job_id}")
        print(f"Status: {job.status}")
        
        # 완료 대기
        while job.status == "running":
            await asyncio.sleep(1)
            state = job.get_state()
            executed = state.get("stats", {}).get("nodes_executed", 0)
            print(f"\r⏳ 진행 중... (노드 실행: {executed}개)", end="")
        
        print(f"\n\n✅ 완료! Status: {job.status}")
        
        # 결과 출력
        state = job.get_state()
        print(f"\n=== 실행 결과 ===")
        print(f"Stats: {state.get('stats', {})}")
        
        # 에러가 있으면 출력
        if state.get("errors"):
            print(f"\n⚠️ Errors:")
            for err in state["errors"]:
                print(f"  - {err}")
    
    try:
        asyncio.run(run_backtest())
    except KeyboardInterrupt:
        print("\n\n⏹️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ 백테스트 완료")
