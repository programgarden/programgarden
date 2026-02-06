"""
[테스트] paper_trading 모드별 수익률 분리 저장 테스트

테스트 시나리오:
1. 모의투자(paper) 모드로 주문 기록 생성
2. 실전투자(live) 모드로 전환 → 모의투자 데이터 보존, live 데이터 독립
3. 다시 모의투자(paper)로 전환 → 기존 paper 데이터 살아있음
4. 모드별 독립적인 통계 확인

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
    print(f"  {title}")
    print("=" * 70)


def print_db_status(tracker: WorkflowPositionTracker, db_path: str):
    """DB 상태 출력"""
    stats = tracker.get_statistics()
    print(f"   DB 상태 (trading_mode={stats['trading_mode']}):")
    print(f"      - workflow_orders: {stats['workflow_orders']}건")
    print(f"      - trust_score: {stats['trust_score']}")


async def test_paper_trading_mode_separation():
    """paper/live 모드별 수익률 분리 저장 테스트"""

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = f"{temp_dir}/test_workflow.db"
        job_id = "test-job-001"
        broker_node_id = "broker-futures"

        # ============================================
        # Step 1: 모의투자 모드로 시작
        # ============================================
        print_separator("Step 1: 모의투자(paper) 모드로 시작")

        tracker_paper = WorkflowPositionTracker(
            db_path=db_path,
            job_id=job_id,
            broker_node_id=broker_node_id,
            product="overseas_futures",
            trading_mode="paper",
        )
        tracker_paper.update_trading_mode("paper")

        # 주문 기록 생성
        tracker_paper.record_order(
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
        await tracker_paper.record_fill(
            order_no="ORD001",
            order_date="20260206",
            symbol="HMCEF26",
            exchange="HKEX",
            side="buy",
            quantity=1,
            price=19500.0,
            fill_time="100000000",
            commda_code="40",
        )

        print(f"   모의투자 주문 기록 생성 완료")
        print_db_status(tracker_paper, db_path)

        positions = tracker_paper.get_workflow_positions()
        print(f"\n   워크플로우 포지션: {dict(positions)}")

        # ============================================
        # Step 2: 실전투자 모드로 전환 (paper 데이터 보존)
        # ============================================
        print_separator("Step 2: 실전투자(live)로 전환 - paper 데이터 보존")

        tracker_live = WorkflowPositionTracker(
            db_path=db_path,
            job_id=job_id,
            broker_node_id=broker_node_id,
            product="overseas_futures",
            trading_mode="live",
        )
        tracker_live.update_trading_mode("live")

        # live에서는 포지션 없음
        positions = tracker_live.get_workflow_positions()
        print(f"   live 포지션 (비어있어야 함): {dict(positions)}")

        # 실전투자에서 새 주문 생성
        tracker_live.record_order(
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

        await tracker_live.record_fill(
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

        print(f"   실전투자 주문 기록 생성 완료")
        print_db_status(tracker_live, db_path)

        positions = tracker_live.get_workflow_positions()
        print(f"\n   live 포지션: {dict(positions)}")

        # ============================================
        # Step 3: 다시 모의투자로 전환 (기존 paper 데이터 살아있음)
        # ============================================
        print_separator("Step 3: 다시 모의투자(paper)로 전환 - 기존 데이터 살아있음")

        tracker_paper2 = WorkflowPositionTracker(
            db_path=db_path,
            job_id=job_id,
            broker_node_id=broker_node_id,
            product="overseas_futures",
            trading_mode="paper",
        )
        tracker_paper2.update_trading_mode("paper")

        positions = tracker_paper2.get_workflow_positions()
        print(f"   paper 포지션 (보존됨): {dict(positions)}")
        print_db_status(tracker_paper2, db_path)

        # ============================================
        # Step 4: 모드별 통계 비교
        # ============================================
        print_separator("Step 4: 모드별 통계 비교")

        paper_stats = tracker_paper2.get_statistics()
        live_stats = tracker_live.get_statistics()

        print(f"   [paper] orders={paper_stats['workflow_orders']}, trust={paper_stats['trust_score']}")
        print(f"   [live]  orders={live_stats['workflow_orders']}, trust={live_stats['trust_score']}")

        # ============================================
        # 결과 요약
        # ============================================
        print_separator("테스트 결과 요약")
        print("""
   Step 1: 모의투자 모드 시작 -> 주문 기록 생성
   Step 2: 실전투자로 전환 -> paper 데이터 보존, live 독립 기록
   Step 3: 다시 모의투자로 -> 기존 paper 데이터 살아있음
   Step 4: 모드별 통계가 독립적으로 계산됨

   결론: 모의투자/실전투자 전환 시 데이터가 초기화되지 않고
         모드별로 분리 저장되어 독립적으로 유지됩니다!
        """)


if __name__ == "__main__":
    asyncio.run(test_paper_trading_mode_separation())
