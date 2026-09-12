"""체결번호(execution_id) 축이 깨져도 체결은 원장에 남는다 — context.record_workflow_fill.

배경(회귀 방지):
    원장의 중복방지 키는 (product, provider, trading_mode, order_date, order_no,
    execution_id) 이고, 그 키를 만드는 WorkflowPositionTracker._execution_key 는
    **체결번호 자체**를 먼저 _normalize_identifier 에 통과시킨다. 정수가 아닌 수치
    문자열("0.0" / "-0" / "12.5")이면 거기서
    ValueError("Numeric execution/order identity must be a positive integer") 가
    나고, 종전에는 그 예외를 context.record_workflow_fill 의 광역 except 가 삼켜
    "error" 만 반환했다 — trade_history 에도 workflow_position_lots 에도 **아무것도
    남지 않았다**(체결 통째 유실).

    executor._usable_execution_identity 는 (주문번호, 주문일자) 축만 미리 거르므로
    이 축은 열려 있었다. 그래서 축마다 가드를 덧대는 대신, record_workflow_fill 에서
    **identity 관련 ValueError 만** 잡아 체결번호 없이 한 번 더 기록한다
    (중복방지만 포기하고 체결은 보존).

    단 ExecutionIdentityConflictError(ValueError 서브클래스)는 "같은 체결번호가 이미
    기록돼 있는데 사실이 다르다" 는 신호라, 재시도하면 같은 브로커 체결이 두 번
    기록된다 — 재시도 대상에서 제외한다.

라이브 키 없이 실제 SQLite 원장으로 검증한다.
"""

import logging
import sqlite3
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.database.workflow_position_tracker import WorkflowPositionTracker


TODAY = datetime.now().strftime("%Y%m%d")


def _make_context(tmp_path):
    ctx = ExecutionContext(job_id="fill-identity", workflow_id="offline")
    tracker = WorkflowPositionTracker(
        str(tmp_path / "stock.sqlite"), ctx.job_id, "broker", product="overseas_stock"
    )
    ctx._workflow_position_tracker = tracker
    ctx._workflow_risk_tracker = MagicMock()
    # 우리 주문으로 기록해 둬야 체결이 버퍼링('pending') 없이 즉시 분류된다.
    tracker.record_order("123", TODAY, "AAPL", "NASDAQ", "buy", 5, 100.0,
                         ctx.job_id, "order-node")
    return ctx, tracker


def _history(tracker):
    with sqlite3.connect(tracker.db_path) as conn:
        return conn.execute(
            "SELECT order_no, order_date, symbol, side, quantity, price, "
            "classification, execution_id FROM trade_history ORDER BY id"
        ).fetchall()


def _lots(tracker):
    with sqlite3.connect(tracker.db_path) as conn:
        return conn.execute(
            "SELECT symbol, original_qty, classification FROM workflow_position_lots ORDER BY id"
        ).fetchall()


async def _fill(ctx, *, execution_id, quantity=5, price=100.0):
    return await ctx.record_workflow_fill(
        order_no="123", order_date=TODAY, symbol="AAPL", exchange="NASDAQ",
        side="buy", quantity=quantity, price=price, fill_time="120000000",
        commda_code="40", execution_id=execution_id,
    )


# ---------------------------------------------------------------------------
# 깨진 체결번호 축 — 체결은 보존되고 경고가 남는다
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("execution_id", ["0.0", "-0", "12.5", "1e3", 4.0])
@pytest.mark.asyncio
async def test_unusable_execution_id_still_records_the_fill(tmp_path, caplog, execution_id):
    """비정수 수치 체결번호여도 trade_history 행이 남고 warning 이 찍힌다."""
    ctx, tracker = _make_context(tmp_path)

    with caplog.at_level(logging.WARNING, logger="programgarden.context"):
        result = await _fill(ctx, execution_id=execution_id)

    assert result == "workflow"
    rows = _history(tracker)
    assert len(rows) == 1
    assert rows[0][:7] == ("123", TODAY, "AAPL", "buy", 5, 100.0, "workflow")
    # 중복방지만 포기한다 — 체결번호는 원장에 남기지 않는다(거짓 키를 만들지 않는다).
    assert rows[0][7] is None
    assert _lots(tracker) == [("AAPL", 5, "workflow")]

    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("Execution identity unusable" in m and repr(execution_id) in m
               for m in warnings), warnings


