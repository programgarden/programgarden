"""ScheduleNode jitter (owner concern 2026-09-28).

Many workflows sharing one cron instant ("0 9 * * *") would all fire at the same
second and stampede a shared cloud egress IP. `jitter_seconds` staggers the
ACTUAL fire by a random 0..jitter seconds past the cron instant. Default 0 = no
jitter (fire exactly on the instant). The value is clamped to [0, 300].

Driven directly against the executor scheduler loop with an instant-cron stand-in
(same pattern as test_schedule_unbounded.py); `random.uniform` is spied so no real
jitter wait is needed and the requested range is asserted.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from programgarden.context import ExecutionContext
from programgarden.executor import ScheduleNodeExecutor


def make_context() -> ExecutionContext:
    ctx = ExecutionContext(
        job_id="schedule-jitter-test",
        workflow_id="wf-schedule-jitter-test",
        context_params={},
    )
    ctx._is_running = True
    return ctx


class _InstantCron:
    """Fires in the past → inter-tick wait <= 0 → ticks immediately."""

    def __init__(self, expr, base, **kw):
        self._tz = base.tzinfo

    @staticmethod
    def is_valid(expr, **kw):
        return True

    def get_next(self, ret_type):
        return datetime.now(self._tz) - timedelta(seconds=1)


async def _run_once(config, uniform_return=0.02):
    """Run the scheduler for exactly one tick and return (ticks, uniform_spy)."""
    ctx = make_context()
    executor = ScheduleNodeExecutor()
    ticks = []

    async def fake_emit(**kwargs):
        ticks.append(kwargs.get("data"))
        ctx._is_running = False  # stop after the first tick

    uniform_spy = MagicMock(return_value=uniform_return)

    with patch("croniter.croniter", _InstantCron), \
            patch("random.uniform", uniform_spy), \
            patch.object(ctx, "emit_event", side_effect=fake_emit), \
            patch.object(ctx, "send_notification", new=AsyncMock()):
        result = await executor.execute(
            node_id="sched", node_type="ScheduleNode", config=config, context=ctx,
        )
        assert result == {"trigger": True}
        task = ctx._persistent_tasks["sched"]
        await asyncio.wait_for(task, timeout=5.0)

    return ticks, uniform_spy


async def test_no_jitter_by_default():
    """No jitter_seconds → random.uniform is never called; the tick still fires."""
    ticks, uniform_spy = await _run_once({"cron": "*/5 * * * *", "timezone": "UTC"})
    assert len(ticks) == 1
    uniform_spy.assert_not_called()


async def test_jitter_zero_explicit_no_delay():
    """jitter_seconds=0 explicitly → no jitter delay."""
    ticks, uniform_spy = await _run_once(
        {"cron": "*/5 * * * *", "timezone": "UTC", "jitter_seconds": 0}
    )
    assert len(ticks) == 1
    uniform_spy.assert_not_called()


async def test_jitter_applied_within_range():
    """jitter_seconds=4 → the fire is delayed by random.uniform(0, 4)."""
    ticks, uniform_spy = await _run_once(
        {"cron": "*/5 * * * *", "timezone": "UTC", "jitter_seconds": 4}
    )
    assert len(ticks) == 1
    uniform_spy.assert_called_once_with(0, 4)


async def test_jitter_clamped_to_300_max():
    """jitter_seconds above 300 is clamped to 300."""
    ticks, uniform_spy = await _run_once(
        {"cron": "*/5 * * * *", "timezone": "UTC", "jitter_seconds": 1000}
    )
    assert len(ticks) == 1
    uniform_spy.assert_called_once_with(0, 300)


async def test_jitter_negative_clamped_to_zero():
    """A negative jitter_seconds is clamped to 0 → no jitter."""
    ticks, uniform_spy = await _run_once(
        {"cron": "*/5 * * * *", "timezone": "UTC", "jitter_seconds": -5}
    )
    assert len(ticks) == 1
    uniform_spy.assert_not_called()
