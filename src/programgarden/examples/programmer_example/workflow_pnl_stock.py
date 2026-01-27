"""
[해외주식] 워크플로우 수익률 추적 테스트 - 실제 주문

테스트 시나리오:
1. BrokerNode 연결
2. NewOrderNode로 지정가 매수 (또는 기존 보유 종목 매도)
3. 체결 대기 및 on_workflow_pnl_update 콜백 확인
4. 실시간 틱 데이터에 따른 수익률 변동 확인

⚠️ 실제 주문이 실행됩니다!

실행:
  보유 확인: cd src/programgarden && poetry run python examples/programmer_example/workflow_pnl_stock.py watch
  매수: cd src/programgarden && poetry run python examples/programmer_example/workflow_pnl_stock.py buy SYMBOL QUANTITY PRICE
  매도: cd src/programgarden && poetry run python examples/programmer_example/workflow_pnl_stock.py sell SYMBOL QUANTITY [PRICE]
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

# 테스트 종목 설정 (기본값)
TEST_SYMBOL = "GOSS"
TEST_EXCHANGE = "NASDAQ"
TEST_QUANTITY = 1
TEST_PRICE = 2.67  # 현재가 기준 (PnL 이벤트에서 확인)
TEST_SIDE = "buy"  # 기본: 매수
WATCH_MODE = False  # 주문 없이 보유 현황만 확인


def parse_args():
    """커맨드라인 인자 파싱

    사용법:
        보유 확인: python workflow_pnl_stock.py watch
        매수: python workflow_pnl_stock.py buy SYMBOL QUANTITY PRICE
        매도: python workflow_pnl_stock.py sell SYMBOL QUANTITY [PRICE]
    """
    global TEST_SYMBOL, TEST_QUANTITY, TEST_PRICE, TEST_SIDE, TEST_EXCHANGE, WATCH_MODE

    if len(sys.argv) >= 2:
        if sys.argv[1].lower() == "watch":
            WATCH_MODE = True
            print("👀 Watch 모드: 주문 없이 보유 현황만 확인합니다.")
        elif sys.argv[1].lower() == "sell":
            TEST_SIDE = "sell"
            if len(sys.argv) >= 3:
                TEST_SYMBOL = sys.argv[2].upper()
            if len(sys.argv) >= 4:
                TEST_QUANTITY = int(sys.argv[3])
            if len(sys.argv) >= 5:
                TEST_PRICE = float(sys.argv[4])
            else:
                TEST_PRICE = 0  # 시장가
            print(f"📤 매도 모드: {TEST_SYMBOL} {TEST_QUANTITY}주 @ ${TEST_PRICE or '시장가'}")
        elif sys.argv[1].lower() == "buy":
            TEST_SIDE = "buy"
            if len(sys.argv) >= 3:
                TEST_SYMBOL = sys.argv[2].upper()
            if len(sys.argv) >= 4:
                TEST_QUANTITY = int(sys.argv[3])
            if len(sys.argv) >= 5:
                TEST_PRICE = float(sys.argv[4])
            print(f"📥 매수 모드: {TEST_SYMBOL} {TEST_QUANTITY}주 @ ${TEST_PRICE}")


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
        if event.node_id == "order" and event.state == NodeState.COMPLETED:
            if event.outputs:
                result = event.outputs.get("order_result", {})
                print(f"   📋 주문 결과: {result}")

    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
        """워크플로우 수익률 업데이트 - 전체 데이터 출력"""
        self.workflow_pnl_events.append(event)

        wf_rate = float(event.workflow_pnl_rate)
        other_rate = float(event.other_pnl_rate)
        total_rate = float(event.total_pnl_rate)
        trust = event.trust_score

        emoji = "📈" if total_rate >= 0 else "📉"
        trust_badge = "🟢" if trust >= 80 else "🟡" if trust >= 50 else "🔴"

        print(f"\n{emoji} === WorkflowPnLEvent #{len(self.workflow_pnl_events)} ===")
        print(f"   [기본 정보]")
        print(f"   job_id: {event.job_id}")
        print(f"   broker_node_id: {event.broker_node_id}")
        print(f"   product: {event.product}")
        print(f"   timestamp: {event.timestamp}")

        print(f"\n   [워크플로우 P&L]")
        print(f"   workflow_pnl_rate: {wf_rate:+.4f}%")
        print(f"   workflow_eval_amount: ${float(event.workflow_eval_amount):,.2f}")
        print(f"   workflow_buy_amount: ${float(event.workflow_buy_amount):,.2f}")
        print(f"   workflow_pnl_amount: ${float(event.workflow_pnl_amount):,.2f}")

        print(f"\n   [그 외 P&L]")
        print(f"   other_pnl_rate: {other_rate:+.4f}%")
        print(f"   other_eval_amount: ${float(event.other_eval_amount):,.2f}")
        print(f"   other_buy_amount: ${float(event.other_buy_amount):,.2f}")
        print(f"   other_pnl_amount: ${float(event.other_pnl_amount):,.2f}")

        print(f"\n   [전체 P&L]")
        print(f"   total_pnl_rate: {total_rate:+.4f}%")
        print(f"   total_eval_amount: ${float(event.total_eval_amount):,.2f}")
        print(f"   total_buy_amount: ${float(event.total_buy_amount):,.2f}")
        print(f"   total_pnl_amount: ${float(event.total_pnl_amount):,.2f}")

        print(f"\n   [신뢰도]")
        print(f"   trust_score: {trust_badge} {trust}")
        print(f"   anomaly_count: {event.anomaly_count}")

        print(f"\n   [포지션 카운트]")
        print(f"   워크플로우 포지션: {len(event.workflow_positions)}개")
        print(f"   그 외 포지션: {len(event.other_positions)}개")
        print(f"   total_position_count: {event.total_position_count}")

        # v2.0 필드들
        print(f"\n   [v2.0 상품별 P&L]")
        if event.workflow_stock_pnl_rate is not None:
            print(f"   workflow_stock_pnl_rate: {float(event.workflow_stock_pnl_rate):+.4f}%")
            print(f"   workflow_stock_pnl_amount: ${float(event.workflow_stock_pnl_amount or 0):,.2f}")
        if event.workflow_futures_pnl_rate is not None:
            print(f"   workflow_futures_pnl_rate: {float(event.workflow_futures_pnl_rate):+.4f}%")
            print(f"   workflow_futures_pnl_amount: ${float(event.workflow_futures_pnl_amount or 0):,.2f}")

        print(f"\n   [v2.0 계좌 전체 P&L]")
        if event.account_total_pnl_rate is not None:
            print(f"   account_total_pnl_rate: {float(event.account_total_pnl_rate):+.4f}%")
            print(f"   account_total_pnl_amount: ${float(event.account_total_pnl_amount or 0):,.2f}")
            print(f"   account_total_eval_amount: ${float(event.account_total_eval_amount or 0):,.2f}")
            print(f"   account_total_buy_amount: ${float(event.account_total_buy_amount or 0):,.2f}")

        print(f"\n   [v2.0 계좌 상품별 P&L]")
        if event.account_stock_pnl_rate is not None:
            print(f"   account_stock_pnl_rate: {float(event.account_stock_pnl_rate):+.4f}%")
            print(f"   account_stock_pnl_amount: ${float(event.account_stock_pnl_amount or 0):,.2f}")
        if event.account_futures_pnl_rate is not None:
            print(f"   account_futures_pnl_rate: {float(event.account_futures_pnl_rate):+.4f}%")
            print(f"   account_futures_pnl_amount: ${float(event.account_futures_pnl_amount or 0):,.2f}")

        print(f"\n   [워크플로우 메타데이터]")
        if event.workflow_start_datetime:
            print(f"   workflow_start_datetime: {event.workflow_start_datetime}")
        if event.workflow_elapsed_days is not None:
            print(f"   workflow_elapsed_days: {event.workflow_elapsed_days}일")

        # 대회 필드
        if event.competition_start_date:
            print(f"\n   [대회 관련 P&L]")
            print(f"   competition_start_date: {event.competition_start_date}")
            if event.competition_workflow_pnl_rate is not None:
                print(f"   competition_workflow_pnl_rate: {float(event.competition_workflow_pnl_rate):+.4f}%")

        # 포지션 상세
        if event.workflow_positions:
            print(f"\n   📋 워크플로우 포지션 상세:")
            for pos in event.workflow_positions:
                print(f"      - {pos.symbol}: {pos.quantity}주 @ ${pos.avg_price:.2f} → ${pos.current_price:.2f} ({pos.pnl_rate:+.2f}%)")

        if event.other_positions:
            print(f"\n   📋 그 외 포지션 상세:")
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


def create_workflow() -> dict:
    """주문 설정에 따라 워크플로우 생성"""
    nodes = [
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
    ]

    edges = [
        {"from": "start", "to": "broker"}
    ]

    # Watch 모드가 아니면 주문 노드 추가
    if not WATCH_MODE:
        order_type = "limit" if TEST_PRICE > 0 else "market"
        plugin = "LimitOrder" if TEST_PRICE > 0 else "MarketOrder"

        nodes.append({
            "id": "order",
            "type": "OverseasStockNewOrderNode",
            "plugin": plugin,
            "connection": "{{ nodes.broker.connection }}",
            "side": TEST_SIDE,
            "order_type": order_type,
            "orders": [
                {"exchange": TEST_EXCHANGE, "symbol": TEST_SYMBOL, "quantity": TEST_QUANTITY, "price": TEST_PRICE}
            ],
        })
        edges.append({"from": "broker", "to": "order"})

    workflow = {
        "id": "workflow-pnl-stock-test",
        "name": f"해외주식 워크플로우 PnL 테스트 ({'watch' if WATCH_MODE else TEST_SIDE})",
        "nodes": nodes,
        "edges": edges,
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
    return workflow


async def main():
    """테스트 실행 - 실제 주문

    핵심 테스트 흐름:
    1. BrokerNode 연결
    2. NewOrderNode로 매수/매도 주문
    3. 체결 대기 및 on_workflow_pnl_update 콜백 호출 확인
    4. 실시간 틱 데이터에 따른 수익률 변동 확인
    """
    # 커맨드라인 인자 파싱
    parse_args()

    # .env에서 해외주식 credential 로드
    cred_data = load_credential_from_env()

    if not cred_data.get("appkey") or not cred_data.get("appsecret"):
        print("❌ .env에서 APPKEY, APPSECRET을 찾을 수 없습니다")
        return

    # 워크플로우 생성
    workflow = create_workflow()

    # credentials에 실제 값 주입
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
    if WATCH_MODE:
        print("👀 [해외주식] 보유 현황 모니터링")
        print("=" * 70)
        print()
        print("📌 주문 없이 보유 현황과 PnL 이벤트만 확인합니다.")
    else:
        side_emoji = "📥" if TEST_SIDE == "buy" else "📤"
        order_type_str = f"${TEST_PRICE} (지정가)" if TEST_PRICE > 0 else "시장가"

        print(f"🚀 [해외주식] 워크플로우 수익률 추적 테스트 ({TEST_SIDE.upper()})")
        print("=" * 70)
        print()
        print("⚠️  주의: 실제 주문이 실행됩니다!")
        print()
        print(f"📌 주문 정보:")
        print(f"   - 종목: {TEST_SYMBOL} ({TEST_EXCHANGE})")
        print(f"   - 방향: {side_emoji} {TEST_SIDE.upper()}")
        print(f"   - 수량: {TEST_QUANTITY}주")
        print(f"   - 가격: {order_type_str}")
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

        if WATCH_MODE:
            # Watch 모드: PnL 이벤트 수신 대기
            print("\n📡 보유 현황 및 실시간 수익률 모니터링 중... (60초)")
            print("   틱 데이터가 변하면 수익률도 변합니다.")
            for i in range(60, 0, -10):
                pnl_count = len(listener.workflow_pnl_events)
                print(f"   {i}초 남음... (PnL 이벤트: {pnl_count}개)")
                await asyncio.sleep(10)
        else:
            # 주문 체결 대기
            print("\n⏳ 주문 실행 및 체결 대기중... (30초)")
            for i in range(30, 0, -5):
                pnl_count = len(listener.workflow_pnl_events)
                print(f"   {i}초 남음... (PnL 이벤트: {pnl_count}개)")
                await asyncio.sleep(5)

            # 실시간 틱 데이터에 따른 수익률 변화 모니터링 (60초)
            print("\n📡 실시간 수익률 모니터링 중... (60초)")
            print("   틱 데이터가 변하면 워크플로우 수익률도 변합니다.")
            start_pnl_count = len(listener.workflow_pnl_events)
            for i in range(60, 0, -10):
                current_count = len(listener.workflow_pnl_events)
                new_events = current_count - start_pnl_count
                print(f"   {i}초 남음... (신규 PnL 이벤트: {new_events}개)")
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
            print(f"   총 이벤트 수: {len(listener.workflow_pnl_events)}개")

            # 수익률 변화 추적
            if len(listener.workflow_pnl_events) >= 2:
                first_event = listener.workflow_pnl_events[0]
                last_event = listener.workflow_pnl_events[-1]
                wf_change = float(last_event.workflow_pnl_rate) - float(first_event.workflow_pnl_rate)
                total_change = float(last_event.total_pnl_rate) - float(first_event.total_pnl_rate)

                print(f"\n   📊 수익률 변화 (첫 이벤트 → 마지막 이벤트):")
                print(f"   - 워크플로우: {float(first_event.workflow_pnl_rate):+.4f}% → {float(last_event.workflow_pnl_rate):+.4f}% (변화: {wf_change:+.4f}%)")
                print(f"   - 전체: {float(first_event.total_pnl_rate):+.4f}% → {float(last_event.total_pnl_rate):+.4f}% (변화: {total_change:+.4f}%)")

            last_event = listener.workflow_pnl_events[-1]
            print(f"\n   🔚 마지막 이벤트 요약:")
            print(f"   - 워크플로우 수익률: {float(last_event.workflow_pnl_rate):+.4f}%")
            print(f"   - 그 외 수익률: {float(last_event.other_pnl_rate):+.4f}%")
            print(f"   - 전체 수익률: {float(last_event.total_pnl_rate):+.4f}%")
            print(f"   - 신뢰도: {last_event.trust_score}")
            print(f"   - 워크플로우 포지션: {len(last_event.workflow_positions)}개")
            print(f"   - 그 외 포지션: {len(last_event.other_positions)}개")
        else:
            print("\n⚠️ 워크플로우 PnL 이벤트가 발생하지 않았습니다.")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
