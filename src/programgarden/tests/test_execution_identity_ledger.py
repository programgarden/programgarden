"""Real SQLite guards for explicit execution replay and early partial fills."""

import asyncio
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from programgarden.database.workflow_position_tracker import (
    ExecutionIdentityConflictError,
    WorkflowPositionTracker,
)


def tracker(tmp_path, **kwargs):
    return WorkflowPositionTracker(str(tmp_path / "ledger.db"), "job", "broker", **kwargs)


def fill(**kwargs):
    return {
        "order_no": "000123", "order_date": "20260909", "symbol": "SYNTH", "exchange": "TEST",
        "side": "buy", "quantity": 2, "price": 100.0, "fill_time": "100000001", "commda_code": "40",
        **kwargs,
    }


def order(target, number="000123", date="20260909"):
    target.record_order(number, date, "SYNTH", "TEST", "buy", 10, 100, "job", "node")


def rows(target, table):
    assert table in {"trade_history", "workflow_position_lots", "workflow_orders"}
    with sqlite3.connect(target.db_path) as conn:
        return conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()


def remaining(target):
    with sqlite3.connect(target.db_path) as conn:
        return conn.execute("SELECT COALESCE(SUM(remaining_qty), 0) FROM workflow_position_lots").fetchone()[0]


@pytest.mark.asyncio
async def test_replay_and_reopen_preserve_buy_and_sell_fifo(tmp_path):
    target = tracker(tmp_path)
    order(target)
    assert await target.record_fill(**fill(), execution_id="001") == "workflow"
    before = rows(target, "trade_history"), rows(target, "workflow_position_lots")
    assert await target.record_fill(**fill(), execution_id=1) == "workflow"
    reopened = tracker(tmp_path)
    assert await reopened.record_fill(**fill(), execution_id="1") == "workflow"
    assert (rows(target, "trade_history"), rows(target, "workflow_position_lots")) == before

    order(target, "sell")
    sale = fill(order_no="sell", side="sell", quantity=1, price=110, fill_time="110000000")
    assert await target.record_fill(**sale, execution_id="sell-fill") == "workflow"
    before = rows(target, "trade_history"), rows(target, "workflow_position_lots")
    assert await reopened.record_fill(**sale, execution_id="sell-fill") == "workflow"
    assert (rows(target, "trade_history"), rows(target, "workflow_position_lots")) == before
    assert remaining(target) == 1
    with sqlite3.connect(target.db_path) as conn:
        assert conn.execute("SELECT SUM(realized_pnl) FROM trade_history").fetchone()[0] == 10


@pytest.mark.asyncio
async def test_padded_order_and_execution_replay_keeps_original_evidence(tmp_path):
    target = tracker(tmp_path)
    order(target, "123")
    assert await target.record_fill(**fill(), execution_id=" 000456 ") == "workflow"
    assert await target.record_fill(**fill(order_no="123", quantity=2.0, price=100), execution_id=456) == "workflow"
    with sqlite3.connect(target.db_path) as conn:
        row = conn.execute("SELECT order_no, normalized_order_no, execution_id, execution_payload FROM trade_history").fetchone()
    assert row[:3] == ("000123", "123", "456")
    assert json.loads(row[3])["reported_execution_id"] == " 000456 "
    assert len(rows(target, "trade_history")) == 1


@pytest.mark.asyncio
async def test_distinct_opaque_ids_do_not_collapse_identical_fill_facts(tmp_path):
    target = tracker(tmp_path)
    args = fill(commda_code="10")
    for identity in (" 000A ", "A", "a"):
        assert await target.record_fill(**args, execution_id=identity) == "manual"
    assert await target.record_fill(**args, execution_id="000A") == "manual"
    assert len(rows(target, "trade_history")) == 3
    assert remaining(target) == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", [
    {"symbol": "OTHER"}, {"exchange": "OTHER"}, {"side": "sell"},
    {"quantity": 3}, {"price": 101}, {"fill_time": "100000002"}, {"commda_code": "10"},
])
async def test_conflicting_committed_identity_never_mutates_facts(tmp_path, changed):
    target = tracker(tmp_path)
    order(target)
    await target.record_fill(**fill(), execution_id="same")
    before = rows(target, "trade_history"), rows(target, "workflow_position_lots")
    with pytest.raises(ExecutionIdentityConflictError, match="Conflicting fill facts"):
        await target.record_fill(**fill(**changed), execution_id="same")
    assert (rows(target, "trade_history"), rows(target, "workflow_position_lots")) == before


