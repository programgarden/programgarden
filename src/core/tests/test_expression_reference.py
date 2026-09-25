"""
Tests for the code-verified expression reference (reference.py).

These guarantee the exported ``expression_reference()`` cannot drift away from
the evaluator: every function/helper/builtin name in the reference must exist
in the evaluator's live namespaces and vice versa, every listed example must
evaluate, and the survey's pitfalls must reproduce exactly.
"""

import signal

import pytest

from programgarden_core.expression import expression_reference
from programgarden_core.expression.evaluator import (
    ExpressionContext,
    ExpressionError,
    ExpressionEvaluator,
    NodeOutputProxy,
    SafeEvaluator,
)


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

_NAMESPACE_NAMES = ("date", "finance", "stats", "format", "lst")
_LITERAL_NAMES = {"True", "False", "None", "null", "true", "false"}


def _public_methods(obj):
    """Public (non-underscore) callable attribute names of ``obj``."""
    return {
        name
        for name in dir(obj)
        if not name.startswith("_") and callable(getattr(obj, name))
    }


def _build_evaluator():
    """Build an evaluator from the reference's own ``example_context``.

    Mirrors how tests/test_expression_namespace.py builds a context
    (ExpressionContext + set_node_output), but sourced from the reference so
    every documented example is exercised against exactly the context it
    assumes.
    """
    ref = expression_reference()
    ec = ref["example_context"]
    ctx = ExpressionContext(
        node_outputs=ec["node_outputs"],
        item=ec["item"],
        index=ec["index"],
        total=ec["total"],
        current_symbol=ec["current_symbol"],
        variables=dict(ec["variables"]),
    )
    return ExpressionEvaluator(ctx)


class _Timeout:
    """SIGALRM guard so a NodeOutputProxy-iteration hang fails fast and loud."""

    def __init__(self, seconds=5):
        self.seconds = seconds

    def __enter__(self):
        def _raise(*_):
            raise TimeoutError("expression evaluation hung")

        self._prev = signal.signal(signal.SIGALRM, _raise)
        signal.alarm(self.seconds)
        return self

    def __exit__(self, *exc):
        signal.alarm(0)
        signal.signal(signal.SIGALRM, self._prev)
        return False


def _collect_examples(obj):
    """Every string under an ``example`` key or in an ``examples`` list."""
    out = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "example" and isinstance(value, str):
                out.append(value)
            elif key == "examples" and isinstance(value, list):
                out.extend(v for v in value if isinstance(v, str))
            else:
                out.extend(_collect_examples(value))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_collect_examples(item))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# no-drift: names in the reference == names in the evaluator
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("ns_name", _NAMESPACE_NAMES)
def test_namespace_functions_match_the_evaluator(ns_name):
    ref = expression_reference()
    instance = SafeEvaluator.ALLOWED_BUILTINS[ns_name]
    assert set(ref["namespaces"][ns_name]) == _public_methods(instance), (
        f"{ns_name}.* drift between reference and evaluator"
    )


def test_proxy_helper_names_match_NodeOutputProxy():
    ref = expression_reference()
    assert set(ref["node_proxy"]["helpers"]) == _public_methods(NodeOutputProxy)


def test_builtins_literals_namespaces_cover_ALLOWED_BUILTINS_exactly():
    ref = expression_reference()
    covered = (
        set(ref["builtins"]) | set(ref["literals"]) | set(ref["namespaces"])
    )
    assert covered == set(SafeEvaluator.ALLOWED_BUILTINS)


def test_literal_names_are_exactly_the_json_and_python_literals():
    ref = expression_reference()
    assert set(ref["literals"]) == _LITERAL_NAMES


