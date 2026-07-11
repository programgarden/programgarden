"""Core tests for CodeNode: compile/screen pipeline + node schema + ports.

These are stdlib-only (no programgarden dependency). Runtime execution,
subprocess isolation, and resolver validation are tested in the programgarden
package.
"""
import pytest

from programgarden_core.code_node import (
    compile_code_node,
    build_restricted_builtins,
    CodeScreenResult,
    DEFAULT_ALLOWED_IMPORTS,
    EXECUTE_FN_NAME,
)
from programgarden_core.nodes.code import CodeNode
from programgarden_core.registry import NodeTypeRegistry


# ── compile_code_node: happy path ──────────────────────────────────────────

def test_compile_valid_async():
    r = compile_code_node(
        "import statistics\n"
        "async def execute(data, params, context):\n"
        "    return {'m': statistics.mean(data)}",
        "n1",
    )
    assert r.ok and r.code_object is not None
    assert r.error_code is None


def test_compile_valid_sync_execute_accepted():
    r = compile_code_node("def execute(data, params, context):\n    return 1", "n1")
    assert r.ok


def test_compile_filename_is_node_scoped():
    r = compile_code_node("async def execute(d, p, c):\n    return 1", "my_node")
    assert r.ok
    assert r.code_object.co_filename == "<code:my_node>"


# ── compile_code_node: structured errors ───────────────────────────────────

def test_syntax_error_reports_line():
    r = compile_code_node("async def execute(d, p, c)\n    return 1", "n1")
    assert not r.ok
    assert r.error_code == "CODE_NODE_SYNTAX_ERROR"
    assert r.line is not None
    assert r.suggestion


def test_empty_code_is_syntax_error():
    r = compile_code_node("   ", "n1")
    assert not r.ok and r.error_code == "CODE_NODE_SYNTAX_ERROR"


def test_missing_execute_reported():
    r = compile_code_node("async def run(d, p, c):\n    return 1", "n1")
    assert not r.ok and r.error_code == "CODE_NODE_NO_EXECUTE"
    assert EXECUTE_FN_NAME in (r.message or "")


@pytest.mark.parametrize("code_body", [
    "import os\n",
    "import sys\n",
    "import subprocess\n",
    "import socket\n",
    "from urllib import request\n",
    "import requests\n",
    "import ctypes\n",
    "import inspect\n",
    "import multiprocessing\n",
    "import pickle\n",
])
def test_forbidden_imports(code_body):
    r = compile_code_node(code_body + "async def execute(d, p, c):\n    return 1", "n1")
    assert not r.ok and r.error_code == "CODE_NODE_FORBIDDEN"
    assert r.details.get("forbidden_names")


@pytest.mark.parametrize("expr", [
    "eval('1')",
    "exec('x=1')",
    "compile('1', '<s>', 'eval')",
    "open('/etc/passwd')",
    "getattr(context, 'x')",
    "setattr(context, 'x', 1)",
    "globals()",
    "locals()",
    "vars()",
    "__import__('os')",
])
def test_forbidden_builtins(expr):
    r = compile_code_node(f"async def execute(d, p, c):\n    return {expr}", "n1")
    assert not r.ok and r.error_code == "CODE_NODE_FORBIDDEN"


@pytest.mark.parametrize("expr", [
    "().__class__",
    "().__class__.__bases__",
    "type(1).__subclasses__()",
    "execute.__globals__",
    "execute.__code__",
    "context.__dict__",
    "{}['__class__']",
])
def test_forbidden_introspection(expr):
    r = compile_code_node(f"async def execute(d, p, c):\n    return {expr}", "n1")
    assert not r.ok and r.error_code == "CODE_NODE_FORBIDDEN"


def test_screen_off_still_compiles_forbidden():
    # screen=False is for internal use only; it must still compile but not screen.
    r = compile_code_node(
        "import os\nasync def execute(d, p, c):\n    return 1", "n1", screen=False
    )
    assert r.ok


