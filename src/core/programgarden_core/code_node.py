"""ProgramGarden Core — CodeNode static compilation & AST security screening.

This module is the single source of truth for the CodeNode security lists and
the compile/screen pipeline. It is intentionally dependency-free (stdlib only)
so it can be reused verbatim by:

  1. `WorkflowResolver.validate()` — pre-flight structured errors before run.
  2. `CodeNodeExecutor` / subprocess worker — screen again right before `exec`.
  3. An external web-platform "share gate" server — re-run the same hard AST scan.

Security model (see plan §2): CodeNode runs untrusted Python. Defense is layered:

  * Layer 1 — scrubbed context (runtime, programgarden): the code never receives
    credential accessors.
  * Layer 2 — restricted builtins + AST denylist (THIS module): a curated
    `__builtins__` (no eval/exec/open/getattr/...), a safe `__import__` gated by a
    whitelist, and a static AST scan that rejects dangerous imports, builtin
    calls, and introspection-escape dunders BEFORE any code runs.
  * Layer 3 — binding seal (runtime, resolver): credentials cannot flow into
    `data`/`params`.
  * Layer 4 — subprocess isolation (runtime, programgarden): the code always runs
    in a credential-free child process.

`compile_code_node` NEVER executes the code — it only parses, screens, and
compiles. Execution (exec + calling `execute`) is the runtime's responsibility.

All user-facing strings are English (AI-chatbot consumer contract).
"""
from __future__ import annotations

import ast
import builtins as _builtins
from dataclasses import dataclass, field
from types import CodeType
from typing import Any, Dict, List, Optional, Set, Tuple

# Name of the entry-point coroutine the code text must define.
EXECUTE_FN_NAME = "execute"

# ── Whitelist: modules importable from CodeNode code ────────────────────────
# Pure-computation stdlib only. Everything else is rejected at screen time
# (AST) and at runtime (safe __import__). The embedding application may EXTEND
# this via `compile_code_node(..., allowed_imports=...)` / the worker config
# (e.g. to allow `numpy`), but the library default is secure-by-default.
DEFAULT_ALLOWED_IMPORTS: frozenset = frozenset({
    "math", "cmath", "statistics", "decimal", "fractions", "numbers",
    "random", "json", "re", "datetime", "time", "calendar",
    "collections", "itertools", "functools", "operator",
    "string", "textwrap", "unicodedata",
    "heapq", "bisect", "array", "copy",
    "dataclasses", "enum", "typing", "uuid",
    "hashlib", "hmac", "base64", "binascii", "zlib",
})

# ── Denylist: modules called out for a clearer error message ────────────────
# Enforcement is whitelist-based (not in DEFAULT_ALLOWED_IMPORTS → blocked);
# this set only makes the message explicit for well-known dangerous modules.
FORBIDDEN_MODULES: frozenset = frozenset({
    "os", "sys", "subprocess", "socket", "shutil", "importlib", "imp",
    "ctypes", "cffi", "gc", "inspect", "pathlib", "glob", "tempfile", "io",
    "urllib", "http", "requests", "ftplib", "smtplib", "asyncio",
    "multiprocessing", "threading", "concurrent", "_thread",
    "builtins", "marshal", "pickle", "shelve", "dbm", "sqlite3",
    "code", "codeop", "pty", "resource", "signal", "mmap", "fcntl",
    "platform", "webbrowser", "ssl", "select", "selectors",
})

# ── Denylist: builtin names that must never be called or aliased ────────────
FORBIDDEN_BUILTINS: frozenset = frozenset({
    "eval", "exec", "compile", "open", "__import__",
    "getattr", "setattr", "delattr",
    "globals", "locals", "vars",
    "input", "breakpoint", "help", "memoryview",
    "exit", "quit", "__build_class__",
})

# ── Denylist: introspection-escape / exfiltration dunders & frame attrs ──────
# Blocking these severs the object-graph walk that would otherwise reach the
# process globals (and, without subprocess isolation, credentials).
FORBIDDEN_DUNDERS: frozenset = frozenset({
    "__class__", "__bases__", "__base__", "__subclasses__", "__mro__",
    "__globals__", "__code__", "__closure__", "__func__", "__self__",
    "__dict__", "__getattribute__", "__setattr__", "__delattr__",
    "__reduce__", "__reduce_ex__", "__builtins__", "__import__",
    "__loader__", "__spec__", "__init_subclass__", "__subclasshook__",
    "__getattr__", "__wrapped__", "__objclass__",
    "gi_frame", "gi_code", "cr_frame", "cr_code", "ag_frame",
    "f_back", "f_globals", "f_locals", "f_builtins", "tb_frame",
})


