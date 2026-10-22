"""Contract and execution checks for observed futures orderable quantity."""

from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
import socket

import pytest
from programgarden_core import NodeTypeRegistry
from programgarden.executor import FuturesOrderableQuantityNodeExecutor
from programgarden.context import ExecutionContext
from programgarden.futures_orderable import (
    build_orderable_request,
    read_orderable_quantity,
)
from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01400.blocks import (
    CIDBQ01400OutBlock1,
    CIDBQ01400OutBlock2,
    CIDBQ01400Response,
)
from programgarden_finance.ls.overseas_futureoption.market.o3105.blocks import (
    O3105OutBlock,
)


def config():
    return {
        "symbol": {"symbol": "HMHU26", "exchange": "HKEX"},
        "side": "buy",
        "order_type": "limit",
        "price": 24760,
        "connection": {
            "broker_node_id": "broker",
            "provider": "ls-sec.co.kr",
            "product": "overseas_futures",
            "credential_id": "selected",
            "paper_trading": True,
        },
    }


def execution_context(source="workflow_list"):
    credential = {"appkey": "selected-key", "appsecret": "selected-secret"}
    references = []
    if source.startswith("workflow"):
        data = credential if source == "workflow_dict" else [
            {"key": key, "value": value} for key, value in credential.items()
        ]
        references = [{"credential_id": "selected", "type": "broker_ls_overseas_futures", "data": data}]
    context = ExecutionContext(job_id="capacity-test", workflow_id="capacity-test", workflow_credentials=references)
    context._workflow_nodes_map = {
        "broker": SimpleNamespace(node_type="OverseasFuturesBrokerNode", product_scope="overseas_futures", config={"credential_id": "selected"})
    }
    context.set_output("broker", "connection", config()["connection"])
    if source == "scoped_secret":
        context.set_secret("broker_credentials:broker:selected", {**credential, "paper_trading": True})
    # A different broker's generic and direct slots must never win resolution.
    for key in ("selected", "credential_id", "broker_credentials:overseas_futures"):
        context.set_secret(key, {"appkey": "wrong-key", "appsecret": "wrong-secret"})
    return context


def response(quantity=43):
    request = build_orderable_request(config())
    echo = request.model_dump()
    echo["OvrsDrvtOrdPrc"] = "24760.00000000000"
    return CIDBQ01400Response(
        status_code=200,
        rsp_cd="00136",
        rsp_msg="Query completed",
        block1=CIDBQ01400OutBlock1(**echo),
        block2=CIDBQ01400OutBlock2(RecCnt=1, OrdAbleQty=quantity),
    )


def test_consumed_response_fields_exist_in_sdk_models():
    assert (
        set(build_orderable_request(config()).model_dump())
        <= CIDBQ01400OutBlock1.model_fields.keys()
    )
    assert "OrdAbleQty" in CIDBQ01400OutBlock2.model_fields
    assert {"Symbol", "TrdP", "UntPrc"} <= O3105OutBlock.model_fields.keys()


@pytest.mark.parametrize("quantity", [0, 1, 43])
def test_complete_zero_and_positive_capacity_are_valid(quantity):
    assert (
        read_orderable_quantity(response(quantity), build_orderable_request(config()))
        == quantity
    )


@pytest.mark.parametrize(
    "change",
    [
        {"side": "invalid"},
        {"price": 0},
        {"price": None},
        {"price": float("nan")},
        {"price": True},
        {"symbol": "HMHU26"},
        {"symbol": {"symbol": "HMHU26"}},
        {"query_type": "unknown"},
    ],
)
def test_bad_query_never_uses_a_default_price_or_instrument(change):
    with pytest.raises(ValueError):
        build_orderable_request({**config(), **change})


def test_explicit_market_and_close_query_codes_match_the_model():
    request = build_orderable_request(
        {
            **config(),
            "order_type": "market",
            "side": "sell",
            "query_type": "close",
            "price": None,
        }
    )
    assert (
        request.OvrsDrvtOrdPrc == 0
        and request.AbrdFutsOrdPtnCode == "1"
        and request.BnsTpCode == "1"
        and request.QryTpCode == "2"
    )


