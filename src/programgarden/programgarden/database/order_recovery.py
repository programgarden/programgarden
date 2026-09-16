"""Recover verified terminal order totals without inventing individual fills.

The aggregate is separate from trade_history. Late identified executions consume
its coverage, not its inventory, and cannot create another fill notification.
Nonterminal totals cannot establish which later executions overlap the snapshot.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import math
import re
import sqlite3

from .position_reconciliation import ReconciliationUnavailable, normalized_symbol, quantity


@dataclass(frozen=True)
class VerifiedOrderTotal:
    execution_key: str
    product: str
    provider: str
    trading_mode: str
    order_date: str
    order_no: str
    symbol: str
    side: str
    ordered_quantity: Decimal
    filled_quantity: Decimal
    average_price: Decimal
    remaining_quantity: Decimal
    currency: str
    fill_time: str
    observed_at: datetime
    source: str = "COSAQ00102"
    original_order_no: str = "0"

    def validate(self, tracker):
        if (not tracker.execution_key or self.execution_key != tracker.execution_key
                or (self.product, self.provider, self.trading_mode) !=
                (tracker.product, tracker.provider, tracker.trading_mode)
                or self.product != "overseas_stock" or self.source != "COSAQ00102"):
            raise ReconciliationUnavailable("order_total_scope_mismatch")
        if (not isinstance(self.observed_at, datetime) or self.observed_at.tzinfo is None
                or not 0 <= (datetime.now(timezone.utc) - self.observed_at).total_seconds() <= 120):
            raise ReconciliationUnavailable("stale_order_total")
        try:
            datetime.strptime(self.order_date, "%Y%m%d")
            if not re.fullmatch(r"\d{8}", self.order_date):
                raise ValueError
            number = str(self.order_no).lstrip("0")
            if not number.isdigit() or int(number) <= 0:
                raise ValueError
            if not re.fullmatch(r"\d{6}(?:\d{3})?", self.fill_time):
                raise ValueError
            datetime.strptime(self.fill_time[:6], "%H%M%S")
        except (ValueError, TypeError):
            raise ReconciliationUnavailable("invalid_order_total_identity") from None
        total, filled, remainder, price = map(quantity, (
            self.ordered_quantity, self.filled_quantity, self.remaining_quantity, self.average_price))
        if (total <= 0 or filled != total or remainder != 0 or price <= 0
                or str(self.original_order_no).strip("0")
                or self.side not in {"buy", "sell"}
                or not isinstance(self.currency, str) or not re.fullmatch(r"[A-Z]{3}", self.currency)):
            raise ReconciliationUnavailable("nonterminal_or_ambiguous_order_total")
        if not all(math.isfinite(float(value)) for value in (total, price, total * price)):
            raise ReconciliationUnavailable("order_total_out_of_range")
        return number, normalized_symbol(self.symbol, self.product), total, price


def initialize_recovery(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workflow_order_recoveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT NOT NULL, provider TEXT NOT NULL, trading_mode TEXT NOT NULL,
            order_date TEXT NOT NULL, order_no TEXT NOT NULL, symbol TEXT NOT NULL,
            exchange TEXT NOT NULL, side TEXT NOT NULL,
            total_quantity TEXT NOT NULL, total_amount TEXT NOT NULL,
            recovered_quantity TEXT NOT NULL, recovered_price TEXT NOT NULL,
            estimated_pnl TEXT NOT NULL, currency TEXT NOT NULL,
            fill_datetime TEXT NOT NULL, source TEXT NOT NULL, observed_at TEXT NOT NULL,
            baseline_fill_ids TEXT NOT NULL,
            coverage_quantity TEXT NOT NULL, coverage_amount TEXT NOT NULL,
            legacy_fill_ids TEXT NOT NULL,
            UNIQUE(product,provider,trading_mode,order_date,order_no)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recovered_execution_observations (
            recovery_id INTEGER NOT NULL REFERENCES workflow_order_recoveries(id),
            execution_id TEXT NOT NULL, quantity TEXT NOT NULL, amount TEXT NOT NULL,
            execution_payload TEXT NOT NULL,
            PRIMARY KEY(recovery_id,execution_id)
        )
    """)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(workflow_position_lots)")}
    if "recovery_id" not in columns:
        conn.execute("ALTER TABLE workflow_position_lots ADD COLUMN recovery_id INTEGER")


