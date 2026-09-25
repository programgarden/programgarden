"""
ProgramGarden Core - Expression Reference

A machine-readable, code-verified reference for the ``{{ }}`` expression
language evaluated by :mod:`programgarden_core.expression.evaluator`.

Purpose
-------
The auto-trading chatbot authors workflow JSON whose fields carry ``{{ }}``
bindings. It reads the exported ``expression_reference()`` dict to learn which
roots, helpers and namespace functions actually exist, what each one returns,
and which shapes silently fail. Every *name* in the returned dict is
**introspected from the running evaluator** (``SafeEvaluator.ALLOWED_BUILTINS``,
the namespace instances, and ``NodeOutputProxy``) so the reference can never
drift out of sync with the code; only the human-readable *semantics* text is
hand-written. ``tests/test_expression_reference.py`` fails the build if a name
appears in the evaluator but not here, or vice versa, and if any listed example
does not evaluate.

The reference describes behaviour verified against evaluator.py at core 2.2.0
(git fedbb29). Line references in the semantics text point at that file.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, List

from programgarden_core.expression.evaluator import (
    DateNamespace,
    FinanceNamespace,
    FormatNamespace,
    ListNamespace,
    NodeOutputProxy,
    SafeEvaluator,
    StatsNamespace,
)

# ═══════════════════════════════════════════════════════════════════════════
# Classification of ALLOWED_BUILTINS keys
# ═══════════════════════════════════════════════════════════════════════════

# Keys in ALLOWED_BUILTINS that are namespace instances (introspected below).
_NAMESPACE_NAMES = ("date", "finance", "stats", "format", "lst")

# Keys in ALLOWED_BUILTINS that are literal constants, not callables.
_LITERAL_NAMES = ("True", "False", "None", "null", "true", "false")


# ═══════════════════════════════════════════════════════════════════════════
# Hand-written semantics (keyed by the introspected name)
# ═══════════════════════════════════════════════════════════════════════════

# NodeOutputProxy chain helpers. `nodes.<id>.<listPort>` (a list-valued port)
# is re-wrapped as a NodeOutputProxy, so these chain. See evaluator.py:419-516.
_PROXY_HELPERS: Dict[str, Dict[str, str]] = {
    "all": {
        "semantics": (
            "Return the whole array (evaluator.py:421-423). Also the safe way to "
            "hand a proxy to len()/sorted()/max()/`in`: a bare NodeOutputProxy has "
            "no __len__/__iter__ and hangs those, call .all() first."
        ),
        "example": "{{ nodes.account.positions.all() }}",
    },
    "first": {
        "semantics": (
            "arr[0] of the array, or None when empty (evaluator.py:425-428). "
            "Chain a field off it: .first().symbol."
        ),
        "example": "{{ nodes.account.positions.first() }}",
    },
    "last": {
        "semantics": "arr[-1], or None when empty (evaluator.py:430-433).",
        "example": "{{ nodes.account.positions.last() }}",
    },
    "count": {
        "semantics": (
            "len(array) as an int (evaluator.py:435-437). Use `.count() == 0` to "
            "test emptiness — a proxy is always truthy and has no len()."
        ),
        "example": "{{ nodes.account.positions.count() }}",
    },
    "filter": {
        "semantics": (
            "Keep dict items matching ONE comparison `<field> <op> <value>` "
            "(op in > < >= <= == !=). Value parsing: quoted -> string, "
            "true/false/none -> literal, digits -> int/float, otherwise a raw "
            "string (so `symbol == AAPL` unquoted also works). No and/or/not and "
            "no parentheses — chain two .filter() calls instead. A condition that "
            "does not match the grammar returns the array UNCHANGED (no error). "
            "Ordering ops are None-safe; non-dict items are dropped "
            "(evaluator.py:441-453, 574-634)."
        ),
        "example": "{{ nodes.account.positions.filter('pnl > 0') }}",
    },
    "map": {
        "semantics": (
            "Extract one field from each dict item; dotted paths work ('a.b'); "
            "non-dict items are dropped; a missing field yields None "
            "(evaluator.py:455-467)."
        ),
        "example": "{{ nodes.account.positions.map('symbol') }}",
    },
    "sum": {
        "semantics": (
            "Sum of a numeric field over dict items, None counted as 0 "
            "(evaluator.py:469-484)."
        ),
        "example": "{{ nodes.account.positions.sum('quantity') }}",
    },
    "avg": {
        "semantics": (
            "Mean of a field over dict items, ignoring None; 0 when there are no "
            "values (evaluator.py:486-502)."
        ),
        "example": "{{ nodes.account.positions.avg('pnl') }}",
    },
    "flatten": {
        "semantics": (
            "For each dict item, merge every dict row of item[nested_key] as "
            "{**parent_without_nested_key, **row}; non-dict items and non-list "
            "nested values are skipped (evaluator.py:504-516)."
        ),
        "example": "{{ nodes.scan.symbols.flatten('bars') }}",
    },
}

# date.* namespace. Live uses the local clock; replay pins the clock to the
# fixture as_of (see error_behaviour). evaluator.py:137-213.
_DATE_SEMANTICS: Dict[str, Dict[str, str]] = {
    "today": {
        "semantics": (
            "Today's date. format=None -> ISO 'YYYY-MM-DD'; 'yyyymmdd' -> "
            "'%Y%m%d'; 'iso' -> '%Y-%m-%d'; ANY OTHER string is passed straight "
            "to strftime, so '%Y/%m/%d' works but the placeholder text 'yyyy-mm-dd' "
            "returns itself literally (evaluator.py:149-179)."
        ),
        "example": "{{ date.today() }}",
    },
    "now": {
        "semantics": (
            "Live: naive local 'YYYY-MM-DDTHH:MM:SS' (19 chars). Replay: the "
            "fixture as_of, tz-aware, e.g. '2026-01-01T00:15:00+09:00' "
            "(evaluator.py:181-183)."
        ),
        "example": "{{ date.now() }}",
    },
    "ago": {
        "semantics": (
            "today - N days (string digits are accepted). Same format rules as "
            "today (evaluator.py:185-188)."
        ),
        "example": "{{ date.ago(30, format='yyyymmdd') }}",
    },
    "later": {
        "semantics": "today + N days. Same format rules as today (evaluator.py:190-193).",
        "example": "{{ date.later(7) }}",
    },
    "months_ago": {
        "semantics": (
            "today - N*30 days — 30-DAY months, NOT calendar months "
            "(evaluator.py:195-198)."
        ),
        "example": "{{ date.months_ago(3) }}",
    },
    "year_start": {
        "semantics": "January 1 of the current year (evaluator.py:200-203).",
        "example": "{{ date.year_start() }}",
    },
    "year_end": {
        "semantics": "December 31 of the current year (evaluator.py:205-208).",
        "example": "{{ date.year_end() }}",
    },
    "month_start": {
        "semantics": (
            "Day 1 of the current month. There is NO month_end, NO weekday and NO "
            "date-parsing/diff helper (evaluator.py:210-213)."
        ),
        "example": "{{ date.month_start() }}",
    },
}

# finance.* namespace. evaluator.py:216-254.
_FINANCE_SEMANTICS: Dict[str, Dict[str, str]] = {
    "pct_change": {
        "semantics": (
            "Percent change ((new-old)/old*100); 0.0 when old == 0 "
            "(evaluator.py:226-230). pct_change(100, 110) == 10.0."
        ),
        "example": "{{ finance.pct_change(100, 110) }}",
    },
    "pct": {
        "semantics": (
            "part AS A PERCENT OF total ((part/total)*100); 0.0 when total == 0 "
            "(evaluator.py:232-236). NOT 'pct percent of value': "
            "finance.pct(1000, 10) == 10000.0, and finance.pct(50, 200) == 25.0. "
            "To take 10% of a balance use `balance * 0.1`, never finance.pct."
        ),
        "example": "{{ finance.pct(50, 200) }}",
    },
    "discount": {
        "semantics": "price*(1 - pct/100) (evaluator.py:238-240).",
        "example": "{{ finance.discount(1000, 20) }}",
    },
    "markup": {
        "semantics": "price*(1 + pct/100) (evaluator.py:242-244).",
        "example": "{{ finance.markup(1000, 20) }}",
    },
    "annualize": {
        "semantics": (
            "((1+ret/100)**(252/days)-1)*100 on a 252-trading-day basis; 0.0 when "
            "days <= 0 (evaluator.py:246-250)."
        ),
        "example": "{{ finance.annualize(5, 30) }}",
    },
    "compound": {
        "semantics": "principal*((1+rate/100)**periods) (evaluator.py:252-254).",
        "example": "{{ finance.compound(1000, 10, 3) }}",
    },
}

# stats.* namespace. Operates on a PLAIN list only — it does NOT unwrap a
# NodeOutputProxy (only lst.* do), so pass `.all()` or `.map('f').all()`.
# evaluator.py:257-293.
_STATS_SEMANTICS: Dict[str, Dict[str, str]] = {
    "mean": {
        "semantics": "statistics.mean; empty list -> 0.0 (evaluator.py:267-271).",
        "example": "{{ stats.mean([1, 2, 3, 4, 5]) }}",
    },
    "avg": {
        "semantics": "Alias of mean (evaluator.py:273-275).",
        "example": "{{ stats.avg([1, 2, 3, 4, 5]) }}",
    },
    "median": {
        "semantics": "statistics.median; empty list -> 0.0 (evaluator.py:277-281).",
        "example": "{{ stats.median([1, 2, 3, 4, 5]) }}",
    },
    "stdev": {
        "semantics": (
            "statistics.stdev; fewer than 2 values -> 0.0 (evaluator.py:283-287)."
        ),
        "example": "{{ stats.stdev([1, 2, 3, 4, 5]) }}",
    },
    "variance": {
        "semantics": (
            "statistics.variance; fewer than 2 values -> 0.0 (evaluator.py:289-293)."
        ),
        "example": "{{ stats.variance([1, 2, 3, 4, 5]) }}",
    },
}

# format.* namespace. evaluator.py:296-316.
_FORMAT_SEMANTICS: Dict[str, Dict[str, str]] = {
    "pct": {
        "semantics": (
            "f'{value:.{decimals}f}%' — the value is assumed to ALREADY be a "
            "percent; format.pct does not multiply by 100 (evaluator.py:306-308)."
        ),
        "example": "{{ format.pct(12.34) }}",
    },
    "currency": {
        "semantics": "f'{symbol}{value:,.{decimals}f}' (evaluator.py:310-312).",
        "example": "{{ format.currency(1234.56) }}",
    },
    "number": {
        "semantics": "f'{value:,.{decimals}f}', thousands-separated (evaluator.py:314-316).",
        "example": "{{ format.number(1234567.89) }}",
    },
}

# lst.* namespace. Named `lst` because `list` is the builtin type-cast;
# `list.first(...)` fails. lst.* DO unwrap a NodeOutputProxy. evaluator.py:319-353.
_LIST_SEMANTICS: Dict[str, Dict[str, str]] = {
    "first": {
        "semantics": (
            "First element (list or proxy), None on empty (evaluator.py:329-333)."
        ),
        "example": "{{ lst.first([1, 2, 3]) }}",
    },
    "last": {
        "semantics": "Last element, None on empty (evaluator.py:335-339).",
        "example": "{{ lst.last([1, 2, 3]) }}",
    },
    "count": {
        "semantics": "len, or 0 on empty (evaluator.py:341-345).",
        "example": "{{ lst.count([1, 2, 3]) }}",
    },
    "pluck": {
        "semantics": (
            "Extract a dotted path from each item; proxy is unwrapped; non-list -> "
            "[] (evaluator.py:347-349)."
        ),
        "example": "{{ lst.pluck(nodes.account.positions, 'symbol') }}",
    },
    "flatten": {
        "semantics": (
            "TWO arguments required — flatten(items, nested_key). Same merge as "
            "the proxy .flatten helper (evaluator.py:351-353)."
        ),
        "example": "{{ lst.flatten(nodes.scan.symbols, 'bars') }}",
    },
}

_NAMESPACE_SEMANTICS = {
    "date": _DATE_SEMANTICS,
    "finance": _FINANCE_SEMANTICS,
    "stats": _STATS_SEMANTICS,
    "format": _FORMAT_SEMANTICS,
    "lst": _LIST_SEMANTICS,
}

# Builtin functions / math names exposed as bare names. evaluator.py:773-811.
_BUILTIN_SEMANTICS: Dict[str, Dict[str, str]] = {
    "bool": {"semantics": "Python bool() cast.", "example": "{{ bool(1) }}"},
    "int": {"semantics": "Python int() cast.", "example": "{{ int('5') }}"},
    "float": {"semantics": "Python float() cast.", "example": "{{ float('1.5') }}"},
    "str": {"semantics": "Python str() cast. str(proxy) gives 'NodeOutputProxy([...])'.", "example": "{{ str(42) }}"},
    "list": {"semantics": "Python list() cast. list(proxy) HANGS (proxy iteration) — use .all().", "example": "{{ list((1, 2)) }}"},
    "dict": {"semantics": "Python dict() cast.", "example": "{{ dict(a=1) }}"},
    "tuple": {"semantics": "Python tuple() cast. tuple(proxy) HANGS — use .all().", "example": "{{ tuple([1, 2]) }}"},
    "abs": {"semantics": "Absolute value.", "example": "{{ abs(-3) }}"},
    "min": {"semantics": "Minimum. min(proxy) fails/hangs — pass .all().", "example": "{{ min(3, 1, 2) }}"},
    "max": {"semantics": "Maximum. max(proxy) fails/hangs — pass .all().", "example": "{{ max(3, 1, 2) }}"},
    "sum": {"semantics": "Sum of an iterable (the builtin). sum(proxy) fails — pass .all().", "example": "{{ sum([1, 2, 3]) }}"},
    "pow": {"semantics": "Power; the exponent must be <= 1000 (DoS guard).", "example": "{{ pow(2, 5) }}"},
    "round": {"semantics": "Python round().", "example": "{{ round(3.14159, 2) }}"},
    "len": {"semantics": "Length. len(proxy) raises TypeError('no len()') — use .count().", "example": "{{ len([1, 2, 3]) }}"},
    "range": {"semantics": "range(); capped at 100,000 elements (DoS guard, evaluator.py:845-853).", "example": "{{ list(range(3)) }}"},
    "sorted": {"semantics": "sorted(); sorted(proxy) hangs — pass .all().", "example": "{{ sorted([3, 1, 2]) }}"},
    "zip": {"semantics": "zip(); wrap in list(...) to materialize.", "example": "{{ list(zip([1, 2], [3, 4])) }}"},
    "all": {"semantics": "True if every element is truthy.", "example": "{{ all([True, True]) }}"},
    "any": {"semantics": "True if any element is truthy.", "example": "{{ any([False, True]) }}"},
    "sqrt": {"semantics": "math.sqrt.", "example": "{{ sqrt(9) }}"},
    "log": {"semantics": "math.log (natural log).", "example": "{{ log(e) }}"},
    "log10": {"semantics": "math.log10.", "example": "{{ log10(100) }}"},
    "exp": {"semantics": "math.exp.", "example": "{{ exp(0) }}"},
    "ceil": {"semantics": "math.ceil.", "example": "{{ ceil(1.2) }}"},
    "floor": {"semantics": "math.floor.", "example": "{{ floor(1.8) }}"},
    "pi": {"semantics": "math.pi constant (a bare name, not a call).", "example": "{{ pi }}"},
    "e": {"semantics": "math.e constant (a bare name, not a call).", "example": "{{ e }}"},
}

# Literal constants. evaluator.py:826-836.
_LITERAL_SEMANTICS: Dict[str, Dict[str, str]] = {
    "True": {"semantics": "Python True.", "example": "{{ True }}"},
    "False": {"semantics": "Python False.", "example": "{{ False }}"},
    "None": {"semantics": "Python None.", "example": "{{ None }}"},
    "true": {"semantics": "JSON-style alias of True (workflows are authored as JSON).", "example": "{{ true }}"},
    "false": {"semantics": "JSON-style alias of False.", "example": "{{ false }}"},
    "null": {"semantics": "JSON-style alias of None — so `{{ x != null }}` is valid.", "example": "{{ null }}"},
}


# ═══════════════════════════════════════════════════════════════════════════
# Introspection helpers (names come from the running evaluator, never a list)
# ═══════════════════════════════════════════════════════════════════════════


def _public_methods(obj: Any) -> List[str]:
    """Public (non-underscore) callable attribute names of ``obj``."""
    return sorted(
        name
        for name in dir(obj)
        if not name.startswith("_") and callable(getattr(obj, name))
    )


def _signature_without_self(func: Any) -> str:
    """``str(inspect.signature(func))`` with a leading ``self`` parameter dropped."""
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return "(...)"
    params = [p for name, p in sig.parameters.items() if name != "self"]
    return "(" + ", ".join(str(p) for p in params) + ")"


def _namespace_functions(ns_name: str, instance: Any) -> Dict[str, Dict[str, str]]:
    """Introspect one namespace instance's public methods, attach semantics."""
    semantics = _NAMESPACE_SEMANTICS[ns_name]
    out: Dict[str, Dict[str, str]] = {}
    for method_name in _public_methods(instance):
        entry = dict(semantics.get(method_name, {}))
        entry["signature"] = f"{ns_name}.{method_name}" + _signature_without_self(
            getattr(instance, method_name)
        )
        out[method_name] = entry
    return out


