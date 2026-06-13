"""Phase 1 unit tests for src/core/programgarden_core/models/validation.py.

Covers ErrorInfo / ErrorLocation / ErrorCode / Recommendation /
ValidationLimits / ResultSummary / ValidationResult shape, plus the
build_error helper and suggest_close_match utility. Cascade suppression
behavior itself is exercised in Phase 4 / 5 — here we only verify the
rule data table is well-formed.
"""
from __future__ import annotations

import json

import pytest

from programgarden_core import (
    CASCADE_SUPPRESSION_RULES,
    ErrorCode,
    ErrorInfo,
    ErrorLocation,
    ErrorSeverity,
    Recommendation,
    RecommendationCategory,
    ResultSummary,
    ValidationLimits,
    ValidationResult,
    build_error,
    default_severity_for,
    suggest_close_match,
)


# ---------------------------------------------------------------------------
# ErrorCode / ErrorSeverity
# ---------------------------------------------------------------------------


def test_error_code_count_matches_matrix() -> None:
    # 26 baseline + 3 AI/Dynamic edge codes (INVALID_AI_MODEL_EDGE,
    # INVALID_TOOL_EDGE, DYNAMIC_NODE_CLASS_NOT_INJECTED) = 29 codes,
    # + 3 deep_validate codes (DEEP_VALIDATION_NODE_ERROR,
    # DEEP_VALIDATION_FLOW_BROKEN, DEEP_VALIDATION_BINDING_UNRESOLVED) = 32,
    # + 4 semantic/safety layer codes (SEMANTIC_ORDER_QTY_FROM_AI,
    # SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA, SEMANTIC_HARDCODED_ORDER_QTY,
    # SEMANTIC_ORDER_IGNORED_FIELD) = 36.
    assert len(list(ErrorCode)) == 36


def test_unknown_plugin_defaults_to_warning() -> None:
    assert default_severity_for(ErrorCode.UNKNOWN_PLUGIN) == ErrorSeverity.WARNING


# Codes whose default severity is WARNING (advisory), not ERROR.
_WARNING_DEFAULT_CODES = {
    ErrorCode.UNKNOWN_PLUGIN,
    ErrorCode.SEMANTIC_HARDCODED_ORDER_QTY,   # R3 — advisory
    ErrorCode.SEMANTIC_ORDER_IGNORED_FIELD,   # R4 — advisory
}


def test_semantic_default_severities() -> None:
    # R1/R2 are blocking anti-patterns; R3/R4 are advisory.
    assert default_severity_for(ErrorCode.SEMANTIC_ORDER_QTY_FROM_AI) == ErrorSeverity.ERROR
    assert default_severity_for(ErrorCode.SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA) == ErrorSeverity.ERROR
    assert default_severity_for(ErrorCode.SEMANTIC_HARDCODED_ORDER_QTY) == ErrorSeverity.WARNING
    assert default_severity_for(ErrorCode.SEMANTIC_ORDER_IGNORED_FIELD) == ErrorSeverity.WARNING


def test_other_codes_default_to_error() -> None:
    for code in ErrorCode:
        if code in _WARNING_DEFAULT_CODES:
            continue
        assert default_severity_for(code) == ErrorSeverity.ERROR


# ---------------------------------------------------------------------------
# ErrorLocation
# ---------------------------------------------------------------------------


def test_error_location_all_fields_optional() -> None:
    loc = ErrorLocation()
    assert loc.node_id is None
    assert loc.field_path is None


