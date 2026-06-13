"""Structured validation errors for AI-chatbot-friendly workflow validation.

ErrorInfo objects let downstream consumers (AI chatbots, IDEs, dashboards)
make deterministic self-correction decisions based on error codes and
structured location metadata instead of parsing free-form strings.

All user-facing strings in this module (and all consumers) must be English.
"""
from __future__ import annotations

from difflib import get_close_matches
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ErrorSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class ErrorCode(str, Enum):
    # Definition / structure
    DEFINITION_PARSE_ERROR = "DEFINITION_PARSE_ERROR"
    DUPLICATE_NODE_ID = "DUPLICATE_NODE_ID"
    RESERVED_NODE_ID = "RESERVED_NODE_ID"
    MISSING_START_NODE = "MISSING_START_NODE"
    MULTIPLE_START_NODES = "MULTIPLE_START_NODES"
    CYCLE_DETECTED = "CYCLE_DETECTED"

    # Node / plugin registry
    UNKNOWN_NODE_TYPE = "UNKNOWN_NODE_TYPE"
    UNKNOWN_DYNAMIC_NODE_SCHEMA = "UNKNOWN_DYNAMIC_NODE_SCHEMA"
    DYNAMIC_NODE_CREDENTIAL_FORBIDDEN = "DYNAMIC_NODE_CREDENTIAL_FORBIDDEN"
    DYNAMIC_NODE_CLASS_NOT_INJECTED = "DYNAMIC_NODE_CLASS_NOT_INJECTED"
    MISSING_PLUGIN = "MISSING_PLUGIN"
    UNKNOWN_PLUGIN = "UNKNOWN_PLUGIN"

    # Edges
    INVALID_EDGE_REF = "INVALID_EDGE_REF"
    INVALID_EDGE_PORT = "INVALID_EDGE_PORT"
    INVALID_AI_MODEL_EDGE = "INVALID_AI_MODEL_EDGE"
    INVALID_TOOL_EDGE = "INVALID_TOOL_EDGE"

    # Expressions / fields
    INVALID_EXPRESSION_REF = "INVALID_EXPRESSION_REF"
    INVALID_EXPRESSION_SYNTAX = "INVALID_EXPRESSION_SYNTAX"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FIELD_TYPE = "INVALID_FIELD_TYPE"
    INVALID_FIELD_ENUM = "INVALID_FIELD_ENUM"

    # Credentials
    UNKNOWN_CREDENTIAL = "UNKNOWN_CREDENTIAL"

    # Broker / connection rules
    DUPLICATE_BROKER_NODE = "DUPLICATE_BROKER_NODE"
    MISSING_REQUIRED_BROKER = "MISSING_REQUIRED_BROKER"
    INCOMPATIBLE_BROKER_PROVIDER = "INCOMPATIBLE_BROKER_PROVIDER"
    CONNECTION_RULE_VIOLATION = "CONNECTION_RULE_VIOLATION"

    # Runtime (dry_run)
    DRY_RUN_RUNTIME_ERROR = "DRY_RUN_RUNTIME_ERROR"
    DRY_RUN_CREDENTIAL_MISSING = "DRY_RUN_CREDENTIAL_MISSING"
    DRY_RUN_DEPENDENCY_FAILURE = "DRY_RUN_DEPENDENCY_FAILURE"

    # Deep validation (virtual full-execution / deep_validate)
    DEEP_VALIDATION_NODE_ERROR = "DEEP_VALIDATION_NODE_ERROR"
    DEEP_VALIDATION_FLOW_BROKEN = "DEEP_VALIDATION_FLOW_BROKEN"
    DEEP_VALIDATION_BINDING_UNRESOLVED = "DEEP_VALIDATION_BINDING_UNRESOLVED"

    # Semantic / safety layer (deep_validate configurable rules — R1~R4).
    # These are intent/safety checks that structure + dry_run + type validation
    # cannot express; they are OFF by default and opted into per-rule severity by
    # the caller (e.g. the chatbot save chokepoint). See programgarden.semantic_rules.
    SEMANTIC_ORDER_QTY_FROM_AI = "SEMANTIC_ORDER_QTY_FROM_AI"                    # R1
    SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA = "SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA"  # R2
    SEMANTIC_HARDCODED_ORDER_QTY = "SEMANTIC_HARDCODED_ORDER_QTY"                # R3
    SEMANTIC_ORDER_IGNORED_FIELD = "SEMANTIC_ORDER_IGNORED_FIELD"               # R4


_DEFAULT_SEVERITY: Dict[ErrorCode, ErrorSeverity] = {
    ErrorCode.UNKNOWN_PLUGIN: ErrorSeverity.WARNING,
    # Semantic layer default severities (when a rule is enabled without an
    # explicit severity). R1/R2 are blocking anti-patterns; R3/R4 are advisory.
    ErrorCode.SEMANTIC_ORDER_QTY_FROM_AI: ErrorSeverity.ERROR,
    ErrorCode.SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA: ErrorSeverity.ERROR,
    ErrorCode.SEMANTIC_HARDCODED_ORDER_QTY: ErrorSeverity.WARNING,
    ErrorCode.SEMANTIC_ORDER_IGNORED_FIELD: ErrorSeverity.WARNING,
}


