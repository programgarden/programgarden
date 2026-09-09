"""Actual futures executor with in-memory SDK transport and local-only hooks."""
from copy import deepcopy
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
import asyncio
import socket

import pytest

from programgarden.context import ExecutionContext
import programgarden.executor as engine
from programgarden.order_lifecycle import OrderLifecycleMetadata
from programgarden_finance.ls.overseas_futureoption.order.CIDBT00100.blocks import CIDBT00100OutBlock2


ORDER = {"symbol": "SYNTHETIC", "exchange": "HKEX", "quantity": 1, "price": 25000}
CONNECTION = {"broker_node_id": "broker-a", "credential_id": "cred-a", "product": "overseas_futures", "paper_trading": True}
CONFIG = {"connection": CONNECTION, "order": ORDER, "side": "buy", "order_type": "limit"}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Lifecycle tests cannot access a network socket")
    for name in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, name, denied)


class Journal:
    def __init__(self):
        self.prepared = []
        self.accepted_rows = []
        self.rejected_rows = []
        self.fail_prepare = False
        self.fail_accept = False
        self.replay = None

    def prepare(self, metadata):
        self.prepared.append(metadata)
        if self.fail_prepare:
            raise OSError("Synthetic disk failure")
        return deepcopy(self.replay)

    def accepted(self, metadata, result):
        self.accepted_rows.append((metadata, deepcopy(result)))
        if self.fail_accept:
            raise OSError("Synthetic disk failure after ACK")
        return {"client_order_key": "synthetic-parent", "order_observed_at": result["accepted_at"], "recovery_status": "accepted"}

    def rejected(self, metadata, result):
        self.rejected_rows.append((metadata, deepcopy(result)))


def context(tmp_path, handler=None, job_id="fixture-job"):
    ctx = ExecutionContext(
        job_id=job_id, workflow_id="fixture-workflow", storage_dir=str(tmp_path),
        workflow_credentials=[{"credential_id": "cred-a", "data": {"appkey": "key-a", "appsecret": "secret-a", "paper_trading": True}},
                              {"credential_id": "cred-b", "data": {"appkey": "key-b", "appsecret": "secret-b", "paper_trading": True}}],
        order_lifecycle_handler=handler,
    )
    ctx.set_secret("credential_id", {"appkey": "wrong-legacy-key", "appsecret": "wrong-legacy-secret"})
    ctx.set_output("broker-a", "connection", CONNECTION)
    ctx.set_output("broker-b", "connection", {**CONNECTION, "broker_node_id": "broker-b", "credential_id": "cred-b"})
    return ctx


def sdk(monkeypatch, *, response=None, request_error=None):
    requests, logins = [], []
    if response is None:
        response = SimpleNamespace(error_msg=None, rsp_cd="00000", rsp_msg="Synthetic accepted fixture", block2=CIDBT00100OutBlock2(OvrsFutsOrdNo="000000001"))
    def factory(body):
        async def req_async():
            requests.append(body)
            if request_error:
                raise request_error
            return response
        return SimpleNamespace(req_async=req_async)
    ls = SimpleNamespace(overseas_futureoption=lambda: SimpleNamespace(order=lambda: SimpleNamespace(CIDBT00100=factory)))
    def login(*args, **kwargs):
        logins.append((args, kwargs))
        return ls, True, None
    monkeypatch.setattr(engine, "ensure_ls_login", login)
    return requests, logins


async def execute(executor, ctx, config=None, **kwargs):
    return await executor.execute("order", "OverseasFuturesNewOrderNode", deepcopy(config or CONFIG), ctx, **kwargs)


