"""Regression guard against misleading docstrings on ``Literal[...]`` fields.

Detects descriptions on ``Literal[...]``-typed Pydantic fields that contain
phrases like ``"treated as KRX"`` or ``"any other value is treated as"``. Such
phrases lie because Pydantic ``Literal`` rejects non-listed values — they never
reach LS server-side normalization. A literal-typed exchange-code field cannot
"fall back to KRX" the way an unconstrained ``str`` field can.

Rationale (2026-05-12 AlphaWorks report, issue #1): the misleading docstring on
``T1102InBlock.exchgubun`` ("Other values are treated as KRX per LS source.")
led AlphaWorks to pass ``exchgubun=""`` expecting LS to remap it, causing
repeated ``ValidationError`` crashes at market open. The fix swept the same
phrase out of 16 Korea Stock TR blocks.py files; this test prevents the lie
from being added back.

If a future TR genuinely accepts arbitrary strings (server normalizes),
the field MUST be typed ``str`` (or ``Optional[str]``) — not
``Literal[...]`` — and the test will not fire on it. See
``CSPAT00601.MbrNo`` for the truthful ``str``-typed pattern.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple

import pytest

import programgarden_finance.ls as _ls_root


_LS_ROOT = Path(_ls_root.__file__).parent

_LYING_PHRASES = (
    "treated as KRX",
    "treated as krx",
)


def _is_literal_annotation(node: ast.expr) -> bool:
    """Return True for ``Literal[...]`` and ``Optional[Literal[...]]`` annotations."""
    if isinstance(node, ast.Subscript):
        value = node.value
        if isinstance(value, ast.Name) and value.id == "Literal":
            return True
        if isinstance(value, ast.Attribute) and value.attr == "Literal":
            return True
        # Optional[Literal[...]] / Union[Literal[...], None]
        if isinstance(value, ast.Name) and value.id in {"Optional", "Union"}:
            inner = node.slice
            if isinstance(inner, ast.Tuple):
                return any(_is_literal_annotation(elt) for elt in inner.elts)
            return _is_literal_annotation(inner)
    return False


def _extract_description_text(field_call: ast.Call) -> str:
    """Pull the ``description=`` value out of a ``Field(...)`` call as a flat string."""
    for kw in field_call.keywords:
        if kw.arg != "description":
            continue
        val = kw.value
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            return val.value
        # description=(...): parenthesized implicit concatenation -> ast.Constant after parser
        # Handle JoinedStr (f-string) and BinOp concat as fallback
        if isinstance(val, ast.JoinedStr):
            return "".join(
                v.value for v in val.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)
            )
    return ""


def _scan_file(path: Path) -> List[Tuple[str, str]]:
    """Return [(field_name, description)] for every Literal-typed Field with a lying phrase."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    offenders: List[Tuple[str, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if not _is_literal_annotation(node.annotation):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        call = node.value
        # Match `= Field(...)` — by name or attribute (e.g. `pydantic.Field`)
        func = call.func
        is_field_call = (
            (isinstance(func, ast.Name) and func.id == "Field")
            or (isinstance(func, ast.Attribute) and func.attr == "Field")
        )
        if not is_field_call:
            continue
        desc = _extract_description_text(call)
        if any(p in desc for p in _LYING_PHRASES):
            offenders.append((node.target.id, desc))
    return offenders


def test_no_lying_treated_as_krx_on_literal_fields():
    """No ``Literal[...]`` field may claim "treated as KRX" in its description."""
    failures: List[str] = []
    for path in sorted(_LS_ROOT.rglob("blocks.py")):
        for field_name, desc in _scan_file(path):
            rel = path.relative_to(_LS_ROOT)
            snippet = desc[:120] + ("…" if len(desc) > 120 else "")
            failures.append(f"{rel}::{field_name}\n      description: {snippet!r}")

    if failures:
        msg = "\n  ".join([
            "The following Literal[...] fields claim 'treated as KRX' but",
            "Pydantic Literal rejects non-listed values before LS ever sees them.",
            "If LS really accepts arbitrary input, use `str` (see CSPAT00601.MbrNo);",
            "otherwise remove the misleading phrase.",
            "",
            *failures,
        ])
        pytest.fail(msg)


def test_scanner_finds_str_typed_truthful_claim_as_negative_control():
    """Sanity: the scanner does NOT flag str-typed fields with the same phrase.

    CSPAT00601.MbrNo is a `str` field whose description correctly states that
    LS treats unknown values as KRX server-side — that claim is truthful for
    `str` and must not be flagged.
    """
    target = _LS_ROOT / "korea_stock" / "order" / "CSPAT00601" / "blocks.py"
    assert target.exists(), f"Expected fixture file missing: {target}"
    offenders = _scan_file(target)
    assert offenders == [], (
        f"Scanner false-positive on str-typed truthful claim: {offenders}"
    )
