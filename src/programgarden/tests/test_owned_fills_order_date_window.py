"""A fill recorded under its execution date must still be evidence for an order
placed one day earlier (or later).

The fill tracker associates a fill with an order whose recorded date differs by
at most one day (``_order_date_window``) and stores the fill under the fill's own
execution date, not the order's. ``assert_order_evidence`` used to match fills to
orders on the exact ``order_date`` only, so a futures order placed on D that fills
on D+1 (paper night session / the 07:00 KST business-day roll) looked like it had
zero fills on every restart. Futures has no missing-fill recovery path, so the run
stayed held at the broker node forever (``owned_fills_require_reconciliation``).
These tests reproduce the customer case and pin the guards of the window match.
"""

from datetime import datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

from programgarden.database.position_reconciliation import (
    ReconciliationUnavailable, VerifiedPositionSnapshot,
)
from programgarden.database.workflow_position_tracker import WorkflowPositionTracker


def make_tracker(tmp_path, product, trading_mode):
    return WorkflowPositionTracker(str(tmp_path / "ledger.db"), "job", "broker",
                                   product=product, provider="ls", trading_mode=trading_mode,
                                   execution_key="project:execution")


def snapshot(tracker, amounts):
    return VerifiedPositionSnapshot(
        "project:execution", tracker.product, tracker.provider, tracker.trading_mode,
        datetime.now(timezone.utc), amounts, "verified-test-broker",
        positions_complete=True, pending_orders_verified=True,
    )


async def reconcile(tracker, amounts):
    return await tracker.reconcile_from_broker(
        snapshot(tracker, amounts), expected_revision=tracker.fill_revision)


def fill_dates(tracker):
    with sqlite3.connect(tracker.db_path) as conn:
        return [r[0] for r in conn.execute(
            "SELECT order_date FROM trade_history ORDER BY id").fetchall()]


async def test_customer_case_futures_fill_on_next_business_day_is_recognised(tmp_path):
    """Exact customer case (project 2f978474): MNQ buy #24 placed 20261018,
    filled 20261019, then a restart. Must fail-first before the fix and pass now."""
    tracker = make_tracker(tmp_path, "overseas_futures", "paper")
    tracker.record_order("24", "20261018", "MNQZ26", "CME", "buy", 1, 100.0, "job", "mnq_buy_order")
    result = await tracker.record_fill("24", "20261019", "MNQZ26", "CME", "buy", 1, 100.0,
                                       "090000000", "40", execution_id="ex-24", currency="USD")
    # The fill is our workflow order's, stored under its own execution date (D+1).
    assert result == "workflow"
    assert fill_dates(tracker) == ["20261019"]
    # Restart reconcile: the held MNQ lot is accounted for, nothing is trimmed.
    assert await reconcile(tracker, {"MNQZ26": 1}) == []
    assert tracker.get_workflow_positions()["MNQZ26"].quantity == 1


async def test_adjacent_day_reused_order_number_is_not_double_counted(tmp_path):
    """The broker order number resets daily, so #24 can exist on both days. One
    fill under 20261019 is evidence for exactly one of them; the earlier order
    must not borrow it through its D+1 window and wrongly release."""
    tracker = make_tracker(tmp_path, "overseas_futures", "paper")
    tracker.record_order("24", "20261018", "MNQZ26", "CME", "buy", 1, 100.0, "job", "buy_a")
    tracker.record_order("24", "20261019", "MNQZ26", "CME", "buy", 1, 100.0, "job", "buy_b")
    result = await tracker.record_fill("24", "20261019", "MNQZ26", "CME", "buy", 1, 100.0,
                                       "090000000", "40", execution_id="ex-24b", currency="USD")
    assert result == "workflow"
    assert fill_dates(tracker) == ["20261019"]
    # 20261019/#24 is covered by its exact fill; 20261018/#24 has none -> held.
    with pytest.raises(ReconciliationUnavailable, match="owned_fills_require_reconciliation"):
        await reconcile(tracker, {"MNQZ26": 1})
    assert tracker.get_position_adjustments() == []


async def test_true_missing_fill_still_raises(tmp_path):
    """No fill at all, and a partial window fill short of the ordered quantity,
    both stay held — the window never manufactures the missing evidence."""
    # (a) order with no fill anywhere.
    tracker = make_tracker(tmp_path, "overseas_futures", "paper")
    tracker.record_order("51", "20261018", "MNQZ26", "CME", "buy", 1, 100.0, "job", "buy_c")
    with pytest.raises(ReconciliationUnavailable, match="owned_fills_require_reconciliation"):
        await reconcile(tracker, {"MNQZ26": 1})
    # (b) ordered 2, only 1 filled on the next day -> still one short.
    other = make_tracker(tmp_path / "b", "overseas_futures", "paper")
    other.record_order("52", "20261018", "MNQZ26", "CME", "buy", 2, 100.0, "job", "buy_d")
    assert await other.record_fill("52", "20261019", "MNQZ26", "CME", "buy", 1, 100.0,
                                   "090000000", "40", execution_id="ex-52", currency="USD") == "workflow"
    with pytest.raises(ReconciliationUnavailable, match="owned_fills_require_reconciliation"):
        await other.reconcile_from_broker(snapshot(other, {"MNQZ26": 2}),
                                          expected_revision=other.fill_revision)


async def test_overseas_stock_same_day_path_is_unchanged(tmp_path):
    """The overseas-stock happy path (same-day fill) reconciles with no change,
    and a stock order with no fill still fails closed — nothing regresses."""
    tracker = make_tracker(tmp_path, "overseas_stock", "live")
    tracker.record_order("1", "20260916", "AAPL", "NASDAQ", "buy", 10, 20.0, "job", "buy")
    assert await tracker.record_fill("1", "20260916", "AAPL", "NASDAQ", "buy", 10, 20.0,
                                     "110000", "40", execution_id="1", currency="USD") == "workflow"
    assert fill_dates(tracker) == ["20260916"]
    before = fill_dates(tracker)
    assert await reconcile(tracker, {"AAPL": 10}) == []
    assert fill_dates(tracker) == before
    assert tracker.get_workflow_positions()["AAPL"].quantity == 10
    # A genuinely unproven stock order still holds.
    tracker.record_order("2", "20260916", "AAPL", "NASDAQ", "sell", 3, 25.0, "job", "sell")
    with pytest.raises(ReconciliationUnavailable, match="owned_fills_require_reconciliation"):
        await reconcile(tracker, {"AAPL": 7})