@pytest.mark.asyncio
async def test_ack_frozen_before_fill_wait_cancellation_then_retry_sends_once(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    requests, logins = sdk(monkeypatch)
    executor = engine.NewOrderNodeExecutor()
    legacy = []
    ctx.record_order_submitted = lambda **row: legacy.append(deepcopy(row))
    async def cancelled(*args, **kwargs):
        assert len(legacy) == 1
        assert next(iter(ctx._order_lifecycle_operations.values()))["accepted"]["order_id"] == "000000001"
        raise asyncio.CancelledError()
    monkeypatch.setattr(executor, "_confirm_order_fill", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await execute(executor, ctx)
    replay = await execute(executor, ctx)
    assert len(requests) == len(logins) == 1
    assert replay["order_result"]["success"] is True
    assert replay["result"][0]["idempotent_replay"] is True
    entry = next(iter(ctx._order_lifecycle_operations.values()))
    metadata, accepted = entry["metadata"], entry["accepted"]["order_result"]
    assert isinstance(metadata, OrderLifecycleMetadata)
    assert requests[0].OrdDt == metadata.broker_order_date.strftime("%Y%m%d")
    assert accepted["broker_order_date"] == metadata.broker_order_date.isoformat()
    assert accepted["order_date_basis"] == "CIDBT00100_request_OrdDt"
    assert datetime.fromisoformat(accepted["accepted_at"]).tzinfo is not None
    assert accepted["response_code"] == "00000"
    assert accepted["response_message"] == "Synthetic accepted fixture"


@pytest.mark.asyncio
async def test_post_ack_disk_failure_preserves_success_and_replay(tmp_path, monkeypatch):
    journal = Journal(); journal.fail_accept = True
    ctx = context(tmp_path, journal)
    requests, _ = sdk(monkeypatch)
    executor = engine.NewOrderNodeExecutor()
    monkeypatch.setattr(executor, "_confirm_order_fill", AsyncMock(side_effect=OSError("Synthetic confirmation error")))
    output = await execute(executor, ctx)
    replay = await execute(executor, ctx)
    assert len(requests) == 1
    for row in (output, replay):
        assert row["order_result"]["success"] is True
        assert row["order_id"] == "000000001"
        assert row["result"][0]["recovery_status"] == "persistence_failed"
    assert not journal.rejected_rows


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["prepare", "transport", "cancel"])
async def test_prepared_uncertain_operation_blocks_retry(tmp_path, monkeypatch, failure):
    journal = Journal(); journal.fail_prepare = failure == "prepare"
    ctx = context(tmp_path, journal)
    error = {"prepare": None, "transport": TimeoutError("Synthetic transport timeout"), "cancel": asyncio.CancelledError()}[failure]
    requests, _ = sdk(monkeypatch, request_error=error)
    executor = engine.NewOrderNodeExecutor()
    if failure == "cancel":
        with pytest.raises(asyncio.CancelledError):
            await execute(executor, ctx)
    else:
        first = await execute(executor, ctx)
        assert first["result"][0]["success"] is False
    replay = await execute(executor, ctx)
    assert len(requests) == (0 if failure == "prepare" else 1)
    assert len(journal.prepared) == 1 and not journal.rejected_rows
    assert replay["result"][0]["recovery_status"] == "prepared_or_uncertain"


@pytest.mark.asyncio
async def test_without_handler_paper_ack_guard_is_unconditional(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    requests, _ = sdk(monkeypatch)
    executor = engine.NewOrderNodeExecutor()
    monkeypatch.setattr(executor, "_confirm_order_fill", AsyncMock(side_effect=asyncio.CancelledError()))
    with pytest.raises(asyncio.CancelledError):
        await execute(executor, ctx)
    assert (await execute(executor, ctx))["result"][0]["success"]
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_prior_durable_acceptance_replays_without_transport(tmp_path, monkeypatch):
    journal = Journal()
    journal.replay = {"success": True, "order_id": "known", "client_order_key": "known-parent", "status": "submitted"}
    requests, _ = sdk(monkeypatch)
    output = await execute(engine.NewOrderNodeExecutor(), context(tmp_path, journal))
    assert not requests and not journal.accepted_rows
    assert output["result"][0]["order_id"] == "known"
    assert output["result"][0]["idempotent_replay"]


@pytest.mark.asyncio
async def test_iteration_cycle_tool_call_and_fresh_job_are_distinct_operations(tmp_path, monkeypatch):
    journal = Journal()
    ctx = context(tmp_path, journal)
    ctx._workflow_job = SimpleNamespace(_order_cycle=0)
    requests, _ = sdk(monkeypatch)
    executor = engine.NewOrderNodeExecutor()
    monkeypatch.setattr(executor, "_confirm_order_fill", AsyncMock())
    for index in (0, 1):
        ctx.set_iteration_context(ORDER, index, 2)
        assert (await execute(executor, ctx))["result"][0]["success"]
    assert (await execute(executor, ctx))["result"][0]["idempotent_replay"]
    ctx._workflow_job._order_cycle = 1
    await execute(executor, ctx)
    for call_id in ("tool:agent:call-1", "tool:agent:call-2"):
        await execute(executor, ctx, order_invocation_id=call_id)
    await execute(executor, context(tmp_path, journal, job_id="fresh-job"))
    assert len(requests) == 6
    assert len({m.operation_key for m in journal.prepared}) == 6


@pytest.mark.asyncio
async def test_changed_facts_do_not_create_a_new_retry_key(tmp_path, monkeypatch):
    requests, _ = sdk(monkeypatch)
    executor = engine.NewOrderNodeExecutor()
    monkeypatch.setattr(executor, "_confirm_order_fill", AsyncMock())
    ctx = context(tmp_path, Journal())
    await execute(executor, ctx)
    conflict = await execute(executor, ctx, {**CONFIG, "order": {**ORDER, "quantity": 2}})
    assert len(requests) == 1 and conflict["result"][0]["success"] is False
    assert "facts conflict" in conflict["result"][0]["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize("connection", [
    {"product": "overseas_futures", "paper_trading": True},
    {**CONNECTION, "credential_id": "cred-b"},
    {**CONNECTION, "credential_id": "missing"},
    {**CONNECTION, "product": "overseas_stock"},
    {**CONNECTION, "paper_trading": False},
])
async def test_invalid_route_fails_before_login_and_prepare(tmp_path, monkeypatch, connection):
    requests, logins = sdk(monkeypatch)
    journal = Journal()
    output = await execute(engine.NewOrderNodeExecutor(), context(tmp_path, journal), {**CONFIG, "connection": connection})
    assert output["result"][0]["success"] is False
    assert not requests and not logins and not journal.prepared


@pytest.mark.asyncio
async def test_two_brokers_exact_second_credential_is_used(tmp_path, monkeypatch):
    requests, logins = sdk(monkeypatch)
    ctx = context(tmp_path, Journal())
    executor = engine.NewOrderNodeExecutor()
    monkeypatch.setattr(executor, "_confirm_order_fill", AsyncMock())
    output = await execute(executor, ctx, {**CONFIG, "connection": ctx.get_all_outputs("broker-b")["connection"]})
    assert output["result"][0]["success"]
    assert logins[0][0][:3] == ("key-b", "secret-b", True)
    assert ctx.order_lifecycle_handler.prepared[0].credential_id == "cred-b"


@pytest.mark.parametrize("owner", [engine.WorkflowJob, engine.AIAgentToolExecutor])
def test_both_injection_paths_preserve_explicit_and_reject_ambiguity(tmp_path, owner):
    ctx = context(tmp_path)
    broker = SimpleNamespace(product_scope="overseas_futures", broker_provider="ls", node_type="OverseasFuturesBrokerNode")
    target = SimpleNamespace(product_scope="overseas_futures", broker_provider="ls")
    host = SimpleNamespace(context=ctx, workflow=SimpleNamespace(nodes={"broker-a": broker, "broker-b": broker}))
    explicit = {"connection": ctx.get_all_outputs("broker-b")["connection"]}
    assert owner._auto_inject_connection(host, "order", target, explicit) is explicit
    with pytest.raises(ValueError, match="Multiple compatible"):
        owner._auto_inject_connection(host, "order", target, {})
    host.workflow.nodes.pop("broker-b")
    assert owner._auto_inject_connection(host, "order", target, {})["connection"]["broker_node_id"] == "broker-a"


@pytest.mark.asyncio
async def test_stock_legacy_login_and_dry_run_skip_lifecycle(tmp_path, monkeypatch):
    requests, logins = sdk(monkeypatch)
    journal = Journal(); ctx = context(tmp_path, journal)
    executor = engine.NewOrderNodeExecutor()
    stock = executor._order_result(True, "SYNTHETIC", "NASDAQ", "buy", 1, 5, None, "stock-fixture")
    monkeypatch.setattr(executor, "_execute_overseas_stock", AsyncMock(return_value=stock))
    monkeypatch.setattr(executor, "_confirm_order_fill", AsyncMock())
    output = await executor.execute("stock", "OverseasStockNewOrderNode", {**CONFIG, "connection": {"product": "overseas_stock"}}, ctx)
    assert output["order_id"] == "stock-fixture"
    assert logins[0][0][:2] == ("wrong-legacy-key", "wrong-legacy-secret")
    ctx.context_params["dry_run"] = True
    dry = await execute(executor, ctx)
    assert dry["dry_run"] is True and len(logins) == 1
    assert not journal.prepared and not requests


@pytest.mark.asyncio
@pytest.mark.parametrize("code,order_id,expected_rejected", [("FIXTURE_REJECT", "", True), ("UNMAPPED", "", False), ("00000", "", False), ("00000", "0", False), ("02201", "000000001", False)])
async def test_rejected_hook_requires_known_rejection_without_ack(tmp_path, monkeypatch, code, order_id, expected_rejected):
    journal = Journal()
    from programgarden_core.models.order_diagnostics import OVERSEAS_FUTURES_REJECT_CODES
    monkeypatch.setitem(OVERSEAS_FUTURES_REJECT_CODES, "FIXTURE_REJECT", {"cause": "Synthetic definitive rejection", "retry": "do_not_retry"})
    response = SimpleNamespace(error_msg=None, rsp_cd=code, rsp_msg="Synthetic response fixture", block2=CIDBT00100OutBlock2(OvrsFutsOrdNo=order_id))
    sdk(monkeypatch, response=response)
    executor = engine.NewOrderNodeExecutor()
    monkeypatch.setattr(executor, "_confirm_order_fill", AsyncMock())
    monkeypatch.setattr(executor, "_notify_order_reject", AsyncMock())
    output = await execute(executor, context(tmp_path, journal))
    assert bool(journal.rejected_rows) == expected_rejected
    assert output["result"][0]["success"] == (order_id == "000000001")
    assert output["result"][0]["response_code"] == code


@pytest.mark.asyncio
async def test_managed_futures_ack_skips_legacy_history_and_retains_parent(tmp_path, monkeypatch):
    journal = Journal(); ctx = context(tmp_path, journal)
    requests, _ = sdk(monkeypatch)
    executor = engine.NewOrderNodeExecutor()
    history = AsyncMock(side_effect=AssertionError("Managed futures must not read legacy history"))
    monkeypatch.setattr(executor, "_confirm_order_fill", history)
    result = await execute(executor, ctx)
    history.assert_not_awaited()
    assert len(requests) == 1 and len(journal.accepted_rows) == 1
    assert result["result"][0]["status"] == "submitted"
    assert result["result"][0]["client_order_key"] == "synthetic-parent"
    assert result["result"][0]["order_observed_at"] == result["result"][0]["accepted_at"]
    assert "filled_quantity" not in result["result"][0]


def workflow_definition():
    return {
        "id": "lifecycle-fixture", "name": "Lifecycle fixture", "version": "1.0.0",
        "nodes": [{"id": "start", "type": "StartNode"},
                  {"id": "broker-a", "type": "OverseasFuturesBrokerNode", "credential_id": "cred-a", "paper_trading": True},
                  {"id": "order", "type": "OverseasFuturesNewOrderNode", "order": ORDER}],
        "edges": [{"from": "start", "to": "broker-a"}, {"from": "broker-a", "to": "order"}],
        "credentials": [{"credential_id": "cred-a", "type": "broker_ls_overseas_futures", "data": []}],
    }


@pytest.mark.asyncio
async def test_actual_split_children_and_retries_keep_separate_operations(tmp_path, monkeypatch):
    executor = engine.WorkflowExecutor()
    resolved, validation = executor.compile(workflow_definition())
    assert validation.is_valid, validation.errors
    journal = Journal(); ctx = context(tmp_path, journal)
    job = engine.WorkflowJob("fixture-job", resolved, ctx, executor)
    ctx.set_workflow_job(job)
    requests, _ = sdk(monkeypatch)
    for index in (0, 1, 0, 1):
        await job._execute_branch_for_item("split", ["order"], ORDER, index, 2)
    assert len(requests) == 2
    assert {m.invocation_id for m in journal.prepared} == {"split:split#0", "split:split#1"}
    assert {m.iteration_index for m in journal.prepared} == {0, 1}


@pytest.mark.asyncio
async def test_actual_auto_iteration_keeps_identical_items_distinct_with_legacy_registry(tmp_path, monkeypatch):
    executor = engine.WorkflowExecutor()
    resolved, validation = executor.compile(workflow_definition())
    assert validation.is_valid
    ctx = context(tmp_path, Journal())
    ctx.context_params["enable_order_idempotency"] = True
    job = engine.WorkflowJob("fixture-job", resolved, ctx, executor)
    ctx.set_workflow_job(job)
    requests, _ = sdk(monkeypatch)
    monkeypatch.setattr(job, "_auto_iterate_pacing_sleep", AsyncMock())
    config = {"connection": CONNECTION, "order": "{{ item }}"}
    output = await job._execute_with_auto_iterate("order", resolved.nodes["order"], config, [ORDER, ORDER], "order")
    assert len(requests) == 2
    assert len(output["result"]) == 2 and all(row["success"] for row in output["result"])
    # Restore a fresh runtime context with the same job and durable legacy store.
    restored = context(tmp_path, Journal())
    restored.context_params["enable_order_idempotency"] = True
    restored_job = engine.WorkflowJob("fixture-job", resolved, restored, executor)
    restored.set_workflow_job(restored_job)
    monkeypatch.setattr(restored_job, "_auto_iterate_pacing_sleep", AsyncMock())
    replay = await restored_job._execute_with_auto_iterate("order", resolved.nodes["order"], config, [ORDER, ORDER], "order")
    assert len(requests) == 2 and all(row["idempotent_replay"] for row in replay["result"])


@pytest.mark.asyncio
async def test_actual_tool_calls_route_exactly_and_use_call_identity(tmp_path, monkeypatch):
    executor = engine.WorkflowExecutor()
    resolved, validation = executor.compile(workflow_definition())
    assert validation.is_valid
    journal = Journal(); ctx = context(tmp_path, journal)
    tool = engine.AIAgentToolExecutor(ctx, resolved, engine.GenericNodeExecutor(), executor._executors)
    tool._tool_configs["submit"] = {"node_id": "order", "node_type": "OverseasFuturesNewOrderNode", "config": deepcopy(CONFIG)}
    requests, logins = sdk(monkeypatch)
    for call_id in ("call-1", "call-2", "call-1"):
        result = await tool.call_tool("submit", {"connection": ctx.get_all_outputs("broker-b")["connection"], "credential_id": "cred-b"}, "agent", tool_call_id=call_id)
        assert result["result"][0]["success"]
    assert len(requests) == 2 and all(args[0] == "key-a" for args, _ in logins)
    assert len({m.operation_key for m in journal.prepared}) == 2


@pytest.mark.asyncio
async def test_broker_output_carries_exact_identity_without_secret(tmp_path):
    ctx = context(tmp_path)
    ctx.context_params["dry_run"] = True
    output = await engine.BrokerNodeExecutor().execute(
        "broker-b", "OverseasFuturesBrokerNode", {"credential_id": "cred-b", "paper_trading": True}, ctx,
    )
    assert output["connection"] == {"provider": "ls-sec.co.kr", "product": "overseas_futures", "paper_trading": True, "broker_node_id": "broker-b", "credential_id": "cred-b"}
    assert ctx.get_credential("broker_credentials:broker-b:cred-b")["appkey"] == "key-b"
    assert "appkey" not in output["connection"] and "appsecret" not in output["connection"]


@pytest.mark.asyncio
async def test_executor_injects_runtime_handler_separately_from_dsl(tmp_path, monkeypatch):
    executor = engine.WorkflowExecutor(); journal = Journal()
    executor.set_order_lifecycle_handler(journal)
    monkeypatch.setattr(engine.WorkflowJob, "start", AsyncMock())
    job = await executor.execute({"id": "handler-fixture", "name": "Handler fixture", "nodes": [{"id": "start", "type": "StartNode"}], "edges": []}, storage_dir=str(tmp_path))
    assert job.context.order_lifecycle_handler is journal
    assert "order_lifecycle_handler" not in job.context.context_params
    assert "order_lifecycle_handler" not in job.context._secrets
    await job._save_checkpoint()
    checkpoint = job._get_checkpoint_mgr().load_checkpoint(job.job_id)
    assert "order_lifecycle_handler" not in (checkpoint["context_params"] or {})
    fresh_executor = engine.WorkflowExecutor(); fresh_handler = Journal()
    fresh_executor.set_order_lifecycle_handler(fresh_handler)
    restored = await fresh_executor.restore(
        {"id": "handler-fixture", "name": "Handler fixture", "nodes": [{"id": "start", "type": "StartNode"}], "edges": []},
        job.job_id, storage_dir=str(tmp_path),
    )
    assert restored.context.order_lifecycle_handler is fresh_handler
    assert not restored.context._order_lifecycle_operations
    if restored.context._resource_context:
        await restored.context._resource_context.stop()
    if job.context._resource_context:
        await job.context._resource_context.stop()


@pytest.mark.asyncio
async def test_managed_futures_broker_does_not_schedule_legacy_history(tmp_path, monkeypatch):
    executor = engine.BrokerNodeExecutor(); ctx = context(tmp_path, Journal())
    calls = []
    monkeypatch.setattr(executor, "_start_background_task", lambda *args: calls.append(args))
    monkeypatch.setattr(ctx, "init_workflow_position_tracker", lambda **kwargs: None)
    await executor.execute("broker-a", "OverseasFuturesBrokerNode", {"credential_id": "cred-a", "paper_trading": True}, ctx)
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["prepare", "accepted"])
async def test_async_handlers_are_rejected_without_awaiting(tmp_path, monkeypatch, phase):
    journal = Journal()
    async def invalid_hook(*args):
        raise AssertionError("Async lifecycle hook body must never run")
    setattr(journal, phase, invalid_hook)
    requests, _ = sdk(monkeypatch)
    output = await execute(engine.NewOrderNodeExecutor(), context(tmp_path, journal))
    assert len(requests) == (1 if phase == "accepted" else 0)
    assert output["result"][0]["success"] is (phase == "accepted")
    assert output["result"][0]["recovery_status"] == ("persistence_failed" if phase == "accepted" else "prepared_or_uncertain")


