"""Node admission uses actual cumulative execution, not mocked PASS flags."""
from copy import deepcopy
import pytest
from programgarden.incremental_build import BuildGateError, BuildWorkspace
from programgarden.validation_replay import replay


def workspace():
    return BuildWorkspace("task", 1, {"id":"incremental","name":"Incremental","nodes":[],"edges":[]},
        [{"expected":{"sum":{"type":"object","required":["result"],
                               "properties":{"result":{"type":"number","const":3}}}}}])


@pytest.mark.parametrize("fixtures", [None, {}, "invalid", [None], [{}] * 17])
def test_invalid_fixture_replacement_is_atomic(fixtures):
    from dataclasses import asdict
    ws = workspace()
    before = asdict(ws)
    with pytest.raises(BuildGateError, match="bounded array"):
        ws.replace_fixtures(fixtures, expected_revision=ws.revision)
    assert asdict(ws) == before
    with pytest.raises(BuildGateError, match="bounded array"):
        BuildWorkspace("task", 1, {"nodes": [], "edges": []}, fixtures)


def test_identical_fixture_resume_preserves_revision_and_evidence():
    from dataclasses import asdict
    ws = workspace()
    before = asdict(ws)
    ws.replace_fixtures(deepcopy(ws.fixtures), expected_revision=ws.revision)
    assert asdict(ws) == before


def code(node_id, expression, data=None):
    return {"id":node_id,"type":"CodeNode","outputs":[{"name":"result","type":"number"}],
            "code":f"def execute(data, params, context):\n return {{'result': {expression}}}",
            **({"data":data} if data is not None else {})}


async def append(ws, node, source=None):
    ws.add_node(node, [] if source is None else [{"from":source,"to":node["id"]}],expected_revision=ws.revision)
    return await ws.run_pending(node["id"],expected_revision=ws.revision)


@pytest.mark.asyncio
async def test_each_addition_reexecutes_full_chain_before_next_dependency():
    ws=workspace()
    first=await append(ws,{"id":"start","type":"StartNode"})
    second=await append(ws,code("one","1"),"start")
    third=await append(ws,code("sum","data + 2","{{ nodes.one.result }}"),"one")
    for proof, expected in ((first,["start"]),(second,["start","one"]),(third,["start","one","sum"])):
        assert proof["passed"],proof["errors"]
        chain=[r for r in proof["runs"] if r["stage"]=="chain"]
        assert len(chain)==1 and chain[0]["executed"] == expected
        assert any(r["stage"]=="node" for r in proof["runs"])
    final=await ws.finalize(expected_revision=ws.revision)
    assert final["passed"] and ws.status=="READY" and not final["live_authorized"]
    assert final["runs"][0]["executed"]==["start","one","sum"]


@pytest.mark.asyncio
async def test_failed_node_blocks_next_dependency_and_repair_reopens_it():
    ws=workspace()
    await append(ws,{"id":"start","type":"StartNode"})
    bad=await append(ws,code("one","1 / 0"),"start")
    assert not bad["passed"] and ws.states["one"]=="FAILED"
    before=deepcopy(ws.graph)
    with pytest.raises(BuildGateError,match="Verify every upstream"):
        ws.add_node(code("sum","3"),[{"from":"one","to":"sum"}],expected_revision=ws.revision)
    assert ws.graph==before
    ws.repair_node(code("one","1"),expected_revision=ws.revision)
    assert (await ws.run_pending("one",expected_revision=ws.revision))["passed"]
    assert (await append(ws,code("sum","3"),"one"))["passed"]


@pytest.mark.asyncio
async def test_wrong_numeric_result_fails_before_a_dependent_node_can_be_added():
    ws = workspace()
    await append(ws, {"id": "start", "type": "StartNode"})
    bad = await append(ws, code("sum", "99"), "start")
    assert not bad["passed"]
    assert ws.states["sum"] == "FAILED"
    assert bad["errors"][0]["code"] == "REPLAY_CONTRACT_FAILED"
    with pytest.raises(BuildGateError, match="Verify every upstream"):
        ws.add_node(code("consumer", "data", "{{ nodes.sum.result }}"),
                    [{"from": "sum", "to": "consumer"}], expected_revision=ws.revision)
    ws.repair_node(code("sum", "3"), expected_revision=ws.revision)
    assert (await ws.run_pending("sum", expected_revision=ws.revision))["passed"]


