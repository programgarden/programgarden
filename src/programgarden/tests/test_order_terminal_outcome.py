"""One-shot order rejection is a failed run; handled cycle errors keep flowing."""

from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import NewOrderNodeExecutor, WorkflowJob
from programgarden.resolver import ResolvedEdge, ResolvedNode, ResolvedWorkflow
from programgarden_core.bases.listener import BaseExecutionListener
from programgarden_finance.ls.overseas_futureoption.order.CIDBT00100 import TrCIDBT00100


RAW_MESSAGE = "모의투자 주문가능금액이 부족합니다."
REJECTION = {
    "order_result": {"success": False, "error": RAW_MESSAGE},
    "order_id": "",
}


class Capture(BaseExecutionListener):
    def __init__(self):
        self.notices = []
        self.states = []

    async def on_notification(self, event):
        self.notices.append(asdict(event))

    async def on_job_state_change(self, event):
        self.states.append(event.state)


def make_job(tmp_path, output=None, *, downstream=False, raised=False):
    context = ExecutionContext(job_id="terminal-test", workflow_id="test", storage_dir=str(tmp_path))
    nodes = {
        "start": ResolvedNode("start", "StartNode", "infra", {}),
        "order": ResolvedNode("order", "OverseasFuturesNewOrderNode", "order", {}),
    }
    edges = [ResolvedEdge("start", "order")]
    if downstream:
        nodes["display"] = ResolvedNode("display", "SummaryDisplayNode", "display", {})
        edges.append(ResolvedEdge("order", "display"))
    workflow = ResolvedWorkflow("test", "1.0.0", nodes, edges, list(nodes))
    result = deepcopy(REJECTION if output is None else output)

    async def execute_node(**kwargs):
        if kwargs["node_id"] == "order":
            if raised:
                raise RuntimeError("Direct node exception")
            return deepcopy(result)
        return {}

    job = WorkflowJob("terminal-test", workflow, context, SimpleNamespace(execute_node=execute_node))
    capture = Capture()
    context.add_listener(capture)
    context.start()
    return job, capture, result


@pytest.mark.asyncio
async def test_sdk_rejection_reaches_failed_terminal_state_with_original_message(tmp_path):
    # Actual response parsing + futures executor, with no transport request.
    response = TrCIDBT00100._build_response(
        None, SimpleNamespace(status=200), {"rsp_cd": "01425", "rsp_msg": RAW_MESSAGE}, {}, None,
    )
    request = SimpleNamespace(req_async=AsyncMock(return_value=response))
    ls = MagicMock()
    ls.overseas_futureoption.return_value.order.return_value.CIDBT00100.return_value = request
    context = ExecutionContext(
        job_id="ack-test", workflow_id="test", storage_dir=str(tmp_path),
        workflow_credentials=[{"credential_id": "fixture", "data": {"appkey": "fixture-key", "appsecret": "fixture-secret"}}],
    )
    connection = {"product": "overseas_futures", "paper_trading": True, "broker_node_id": "broker", "credential_id": "fixture"}
    output = await NewOrderNodeExecutor()._execute_overseas_futures(
        ls, {"symbol": "SYNTHETIC", "exchange": "TEST", "quantity": 1, "price": 1.0},
        "buy", "limit", {"connection": connection}, context, "order",
    )
    request.req_async.assert_awaited_once()
    assert output["order_result"]["diagnostics"]["raw_msg"] == RAW_MESSAGE
    assert output["order_result"]["error"] == f"Empty OrderNo: {RAW_MESSAGE}"
    job, capture, _ = make_job(tmp_path, output)
    await job._run()
    state = job.get_state()
    assert state["status"] == "failed"
    assert state["nodes"]["order"]["state"] == "failed"
    assert RAW_MESSAGE in state["stats"]["last_error"]
    assert state["nodes"]["order"]["outputs"]["order_result"]["diagnostics"]["raw_msg"] == RAW_MESSAGE
    assert state["stats"]["orders_placed"] == state["stats"]["orders_filled"] == 0
    assert capture.states[-1] == "failed"
    assert [n["category"] for n in capture.notices] == ["workflow_failed"]
    assert RAW_MESSAGE in capture.notices[0]["data"]["error"]


@pytest.mark.asyncio
async def test_successful_downstream_does_not_handle_an_order_rejection(tmp_path):
    job, capture, _ = make_job(tmp_path, downstream=True)
    await job._run()
    assert job.get_state()["nodes"]["display"]["state"] == "completed"
    assert job.status == "failed"
    assert capture.notices[-1]["category"] == "workflow_failed"


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["fetch_failed", "no_symbol"])
async def test_direct_non_broker_order_failure_also_fails_one_shot(tmp_path, reason):
    job, _, _ = make_job(tmp_path, {"order_result": {"success": False, "reason": reason}})
    await job._run()
    assert job.status == "failed"


