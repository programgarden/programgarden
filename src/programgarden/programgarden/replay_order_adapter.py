"""Order intents from actual graph bindings, executed only by the fixture book.

The normalizer/result envelope are shared with the live executor. Broker login,
quote requests and request transports are unreachable from this adapter. Broker
acceptance/fill semantics are explicit scenario assumptions, never observations.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from programgarden.executor import NewOrderNodeExecutor, resolve_overseas_stock_order_market
from programgarden.replay_contracts import ContractViolation, check_contract
from programgarden.replay_orders import SimulationBook

ORDER_NODES = frozenset(f"{product}NewOrderNode" for product in ("KoreaStock","OverseasStock","OverseasFutures"))


class ReplayOrders:
    def __init__(self, fixture):
        broker = fixture.get("broker")
        if not isinstance(broker, dict) or not {"account","instruments","as_of"} <= broker.keys():
            raise ContractViolation("broker", "Explicit account, instrument and time fixtures are required", "REPLAY_FIXTURE_REQUIRED")
        self.book = SimulationBook(broker["account"],broker["instruments"],as_of=broker["as_of"])
        self.responses = fixture.get("orders",{})
        self.normalizer = NewOrderNodeExecutor()

    def execute(self, node_id, node_type, config, context):
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
        expected_product = ("korea_stock" if node_type.startswith("KoreaStock") else
                            "overseas_futures" if node_type.startswith("OverseasFutures") else "overseas_stock")
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
        key = node_id + ":" + hashlib.sha256(json.dumps(intent,sort_keys=True,allow_nan=False).encode()).hexdigest()
        order = self.book.submit(intent,key=key,response=record["response"],filled_quantity=record.get("filled_quantity",0))
        known_accepted = order["status"] in ("accepted","partial_fill","filled")
        output = self.normalizer._order_result(known_accepted,intent["symbol"],intent["exchange"],side,
            intent["quantity"],intent["price"],order["reason"],order["order_id"])
        output["order_result"].update({"status":{"accepted":"submitted","partial_fill":"partially_filled",
            "rejected":"failed"}.get(order["status"],order["status"]),"filled_quantity":order["filled_quantity"],
            "simulation":True,"risk_decision":order["reason"] or "allowed",
            "duplicate":order.get("duplicate",False)})
        output["result"] = [{**deepcopy(output["order_result"]),"order_id":order["order_id"]}]
        return output
