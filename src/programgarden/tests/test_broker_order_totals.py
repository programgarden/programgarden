"""Verify recovery requests/fields at the actual SDK response boundary."""

from types import SimpleNamespace as NS
import json
from unittest.mock import AsyncMock

import pytest
from programgarden_finance import COSAQ00102, COSOQ00201

from programgarden.database.broker_order_totals import read_stock_order_totals
from programgarden.database.order_recovery import orders_needing_recovery
from programgarden.database.position_reconciliation import ReconciliationUnavailable
from programgarden.database.broker_evidence import StartupEvidenceUnavailable
from test_execution_broker_snapshot import query
from test_order_total_recovery import make_tracker, order
from test_position_reconciliation import buy


def row(**updates):
    return {"OrdNo": 2, "OrgOrdNo": 0, "ShtnIsuNo": "AAA", "BnsTpCode": "1",
            "OrdQty": 3, "ExecQty": 3, "AllExecQty": 3, "OvrsExecPrc": 25,
            "UnercQty": 0, "CrcyCode": "USD", "ExecTime": "110000000", **updates}


def client(rows, mutate=None, position=7):
    calls = []
    def orders(body):
        calls.append(body)
        return query(COSAQ00102, "COSAQ00102", body,
                     rows if body.ExecYn in {"0", "1"} else [], mutate=mutate)
    def positions(body):
        return query(COSOQ00201, "COSOQ00201", body, [{"ShtnIsuNo": "AAA", "AstkBalQty": position}])
    accno = NS(cosaq00102=orders, cosoq00201=positions)
    return NS(overseas_stock=lambda: NS(accno=lambda: accno)), calls


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr("programgarden.database.broker_order_totals.asyncio.sleep", AsyncMock())


async def test_sdk_query_preserves_explicit_historical_date_and_partial_order(tmp_path):
    tracker = make_tracker(tmp_path)
    await buy(tracker, 1, 10, 20)
    order(tracker)
    await tracker.record_fill("2", "20260916", "AAA", "NASDAQ", "sell", 1, 25,
                              "105959000", "40", execution_id="21", currency="USD")
    unresolved = orders_needing_recovery(tracker)
    assert [r["order_no"] for r in unresolved] == ["2"]
    ls, calls = client([row()])
    totals = await read_stock_order_totals(ls, tracker, unresolved)
    assert totals[0].order_date == "20260916"
    assert totals[0].filled_quantity == 3
    assert calls[0].ExecYn == "1" and calls[0].ThdayBnsAppYn == "0"
    assert calls[0].OrdDt == "20260916" and calls[0].SrtOrdNo == 999999999


async def test_observed_short_header_requires_full_tr_body_and_matching_query(tmp_path):
    tracker = make_tracker(tmp_path)
    order(tracker)
    def short_header(response, body):
        response.header.tr_cd = "COSAQ"
        response.block1.OrdMktCode = "%"
        body["COSAQ00102OutBlock1"]["OrdMktCode"] = "%"
        response.rsp_cd = "00136"
    ls, _ = client([row()], short_header)
    totals = await read_stock_order_totals(ls, tracker, orders_needing_recovery(tracker))
    assert len(totals) == 1 and totals[0].filled_quantity == 3
    def wrong_family(response, body):
        short_header(response, body)
        response.header.tr_cd = "COSOQ"
    ls, _ = client([row()], wrong_family)
    with pytest.raises(StartupEvidenceUnavailable, match="incomplete_continuation"):
        await read_stock_order_totals(ls, tracker, orders_needing_recovery(tracker))

    def wrong_body(response, body):
        short_header(response, body)
        body["COSAQ99999OutBlock3"] = body.pop("COSAQ00102OutBlock3")
    ls, _ = client([row()], wrong_body)
    with pytest.raises(StartupEvidenceUnavailable, match="missing_response_blocks"):
        await read_stock_order_totals(ls, tracker, orders_needing_recovery(tracker))


@pytest.mark.parametrize("code,side", [("1", "sell"), ("2", "buy")])
async def test_actual_sdk_parser_accepts_observed_header_and_documented_side(tmp_path, code, side):
    from requests import Response
    tracker = make_tracker(tmp_path)
    order(tracker, side=side)
    def query_wire(request):
        echo = request.model_dump()
        echo["OrdMktCode"] = "%"
        packet = {"rsp_cd": "00136", "rsp_msg": "조회가 완료되었습니다.",
                  "COSAQ00102OutBlock1": echo, "COSAQ00102OutBlock2": {},
                  "COSAQ00102OutBlock3": [row(BnsTpCode=code)]}
        raw = Response()
        raw.status_code = 200
        raw._content = json.dumps(packet).encode()
        result = COSAQ00102.TrCOSAQ00102._build_response(None, raw, packet,
            {"Content-Type": "application/json;charset=UTF-8", "tr_cd": "COSAQ",
             "tr_cont": "N", "tr_cont_key": ""}, None)
        return NS(request_data=NS(body={"input": request}), req_async=AsyncMock(return_value=result))
    ls = NS(overseas_stock=lambda: NS(accno=lambda: NS(cosaq00102=query_wire)))
    totals = await read_stock_order_totals(ls, tracker, orders_needing_recovery(tracker))
    assert len(totals) == 1 and totals[0].side == side and totals[0].filled_quantity == 3


