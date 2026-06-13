"""Phase 3 — configurable semantic/safety rule layer (R1~R4) for deep_validate.

Covers:
- ``analyze_workflow_semantics`` per-rule severity config (off by default).
- R1 order-quantity-from-AI (structural binding-graph detection, no keywords).
- R2 schema-less structured AIAgent output + preset/schema false-reject guards.
- R3 hardcoded quantity + PositionSizing guard. R4 ignored broker field.
- Korean ``suggestion`` clarity on every finding (feedback_chatbot_error_clarity).
- Never-raising on malformed DSL.
- ``deep_validate`` integration: strict opt-in REJECTs the AI→order probe while
  the default (no config) pass is byte-for-byte unchanged (no SEMANTIC codes).
- 86-example corpus: zero error-severity semantic findings under strict
  (false-reject 0).
"""
from __future__ import annotations

import copy
import glob
import json
import os

import pytest

from programgarden import ProgramGarden
from programgarden.semantic_rules import (
    analyze_workflow_semantics,
    normalize_severities,
    DEFAULT_SEMANTIC_SEVERITIES,
    STRICT_SEMANTIC_SEVERITIES,
    RULE_ORDER_QTY_FROM_AI,
    RULE_STRUCTURED_OUTPUT_NO_SCHEMA,
    RULE_HARDCODED_ORDER_QTY,
    RULE_ORDER_IGNORED_FIELD,
)

pytestmark = pytest.mark.timeout(60)

EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples", "workflows"
)


def _codes(infos):
    return [str(i.code) for i in infos]


def _has(infos, code_suffix):
    return any(str(i.code).endswith(code_suffix) for i in infos)


# ---------------------------------------------------------------------------
# Default = off (zero regression)
# ---------------------------------------------------------------------------

def test_default_no_config_is_empty():
    wf = {"nodes": [
        {"id": "agent", "type": "AIAgentNode", "output_format": "text"},
        {"id": "ord", "type": "OverseasStockNewOrderNode",
         "order": {"symbol": "AAPL", "quantity": "{{ nodes.agent.response }}"}},
    ], "edges": []}
    assert analyze_workflow_semantics(wf) == []
    assert analyze_workflow_semantics(wf, DEFAULT_SEMANTIC_SEVERITIES) == []


def test_default_severities_all_off():
    assert set(DEFAULT_SEMANTIC_SEVERITIES.values()) == {"off"}


# ---------------------------------------------------------------------------
# R1 — order quantity bound to AIAgent response
# ---------------------------------------------------------------------------

def _ai_to_order_wf(qty_expr="{{ nodes.agent.response }}"):
    return {"nodes": [
        {"id": "agent", "type": "AIAgentNode", "output_format": "text"},
        {"id": "ord", "type": "OverseasStockNewOrderNode",
         "order": {"symbol": "AAPL", "quantity": qty_expr}},
    ], "edges": []}


def test_r1_strict_rejects_ai_bound_quantity():
    infos = analyze_workflow_semantics(_ai_to_order_wf(), STRICT_SEMANTIC_SEVERITIES)
    r1 = [i for i in infos if str(i.code) == "SEMANTIC_ORDER_QTY_FROM_AI"]
    assert len(r1) == 1
    e = r1[0]
    assert str(e.severity) == "error"
    assert e.location.node_id == "ord"
    assert e.location.field_path == "order.quantity"
    assert e.details.get("ai_node_id") == "agent"
    # Korean beginner guidance (clarity rule).
    assert "PositionSizingNode" in e.suggestion


def test_r1_not_fired_when_quantity_from_position_sizing():
    # The canonical-safe shape: order bound to a PositionSizingNode output.
    wf = {"nodes": [
        {"id": "agent", "type": "AIAgentNode", "output_format": "text"},
        {"id": "sizing", "type": "PositionSizingNode"},
        {"id": "ord", "type": "OverseasStockNewOrderNode",
         "order": "{{ nodes.sizing.order }}"},
    ], "edges": []}
    assert not _has(analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES),
                    "SEMANTIC_ORDER_QTY_FROM_AI")


def test_r1_whole_order_bound_to_ai_is_caught():
    wf = {"nodes": [
        {"id": "agent", "type": "AIAgentNode"},
        {"id": "ord", "type": "OverseasStockNewOrderNode",
         "order": "{{ nodes.agent.response }}"},
    ], "edges": []}
    assert _has(analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES),
                "SEMANTIC_ORDER_QTY_FROM_AI")


