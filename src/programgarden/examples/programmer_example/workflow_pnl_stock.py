"""
[해외주식] 워크플로우 수익률 추적 테스트

테스트 시나리오:
1. BrokerNode 연결 후 context 획득
2. context.record_workflow_order() 호출 → workflow_orders 테이블 저장
3. 시간차 대기 (AS0 접수 이벤트 시뮬레이션)
4. context.record_workflow_fill() 호출 → workflow_position_lots 저장 (AS1 체결 이벤트 시뮬레이션)
5. on_workflow_pnl_update 콜백 호출 확인

💡 이 테스트는 실제 주문을 넣지 않고, record_workflow_order/record_workflow_fill을
   직접 호출하여 AS0→AS1 이벤트 흐름을 시뮬레이션합니다.

AS0/AS1 참고:
- AS0만 등록해도 AS0~AS4 전부 수신됨
- AS0: 접수 (sOrdxctPtnCode: 01=신규, 03=취소접수, 12=정정완료, 13=취소완료, 14=거부)
- AS1: 체결 (sExecQty > 0, sExecPrc > 0)

실행: cd src/programgarden && poetry run python examples/programmer_example/workflow_pnl_stock.py
"""

import asyncio
import copy
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 설정
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src" / "programgarden"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# 암호화 유틸리티 로드
workflow_editor_path = Path(__file__).parent.parent / "workflow_editor"
sys.path.insert(0, str(workflow_editor_path))
from encryption import decrypt_data