@pytest.mark.parametrize("missing", ["ExecQty", "AllExecQty", "OvrsExecPrc", "OrgOrdNo", "OrdQty", "CrcyCode", "ExecTime", "BnsTpCode"])
async def test_defaulted_sdk_fields_are_not_recovery_evidence(tmp_path, missing):
    tracker = make_tracker(tmp_path)
    order(tracker)
    data = row()
    del data[missing]
    ls, calls = client([data])
    with pytest.raises(ReconciliationUnavailable, match="missing_broker_field"):
        await read_stock_order_totals(ls, tracker, orders_needing_recovery(tracker))
    assert len(calls) == 1


@pytest.mark.parametrize("rows", [[], [row(), row()], [row(OrgOrdNo=1)],
                                  [row(ExecQty=2, AllExecQty=3)], [row(ExecQty=2, AllExecQty=2, UnercQty=1)]])
async def test_missing_duplicate_nonterminal_and_chain_totals_hold(tmp_path, rows):
    tracker = make_tracker(tmp_path)
    order(tracker)
    ls, _ = client(rows)
    with pytest.raises(ReconciliationUnavailable):
        await read_stock_order_totals(ls, tracker, orders_needing_recovery(tracker))
    assert tracker.get_order_recoveries() == []


@pytest.mark.parametrize("fault", ["date", "page", "parse", "rejected"])
async def test_incomplete_scope_or_response_cannot_authorize_recovery(tmp_path, fault):
    tracker = make_tracker(tmp_path)
    order(tracker)
    def mutate(response, body):
        if fault == "date": response.block1.OrdDt = "20260915"
        elif fault == "page": response.header.tr_cont = "Y"
        elif fault == "parse": response.block3 = []
        elif fault == "rejected": response.rsp_cd = "99999"
    ls, calls = client([row()], mutate)
    with pytest.raises(StartupEvidenceUnavailable):
        await read_stock_order_totals(ls, tracker, orders_needing_recovery(tracker))
    assert len(calls) == 1


def test_every_consumed_recovery_field_exists_in_actual_sdk():
    assert {"OrdNo", "OrgOrdNo", "ShtnIsuNo", "IsuNo", "BnsTpCode", "ExecQty",
            "AllExecQty", "OrdQty", "OvrsExecPrc", "UnercQty", "CrcyCode", "ExecTime"} <= COSAQ00102.COSAQ00102OutBlock3.model_fields.keys()
    assert "OrdDt" in COSAQ00102.COSAQ00102OutBlock1.model_fields
    assert "OrdDt" not in COSAQ00102.COSAQ00102OutBlock3.model_fields


async def test_real_startup_recovers_before_trim_then_late_fill_cannot_double_sell(tmp_path, monkeypatch):
    from programgarden.context import ExecutionContext
    from programgarden.executor import BrokerNodeExecutor

    context = ExecutionContext("job", workflow_id="strategy", storage_dir=str(tmp_path),
                               execution_key="project:execution")
    context.init_workflow_position_tracker("broker", "overseas_stock", "ls", False)
    tracker = context._workflow_position_tracker
    await buy(tracker, 1, 10, 20)
    order(tracker)
    ls, calls = client([row()])
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", lambda *args, **kwargs: (ls, True, None))
    context.notify_risk_event = AsyncMock()
    fill_callback = AsyncMock()
    tracker.set_fill_classified_callback(fill_callback)
    await BrokerNodeExecutor()._reconcile_startup_account(
        context=context, node_id="broker", product="overseas_stock", provider="ls",
        appkey="test-key", appsecret="test-secret", paper_trading=False)
    assert context._startup_reconciled
    assert [request.ExecYn for request in calls] == ["0", "2"]
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    assert tracker.get_position_adjustments() == []
    assert context.notify_risk_event.await_count == 1
    assert context.notify_risk_event.call_args.args[0].event_type == "order_totals_recovered"
    await tracker.record_fill("2", "20260916", "AAA", "NASDAQ", "sell", 3, 25,
                              "110000000", "40", execution_id="21", currency="USD")
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    fill_callback.assert_not_awaited()
    assert tracker.personal_metrics()["closed_trade_count"] == 0


async def test_committed_recovery_is_notified_even_when_later_snapshot_holds(tmp_path, monkeypatch):
    from programgarden.context import ExecutionContext
    from programgarden.executor import BrokerNodeExecutor
    from programgarden.database.broker_snapshot import read_broker_snapshot

    context = ExecutionContext("job", workflow_id="strategy", storage_dir=str(tmp_path),
                               execution_key="project:execution")
    context.init_workflow_position_tracker("broker", "overseas_stock", "ls", False)
    tracker = context._workflow_position_tracker
    await buy(tracker, 1, 10, 20)
    order(tracker)
    ls, _ = client([row()])
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", lambda *args, **kwargs: (ls, True, None))
    context.notify_risk_event = AsyncMock()
    monkeypatch.setattr("programgarden.database.broker_snapshot.read_broker_snapshot",
                        AsyncMock(side_effect=ReconciliationUnavailable("positions_unavailable")))
    kwargs = dict(context=context, node_id="broker", product="overseas_stock", provider="ls",
                  appkey="test-key", appsecret="test-secret", paper_trading=False)
    with pytest.raises(ReconciliationUnavailable, match="positions_unavailable"):
        await BrokerNodeExecutor()._reconcile_startup_account(**kwargs)
    assert not getattr(context, "_startup_reconciled", False)
    assert tracker.get_workflow_positions()["AAA"].quantity == 7
    assert context.notify_risk_event.await_count == 1
    monkeypatch.setattr("programgarden.database.broker_snapshot.read_broker_snapshot", read_broker_snapshot)
    await BrokerNodeExecutor()._reconcile_startup_account(**kwargs)
    assert context._startup_reconciled
    assert context.notify_risk_event.await_count == 1
    assert len(tracker.get_order_recoveries()) == 1
