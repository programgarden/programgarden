"""Broker-owned trackers stop with the workflow, without any network access."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import BrokerNodeExecutor, WorkflowJob
from programgarden.resolver import ResolvedWorkflow
from programgarden_core.bases.listener import BaseExecutionListener
from programgarden_finance.ls.overseas_futureoption.extension.tracker import FuturesAccountTracker


POLL_INTERVAL = 0.01


@pytest.fixture(autouse=True)
def isolate_broker_registries(monkeypatch):
    monkeypatch.setattr(BrokerNodeExecutor, "_active_trackers", {})
    monkeypatch.setattr(BrokerNodeExecutor, "_background_tasks", {})
    monkeypatch.setattr(BrokerNodeExecutor, "_notification_tasks", {})


def make_job(job_id="broker-lifecycle"):
    context = ExecutionContext(job_id=job_id, workflow_id="offline-workflow")
    workflow = ResolvedWorkflow("offline-workflow", "1.0.0", {}, [], [])
    return WorkflowJob(job_id, workflow, context, MagicMock())


def make_futures_fixture():
    real = SimpleNamespace(connect=AsyncMock(), is_connected=AsyncMock(return_value=True), close=AsyncMock())
    tracker = FuturesAccountTracker(MagicMock(), MagicMock(), real, refresh_interval=POLL_INTERVAL)
    tracker._spec_manager = SimpleNamespace(initialize=AsyncMock(), stop=AsyncMock())
    tracker._fetch_all_data = AsyncMock()
    tracker._setup_subscriptions = AsyncMock()
    tracker._cleanup_subscriptions = AsyncMock()
    api = SimpleNamespace(
        real=lambda: real,
        accno=lambda: SimpleNamespace(account_tracker=lambda **kwargs: tracker),
        market=MagicMock(),
    )
    return SimpleNamespace(overseas_futureoption=lambda: api), tracker, real


@pytest.mark.asyncio
@pytest.mark.parametrize("termination", ["complete", "stop", "cancel", "force_stop"])
async def test_sdk_periodic_polling_stops_after_job_termination(termination):
    """Use the SDK's actual start/periodic-refresh/stop loop, with read calls mocked."""
    job = make_job()
    broker = BrokerNodeExecutor()
    ls, tracker, real = make_futures_fixture()

    async def main_flow():
        await broker._start_overseas_futures_tracker(
            ls, "broker", "overseas_futures", "ls", job.context,
        )
        # Prove the periodic loop is active before terminating the job.
        await asyncio.sleep(POLL_INTERVAL * 3)
        assert tracker._fetch_all_data.await_count >= 2

    job._execute_main_flow = AsyncMock(side_effect=main_flow)
    try:
        if termination == "complete":
            await job._run()
            assert job.status == "completed"
        else:
            await main_flow()
            await getattr(job, termination)()
            assert job.status == {"stop": "stopped", "cancel": "cancelled", "force_stop": "force_stopped"}[termination]

        reads_at_termination = tracker._fetch_all_data.await_count
        await asyncio.sleep(POLL_INTERVAL * 8)
        assert tracker._fetch_all_data.await_count == reads_at_termination
        assert tracker._refresh_task is None
        assert tracker._is_running is False
        real.close.assert_awaited_once()
        assert f"{job.job_id}_broker" not in broker._active_trackers

        # Explicit stop after normal completion is safe and idempotent.
        await job.stop()
        real.close.assert_awaited_once()
    finally:
        await tracker.stop()
        broker._active_trackers.pop(f"{job.job_id}_broker", None)