def _proxy_helpers() -> Dict[str, Dict[str, str]]:
    """Introspect NodeOutputProxy chain helpers, attach semantics."""
    out: Dict[str, Dict[str, str]] = {}
    for method_name in _public_methods(NodeOutputProxy):
        entry = dict(_PROXY_HELPERS.get(method_name, {}))
        entry["signature"] = ".{}{}".format(
            method_name, _signature_without_self(getattr(NodeOutputProxy, method_name))
        )
        out[method_name] = entry
    return out


def _builtins_and_literals() -> Dict[str, Dict[str, Dict[str, str]]]:
    """Split ALLOWED_BUILTINS keys into builtin functions vs literal constants."""
    builtins_out: Dict[str, Dict[str, str]] = {}
    literals_out: Dict[str, Dict[str, str]] = {}
    for name in sorted(SafeEvaluator.ALLOWED_BUILTINS):
        if name in _NAMESPACE_NAMES:
            continue
        if name in _LITERAL_NAMES:
            literals_out[name] = dict(_LITERAL_SEMANTICS.get(name, {}))
        else:
            builtins_out[name] = dict(_BUILTIN_SEMANTICS.get(name, {}))
    return {"builtins": builtins_out, "literals": literals_out}


# ═══════════════════════════════════════════════════════════════════════════
# The reference
# ═══════════════════════════════════════════════════════════════════════════


