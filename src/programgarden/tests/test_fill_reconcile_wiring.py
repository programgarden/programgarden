"""재조정 주기 태스크가 실행기에 제대로 붙어 있는지.

순수 로직(test_fill_reconciler)과 별개로, **실제로 돌기는 하는가**를 본다. 붙이지 못하면
로직이 아무리 맞아도 원장은 계속 빈다.
"""
import asyncio
import types

import pytest

from programgarden.executor import WorkflowJob


class _Pos:
    def __init__(self, quantity, buy_price):
        self.quantity = quantity
        self.buy_price = buy_price


class _AcctTracker:
    def __init__(self, positions):
        self._positions = positions


def _job():
    """생성자를 타지 않고 재조정 관련 상태만 갖춘 최소 객체."""
    job = WorkflowJob.__new__(WorkflowJob)
    job._active_trackers = {}
    job._reconcile_task = None
    job.context = types.SimpleNamespace(_workflow_position_tracker=None)
    return job


# ── 계좌 스냅샷 ────────────────────────────────────────────────────────────

def test_snapshot_reads_quantity_and_avg_price():
    snap = WorkflowJob._account_positions_snapshot(
        _AcctTracker({"MARA": _Pos(1, 11.78), "NIO": _Pos(3, 4.19)})
    )
    assert snap == {"MARA": {"quantity": 1.0, "avg_price": 11.78},
                    "NIO": {"quantity": 3.0, "avg_price": 4.19}}


def test_empty_cache_is_unavailable_not_empty_holdings():
    """🔴 빈 dict 를 돌려주면 보유 중인 포지션이 전부 '밖에서 팔렸다' 로 기록된다."""
    assert WorkflowJob._account_positions_snapshot(_AcctTracker({})) is None
    assert WorkflowJob._account_positions_snapshot(types.SimpleNamespace()) is None


def test_unparsable_fields_do_not_crash_the_snapshot():
    snap = WorkflowJob._account_positions_snapshot(_AcctTracker({"X": _Pos("bad", "bad")}))
    assert snap == {"X": {"quantity": 0.0, "avg_price": None}}


# ── 추적기 선택 ────────────────────────────────────────────────────────────

def test_picks_the_account_tracker_not_the_fill_subscription():
    job = _job()
    job._active_trackers = {
        "a_fill_sub": {"type": "fill_subscription", "ls": object(), "real": object()},
        "a": {"type": "account_tracker", "tracker": _AcctTracker({}), "ls": object()},
    }
    entry = job._find_account_tracker_entry()
    assert entry is not None and entry["type"] == "account_tracker"


def test_no_account_tracker_returns_none():
    job = _job()
    job._active_trackers = {"a_fill_sub": {"type": "fill_subscription", "ls": object()}}
    assert job._find_account_tracker_entry() is None


# ── 한 주기 실행 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_skips_quietly_without_a_ledger_tracker():
    job = _job()
    job._active_trackers = {"a": {"type": "account_tracker", "tracker": _AcctTracker({}), "ls": object()}}
    assert await job._reconcile_fills_once() is None


@pytest.mark.asyncio
async def test_skips_quietly_without_an_account_tracker():
    job = _job()
    job.context._workflow_position_tracker = object()
    assert await job._reconcile_fills_once() is None


# ── 루프 수명 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_loop_starts_once_and_stops_cleanly():
    job = _job()
    job._start_reconcile_loop()
    task = job._reconcile_task
    assert task is not None and not task.done()

    job._start_reconcile_loop()
    assert job._reconcile_task is task, "중복 기동되면 같은 체결을 두 번 확인한다"

    await job._stop_reconcile_loop()
    assert job._reconcile_task is None
    assert task.cancelled() or task.done()


@pytest.mark.asyncio
async def test_stop_is_safe_when_never_started():
    job = _job()
    await job._stop_reconcile_loop()
    assert job._reconcile_task is None


@pytest.mark.asyncio
async def test_a_failing_cycle_does_not_kill_the_loop():
    """한 주기가 터져도 다음 주기가 살아 있어야 한다 — 아니면 조용히 재조정이 멈춘다."""
    job = _job()
    calls = []

    async def boom():
        calls.append(1)
        raise RuntimeError("broker down")

    job._reconcile_fills_once = boom
    job.RECONCILE_INTERVAL_SEC = 0.01
    job._start_reconcile_loop()
    await asyncio.sleep(0.08)
    running = not job._reconcile_task.done()
    await job._stop_reconcile_loop()

    assert len(calls) >= 2, "첫 실패 후 루프가 죽었다"
    assert running


def test_interval_is_above_the_account_tracker_cadence():
    """계좌 추적기가 60초마다 같은 앱키를 쓴다 — 그보다 촘촘하면 조회 예산을 잠식한다."""
    assert WorkflowJob.RECONCILE_INTERVAL_SEC >= 60.0
    assert WorkflowJob.RECONCILE_MIN_ORDER_AGE_SEC >= 10.0