@dataclass
class CodeScreenResult:
    """Structured outcome of `compile_code_node`. `ok=False` carries an
    AI-chatbot-consumable error (code + message + suggestion + location)."""

    ok: bool
    code_object: Optional[CodeType] = None
    error_code: Optional[str] = None       # one of CODE_NODE_SYNTAX_ERROR / _FORBIDDEN / _NO_EXECUTE
    message: Optional[str] = None
    suggestion: Optional[str] = None
    line: Optional[int] = None
    offset: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


def _module_root(name: Optional[str]) -> str:
    return (name or "").split(".")[0]


def _scan_ast(tree: ast.AST, allowed_imports: Set[str]) -> List[Dict[str, Any]]:
    """Return a list of violation dicts (empty when clean).

    Each violation: {kind, name, line, col, reason}. `kind` ∈
    {import, builtin, dunder}.
    """
    violations: List[Dict[str, Any]] = []

    for node in ast.walk(tree):
        # ── Imports (whitelist-enforced) ──
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = _module_root(alias.name)
                if root not in allowed_imports:
                    reason = (
                        f"module '{alias.name}' is blocked (filesystem/process/network access)"
                        if root in FORBIDDEN_MODULES
                        else f"module '{alias.name}' is not in the allowed import list"
                    )
                    violations.append({
                        "kind": "import", "name": alias.name,
                        "line": node.lineno, "col": node.col_offset, "reason": reason,
                    })
        elif isinstance(node, ast.ImportFrom):
            root = _module_root(node.module)
            # `from . import x` (level>0) is always blocked — no package context.
            if node.level and node.level > 0:
                violations.append({
                    "kind": "import", "name": node.module or ".",
                    "line": node.lineno, "col": node.col_offset,
                    "reason": "relative imports are not allowed in CodeNode",
                })
            elif root not in allowed_imports:
                reason = (
                    f"module '{node.module}' is blocked (filesystem/process/network access)"
                    if root in FORBIDDEN_MODULES
                    else f"module '{node.module}' is not in the allowed import list"
                )
                violations.append({
                    "kind": "import", "name": node.module or "",
                    "line": node.lineno, "col": node.col_offset, "reason": reason,
                })

        # ── Forbidden builtin names (call or alias) ──
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_BUILTINS:
                violations.append({
                    "kind": "builtin", "name": node.id,
                    "line": node.lineno, "col": node.col_offset,
                    "reason": f"use of '{node.id}' is not allowed",
                })

        # ── Introspection-escape dunders / frame attrs ──
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_DUNDERS:
                violations.append({
                    "kind": "dunder", "name": node.attr,
                    "line": node.lineno, "col": node.col_offset,
                    "reason": f"attribute '{node.attr}' access is not allowed (introspection escape)",
                })

        # ── String-literal dunder access via subscript, e.g. x['__class__'] ──
        # (only flag when the constant string is a forbidden dunder)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in FORBIDDEN_DUNDERS:
                violations.append({
                    "kind": "dunder", "name": node.value,
                    "line": node.lineno, "col": node.col_offset,
                    "reason": f"reference to '{node.value}' is not allowed (introspection escape)",
                })

    return violations


