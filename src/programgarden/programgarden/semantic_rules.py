"""Configurable semantic / safety rule layer for ``deep_validate`` (R1~R4).

Single source for the chatbot anti-pattern checks that used to live client-side
in ``programgarden_ai``'s ``workflow_semantic_lint``. This module exists because
structure-validation, ``dry_run`` and the Phase 2 port-type checks all pass for
workflows that are still *semantically* wrong or *unsafe* — they validate
*executability*, never *intent* or *safety*.

The four ground-truth anti-patterns (verified against the canonical example
corpus — maintained internally since the 2026-08 privatization — and the live
node registry):

  * **R1 — order quantity bound to an AIAgent response.** An AIAgent
    sentiment/decision output wired straight into an order quantity risks a
    0 / negative / nonsense size. ``BaseOrderNode`` declares ``order: Any`` so
    structure-validate accepts it. (Blocking when enabled.)
  * **R2 — AIAgent ``output_format='structured'`` with no ``output_schema``.**
    The ``response`` output port is declared ``type='any'`` with no sub-fields,
    so port-type validation cannot constrain it; an unconstrained structured
    output is one downstream consumers cannot rely on. (Blocking when enabled.)
    NOTE: the *harmful* case (a downstream binding to a specific sub-field) is
    already caught by ``deep_validate``'s runtime binding-resolution pass — the
    schema-less fixture yields no such field, so the binding is reported as
    ``DEEP_VALIDATION_BINDING_UNRESOLVED``. This rule adds *upfront* clarity
    (say why/how before a field-miss happens), per ``feedback_chatbot_error_clarity``.
  * **R3 — hardcoded literal order quantity with no PositionSizingNode.**
    Always trades the same size regardless of balance/risk. (Advisory.)
  * **R4 — order node carrying ``paper_trading``.** That field is a *broker*
    field; on an order node it is silently ignored. (Advisory.)
  * **R5 — unknown node config key.** A key that is not in the node's
    ``get_field_schema()`` nor its declared model fields. ``BaseNode`` sets
    ``extra="allow"`` so Pydantic accepts it, and the executor never reads it —
    the workflow *looks* configured but behaves differently (e.g. ScheduleNode
    ``{mode, schedule}`` instead of ``cron`` → silent 5-min fallback;
    PositionSizingNode ``size_type`` instead of ``method``). (Blocking when
    enabled.) Structural, not keyword-based: the allowed set is derived from the
    registry node class, and unknown / community / dynamic types (no resolvable
    class) are skipped rather than false-flagged.

Design contract
---------------
* **Pure** — no network, no LLM, no DB; never raises (a malformed DSL is
  defensively coerced, never crashes the validator).
* **Structural signals only.** Node identity (order / AIAgent) is resolved from
  the node *registry class hierarchy* (``BaseOrderNode`` / ``BaseModifyOrderNode``
  / ``AIAgentNode``), never from natural-language keyword arrays
  (project rule ``feedback_no_keyword_hardcoding_in_ai``). The binding graph is
  read from the DSL ``{{ nodes.<id>.<path> }}`` templates.
* **Off by default.** ``deep_validate`` only runs this layer when the caller
  passes a ``semantic_rules`` config, so the sandbox / editor default path is
  byte-for-byte unchanged (zero false-reject regression on the example corpus).
* **Per-rule configurable severity** — ``"error"`` (blocks), ``"warning"``
  (surfaced, non-blocking), or ``"off"`` (skipped).

All Korean ``suggestion`` strings are clear beginner-investor guidance the
chatbot can relay verbatim (``feedback_chatbot_error_clarity``).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from programgarden_core import (
    ErrorCode,
    ErrorInfo,
    ErrorLocation,
    ErrorSeverity,
    build_error,
    suggest_close_match,
)

# ---------------------------------------------------------------------------
# Rule identifiers + severity presets
# ---------------------------------------------------------------------------

RULE_ORDER_QTY_FROM_AI = "order_qty_from_ai_response"            # R1
RULE_STRUCTURED_OUTPUT_NO_SCHEMA = "structured_output_missing_schema"  # R2
RULE_HARDCODED_ORDER_QTY = "hardcoded_order_quantity"            # R3
RULE_ORDER_IGNORED_FIELD = "order_ignored_field"                # R4
RULE_UNKNOWN_NODE_FIELD = "unknown_node_field"                  # R5

ALL_RULES: tuple[str, ...] = (
    RULE_ORDER_QTY_FROM_AI,
    RULE_STRUCTURED_OUTPUT_NO_SCHEMA,
    RULE_HARDCODED_ORDER_QTY,
    RULE_ORDER_IGNORED_FIELD,
    RULE_UNKNOWN_NODE_FIELD,
)

_RULE_CODE: Dict[str, ErrorCode] = {
    RULE_ORDER_QTY_FROM_AI: ErrorCode.SEMANTIC_ORDER_QTY_FROM_AI,
    RULE_STRUCTURED_OUTPUT_NO_SCHEMA: ErrorCode.SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA,
    RULE_HARDCODED_ORDER_QTY: ErrorCode.SEMANTIC_HARDCODED_ORDER_QTY,
    RULE_ORDER_IGNORED_FIELD: ErrorCode.SEMANTIC_ORDER_IGNORED_FIELD,
    RULE_UNKNOWN_NODE_FIELD: ErrorCode.UNKNOWN_NODE_FIELD,
}

# Everything off — the default when no config is supplied.
DEFAULT_SEMANTIC_SEVERITIES: Dict[str, str] = {r: "off" for r in ALL_RULES}

# Chatbot strict preset — the save-chokepoint anti-pattern gate (R1/R2/R5
# block, R3/R4 advise). R5 blocks hallucinated / typo'd node config keys
# (e.g. ScheduleNode {mode,schedule} instead of cron, PositionSizingNode
# size_type instead of method) that ``extra="allow"`` silently accepts — the
# workflow looks configured but the extra keys are ignored at runtime.
STRICT_SEMANTIC_SEVERITIES: Dict[str, str] = {
    RULE_ORDER_QTY_FROM_AI: "error",
    RULE_STRUCTURED_OUTPUT_NO_SCHEMA: "error",
    RULE_HARDCODED_ORDER_QTY: "warning",
    RULE_ORDER_IGNORED_FIELD: "warning",
    RULE_UNKNOWN_NODE_FIELD: "error",
}

_SEVERITY_MAP: Dict[str, ErrorSeverity] = {
    "error": ErrorSeverity.ERROR,
    "warning": ErrorSeverity.WARNING,
}

# ---------------------------------------------------------------------------
# DSL field shapes (verified against the canonical examples — flat node dict)
# ---------------------------------------------------------------------------

_ORDER_FIELD = "order"
_QUANTITY_KEY = "quantity"
# ``paper_trading`` is a legitimate BrokerNode field; on an order node it is
# silently ignored. Scoped denylist (not a broad unknown-field sweep) to avoid
# false positives on legitimately-varied order fields.
_ORDER_IGNORED_FIELDS: frozenset[str] = frozenset({"paper_trading"})

# Binding template: "{{ nodes.<node_id>.<rest...> }}" (spaces optional).
_NODE_REF_RE = re.compile(r"\{\{\s*nodes\.([A-Za-z0-9_\-]+)\.")


# ---------------------------------------------------------------------------
# Structural node identity (registry class hierarchy — no keyword arrays)
# ---------------------------------------------------------------------------

def _order_base_classes() -> tuple:
    """Order-family base classes from the registry (placing OR mutating quantity).

    ``BaseOrderNode`` = New orders (carry an ``order.quantity``); ``BaseModifyOrderNode``
    = Modify/Cancel. Imported lazily so importing this module never forces the
    (heavy) node package at import time.
    """
    from programgarden_core.nodes.order import BaseOrderNode, BaseModifyOrderNode
    return (BaseOrderNode, BaseModifyOrderNode)


def _aiagent_base_class():
    from programgarden_core.nodes.ai import AIAgentNode
    return AIAgentNode


def _node_class(node_type: Any):
    """Resolve a node ``type`` string to its registered class, or None.

    None for unknown / dynamic / community types and for non-str types (a
    malformed DSL may carry a list/dict ``type``) — callers treat None as
    "neither order nor AI", keeping the lint never-raising.
    """
    if not isinstance(node_type, str):
        return None
    try:
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        return NodeTypeRegistry().get(node_type)
    except Exception:  # pragma: no cover - defensive
        return None


def _is_order_node(node_type: Any) -> bool:
    cls = _node_class(node_type)
    if cls is None:
        return False
    try:
        return issubclass(cls, _order_base_classes())
    except Exception:  # pragma: no cover - defensive
        return False


def _is_aiagent_node(node_type: Any) -> bool:
    cls = _node_class(node_type)
    if cls is None:
        return False
    try:
        return issubclass(cls, _aiagent_base_class())
    except Exception:  # pragma: no cover - defensive
        return False


# Structural keys present on every node dict but not always declared as a schema
# / model field. ``config`` / ``description`` are BaseNode fields; ``plugin`` /
# ``fields`` are the ConditionNode plugin-binding structure carried at node level.
# ``credential_id`` is the canonical credential-binding key (``nodes[].credential_id``
# + top-level ``credentials[]``): the executor's universal node-creation layer reads
# it (``config.get("credential_id")`` → ``_inject_credentials``) for every node type,
# so no per-node schema declares it — flagging it would block every credential-bound
# workflow at the strict save gate.
_RESERVED_NODE_KEYS: frozenset = frozenset(
    {"id", "type", "category", "position", "config", "description", "plugin",
     "fields", "credential_id"}
)


def _node_allowed_keys(node_type: Any) -> Optional[frozenset]:
    """Allowed top-level config keys for a registered node type, or None.

    The allowed set is the union of the node's declared Pydantic model fields,
    its ``get_field_schema()`` keys (the AI/UI-facing schema), and the reserved
    structural keys. Returns None when ``node_type`` does not resolve to a
    registered class (unknown / community / dynamic) — R5 skips those, since
    their schema is unknown and any key would otherwise be false-flagged.
    Never raises.
    """
    cls = _node_class(node_type)
    if cls is None:
        return None
    allowed = set(_RESERVED_NODE_KEYS)
    try:
        allowed |= set(cls.model_fields.keys())
    except Exception:  # pragma: no cover - defensive
        pass
    try:
        fs = cls.get_field_schema()
        if isinstance(fs, dict):
            allowed |= set(fs.keys())
    except Exception:  # pragma: no cover - defensive
        pass
    return frozenset(allowed)


# ---------------------------------------------------------------------------
# Binding helpers
# ---------------------------------------------------------------------------

def _is_binding(value: Any) -> bool:
    return isinstance(value, str) and "{{" in value and "}}" in value


def _referenced_node_ids(value: Any) -> List[str]:
    if not isinstance(value, str):
        return []
    return _NODE_REF_RE.findall(value)


def _order_quantity_value(node: Dict[str, Any]) -> tuple[bool, Any]:
    """Return ``(present, value)`` for an order's quantity.

    Order shape (canonical examples): ``order`` is either a literal dict
    ``{"quantity": <int>, ...}`` or a whole-order binding ``"{{ nodes.X.order }}"``.
    ``value`` is the quantity expression when ``order`` is a dict, else the whole
    ``order`` value. ``present`` is False only when there is no quantity to check
    (no ``order`` field, or a dict ``order`` without ``quantity`` — e.g. cancel).
    """
    if _ORDER_FIELD not in node:
        return False, None
    order = node.get(_ORDER_FIELD)
    if isinstance(order, dict):
        if _QUANTITY_KEY in order:
            return True, order.get(_QUANTITY_KEY)
        return False, None
    return True, order


# ---------------------------------------------------------------------------
# Config normalization
# ---------------------------------------------------------------------------

def normalize_severities(config: Any) -> Dict[str, str]:
    """Merge a caller config over the all-off default → ``{rule: severity}``.

    ``config`` may be a partial ``{rule_id: "error"|"warning"|"off"}`` dict (only
    the named rules are overridden), one of the preset dicts, or None (→ all off).
    Unknown rule keys and invalid severities are ignored defensively.
    """
    merged = dict(DEFAULT_SEMANTIC_SEVERITIES)
    if isinstance(config, dict):
        for rule, sev in config.items():
            if rule in merged and isinstance(sev, str) and sev in ("error", "warning", "off"):
                merged[rule] = sev
    return merged


def _enabled(severities: Dict[str, str], rule: str) -> Optional[ErrorSeverity]:
    """ErrorSeverity for an enabled rule, or None when the rule is 'off'."""
    return _SEVERITY_MAP.get(severities.get(rule, "off"))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def analyze_workflow_semantics(
    definition: Dict[str, Any],
    config: Any = None,
) -> List[ErrorInfo]:
    """Run the configurable semantic/safety layer over a workflow definition.

    Pure, never-raising. Returns a list of ``ErrorInfo`` (the same structured
    shape as every other validation error — ``code`` / ``severity`` /
    ``location{node_id,node_type,field_path,expression}`` / ``message`` /
    ``suggestion``), so consumers handle these uniformly with structure/deep
    errors. Severity per finding follows ``config`` (see ``normalize_severities``).

    Args:
        definition: Workflow definition (JSON dict) with ``nodes`` / ``edges``.
        config: Per-rule severity config; None → all rules off → ``[]``.
    """
    severities = normalize_severities(config)
    # Fast exit: nothing enabled → no work, no node-class resolution.
    if all(v == "off" for v in severities.values()):
        return []

    nodes = definition.get("nodes") if isinstance(definition, dict) else None
    if not isinstance(nodes, list):
        return []

    sev_r1 = _enabled(severities, RULE_ORDER_QTY_FROM_AI)
    sev_r2 = _enabled(severities, RULE_STRUCTURED_OUTPUT_NO_SCHEMA)
    sev_r3 = _enabled(severities, RULE_HARDCODED_ORDER_QTY)
    sev_r4 = _enabled(severities, RULE_ORDER_IGNORED_FIELD)
    sev_r5 = _enabled(severities, RULE_UNKNOWN_NODE_FIELD)

    # Index node id → node, and whether any PositionSizingNode exists (R3).
    nodes_by_id: Dict[str, Dict[str, Any]] = {}
    has_position_sizing = False
    for n in nodes:
        if not isinstance(n, dict):
            continue
        nid = n.get("id")
        if isinstance(nid, str):
            nodes_by_id[nid] = n
        if n.get("type") == "PositionSizingNode":
            has_position_sizing = True

    errors: List[ErrorInfo] = []

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        node_id = node.get("id") if isinstance(node.get("id"), str) else "?"

        # ── R5: unknown node config key (hallucinated / typo'd field) ──────
        # Runs for every node. Structural: the allowed set comes from the
        # registry node class; unknown / dynamic types (allowed is None) are
        # skipped rather than false-flagged.
        if sev_r5 is not None:
            allowed = _node_allowed_keys(node_type)
            if allowed is not None:
                for key in node.keys():
                    if key in allowed:
                        continue
                    errors.append(build_error(
                        ErrorCode.UNKNOWN_NODE_FIELD,
                        f"Node '{node_id}' ({node_type}) has field '{key}', which is not "
                        f"in this node's schema. Pydantic accepts it (extra='allow') but "
                        f"the executor never reads it, so the workflow looks configured "
                        f"but behaves differently than it appears.",
                        severity=sev_r5,
                        location=ErrorLocation(
                            node_id=node_id,
                            node_type=node_type if isinstance(node_type, str) else None,
                            field_path=key if isinstance(key, str) else None,
                        ),
                        available_values=(
                            suggest_close_match(key, sorted(allowed))
                            if isinstance(key, str) else None
                        ),
                        suggestion=(
                            f"'{key}' 는 {node_type} 노드에 없는 필드예요. 오탈자이거나 "
                            f"다른 노드의 필드일 수 있습니다. 이 노드의 config_schema 에 "
                            f"정의된 필드만 사용하세요 (예: ScheduleNode 는 cron, "
                            f"PositionSizingNode 는 method)."
                        ),
                        details={"rule": RULE_UNKNOWN_NODE_FIELD, "field": key},
                    ))

        # ── R2: AIAgent structured output with no schema (and no preset) ──
        if sev_r2 is not None and _is_aiagent_node(node_type):
            if node.get("output_format") == "structured":
                schema = node.get("output_schema")
                # missing / None / empty dict / empty string all = "no schema".
                # FALSE-REJECT GUARD: shipped examples 33/34 use structured + no
                # schema + a built-in ``preset`` (risk_manager / technical_analyst);
                # the lib treats schema-less structured as a non-fatal fallback to
                # raw JSON and a preset carries a behavior contract — so only the
                # truly-unconstrained case (no schema AND no preset) is flagged.
                if not schema and not node.get("preset"):
                    errors.append(build_error(
                        ErrorCode.SEMANTIC_STRUCTURED_OUTPUT_NO_SCHEMA,
                        "AIAgentNode output_format='structured' has no output_schema, "
                        "so the structured output is unconstrained and downstream "
                        "nodes cannot rely on its shape.",
                        severity=sev_r2,
                        location=ErrorLocation(
                            node_id=node_id, node_type=node_type, field_path="output_schema"
                        ),
                        suggestion=(
                            "output_schema 를 제공하거나(예: action/quantity 등 필드와 "
                            "타입을 명시), 구조가 필요 없으면 output_format=text 로 바꾸세요."
                        ),
                        details={"rule": RULE_STRUCTURED_OUTPUT_NO_SCHEMA},
                    ))

        # ── Order-node rules (R1 / R3 / R4) ──────────────────────────────
        if _is_order_node(node_type):
            present, qty_value = _order_quantity_value(node)

            # R1: order quantity bound to an AIAgent response → block.
            r1_hit = False
            if sev_r1 is not None and present and _is_binding(qty_value):
                ref_ids = _referenced_node_ids(qty_value)
                ai_ref = next(
                    (rid for rid in ref_ids
                     if _is_aiagent_node(nodes_by_id.get(rid, {}).get("type"))),
                    None,
                )
                if ai_ref is not None:
                    r1_hit = True
                    errors.append(build_error(
                        ErrorCode.SEMANTIC_ORDER_QTY_FROM_AI,
                        f"Order quantity is bound to AIAgent '{ai_ref}' output; an AI "
                        "sentiment/decision response wired straight into quantity risks "
                        "a 0 / negative / nonsense order size.",
                        severity=sev_r1,
                        location=ErrorLocation(
                            node_id=node_id, node_type=node_type,
                            field_path="order.quantity",
                            expression=qty_value if isinstance(qty_value, str) else None,
                        ),
                        suggestion=(
                            "수량은 PositionSizingNode 로 산출하고 order.quantity 는 그 "
                            "출력을 바인딩하세요. AI 감성/신호 응답을 주문 수량에 직결하면 "
                            "0/음수/엉뚱한 수량 위험이 있습니다 (주문 안티패턴 #1)."
                        ),
                        details={"rule": RULE_ORDER_QTY_FROM_AI, "ai_node_id": ai_ref},
                    ))

            # R3: hardcoded literal quantity AND no PositionSizingNode → advise.
            # Never on a binding (a binding is not a hardcoded literal). bool is
            # an int subclass — exclude it.
            if (
                sev_r3 is not None and not r1_hit and present
                and isinstance(qty_value, int) and not isinstance(qty_value, bool)
                and not has_position_sizing
            ):
                errors.append(build_error(
                    ErrorCode.SEMANTIC_HARDCODED_ORDER_QTY,
                    f"Order quantity is hardcoded ({qty_value}) and the workflow has no "
                    "PositionSizingNode — it always trades the same size regardless of "
                    "account balance or risk.",
                    severity=sev_r3,
                    location=ErrorLocation(
                        node_id=node_id, node_type=node_type, field_path="order.quantity"
                    ),
                    suggestion=(
                        "계정/리스크 기반 수량은 PositionSizingNode 사용을 권장합니다 "
                        "(고정 수량이 의도라면 그대로 두어도 됩니다)."
                    ),
                    details={"rule": RULE_HARDCODED_ORDER_QTY, "quantity": qty_value},
                ))

            # R4: order node carries a silently-ignored broker field → advise.
            if sev_r4 is not None:
                for field in _ORDER_IGNORED_FIELDS:
                    if field in node:
                        errors.append(build_error(
                            ErrorCode.SEMANTIC_ORDER_IGNORED_FIELD,
                            f"Order node carries '{field}', which the order schema does "
                            "not define and silently ignores; real/paper is decided at "
                            "the broker/credential level, not on the order node.",
                            severity=sev_r4,
                            location=ErrorLocation(
                                node_id=node_id, node_type=node_type, field_path=field
                            ),
                            suggestion=(
                                f"'{field}' 는 주문 노드에서 무시됩니다. 실전/모의 구분은 "
                                "BrokerNode 의 paper_trading 또는 모의 credential 로 "
                                "결정하세요."
                            ),
                            details={"rule": RULE_ORDER_IGNORED_FIELD, "field": field},
                        ))

    return errors


__all__ = [
    "RULE_ORDER_QTY_FROM_AI",
    "RULE_STRUCTURED_OUTPUT_NO_SCHEMA",
    "RULE_HARDCODED_ORDER_QTY",
    "RULE_ORDER_IGNORED_FIELD",
    "RULE_UNKNOWN_NODE_FIELD",
    "ALL_RULES",
    "DEFAULT_SEMANTIC_SEVERITIES",
    "STRICT_SEMANTIC_SEVERITIES",
    "normalize_severities",
    "analyze_workflow_semantics",
]
