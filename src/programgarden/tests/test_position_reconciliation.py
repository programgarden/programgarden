"""Restart corrections must preserve real trade evidence and fail closed."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import sqlite3

import pytest

from programgarden.database.position_reconciliation import (
    ReconciliationUnavailable, VerifiedPositionSnapshot,
)
from programgarden.database.workflow_position_tracker import WorkflowPositionTracker


def make_tracker(tmp_path, product="overseas_stock"):
    return WorkflowPositionTracker(str(tmp_path / "ledger.db"), "job", "broker",
                                   product=product, provider="ls", trading_mode="live",
                                   execution_key="project:execution")


async def buy(tracker, number, qty, price, symbol="AAA", *, owned=True):
    if owned:
        tracker.record_order(str(number), "20260916", symbol, "NASDAQ", "buy",
                             qty, price, "job", "buy")
    return await tracker.record_fill(str(number), "20260916", symbol, "NASDAQ",
                                     "buy", qty, price, f"1000{number:02d}",
                                     "40" if owned else "85", execution_id=str(number), currency="USD")


def snapshot(tracker, amounts):
    return VerifiedPositionSnapshot(
        "project:execution", tracker.product, tracker.provider, tracker.trading_mode,
        datetime.now(timezone.utc), amounts, "verified-test-broker",
        positions_complete=True, pending_orders_verified=True,
    )


async def reconcile(tracker, evidence, revision=None):
    return await tracker.reconcile_from_broker(
        evidence,
        expected_revision=tracker.fill_revision if revision is None else revision,
    )


def history(tracker):
    with sqlite3.connect(tracker.db_path) as conn:
        return conn.execute("SELECT * FROM trade_history ORDER BY id").fetchall()


async def test_trim_is_atomic_audited_and_not_a_sell(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 4, 10)
    await buy(tracker, 2, 6, 20)
    recorded = history(tracker)
    metrics = tracker.personal_metrics()
    notifications = []
    async def notified(*args):
        notifications.append(args)
    tracker.set_fill_classified_callback(notified)

    changed = await reconcile(tracker, snapshot(tracker, {"AAA": 7}))
    assert changed[0]["previous_quantity"] == "10"
    assert changed[0]["quantity"] == "7"
    position = tracker.get_workflow_positions()["AAA"]
    assert position.quantity == 7
    assert position.avg_price == Decimal(130) / 7
    assert history(tracker) == recorded
    assert {k: v for k, v in tracker.personal_metrics().items() if k != "as_of"} == {
        k: v for k, v in metrics.items() if k != "as_of"
    }
    assert notifications == []
    audit = tracker.get_position_adjustments()
    assert len(audit) == 1
    assert audit[0]["previous_quantity"] == "10"
    assert audit[0]["retained_quantity"] == "7"
    assert json.loads(audit[0]["removed_lots"])[0]["quantity"] == "3"
    assert await reconcile(tracker, snapshot(tracker, {"AAA": 7})) == []
    assert len(tracker.get_position_adjustments()) == 1


async def test_account_excess_is_never_imported_and_manual_lots_are_preserved(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    await buy(tracker, 2, 5, 30, owned=False)
    assert await reconcile(tracker, snapshot(tracker, {"AAA": 15, "MANUAL": 8})) == []
    assert set(tracker.get_workflow_positions()) == {"AAA"}
    assert tracker.get_workflow_positions()["AAA"].quantity == 10
    await reconcile(tracker, snapshot(tracker, {"AAA": 7}))
    with sqlite3.connect(tracker.db_path) as conn:
        assert conn.execute("SELECT remaining_qty FROM workflow_position_lots WHERE classification='manual'").fetchone()[0] == 5


async def test_explicit_complete_empty_snapshot_removes_owned_lots_only(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 0.75, 10)
    recorded = history(tracker)
    changed = await reconcile(tracker, snapshot(tracker, {}))
    assert changed[0]["removed_quantity"] == "0.75"
    assert tracker.get_workflow_positions() == {}
    assert history(tracker) == recorded


@pytest.mark.parametrize("change", [
    {"execution_key": "another-execution"}, {"product": "korea_stock"},
    {"provider": "other"}, {"trading_mode": "paper"},
    {"positions_complete": False}, {"pending_orders_verified": False},
    {"source": ""}, {"quantities": {"AAA": None}}, {"quantities": {"AAA": -1}},
    {"quantities": {"AAA": True}}, {"quantities": {"AAA": "NaN"}},
    {"quantities": {"AAA": "Infinity"}}, {"quantities": {"AAA": 1, " aaa ": 2}},
    {"quantities": {"": 0}},
])
async def test_invalid_or_wrong_account_snapshot_cannot_mutate_lots(tmp_path, change):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    with pytest.raises(ReconciliationUnavailable):
        await reconcile(tracker, replace(snapshot(tracker, {}), **change))
    assert tracker.get_workflow_positions()["AAA"].quantity == 10
    assert tracker.get_position_adjustments() == []


@pytest.mark.parametrize("seconds", [-130, 10])
async def test_stale_or_future_snapshot_is_held(tmp_path, seconds):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    evidence = replace(snapshot(tracker, {}), observed_at=datetime.now(timezone.utc) + timedelta(seconds=seconds))
    with pytest.raises(ReconciliationUnavailable, match="stale_account_snapshot"):
        await reconcile(tracker, evidence)
    assert tracker.get_workflow_positions()["AAA"].quantity == 10


async def test_fill_during_broker_read_invalidates_snapshot(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    revision = tracker.fill_revision
    evidence = snapshot(tracker, {"AAA": 7})
    await buy(tracker, 2, 2, 20)
    with pytest.raises(ReconciliationUnavailable, match="ledger_changed"):
        await reconcile(tracker, evidence, revision=revision)
    assert tracker.get_workflow_positions()["AAA"].quantity == 12
    assert tracker.get_position_adjustments() == []


async def test_reconciliation_rollback_and_domestic_symbol_identity(tmp_path):
    tracker = make_tracker(tmp_path, product="korea_stock")
    await buy(tracker, 1, 5, 20, symbol="005930")
    assert await reconcile(tracker, snapshot(tracker, {"A005930": 5})) == []
    with sqlite3.connect(tracker.db_path) as conn:
        conn.execute("""CREATE TRIGGER reject_adjustment BEFORE INSERT ON position_adjustments
                        BEGIN SELECT RAISE(ABORT, 'audit write failed'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="audit write failed"):
        await reconcile(tracker, snapshot(tracker, {}))
    assert tracker.get_workflow_positions()["005930"].quantity == 5
    assert tracker.get_position_adjustments() == []


