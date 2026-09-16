"""Bounded, journalled cancellation of this execution's verified pending orders.

The host must pause and drain strategy order nodes before entering this operation.
Requests are never repeated automatically, including after a transport timeout.
Only the verified overseas-stock terminal evidence is currently supported.
"""

import asyncio
from datetime import datetime, timezone
import sqlite3

from .broker_snapshot import read_broker_snapshot
from .broker_order_totals import read_stock_order_outcomes
from .order_cancellation import cancellation_quantity
from .position_reconciliation import ReconciliationUnavailable, normalized_symbol, quantity


def owned_targets(tracker, snapshot):
    snapshot.validated_quantities(tracker, tracker.execution_key, datetime.now(timezone.utc))
    if tracker.product != "overseas_stock" or tracker.provider not in {"ls", "ls-sec.co.kr"}:
        raise ReconciliationUnavailable("unsupported_owned_cancellation_product")
    targets, seen = [], set()
    with sqlite3.connect(tracker.db_path) as conn:
        for pending in snapshot.pending_orders:
            day, number = pending["order_date"], str(pending["order_id"]).lstrip("0")
            try:
                datetime.strptime(day, "%Y%m%d")
                if len(day) != 8 or not number.isdigit() or int(number) <= 0 or (day, number) in seen:
                    raise ValueError
            except (TypeError, ValueError):
                raise ReconciliationUnavailable("invalid_pending_order_identity") from None
            seen.add((day, number))
            scope = tracker.product, tracker.provider, tracker.trading_mode
            rows = conn.execute("""SELECT symbol,exchange,side,quantity FROM workflow_orders
                WHERE product=? AND provider=? AND trading_mode=? AND order_date=?
                AND ltrim(order_no,'0')=?""", (*scope, day, number)).fetchall()
            if not rows:
                continue  # Manual and other executions' orders are never targets.
            if len(rows) != 1:
                raise ReconciliationUnavailable("ambiguous_owned_pending_order")
            symbol, exchange, side, ordered = rows[0]
            if (normalized_symbol(symbol, tracker.product) != normalized_symbol(pending["symbol"], tracker.product)
                    or side != pending["side"]
                    or {"81": "NYSE", "82": "NASDAQ"}.get(pending["market_code"]) != exchange
                    or not 0 < quantity(pending["remaining_quantity"]) <= quantity(ordered)):
                raise ReconciliationUnavailable("pending_order_ownership_conflict")
            if cancellation_quantity(conn, tracker, day, number, symbol, side):
                raise ReconciliationUnavailable("cancelled_order_still_pending")
            targets.append(dict(order_date=day, order_no=number, symbol=symbol,
                                exchange=exchange, side=side, quantity=ordered))
    if len(targets) > 20:
        raise ReconciliationUnavailable("too_many_pending_cancellations")
    return targets


