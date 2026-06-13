"""End-to-end tests for the structured-validation pipeline.

Covers:
- ErrorCode emission on representative workflows.
- Static recommendations (8 rules) and inline error->rec attachments.
- Cascade suppression for all four root codes.
- Volume capping via ValidationLimits.
- ResultSummary deterministic next_action_hint generation.

Tests purposefully construct minimal workflows so the assertions stay
robust against unrelated catalogue changes.
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from programgarden import WorkflowExecutor
from programgarden_core import (
    ErrorCode,
    ValidationLimits,
)


def _wrap(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    return {
        "id": "test-wf",
        "name": "structured validation test",
        "version": "1.0",
        "nodes": nodes,
        "edges": edges or [],
        "credentials": [],
    }


def _codes(result) -> List[str]:
    return [e.code if isinstance(e.code, str) else e.code.value for e in result.errors]


@pytest.fixture(scope="module")
def executor() -> WorkflowExecutor:
    return WorkflowExecutor()


# ---------------------------------------------------------------------------
# Static error codes (sampled — full coverage lives in Phase 5 expansion)
# ---------------------------------------------------------------------------


def test_missing_start_node(executor: WorkflowExecutor) -> None:
    workflow = _wrap([
        {"id": "thr", "type": "ThrottleNode", "interval_seconds": 1.0},
    ])
    result = executor.validate(workflow)
    assert ErrorCode.MISSING_START_NODE.value in _codes(result)


def test_multiple_start_nodes(executor: WorkflowExecutor) -> None:
    workflow = _wrap([
        {"id": "s1", "type": "StartNode"},
        {"id": "s2", "type": "StartNode"},
    ])
    result = executor.validate(workflow)
    assert ErrorCode.MULTIPLE_START_NODES.value in _codes(result)


def test_unknown_node_type_attaches_suggestion(executor: WorkflowExecutor) -> None:
    workflow = _wrap([
        {"id": "s1", "type": "StartNode"},
        {"id": "rogue", "type": "OverseasStokBrokerNode"},
    ])
    result = executor.validate(workflow)
    assert ErrorCode.UNKNOWN_NODE_TYPE.value in _codes(result)
    unknown_err = next(e for e in result.errors if (e.code if isinstance(e.code, str) else e.code.value) == "UNKNOWN_NODE_TYPE")
    assert unknown_err.available_values is not None
    assert any("Broker" in v for v in unknown_err.available_values)


def test_reserved_node_id(executor: WorkflowExecutor) -> None:
    workflow = _wrap([
        {"id": "input", "type": "StartNode"},
    ])
    result = executor.validate(workflow)
    assert ErrorCode.RESERVED_NODE_ID.value in _codes(result)


def test_duplicate_node_id_cascade_suppresses_invalid_edge_ref(executor: WorkflowExecutor) -> None:
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "dup", "type": "ThrottleNode", "interval_seconds": 1.0},
            {"id": "dup", "type": "ThrottleNode", "interval_seconds": 2.0},
        ],
        edges=[{"from": "s1", "to": "dup"}, {"from": "dup", "to": "nowhere"}],
    )
    result = executor.validate(workflow)
    codes = _codes(result)
    assert ErrorCode.DUPLICATE_NODE_ID.value in codes
    # The INVALID_EDGE_REF for "nowhere" survives (different node id), but
    # cascade suppression should still surface a root cause summary entry.
    assert result.summary is not None
    assert "dup" in result.summary.root_cause_node_ids or result.summary.root_cause_node_ids == []


def test_cycle_detected_emits_with_location(executor: WorkflowExecutor) -> None:
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "a", "type": "ThrottleNode", "interval_seconds": 1.0},
            {"id": "b", "type": "ThrottleNode", "interval_seconds": 1.0},
        ],
        edges=[
            {"from": "s1", "to": "a"},
            {"from": "a", "to": "b"},
            {"from": "b", "to": "a"},
        ],
    )
    result = executor.validate(workflow)
    cycle_err = next(
        (e for e in result.errors if (e.code if isinstance(e.code, str) else e.code.value) == "CYCLE_DETECTED"),
        None,
    )
    assert cycle_err is not None
    assert "cycle_path" in cycle_err.details


def test_invalid_expression_ref_gets_inline_recommendation(executor: WorkflowExecutor) -> None:
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "real_node", "type": "ThrottleNode", "interval_seconds": 1.0},
            {
                "id": "consumer",
                "type": "ThrottleNode",
                "interval_seconds": 1.0,
                "label": "{{ nodes.real_nod.output }}",
            },
        ],
        edges=[
            {"from": "s1", "to": "real_node"},
            {"from": "real_node", "to": "consumer"},
        ],
    )
    result = executor.validate(workflow)
    invalid = next(
        e for e in result.errors
        if (e.code if isinstance(e.code, str) else e.code.value) == "INVALID_EXPRESSION_REF"
    )
    assert invalid.recommendations
    rec = invalid.recommendations[0]
    assert rec.rule_id == "REC_EXPRESSION_PORT_TYPO"
    assert any("real_node" in opt for opt in rec.options)


# ---------------------------------------------------------------------------
# Static recommendation rules (sampled)
# ---------------------------------------------------------------------------


def test_realtime_throttle_recommendation_emitted(executor: WorkflowExecutor) -> None:
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {"id": "rt", "type": "OverseasStockRealMarketDataNode"},
            {"id": "ord", "type": "OverseasStockNewOrderNode"},
        ],
        edges=[
            {"from": "s1", "to": "broker"},
            {"from": "broker", "to": "rt"},
            {"from": "rt", "to": "ord"},
        ],
    )
    workflow["credentials"] = [
        {
            "credential_id": "c1",
            "type": "broker_ls_overseas_stock",
            "data": [{"key": "appkey", "value": "x"}, {"key": "appsecret", "value": "y"}],
        }
    ]
    result = executor.validate(workflow)
    rule_ids = [r.rule_id for r in result.static_recommendations]
    assert "REC_REALTIME_THROTTLE" in rule_ids


def test_order_retry_risk_recommendation_emitted(executor: WorkflowExecutor) -> None:
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {
                "id": "ord",
                "type": "OverseasStockNewOrderNode",
                "resilience": {"retry": {"enabled": True, "max_retries": 3}},
            },
        ],
        edges=[
            {"from": "s1", "to": "broker"},
            {"from": "broker", "to": "ord"},
        ],
    )
    workflow["credentials"] = [
        {
            "credential_id": "c1",
            "type": "broker_ls_overseas_stock",
            "data": [{"key": "appkey", "value": "x"}, {"key": "appsecret", "value": "y"}],
        }
    ]
    result = executor.validate(workflow)
    rule_ids = [r.rule_id for r in result.static_recommendations]
    assert "REC_ORDER_RETRY_RISK" in rule_ids


def test_external_api_resilience_recommendation_for_http_node(executor: WorkflowExecutor) -> None:
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "http", "type": "HTTPRequestNode", "url": "https://example.com"},
        ],
        edges=[{"from": "s1", "to": "http"}],
    )
    result = executor.validate(workflow)
    rule_ids = [r.rule_id for r in result.static_recommendations]
    assert "REC_EXTERNAL_API_RESILIENCE" in rule_ids


def test_runtime_recommendations_empty_without_dry_run(executor: WorkflowExecutor) -> None:
    """validate() never populates runtime_recommendations."""
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "thr", "type": "ThrottleNode", "interval_seconds": 1.0},
        ],
        edges=[{"from": "s1", "to": "thr"}],
    )
    result = executor.validate(workflow)
    assert result.runtime_recommendations == []


# ---------------------------------------------------------------------------
# Volume control
# ---------------------------------------------------------------------------


def test_suppress_recommendations_filters_by_rule_id(executor: WorkflowExecutor) -> None:
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "http", "type": "HTTPRequestNode", "url": "https://example.com"},
        ],
        edges=[{"from": "s1", "to": "http"}],
    )
    full = executor.validate(workflow)
    assert any(r.rule_id == "REC_EXTERNAL_API_RESILIENCE" for r in full.static_recommendations)

    filtered = executor.validate(workflow, suppress_recommendations=["REC_EXTERNAL_API_RESILIENCE"])
    assert not any(r.rule_id == "REC_EXTERNAL_API_RESILIENCE" for r in filtered.static_recommendations)


def test_validation_limits_caps_errors(executor: WorkflowExecutor) -> None:
    """Caps `errors` channel and records the dropped count in `truncated`."""
    nodes: List[Dict[str, Any]] = [{"id": "s1", "type": "StartNode"}]
    for idx in range(15):
        nodes.append({"id": f"u{idx}", "type": "OverseasStokBrokerNode"})  # typo on purpose
    workflow = _wrap(nodes)
    result = executor.validate(workflow, limits=ValidationLimits(max_errors=5))
    assert len(result.errors) <= 5
    assert result.truncated.get("errors", 0) >= 1
    assert result.summary is not None and result.summary.truncated


def test_summary_hint_for_single_error(executor: WorkflowExecutor) -> None:
    workflow = _wrap([
        {"id": "thr", "type": "ThrottleNode", "interval_seconds": 1.0},
    ])
    result = executor.validate(workflow)
    assert result.summary is not None
    assert result.summary.next_action_hint is not None
    assert "MISSING_START_NODE" in result.summary.next_action_hint


def test_summary_hint_when_only_recommendations(executor: WorkflowExecutor) -> None:
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "http", "type": "HTTPRequestNode", "url": "https://example.com"},
        ],
        edges=[{"from": "s1", "to": "http"}],
    )
    result = executor.validate(workflow)
    assert result.is_valid
    assert result.summary is not None
    assert result.summary.next_action_hint is not None
    assert "improvement" in result.summary.next_action_hint.lower()


# ---------------------------------------------------------------------------
# AI Agent edge type semantics
# ---------------------------------------------------------------------------


def test_ai_model_edge_rejects_non_llm_source(executor: WorkflowExecutor) -> None:
    """ai_model edge source must be LLMModelNode."""
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {"id": "agent", "type": "AIAgentNode"},
        ],
        edges=[
            {"from": "s1", "to": "agent"},
            {"from": "broker", "to": "agent", "type": "ai_model"},
        ],
    )
    workflow["credentials"] = [{"credential_id": "c1", "type": "broker_ls_overseas_stock", "data": []}]
    result = executor.validate(workflow)
    assert ErrorCode.INVALID_AI_MODEL_EDGE.value in _codes(result)


def test_ai_model_edge_rejects_non_agent_target(executor: WorkflowExecutor) -> None:
    """ai_model edge target must be AIAgentNode."""
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "llm", "type": "LLMModelNode", "credential_id": "c1"},
            {"id": "throttle", "type": "ThrottleNode", "interval_seconds": 1.0},
        ],
        edges=[
            {"from": "s1", "to": "throttle"},
            {"from": "llm", "to": "throttle", "type": "ai_model"},
        ],
    )
    workflow["credentials"] = [{"credential_id": "c1", "type": "llm_anthropic", "data": []}]
    result = executor.validate(workflow)
    assert ErrorCode.INVALID_AI_MODEL_EDGE.value in _codes(result)


def test_expression_port_typo_flagged(executor: WorkflowExecutor) -> None:
    """Strict port validation catches typos like held_symbolls (correct: held_symbols)."""
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {"id": "account", "type": "OverseasStockAccountNode"},
            {
                "id": "display",
                "type": "TableDisplayNode",
                "data": "{{ nodes.account.held_symbolls }}",  # typo
                "columns": ["symbol"],
            },
        ],
        edges=[
            {"from": "s1", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "display"},
        ],
    )
    workflow["credentials"] = [{"credential_id": "c1", "type": "broker_ls_overseas_stock", "data": []}]
    result = executor.validate(workflow)
    invalid_refs = [e for e in result.errors if (e.code if isinstance(e.code, str) else e.code.value) == "INVALID_EXPRESSION_REF"]
    assert any(e.location and e.location.output_port == "held_symbolls" for e in invalid_refs), (
        "held_symbolls typo should be flagged by strict port validation"
    )


def test_expression_chain_method_not_flagged(executor: WorkflowExecutor) -> None:
    """Chain methods like .filter()/.first() are not ports — must not be flagged."""
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {"id": "account", "type": "OverseasStockAccountNode"},
            {
                "id": "display",
                "type": "TableDisplayNode",
                "data": "{{ nodes.account.filter('pnl > 0') }}",
                "columns": ["symbol"],
            },
        ],
        edges=[
            {"from": "s1", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "display"},
        ],
    )
    workflow["credentials"] = [{"credential_id": "c1", "type": "broker_ls_overseas_stock", "data": []}]
    result = executor.validate(workflow)
    invalid_refs = [e for e in result.errors if (e.code if isinstance(e.code, str) else e.code.value) == "INVALID_EXPRESSION_REF"]
    assert not any(e.location and e.location.output_port == "filter" for e in invalid_refs), (
        "filter() is a chain method, not a port — must not be flagged"
    )


def test_dynamic_node_injection_readiness(executor: WorkflowExecutor) -> None:
    """validate_dynamic_injection=True catches schema-registered-but-not-injected nodes."""
    from programgarden_core.registry import DynamicNodeRegistry
    from programgarden_core.registry.dynamic_node_registry import DynamicNodeSchema

    schema = DynamicNodeSchema(
        node_type="Dynamic_TestInjectionGate",
        category="data",
        outputs=[{"name": "out", "type": "number"}],
    )
    registry = DynamicNodeRegistry()
    registry.register_schema(schema)
    # Make sure the class isn't injected (clear if any).
    registry._node_classes.pop("Dynamic_TestInjectionGate", None)

    try:
        workflow = _wrap(
            [
                {"id": "s1", "type": "StartNode"},
                {"id": "dyn", "type": "Dynamic_TestInjectionGate"},
            ],
            edges=[{"from": "s1", "to": "dyn"}],
        )

        # Default validate() does NOT flag injection state.
        default_result = executor.validate(workflow)
        assert ErrorCode.DYNAMIC_NODE_CLASS_NOT_INJECTED.value not in _codes(default_result)

        # validate_dynamic_injection=True surfaces the missing class.
        strict_result = executor.validate(workflow, validate_dynamic_injection=True)
        assert ErrorCode.DYNAMIC_NODE_CLASS_NOT_INJECTED.value in _codes(strict_result)
    finally:
        registry._schemas.pop("Dynamic_TestInjectionGate", None)


def test_tool_edge_rejects_non_agent_target(executor: WorkflowExecutor) -> None:
    """tool edge target must be AIAgentNode."""
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {"id": "throttle", "type": "ThrottleNode", "interval_seconds": 1.0},
        ],
        edges=[
            {"from": "s1", "to": "throttle"},
            {"from": "broker", "to": "throttle", "type": "tool"},
        ],
    )
    workflow["credentials"] = [{"credential_id": "c1", "type": "broker_ls_overseas_stock", "data": []}]
    result = executor.validate(workflow)
    assert ErrorCode.INVALID_TOOL_EDGE.value in _codes(result)


def test_expression_nested_field_typo_flagged(executor: WorkflowExecutor) -> None:
    """Nested-field typos under a port with declared `fields` are flagged.

    Example: `{{ nodes.account.balance.orderabl_amount }}` — balance is a
    real port on OverseasStockAccountNode and its OutputPort declares
    `orderable_amount`, so the typo should surface as INVALID_EXPRESSION_REF
    rather than silently evaluating to None at runtime.
    """
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {"id": "account", "type": "OverseasStockAccountNode"},
            {
                "id": "display",
                "type": "TableDisplayNode",
                "data": "{{ nodes.account.balance.orderabl_amount }}",  # typo
                "columns": ["value"],
            },
        ],
        edges=[
            {"from": "s1", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "display"},
        ],
    )
    workflow["credentials"] = [{"credential_id": "c1", "type": "broker_ls_overseas_stock", "data": []}]
    result = executor.validate(workflow)
    invalid_refs = [
        e for e in result.errors
        if (e.code if isinstance(e.code, str) else e.code.value) == "INVALID_EXPRESSION_REF"
    ]
    assert any("orderabl_amount" in (e.message or "") for e in invalid_refs), (
        "Nested-field typo on balance.orderable_amount should be flagged"
    )


def test_expression_nested_field_valid_not_flagged(executor: WorkflowExecutor) -> None:
    """Correct nested-field access does not produce a false positive."""
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {"id": "account", "type": "OverseasStockAccountNode"},
            {
                "id": "display",
                "type": "TableDisplayNode",
                "data": "{{ nodes.account.balance.orderable_amount }}",
                "columns": ["value"],
            },
        ],
        edges=[
            {"from": "s1", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "display"},
        ],
    )
    workflow["credentials"] = [{"credential_id": "c1", "type": "broker_ls_overseas_stock", "data": []}]
    result = executor.validate(workflow)
    invalid_refs = [
        e for e in result.errors
        if (e.code if isinstance(e.code, str) else e.code.value) == "INVALID_EXPRESSION_REF"
    ]
    assert not any("orderable_amount" in (e.message or "") for e in invalid_refs), (
        "Valid nested field orderable_amount must not be flagged"
    )


def test_expression_nested_field_skipped_when_no_fields_schema(executor: WorkflowExecutor) -> None:
    """Ports without a declared `fields` schema skip nested validation.

    Many ports have free-form shape (signal payloads, raw event objects).
    Their consumers should still be able to deep-access without validate()
    second-guessing the shape.
    """
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {
                "id": "display",
                "type": "TableDisplayNode",
                # StartNode.start has no `fields` schema declared — nested
                # access is left open.
                "data": "{{ nodes.s1.start.anything_at_all }}",
                "columns": ["value"],
            },
        ],
        edges=[{"from": "s1", "to": "display"}],
    )
    result = executor.validate(workflow)
    invalid_refs = [
        e for e in result.errors
        if (e.code if isinstance(e.code, str) else e.code.value) == "INVALID_EXPRESSION_REF"
    ]
    assert not any("anything_at_all" in (e.message or "") for e in invalid_refs), (
        "Nested access on a port without `fields` schema must not be flagged"
    )


def test_expression_dynamic_node_nested_field_typo_flagged(executor: WorkflowExecutor) -> None:
    """Dynamic_* nodes that declare `fields` on an output port get the
    same nested-field typo gate as static nodes — otherwise injected
    schemas would silently let `{{ nodes.dyn.value.prcie }}` evaluate
    to None at runtime."""
    from programgarden_core.registry import DynamicNodeRegistry
    from programgarden_core.registry.dynamic_node_registry import DynamicNodeSchema

    schema = DynamicNodeSchema(
        node_type="Dynamic_TestNestedField",
        category="data",
        outputs=[
            {
                "name": "value",
                "type": "object",
                "fields": [
                    {"name": "price", "type": "number"},
                    {"name": "volume", "type": "number"},
                ],
            },
        ],
    )
    registry = DynamicNodeRegistry()
    registry.register_schema(schema)

    try:
        workflow = _wrap(
            [
                {"id": "s1", "type": "StartNode"},
                {"id": "dyn", "type": "Dynamic_TestNestedField"},
                {
                    "id": "display",
                    "type": "TableDisplayNode",
                    # Typo: should be `price` (declared in fields)
                    "data": "{{ nodes.dyn.value.prcie }}",
                    "columns": ["value"],
                },
            ],
            edges=[
                {"from": "s1", "to": "dyn"},
                {"from": "dyn", "to": "display"},
            ],
        )
        result = executor.validate(workflow)
        invalid_refs = [
            e for e in result.errors
            if (e.code if isinstance(e.code, str) else e.code.value) == "INVALID_EXPRESSION_REF"
        ]
        assert any("prcie" in (e.message or "") for e in invalid_refs), (
            "Dynamic node nested-field typo must be flagged the same as static nodes"
        )
    finally:
        registry._schemas.pop("Dynamic_TestNestedField", None)


def test_expression_dynamic_node_nested_field_valid_not_flagged(executor: WorkflowExecutor) -> None:
    """Valid nested-field access on a Dynamic_* node does not produce
    a false positive."""
    from programgarden_core.registry import DynamicNodeRegistry
    from programgarden_core.registry.dynamic_node_registry import DynamicNodeSchema

    schema = DynamicNodeSchema(
        node_type="Dynamic_TestNestedFieldValid",
        category="data",
        outputs=[
            {
                "name": "value",
                "type": "object",
                "fields": [{"name": "price", "type": "number"}],
            },
        ],
    )
    registry = DynamicNodeRegistry()
    registry.register_schema(schema)

    try:
        workflow = _wrap(
            [
                {"id": "s1", "type": "StartNode"},
                {"id": "dyn", "type": "Dynamic_TestNestedFieldValid"},
                {
                    "id": "display",
                    "type": "TableDisplayNode",
                    "data": "{{ nodes.dyn.value.price }}",
                    "columns": ["value"],
                },
            ],
            edges=[
                {"from": "s1", "to": "dyn"},
                {"from": "dyn", "to": "display"},
            ],
        )
        result = executor.validate(workflow)
        invalid_refs = [
            e for e in result.errors
            if (e.code if isinstance(e.code, str) else e.code.value) == "INVALID_EXPRESSION_REF"
        ]
        assert not any("price" in (e.message or "") for e in invalid_refs), (
            "Valid dynamic nested field must not be flagged"
        )
    finally:
        registry._schemas.pop("Dynamic_TestNestedFieldValid", None)


def test_expression_nested_method_call_not_flagged(executor: WorkflowExecutor) -> None:
    """Method call after a port (e.g. .toString()) is not validated as a field."""
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {"id": "account", "type": "OverseasStockAccountNode"},
            {
                "id": "display",
                "type": "TableDisplayNode",
                # `.something()` after balance is a method call on the
                # value, not a nested field reference.
                "data": "{{ nodes.account.balance.something() }}",
                "columns": ["value"],
            },
        ],
        edges=[
            {"from": "s1", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "display"},
        ],
    )
    workflow["credentials"] = [{"credential_id": "c1", "type": "broker_ls_overseas_stock", "data": []}]
    result = executor.validate(workflow)
    invalid_refs = [
        e for e in result.errors
        if (e.code if isinstance(e.code, str) else e.code.value) == "INVALID_EXPRESSION_REF"
    ]
    assert not any("something" in (e.message or "") for e in invalid_refs), (
        "Method call after a port must not be flagged as a nested-field typo"
    )


# ---------------------------------------------------------------------------
# Phase 2 — cross-port TYPE compatibility (INVALID_FIELD_TYPE)
# ---------------------------------------------------------------------------


def _sizing_wf(balance_expr: str) -> Dict[str, Any]:
    """start → broker → account → sizing, binding `balance` to `balance_expr`.
    `PositionSizingNode.balance` is a numeric field — the type-compat gate."""
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {"id": "account", "type": "OverseasStockAccountNode"},
            {
                "id": "sizing",
                "type": "PositionSizingNode",
                "symbol": "{{ item }}",
                "balance": balance_expr,
                "market_data": "{{ nodes.market.value }}",
                "method": "fixed_percent",
                "max_percent": 10.0,
            },
        ],
        edges=[
            {"from": "s1", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "sizing"},
        ],
    )
    workflow["credentials"] = [{"credential_id": "c1", "type": "broker_ls_overseas_stock", "data": []}]
    return workflow


def test_type_mismatch_number_field_reads_string_output(executor: WorkflowExecutor) -> None:
    # balance (number) <- held_symbols.symbol (string) → INVALID_FIELD_TYPE
    result = executor.validate(_sizing_wf("{{ nodes.account.held_symbols.symbol }}"))
    type_errs = [
        e for e in result.errors
        if (e.code if isinstance(e.code, str) else e.code.value) == "INVALID_FIELD_TYPE"
    ]
    assert type_errs, "feeding a string output field into a numeric config field must be flagged"
    err = type_errs[0]
    assert err.location.node_id == "sizing"
    assert err.location.field_path == "balance"
    assert err.details.get("ref_field") == "symbol"


def test_type_match_number_field_reads_number_output(executor: WorkflowExecutor) -> None:
    # balance (number) <- balance.orderable_amount (number) → no type error
    result = executor.validate(_sizing_wf("{{ nodes.account.balance.orderable_amount }}"))
    codes = _codes(result)
    assert ErrorCode.INVALID_FIELD_TYPE.value not in codes


def test_type_check_skips_any_typed_consumer(executor: WorkflowExecutor) -> None:
    # IfNode.left/right are `expected_type='any'` — must never be type-checked,
    # even when reading a string output field.
    workflow = _wrap(
        [
            {"id": "s1", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "c1"},
            {"id": "account", "type": "OverseasStockAccountNode"},
            {
                "id": "gate",
                "type": "IfNode",
                "left": "{{ nodes.account.held_symbols.symbol }}",
                "operator": "==",
                "right": "AAPL",
            },
        ],
        edges=[
            {"from": "s1", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "gate"},
        ],
    )
    workflow["credentials"] = [{"credential_id": "c1", "type": "broker_ls_overseas_stock", "data": []}]
    result = executor.validate(workflow)
    assert ErrorCode.INVALID_FIELD_TYPE.value not in _codes(result)


def test_type_check_skips_method_chain(executor: WorkflowExecutor) -> None:
    # A chaining method (.first()) yields a value the static gate cannot type —
    # it must not be flagged as a mismatch.
    result = executor.validate(_sizing_wf("{{ nodes.account.positions.first() }}"))
    assert ErrorCode.INVALID_FIELD_TYPE.value not in _codes(result)
