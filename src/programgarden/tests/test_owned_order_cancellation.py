"""Actual adapter requests must remain owned, single-attempt and non-liquidating."""

from datetime import datetime, timezone, timedelta
from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import sqlite3

import pytest
from programgarden_finance import COSAQ00102, COSOQ00201
from programgarden.database.broker_snapshot import BrokerStartupSnapshot
from programgarden.database.owned_order_cancellation import cancel_owned_pending_orders, owned_targets
from programgarden.database.position_reconciliation import ReconciliationUnavailable, VerifiedPositionSnapshot
from programgarden.executor import CancelOrderNodeExecutor, WorkflowJob
from test_execution_broker_snapshot import query
from test_order_total_recovery import make_tracker, order
from test_order_cancellation_evidence import rows


def snapshot(tracker, orders=None):
    pending = ({"order_date": "20260916", "order_id": "2", "symbol": "AAA", "side": "sell",
                "market_code": "82", "remaining_quantity": 3},) if orders is None else tuple(orders)
    return VerifiedPositionSnapshot(tracker.execution_key, tracker.product, tracker.provider,
                                    tracker.trading_mode, datetime.now(timezone.utc), {}, "test",
                                    True, True, pending)


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr("programgarden.database.owned_order_cancellation.asyncio.sleep", AsyncMock())


async def test_actual_sdk_adapter_cancels_only_owned_original_once(tmp_path):
    tracker = make_tracker(tmp_path)
    day = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d")
    tracker.record_order("2", day, "AAA", "NASDAQ", "sell", 3, 25, "job", "sell")
    writes = []
    def history(request):
        data = rows() if request.ExecYn == "0" else [dict(rows()[0], UnercQty=3),
                                                     dict(rows()[0], OrdNo=99, ShtnIsuNo="MANUAL", UnercQty=3)]
        return query(COSAQ00102, "COSAQ00102", request, data)
    def positions(request):
        return query(COSOQ00201, "COSOQ00201", request, [])
    def cancel(request):
        from programgarden_finance.ls.overseas_stock.order.COSAT00301.blocks import COSAT00301OutBlock2
        writes.append(request)
        assert request.OrdPtnCode == "08" and request.OrgOrdNo == 2
        assert request.OrdQty == 0 and request.OvrsOrdPrc == 0
        assert request.IsuNo == "AAA" and request.OrdMktCode == "82"
        return NS(req_async=AsyncMock(return_value=NS(error_msg=None, block2=COSAT00301OutBlock2(OrdNo=3))))
    stock = NS(accno=lambda: NS(cosoq00201=positions, cosaq00102=history),
               주문=lambda: NS(cosat00301=cancel))
    ls = NS(overseas_stock=lambda: stock)
    context = NS(log=lambda *args: None)
    async def send(target):
        return await CancelOrderNodeExecutor()._cancel_overseas_stock(
            ls, target["order_no"], target["symbol"], target["exchange"], {}, context, "cancel")
    for _ in range(2):
        result = await cancel_owned_pending_orders(ls, tracker, send, can_send=lambda: True)
        assert result["status"] == "confirmed"
        assert result["cancelled_orders"] == [{"order_date": day, "order_no": "2"}]
        assert result["pending_orders"] == []
    assert len(writes) == 1
    with sqlite3.connect(tracker.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM trade_history").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM workflow_position_lots").fetchone()[0] == 0


async def test_unknown_submission_and_missing_pending_row_never_mean_cancelled(tmp_path, monkeypatch):
    tracker = make_tracker(tmp_path)
    order(tracker)
    snap = snapshot(tracker)
    read = AsyncMock(return_value=BrokerStartupSnapshot(snap, snap.pending_orders))
    monkeypatch.setattr("programgarden.database.owned_order_cancellation.read_broker_snapshot", read)
    monkeypatch.setattr("programgarden.database.owned_order_cancellation.read_stock_order_outcomes",
                        AsyncMock(side_effect=ReconciliationUnavailable("partial_unknown")))
    send = AsyncMock(side_effect=TimeoutError())
    for pending in (snap.pending_orders, ()):
        read.return_value = BrokerStartupSnapshot(replace(snap, pending_orders=pending), pending)
        result = await cancel_owned_pending_orders(None, tracker, send, can_send=lambda: True)
        assert result["status"] == "confirmation_pending" and result["cancelled_orders"] == []
        assert result["pending_orders"] == [{"order_date": "20260916", "order_no": "2"}]
    assert send.await_count == 1


@pytest.mark.parametrize("updates", [{"symbol": "OTHER"}, {"side": "buy"}, {"market_code": "81"},
                                     {"remaining_quantity": 4}, {"remaining_quantity": 0}])
def test_conflicting_pending_identity_blocks_whole_batch(tmp_path, updates):
    tracker = make_tracker(tmp_path)
    order(tracker)
    snap = snapshot(tracker)
    bad = dict(snap.pending_orders[0], **updates)
    with pytest.raises(ReconciliationUnavailable):
        owned_targets(tracker, replace(snap, pending_orders=(bad,)))


@pytest.mark.parametrize("updates", [{"positions_complete": False}, {"pending_orders_verified": False},
                                     {"execution_key": "other"}, {"trading_mode": "paper"},
                                     {"observed_at": datetime.now(timezone.utc)-timedelta(minutes=3)}])
def test_incomplete_stale_or_wrong_scope_blocks_requests(tmp_path, updates):
    tracker = make_tracker(tmp_path)
    order(tracker)
    with pytest.raises(ReconciliationUnavailable):
        owned_targets(tracker, replace(snapshot(tracker), **updates))


async def test_failed_read_or_unpaused_execution_sends_nothing(tmp_path, monkeypatch):
    tracker = make_tracker(tmp_path)
    order(tracker)
    read = AsyncMock(side_effect=RuntimeError("query_failed"))
    monkeypatch.setattr("programgarden.database.owned_order_cancellation.read_broker_snapshot", read)
    send = AsyncMock()
    with pytest.raises(ReconciliationUnavailable):
        await cancel_owned_pending_orders(None, tracker, send, can_send=lambda: False)
    assert read.await_count == 0
    with pytest.raises(RuntimeError, match="query_failed"):
        await cancel_owned_pending_orders(None, tracker, send, can_send=lambda: True)
    assert send.await_count == 0


async def test_job_rejects_running_nodes_and_requires_restart(tmp_path):
    from programgarden_core.bases.listener import NodeState
    job = object.__new__(WorkflowJob)
    job.status = "paused"
    job._node_states = {"buy": NodeState.RUNNING}
    job.context = NS(is_paused=True, is_shutdown=False, is_dry_run=False,
                     _workflow_position_tracker=make_tracker(tmp_path))
    with pytest.raises(ReconciliationUnavailable):
        await job.cancel_pending_orders()
    job._cancellation_requires_restart = True
    with pytest.raises(RuntimeError, match="Restart"):
        await job.resume()
