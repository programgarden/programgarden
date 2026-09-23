"""Credential-free deterministic execution using the real workflow scheduler.

This runner is for an isolated validation worker, never a live account process.
Only explicitly listed computation nodes execute. External nodes require exact
recorded fixtures; unsupported capabilities block. Deep-validation's synthetic
condition/filter passes are deliberately not used as replay evidence.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

from programgarden.context import ExecutionContext
from programgarden.executor import WorkflowExecutor, WorkflowJob, CodeNodeError
from programgarden.replay_order_adapter import ORDER_NODES, ReplayOrders
from programgarden.replay_contracts import CONTRACT_VERSION, ContractViolation, check_contract, finite_json
from programgarden.replay_sources import SOURCE_NODES

VALIDATOR_VERSION = "incremental-replay-3"
COMPUTATION_NODES = frozenset({
    "StartNode", "WatchlistNode", "SymbolFilterNode", "ExclusionListNode",
    "ConditionNode", "LogicNode", "IfNode", "CodeNode", "PositionSizingNode",
    "PortfolioNode", "BenchmarkCompareNode", "BacktestEngineNode",
    "SplitNode", "AggregateNode", "ThrottleNode",
    "FieldMappingNode", "PerformanceReportNode", "TableDisplayNode", "LineChartNode",
    "MultiLineChartNode", "CandlestickChartNode", "BarChartNode", "SummaryDisplayNode",
})
# Fixtures replace I/O boundaries, never calculation nodes or arbitrary unknown
# implementations. Add an external type only with its explicit contract tests.
FIXTURE_NODES = frozenset({
    f"{product}{kind}Node"
    for product in ("OverseasStock", "OverseasFutures", "KoreaStock")
    for kind in ("Broker", "Account", "RealAccount", "MarketData", "HistoricalData",
                 "Fundamental", "SymbolQuery", "OpenOrders", "RealMarketData", "RealOrderEvent")
    if not (product == "OverseasFutures" and kind == "Fundamental")
}) | {"HTTPRequestNode", "LLMModelNode", "AIAgentNode", "MarketStatusNode", "CurrencyRateNode", "TelegramNode"}


def content_hash(value: Any) -> str:
    finite_json(value)
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


# The live runtime (node_runner) and this replay treat a top-level `error` value,
# and a top-level `reason` in this set, as a node failure. They are therefore
# reserved output-key names: a CodeNode must not declare a port called `error`
# or `reason`, or its own successful result reads as an engine failure.
_RESERVED_OUTPUT_KEYS = ("error", "reason")
_INVALID_INPUT_REASONS = ("no_symbol", "no_price", "invalid_input")
_RESERVED_PREVIEW_LIMIT = 200


def _reserved_key_detail(key: str, value: Any, node_type: str, config: dict) -> dict[str, Any]:
    """Secret-free evidence for a reserved-key failure: the node's own output.

    ``value`` is the node's declared output text, never a credential; it is
    length-bounded so a large payload cannot bloat the diagnostic.
    """
    if isinstance(value, str):
        text = value
    elif value is None:
        text = "None"  # a present `error: None` key still fails; show it plainly
    else:
        text = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(text) > _RESERVED_PREVIEW_LIMIT:
        text = text[:_RESERVED_PREVIEW_LIMIT] + "…(truncated)"
    declared = node_type == "CodeNode" and any(
        isinstance(port, dict) and port.get("name") == key for port in (config.get("outputs") or []))
    return {"reserved_key": key, "value": text, "declared_output_port": declared}


def _reserved_key_message(key: str, reason: str | None = None) -> str:
    hint = ("a declared CodeNode output port must not be named `error` or `reason` "
            "(both are reserved); rename it and report status inside a nested object")
    if key == "reason":
        return (f"Invalid computation input: {reason}. The engine reserves a top-level "
                f"`reason` of {'/'.join(_INVALID_INPUT_REASONS)} as invalid input, so {hint}.")
    return ("Node reported an execution error: the engine treats a top-level `error` output "
            f"value as a node failure, so {hint}.")


@dataclass
class ReplayResult:
    passed: bool
    graph_hash: str
    fixture_hash: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    outputs: dict[str, Any] = field(default_factory=dict)
    executed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    mode: str = "SIMULATION"
    validator_version: str = VALIDATOR_VERSION
    contract_version: str = CONTRACT_VERSION
    live_authorized: bool = False
    simulation: dict[str, Any] = field(default_factory=dict)
    node_states: dict[str, str] = field(default_factory=dict)
    order_observations: list[dict[str, Any]] = field(default_factory=list)
    setup_executed: list[str] = field(default_factory=list)
    node_under_test: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


class ReplayContext(ExecutionContext):
    is_replay_validation = True
    validation_as_of = None

    def get_expression_context(self):
        from programgarden_core.expression.evaluator import DateNamespace
        value = super().get_expression_context()
        if self.validation_as_of is not None:
            value.variables["date"] = DateNamespace(as_of=self.validation_as_of)
        return value

    def record_deep_unresolved_binding(self, node_id, expression, reason):
        # Preserve unresolved evidence while is_deep_validate remains false, so
        # actual conditions and set operations are not forced to pass.
        entry = {"node_id": node_id, "expression": expression, "reason": reason}
        if entry not in self._deep_unresolved_bindings:
            self._deep_unresolved_bindings.append(entry)


class ReplayJob(WorkflowJob):
    async def _save_checkpoint(self):
        # Validation never reads or writes a running strategy's execution DB.
        return None

    async def _auto_iterate_pacing_sleep(self, node_id, node_type):
        return None

    def _rate_limit_now(self):
        from programgarden.replay_triggers import fixture_instant
        return fixture_instant(self.context, "rate_limit")

    def _guard_whole_array_reevaluation(self, node_id, node_type, config, item, total):
        # Do not silently narrow input to make a replay succeed. The real I/O
        # adapter selects its per-item fixture; computation retains actual input.
        return config

    def _auto_inject_connection(self, node_id, node, config):
        config = super()._auto_inject_connection(node_id, node, config)
        if node.node_type == "ScreenerNode":
            from programgarden.executor import ScreenerNodeExecutor
            connection, _ = ScreenerNodeExecutor.resolve_connection(
                self.context, node_id, config.get("market", "auto"), config.get("connection"))
            if connection:
                config = {**config, "connection": connection}
        return config

    def _resolve_config_expressions(self, config, node_id=None):
        from programgarden_core.expression import ExpressionEvaluator
        ordinary, deferred = {}, {}
        for key, value in config.items():
            if key in ("items", "code") or (self.context._iteration_item is None and self._references_iteration_item(value)):
                deferred[key] = value
            else:
                ordinary[key] = value
        failures = []
        def record(expr, exc):
            failures.append((expr, str(exc)))
        result = ExpressionEvaluator(self.context.get_expression_context()).evaluate_fields(ordinary, on_error=record)
        if failures:
            raise ContractViolation(str(node_id), f"Unresolved mapping: {failures[0][0]}")
        result.update(deferred)
        return result


class ReplayExecutor(WorkflowExecutor):
    def __init__(self, fixture, outcome):
        super().__init__()
        self.fixture, self.outcome = fixture, outcome
        self.orders = None

    async def execute_node(self, node_id, node_type, config, context, **kwargs):
        if self.outcome.errors:
            raise ContractViolation(node_id, "Replay stopped at the first failed boundary", "REPLAY_DEPENDENCY_BLOCKED")
        self.outcome.executed.append(node_id)
        try:
            from programgarden_core import NodeTypeRegistry
            from pydantic import ValidationError
            node_class = NodeTypeRegistry().get(node_type)
            if node_class is None:
                raise ContractViolation(node_id,"Unknown node type")
            candidate = {"id":node_id,**config}
            if kwargs.get("plugin") is not None:
                plugin = kwargs["plugin"]
                candidate["plugin"] = plugin.id if hasattr(plugin,"id") else str(plugin)
            if kwargs.get("fields"):
                candidate["fields"] = kwargs["fields"]
            try:
                # JSON-mode strict validation permits schema enums/date strings
                # while refusing numeric/string/boolean coercion at the boundary.
                validated_node = node_class.model_validate_json(json.dumps(candidate,allow_nan=False),strict=True)
            except ValidationError as exc:
                first = exc.errors(include_input=False,include_url=False)[0]
                raise ContractViolation(f"{node_id}.input."+".".join(map(str,first["loc"])),first["msg"]) from exc
            rules = self.fixture.get("contracts", {}).get(node_id, {})
            if "input" in rules:
                check_contract(config, rules["input"], f"{node_id}.input")
            if node_type in FIXTURE_NODES:
                from programgarden.replay_external import external_record
                record = external_record(self.fixture, node_id, node_type, config, context)
                if not isinstance(record,dict) or "output" not in record or "contract" not in record:
                    raise ContractViolation(node_id,"No matching per-item I/O fixture/contract","REPLAY_FIXTURE_REQUIRED")
                if "order_events" in record:
                    if self.orders is None or not node_type.endswith(("OpenOrdersNode", "RealOrderEventNode")):
                        raise ContractViolation(node_id,"Completion evidence requires an existing request and broker observation node")
                    self.orders.apply_events(record["order_events"], node_type)
                output = deepcopy(record["output"])
                check_contract(output, record["contract"], f"{node_id}.output")
                if self.orders is not None and node_type.endswith("OpenOrdersNode"):
                    self.orders.check_open_orders(output, node_type)
            elif node_type in SOURCE_NODES:
                from programgarden.replay_sources import execute_source
                output = await execute_source(validated_node, config, self.fixture, context)
            elif node_type in ORDER_NODES:
                if self.orders is None:
                    self.orders = ReplayOrders(self.fixture)
                output = self.orders.execute(node_id,node_type,config,context,
                    invocation_id=kwargs.get("order_invocation_id", "main"),
                    iteration_index=kwargs.get("order_iteration_index"))
                observed = deepcopy(self.orders.last_observation)
                self.outcome.order_observations.append({"node_id":node_id,**observed})
            elif node_type == "SessionGateNode":
                from datetime import datetime
                instant = context.validation_as_of
                if instant is None:
                    raise ContractViolation(node_id, "Session verification requires an explicit fixture clock", "REPLAY_FIXTURE_REQUIRED")
                # Reuse the live node's pure decision, never its wall clock or
                # a manufactured allow result. Every branch shares this instant.
                output = validated_node.evaluate_at(datetime.fromisoformat(instant.replace("Z", "+00:00")))
            elif node_type == "ScheduleNode":
                from programgarden.replay_triggers import schedule_startup
                output = await schedule_startup(validated_node, config, context)
            elif node_type == "TradingHoursFilterNode":
                from programgarden.replay_triggers import trading_hours
                output = trading_hours(validated_node, context)
            elif node_type == "SQLiteNode":
                from programgarden.replay_sqlite import execute_sqlite
                output = await execute_sqlite(node_id, config, context)
            elif node_type in COMPUTATION_NODES:
                # Code source and row extraction expressions have their own
                # evaluator/AST boundary; do not pre-evaluate those payloads.
                output = await super().execute_node(node_id, node_type, config, context, **kwargs)
            else:
                raise ContractViolation(node_id, "No replay adapter for this capability", "REPLAY_CAPABILITY_BLOCKED")
            finite_json(output, f"{node_id}.output")
            if not isinstance(output, dict):
                raise ContractViolation(node_id, "Node reported an execution error")
            # Match the live node_runner rule (`"error" in result`) for computation
            # nodes: a top-level `error` KEY of any value (including None/"") is a
            # failure, so a CodeNode returning {"error": None, ...} fails here just as
            # it would live. Native envelope adapters (FIXTURE/SOURCE/ORDER nodes)
            # legitimately carry `error: None` on success — e.g.
            # OverseasFuturesOrderableQuantityNode returns {"quantity", "verified",
            # "error": None} — so for those we keep the truthy rule.
            error_failed = "error" in output if node_type in COMPUTATION_NODES else bool(output.get("error"))
            if error_failed:
                raise ContractViolation(node_id, _reserved_key_message("error"),
                    detail=_reserved_key_detail("error", output.get("error"), node_type, config))
            if output.get("reason") in _INVALID_INPUT_REASONS:
                raise ContractViolation(node_id, _reserved_key_message("reason", output["reason"]),
                    detail=_reserved_key_detail("reason", output["reason"], node_type, config))
            if "output" in rules:
                check_contract(output, rules["output"], f"{node_id}.output")
            if node_type == "CodeNode":
                for port in config.get("outputs") or []:
                    if port["name"] not in output:
                        raise ContractViolation(f"{node_id}.{port['name']}", "Declared output is absent")
                    kind = port.get("type", "any")
                    if kind != "any":
                        check_contract(output[port["name"]], {"type": kind}, f"{node_id}.{port['name']}")
            return output
        except Exception as exc:
            if isinstance(exc,ContractViolation):
                error = exc.as_dict()
            elif isinstance(exc,CodeNodeError) and exc.details.get("code") in {"REPLAY_CONTRACT_FAILED","REPLAY_CONTRACT_UNSUPPORTED"}:
                error = deepcopy(exc.details)
            else:
                error = {"code":"REPLAY_NODE_FAILED","message":str(exc),"path":node_id}
            self.outcome.errors.append({**error, "node_id": node_id})
            context.stop()
            raise


async def replay(definition: dict[str, Any], fixture: dict[str, Any], *,
                 timeout: float = 30, node_under_test: str | None = None) -> ReplayResult:
    """Run actual scheduler/mappings in disposable state; no silent soft PASS.

    A node check executes its actual upstream setup in the same disposable
    workspace. Output-only snapshots cannot reproduce SQLite or broker state.
    The caller supplies the ancestor subgraph; cumulative/final checks omit
    node_under_test and always start with another fresh workspace.
    An empty branch is not an exception; required activation/output expectations
    belong to the suite and are checked explicitly by the coordinator.
    """
    outcome = ReplayResult(False, content_hash(definition), content_hash(fixture))
    outcome.node_under_test = node_under_test
    runner = ReplayExecutor(fixture, outcome)
    resolved, static = runner.compile(definition)
    if not static.is_valid:
        outcome.errors = [e.model_dump(mode="json") for e in static.errors]
        return outcome
    if node_under_test is not None and node_under_test not in resolved.nodes:
        outcome.errors.append({"code":"REPLAY_NODE_MISSING", "message":"Standalone target is absent"})
        return outcome
    if definition.get("credentials"):
        # Declarations can be represented by non-secret fixture connections.
        # The validation caller must strip credential data before dispatch.
        for cred in definition["credentials"]:
            if cred.get("data"):
                outcome.errors.append({"code": "REPLAY_CREDENTIALS_FORBIDDEN", "message": "Replay accepts no credential data"})
                return outcome
    with TemporaryDirectory(prefix="pg-replay-") as storage:
        context = ReplayContext(outcome.run_id, resolved.workflow_id,
            context_params={"dry_run": True, "dry_run_sample_size": 0},
            workflow_inputs=definition.get("inputs", {}), workflow_credentials=[],
            secrets={}, workflow_edges=resolved.edges, workflow_nodes=resolved.nodes,
            storage_dir=storage)
        as_of = fixture.get("as_of", fixture.get("broker", {}).get("as_of"))
        if as_of is not None:
            check_contract(as_of, {"type":"string","format":"date-time"}, "fixture.as_of")
        context.validation_as_of = as_of
        context.allow_code_node = True
        job = ReplayJob(outcome.run_id, resolved, context, runner)
        context.set_workflow_job(job)
        context.start()
        async def run_all():
            if any(node.node_type in ORDER_NODES for node in resolved.nodes.values()):
                # A no-signal branch still has account state to verify. Starting
                # the book only on the first order loses unchanged cash/holdings
                # and makes every correctly skipped order look unverifiable.
                runner.orders = ReplayOrders(fixture)
            await job._execute_main_flow()
            if fixture.get("events") and not outcome.errors:
                from programgarden.replay_events import replay_events
                await replay_events(job, runner, fixture, outcome)

        try:
            await asyncio.wait_for(run_all(), timeout=timeout)
        except Exception as exc:
            outcome.errors.append(exc.as_dict() if isinstance(exc, ContractViolation) else {
                "code": "REPLAY_EXECUTION_FAILED", "message": type(exc).__name__ + ": " + str(exc)})
        finally:
            context.stop()
        # Capture partial state even if a later contract, mapping or timeout
        # interrupts the chain. Failure evidence must retain earlier intents,
        # fills and outstanding reservations rather than return an empty book.
        try:
            outcome.outputs = {node: context.get_all_outputs(node) for node in resolved.nodes}
            states = job.get_state()["nodes"]
            outcome.skipped = [node for node, state in states.items() if state.get("state") == "skipped"]
            outcome.node_states = {node: str(state.get("state")) for node,state in states.items()}
            for node,state in states.items():
                if state.get("state") == "failed" and not any(e.get("node_id")==node for e in outcome.errors):
                    outcome.errors.append({"code":"REPLAY_NODE_FAILED","node_id":node,
                                           "message":str(state.get("error") or "Node failed")})
            if runner.orders is not None:
                outcome.simulation = runner.orders.book.snapshot()
            for order in outcome.order_observations:
                if order["status"] in {"rejected","unknown"}:
                    outcome.errors.append({"code":"REPLAY_ORDER_NOT_ACCEPTED","node_id":order["node_id"],
                        "order_id":order["order_id"],"status":order["status"],"reason":order["reason"]})
            for entry in context.get_deep_unresolved_bindings():
                outcome.errors.append({"code": "REPLAY_BINDING_UNRESOLVED", **entry})
            for error in job.get_structured_errors():
                outcome.errors.append(error.model_dump(mode="json"))
            finite_json(outcome.outputs)
        except Exception as exc:
            outcome.errors.append(exc.as_dict() if isinstance(exc, ContractViolation) else {
                "code": "REPLAY_EVIDENCE_FAILED", "message": type(exc).__name__ + ": " + str(exc)})
    if node_under_test is not None:
        outcome.setup_executed = [node for node in outcome.executed if node != node_under_test]
        outcome.executed = [node for node in outcome.executed if node == node_under_test]
    outcome.passed = not outcome.errors
    return outcome
