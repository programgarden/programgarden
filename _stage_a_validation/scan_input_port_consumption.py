#!/usr/bin/env python
"""Input-side declaration==runtime scan.

The 1.28.0 contract tests only checked OUTPUT ports. This scans the mirror:
does the executor actually READ each DECLARED input port/field? A declared
input port whose name never appears in the executor source is a dead port
(the `symbol` bug class). Heuristic — reports candidates for manual review.
"""
import inspect
import re
import sys

import programgarden_community  # noqa: F401
from programgarden.executor import WorkflowExecutor
from programgarden_core.registry.node_registry import NodeTypeRegistry

wx = WorkflowExecutor()
executors = wx._executors

# node_type -> declared input port names
reg = NodeTypeRegistry()
try:
    node_types = reg.list_all() if hasattr(reg, "list_all") else reg.all()
except Exception:
    node_types = None

# Control-flow / framework-consumed port names: delivered via edges, not read
# by name in executor source. Excluded to cut false positives.
FRAMEWORK_PORTS = {"trigger", "item", "data", "input", "connection"}

def declared_inputs(node_cls):
    names = set()
    inp = getattr(node_cls, "_inputs", None)
    # Pydantic private attr on the class → unwrap .default to the list
    if inp is not None and inp.__class__.__name__ == "ModelPrivateAttr":
        inp = getattr(inp, "default", None)
    if inp:
        try:
            for p in inp:
                n = getattr(p, "name", None) or (p.get("name") if isinstance(p, dict) else None)
                ptype = getattr(p, "type", None) or (p.get("type") if isinstance(p, dict) else None)
                if n and n not in FRAMEWORK_PORTS and ptype != "trigger":
                    names.add(n)
        except TypeError:
            pass
    return names

# Build node_type -> class map via registry.get
type_to_cls = {}
for nt in executors:
    try:
        c = reg.get(nt)
        if c:
            type_to_cls[nt] = c
    except Exception:
        pass

src_cache = {}
def exec_source(ex):
    cls = type(ex)
    if cls not in src_cache:
        try:
            src_cache[cls] = inspect.getsource(cls)
        except Exception:
            src_cache[cls] = ""
    return src_cache[cls]

violations = []  # (node_type, executor_class, [dead_ports])
checked = 0
for nt, ex in sorted(executors.items()):
    exclass = type(ex).__name__
    if exclass == "GenericNodeExecutor":
        continue  # passthrough — consumes config generically
    cls = type_to_cls.get(nt)
    if cls is None:
        try:
            cls = reg.get(nt)
        except Exception:
            cls = None
    if cls is None:
        continue
    inputs = declared_inputs(cls)
    if not inputs:
        continue
    checked += 1
    src = exec_source(ex)
    dead = []
    for name in sorted(inputs):
        # consumed if referenced as a string literal (config.get("x") / get_output(..,"x") / "x" in config)
        if re.search(rf'["\']{re.escape(name)}["\']', src):
            continue
        dead.append(name)
    if dead:
        violations.append((nt, exclass, dead))

print(f"checked {checked} node types with declared input ports\n")
if not violations:
    print("✅ no declared input ports appear unreferenced in their executor source")
else:
    print(f"🔴 {len(violations)} node types have declared input port(s) NOT referenced in executor source:")
    for nt, exclass, dead in violations:
        print(f"  - {nt:42s} [{exclass}]  dead: {dead}")
