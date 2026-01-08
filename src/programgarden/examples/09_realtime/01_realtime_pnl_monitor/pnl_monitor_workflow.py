"""
예제 34: 보유 종목 실시간 수익률 모니터링

RealAccountNode와 AccountNode의 차이를 보여주는 예제입니다.

노드 선택 가이드:
- RealAccountNode: 실시간 WebSocket 연결, 틱마다 수익률 계산
  - stay_connected=True: 플로우 끝나도 계속 연결 유지
  - stay_connected=False: 플로우 끝나면 연결 종료
- AccountNode: REST API 1회 조회 (실시간 X)

RealAccountNode 동작 방식:
1. StockAccountTracker가 WebSocket 연결 수립
2. 틱마다 실시간 수익률 재계산 (pnl_rate, pnl_amount)
3. 60초마다 REST API로 데이터 정합성 동기화
4. Job.stop() 호출 시 종료

사전 준비:
1. .env 파일에 LS증권 API 키 설정
   APPKEY=your_appkey
   APPSECRET=your_appsecret

2. 실전계좌에 보유 종목이 있어야 합니다.
"""

import os
import asyncio
import signal
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
    "description": "stay_connected=True로 실시간 WebSocket 연결을 유지하며 틱마다 수익률 계산",
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
        # Layer 2: Realtime - 계좌 정보 (실시간 수익률)
        # ============================================
        {
            "id": "account",
            "type": "RealAccountNode",
            "category": "realtime",
            "stay_connected": True,       # 🔑 핵심: WebSocket 연결 유지
            "sync_interval_sec": 60,      # 60초마다 REST API로 데이터 동기화
            "position": {"x": 400, "y": 200},
            # stay_connected=True 동작:
            # 1. WebSocket으로 실시간 틱 수신
            # 2. 틱마다 StockAccountTracker가 수익률 재계산
            # 3. positions에 pnl_rate, pnl_amount 포함
            # 4. Job.stop() 호출 전까지 계속 유지
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
        {"from": "account.positions", "to": "display.data"},
    ],
}


def print_workflow_info():
    """워크플로우 정보 출력"""
    print("\n" + "=" * 60)
    print("📊 예제 34: 보유 종목 실시간 수익률 모니터링")
    print("=" * 60)
    
    print("\n=== 핵심 옵션 ===")
    account_node = next(n for n in REALTIME_PNL_MONITOR["nodes"] if n["id"] == "account")
    print(f"  stay_connected: {account_node.get('stay_connected', True)}")
    print(f"  sync_interval_sec: {account_node.get('sync_interval_sec', 60)}")
    
    print("\n=== 노드 구성 ===")
    for node in REALTIME_PNL_MONITOR["nodes"]:
        print(f"  - {node['id']}: {node['type']} ({node['category']})")
    
    print("\n=== 데이터 흐름 ===")
    for edge in REALTIME_PNL_MONITOR["edges"]:
        print(f"  {edge['from']} → {edge['to']}")
    
    print("\n=== 동작 방식 ===")
    print("  1. StockAccountTracker가 WebSocket 연결 수립")
    print("  2. 틱마다 실시간 수익률 재계산 (pnl_rate, pnl_amount)")
    print("  3. 60초마다 REST API로 데이터 정합성 동기화")
    print("  4. Ctrl+C 또는 job.stop()으로 종료")


# AccountNode 버전 (1회 REST API 조회용)
ONESHOT_PNL_CHECK = {
    "id": "34-oneshot-pnl-check",
    "version": "1.0.0",
    "name": "보유 종목 수익률 1회 조회",
    "description": "AccountNode로 1회 REST API 조회 후 종료 (실시간 X)",
    "inputs": {
        "credential_id": {
            "type": "credential",
            "required": True,
        },
    },
    "nodes": [
        {"id": "start", "type": "StartNode", "category": "infra"},
        {"id": "broker", "type": "BrokerNode", "category": "infra", 
         "provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
        {
            "id": "account", 
            "type": "AccountNode",  # 🔑 1회 REST API 조회 (실시간 아님)
            "category": "account",
        },
        {"id": "display", "type": "DisplayNode", "category": "display",
         "chart_type": "table", "title": "📊 수익률 현황 (1회 조회)"},
    ],
    "edges": [
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "account"},
        {"from": "account.positions", "to": "display.data"},
    ],
}