def _has_execute(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == EXECUTE_FN_NAME:
            return True
    return False


def compile_code_node(
    code: str,
    node_id: str,
    *,
    screen: bool = True,
    allowed_imports: Optional[Set[str]] = None,
) -> CodeScreenResult:
    """Parse, security-screen, and compile CodeNode source WITHOUT executing it.

    Pipeline:
      1. `ast.parse` — SyntaxError → CODE_NODE_SYNTAX_ERROR (line/offset).
      2. AST denylist scan (when `screen=True`) — CODE_NODE_FORBIDDEN.
      3. `execute` function must be defined — CODE_NODE_NO_EXECUTE.
      4. `compile(filename=f'<code:{node_id}>')` — preserves traceback lines.

    Args:
        code: Python source text (must define `execute`).
        node_id: node id, used only for the compiled filename (traceback anchor).
        screen: run the AST denylist scan (always True in production).
        allowed_imports: override the import whitelist (defaults to
            DEFAULT_ALLOWED_IMPORTS). Enforced both here and by the runtime
            safe `__import__`.

    Returns:
        CodeScreenResult — `ok=True` with `code_object`, or `ok=False` with a
        structured, English, chatbot-consumable error. Never raises for
        screening/syntax failures (they are returned as data).
    """
    allowed = set(allowed_imports) if allowed_imports is not None else set(DEFAULT_ALLOWED_IMPORTS)

    if not isinstance(code, str) or not code.strip():
        return CodeScreenResult(
            ok=False,
            error_code="CODE_NODE_SYNTAX_ERROR",
            message="CodeNode 'code' is empty.",
            suggestion="Provide Python source that defines `async def execute(data, params, context)`.",
            line=1, offset=0,
        )

    # 1. Parse
    try:
        tree = ast.parse(code, filename=f"<code:{node_id}>", mode="exec")
    except SyntaxError as e:
        return CodeScreenResult(
            ok=False,
            error_code="CODE_NODE_SYNTAX_ERROR",
            message=f"CodeNode syntax error: {e.msg}",
            suggestion="Fix the Python syntax at the reported line/offset.",
            line=e.lineno,
            offset=e.offset,
            details={"raw": str(e)},
        )

    # 2. Screen
    if screen:
        violations = _scan_ast(tree, allowed)
        if violations:
            first = violations[0]
            names = sorted({v["name"] for v in violations})
            return CodeScreenResult(
                ok=False,
                error_code="CODE_NODE_FORBIDDEN",
                message=(
                    f"CodeNode uses forbidden construct(s): {', '.join(names)} "
                    f"({first['reason']})."
                ),
                suggestion=(
                    "Remove the blocked import/builtin/introspection. CodeNode allows "
                    "pure-computation stdlib only (math, statistics, json, datetime, ...); "
                    "credentials, filesystem, network, subprocess, and object-graph "
                    "introspection are not available."
                ),
                line=first["line"],
                offset=first["col"],
                details={"violations": violations, "forbidden_names": names},
            )

    # 3. execute() must exist
    if not _has_execute(tree):
        return CodeScreenResult(
            ok=False,
            error_code="CODE_NODE_NO_EXECUTE",
            message=f"CodeNode code must define a function named '{EXECUTE_FN_NAME}'.",
            suggestion=(
                "Define `async def execute(data, params, context):` (a plain "
                "`def execute(...)` is also accepted and auto-wrapped)."
            ),
            line=1, offset=0,
        )

    # 4. Compile (never exec here)
    try:
        code_object = compile(tree, filename=f"<code:{node_id}>", mode="exec")
    except (SyntaxError, ValueError) as e:  # e.g. too-deeply-nested
        return CodeScreenResult(
            ok=False,
            error_code="CODE_NODE_SYNTAX_ERROR",
            message=f"CodeNode failed to compile: {e}",
            suggestion="Simplify the code so it compiles as a module.",
            line=getattr(e, "lineno", 1) or 1,
            offset=getattr(e, "offset", 0) or 0,
            details={"raw": str(e)},
        )

    return CodeScreenResult(ok=True, code_object=code_object)


# The real import machinery, captured once so the sandbox can delegate to it
# after the whitelist check.
_REAL_IMPORT = _builtins.__import__

# Curated safe builtins — everything a pure-compute function needs, and nothing
# that grants escape (no eval/exec/compile/open/getattr/setattr/globals/...).
_SAFE_BUILTIN_NAMES: Tuple[str, ...] = (
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "callable", "chr", "complex", "dict", "divmod", "enumerate", "filter",
    "float", "format", "frozenset", "hash", "hex", "int", "isinstance",
    "issubclass", "iter", "len", "list", "map", "max", "min", "next", "oct",
    "ord", "pow", "print", "range", "repr", "reversed", "round", "set",
    "slice", "sorted", "str", "sum", "tuple", "type", "zip", "hasattr",
    # exceptions & sentinels
    "Exception", "BaseException", "ValueError", "TypeError", "KeyError",
    "IndexError", "AttributeError", "ZeroDivisionError", "ArithmeticError",
    "OverflowError", "RuntimeError", "StopIteration", "StopAsyncIteration",
    "NotImplementedError", "AssertionError", "LookupError", "NameError",
    "RecursionError", "FloatingPointError", "GeneratorExit", "KeyboardInterrupt",
    "True", "False", "None", "NotImplemented", "Ellipsis",
    "object", "property", "staticmethod", "classmethod", "super",
    # __build_class__ is required for `class` statements in user code; it is not
    # itself an escape vector (dunder screen blocks the dangerous follow-ups).
    "__build_class__",
)


def build_restricted_builtins(allowed_imports: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Build the `__builtins__` dict used when exec-ing CodeNode source.

    Contains only the curated safe builtins plus a whitelist-gated
    `__import__`. Pure function (no exec, stdlib only) so it lives in core and
    is reused by the runtime worker.
    """
    allowed = set(allowed_imports) if allowed_imports is not None else set(DEFAULT_ALLOWED_IMPORTS)

    def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level and level != 0:
            raise ImportError("relative imports are not allowed in CodeNode")
        root = _module_root(name)
        if root not in allowed:
            raise ImportError(
                f"import of '{name}' is not allowed in CodeNode "
                f"(allowed: pure-computation stdlib only)"
            )
        return _REAL_IMPORT(name, globals, locals, fromlist, level)

    safe: Dict[str, Any] = {}
    for bn in _SAFE_BUILTIN_NAMES:
        if hasattr(_builtins, bn):
            safe[bn] = getattr(_builtins, bn)
    safe["__import__"] = _safe_import
    return safe
