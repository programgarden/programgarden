"""Order intents from actual graph bindings, executed only by the fixture book.

The normalizer/result envelope are shared with the live executor. Broker login,
quote requests and request transports are unreachable from this adapter. Broker
acceptance/fill semantics are explicit scenario assumptions, never observations.
"""
from __future__ import annotations

from copy import deepcopy

from programgarden.executor import ModifyOrderNodeExecutor, NewOrderNodeExecutor, resolve_overseas_stock_order_market
from programgarden.replay_contracts import ContractViolation, check_contract
from programgarden.replay_orders import SimulationBook

ORDER_NODES = frozenset(f"{product}{action}OrderNode"
    for product in ("KoreaStock","OverseasStock","OverseasFutures")
    for action in ("New", "Modify", "Cancel"))


def _product(node_type):
    return ("korea_stock" if node_type.startswith("KoreaStock") else
            "overseas_futures" if node_type.startswith("OverseasFutures") else "overseas_stock")


def _same_exchange(product, left, right):
    if product == "overseas_stock":
        left_code, left_error = resolve_overseas_stock_order_market(left)
        right_code, right_error = resolve_overseas_stock_order_market(right)
        return left_error is None and right_error is None and left_code == right_code
    return left == right


class _FixtureLedger:
    """Only the two read methods used by the real modification normalizer."""
    def __init__(self, order):
        self.order = order

    def has_workflow_order_ledger(self):
        return True

    def find_workflow_order(self, order_id, order_date, *, symbol):
        if order_id == self.order["order_id"] and symbol == self.order["intent"]["symbol"]:
            return deepcopy(self.order["intent"])
        return None