def test_error_location_extra_forbidden() -> None:
    with pytest.raises(Exception):
        ErrorLocation(unknown_field="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# ErrorInfo
# ---------------------------------------------------------------------------


def test_error_info_short_with_node_and_field() -> None:
    info = ErrorInfo(
        code=ErrorCode.INVALID_EXPRESSION_REF,
        location=ErrorLocation(node_id="rsi1", field_path="data"),
        message="Reference 'nodes.missing' not found",
    )
    assert info.short() == (
        "[INVALID_EXPRESSION_REF] Reference 'nodes.missing' not found "
        "(node=rsi1, field=data)"
    )


def test_error_info_short_with_edge_only() -> None:
    info = ErrorInfo(
        code=ErrorCode.INVALID_EDGE_REF,
        location=ErrorLocation(edge_index=4),
        message="Edge target 'ghost' is not defined",
    )
    assert info.short() == "[INVALID_EDGE_REF] Edge target 'ghost' is not defined (edge[4])"


def test_error_info_short_without_location() -> None:
    info = ErrorInfo(
        code=ErrorCode.MISSING_START_NODE,
        message="Workflow has no StartNode",
    )
    assert info.short() == "[MISSING_START_NODE] Workflow has no StartNode"


def test_error_info_json_roundtrip_preserves_code_and_severity() -> None:
    info = build_error(
        ErrorCode.UNKNOWN_NODE_TYPE,
        "Unknown node type 'OverseasFoo'",
        location=ErrorLocation(node_id="x1", node_type="OverseasFoo"),
        suggestion="Did you mean OverseasStockBrokerNode?",
        available_values=["OverseasStockBrokerNode", "OverseasFuturesBrokerNode"],
    )
    blob = info.model_dump_json()
    payload = json.loads(blob)
    assert payload["code"] == "UNKNOWN_NODE_TYPE"
    assert payload["severity"] == "error"
    assert payload["available_values"][0] == "OverseasStockBrokerNode"


def test_build_error_warning_severity_via_default_table() -> None:
    info = build_error(ErrorCode.UNKNOWN_PLUGIN, "Plugin 'RSIv2' not registered")
    assert info.severity == ErrorSeverity.WARNING.value


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


def test_recommendation_short_format() -> None:
    rec = Recommendation(
        title="Consider enabling retry for external API nodes",
        rationale="Transient network failures otherwise crash the workflow.",
        category=RecommendationCategory.RESILIENCE,
        options=[
            "Set resilience.retry.enabled=true",
            "Configure resilience.fallback.mode='skip'",
        ],
        rule_id="REC_EXTERNAL_API_RESILIENCE",
    )
    line = rec.short()
    assert line.startswith("[REC_EXTERNAL_API_RESILIENCE]")
    assert "retry" in line


def test_recommendation_example_snippet_is_partial_fragment() -> None:
    rec = Recommendation(
        title="Consider inserting a guard between realtime data and order nodes",
        rationale="Direct realtime->order connections amplify duplicate-order risk.",
        category=RecommendationCategory.SAFETY,
        options=["Insert ThrottleNode", "Insert ConditionNode"],
        example_snippet={"nodes": [{"id": "throttle1", "type": "ThrottleNode", "interval_seconds": 1.0}]},
        rule_id="REC_REALTIME_THROTTLE",
    )
    assert rec.example_snippet is not None
    assert "edges" not in rec.example_snippet  # partial: just the new node
    assert rec.example_snippet["nodes"][0]["type"] == "ThrottleNode"


# ---------------------------------------------------------------------------
# ValidationLimits / ResultSummary
# ---------------------------------------------------------------------------


def test_validation_limits_defaults() -> None:
    limits = ValidationLimits()
    assert limits.max_errors == 20
    assert limits.max_warnings == 10
    assert limits.max_recommendations_per_channel == 10
    assert limits.max_per_node == 3


def test_validation_limits_rejects_unknown_field() -> None:
    with pytest.raises(Exception):
        ValidationLimits(max_critical=5)  # type: ignore[call-arg]


def test_result_summary_defaults_to_empty() -> None:
    s = ResultSummary(is_valid=True)
    assert s.error_count == 0
    assert s.critical_codes == []
    assert s.next_action_hint is None
    assert s.truncated is False


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


def test_validation_result_add_routes_by_severity() -> None:
    result = ValidationResult()
    err = build_error(ErrorCode.CYCLE_DETECTED, "Cycle detected: A -> B -> A")
    warn = build_error(ErrorCode.UNKNOWN_PLUGIN, "Plugin 'foo' not registered")
    result.add(err)
    result.add(warn)
    assert len(result.errors) == 1
    assert len(result.warnings) == 1
    assert result.is_valid is False


def test_validation_result_is_valid_when_only_warnings() -> None:
    result = ValidationResult()
    result.add(build_error(ErrorCode.UNKNOWN_PLUGIN, "Plugin 'foo' not registered"))
    assert result.is_valid is True


def test_validation_result_channels_are_independent() -> None:
    result = ValidationResult()
    static_rec = Recommendation(
        title="Consider deriving order quantity from account state",
        rationale="Hardcoded quantities miss account-based sizing.",
        category=RecommendationCategory.DATA_FLOW,
        options=["Insert PositionSizingNode", "Compute via expression"],
        rule_id="REC_POSITION_SIZING_MISSING",
    )
    runtime_rec = Recommendation(
        title="Symbol list is empty at runtime",
        rationale="Downstream consumers will skip iterations.",
        category=RecommendationCategory.DATA_FLOW,
        options=["Populate via WatchlistNode", "Populate via MarketUniverseNode"],
        rule_id="REC_EMPTY_SYMBOL_LIST",
    )
    result.add_static_recommendation(static_rec)
    result.add_runtime_recommendation(runtime_rec)
    assert len(result.static_recommendations) == 1
    assert len(result.runtime_recommendations) == 1
    merged = result.all_recommendations()
    assert len(merged) == 2
    assert {r.rule_id for r in merged} == {"REC_POSITION_SIZING_MISSING", "REC_EMPTY_SYMBOL_LIST"}


def test_validation_result_as_strings_includes_all_lines() -> None:
    result = ValidationResult()
    result.add(build_error(ErrorCode.MISSING_START_NODE, "Workflow has no StartNode"))
    result.add(build_error(ErrorCode.UNKNOWN_PLUGIN, "Plugin 'foo' not registered"))
    result.add_static_recommendation(
        Recommendation(
            title="Consider enabling retry for external API nodes",
            rationale="Transient failures will otherwise propagate.",
            category=RecommendationCategory.RESILIENCE,
            options=["Set retry.enabled=true", "Use fallback.mode='skip'"],
            rule_id="REC_EXTERNAL_API_RESILIENCE",
        )
    )
    lines = result.as_strings()
    assert any(l.startswith("[MISSING_START_NODE]") for l in lines)
    assert any(l.startswith("[UNKNOWN_PLUGIN]") for l in lines)
    assert any(l.startswith("[REC_EXTERNAL_API_RESILIENCE]") for l in lines)


def test_validation_result_json_roundtrip_includes_both_channels() -> None:
    result = ValidationResult()
    result.add(build_error(ErrorCode.MISSING_START_NODE, "Workflow has no StartNode"))
    result.add_static_recommendation(
        Recommendation(
            title="Consider deriving order quantity from account state",
            rationale="Hardcoded quantities miss account-based sizing.",
            category=RecommendationCategory.DATA_FLOW,
            options=["Insert PositionSizingNode", "Compute via expression"],
            rule_id="REC_POSITION_SIZING_MISSING",
        )
    )
    payload = json.loads(result.model_dump_json())
    assert payload["errors"][0]["code"] == "MISSING_START_NODE"
    assert payload["static_recommendations"][0]["rule_id"] == "REC_POSITION_SIZING_MISSING"
    assert payload["runtime_recommendations"] == []


# ---------------------------------------------------------------------------
# suggest_close_match
# ---------------------------------------------------------------------------


def test_suggest_close_match_returns_top_n() -> None:
    candidates = [
        "OverseasStockBrokerNode",
        "OverseasFuturesBrokerNode",
        "KoreaStockBrokerNode",
        "ThrottleNode",
    ]
    matches = suggest_close_match("OverseasStokBrokerNode", candidates, n=2)
    assert matches is not None
    assert matches[0] == "OverseasStockBrokerNode"
    assert len(matches) <= 2


def test_suggest_close_match_returns_none_on_no_match() -> None:
    assert suggest_close_match("zzzzzzz", ["OverseasStockBrokerNode"]) is None


# ---------------------------------------------------------------------------
# Cascade rule data
# ---------------------------------------------------------------------------


def test_cascade_suppression_rules_cover_four_root_codes() -> None:
    assert set(CASCADE_SUPPRESSION_RULES.keys()) == {
        ErrorCode.UNKNOWN_NODE_TYPE,
        ErrorCode.MISSING_REQUIRED_BROKER,
        ErrorCode.CYCLE_DETECTED,
        ErrorCode.DUPLICATE_NODE_ID,
    }
    for description in CASCADE_SUPPRESSION_RULES.values():
        assert description and isinstance(description, str)
