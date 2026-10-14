"""Expressions run only from authored templates; runtime values are data.

Before 2.6.6 a node's config was evaluated twice: the workflow job resolved
``{{ … }}`` bindings (``WorkflowJob._resolve_config_expressions``) and the node
executor then evaluated the already-resolved config again
(``evaluate_all_bindings``). Any value produced at runtime that contained
``{{`` — LLM text, HTTP bodies, broker strings, workflow inputs, credentials —
was evaluated a second time in the workflow expression context.

Invariant: an expression is evaluated only if its template text was authored
in the workflow definition (the node config as stored in the DSL), and at most
once per execution of that node (per iteration for deferred ``{{ item }}``
bindings). The check is positional: a string at config path *P* is evaluated
only while it is still exactly the authored string at *P*. Once a template has
been resolved, the value at *P* is data and passes byte-identical.

Each workflow job registers an authored snapshot per node
(``ExecutionContext.register_authored_node_configs``). Without a snapshot (a
node run outside a workflow job, e.g. ``NodeRunner``) the engine keeps the
legacy behaviour and evaluates every template it is given, because that config
is the caller's authored input.

Source-code fields are never evaluated (``NEVER_EVALUATED_KEYS``).
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

# A position the authored config does not have (engine-injected keys, runtime data).
NOT_AUTHORED = object()
# No authored snapshot for this node: evaluate every template (pre-2.6.6 behaviour).
LEGACY = object()

# Fields that hold source code, not templates. They are never evaluated, even
# when the text contains ``{{ … }}``.
NEVER_EVALUATED_KEYS: Dict[str, frozenset] = {
    "CodeNode": frozenset({"code"}),
}


def authored_snapshot(node_type: str, config: Optional[Dict[str, Any]], fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deep copy of a node's authored config, as evaluation positions see it.

    Plugin ``fields`` are exposed under the ``fields`` key (executors receive
    them there). Never-evaluated keys are removed so their positions read as
    not authored.
    """
    snapshot = copy.deepcopy(dict(config or {}))
    if fields and "fields" not in snapshot:
        snapshot["fields"] = copy.deepcopy(fields)
    for key in NEVER_EVALUATED_KEYS.get(node_type, ()):
        snapshot.pop(key, None)
    return snapshot


def authored_root(context: Any, node_id: Optional[str]) -> Any:
    """The authored snapshot of ``node_id``, or ``LEGACY`` when none is registered."""
    if node_id is None:
        return LEGACY
    getter = getattr(context, "authored_node_config", None)
    if not callable(getter):
        return LEGACY
    try:
        snapshot = getter(node_id)
    except Exception:  # pragma: no cover - defensive (mock contexts)
        return LEGACY
    return snapshot if isinstance(snapshot, dict) else LEGACY


def child(authored: Any, key: Any) -> Any:
    """Authored value at ``key`` of a dict position."""
    if authored is LEGACY:
        return LEGACY
    if isinstance(authored, dict):
        return authored.get(key, NOT_AUTHORED)
    return NOT_AUTHORED


def element(authored: Any, index: int, length: int) -> Any:
    """Authored value at ``index`` of a list position of ``length`` items."""
    if authored is LEGACY:
        return LEGACY
    if isinstance(authored, list) and len(authored) == length:
        return authored[index]
    return NOT_AUTHORED


def authored_at(context: Any, node_id: Optional[str], *path: Any) -> Any:
    """Authored value at a top-level path of ``node_id`` (``LEGACY`` without a snapshot)."""
    authored = authored_root(context, node_id)
    for key in path:
        authored = child(authored, key)
    return authored


def may_evaluate(value: Any, authored: Any) -> bool:
    """True when ``value`` is a template the author wrote at this position, unchanged."""
    if not isinstance(value, str):
        return False
    if authored is LEGACY:
        return True
    return isinstance(authored, str) and value == authored


def copy_containers(value: Any) -> Any:
    """Rebuild dicts/lists (leaves shared) without evaluating anything."""
    if isinstance(value, dict):
        return {k: copy_containers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [copy_containers(v) for v in value]
    return value


class _Literal:
    """Opaque wrapper that hides runtime data from ``ExpressionEvaluator.evaluate_fields``."""

    __slots__ = ("value",)

    def __init__(self, value: Any) -> None:
        self.value = value


def shield(value: Any, authored: Any) -> Any:
    """Wrap every non-authored position so ``evaluate_fields`` leaves it untouched."""
    if authored is LEGACY:
        return value
    if isinstance(value, str):
        if "{{" in value and not may_evaluate(value, authored):
            return _Literal(value)
        return value
    if isinstance(value, dict):
        if isinstance(authored, dict):
            return {k: shield(v, authored.get(k, NOT_AUTHORED)) for k, v in value.items()}
        return _Literal(value)
    if isinstance(value, list):
        if isinstance(authored, list) and len(authored) == len(value):
            return [shield(v, a) for v, a in zip(value, authored)]
        return _Literal(value)
    return value


def _rebuild_like_evaluate_fields(value: Any) -> Any:
    # evaluate_fields rebuilds dicts recursively and lists one level deep.
    if isinstance(value, dict):
        return {k: _rebuild_like_evaluate_fields(v) for k, v in value.items()}
    if isinstance(value, list):
        return list(value)
    return value


def unshield(value: Any, authored: Any) -> Any:
    """Undo ``shield`` along the authored structure (resolved data is not walked)."""
    if isinstance(value, _Literal):
        return _rebuild_like_evaluate_fields(value.value)
    if authored is LEGACY:
        return value
    if isinstance(value, dict) and isinstance(authored, dict):
        return {k: unshield(v, authored.get(k, NOT_AUTHORED)) for k, v in value.items()}
    if isinstance(value, list) and isinstance(authored, list) and len(value) == len(authored):
        return [unshield(v, a) for v, a in zip(value, authored)]
    return value


def shield_config(config: Dict[str, Any], authored: Any) -> Dict[str, Any]:
    return {k: shield(v, child(authored, k)) for k, v in config.items()}


def unshield_config(config: Dict[str, Any], authored: Any) -> Dict[str, Any]:
    return {k: unshield(v, child(authored, k)) for k, v in config.items()}


def evaluate_fields_authored(evaluator: Any, fields: Dict[str, Any], authored: Any, on_error: Any = None) -> Dict[str, Any]:
    """``ExpressionEvaluator.evaluate_fields`` limited to authored templates."""
    shielded = shield_config(fields, authored)
    if on_error is None:
        resolved = evaluator.evaluate_fields(shielded)
    else:
        resolved = evaluator.evaluate_fields(shielded, on_error=on_error)
    return unshield_config(resolved, authored)
