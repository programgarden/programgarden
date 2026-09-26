"""In-memory order-intent replay; deliberately has no broker/HTTP dependency.

This is a fixture model, not an emulation of undocumented LS response fields.
It verifies submitted intents, risk decisions and state transitions. A successful
simulation is never evidence of broker acceptance, buying power or live fills.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import json
from typing import Any

from programgarden.replay_contracts import ContractViolation, check_contract, finite_json


def number(value: Any, name: str, *, positive: bool = False) -> Decimal:
    check_contract(value, {"type": "number", "minimum": 0}, name)
    result = Decimal(str(value))
    if positive and result <= 0:
        raise ContractViolation(name, "Expected a positive value")
    return result


class SimulationBook:
    def __init__(self, account: dict[str, Any], instruments: dict[str, Any], *, as_of: str):
        finite_json(account); finite_json(instruments)
        check_contract(as_of, {"type": "string", "format": "date-time"}, "as_of")
        check_contract(account, {"type": "object", "required": ["currency", "cash", "max_investment"],
            "properties": {"currency": {"type": "string", "minLength": 1}}}, "account")
        self.currency = account["currency"]
        self.cash = number(account["cash"], "cash")
        self.max_investment = number(account["max_investment"], "max_investment", positive=True)
        self.positions = deepcopy(account.get("positions", {}))
        self.entry_prices = deepcopy(account.get("entry_prices", {}))
        check_contract(self.positions, {"type":"object"}, "positions")
        check_contract(self.entry_prices, {"type":"object"}, "entry_prices")
        for symbol, quantity in self.positions.items():
            check_contract(quantity, {"type": "integer"}, f"positions.{symbol}")
        self.instruments = deepcopy(instruments)
        self.as_of = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        self.orders: dict[str, dict[str, Any]] = {}
        self.intent_keys: dict[str, str] = {}
        self.events: dict[str, str] = {}
        self.transitions: list[dict[str, Any]] = []
        self.operations: dict[str, dict[str, Any]] = {}
        self.operation_keys: dict[str, str] = {}
        # Simulated ids are NODE-BASED, not a running count, so an independent
        # suite designer names an order by the node that placed it instead of
        # predicting arithmetic. These count DISTINCT ids per placing node: the
        # 1st has no suffix, later ones get "#2", "#3". Idempotent re-submission
        # returns before assigning an id, so a duplicate never consumes an ordinal.
        self.node_order_counts: dict[str, int] = {}
        self.node_operation_counts: dict[str, int] = {}

    def snapshot(self):
        return {"cash": float(self.cash), "currency": self.currency,
                "positions": deepcopy(self.positions), "entry_prices": deepcopy(self.entry_prices),
                "orders": deepcopy(self.orders),
                "operations": deepcopy(self.operations),
                "reserved_cash": float(self._reserved_cash()),
                "transitions": deepcopy(self.transitions), "live_order_count": 0}

    def submit(self, intent: dict[str, Any], *, key: str, response: str = "accepted",
               filled_quantity: int = 0, node_id: str = "order") -> dict[str, Any]:
        check_contract(key, {"type":"string", "minLength":1, "maxLength":200}, "intent_key")
        finite_json(intent)
        if key in self.intent_keys:
            order = self.orders[self.intent_keys[key]]
            if self._event_payload(order["intent"]) != self._event_payload(intent):
                raise ContractViolation("intent_key", "An idempotency key cannot refer to a different order")
            return {**deepcopy(order), "duplicate": True}
        check_contract(intent, {"type": "object", "required": ["symbol", "exchange", "side", "quantity", "order_type"],
            "properties": {"symbol": {"type": "string", "minLength": 1},
                           "exchange": {"type": "string", "minLength": 1},
                           "side": {"type": "string", "enum": ["buy", "sell"]},
                           "quantity": {"type": "integer", "minimum": 1},
                           "order_type": {"type": "string", "enum": ["limit", "market"]}}}, "intent")
        if response not in ("accepted", "rejected", "partial_fill", "filled", "timeout"):
            raise ContractViolation("response", "Unsupported simulated order response")
        if response == "partial_fill":
            check_contract(filled_quantity, {"type":"integer", "minimum":1,
                           "maximum":intent["quantity"]-1}, "filled_quantity")
        symbol = intent["exchange"] + ":" + intent["symbol"]
        instrument = self.instruments.get(symbol)
        if not isinstance(instrument, dict):
            raise ContractViolation(symbol, "Instrument metadata is required", "REPLAY_FIXTURE_REQUIRED")
        check_contract(instrument, {"type": "object", "required": ["currency", "price", "as_of", "session_open", "tradeable", "tick_size", "max_age_seconds"],
            "properties": {"as_of": {"type": "string", "format": "date-time"},
                           "session_open": {"type": "boolean"}, "tradeable": {"type": "boolean"}}}, symbol)
        price = number(instrument["price"] if intent["order_type"] == "market" else intent.get("price"), "price", positive=True)
        tick = number(instrument["tick_size"], "tick_size", positive=True)
        cost_per_unit = number(instrument.get("margin_per_contract", float(price)), "unit_cost", positive=True)
        futures = instrument.get("product") == "overseas_futures"
        held = self.positions.get(symbol, 0)
        direction = 1 if intent["side"] == "buy" else -1
        closing = bool(futures and held * direction < 0)
        if futures:
            if "margin_per_contract" not in instrument or "multiplier" not in instrument:
                raise ContractViolation(symbol, "Futures simulation requires explicit margin assumptions and multiplier", "REPLAY_FIXTURE_REQUIRED")
            number(instrument["multiplier"], "multiplier", positive=True)
            if held:
                number(self.entry_prices.get(symbol), "entry_price", positive=True)
        elif held < 0:
            raise ContractViolation(symbol, "Stock short positions are not supported by this fixture book")
        cost = cost_per_unit * intent["quantity"]
        observed = datetime.fromisoformat(instrument["as_of"].replace("Z", "+00:00"))
        max_age = number(instrument["max_age_seconds"], "max_age_seconds")
        age = Decimal(str((self.as_of - observed).total_seconds()))
        active = [o for o in self.orders.values() if o["symbol_key"] == symbol and o["status"] in ("accepted", "partial_fill", "unknown")]
        pending_change = any(op["symbol_key"] == symbol and op["status"] in ("accepted", "unknown")
                             for op in self.operations.values())
        reason = None
        if instrument["currency"] != self.currency: reason = "currency_mismatch"
        elif not instrument["tradeable"]: reason = "instrument_not_tradeable"
        elif not instrument["session_open"]: reason = "market_closed"
        elif age < 0 or age > max_age: reason = "stale_market_data"
        elif price % tick: reason = "invalid_price_tick"
        elif active or pending_change: reason = "pending_or_unknown_order"
        # The LIVE NewOrderNode (executor.py) has NO held-symbol refusal for stocks:
        # LS accepts an additional buy while the account already holds the symbol.
        # The product's "no additional buy by default" is a chatbot CodeNode GUARD,
        # not an engine rule — so replaying a legitimate add-to-position workflow
        # must not reject it here. We mirror live: only futures ADDING to an open
        # position (same direction, i.e. held and not closing) stays refused; a
        # stock buy while held falls through to the normal budget/cash checks below.
        elif held and futures and not closing: reason = "position_already_held"
        elif closing and intent["quantity"] > abs(held): reason = "position_reversal_not_supported"
        elif not closing and (futures or intent["side"] == "buy") and cost + self._exposure() > self.max_investment: reason = "max_investment_exceeded"
        elif not closing and (futures or intent["side"] == "buy") and cost > self.cash - self._reserved_cash(): reason = "insufficient_cash"
        elif not futures and intent["side"] == "sell" and intent["quantity"] > held: reason = "insufficient_position"
        elif response == "rejected": reason = "simulated_broker_rejection"
        order_id = self._scoped_id("SIM-", node_id, self._next_ordinal(node_id, self.node_order_counts))
        order = {"order_id": order_id, "intent": deepcopy(intent), "symbol_key": symbol,
                 "status": "rejected" if reason else ("unknown" if response == "timeout" else "accepted"),
                 "reason": reason, "filled_quantity": 0, "unit_cost": float(cost_per_unit),
                 "fill_price": float(price), "simulation": True, "closing": closing, "futures": futures}
        self.orders[order_id] = order
        self.intent_keys[key] = order_id
        self.transitions.append({"order_id": order_id, "event": "submit", "status": order["status"]})
        if not reason and response in ("partial_fill", "filled"):
            quantity = intent["quantity"] if response == "filled" else filled_quantity
            self.fill(order_id, quantity, event_id=key + ":fill")
        return deepcopy(order)

    def _exposure(self):
        value = self._reserved_cash()
        for symbol, quantity in self.positions.items():
            if not quantity:
                continue
            instrument = self.instruments.get(symbol)
            if not isinstance(instrument, dict):
                raise ContractViolation(symbol, "Held positions require valuation metadata", "REPLAY_FIXTURE_REQUIRED")
            field = "margin_per_contract" if instrument.get("product") == "overseas_futures" else "price"
            value += number(instrument.get(field), field, positive=True) * abs(quantity)
        return value

    def _reserved_cash(self):
        reserved = sum((Decimal(str(o["unit_cost"])) * (o["intent"]["quantity"] - o["filled_quantity"])
                    for o in self.orders.values() if (o["intent"]["side"] == "buy" or o["futures"]) and not o["closing"]
                    and o["status"] in ("accepted", "partial_fill", "unknown")), Decimal(0))
        # A timed-out replacement can have reached the broker. Keep the larger
        # of original/replacement exposure until matching evidence reconciles it.
        for op in self.operations.values():
            if op["status"] not in ("accepted", "unknown"):
                continue
            original = self.orders[op["original_order_id"]]
            original_reserve = Decimal(str(original["unit_cost"])) * (
                original["intent"]["quantity"]-original["filled_quantity"])
            reserved += max(Decimal(0), Decimal(str(op.get("replacement_reserve", 0)))-original_reserve)
        return reserved

    def request_change(self, action: str, order_id: str, *, key: str,
                       response: str, replacement: dict[str, Any] | None = None,
                       node_id: str = "change"):
        """Record an acknowledged/unknown request without inventing completion.

        Replacement quantities are supported only before any fill. Partial-fill
        replacement quantity semantics need a separate broker-specific contract;
        this simulator does not guess whether a wire quantity means total or open.
        """
        check_contract(key, {"type":"string", "minLength":1, "maxLength":200}, "operation_key")
        check_contract(action, {"type":"string", "enum":["modify", "cancel"]}, "action")
        check_contract(response, {"type":"string", "enum":["accepted", "rejected", "timeout"]}, "response")
        payload = self._event_payload([action, order_id, replacement])
        if key in self.operation_keys:
            operation = self.operations[self.operation_keys[key]]
            if operation["payload"] != payload:
                raise ContractViolation("operation_key", "An operation key cannot change its target or payload")
            return {**deepcopy(operation), "duplicate":True}
        order = self.orders.get(order_id)
        if order is None:
            raise ContractViolation("original_order_id", "The target must exist in this simulation's order book")
        replacement_reserve = Decimal(0)
        reason = None
        if order["status"] not in ("accepted", "partial_fill"):
            reason = "original_order_not_open"
        elif order.get("pending_operation"):
            reason = "operation_pending_or_unknown"
        if action == "modify":
            if order["filled_quantity"]:
                raise ContractViolation("replacement", "Partial-fill replacement quantity semantics are unsupported", "REPLAY_CAPABILITY_BLOCKED")
            if replacement is None:
                raise ContractViolation("replacement", "An explicit resolved replacement intent is required")
            check_contract(replacement, {"type":"object", "required":["quantity", "price"],
                "additionalProperties":False, "properties":{
                    "quantity":{"type":"integer", "minimum":1},
                    "price":{"type":"number", "minimum":0}}}, "replacement")
            number(replacement["price"], "replacement.price", positive=True)
            if order["intent"]["order_type"] != "limit":
                raise ContractViolation("replacement", "Only limit-to-limit replacement has a replay contract", "REPLAY_CAPABILITY_BLOCKED")
            # Reuse the same risk implementation on a disposable probe book.
            # Remove the original reservation only in that probe. The actual
            # original stays reserved until confirmation arrives.
            probe = deepcopy(self)
            probe.orders[order_id]["status"] = "replaced"
            intended = {**order["intent"], **replacement}
            candidate = probe.submit(intended, key="replacement-risk-check", response="accepted")
            reason = reason or candidate["reason"]
            if (order["intent"]["side"] == "buy" or order["futures"]) and not order["closing"]:
                replacement_reserve = Decimal(str(candidate["unit_cost"])) * replacement["quantity"]
        elif replacement is not None:
            raise ContractViolation("replacement", "A cancel request cannot change quantity or price")
        reason = reason or ("simulated_broker_rejection" if response == "rejected" else None)
        # The request and its (modify-only) replacement share one node ordinal so
        # both read from the same placing node: request SIM-CHANGE-<node>, the
        # replacement order SIM-REPLACE-<node> (and "#2"... on a repeated node).
        ordinal = self._next_ordinal(node_id, self.node_operation_counts)
        request_id = self._scoped_id("SIM-CHANGE-", node_id, ordinal)
        operation = {"request_id":request_id, "action":action, "original_order_id":order_id,
            "symbol_key":order["symbol_key"], "status":"rejected" if reason else ("unknown" if response == "timeout" else "accepted"),
            "reason":reason or ("order_outcome_unknown" if response == "timeout" else None),
            "replacement":deepcopy(replacement), "payload":payload,
            "replacement_reserve":float(replacement_reserve), "filled_quantity":order["filled_quantity"],
            "replacement_order_id":(self._scoped_id("SIM-REPLACE-", node_id, ordinal) if action == "modify" else None)}
        self.operations[request_id] = operation
        self.operation_keys[key] = request_id
        if not reason:
            order["pending_operation"] = request_id
        self.transitions.append({"order_id":order_id, "request_id":request_id,
            "event":action+"_request", "status":operation["status"]})
        return deepcopy(operation)

    def confirm_change(self, request_id: str, *, event_id: str, applied: bool):
        """Apply explicit matching fixture evidence, including UNKNOWN recovery."""
        check_contract(applied, {"type":"boolean"}, "applied")
        payload = self._event_payload(["confirm_change", request_id, applied])
        if self._duplicate(event_id, payload):
            return deepcopy(self.operations[request_id])
        operation = self.operations.get(request_id)
        if operation is None or operation["status"] not in ("accepted", "unknown"):
            raise ContractViolation("request_id", "Confirmation needs an outstanding matching request")
        order = self.orders[operation["original_order_id"]]
        if order.get("pending_operation") != request_id:
            raise ContractViolation("request_id", "The original order has a different pending operation")
        if applied:
            if order["status"] not in ("accepted", "partial_fill"):
                raise ContractViolation("confirmation", "An already terminal order cannot be cancelled or replaced")
            if operation["action"] == "modify":
                if order["filled_quantity"]:
                    raise ContractViolation("confirmation", "A fill raced with replacement; quantity semantics need review", "REPLAY_CAPABILITY_BLOCKED")
                child = deepcopy(order)
                child.pop("pending_operation", None)
                child.update(order_id=operation["replacement_order_id"], status="accepted", reason=None)
                child["intent"].update(operation["replacement"])
                child["fill_price"] = operation["replacement"]["price"]
                if not child["futures"]:
                    child["unit_cost"] = operation["replacement"]["price"]
                self.orders[child["order_id"]] = child
                order["status"] = "replaced"
            else:
                order["status"] = "cancelled"
            operation["status"] = "confirmed"
        else:
            operation["status"] = "rejected"
            operation["reason"] = "simulated_completion_rejection"
        order.pop("pending_operation")
        self.events[event_id] = payload
        self.transitions.append({"order_id":order["order_id"], "request_id":request_id,
            "event":operation["action"]+"_confirmation", "status":operation["status"]})
        return deepcopy(operation)

    def fill(self, order_id: str, quantity: int, *, event_id: str):
        payload = self._event_payload(["fill", order_id, quantity])
        if self._duplicate(event_id, payload): return deepcopy(self.orders[order_id])
        order = self.orders[order_id]
        if order["status"] not in ("accepted", "partial_fill"):
            raise ContractViolation("order", "Reconcile unknown orders before applying fills")
        remaining = order["intent"]["quantity"] - order["filled_quantity"]
        check_contract(quantity, {"type": "integer", "minimum": 1, "maximum": remaining}, "fill.quantity")
        direction = 1 if order["intent"]["side"] == "buy" else -1
        symbol = order["symbol_key"]
        held = self.positions.get(symbol, 0)
        if order["futures"]:
            if order["closing"]:
                entry = number(self.entry_prices[symbol], "entry_price", positive=True)
                multiplier = number(self.instruments[symbol]["multiplier"], "multiplier", positive=True)
                profit = (Decimal(str(order["fill_price"])) - entry) * multiplier * (1 if held > 0 else -1)
                self.cash += (Decimal(str(order["unit_cost"])) + profit) * quantity
            else:
                self.cash -= Decimal(str(order["unit_cost"])) * quantity
                self.entry_prices[symbol] = order["fill_price"]
        else:
            self.cash -= direction * Decimal(str(order["unit_cost"])) * quantity
        self.positions[symbol] = held + direction * quantity
        order["filled_quantity"] += quantity
        order["status"] = "filled" if quantity == remaining else "partial_fill"
        self.events[event_id] = payload
        self.transitions.append({"order_id": order_id, "event": "fill", "quantity": quantity, "status": order["status"]})
        return deepcopy(order)

    def reconcile(self, order_id: str, *, accepted: bool, event_id: str):
        payload = self._event_payload(["reconcile", order_id, accepted])
        if self._duplicate(event_id, payload): return deepcopy(self.orders[order_id])
        order = self.orders[order_id]
        if order["status"] != "unknown" or type(accepted) is not bool:
            raise ContractViolation("reconcile", "Reconciliation requires an unknown order and explicit acceptance evidence")
        order["status"] = "accepted" if accepted else "rejected"
        self.events[event_id] = payload
        self.transitions.append({"order_id": order_id, "event": "reconcile", "status": order["status"]})
        return deepcopy(order)

    def cancel(self, order_id: str, *, event_id: str):
        payload = self._event_payload(["cancel", order_id])
        if self._duplicate(event_id, payload): return deepcopy(self.orders[order_id])
        order = self.orders[order_id]
        if order["status"] not in ("accepted", "partial_fill"):
            raise ContractViolation("cancel", "Only reconciled open orders can be cancelled")
        if order.get("pending_operation"):
            raise ContractViolation("cancel", "Use matching request confirmation for a pending operation")
        order["status"] = "cancelled"
        self.events[event_id] = payload
        self.transitions.append({"order_id": order_id, "event": "cancel", "status": "cancelled"})
        return deepcopy(order)

    @staticmethod
    def _scoped_id(prefix: str, node_id: str, ordinal: int) -> str:
        """Deterministic node-based simulated id; the 1st per node has no suffix."""
        return f"{prefix}{node_id}" + ("" if ordinal == 1 else f"#{ordinal}")

    def _next_ordinal(self, node_id: str, counts: dict[str, int]) -> int:
        """Nth distinct id this node has originated in this book (1-based)."""
        ordinal = counts.get(node_id, 0) + 1
        counts[node_id] = ordinal
        return ordinal

    @staticmethod
    def _event_payload(value):
        finite_json(value)
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

    def _duplicate(self, event_id, payload):
        if not isinstance(event_id, str) or not event_id:
            raise ContractViolation("event_id", "A stable event ID is required")
        if event_id not in self.events: return False
        if self.events[event_id] != payload:
            raise ContractViolation("event_id", "A duplicate event cannot carry a different transition")
        return True
