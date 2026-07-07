"""CodeNode runtime tests: execution contract, subprocess isolation,
credential isolation, resolver static validation, and the opt-out gate.

Execution always happens in a spawned subprocess (Layer 4). These tests drive
the real worker pool — no mocking of the isolation boundary.
"""
import asyncio

import pytest

from programgarden import NodeRunner, WorkflowExecutor
from programgarden.executor import CodeNodeExecutor, CodeNodeError


# ── helpers ────────────────────────────────────────────────────────────────

async def _run_code(**config):
    runner = NodeRunner()
    return await runner.run("CodeNode", **config)


async def _run_workflow(wf, context_params=None):
    exe = WorkflowExecutor()
    job = await exe.execute(wf, context_params={**(context_params or {}), "dry_run": True, "max_cycles": 1})
    task = getattr(job, "_task", None)
    if task is not None:
        try:
            await asyncio.wait_for(task, timeout=30)
        except asyncio.CancelledError:
            pass
    return job


# ── execution contract ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_async_execute_maps_declared_ports():
    out = await _run_code(
        code="async def execute(data, params, context):\n    return {'a': data[0], 'b': sum(data)}",
        outputs=[{"name": "a", "type": "number"}, {"name": "b", "type": "number"}],
        data=[3, 4, 5],
    )
    assert out == {"a": 3, "b": 12}


@pytest.mark.asyncio
async def test_sync_execute_accepted():
    out = await _run_code(
        code="def execute(data, params, context):\n    return {'n': len(data)}",
        outputs=[{"name": "n", "type": "number"}],
        data=[1, 2, 3, 4],
    )
    assert out == {"n": 4}


@pytest.mark.asyncio
async def test_no_declared_outputs_uses_result_port():
    out = await _run_code(
        code="async def execute(data, params, context):\n    return {'x': 1, 'y': 2}",
        data=None,
    )
    assert out == {"result": {"x": 1, "y": 2}}


@pytest.mark.asyncio
async def test_non_dict_return_maps_to_first_declared_port():
    out = await _run_code(
        code="async def execute(data, params, context):\n    return 42",
        outputs=[{"name": "answer", "type": "number"}],
        data=None,
    )
    assert out == {"answer": 42}


@pytest.mark.asyncio
async def test_missing_declared_port_becomes_none():
    out = await _run_code(
        code="async def execute(data, params, context):\n    return {'a': 1}",
        outputs=[{"name": "a", "type": "number"}, {"name": "b", "type": "number"}],
        data=None,
    )
    assert out == {"a": 1, "b": None}


@pytest.mark.asyncio
async def test_params_passed_through():
    out = await _run_code(
        code="async def execute(data, params, context):\n    return {'p': params.get('period')}",
        outputs=[{"name": "p", "type": "number"}],
        params={"period": 14},
    )
    assert out == {"p": 14}


@pytest.mark.asyncio
async def test_context_helper_namespaces():
    out = await _run_code(
        code="async def execute(data, params, context):\n    return {'pct': context.finance.pct_change(100, 110), 'mean': context.stats.mean([2, 4, 6])}",
        outputs=[{"name": "pct", "type": "number"}, {"name": "mean", "type": "number"}],
    )
    assert out["pct"] == pytest.approx(10.0)
    assert out["mean"] == pytest.approx(4.0)


# ── subprocess isolation / error handling ──────────────────────────────────

@pytest.mark.asyncio
async def test_runtime_exception_is_structured():
    with pytest.raises(CodeNodeError) as ei:
        await _run_code(code="async def execute(data, params, context):\n    return 1 / 0", data=None)
    assert ei.value.error_code.value == "CODE_NODE_EXEC_ERROR"
    assert ei.value.details.get("traceback")


@pytest.mark.asyncio
async def test_non_json_serializable_return_is_structured():
    with pytest.raises(CodeNodeError) as ei:
        await _run_code(code="async def execute(data, params, context):\n    return {'s': {1, 2, 3}}", data=None)
    assert ei.value.error_code.value == "CODE_NODE_EXEC_ERROR"


