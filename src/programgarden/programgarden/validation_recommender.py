"""Workflow topology rule engine for non-blocking improvement recommendations.

Each rule is a pure function: same workflow + registry -> same recommendations
(deterministic, no LLM calls). Rules are split into two channels:

- **Static rules**: run as part of `WorkflowExecutor.validate()` (topology
  only — no execution needed).
- **Runtime rules**: run after `WorkflowExecutor.execute(dry_run=True)` and
  inspect dry-run JobState (e.g. empty symbol lists at runtime).

This module also exposes post-processing helpers (`apply_cascade_suppression`,
`apply_limits`, `build_summary`) which turn a raw ValidationResult into the
LLM-friendly output described in plan §5.6.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

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
    suggest_close_match,
)


# ---------------------------------------------------------------------------
# Node-type whitelists used by multiple rules
# ---------------------------------------------------------------------------

REALTIME_NODES: Set[str] = {
    "OverseasStockRealMarketDataNode",
    "OverseasFuturesRealMarketDataNode",
    "KoreaStockRealMarketDataNode",
    "OverseasStockRealAccountNode",
    "OverseasFuturesRealAccountNode",
    "KoreaStockRealAccountNode",
    "OverseasStockRealOrderEventNode",
    "OverseasFuturesRealOrderEventNode",
    "KoreaStockRealOrderEventNode",
}

ORDER_NODES: Set[str] = {
    "OverseasStockNewOrderNode",
    "OverseasFuturesNewOrderNode",
    "KoreaStockNewOrderNode",
    "OverseasStockModifyOrderNode",
    "OverseasFuturesModifyOrderNode",
    "KoreaStockModifyOrderNode",
    "OverseasStockCancelOrderNode",
    "OverseasFuturesCancelOrderNode",
    "KoreaStockCancelOrderNode",
}

ACCOUNT_NODES: Set[str] = {
    "OverseasStockAccountNode",
    "OverseasFuturesAccountNode",
    "KoreaStockAccountNode",
    "OverseasStockRealAccountNode",
    "OverseasFuturesRealAccountNode",
    "KoreaStockRealAccountNode",
}

EXTERNAL_API_NODES: Set[str] = {
    "HTTPRequestNode",
    "TelegramNode",
    "FundamentalDataNode",
    "FearGreedIndexNode",
}

AGGREGATE_NODES: Set[str] = {"AggregateNode", "FieldMappingNode", "ConditionNode", "SplitNode"}

SINGLE_VALUE_CONSUMER_NODES: Set[str] = {
    "TableDisplayNode",
    "LineChartNode",
    "MultiLineChartNode",
    "CandlestickChartNode",
    "BarChartNode",
    "SummaryDisplayNode",
}


# ---------------------------------------------------------------------------
# Workflow helpers (operate on the dict-based shape produced by WorkflowDefinition)
# ---------------------------------------------------------------------------


def _nodes_by_id(workflow) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for n in workflow.nodes:
        nid = n.get("id") if isinstance(n, dict) else getattr(n, "id", None)
        if nid:
            out[nid] = n if isinstance(n, dict) else dict(n)
    return out


def _node_type(node: Dict[str, Any]) -> Optional[str]:
    return node.get("type") if node else None


def _resilience_retry_enabled(node: Dict[str, Any]) -> Optional[bool]:
    res = node.get("resilience") if node else None
    if not isinstance(res, dict):
        return None
    retry = res.get("retry") if isinstance(res, dict) else None
    if isinstance(retry, dict):
        return bool(retry.get("enabled"))
    return None


# ---------------------------------------------------------------------------
# Static rules (8) — run during validate()
# ---------------------------------------------------------------------------


def check_realtime_throttle(workflow, registry) -> List[Recommendation]:
    """REC_REALTIME_THROTTLE — realtime market data feeding directly into order nodes."""
    nodes = _nodes_by_id(workflow)
    out: List[Recommendation] = []
    for idx, edge in enumerate(workflow.edges):
        src = nodes.get(edge.from_node_id)
        dst = nodes.get(edge.to_node_id)
        if not src or not dst:
            continue
        if _node_type(src) in REALTIME_NODES and _node_type(dst) in ORDER_NODES:
            out.append(
                Recommendation(
                    rule_id="REC_REALTIME_THROTTLE",
                    category=RecommendationCategory.SAFETY,
                    title="Consider inserting a guard between realtime data and order nodes",
                    rationale=(
                        "Realtime market data ticks at high frequency. Direct connection to an "
                        "order node may trigger duplicate or excessive orders before broker "
                        "rate limits engage."
                    ),
                    location=ErrorLocation(
                        node_id=edge.to_node_id,
                        node_type=_node_type(dst),
                        edge_index=idx,
                        edge_from=edge.from_node_id,
                        edge_to=edge.to_node_id,
                    ),
                    options=[
                        "Insert ThrottleNode between the realtime source and the order node",
                        "Insert ConditionNode to gate orders by strategy logic",
                        "Switch to ScheduleNode for periodic order evaluation",
                    ],
                    example_snippet={
                        "nodes": [{"id": "throttle1", "type": "ThrottleNode", "interval_seconds": 1.0}],
                    },
                )
            )
    return out


def check_external_api_resilience(workflow, registry) -> List[Recommendation]:
    """REC_EXTERNAL_API_RESILIENCE — external API nodes without retry."""
    out: List[Recommendation] = []
    for node in workflow.nodes:
        if not isinstance(node, dict):
            node = dict(node)
        if _node_type(node) not in EXTERNAL_API_NODES:
            continue
        if _resilience_retry_enabled(node) is False or "resilience" not in node:
            out.append(
                Recommendation(
                    rule_id="REC_EXTERNAL_API_RESILIENCE",
                    category=RecommendationCategory.RESILIENCE,
                    title="Consider enabling retry for external API nodes",
                    rationale=(
                        "Transient network failures will otherwise propagate as workflow errors. "
                        "Retry with backoff or a safe fallback usually preserves the run."
                    ),
                    location=ErrorLocation(node_id=node.get("id"), node_type=_node_type(node)),
                    options=[
                        "Set resilience.retry.enabled=true",
                        "Configure resilience.fallback.mode='skip'",
                        "Configure resilience.fallback.mode='default_value' with a sane default",
                    ],
                    example_snippet={
                        "resilience": {"retry": {"enabled": True, "max_retries": 3}},
                    },
                )
            )
    return out


def check_order_retry_risk(workflow, registry) -> List[Recommendation]:
    """REC_ORDER_RETRY_RISK — order nodes with retry enabled (duplicate-order risk)."""
    out: List[Recommendation] = []
    for node in workflow.nodes:
        if not isinstance(node, dict):
            node = dict(node)
        if _node_type(node) not in ORDER_NODES:
            continue
        if _resilience_retry_enabled(node) is True:
            out.append(
                Recommendation(
                    rule_id="REC_ORDER_RETRY_RISK",
                    category=RecommendationCategory.SAFETY,
                    title="Retry on order nodes may cause duplicate orders",
                    rationale=(
                        "Order endpoints are typically not idempotent. Retry can re-submit the "
                        "same order if the original succeeded but the response was lost."
                    ),
                    location=ErrorLocation(node_id=node.get("id"), node_type=_node_type(node)),
                    options=[
                        "Disable retry on order nodes (resilience.retry.enabled=false)",
                        "Use resilience.fallback.mode='skip' instead of retry",
                        "Introduce an idempotency_key on the order payload",
                    ],
                    example_snippet={
                        "resilience": {"retry": {"enabled": False}, "fallback": {"mode": "skip"}},
                    },
                )
            )
    return out


def check_position_sizing_missing(workflow, registry) -> List[Recommendation]:
    """REC_POSITION_SIZING_MISSING — account -> order path without PositionSizingNode."""
    nodes = _nodes_by_id(workflow)
    has_position_sizing = any(_node_type(n) == "PositionSizingNode" for n in nodes.values())
    if has_position_sizing:
        return []

    # Build forward adjacency for shallow reachability check (account -> order).
    adj: Dict[str, List[str]] = {nid: [] for nid in nodes}
    for edge in workflow.edges:
        if edge.from_node_id in adj:
            adj[edge.from_node_id].append(edge.to_node_id)

    out: List[Recommendation] = []
    emitted_for_node: Set[str] = set()
    for nid, node in nodes.items():
        if _node_type(node) not in ACCOUNT_NODES:
            continue
        visited: Set[str] = set()
        stack: List[str] = list(adj.get(nid, []))
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            if _node_type(nodes.get(cur, {})) in ORDER_NODES and cur not in emitted_for_node:
                emitted_for_node.add(cur)
                out.append(
                    Recommendation(
                        rule_id="REC_POSITION_SIZING_MISSING",
                        category=RecommendationCategory.DATA_FLOW,
                        title="Consider deriving order quantity from account state",
                        rationale=(
                            "An account node feeds an order node without a PositionSizingNode. "
                            "Hardcoded quantities ignore current balance and existing positions."
                        ),
                        location=ErrorLocation(node_id=cur, node_type=_node_type(nodes.get(cur))),
                        options=[
                            "Insert PositionSizingNode between the account and the order node",
                            "Compute quantity via expression on the order node's quantity field",
                        ],
                        example_snippet={
                            "nodes": [{"id": "sizing1", "type": "PositionSizingNode", "method": "fixed_pct"}],
                        },
                    )
                )
            stack.extend(adj.get(cur, []))
    return out


def check_large_symbol_list_batch(workflow, registry) -> List[Recommendation]:
    """REC_LARGE_SYMBOL_LIST_BATCH — symbol arrays > 50 without throttle/split."""
    out: List[Recommendation] = []
    has_throttle_or_split = any(
        _node_type(n) in {"ThrottleNode", "SplitNode"} for n in workflow.nodes if isinstance(n, dict)
    )
    if has_throttle_or_split:
        return []

    for node in workflow.nodes:
        if not isinstance(node, dict):
            continue
        for key in ("symbols", "symbol_list", "watchlist"):
            arr = node.get(key)
            if isinstance(arr, list) and len(arr) > 50:
                out.append(
                    Recommendation(
                        rule_id="REC_LARGE_SYMBOL_LIST_BATCH",
                        category=RecommendationCategory.PERFORMANCE,
                        title="Large symbol lists may hit rate limits without batching",
                        rationale=(
                            f"Node '{node.get('id')}' carries {len(arr)} symbols. Brokers often "
                            "throttle requests per second; batching avoids API rejection."
                        ),
                        location=ErrorLocation(node_id=node.get("id"), node_type=_node_type(node), field_path=key),
                        options=[
                            "Insert ThrottleNode to space out requests",
                            "Insert SplitNode to partition the symbol list",
                            "Reduce the universe via WatchlistNode filters",
                        ],
                        example_snippet={
                            "nodes": [{"id": "throttle1", "type": "ThrottleNode", "interval_seconds": 0.2}],
                        },
                    )
                )
                break  # one rec per node
    return out


def check_auto_iterate_aggregate_missing(workflow, registry) -> List[Recommendation]:
    """REC_AUTO_ITERATE_AGGREGATE_MISSING — array producer -> single-value consumer.

    Confidence model: only emit when (a) the upstream node is a known array
    producer (Account/Screener/Watchlist/MarketUniverse) AND (b) the
    downstream node is in `SINGLE_VALUE_CONSUMER_NODES` AND (c) no
    aggregator sits in between. Anything outside that envelope is skipped to
    keep false positives low (Codex review 🟡).
    """
    nodes = _nodes_by_id(workflow)
    array_producers = {
        "OverseasStockAccountNode",
        "OverseasFuturesAccountNode",
        "KoreaStockAccountNode",
        "ScreenerNode",
        "WatchlistNode",
        "MarketUniverseNode",
        "SymbolFilterNode",
        "ExclusionListNode",
    }
    out: List[Recommendation] = []
    for idx, edge in enumerate(workflow.edges):
        src = nodes.get(edge.from_node_id)
        dst = nodes.get(edge.to_node_id)
        if not src or not dst:
            continue
        if _node_type(src) not in array_producers:
            continue
        if _node_type(dst) not in SINGLE_VALUE_CONSUMER_NODES:
            continue
        out.append(
            Recommendation(
                rule_id="REC_AUTO_ITERATE_AGGREGATE_MISSING",
                category=RecommendationCategory.DATA_FLOW,
                title="Auto-iterate output may need aggregation before a single-value consumer",
                rationale=(
                    f"'{edge.from_node_id}' produces an array but '{edge.to_node_id}' typically "
                    "renders a single value. The display may iterate per row instead of summarising."
                ),
                location=ErrorLocation(
                    node_id=edge.to_node_id,
                    node_type=_node_type(dst),
                    edge_index=idx,
                    edge_from=edge.from_node_id,
                    edge_to=edge.to_node_id,
                ),
                options=[
                    "Insert AggregateNode to collapse iterations",
                    "Insert FieldMappingNode to reshape the payload",
                    "Insert ConditionNode to filter to one item",
                ],
                example_snippet={
                    "nodes": [{"id": "agg1", "type": "AggregateNode", "strategy": "first"}],
                },
            )
        )
    return out


def make_expression_port_typo_rec(
    *,
    ref_id: str,
    candidates: Iterable[str],
    location: ErrorLocation,
) -> Recommendation:
    """REC_EXPRESSION_PORT_TYPO — used inline on INVALID_EXPRESSION_REF.

    Always emits ≥1 candidate via `suggest_close_match`; if difflib finds
    nothing, falls back to the first few candidates so the consumer always
    has something concrete to act on.
    """
    matches = suggest_close_match(ref_id, candidates, n=3, cutoff=0.4) or sorted(set(candidates))[:3]
    return Recommendation(
        rule_id="REC_EXPRESSION_PORT_TYPO",
        category=RecommendationCategory.DATA_FLOW,
        title="Expression references an unknown node id (possible typo)",
        rationale="The referenced node id does not exist. The closest matches are listed.",
        location=location,
        options=[f"Use '{m}' instead of '{ref_id}'" for m in matches],
        example_snippet={"data": "{{ nodes." + (matches[0] if matches else "<existing>") + ".values }}"},
    )


def make_broker_product_mismatch_rec(
    *,
    node_id: str,
    node_type: str,
    required_provider: str,
) -> Recommendation:
    """REC_BROKER_PRODUCT_MISMATCH — used inline on INCOMPATIBLE_BROKER_PROVIDER."""
    return Recommendation(
        rule_id="REC_BROKER_PRODUCT_MISMATCH",
        category=RecommendationCategory.DATA_FLOW,
        title="Broker product scope does not match this node",
        rationale=(
            f"Node '{node_id}' ({node_type}) needs a '{required_provider}' broker, but the "
            "workflow's broker is a different product type."
        ),
        location=ErrorLocation(node_id=node_id, node_type=node_type),
        options=[
            f"Add the matching broker node (e.g. '{required_provider}' broker)",
            "Switch the dependent node to one that matches the existing broker",
        ],
    )


STATIC_RECOMMENDATION_RULES: List[Callable[[Any, Any], List[Recommendation]]] = [
    check_realtime_throttle,
    check_external_api_resilience,
    check_order_retry_risk,
    check_position_sizing_missing,
    check_large_symbol_list_batch,
    check_auto_iterate_aggregate_missing,
]


def run_static_recommendation_rules(
    workflow,
    registry,
    *,
    suppress: Optional[Iterable[str]] = None,
) -> List[Recommendation]:
    suppress_set = set(suppress or [])
    out: List[Recommendation] = []
    for rule in STATIC_RECOMMENDATION_RULES:
        for rec in rule(workflow, registry):
            if rec.rule_id in suppress_set:
                continue
            out.append(rec)
    return out


# ---------------------------------------------------------------------------
# Runtime rules (1) — run after dry_run
# ---------------------------------------------------------------------------


def check_empty_symbol_list_runtime(workflow, dry_run_state: Dict[str, Any], registry) -> List[Recommendation]:
    """REC_EMPTY_SYMBOL_LIST — dry_run reported an empty symbol list output."""
    out: List[Recommendation] = []
    if not isinstance(dry_run_state, dict):
        return out
    node_outputs = dry_run_state.get("node_outputs") or {}
    symbol_ports = {"symbols", "symbol_list", "watchlist", "universe"}

    for node_id, ports in node_outputs.items():
        if not isinstance(ports, dict):
            continue
        for port_name, value in ports.items():
            if port_name in symbol_ports and isinstance(value, list) and len(value) == 0:
                out.append(
                    Recommendation(
                        rule_id="REC_EMPTY_SYMBOL_LIST",
                        category=RecommendationCategory.DATA_FLOW,
                        title="Symbol list is empty at runtime",
                        rationale=(
                            f"Node '{node_id}' produced an empty '{port_name}' at dry_run. "
                            "Downstream consumers will run zero iterations."
                        ),
                        location=ErrorLocation(node_id=node_id, field_path=port_name),
                        options=[
                            "Populate the universe via WatchlistNode",
                            "Populate the universe via MarketUniverseNode",
                            "Provide symbols inline on the upstream producer",
                        ],
                    )
                )
    return out


RUNTIME_RECOMMENDATION_RULES: List[Callable[[Any, Dict[str, Any], Any], List[Recommendation]]] = [
    check_empty_symbol_list_runtime,
]


def run_runtime_recommendation_rules(
    workflow,
    dry_run_state: Dict[str, Any],
    registry,
    *,
    suppress: Optional[Iterable[str]] = None,
) -> List[Recommendation]:
    suppress_set = set(suppress or [])
    out: List[Recommendation] = []
    for rule in RUNTIME_RECOMMENDATION_RULES:
        for rec in rule(workflow, dry_run_state, registry):
            if rec.rule_id in suppress_set:
                continue
            out.append(rec)
    return out


# ---------------------------------------------------------------------------
# Post-processing: cascade suppression + capping + summary
# ---------------------------------------------------------------------------


def _normalise_code(value: Any) -> Optional[ErrorCode]:
    """ErrorInfo.code may be the raw enum or its string value (use_enum_values=True)."""
    if isinstance(value, ErrorCode):
        return value
    if isinstance(value, str):
        try:
            return ErrorCode(value)
        except ValueError:
            return None
    return None


def _find_cascade_children(root: ErrorInfo, survivors: List[ErrorInfo]) -> List[ErrorInfo]:
    root_code = _normalise_code(root.code)
    if root_code is None:
        return []
    root_node_id = root.location.node_id
    root_scope = root.details.get("product_scope")
    cascaded: List[ErrorInfo] = []

    for other in survivors:
        if other is root:
            continue
        if _normalise_code(other.code) not in {
            ErrorCode.INVALID_EXPRESSION_REF,
            ErrorCode.INVALID_EDGE_REF,
            ErrorCode.INVALID_EDGE_PORT,
            ErrorCode.MISSING_REQUIRED_BROKER,
        }:
            continue

        if root_code == ErrorCode.UNKNOWN_NODE_TYPE and root_node_id:
            # Suppress ref errors that point at the unknown node id.
            if other.location.node_id == root_node_id:
                cascaded.append(other)
            elif other.location.edge_from and other.location.edge_from.split(".")[0] == root_node_id:
                cascaded.append(other)
            elif other.location.edge_to and other.location.edge_to.split(".")[0] == root_node_id:
                cascaded.append(other)

        elif root_code == ErrorCode.MISSING_REQUIRED_BROKER and root_scope:
            if (
                _normalise_code(other.code) == ErrorCode.MISSING_REQUIRED_BROKER
                and other.details.get("product_scope") == root_scope
                and other is not root
            ):
                cascaded.append(other)

        elif root_code == ErrorCode.CYCLE_DETECTED:
            cycle_path = root.details.get("cycle_path") or []
            if other.location.node_id and other.location.node_id in cycle_path:
                cascaded.append(other)

        elif root_code == ErrorCode.DUPLICATE_NODE_ID and root_node_id:
            if other.location.node_id == root_node_id:
                cascaded.append(other)
            elif other.location.edge_from and other.location.edge_from.split(".")[0] == root_node_id:
                cascaded.append(other)
            elif other.location.edge_to and other.location.edge_to.split(".")[0] == root_node_id:
                cascaded.append(other)

    return cascaded


def apply_cascade_suppression(
    result: ValidationResult,
    *,
    expand_cascade: bool = False,
) -> List[str]:
    """Mutate `result.errors` to fold cascades into their root cause's details.

    Returns the list of root-cause node ids touched (for summary use).
    """
    if expand_cascade:
        return []

    survivors: List[ErrorInfo] = list(result.errors)
    roots = [e for e in survivors if _normalise_code(e.code) in CASCADE_SUPPRESSION_RULES]
    root_node_ids: List[str] = []

    for root in roots:
        cascaded = _find_cascade_children(root, survivors)
        if not cascaded:
            continue
        root.details["suppressed_count"] = len(cascaded)
        root.details["suppressed_codes"] = sorted({
            (c.code.value if isinstance(c.code, ErrorCode) else str(c.code)) for c in cascaded
        })
        if root.location.node_id and root.location.node_id not in root_node_ids:
            root_node_ids.append(root.location.node_id)
        for child in cascaded:
            child.details.setdefault("suppressed_by", []).append(
                root.code.value if isinstance(root.code, ErrorCode) else str(root.code)
            )
            if child in survivors:
                survivors.remove(child)

    result.errors = survivors
    return root_node_ids


def apply_limits(result: ValidationResult, limits: ValidationLimits) -> None:
    """Cap each channel by `limits`, populating `result.truncated[...]` counters.

    Also enforces `max_per_node` for the errors channel.
    """
    # Per-node cap on errors channel.
    if limits.max_per_node and result.errors:
        per_node: Counter = Counter()
        kept: List[ErrorInfo] = []
        dropped_per_node = 0
        for info in result.errors:
            key = info.location.node_id or "__noloc__"
            per_node[key] += 1
            if per_node[key] <= limits.max_per_node:
                kept.append(info)
            else:
                dropped_per_node += 1
        if dropped_per_node:
            result.truncated["errors_per_node"] = (
                result.truncated.get("errors_per_node", 0) + dropped_per_node
            )
        result.errors = kept

    def _cap(items: List, cap: int, label: str) -> List:
        if cap and len(items) > cap:
            result.truncated[label] = (result.truncated.get(label, 0) + (len(items) - cap))
            return items[:cap]
        return items

    result.errors = _cap(result.errors, limits.max_errors, "errors")
    result.warnings = _cap(result.warnings, limits.max_warnings, "warnings")
    result.static_recommendations = _cap(
        result.static_recommendations, limits.max_recommendations_per_channel, "static_recommendations"
    )
    result.runtime_recommendations = _cap(
        result.runtime_recommendations, limits.max_recommendations_per_channel, "runtime_recommendations"
    )


def build_summary(
    result: ValidationResult,
    *,
    root_cause_node_ids: List[str],
) -> ResultSummary:
    """Produce a ResultSummary suitable for fast LLM triage.

    Critical codes are ordered by (cascade root first, then frequency).
    `next_action_hint` follows the deterministic rule set in plan §5.6.3.
    """
    code_counts: Counter = Counter()
    cascade_roots: List[ErrorInfo] = []
    for e in result.errors:
        c = _normalise_code(e.code)
        if c is None:
            continue
        code_counts[c] += 1
        if c in CASCADE_SUPPRESSION_RULES and e.details.get("suppressed_count"):
            cascade_roots.append(e)

    critical: List[ErrorCode] = []
    seen: Set[ErrorCode] = set()
    for e in cascade_roots:
        c = _normalise_code(e.code)
        if c and c not in seen:
            critical.append(c)
            seen.add(c)
    for code, _ in code_counts.most_common():
        if code not in seen:
            critical.append(code)
            seen.add(code)
        if len(critical) >= 3:
            break

    hint: Optional[str] = None
    if cascade_roots:
        biggest = max(cascade_roots, key=lambda x: x.details.get("suppressed_count", 0))
        code_str = biggest.code.value if isinstance(biggest.code, ErrorCode) else str(biggest.code)
        hint = (
            f"Fix {code_str} first — "
            f"{biggest.details.get('suppressed_count', 0)} cascade errors will resolve"
        )
    elif len(result.errors) == 1:
        only = result.errors[0]
        code_str = only.code.value if isinstance(only.code, ErrorCode) else str(only.code)
        node = only.location.node_id or "<workflow>"
        hint = f"Resolve {code_str} on node '{node}'"
    elif not result.errors and (result.static_recommendations or result.runtime_recommendations):
        rec_count = len(result.static_recommendations) + len(result.runtime_recommendations)
        hint = f"Workflow is valid. {rec_count} improvement suggestion(s) available."

    return ResultSummary(
        is_valid=not result.errors,
        error_count=len(result.errors),
        warning_count=len(result.warnings),
        static_recommendation_count=len(result.static_recommendations),
        runtime_recommendation_count=len(result.runtime_recommendations),
        critical_codes=critical,
        root_cause_node_ids=root_cause_node_ids,
        next_action_hint=hint,
        truncated=bool(result.truncated),
    )


def finalize_result(
    result: ValidationResult,
    *,
    limits: Optional[ValidationLimits] = None,
    expand_cascade: bool = False,
) -> ValidationResult:
    """End-of-pipeline helper: cascade -> capping -> summary."""
    effective_limits = limits or ValidationLimits()
    root_ids = apply_cascade_suppression(result, expand_cascade=expand_cascade)
    apply_limits(result, effective_limits)
    result.summary = build_summary(result, root_cause_node_ids=root_ids)
    return result


__all__ = [
    "REALTIME_NODES",
    "ORDER_NODES",
    "ACCOUNT_NODES",
    "EXTERNAL_API_NODES",
    "STATIC_RECOMMENDATION_RULES",
    "RUNTIME_RECOMMENDATION_RULES",
    "check_realtime_throttle",
    "check_external_api_resilience",
    "check_order_retry_risk",
    "check_position_sizing_missing",
    "check_large_symbol_list_batch",
    "check_auto_iterate_aggregate_missing",
    "check_empty_symbol_list_runtime",
    "make_expression_port_typo_rec",
    "make_broker_product_mismatch_rec",
    "run_static_recommendation_rules",
    "run_runtime_recommendation_rules",
    "apply_cascade_suppression",
    "apply_limits",
    "build_summary",
    "finalize_result",
]
