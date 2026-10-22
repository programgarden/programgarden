"""C-8: reconnect notification promotion + post-reconnect reconcile.

Covers two deliverables, both mock-only (no live API / no real websocket):

1. ReconnectHandler promotes connection lost/restored/failed to on_notification
   (previously log-only), running a reconcile hook on success.
2. _build_reconnect_hooks (executor) snapshots open-orders/positions, forces a
   refresh, and diffs them to surface gap drift — notify-only.
"""

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from programgarden.reconnect_handler import ReconnectHandler
from programgarden.executor import _build_reconnect_hooks
from programgarden_core.bases.listener import (
    NotificationCategory,
    NotificationSeverity,
)


class NotifyRecorder:
    """Captures notify(category, severity, title, message, data) calls."""

    def __init__(self, fail: bool = False):
        self.calls: List[Dict[str, Any]] = []
        self._fail = fail

    async def __call__(self, category, severity, title, message, data):
        if self._fail:
            raise RuntimeError("notify sink boom")
        self.calls.append({
            "category": category,
            "severity": severity,
            "title": title,
            "message": message,
            "data": data,
        })

    def categories(self):
        return [c["category"] for c in self.calls]

    def of(self, category):
        return [c for c in self.calls if c["category"] == category]


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Backoff sleeps must not slow the suite."""
    async def _instant(_):
        return None
    monkeypatch.setattr("programgarden.reconnect_handler.asyncio.sleep", _instant)


# ───────────────────────── ReconnectHandler notifications ─────────────────────────

class TestConnectionNotifications:
    @pytest.mark.asyncio
    async def test_disconnect_emits_connection_lost_once_per_episode(self):
        notify = NotifyRecorder()
        h = ReconnectHandler(notify=notify)

        assert await h.handle_disconnect() is True   # attempt 1
        assert await h.handle_disconnect() is True   # attempt 2

        lost = notify.of(NotificationCategory.CONNECTION_LOST)
        assert len(lost) == 1, "CONNECTION_LOST must fire once per episode, not per retry"
        assert lost[0]["severity"] == NotificationSeverity.WARNING

    @pytest.mark.asyncio
    async def test_max_attempts_emits_connection_failed_critical(self):
        notify = NotifyRecorder()
        h = ReconnectHandler(notify=notify)
        h._lost_notified = True  # isolate the FAILED emission

        # MAX_ATTEMPTS=5 → the 6th call crosses the threshold and gives up.
        result = True
        for _ in range(ReconnectHandler.MAX_ATTEMPTS + 1):
            result = await h.handle_disconnect()
        assert result is False

        failed = notify.of(NotificationCategory.CONNECTION_FAILED)
        assert len(failed) == 1
        assert failed[0]["severity"] == NotificationSeverity.CRITICAL
        assert "total_disconnection_sec" in failed[0]["data"]

    @pytest.mark.asyncio
    async def test_reconnect_success_no_gap_no_drift_is_info(self):
        notify = NotifyRecorder()

        async def reconcile():
            return {"drift": False, "open_orders_count": 0, "positions_count": 1}

        h = ReconnectHandler(notify=notify, reconcile=reconcile)
        # No gap accrued (total_disconnection_sec == 0) and no drift → INFO.
        await h.on_reconnect_success()

        restored = notify.of(NotificationCategory.CONNECTION_RESTORED)
        assert len(restored) == 1
        assert restored[0]["severity"] == NotificationSeverity.INFO
        assert restored[0]["data"]["reconcile"]["drift"] is False

    @pytest.mark.asyncio
    async def test_reconnect_success_with_gap_warns(self):
        notify = NotifyRecorder()
        h = ReconnectHandler(notify=notify)
        h._total_disconnection_sec = 7.0  # a real gap, even without drift, warns

        await h.on_reconnect_success()

        restored = notify.of(NotificationCategory.CONNECTION_RESTORED)
        assert restored[0]["severity"] == NotificationSeverity.WARNING
        assert restored[0]["data"]["total_disconnection_sec"] == 7.0

    @pytest.mark.asyncio
    async def test_reconnect_success_drift_warns_and_carries_summary(self):
        notify = NotifyRecorder()
        summary = {
            "drift": True,
            "closed_or_filled_orders": ["O1"],
            "new_orders": [],
            "position_changes": [{"symbol": "AAPL", "before": 10, "after": 5}],
        }

        async def reconcile():
            return summary

        h = ReconnectHandler(notify=notify, reconcile=reconcile)
        await h.on_reconnect_success()

        restored = notify.of(NotificationCategory.CONNECTION_RESTORED)
        assert restored[0]["severity"] == NotificationSeverity.WARNING
        assert restored[0]["data"]["reconcile"] == summary
        assert "변동" in restored[0]["message"]

    @pytest.mark.asyncio
    async def test_reconcile_error_warns_and_flags(self):
        notify = NotifyRecorder()

        async def reconcile():
            raise RuntimeError("TR query failed")

        h = ReconnectHandler(notify=notify, reconcile=reconcile)
        await h.on_reconnect_success()  # must not raise

        restored = notify.of(NotificationCategory.CONNECTION_RESTORED)
        assert restored[0]["severity"] == NotificationSeverity.WARNING
        assert "error" in restored[0]["data"]["reconcile"]
        assert "reconcile" in restored[0]["message"]

    @pytest.mark.asyncio
    async def test_notify_failure_never_aborts_reconnect(self):
        notify = NotifyRecorder(fail=True)
        ran = {"reconcile": False}

        async def reconcile():
            ran["reconcile"] = True
            return {"drift": False}

        h = ReconnectHandler(notify=notify, reconcile=reconcile)
        h._attempt_count = 3
        # A failing notify sink must be swallowed; reconcile + reset still happen.
        await h.on_reconnect_success()
        assert ran["reconcile"] is True
        assert h.attempt_count == 0  # reset() ran

    @pytest.mark.asyncio
    async def test_resubscribe_runs_before_reconcile(self):
        order: List[str] = []

        async def resubscribe():
            order.append("resubscribe")

        async def reconcile():
            order.append("reconcile")
            return {"drift": False}

        h = ReconnectHandler(notify=NotifyRecorder(), reconcile=reconcile)
        h.add_on_reconnect(resubscribe)
        await h.on_reconnect_success()
        assert order == ["resubscribe", "reconcile"]

    @pytest.mark.asyncio
    async def test_no_notify_sink_is_silent_noop(self):
        # Backward compat: without a notify sink the handler behaves as before.
        h = ReconnectHandler()
        assert await h.handle_disconnect() is True
        await h.on_reconnect_success()  # no crash, no sink


# ───────────────────────── executor reconcile-hook diff ─────────────────────────

class FakeTracker:
    """Tracker whose state flips on refresh_now() to emulate gap drift."""

    def __init__(self, before_orders, after_orders, before_pos, after_pos):
        self._before_orders = before_orders
        self._after_orders = after_orders
        self._before_pos = before_pos
        self._after_pos = after_pos
        self._refreshed = False

    def get_open_orders(self):
        return self._after_orders if self._refreshed else self._before_orders

    def get_positions(self):
        return self._after_pos if self._refreshed else self._before_pos

    async def refresh_now(self):
        self._refreshed = True


class FakeContext:
    def __init__(self):
        self.notifications: List[Dict[str, Any]] = []
        self.logs: List[Dict[str, Any]] = []

    async def send_notification(self, **kwargs):
        self.notifications.append(kwargs)

    def log(self, level, message, node_id=None, data=None):
        self.logs.append({"level": level, "message": message, "node_id": node_id, "data": data})


def _pos(qty):
    return SimpleNamespace(quantity=qty)


class TestBuildReconnectHooks:
    @pytest.mark.asyncio
    async def test_reconcile_detects_fill_and_position_change(self):
        tracker = FakeTracker(
            before_orders={"O1": object(), "O2": object()},
            after_orders={"O2": object()},                       # O1 filled/cancelled
            before_pos={"AAPL": _pos(10)},
            after_pos={"AAPL": _pos(5), "MSFT": _pos(3)},          # AAPL resized, MSFT new
        )
        ctx = FakeContext()
        _, reconcile = _build_reconnect_hooks(tracker, ctx, "acc", "OverseasStockRealAccountNode")

        summary = await reconcile()
        assert summary["drift"] is True
        assert summary["closed_or_filled_orders"] == ["O1"]
        assert summary["new_orders"] == []
        assert summary["open_orders_count"] == 1
        changed = {c["symbol"]: (c["before"], c["after"]) for c in summary["position_changes"]}
        assert changed["AAPL"] == (10, 5)
        assert changed["MSFT"] == (None, 3)

    @pytest.mark.asyncio
    async def test_reconcile_no_drift_when_state_stable(self):
        snapshot_orders = {"O1": object()}
        snapshot_pos = {"AAPL": _pos(10)}
        tracker = FakeTracker(snapshot_orders, dict(snapshot_orders), snapshot_pos, dict(snapshot_pos))
        ctx = FakeContext()
        _, reconcile = _build_reconnect_hooks(tracker, ctx, "acc", "KoreaStockRealAccountNode")

        summary = await reconcile()
        assert summary["drift"] is False
        assert summary["closed_or_filled_orders"] == []
        assert summary["new_orders"] == []
        assert summary["position_changes"] == []

    @pytest.mark.asyncio
    async def test_reconcile_forces_refresh(self):
        tracker = FakeTracker({"O1": object()}, {}, {}, {})
        ctx = FakeContext()
        _, reconcile = _build_reconnect_hooks(tracker, ctx, "acc", "OverseasFuturesRealAccountNode")

        assert tracker._refreshed is False
        await reconcile()
        assert tracker._refreshed is True, "reconcile must call tracker.refresh_now()"

    @pytest.mark.asyncio
    async def test_notify_hook_forwards_to_context(self):
        ctx = FakeContext()
        notify, _ = _build_reconnect_hooks(FakeTracker({}, {}, {}, {}), ctx, "acc-7", "KoreaStockRealAccountNode")

        await notify(
            NotificationCategory.CONNECTION_RESTORED,
            NotificationSeverity.INFO,
            "title",
            "msg",
            {"k": "v"},
        )
        assert len(ctx.notifications) == 1
        n = ctx.notifications[0]
        assert n["category"] == NotificationCategory.CONNECTION_RESTORED
        assert n["node_id"] == "acc-7"
        assert n["node_type"] == "KoreaStockRealAccountNode"
        assert n["data"] == {"k": "v"}

    @pytest.mark.asyncio
    async def test_notify_also_emits_to_on_log(self):
        # Connection events must surface in BOTH channels: on_notification AND
        # on_log (recorded + shown to the user). Severity maps to log level.
        ctx = FakeContext()
        notify, _ = _build_reconnect_hooks(FakeTracker({}, {}, {}, {}), ctx, "acc-9", "OverseasStockRealAccountNode")

        await notify(
            NotificationCategory.CONNECTION_FAILED,
            NotificationSeverity.CRITICAL,
            "재연결 실패",
            "최대 재시도 소진",
            {"total_disconnection_sec": 31.0},
        )
        assert len(ctx.notifications) == 1            # on_notification
        assert len(ctx.logs) == 1                     # on_log
        log = ctx.logs[0]
        assert log["level"] == "error"               # CRITICAL → error
        assert "재연결 실패" in log["message"] and "최대 재시도 소진" in log["message"]
        assert log["node_id"] == "acc-9"
        assert log["data"] == {"total_disconnection_sec": 31.0}

    @pytest.mark.asyncio
    async def test_severity_to_log_level_mapping(self):
        ctx = FakeContext()
        notify, _ = _build_reconnect_hooks(FakeTracker({}, {}, {}, {}), ctx, "acc", "KoreaStockRealAccountNode")
        for sev, expected in [
            (NotificationSeverity.INFO, "info"),
            (NotificationSeverity.WARNING, "warning"),
            (NotificationSeverity.CRITICAL, "error"),
        ]:
            await notify(NotificationCategory.CONNECTION_RESTORED, sev, "t", "m", {})
        assert [l["level"] for l in ctx.logs] == ["info", "warning", "error"]

    @pytest.mark.asyncio
    async def test_end_to_end_handler_with_executor_hooks(self):
        """Wire the real hooks into a real handler: drift → WARNING restored."""
        tracker = FakeTracker(
            before_orders={"O1": object()},
            after_orders={},                    # filled during gap
            before_pos={"AAPL": _pos(10)},
            after_pos={"AAPL": _pos(10)},
        )
        ctx = FakeContext()
        notify, reconcile = _build_reconnect_hooks(tracker, ctx, "acc", "OverseasStockRealAccountNode")
        h = ReconnectHandler(notify=notify, reconcile=reconcile)
        h._total_disconnection_sec = 3.0

        await h.on_reconnect_success()

        restored = [n for n in ctx.notifications if n["category"] == NotificationCategory.CONNECTION_RESTORED]
        assert len(restored) == 1
        assert restored[0]["severity"] == NotificationSeverity.WARNING
        assert restored[0]["data"]["reconcile"]["closed_or_filled_orders"] == ["O1"]