@pytest.mark.asyncio
async def test_change_invalidates_descendants_and_old_pass_cannot_finalize():
    ws=workspace()
    await append(ws,{"id":"start","type":"StartNode"})
    await append(ws,code("one","1"),"start")
    await append(ws,code("sum","3"),"one")
    ws.repair_node(code("one","2"),expected_revision=ws.revision)
    assert ws.states["sum"]=="STALE" and "sum" not in ws.evidence
    with pytest.raises(BuildGateError):
        await ws.finalize(expected_revision=ws.revision)


@pytest.mark.asyncio
async def test_restore_from_serialized_workspace_reuses_identity_not_a_new_plan():
    from dataclasses import asdict
    import json
    ws=workspace()
    await append(ws,{"id":"start","type":"StartNode"})
    restored=BuildWorkspace(**json.loads(json.dumps(asdict(ws))))
    assert restored.task_id==ws.task_id and restored.states=={"start":"VERIFIED"}
    assert (await append(restored,code("one","1"),"start"))["passed"]


@pytest.mark.asyncio
async def test_concurrent_edit_rejects_old_validation_result(monkeypatch):
    import programgarden.incremental_build as module
    ws=workspace()
    ws.add_node({"id":"start","type":"StartNode"},[],expected_revision=0)
    changed=False
    async def racing(*args,**kwargs):
        nonlocal changed
        result=await replay(*args,**kwargs)
        if not changed:
            changed=True
            ws.repair_node({"id":"start","type":"StartNode","description":"changed"},expected_revision=ws.revision)
        return result
    monkeypatch.setattr(module,"replay",racing)
    with pytest.raises(BuildGateError,match="changed while"):
        await ws.run_pending("start",expected_revision=1)
    assert ws.states["start"]=="BUILT" and "start" not in ws.evidence


@pytest.mark.asyncio
async def test_final_requires_expected_outputs_not_only_no_exception():
    ws=workspace();ws.fixtures=[{}]
    await append(ws,{"id":"start","type":"StartNode"})
    result=await ws.finalize(expected_revision=ws.revision)
    assert not result["passed"] and ws.status=="FAILED"
    assert result["runs"][0]["scenario_errors"][0]["code"]=="REPLAY_EXPECTATIONS_REQUIRED"


@pytest.mark.asyncio
async def test_unexercised_branch_never_becomes_verified():
    ws=workspace()
    await append(ws,{"id":"start","type":"StartNode"})
    await append(ws,{"id":"gate","type":"IfNode","left":0,"right":1,"operator":">"},"start")
    ws.add_node(code("sum","3"),[{"from":"gate","from_port":"true","to":"sum"}],expected_revision=ws.revision)
    result=await ws.run_pending("sum",expected_revision=ws.revision)
    assert not result["passed"] and ws.states["sum"]=="FAILED"
    assert result["errors"][0]["code"]=="BUILD_BRANCH_UNCOVERED"


@pytest.mark.asyncio
async def test_independent_branches_must_all_verify_before_join():
    ws=workspace()
    await append(ws,{"id":"start","type":"StartNode"})
    await append(ws,code("a","1"),"start")
    failed=await append(ws,code("b","1 / 0"),"start")
    assert not failed["passed"]
    edges=[{"from":"a","to":"sum"},{"from":"b","to":"sum"}]
    with pytest.raises(BuildGateError):
        ws.add_node(code("sum","3"),edges,expected_revision=ws.revision)
    ws.repair_node(code("b","2"),expected_revision=ws.revision)
    assert (await ws.run_pending("b",expected_revision=ws.revision))["passed"]
    ws.add_node(code("sum","data","{{ nodes.a.result + nodes.b.result }}"),edges,expected_revision=ws.revision)
    proof=await ws.run_pending("sum",expected_revision=ws.revision)
    assert proof["passed"] and proof["runs"][-1]["outputs"]["sum"]["result"]==3


