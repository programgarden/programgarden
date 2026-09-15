"""Actual response models, pagination and missing evidence; no broker requests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from programgarden_finance.ls.korea_stock.accno.CSPAQ22200 import blocks as cash
from programgarden_finance.ls.korea_stock.accno.t0425 import TrT0425, blocks as orders
from programgarden_finance.ls.korea_stock.extension.account_queries import (
    collect_domestic_cash_evidence, collect_domestic_open_orders,
)
from programgarden_finance.ls.korea_stock.extension.valuation import DomesticPositionEvidenceUnavailable

ROW = dict(ordno=12, expcode="001500", medosu="매수", qty=2, cheqty=1,
           ordrem=1, price=7990, exchname="NXT")


def order_response(rows=None, flag="0", cursor="", raw_override=None):
    raw = {"rsp_cd": "00000", "t0425OutBlock": {"cts_ordno": cursor},
           "t0425OutBlock1": [ROW] if rows is None else rows}
    raw.update(raw_override or {})
    return TrT0425._build_response(None, SimpleNamespace(status_code=200), raw,
                                  {"Content-Type": "application/json", "tr_cd": "t0425", "tr_cont": flag, "tr_cont_key": ""}, None)


def client_for(*responses, method="t0425"):
    tr = SimpleNamespace(req_async=AsyncMock(side_effect=list(responses)),
                         request_data=SimpleNamespace(header=SimpleNamespace(tr_cont="N", tr_cont_key="")))
    client = Mock()
    getattr(client, method).return_value = tr
    return client, tr


def cash_response(**changes):
    fields = dict(RcvblUablOrdAbleAmt=0, MnyOrdAbleAmt=900000, MgnRat100pctOrdAbleAmt=999999,
                  Dps=10, D2Dps=0, MgnMny=0)
    fields.update(changes)
    return cash.CSPAQ22200Response(status_code=200, rsp_cd="00136", rsp_msg="complete",
        block1=cash.CSPAQ22200OutBlock1(BalCreTp="0"), block2=cash.CSPAQ22200OutBlock2(**fields))


def test_consumed_fields_exist_on_real_models():
    assert {"BalCreTp"} <= cash.CSPAQ22200InBlock1.model_fields.keys()
    assert {"BalCreTp"} <= cash.CSPAQ22200OutBlock1.model_fields.keys()
    assert {"RcvblUablOrdAbleAmt", "Dps", "D2Dps", "MgnMny"} <= cash.CSPAQ22200OutBlock2.model_fields.keys()
    assert {"expcode", "chegb", "medosu", "sortgb", "cts_ordno"} <= orders.T0425InBlock.model_fields.keys()
    assert {"cts_ordno"} <= orders.T0425OutBlock.model_fields.keys()
    assert set(ROW) | {"hogagb", "ordtime"} <= orders.T0425OutBlock1.model_fields.keys()


@pytest.mark.asyncio
async def test_observed_zero_cash_never_falls_back_to_credit_or_other_amounts():
    client, _ = client_for(cash_response(), method="cspaq22200")
    value = await collect_domestic_cash_evidence(client)
    assert value["orderable_amount"] == 0 and value["d2_deposit"] == 0
    assert client.cspaq22200.call_args.kwargs["body"].model_dump() == {"BalCreTp": "0"}


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["missing", "negative", "echo_missing", "echo_wrong", "error", "http", "rejected"])
async def test_cash_unavailability_is_not_zero(case):
    response = cash_response()
    if case == "missing": response.block2.model_fields_set.discard("RcvblUablOrdAbleAmt")
    elif case == "negative": response.block2.RcvblUablOrdAbleAmt = -1
    elif case == "echo_missing": response.block1.model_fields_set.discard("BalCreTp")
    elif case == "echo_wrong": response.block1.BalCreTp = "1"
    elif case == "error": response.error_msg = "offline"
    elif case == "http": response.status_code = 500
    elif case == "rejected": response.rsp_cd = "UNKNOWN"
    client, tr = client_for(response, method="cspaq22200")
    with pytest.raises(DomesticPositionEvidenceUnavailable):
        await collect_domestic_cash_evidence(client)
    assert tr.req_async.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("side,expected", [("매수", "buy"), ("매도", "sell"), ("1", "sell"), ("2", "buy")])
async def test_pending_sides_and_venue_keep_instrument_identity(side, expected):
    client, _ = client_for(order_response(rows=[{**ROW, "medosu": side}]))
    row = (await collect_domestic_open_orders(client))[0]
    assert row["side"] == expected and row["remaining_quantity"] == 1
    assert row["exchange"] == "KRX" and row["order_venue"] == "NXT"
    assert client.t0425.call_args.kwargs["body"].model_dump() == {
        "expcode": "", "chegb": "0", "medosu": "0", "sortgb": "1", "cts_ordno": ""}


@pytest.mark.asyncio
async def test_filled_and_complete_empty_orders_are_normal():
    for rows in ([], [{**ROW, "ordrem": 0, "cheqty": 2}], [{"ordrem": 0}]):
        client, _ = client_for(order_response(rows=rows))
        assert await collect_domestic_open_orders(client) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["absent", "null", "wrong_block", "side", "missing_qty", "missing_remaining", "negative", "symbol", "duplicate", "default_cursor", "default_header", "business_error"])
async def test_partial_or_malformed_orders_block_entry(case):
    response = order_response()
    if case == "absent": response._orders_block_present = False
    elif case == "null": response = order_response(raw_override={"t0425OutBlock1": None})
    elif case == "wrong_block": response = order_response(raw_override={"t0425OutBlock1": {}})
    elif case == "side": response.block[0].medosu = "unknown"
    elif case == "missing_qty": response.block[0].model_fields_set.discard("qty")
    elif case == "missing_remaining": response.block[0].model_fields_set.discard("ordrem")
    elif case == "negative": response.block[0].ordrem = -1
    elif case == "symbol": response.block[0].expcode = "bad"
    elif case == "duplicate": response.block.append(response.block[0])
    elif case == "default_cursor": response.cont_block.model_fields_set.discard("cts_ordno")
    elif case == "default_header": response.header.model_fields_set.discard("tr_cont")
    elif case == "business_error": response.rsp_cd = "UNKNOWN"
    client, tr = client_for(response)
    with pytest.raises(DomesticPositionEvidenceUnavailable):
        await collect_domestic_open_orders(client)
    assert tr.req_async.await_count == 1


@pytest.mark.asyncio
async def test_later_page_pending_buy_is_retained_and_failed_page_invalidates_first():
    first = order_response(rows=[{**ROW, "ordrem": 0}], flag="Y", cursor="NEXT")
    second = order_response(rows=[{**ROW, "ordno": 13}])
    client, tr = client_for(first, second)
    with patch("programgarden_finance.ls.korea_stock.extension.account_queries.asyncio.sleep", new=AsyncMock()):
        result = await collect_domestic_open_orders(client)
    assert len(result) == 1 and result[0]["order_id"] == "13"
    assert tr.req_async.await_count == 2
    assert client.t0425.call_args.kwargs["body"].cts_ordno == "NEXT"
    for response in (order_response(flag="Y", cursor="NEXT"), order_response(raw_override={"rsp_cd": "UNKNOWN"})):
        client, _ = client_for(first, response)
        with patch("programgarden_finance.ls.korea_stock.extension.account_queries.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(DomesticPositionEvidenceUnavailable):
                await collect_domestic_open_orders(client)