@pytest.mark.asyncio
async def test_accepted_hook_cannot_override_broker_success_or_order_id(tmp_path, monkeypatch):
    journal = Journal()
    journal.accepted = lambda *args: {"success": False, "order_id": "replacement"}
    sdk(monkeypatch)
    output = await execute(engine.NewOrderNodeExecutor(), context(tmp_path, journal))
    assert output["order_id"] == "000000001" and output["result"][0]["success"]
    assert output["result"][0]["recovery_status"] == "persistence_failed"


@pytest.mark.asyncio
async def test_ack_date_is_actual_request_date_across_midnight(tmp_path, monkeypatch):
    import datetime as datetime_module
    class BeforeMidnight(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 9)
    class AfterMidnight(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 10)
    monkeypatch.setattr(datetime_module, "date", BeforeMidnight)
    requests, _ = sdk(monkeypatch)
    journal = Journal(); ctx = context(tmp_path, journal)
    original = journal.accepted
    def accepted(metadata, result):
        monkeypatch.setattr(datetime_module, "date", AfterMidnight)
        return original(metadata, result)
    journal.accepted = accepted
    executor = engine.NewOrderNodeExecutor()
    output = await execute(executor, ctx)
    replay = await execute(executor, ctx)
    assert len(requests) == 1 and requests[0].OrdDt == "20260909"
    assert output["result"][0]["broker_order_date"] == "2026-09-09"
    assert replay["result"][0]["broker_order_date"] == "2026-09-09"


