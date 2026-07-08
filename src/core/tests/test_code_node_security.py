"""CodeNode sandbox-escape regression tests.

Every case here is a bypass an adversarial audit REPRODUCED against an earlier
version of the screener (RCE / credential exfiltration). They must stay blocked.

Reminder (see code_node.py SECURITY POSTURE): this screen is hardened
defense-in-depth, NOT a proven sandbox. These tests guard against regressions of
the *known* vectors; true containment of hostile code is an OS-level concern.
"""
import pytest

from programgarden_core.code_node import (
    compile_code_node,
    build_restricted_builtins,
    DEFAULT_ALLOWED_IMPORTS,
)


def _screen(code: str):
    return compile_code_node(code, "sec", screen=True)


# ── getattr / attribute-walk substitutes ───────────────────────────────────

@pytest.mark.parametrize("code", [
    # operator.attrgetter / methodcaller are getattr/dispatch substitutes.
    "import operator\ndef execute(d, p, c):\n    return operator.attrgetter('x')(d)",
    "import operator\ndef execute(d, p, c):\n    return operator.methodcaller('x')(d)",
    # direct getattr / vars / globals
    "def execute(d, p, c):\n    return getattr(c, 'x')",
    "def execute(d, p, c):\n    return vars(c)",
    "def execute(d, p, c):\n    return globals()",
])
def test_getattr_substitutes_blocked(code):
    assert _screen(code).error_code == "CODE_NODE_FORBIDDEN"


# ── module attribute re-exports (os/sys reachable via allowed modules) ──────

@pytest.mark.parametrize("code", [
    "import random\ndef execute(d, p, c):\n    return random._os.system('id')",
    "import random\ndef execute(d, p, c):\n    return random._urandom(8)",
    "import uuid\ndef execute(d, p, c):\n    return uuid.os.system('id')",
    "import statistics\ndef execute(d, p, c):\n    return statistics.sys.modules['os']",
    "import datetime\ndef execute(d, p, c):\n    return datetime.sys",
])
def test_module_reexport_escape_blocked(code):
    assert _screen(code).error_code == "CODE_NODE_FORBIDDEN"


# ── object-graph walk via dunders / type() ─────────────────────────────────

@pytest.mark.parametrize("code", [
    "def execute(d, p, c):\n    return ().__class__.__bases__[0].__subclasses__()",
    "def execute(d, p, c):\n    return type(()).__subclasses__()",
    "def execute(d, p, c):\n    return type(()).mro()",
    "def execute(d, p, c):\n    return execute.__globals__",
    "def execute(d, p, c):\n    return execute.__code__",
    "def execute(d, p, c):\n    return c.__dict__",
])
def test_object_graph_walk_blocked(code):
    assert _screen(code).error_code == "CODE_NODE_FORBIDDEN"


# ── string-obfuscated attribute access (subscript / str.format / f-string) ──

@pytest.mark.parametrize("code", [
    "def execute(d, p, c):\n    return d['__class__']",
    "def execute(d, p, c):\n    return '{0.__class__}'.format(d)",
    "import statistics\ndef execute(d, p, c):\n    return '{0.sys}'.format(statistics)",
    "import statistics\ndef execute(d, p, c):\n    return f'{statistics.sys}'",
    "def execute(d, p, c):\n    return '_os'",           # would feed a getattr substitute
    "def execute(d, p, c):\n    return '__class__'",
])
def test_string_attribute_obfuscation_blocked(code):
    assert _screen(code).error_code == "CODE_NODE_FORBIDDEN"


# ── shell / process / network reachability ─────────────────────────────────

@pytest.mark.parametrize("code", [
    "import os\ndef execute(d, p, c):\n    return os.environ",
    "def execute(d, p, c):\n    return open('/etc/passwd').read()",
    "import subprocess\ndef execute(d, p, c):\n    return subprocess.run(['id'])",
])
def test_direct_os_paths_blocked(code):
    assert _screen(code).error_code == "CODE_NODE_FORBIDDEN"


# ── legitimate compute must survive the hardening ──────────────────────────

@pytest.mark.parametrize("code", [
    "import statistics\nasync def execute(data, params, context):\n    return {'m': statistics.mean(data)}",
    "import math\nasync def execute(data, params, context):\n    return {'r': [math.sqrt(x) for x in data]}",
    "import json\nasync def execute(data, params, context):\n    return {'j': json.dumps({'n': 1})}",
    "import collections\nasync def execute(data, params, context):\n    return {'c': dict(collections.Counter(data))}",
    # helper namespaces on the scrubbed context (public attrs, no underscore)
    "async def execute(data, params, context):\n    return {'p': context.finance.pct_change(100, 110)}",
    # defining a class with __init__ is fine (FunctionDef name, not attr access)
    "async def execute(data, params, context):\n    class P:\n        def __init__(self, v):\n            self.v = v\n    return {'v': P(1).v}",
])
def test_legitimate_compute_allowed(code):
    assert _screen(code).ok, _screen(code).message


def test_operator_and_uuid_no_longer_whitelisted():
    assert "operator" not in DEFAULT_ALLOWED_IMPORTS
    assert "uuid" not in DEFAULT_ALLOWED_IMPORTS


def test_restricted_builtins_have_no_getattr_family():
    b = build_restricted_builtins()
    for n in ("getattr", "setattr", "delattr", "eval", "exec", "compile", "open", "globals", "vars"):
        assert n not in b
