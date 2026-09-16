"""Exercise startup adapters against real SDK models, with HTTP intercepted."""

import json
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest
from requests import Response
from programgarden_finance import COSOQ00201, COSAQ00102, CIDBQ01500, CIDBQ02400

from programgarden.database.broker_evidence import StartupEvidenceUnavailable
from programgarden.database.broker_snapshot import read_broker_snapshot
from programgarden.database.position_reconciliation import ReconciliationUnavailable


def query(module, name, request, detail, *, mutate=None):
    echo_model = getattr(module, name + "OutBlock1")
    echo = echo_model.model_validate({k: v for k, v in request.model_dump().items()
                                      if k in echo_model.model_fields})
    detail_number = 4 if name == "COSOQ00201" else 3 if name == "COSAQ00102" else 2
    fields = {"block1": echo}
    body = {name + "OutBlock1": echo.model_dump(exclude_unset=True)}
    if name == "COSOQ00201":
        fields["block3"] = []
        body[name + "OutBlock3"] = []
    elif name == "COSAQ00102":
        fields["block2"] = module.COSAQ00102OutBlock2()
        body[name + "OutBlock2"] = {}
    fields[f"block{detail_number}"] = [getattr(module, name + f"OutBlock{detail_number}")(**row) for row in detail]
    body[name + f"OutBlock{detail_number}"] = detail
    response = getattr(module, name + "Response")(
        status_code=200, rsp_cd="00000", rsp_msg="",
        header=getattr(module, name + "ResponseHeader")(**{
            "Content-Type": "application/json", "tr_cd": name, "tr_cont": "N", "tr_cont_key": "",
        }),
        **fields,
    )
    if mutate:
        mutate(response, body)
    raw = Response()
    raw.status_code = 200
    raw._content = json.dumps(body).encode()
    response.raw_data = raw
    return NS(request_data=NS(body={"input": request}), req_async=AsyncMock(return_value=response))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("programgarden.database.broker_snapshot.asyncio.sleep", AsyncMock())


def stock_client(*, balances=None, orders=None, mutate=None):
    calls = []
    def positions(body):
        calls.append(("COSOQ00201", body))
        return query(COSOQ00201, "COSOQ00201", body, balances or [], mutate=mutate)
    def pending(body):
        calls.append(("COSAQ00102", body))
        return query(COSAQ00102, "COSAQ00102", body, orders or [])
    accno = NS(cosoq00201=positions, cosaq00102=pending)
    return NS(overseas_stock=lambda: NS(accno=lambda: accno)), calls


async def read(client, product="overseas_stock", mode="live"):
    return await read_broker_snapshot(client, execution_key="project:execution", product=product,
                                      provider="ls", trading_mode=mode)


async def test_stock_balance_and_pending_use_declared_fields_and_query_echo_date():
    ls, calls = stock_client(balances=[{"ShtnIsuNo": "AAA", "IsuNo": "WRONG", "AstkBalQty": 7}],
                            orders=[{"ShtnIsuNo": "AAA", "OrdNo": 42, "BnsTpCode": "02",
                                     "OrdMktCode": "82", "UnercQty": 1}])
    result = await read(ls)
    assert result.positions.quantities == {"AAA": 7}
    assert result.pending_orders[0]["order_date"] == calls[1][1].OrdDt
    assert result.pending_orders[0]["order_id"] == "42"
    assert result.pending_orders[0]["remaining_quantity"] == 1
    assert result.positions.pending_orders == result.pending_orders
    assert calls[0][1].AstkBalTpCode == "00"
    assert calls[1][1].ExecYn == "2"
    assert "OrdDt" not in COSAQ00102.COSAQ00102OutBlock3.model_fields


@pytest.mark.parametrize("failure", ["missing_raw", "partial", "wrong_tr", "rejected", "skipped_row", "warning"])
async def test_stock_bad_balance_never_becomes_empty_holdings(failure):
    def mutate(response, body):
        if failure == "missing_raw": del body["COSOQ00201OutBlock4"]
        elif failure == "partial": response.header.tr_cont = "Y"
        elif failure == "wrong_tr": response.header.tr_cd = "COSAQ00102"
        elif failure == "rejected": response.rsp_cd = "99999"
        elif failure == "skipped_row": response.block4 = []
        elif failure == "warning": response.parse_warnings = ["row skipped"]
    ls, calls = stock_client(balances=[{"ShtnIsuNo": "AAA", "AstkBalQty": 7}], mutate=mutate)
    with pytest.raises(StartupEvidenceUnavailable):
        await read(ls)
    assert len(calls) == 1  # Never retry a rejected broker call.


async def test_defaulted_stock_quantity_is_not_observed_zero():
    ls, _ = stock_client(balances=[{"ShtnIsuNo": "AAA"}])
    with pytest.raises(StartupEvidenceUnavailable, match="incomplete_row"):
        await read(ls)


