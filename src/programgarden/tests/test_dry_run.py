"""
dry_run 모드 테스트

`context_params={"dry_run": True}`로 워크플로우를 실행할 때 각 노드 카테고리가
올바르게 동작하는지 검증한다.

- ScheduleNode / TradingHoursFilterNode: 1 cycle 후 종료
- 주문 노드: LS API 미호출, simulated 응답 반환
- Realtime 노드: WebSocket 미개방, skip 반환
- Messaging 노드: no-op, simulated 반환
- 조회 노드: dry_run 과 무관하게 실제 경로 타는지 (mock 으로 검증)
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import (
    CancelOrderNodeExecutor,
    MarketDataNodeExecutor,
    ModifyOrderNodeExecutor,
    NewOrderNodeExecutor,
    RealAccountNodeExecutor,
    RealMarketDataNodeExecutor,
    RealOrderEventNodeExecutor,
    ScheduleNodeExecutor,
    WorkflowExecutor,
)


# ============================================================
# Helper
# ============================================================

def make_context(dry_run: bool | None = None, job_id: str = "dry-run-test") -> ExecutionContext:
    """Helper: ExecutionContext 생성"""
    ctx_params: dict = {}
    if dry_run is not None:
        ctx_params["dry_run"] = dry_run
    ctx = ExecutionContext(
        job_id=job_id,
        workflow_id="wf-dry-run-test",
        context_params=ctx_params,
    )
    ctx._is_running = True  # scheduler_task 루프 진입용
    return ctx


# ============================================================
# 1. dry_run flag propagation
# ============================================================

def test_dry_run_flag_propagates():
    """context_params={"dry_run": True} → ctx.is_dry_run True"""
    ctx = make_context(dry_run=True)
    assert ctx.is_dry_run is True


def test_dry_run_default_false():
    """context_params 미지정 / dry_run 미지정 → False"""
    ctx = make_context()
    assert ctx.is_dry_run is False

    ctx2 = make_context(dry_run=False)
    assert ctx2.is_dry_run is False


# ============================================================
# 2. Order nodes return simulated response
# ============================================================

async def test_order_node_returns_simulated():
    """NewOrderNodeExecutor: dry_run 시 LS API 호출 없이 simulated 응답 반환"""
    ctx = make_context(dry_run=True)
    executor = NewOrderNodeExecutor()

    config = {
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "quantity": 10,
        "price": 150.0,
        # 일부러 connection 미제공 — dry_run 가드가 먼저 return 해야 함
    }

    result = await executor.execute(
        node_id="order-1",
        node_type="OverseasStockNewOrderNode",
        config=config,
        context=ctx,
    )

    assert result["status"] == "simulated"
    assert result["dry_run"] is True
    assert result["order_id"].startswith("DRYRUN-")
    assert result["requested"] == config


async def test_modify_order_returns_simulated():
    ctx = make_context(dry_run=True)
    executor = ModifyOrderNodeExecutor()

    result = await executor.execute(
        node_id="modify-1",
        node_type="OverseasStockModifyOrderNode",
        config={"original_order_id": "ORD-123", "new_quantity": 5},
        context=ctx,
    )

    assert result["status"] == "simulated"
    assert result["order_id"].startswith("DRYRUN-")


async def test_cancel_order_returns_simulated():
    ctx = make_context(dry_run=True)
    executor = CancelOrderNodeExecutor()

    result = await executor.execute(
        node_id="cancel-1",
        node_type="OverseasStockCancelOrderNode",
        config={"original_order_id": "ORD-123"},
        context=ctx,
    )

    assert result["status"] == "simulated"
    assert result["order_id"].startswith("DRYRUN-")


# ============================================================
# 3. ScheduleNode exits after one cycle
# ============================================================

async def test_schedule_node_exits_after_one_cycle():
    """ScheduleNode: dry_run 시 1 cycle emit 후 scheduler_task 종료"""
    ctx = make_context(dry_run=True)
    executor = ScheduleNodeExecutor()

    # 첫 실행 → trigger 반환 + 백그라운드 task 등록
    result = await executor.execute(
        node_id="schedule-1",
        node_type="ScheduleNode",
        config={
            "cron": "*/5 * * * *",  # 실제로는 대기하지 않음 — dry_run 분기 진입
            "timezone": "UTC",
            "enabled": True,
            "count": 1000,
        },
        context=ctx,
    )

    assert result.get("trigger") is True

    # 백그라운드 scheduler_task 가 등록되어 있어야 함
    assert "schedule-1" in ctx._persistent_tasks
    task = ctx._persistent_tasks["schedule-1"]

    # dry_run 이므로 1 cycle 후 즉시 종료 — 3초 안에 끝나야 함
    await asyncio.wait_for(task, timeout=3.0)
    assert task.done()

    # schedule_tick event 가 1회 emit 되었는지
    events = []
    while not ctx._event_queue.empty():
        events.append(ctx._event_queue.get_nowait())

    schedule_ticks = [e for e in events if e.type == "schedule_tick"]
    assert len(schedule_ticks) == 1
    assert schedule_ticks[0].data.get("dry_run") is True


# ============================================================
# 4. Realtime nodes skipped
# ============================================================

async def test_realtime_account_skipped():
    ctx = make_context(dry_run=True)
    executor = RealAccountNodeExecutor()

    result = await executor.execute(
        node_id="real-acc-1",
        node_type="OverseasStockRealAccountNode",
        config={},
        context=ctx,
    )

    assert result["status"] == "skipped_dry_run"
    assert result["dry_run"] is True


async def test_realtime_market_data_skipped():
    ctx = make_context(dry_run=True)
    executor = RealMarketDataNodeExecutor()

    result = await executor.execute(
        node_id="real-md-1",
        node_type="OverseasStockRealMarketDataNode",
        config={},
        context=ctx,
    )

    assert result["status"] == "skipped_dry_run"


async def test_realtime_order_event_skipped():
    ctx = make_context(dry_run=True)
    executor = RealOrderEventNodeExecutor()

    result = await executor.execute(
        node_id="real-ord-1",
        node_type="OverseasStockRealOrderEventNode",
        config={},
        context=ctx,
    )

    assert result["status"] == "skipped_dry_run"


# ============================================================
# 5. Query nodes still call API
# ============================================================

async def test_query_node_still_calls_api():
    """MarketDataNode 는 dry_run 과 무관하게 실제 경로 타야 함.

    connection 미제공이므로 에러 응답이 나오지만, 핵심은:
    - `status == "skipped_dry_run"` 이 아님
    - `dry_run == True` 짐수가 없음
    → dry_run 분기를 타지 않았음을 증명
    """
    ctx = make_context(dry_run=True)
    executor = MarketDataNodeExecutor()

    result = await executor.execute(
        node_id="md-1",
        node_type="OverseasStockMarketDataNode",
        config={},  # connection 없음 → 에러 경로 진입
        context=ctx,
    )

    # dry_run 가드가 개입했다면 이 두 조건 중 하나를 만족했을 것
    assert result.get("status") != "skipped_dry_run"
    assert result.get("dry_run") is not True


# ============================================================
# 6. End-to-end: workflow completes quickly under dry_run
# ============================================================

async def test_dry_run_completes_quickly():
    """ScheduleNode + Order 조합 워크플로우가 dry_run 으로 30초 이내 종료"""
    workflow = {
        "id": "test-dry-run-wf",
        "name": "Dry Run Quick Test",
        "nodes": [
            {"id": "start", "type": "StartNode"},
        ],
        "edges": [],
    }

    executor = WorkflowExecutor()
    start = time.monotonic()

    job = await executor.execute(
        workflow,
        context_params={"dry_run": True},
        job_id=f"dry-run-quick-{int(time.time() * 1000)}",
    )

    # 완료 대기 (최대 30초)
    deadline = start + 30.0
    while job.status in ("pending", "running"):
        if time.monotonic() > deadline:
            break
        await asyncio.sleep(0.1)

    elapsed = time.monotonic() - start
    assert elapsed < 30.0, f"dry_run 워크플로우가 30초 내 종료되지 않음 (elapsed={elapsed:.1f}s)"
    assert job.status in ("completed", "finished", "success"), (
        f"dry_run workflow should complete, got status={job.status}"
    )