def test_allowed_imports_extensible():
    r = compile_code_node(
        "import numpy\nasync def execute(d, p, c):\n    return 1",
        "n1",
        allowed_imports=set(DEFAULT_ALLOWED_IMPORTS) | {"numpy"},
    )
    assert r.ok


def test_pure_compute_imports_allowed():
    for mod in ("math", "statistics", "json", "datetime", "collections", "itertools"):
        r = compile_code_node(
            f"import {mod}\nasync def execute(d, p, c):\n    return 1", "n1"
        )
        assert r.ok, f"{mod} should be allowed"


# ── build_restricted_builtins ──────────────────────────────────────────────

def test_restricted_builtins_omit_dangerous():
    b = build_restricted_builtins()
    for name in ("eval", "exec", "compile", "open", "getattr", "setattr",
                 "delattr", "globals", "locals", "vars", "input"):
        assert name not in b, f"{name} must not be in restricted builtins"
    for name in ("len", "range", "dict", "list", "sum", "min", "max", "print",
                 "isinstance", "enumerate", "sorted", "__import__"):
        assert name in b, f"{name} must be in restricted builtins"


def test_restricted_import_blocks_and_allows():
    b = build_restricted_builtins()
    with pytest.raises(ImportError):
        b["__import__"]("os")
    with pytest.raises(ImportError):
        b["__import__"]("socket")
    assert b["__import__"]("math") is not None


# ── CodeNode schema / ports ────────────────────────────────────────────────

def test_default_output_is_result_port():
    node = CodeNode(id="c", code="async def execute(d,p,c):\n    return 1")
    ports = node.get_outputs()
    assert [p.name for p in ports] == ["result"]


def test_declared_outputs_reflected():
    node = CodeNode(
        id="c",
        code="async def execute(d,p,c):\n    return {'a': 1, 'b': 2}",
        outputs=[{"name": "a", "type": "number"}, {"name": "b", "type": "string"}],
    )
    ports = node.get_outputs()
    assert [p.name for p in ports] == ["a", "b"]
    assert [p.type for p in ports] == ["number", "string"]


def test_code_node_registered_category_data():
    schema = NodeTypeRegistry().get_schema("CodeNode", locale="en")
    assert schema is not None
    assert schema.category == "data"
    assert not schema.display_name.startswith("i18n:")


def test_codenode_allowed_imports_surface_no_drift():
    """AI 챗봇에 노출되는 샌드박스 화이트리스트는 DEFAULT_ALLOWED_IMPORTS 에서
    파생돼야 하며(손 복사 금지), 상수가 바뀌었는데 스키마 표면이 stale 리터럴을
    하드코딩하면 이 테스트가 실패한다(단일 진실원천 가드).
    """
    from programgarden_core.code_node import DEFAULT_ALLOWED_IMPORTS

    expected_sorted = sorted(DEFAULT_ALLOWED_IMPORTS)
    expected_csv = ", ".join(expected_sorted)

    schema = NodeTypeRegistry().get_schema("CodeNode")
    assert schema is not None

    # 1. PRIMARY: 구조화 화이트리스트가 상수와 정확히 일치(원소 + 정렬순서).
    assert schema.node_guide["allowed_imports"] == expected_sorted
    # import_policy 프로즈에 hand-roll 계약 명시.
    assert "CODE_NODE_FORBIDDEN" in schema.node_guide["import_policy"]

    # 2. 'code' 필드 help_text 가 부분 목록이 아니라 전체 파생 목록을 담는다.
    assert expected_csv in schema.config_schema["code"]["help_text"]

    # 3. pitfalls 중 최소 하나가 전체 파생 목록을 담는다(프로즈 드리프트 가드).
    assert any(expected_csv in p for p in schema.node_guide["pitfalls"])

    # 4. 비-stdlib → 직접구현 계약이 대표 라이브러리에 대해 명시적.
    anti_blob = " ".join(
        ap["pattern"] + ap["reason"] + ap["alternative"]
        for ap in (schema.anti_patterns or [])
    )
    for lib in ("numpy", "pandas", "scipy", "pandas-ta", "TA-Lib"):
        assert lib in anti_blob, f"missing '{lib}' hand-roll guidance"
