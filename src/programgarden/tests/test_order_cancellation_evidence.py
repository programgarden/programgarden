"""Exercise broker evidence, durable cancellation and restart against real SQLite."""

from dataclasses import replace
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import sqlite3
from types import SimpleNamespace as NS

import pytest
from programgarden_finance import COSAQ00102
from programgarden.database.broker_order_totals import read_stock_order_outcomes
from programgarden.database.broker_evidence import StartupEvidenceUnavailable
from programgarden.database.order_cancellation import record_cancellations
from programgarden.database.order_recovery import orders_needing_recovery
from programgarden.database.position_reconciliation import ReconciliationUnavailable, VerifiedPositionSnapshot
from test_execution_broker_snapshot import query
from test_order_total_recovery import make_tracker, order


def rows():
    common = dict(ShtnIsuNo="AAA", BnsTpCode="1", OrdMktCode="82", OrdQty=3,
                  ExecQty=0, AllExecQty=0, UnercQty=0, MrcTpCode="", OrdTrxPtnCode="0")
    return [dict(common, OrdNo=2, OrgOrdNo=0),
            dict(common, OrdNo=3, OrgOrdNo=2, CnfQty=3, MrcTpNm="취소", OrdTrxPtnNm="취소완료")]


async def evidence(tracker, data=None):
    calls = []
    def orders(request):
        calls.append(request)
        return query(COSAQ00102, "COSAQ00102", request, rows() if data is None else data)
    ls = NS(overseas_stock=lambda: NS(accno=lambda: NS(cosaq00102=orders)))
    totals, cancellations = await read_stock_order_outcomes(ls, tracker, orders_needing_recovery(tracker))
    assert calls[0].ExecYn == "0" and calls[0].ThdayBnsAppYn == "0"
    return totals, cancellations


async def test_confirmed_unfilled_cancellation_unblocks_restart_without_a_trade(tmp_path):
    tracker = make_tracker(tmp_path)
    order(tracker)
    totals, cancellations = await evidence(tracker)
    assert totals == [] and len(cancellations) == 1
    await tracker.recover_order_totals(totals, cancellations=cancellations,
                                      expected_revision=tracker.fill_revision)
    assert orders_needing_recovery(tracker) == []
    assert record_cancellations(tracker, cancellations) == 0
    with sqlite3.connect(tracker.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM workflow_orders").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM trade_history").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM workflow_position_lots").fetchone()[0] == 0
    snapshot = VerifiedPositionSnapshot(
        tracker.execution_key, tracker.product, tracker.provider, tracker.trading_mode,
        datetime.now(timezone.utc), {}, "test", True, True)
    assert await tracker.reconcile_from_broker(snapshot, expected_revision=tracker.fill_revision) == []
    reopened = make_tracker(tmp_path)
    assert orders_needing_recovery(reopened) == []


@pytest.mark.parametrize("index,field,value", [
    (0, "ExecQty", 1), (0, "AllExecQty", 1), (0, "UnercQty", 3),
    (0, "OrgOrdNo", 1), (1, "OrgOrdNo", 4), (1, "OrdNo", 0),
    (1, "OrdNo", 2), (1, "CnfQty", 2), (1, "CnfQty", 4),
    (1, "OrdQty", 2), (1, "UnercQty", 1), (1, "ExecQty", 1),
    (1, "AllExecQty", 1), (1, "BnsTpCode", "2"), (1, "ShtnIsuNo", "BBB"),
    (1, "OrdMktCode", "81"), (1, "MrcTpNm", "정정"), (1, "OrdTrxPtnNm", "접수"),
])
async def test_acknowledgement_partial_or_conflicting_chain_remains_held(tmp_path, index, field, value):
    tracker = make_tracker(tmp_path)
    order(tracker)
    data = rows()
    data[index][field] = value
    with pytest.raises((ReconciliationUnavailable, StartupEvidenceUnavailable)):
        await evidence(tracker, data)
    assert len(orders_needing_recovery(tracker)) == 1


@pytest.mark.parametrize("field", ["OrdNo", "OrgOrdNo", "OrdQty", "CnfQty", "UnercQty",
                                  "ExecQty", "AllExecQty", "BnsTpCode", "OrdMktCode",
                                  "MrcTpNm", "OrdTrxPtnNm"])
async def test_missing_sdk_default_is_not_confirmation(tmp_path, field):
    tracker = make_tracker(tmp_path)
    order(tracker)
    data = rows()
    del data[1][field]
    with pytest.raises((ReconciliationUnavailable, StartupEvidenceUnavailable)):
        await evidence(tracker, data)


async def test_multiple_children_and_missing_parent_hold(tmp_path):
    tracker = make_tracker(tmp_path)
    order(tracker)
    for data in (rows()[1:], [*rows(), dict(rows()[1], OrdNo=4)], rows()[:1]):
        with pytest.raises(ReconciliationUnavailable):
            await evidence(tracker, data)


@pytest.mark.parametrize("updates", [
    {"execution_key": "other"}, {"trading_mode": "paper"}, {"product": "korea_stock"},
    {"symbol": "BBB"}, {"side": "buy"}, {"ordered_quantity": Decimal(2)},
    {"exchange": "NYSE"}, {"source": "AS1"}, {"order_date": "20260915"},
    {"observed_at": datetime.now(timezone.utc) - timedelta(minutes=3)},
])
async def test_cancellation_cannot_cross_execution_or_identity(tmp_path, updates):
    tracker = make_tracker(tmp_path)
    order(tracker)
    _, items = await evidence(tracker)
    with pytest.raises(ReconciliationUnavailable):
        record_cancellations(tracker, [replace(items[0], **updates)])
    assert len(orders_needing_recovery(tracker)) == 1


async def test_fills_during_query_and_conflicting_durable_evidence_hold(tmp_path):
    tracker = make_tracker(tmp_path)
    order(tracker)
    _, items = await evidence(tracker)
    revision = tracker.fill_revision
    tracker.fill_revision += 1
    with pytest.raises(ReconciliationUnavailable, match="ledger_changed"):
        await tracker.recover_order_totals([], cancellations=items, expected_revision=revision)
    record_cancellations(tracker, items)
    with pytest.raises(ReconciliationUnavailable, match="conflicting_cancellation"):
        record_cancellations(tracker, [replace(items[0], cancel_order_no="4")])


def test_consumed_fields_exist_in_actual_sdk_model():
    fields = {"OrdNo", "OrgOrdNo", "ShtnIsuNo", "IsuNo", "BnsTpCode", "OrdMktCode",
              "OrdQty", "ExecQty", "AllExecQty", "UnercQty", "CnfQty", "MrcTpNm", "OrdTrxPtnNm"}
    assert fields <= COSAQ00102.COSAQ00102OutBlock3.model_fields.keys()
