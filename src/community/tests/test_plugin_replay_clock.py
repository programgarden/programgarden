"""RollManagement and TimeBasedExit read the replay fixture clock.

A credential-free replay runs at ``context.validation_as_of``. Before 2.3.2 both
plugins read the wall clock, so the same replay took a different branch on a
different day (and a rollover check could never be shown "near expiry").
Live contexts have no ``validation_as_of`` and keep the wall clock.
"""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from programgarden_community.plugins._replay_clock import fixture_now
from programgarden_community.plugins.roll_management import roll_management_condition
from programgarden_community.plugins.time_based_exit import time_based_exit_condition


class _ReplayCtx:
    def __init__(self, as_of, tracker=None):
        self.validation_as_of = as_of
        self.risk_tracker = tracker


class _MemoryTracker:
    def __init__(self, state=None):
        self.state = dict(state or {})

    def load_state(self, key):
        return self.state.get(key)

    def save_state(self, key, value):
        self.state[key] = value
        return True

    def delete_state(self, key):
        self.state.pop(key, None)

    def list_state_keys(self, prefix=""):
        return [k for k in self.state if k.startswith(prefix)]


def test_fixture_now_reads_only_a_timezone_aware_instant():
    assert fixture_now(_ReplayCtx("2026-12-14T15:00:00Z")) == datetime(2026, 12, 14, 15, 0)
    assert fixture_now(_ReplayCtx("2026-12-14T09:00:00+09:00")) == datetime(2026, 12, 14, 9, 0)
    assert fixture_now(_ReplayCtx("2026-12-14T15:00:00")) is None        # no offset
    assert fixture_now(_ReplayCtx(None)) is None
    assert fixture_now(None) is None
    assert fixture_now(MagicMock()) is None                                # live mock context


@pytest.mark.asyncio
@pytest.mark.parametrize("as_of,should_roll,days", [
    ("2026-12-14T15:00:00Z", True, 3),     # MESZ26 third Friday 2026-12-18
    ("2026-10-01T15:00:00Z", False, 77),
])
async def test_roll_management_judges_at_the_fixture_instant(as_of, should_roll, days):
    out = await roll_management_condition(
        positions=[{"symbol": "MESZ26", "current_price": 6050.25, "qty": 1, "exchange": "CME"}],
        fields={"days_before_expiry": 5}, context=_ReplayCtx(as_of))
    row = out["symbol_results"][0]
    assert row["days_to_expiry"] == days
    assert row["should_roll"] is should_roll
    assert out["result"] is should_roll


@pytest.mark.asyncio
async def test_roll_management_live_context_keeps_the_wall_clock():
    out = await roll_management_condition(
        positions=[{"symbol": "MESZ26", "current_price": 1, "qty": 1, "exchange": "CME"}],
        fields={"days_before_expiry": 5}, context=MagicMock(risk_tracker=None))
    expected = (datetime(2026, 12, 18) - datetime.now()).days
    assert out["symbol_results"][0]["days_to_expiry"] == expected


@pytest.mark.asyncio
async def test_time_based_exit_counts_hold_days_at_the_fixture_date():
    tracker = _MemoryTracker({"time_exit.AAPL.entry_date": "2026-09-14"})
    out = await time_based_exit_condition(
        positions=[{"symbol": "AAPL", "qty": 10, "market_code": "82"}],
        fields={"max_hold_days": 5, "warn_days": 2},
        context=_ReplayCtx("2026-09-19T14:30:00Z", tracker))
    row = out["symbol_results"][0]
    assert row["hold_days"] == 5 and row["action"] == "exit"


@pytest.mark.asyncio
async def test_time_based_exit_records_the_fixture_date_as_entry():
    tracker = _MemoryTracker()
    await time_based_exit_condition(
        positions=[{"symbol": "AAPL", "qty": 10, "market_code": "82"}],
        fields={"max_hold_days": 5}, context=_ReplayCtx("2026-09-14T14:30:00Z", tracker))
    assert tracker.state["time_exit.AAPL.entry_date"] == "2026-09-14"