# ---------------------------------------------------------------------------
# 정상 체결번호 — 종전대로 identity 를 쓴다
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_usable_execution_id_keeps_identity_and_replay_protection(tmp_path, caplog):
    ctx, tracker = _make_context(tmp_path)

    with caplog.at_level(logging.WARNING, logger="programgarden.context"):
        first = await _fill(ctx, execution_id="0077")
        replay = await _fill(ctx, execution_id="77")   # 0-패딩 차이 = 같은 체결

    assert (first, replay) == ("workflow", "workflow")
    rows = _history(tracker)
    assert len(rows) == 1                      # 재전달은 이중 기록되지 않는다
    assert rows[0][7] == "77"                  # 정규화된 체결번호가 원장에 남는다
    assert _lots(tracker) == [("AAPL", 5, "workflow")]
    assert not [r for r in caplog.records
                if "Execution identity unusable" in r.getMessage()]


# ---------------------------------------------------------------------------
# 사실 충돌 — 재시도하지 않는다(이중 기록 금지)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_identity_conflict_is_not_retried_without_identity(tmp_path):
    """같은 체결번호 + 다른 사실이면 'error' 로 두고 두 번째 행을 만들지 않는다."""
    ctx, tracker = _make_context(tmp_path)

    assert await _fill(ctx, execution_id="77", quantity=5) == "workflow"
    conflicted = await _fill(ctx, execution_id="77", quantity=4)

    assert conflicted == "error"
    assert len(_history(tracker)) == 1
    assert _lots(tracker) == [("AAPL", 5, "workflow")]


# ---------------------------------------------------------------------------
# Y2 — 폴백이 잡는 범위는 **identity 예외 하나**다
#
# 종전 폴백은 `except ValueError` 라, execution_id 가 실려 있기만 하면 identity 와
# 무관한 tracker 예외까지 삼켜 체결번호 없이 재기록했다. 실제로 닿는 경로가 있다 —
# _execution_facts 의 유한성 가드(수량/가격이 inf·nan 이면
# ValueError("Explicit execution quantity and price must be finite")). 그건 체결번호를
# 뗀다고 나아지지 않는 **체결 사실 자체의 문제**이므로, 비유한 값을 원장에 남기는 대신
# "error" 로 끝나야 한다. 그래서 tracker 에 ExecutionIdentityError 를 두고
# _normalize_identifier / _execution_key 계열만 그걸 올린다.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_price", [float("inf"), float("nan")])
@pytest.mark.asyncio
async def test_non_identity_value_error_is_not_swallowed_by_the_fallback(
    tmp_path, caplog, bad_price
):
    """비유한 체결가는 체결번호를 떼고 재기록되지 않는다 — 'error' 로 끝난다."""
    ctx, tracker = _make_context(tmp_path)

    with caplog.at_level(logging.WARNING, logger="programgarden.context"):
        result = await _fill(ctx, execution_id="77", price=bad_price)

    assert result == "error"
    assert _history(tracker) == [], "비유한 값이 원장에 남으면 안 된다"
    assert _lots(tracker) == []
    assert not [r for r in caplog.records
                if "Execution identity unusable" in r.getMessage()], \
        "identity 폴백이 identity 와 무관한 예외를 잡으면 안 된다"


@pytest.mark.asyncio
async def test_identity_errors_are_a_dedicated_exception_type():
    """계약 고정 — 정규화 실패만 ExecutionIdentityError 다(충돌은 별도 타입)."""
    from programgarden.database.workflow_position_tracker import (
        ExecutionIdentityConflictError,
        ExecutionIdentityError,
        WorkflowPositionTracker,
    )

    assert issubclass(ExecutionIdentityError, ValueError)
    with pytest.raises(ExecutionIdentityError):
        WorkflowPositionTracker._normalize_identifier("12.5")
    with pytest.raises(ExecutionIdentityError):
        WorkflowPositionTracker._normalize_identifier(4.0)
    # 충돌은 재시도 대상이 아니므로 일부러 이 타입의 서브클래스가 아니다.
    assert not issubclass(ExecutionIdentityConflictError, ExecutionIdentityError)


