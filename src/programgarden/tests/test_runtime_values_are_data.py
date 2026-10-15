"""Runtime values are data, never expressions (2.6.6, F2).

Before 2.6.6 the job resolved ``{{ … }}`` bindings and the node executor then
evaluated the already-resolved config again. Any runtime text containing ``{{``
(LLM output, HTTP bodies, workflow inputs, credentials, broker strings) was
evaluated a second time in the workflow expression context — e.g. AI text
``{{ nodes.hidden.value }}`` became the secret.

Invariant tested here: an expression is evaluated only while its authored
template is still at its authored position, at most once per node execution;
every runtime value passes byte-identical.

The producer CodeNode builds the brace text at runtime (``"{" + "{ … }" + "}"``)
so the producer's own source contains no template.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest

from programgarden import WorkflowExecutor
from programgarden.context import ExecutionContext
from programgarden.executor import GenericNodeExecutor, evaluate_all_bindings
from programgarden import binding_provenance as bp

SECRET = "TOP-SECRET-VALUE"
TEXT_SECRET = "{{ nodes.hidden.value }}"
TEXT_MATH = "{{ 1 + 1 }}"
TEXT_WRAPPED = "prefix {{ x }} suffix"

# Producer CodeNode: returns the three runtime strings without authoring any template.
PRODUCER_CODE = (
    "async def execute(data, params, context):\n"
    "    o, c = '{' + '{', '}' + '}'\n"
    "    return {\n"
    "        'secretish': o + ' nodes.hidden.value ' + c,\n"
    "        'math': o + ' 1 + 1 ' + c,\n"
    "        'wrapped': 'prefix ' + o + ' x ' + c + ' suffix',\n"
    "        'rows': [{'symbol': 'AAPL', 'exchange': 'NASDAQ', 'note': o + ' nodes.hidden.value ' + c},\n"
    "                 {'symbol': 'MSFT', 'exchange': 'NASDAQ', 'note': 'plain'}],\n"
    "        'n': 7,\n"
    "    }\n"
)
PRODUCER_PORTS = [
    {"name": "secretish", "type": "string"},
    {"name": "math", "type": "string"},
    {"name": "wrapped", "type": "string"},
    {"name": "rows", "type": "array"},
    {"name": "n", "type": "number"},
]
SECRET_CODE = "async def execute(data, params, context):\n    return {'value': '" + SECRET + "'}"
ECHO_CODE = "async def execute(data, params, context):\n    return {'data': data, 'params': params}"


def _wf(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]], credentials=None) -> Dict[str, Any]:
    base_nodes = [
        {"id": "start", "type": "StartNode"},
        {"id": "hidden", "type": "CodeNode", "code": SECRET_CODE, "outputs": [{"name": "value", "type": "string"}]},
        {"id": "agent", "type": "CodeNode", "code": PRODUCER_CODE, "outputs": PRODUCER_PORTS},
    ]
    base_edges = [{"from": "start", "to": "hidden"}, {"from": "hidden", "to": "agent"}]
    return {
        "id": "wf-runtime-data", "name": "wf-runtime-data",
        "nodes": base_nodes + nodes, "edges": base_edges + edges,
        "credentials": credentials or [],
    }


async def _run(wf, context_params=None, dry_run=True, storage_dir=None):
    exe = WorkflowExecutor()
    params = {"max_cycles": 1, **(context_params or {})}
    if dry_run:
        params["dry_run"] = True
    job = await exe.execute(wf, context_params=params, storage_dir=str(storage_dir) if storage_dir else None)
    task = getattr(job, "_task", None)
    if task is not None:
        try:
            await asyncio.wait_for(task, timeout=60)
        except asyncio.CancelledError:
            pass
    return job


def _out(job, node_id, port):
    return job.context.get_output(node_id, port)


# ── (a) CodeNode data / params, (c) interpolation, (h) ordinary bindings ────────

@pytest.mark.asyncio
async def test_codenode_receives_runtime_text_byte_identical(tmp_path):
    wf = _wf(
        [{
            "id": "consumer", "type": "CodeNode", "code": ECHO_CODE,
            "outputs": [{"name": "data", "type": "object"}, {"name": "params", "type": "object"}],
            "data": "{{ nodes.agent.secretish }}",
            "params": {
                "math": "{{ nodes.agent.math }}",
                "wrapped": "{{ nodes.agent.wrapped }}",
                "interpolated": "Prefix {{ nodes.agent.secretish }}",
                "rows": "{{ nodes.agent.rows }}",
                # (h) ordinary single-pass and nested bindings keep resolving
                "n": "{{ nodes.agent.n }}",
                "sum": "{{ nodes.agent.n + 1 }}",
                "nested": {"list": ["{{ nodes.agent.n }}", {"deep": "{{ nodes.hidden.value }}"}]},
            },
        }],
        [{"from": "agent", "to": "consumer"}],
    )
    job = await _run(wf, storage_dir=tmp_path)
    data = _out(job, "consumer", "data")
    params = _out(job, "consumer", "params")
    assert data == TEXT_SECRET
    assert params["math"] == TEXT_MATH
    assert params["wrapped"] == TEXT_WRAPPED
    assert params["interpolated"] == "Prefix " + TEXT_SECRET
    assert params["rows"][0]["note"] == TEXT_SECRET
    assert params["n"] == 7
    assert params["sum"] == 8
    assert params["nested"] == {"list": [7, {"deep": SECRET}]}
    assert SECRET not in repr(data) and SECRET not in repr(params["interpolated"])


# ── (b) IfNode left / right ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ifnode_operands_are_not_reevaluated(tmp_path):
    wf = _wf(
        [
            # Old engine: left became the secret and matched the authored right → True.
            {"id": "if_secret", "type": "IfNode", "left": "{{ nodes.agent.secretish }}",
             "operator": "==", "right": "{{ nodes.hidden.value }}"},
            # Old engine: left became 2 (int) → `"1 + 1 }}" in 2` → False.
            {"id": "if_math", "type": "IfNode", "left": "{{ nodes.agent.math }}",
             "operator": "contains", "right": "1 + 1 }}"},
            # Old engine: right became 2 → 2 == 2 → True.
            {"id": "if_right", "type": "IfNode", "left": 2,
             "operator": "==", "right": "{{ nodes.agent.math }}"},
        ],
        [{"from": "agent", "to": "if_secret"}, {"from": "agent", "to": "if_math"},
         {"from": "agent", "to": "if_right"}],
    )
    job = await _run(wf, storage_dir=tmp_path)
    assert _out(job, "if_secret", "result") is False
    assert _out(job, "if_math", "result") is True
    assert _out(job, "if_right", "result") is False


# ── (d) TelegramNode template, (e) GenericNode fields, (g) credential + input ───

@pytest.mark.asyncio
async def test_telegram_template_and_credentials_are_data(monkeypatch, tmp_path):
    import programgarden_community  # noqa: F401 - registers TelegramNode
    from programgarden_community.nodes.messaging.telegram import TelegramNode

    captured: List[Dict[str, Any]] = []

    async def _capture(self, context):
        captured.append({"template": self.template, "chat_id": self.chat_id, "bot_token": self.bot_token})
        return {"sent": False, "message_id": "", "captured": True}

    monkeypatch.setattr(TelegramNode, "execute", _capture)
    wf = _wf(
        [{
            "id": "notify", "type": "TelegramNode", "credential_id": "tg",
            "template": "AI says: {{ nodes.agent.secretish }} / {{ nodes.agent.math }} / input={{ input.note }}",
        }],
        [{"from": "agent", "to": "notify"}],
        credentials=[{
            "credential_id": "tg", "type": "telegram_bot",
            "data": [
                {"key": "bot_token", "value": "tok-{{ 1 + 1 }}", "type": "password", "label": "Bot Token"},
                {"key": "chat_id", "value": TEXT_SECRET, "type": "text", "label": "Chat ID"},
            ],
        }],
    )
    # Real (non dry-run) pass: the send itself is replaced above, nothing leaves the host.
    job = await _run(wf, context_params={"note": TEXT_MATH}, dry_run=False, storage_dir=tmp_path)
    assert captured, "TelegramNode.execute was not reached"
    rendered = captured[0]
    assert rendered["template"] == f"AI says: {TEXT_SECRET} / {TEXT_MATH} / input={TEXT_MATH}"
    assert rendered["chat_id"] == TEXT_SECRET
    assert rendered["bot_token"] == "tok-{{ 1 + 1 }}"
    assert _out(job, "notify", "captured") is True


@pytest.mark.asyncio
async def test_workflow_input_value_is_data(tmp_path):
    wf = _wf(
        [{
            "id": "consumer", "type": "CodeNode", "code": ECHO_CODE,
            "outputs": [{"name": "data", "type": "object"}],
            "data": "{{ input.note }}",
        }],
        [{"from": "agent", "to": "consumer"}],
    )
    job = await _run(wf, context_params={"note": TEXT_SECRET}, storage_dir=tmp_path)
    assert _out(job, "consumer", "data") == TEXT_SECRET


# ── (f) auto-iterated {{ item.field }} whose value contains {{ ─────────────────

@pytest.mark.asyncio
async def test_auto_iterated_item_value_is_data(monkeypatch, tmp_path):
    import programgarden_community  # noqa: F401
    from programgarden_community.nodes.messaging.telegram import TelegramNode

    seen: List[str] = []

    async def _capture(self, context):
        seen.append(self.template)
        return {"sent": False, "message_id": ""}

    monkeypatch.setattr(TelegramNode, "execute", _capture)
    wf = _wf(
        [
            {"id": "rows", "type": "CodeNode",
             "code": (
                 "async def execute(data, params, context):\n"
                 "    o, c = '{' + '{', '}' + '}'\n"
                 "    return {'symbols': [\n"
                 "        {'symbol': 'AAPL', 'exchange': 'NASDAQ', 'note': o + ' nodes.hidden.value ' + c},\n"
                 "        {'symbol': 'MSFT', 'exchange': 'NASDAQ', 'note': 'plain'}]}\n"
             ),
             "outputs": [{"name": "symbols", "type": "array"}]},
            {"id": "notify", "type": "TelegramNode", "credential_id": "tg",
             "template": "Item {{ item.symbol }}: {{ item.note }}"},
        ],
        [{"from": "agent", "to": "rows"}, {"from": "rows", "to": "notify"}],
        credentials=[{"credential_id": "tg", "type": "telegram_bot", "data": [
            {"key": "bot_token", "value": "t", "type": "password", "label": "Bot Token"},
            {"key": "chat_id", "value": "1", "type": "text", "label": "Chat ID"},
        ]}],
    )
    await _run(wf, dry_run=False, storage_dir=tmp_path)
    assert seen == [f"Item AAPL: {TEXT_SECRET}", "Item MSFT: plain"]


# ── (i) deep_validate records no unresolved binding for runtime values ─────────

@pytest.mark.asyncio
async def test_deep_validate_does_not_flag_runtime_text():
    code = (
        "async def execute(data, params, context):\n"
        "    o, c = '{' + '{', '}' + '}'\n"
        "    return {'text': o + ' nodes.missing.value ' + c}\n"
    )
    wf = {
        "id": "wf-deep", "name": "wf-deep",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "agent", "type": "CodeNode", "code": code, "outputs": [{"name": "text", "type": "string"}]},
            {"id": "consumer", "type": "CodeNode",
             "code": "async def execute(data, params, context):\n    return {'data': data}",
             "outputs": [{"name": "data", "type": "string"}], "data": "{{ nodes.agent.text }}"},
        ],
        "edges": [{"from": "start", "to": "agent"}, {"from": "agent", "to": "consumer"}],
        "credentials": [],
    }
    result = await WorkflowExecutor().deep_validate(wf)
    codes = [getattr(e.code, "value", e.code) for e in result.errors]
    assert "DEEP_VALIDATION_BINDING_UNRESOLVED" not in codes, result.errors
    assert result.is_valid, result.errors


# ── (j) CodeNode code containing "{{" runs unchanged ───────────────────────────

@pytest.mark.asyncio
async def test_codenode_source_with_braces_is_not_evaluated(tmp_path):
    wf = _wf(
        [
            # Old engine: the job pass rewrote the source to return '2'.
            {"id": "src", "type": "CodeNode",
             "code": "async def execute(data, params, context):\n    return {'t': '{{ 1 + 1 }}'}",
             "outputs": [{"name": "t", "type": "string"}]},
            {"id": "src_f", "type": "CodeNode",
             "code": "async def execute(data, params, context):\n    x = 1\n    return {'f': f'{{x}}'}",
             "outputs": [{"name": "f", "type": "string"}]},
        ],
        [{"from": "agent", "to": "src"}, {"from": "agent", "to": "src_f"}],
    )
    job = await _run(wf, storage_dir=tmp_path)
    assert _out(job, "src", "t") == "{{ 1 + 1 }}"
    assert _out(job, "src_f", "f") == "{x}"


# ── unit level: evaluate_all_bindings / provenance helpers ──────────────────────

class _Node:
    def __init__(self, node_type, config, fields=None):
        self.node_type, self.config, self.fields = node_type, config, fields or {}


class _Workflow:
    def __init__(self, nodes):
        self.nodes = nodes


def _context(authored: Dict[str, Any]) -> ExecutionContext:
    ctx = ExecutionContext(job_id="t", workflow_id="t")
    ctx.register_authored_node_configs(_Workflow({"n": _Node("TelegramNode", authored)}))
    ctx.set_output("hidden", "value", SECRET)
    ctx.set_output("agent", "text", TEXT_SECRET)
    return ctx


def test_evaluate_all_bindings_skips_resolved_and_injected_values():
    authored = {"template": "{{ nodes.agent.text }}", "keep": "{{ nodes.hidden.value }}",
                "nested": {"a": ["{{ nodes.agent.text }}"]}}
    ctx = _context(authored)
    config = {
        "template": TEXT_SECRET,               # resolved by pass 1 → data
        "keep": "{{ nodes.hidden.value }}",    # still authored → evaluated once
        "nested": {"a": ["{{ nodes.agent.text }}"]},
        "connection": {"appkey": TEXT_SECRET},  # engine-injected → data
        "tool_arg": TEXT_SECRET,               # e.g. an AI tool-call argument → data
    }
    out = evaluate_all_bindings(config, ctx, "n")
    assert out["template"] == TEXT_SECRET
    assert out["keep"] == SECRET
    assert out["nested"] == {"a": [TEXT_SECRET]}
    assert out["connection"] == {"appkey": TEXT_SECRET}
    assert out["connection"] is not config["connection"]  # containers are still copied
    assert out["tool_arg"] == TEXT_SECRET


def test_evaluate_all_bindings_without_snapshot_keeps_legacy_behaviour():
    ctx = ExecutionContext(job_id="t", workflow_id="t")
    ctx.set_output("hidden", "value", SECRET)
    out = evaluate_all_bindings({"x": "{{ nodes.hidden.value }}"}, ctx, "standalone")
    assert out == {"x": SECRET}


def test_shield_round_trip_restores_runtime_values():
    authored = {"a": "{{ nodes.x.y }}", "b": {"c": "{{ nodes.x.z }}"}, "lst": ["{{ nodes.x.y }}", 1]}
    runtime = {"a": TEXT_SECRET, "b": {"c": "{{ nodes.x.z }}", "extra": TEXT_MATH},
               "lst": ["{{ nodes.x.y }}", 1], "_realtime_data": {"k": TEXT_MATH}}
    shielded = bp.shield_config(runtime, authored)
    assert isinstance(shielded["a"], bp._Literal)
    assert shielded["b"]["c"] == "{{ nodes.x.z }}"
    assert isinstance(shielded["b"]["extra"], bp._Literal)
    assert isinstance(shielded["_realtime_data"], bp._Literal)
    assert bp.unshield_config(shielded, authored) == runtime


def test_codenode_code_is_never_authored():
    snap = bp.authored_snapshot("CodeNode", {"code": "x = '{{ 1 }}'", "data": "{{ nodes.a.b }}"})
    assert "code" not in snap and snap["data"] == "{{ nodes.a.b }}"
    assert bp.may_evaluate("{{ 1 }}", bp.child(snap, "code")) is False


@pytest.mark.asyncio
async def test_generic_plugin_fields_are_evaluated_once(monkeypatch):
    authored = {"fields": {"f": "{{ nodes.agent.text }}"}}
    ctx = _context(authored)
    ctx.set_output("agent", "text", TEXT_SECRET)
    executor = GenericNodeExecutor()
    seen = {}

    class _Fake:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        async def execute(self, context):
            return {"ok": True}

    from programgarden_core.registry import NodeTypeRegistry

    original = NodeTypeRegistry.get

    def _get(self, node_type):
        return _Fake if node_type == "FakeNode" else original(self, node_type)

    monkeypatch.setattr(NodeTypeRegistry, "get", _get)
    await executor.execute("n", "FakeNode", {"fields": {"f": "{{ nodes.agent.text }}"}}, ctx)
    # Evaluated once (authored template → runtime text); the plugin-fields pass that
    # follows must not evaluate the runtime text a second time.
    assert seen["fields"] == {"f": TEXT_SECRET}