@pytest.mark.asyncio
async def test_expression_dependency_cannot_bypass_edges_or_failed_parent():
    ws=workspace()
    await append(ws,{"id":"start","type":"StartNode"})
    await append(ws,code("bad","1 / 0"),"start")
    with pytest.raises(BuildGateError,match="referenced node"):
        ws.add_node(code("sum","data","{{ nodes.bad.result }}"),[{"from":"start","to":"sum"}],expected_revision=ws.revision)
    await append(ws,code("good","1"),"start")
    with pytest.raises(BuildGateError,match="upstream path"):
        ws.add_node(code("sum","data","{{ nodes.good.result }}"),[{"from":"start","to":"sum"}],expected_revision=ws.revision)


@pytest.mark.asyncio
async def test_edge_repair_and_plan_revision_invalidate_existing_evidence():
    ws=workspace()
    await append(ws,{"id":"start","type":"StartNode"})
    await append(ws,code("one","1"),"start")
    await append(ws,code("sum","3"),"one")
    ws.replace_incoming_edges("one",[{"from":"start","to":"one","from_port":"trigger"}],expected_revision=ws.revision)
    assert ws.states=={"start":"VERIFIED","one":"STALE","sum":"STALE"}
    with pytest.raises(BuildGateError):
        ws.replace_incoming_edges("start",[{"from":"sum","to":"start"}],expected_revision=ws.revision)
    ws.replan(2,expected_revision=ws.revision)
    assert all(s=="STALE" for s in ws.states.values()) and not ws.evidence


@pytest.mark.asyncio
async def test_cancellation_keeps_node_unverified(monkeypatch):
    import asyncio
    import programgarden.incremental_build as module
    ws=workspace();ws.add_node({"id":"start","type":"StartNode"},[],expected_revision=0)
    async def cancelled(*args,**kwargs): raise asyncio.CancelledError()
    monkeypatch.setattr(module,"replay",cancelled)
    with pytest.raises(asyncio.CancelledError): await ws.run_pending("start",expected_revision=ws.revision)
    assert ws.states["start"]=="BLOCKED" and not ws.evidence


def test_computation_dependency_change_invalidates_verification(monkeypatch):
    import programgarden.incremental_build as module
    ws=workspace()
    version=module.importlib.metadata.version
    monkeypatch.setattr(module.importlib.metadata,"version",lambda name:"changed-version" if name=="numpy" else version(name))
    with pytest.raises(BuildGateError,match="engine or contract changed"):
        ws.add_node({"id":"start","type":"StartNode"},[],expected_revision=0)
    assert ws.status=="STALE" and not ws.states


def test_shared_plugin_edit_without_version_bump_changes_runtime_hash(monkeypatch,tmp_path):
    from types import SimpleNamespace
    import programgarden.incremental_build as module
    find_spec=module.importlib.util.find_spec
    (tmp_path/"__init__.py").write_text("")
    plugin=tmp_path/"strategy.py"
    plugin.write_text("THRESHOLD = 30\n")
    monkeypatch.setattr(module.importlib.util,"find_spec",lambda name:
        SimpleNamespace(origin=str(tmp_path/"__init__.py")) if name=="programgarden_community" else find_spec(name))
    before=module.runtime_identity()
    plugin.write_text("THRESHOLD = 25\n")
    assert module.runtime_identity()!=before


@pytest.mark.asyncio
async def test_remove_rechecks_roots_and_cannot_reset_attempts_or_final_expectations():
    ws = workspace()
    await append(ws, {"id": "start", "type": "StartNode"})
    await append(ws, code("sum", "3"), "start")
    assert (await ws.finalize(expected_revision=ws.revision))["passed"]
    attempts = dict(ws.attempts)
    ws.remove_node("sum", expected_revision=ws.revision)
    assert ws.graph["edges"] == [] and ws.states == {"start": "STALE"}
    assert not ws.evidence and ws.attempts == attempts
    with pytest.raises(BuildGateError, match="Every required node"):
        await ws.finalize(expected_revision=ws.revision)
    assert (await ws.run_pending("start", expected_revision=ws.revision))["passed"]
    assert not (await ws.finalize(expected_revision=ws.revision))["passed"]
    assert (await append(ws, code("sum", "3"), "start"))["passed"]
    assert ws.attempts["sum"] == attempts["sum"] + 1