def test_database_rejects_another_execution_even_if_path_is_reused(tmp_path):
    tracker = make_tracker(tmp_path)
    with pytest.raises(ValueError, match="storage identity"):
        WorkflowPositionTracker(tracker.db_path, "job2", "broker", execution_key="other")
    with pytest.raises(ValueError, match="storage identity"):
        WorkflowPositionTracker(tracker.db_path, "legacy-job", "broker")


@pytest.mark.parametrize("filled", [0, 1])
async def test_missing_or_partial_sell_holds_before_trimming(tmp_path, filled):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    tracker.record_order("2", "20260916", "AAA", "NASDAQ", "sell", 3, 25, "job", "sell")
    if filled:
        await tracker.record_fill("2", "20260916", "AAA", "NASDAQ", "sell", 1, 25,
                                  "110000", "40", execution_id="21")
    recorded = history(tracker)
    with pytest.raises(ReconciliationUnavailable, match="owned_fills_require_reconciliation"):
        await reconcile(tracker, snapshot(tracker, {"AAA": 7}))
    assert history(tracker) == recorded
    assert tracker.get_workflow_positions()["AAA"].quantity == 10 - filled
    assert tracker.get_position_adjustments() == []
    # Once the real missing event arrives, no synthetic trim is necessary.
    await tracker.record_fill("2", "20260916", "AAA", "NASDAQ", "sell", 3 - filled, 25,
                              "110001", "40", execution_id="22")
    assert await reconcile(tracker, snapshot(tracker, {"AAA": 7})) == []
    assert tracker.get_workflow_positions()["AAA"].quantity == 7


async def test_cancel_does_not_erase_evidence_of_a_missing_partial_fill(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    tracker.record_order("2", "20260916", "AAA", "NASDAQ", "sell", 3, 25, "job", "sell")
    assert tracker.cancel_order("2", "20260916")
    with pytest.raises(ReconciliationUnavailable, match="owned_fills_require_reconciliation"):
        await reconcile(tracker, snapshot(tracker, {"AAA": 9}))
    assert tracker.get_workflow_positions()["AAA"].quantity == 10


async def test_late_manual_sell_does_not_reduce_adjusted_lots_twice(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    await reconcile(tracker, snapshot(tracker, {"AAA": 7}))
    await tracker.record_fill("99", "20260916", "AAA", "NASDAQ", "sell", 3, 25,
                              "110000", "85", execution_id="99")
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    assert len(tracker.get_position_adjustments()) == 1


async def test_active_external_order_blocks_a_quantity_trim(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    evidence = replace(snapshot(tracker, {"AAA": 7}), pending_orders=({
        "order_date": "20260916", "order_id": "99", "symbol": "AAA", "side": "sell",
        "remaining_quantity": 3,
    },))
    with pytest.raises(ReconciliationUnavailable, match="position_has_pending_orders"):
        await reconcile(tracker, evidence)
    assert tracker.get_workflow_positions()["AAA"].quantity == 10


@pytest.mark.parametrize("identity", [{"product": "korea_stock"}, {"trading_mode": "paper"}, {"provider": "other"}])
def test_same_execution_cannot_open_another_product_or_mode(tmp_path, identity):
    tracker = make_tracker(tmp_path)
    with pytest.raises(ValueError, match="storage identity"):
        WorkflowPositionTracker(tracker.db_path, "job2", "broker",
                                execution_key=tracker.execution_key, **identity)