def recovery_for_order(conn, tracker, day, number):
    row = conn.execute("""
        SELECT * FROM workflow_order_recoveries WHERE product=? AND provider=?
        AND trading_mode=? AND order_date=? AND order_no=?
    """, (tracker.product, tracker.provider, tracker.trading_mode, day, str(number).lstrip("0"))).fetchone()
    if row is None:
        return None
    names = [row[1] for row in conn.execute("PRAGMA table_info(workflow_order_recoveries)")]
    return dict(zip(names, row))


def adjacent_order_dates(day):
    """Date mismatches require evidence; never infer that two fills are the same."""
    try:
        parsed = datetime.strptime(day, "%Y%m%d")
    except (TypeError, ValueError):
        raise ReconciliationUnavailable("invalid_order_total_identity") from None
    return tuple((parsed + timedelta(days=offset)).strftime("%Y%m%d") for offset in (-1, 1))


def orders_needing_recovery(tracker):
    """Include partial fills; absence of any history row is not the criterion."""
    result = []
    with sqlite3.connect(tracker.db_path) as conn:
        scope = tracker.product, tracker.provider, tracker.trading_mode
        orders = conn.execute("""SELECT order_date,order_no,symbol,side,quantity FROM workflow_orders
            WHERE product=? AND provider=? AND trading_mode=? ORDER BY order_date,id""", scope).fetchall()
        for day, number, symbol, side, ordered in orders:
            recovered = recovery_for_order(conn, tracker, day, number)
            if recovered:
                continue
            fills = conn.execute("""SELECT quantity,execution_id FROM trade_history
                WHERE product=? AND provider=? AND trading_mode=? AND order_date=?
                AND ltrim(order_no,'0')=?""", (*scope, day, str(number).lstrip("0"))).fetchall()
            if (any(not row[1] for row in fills)
                    or sum((quantity(row[0]) for row in fills), Decimal(0)) != quantity(ordered)):
                result.append({"order_date": day, "order_no": number, "symbol": symbol,
                               "side": side, "quantity": ordered})
    return result


