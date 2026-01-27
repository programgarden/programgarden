"""
주문 노드 통합 테스트: 신규 → 정정 → 취소

테스트 시나리오:
1. OverseasStockNewOrderNode로 GOSS 1주 지정가 매수 (현재가보다 낮게 → 미체결 유도)
2. OverseasStockModifyOrderNode로 가격 정정
3. OverseasStockCancelOrderNode로 취소

실행:
  cd src/programgarden && poetry run python examples/programmer_example/test_order_modify_cancel.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src" / "programgarden"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from programgarden import ProgramGarden
from programgarden_core.bases import BaseExecutionListener, NodeStateEvent, NodeState

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logging.getLogger('programgarden.executor').setLevel(logging.DEBUG)

# 테스트 설정
TEST_SYMBOL = "GOSS"
TEST_EXCHANGE = "NASDAQ"
TEST_QUANTITY = 1
# 현재가보다 낮게 설정하여 미체결 유도 (GOSS 현재가 약 $2.6~2.7)
TEST_PRICE = 2.00  # 미체결될 낮은 가격
MODIFIED_PRICE = 2.10  # 정정 가격


class TestListener(BaseExecutionListener):
    def __init__(self):
        self.order_results = {}

    async def on_node_state_change(self, event: NodeStateEvent) -> None:
        status = "✅" if event.state == NodeState.COMPLETED else "🔄" if event.state == NodeState.RUNNING else "⏳"
        print(f"{status} [{event.node_id}] {event.state.value}")

        if event.state == NodeState.COMPLETED and event.outputs:
            self.order_results[event.node_id] = event.outputs
            # 전체 출력 (디버깅용)
            print(f"   📋 전체 결과: {event.outputs}")


async def test_new_order():
    """1단계: 신규 주문"""
    print("\n" + "="*70)
    print("📥 1단계: 신규 주문 (OverseasStockNewOrderNode)")
    print("="*70)

    workflow = {
        "id": "test-new-order",
        "name": "신규 주문 테스트",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "broker",
                "type": "OverseasStockBrokerNode",
                "credential_id": "broker-cred"
            },
            {
                "id": "new_order",
                "type": "OverseasStockNewOrderNode",
                "side": "buy",
                "order_type": "limit",
                "orders": [
                    {"symbol": TEST_SYMBOL, "exchange": TEST_EXCHANGE, "quantity": TEST_QUANTITY, "price": TEST_PRICE}
                ],
            }
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "new_order"}
        ],
        "credentials": [
            {
                "id": "broker-cred",
                "type": "broker_ls_stock",
                "data": {
                    "appkey": os.getenv("APPKEY"),
                    "appsecret": os.getenv("APPSECRET"),
                    "paper_trading": False
                }
            }
        ]
    }

    listener = TestListener()
    pg = ProgramGarden()

    job = await pg.run_async(workflow, listeners=[listener])
    await asyncio.sleep(3)
    await job.stop()

    # 주문번호 추출
    order_id = None
    if "new_order" in listener.order_results:
        submitted = listener.order_results["new_order"].get("submitted_orders", [])
        if submitted and submitted[0].get("order_id"):
            order_id = submitted[0]["order_id"]

    return order_id


async def test_modify_order(order_id: str):
    """2단계: 정정 주문"""
    print("\n" + "="*70)
    print(f"📝 2단계: 정정 주문 (OverseasStockModifyOrderNode)")
    print(f"   원주문번호: {order_id}")
    print(f"   정정 가격: ${TEST_PRICE} → ${MODIFIED_PRICE}")
    print("="*70)

    workflow = {
        "id": "test-modify-order",
        "name": "정정 주문 테스트",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "broker",
                "type": "OverseasStockBrokerNode",
                "credential_id": "broker-cred"
            },
            {
                "id": "modify_order",
                "type": "OverseasStockModifyOrderNode",
                "original_order_id": order_id,
                "symbol": TEST_SYMBOL,
                "exchange": TEST_EXCHANGE,
                "new_price": MODIFIED_PRICE,
            }
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "modify_order"}
        ],
        "credentials": [
            {
                "id": "broker-cred",
                "type": "broker_ls_stock",
                "data": {
                    "appkey": os.getenv("APPKEY"),
                    "appsecret": os.getenv("APPSECRET"),
                    "paper_trading": False
                }
            }
        ]
    }

    listener = TestListener()
    pg = ProgramGarden()

    job = await pg.run_async(workflow, listeners=[listener])
    await asyncio.sleep(3)
    await job.stop()

    # 정정된 주문번호 추출 (정정하면 새 주문번호가 생성됨!)
    new_order_id = None
    if "modify_order" in listener.order_results:
        result = listener.order_results["modify_order"]
        # 새 주문번호 우선
        new_order_id = result.get("modified_order", {}).get("new_order_id")
        if not new_order_id:
            new_order_id = result.get("modify_result", {}).get("new_order_id")

    return new_order_id or order_id


async def test_cancel_order(order_id: str):
    """3단계: 취소 주문"""
    print("\n" + "="*70)
    print(f"❌ 3단계: 취소 주문 (OverseasStockCancelOrderNode)")
    print(f"   취소할 주문번호: {order_id}")
    print("="*70)

    workflow = {
        "id": "test-cancel-order",
        "name": "취소 주문 테스트",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "broker",
                "type": "OverseasStockBrokerNode",
                "credential_id": "broker-cred"
            },
            {
                "id": "cancel_order",
                "type": "OverseasStockCancelOrderNode",
                "original_order_id": order_id,
                "symbol": TEST_SYMBOL,
                "exchange": TEST_EXCHANGE,
            }
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "cancel_order"}
        ],
        "credentials": [
            {
                "id": "broker-cred",
                "type": "broker_ls_stock",
                "data": {
                    "appkey": os.getenv("APPKEY"),
                    "appsecret": os.getenv("APPSECRET"),
                    "paper_trading": False
                }
            }
        ]
    }

    listener = TestListener()
    pg = ProgramGarden()

    job = await pg.run_async(workflow, listeners=[listener])
    await asyncio.sleep(3)
    await job.stop()

    return listener.order_results.get("cancel_order", {})


async def main():
    print("="*70)
    print("🧪 주문 노드 통합 테스트: 신규 → 정정 → 취소")
    print("="*70)
    print(f"종목: {TEST_SYMBOL} ({TEST_EXCHANGE})")
    print(f"수량: {TEST_QUANTITY}주")
    print(f"신규 주문 가격: ${TEST_PRICE} (미체결 유도)")
    print(f"정정 가격: ${MODIFIED_PRICE}")

    # 1. 신규 주문
    order_id = await test_new_order()

    if not order_id:
        print("\n❌ 신규 주문 실패 - 테스트 중단")
        return

    print(f"\n✅ 신규 주문 성공: {order_id}")

    # 잠시 대기
    print("\n⏳ 3초 대기...")
    await asyncio.sleep(3)

    # 2. 정정 주문
    modified_order_id = await test_modify_order(order_id)
    print(f"\n✅ 정정 주문 완료: {modified_order_id}")

    # 정정 완료 대기 (증권사 처리 시간 필요)
    print("\n⏳ 10초 대기 (정정 완료 대기)...")
    await asyncio.sleep(10)

    # 3. 취소 주문
    cancel_result = await test_cancel_order(modified_order_id)
    print(f"\n✅ 취소 주문 완료")

    print("\n" + "="*70)
    print("🎉 테스트 완료")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
