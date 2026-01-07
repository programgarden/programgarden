"""
예제 32: 보유종목 이평선 추세 확인 백테스트 (Production Format)

워크플로우:
1. StartNode → BrokerNode → AccountBalanceNode로 해외주식 잔고 조회
2. ConditionNode (HasPositions)로 보유종목 존재 확인
3. HistoricalDataNode로 120일 일봉 데이터 조회
4. BacktestExecutorNode로 이동평균선 추세 분석
5. BacktestResultNode로 결과 집계
6. DisplayNode로 출력

실전 활용: 보유중인 종목의 추세가 유효한지 정기적으로 점검
"""

import os

from dotenv import load_dotenv

from programgarden import ProgramGarden

load_dotenv()


# =============================================================================
# 워크플로우 정의 (JSON DSL)
# =============================================================================

WORKFLOW_DSL = {
    "id": "ma-trend-backtest",
    "version": "1.0.0",
    "name": "보유종목 이평선 추세 백테스트",
    "description": "해외주식 보유종목의 이동평균선 추세를 분석하여 현재 추세 유효성을 점검합니다.",
    
    # 워크플로우 입력 파라미터 정의
    "inputs": {
        "credential_id": {"type": "credential", "required": True},
        "short_ma_period": {"type": "number", "default": 5, "description": "단기 이동평균 기간"},
        "long_ma_period": {"type": "number", "default": 20, "description": "장기 이동평균 기간"},
        "analysis_days": {"type": "number", "default": 120, "description": "분석 기간 (일)"},
    },
    
    # 노드 정의
    "nodes": [
        # 1. 인프라 노드
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra"
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "config": {
                "company": "ls",
                "product": "overseas_stock"
            }
        },
        
        # 2. 계좌 데이터 노드
        {
            "id": "fetchBalance",
            "type": "AccountNode",
            "category": "data",
            "config": {
                "api": "COSOQ00201",
                "product": "overseas_stock"
            }
        },
        
        # 3. 조건 노드 - 보유종목 존재 확인
        {
            "id": "hasHoldings",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "HasPositions",
            "params": {
                "min_count": 1
            }
        },
        
        # 4. 과거 데이터 노드 - 차트 데이터 조회
        {
            "id": "historicalData",
            "type": "HistoricalDataNode",
            "category": "data",
            "config": {
                "api": "g3103",
                "interval": "1d",
                "period": "{{ input.analysis_days }}"
            }
        },
        
        # 5. 백테스트 실행 노드 - MA 추세 분석
        {
            "id": "maTrendBacktest",
            "type": "BacktestExecutorNode",
            "category": "backtest",
            "plugin": "MATrendAnalysis",
            "params": {
                "short_period": "{{ input.short_ma_period }}",
                "long_period": "{{ input.long_ma_period }}",
                "trend_check_days": 5
            }
        },
        
        # 6. 백테스트 결과 노드
        {
            "id": "backtestResult",
            "type": "BacktestResultNode",
            "category": "backtest",
            "config": {
                "metrics": ["uptrend_ratio", "avg_ma_gap", "current_trend", "ma_slope"]
            }
        },
        
        # 7. 디스플레이 노드
        {
            "id": "resultDisplay",
            "type": "DisplayNode",
            "category": "display",
            "config": {
                "type": "table",
                "title": "📊 해외주식 보유종목 이평선 추세 분석 결과",
                "columns": [
                    {"key": "symbol", "label": "종목"},
                    {"key": "quantity", "label": "보유수량"},
                    {"key": "pnl_rate", "label": "손익률(%)"},
                    {"key": "current_trend", "label": "현재 추세"},
                    {"key": "uptrend_ratio", "label": "우상향 비율(%)"},
                    {"key": "ma_gap_percent", "label": "이평선 갭(%)"},
                    {"key": "long_ma_slope", "label": "장기이평 기울기(%)"},
                    {"key": "recommendation", "label": "권고"}
                ]
            }
        }
    ],
    
    # 엣지 정의 - 데이터 흐름
    "edges": [
        # 시작 → 브로커 → 잔고조회
        {"from": "start", "to": "broker"},
        {"from": "broker.connection", "to": "fetchBalance"},
        
        # 잔고조회 → 보유종목 확인
        {"from": "fetchBalance.holdings", "to": "hasHoldings.positions"},
        
        # 보유종목 → 과거 데이터 조회
        {"from": "hasHoldings.passed_symbols", "to": "historicalData.symbols"},
        
        # 과거 데이터 → 백테스트 실행
        {"from": "historicalData.ohlcv_data", "to": "maTrendBacktest.historical_data"},
        {"from": "fetchBalance.holdings", "to": "maTrendBacktest.position_info"},
        
        # 백테스트 실행 → 결과 집계
        {"from": "maTrendBacktest.result", "to": "backtestResult.backtest_result"},
        
        # 결과 집계 → 디스플레이
        {"from": "backtestResult.summary", "to": "resultDisplay.data"}
    ]
}


# =============================================================================
# 실행 컨텍스트 (Credential + 파라미터)
# =============================================================================

EXECUTION_CONTEXT = {
    # Credential Layer - 인증 정보 (환경변수에서 로드)
    "credentials": {
        "ls": {
            "app_key": os.getenv("LS_APP_KEY"),
            "app_secret": os.getenv("LS_APP_SECRET"),
            "paper_trading": True
        }
    },
    
    # 워크플로우 입력 파라미터
    "inputs": {
        "short_ma_period": 5,
        "long_ma_period": 20,
        "analysis_days": 120
    },
    
    # 실행 옵션
    "options": {
        "dry_run": False,
        "verbose": True
    }
}


# =============================================================================
# 메인 실행
# =============================================================================

def main():
    """워크플로우 실행"""
    print("=" * 70)
    print("📊 해외주식 보유종목 이평선 추세 백테스트")
    print("=" * 70)
    
    # ProgramGarden 클라이언트 생성
    pg = ProgramGarden()
    
    # 워크플로우 검증
    validation_result = pg.validate(WORKFLOW_DSL)
    if not validation_result.is_valid:
        print(f"❌ 워크플로우 검증 실패: {validation_result.errors}")
        return
    
    print("✅ 워크플로우 검증 완료")
    
    # 워크플로우 실행 (동기)
    result = pg.run(WORKFLOW_DSL, EXECUTION_CONTEXT)
    
    # 결과 출력
    status = result.get("status", "unknown")
    if status == "completed":
        print("\n✅ 워크플로우 실행 완료")
        print(f"📋 Job ID: {result.get('job_id')}")
        print(f"📋 Workflow ID: {result.get('workflow_id')}")
        
        # 통계
        stats = result.get("stats", {})
        if stats:
            print(f"📊 통계: 조건 평가 {stats.get('conditions_evaluated', 0)}회, "
                  f"주문 {stats.get('orders_placed', 0)}건, "
                  f"에러 {stats.get('errors_count', 0)}건")
        
        # 로그 출력
        logs = result.get("logs", [])
        if logs:
            print("\n📝 실행 로그:")
            for log in logs[-10:]:  # 최근 10개
                print(f"   [{log.get('level', 'info').upper()}] {log.get('message', '')}")
    else:
        print(f"\n❌ 워크플로우 실행 결과: {status}")
        print(f"   상세: {result}")


if __name__ == "__main__":
    main()