class ReplayOrders:
    def __init__(self, fixture):
        broker = fixture.get("broker")
        if not isinstance(broker, dict) or not {"account","instruments","as_of"} <= broker.keys():
            raise ContractViolation("broker", "Explicit account, instrument and time fixtures are required", "REPLAY_FIXTURE_REQUIRED")
        self.book = SimulationBook(broker["account"],broker["instruments"],as_of=broker["as_of"])
        self.responses = fixture.get("orders",{})
        self.normalizer = NewOrderNodeExecutor()
        self.modify_normalizer = ModifyOrderNodeExecutor()
        self.last_observation = None
        self.operation_nodes = {}
        self.submissions = 0

    def execute(self, node_id, node_type, config, context, *, invocation_id="main", iteration_index=None):
        if not node_type.endswith("NewOrderNode"):
            return self._change(node_id, node_type, config)
        raw = config.get("order")
        required = ["symbol","quantity"] + ([] if node_type.startswith("KoreaStock") else ["exchange"])
        check_contract(raw,{"type":"object","required":required,"properties":{
            "symbol":{"type":"string","minLength":1},"exchange":{"type":"string","minLength":1},
            "quantity":{"type":"integer","minimum":1},"price":{"type":"number","minimum":0}}},f"{node_id}.order")
        raw = deepcopy(raw)
        if node_type.startswith("KoreaStock"):
            raw.setdefault("exchange","KRX")
        normalized = self.normalizer._normalize_order(raw,config,context,node_id)
        if normalized is None:
            raise ContractViolation(node_id,"Actual order normalizer rejected the payload")
        if node_type.startswith("OverseasStock"):
            _, error = resolve_overseas_stock_order_market(normalized["exchange"],normalized["symbol"])
            if error:
                raise ContractViolation(node_id,error)
        side = config.get("side","buy")
        order_type = config.get("price_type",config.get("order_type","limit"))
        check_contract(order_type,{"type":"string","enum":["limit","market"]},f"{node_id}.order_type")
        instrument_key = normalized["exchange"] + ":" + normalized["symbol"]
        instrument = self.book.instruments.get(instrument_key)
        if not isinstance(instrument,dict):
            raise ContractViolation(node_id,"Order instrument fixture is absent","REPLAY_FIXTURE_REQUIRED")
        expected_product = _product(node_type)
        if instrument.get("product") != expected_product:
            raise ContractViolation(node_id,"Order node and fixture product do not match")
        # Match the existing overseas-stock executor's market-buy conversion;
        # an unavailable quote blocks instead of pretending a broker fetched it.
        if expected_product == "overseas_stock" and side == "buy" and order_type == "market":
            order_type = "limit"
        if order_type == "limit" and normalized["price"] <= 0:
            normalized["price"] = instrument["price"]
        intent = {**normalized,"side":side,"order_type":order_type}
        record = self.responses.get(node_id)
        if not isinstance(record,dict) or "response" not in record:
            raise ContractViolation(node_id,"An explicit order-response scenario is required","REPLAY_FIXTURE_REQUIRED")
        # Do not grant stock workflows an idempotency guard they did not enable.
        # Live futures use invocation identity; stocks without the optional
        # durable registry submit again, which the scenario must detect.
        self.submissions += 1
        if expected_product == "overseas_futures":
            from programgarden.order_lifecycle import operation_key
            if iteration_index is None:
                iteration_index = context._iteration_index if context._iteration_item is not None else -1
            key = operation_key(context.job_id, node_id,
                getattr(context._workflow_job, "_order_cycle", 0), iteration_index, invocation_id)
        else:
            key = f"{node_id}:submission:{self.submissions}"
        order = self.book.submit(intent,key=key,response=record["response"],filled_quantity=record.get("filled_quantity",0))
        self.last_observation = deepcopy(order)
        known_accepted = order["status"] in ("accepted","partial_fill","filled")
        output = self.normalizer._order_result(known_accepted,intent["symbol"],intent["exchange"],side,
            intent["quantity"],intent["price"],order["reason"],order["order_id"])
        output["order_result"].update({"status":{"accepted":"submitted","partial_fill":"partially_filled",
            "rejected":"failed"}.get(order["status"],order["status"]),"filled_quantity":order["filled_quantity"],
            "simulation":True,"risk_decision":order["reason"] or "allowed",
            "duplicate":order.get("duplicate",False)})
        output["result"] = [{**deepcopy(output["order_result"]),"order_id":order["order_id"]}]
        return output

    def _change(self, node_id, node_type, config):
        check_contract(config, {"type":"object", "required":["original_order_id", "symbol"],
            "properties":{"original_order_id":{"type":"string", "minLength":1},
                          "symbol":{"type":"string", "minLength":1}}}, node_id)
        original_id = config["original_order_id"]
        original = self.book.orders.get(original_id)
        if original is None:
            raise ContractViolation(node_id, "The target order is not in this workflow's fixture book", "REPLAY_FIXTURE_REQUIRED")
        exchange = config.get("exchange") or ("KRX" if node_type.startswith("KoreaStock") else None)
        product = _product(node_type)
        if config["symbol"] != original["intent"]["symbol"] or not _same_exchange(product, exchange, original["intent"]["exchange"]):
            raise ContractViolation(node_id, "Order target symbol/exchange does not match the original order")
        if self.book.instruments[original["symbol_key"]].get("product") != product:
            raise ContractViolation(node_id, "Order target and node product do not match")
        action = "modify" if node_type.endswith("ModifyOrderNode") else "cancel"
        replacement = None
        if action == "modify":
            if config.get("price_type", "limit") != "limit":
                raise ContractViolation(node_id, "Only limit-to-limit modification has a replay contract", "REPLAY_CAPABILITY_BLOCKED")
            if config.get("new_quantity") is None and config.get("new_price") is None:
                raise ContractViolation(node_id, "A modification must change quantity or price")
            resolved, error = self.modify_normalizer._resolve_modify_target(
                _FixtureLedger(original), product_label=product, original_order_id=original_id,
                symbol=config["symbol"], exchange=exchange, new_quantity=config.get("new_quantity"),
                new_price=config.get("new_price"), requires_side=True)
            if error:
                raise ContractViolation(node_id, error)
            if resolved["side"] != original["intent"]["side"]:
                raise ContractViolation(node_id, "Modification changed the original direction")
            replacement = {"quantity":resolved["quantity"], "price":resolved["price"]}
        record = self.responses.get(node_id)
        if not isinstance(record, dict) or "response" not in record:
            raise ContractViolation(node_id, "An explicit change-response fixture is required", "REPLAY_FIXTURE_REQUIRED")
        self.submissions += 1
        key = f"{node_id}:change:{self.submissions}"
        operation = self.book.request_change(action, original_id, key=key,
            response=record["response"], replacement=replacement)
        self.operation_nodes[(node_id, original["symbol_key"])] = operation["request_id"]
        self.last_observation = {**deepcopy(operation), "order_id":operation["request_id"]}
        accepted = operation["status"] == "accepted"
        details = {"success":accepted, "status":operation["status"], "product":product,
            "simulation":True, "confirmation_pending":operation["status"] in ("accepted", "unknown")}
        if not accepted:
            details["error"] = operation["reason"] or "order_outcome_unknown"
        if action == "cancel":
            details.update(order_id=original_id, cancel_order_no=operation["request_id"] if accepted else "")
            return {"cancel_result":details, "cancelled_order_id":original_id if accepted else "",
                "cancelled_order":{"symbol":config["symbol"], "exchange":exchange,
                    "order_id":original_id, "status":"cancel_requested"} if accepted else None}
        replacement_id = operation["replacement_order_id"] if accepted else ""
        details.update(original_order_id=original_id, new_order_id=replacement_id)
        return {"modify_result":details, "modified_order_id":replacement_id,
            "modified_order":{"symbol":config["symbol"], "exchange":exchange,
                "original_order_id":original_id, "new_order_id":replacement_id,
                "new_quantity":config.get("new_quantity"), "new_price":config.get("new_price"),
                "status":"modified"} if accepted else None}

    def apply_events(self, events, node_type):
        """Trusted fixture evidence at a subsequent broker-observation boundary."""
        check_contract(events, {"type":"array", "items":{"type":"object",
            "required":["request_node", "symbol_key", "event_id", "applied"],
            "additionalProperties":False, "properties":{
                "request_node":{"type":"string", "minLength":1},
                "symbol_key":{"type":"string", "minLength":1},
                "event_id":{"type":"string", "minLength":1}, "applied":{"type":"boolean"}}}}, "order_events")
        for event in events:
            request = self.operation_nodes.get((event["request_node"], event["symbol_key"]))
            if request is None:
                raise ContractViolation("order_events", "No matching workflow request for completion evidence")
            if self.book.instruments[event["symbol_key"]].get("product") != _product(node_type):
                raise ContractViolation("order_events", "Completion evidence belongs to a different product")
            self.book.confirm_change(request, event_id=event["event_id"], applied=event["applied"])

    def check_open_orders(self, output, node_type):
        """A fixture cannot hide this workflow's still-open simulated orders."""
        check_contract(output, {"type":"object", "required":["open_orders", "count"],
            "properties":{"open_orders":{"type":"array", "items":{"type":"object",
                "required":["order_id"], "properties":{"order_id":{"type":"string", "minLength":1}}}},
                "count":{"type":"integer", "minimum":0}}}, "open_orders")
        rows = output["open_orders"]
        indexed = {row["order_id"]:row for row in rows}
        if len(indexed) != len(rows) or output["count"] != len(rows):
            raise ContractViolation("open_orders", "Order IDs/count do not describe a complete unique snapshot")
        for order_id, order in self.book.orders.items():
            product = self.book.instruments[order["symbol_key"]].get("product")
            if product != _product(node_type):
                if order_id in indexed:
                    raise ContractViolation("open_orders", "An order from a different product appears in this snapshot")
                continue
            active = order["status"] in ("accepted", "partial_fill", "unknown")
            row = indexed.get(order_id)
            if active != (row is not None):
                raise ContractViolation("open_orders", "Fixture contradicts the simulated order state")
            if row is None:
                continue
            intent = order["intent"]
            if not _same_exchange(product, row.get("exchange"), intent["exchange"]):
                raise ContractViolation("open_orders", "The observed order exchange does not match the original")
            expected = {"symbol":intent["symbol"], "side":intent["side"], "quantity":intent["quantity"],
                "filled_quantity":order["filled_quantity"],
                "remaining_quantity":intent["quantity"]-order["filled_quantity"], "price":intent["price"]}
            for field, value in expected.items():
                check_contract(row.get(field), {"type":"string" if isinstance(value,str) else "number", "const":value},
                               f"open_orders.{order_id}.{field}")