def recover_totals(tracker, totals):
    """Apply a validated batch under the tracker lock, with one SQLite commit."""
    validated = []
    identities = set()
    for total in totals:
        if not isinstance(total, VerifiedOrderTotal):
            raise ReconciliationUnavailable("unverified_order_total")
        facts = total.validate(tracker)
        key = total.order_date, facts[0]
        if key in identities:
            raise ReconciliationUnavailable("duplicate_order_total")
        identities.add(key)
        validated.append((total, facts))
    results = []
    with sqlite3.connect(tracker.db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        # Aggregate execution times are only a recovery ordering, never invented
        # timestamps for individual executions. Missing basis fails closed.
        for total, (number, symbol, total_qty, price) in sorted(
                validated, key=lambda item: (item[0].order_date, item[0].fill_time, int(item[1][0]))):
            scope = tracker.product, tracker.provider, tracker.trading_mode
            orders = conn.execute("""
                SELECT symbol,exchange,side,quantity FROM workflow_orders
                WHERE product=? AND provider=? AND trading_mode=? AND order_date=?
                AND ltrim(order_no,'0')=?
            """, (*scope, total.order_date, number)).fetchall()
            if (len(orders) != 1 or normalized_symbol(orders[0][0], tracker.product) != symbol
                    or orders[0][2] != total.side or quantity(orders[0][3]) != total_qty):
                raise ReconciliationUnavailable("order_total_ownership_mismatch")
            exchange = orders[0][1] or ""
            # Legacy classification permits a bounded date window, but recovery
            # cannot count those rows again using an invented canonical date.
            nearby = conn.execute("""
                SELECT t.order_date FROM trade_history t WHERE t.product=?
                AND t.provider=? AND t.trading_mode=? AND ltrim(t.order_no,'0')=?
                AND t.order_date IN (?,?) AND NOT EXISTS (
                    SELECT 1 FROM workflow_orders o WHERE o.product=t.product
                    AND o.provider=t.provider AND o.trading_mode=t.trading_mode
                    AND o.order_date=t.order_date AND ltrim(o.order_no,'0')=?)
            """, (*scope, number, *adjacent_order_dates(total.order_date), number)).fetchone()
            if nearby:
                raise ReconciliationUnavailable("historical_fill_date_ambiguous")
            old = recovery_for_order(conn, tracker, total.order_date, number)
            total_amount = total_qty * price
            if old:
                if (old["symbol"] != symbol or old["side"] != total.side
                        or Decimal(old["total_quantity"]) != total_qty
                        or Decimal(old["total_amount"]) != total_amount
                        or old["currency"] != total.currency):
                    raise ReconciliationUnavailable("conflicting_order_total")
                continue
            fills = conn.execute("""
                SELECT id,symbol,side,quantity,price,classification,execution_id,currency
                FROM trade_history WHERE product=? AND provider=? AND trading_mode=?
                AND order_date=? AND ltrim(order_no,'0')=? ORDER BY id
            """, (*scope, total.order_date, number)).fetchall()
            known_qty, known_amount = Decimal(0), Decimal(0)
            legacy_qty, legacy_amount = Decimal(0), Decimal(0)
            legacy_ids = []
            for fill_id, fsymbol, side, qty, fprice, classification, execution_id, currency in fills:
                if (normalized_symbol(fsymbol, tracker.product) != symbol or side != total.side
                        or classification != "workflow"
                        or currency not in (None, total.currency)):
                    raise ReconciliationUnavailable("ambiguous_recorded_order_fills")
                known_qty += quantity(qty)
                known_amount += quantity(qty) * quantity(fprice)
                if not execution_id:
                    legacy_ids.append(fill_id)
                    legacy_qty += quantity(qty)
                    legacy_amount += quantity(qty) * quantity(fprice)
            missing = total_qty - known_qty
            missing_amount = total_amount - known_amount
            if missing < 0 or (missing == 0 and abs(missing_amount) > Decimal("0.000001")):
                raise ReconciliationUnavailable("order_total_below_recorded_fills")
            if not missing and not legacy_ids:
                continue
            if missing > 0 and missing_amount <= 0:
                raise ReconciliationUnavailable("invalid_missing_execution_price")
            recovered_price = missing_amount / missing if missing else price
            if not math.isfinite(float(recovered_price)):
                raise ReconciliationUnavailable("recovery_price_out_of_range")
            fill_datetime = total.order_date + "_" + total.fill_time
            # A newly discovered earlier buy cannot silently rewrite an already
            # valued sell or an external quantity adjustment. That requires a
            # complete historical replay, not this bounded recovery.
            if total.side == "buy" and missing:
                later_sell = conn.execute("""
                    SELECT 1 FROM trade_history WHERE product=? AND provider=? AND trading_mode=?
                    AND symbol=? AND classification='workflow' AND side='sell' AND fill_datetime>=? LIMIT 1
                """, (*scope, symbol, fill_datetime)).fetchone()
                adjusted = conn.execute("SELECT 1 FROM sqlite_master WHERE name='position_adjustments'").fetchone()
                if adjusted:
                    adjusted = conn.execute("""SELECT 1 FROM position_adjustments WHERE product=?
                        AND provider=? AND trading_mode=? AND symbol=? LIMIT 1""", (*scope, symbol)).fetchone()
                if later_sell or adjusted:
                    raise ReconciliationUnavailable("historical_buy_requires_full_replay")
            pnl = Decimal(0)
            lots = []
            if total.side == "sell" and missing:
                lots = conn.execute("""
                    SELECT id,buy_price,remaining_qty FROM workflow_position_lots WHERE product=?
                    AND provider=? AND trading_mode=? AND symbol=? AND classification='workflow'
                    AND remaining_qty>0 AND fill_datetime<=? ORDER BY fill_datetime,id
                """, (*scope, symbol, fill_datetime)).fetchall()
                if (any(quantity(row[1]) <= 0 for row in lots)
                        or sum((quantity(row[2]) for row in lots), Decimal(0)) < missing):
                    raise ReconciliationUnavailable("recovery_cost_basis_unavailable")
            cursor = conn.execute("""
                INSERT INTO workflow_order_recoveries
                (product,provider,trading_mode,order_date,order_no,symbol,exchange,side,
                 total_quantity,total_amount,recovered_quantity,recovered_price,estimated_pnl,
                 currency,fill_datetime,source,observed_at,baseline_fill_ids,
                 coverage_quantity,coverage_amount,legacy_fill_ids)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (*scope, total.order_date, number, symbol, exchange, total.side, str(total_qty),
                  str(total_amount), str(missing), str(recovered_price), "0", total.currency,
                  fill_datetime, total.source, total.observed_at.isoformat(), json.dumps([row[0] for row in fills]),
                  str(missing + legacy_qty), str(missing_amount + legacy_amount), json.dumps(legacy_ids)))
            recovery_id = cursor.lastrowid
            if total.side == "buy" and missing:
                conn.execute("""
                    INSERT INTO workflow_position_lots
                    (product,provider,trading_mode,symbol,exchange,fill_datetime,buy_price,
                     original_qty,remaining_qty,classification,order_no,order_date,created_at,recovery_id)
                    VALUES (?,?,?,?,?,?,?,?,?,'workflow',?,?,?,?)
                """, (*scope, symbol, exchange, fill_datetime, float(recovered_price), float(missing),
                      float(missing), number, total.order_date, datetime.now(timezone.utc).isoformat(), recovery_id))
            elif total.side == "sell" and missing:
                remainder = missing
                for lot_id, basis, available in lots:
                    used = min(remainder, quantity(available))
                    pnl += (recovered_price - quantity(basis)) * used
                    conn.execute("UPDATE workflow_position_lots SET remaining_qty=? WHERE id=?",
                                 (float(quantity(available) - used), lot_id))
                    remainder -= used
                    if not remainder:
                        break
                conn.execute("UPDATE workflow_order_recoveries SET estimated_pnl=? WHERE id=?", (str(pnl), recovery_id))
            results.append({"id": recovery_id, "order_date": total.order_date, "order_no": number,
                            "symbol": symbol, "side": total.side, "quantity": str(missing),
                            "estimated_pnl": str(pnl), "currency": total.currency,
                            "basis": "broker_order_total", "is_estimated": True, "is_trade": False})
    return results


def observe_covered_execution(conn, tracker, fill):
    """Return True for a late fill already covered by a terminal aggregate."""
    row = recovery_for_order(conn, tracker, fill.order_date, fill.order_no)
    from .workflow_position_tracker import ExecutionIdentityConflictError
    if row is None:
        scope = tracker.product, tracker.provider, tracker.trading_mode
        number = str(fill.order_no).lstrip("0")
        exact_order = conn.execute("""SELECT 1 FROM workflow_orders WHERE product=?
            AND provider=? AND trading_mode=? AND order_date=? AND ltrim(order_no,'0')=?""",
            (*scope, fill.order_date, number)).fetchone()
        if not exact_order:
            try:
                dates = adjacent_order_dates(fill.order_date)
            except ReconciliationUnavailable:
                raise ExecutionIdentityConflictError("Covered execution needs a valid order date") from None
            nearby = conn.execute("""SELECT 1 FROM workflow_order_recoveries WHERE product=?
                AND provider=? AND trading_mode=? AND order_no=? AND order_date IN (?,?)""",
                (*scope, number, *dates)).fetchone()
            if nearby:
                raise ExecutionIdentityConflictError("Execution date may overlap a recovered order")
        return False
    identity = tracker._execution_key(fill)
    if identity is None:
        raise ExecutionIdentityConflictError("Recovered orders require an explicit live execution identity")
    if (normalized_symbol(fill.symbol, tracker.product) != row["symbol"] or fill.side != row["side"]
            or fill.exchange != row["exchange"] or fill.currency not in (None, row["currency"])):
        raise ExecutionIdentityConflictError("Live execution conflicts with recovered order")
    facts = tracker._execution_facts(fill)
    facts = {**facts, "quantity": str(facts["quantity"].normalize()),
             "price": str(facts["price"].normalize())}
    payload = json.dumps(facts, default=str, sort_keys=True)
    previous = conn.execute("""SELECT execution_payload FROM recovered_execution_observations
        WHERE recovery_id=? AND execution_id=?""", (row["id"], identity[5])).fetchone()
    if previous:
        if previous[0] != payload:
            raise ExecutionIdentityConflictError("Conflicting covered execution replay")
        return True
    qty, price = quantity(fill.quantity), quantity(fill.price)
    if qty <= 0 or price <= 0:
        raise ExecutionIdentityConflictError("Invalid covered execution quantity or price")
    observations = conn.execute("SELECT quantity,amount FROM recovered_execution_observations WHERE recovery_id=?", (row["id"],)).fetchall()
    consumed = sum((Decimal(r[0]) for r in observations), Decimal(0)) + qty
    amount = sum((Decimal(r[1]) for r in observations), Decimal(0)) + qty * price
    covered_qty = Decimal(row["coverage_quantity"])
    covered_amount = Decimal(row["coverage_amount"])
    tolerance = max(Decimal("0.000001"), abs(covered_amount) * Decimal("0.000000001"))
    if (consumed > covered_qty or amount > covered_amount + tolerance
            or (consumed == covered_qty and abs(amount - covered_amount) > tolerance)):
        raise ExecutionIdentityConflictError("Late executions exceed or contradict recovered total")
    conn.execute("INSERT INTO recovered_execution_observations VALUES (?,?,?,?,?)",
                 (row["id"], identity[5], str(qty), str(qty * price), payload))
    return True