@pytest.mark.asyncio
async def test_infinite_loop_times_out(monkeypatch):
    # Drive the worker pool directly with a short timeout to keep the test fast.
    from programgarden.code_worker import run_code_node_sandboxed
    env = await asyncio.to_thread(
        run_code_node_sandboxed,
        code="async def execute(data, params, context):\n    while True:\n        pass",
        node_id="loop",
        data=None,
        params={},
        ctx_snapshot={},
        timeout=3,
    )
    assert env["ok"] is False and env["error_code"] == "CODE_NODE_EXEC_ERROR"
    assert "timed out" in env["message"].lower()


# ── credential isolation (the core security property) ──────────────────────

@pytest.mark.asyncio
async def test_context_has_no_credential_accessors():
    # The sandboxed context must not expose credential access — the code path
    # simply does not exist (hasattr is False), and there are no keys anyway.
    # (Underscore names like _secrets can't even be *written* in CodeNode code —
    # the screener rejects underscore string literals — so we probe only the
    # public accessor names here; the underscore path is covered by the screen.)
    out = await _run_code(
        code=(
            "async def execute(data, params, context):\n"
            "    found = []\n"
            "    for name in ('get_credential', 'get_workflow_credential', 'broker', 'executor'):\n"
            "        if hasattr(context, name):\n"
            "            found.append(name)\n"
            "    return {'exposed': found}"
        ),
        outputs=[{"name": "exposed", "type": "array"}],
    )
    assert out == {"exposed": []}


@pytest.mark.asyncio
async def test_underscore_credential_probe_is_screened_out():
    # Even *attempting* to reference a private/credential attr by string is
    # blocked at the screen — a defense-in-depth reinforcement of the scrub.
    from programgarden.executor import CodeNodeError
    with pytest.raises(CodeNodeError) as ei:
        await _run_code(
            code="async def execute(data, params, context):\n    return {'x': hasattr(context, '_secrets')}",
            outputs=[{"name": "x", "type": "boolean"}],
        )
    assert ei.value.error_code.value == "CODE_NODE_FORBIDDEN"


def test_ctx_snapshot_excludes_secrets():
    # Build a snapshot from a context carrying secrets and assert none leak.
    class _FakeCtx:
        job_id = "j1"
        is_dry_run = False
        _iteration_index = 0
        _iteration_total = 0
        _secrets = {"credential_id": {"appkey": "SECRET_KEY", "appsecret": "SECRET_VAL"}}
        _workflow_credentials = [{"credential_id": "c", "data": [{"key": "appkey", "value": "SECRET_KEY"}]}]
        risk_tracker = None

    snap = CodeNodeExecutor._build_ctx_snapshot(_FakeCtx())
    flat = repr(snap)
    assert "SECRET_KEY" not in flat and "SECRET_VAL" not in flat
    assert "appsecret" not in flat
    assert set(snap.keys()) <= {"job_id", "dry_run", "iteration_index", "iteration_total", "risk"}


# ── opt-out gate ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_disabled_gate_blocks_execution():
    runner = NodeRunner(allow_code_node=False)
    with pytest.raises(CodeNodeError) as ei:
        await runner.run("CodeNode", code="async def execute(d,p,c):\n    return {'x': 1}")
    assert ei.value.error_code.value == "CODE_NODE_DISABLED"


# ── resolver static validation ──────────────────────────────────────────────

def _wf_with_code(node, extra_nodes=None, extra_edges=None):
    nodes = [{"id": "start", "type": "StartNode"}, node]
    edges = [{"from": "start", "to": node["id"]}]
    if extra_nodes:
        nodes.extend(extra_nodes)
    if extra_edges:
        edges.extend(extra_edges)
    return {"id": "wf", "name": "wf", "nodes": nodes, "edges": edges, "credentials": []}


def _codes(result):
    return {e.code for e in result.errors}


def test_validate_syntax_error():
    wf = _wf_with_code({"id": "c", "type": "CodeNode", "code": "async def execute(d, p, c)\n    return 1"})
    r = WorkflowExecutor().validate(wf)
    assert "CODE_NODE_SYNTAX_ERROR" in _codes(r)