async def test_duplicate_custody_rows_hold_instead_of_overwriting_quantity():
    ls, _ = stock_client(balances=[{"ShtnIsuNo": "AAA", "AstkBalQty": 7}] * 2)
    with pytest.raises(ReconciliationUnavailable, match="ambiguous_position_rows"):
        await read(ls)


async def test_futures_short_does_not_inflate_long_fifo_and_order_keeps_business_day():
    calls = []
    def positions(*, body):
        calls.append(body)
        return query(CIDBQ01500, "CIDBQ01500", body, [
            {"IsuCodeVal": "CONTRACT", "BnsTpCode": "2", "BalQty": 3},
            {"IsuCodeVal": "CONTRACT", "BnsTpCode": "1", "BalQty": 5},
        ])
    def pending(*, body):
        calls.append(body)
        return query(CIDBQ02400, "CIDBQ02400", body, [{
            "IsuCodeVal": "CONTRACT", "BnsTpCode": "1", "UnercQty": 1,
            "OrdDt": "20260915", "OvrsFutsOrdNo": "00042",
        }])
    accno = NS(CIDBQ01500=positions, CIDBQ02400=pending)
    ls = NS(overseas_futureoption=lambda: NS(accno=lambda: accno))
    result = await read(ls, "overseas_futures", "paper")
    assert result.positions.quantities == {"CONTRACT": 3}
    assert result.pending_orders[0]["order_date"] == "20260915"
    assert result.positions.trading_mode == "paper"
    assert calls[0].BalTpCode == "2"


def test_all_consumed_detail_fields_exist_in_the_published_models():
    from programgarden_finance import CSPAQ12300
    for model, fields in [
        (COSOQ00201.COSOQ00201OutBlock4, {"ShtnIsuNo", "IsuNo", "AstkBalQty"}),
        (COSAQ00102.COSAQ00102OutBlock3, {"ShtnIsuNo", "IsuNo", "OrdNo", "BnsTpCode", "OrdMktCode", "UnercQty"}),
        (CIDBQ01500.CIDBQ01500OutBlock2, {"IsuCodeVal", "BnsTpCode", "BalQty"}),
        (CIDBQ02400.CIDBQ02400OutBlock2, {"IsuCodeVal", "OvrsFutsOrdNo", "OrdDt", "BnsTpCode", "UnercQty"}),
        (CSPAQ12300.CSPAQ12300OutBlock3, {"IsuNo", "BnsBaseBalQty"}),
    ]:
        assert fields <= model.model_fields.keys(), model.__name__


@pytest.mark.parametrize("available", [7, 10])
async def test_broker_startup_applies_real_ledger_and_notifies_only_changes(tmp_path, monkeypatch, available):
    from programgarden.context import ExecutionContext
    from programgarden.executor import BrokerNodeExecutor

    context = ExecutionContext("job", workflow_id="strategy", storage_dir=str(tmp_path),
                               execution_key="project:execution")
    context.init_workflow_position_tracker("broker", "overseas_stock", "ls", False)
    tracker = context._workflow_position_tracker
    tracker.record_order("1", "20260916", "AAA", "NASDAQ", "buy", 10, 20, "job", "buy")
    await tracker.record_fill("1", "20260916", "AAA", "NASDAQ", "buy", 10, 20, "100000", "40",
                              execution_id="1")
    ls, _ = stock_client(balances=[{"ShtnIsuNo": "AAA", "AstkBalQty": available}])
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", lambda *args, **kwargs: (ls, True, None))
    context.notify_risk_event = AsyncMock()
    await BrokerNodeExecutor()._reconcile_startup_account(
        context=context, node_id="broker", product="overseas_stock", provider="ls",
        appkey="test-key", appsecret="test-secret", paper_trading=False,
    )
    assert context._startup_reconciled is True
    assert tracker.get_workflow_positions()["AAA"].quantity == available
    assert context.notify_risk_event.await_count == (1 if available < 10 else 0)
    if available < 10:
        event = context.notify_risk_event.call_args.args[0]
        assert event.event_type == "position_reconciled"
        assert event.details["is_trade"] is False
        assert len(tracker.get_position_adjustments()) == 1


async def test_failed_broker_startup_remains_held(tmp_path, monkeypatch):
    from programgarden.context import ExecutionContext
    from programgarden.executor import BrokerNodeExecutor

    context = ExecutionContext("job", workflow_id="strategy", storage_dir=str(tmp_path),
                               execution_key="project:execution")
    context.init_workflow_position_tracker("broker", "overseas_stock", "ls", False)
    ls, _ = stock_client(mutate=lambda response, body: body.pop("COSOQ00201OutBlock4"))
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", lambda *args, **kwargs: (ls, True, None))
    context.notify_risk_event = AsyncMock()
    with pytest.raises(StartupEvidenceUnavailable):
        await BrokerNodeExecutor()._reconcile_startup_account(
            context=context, node_id="broker", product="overseas_stock", provider="ls",
            appkey="test-key", appsecret="test-secret", paper_trading=False,
        )
    assert context._startup_reconciled is False
    assert context._workflow_position_tracker.get_position_adjustments() == []
    context.notify_risk_event.assert_not_awaited()
