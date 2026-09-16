"""Terminal aggregate recovery must never double-count a late broker fill."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sqlite3
from unittest.mock import AsyncMock

import pytest

from programgarden.database.order_recovery import VerifiedOrderTotal
from programgarden.database.position_reconciliation import ReconciliationUnavailable
from programgarden.database.workflow_position_tracker import (
    WorkflowPositionTracker, ExecutionIdentityConflictError,
)
from test_position_reconciliation import buy, snapshot


def make_tracker(tmp_path):
    return WorkflowPositionTracker(str(tmp_path / "ledger.db"), "job", "broker",
                                   execution_key="project:execution")


def order(tracker, number="2", side="sell", qty=3):
    tracker.record_order(number, "20260916", "AAA", "NASDAQ", side, qty, 25, "job", side)


def total(tracker, number="2", side="sell", qty=3, price=25):
    return VerifiedOrderTotal(tracker.execution_key, tracker.product, tracker.provider,
                              tracker.trading_mode, "20260916", number, "AAA", side,
                              Decimal(str(qty)), Decimal(str(qty)), Decimal(str(price)),
                              Decimal(0), "USD", "110000000", datetime.now(timezone.utc))


async def recover(tracker, *totals):
    return await tracker.recover_order_totals(totals, expected_revision=tracker.fill_revision)


async def late(tracker, execution="21", qty=3, price=25, side="sell", time="110000000"):
    return await tracker.record_fill("2", "20260916", "AAA", "NASDAQ", side,
                                     qty, price, time, "40", execution_id=execution, currency="USD")


def history(tracker):
    with sqlite3.connect(tracker.db_path) as conn:
        return conn.execute("SELECT * FROM trade_history ORDER BY id").fetchall()


async def test_missing_sell_recovers_quantity_estimate_without_fill_or_win(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    before = history(tracker)
    callback = AsyncMock()
    tracker.set_fill_classified_callback(callback)
    result = await recover(tracker, total(tracker))
    assert Decimal(result[0]["estimated_pnl"]) == 15
    assert result[0]["is_trade"] is False
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    assert history(tracker) == before
    callback.assert_not_awaited()
    metrics = tracker.personal_metrics()
    assert metrics["closed_trade_count"] == metrics["winning_trade_count"] == 0
    assert metrics["executed_order_count"] == 1
    assert metrics["closed_trade_reason"] == "aggregate_recovery_excluded"
    assert metrics["realized_pnl"][0]["amount"] == 15
    assert metrics["realized_pnl"][0]["status"] == "estimated"
    assert await tracker.reconcile_from_broker(snapshot(tracker, {"AAA": 7}),
                                               expected_revision=tracker.fill_revision) == []
    assert await recover(tracker, total(tracker)) == []
    assert len(tracker.get_order_recoveries()) == 1


async def test_late_partial_execs_are_covered_persistently_and_emit_nothing(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    await recover(tracker, total(tracker))
    before = history(tracker)
    callback = AsyncMock()
    tracker.set_fill_classified_callback(callback)
    assert await late(tracker, qty=1) == "workflow"
    assert await late(tracker, qty=1.0, price=25.0) == "workflow"
    tracker = make_tracker(tmp_path)
    tracker.set_fill_classified_callback(callback)
    assert await late(tracker, execution="22", qty=2) == "workflow"
    assert history(tracker) == before
    assert tracker.get_workflow_positions()["AAA"].quantity == 7

    callback.assert_not_awaited()
    with pytest.raises(ExecutionIdentityConflictError):
        await late(tracker, execution="23", qty=1)
    with pytest.raises(ExecutionIdentityConflictError):
        await late(tracker, qty=1, price=26)
    assert tracker.get_workflow_positions()["AAA"].quantity == 7


async def test_adjacent_date_cannot_replay_recovery_but_explicit_new_order_can(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    await recover(tracker, total(tracker))
    with pytest.raises(ExecutionIdentityConflictError, match="date may overlap"):
        await tracker.record_fill("2", "20260917", "AAA", "NASDAQ", "sell", 3, 25,
                                  "110000000", "40", execution_id="21", currency="USD")
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    tracker.record_order("2", "20260917", "AAA", "NASDAQ", "sell", 1, 26, "job", "sell")
    await tracker.record_fill("2", "20260917", "AAA", "NASDAQ", "sell", 1, 26,
                              "110000000", "40", execution_id="21", currency="USD")
    assert tracker.get_workflow_positions()["AAA"].quantity == 6


async def test_legacy_date_window_fill_is_not_duplicated_by_exact_date_recovery(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    await late(tracker)
    with sqlite3.connect(tracker.db_path) as conn:
        conn.execute("UPDATE trade_history SET order_date='20260917' WHERE side='sell'")
    with pytest.raises(ReconciliationUnavailable, match="historical_fill_date_ambiguous"):
        await recover(tracker, total(tracker))
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    assert tracker.get_order_recoveries() == []


async def test_known_partial_fill_is_not_recovered_twice_and_remains_scorable(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    await late(tracker, qty=1, price=23, time="105959000")
    result = await recover(tracker, total(tracker, price=25))
    assert result[0]["quantity"] == "2"
    assert Decimal(result[0]["estimated_pnl"]) == 12
    await late(tracker, qty=1, price=23, time="105959000")
    await late(tracker, execution="22", qty=2, price=26)
    metrics = tracker.personal_metrics()
    assert metrics["closed_trade_count"] == 1
    assert metrics["winning_trade_count"] == 1
    assert metrics["executed_order_count"] == 2
    assert metrics["realized_pnl"][0]["amount"] == 15
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    assert len(history(tracker)) == 2


async def test_recovered_buy_cost_basis_is_estimated_when_later_sold(tmp_path):
    tracker = make_tracker(tmp_path)
    order(tracker, side="buy", qty=3)
    await recover(tracker, total(tracker, side="buy", price=20))
    await late(tracker, side="buy", price=20)
    order(tracker, number="3", side="sell", qty=3)
    await tracker.record_fill("3", "20260916", "AAA", "NASDAQ", "sell", 3, 25,
                              "120000000", "40", execution_id="31", currency="USD")
    metrics = tracker.personal_metrics()
    assert metrics["realized_pnl"][0]["amount"] == 15
    assert metrics["realized_pnl"][0]["status"] == "estimated"
    assert metrics["winning_trade_count"] == 0
    assert tracker.get_workflow_positions() == {}
    assert metrics["executed_order_count"] == 1
    assert len(history(tracker)) == 1


@pytest.mark.parametrize("changes", [
    {"execution_key": "wrong"}, {"trading_mode": "paper"}, {"provider": "wrong"},
    {"symbol": "OTHER"}, {"side": "buy"}, {"order_date": "20260915"},
    {"order_no": "99"}, {"remaining_quantity": 1}, {"filled_quantity": 2},
    {"ordered_quantity": 4, "filled_quantity": 4}, {"original_order_no": "1"},
    {"currency": ""}, {"average_price": 0}, {"average_price": "NaN"},
    {"fill_time": "unknown"}, {"observed_at": datetime.now(timezone.utc)-timedelta(minutes=5)},
])
async def test_unverified_or_conflicting_total_cannot_change_quantity(tmp_path, changes):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    with pytest.raises(ReconciliationUnavailable):
        await recover(tracker, replace(total(tracker), **changes))
    assert tracker.get_workflow_positions()["AAA"].quantity == 10
    assert tracker.get_order_recoveries() == []


async def test_batch_rollback_unknown_basis_and_revision_hold(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 3, 20)
    order(tracker)
    order(tracker, number="3", qty=4)
    revision = tracker.fill_revision
    with pytest.raises(ReconciliationUnavailable, match="cost_basis"):
        await recover(tracker, total(tracker), replace(total(tracker, number="3", qty=4), fill_time="120000000"))
    assert tracker.get_workflow_positions()["AAA"].quantity == 3
    assert tracker.get_order_recoveries() == []
    with pytest.raises(ReconciliationUnavailable, match="ledger_changed"):
        await tracker.recover_order_totals([total(tracker)], expected_revision=revision-1)
    with sqlite3.connect(tracker.db_path) as conn:
        conn.execute("""CREATE TRIGGER fail_recovery BEFORE INSERT ON workflow_order_recoveries
                        BEGIN SELECT RAISE(ABORT, 'audit failure'); END""")
    with pytest.raises(sqlite3.IntegrityError):
        await recover(tracker, total(tracker))
    assert tracker.get_workflow_positions()["AAA"].quantity == 3


async def test_conflicting_second_snapshot_does_not_rewrite_first_estimate(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    await recover(tracker, total(tracker))
    with pytest.raises(ReconciliationUnavailable, match="conflicting_order_total"):
        await recover(tracker, total(tracker, price=26))
    assert Decimal(tracker.get_order_recoveries()[0]["estimated_pnl"]) == 15


async def test_legacy_unidentified_aggregate_is_covered_without_inventory_replay(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    await tracker.record_fill("2", "20260916", "AAA", "NASDAQ", "sell", 3, 25,
                              "110000000", "40", currency="USD")
    before = history(tracker)
    result = await recover(tracker, total(tracker))
    assert Decimal(result[0]["quantity"]) == 0
    assert history(tracker) == before
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    await late(tracker)
    assert history(tracker) == before
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    metrics = tracker.personal_metrics()
    assert metrics["version"] == 3
    assert metrics["winning_trade_count"] == 0
    assert metrics["realized_pnl"][0]["amount"] == 15
    assert metrics["realized_pnl"][0]["recovery_gross_profit"] == 15
    assert await tracker.reconcile_from_broker(snapshot(tracker, {"AAA": 7}),
                                               expected_revision=tracker.fill_revision) == []


async def test_legacy_partial_and_missing_total_share_one_late_fill_coverage(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    await tracker.record_fill("2", "20260916", "AAA", "NASDAQ", "sell", 1, 25,
                              "105959000", "40", currency="USD")
    await recover(tracker, total(tracker))
    await late(tracker, qty=1, execution="21", time="105959000")
    await late(tracker, qty=2, execution="22")
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    metrics = tracker.personal_metrics()
    assert metrics["winning_trade_count"] == 0
    assert metrics["realized_pnl"][0]["amount"] == 15


async def test_recovery_money_does_not_change_the_measured_profit_loss_ratio(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    await recover(tracker, total(tracker))
    for number, price in [(3, 22), (4, 19)]:
        order(tracker, number=str(number), qty=1)
        await tracker.record_fill(str(number), "20260916", "AAA", "NASDAQ", "sell", 1, price,
                                  f"12000{number}000", "40", execution_id=str(number), currency="USD")
    metrics = tracker.personal_metrics()
    assert metrics["closed_trade_count"] == 2
    assert metrics["winning_trade_count"] == 1
    assert metrics["profit_loss_ratio"] == 2
    assert metrics["realized_pnl"][0]["gross_profit"] == 17
    assert metrics["realized_pnl"][0]["recovery_gross_profit"] == 15
