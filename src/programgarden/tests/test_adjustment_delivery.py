"""Adjustment delivery survives restart and acknowledges one destination only."""

import sqlite3
import pytest
from test_order_total_recovery import make_tracker
from test_position_reconciliation import buy, snapshot


async def test_delivery_replays_until_ack_and_keeps_original_audit(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 5, 10)
    await tracker.reconcile_from_broker(snapshot(tracker, {"AAA": 2}), expected_revision=tracker.fill_revision)
    pending = tracker.pending_position_adjustments("https://dev/ingest")
    assert len(pending) == 1 and pending[0]["symbol"] == "AAA"
    assert pending[0]["previous_quantity"] == "5" and pending[0]["retained_quantity"] == "2"
    assert "removed_lots" not in pending[0] and "provider" not in pending[0]
    reopened = make_tracker(tmp_path)
    assert reopened.pending_position_adjustments("https://dev/ingest") == pending
    ids = [pending[0]["adjustment_id"]]
    reopened.acknowledge_position_adjustments("https://dev/ingest", ids)
    reopened.acknowledge_position_adjustments("https://dev/ingest", ids)
    assert reopened.pending_position_adjustments("https://dev/ingest") == []
    assert reopened.pending_position_adjustments("https://prod/ingest") == pending
    assert len(reopened.get_position_adjustments()) == 1


def test_empty_ledger_and_invalid_acknowledgements(tmp_path):
    tracker = make_tracker(tmp_path)
    assert tracker.pending_position_adjustments("api") == []
    tracker.acknowledge_position_adjustments("api", [999])
    for ids in ([True], [0], [-1], ["1"], list(range(1, 502))):
        with pytest.raises(ValueError):
            tracker.acknowledge_position_adjustments("api", ids)
    for limit in (0, True, 501):
        with pytest.raises(ValueError):
            tracker.pending_position_adjustments("api", limit)


async def test_transport_failure_and_invalid_ack_never_drop_audit(tmp_path):
    from programgarden.database.adjustment_delivery import AdjustmentDelivery
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 5, 10)
    await tracker.reconcile_from_broker(snapshot(tracker, {"AAA": 2}), expected_revision=tracker.fill_revision)
    responses = [OSError("offline"), [True], [999], {"accepted_ids": [1]}, [], [1]]
    payloads = []

    async def send(rows):
        payloads.append(rows)
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    delivery = AdjustmentDelivery(lambda: tracker, "api/run", send)
    for _ in range(5):
        await delivery.flush()
        assert len(tracker.pending_position_adjustments("api/run")) == 1
    await delivery.flush()
    assert len(payloads) == 6 and all(rows == payloads[0] for rows in payloads)
    assert tracker.pending_position_adjustments("api/run") == []
    assert len(tracker.get_position_adjustments()) == 1


async def test_delivery_stop_cancels_inflight_and_replays_final_flush(tmp_path):
    import asyncio
    from programgarden.database.adjustment_delivery import AdjustmentDelivery
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 5, 10)
    await tracker.reconcile_from_broker(snapshot(tracker, {"AAA": 2}), expected_revision=tracker.fill_revision)
    started = asyncio.Event()
    calls = []

    async def send(rows):
        calls.append(rows)
        if len(calls) == 1:
            started.set()
            await asyncio.Event().wait()
        return [row["adjustment_id"] for row in rows]

    delivery = AdjustmentDelivery(lambda: tracker, "api/run", send)
    delivery.start()
    await asyncio.wait_for(started.wait(), timeout=1)
    await delivery.stop()
    assert delivery.task is None and len(calls) == 2
    assert tracker.pending_position_adjustments("api/run") == []


async def test_delivery_acknowledges_only_accepted_subset(tmp_path):
    from programgarden.database.adjustment_delivery import AdjustmentDelivery
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 5, 10)
    for quantity in [3, 1]:
        await tracker.reconcile_from_broker(snapshot(tracker, {"AAA": quantity}), expected_revision=tracker.fill_revision)

    async def send(rows):
        assert len(rows) == 2
        return [rows[0]["adjustment_id"]]

    await AdjustmentDelivery(lambda: tracker, "api/run", send).flush()
    pending = tracker.pending_position_adjustments("api/run")
    assert len(pending) == 1 and pending[0]["retained_quantity"] == "1"