def test_r1_partial_config_enables_only_r1():
    # Only R1 enabled → a hardcoded-quantity sibling does NOT produce R3.
    wf = {"nodes": [
        {"id": "agent", "type": "AIAgentNode"},
        {"id": "ord", "type": "OverseasStockNewOrderNode",
         "order": {"quantity": "{{ nodes.agent.response }}"}},
    ], "edges": []}
    infos = analyze_workflow_semantics(wf, {RULE_ORDER_QTY_FROM_AI: "error"})
    assert _codes(infos) == ["SEMANTIC_ORDER_QTY_FROM_AI"]


def test_r1_severity_override_to_warning():
    infos = analyze_workflow_semantics(_ai_to_order_wf(), {RULE_ORDER_QTY_FROM_AI: "warning"})
    assert infos and str(infos[0].severity) == "warning"


# ---------------------------------------------------------------------------
# R2 — structured output with no schema
# ---------------------------------------------------------------------------

def test_r2_structured_no_schema_rejected():
    wf = {"nodes": [{"id": "a", "type": "AIAgentNode", "output_format": "structured"}], "edges": []}
    infos = analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES)
    assert _has(infos, "SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA")


def test_r2_guarded_by_preset():
    wf = {"nodes": [{"id": "a", "type": "AIAgentNode", "output_format": "structured",
                     "preset": "risk_manager"}], "edges": []}
    assert not _has(analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES),
                    "SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA")


def test_r2_guarded_by_schema():
    wf = {"nodes": [{"id": "a", "type": "AIAgentNode", "output_format": "structured",
                     "output_schema": {"signal": {"type": "string"}}}], "edges": []}
    assert not _has(analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES),
                    "SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA")


def test_r2_text_format_not_flagged():
    wf = {"nodes": [{"id": "a", "type": "AIAgentNode", "output_format": "text"}], "edges": []}
    assert not _has(analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES),
                    "SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA")


# ---------------------------------------------------------------------------
# R3 — hardcoded quantity / R4 — ignored broker field
# ---------------------------------------------------------------------------

def test_r3_hardcoded_quantity_warns():
    wf = {"nodes": [{"id": "o", "type": "OverseasStockNewOrderNode",
                     "order": {"symbol": "AAPL", "quantity": 5}}], "edges": []}
    infos = analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES)
    r3 = [i for i in infos if str(i.code) == "SEMANTIC_HARDCODED_ORDER_QTY"]
    assert len(r3) == 1 and str(r3[0].severity) == "warning"
    assert r3[0].details.get("quantity") == 5


def test_r3_suppressed_when_position_sizing_present():
    wf = {"nodes": [
        {"id": "ps", "type": "PositionSizingNode"},
        {"id": "o", "type": "OverseasStockNewOrderNode",
         "order": {"symbol": "AAPL", "quantity": 5}},
    ], "edges": []}
    assert not _has(analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES),
                    "SEMANTIC_HARDCODED_ORDER_QTY")


def test_r3_bool_quantity_not_treated_as_int():
    # bool is an int subclass — must not be flagged as a hardcoded quantity.
    wf = {"nodes": [{"id": "o", "type": "OverseasStockNewOrderNode",
                     "order": {"quantity": True}}], "edges": []}
    assert not _has(analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES),
                    "SEMANTIC_HARDCODED_ORDER_QTY")


def test_r4_ignored_paper_trading_field_warns():
    wf = {"nodes": [
        {"id": "ps", "type": "PositionSizingNode"},
        {"id": "o", "type": "OverseasStockNewOrderNode",
         "order": {"quantity": 5}, "paper_trading": True},
    ], "edges": []}
    infos = analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES)
    r4 = [i for i in infos if str(i.code) == "SEMANTIC_ORDER_IGNORED_FIELD"]
    assert len(r4) == 1 and str(r4[0].severity) == "warning"
    assert r4[0].location.field_path == "paper_trading"


def test_r4_paper_trading_on_broker_node_not_flagged():
    # paper_trading is legitimate on a broker node — never flagged there.
    wf = {"nodes": [{"id": "broker", "type": "OverseasStockBrokerNode",
                     "credential_id": "c", "paper_trading": False}], "edges": []}
    assert not _has(analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES),
                    "SEMANTIC_ORDER_IGNORED_FIELD")


