"""Actual AS1 callback and SQLite ledger preserve individual stock executions."""

import asyncio
from datetime import datetime
import json
import socket
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.database.workflow_position_tracker import WorkflowPositionTracker
from programgarden.executor import BrokerNodeExecutor
from programgarden_finance.ls.overseas_stock.real.AS1.blocks import AS1RealResponseBody


@pytest.fixture(autouse=True)
def isolate_runtime(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Stock execution identity tests are offline")

    for name in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, name, denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(BrokerNodeExecutor, "_active_trackers", {})


def execution_body(execution_id):
    values = {name: field.examples[0] for name, field in AS1RealResponseBody.model_fields.items()}
    values.update(sOrdNo=123, sExecNO=execution_id, sExecQty=0.5, sExecPrc=100,
                  sShtnIsuNo="SYNTH", sOrdMktCode="82", sOrdPtnCode="02", sBnsTp="2",
                  proctm="120000001")
    return AS1RealResponseBody.model_validate(values)


def ledger_rows(path):
    with sqlite3.connect(path) as conn:
        return conn.execute(
            "SELECT execution_id, quantity, execution_payload FROM trade_history ORDER BY id"
        ).fetchall()


@pytest.mark.asyncio
async def test_as1_replay_and_identical_partials_reach_durable_identity(tmp_path, monkeypatch):
    context = ExecutionContext(job_id="stock-identity", workflow_id="offline")
    path = str(tmp_path / "stock.sqlite")
    tracker = WorkflowPositionTracker(path, context.job_id, "broker", product="overseas_stock")
    context._workflow_position_tracker = tracker
    tracker.record_order("123", datetime.now().strftime("%Y%m%d"), "SYNTH", "NASDAQ",
                         "buy", 1, 100, context.job_id, "order-node")

    callbacks = {}
    real = SimpleNamespace(
        connect=AsyncMock(),
        AS0=lambda: SimpleNamespace(on_as0_message=lambda callback: callbacks.update(as0=callback)),
        AS1=lambda: SimpleNamespace(on_as1_message=lambda callback: callbacks.update(as1=callback)),
    )
    ls = SimpleNamespace(overseas_stock=lambda: SimpleNamespace(real=lambda: real))
    submitted = []
    schedule = asyncio.run_coroutine_threadsafe

    def capture(coroutine, loop):
        future = schedule(coroutine, loop)
        submitted.append(future)
        return future

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", capture)
    await BrokerNodeExecutor()._subscribe_overseas_stock_fill_events(ls, "broker", context)

    async def emit(execution_id):
        callbacks["as1"](SimpleNamespace(body=execution_body(execution_id)))
        assert submitted, "AS1 callback did not schedule execution recording"
        await asyncio.wrap_future(submitted.pop())

    await emit("0001")
    first = ledger_rows(path)
    assert len(first) == 1 and first[0][:2] == ("1", 0.5)
    assert json.loads(first[0][2])["reported_execution_id"] == "0001"

    await emit("1")
    assert ledger_rows(path) == first

    # Same order, time, price and quantity; the distinct broker execution ID
    # proves that this is another partial fill, not a repeated notification.
    await emit("0002")
    both = ledger_rows(path)
    assert [(row[0], row[1]) for row in both] == [("1", 0.5), ("2", 0.5)]

    context._workflow_position_tracker = WorkflowPositionTracker(
        path, context.job_id, "broker", product="overseas_stock")
    await emit("0002")
    assert ledger_rows(path) == both
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT SUM(remaining_qty) FROM workflow_position_lots").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_context_call_without_execution_identity_retains_legacy_arguments(tmp_path):
    context = ExecutionContext(job_id="stock-legacy", workflow_id="offline")
    calls = []

    class LegacyTracker:
        async def record_fill(self, **kwargs):
            calls.append(kwargs)
            return "manual"

    context._workflow_position_tracker = LegacyTracker()
    result = await context.record_workflow_fill(
        "123", "20260909", "SYNTH", "NASDAQ", "buy", 0.5, 100, "120000001", "10")
    assert result == "manual"
    assert calls == [{"order_no": "123", "order_date": "20260909", "symbol": "SYNTH",
                      "exchange": "NASDAQ", "side": "buy", "quantity": 0.5, "price": 100,
                      "fill_time": "120000001", "commda_code": "10"}]