def test_validate_forbidden_import():
    wf = _wf_with_code({"id": "c", "type": "CodeNode", "code": "import os\nasync def execute(d, p, c):\n    return 1"})
    r = WorkflowExecutor().validate(wf)
    assert "CODE_NODE_FORBIDDEN" in _codes(r)


def test_validate_no_execute():
    wf = _wf_with_code({"id": "c", "type": "CodeNode", "code": "async def run(d, p, c):\n    return 1"})
    r = WorkflowExecutor().validate(wf)
    assert "CODE_NODE_NO_EXECUTE" in _codes(r)


def test_validate_credential_id_forbidden():
    wf = _wf_with_code({"id": "c", "type": "CodeNode", "credential_id": "x",
                        "code": "async def execute(d, p, c):\n    return 1"})
    wf["credentials"] = [{"credential_id": "x", "type": "broker_ls_overseas_stock", "data": []}]
    r = WorkflowExecutor().validate(wf)
    assert "CODE_NODE_FORBIDDEN" in _codes(r)


def test_validate_credential_like_binding_seal():
    wf = _wf_with_code(
        {"id": "c", "type": "CodeNode", "code": "async def execute(d, p, c):\n    return {}",
         "params": {"k": "{{ nodes.up.appsecret }}"}},
        extra_nodes=[{"id": "up", "type": "FieldMappingNode", "data": "{{ nodes.start.trigger }}"}],
        extra_edges=[{"from": "start", "to": "up"}, {"from": "up", "to": "c"}],
    )
    r = WorkflowExecutor().validate(wf)
    assert "CODE_NODE_FORBIDDEN" in _codes(r)


def test_validate_per_instance_output_port_typo():
    # {{ nodes.c.signl }} — typo of a declared port 'signal' must be caught.
    wf = _wf_with_code(
        {"id": "c", "type": "CodeNode",
         "outputs": [{"name": "signal", "type": "string"}],
         "code": "async def execute(d, p, c):\n    return {'signal': 'buy'}"},
        extra_nodes=[{"id": "disp", "type": "TableDisplayNode", "data": "{{ nodes.c.signl }}"}],
        extra_edges=[{"from": "c", "to": "disp"}],
    )
    r = WorkflowExecutor().validate(wf)
    assert "INVALID_EXPRESSION_REF" in _codes(r)


def test_validate_per_instance_output_port_valid():
    wf = _wf_with_code(
        {"id": "c", "type": "CodeNode",
         "outputs": [{"name": "signal", "type": "string"}],
         "code": "async def execute(d, p, c):\n    return {'signal': 'buy'}"},
        extra_nodes=[{"id": "disp", "type": "TableDisplayNode", "data": "{{ nodes.c.signal }}"}],
        extra_edges=[{"from": "c", "to": "disp"}],
    )
    r = WorkflowExecutor().validate(wf)
    assert r.is_valid, [e.short() for e in r.errors]


# ── full workflow: auto-iterate batching (whole array in one call) ──────────

@pytest.mark.asyncio
async def test_whole_array_passed_in_one_call():
    wf = _wf_with_code(
        {"id": "c", "type": "CodeNode",
         "outputs": [{"name": "count", "type": "number"}, {"name": "syms", "type": "array"}],
         "data": "{{ nodes.wl.symbols }}",
         "code": ("async def execute(data, params, context):\n"
                  "    return {'count': len(data), 'syms': [r['symbol'] for r in data]}")},
        extra_nodes=[{"id": "wl", "type": "WatchlistNode",
                      "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"},
                                  {"symbol": "MSFT", "exchange": "NASDAQ"}]}],
        extra_edges=[{"from": "start", "to": "wl"}, {"from": "wl", "to": "c"}],
    )
    job = await _run_workflow(wf)
    out = job.context.get_all_outputs("c")
    assert out.get("count") == 2
    assert out.get("syms") == ["AAPL", "MSFT"]
