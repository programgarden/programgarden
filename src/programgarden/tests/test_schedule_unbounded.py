"""ScheduleNode unbounded scheduling (owner decision 2026-09-26).

"언급이 없으면, 시간을 챗봇이 알아서 정해서 주기적으로 계속 돌게 만들자." — when the
investor names no duration, a recurring ScheduleNode must run **until the user
stops the workflow**. count / max_duration_hours are optional now: absent = None =
unbounded, a provided value is still enforced as a cap.

These drive the executor scheduler loop directly with a croniter stand-in so
ticks fire without real cron waits. No global time source is patched (that would
disturb the asyncio event loop clock); the max-duration case paces on a small
real interval instead.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from programgarden.context import ExecutionContext
from programgarden.executor import ScheduleNodeExecutor


def make_context() -> ExecutionContext:
    ctx = ExecutionContext(
        job_id="schedule-unbounded-test",
        workflow_id="wf-schedule-unbounded-test",
        context_params={},
    )
    ctx._is_running = True  # scheduler_task 루프 진입용
    return ctx


class _InstantCron:
    """croniter stand-in whose next firing is already in the past, so the
    executor's inter-tick wait computes to <= 0 and it ticks immediately."""

    def __init__(self, expr, base, **kw):
        self._tz = base.tzinfo

    @staticmethod
    def is_valid(expr, **kw):
        return True

    def get_next(self, ret_type):
        return datetime.now(self._tz) - timedelta(seconds=1)


class _PacedCron:
    """croniter stand-in that fires a small real interval ahead, so the loop
    advances on wall-clock time (used to let a max_duration cap actually trip)."""

    def __init__(self, expr, base, **kw):
        self._tz = base.tzinfo

    @staticmethod
    def is_valid(expr, **kw):
        return True

    def get_next(self, ret_type):
        return datetime.now(self._tz) + timedelta(seconds=0.03)


async def test_unbounded_schedule_ticks_until_stopped():
    """(b) count=None + max_duration_hours=None keeps ticking well past what the
    old defaults (count 1000 / 24h) allowed, and stops the instant is_running
    flips to False (the user stopping the workflow)."""
    ctx = make_context()
    executor = ScheduleNodeExecutor()

    ticks = []

    async def fake_emit(**kwargs):
        ticks.append(kwargs.get("data"))
        if len(ticks) >= 3:
            ctx._is_running = False  # simulate the user stopping the workflow

    with patch("croniter.croniter", _InstantCron), \
            patch.object(ctx, "emit_event", side_effect=fake_emit), \
            patch.object(ctx, "send_notification", new=AsyncMock()):
        result = await executor.execute(
            node_id="sched",
            node_type="ScheduleNode",
            config={"cron": "*/5 * * * *", "timezone": "UTC"},  # no count / max_duration_hours
            context=ctx,
        )
        assert result == {"trigger": True}
        task = ctx._persistent_tasks["sched"]
        await asyncio.wait_for(task, timeout=5.0)

    assert task.done()
    # It fired purely because is_running stayed True (no cycle/time cap), and
    # stopped as soon as is_running went False.
    assert len(ticks) == 3
    assert [t["count"] for t in ticks] == [1, 2, 3]
    assert ctx.is_running is False


async def test_count_bound_stops_after_exact_cycles():
    """(c) a provided count still bounds the loop: count=2 → exactly 2 ticks,
    and the loop ends on the cap (not on shutdown)."""
    ctx = make_context()
    executor = ScheduleNodeExecutor()

    ticks = []

    async def fake_emit(**kwargs):
        ticks.append(kwargs.get("data"))

    with patch("croniter.croniter", _InstantCron), \
            patch.object(ctx, "emit_event", side_effect=fake_emit), \
            patch.object(ctx, "send_notification", new=AsyncMock()):
        await executor.execute(
            node_id="sched",
            node_type="ScheduleNode",
            config={"cron": "*/5 * * * *", "timezone": "UTC", "count": 2},
            context=ctx,
        )
        task = ctx._persistent_tasks["sched"]
        await asyncio.wait_for(task, timeout=5.0)

    assert task.done()
    assert len(ticks) == 2
    # stopped by the count cap, not a shutdown — is_running is still True.
    assert ctx.is_running is True


async def test_max_duration_bound_stops_the_loop():
    """(c) a provided max_duration_hours still bounds the loop: a tiny cap stops
    the scheduler even while is_running stays True and no count cap exists."""
    ctx = make_context()
    executor = ScheduleNodeExecutor()

    ticks = []

    async def fake_emit(**kwargs):
        ticks.append(kwargs.get("data"))

    # 0.1s wall-clock cap; the paced cron advances ~0.03s per tick, so the cap
    # trips after a few ticks. is_running stays True throughout.
    with patch("croniter.croniter", _PacedCron), \
            patch.object(ctx, "emit_event", side_effect=fake_emit), \
            patch.object(ctx, "send_notification", new=AsyncMock()):
        await executor.execute(
            node_id="sched",
            node_type="ScheduleNode",
            config={"cron": "*/5 * * * *", "timezone": "UTC",
                    "max_duration_hours": 0.1 / 3600},
            context=ctx,
        )
        task = ctx._persistent_tasks["sched"]
        await asyncio.wait_for(task, timeout=5.0)

    assert task.done()
    assert len(ticks) >= 1  # at least one tick before the wall-clock cap trips
    # stopped by the duration cap, not a shutdown.
    assert ctx.is_running is True
