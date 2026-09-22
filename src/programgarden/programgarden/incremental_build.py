"""Server-owned node admission and fresh cumulative replay coordinator.

Persistence/ownership/CAS are enforced by the host service. This module contains
the same deterministic state machine for the library, API, imports and AI tools.
Only run_pending/finalize can produce VERIFIED/READY; request handlers must not
accept these states or receipts from a model or end-user request.
"""
from __future__ import annotations

import asyncio
import ast
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import importlib.metadata
import importlib.util
import hashlib
import json
from pathlib import Path
from typing import Any

from programgarden.replay_contracts import ContractViolation, finite_json
from programgarden.validation_replay import content_hash, replay, VALIDATOR_VERSION, CONTRACT_VERSION
from programgarden.replay_scenarios import check_final_expectations, scenario_receipt


class BuildGateError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def runtime_identity() -> str:
    """Identify actual implementations and computation dependencies.

    A changed plugin/schema/shared module in an editable checkout must invalidate
    proof even before a version bump. Dependency versions matter too: matching
    engine source alone does not prove equivalent numpy/pandas behavior.
    """
    sources = {}
    for module in ("programgarden", "programgarden_core", "programgarden_community", "programgarden_finance"):
        root = Path(importlib.util.find_spec(module).origin).parent
        sources[module] = {str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in sorted(root.rglob("*.py"))}
    packages = {}
    for name in ("programgarden", "programgarden-core", "programgarden-community", "programgarden-finance",
                 "pydantic", "pydantic-core", "numpy", "pandas", "scipy", "tzdata", "pytz", "croniter", "aiosqlite",
                 "pyportfolioopt", "quantstats", "scikit-learn", "statsmodels"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return content_hash({"source": sources, "packages": packages})


def dependencies(graph: dict[str, Any], node_id: str) -> set[str]:
    return {e["from"].split(".")[0] for e in graph.get("edges", [])
            if e["to"].split(".")[0] == node_id}


def binding_dependencies(node: dict[str, Any]) -> set[str]:
    from programgarden_core.expression import ExpressionEvaluator
    refs = set()
    def visit(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key not in {"code","description","name","position"}:
                    visit(item)
        elif isinstance(value,list):
            for item in value: visit(item)
        elif isinstance(value,str):
            for match in ExpressionEvaluator.EXPRESSION_PATTERN.finditer(value):
                try:
                    tree = ast.parse(match.group(1),mode="eval")
                except SyntaxError as exc:
                    raise BuildGateError("BUILD_EXPRESSION_INVALID", "Repair the expression before admitting its node") from exc
                resolved_names = set()
                for part in ast.walk(tree):
                    if isinstance(part,ast.Attribute) and isinstance(part.value,ast.Name) and part.value.id=="nodes":
                        refs.add(part.attr); resolved_names.add(id(part.value))
                    if isinstance(part,ast.Subscript) and isinstance(part.value,ast.Name) and part.value.id=="nodes":
                        if not isinstance(part.slice,ast.Constant) or type(part.slice.value) is not str:
                            raise BuildGateError("BUILD_DEPENDENCY_DYNAMIC", "Use a stable explicit node reference")
                        refs.add(part.slice.value); resolved_names.add(id(part.value))
                if any(isinstance(part,ast.Name) and part.id=="nodes" and id(part) not in resolved_names for part in ast.walk(tree)):
                    raise BuildGateError("BUILD_DEPENDENCY_DYNAMIC", "Use explicit node dependencies instead of the whole graph")
    visit(node)
    return refs


def ancestors(graph: dict[str,Any], node_id: str) -> set[str]:
    found = set()
    pending = list(dependencies(graph,node_id))
    while pending:
        parent = pending.pop()
        if parent in found: continue
        found.add(parent)
        pending.extend(dependencies(graph,parent))
    return found


def _prefix(graph: dict[str, Any], selected: set[str]) -> dict[str, Any]:
    return {**deepcopy(graph), "nodes": [deepcopy(n) for n in graph["nodes"] if n["id"] in selected],
            "edges": [deepcopy(e) for e in graph.get("edges", [])
                      if e["from"].split(".")[0] in selected and e["to"].split(".")[0] in selected]}


@dataclass
class BuildWorkspace:
    task_id: str
    plan_revision: int
    graph: dict[str, Any]
    fixtures: list[dict[str, Any]]
    revision: int = 0
    states: dict[str, str] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)
    status: str = "BUILDING"
    runtime: str = field(default_factory=runtime_identity)
    max_attempts: int = 6

    def __post_init__(self):
        if not isinstance(self.fixtures, list) or len(self.fixtures) > 16 or any(not isinstance(f, dict) for f in self.fixtures):
            raise BuildGateError("BUILD_FIXTURE_INVALID", "Fixtures must be a bounded array of scenario objects")
        # Never retain aliases to a caller's snapshot or a previously loaded
        # revision. The worker owns this mutable working state.
        for key in ("graph", "fixtures", "states", "evidence", "attempts"):
            value = deepcopy(getattr(self, key))
            finite_json(value, key)
            setattr(self, key, value)
        if type(self.plan_revision) is not int or self.plan_revision < 1:
            raise BuildGateError("BUILD_PLAN_REVISION_INVALID", "A positive execution plan revision is required")
        if type(self.revision) is not int or self.revision < 0:
            raise BuildGateError("BUILD_REVISION_CONFLICT", "Invalid workspace revision")
        if not 1 <= self.max_attempts <= 6 or len(self.graph.get("nodes", [])) > 64 or len(self.fixtures) > 16:
            raise BuildGateError("BUILD_BUDGET_INVALID", "Build size or retry budget exceeds the supported limit")
        if {n["id"] for n in self.graph.get("nodes", [])} != set(self.states):
            raise BuildGateError("BUILD_STATE_INVALID", "Each stored node must have a server-owned state")

    def _invalidate(self, node_ids: set[str]):
        affected = set(node_ids)
        while True:
            extra = {n for n in self.states if dependencies(self.graph, n) & affected}
            if extra <= affected:
                break
            affected |= extra
        for node_id in affected:
            self.states[node_id] = "STALE"
            self.evidence.pop(node_id, None)
        self.status = "STALE"


    def _revision(self, expected: int):
        if expected != self.revision:
            raise BuildGateError("BUILD_REVISION_CONFLICT", "Reload the owned workspace before editing")
        if self.runtime != runtime_identity():
            self.states = {node: "STALE" for node in self.states}
            self.evidence.clear()
            self.status = "STALE"
            self.runtime = runtime_identity()
            self.revision += 1
            raise BuildGateError("BUILD_RUNTIME_CHANGED", "Revalidate nodes after the engine or contract changed")

    def add_node(self, node: dict[str, Any], edges: list[dict[str, Any]], *, expected_revision: int):
        self._revision(expected_revision)
        if len(self.states) >= 64:
            raise BuildGateError("BUILD_NODE_LIMIT", "A build supports at most 64 nodes")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id or node_id in self.states:
            raise BuildGateError("BUILD_NODE_ID_INVALID", "Use a new stable node ID; repair existing nodes explicitly")
        if any(e.get("to", "").split(".")[0] != node_id for e in edges):
            raise BuildGateError("BUILD_EDGE_SCOPE", "An addition may attach only incoming edges of that node")
        parents = {e.get("from", "").split(".")[0] for e in edges}
        if any(self.states.get(parent) != "VERIFIED" for parent in parents):
            raise BuildGateError("BUILD_DEPENDENCY_UNVERIFIED", "Verify every upstream node before adding this dependency")
        if self.graph.get("nodes") and not parents:
            raise BuildGateError("BUILD_DEPENDENCY_REQUIRED", "Attach the new node to its verified upstream nodes")
        candidate = {**self.graph,"edges":[*self.graph.get("edges",[]),*edges]}
        refs = binding_dependencies(node)
        if any(self.states.get(ref)!="VERIFIED" for ref in refs):
            raise BuildGateError("BUILD_DEPENDENCY_UNVERIFIED", "Verify every referenced node before adding this dependency")
        if not refs <= ancestors(candidate,node_id):
            raise BuildGateError("BUILD_DEPENDENCY_EDGE_REQUIRED", "Connect every expression source through an upstream path")
        self.graph.setdefault("nodes", []).append(deepcopy(node))
        self.graph.setdefault("edges", []).extend(deepcopy(edges))
        self.states[node_id] = "BUILT"
        self.status = "BUILDING"
        self.revision += 1

    def repair_node(self, node: dict[str, Any], *, expected_revision: int):
        self._revision(expected_revision)
        node_id = node.get("id")
        if node_id not in self.states:
            raise BuildGateError("BUILD_NODE_NOT_FOUND", "Select an existing node for repair")
        self.graph["nodes"] = [deepcopy(node) if n["id"] == node_id else n for n in self.graph["nodes"]]
        self._invalidate({node_id})
        self.states[node_id] = "BUILT"
        self.status = "BUILDING"
        self.revision += 1

    def replace_incoming_edges(self, node_id: str, edges: list[dict[str, Any]], *, expected_revision: int):
        self._revision(expected_revision)
        if node_id not in self.states:
            raise BuildGateError("BUILD_NODE_NOT_FOUND", "Select an existing node")
        if any(e.get("to", "").split(".")[0] != node_id for e in edges):
            raise BuildGateError("BUILD_EDGE_SCOPE", "Repair only this node's incoming edges")
        parents = {e.get("from", "").split(".")[0] for e in edges}
        if node_id in parents or not parents <= self.states.keys():
            raise BuildGateError("BUILD_EDGE_SCOPE", "Every source must be a different existing node")
        candidate = deepcopy(self.graph)
        candidate["edges"] = [e for e in candidate.get("edges", []) if e["to"].split(".")[0] != node_id] + deepcopy(edges)
        # Reject cycles before committing the graph or invalidating evidence.
        remaining = set(self.states)
        while remaining:
            roots = {n for n in remaining if not dependencies(candidate, n) & remaining}
            if not roots:
                raise BuildGateError("BUILD_GRAPH_CYCLE", "A build graph must be acyclic")
            remaining -= roots
        self.graph = candidate
        self._invalidate({node_id})
        self.revision += 1

    def replan(self, plan_revision: int, *, expected_revision: int):
        self._revision(expected_revision)
        if type(plan_revision) is not int or plan_revision <= self.plan_revision:
            raise BuildGateError("BUILD_PLAN_REVISION_INVALID", "Select a newer owned execution plan revision")
        self.plan_revision = plan_revision
        self._invalidate(set(self.states))
        self.revision += 1

    def replace_fixtures(self, fixtures: list[dict[str, Any]], *, expected_revision: int):
        self._revision(expected_revision)
        if not isinstance(fixtures, list) or len(fixtures) > 16 or any(not isinstance(f, dict) for f in fixtures):
            raise BuildGateError("BUILD_FIXTURE_INVALID", "Fixtures must be a bounded array of scenario objects")
        finite_json(fixtures, "fixtures")
        if content_hash(self.fixtures) == content_hash(fixtures):
            return
        self.fixtures = deepcopy(fixtures)
        self.states = {n: "STALE" for n in self.states}
        self.evidence.clear()
        self.status = "STALE" if fixtures else "BLOCKED"
        self.revision += 1

    async def run_pending(self, node_id: str, *, expected_revision: int, timeout: float = 30):
        self._revision(expected_revision)
        if node_id not in self.states:
            raise BuildGateError("BUILD_NODE_NOT_FOUND", "Select a built node")
        if any(self.states.get(n) != "VERIFIED" for n in dependencies(self.graph, node_id)):
            raise BuildGateError("BUILD_DEPENDENCY_UNVERIFIED", "Repair and verify upstream nodes first")
        target = next(n for n in self.graph["nodes"] if n["id"]==node_id)
        refs = binding_dependencies(target)
        if not refs <= ancestors(self.graph,node_id) or any(self.states.get(ref)!="VERIFIED" for ref in refs):
            raise BuildGateError("BUILD_DEPENDENCY_UNVERIFIED", "Verify and connect every referenced input before execution")
        if not self.fixtures:
            self.states[node_id] = "BLOCKED"
            self.status = "BLOCKED"
            self.revision += 1
            raise BuildGateError("BUILD_FIXTURE_REQUIRED", "A reproducible fixture suite is required")
        if self.attempts.get(node_id, 0) >= self.max_attempts:
            self.states[node_id] = "BLOCKED"
            self.status = "BLOCKED"
            self.revision += 1
            raise BuildGateError("BUILD_REPAIR_LIMIT", "Validation budget exhausted; review the saved failure")
        if self.states[node_id] == "VALIDATING":
            raise BuildGateError("BUILD_VALIDATION_BUSY", "This node already has a validation claim")
        self.attempts[node_id] = self.attempts.get(node_id, 0) + 1
        self.states[node_id] = "VALIDATING"
        self.revision += 1
        revision = self.revision
        selected = {n for n, state in self.states.items() if state == "VERIFIED"} | {node_id}
        graph = _prefix(self.graph, selected)
        node_graph = _prefix(graph, ancestors(graph, node_id) | {node_id})
        identity = {"task_id": self.task_id, "plan_revision": self.plan_revision,
                    "workflow_revision": revision, "graph_hash": content_hash(graph),
                    "node_hash": content_hash(next(n for n in graph["nodes"] if n["id"] == node_id)),
                    "fixture_hash": content_hash(self.fixtures), "runtime_hash": self.runtime,
                    "contract_version": CONTRACT_VERSION, "validator_version": VALIDATOR_VERSION,
                    "mode": "SIMULATION", "live_authorized": False}
        runs, failure, reached = [], None, False
        try:
            for fixture in deepcopy(self.fixtures):
                standalone = await replay(node_graph, fixture, timeout=timeout, node_under_test=node_id)
                assessed = scenario_receipt(standalone,fixture,node_graph)
                runs.append({"stage": "node", **asdict(standalone), **assessed})
                if not assessed["scenario_passed"]:
                    failure = standalone.errors + assessed["scenario_errors"]
                    break
                chain = await replay(graph, fixture, timeout=timeout)
                assessed = scenario_receipt(chain,fixture,graph)
                runs.append({"stage": "chain", **asdict(chain), **assessed})
                if not assessed["scenario_passed"]:
                    failure = chain.errors + assessed["scenario_errors"]
                    break
                reached |= node_id in chain.executed
        except BaseException:
            if self.revision == revision:
                self.states[node_id] = "BLOCKED"
                self.status = "BLOCKED"
                self.evidence.pop(node_id, None)
                self.revision += 1
            raise
        if (self.revision != revision or self.runtime != runtime_identity()
                or content_hash(_prefix(self.graph, selected)) != identity["graph_hash"]
                or content_hash(self.fixtures) != identity["fixture_hash"]
                or self.plan_revision != identity["plan_revision"]):
            raise BuildGateError("BUILD_RESULT_STALE", "The candidate changed while validation was running")
        if not failure and not reached:
            failure = [{"code": "BUILD_BRANCH_UNCOVERED", "message": "No fixture exercised this node in its actual chain"}]
        self.states[node_id] = "FAILED" if failure else "VERIFIED"
        self.status = "FAILED" if failure else "BUILDING"
        self.evidence[node_id] = {**identity, "passed": not failure, "errors": failure or [], "runs": runs}
        self.revision += 1
        return deepcopy(self.evidence[node_id])

    async def finalize(self, *, expected_revision: int, timeout: float = 30):
        self._revision(expected_revision)
        if not self.states or any(s != "VERIFIED" for s in self.states.values()):
            raise BuildGateError("BUILD_NOT_VERIFIED", "Every required node must be verified before final replay")
        revision = self.revision
        plan_revision, fixture_hash = self.plan_revision, content_hash(self.fixtures)
        states_hash = content_hash(self.states)
        # Serialization and a fresh load are mandatory; no in-memory result reuse.
        graph = json.loads(json.dumps(self.graph, allow_nan=False))
        results = []
        for fixture in deepcopy(self.fixtures):
            result = await replay(graph, fixture, timeout=timeout)
            assessed = scenario_receipt(result,fixture,graph)
            if assessed["scenario_passed"]:
                try:
                    check_final_expectations(result,fixture,graph)
                except ContractViolation as exc:
                    assessed["scenario_passed"] = False
                    assessed["scenario_errors"].append(exc.as_dict())
            results.append({**asdict(result),**assessed})
        if (self.revision != revision or self.runtime != runtime_identity()
                or self.plan_revision != plan_revision or content_hash(self.graph) != content_hash(graph)
                or content_hash(self.fixtures) != fixture_hash or content_hash(self.states) != states_hash):
            raise BuildGateError("BUILD_RESULT_STALE", "The saved candidate changed during final replay")
        passed = bool(results) and all(r["scenario_passed"] for r in results)
        self.status = "READY" if passed else "FAILED"
        self.revision += 1
        return {"passed": passed, "graph_hash": content_hash(graph), "runtime_hash": self.runtime,
                "fixture_hash": content_hash(self.fixtures), "runs": results, "live_authorized": False}