def test_every_documented_name_has_semantics_and_signature():
    ref = expression_reference()
    for ns_name in _NAMESPACE_NAMES:
        for fn_name, entry in ref["namespaces"][ns_name].items():
            assert entry.get("semantics"), f"{ns_name}.{fn_name} missing semantics"
            assert entry.get("signature"), f"{ns_name}.{fn_name} missing signature"
            assert entry.get("example"), f"{ns_name}.{fn_name} missing example"
    for name, entry in ref["node_proxy"]["helpers"].items():
        assert entry.get("semantics"), f"proxy.{name} missing semantics"
        assert entry.get("signature"), f"proxy.{name} missing signature"
        assert entry.get("example"), f"proxy.{name} missing example"
    for name, entry in ref["builtins"].items():
        assert entry.get("semantics"), f"builtin {name} missing semantics"
        assert entry.get("example"), f"builtin {name} missing example"
    for name, entry in ref["literals"].items():
        assert entry.get("semantics"), f"literal {name} missing semantics"
        assert entry.get("example"), f"literal {name} missing example"


def test_signatures_are_introspected_from_the_live_functions():
    """A spot check that signatures come from inspect (annotations included),
    with `self` dropped — not a hand-written string."""
    ref = expression_reference()
    ago = ref["namespaces"]["date"]["ago"]["signature"]
    assert ago.startswith("date.ago(days") and "format" in ago and "None" in ago
    assert "self" not in ago
    flatten = ref["namespaces"]["lst"]["flatten"]["signature"]
    assert flatten.startswith("lst.flatten(items") and "nested_key" in flatten
    filt = ref["node_proxy"]["helpers"]["filter"]["signature"]
    assert filt.startswith(".filter(condition") and "self" not in filt


# ─────────────────────────────────────────────────────────────────────────────
# every example (and every corrected pitfall form) evaluates without error
# ─────────────────────────────────────────────────────────────────────────────


def test_every_reference_example_evaluates():
    evaluator = _build_evaluator()
    examples = _collect_examples(expression_reference())
    assert len(examples) > 40  # sanity: we actually collected the tables
    for expr in examples:
        with _Timeout(5):
            try:
                evaluator.evaluate(expr)
            except Exception as exc:  # noqa: BLE001 - surface which example broke
                pytest.fail(f"example failed to evaluate: {expr!r} -> {exc!r}")


def test_every_pitfall_right_form_evaluates():
    evaluator = _build_evaluator()
    for pitfall in expression_reference()["pitfalls"]:
        right = pitfall.get("right")
        if not right:
            continue
        with _Timeout(5):
            try:
                evaluator.evaluate(right)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(
                    f"pitfall {pitfall['id']} 'right' form failed: {right!r} -> {exc!r}"
                )


# ─────────────────────────────────────────────────────────────────────────────
# the survey's pitfalls reproduce exactly
# ─────────────────────────────────────────────────────────────────────────────


def test_finance_pct_is_percent_of_total_not_percent_of_value():
    evaluator = _build_evaluator()
    assert evaluator.evaluate("{{ finance.pct(1000, 10) }}") == 10000.0
    assert evaluator.evaluate("{{ finance.pct(50, 200) }}") == 25.0


def test_lst_flatten_requires_a_nested_key_argument():
    evaluator = _build_evaluator()
    # two-arg form works
    assert evaluator.evaluate("{{ lst.flatten(nodes.scan.symbols, 'bars') }}")
    # one-arg form raises
    with pytest.raises(ExpressionError):
        evaluator.evaluate("{{ lst.flatten(nodes.scan.symbols) }}")


def test_keyword_node_id_needs_bracket_form():
    evaluator = _build_evaluator()
    with pytest.raises(ExpressionError):
        evaluator.evaluate("{{ nodes.if.result }}")  # `if` is a Python keyword
    assert evaluator.evaluate("{{ nodes['if'].result }}") is True


def test_node_output_proxy_has_no_len():
    evaluator = _build_evaluator()
    with pytest.raises(ExpressionError):
        evaluator.evaluate("{{ len(nodes.account.positions) }}")
    # the documented workarounds both work
    assert evaluator.evaluate("{{ nodes.account.positions.count() }}") == 2
    assert evaluator.evaluate("{{ len(nodes.account.positions.all()) }}") == 2


def test_reference_pitfall_ids_include_the_survey_cases():
    ids = {p["id"] for p in expression_reference()["pitfalls"]}
    for required in (
        "finance_pct_is_of_total",
        "lst_flatten_needs_key",
        "keyword_node_id",
        "proxy_no_len",
    ):
        assert required in ids
