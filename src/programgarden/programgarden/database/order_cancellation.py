"""Persist positively linked terminal cancellations, separately from executions.

Only the observed COSAQ00102 unfilled-original/cancel-child pattern is accepted.
An acknowledgement, an absent pending row, a name or CnfQty alone is insufficient.
Partial cancellation recovery remains held until its broker semantics are verified.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import sqlite3

from .position_reconciliation import ReconciliationUnavailable, normalized_symbol, quantity


@dataclass(frozen=True)
class VerifiedUnfilledCancellation:
    execution_key: str
    product: str
    provider: str
    trading_mode: str
    order_date: str
    order_no: str
    cancel_order_no: str
    symbol: str
    side: str
    ordered_quantity: Decimal
    exchange: str
    observed_at: datetime
    source: str = "COSAQ00102"

    def validate(self, tracker):
        if (not tracker.execution_key or self.execution_key != tracker.execution_key
                or (self.product, self.provider, self.trading_mode) !=
                (tracker.product, tracker.provider, tracker.trading_mode)
                or self.product != "overseas_stock" or self.source != "COSAQ00102"):
            raise ReconciliationUnavailable("cancellation_scope_mismatch")
        if (not isinstance(self.observed_at, datetime) or self.observed_at.tzinfo is None
                or not 0 <= (datetime.now(timezone.utc) - self.observed_at).total_seconds() <= 120):
            raise ReconciliationUnavailable("stale_cancellation_evidence")
        try:
            datetime.strptime(self.order_date, "%Y%m%d")
            if len(self.order_date) != 8:
                raise ValueError
            numbers = [str(value).lstrip("0") for value in (self.order_no, self.cancel_order_no)]
            if any(not value.isdigit() or int(value) <= 0 for value in numbers):
                raise ValueError
        except (TypeError, ValueError):
            raise ReconciliationUnavailable("invalid_cancellation_identity") from None
        if (numbers[0] == numbers[1] or self.side not in {"buy", "sell"}
                or self.exchange not in {"NYSE", "NASDAQ"} or quantity(self.ordered_quantity) <= 0):
            raise ReconciliationUnavailable("invalid_cancellation_identity")
        return numbers


def initialize_cancellations(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS workflow_order_cancellations (
        product TEXT NOT NULL, provider TEXT NOT NULL, trading_mode TEXT NOT NULL,
        order_date TEXT NOT NULL, order_no TEXT NOT NULL, cancel_order_no TEXT NOT NULL,
        symbol TEXT NOT NULL, side TEXT NOT NULL, quantity TEXT NOT NULL,
        source TEXT NOT NULL, observed_at TEXT NOT NULL,
        PRIMARY KEY(product,provider,trading_mode,order_date,order_no)
    )""")


def cancellation_quantity(conn, tracker, day, number, symbol, side):
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='workflow_order_cancellations'").fetchone()
    if not exists:
        return Decimal(0)
    row = conn.execute("""SELECT symbol,side,quantity FROM workflow_order_cancellations
        WHERE product=? AND provider=? AND trading_mode=? AND order_date=? AND order_no=?""",
        (tracker.product, tracker.provider, tracker.trading_mode, day, str(number).lstrip("0"))).fetchone()
    if not row:
        return Decimal(0)
    if (row[0] != normalized_symbol(symbol, tracker.product) or row[1] != side):
        raise ReconciliationUnavailable("cancellation_identity_conflict")
    return quantity(row[2])


def record_cancellations(tracker, cancellations):
    """Validate the entire batch against owned orders and atomically persist it."""
    with sqlite3.connect(tracker.db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        initialize_cancellations(conn)
        changes = 0
        for item in cancellations:
            if not isinstance(item, VerifiedUnfilledCancellation):
                raise ReconciliationUnavailable("unverified_cancellation")
            number, child = item.validate(tracker)
            scope = tracker.product, tracker.provider, tracker.trading_mode
            rows = conn.execute("""SELECT symbol,side,quantity,exchange FROM workflow_orders
                WHERE product=? AND provider=? AND trading_mode=? AND order_date=?
                AND ltrim(order_no,'0')=?""", (*scope, item.order_date, number)).fetchall()
            symbol = normalized_symbol(item.symbol, tracker.product)
            if (len(rows) != 1 or normalized_symbol(rows[0][0], tracker.product) != symbol
                    or rows[0][1] != item.side or quantity(rows[0][2]) != item.ordered_quantity
                    or rows[0][3] != item.exchange):
                raise ReconciliationUnavailable("cancellation_ownership_mismatch")
            for table in ("trade_history", "workflow_order_recoveries"):
                if conn.execute(f"""SELECT 1 FROM {table} WHERE product=? AND provider=?
                    AND trading_mode=? AND order_date=? AND ltrim(order_no,'0')=? LIMIT 1""",
                    (*scope, item.order_date, number)).fetchone():
                    raise ReconciliationUnavailable("cancellation_conflicts_with_execution")
            existing = conn.execute("""SELECT cancel_order_no,symbol,side,quantity FROM
                workflow_order_cancellations WHERE product=? AND provider=? AND trading_mode=?
                AND order_date=? AND order_no=?""", (*scope, item.order_date, number)).fetchone()
            facts = child, symbol, item.side, str(item.ordered_quantity)
            if existing:
                if (existing[:3] != facts[:3] or quantity(existing[3]) != item.ordered_quantity):
                    raise ReconciliationUnavailable("conflicting_cancellation_evidence")
                continue
            conn.execute("INSERT INTO workflow_order_cancellations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (*scope, item.order_date, number, *facts,
                          item.source, item.observed_at.isoformat()))
            changes += 1
        return changes