@pytest.mark.asyncio
@pytest.mark.parametrize("termination", ["complete", "stop", "cancel"])
@pytest.mark.parametrize("blocked_stage", ["connect", "start"])
@pytest.mark.parametrize("product", ["overseas_stock", "overseas_futures", "korea_stock"])
async def test_termination_cancels_partial_tracker_startup(termination, blocked_stage, product):
    """A slow connect/initial read must not install a tracker after job cleanup."""
    job = make_job()
    broker = BrokerNodeExecutor()
    entered = asyncio.Event()
    released = asyncio.Event()

    async def blocked():
        entered.set()
        await released.wait()

    real = SimpleNamespace(connect=AsyncMock(), close=AsyncMock())
    tracker = SimpleNamespace(start=AsyncMock(), stop=AsyncMock(), on_account_pnl_change=MagicMock())
    setattr(real if blocked_stage == "connect" else tracker, blocked_stage, AsyncMock(side_effect=blocked))
    api = SimpleNamespace(
        real=lambda: real, market=MagicMock(),
        accno=lambda: SimpleNamespace(account_tracker=lambda **kwargs: tracker),
    )
    api_name = "overseas_futureoption" if product == "overseas_futures" else product
    ls = SimpleNamespace(**{api_name: lambda: api})
    startup = broker._start_background_task(
        job.context,
        getattr(broker, f"_start_{product}_tracker")(ls, "broker", product, "ls", job.context),
    )
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
        if termination == "complete":
            job._execute_main_flow = AsyncMock()
            await job._run()
        elif termination == "stop":
            await job.stop()
        else:
            async def running_flow():
                await asyncio.Event().wait()

            job._execute_main_flow = AsyncMock(side_effect=running_flow)
            job._task = asyncio.create_task(job._run())
            await asyncio.sleep(0)
            await job.cancel()
        released.set()
        await asyncio.sleep(POLL_INTERVAL * 2)
        assert startup.cancelled()
        tracker.stop.assert_awaited_once()
        real.close.assert_awaited_once()
        assert not broker._active_trackers
        assert not broker._background_tasks
    finally:
        startup.cancel()
        await asyncio.gather(startup, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("product", ["overseas_stock", "overseas_futures", "korea_stock"])
async def test_late_pnl_callback_cannot_restart_job_work(product):
    job = make_job()
    job.context.notify_workflow_pnl = AsyncMock()
    broker = BrokerNodeExecutor()
    real = SimpleNamespace(connect=AsyncMock(), close=AsyncMock())
    tracker = SimpleNamespace(
        start=AsyncMock(), stop=AsyncMock(), get_positions=lambda: {},
        on_account_pnl_change=MagicMock(),
    )
    api = SimpleNamespace(
        real=lambda: real, market=MagicMock(),
        accno=lambda: SimpleNamespace(account_tracker=lambda **kwargs: tracker),
    )
    api_name = "overseas_futureoption" if product == "overseas_futures" else product
    ls = SimpleNamespace(**{api_name: lambda: api})
    await getattr(broker, f"_start_{product}_tracker")(ls, "broker", product, "ls", job.context)
    callback = tracker.on_account_pnl_change.call_args.args[0]
    callback(SimpleNamespace())
    await asyncio.sleep(0)
    assert job.context.notify_workflow_pnl.await_count == 1
    await job.stop()
    callback(SimpleNamespace())
    await asyncio.sleep(0)
    assert job.context.notify_workflow_pnl.await_count == 1
    assert not broker._background_tasks


@pytest.mark.asyncio
async def test_cleanup_preserves_another_job_with_a_similar_id():
    broker = BrokerNodeExecutor()
    job = make_job("job-1")
    other = make_job("job-10")
    entered = asyncio.Event()

    async def background_read():
        entered.set()
        await asyncio.Event().wait()

    task = broker._start_background_task(other.context, background_read())
    tracker = SimpleNamespace(stop=AsyncMock())
    real = SimpleNamespace(close=AsyncMock())
    broker._active_trackers["job-10_broker"] = {"tracker": tracker, "real": real}
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
        await job.stop()
        assert not task.done()
        tracker.stop.assert_not_awaited()
        real.close.assert_not_awaited()
        await other.stop()
        assert task.cancelled()
        tracker.stop.assert_awaited_once()
        real.close.assert_awaited_once()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("termination", ["complete", "stop", "cancel", "force_stop"])
@pytest.mark.parametrize("already_started", [False, True])
async def test_termination_preserves_pending_actual_pnl_listener_delivery(termination, already_started):
    """Real context dispatch must finish before listener cleanup closes its sink."""
    job = make_job()
    broker = BrokerNodeExecutor()
    ls, tracker, real = make_futures_fixture()
    entered, release, connection_closed = asyncio.Event(), asyncio.Event(), asyncio.Event()
    delivered = []

    class Listener(BaseExecutionListener):
        async def on_workflow_pnl_update(self, event):
            entered.set()
            await release.wait()
            assert connection_closed.is_set()
            delivered.append(True)

    job.context.add_listener(Listener())
    await broker._start_overseas_futures_tracker(ls, "broker", "overseas_futures", "ls", job.context)
    real.close.side_effect = connection_closed.set
    tracker._on_account_pnl_change_callbacks[0](SimpleNamespace(currency="USD"))
    if already_started:
        await asyncio.wait_for(entered.wait(), timeout=1)
    job._execute_main_flow = AsyncMock()
    ending = asyncio.create_task(job._run() if termination == "complete" else getattr(job, termination)())
    try:
        await asyncio.wait_for(connection_closed.wait(), timeout=1)
        assert not tracker._is_running
        assert not ending.done()
        release.set()
        await asyncio.wait_for(ending, timeout=1)
        assert delivered == [True]
        assert not broker._notification_tasks
        assert not job.context._listeners
    finally:
        release.set()
        await asyncio.gather(ending, return_exceptions=True)
        await tracker.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("resists_cancellation", [False, True])
async def test_wedged_pnl_listener_has_bounded_observable_stop(monkeypatch, caplog, resists_cancellation):
    job = make_job()
    broker = BrokerNodeExecutor()
    ls, tracker, real = make_futures_fixture()
    entered, release, cancelled = asyncio.Event(), asyncio.Event(), asyncio.Event()
    monkeypatch.setattr(BrokerNodeExecutor, "_PNL_DRAIN_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setattr(BrokerNodeExecutor, "_PNL_CANCEL_TIMEOUT_SECONDS", 0.02)

    class Listener(BaseExecutionListener):
        async def on_workflow_pnl_update(self, event):
            entered.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                cancelled.set()
                if not resists_cancellation:
                    raise
                await release.wait()

    job.context.add_listener(Listener())
    await broker._start_overseas_futures_tracker(ls, "broker", "overseas_futures", "ls", job.context)
    tracker._on_account_pnl_change_callbacks[0](SimpleNamespace(currency="USD"))
    notification = next(iter(broker._notification_tasks[job.job_id]))
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
        await asyncio.wait_for(job.stop(), timeout=0.5)
        assert cancelled.is_set()
        assert "PnL notification drain timed out" in caplog.text
        assert not tracker._is_running
        real.close.assert_awaited_once()
        if resists_cancellation:
            assert "notification cancellation did not finish" in caplog.text
            assert notification in broker._notification_tasks[job.job_id]
        else:
            assert notification.cancelled()
            assert not broker._notification_tasks
    finally:
        release.set()
        await asyncio.gather(notification, return_exceptions=True)
        await tracker.stop()
