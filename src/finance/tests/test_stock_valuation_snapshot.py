"""Valuation money requires observed broker fields, complete rows and currency."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden_finance.ls.overseas_stock.accno.COSOQ00201 import blocks
from programgarden_finance.ls.overseas_stock.accno.COSOQ00201 import TrCOSOQ00201
from programgarden_finance.ls.overseas_stock.extension.valuation import stock_valuation_snapshot
from programgarden_finance.ls.overseas_stock.extension.tracker import StockAccountTracker

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)
REQUEST = blocks.COSOQ00201InBlock1(RecCnt=1, BaseDt="20260915", CrcyCode="ALL", AstkBalTpCode="00")


def response():
    value = blocks.COSOQ00201Response(
        status_code=200, rsp_cd="00000", rsp_msg="success",
        header=blocks.COSOQ00201ResponseHeader(content_type="application/json", tr_cd="COSOQ00201", tr_cont="N", tr_cont_key=""),
        block1=blocks.COSOQ00201OutBlock1(**REQUEST.model_dump()),
        block3=[blocks.COSOQ00201OutBlock3(CrcyCode="USD", FcurrEvalPnlAmt=6),
                blocks.COSOQ00201OutBlock3(CrcyCode="HKD", FcurrEvalPnlAmt=-2)],
        block4=[blocks.COSOQ00201OutBlock4(ShtnIsuNo="TEST1", AstkBalQty=0.5, CrcyCode="USD", FcurrEvalPnlAmt=10),
                blocks.COSOQ00201OutBlock4(IsuNo="TEST2", AstkBalQty=1, CrcyCode="USD", FcurrEvalPnlAmt=-4),
                blocks.COSOQ00201OutBlock4(ShtnIsuNo="TEST3", AstkBalQty=1, CrcyCode="HKD", FcurrEvalPnlAmt=-2)],
    )
    value._valuation_blocks_present = True
    return value


def test_actual_field_contract():
    assert {"CrcyCode", "FcurrEvalPnlAmt"} <= blocks.COSOQ00201OutBlock3.model_fields.keys()
    assert {"CrcyCode", "FcurrEvalPnlAmt", "AstkBalQty", "ShtnIsuNo", "IsuNo", "FcurrMktCode", "AstkBalTpCode"} <= blocks.COSOQ00201OutBlock4.model_fields.keys()
    assert {"BaseDt", "CrcyCode", "AstkBalTpCode"} <= blocks.COSOQ00201OutBlock1.model_fields.keys()


def test_gains_losses_and_net_stay_separate_per_currency():
    source = response()
    before = source.model_dump()
    value = stock_valuation_snapshot(source, REQUEST, NOW)
    assert value["groups"] == [
        {"currency": "HKD", "earned": 0, "lost": 2, "net": -2},
        {"currency": "USD", "earned": 10, "lost": 4, "net": 6},
    ]
    assert value["observed_at"] == NOW.isoformat()
    assert source.model_dump() == before
    assert "TEST" not in str(value)


@pytest.mark.parametrize("case", ["default_pnl", "missing_unit", "partial", "failed", "http", "echo", "continued", "duplicate", "missing_row", "missing_block", "nonfinite", "negative_quantity"])
def test_incomplete_or_defaulted_evidence_never_becomes_zero(case):
    value = response()
    if case == "default_pnl":
        value.block4[0] = blocks.COSOQ00201OutBlock4(ShtnIsuNo="TEST1", AstkBalQty=1, CrcyCode="USD")
    elif case == "missing_unit": value.block4[0].CrcyCode = ""
    elif case == "partial": value.parse_warnings = ["omitted row"]
    elif case == "failed": value.error_msg = "failure"
    elif case == "http": value.status_code = 500
    elif case == "echo": value.block1.BaseDt = "20260914"
    elif case == "continued": value.header.tr_cont = "Y"
    elif case == "duplicate": value.block4.append(deepcopy(value.block4[0]))
    elif case == "missing_row": value.block4.pop()
    elif case == "missing_block": value.model_fields_set.discard("block4")
    elif case == "nonfinite": value.block4[0].FcurrEvalPnlAmt = float("nan")
    elif case == "negative_quantity": value.block4[0].AstkBalQty = -1
    assert stock_valuation_snapshot(value, REQUEST, NOW) is None


def test_explicit_flat_account_is_zero_in_known_currency():
    value = response()
    value.block4 = []
    value.block3 = [blocks.COSOQ00201OutBlock3(CrcyCode="USD", FcurrEvalPnlAmt=0)]
    assert stock_valuation_snapshot(value, REQUEST, NOW)["groups"] == [
        {"currency": "USD", "earned": 0, "lost": 0, "net": 0}]
    value.block3 = []
    assert stock_valuation_snapshot(value, REQUEST, NOW) is None


def test_real_parser_preserves_missing_blocks_even_when_net_is_zero():
    data = {'rsp_cd': '00000', 'rsp_msg': 'success',
            'COSOQ00201OutBlock1': REQUEST.model_dump(),
            'COSOQ00201OutBlock3': [{'CrcyCode': 'USD', 'FcurrEvalPnlAmt': 0}]}
    metadata = response().header.model_dump(by_alias=True)
    from types import SimpleNamespace
    http = SimpleNamespace(status_code=200, headers=metadata)
    parsed = TrCOSOQ00201._build_response(None, http, data, None, None)
    assert not parsed._valuation_blocks_present
    assert stock_valuation_snapshot(parsed, REQUEST, NOW) is None
    data['COSOQ00201OutBlock4'] = []
    complete = TrCOSOQ00201._build_response(None, http, data, response().header, None)
    assert complete._valuation_blocks_present
    assert stock_valuation_snapshot(complete, REQUEST, NOW)['groups'][0]['net'] == 0


@pytest.mark.asyncio
async def test_failed_refresh_invalidates_snapshot_without_clearing_positions():
    client = MagicMock()
    client.cosoq00201.return_value.req_async = AsyncMock(side_effect=RuntimeError("offline"))
    tracker = StockAccountTracker(client)
    tracker._valuation_snapshot = {"groups": [{"net": Decimal(2)}]}
    tracker._positions = {"kept": object()}
    detached = tracker.get_valuation_snapshot()
    detached["groups"][0]["net"] = 99
    assert tracker.get_valuation_snapshot()["groups"][0]["net"] == 2
    await tracker._fetch_positions()
    assert tracker.get_valuation_snapshot() is None
    assert "kept" in tracker._positions
