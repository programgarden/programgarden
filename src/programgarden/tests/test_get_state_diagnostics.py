"""
get_state() diagnostic payload regression guards (Bug 1/2/3 fix).

Verifies the WorkflowJob.get_state() contract introduced in v1.21.5:
- nodes_state[*].state reflects the actual NodeState (no more "completed" hardcoding)
- nodes_state contains every workflow node, defaulting to "pending"
- nodes_state[failed_id] surfaces "error" + "duration_ms" + correct state
- stats["last_error"] / stats["last_error_detail"] populated on failure
- errors[] structured field with (node_id, error) dedup and timestamp sort
- IfNode inactive branch produces NodeState.SKIPPED (semantic fix D-8)

The controlled nodes are CodeNodes (the generic custom-code node). To
exercise the WorkflowJob.status="failed" path we patch
CodeNodeExecutor.execute to raise for one node.
"""

import asyncio
from typing import Any, Dict
from unittest.mock import patch

import pytest

from programgarden.executor import CodeNodeExecutor, WorkflowExecutor


# ============================================================
# Fixtures — CodeNodes for controlled success / failure
# ============================================================


# Emits {'value': params['payload']} on the declared 'value' port.
_OK_CODE = (
    "async def execute(data, params, context):\n"
    "    return {'value': params.get('payload', 42)}"
)


def _ok(node_id: str, payload: int = 42) -> Dict[str, Any]:
    """A CodeNode that returns {'value': payload} on its 'value' output port."""
    return {
        "id": node_id,
        "type": "CodeNode",
        "params": {"payload": payload},
        "outputs": [{"name": "value", "type": "number"}],
        "code": _OK_CODE,
    }


@pytest.fixture
def executor():
    return WorkflowExecutor()


async def _run(executor: WorkflowExecutor, workflow: Dict[str, Any], timeout: float = 30.0):
    job = await executor.execute(workflow)
    try:
        await asyncio.wait_for(job._task, timeout=timeout)
    except asyncio.TimeoutError:
        await job.stop()
    return job


# ============================================================
# T-1: Normal workflow — clean diagnostic payload
# ============================================================


@pytest.mark.asyncio
async def test_normal_workflow_no_errors(executor):
    """Successful workflow yields errors=[], last_error=None, all completed."""
    workflow = {
        "id": "wf-ok",
        "name": "Normal",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _ok("ok", 7),
        ],
        "edges": [{"from": "start", "to": "ok"}],
    }
    job = await _run(executor, workflow)
    state = job.get_state()

    assert state["status"] == "completed"
    assert state["errors"] == []
    assert state["stats"]["last_error"] is None
    assert state["stats"]["last_error_detail"] is None

    # nodes contains every workflow node
    assert set(state["nodes"].keys()) == {"start", "ok"}
    for node_id, entry in state["nodes"].items():
        assert entry["state"] == "completed", f"{node_id} state {entry['state']!r}"
        assert "error" not in entry
        assert "node_type" in entry


# ============================================================
# T-2: Failing node — full diagnostic surface
# ============================================================


async def _run_with_failing_executor(
    executor: WorkflowExecutor,
    workflow: Dict[str, Any],
    *,
    fail_node_id: str,
    fail_message: str,
    timeout: float = 30.0,
):
    """Run workflow while forcing CodeNodeExecutor.execute to raise for one node."""
    real_execute = CodeNodeExecutor.execute

    async def fake_execute(self, node_id, node_type, config, context, **kwargs):
        if node_id == fail_node_id:
            raise RuntimeError(fail_message)
        return await real_execute(self, node_id, node_type, config, context, **kwargs)

    with patch.object(CodeNodeExecutor, "execute", new=fake_execute):
        job = await executor.execute(workflow)
        try:
            await asyncio.wait_for(job._task, timeout=timeout)
        except asyncio.TimeoutError:
            await job.stop()
        return job


@pytest.mark.asyncio
async def test_failing_node_surfaces_error(executor):
    """Failing node populates state/error/last_error/errors[0]."""
    workflow = {
        "id": "wf-fail",
        "name": "Failing",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _ok("boom"),
        ],
        "edges": [{"from": "start", "to": "boom"}],
    }
    job = await _run_with_failing_executor(
        executor, workflow, fail_node_id="boom", fail_message="kaboom-msg"
    )
    state = job.get_state()

    # Job-level
    assert state["status"] == "failed"

    # nodes_state — failed node has state + error + duration_ms
    boom = state["nodes"]["boom"]
    assert boom["state"] == "failed", (
        f"Bug 1 regression: failed node state should be 'failed', got {boom['state']!r}"
    )
    assert "error" in boom
    assert "kaboom-msg" in boom["error"]
    assert boom.get("duration_ms") is not None and boom["duration_ms"] >= 0

    # stats — last_error / last_error_detail
    last = state["stats"]["last_error"]
    assert last is not None, "Bug 2 regression: last_error must be set on node failure"
    assert last.startswith("boom: "), f"unexpected last_error format: {last!r}"
    detail = state["stats"]["last_error_detail"]
    assert detail is not None
    assert detail["node_id"] == "boom"
    assert detail["node_type"] == "CodeNode"
    assert "kaboom-msg" in detail["error"]
    assert detail["timestamp"] is not None

    # errors[] — at least one entry referencing the failed node
    assert state["errors"], "Bug 3 regression: errors[] must surface failures"
    failure_entries = [e for e in state["errors"] if e.get("node_id") == "boom"]
    assert failure_entries, f"no error entry for 'boom' in {state['errors']}"
    e0 = failure_entries[0]
    assert e0["node_type"] == "CodeNode"
    assert "kaboom-msg" in e0["error"]
    assert e0["level"] == "error"


