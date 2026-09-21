"""Use the immutable SQLite adjustment audit as a durable, acknowledged outbox."""

import hashlib
import sqlite3
import asyncio
import logging

logger = logging.getLogger(__name__)


def _destination(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise ValueError("A delivery destination is required")
    return hashlib.sha256(value.encode()).hexdigest()


def _initialize(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS position_adjustment_deliveries (
        adjustment_id INTEGER NOT NULL, destination TEXT NOT NULL,
        delivered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(adjustment_id,destination))""")


def pending_adjustments(tracker, destination, limit=100):
    """Return oldest unsent records, including after a crash or failed HTTP call."""
    destination = _destination(destination)
    if not tracker.execution_key:
        raise ValueError("Adjustment delivery requires execution-scoped storage")
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    with sqlite3.connect(tracker.db_path) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='position_adjustments'").fetchone():
            return []
        _initialize(conn)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT a.id AS adjustment_id,a.product,a.trading_mode,a.symbol,
            a.previous_quantity,a.broker_quantity,a.retained_quantity,a.source,a.observed_at,a.created_at,a.reason
            FROM position_adjustments a LEFT JOIN position_adjustment_deliveries d
            ON a.id=d.adjustment_id AND d.destination=?
            WHERE a.product=? AND a.provider=? AND a.trading_mode=? AND d.adjustment_id IS NULL
            ORDER BY a.id LIMIT ?""", (destination, tracker.product, tracker.provider, tracker.trading_mode, limit)).fetchall()
        return [dict(row) for row in rows]


def acknowledge_adjustments(tracker, destination, ids):
    """Acknowledge only server-accepted IDs; preserve every original audit row."""
    destination = _destination(destination)
    if (not tracker.execution_key or not isinstance(ids, (list, tuple)) or len(ids) > 500
            or any(type(value) is not int or value <= 0 for value in ids)):
        raise ValueError("Invalid adjustment acknowledgement")
    with sqlite3.connect(tracker.db_path) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='position_adjustments'").fetchone():
            return
        _initialize(conn)
        conn.executemany("""INSERT OR IGNORE INTO position_adjustment_deliveries(adjustment_id,destination)
            SELECT id,? FROM position_adjustments WHERE id=? AND product=? AND provider=? AND trading_mode=?""",
            [(destination, value, tracker.product, tracker.provider, tracker.trading_mode) for value in ids])


class AdjustmentDelivery:
    """Replay the audit through a host-supplied authenticated transport."""

    def __init__(self, get_tracker, destination, send, *, interval=10):
        _destination(destination)
        self.get_tracker, self.destination, self.send = get_tracker, destination, send
        self.interval = interval
        self.task = None
        self._lock = asyncio.Lock()

    async def flush(self):
        async with self._lock:
            try:
                tracker = self.get_tracker()
                if tracker is None or not tracker.execution_key:
                    return
                rows = tracker.pending_position_adjustments(self.destination)
                if not rows:
                    return
                accepted = await asyncio.wait_for(self.send(rows), timeout=5)
                sent = {row["adjustment_id"] for row in rows}
                if (not isinstance(accepted, list) or any(type(value) is not int for value in accepted)
                        or not set(accepted) <= sent):
                    return
                tracker.acknowledge_position_adjustments(self.destination, accepted)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Keep the audit for the next attempt; never log payloads or tokens.
                logger.warning("Adjustment delivery deferred: %s", type(exc).__name__)

    async def _run(self):
        while True:
            await self.flush()
            await asyncio.sleep(self.interval)

    def start(self):
        if self.task is None:
            self.task = asyncio.create_task(self._run())

    async def stop(self):
        if self.task is not None:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        await self.flush()
