"""Broker currency evidence must never create or revalue an execution."""

import asyncio
from datetime import datetime
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.database.workflow_position_tracker import (
    ExecutionIdentityConflictError,
    WorkflowPositionTracker,
)
from programgarden.executor import BrokerNodeExecutor, NewOrderNodeExecutor, _stock_position_fill_currency
from programgarden_finance.ls.overseas_stock.accno.COSAQ00102.blocks import COSAQ00102OutBlock3
from programgarden_finance.ls.overseas_stock.accno.COSOQ00201.blocks import COSOQ00201OutBlock4
from programgarden_finance.ls.overseas_stock.extension.models import StockPositionItem
from programgarden_finance.ls.overseas_stock.real.AS1.blocks import AS1RealResponseBody


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket

    def denied(*args, **kwargs):
        raise AssertionError("Currency evidence tests are offline")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(BrokerNodeExecutor, "_active_trackers", {})


def ledger(tmp_path, **kwargs):
    return WorkflowPositionTracker(str(tmp_path / "ledger.sqlite"), "job", "broker", **kwargs)


def facts(order="1", side="buy", price=100):
    return dict(order_no=order, order_date="20260915", symbol="SYNTH", exchange="NASDAQ",
                side=side, quantity=1, price=price, fill_time="100000", commda_code="40",
                execution_id=order)


async def record(tracker, data, currency=None):
    tracker.record_order(data["order_no"], data["order_date"], data["symbol"], data["exchange"],
                         data["side"], data["quantity"], data["price"], "job", "node")
    return await tracker.record_fill(**data, currency=currency)


@pytest.mark.asyncio
@pytest.mark.parametrize("units,expected", [
    (["USD", "USD", "USD", "USD"], "USD"),
    (["HKD", "HKD", "HKD", "HKD"], "HKD"),
    ([None, "USD", "USD", "USD"], None),
    (["USD", "JPY", "USD", "USD"], None),
    (["", "USD", "USD", "USD"], None),
])
async def test_earned_lost_and_net_keep_the_proven_unit(tmp_path, units, expected):
    tracker = ledger(tmp_path)
    for data, unit in zip([facts(), facts("2", "sell", 110),
                           facts("3"), facts("4", "sell", 96)], units):
        await record(tracker, data, unit)
    group = tracker.personal_metrics()["realized_pnl"][0]
    assert group["currency"] == expected
    if len(set(units) - {None, ""}) > 1:
        assert group["status"] == "unavailable"
        assert group["amount"] is None and group["closed_trades"] is None
    else:
        assert (group["gross_profit"], group["gross_loss"], group["amount"]) == (10, 4, 6)
        assert group["closed_trades"] == 2
    assert ledger(tmp_path).personal_metrics()["realized_pnl"] == [group]


@pytest.mark.asyncio
async def test_annotation_is_exact_scoped_and_does_not_replay_fifo(tmp_path):
    tracker = ledger(tmp_path)
    data = facts()
    await record(tracker, data)
    with sqlite3.connect(tracker.db_path) as conn:
        original = conn.execute("SELECT execution_payload, realized_pnl FROM trade_history").fetchall()
    revision = tracker.fill_revision
    assert await tracker.annotate_fill_currency(currency="USD", **data)
    assert tracker.fill_revision == revision + 1
    assert not await tracker.annotate_fill_currency(currency="USD", **data)
    assert not await tracker.annotate_fill_currency(currency="USD", **{**data, "execution_id": "99"})
    assert not await tracker.annotate_fill_currency(currency="USD", **{**data, "execution_id": None})
    with pytest.raises(ExecutionIdentityConflictError):
        await tracker.annotate_fill_currency(currency="USD", **{**data, "quantity": 2})
    assert not await ledger(tmp_path, trading_mode="paper").annotate_fill_currency(currency="USD", **data)
    assert await tracker.record_fill(**data) == "workflow"
    with sqlite3.connect(tracker.db_path) as conn:
        assert conn.execute("SELECT execution_payload, realized_pnl FROM trade_history").fetchall() == original
        assert conn.execute("SELECT SUM(remaining_qty) FROM workflow_position_lots").fetchone()[0] == 1
        assert conn.execute("SELECT currency FROM trade_history").fetchone()[0] == "USD"


@pytest.mark.asyncio
async def test_conflicting_units_remain_unknown_after_restart(tmp_path):
    tracker = ledger(tmp_path)
    await record(tracker, facts(), "USD")
    assert await tracker.annotate_fill_currency(currency="JPY", **facts())
    assert not await tracker.annotate_fill_currency(currency="USD", **facts())
    with sqlite3.connect(tracker.db_path) as conn:
        assert conn.execute("SELECT currency, currency_conflict FROM trade_history").fetchone() == (None, 1)
    assert ledger(tmp_path).personal_metrics()["realized_pnl"][0]["currency"] is None


@pytest.mark.asyncio
async def test_buffered_execution_keeps_currency_when_ack_arrives(tmp_path):
    tracker = ledger(tmp_path)
    data = facts()
    assert await tracker.record_fill(**data) == "pending"
    assert await tracker.annotate_fill_currency(currency="USD", **data)
    await record(tracker, data)
    await tracker._process_buffered_fill(data["order_no"], data["order_date"])
    assert tracker.personal_metrics()["realized_pnl"][0]["currency"] == "USD"