# ============================================================
# T-3: Unexecuted nodes default to "pending" (D-3)
# ============================================================


@pytest.mark.asyncio
async def test_unexecuted_nodes_pending(executor):
    """When a node fails early, downstream unexecuted nodes appear as 'pending'."""
    workflow = {
        "id": "wf-partial",
        "name": "PartialFail",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _ok("boom"),
            _ok("downstream"),
        ],
        "edges": [
            {"from": "start", "to": "boom"},
            {"from": "boom", "to": "downstream"},
        ],
    }
    job = await _run_with_failing_executor(
        executor, workflow, fail_node_id="boom", fail_message="early-failure"
    )
    state = job.get_state()

    assert state["status"] == "failed"
    assert "downstream" in state["nodes"]
    downstream_state = state["nodes"]["downstream"]["state"]
    assert downstream_state == "pending", (
        f"unexecuted downstream node should be 'pending', got {downstream_state!r}"
    )


# ============================================================
# T-4: IfNode inactive branch is SKIPPED (D-8)
# ============================================================


@pytest.mark.asyncio
async def test_if_node_inactive_branch_skipped(executor):
    """IfNode false branch yields NodeState.SKIPPED (was COMPLETED before D-8)."""
    workflow = {
        "id": "wf-if",
        "name": "IfBranch",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "if1", "type": "IfNode", "left": 1, "operator": "==", "right": 1},
            _ok("true_node", 1),
            _ok("false_node", 2),
        ],
        "edges": [
            {"from": "start", "to": "if1"},
            {"from": "if1", "to": "true_node", "from_port": "true"},
            {"from": "if1", "to": "false_node", "from_port": "false"},
        ],
    }
    job = await _run(executor, workflow)
    state = job.get_state()

    assert state["status"] == "completed"
    assert state["nodes"]["true_node"]["state"] == "completed"
    assert state["nodes"]["false_node"]["state"] == "skipped", (
        "D-8 regression: IfNode inactive branch must report 'skipped'"
    )


# ============================================================
# T-5: errors[] is sorted by timestamp ascending (D-5)
# ============================================================


@pytest.mark.asyncio
async def test_errors_sorted_by_timestamp(executor):
    """errors[0] is the earliest failure."""
    workflow = {
        "id": "wf-sorted",
        "name": "TimestampSort",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _ok("boom"),
        ],
        "edges": [{"from": "start", "to": "boom"}],
    }
    job = await _run_with_failing_executor(
        executor, workflow, fail_node_id="boom", fail_message="first-error"
    )
    state = job.get_state()

    timestamps = [e.get("timestamp") for e in state["errors"] if e.get("timestamp")]
    assert timestamps == sorted(timestamps), (
        f"D-5 regression: errors[] must be timestamp-asc; got {timestamps}"
    )


# ============================================================
# T-6: errors[] dedup on (node_id, message) (D-6)
# ============================================================


@pytest.mark.asyncio
async def test_errors_dedup(executor):
    """Same (node_id, message) appears at most once even if cache + log overlap."""
    workflow = {
        "id": "wf-dedup",
        "name": "DedupTest",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _ok("boom"),
        ],
        "edges": [{"from": "start", "to": "boom"}],
    }
    job = await _run_with_failing_executor(
        executor, workflow, fail_node_id="boom", fail_message="single-failure"
    )
    state = job.get_state()

    boom_entries = [
        e for e in state["errors"]
        if e.get("node_id") == "boom" and "single-failure" in (e.get("error") or "")
    ]
    assert len(boom_entries) == 1, (
        f"D-6 regression: dedup failed — {len(boom_entries)} entries for "
        f"('boom', 'single-failure'): {boom_entries}"
    )


# ============================================================
# T-7: stats schema — keys always present (D-7)
# ============================================================


@pytest.mark.asyncio
async def test_stats_schema_always_present(executor):
    """stats always exposes last_error / last_error_detail keys (None when no failure)."""
    workflow = {
        "id": "wf-schema",
        "name": "Schema",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _ok("ok"),
        ],
        "edges": [{"from": "start", "to": "ok"}],
    }
    job = await _run(executor, workflow)
    state = job.get_state()

    stats = state["stats"]
    assert "last_error" in stats
    assert "last_error_detail" in stats
    assert "errors_count" in stats
    assert "errors" in state, "errors[] key must always be present even when empty"


# ============================================================
# T-8: backward-compat — existing get_state() callers still work
# ============================================================


@pytest.mark.asyncio
async def test_existing_caller_compat(executor):
    """test_examples_validation.py:154 access patterns still work."""
    workflow = {
        "id": "wf-compat",
        "name": "Compat",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _ok("ok"),
        ],
        "edges": [{"from": "start", "to": "ok"}],
    }
    job = await _run(executor, workflow)
    state = job.get_state()

    # mirrors test_examples_validation.py:154-176 access pattern
    status = state.get("status")
    errors_count = state.get("stats", {}).get("errors_count", 0)
    logs = state.get("logs", [])
    assert status == "completed"
    assert errors_count == 0
    assert isinstance(logs, list)


# ============================================================
# T-9: nodes_state contains every workflow node (D-3)
# ============================================================


@pytest.mark.asyncio
async def test_nodes_state_covers_every_node(executor):
    """nodes_state.keys() == workflow.nodes.keys() — no missing entries."""
    workflow = {
        "id": "wf-cover",
        "name": "Coverage",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _ok("n1", 1),
            _ok("n2", 2),
            _ok("n3", 3),
        ],
        "edges": [
            {"from": "start", "to": "n1"},
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3"},
        ],
    }
    job = await _run(executor, workflow)
    state = job.get_state()

    expected = {n["id"] for n in workflow["nodes"]}
    assert set(state["nodes"].keys()) == expected
