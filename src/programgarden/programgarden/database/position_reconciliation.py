"""Reduce owned lots using a complete, fresh snapshot; never manufacture fills.

Only a runtime broker adapter may supply the snapshot. It is not a DSL input or
a cached account-tracker dictionary. The caller must verify both holdings and
pending orders before constructing it and must apply it before order execution.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import re
import sqlite3
from typing import Mapping


class ReconciliationUnavailable(RuntimeError):
    """Keep execution held when safe reconciliation cannot be established."""


def normalized_symbol(symbol: str, product: str) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ReconciliationUnavailable("missing_position_symbol")
    result = symbol.strip().upper()
    if product == "korea_stock" and re.fullmatch(r"[AQ][0-9]{6}", result):
        result = result[1:]
    return result


def quantity(value) -> Decimal:
    if isinstance(value, bool):
        raise ReconciliationUnavailable("invalid_position_quantity")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ReconciliationUnavailable("invalid_position_quantity") from None
    if not result.is_finite() or result < 0:
        raise ReconciliationUnavailable("invalid_position_quantity")
    return result


@dataclass(frozen=True)
class VerifiedPositionSnapshot:
    execution_key: str
    product: str
    provider: str
    trading_mode: str
    observed_at: datetime
    quantities: Mapping[str, Decimal]
    source: str
    positions_complete: bool
    pending_orders_verified: bool
    pending_orders: tuple[dict, ...] = ()

    def validated_quantities(self, tracker, execution_key: str, now: datetime) -> dict[str, Decimal]:
        if (not execution_key or self.execution_key != execution_key
                or self.product != tracker.product or self.provider != tracker.provider
                or self.trading_mode != tracker.trading_mode):
            raise ReconciliationUnavailable("snapshot_identity_mismatch")
        if (self.positions_complete is not True or self.pending_orders_verified is not True
                or not isinstance(self.source, str) or not self.source.strip()
                or not isinstance(self.quantities, Mapping)):
            raise ReconciliationUnavailable("incomplete_account_snapshot")
        if (not isinstance(self.observed_at, datetime) or self.observed_at.tzinfo is None
                or now.tzinfo is None or not 0 <= (now - self.observed_at).total_seconds() <= 120):
            raise ReconciliationUnavailable("stale_account_snapshot")
        result = {}
        for symbol, value in self.quantities.items():
            key = normalized_symbol(symbol, self.product)
            if key in result:
                raise ReconciliationUnavailable("duplicate_position_symbol")
            result[key] = quantity(value)
        return result


def assert_order_evidence(conn, tracker, snapshot):
    """Never trim holdings while an owned fill may still be missing.

    A pending order is not a fill. For every retained acknowledgement, the
    recorded fills plus the explicitly observed remainder must account for the
    whole quantity. Absence from a pending list does not prove cancellation.
    In particular a partially filled order must not disappear from this check
    merely because one trade_history row already exists.
    """
    pending = {}
    for row in snapshot.pending_orders:
        try:
            day, number = row["order_date"], str(row["order_id"]).lstrip("0")
            datetime.strptime(day, "%Y%m%d")
            if not number.isdigit() or int(number) <= 0:
                raise ValueError
            key = day, number
            if key in pending:
                raise ValueError
            pending[key] = row
        except (KeyError, TypeError, ValueError):
            raise ReconciliationUnavailable("invalid_pending_order_identity") from None
    scope = tracker.product, tracker.provider, tracker.trading_mode
    orders = conn.execute("""
        SELECT order_date, order_no, symbol, side, quantity FROM workflow_orders
        WHERE product=? AND provider=? AND trading_mode=?
    """, scope).fetchall()
    for day, number, symbol, side, raw_qty in orders:
        key = day, str(number).lstrip("0")
        fills = conn.execute("""
            SELECT symbol, side, quantity, classification, execution_id FROM trade_history
            WHERE product=? AND provider=? AND trading_mode=? AND order_date=?
              AND ltrim(order_no, '0')=?
        """, (*scope, *key)).fetchall()
        symbol = normalized_symbol(symbol, tracker.product)
        total = Decimal(0)
        for fill_symbol, fill_side, fill_qty, classification, execution_id in fills:
            if (normalized_symbol(fill_symbol, tracker.product) != symbol or fill_side != side
                    or classification != "workflow"):
                raise ReconciliationUnavailable("ambiguous_order_fill_identity")
            if not execution_id:
                raise ReconciliationUnavailable("historical_execution_identity_unavailable")
            total += quantity(fill_qty)
        remainder = Decimal(0)
        if key in pending:
            row = pending[key]
            if normalized_symbol(row["symbol"], tracker.product) != symbol or row["side"] != side:
                raise ReconciliationUnavailable("pending_order_identity_mismatch")
            remainder = quantity(row["remaining_quantity"])
            # A still executable order could fill between the two REST reads.
            # Wait for terminal evidence before changing any owned lots.
            if remainder:
                raise ReconciliationUnavailable("owned_order_still_pending")
        if total != quantity(raw_qty):
            raise ReconciliationUnavailable("owned_fills_require_reconciliation")


def initialize_adjustments(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS position_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT NOT NULL, provider TEXT NOT NULL, trading_mode TEXT NOT NULL,
            symbol TEXT NOT NULL, previous_quantity TEXT NOT NULL, broker_quantity TEXT NOT NULL,
            retained_quantity TEXT NOT NULL, removed_lots TEXT NOT NULL,
            source TEXT NOT NULL, observed_at TEXT NOT NULL, created_at TEXT NOT NULL,
            reason TEXT NOT NULL
        )
    """)