@pytest.mark.asyncio
async def test_header_edit_invalidates_verified_nodes_and_identical_retry_preserves_state():
    from dataclasses import asdict
    ws = workspace()
    await append(ws, {"id": "start", "type": "StartNode"})
    before = asdict(ws)
    ws.update_header({"name": ws.graph["name"]}, expected_revision=ws.revision)
    assert asdict(ws) == before
    ws.update_header({"inputs": {"quantity": {"type": "number", "default": 2}}}, expected_revision=ws.revision)
    assert ws.states == {"start": "STALE"} and not ws.evidence
    assert ws.attempts == before["attempts"]
    with pytest.raises(BuildGateError, match="Every required node"):
        await ws.finalize(expected_revision=ws.revision)


@pytest.mark.parametrize("change", [{"id": "replace"}, {"nodes": []}, {"credentials": []},
    {"states": {"start": "VERIFIED"}}, {"resource_limits": {"cpu_cores": "invalid"}},
    {"inputs": {"quantity": {"type": "imaginary"}}}, {"name": 7}, {"tags": [float("nan")]}])
def test_invalid_header_edit_is_atomic(change):
    from dataclasses import asdict
    ws = workspace()
    before = asdict(ws)
    with pytest.raises(BuildGateError):
        ws.update_header(change, expected_revision=ws.revision)
    assert asdict(ws) == before


@pytest.mark.asyncio
async def test_successful_edits_and_finalizations_do_not_exhaust_failed_repair_limit():
    ws = workspace()
    await append(ws, {"id": "start", "type": "StartNode"})
    await append(ws, code("sum", "3"), "start")
    for i in range(8):
        ws.repair_node({**code("sum", "3"), "description": f"Revision {i}"}, expected_revision=ws.revision)
        assert (await ws.run_pending("sum", expected_revision=ws.revision))["passed"]
        assert (await ws.finalize(expected_revision=ws.revision))["passed"]
    assert ws.attempts["sum"] == 9 and ws.attempts["$final"] == 8
    assert ws.failure_streaks["sum"] == ws.failure_streaks["$final"] == 0


@pytest.mark.asyncio
async def test_failed_repairs_remain_bounded_after_edit_remove_and_readd():
    ws = workspace()
    await append(ws, {"id": "start", "type": "StartNode"})
    ws.add_node(code("sum", "99"), [{"from": "start", "to": "sum"}], expected_revision=ws.revision)
    for i in range(6):
        if i:
            ws.repair_node({**code("sum", "99"), "description": str(i)}, expected_revision=ws.revision)
        assert not (await ws.run_pending("sum", expected_revision=ws.revision))["passed"]
    ws.remove_node("sum", expected_revision=ws.revision)
    assert (await ws.run_pending("start", expected_revision=ws.revision))["passed"]
    ws.add_node(code("sum", "3"), [{"from": "start", "to": "sum"}], expected_revision=ws.revision)
    with pytest.raises(BuildGateError, match="Consecutive failures"):
        await ws.run_pending("sum", expected_revision=ws.revision)
    assert ws.attempts["sum"] == ws.failure_streaks["sum"] == 6


@pytest.mark.asyncio
async def test_total_validation_budget_still_bounds_repeated_success():
    ws = workspace()
    ws.add_node({"id": "start", "type": "StartNode"}, [], expected_revision=0)
    ws.attempts["other"] = 384
    with pytest.raises(BuildGateError, match="total validation budget"):
        await ws.run_pending("start", expected_revision=ws.revision)
    assert ws.attempts == {"other": 384}
