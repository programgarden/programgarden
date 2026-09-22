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

    def snapshot(self):
        return {"cash": float(self.cash), "currency": self.currency,
                "positions": deepcopy(self.positions), "entry_prices": deepcopy(self.entry_prices),
                "orders": deepcopy(self.orders),
                "transitions": deepcopy(self.transitions), "live_order_count": 0}

    def submit(self, intent: dict[str, Any], *, key: str, response: str = "accepted",
               filled_quantity: int = 0) -> dict[str, Any]:
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
        reason = None
        if instrument["currency"] != self.currency: reason = "currency_mismatch"
        elif not instrument["tradeable"]: reason = "instrument_not_tradeable"
        elif not instrument["session_open"]: reason = "market_closed"
        elif age < 0 or age > max_age: reason = "stale_market_data"
        elif price % tick: reason = "invalid_price_tick"
        elif active: reason = "pending_or_unknown_order"
        elif held and (not futures and intent["side"] == "buy" or futures and not closing): reason = "position_already_held"
        elif closing and intent["quantity"] > abs(held): reason = "position_reversal_not_supported"
        elif not closing and (futures or intent["side"] == "buy") and cost + self._exposure() > self.max_investment: reason = "max_investment_exceeded"
        elif not closing and (futures or intent["side"] == "buy") and cost > self.cash - self._reserved_cash(): reason = "insufficient_cash"
        elif not futures and intent["side"] == "sell" and intent["quantity"] > held: reason = "insufficient_position"
        elif response == "rejected": reason = "simulated_broker_rejection"
        order_id = f"SIM-{len(self.orders) + 1}"
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
        return sum((Decimal(str(o["unit_cost"])) * (o["intent"]["quantity"] - o["filled_quantity"])
                    for o in self.orders.values() if (o["intent"]["side"] == "buy" or o["futures"]) and not o["closing"]
                    and o["status"] in ("accepted", "partial_fill", "unknown")), Decimal(0))

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
        order["status"] = "cancelled"
        self.events[event_id] = payload
        self.transitions.append({"order_id": order_id, "event": "cancel", "status": "cancelled"})
        return deepcopy(order)

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
