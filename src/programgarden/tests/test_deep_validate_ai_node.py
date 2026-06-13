"""Phase 1 — deep_validate AIAgentNode fixture + silent-fail error promotion.

Covers:
- ``deep_fixtures.ai_agent_fixture`` shapes the ``response`` port from
  output_format / output_schema (text / json / structured).
- ``AIAgentNodeExecutor`` never touches a live LLM in deep mode.
- A full deep_validate over an AI workflow completes (is_valid) with downstream
  ``{{ nodes.agent.response.<field> }}`` bindings resolving (false-reject 0).
- A node that *returns* a sole-``error`` dict (instead of raising) is promoted
  to a blocking DEEP_VALIDATION_NODE_ERROR rather than silently swallowed.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

import programgarden.executor as executor_mod
from programgarden import ProgramGarden
from programgarden import deep_fixtures as df
from programgarden.executor import AIAgentNodeExecutor

from test_deep_validate import make_deep_context, order_workflow


pytestmark = pytest.mark.timeout(30)


# ============================================================
# 1. ai_agent_fixture shaping
# ============================================================

def test_ai_agent_fixture_text_is_string():
    out = df.ai_agent_fixture({"output_format": "text"})
    assert set(out.keys()) == {"response"}
    assert isinstance(out["response"], str) and out["response"]


def test_ai_agent_fixture_default_format_is_text():
    # No output_format → text default.
    out = df.ai_agent_fixture({})
    assert isinstance(out["response"], str)


def test_ai_agent_fixture_json_is_dict():
    out = df.ai_agent_fixture({"output_format": "json"})
    assert out["response"] == {}


def test_ai_agent_fixture_structured_shapes_every_field():
    schema = {
        "signal": {"type": "string", "enum": ["buy", "sell", "hold"]},
        "confidence": {"type": "number"},
        "qty": {"type": "integer"},
        "urgent": {"type": "boolean"},
        "notes": "string",  # bare-string entry form
        "legs": {
            "type": "array",
            "items": {"type": "object", "properties": {"symbol": {"type": "string"}}},
        },
    }
    resp = df.ai_agent_fixture(
        {"output_format": "structured", "output_schema": schema}
    )["response"]

    assert resp["signal"] == "buy"  # enum → first allowed value
    assert isinstance(resp["confidence"], float)
    assert isinstance(resp["qty"], int) and not isinstance(resp["qty"], bool)
    assert resp["urgent"] is True
    assert isinstance(resp["notes"], str)
    assert isinstance(resp["legs"], list) and resp["legs"]
    assert resp["legs"][0] == {"symbol": "deep_validate"}


def test_ai_agent_fixture_structured_without_schema_falls_back_to_string():
    out = df.ai_agent_fixture({"output_format": "structured"})
    assert isinstance(out["response"], str)


# ============================================================
# 2. Executor never calls a live LLM in deep mode
# ============================================================

@pytest.mark.asyncio
async def test_ai_executor_no_live_llm_in_deep_mode():
    """In deep mode AIAgentNodeExecutor must return a fixture WITHOUT ever
    constructing an LLM provider or making a model call."""
    ctx = make_deep_context()
    ex = AIAgentNodeExecutor()

    def _boom(*a, **k):  # pragma: no cover - asserted via call_count
        raise AssertionError("LLMProvider must NOT be built in deep_validate")

    with patch("programgarden.providers.LLMProvider.from_connection", side_effect=_boom) as mock_prov:
        out = await ex.execute(
            node_id="agent",
            node_type="AIAgentNode",
            config={
                "output_format": "structured",
                "output_schema": {"signal": {"type": "string", "enum": ["buy", "hold"]}},
            },
            context=ctx,
        )

    assert mock_prov.call_count == 0
    assert out == {"response": {"signal": "buy"}}


@pytest.mark.asyncio
async def test_ai_executor_deep_honours_caller_override():
    ctx = make_deep_context()
    ctx.context_params["deep_fixtures"] = {"agent": {"response": {"signal": "sell"}}}
    ex = AIAgentNodeExecutor()
    out = await ex.execute(
        node_id="agent",
        node_type="AIAgentNode",
        config={"output_format": "json"},
        context=ctx,
    )
    assert out == {"response": {"signal": "sell"}}


# ============================================================
# 3. Full deep_validate over an AI workflow — false-reject 0
# ============================================================

def _ai_workflow() -> dict:
    """start → llm → agent (structured) → summary, with a sub-field binding."""
    return {
        "id": "wf-deep-ai",
        "name": "deep ai workflow",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "llm", "type": "LLMModelNode", "credential_id": "llm_cred", "model": "gpt-4o"},
            {
                "id": "agent",
                "type": "AIAgentNode",
                "user_prompt": "Give a trading signal.",
                "output_format": "structured",
                "output_schema": {
                    "signal": {"type": "string", "enum": ["buy", "sell", "hold"]},
                    "confidence": {"type": "number"},
                },
                "max_tool_calls": 0,
            },
            {
                "id": "summary",
                "type": "SummaryDisplayNode",
                "title": "Signal",
                "data": "{{ nodes.agent.response.signal }}",
            },
        ],
        "edges": [
            {"from": "start", "to": "llm"},
            {"from": "llm", "to": "agent", "type": "ai_model"},
            {"from": "agent", "to": "summary"},
        ],
        "credentials": [
            {
                "credential_id": "llm_cred",
                "type": "llm_openai",
                "data": [{"key": "api_key", "value": "", "type": "password", "label": "API Key"}],
            }
        ],
    }


@pytest.mark.asyncio
async def test_deep_validate_ai_workflow_passes_without_live_llm():
    pg = ProgramGarden()

    def _boom(*a, **k):  # pragma: no cover
        raise AssertionError("no live LLM call allowed in deep_validate")

    with patch("programgarden.providers.LLMProvider.from_connection", side_effect=_boom) as mock_prov:
        result = await pg.executor.deep_validate(_ai_workflow(), timeout=12.0)

    assert mock_prov.call_count == 0
    assert result.is_valid, [e.short() for e in result.errors]
    # The {{ nodes.agent.response.signal }} binding must NOT be flagged unresolved.
    assert not any(
        getattr(e, "code", None)
        and str(e.code).endswith("BINDING_UNRESOLVED")
        for e in result.errors
    ), [e.short() for e in result.errors]


# ============================================================
# 4. silent-fail: a sole-`error` node return is promoted (not swallowed)
# ============================================================

@pytest.mark.asyncio
async def test_sole_error_return_promoted_to_structured_error_in_deep():
    """A node returning ``{"error": ...}`` instead of raising must surface as a
    blocking DEEP_VALIDATION_NODE_ERROR — not pass as a COMPLETED output."""
    pg = ProgramGarden()

    async def _err_execute(self, node_id, node_type, config, context, **kwargs):
        return {"error": "simulated account failure"}

    with patch.object(executor_mod.AccountNodeExecutor, "execute", _err_execute):
        result = await pg.executor.deep_validate(order_workflow(), timeout=12.0)

    assert not result.is_valid
    promoted = [
        e for e in result.errors
        if str(getattr(e, "code", "")).endswith("DEEP_VALIDATION_NODE_ERROR")
        and getattr(getattr(e, "location", None), "node_id", None) == "account"
    ]
    assert promoted, [e.short() for e in result.errors]
    assert "simulated account failure" in promoted[0].message


@pytest.mark.asyncio
async def test_error_with_other_ports_is_not_promoted():
    """A partial payload like ``{"symbols": [], "error": ...}`` keeps flowing —
    only a *sole* error key is treated as a swallowed failure."""
    pg = ProgramGarden()

    async def _partial_execute(self, node_id, node_type, config, context, **kwargs):
        return {"positions": [], "balance": {}, "error": "soft warning"}

    with patch.object(executor_mod.AccountNodeExecutor, "execute", _partial_execute):
        result = await pg.executor.deep_validate(order_workflow(), timeout=12.0)

    # No DEEP_VALIDATION_NODE_ERROR was raised for "account" from the promotion path.
    assert not any(
        str(getattr(e, "code", "")).endswith("DEEP_VALIDATION_NODE_ERROR")
        and getattr(getattr(e, "location", None), "node_id", None) == "account"
        and "soft warning" in getattr(e, "message", "")
        for e in result.errors
    ), [e.short() for e in result.errors]