def expression_reference() -> Dict[str, Any]:
    """Return the full, code-verified ``{{ }}`` expression reference.

    The returned dict is JSON-serializable. Function/helper/builtin NAME lists
    are introspected from the evaluator, so this cannot drift; the semantics
    text and examples are hand-written and covered by
    ``tests/test_expression_reference.py``.
    """
    namespaces = {
        ns_name: _namespace_functions(ns_name, SafeEvaluator.ALLOWED_BUILTINS[ns_name])
        for ns_name in _NAMESPACE_NAMES
    }
    split = _builtins_and_literals()

    return {
        "summary": (
            "Field values in workflow JSON may contain `{{ ... }}` bindings. The "
            "inner text is a small Python-eval expression (NOT Jinja): no pipe "
            "filters, no `{% %}`, no `~`. Roots are nodes / item / index / total / "
            "input / context (and row inside a ConditionNode items.extract). "
            "Verified against evaluator.py at core 2.2.0."
        ),
        "grammar": {
            "pattern": r"\{\{\s*(.+?)\s*\}\}",
            "whole_string_vs_embedded": (
                "If the trimmed value is exactly one `{{ expr }}`, the TYPED result "
                "is returned (list/dict/number/bool/None). Otherwise every match is "
                "substituted with str(result) into the surrounding text "
                "(evaluator.py:1033-1062)."
            ),
            "engine": (
                "The inner text is parsed as a Python `eval`-mode AST and walked by "
                "a whitelist (SafeEvaluator). There is no Jinja engine."
            ),
            "allowed_ast": (
                "Constant, Name, BinOp, UnaryOp, Compare (chained), BoolOp (and/or), "
                "IfExp (a if c else b), Attribute, Subscript (index only), Call "
                "(positional + keyword), and List/Dict/Tuple literals "
                "(evaluator.py:881-996)."
            ),
            "unsupported": [
                "Jinja pipe filters `{{ x | length }}` (| is bit-or, so `length` is an undefined variable)",
                "`~` string concat (SyntaxError)",
                "slices `[1:]`, lambda, comprehensions, f-strings, starred args, walrus",
                "two adjacent expressions with no leading text, e.g. `{{ a }}-{{ b }}` (parsed as ONE expression -> SyntaxError). `x {{ a }} {{ b }}` with leading text works.",
                "`{% if %}` / `{% for %}` blocks",
                "String methods DO work: `'AAPL'.lower()`.",
            ],
            "limits": {
                "max_ast_depth": SafeEvaluator.MAX_AST_DEPTH,
                "max_power_exponent": SafeEvaluator.MAX_POWER,
                "max_range_size": SafeEvaluator.MAX_RANGE_SIZE,
            },
            "example": "{{ nodes.account.positions.count() }}",
            "examples": ["Price: {{ item.price }}"],
        },
        "roots": {
            "note": (
                "Only these root names are defined. ANY other bare identifier "
                "(balance, rsi, price, symbols, a nodeId without `nodes.`, row "
                "outside items.extract) raises \"정의되지 않은 변수: <name>\" "
                "(ExpressionContext.to_dict, evaluator.py:668-693; context.py:3390-3430)."
            ),
            "nodes": {
                "semantics": (
                    "Access a prior node's outputs: `nodes.<id>` or `nodes['<id>']`. "
                    "`nodes.<id>.<port>` reads an output port. A missing id/port via "
                    "dotted access resolves to None silently at RUNTIME; only the "
                    "static resolver reports it. Bracket form is required for "
                    "hyphenated or keyword ids (see node_ids)."
                ),
                "example": "{{ nodes.account.balance.orderable_amount }}",
            },
            "item": {
                "semantics": (
                    "The current element during auto-iterate or inside a SplitNode "
                    "branch. Defined ONLY when an iteration item is set — `{{ item }}` "
                    "otherwise raises 'undefined variable: item'. If the element is a "
                    "string, `{{ item.symbol }}` silently yields None."
                ),
                "example": "{{ item.symbol }}",
            },
            "index": {
                "semantics": (
                    "0-based iteration index. ALWAYS defined — literally 0 outside "
                    "iteration, never an error (evaluator.py:680-683)."
                ),
                "example": "{{ index }}",
            },
            "total": {
                "semantics": "Item count during iteration; literally 0 outside iteration.",
                "example": "{{ total }}",
            },
            "input": {
                "semantics": (
                    "Workflow inputs (defaults merged with user overrides), a plain "
                    "dict — `input.<name>` (context.py:3423-3425)."
                ),
                "example": "{{ input.threshold }}",
            },
            "context": {
                "semantics": (
                    "The runtime context_params dict — `context.<key>`. A missing key "
                    "yields None. (There is no `context.available_balance`; nothing "
                    "populates it.)"
                ),
                "example": "{{ context.mode }}",
            },
            "current_symbol": {
                "semantics": (
                    "Legacy iteration variable; present only when set to a truthy "
                    "value. Prefer `item`."
                ),
                "example": "{{ current_symbol }}",
            },
            "current_index": {
                "semantics": "Legacy; always present (0 outside iteration).",
                "example": "{{ current_index }}",
            },
            "row": {
                "semantics": (
                    "Exists ONLY inside a ConditionNode / BacktestEngineNode "
                    "`items.extract` value, one row at a time. An extract expression "
                    "is treated as per-row only if its text contains the substring "
                    "'row.', so `{{ row['date'] }}` (bracket form) is misclassified "
                    "as an external binding. Not a general root."
                ),
            },
            "realtime_keys": {
                "semantics": (
                    "ExecutionContext._realtime_data is merged into variables, but "
                    "nothing writes it in the shipped executor, so no realtime bare "
                    "names are actually available."
                ),
            },
        },
        "node_proxy": {
            "semantics": (
                "`nodes.<id>` and any list-valued port resolve to a NodeOutputProxy "
                "(evaluator.py:370-545). A bare `{{ nodes.<id> }}` unwraps to a LIST: "
                "the first list-valued key among positions, symbols, values, data, "
                "items, array, results; else the outputs dict wrapped as a "
                "1-element list [dict]. On a whole node without an array port, "
                ".all()/.first()/.count() therefore operate on that 1-element list."
            ),
            "helpers": _proxy_helpers(),
            "subscript": {
                "semantics": (
                    "proxy[int] -> element or None if out of range (NEVER IndexError, "
                    "which is why Python's iteration protocol hangs — see pitfalls). "
                    "proxy['key'] on dict data -> dict.get. A plain dict/list subscript "
                    "uses raw obj[key] and can raise (evaluator.py:535-542, 957-961)."
                ),
                "example": "{{ nodes.account.positions[0]['symbol'] }}",
            },
            "port_vs_helper_precedence": {
                "semantics": (
                    "A bare attribute that names an output PORT wins over the helper "
                    "of the same name: `{{ nodes.x.count }}` is the `count` port value "
                    "if the node has one, else the bound helper method. A CALL always "
                    "means the helper: `{{ nodes.x.count() }}` runs the helper even "
                    "when a `count` port exists (evaluator.py:942-979). Corollary: a "
                    "bare `{{ nodes.x.first }}` on a node WITHOUT a `first` port "
                    "returns the bound method object, which is not JSON-serializable — "
                    "add () or a port name."
                ),
                "examples": [
                    "{{ nodes.open_orders.count }}",
                    "{{ nodes.open_orders.count() }}",
                ],
            },
        },
        "namespaces": namespaces,
        "builtins": split["builtins"],
        "literals": split["literals"],
        "node_ids": {
            "semantics": (
                "For dotted access `nodes.<id>` the id must be a valid Python "
                "identifier. A hyphen parses as subtraction (`nodes.if-balance.x` "
                "breaks) and a Python keyword is a SyntaxError: `{{ nodes.if.result }}` "
                "fails because `if` is a keyword. Use the bracket form "
                "`nodes['if'].result` (the only way to reach hyphenated/keyword ids) "
                "or rename the node to snake_case/camelCase."
            ),
            "python_keywords_needing_bracket": [
                "if", "in", "for", "is", "and", "or", "not", "else", "elif",
                "while", "def", "class", "return", "import", "from", "as",
                "lambda", "with", "try", "except", "finally", "None", "True", "False",
            ],
            "wrong": "{{ nodes.if.result }}",
            "right": "{{ nodes['if'].result }}",
        },
        "auto_iteration": {
            "semantics": (
                "A node auto-iterates when its input is a NON-EMPTY list, its type is "
                "not excluded (NO_AUTO_ITERATE_NODE_TYPES; account nodes are also "
                "banned as an implicit iteration SOURCE), and — for whole-array-port "
                "nodes such as PositionSizingNode.symbols — the whole-array port is "
                "not bound as a whole (executor.py auto-iterate). There is NO "
                "requirement that the config reference `{{ item }}`: a node with no "
                "item binding still runs N times."
            ),
            "deferred_keys": (
                "Before iteration, top-level keys whose value text contains the "
                "substring '{{ item', '{{item' or '{{ index' are deferred untouched "
                "and re-resolved per element. The check is a substring test, so "
                "`{{ total }}` alone is not deferred and evaluates to 0 before "
                "iteration; '{{  item' (two spaces) is also not deferred."
            ),
            "item_binding_not_required": True,
        },
        "error_behaviour": {
            "live": (
                "An expression that fails does NOT abort the node. Per-leaf "
                "(evaluate_all_bindings, 25 node executors) keeps the literal "
                "'{{ ... }}' string and logs a warning. In normal/dry_run "
                "_resolve_config_expressions a SINGLE failure keeps the WHOLE node "
                "config literal (executor.py). Downstream nodes then receive the "
                "literal template text — a silent mis-binding, not a raised error."
            ),
            "replay": (
                "Validation replay (ReplayContext) uses the SAME evaluator but pins "
                "`date.*` to the fixture as_of (tz-aware) and raises "
                "ContractViolation('Unresolved mapping: <expr>') on ANY unresolved "
                "binding — replay never keeps a literal (validation_replay.py)."
            ),
            "static_resolver": (
                "Before run, the resolver regex-checks only the dotted "
                "`nodes.<id>.<port>[.<field>]` form: unknown node id -> "
                "INVALID_EXPRESSION_REF; first attr must be a declared port or a "
                "known chain method. Bracket form and `{{ item }}`/`{{ row }}` are "
                "NOT statically checked. Note the chain-method whitelist is broader "
                "than the proxy actually implements (e.g. .mean/.min/.unique pass "
                "static checks but fail at runtime)."
            ),
        },
        "example_context": {
            "node_outputs": {
                "account": {
                    "positions": [
                        {"symbol": "AAPL", "pnl": 120, "quantity": 10},
                        {"symbol": "TSLA", "pnl": -30, "quantity": 5},
                    ],
                    "balance": {"orderable_amount": 50000},
                    "count": 2,
                },
                "scan": {
                    "symbols": [
                        {"symbol": "AAPL", "bars": [{"rsi": 28}, {"rsi": 31}]},
                        {"symbol": "TSLA", "bars": [{"rsi": 40}]},
                    ]
                },
                "open_orders": {
                    "open_orders": [{"symbol": "PLUG", "order_id": "300"}],
                    "count": 1,
                },
                "gate": {"result": True},
                "if": {"result": True},
            },
            "item": {"symbol": "AAPL", "rsi": 28, "price": 150},
            "index": 0,
            "total": 2,
            "current_symbol": "AAPL",
            "variables": {
                "input": {"threshold": 1000, "capital": 100000},
                "context": {"mode": "live"},
            },
        },
        "pitfalls": [
            {
                "id": "finance_pct_is_of_total",
                "text": (
                    "finance.pct(part, total) is part AS A PERCENT OF total, so "
                    "finance.pct(1000, 10) == 10000.0, not 100. To take 10% of a "
                    "balance write `balance * 0.1`."
                ),
                "wrong": "{{ finance.pct(1000, 10) }}",
                "right": "{{ nodes.account.balance.orderable_amount * 0.1 }}",
            },
            {
                "id": "lst_flatten_needs_key",
                "text": "lst.flatten requires TWO arguments: lst.flatten(items, nested_key).",
                "wrong": "{{ lst.flatten(nodes.scan.symbols) }}",
                "right": "{{ lst.flatten(nodes.scan.symbols, 'bars') }}",
            },
            {
                "id": "keyword_node_id",
                "text": (
                    "A keyword/hyphenated node id breaks dotted access; "
                    "`{{ nodes.if.result }}` is a SyntaxError. Use bracket form."
                ),
                "wrong": "{{ nodes.if.result }}",
                "right": "{{ nodes['if'].result }}",
            },
            {
                "id": "proxy_no_len",
                "text": (
                    "A NodeOutputProxy has no len(): `len(nodes.x.positions)` raises "
                    "TypeError. Use .count(), or len(...all())."
                ),
                "wrong": "{{ len(nodes.account.positions) }}",
                "right": "{{ nodes.account.positions.count() }}",
            },
            {
                "id": "proxy_no_iteration",
                "text": (
                    "A NodeOutputProxy has no __iter__/__contains__ and __getitem__ "
                    "returns None instead of raising IndexError, so `x in proxy`, "
                    "sorted(proxy), list(proxy), tuple(proxy), max(proxy) HANG "
                    "FOREVER. Convert with .all() first."
                ),
                "wrong": "{{ 'AAPL' in nodes.account.positions }}",
                "right": "{{ 'AAPL' in nodes.account.positions.all() }}",
            },
            {
                "id": "proxy_always_truthy",
                "text": (
                    "A NodeOutputProxy has no __bool__, so it is ALWAYS truthy even "
                    "when empty: `{{ 'yes' if nodes.c.passed_symbols else 'no' }}` is "
                    "'yes' on an empty result. Test emptiness with `.count() == 0`."
                ),
                "wrong": "{{ 'yes' if nodes.account.positions else 'no' }}",
                "right": "{{ 'no' if nodes.account.positions.count() == 0 else 'yes' }}",
            },
            {
                "id": "date_format_literal",
                "text": (
                    "date.* format accepts only the presets 'yyyymmdd' and 'iso', or "
                    "a real strftime pattern. A placeholder like 'yyyy-mm-dd' is "
                    "returned literally. Omit format (or use 'iso') for ISO."
                ),
                "wrong": "{{ date.today(format='yyyy-mm-dd') }}",
                "right": "{{ date.today(format='iso') }}",
            },
            {
                "id": "undefined_bare_names",
                "text": (
                    "Bare business names are NOT variables: `balance`, `rsi`, "
                    "`price`, `symbols`, or a nodeId without `nodes.` all raise "
                    "'undefined variable'. Reach values through nodes.* / input.* / "
                    "item.*."
                ),
                "wrong": "{{ balance * 0.1 }}",
                "right": "{{ nodes.account.balance.orderable_amount * 0.1 }}",
            },
            {
                "id": "no_legacy_bare_date_helpers",
                "text": (
                    "today_yyyymmdd(), months_ago_yyyymmdd(N), days_ago_yyyymmdd(N), "
                    "today(), days_ago(), pct_change(), mean(), first(), pluck() as "
                    "BARE names do not exist (some node-schema defaults wrongly use "
                    "them). Use date.today(format='yyyymmdd'), date.months_ago(N, "
                    "format='yyyymmdd'), stats.mean(...), lst.first(...), etc."
                ),
                "wrong": "{{ today_yyyymmdd() }}",
                "right": "{{ date.today(format='yyyymmdd') }}",
            },
            {
                "id": "no_nodeid_without_nodes_prefix",
                "text": (
                    "`{{ acct.positions }}` (a nodeId without the `nodes.` prefix) is "
                    "an undefined variable, despite some docstrings. Always write "
                    "`nodes.<id>`."
                ),
                "wrong": "{{ acct.positions }}",
                "right": "{{ nodes.account.positions }}",
            },
            {
                "id": "filter_single_comparison_only",
                "text": (
                    "proxy.filter() takes exactly ONE `field op value` comparison. "
                    "`filter('pnl > 0 and symbol == \"AAPL\"')` parses the value as "
                    "the string '0 and symbol == \"AAPL\"' and errors. Chain two "
                    "filters instead."
                ),
                "wrong": "{{ nodes.account.positions.filter('pnl > 0 and symbol == \"AAPL\"') }}",
                "right": "{{ nodes.account.positions.filter('pnl > 0').filter('symbol == AAPL') }}",
            },
            {
                "id": "stats_needs_plain_list",
                "text": (
                    "stats.* do NOT unwrap a NodeOutputProxy (only lst.* do). "
                    "stats.mean(nodes.x.values) hangs/raises — pass .all() or "
                    ".map('field').all()."
                ),
                "wrong": "{{ stats.mean(nodes.account.positions.map('pnl')) }}",
                "right": "{{ stats.mean(nodes.account.positions.map('pnl').all()) }}",
            },
            {
                "id": "condition_result_is_boolean",
                "text": (
                    "A ConditionNode's `result` port is a BOOLEAN, not an array: "
                    "`nodes.cond.result.all()` resolves .all -> None and raises "
                    "'호출 불가능한 객체: None'. Use the array port (e.g. "
                    "passed_symbols) for chaining."
                ),
                "wrong": "{{ nodes.gate.result.all() }}",
                "right": "{{ nodes.gate.result }}",
            },
        ],
    }


__all__ = ["expression_reference"]