# ---------------------------------------------------------------------------
# Robustness / config normalization
# ---------------------------------------------------------------------------

def test_never_raises_on_malformed_dsl():
    for bad in [None, {}, {"nodes": None}, {"nodes": [None, 1, "x"]},
                {"nodes": [{"id": ["unhashable"], "type": {"bad": 1}}]}]:
        assert analyze_workflow_semantics(bad, STRICT_SEMANTIC_SEVERITIES) == []


def test_normalize_severities_merges_over_off():
    merged = normalize_severities({RULE_HARDCODED_ORDER_QTY: "error"})
    assert merged[RULE_HARDCODED_ORDER_QTY] == "error"
    assert merged[RULE_ORDER_QTY_FROM_AI] == "off"


def test_normalize_severities_ignores_unknown_and_invalid():
    merged = normalize_severities({"bogus_rule": "error", RULE_ORDER_IGNORED_FIELD: "loud"})
    assert "bogus_rule" not in merged
    assert merged[RULE_ORDER_IGNORED_FIELD] == "off"  # invalid value ignored


def test_unknown_node_type_is_neither_order_nor_ai():
    wf = {"nodes": [{"id": "x", "type": "TotallyMadeUpNode",
                     "order": {"quantity": "{{ nodes.x.response }}"}}], "edges": []}
    assert analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES) == []


# ---------------------------------------------------------------------------
# deep_validate integration
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pg():
    return ProgramGarden()


@pytest.fixture(scope="module")
def ai_autotrade_def():
    path = os.path.join(EXAMPLES_DIR, "86-ai-news-sentiment-auto-trade.json")
    with open(path) as fh:
        return json.load(fh)


def test_deep_validate_default_has_no_semantic_codes(pg, ai_autotrade_def):
    r = pg.validate_deep(ai_autotrade_def, timeout=40)
    assert not any(str(e.code).startswith("SEMANTIC")
                   for e in list(r.errors) + list(r.warnings))


def test_deep_validate_strict_keeps_canonical_safe_pattern_valid(pg, ai_autotrade_def):
    # 86 routes AI → IfNode → PositionSizing → order: must NOT trip R1.
    r = pg.validate_deep(ai_autotrade_def, semantic_rules=STRICT_SEMANTIC_SEVERITIES, timeout=40)
    assert not any(str(e.code) == "SEMANTIC_ORDER_QTY_FROM_AI" for e in r.errors)


def test_deep_validate_strict_rejects_ai_to_order_probe(pg, ai_autotrade_def):
    probe = copy.deepcopy(ai_autotrade_def)
    for n in probe["nodes"]:
        if n.get("id") == "buy_order":
            n["order"] = {"symbol": "{{ item.symbol }}",
                          "quantity": "{{ nodes.sentiment_agent.response }}", "price": 0}
    r = pg.validate_deep(probe, semantic_rules=STRICT_SEMANTIC_SEVERITIES, timeout=40)
    assert not r.is_valid
    assert any(str(e.code) == "SEMANTIC_ORDER_QTY_FROM_AI" for e in r.errors)
    # Default pass over the same probe introduces no semantic code (opt-in only).
    rd = pg.validate_deep(probe, timeout=40)
    assert not any(str(e.code).startswith("SEMANTIC")
                   for e in list(rd.errors) + list(rd.warnings))


# ---------------------------------------------------------------------------
# 86-example corpus — false-reject 0 under strict
# ---------------------------------------------------------------------------

_EXAMPLE_FILES = sorted(glob.glob(os.path.join(EXAMPLES_DIR, "*.json")))


@pytest.mark.parametrize("wf_path", _EXAMPLE_FILES,
                         ids=[os.path.basename(p) for p in _EXAMPLE_FILES])
def test_corpus_zero_strict_errors(wf_path):
    """No shipped example produces an error-severity (blocking) semantic finding."""
    with open(wf_path) as fh:
        d = json.load(fh)
    infos = analyze_workflow_semantics(d, STRICT_SEMANTIC_SEVERITIES)
    blocking = [str(i.code) for i in infos if str(i.severity) == "error"]
    assert blocking == [], f"{os.path.basename(wf_path)} false-rejected: {blocking}"
