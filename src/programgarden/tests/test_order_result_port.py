"""Catalog result rows resolve in direct, standalone, and saved workflow paths."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import NewOrderNodeExecutor, WorkflowExecutor, WorkflowJob
from programgarden.node_runner import NodeRunner
from programgarden_core import EmptyOrderReason
from programgarden_core.expression import ExpressionEvaluator
from programgarden_core.nodes.order import (
    KoreaStockNewOrderNode, OverseasFuturesNewOrderNode, OverseasStockNewOrderNode,
)


RAW_MESSAGE = "모의투자 주문가능금액이 부족합니다."
ORDER = {"symbol": "HMHU26", "exchange": "HKEX", "quantity": 1, "price": 25250.0}
FUTURES_CONNECTION = {"product": "overseas_futures", "paper_trading": True, "broker_node_id": "broker", "credential_id": "fixture"}
MARKETS = [
    (OverseasStockNewOrderNode, "overseas_stock", "_execute_overseas_stock"),
    (OverseasFuturesNewOrderNode, "overseas_futures", "_execute_overseas_futures"),
    (KoreaStockNewOrderNode, "korea_stock", "_execute_korea_stock"),
]


def context(tmp_path, *, dry_run=False):
    return ExecutionContext(
        job_id="result-port", workflow_id="result-port", storage_dir=str(tmp_path),
        context_params={"dry_run": dry_run},
        secrets={"credential_id": {"appkey": "fixture-key", "appsecret": "fixture-secret"}},
        workflow_credentials=[{"credential_id": "fixture", "data": {"appkey": "fixture-key", "appsecret": "fixture-secret"}}],
    )


def result_for(executor, outcome, *, nested_id=False):
    if outcome == "no_signal":
        return executor._empty_result(EmptyOrderReason.NO_SIGNAL)
    output = executor._order_result(
        outcome == "accepted", ORDER["symbol"], ORDER["exchange"], "buy", 1, ORDER["price"],
        None if outcome == "accepted" else RAW_MESSAGE,
        "fixture-order" if outcome == "accepted" and not nested_id else "",
    )
    if nested_id and outcome == "accepted":
        output["order_result"]["order_id"] = "fixture-order"
        output["order_result"]["product"] = "korea_stock"
    if outcome == "rejected":
        output["order_result"]["diagnostics"] = {"rsp_cd": "01425", "raw_msg": RAW_MESSAGE}
    return output


@pytest.mark.asyncio
@pytest.mark.parametrize("node_class,product,method", MARKETS)
@pytest.mark.parametrize("outcome", ["accepted", "rejected", "no_signal"])
async def test_catalog_result_list_preserves_final_legacy_output(tmp_path, monkeypatch, node_class, product, method, outcome):
    executor = NewOrderNodeExecutor()
    legacy = result_for(executor, outcome, nested_id=product == "korea_stock")
    product_call = AsyncMock(return_value=legacy)
    monkeypatch.setattr(executor, method, product_call)
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", lambda *a, **k: (object(), True, None))

    async def confirm(ls, product, order_type, output, *args):
        # Real confirmation updates legacy output in place, after result creation.
        output["order_result"].update(status="open", filled_quantity=0, filled_count=0)

    monkeypatch.setattr(executor, "_confirm_order_fill", confirm)
    output = await executor.execute(
        "order", node_class.__name__,
        {"connection": FUTURES_CONNECTION if product == "overseas_futures" else {"product": product}, "order": dict(ORDER)}, context(tmp_path),
    )
    assert {key: value for key, value in output.items() if key != "result"} == legacy
    assert isinstance(output["result"], list) and len(output["result"]) == 1
    row = output["result"][0]
    assert next(iter(row)) == "order_id"
    assert row == {**legacy["order_result"], "order_id": "fixture-order" if outcome == "accepted" else ""}
    assert row is not output["order_result"]
    product_call.assert_awaited_once()
    if outcome == "accepted":
        assert row["status"] == "open" and row["filled_quantity"] == 0
        # The declared successful row fields exist, including the formerly
        # separate top-level order_id (or Korea's legacy inner order_id).
        port = next(p for p in node_class(id="fixture")._outputs if p.name == "result")
        assert isinstance(port.example, list)
        assert {field["name"] for field in port.fields}.issubset(row)
    elif outcome == "rejected":
        assert row["status"] == "failed" and row["diagnostics"]["raw_msg"] == RAW_MESSAGE
        row["diagnostics"]["raw_msg"] = "Consumer-local change"
        assert legacy["order_result"]["diagnostics"]["raw_msg"] == RAW_MESSAGE
    else:
        assert row["reason"] == "no_signal" and row["success"] is False
        assert "filled_quantity" not in row


@pytest.mark.asyncio
@pytest.mark.parametrize("node_class,product,method", MARKETS)
async def test_dry_run_exposes_simulated_row_without_changing_flat_envelope(tmp_path, monkeypatch, node_class, product, method):
    def no_login(*args, **kwargs):
        pytest.fail("Dry-run result projection must not contact a broker")

    monkeypatch.setattr("programgarden.executor.ensure_ls_login", no_login)
    config = {"order": dict(ORDER), "connection": {"appsecret": "fixture-secret"}}
    output = await NewOrderNodeExecutor().execute("order", node_class.__name__, config, context(tmp_path, dry_run=True))
    assert output["requested"] is config and output["dry_run"] is True
    assert output["status"] == "simulated" and output["order_id"].startswith("DRYRUN-")
    assert output["result"] == [{"order_id": output["order_id"], "status": "simulated", "dry_run": True}]
    assert "order_result" not in output  # Legacy simulation envelope stays intact.


@pytest.mark.asyncio
async def test_no_signal_and_early_error_have_rows_without_any_dispatch(tmp_path, monkeypatch):
    def no_login(*args, **kwargs):
        pytest.fail("Early results must return without broker login")

    monkeypatch.setattr("programgarden.executor.ensure_ls_login", no_login)
    executor = NewOrderNodeExecutor()
    ctx = context(tmp_path)
    ctx.set_output("sizing", "orders", [])
    ctx.set_output("sizing", "reason", "no_signal")
    output = await executor.execute("order", "OverseasFuturesNewOrderNode", {
        "connection": dict(FUTURES_CONNECTION), "order": "{{ nodes.sizing.orders }}",
    }, ctx)
    assert output["result"][0]["reason"] == "no_signal"
    assert output["result"][0]["order_id"] == ""
    failed = await executor.execute("order", "OverseasFuturesNewOrderNode", {}, ctx)
    assert failed["result"][0]["error"] == failed["order_result"]["error"]
    assert failed["result"][0]["success"] is False


@pytest.mark.asyncio
async def test_replay_rebuilds_rows_after_replay_marker_without_mutating_registry(tmp_path, monkeypatch):
    executor = NewOrderNodeExecutor()
    cached = result_for(executor, "accepted")
    cached["result"] = [{"status": "stale fixture"}]
    before = deepcopy(cached)
    ctx = context(tmp_path)
    monkeypatch.setattr(ctx, "check_order_already_submitted", lambda **kwargs: cached)
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", lambda *a, **k: pytest.fail("Replay must not send an order"))
    output = await executor.execute("order", "OverseasFuturesNewOrderNode", {
        "connection": dict(FUTURES_CONNECTION), "order": dict(ORDER),
    }, ctx)
    assert output["result"][0]["idempotent_replay"] is True
    assert output["result"][0]["order_id"] == "fixture-order"
    assert output["result"][0]["status"] == "submitted"
    assert cached == before


@pytest.mark.asyncio
async def test_fill_confirmation_and_fractional_metadata_are_projected_after_updates(tmp_path, monkeypatch):
    executor = NewOrderNodeExecutor()
    legacy = result_for(executor, "accepted")
    monkeypatch.setattr(executor, "_execute_overseas_stock", AsyncMock(return_value=legacy))
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", lambda *a, **k: (object(), True, None))

    async def confirm(ls, product, order_type, output, *args):
        output["order_result"].update(status="filled", filled_quantity=1, filled_count=1, fill_price=25249.0)

    monkeypatch.setattr(executor, "_confirm_order_fill", confirm)
    output = await executor.execute("order", "OverseasStockNewOrderNode", {
        "connection": {"product": "overseas_stock"}, "order": {**ORDER, "quantity": 1.5},
    }, context(tmp_path))
    row = output["result"][0]
    assert (row["status"], row["filled_quantity"], row["filled_count"], row["fill_price"]) == ("filled", 1, 1, 25249.0)
    assert row["fractional_remainder"] == 0.5
    assert output["order_result"] == legacy["order_result"]


@pytest.mark.asyncio
async def test_node_runner_receives_the_same_result_port(tmp_path):
    runner = NodeRunner()
    runner._context = context(tmp_path)
    # Missing connection returns a real executor error before broker setup.
    output = await runner.run("OverseasFuturesNewOrderNode", node_id="order")
    assert output["result"] == [{**output["order_result"], "order_id": ""}]
    assert output["result"][0]["success"] is False
    await runner.cleanup()


def saved_four_node_workflow():
    # Task 8e's generated/saved graph, node settings, and expression are intact.
    # Only redacted identity/credential references are replaced with inert fixtures.
    return {
        "id": "saved-order-result-fixture", "name": "HMHU26 Paper One Shot", "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "fixture", "paper_trading": True},
            {"id": "order", "type": "OverseasFuturesNewOrderNode", "side": "buy", "order_type": "limit", "order": dict(ORDER)},
            {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.order.result }}", "title": "HMHU26 주문 결과"},
        ],
        "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "order"}, {"from": "order", "to": "display"}],
        "credentials": [{"credential_id": "fixture", "type": "broker_ls_overseas_futures", "data": []}],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["accepted", "rejected", "no_signal"])
async def test_saved_workflow_expression_and_table_receive_result_rows(tmp_path, monkeypatch, outcome):
    executor = WorkflowExecutor()
    resolved, validation = executor.compile(saved_four_node_workflow())
    assert validation.is_valid, validation.errors
    ctx = context(tmp_path)
    broker = executor._executors["OverseasFuturesBrokerNode"]
    monkeypatch.setattr(broker, "execute", AsyncMock(return_value={"connection": dict(FUTURES_CONNECTION)}))
    order_executor = executor._executors["OverseasFuturesNewOrderNode"]
    product_call = AsyncMock(return_value=result_for(order_executor, outcome))
    monkeypatch.setattr(order_executor, "_execute_overseas_futures", product_call)
    monkeypatch.setattr(order_executor, "_confirm_order_fill", AsyncMock())
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", lambda *a, **k: (object(), True, None))
    job = WorkflowJob("result-port", resolved, ctx, executor)
    ctx.start()
    await job._run()
    product_call.assert_awaited_once()
    rows = ExpressionEvaluator(ctx.get_expression_context()).evaluate("{{ nodes.order.result }}")
    assert isinstance(rows, list) and len(rows) == 1
    assert ctx.get_all_outputs("display")["data"] == rows
    assert ctx.get_all_outputs("display")["rendered"] is True
    assert job.status == ("failed" if outcome == "rejected" else "completed")
    assert job.stats["orders_filled"] == 0
    if outcome == "accepted":
        assert rows[0]["order_id"] == "fixture-order" and rows[0]["status"] == "submitted"
        assert job.stats["orders_placed"] == 1
    elif outcome == "rejected":
        assert rows[0]["error"] == RAW_MESSAGE and rows[0]["diagnostics"]["rsp_cd"] == "01425"
        assert rows[0]["order_id"] == "" and job.stats["orders_placed"] == 0
    else:
        assert rows[0]["reason"] == "no_signal" and job.stats["orders_placed"] == 0


def test_existing_auto_iteration_merges_all_result_rows_without_changing_legacy_rule(tmp_path):
    executor = NewOrderNodeExecutor()
    outputs = [result_for(executor, "accepted"), result_for(executor, "rejected")]
    for output in outputs:
        output["result"] = [{**output["order_result"], "order_id": output["order_id"]}]
    job = WorkflowJob("merge", SimpleNamespace(nodes={}), context(tmp_path), SimpleNamespace())
    merged = job._merge_iterate_results(outputs)
    assert len(merged["result"]) == 2
    assert merged["result"][0]["order_id"] == "fixture-order"
    assert merged["result"][1]["error"] == RAW_MESSAGE
    assert merged["order_result"] == outputs[-1]["order_result"]


@pytest.mark.asyncio
async def test_implicit_split_order_collection_keeps_legacy_row_shape(tmp_path, monkeypatch):
    definition = saved_four_node_workflow()
    definition["nodes"].insert(2, {"id": "split", "type": "SplitNode", "array": [dict(ORDER)]})
    definition["nodes"][-1] = {"id": "aggregate", "type": "AggregateNode", "mode": "collect"}
    definition["edges"] = [
        {"from": "start", "to": "broker"}, {"from": "broker", "to": "split"},
        {"from": "split", "to": "order"}, {"from": "order", "to": "aggregate"},
    ]
    executor = WorkflowExecutor()
    resolved, validation = executor.compile(definition)
    assert validation.is_valid, validation.errors
    ctx = context(tmp_path)
    monkeypatch.setattr(executor._executors["OverseasFuturesBrokerNode"], "execute", AsyncMock(
        return_value={"connection": dict(FUTURES_CONNECTION)},
    ))
    order_executor = executor._executors["OverseasFuturesNewOrderNode"]
    legacy = result_for(order_executor, "accepted")
    monkeypatch.setattr(order_executor, "_execute_overseas_futures", AsyncMock(return_value=legacy))
    monkeypatch.setattr(order_executor, "_confirm_order_fill", AsyncMock())
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", lambda *a, **k: (object(), True, None))
    job = WorkflowJob("result-port", resolved, ctx, executor)
    ctx.start()
    await job._run()
    assert job.status == "completed"
    assert ctx.get_all_outputs("aggregate")["array"] == [legacy["order_result"]]
    # Explicit catalog expressions still resolve to their documented list.
    assert ExpressionEvaluator(ctx.get_expression_context()).evaluate("{{ nodes.order.result }}") == [
        {**legacy["order_result"], "order_id": "fixture-order"},
    ]