from programgarden import ProgramGarden
from programgarden_core.bases import (
    BaseExecutionListener,
    WorkflowPnLEvent,
    NodeStateEvent,
    NodeState,
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logging.getLogger('programgarden.executor').setLevel(logging.DEBUG)

# 해외주식 credential ID (credentials.json에서)
OVERSEAS_STOCK_CREDENTIAL_ID = "7c5caa90-f013-44fd-855d-410437c86737"

# 이벤트 흐름 시뮬레이션 모드 (주말/휴일에도 테스트 가능)
SIMULATE_EVENT_FLOW = True


def load_credential(credential_id: str) -> dict:
    """credentials.json에서 특정 credential 로드 및 복호화"""
    cred_path = workflow_editor_path / "credentials.json"
    
    with open(cred_path) as f:
        data = json.load(f)
    
    for cred in data.get("credentials", []):
        if cred["id"] == credential_id:
            encrypted_data = cred.get("data", "{}")
            decrypted = decrypt_data(encrypted_data)
            print(f"✅ Credential 로드: {cred['name']} (appkey: {decrypted.get('appkey', 'N/A')[:8]}...)")
            return decrypted
    
    return {}


class WorkflowPnLTestListener(BaseExecutionListener):
    """워크플로우 수익률 테스트 리스너 (이벤트 흐름 검증용)"""
    
    def __init__(self):
        self.workflow_pnl_events = []
        self.node_events = []
        self.context = None  # 이벤트 흐름 시뮬레이션용
    
    async def on_node_state_change(self, event: NodeStateEvent) -> None:
        """노드 상태 변경 추적"""
        self.node_events.append(event)
        status = "✅" if event.state == NodeState.COMPLETED else "🔄" if event.state == NodeState.RUNNING else "⏳"
        print(f"{status} [{event.node_id}] {event.state.value}")
        
        # BrokerNode 완료 시 context 저장 (이벤트 흐름 시뮬레이션용)
        if event.node_id == "broker" and event.state == NodeState.COMPLETED:
            # outputs에서 context 접근 가능한지 확인
            print(f"   📋 BrokerNode 완료")
    
    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
        """워크플로우 수익률 업데이트"""
        self.workflow_pnl_events.append(event)
        
        wf_rate = float(event.workflow_pnl_rate)
        total_rate = float(event.total_pnl_rate)
        trust = event.trust_score
        
        print(f"\n📊 WorkflowPnL: wf={wf_rate:+.2f}%, total={total_rate:+.2f}%, trust={trust}")
        print(f"   워크플로우 포지션: {len(event.workflow_positions)}개")
        print(f"   그 외 포지션: {len(event.other_positions)}개")
        
        # 워크플로우 포지션 상세
        if event.workflow_positions:
            for pos in event.workflow_positions:
                print(f"   📈 WF: {pos.symbol} {pos.quantity}주 @ ${pos.avg_price:.2f} → ${pos.current_price:.2f} ({pos.pnl_rate:+.2f}%)")


async def simulate_event_flow(context, job_id: str):
    """AS0→AS1 이벤트 흐름 시뮬레이션
    
    실제 흐름:
    1. NewOrderNode → context.record_workflow_order() 호출 (동기)
    2. AS0 접수 이벤트 수신 (약 0.1~0.5초 후)
    3. AS1 체결 이벤트 수신 → context.record_workflow_fill() 호출 (비동기)
    4. AccountTracker refresh → on_workflow_pnl_update 콜백
    
    이 함수는 2~4 단계를 시뮬레이션합니다.
    
    ⚠️ 실제 계좌 보유 종목: GOSS 1주, RETO 5주
    """
    print("\n🔧 AS0→AS1 이벤트 흐름 시뮬레이션")
    print("   📌 실제 계좌 보유 종목: GOSS 1주, RETO 5주")
    
    now = datetime.now()
    order_date = now.strftime('%Y%m%d')
    fill_time = now.strftime('%H%M%S000')
    
    # === 시뮬레이션 1: GOSS 1주 매수 (실제 보유 종목) ===
    print("\n[1] 주문 기록: GOSS 1주 @ $1.50")
    
    # Step 1: record_workflow_order (NewOrderNode가 하는 일) - 동기 메서드!
    context.record_workflow_order(
        order_no='SIM001',
        order_date=order_date,
        symbol='GOSS',
        exchange='NASDAQ',
        side='buy',
        quantity=1,
        price=1.50,
        node_id='buy_order',
    )
    print("   📝 workflow_orders 테이블에 주문 기록됨")
    
    # Step 2: AS0 접수 이벤트 시뮬레이션 (약간의 딜레이)
    print("   ⏳ AS0 접수 이벤트 대기 시뮬레이션 (0.3초)...")
    await asyncio.sleep(0.3)
    
    # Step 3: AS1 체결 이벤트 → record_workflow_fill (비동기)
    print("   📡 AS1 체결 이벤트 시뮬레이션")
    result = await context.record_workflow_fill(
        order_no='SIM001',
        order_date=order_date,
        symbol='GOSS',
        exchange='NASDAQ',
        side='buy',
        quantity=1,
        price=1.50,
        fill_time=fill_time,
        commda_code='40',  # OPEN API
    )
    print(f"   ✅ 체결 기록 결과: {result}")
    
    # === 시뮬레이션 2: RETO 5주 매수 (실제 보유 종목) ===
    print("\n[2] 주문 기록: RETO 5주 @ $1.20")
    
    # 동기 메서드
    context.record_workflow_order(
        order_no='SIM002',
        order_date=order_date,
        symbol='RETO',
        exchange='NASDAQ',
        side='buy',
        quantity=5,
        price=1.20,
        node_id='buy_order',
    )
    print("   📝 workflow_orders 테이블에 주문 기록됨")
    
    await asyncio.sleep(0.3)
    
    # 비동기 메서드
    result = await context.record_workflow_fill(
        order_no='SIM002',
        order_date=order_date,
        symbol='RETO',
        exchange='NASDAQ',
        side='buy',
        quantity=5,
        price=1.20,
        fill_time=fill_time,
        commda_code='40',
    )
    print(f"   ✅ 체결 기록 결과: {result}")
    
    print("\n✅ 이벤트 흐름 시뮬레이션 완료!")
    print("   - 다음 틱 수신 시 on_workflow_pnl_update 콜백이 호출됩니다.")
    print("   - GOSS 1주, RETO 5주가 워크플로우 포지션으로 분류되어야 합니다.")
    
    # === DB 기반 PnL 직접 계산 ===
    print("\n" + "=" * 50)
    print("📊 DB 기반 PnL 직접 계산 (calculate_pnl)")
    print("=" * 50)
    
    tracker = context._workflow_position_tracker
    if tracker:
        # 워크플로우 포지션 확인
        wf_positions = tracker.get_workflow_positions()
        print(f"\n📌 워크플로우 포지션 (DB 기준): {len(wf_positions)}개")
        for symbol, pos in wf_positions.items():
            print(f"   - {symbol}: {pos.quantity}주 @ ${float(pos.avg_price):.2f}")
        
        # 현재가 가정 (테스트용)
        mock_prices = {
            'GOSS': 1.55,  # 가상 현재가 (매입가 1.50 → +3.33%)
            'RETO': 1.25,  # 가상 현재가 (매입가 1.20 → +4.17%)
        }
        
        # 전체 포지션 (실제 계좌에서 가져온 것처럼 시뮬레이션) - dict 형태로
        all_positions = {
            'GOSS': {'quantity': 1, 'avg_price': 1.50, 'exchange': 'NASDAQ'},
            'RETO': {'quantity': 5, 'avg_price': 1.20, 'exchange': 'NASDAQ'},
        }
        
        # calculate_pnl 호출
        pnl_data = tracker.calculate_pnl(
            current_prices=mock_prices,
            all_positions=all_positions,
            currency="USD",
        )
        
        print(f"\n📊 PnL 계산 결과:")
        print(f"   워크플로우 수익률: {float(pnl_data['workflow_pnl_rate']):+.2f}%")
        print(f"   워크플로우 평가금액: ${float(pnl_data['workflow_eval_amount']):.2f}")
        print(f"   워크플로우 매입금액: ${float(pnl_data['workflow_buy_amount']):.2f}")
        print(f"   워크플로우 손익: ${float(pnl_data['workflow_pnl_amount']):.2f}")
        print(f"   그 외 수익률: {float(pnl_data['other_pnl_rate']):+.2f}%")
        print(f"   전체 수익률: {float(pnl_data['total_pnl_rate']):+.2f}%")
        print(f"   신뢰도: {pnl_data['trust_score']}")
        
        # 워크플로우 포지션 상세
        print(f"\n📈 워크플로우 포지션 상세:")
        for pos in pnl_data['workflow_positions']:
            print(f"   - {pos.symbol}: {pos.quantity}주 @ ${float(pos.avg_price):.2f} → ${float(pos.current_price):.2f} ({float(pos.pnl_rate):+.2f}%)")
    else:
        print("⚠️ WorkflowPositionTracker가 초기화되지 않음")


def check_db(db_path: Path):
    """DB 파일 내용 확인"""
    if not db_path.exists():
        print(f"\n❌ DB 파일 없음: {db_path}")
        return
    
    print(f"\n📋 DB 파일 확인: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # workflow_orders 테이블 확인
    try:
        cursor.execute("SELECT * FROM workflow_orders")
        orders = cursor.fetchall()
        print(f"\n   workflow_orders 테이블: {len(orders)}건")
        for order in orders:
            print(f"      {order}")
    except Exception as e:
        print(f"   workflow_orders 테이블 조회 실패: {e}")
    
    # workflow_position_lots 테이블 확인
    try:
        cursor.execute("SELECT * FROM workflow_position_lots")
        lots = cursor.fetchall()
        print(f"\n   workflow_position_lots 테이블: {len(lots)}건")
        for lot in lots:
            print(f"      {lot}")
    except Exception as e:
        print(f"   workflow_position_lots 테이블 조회 실패: {e}")
    
    # trade_history 테이블 확인
    try:
        cursor.execute("SELECT * FROM trade_history")
        trades = cursor.fetchall()
        print(f"\n   trade_history 테이블: {len(trades)}건")
        for trade in trades:
            print(f"      {trade}")
    except Exception as e:
        print(f"   trade_history 테이블 조회 실패: {e}")
    
    conn.close()


# 테스트용 워크플로우: BrokerNode만 (주문 없이 PnL 추적만)
TEST_WORKFLOW = {
    "id": "workflow-pnl-stock-test",
    "name": "해외주식 워크플로우 PnL 테스트",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode"
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "provider": "ls-sec.co.kr",
            "product": "overseas_stock",
            "credential_id": "broker-cred"
        }
    ],
    "edges": [
        {"from": "start", "to": "broker"}
    ],
    "credentials": [
        {
            "id": "broker-cred",
            "type": "broker_ls",
            "name": "LS증권 (해외주식)",
            "data": {
                "appkey": "",
                "appsecret": "",
                "paper_trading": False
            }
        }
    ]
}