@pytest.mark.asyncio
async def test_distinct_early_partials_survive_ack_and_buffer_replays(tmp_path):
    target = tracker(tmp_path)
    target.FILL_BUFFER_TIMEOUT = 0
    assert await target.record_fill(**fill(), execution_id="0001") == "pending"
    assert await target.record_fill(**fill(order_no="123"), execution_id=1) == "pending"
    assert await target.record_fill(**fill(quantity=3, price=101, fill_time="100000002"), execution_id="2") == "pending"
    with pytest.raises(ExecutionIdentityConflictError):
        await target.record_fill(**fill(quantity=20), execution_id="1")
    assert len(target._pending_fills) == 2
    order(target, "123")
    await target._process_buffered_fill("123", "20260909")
    await asyncio.sleep(0)
    assert remaining(target) == 5
    assert len(rows(target, "trade_history")) == 2
    assert target._pending_fills == {}


@pytest.mark.asyncio
async def test_early_partials_all_timeout_without_order(tmp_path):
    target = tracker(tmp_path)
    target.FILL_BUFFER_TIMEOUT = 0
    await target.record_fill(**fill(), execution_id="1")
    await target.record_fill(**fill(quantity=3, fill_time="100000002"), execution_id="2")
    for key in list(target._pending_fills):
        await target._process_timeout_fill(key)
    assert remaining(target) == 5
    with sqlite3.connect(target.db_path) as conn:
        assert conn.execute("SELECT classification FROM trade_history").fetchall() == [("unknown_api",), ("unknown_api",)]
    order(target)
    assert await target.record_fill(**fill(), execution_id="1") == "unknown_api"
    assert len(rows(target, "trade_history")) == 2


@pytest.mark.asyncio
async def test_timeout_belongs_to_one_arrival_not_later_partial(tmp_path):
    target = tracker(tmp_path)
    target.FILL_BUFFER_TIMEOUT = 0
    previous_tasks = asyncio.all_tasks()
    await target.record_fill(**fill(), execution_id="1")
    first = next(iter(target._pending_fills))
    await target.record_fill(**fill(quantity=3, fill_time="100000002"), execution_id="2")
    # Drive the real expiry method one arrival at a time, with no wall-clock race.
    timers = asyncio.all_tasks() - previous_tasks
    for timer in timers:
        timer.cancel()
    await asyncio.gather(*timers, return_exceptions=True)
    await target._process_timeout_fill(first)
    assert len(rows(target, "trade_history")) == 1
    assert len(target._pending_fills) == 1
    for key in list(target._pending_fills):
        await target._process_timeout_fill(key)
    assert remaining(target) == 5


@pytest.mark.asyncio
@pytest.mark.parametrize("identity", [None, "", "   ", 0, "0000"])
async def test_missing_identity_retains_legacy_arrivals_without_partial_loss(tmp_path, identity):
    target = tracker(tmp_path)
    target.FILL_BUFFER_TIMEOUT = 0
    await target.record_fill(**fill(), execution_id=identity)
    await target.record_fill(**fill(), execution_id=identity)
    order(target)
    await target._process_buffered_fill("000123", "20260909")
    assert remaining(target) == 4
    assert len(rows(target, "trade_history")) == 2
    with sqlite3.connect(target.db_path) as conn:
        assert conn.execute("SELECT execution_id FROM trade_history").fetchall() == [(None,), (None,)]
    await target.record_fill(**fill(), execution_id=identity)
    assert remaining(target) == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("identity", [-1, "-001", 1.0, "1.0", True])
async def test_invalid_numeric_id_does_not_write_or_buffer(tmp_path, identity):
    target = tracker(tmp_path)
    with pytest.raises(ValueError):
        await target.record_fill(**fill(), execution_id=identity)
    assert target._pending_fills == {}
    assert rows(target, "trade_history") == []


@pytest.mark.asyncio
async def test_identity_domain_separates_dates_orders_modes_products_and_providers(tmp_path):
    targets = [
        tracker(tmp_path), tracker(tmp_path, trading_mode="paper"),
        tracker(tmp_path, product="overseas_futures"), tracker(tmp_path, provider="other-provider"),
    ]
    for target in targets:
        for date, number in [("20260909", "123"), ("20260910", "123"), ("20260909", "124")]:
            args = fill(order_date=date, order_no=number, commda_code="10")
            assert await target.record_fill(**args, execution_id="same") == "manual"
            assert await target.record_fill(**args, execution_id="same") == "manual"
    assert len(rows(targets[0], "trade_history")) == 12


