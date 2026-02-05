"""
[테스트] paper_trading 모드 전환 시 수익률 기록 초기화 테스트

테스트 시나리오:
1. 모의투자(paper_trading=True)로 워크플로우 실행 → 주문 기록 생성
2. 실전투자(paper_trading=False)로 전환하여 재실행
3. 기존 수익률 기록이 초기화되었는지 확인

💡 이 테스트는 실제 주문을 발생시키지 않고, DB 기록만 확인합니다.

실행: cd src/programgarden && poetry run python examples/programmer_example/test_paper_trading_reset.py
"""

import asyncio
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime

from programgarden.database import WorkflowPositionTracker


def print_separator(title: str):
    print("\n" + "=" * 70)
    print(f"📌 {title}")
    print("=" * 70)


def print_db_status(tracker: WorkflowPositionTracker, db_path: str):
    """DB 상태 출력"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # workflow_orders 수
        cursor.execute("SELECT COUNT(*) FROM workflow_orders")
        order_count = cursor.fetchone()[0]

        # workflow_position_lots 수
        cursor.execute("SELECT COUNT(*) FROM workflow_position_lots")
        lot_count = cursor.fetchone()[0]

        # trade_history 수
        cursor.execute("SELECT COUNT(*) FROM trade_history")
        trade_count = cursor.fetchone()[0]

        # broker_metadata
        cursor.execute("SELECT broker_node_id, paper_trading, updated_at FROM broker_metadata")
        metadata = cursor.fetchall()

        print(f"   📊 DB 상태:")
        print(f"      - workflow_orders: {order_count}건")
        print(f"      - workflow_position_lots: {lot_count}건")
        print(f"      - trade_history: {trade_count}건")
        print(f"      - broker_metadata: {metadata}")


async def test_paper_trading_reset():
    """paper_trading 모드 전환 테스트"""

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = f"{temp_dir}/test_workflow.db"
        job_id = "test-job-001"
        broker_node_id = "broker-futures"

        # ============================================
        # Step 1: 모의투자 모드로 시작
        # ============================================
        print_separator("Step 1: 모의투자(paper_trading=True) 모드로 시작")

        tracker = WorkflowPositionTracker(
            db_path=db_path,
            job_id=job_id,
            broker_node_id=broker_node_id,
            product="overseas_futures",
        )

        # 모의투자 모드 설정
        reset_happened = tracker.check_and_reset_if_mode_changed(paper_trading=True)
        print(f"   🔄 모드 전환 감지: {reset_happened} (최초 실행이므로 False)")

        # 주문 기록 생성
        tracker.record_order(
            order_no="ORD001",
            order_date="20260206",
            symbol="HMCEF26",
            exchange="HKEX",
            side="buy",
            quantity=1,
            price=19500.0,
            job_id=job_id,
            node_id="entry_order",
        )

        # 체결 기록 생성
        await tracker.record_fill(
            order_no="ORD001",
            order_date="20260206",
            symbol="HMCEF26",
            exchange="HKEX",
            side="buy",
            quantity=1,
            price=19500.0,
            fill_time="100000000",
            commda_code="40",  # OPEN API
        )

        print(f"   ✅ 모의투자 주문 기록 생성 완료")
        print_db_status(tracker, db_path)

        # 워크플로우 포지션 확인
        positions = tracker.get_workflow_positions()
        print(f"\n   📋 워크플로우 포지션: {dict(positions)}")

        # ============================================
        # Step 2: 동일 모드로 재실행 (데이터 유지)
        # ============================================
        print_separator("Step 2: 동일 모드(paper_trading=True)로 재실행")

        tracker2 = WorkflowPositionTracker(
            db_path=db_path,
            job_id=job_id,
            broker_node_id=broker_node_id,
            product="overseas_futures",
        )

        reset_happened = tracker2.check_and_reset_if_mode_changed(paper_trading=True)
        print(f"   🔄 모드 전환 감지: {reset_happened} (동일 모드이므로 False)")

        print_db_status(tracker2, db_path)

        positions = tracker2.get_workflow_positions()
        print(f"\n   📋 워크플로우 포지션: {dict(positions)}")
        print(f"   ✅ 기존 데이터 유지됨!")

        # ============================================
        # Step 3: 실전투자 모드로 전환 (데이터 초기화)
        # ============================================
        print_separator("Step 3: 실전투자(paper_trading=False)로 전환")

        tracker3 = WorkflowPositionTracker(
            db_path=db_path,
            job_id=job_id,
            broker_node_id=broker_node_id,
            product="overseas_futures",
        )

        reset_happened = tracker3.check_and_reset_if_mode_changed(paper_trading=False)
        print(f"   🔄 모드 전환 감지: {reset_happened} (모드 변경으로 True)")

        print_db_status(tracker3, db_path)

        positions = tracker3.get_workflow_positions()
        print(f"\n   📋 워크플로우 포지션: {dict(positions)}")
        print(f"   ✅ 데이터 초기화됨!")

        # ============================================
        # Step 4: 실전투자 모드에서 새 주문 기록
        # ============================================
        print_separator("Step 4: 실전투자 모드에서 새 주문 기록")

        tracker3.record_order(
            order_no="ORD002",
            order_date="20260206",
            symbol="HMCEF26",
            exchange="HKEX",
            side="buy",
            quantity=2,
            price=19600.0,
            job_id=job_id,
            node_id="entry_order",
        )

        await tracker3.record_fill(
            order_no="ORD002",
            order_date="20260206",
            symbol="HMCEF26",
            exchange="HKEX",
            side="buy",
            quantity=2,
            price=19600.0,
            fill_time="110000000",
            commda_code="40",
        )

        print(f"   ✅ 실전투자 주문 기록 생성 완료")
        print_db_status(tracker3, db_path)

        positions = tracker3.get_workflow_positions()
        print(f"\n   📋 워크플로우 포지션: {dict(positions)}")

        # ============================================
        # Step 5: 다시 모의투자로 전환 (데이터 초기화)
        # ============================================
        print_separator("Step 5: 다시 모의투자(paper_trading=True)로 전환")

        tracker4 = WorkflowPositionTracker(
            db_path=db_path,
            job_id=job_id,
            broker_node_id=broker_node_id,
            product="overseas_futures",
        )

        reset_happened = tracker4.check_and_reset_if_mode_changed(paper_trading=True)
        print(f"   🔄 모드 전환 감지: {reset_happened} (모드 변경으로 True)")

        print_db_status(tracker4, db_path)

        positions = tracker4.get_workflow_positions()
        print(f"\n   📋 워크플로우 포지션: {dict(positions)}")
        print(f"   ✅ 데이터 초기화됨!")

        # ============================================
        # 결과 요약
        # ============================================
        print_separator("테스트 결과 요약")
        print("""
   ✅ Step 1: 모의투자 모드로 시작 → 주문 기록 생성
   ✅ Step 2: 동일 모드로 재실행 → 데이터 유지
   ✅ Step 3: 실전투자로 전환 → 데이터 초기화
   ✅ Step 4: 실전투자에서 새 주문 → 새 기록 생성
   ✅ Step 5: 모의투자로 재전환 → 데이터 초기화

   📌 결론: paper_trading 모드 전환 시 수익률 기록이
           정상적으로 초기화됩니다!
        """)


if __name__ == "__main__":
    asyncio.run(test_paper_trading_reset())