@pytest.mark.asyncio
@pytest.mark.parametrize("output", [
    {"order_result": {"success": True, "status": "submitted"}, "order_id": "fixture-order"},
    {"order_result": {"success": False, "reason": "no_signal"}, "order_id": ""},
])
async def test_success_and_no_signal_still_complete(tmp_path, output):
    job, capture, _ = make_job(tmp_path, output)
    await job._run()
    assert job.status == "completed"
    assert job.stats["errors_count"] == 0
    assert capture.notices[-1]["category"] == "workflow_completed"


@pytest.mark.asyncio
async def test_direct_exception_preserves_existing_fail_fast_contract(tmp_path):
    job, _, _ = make_job(tmp_path, raised=True, downstream=True)
    await job._run()
    assert job.status == "failed"
    assert job.get_state()["nodes"]["display"]["state"] == "pending"


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["schedule", "realtime"])
async def test_rejected_cycle_does_not_kill_a_resident_job(tmp_path, source):
    job, _, output = make_job(tmp_path)
    if source == "schedule":
        job._has_schedule_node = True
    else:
        job._stay_connected_nodes = ["realtime-fixture"]

    async def next_cycle():
        assert job.context.is_running and not job.context.is_failed
        assert job.get_state()["nodes"]["order"]["state"] == "failed"
        output["order_result"] = {"success": False, "reason": "no_signal"}
        await job._execute_main_flow()
        assert job.get_state()["nodes"]["order"]["state"] == "completed"

    job._event_loop = AsyncMock(side_effect=next_cycle)
    await job._run()
    job._event_loop.assert_awaited_once()
    assert job.status == "completed"
    assert job.stats["errors_count"] == 1


@pytest.mark.asyncio
async def test_prior_pass_failure_and_historical_statistics_do_not_poison_success(tmp_path):
    job, _, output = make_job(tmp_path)
    await job._execute_main_flow()
    assert job.stats["errors_count"] == 1
    output["order_result"] = {"success": False, "reason": "no_signal"}
    await job._run()
    assert job.status == "completed"
    assert job.stats["errors_count"] == 1


@pytest.mark.asyncio
async def test_explicit_stop_after_rejection_keeps_existing_stop_completion(tmp_path):
    job, capture, _ = make_job(tmp_path)
    main_flow = job._execute_main_flow

    async def stopped_flow():
        await main_flow()
        job.context.stop()

    job._execute_main_flow = stopped_flow
    await job._run()
    assert job.status == "completed"
    assert capture.notices[-1]["category"] == "workflow_completed"


@pytest.mark.asyncio
@pytest.mark.parametrize("continue_on_error", [True, False])
async def test_split_exception_obeys_its_explicit_continuation_policy(tmp_path, continue_on_error):
    context = ExecutionContext(job_id="split-test", workflow_id="test", storage_dir=str(tmp_path))
    nodes = {
        "split": ResolvedNode("split", "SplitNode", "infra", {
            "array": [1, 2], "continue_on_error": continue_on_error,
        }),
        "branch": ResolvedNode("branch", "FixtureNode", "data", {}),
        "aggregate": ResolvedNode("aggregate", "AggregateNode", "infra", {}),
    }
    workflow = ResolvedWorkflow("test", "1.0.0", nodes, [
        ResolvedEdge("split", "branch"), ResolvedEdge("branch", "aggregate"),
    ], list(nodes))
    branch_results = iter([RuntimeError("Handled branch failure"), {"value": 2}])

    async def execute_node(**kwargs):
        if kwargs["node_id"] == "branch":
            result = next(branch_results)
            if isinstance(result, Exception):
                raise result
            return result
        return {"items": context.get_node_state("aggregate", "_collected_items")}

    job = WorkflowJob("split-test", workflow, context, SimpleNamespace(execute_node=execute_node))
    context.start()
    await job._run()
    assert job.status == ("completed" if continue_on_error else "failed")
    if continue_on_error:
        assert context.get_all_outputs("aggregate")["items"] == [None, 2]


@pytest.mark.asyncio
async def test_auto_iteration_keeps_its_existing_item_continuation_boundary(tmp_path):
    job, _, _ = make_job(tmp_path)
    executor = job.executor.execute_node
    item_results = iter([RuntimeError("Handled item failure"), deepcopy(REJECTION)])

    async def execute_node(**kwargs):
        if kwargs["node_id"] != "order":
            return await executor(**kwargs)
        result = next(item_results)
        if isinstance(result, Exception):
            raise result
        return result

    job.executor.execute_node = execute_node
    job._should_auto_iterate = lambda node_type, *_: (
        (True, "order", [{"quantity": 1}, {"quantity": 1}])
        if node_type == "OverseasFuturesNewOrderNode" else (False, None, [])
    )
    job._auto_iterate_pacing_sleep = AsyncMock()
    await job._run()
    assert job.status == "completed"
    assert any("Handled item failure" in row["message"] for row in job.context.get_logs())
