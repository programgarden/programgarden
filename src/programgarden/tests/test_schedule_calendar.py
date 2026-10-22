"""Real local timers: no credentials, broker traffic, subprocesses or orders."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from croniter import croniter, CroniterBadDateError
from programgarden.executor import WorkflowExecutor


def graph(cron, *, second_cron=None):
    nodes = [{"id":"start","type":"StartNode"},
             {"id":"schedule","type":"ScheduleNode","cron":cron,"timezone":"UTC"},
             {"id":"after","type":"WatchlistNode","symbols":[{"exchange":"NASDAQ","symbol":"AAPL"}]}]
    edges = [{"from":"start","to":"schedule"},{"from":"schedule","to":"after"}]
    if second_cron:
        nodes += [{"id":"other","type":"ScheduleNode","cron":second_cron,"timezone":"UTC"},
                  {"id":"other_after","type":"WatchlistNode","symbols":[{"exchange":"NASDAQ","symbol":"MSFT"}]}]
        edges += [{"from":"start","to":"other"},{"from":"other","to":"other_after"}]
    return {"id":"calendar-test","name":"Calendar test","nodes":nodes,"edges":edges}


def date_cron(date):
    return f"{date.second} {date.minute} {date.hour} {date.day} {date.month} * {date.year}"


async def test_future_date_waits_and_only_its_branch_fires():
    now = datetime.now(timezone.utc)
    due = now + timedelta(seconds=3)
    job = await WorkflowExecutor().execute(graph(date_cron(due), second_cron=date_cron(now + timedelta(days=1))))
    try:
        await asyncio.sleep(0.2)
        assert job.status == "running"
        assert job.context.get_output("after", "symbols") is None
        assert job.context.get_output("other_after", "symbols") is None
        for _ in range(60):
            if job.context.get_output("after", "symbols"):
                break
            await asyncio.sleep(0.1)
        assert job.context.get_output("after", "symbols") == [{"exchange":"NASDAQ","symbol":"AAPL"}]
        assert job.context.get_output("other_after", "symbols") is None
        assert job.status == "running"  # The other calendar is still waiting.
    finally:
        await job.stop()


async def test_finite_calendar_completes_after_one_tick():
    job = await WorkflowExecutor().execute(graph(date_cron(datetime.now(timezone.utc) + timedelta(seconds=2))))
    try:
        await asyncio.wait_for(job._task, 6)
        assert job.status == "completed"
        assert job.stats["errors_count"] == 0
        assert job.context.get_output("after", "symbols")
        assert job.stats["flow_executions"] == 2  # Timer registration + one due cycle.
    finally:
        if not job._task.done():
            await job.stop()


async def test_expired_calendar_does_not_execute_or_wait_forever():
    job = await WorkflowExecutor().execute(graph("0 0 9 1 1 * 2020"))
    await asyncio.wait_for(job._task, 4)
    assert job.status == "completed"
    assert job.stats["errors_count"] == 0
    assert job.context.get_output("after", "symbols") is None


def test_date_repeat_is_bounded_to_selected_year_and_day():
    it = croniter("0 */5 * 5 10 * 2026", datetime(2026,10,5,23,50,tzinfo=timezone.utc), second_at_beginning=True)
    assert it.get_next(datetime) == datetime(2026,10,5,23,55,tzinfo=timezone.utc)
    with pytest.raises(CroniterBadDateError):
        it.get_next(datetime)


def test_missing_monthly_and_leap_days_are_skipped():
    it = croniter("0 9 31 * *", datetime(2026,4,1,tzinfo=timezone.utc), second_at_beginning=True)
    assert it.get_next(datetime) == datetime(2026,5,31,9,tzinfo=timezone.utc)
    it = croniter("0 9 29 2 *", datetime(2026,1,1,tzinfo=timezone.utc), second_at_beginning=True)
    assert it.get_next(datetime) == datetime(2028,2,29,9,tzinfo=timezone.utc)


async def test_far_future_supported_year_keeps_waiting():
    job = await WorkflowExecutor().execute(graph("0 0 9 1 1 * 2099"))
    try:
        await asyncio.sleep(1.2)
        assert job.status == "running"
        assert job.context.get_output("after", "symbols") is None
    finally:
        await job.stop()