# ---------------------------------------------------------------------------
# Y5 — X1 의 대가를 명시적으로 고정한다
#
# 체결번호를 떼고 재기록하면 그 행에는 중복방지 키가 없다. 그래서 **깨진 체결번호를
# 실은 같은 프레임이 재전달되면 2행이 된다** — 의도된 트레이드오프다(체결 한 건이
# 통째로 사라지는 것보다 낫다). 정상 체결번호는 종전대로 1행이다
# (test_usable_execution_id_keeps_identity_and_replay_protection).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_replayed_frame_with_a_broken_execution_id_records_twice(tmp_path, caplog):
    """깨진 체결번호로 같은 프레임이 두 번 오면 2행 + 경고 2회."""
    ctx, tracker = _make_context(tmp_path)

    with caplog.at_level(logging.WARNING, logger="programgarden.context"):
        first = await _fill(ctx, execution_id="0.0")
        replay = await _fill(ctx, execution_id="0.0")

    assert (first, replay) == ("workflow", "workflow")
    rows = _history(tracker)
    assert len(rows) == 2, "중복방지를 포기했으므로 재전달이 2행이 된다(의도된 대가)"
    assert [r[7] for r in rows] == [None, None], "거짓 중복방지 키를 만들지 않는다"
    assert _lots(tracker) == [("AAPL", 5, "workflow"), ("AAPL", 5, "workflow")]

    warnings = [r.getMessage() for r in caplog.records
                if "Execution identity unusable" in r.getMessage()]
    assert len(warnings) == 2, warnings


# ---------------------------------------------------------------------------
# Y4 — record_order 가 띄우는 fire-and-forget 태스크의 침묵 실패
#
# record_order 는 버퍼 처리(_process_buffered_fill)를 `loop.create_task` 로 띄우고
# 아무도 await 하지 않는다. 그 안의 _normalize_identifier 가 ExecutionIdentityError 를
# 올리면 체결은 버퍼에 남아 타임아웃 경로로 unknown_api 가 되는데, **원인 기록이
# 하나도 없었다**. done 콜백으로 드러낸다.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_buffered_fill_task_failure_is_logged(tmp_path, caplog):
    import asyncio

    from programgarden.database.workflow_position_tracker import PendingFill

    ctx, tracker = _make_context(tmp_path)
    tracker._pending_fills[1] = PendingFill(
        order_no="999", order_date=TODAY, symbol="AAPL", exchange="NASDAQ",
        side="buy", quantity=1, price=100.0, fill_time="120000000",
        commda_code="40", received_at=datetime.now(), execution_id="12.5",
    )

    logger_name = "programgarden.database.workflow_position_tracker"
    with caplog.at_level(logging.ERROR, logger=logger_name):
        tracker.record_order("999", TODAY, "AAPL", "NASDAQ", "buy", 1, 100.0,
                             ctx.job_id, "order-node")
        for _ in range(5):
            await asyncio.sleep(0)

    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert any("Buffered-fill processing task failed" in m for m in errors), errors


@pytest.mark.asyncio
async def test_successful_buffered_fill_task_logs_nothing(tmp_path, caplog):
    """정상 경로는 조용하다(콜백이 성공 태스크에 잡음을 만들지 않는다)."""
    import asyncio

    logger_name = "programgarden.database.workflow_position_tracker"
    with caplog.at_level(logging.ERROR, logger=logger_name):
        ctx, tracker = _make_context(tmp_path)
        tracker.record_order("456", TODAY, "AAPL", "NASDAQ", "buy", 1, 100.0,
                             ctx.job_id, "order-node")
        for _ in range(5):
            await asyncio.sleep(0)

    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR] == []
