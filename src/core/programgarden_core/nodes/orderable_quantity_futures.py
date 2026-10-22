"""Read contract-specific futures order capacity without submitting an order."""
from typing import ClassVar, Dict, List, Literal, Optional

from pydantic import Field

from programgarden_core.nodes.base import BaseNode, BrokerProvider, InputPort, NodeCategory, OutputPort, ProductScope
from programgarden_core.models.field_binding import ExpressionMode, FieldCategory, FieldSchema, FieldType


class OverseasFuturesOrderableQuantityNode(BaseNode):
    type: Literal["OverseasFuturesOrderableQuantityNode"] = "OverseasFuturesOrderableQuantityNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasFuturesOrderableQuantityNode.description"
    _version: ClassVar[str] = "1.0.1"
    _updated_at: ClassVar[str] = "2026-09-20"
    _change_note: ClassVar[str] = "Complete AI metadata, field descriptions and executable read-only examples."
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    symbol: Optional[Dict[str, str]] = Field(default=None, description="One current contract with symbol and exchange.")
    side: Literal["buy", "sell"] = "buy"
    order_type: Literal["limit", "market"] = "limit"
    price: Optional[float] = Field(default=None, description="The intended limit order price; market queries use zero.")
    query_type: Literal["new", "close", "total"] = "new"

    _inputs: List[InputPort] = [InputPort(name="trigger", type="signal", required=False, description="Read capacity after the contract and current quote are available.")]
    _outputs: List[OutputPort] = [
        OutputPort(name="quantity", type="number", description="Observed orderable contracts; null if unavailable."),
        OutputPort(name="verified", type="boolean", description="True only for a complete matching broker response."),
        OutputPort(name="error", type="string", description="Reason the quantity is unavailable; null for a valid zero or positive result."),
    ]
    _usage: ClassVar[dict] = {
        "when_to_use": ["Check contract-specific capacity before a futures order; connect the current quote first."],
        "when_not_to_use": ["Stock affordability, account performance, or proof of an accepted/filled order."],
        "typical_scenarios": ["FuturesContractNode → market.values → matching quote → orderable quantity → entry guard → order."],
    }
    _features: ClassVar[list] = [
        "Queries CIDBQ01400 using the actual contract, side, order type and price.",
        "Uses the same broker account as the workflow; never submits an order.",
        "Zero capacity is a normal result. Missing, partial or mismatched responses remain unavailable.",
        "Deep validation uses an offline fixture and does not prove real account capacity.",
    ]
    _node_guide: ClassVar[dict] = {
        "input_handling": "Bind symbol as a full {symbol, exchange} object from the runtime contract and price from the matching current quote. Put an ordering edge from every producer. Use query_type=new only for new positions, close for liquidation, total only when explicitly intended.",
        "output_consumption": "Require verified=true and quantity >= the intended contract count. Also verify holdings, pending orders, price/tick validity and their identities. Never replace unknown capacity with zero or compare a quoted futures price to cash as a margin check.",
        "pitfalls": ["Capacity is a snapshot, not a reservation or an order guarantee. ACK and actual fills require separate evidence."],
        "common_combinations": ["FuturesContractNode, OverseasFuturesMarketDataNode, IfNode and a guarded order path."],
    }
    _anti_patterns: ClassVar[list] = [{
        "pattern": "Treat an unavailable or unverified quantity as permission to submit.",
        "reason": "Capacity depends on the exact contract, side, account and proposed price.",
        "alternative": "Require verified=true and sufficient quantity, then apply independent account/order/session guards.",
    }]
    _examples: ClassVar[list] = [
        {
            "title": "Read " + query_type + " capacity",
            "description": "Read-only paper-account component. The live contract and matching current quote supply the query; no order is submitted.",
            "expected_output": "verified=true with a zero or positive quantity, or verified=false and an error.",
            "workflow_snippet": {
                "id": "capacity_" + query_type, "name": "Read contract capacity",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": True},
                    {"id": "contract", "type": "FuturesContractNode", "base_products": ["HMH"], "contract_selection": "front"},
                    {"id": "market", "type": "OverseasFuturesMarketDataNode", "symbol": "{{ nodes.contract.symbols[0] }}"},
                    {"id": "capacity", "type": "OverseasFuturesOrderableQuantityNode", "symbol": "{{ nodes.contract.symbols[0] }}",
                     "side": side, "order_type": "limit", "price": "{{ nodes.market.values[0].price }}", "query_type": query_type},
                ],
                "edges": [{"from": a, "to": b} for a, b in [("start", "broker"), ("broker", "contract"), ("contract", "market"), ("market", "capacity")]],
                "credentials": [{"credential_id": "broker_cred", "type": "broker_ls_overseas_futures", "data": [{"key": "appkey", "value": ""}, {"key": "appsecret", "value": ""}]}],
            },
        }
        for query_type, side in [("new", "buy"), ("close", "sell")]
    ]

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    @classmethod
    def get_field_schema(cls) -> Dict[str, FieldSchema]:
        return {
            "symbol": FieldSchema(name="symbol", type=FieldType.OBJECT, description="Current contract identity.", category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH, required=True, object_schema=[{"name":"symbol","type":"STRING","required":True},{"name":"exchange","type":"STRING","required":True}]),
            "side": FieldSchema(name="side", type=FieldType.ENUM, description="Intended buy or sell direction.", enum_values=["buy","sell"], default="buy", category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH),
            "order_type": FieldSchema(name="order_type", type=FieldType.ENUM, description="Intended limit or market order type.", enum_values=["limit","market"], default="limit", category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH),
            "price": FieldSchema(name="price", type=FieldType.NUMBER, description="Proposed order price in the contract's quotation units.", category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH),
            "query_type": FieldSchema(name="query_type", type=FieldType.ENUM, description="Capacity for new positions, position closing, or total capacity.", enum_values=["new","close","total"], default="new", category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH),
        }