def _journal(tracker, target, result=None):
    """Claim before sending; a crash leaves an unresolved, non-repeatable attempt."""
    with sqlite3.connect(tracker.db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""CREATE TABLE IF NOT EXISTS owned_cancellation_attempts (
            order_date TEXT NOT NULL, order_no TEXT NOT NULL, status TEXT NOT NULL,
            cancel_order_no TEXT, attempted_at TEXT NOT NULL,
            PRIMARY KEY(order_date,order_no))""")
        key = target["order_date"], target["order_no"]
        if result is None:
            existing = conn.execute("""SELECT status,cancel_order_no FROM owned_cancellation_attempts
                                   WHERE order_date=? AND order_no=?""", key).fetchone()
            if existing:
                return False
            conn.execute("INSERT INTO owned_cancellation_attempts VALUES (?,?,'outcome_unknown',NULL,?)",
                         (*key, datetime.now(timezone.utc).isoformat()))
            return True
        accepted = result.get("success") is True and result.get("status") == "accepted"
        child = str(result.get("cancel_order_no", ""))
        accepted = accepted and child.isdigit() and int(child) > 0
        conn.execute("""UPDATE owned_cancellation_attempts SET status=?,cancel_order_no=?
                        WHERE order_date=? AND order_no=?""",
                     ("accepted" if accepted else "outcome_unknown", child if accepted else None, *key))


def _previous_targets(tracker):
    with sqlite3.connect(tracker.db_path) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='owned_cancellation_attempts'").fetchone():
            return []
        rows = conn.execute("""SELECT o.order_date,ltrim(o.order_no,'0'),o.symbol,o.exchange,o.side,o.quantity
            FROM workflow_orders o JOIN owned_cancellation_attempts a
            ON a.order_date=o.order_date AND a.order_no=ltrim(o.order_no,'0')
            WHERE o.product=? AND o.provider=? AND o.trading_mode=? AND a.status!='confirmed'
            ORDER BY a.attempted_at DESC LIMIT 21""",
            (tracker.product, tracker.provider, tracker.trading_mode)).fetchall()
        if len(rows) > 20:
            raise ReconciliationUnavailable("too_many_pending_cancellations")
        return [dict(zip(("order_date", "order_no", "symbol", "exchange", "side", "quantity"), row)) for row in rows]


async def cancel_owned_pending_orders(ls, tracker, send_cancel, *, can_send):
    """Read once, send each claimed request once, then read terminal evidence once.

    A partial cancellation, rejected read or raced fill stays pending. A future
    explicit call rechecks history but cannot resend a journalled request.
    """
    if not tracker.execution_key or not can_send():
        raise ReconciliationUnavailable("cancellation_requires_quiescent_execution")
    snapshot = await asyncio.wait_for(read_broker_snapshot(
        ls, execution_key=tracker.execution_key, product=tracker.product,
        provider=tracker.provider, trading_mode=tracker.trading_mode), timeout=60)
    targets = owned_targets(tracker, snapshot.positions)
    keys = {(t["order_date"], t["order_no"]) for t in targets}
    targets.extend(t for t in _previous_targets(tracker) if (t["order_date"], t["order_no"]) not in keys)
    if len(targets) > 20:
        raise ReconciliationUnavailable("too_many_pending_cancellations")
    result = {"status": "no_owned_pending_orders", "cancelled_orders": [],
              "filled_orders": [], "pending_orders": [], "requested_orders": [], "failed_orders": []}
    if not targets:
        return result
    for target in targets:
        if not can_send():
            raise ReconciliationUnavailable("cancellation_execution_state_changed")
        snapshot.positions.validated_quantities(tracker, tracker.execution_key, datetime.now(timezone.utc))
        if _journal(tracker, target):
            try:
                response = await asyncio.wait_for(send_cancel(target), timeout=15)
                ack = response.get("cancel_result", {})
                _journal(tracker, target, ack)
                if ack.get("success") is True and ack.get("status") == "accepted":
                    result["requested_orders"].append({k: target[k] for k in ("order_date", "order_no")})
            except asyncio.CancelledError:
                raise
            except Exception:
                # Submission may have reached the broker. Persisted intent prevents retry.
                pass
            await asyncio.sleep(2)
    try:
        totals, cancellations = await asyncio.wait_for(
            read_stock_order_outcomes(ls, tracker, targets), timeout=60)
        # Only report verified terminal facts here. Recovery/FIFO changes belong to
        # startup under its fill lock; cancel action must never create a trade.
        result["cancelled_orders"] = [dict(order_date=item.order_date, order_no=item.order_no) for item in cancellations]
        result["filled_orders"] = [dict(order_date=item.order_date, order_no=item.order_no) for item in totals]
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        result["confirmation_error"] = type(exc).__name__
    terminal = {(t["order_date"], t["order_no"]) for t in result["cancelled_orders"] + result["filled_orders"]}
    with sqlite3.connect(tracker.db_path) as conn:
        conn.executemany("UPDATE owned_cancellation_attempts SET status='confirmed' WHERE order_date=? AND order_no=?", terminal)
    result["pending_orders"] = [{k: t[k] for k in ("order_date", "order_no")}
                                for t in targets if (t["order_date"], t["order_no"]) not in terminal]
    result["status"] = "confirmation_pending" if result["pending_orders"] else "confirmed"
    return result