def test_concurrent_connections_gate_before_fifo_mutation(tmp_path):
    first, second = tracker(tmp_path), tracker(tmp_path)
    barrier = Barrier(2)

    def write(target):
        barrier.wait(timeout=5)
        return asyncio.run(target.record_fill(**fill(commda_code="10"), execution_id="race"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write, target) for target in (first, second)]
        assert [future.result(timeout=10) for future in futures] == ["manual", "manual"]
    assert len(rows(first, "trade_history")) == 1
    assert remaining(first) == 2


def test_concurrent_conflicting_identity_accepts_only_one_payload(tmp_path):
    first, second = tracker(tmp_path), tracker(tmp_path)
    barrier = Barrier(2)

    def write(target, quantity):
        barrier.wait(timeout=5)
        try:
            return asyncio.run(target.record_fill(**fill(commda_code="10", quantity=quantity), execution_id="race"))
        except ExecutionIdentityConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write, first, 2), pool.submit(write, second, 3)]
        assert sorted(future.result(timeout=10) for future in futures) == ["conflict", "manual"]
    with sqlite3.connect(first.db_path) as conn:
        quantities = conn.execute("SELECT quantity FROM trade_history").fetchall()
    assert len(quantities) == 1
    assert remaining(first) == quantities[0][0]


@pytest.mark.asyncio
@pytest.mark.parametrize("side", ["buy", "sell"])
async def test_history_write_failure_rolls_back_fifo_and_identity(tmp_path, side):
    target = tracker(tmp_path)
    if side == "sell":
        await target.record_fill(**fill(commda_code="10"), execution_id="opening")
    args = fill(commda_code="10", side=side, quantity=1 if side == "sell" else 2)
    before = rows(target, "trade_history"), rows(target, "workflow_position_lots")
    with sqlite3.connect(target.db_path) as conn:
        conn.execute("CREATE TRIGGER reject_history BEFORE INSERT ON trade_history BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
    with pytest.raises(sqlite3.IntegrityError, match="synthetic failure"):
        await target.record_fill(**args, execution_id="atomic")
    assert (rows(target, "trade_history"), rows(target, "workflow_position_lots")) == before
    with sqlite3.connect(target.db_path) as conn:
        conn.execute("DROP TRIGGER reject_history")
    assert await target.record_fill(**args, execution_id="atomic") == "manual"
    assert remaining(target) == (1 if side == "sell" else 2)


@pytest.mark.asyncio
async def test_existing_schema_rows_are_preserved_without_inferred_identity(tmp_path):
    path = tmp_path / "ledger.db"
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, product TEXT NOT NULL,
                provider TEXT NOT NULL, order_no TEXT, order_date TEXT, symbol TEXT,
                exchange TEXT, side TEXT, quantity INTEGER, price REAL,
                fill_datetime TEXT, classification TEXT, commda_code TEXT,
                realized_pnl REAL, trading_mode TEXT NOT NULL DEFAULT 'live', created_at TEXT
            )
        """)
        conn.execute("""
            INSERT INTO trade_history(product, provider, order_no, order_date, symbol,
                exchange, side, quantity, price, fill_datetime, classification, commda_code,
                realized_pnl, trading_mode, created_at)
            VALUES ('overseas_stock', 'ls', '000123', '20260909', 'SYNTH', 'TEST',
                'buy', 2, 100, '20260909_100000001', 'manual', '10', 0, 'live', 'original')
        """)
        old = conn.execute("SELECT * FROM trade_history").fetchone()
    target = tracker(tmp_path)
    migrated = rows(target, "trade_history")[0]
    assert migrated[:len(old)] == old
    # Additive columns backfill to NULL, never inferred: the three execution
    # identity columns plus the four account-avg-price estimate columns
    # (unmatched_qty, estimate_basis_price, estimate_source, estimated_pnl).
    assert migrated[len(old):] == (None, None, None, None, None, None, None)
    await target.record_fill(**fill(commda_code="10"), execution_id="new-evidence")
    assert len(rows(target, "trade_history")) == 2
    assert rows(target, "trade_history")[0] == migrated
    assert len(rows(tracker(tmp_path), "trade_history")) == 2