def default_severity_for(code: ErrorCode) -> ErrorSeverity:
    return _DEFAULT_SEVERITY.get(code, ErrorSeverity.ERROR)


class ErrorLocation(BaseModel):
    """Where in the workflow definition the error occurred. All fields optional."""

    node_id: Optional[str] = Field(default=None, description="Node id from definition.nodes[].id")
    node_type: Optional[str] = Field(default=None, description="Node type (e.g. 'OverseasStockNewOrderNode')")
    field_path: Optional[str] = Field(default=None, description="Dot/bracket notation: 'fields.period' or 'symbols[0].symbol'")
    edge_index: Optional[int] = Field(default=None, description="Index into definition.edges[]")
    edge_from: Optional[str] = Field(default=None, description="Edge.from raw value (may include dot port)")
    edge_to: Optional[str] = Field(default=None, description="Edge.to raw value")
    credential_id: Optional[str] = Field(default=None, description="Credential id from definition.credentials[]")
    plugin_id: Optional[str] = Field(default=None, description="Plugin id referenced by ConditionNode etc.")
    expression: Optional[str] = Field(default=None, description="Raw expression string when INVALID_EXPRESSION_*")
    output_port: Optional[str] = Field(default=None, description="Output port name on source node")

    model_config = ConfigDict(extra="forbid")


class RecommendationCategory(str, Enum):
    DATA_FLOW = "data_flow"
    RESILIENCE = "resilience"
    PERFORMANCE = "performance"
    SAFETY = "safety"
    READABILITY = "readability"


class Recommendation(BaseModel):
    """Non-blocking quality-improvement hint for AI chatbots and users.

    Recommendations are deterministic, rule-based suggestions — never prescribe
    a single fixed value. Always present options with rationale so the
    consumer (chatbot or human) can pick the right one for their context.

    `example_snippet` is a partial workflow fragment (one or two
    nodes/edges) showing one applied option — not a full workflow JSON. The
    chatbot is expected to merge it into the user's existing workflow.
    """
    title: str = Field(description="Short one-line hint (English). Use 'Consider X' tone.")
    rationale: str = Field(description="Why this may improve the workflow — 1~2 sentences.")
    category: RecommendationCategory
    location: Optional[ErrorLocation] = Field(default=None, description="Optional anchor point in the workflow")
    options: List[str] = Field(default_factory=list, description="2+ alternative approaches the user/AI may pick from")
    example_snippet: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Partial workflow JSON showing one applied option (node/edge fragment only — not a full workflow)",
    )
    rule_id: str = Field(description="Deterministic rule identifier for testing / suppression (e.g. 'REC_REALTIME_THROTTLE')")

    model_config = ConfigDict(use_enum_values=True)

    def short(self) -> str:
        return f"[{self.rule_id}] {self.title} — {self.rationale}"


class ErrorInfo(BaseModel):
    code: ErrorCode
    severity: ErrorSeverity = Field(default=ErrorSeverity.ERROR)
    location: ErrorLocation = Field(default_factory=ErrorLocation)
    message: str = Field(description="Human-readable English message. One sentence preferred.")
    suggestion: Optional[str] = Field(default=None, description="Single-line English remediation hint.")
    available_values: Optional[List[str]] = Field(
        default=None,
        description="Closest valid candidates for enum/registry-style errors (suggest_close_match result).",
    )
    docs_url: Optional[str] = Field(default=None, description="Optional anchor link to documentation.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Free-form structured context.")
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="Optional improvement hints worth considering while fixing this error.",
    )

    model_config = ConfigDict(use_enum_values=True)

    def short(self) -> str:
        loc_parts: List[str] = []
        if self.location.node_id:
            loc_parts.append(f"node={self.location.node_id}")
        if self.location.field_path:
            loc_parts.append(f"field={self.location.field_path}")
        if self.location.edge_index is not None:
            loc_parts.append(f"edge[{self.location.edge_index}]")
        suffix = f" ({', '.join(loc_parts)})" if loc_parts else ""
        return f"[{self.code}] {self.message}{suffix}"


class ValidationLimits(BaseModel):
    """Output volume limits to prevent overwhelming LLM context."""

    max_errors: int = Field(default=20, ge=1)
    max_warnings: int = Field(default=10, ge=1)
    max_recommendations_per_channel: int = Field(default=10, ge=1)
    max_per_node: int = Field(default=3, ge=1)

    model_config = ConfigDict(extra="forbid")


class ResultSummary(BaseModel):
    """Top-level summary for fast LLM triage of a ValidationResult."""

    is_valid: bool
    error_count: int = 0
    warning_count: int = 0
    static_recommendation_count: int = 0
    runtime_recommendation_count: int = 0
    critical_codes: List[ErrorCode] = Field(
        default_factory=list,
        description="Up to 3 most-impactful codes (cascade roots first, then frequency).",
    )
    root_cause_node_ids: List[str] = Field(
        default_factory=list,
        description="Node ids that triggered cascade suppression (fix these first).",
    )
    next_action_hint: Optional[str] = Field(
        default=None,
        description="Deterministic English single-line hint for the consumer's next step.",
    )
    truncated: bool = Field(
        default=False,
        description="True if any channel hit ValidationLimits and entries were dropped.",
    )

    model_config = ConfigDict(use_enum_values=True)