@pytest.mark.asyncio
async def test_old_database_migrates_without_inventing_a_currency(tmp_path):
    tracker = ledger(tmp_path)
    await record(tracker, facts())
    with sqlite3.connect(tracker.db_path) as conn:
        conn.execute("ALTER TABLE trade_history DROP COLUMN currency")
        conn.execute("ALTER TABLE trade_history DROP COLUMN currency_conflict")
    reopened = ledger(tmp_path)
    assert reopened.personal_metrics()["realized_pnl"][0]["currency"] is None
    assert await reopened.record_fill(**facts()) == "workflow"
    with sqlite3.connect(tracker.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM trade_history").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_futures_currency_does_not_turn_fifo_into_money(tmp_path):
    tracker = ledger(tmp_path, product="overseas_futures")
    await record(tracker, facts(), "HKD")
    await record(tracker, facts("2", "sell", 110), "HKD")
    group = tracker.personal_metrics()["realized_pnl"][0]
    assert group["amount"] is None and group["currency"] is None
    assert group["reason"] == "futures_fifo_not_monetary"


def test_actual_model_fields_and_defaults_are_not_evidence():
    assert {"CrcyCode", "ShtnIsuNo", "FcurrMktCode"} <= COSOQ00201OutBlock4.model_fields.keys()
    assert "CrcyCode" in COSAQ00102OutBlock3.model_fields
    assert {"symbol", "market_code", "currency_code"} <= StockPositionItem.model_fields.keys()
    default = StockPositionItem(symbol="SYNTH", market_code="82")
    assert default.currency_code == "USD"
    assert _stock_position_fill_currency(default, "SYNTH", "82") is None
    explicit = StockPositionItem(symbol="SYNTH", market_code="82", currency_code="HKD")
    assert _stock_position_fill_currency(explicit, "SYNTH", "82") == "HKD"
    assert _stock_position_fill_currency(explicit, "OTHER", "82") is None
    assert _stock_position_fill_currency(explicit, "SYNTH", "81") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("refresh_fails", [False, True])
async def test_actual_as1_records_before_refresh_and_annotates_new_position(tmp_path, monkeypatch, refresh_fails):
    tracker = ledger(tmp_path)
    context = ExecutionContext(job_id="job", workflow_id="offline")
    context._workflow_position_tracker = tracker
    today = datetime.now().strftime("%Y%m%d")
    tracker.record_order("123", today, "SYNTH", "NASDAQ", "buy", 1, 100, "job", "order")
    account = SimpleNamespace(_positions={})

    async def refresh():
        with sqlite3.connect(tracker.db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM trade_history").fetchone()[0] == 1
        if refresh_fails:
            raise RuntimeError("Offline account refresh unavailable")
        account._positions["SYNTH"] = StockPositionItem(symbol="SYNTH", market_code="82", currency_code="USD")

    account.refresh_now = refresh
    BrokerNodeExecutor._active_trackers["job_broker"] = {"tracker": account}
    callbacks = {}
    real = SimpleNamespace(connect=AsyncMock(),
        AS0=lambda: SimpleNamespace(on_as0_message=lambda cb: None),
        AS1=lambda: SimpleNamespace(on_as1_message=lambda cb: callbacks.update(as1=cb)))
    ls = SimpleNamespace(overseas_stock=lambda: SimpleNamespace(real=lambda: real))
    submitted = []
    schedule = asyncio.run_coroutine_threadsafe

    def capture(coroutine, loop):
        future = schedule(coroutine, loop)
        submitted.append(future)
        return future

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", capture)
    await BrokerNodeExecutor()._subscribe_overseas_stock_fill_events(ls, "broker", context)
    values = {name: field.examples[0] for name, field in AS1RealResponseBody.model_fields.items()}
    values.update(sOrdNo=123, sExecNO="1", sExecQty=1, sExecPrc=100, sShtnIsuNo="SYNTH",
                  sOrdMktCode="82", sOrdPtnCode="02", sBnsTp="2")
    callbacks["as1"](SimpleNamespace(body=AS1RealResponseBody.model_validate(values)))
    if refresh_fails:
        with pytest.raises(RuntimeError, match="refresh unavailable"):
            await asyncio.wrap_future(submitted.pop())
    else:
        await asyncio.wrap_future(submitted.pop())
    with sqlite3.connect(tracker.db_path) as conn:
        assert conn.execute("SELECT COUNT(*), currency FROM trade_history").fetchone() == (
            1, None if refresh_fails else "USD")
        assert conn.execute("SELECT SUM(remaining_qty) FROM workflow_position_lots").fetchone()[0] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("units,expected", [(["USD", "USD"], "USD"), (["USD", "JPY"], None), (["USD", ""], None)])
async def test_actual_rest_parser_keeps_only_unanimous_execution_currency(units, expected):
    rows = [COSAQ00102OutBlock3(OrdNo=123, ExecQty=1, OvrsExecPrc=100, ShtnIsuNo="SYNTH", CrcyCode=unit)
            for unit in units]
    request = AsyncMock(return_value=SimpleNamespace(block3=rows, error_msg=None))
    ls = SimpleNamespace(overseas_stock=lambda: SimpleNamespace(
        accno=lambda: SimpleNamespace(cosaq00102=lambda **kwargs: SimpleNamespace(req_async=request))))
    result = await NewOrderNodeExecutor()._query_overseas_stock_fills_by_date(
        ls, "20260915", SimpleNamespace(log=lambda *args: None), "node")
    assert result["123"]["currency"] == expected
    assert result["123"]["filled_qty"] == 2