async def main():
    """테스트 실행
    
    핵심 테스트 흐름:
    1. BrokerNode 연결 → context 획득
    2. context.record_workflow_order() → workflow_orders 저장
    3. context.record_workflow_fill() → workflow_position_lots 저장 (AS1 시뮬레이션)
    4. 틱 수신 → on_workflow_pnl_update 콜백 호출 확인
    """
    # credentials.json에서 해외주식 credential 복호화
    cred_data = load_credential(OVERSEAS_STOCK_CREDENTIAL_ID)
    
    if not cred_data.get("appkey") or not cred_data.get("appsecret"):
        print("❌ credentials.json에서 해외주식 credential을 로드할 수 없습니다")
        return
    
    # credentials에 복호화된 실제 값 주입
    workflow = copy.deepcopy(TEST_WORKFLOW)
    workflow["credentials"] = [
        {
            "id": "broker-cred",
            "type": "broker_ls",
            "name": "LS증권 (해외주식)",
            "data": {
                "appkey": cred_data["appkey"],
                "appsecret": cred_data["appsecret"],
                "paper_trading": cred_data.get("paper_trading", False)
            }
        }
    ]
    
    # DB 파일 경로
    db_path = Path("programgarden_data") / "workflow-pnl-stock-test_workflow.db"
    
    print("=" * 70)
    print("🚀 [해외주식] 워크플로우 수익률 추적 테스트")
    print("=" * 70)
    print()
    
    if SIMULATE_EVENT_FLOW:
        print("💡 모드: AS0→AS1 이벤트 흐름 시뮬레이션")
        print("   - context.record_workflow_order() 직접 호출")
        print("   - context.record_workflow_fill() 직접 호출 (AS1 체결 시뮬레이션)")
        print("   - 실제 주문은 넣지 않습니다")
    else:
        print("⚠️  모드: 실투자 (실제 주문이 실행됩니다!)")
    
    print()
    print(f"📌 DB 파일: {db_path}")
    print()
    
    # 리스너 생성
    listener = WorkflowPnLTestListener()
    
    # ProgramGarden 실행
    pg = ProgramGarden()
    
    try:
        print("=" * 70)
        print("📡 워크플로우 실행 시작")
        print("=" * 70)
        
        job = await pg.run_async(
            workflow,
            listeners=[listener],
        )
        
        # BrokerNode 완료 대기 (context 획득용)
        print("\n⏳ BrokerNode 완료 대기중...")
        await asyncio.sleep(3)
        
        # job의 context 획득 (WorkflowJob.context 속성 사용)
        if hasattr(job, 'context') and job.context:
            context = job.context
            print(f"✅ Context 획득 완료 (job_id: {job.job_id})")
            
            if SIMULATE_EVENT_FLOW:
                # 이벤트 흐름 시뮬레이션
                await simulate_event_flow(context, job.job_id)
        
        # 워크플로우 완료 대기 (틱 수신용)
        print("\n⏳ 실시간 틱 수신 대기중... (10초)")
        print("   → 틱 수신 시 on_workflow_pnl_update가 호출됩니다")
        await asyncio.sleep(10)
        
        # Job 종료
        await job.stop()
        
        print()
        print("=" * 70)
        print("📊 테스트 결과")
        print("=" * 70)
        print(f"   노드 이벤트 수: {len(listener.node_events)}")
        print(f"   워크플로우 PnL 이벤트 수: {len(listener.workflow_pnl_events)}")
        
        # DB 파일 확인
        check_db(db_path)
        
        if listener.workflow_pnl_events:
            print("\n✅ on_workflow_pnl_update 리스너가 정상 호출되었습니다!")
            last_event = listener.workflow_pnl_events[-1]
            print(f"   마지막 이벤트:")
            print(f"   - 워크플로우 수익률: {float(last_event.workflow_pnl_rate):+.2f}%")
            print(f"   - 전체 수익률: {float(last_event.total_pnl_rate):+.2f}%")
            print(f"   - 신뢰도: {last_event.trust_score}")
        else:
            print("\n⚠️ 워크플로우 PnL 이벤트가 발생하지 않았습니다.")
            print("   가능한 원인:")
            print("   - 보유 종목이 없어서 틱 구독이 시작되지 않음")
            print("   - AccountTracker가 아직 실행 전")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