class ValidationResult(BaseModel):
    """Structured validation outcome for a workflow definition.

    Two recommendation channels exist:
    - `static_recommendations`: filled by `executor.validate()` (topology
      analysis only)
    - `runtime_recommendations`: filled by `executor.execute(dry_run=True)`
      based on actual node mock outputs (e.g. REC_EMPTY_SYMBOL_LIST)
    """

    errors: List[ErrorInfo] = Field(default_factory=list)
    warnings: List[ErrorInfo] = Field(default_factory=list)
    static_recommendations: List[Recommendation] = Field(default_factory=list)
    runtime_recommendations: List[Recommendation] = Field(default_factory=list)
    summary: Optional[ResultSummary] = Field(
        default=None,
        description="Populated after post-processing (cascade suppression + capping). None until finalize() runs.",
    )
    truncated: Dict[str, int] = Field(
        default_factory=dict,
        description="Per-channel count of entries dropped by ValidationLimits (e.g. {'errors': 5}).",
    )

    model_config = ConfigDict(use_enum_values=True)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add(self, info: ErrorInfo) -> None:
        """Append an ErrorInfo into errors/warnings by severity."""
        if info.severity == ErrorSeverity.WARNING or info.severity == ErrorSeverity.WARNING.value:
            self.warnings.append(info)
        else:
            self.errors.append(info)

    def add_static_recommendation(self, rec: Recommendation) -> None:
        self.static_recommendations.append(rec)

    def add_runtime_recommendation(self, rec: Recommendation) -> None:
        self.runtime_recommendations.append(rec)

    def all_recommendations(self) -> List[Recommendation]:
        """Merge static + runtime channels (read-only helper for consumers that don't distinguish stages)."""
        return [*self.static_recommendations, *self.runtime_recommendations]

    def as_strings(self) -> List[str]:
        """Human-readable one-line per entry. Not a legacy compat shim — English-only."""
        lines: List[str] = []
        lines.extend(e.short() for e in self.errors)
        lines.extend(w.short() for w in self.warnings)
        lines.extend(r.short() for r in self.all_recommendations())
        return lines


def suggest_close_match(
    value: str,
    candidates: Iterable[str],
    cutoff: float = 0.6,
    n: int = 3,
) -> Optional[List[str]]:
    """Return up to `n` closest matches above `cutoff`, or None if there are no matches.

    Thin wrapper over `difflib.get_close_matches` with standardised defaults
    for ErrorInfo.available_values.
    """
    matches = get_close_matches(value, list(candidates), n=n, cutoff=cutoff)
    return matches or None


def build_error(
    code: ErrorCode,
    message: str,
    *,
    location: Optional[ErrorLocation] = None,
    suggestion: Optional[str] = None,
    available_values: Optional[List[str]] = None,
    details: Optional[Dict[str, Any]] = None,
    severity: Optional[ErrorSeverity] = None,
    recommendations: Optional[List[Recommendation]] = None,
) -> ErrorInfo:
    """DRY helper for resolver.py and dry_run capture sites."""
    return ErrorInfo(
        code=code,
        severity=severity or default_severity_for(code),
        location=location or ErrorLocation(),
        message=message,
        suggestion=suggestion,
        available_values=available_values,
        details=details or {},
        recommendations=recommendations or [],
    )


# Cascade suppression rule data — actual application lives in Phase 4 post-processing.
# Each entry documents which subordinate error codes a given root cause hides.
CASCADE_SUPPRESSION_RULES: Dict[ErrorCode, str] = {
    ErrorCode.UNKNOWN_NODE_TYPE: (
        "Suppresses INVALID_EXPRESSION_REF / INVALID_EDGE_REF / INVALID_EDGE_PORT "
        "where the source/target is the unknown node id."
    ),
    ErrorCode.MISSING_REQUIRED_BROKER: (
        "Suppresses additional MISSING_REQUIRED_BROKER entries with the same "
        "product_scope (keeps only the first)."
    ),
    ErrorCode.CYCLE_DETECTED: (
        "Suppresses any follow-on validation errors on nodes inside the cycle."
    ),
    ErrorCode.DUPLICATE_NODE_ID: (
        "Suppresses INVALID_EDGE_REF / INVALID_EXPRESSION_REF that reference the "
        "duplicated id (since id resolution is ambiguous)."
    ),
}


__all__ = [
    "ErrorSeverity",
    "ErrorCode",
    "ErrorLocation",
    "ErrorInfo",
    "RecommendationCategory",
    "Recommendation",
    "ValidationLimits",
    "ResultSummary",
    "ValidationResult",
    "CASCADE_SUPPRESSION_RULES",
    "default_severity_for",
    "suggest_close_match",
    "build_error",
]
