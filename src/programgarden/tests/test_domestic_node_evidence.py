"""Domestic workflow nodes consume real parser contracts, without live requests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from programgarden.executor import AccountNodeExecutor, OpenOrdersNodeExecutor
from programgarden_finance.ls.korea_stock.accno.CSPAQ12300 import TrCSPAQ12300
from programgarden_finance.ls.korea_stock.accno.CSPAQ22200 import blocks as cash
from programgarden_finance.ls.korea_stock.accno.t0425 import TrT0425

REQUEST = dict(RecCnt=1, BalCreTp="0", CmsnAppTpCode="0", D2balBaseQryTp="0", UprcTpCode="0")
POSITION = dict(IsuNo="A001500", BalQty=0, BnsBaseBalQty=1, SellAbleQty=1,
                AvrUprc=7980, PchsAmt=7980, NowPrc=7950, BalEvalAmt=7950,
                EvalPnl=-30, PnlRat=-0.003759)
ORDER = dict(ordno=12, expcode="001500", medosu="매수", qty=2, cheqty=1,
             ordrem=1, price=7990, exchname="NXT")


def position_response(rows=None, error=None):
    value = TrCSPAQ12300._build_response(None, SimpleNamespace(status_code=200),
        {"rsp_cd": "00136", "CSPAQ12300OutBlock1": REQUEST,
         "CSPAQ12300OutBlock2": {"Dps": 999999, "BalEvalAmt": 999999, "EvalPnlSum": 999999},
         "CSPAQ12300OutBlock3": [POSITION] if rows is None else rows},
        {"Content-Type": "application/json", "tr_cd": "CSPAQ", "tr_cont": "N", "tr_cont_key": ""}, None)
    value.error_msg = error
    return value


def cash_response(orderable=10000, error=None):
    return cash.CSPAQ22200Response(status_code=200, rsp_cd="00136", rsp_msg="complete", error_msg=error,
        block1=cash.CSPAQ22200OutBlock1(BalCreTp="0"),
        block2=cash.CSPAQ22200OutBlock2(RcvblUablOrdAbleAmt=orderable,
            MnyOrdAbleAmt=999999, Dps=10000, D2Dps=0, MgnMny=0))


def order_response(rows=None, error=None):
    value = TrT0425._build_response(None, SimpleNamespace(status_code=200),
        {"rsp_cd": "00000", "t0425OutBlock": {"cts_ordno": ""},
         "t0425OutBlock1": [ORDER] if rows is None else rows},
        {"Content-Type": "application/json", "tr_cd": "t0425", "tr_cont": "0", "tr_cont_key": ""}, None)
    value.error_msg = error
    return value


def ls_for(positions=None, funds=None, orders=None):
    client = Mock()
    for method, response in (("cspaq12300", positions), ("cspaq22200", funds), ("t0425", orders)):
        getattr(client, method).return_value = SimpleNamespace(req_async=AsyncMock(return_value=response))
    ls = Mock()
    ls.korea_stock.return_value.accno.return_value = client
    return ls


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_money", [False, True])
async def test_domestic_position_catalog_matches_actual_composed_output(missing_money):
    from programgarden_core import NodeTypeRegistry
    row = {key: value for key, value in POSITION.items()
           if not missing_money or key not in {"AvrUprc", "PchsAmt", "EvalPnl", "PnlRat"}}
    result = await AccountNodeExecutor()._ls_korea_stock(
        ls_for(position_response(rows=[row]), cash_response()), "account", Mock())
    schema = NodeTypeRegistry().get_schema("KoreaStockAccountNode")
    declared = next(port["fields"] for port in schema.outputs if port["name"] == "positions")
    assert result["positions"]
    assert {field["name"] for field in declared} == set(result["positions"][0])
    assert result["positions"][0]["cost_status"] == ("unavailable" if missing_money else "available")


@pytest.mark.asyncio
async def test_unsettled_position_never_disappears_or_uses_unavailable_summary():
    ls = ls_for(position_response(), cash_response())
    result = await AccountNodeExecutor()._ls_korea_stock(ls, "account", Mock())
    assert result["held_symbols"] == [{"exchange": "KRX", "symbol": "001500"}]
    row = result["positions"][0]
    assert row["quantity"] == row["sellable_qty"] == 1
    assert row["avg_price"] == row["purchase_amount"] == 7980
    assert row["pnl_amount"] == -30 and row["pnl_rate"] == pytest.approx(-0.3759)
    assert result["balance"]["eval_pnl"] == -30
    assert result["balance"]["total_eval"] == 7950
    assert result["balance"]["orderable_amount"] == 10000
    assert not result["balance"].get("_partial_failure")


@pytest.mark.asyncio
async def test_complete_empty_and_observed_zero_cash_remain_valid():
    result = await AccountNodeExecutor()._ls_korea_stock(
        ls_for(position_response(rows=[]), cash_response(orderable=0)), "account", Mock())
    assert result["positions"] == [] and result["held_symbols"] == []
    assert result["balance"]["orderable_amount"] == 0
    assert result["balance"]["total_eval"] == result["balance"]["eval_pnl"] == 0
    assert not result["balance"].get("_partial_failure")


@pytest.mark.asyncio
async def test_failed_cash_preserves_holdings_and_blocks_new_entries():
    result = await AccountNodeExecutor()._ls_korea_stock(
        ls_for(position_response(), cash_response(error="offline")), "account", Mock())
    assert result["positions"][0]["quantity"] == 1
    assert result["balance"]["orderable_amount"] is None
    assert result["balance"]["_partial_failure"]
    assert result["balance"]["_failure_codes"] == ["CSPAQ22200"]


@pytest.mark.asyncio
async def test_failed_holdings_cannot_be_treated_as_an_empty_account():
    result = await AccountNodeExecutor()._ls_korea_stock(
        ls_for(position_response(error="offline"), cash_response()), "account", Mock())
    assert result["positions"] == []
    assert result["balance"]["total_eval"] is None
    assert result["balance"]["_partial_failure"]
    assert result["balance"]["_failure_codes"] == ["CSPAQ12300"]


@pytest.mark.asyncio
async def test_missing_money_preserves_quantity_without_fabricating_pnl_or_cost():
    row = {key: value for key, value in POSITION.items() if key not in {"AvrUprc", "PchsAmt", "EvalPnl", "PnlRat"}}
    result = await AccountNodeExecutor()._ls_korea_stock(
        ls_for(position_response(rows=[row]), cash_response()), "account", Mock())
    position = result["positions"][0]
    assert position["quantity"] == 1
    assert position["avg_price"] is position["purchase_amount"] is position["pnl_amount"] is position["pnl_rate"] is None
    assert result["balance"]["purchase_amount"] is result["balance"]["eval_pnl"] is None


@pytest.mark.asyncio
async def test_pending_buy_keeps_confirmed_nxt_venue_without_splitting_instrument():
    result = await OpenOrdersNodeExecutor()._ls_korea_stock(ls_for(orders=order_response()), "orders", Mock())
    assert result["count"] == 1 and "error" not in result
    assert result["open_orders"][0]["side"] == "buy"
    assert result["open_orders"][0]["exchange"] == "KRX"
    assert result["open_orders"][0]["order_venue"] == "NXT"


@pytest.mark.asyncio
@pytest.mark.parametrize("rows,error", [([], None), ([{**ORDER, "ordrem": 0}], None), ([{**ORDER, "medosu": "unknown"}], "unknown_pending_order_side"), (None, "offline")])
async def test_empty_orders_are_normal_but_unknown_or_failed_reads_keep_error(rows, error):
    response = order_response(rows=rows, error="offline" if error == "offline" else None)
    result = await OpenOrdersNodeExecutor()._ls_korea_stock(ls_for(orders=response), "orders", Mock())
    assert result["count"] == 0 and result["open_orders"] == []
    assert bool(result.get("error")) == bool(error)
