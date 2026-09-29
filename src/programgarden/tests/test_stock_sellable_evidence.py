"""Preserve broker sell capacity independently of holdings, without live calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden.executor import AccountNodeExecutor
from programgarden_core.nodes.base import OVERSEAS_STOCK_POSITION_FIELDS
from programgarden_finance import COSOQ00201


@pytest.mark.asyncio
@pytest.mark.parametrize("capacity", [3.0, 0.0, 0.25, None])
async def test_account_preserves_observed_sellable_quantity(capacity):
    raw = {"ShtnIsuNo": "SYNTH", "AstkBalQty": 7.0, "FcurrMktCode": "82"}
    if capacity is not None:
        raw["AstkSellAbleQty"] = capacity
    row = COSOQ00201.COSOQ00201OutBlock4(**raw)
    response = SimpleNamespace(error_msg=None, block2=None, block4=[row], parse_warnings=[])
    account = MagicMock()
    account.cosoq00201.return_value.req_async = AsyncMock(return_value=response)
    account.cosoq02701.return_value.req_async = AsyncMock(return_value=SimpleNamespace(
        error_msg=None, block3=[SimpleNamespace(
            CrcyCode="USD", FcurrOrdAbleAmt=100.0, FcurrDps=100.0, BaseXchrat=1300.0,
        )], block4=None,
    ))
    client = MagicMock()
    client.overseas_stock.return_value.accno.return_value = account

    result = await AccountNodeExecutor()._ls_overseas_stock(client, "account", MagicMock())

    assert len(result["positions"]) == 1
    position = result["positions"][0]
    assert position["quantity"] == position["qty"] == 7.0
    assert position["sellable_qty"] == capacity
    request = account.cosoq00201.call_args.args[0]
    assert request.RecCnt == 1 and request.CrcyCode == "ALL" and request.AstkBalTpCode == "00"
    assert len(request.BaseDt) == 8


def test_sell_capacity_uses_actual_sdk_and_catalog_contract():
    fields = COSOQ00201.COSOQ00201OutBlock4.model_fields
    assert {"ShtnIsuNo", "AstkBalQty", "AstkSellAbleQty", "FcurrMktCode"} <= fields.keys()
    assert "AstkSellAbleQty" not in COSOQ00201.COSOQ00201OutBlock4().model_fields_set
    assert any(field["name"] == "sellable_qty" for field in OVERSEAS_STOCK_POSITION_FIELDS)
