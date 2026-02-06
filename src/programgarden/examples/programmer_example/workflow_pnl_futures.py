"""
[해외선물] 워크플로우 실시간 수익률 추적 테스트 (모의투자)

테스트 시나리오:
1. HMCEG26 (홍콩 미니항생 2026년 2월물) 1계약 롱 진입 (지정가)
2. 체결 대기 (30초)
3. HMCEG26 1계약 롱 청산 (지정가)
4. 워크플로우 수익률 추적 확인

💡 이 예제는 모의투자입니다. 실제 자금이 소모되지 않습니다.
💡 모의투자에서는 시장가 주문이 불가능하여 지정가(매도1호가)로 체결을 유도합니다.

실행: cd src/programgarden && poetry run python examples/programmer_example/workflow_pnl_futures.py
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logging.getLogger('programgarden.executor').setLevel(logging.DEBUG)

# 프로젝트 루트의 .env 파일 로드
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src" / "programgarden"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from programgarden import ProgramGarden
from programgarden_core.bases import (
    BaseExecutionListener,
    WorkflowPnLEvent,
    NodeStateEvent,
    NodeState,
)


class WorkflowPnLTestListener(BaseExecutionListener):
    """워크플로우 수익률 테스트 리스너"""
    
    def __init__(self):
        self.workflow_pnl_events = []
        self.node_events = []
    
    async def on_node_state_change(self, event: NodeStateEvent) -> None:
        """노드 상태 변경 추적"""
        self.node_events.append(event)
        status = "✅" if event.state == NodeState.COMPLETED else "🔄" if event.state == NodeState.RUNNING else "⏳"
        print(f"{status} [{event.node_id}] {event.state.value}")
        
        # 주문 노드 결과 상세 출력
        if event.node_id in ("entry_order", "exit_order") and event.state == NodeState.COMPLETED:
            if event.outputs:
                result = event.outputs.get("order_result", {})
                print(f"   📋 주문 결과: {result}")
    
    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
        """워크플로우 수익률 업데이트"""
        self.workflow_pnl_events.append(event)
        
        wf_rate = float(event.workflow_pnl_rate)
        other_rate = float(event.other_pnl_rate)
        total_rate = float(event.total_pnl_rate)
        trust = event.trust_score
        
        emoji = "📈" if total_rate >= 0 else "📉"
        trust_badge = "🟢" if trust >= 80 else "🟡" if trust >= 50 else "🔴"
        
        print(f"\n{emoji} === WorkflowPnLEvent (해외선물) ===")
        print(f"   워크플로우 수익률: {wf_rate:+.2f}%")
        print(f"   그 외 수익률: {other_rate:+.2f}%")
        print(f"   전체 수익률: {total_rate:+.2f}%")
        print(f"   신뢰도: {trust_badge} {trust}")
        print(f"   워크플로우 포지션: {len(event.workflow_positions)}개")
        print(f"   그 외 포지션: {len(event.other_positions)}개")
        
        # 포지션 상세
        if event.workflow_positions:
            print(f"   📋 워크플로우 포지션:")
            for pos in event.workflow_positions:
                print(f"      - {pos.symbol}: {pos.quantity}계약 @ {pos.avg_price:.2f} → {pos.current_price:.2f} ({pos.pnl_rate:+.2f}%)")
        
        if event.other_positions:
            print(f"   📋 그 외 포지션:")
            for pos in event.other_positions:
                print(f"      - {pos.symbol}: {pos.quantity}계약 @ {pos.avg_price:.2f} → {pos.current_price:.2f} ({pos.pnl_rate:+.2f}%)")


# 테스트용 워크플로우: HMCEG26 1계약 롱 진입 → 청산
# 모의투자에서는 시장가 불가, 지정가로 매도1호가에 체결 유도
TEST_WORKFLOW = {
    "id": "workflow-pnl-futures-test",
    "name": "해외선물 워크플로우 PnL 테스트",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode"
        },
        {
            "id": "broker",
            "type": "OverseasFuturesBrokerNode",
            "credential_id": "broker-cred",
            "paper_trading": True
        },
        {
            "id": "entry_order",
            "type": "OverseasFuturesNewOrderNode",
            "side": "buy",  # 롱 진입
            "order_type": "limit",
            "order": {"exchange": "HKEX", "symbol": "HMCEG26", "quantity": 1, "price": 9060},
        },
        {
            "id": "exit_order",
            "type": "OverseasFuturesNewOrderNode",
            "side": "sell",  # 롱 청산
            "order_type": "limit",
            "order": {"exchange": "HKEX", "symbol": "HMCEG26", "quantity": 1, "price": 9000},
        }
    ],
    "edges": [
        {"from": "start", "to": "broker"},
        {"from": "broker", "to": "entry_order"},
        {"from": "entry_order", "to": "exit_order"}
    ],
    "credentials": [
        {
            "credential_id": "broker-cred",
            "type": "broker_ls_futures",
            "name": "LS증권 (해외선물)",
            "data": [
                {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                {"key": "paper_trading", "value": True, "type": "boolean", "label": "모의투자"}
            ]
        }
    ]
}


async def main():
    """테스트 실행"""
    # .env 파일에서 해외선물 모의투자용 credentials 로드
    appkey = os.getenv("APPKEY_FUTURE_FAKE")
    appsecret = os.getenv("APPSECRET_FUTURE_FAKE")
    
    if not appkey or not appsecret:
        print("❌ .env 파일에 APPKEY_FUTURE_FAKE, APPSECRET_FUTURE_FAKE를 설정해주세요")
        print("   예: APPKEY_FUTURE_FAKE=your_futures_fake_appkey")
        print("       APPSECRET_FUTURE_FAKE=your_futures_fake_appsecret")
        print()
        print("   💡 해외선물 모의투자는 별도의 API 키가 필요합니다.")
        return
    
    # credentials에 실제 값 주입
    workflow = TEST_WORKFLOW.copy()
    workflow["nodes"] = TEST_WORKFLOW["nodes"].copy()
    workflow["edges"] = TEST_WORKFLOW["edges"].copy()
    workflow["credentials"] = [
        {
            "credential_id": "broker-cred",
            "type": "broker_ls_futures",
            "name": "LS증권 (해외선물)",
            "data": [
                {"key": "appkey", "value": appkey, "type": "password", "label": "App Key"},
                {"key": "appsecret", "value": appsecret, "type": "password", "label": "App Secret"},
                {"key": "paper_trading", "value": True, "type": "boolean", "label": "모의투자"}
            ]
        }
    ]
    
    # DB 파일 확인
    db_path = Path("programgarden_data") / "workflow-pnl-futures-test_workflow.db"
    db_exists = db_path.exists()
    
    print("=" * 70)
    print("🚀 [해외선물] 워크플로우 수익률 추적 테스트 (모의투자)")
    print("=" * 70)
    print()
    print("💡 이 테스트는 모의투자입니다. 실제 자금이 소모되지 않습니다.")
    print()
    print("📌 테스트 시나리오:")
    print("   1. HMCEG26 (홍콩 미니항생 2026년 2월물) 1계약 롱 진입 (지정가)")
    print("   2. 체결 대기 (30초)")
    print("   3. HMCEG26 1계약 롱 청산 (지정가)")
    print()
    print(f"📌 DB 파일: {db_path}")
    print(f"   - 기존 DB {'있음 (재사용)' if db_exists else '없음 (새로 생성)'}")
    print()
    
    # 자동 진행
    print("자동으로 진행합니다...")
    
    # 리스너 생성
    listener = WorkflowPnLTestListener()
    
    # ProgramGarden 실행
    pg = ProgramGarden()
    
    try:
        print("\n" + "=" * 70)
        print("📡 워크플로우 실행 시작")
        print("=" * 70)
        
        job = await pg.run_async(
            workflow,
            listeners=[listener],
        )
        
        # 진입 주문 실행 대기
        print("\n⏳ 롱 진입 주문 실행 중...")
        await asyncio.sleep(5)
        
        # 체결 대기 (30초)
        print("\n⏳ 체결 대기 중... (30초)")
        for i in range(30, 0, -5):
            print(f"   {i}초 남음...")
            await asyncio.sleep(5)
        
        # 워크플로우 완료 대기
        print("\n⏳ 롱 청산 주문 실행 중...")
        await asyncio.sleep(10)
        
        # 추가 틱 수신 대기
        print("\n📡 실시간 수익률 업데이트 대기 중... (10초)")
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
        db_exists_after = db_path.exists()
        print(f"\n📌 DB 파일 상태:")
        print(f"   - 경로: {db_path}")
        print(f"   - 존재: {'✅ 있음' if db_exists_after else '❌ 없음'}")
        
        if listener.workflow_pnl_events:
            print("\n✅ on_workflow_pnl_update 리스너가 정상 호출되었습니다!")
            last_event = listener.workflow_pnl_events[-1]
            print(f"   마지막 이벤트:")
            print(f"   - 워크플로우 수익률: {float(last_event.workflow_pnl_rate):+.2f}%")
            print(f"   - 전체 수익률: {float(last_event.total_pnl_rate):+.2f}%")
            print(f"   - 신뢰도: {last_event.trust_score}")
        else:
            print("\n⚠️ 워크플로우 PnL 이벤트가 발생하지 않았습니다.")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
