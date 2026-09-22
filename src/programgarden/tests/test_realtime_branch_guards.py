"""Recurring events must honor the same branch guards as initial traversal."""
import asyncio
from unittest.mock import patch

import pytest

from programgarden import WorkflowExecutor
from programgarden.context import WorkflowEvent
from programgarden.executor import GenericNodeExecutor
from tests.test_split_if_guards import workflow as split_workflow


async def rerun(graph, targets):
    effects = []
    async def intercepted(self, node_id, node_type, config, context, **kwargs):
        effects.append(node_id)
        return {"response": {"node": node_id}}
    with patch.object(GenericNodeExecutor, "execute", intercepted):
        job = await WorkflowExecutor().execute(graph)
        await asyncio.wait_for(job._task, 3)
        effects.clear()
        job.context.start()
        try:
            await job._handle_realtime_update(WorkflowEvent(
                "realtime_update", "start", trigger_nodes=targets))
        finally:
            job.context.stop()
    return effects, job


@pytest.mark.asyncio
@pytest.mark.parametrize("allowed", [False, True])
async def test_tick_uses_actual_if_result_before_side_effect(allowed):
    graph = {"id": "tick-if", "name": "Tick If", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "guard", "type": "IfNode", "left": allowed, "operator": "==", "right": True},
        {"id": "yes", "type": "HTTPRequestNode", "url": "https://fixture.invalid/yes"},
        {"id": "no", "type": "HTTPRequestNode", "url": "https://fixture.invalid/no"}],
        "edges": [{"from": "start", "to": "guard"},
                  {"from": "guard", "to": "yes", "from_port": "true"},
                  {"from": "guard", "to": "no", "from_port": "false"}]}
    effects, job = await rerun(graph, ["guard"])
    assert effects == (["yes"] if allowed else ["no"])
    assert "_if_branch" not in job.context.get_all_outputs("guard")


@pytest.mark.asyncio
@pytest.mark.parametrize("outer", [False, True])
async def test_tick_does_not_predrive_split_before_outer_guard(outer):
    graph = split_workflow([{"symbol": "A", "allowed": True}], outer=outer)
    effects, _ = await rerun(graph, ["outer"])
    assert effects == (["effect"] if outer else [])


@pytest.mark.asyncio
async def test_throttled_tick_keeps_independent_branch_runnable():
    graph = {"id": "tick-throttle", "name": "Tick throttle", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "gate", "type": "ThrottleNode", "pass_first": False, "interval_sec": 3600.0},
        {"id": "blocked", "type": "HTTPRequestNode", "url": "https://fixture.invalid/blocked"},
        {"id": "independent", "type": "HTTPRequestNode", "url": "https://fixture.invalid/independent"}],
        "edges": [{"from": "start", "to": "gate"}, {"from": "gate", "to": "blocked"},
                  {"from": "start", "to": "independent"}]}
    effects, _ = await rerun(graph, ["gate", "independent"])
    assert effects == ["independent"]


@pytest.mark.asyncio
async def test_later_tick_clears_outputs_from_previously_taken_branch():
    graph = {"id": "changing-guard", "name": "Changing guard", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "guard", "type": "IfNode", "left": "{{ nodes.source.response.allowed }}", "operator": "==", "right": True},
        {"id": "source", "type": "HTTPRequestNode", "url": "https://fixture.invalid/source"},
        {"id": "yes", "type": "HTTPRequestNode", "url": "https://fixture.invalid/yes"},
        {"id": "no", "type": "HTTPRequestNode", "url": "https://fixture.invalid/no"}],
        "edges": [{"from": "start", "to": "source"}, {"from": "source", "to": "guard"},
                  {"from": "guard", "to": "yes", "from_port": "true"},
                  {"from": "guard", "to": "no", "from_port": "false"}]}
    effects = []
    allowed = True
    async def intercepted(self, node_id, node_type, config, context, **kwargs):
        effects.append(node_id)
        return {"response": {"allowed": allowed}} if node_id == "source" else {"response": {"node": node_id}}
    with patch.object(GenericNodeExecutor, "execute", intercepted):
        job = await WorkflowExecutor().execute(graph)
        await asyncio.wait_for(job._task, 3)
        assert job.context.get_all_outputs("yes")
        allowed = False
        effects.clear()
        job.context.start()
        try:
            await job._handle_realtime_update(WorkflowEvent("realtime_update", "start", trigger_nodes=["source"]))
        finally:
            job.context.stop()
    assert effects == ["source", "no"]
    assert not job.context.get_all_outputs("yes")
    assert not job.context.get_all_outputs("_input_yes")
    assert job.context.get_all_outputs("no")["response"]["node"] == "no"


@pytest.mark.asyncio
async def test_failed_tick_cannot_reuse_previous_source_output_or_stop_independent_branch():
    graph = {"id": "failing-source", "name": "Failing source", "nodes": [
        {"id": "start", "type": "StartNode"},
        *[{"id": node, "type": "HTTPRequestNode", "url": f"https://fixture.invalid/{node}"}
          for node in ("source", "dependent", "independent")]],
        "edges": [{"from": "start", "to": "source"}, {"from": "source", "to": "dependent"},
                  {"from": "start", "to": "independent"}]}
    effects, fail = [], False
    async def intercepted(self, node_id, node_type, config, context, **kwargs):
        if fail and node_id == "source":
            raise RuntimeError("Recorded source timeout")
        effects.append(node_id)
        return {"response": {"node": node_id}}
    with patch.object(GenericNodeExecutor, "execute", intercepted):
        job = await WorkflowExecutor().execute(graph)
        await asyncio.wait_for(job._task, 3)
        fail = True
        effects.clear()
        job.context.start()
        try:
            await job._handle_realtime_update(WorkflowEvent("realtime_update", "start",
                trigger_nodes=["source", "independent"]))
        finally:
            job.context.stop()
    assert effects == ["independent"]
    assert not job.context.get_all_outputs("source")
    assert not job.context.get_all_outputs("dependent")
    assert not job.context.get_all_outputs("_input_dependent")
    assert job.get_state()["nodes"]["source"]["state"] == "failed"
