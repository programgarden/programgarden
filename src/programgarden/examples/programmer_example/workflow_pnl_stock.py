"""
[해외주식] 워크플로우 수익률 추적 테스트 - 실제 주문

테스트 시나리오:
1. BrokerNode 연결
2. NewOrderNode로 GOSS 1주 지정가 매수
3. 체결 대기 및 on_workflow_pnl_update 콜백 확인

⚠️ 실제 주문이 실행됩니다!

실행: cd src/programgarden && poetry run python examples/programmer_example/workflow_pnl_stock.py
"""

import asyncio
import copy
import logging
import os
import sqlite3
import sys
from pathlib import Path

# 프로젝트 루트 설정
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

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logging.getLogger('programgarden.executor').setLevel(logging.DEBUG)

# 테스트 종목 설정
TEST_SYMBOL = "GOSS"
TEST_EXCHANGE = "NASDAQ"
TEST_QUANTITY = 1
TEST_PRICE = 2.67  # 현재가 기준 (PnL 이벤트에서 확인)


def load_credential_from_env() -> dict:
    """.env에서 해외주식 credential 로드"""
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")

    if appkey and appsecret:
        print(f"✅ Credential 로드: .env (appkey: {appkey[:8]}...)")
        return {
            "appkey": appkey,
            "appsecret": appsecret,
            "paper_trading": False
        }

    return {}


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
        if event.node_id == "buy_order" and event.state == NodeState.COMPLETED:
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

        print(f"\n{emoji} === WorkflowPnLEvent ===")
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
                print(f"      - {pos.symbol}: {pos.quantity}주 @ ${pos.avg_price:.2f} → ${pos.current_price:.2f} ({pos.pnl_rate:+.2f}%)")

        if event.other_positions:
            print(f"   📋 그 외 포지션:")
            for pos in event.other_positions:
                print(f"      - {pos.symbol}: {pos.quantity}주 @ ${pos.avg_price:.2f} → ${pos.current_price:.2f} ({pos.pnl_rate:+.2f}%)")


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
        cursor.execute("SELECT * FROM workflow_orders ORDER BY id DESC LIMIT 5")
        orders = cursor.fetchall()
        print(f"\n   workflow_orders 테이블 (최근 5건): {len(orders)}건")
        for order in orders:
            print(f"      {order}")
    except Exception as e:
        print(f"   workflow_orders 테이블 조회 실패: {e}")

    # workflow_position_lots 테이블 확인
    try:
        cursor.execute("SELECT * FROM workflow_position_lots ORDER BY id DESC LIMIT 5")
        lots = cursor.fetchall()
        print(f"\n   workflow_position_lots 테이블 (최근 5건): {len(lots)}건")
        for lot in lots:
            print(f"      {lot}")
    except Exception as e:
        print(f"   workflow_position_lots 테이블 조회 실패: {e}")

    conn.close()


# 실제 주문 테스트용 워크플로우
TEST_WORKFLOW = {
    "id": "workflow-pnl-stock-test",
    "name": "해외주식 워크플로우 PnL 테스트 (실제 주문)",
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
        },
        {
            "id": "buy_order",
            "type": "NewOrderNode",
            "plugin": "LimitOrder",
            "connection": "{{ nodes.broker.connection }}",
            "product": "overseas_stock",
            "side": "buy",
            "order_type": "limit",
            "symbols": [{"exchange": TEST_EXCHANGE, "symbol": TEST_SYMBOL}],
            "quantities": {TEST_SYMBOL: TEST_QUANTITY},
            "prices": {TEST_SYMBOL: TEST_PRICE}
        }
    ],
    "edges": [
        {"from": "start", "to": "broker"},
        {"from": "broker", "to": "buy_order"}
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
    """테스트 실행 - 실제 주문

    핵심 테스트 흐름:
    1. BrokerNode 연결
    2. NewOrderNode로 GOSS 1주 지정가 매수
    3. 체결 대기 및 on_workflow_pnl_update 콜백 호출 확인
    """
    # .env에서 해외주식 credential 로드
    cred_data = load_credential_from_env()

    if not cred_data.get("appkey") or not cred_data.get("appsecret"):
        print("❌ .env에서 APPKEY, APPSECRET을 찾을 수 없습니다")
        return

    # credentials에 실제 값 주입
    workflow = copy.deepcopy(TEST_WORKFLOW)
    workflow["credentials"] = [
        {
            "id": "broker-cred",
            "type": "broker_ls",
            "name": "LS증권 (해외주식)",
            "data": {
                "appkey": cred_data["appkey"],
                "appsecret": cred_data["appsecret"],
                "paper_trading": False
            }
        }
    ]

    # DB 파일 경로
    db_path = Path("programgarden_data") / "workflow-pnl-stock-test_workflow.db"

    print("=" * 70)
    print("🚀 [해외주식] 워크플로우 수익률 추적 테스트 (실제 주문)")
    print("=" * 70)
    print()
    print("⚠️  주의: 실제 주문이 실행됩니다!")
    print()
    print(f"📌 주문 정보:")
    print(f"   - 종목: {TEST_SYMBOL} ({TEST_EXCHANGE})")
    print(f"   - 수량: {TEST_QUANTITY}주")
    print(f"   - 가격: ${TEST_PRICE} (지정가)")
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

        # 주문 체결 대기
        print("\n⏳ 주문 실행 및 체결 대기중... (30초)")
        for i in range(30, 0, -5):
            print(f"   {i}초 남음...")
            await asyncio.sleep(5)

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

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
