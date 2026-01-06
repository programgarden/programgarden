"""
예제 34: 보유 종목 실시간 수익률 모니터링

RealAccountNode + RealMarketDataNode + PnLCalculatorNode를 사용하여
보유 종목의 실시간 수익률 변화를 테이블로 표시합니다.

사전 준비:
1. .env 파일에 LS증권 API 키 설정
   APPKEY=your_appkey
   APPSECRET=your_appsecret

2. 실전계좌에 보유 종목이 있어야 합니다.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
project_root = Path(__file__).resolve().parents[5]  # src/programgarden/examples/34_xxx → 프로젝트 루트
load_dotenv(project_root / ".env")

# 환경변수에서 API 키 읽기
APPKEY = os.getenv("APPKEY", "")
APPSECRET = os.getenv("APPSECRET", "")


REALTIME_PNL_MONITOR = {
    "id": "34-realtime-pnl-monitor",
    "version": "1.0.0",
    "name": "보유 종목 실시간 수익률 모니터링",
    "description": "보유 중인 종목의 실시간 수익률을 테이블로 표시 (RealAccountNode가 pnl 포함)",
    "inputs": {
        "credential_id": {
            "type": "credential",
            "required": True,
            "description": "LS증권 API 인증 정보",
        },
    },
    "nodes": [
        # ============================================
        # Layer 1: Infra - 시작 및 브로커 연결
        # ============================================
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 0, "y": 200},
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "provider": "ls-sec.co.kr",
            "product": "overseas_stock",  # 해외주식
            "paper_trading": False,       # 실전계좌
            "position": {"x": 200, "y": 200},
        },
        # ============================================
        # Layer 2: Realtime - 계좌 정보 (수익률 포함)
        # ============================================
        {
            "id": "account",
            "type": "RealAccountNode",
            "category": "realtime",
            "sync_interval_sec": 60,  # 1분마다 REST API로 포지션 동기화
            "position": {"x": 400, "y": 200},
            # Note: RealAccountNode는 내부적으로 StockAccountTracker를 사용하여
            # 틱마다 수익률을 자동 계산합니다. positions에 pnl_rate, pnl_amount 포함됨.
        },
        # ============================================
        # Layer 3: Display - 결과 시각화
        # ============================================
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "chart_type": "table",
            "title": "📊 실시간 수익률 현황",
            "options": {
                "columns": [
                    "symbol",        # 종목코드
                    "qty",           # 보유수량
                    "avg_price",     # 평균단가
                    "current_price", # 현재가
                    "pnl_rate",      # 수익률 (%)
                    "pnl_amount",    # 평가손익 ($)
                ],
                "refresh_ms": 500,   # 0.5초마다 갱신
                "sort_by": "pnl_rate",
                "sort_order": "desc",
                "highlight": {
                    "positive": "green",  # 양수 수익률
                    "negative": "red",    # 음수 수익률
                },
            },
            "position": {"x": 600, "y": 200},
        },
    ],
    "edges": [
        # ============================================
        # 기본 연결: Start → Broker → Account → Display
        # ============================================
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "account"},
        # RealAccountNode.positions에 pnl_rate, pnl_amount 이미 포함
        {"from": "account.positions", "to": "display.data"},
    ],
}


def print_workflow_info():
    """워크플로우 정보 출력"""
    print("\n" + "=" * 60)
    print("📊 예제 34: 보유 종목 실시간 수익률 모니터링")
    print("=" * 60)
    
    print("\n=== 노드 구성 ===")
    for node in REALTIME_PNL_MONITOR["nodes"]:
        print(f"  - {node['id']}: {node['type']} ({node['category']})")
    
    print("\n=== 데이터 흐름 ===")
    for edge in REALTIME_PNL_MONITOR["edges"]:
        print(f"  {edge['from']} → {edge['to']}")
    
    print("\n=== 실행 설정 ===")
    broker = next(n for n in REALTIME_PNL_MONITOR["nodes"] if n["id"] == "broker")
    print(f"  계좌: {'모의투자' if broker.get('paper_trading') else '실전계좌'}")
    print(f"  상품: {broker['product']}")
    print(f"  증권사: {broker['provider']}")


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
    result = pg.validate(REALTIME_PNL_MONITOR)
    print(f"Valid: {result.is_valid}")
    if result.errors:
        print(f"Errors: {result.errors}")
    if result.warnings:
        print(f"Warnings: {result.warnings}")

    # 워크플로우 정보 출력
    print_workflow_info()

    # 실제 실행 (credential 설정 필요)
    # print("\n=== 실행 ===")
    # print("실제 실행하려면 아래 코드의 주석을 해제하세요:")
    # print("""
    # secrets = {
    #     "credential_id": {
    #         "appkey": APPKEY,
    #         "appsecret": APPSECRET,
    #     }
    # }
    # job = pg.run(REALTIME_PNL_MONITOR, secrets=secrets)
    # print(f"Job ID: {job.id}")
    # print(f"Status: {job.status}")
    # """)

    # 실제 실행: 3초마다 반복
    import time
    
    secrets = {
        "credential_id": {
            "appkey": APPKEY,
            "appsecret": APPSECRET,
        }
    }
    
    print("\n🚀 실시간 수익률 모니터링 시작 (Ctrl+C로 종료)")
    print("   10초마다 업데이트됩니다...\n")
    
    try:
        iteration = 0
        while True:
            iteration += 1
            print(f"\n[{iteration}회차] {time.strftime('%H:%M:%S')}")
            
            job = pg.run(REALTIME_PNL_MONITOR, secrets=secrets)
            
            # 10초 대기
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  모니터링 종료")
        print(f"   총 {iteration}회 업데이트")