# 스케줄 + 실시간 노드 통합 버전
SCHEDULED_PNL_MONITOR = {
    "id": "34-scheduled-pnl-monitor",
    "version": "1.0.0",
    "name": "스케줄 기반 실시간 수익률 모니터링",
    "description": "ScheduleNode로 주기적 트리거 + stay_connected로 실시간 연결 유지",
    "inputs": {
        "credential_id": {
            "type": "credential",
            "required": True,
        },
    },
    "nodes": [
        {"id": "start", "type": "StartNode", "category": "infra"},
        {
            "id": "schedule", 
            "type": "ScheduleNode", 
            "category": "trigger",
            "cron": "*/30 * * * * *",  # 30초마다 플로우 재실행
            "timezone": "Asia/Seoul",
            # 동작: 30초마다 schedule_tick 이벤트 → 전체 플로우 재실행
        },
        {"id": "broker", "type": "BrokerNode", "category": "infra", 
         "provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
        {
            "id": "account", 
            "type": "RealAccountNode", 
            "category": "realtime",
            "stay_connected": True,   # 🔑 스케줄 사이에도 연결 유지
            "sync_interval_sec": 60,
            # 동작: 첫 실행 시 StockAccountTracker 시작,
            #       이후 schedule_tick에서는 기존 tracker 재사용
        },
        {"id": "display", "type": "DisplayNode", "category": "display",
         "chart_type": "table", "title": "📊 실시간 수익률 (스케줄 연동)"},
    ],
    "edges": [
        {"from": "start.start", "to": "schedule"},
        {"from": "schedule.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "account"},
        {"from": "account.positions", "to": "display.data"},
    ],
}


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

    # ========================================
    # 실행 모드 선택
    # ========================================
    print("\n=== 실행 모드 선택 ===")
    print("  1. 실시간 모니터링 (stay_connected=True, Ctrl+C로 종료)")
    print("  2. 1회 조회 (stay_connected=False, 자동 종료)")
    print("  3. 스케줄 + 실시간 (30초마다 플로우 재실행, 연결 유지)")
    
    mode = input("\n선택 (1/2/3, 기본 1): ").strip() or "1"
    
    secrets = {
        "credential_id": {
            "appkey": APPKEY,
            "appsecret": APPSECRET,
        }
    }
    
    if mode == "2":
        # 1회 조회 모드
        print("\n🔍 1회 조회 모드 실행")
        
        async def run_oneshot():
            job = await pg.run_async(ONESHOT_PNL_CHECK, secrets=secrets)
            print(f"Job ID: {job.job_id}")
            print(f"Status: {job.status}")
            
            # Job이 완료될 때까지 대기 (짧은 시간 내 완료됨)
            while job.status == "running":
                await asyncio.sleep(0.5)
            
            print(f"\n✅ 완료! Status: {job.status}")
            state = job.get_state()
            print(f"Stats: {state['stats']}")
        
        asyncio.run(run_oneshot())
    
    elif mode == "3":
        # 스케줄 + 실시간 모드
        print("\n🕐 스케줄 + 실시간 모드 시작 (30초마다 플로우 재실행, Ctrl+C로 종료)")
        print("   stay_connected=True로 스케줄 사이에도 WebSocket 연결 유지\n")
        
        async def run_scheduled():
            job = await pg.run_async(SCHEDULED_PNL_MONITOR, secrets=secrets)
            print(f"Job ID: {job.job_id}")
            print(f"Status: {job.status}")
            print(f"Stay Connected Nodes: {job._stay_connected_nodes}")
            print(f"Has Schedule: {job._has_schedule_node}")
            print(f"Persistent Tasks: {len(job.context._persistent_tasks)}")
            
            try:
                while job.status == "running":
                    await asyncio.sleep(10)
                    state = job.get_state()
                    print(f"\n📊 [{state['stats']['flow_executions']}회 실행] "
                          f"realtime_updates={state['stats']['realtime_updates']}")
            except asyncio.CancelledError:
                pass
            finally:
                if job.status == "running":
                    print("\n\n⏹️  종료 중...")
                    await job.stop()
                print(f"Final Status: {job.status}")
                state = job.get_state()
                print(f"Final Stats: {state['stats']}")
        
        try:
            asyncio.run(run_scheduled())
        except KeyboardInterrupt:
            pass
        
        print("\n✅ 스케줄 모니터링 종료")
        
    else:
        # 실시간 모니터링 모드
        print("\n🚀 실시간 모니터링 시작 (Ctrl+C로 종료)")
        print("   WebSocket으로 틱마다 수익률이 업데이트됩니다...\n")
        
        async def run_realtime():
            job = await pg.run_async(REALTIME_PNL_MONITOR, secrets=secrets)
            print(f"Job ID: {job.job_id}")
            print(f"Status: {job.status}")
            print(f"Stay Connected Nodes: {job._stay_connected_nodes}")
            
            # Job이 실행 중인 동안 상태 출력 (5초마다)
            try:
                while job.status == "running":
                    await asyncio.sleep(5)
                    state = job.get_state()
                    print(f"\n📊 Stats: flow_executions={state['stats']['flow_executions']}, "
                          f"realtime_updates={state['stats']['realtime_updates']}")
            except asyncio.CancelledError:
                pass
            finally:
                # 종료 시 cleanup
                if job.status == "running":
                    print("\n\n⏹️  종료 중...")
                    await job.stop()
                print(f"Final Status: {job.status}")
                state = job.get_state()
                print(f"Final Stats: {state['stats']}")
        
        try:
            asyncio.run(run_realtime())
        except KeyboardInterrupt:
            pass
        
        print("\n✅ 모니터링 종료")
