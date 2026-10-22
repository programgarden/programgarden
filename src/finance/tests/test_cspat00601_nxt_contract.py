"""NXT source and real SDK transport regressions using offline HTTP doubles."""
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import requests

from programgarden_finance import CSPAT00601
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock.order import Order
from programgarden_finance.ls.token_manager import TokenManager


# Whitelisted fields from the owner's LS documentation example, not live data.
SOURCE_REQUEST = {
    "IsuNo": "A272210", "OrdQty": 1, "OrdPrc": 35000,
    "BnsTpCode": "2", "OrdprcPtnCode": "00", "MgntrnCode": "000",
    "LoanDt": "", "OrdCndiTpCode": "0", "MbrNo": "NXT",
}
SOURCE_RESPONSE = {
    "rsp_cd": "00040",
    "CSPAT00601OutBlock1": {**SOURCE_REQUEST, "OrdPrc": "35000.00", "RecCnt": 1},
    "CSPAT00601OutBlock2": {
        "RecCnt": 1, "OrdNo": 32004, "OrdTime": "153257702",
        "OrdMktCode": "10", "OrdPtnCode": "02", "ShtnIsuNo": "A272210",
        "OrdAmt": 35000,
    },
}


def example_module():
    path = Path(__file__).resolve().parents[1] / "example/korea_stock/run_CSPAT00601_nxt.py"
    spec = importlib.util.spec_from_file_location("nxt_order_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def order_from_public_facade():
    manager = MagicMock(spec=TokenManager)
    manager.get_bearer_token.return_value = "Bearer offline-test"
    manager.appkey = None
    ls = Mock()
    ls.korea_stock.return_value.order.return_value = Order(manager)
    return example_module().build_order(
        ls, symbol="A272210", side="buy", quantity=1, limit_price=35000,
    )


def test_preview_matches_the_supplied_request_without_login_or_submission(capsys):
    with patch("programgarden_finance.LS.login", side_effect=AssertionError("No login")), \
         patch("requests.post", side_effect=AssertionError("No HTTP")):
        example_module().main([])
    output = capsys.readouterr().out
    assert '"MbrNo": "NXT"' in output
    assert "Preview only" in output
    assert example_module().build_body("A272210", "buy", 1, 35000).model_dump() == SOURCE_REQUEST


@pytest.mark.parametrize("symbol", ["272210", "A272210"])
def test_documented_live_stock_symbol_formats(symbol):
    body = example_module().build_body(symbol, "sell", 1, 35000)
    assert body.IsuNo == symbol and body.BnsTpCode == "1" and body.MbrNo == "NXT"


@pytest.mark.parametrize("symbol,side,quantity,price", [
    ("N272210", "buy", 1, 35000), ("272210", "hold", 1, 35000),
    ("272210", "buy", 0, 35000), ("272210", "buy", True, 35000),
    ("272210", "buy", 1, 0), ("272210", "buy", 1, float("nan")),
])
def test_example_rejects_invalid_inputs(symbol, side, quantity, price):
    with pytest.raises(ValueError):
        example_module().build_body(symbol, side, quantity, price)


def test_sync_public_facade_sends_nxt_unchanged_and_parses_ack():
    order = order_from_public_facade()
    wire = Mock(spec=requests.Response, status_code=200, headers={})
    wire.json.return_value = SOURCE_RESPONSE
    with patch("requests.post", return_value=wire) as post:
        result = order.req()
    assert result.error_msg is None
    assert post.call_count == 1
    assert post.call_args.kwargs["url"] == URLS.KOREA_STOCK_ORDER_URL
    assert post.call_args.kwargs["json"] == {"CSPAT00601InBlock1": SOURCE_REQUEST}
    assert result.block1.MbrNo == "NXT" and "MbrNo" in result.block1.model_fields_set
    assert result.block2.OrdNo == 32004
    assert result.block2.OrdMktCode == "10"  # Preserve raw market code, not a venue.


@pytest.mark.asyncio
async def test_async_transport_sends_nxt_unchanged():
    order = order_from_public_facade()
    wire = MagicMock(status=200, headers={})
    wire.json = AsyncMock(return_value=SOURCE_RESPONSE)
    request_context = MagicMock()
    request_context.__aenter__ = AsyncMock(return_value=wire)
    session = MagicMock()
    session.post.return_value = request_context
    session.__aenter__ = AsyncMock(return_value=session)
    with patch("aiohttp.ClientSession", return_value=session):
        result = await order.req_async()
    assert result.error_msg is None
    assert session.post.call_count == 1
    assert session.post.call_args.kwargs["json"] == {"CSPAT00601InBlock1": SOURCE_REQUEST}
    assert result.block1.MbrNo == "NXT"


def test_order_timeout_does_not_retry():
    with patch("requests.post", side_effect=requests.Timeout("offline timeout")) as post:
        result = order_from_public_facade().req()
    assert post.call_count == 1
    assert result.error_msg and result.block2 is None


def test_missing_route_echo_is_unavailable_and_legacy_default_is_preserved():
    absent = CSPAT00601.CSPAT00601OutBlock1(IsuNo="A272210")
    observed_empty = CSPAT00601.CSPAT00601OutBlock1(MbrNo="")
    assert absent.MbrNo == observed_empty.MbrNo == ""
    assert "MbrNo" not in absent.model_fields_set
    assert "MbrNo" in observed_empty.model_fields_set
    assert CSPAT00601.CSPAT00601InBlock1(IsuNo="005930", OrdQty=1, BnsTpCode="2").MbrNo == ""
    assert set(SOURCE_REQUEST) <= CSPAT00601.CSPAT00601InBlock1.model_fields.keys()
    assert set(SOURCE_RESPONSE["CSPAT00601OutBlock1"]) <= CSPAT00601.CSPAT00601OutBlock1.model_fields.keys()
    assert set(SOURCE_RESPONSE["CSPAT00601OutBlock2"]) <= CSPAT00601.CSPAT00601OutBlock2.model_fields.keys()