def reconcile_lots(tracker, snapshot: VerifiedPositionSnapshot, execution_key: str,
                   *, now: datetime | None = None) -> list[dict]:
    """Called with the tracker's fill lock held; transaction covers all symbols.

    The existing FIFO policy removes oldest lots first. Original lot quantity,
    price and trade history are preserved, and the removed basis is audited.
    Account excess is never added to workflow ownership. Opposite-side futures
    quantities must already be separated by the verified product adapter.
    """
    now = now or datetime.now(timezone.utc)
    if not isinstance(snapshot, VerifiedPositionSnapshot):
        raise ReconciliationUnavailable("unverified_account_snapshot")
    positions = snapshot.validated_quantities(tracker, execution_key, now)
    adjustments = []
    with sqlite3.connect(tracker.db_path) as conn:
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("BEGIN IMMEDIATE")
        assert_order_evidence(conn, tracker, snapshot)
        initialize_adjustments(conn)
        rows = conn.execute("""
            SELECT id, symbol, remaining_qty, buy_price FROM workflow_position_lots
            WHERE product=? AND provider=? AND trading_mode=? AND classification='workflow'
              AND remaining_qty > 0 ORDER BY fill_datetime, id
        """, (tracker.product, tracker.provider, tracker.trading_mode)).fetchall()
        lots_by_symbol = {}
        for row in rows:
            lots_by_symbol.setdefault(normalized_symbol(row[1], tracker.product), []).append(row)
        for symbol, lots in lots_by_symbol.items():
            before = sum((quantity(row[2]) for row in lots), Decimal(0))
            available = positions.get(symbol, Decimal(0))
            after = min(before, available)
            remaining_trim = before - after
            if remaining_trim == 0:
                continue
            if any(normalized_symbol(order["symbol"], tracker.product) == symbol
                   and quantity(order["remaining_quantity"]) > 0 for order in snapshot.pending_orders):
                raise ReconciliationUnavailable("position_has_pending_orders")
            removed = []
            for lot_id, _, raw_qty, basis_price in lots:
                if remaining_trim == 0:
                    break
                old_qty = quantity(raw_qty)
                trimmed = min(old_qty, remaining_trim)
                conn.execute("UPDATE workflow_position_lots SET remaining_qty=? WHERE id=?",
                             (float(old_qty - trimmed), lot_id))
                removed.append({"lot_id": lot_id, "quantity": str(trimmed), "basis_price": basis_price})
                remaining_trim -= trimmed
            cursor = conn.execute("""
                INSERT INTO position_adjustments
                (product,provider,trading_mode,symbol,previous_quantity,broker_quantity,
                 retained_quantity,removed_lots,source,observed_at,created_at,reason)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (tracker.product, tracker.provider, tracker.trading_mode, symbol,
                  str(before), str(available), str(after), json.dumps(removed), snapshot.source,
                  snapshot.observed_at.isoformat(), now.isoformat(), "broker_quantity_reduction"))
            adjustments.append({"id": cursor.lastrowid, "symbol": symbol,
                                "previous_quantity": str(before), "quantity": str(after),
                                "removed_quantity": str(before - after),
                                "reason": "broker_quantity_reduction"})
    return adjustments