@pytest.mark.asyncio
async def test_standalone_post_ack_wait_exception_preserves_success(tmp_path, monkeypatch):
    requests, _ = sdk(monkeypatch)
    executor = engine.NewOrderNodeExecutor()
    history = AsyncMock(side_effect=OSError("Synthetic confirmation failure"))
    monkeypatch.setattr(executor, "_confirm_order_fill", history)
    result = await execute(executor, context(tmp_path))
    history.assert_awaited_once()
    assert len(requests) == 1 and result["result"][0]["success"]
    assert result["order_id"] == "000000001"


@pytest.mark.asyncio
async def test_prepared_disk_marker_blocks_retry_in_fresh_runtime_context(tmp_path, monkeypatch):
    import sqlite3
    path = tmp_path / "prepared.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE operations (operation_key TEXT PRIMARY KEY)")
    class DiskJournal(Journal):
        def prepare(self, metadata):
            self.prepared.append(metadata)
            try:
                with sqlite3.connect(path) as db:
                    db.execute("INSERT INTO operations VALUES (?)", (metadata.operation_key,))
            except sqlite3.IntegrityError as exc:
                raise RuntimeError("Existing prepared operation requires reconciliation") from exc
    journal = DiskJournal()
    requests, _ = sdk(monkeypatch, request_error=TimeoutError("Synthetic uncertain transport"))
    for _ in range(2):
        output = await execute(engine.NewOrderNodeExecutor(), context(tmp_path, journal))
        assert output["result"][0]["recovery_status"] == "prepared_or_uncertain"
    assert len(requests) == 1 and len(journal.prepared) == 2
    assert journal.prepared[0].operation_key == journal.prepared[1].operation_key
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM operations").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_explicit_bound_tool_connection_reaches_exact_second_broker(tmp_path, monkeypatch):
    executor = engine.WorkflowExecutor()
    resolved, validation = executor.compile(workflow_definition())
    assert validation.is_valid
    ctx = context(tmp_path, Journal())
    tool = engine.AIAgentToolExecutor(ctx, resolved, engine.GenericNodeExecutor(), executor._executors)
    tool._tool_configs["submit"] = {"node_id": "order", "node_type": "OverseasFuturesNewOrderNode", "config": {**CONFIG, "connection": "{{ nodes['broker-b'].connection }}"}}
    requests, logins = sdk(monkeypatch)
    output = await tool.call_tool("submit", {}, "agent", tool_call_id="bound-call")
    assert len(requests) == 1 and output["result"][0]["success"], output
    assert logins[0][0][:2] == ("key-b", "secret-b")