@pytest.mark.parametrize(
    "case",
    [
        "missing_quantity",
        "missing_echo",
        "wrong_symbol",
        "wrong_side",
        "wrong_price",
        "http_failure",
        "continued",
        "negative",
    ],
)
def test_unavailable_or_mismatched_evidence_is_rejected(case):
    result = response()
    if case == "missing_quantity":
        result.block2 = CIDBQ01400OutBlock2()
    if case == "missing_echo":
        result.block1 = CIDBQ01400OutBlock1()
    if case == "wrong_symbol":
        result.block1.IsuCodeVal = "OTHER"
    if case == "wrong_side":
        result.block1.BnsTpCode = "1"
    if case == "wrong_price":
        result.block1.OvrsDrvtOrdPrc = "24759"
    if case == "http_failure":
        result.status_code = 503
    if case == "continued":
        result.rsp_cd = "00133"
    if case == "negative":
        result.block2.OrdAbleQty = -1
    with pytest.raises(ValueError):
        read_orderable_quantity(result, build_orderable_request(config()))


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["workflow_list", "workflow_dict", "scoped_secret"])
async def test_executor_uses_exact_credential_and_read_only_query(source):
    context = execution_context(source)
    api = MagicMock()
    call = api.overseas_futureoption.return_value.accno.return_value.CIDBQ01400.return_value
    call.req_async = AsyncMock(return_value=response(0))
    with (
        patch(
            "programgarden.executor.evaluate_all_bindings", side_effect=lambda c, *_: c
        ),
        patch("programgarden.executor.ensure_ls_login", return_value=(api, True, None)) as login,
        patch.object(
            socket.socket, "connect", side_effect=AssertionError("Network forbidden")
        ),
    ):
        result = await FuturesOrderableQuantityNodeExecutor().execute(
            "capacity", "OverseasFuturesOrderableQuantityNode", config(), context
        )
    assert login.call_args.args[:3] == ("selected-key", "selected-secret", True)
    call.req_async.assert_awaited_once()
    assert result == {"quantity": 0, "verified": True, "error": None}
    api.overseas_futureoption.return_value.order.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [RuntimeError, ValueError])
async def test_failed_query_does_not_fabricate_zero_or_retry(exception):
    context = execution_context()
    api = MagicMock()
    call = api.overseas_futureoption.return_value.accno.return_value.CIDBQ01400.return_value
    call.req_async = AsyncMock(side_effect=exception("PRIVATE TOKEN"))
    with (
        patch(
            "programgarden.executor.evaluate_all_bindings", side_effect=lambda c, *_: c
        ),
        patch("programgarden.executor.ensure_ls_login", return_value=(api, True, None)),
    ):
        result = await FuturesOrderableQuantityNodeExecutor().execute(
            "capacity", "OverseasFuturesOrderableQuantityNode", config(), context
        )
    assert result["quantity"] is None and result["verified"] is False
    assert "PRIVATE" not in result["error"]
    call.req_async.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["missing", "duplicate", "wrong_type", "wrong_mode", "wrong_broker", "wrong_alias", "wrong_output"])
async def test_incompatible_credential_evidence_never_logs_in(case):
    context = execution_context("missing" if case == "missing" else "workflow_dict")
    value = config()
    if case == "duplicate":
        context._workflow_credentials *= 2
    if case == "wrong_type":
        context._workflow_credentials[0]["type"] = "broker_ls_overseas_stock"
    if case == "wrong_mode":
        context._workflow_credentials[0]["data"]["paper_trading"] = False
    if case == "wrong_broker":
        value["connection"]["broker_node_id"] = "other"
    if case == "wrong_alias":
        value["connection"]["credential_id"] = "other"
    if case == "wrong_output":
        context.set_output("broker", "connection", {**value["connection"], "paper_trading": False})
    with patch("programgarden.executor.ensure_ls_login") as login:
        result = await FuturesOrderableQuantityNodeExecutor().execute(
            "capacity", "OverseasFuturesOrderableQuantityNode", value, context
        )
    login.assert_not_called()
    assert result["verified"] is False and result["quantity"] is None


@pytest.mark.asyncio
async def test_deep_fixture_never_logs_in_or_queries():
    context = MagicMock(is_deep_validate=True)
    context.get_deep_fixture.return_value = None
    with (
        patch(
            "programgarden.executor.evaluate_all_bindings", side_effect=lambda c, *_: c
        ),
        patch("programgarden.executor.ensure_ls_login") as login,
        patch.object(
            socket.socket, "connect", side_effect=AssertionError("Network forbidden")
        ),
    ):
        result = await FuturesOrderableQuantityNodeExecutor().execute(
            "capacity", "OverseasFuturesOrderableQuantityNode", config(), context
        )
    assert result["quantity"] == 1 and result["verified"]
    login.assert_not_called()


def test_registered_schema_supports_expression_inputs_and_output_ports():
    registry = NodeTypeRegistry()
    schema = registry.get_schema("OverseasFuturesOrderableQuantityNode")
    assert schema.product_scope == "overseas_futures"
    assert {
        "symbol",
        "side",
        "price",
        "query_type",
        "order_type",
    } <= schema.config_schema.keys()
    assert {o["name"] for o in schema.outputs} == {"quantity", "verified", "error"}
    market = registry.get_schema("OverseasFuturesMarketDataNode")
    fields = next(o["fields"] for o in market.outputs if o["name"] == "values")
    assert "tick_size" in {f["name"] for f in fields}
