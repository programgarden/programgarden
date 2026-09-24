"""Native main/Split/realtime traversal must respect time gate decisions.

There are no broker, network or messaging nodes. A computation behind the gate
represents the trading body; reaching it after a refusal is the regression.
"""
import pytest

from programgarden.context import ExecutionContext, WorkflowEvent
from programgarden.executor import WorkflowExecutor, WorkflowJob
from programgarden_core.nodes.trigger import TradingHoursFilterNode
from tests.test_validation_replay import code


class ObservedExecutor(WorkflowExecutor):
    def __init__(self):
        super().__init__()
        self.visited = []

    async def execute_node(self, node_id, *args, **kwargs):
        self.visited.append(node_id)
        return await super().execute_node(node_id, *args, **kwargs)


async def traverse(tmp_path, gate, path, *, branch=False, merge=False):
    nodes = [{"id": "start", "type": "StartNode"}]
    source = "start"
    if path == "split":
        nodes += [{"id": "watch", "type": "WatchlistNode", "symbols": [{"symbol": "OFFLINE", "exchange": "NASDAQ"}]},
                  {"id": "split", "type": "SplitNode", "array": "{{ nodes.watch.symbols }}"}]
        source = "split"
    nodes += [gate, code("body", "17"), code("independent", "42"), code("join", "99")]
    edges = [{"from": source, "to": "gate"}, {"from": "gate", "to": "body"},
             {"from": "body", "to": "join"}, {"from": source, "to": "independent"},
             {"from": "independent", "to": "join"}]
    if path == "split":
        edges += [{"from": "start", "to": "watch"}, {"from": "watch", "to": "split"}]
        nodes.append({"id": "aggregate", "type": "AggregateNode", "mode": "collect"})
        edges.append({"from": "join", "to": "aggregate"})
    if branch:
        nodes.append(code("blocked", "-1"))
        edges.append({"from": "gate", "from_port": "blocked", "to": "blocked"})
        if merge:
            edges.append({"from": "blocked", "to": "join"})
        if path == "split":
            edges.append({"from": "blocked", "to": "aggregate"})
    executor = ObservedExecutor()
    workflow, validation = executor.compile({"id": "time-gate", "name": "Time gate", "nodes": nodes, "edges": edges})
    assert validation.is_valid, [(e.location, e.message) for e in validation.errors]
    context = ExecutionContext("offline", workflow.workflow_id, context_params={"dry_run": False},
        workflow_edges=workflow.edges, workflow_nodes=workflow.nodes, storage_dir=str(tmp_path))
    context.allow_code_node = True
    context.start()
    job = WorkflowJob("offline", workflow, context, executor)
    context.set_workflow_job(job)
    try:
        if path == "main":
            await job._execute_main_flow()
        elif path == "split":
            branch_nodes = job._get_branch_nodes("split", "aggregate")
            order = [n for n in workflow.execution_order if n in branch_nodes]
            await job._execute_branch_for_item("split", order,
                {"symbol": "OFFLINE", "exchange": "TEST"}, 0, 1)
        else:
            await job._handle_realtime_update(WorkflowEvent("market_data", "start", data={},
                trigger_nodes=["gate", "independent"]))
        return executor.visited, context.get_all_outputs("gate")
    finally:
        context.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["main", "split", "realtime"])
@pytest.mark.parametrize("kind", ["disabled_schedule", "timed_out_hours"])
async def test_refused_trigger_blocks_body_and_join_but_not_independent_branch(tmp_path, monkeypatch, path, kind):
    monkeypatch.setattr(TradingHoursFilterNode, "_is_trading_hours", lambda *a, **k: False)
    gate = ({"id": "gate", "type": "ScheduleNode", "cron": "* * * * *", "enabled": False}
        if kind == "disabled_schedule" else
        {"id": "gate", "type": "TradingHoursFilterNode", "max_wait_hours": 0.0})
    visited, output = await traverse(tmp_path, gate, path)
    assert "gate" in visited and "independent" in visited
    assert not {"body", "join"} & set(visited)
    assert output["trigger" if kind == "disabled_schedule" else "passed"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["main", "split", "realtime"])
@pytest.mark.parametrize("inside", [False, True])
async def test_explicit_blocked_branch_and_passed_default_remain_exclusive(tmp_path, monkeypatch, path, inside):
    monkeypatch.setattr(TradingHoursFilterNode, "_is_trading_hours", lambda *a, **k: inside)
    visited, output = await traverse(tmp_path,
        {"id": "gate", "type": "TradingHoursFilterNode", "max_wait_hours": 0.0}, path, branch=True)
    assert ("body" in visited) is inside
    assert ("blocked" in visited) is not inside
    assert output["passed"] is inside and output["blocked"] is not inside


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["main", "split", "realtime"])
@pytest.mark.parametrize("inside", [False, True])
async def test_selected_alternative_keeps_merged_descendant_eligible(tmp_path, monkeypatch, path, inside):
    monkeypatch.setattr(TradingHoursFilterNode, "_is_trading_hours", lambda *a, **k: inside)
    visited, output = await traverse(tmp_path,
        {"id": "gate", "type": "TradingHoursFilterNode", "max_wait_hours": 0.0},
        path, branch=True, merge=True)
    assert "join" in visited and "independent" in visited
    assert visited.index("join") > visited.index("body" if inside else "blocked")
    assert ("body" in visited) is inside
    assert ("blocked" in visited) is not inside
