"""Real parser contracts and bounded account observations; no live orders."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from programgarden_finance.ls.korea_stock.accno.CSPAQ12300 import TrCSPAQ12300
from programgarden_finance.ls.korea_stock.accno.CSPAQ12300 import blocks as csp
from programgarden_finance.ls.korea_stock.accno.t0424 import TrT0424
from programgarden_finance.ls.korea_stock.accno.t0424 import blocks as cash
from programgarden_finance.ls.korea_stock.extension.tracker import KrStockAccountTracker
from programgarden_finance.ls.korea_stock.extension.valuation import (
    DomesticPositionEvidenceUnavailable, collect_domestic_position_evidence,
    collect_domestic_trading_positions, position_evidence,
)

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)
REQUEST = dict(RecCnt=1, BalCreTp="0", CmsnAppTpCode="0", D2balBaseQryTp="0", UprcTpCode="0")
ROW = dict(IsuNo="A001500", BalQty=0, BnsBaseBalQty=1, AvrUprc="7980.00",
           PchsAmt=7980, NowPrc="7980.00", BalEvalAmt=7980, EvalPnl=0)


def response(rows=None, flag="N", cursor="", raw_override=None):
    raw = {"rsp_cd": "00136", "CSPAQ12300OutBlock1": REQUEST,
           "CSPAQ12300OutBlock2": {"Dps": 999999, "EvalPnlSum": 999999},
           "CSPAQ12300OutBlock3": [ROW] if rows is None else rows}
    raw.update(raw_override or {})
    headers = {"Content-Type": "application/json", "tr_cd": "CSPAQ", "tr_cont": flag, "tr_cont_key": cursor}
    return TrCSPAQ12300._build_response(None, SimpleNamespace(status_code=200), raw, headers, None)


def client_for(*responses, method="cspaq12300"):
    tr = SimpleNamespace(req_async=AsyncMock(side_effect=list(responses)),
                         request_data=SimpleNamespace(header=SimpleNamespace(tr_cont="N", tr_cont_key="")))
    client = Mock()
    getattr(client, method).return_value = tr
    return client, tr


def test_consumed_fields_exist_on_actual_models():
    assert set(REQUEST) <= csp.CSPAQ12300InBlock1.model_fields.keys()
    assert set(REQUEST) <= csp.CSPAQ12300OutBlock1.model_fields.keys()
    assert set(ROW) <= csp.CSPAQ12300OutBlock3.model_fields.keys()
    assert {"expcode", "janqty", "mdposqt", "pamt", "price", "mamt", "appamt",
            "dtsunik", "sunikrt", "marketgb", "hname"} <= cash.T0424OutBlock1.model_fields.keys()
    assert {"cts_expcode", "sunamt", "dtsunik", "mamt", "tappamt", "tdtsunik"} <= cash.T0424OutBlock.model_fields.keys()


def test_unsettled_holding_uses_observed_average_not_bep_or_summary():
    value = position_evidence(response().block3, NOW)
    row = value["positions"]["001500"]
    assert row["quantity"] == 1 and row["average_price"] == 7980
    assert row["acquisition_amount"] == 7980 and row["currency"] == "KRW"
    assert row["pnl_amount"] == 0 and row["pnl_status"] == "available"
    assert value["account_valuation"]["groups"] == [{"currency": "KRW", "earned": 0, "lost": 0, "net": 0}]


def test_distinct_gains_losses_and_missing_fields():
    rows = [csp.CSPAQ12300OutBlock3(**{**ROW, "EvalPnl": 30}),
            csp.CSPAQ12300OutBlock3(**{**ROW, "IsuNo": "000080", "EvalPnl": -10})]
    assert position_evidence(rows, NOW)["account_valuation"]["groups"][0] == {"currency": "KRW", "earned": 30, "lost": 10, "net": 20}
    rows[1].model_fields_set.discard("EvalPnl")
    result = position_evidence(rows, NOW)
    assert result["account_valuation"] is None
    assert result["positions"]["000080"]["pnl_amount"] is None
    assert result["positions"]["000080"]["pnl_unavailable_reason"] == "broker_field_not_observed"
    rows[0].model_fields_set.discard("AvrUprc")
    assert position_evidence(rows, NOW)["positions"]["001500"]["average_price"] is None


@pytest.mark.parametrize("update", [{"IsuNo": "bad"}, {"BnsBaseBalQty": -1}])
def test_ambiguous_holdings_fail_closed(update):
    with pytest.raises(DomesticPositionEvidenceUnavailable):
        position_evidence([csp.CSPAQ12300OutBlock3(**{**ROW, **update})], NOW)
    with pytest.raises(DomesticPositionEvidenceUnavailable):
        position_evidence(response().block3 * 2, NOW)


@pytest.mark.asyncio
async def test_complete_empty_is_zero_missing_or_null_block_is_unavailable():
    client, _ = client_for(response(rows=[]))
    assert (await collect_domestic_position_evidence(client))["account_valuation"]["groups"][0]["net"] == 0
    for block in (None, {}, ""):
        client, _ = client_for(response(raw_override={"CSPAQ12300OutBlock3": block}))
        with pytest.raises(DomesticPositionEvidenceUnavailable):
            await collect_domestic_position_evidence(client)


@pytest.mark.asyncio
async def test_pagination_preserves_scope_and_accumulates_every_row():
    client, tr = client_for(response(flag="Y", cursor="NEXT"),
                            response(rows=[{**ROW, "IsuNo": "000080", "EvalPnl": -10}]))
    with patch("programgarden_finance.ls.korea_stock.extension.valuation.asyncio.sleep", new=AsyncMock()):
        result = await collect_domestic_position_evidence(client)
    assert set(result["positions"]) == {"001500", "000080"}
    assert tr.req_async.await_count == 2 and tr.request_data.header.tr_cont_key == "NEXT"
    assert client.cspaq12300.call_args.kwargs["body"].model_dump() == REQUEST


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["repeat", "failed_page", "echo", "default_header", "default_quantity"])
async def test_partial_pages_and_defaulted_scope_do_not_become_success(case):
    second = response(rows=[{**ROW, "IsuNo": "000080"}])
    if case == "repeat": second.header.tr_cont = "Y"; second.header.tr_cont_key = "NEXT"
    elif case == "failed_page": second.error_msg = "offline"
    elif case == "echo": second.block1.UprcTpCode = "1"
    elif case == "default_header": second.header.model_fields_set.discard("tr_cont")
    elif case == "default_quantity": second.block3[0].model_fields_set.discard("BnsBaseBalQty")
    client, tr = client_for(response(flag="Y", cursor="NEXT"), second)
    with patch("programgarden_finance.ls.korea_stock.extension.valuation.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(DomesticPositionEvidenceUnavailable):
            await collect_domestic_position_evidence(client)
    assert tr.req_async.await_count == 2


@pytest.mark.asyncio
async def test_tracker_failure_invalidates_financial_evidence_keeps_trading_cache():
    tracker = KrStockAccountTracker(Mock())
    tracker._positions = {"kept": object()}
    tracker._position_evidence = position_evidence(response().block3, NOW)
    detached = tracker.get_position_evidence()
    detached["positions"]["001500"]["quantity"] = 100
    assert tracker.get_position_evidence()["positions"]["001500"]["quantity"] == 1
    tracker._fetch_positions = AsyncMock()
    tracker._fetch_balance = AsyncMock()
    tracker._fetch_open_orders = AsyncMock()
    tracker._calculate_and_notify_account_pnl = Mock()
    with patch("programgarden_finance.ls.korea_stock.extension.tracker.asyncio.sleep", new=AsyncMock()), \
         patch("programgarden_finance.ls.korea_stock.extension.tracker.collect_domestic_position_evidence", new=AsyncMock(side_effect=ValueError("offline"))):
        await tracker._fetch_all_data()
    assert tracker.get_position_evidence() is None and tracker.get_valuation_snapshot() is None
    assert "kept" in tracker._positions


def trading_response(symbol="001500", cursor="", flag="0"):
    raw = {"rsp_cd": "00000", "t0424OutBlock": {"cts_expcode": cursor},
           "t0424OutBlock1": [{"expcode": symbol, "janqty": 1, "pamt": 7999,
                              "price": 7980, "mamt": 7981, "appamt": 7965,
                              "dtsunik": -16, "sunikrt": "-0.20"}]}
    headers = {"Content-Type": "application/json", "tr_cd": "t0424", "tr_cont": flag, "tr_cont_key": ""}
    return TrT0424._build_response(None, SimpleNamespace(status_code=200), raw, headers, None)


@pytest.mark.asyncio
async def test_trading_cache_reads_all_pages_and_never_overwrites_duplicate_symbols():
    client, tr = client_for(trading_response(cursor="NEXT", flag="Y"), trading_response("000080"), method="t0424")
    with patch("programgarden_finance.ls.korea_stock.extension.valuation.asyncio.sleep", new=AsyncMock()):
        _, rows = await collect_domestic_trading_positions(client)
    assert len(rows) == 2
    body = client.t0424.call_args.kwargs["body"]
    assert body.chegb == "2" and body.prcgb == "2" and body.charge == "1" and body.cts_expcode == "NEXT"
    client, _ = client_for(trading_response(cursor="NEXT", flag="Y"), trading_response(), method="t0424")
    with patch("programgarden_finance.ls.korea_stock.extension.valuation.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(DomesticPositionEvidenceUnavailable):
            await collect_domestic_trading_positions(client)
