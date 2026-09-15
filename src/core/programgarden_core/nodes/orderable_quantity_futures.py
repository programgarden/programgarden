"""Read contract-specific futures order capacity without submitting an order."""
from typing import ClassVar, Dict, List, Literal, Optional

from pydantic import Field

from programgarden_core.nodes.base import BaseNode, BrokerProvider, InputPort, NodeCategory, OutputPort, ProductScope
from programgarden_core.models.field_binding import ExpressionMode, FieldCategory, FieldSchema, FieldType


class OverseasFuturesOrderableQuantityNode(BaseNode):
    type: Literal["OverseasFuturesOrderableQuantityNode"] = "OverseasFuturesOrderableQuantityNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasFuturesOrderableQuantityNode.description"
    _version: ClassVar[str] = "1.0.0"
    _updated_at: ClassVar[str] = "2026-09-16"
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    symbol: Optional[Dict[str, str]] = Field(default=None, description="One current contract with symbol and exchange.")
    side: Literal["buy", "sell"] = "buy"
    order_type: Literal["limit", "market"] = "limit"
    price: Optional[float] = Field(default=None, description="The intended limit order price; market queries use zero.")
    query_type: Literal["new", "close", "total"] = "new"

    _inputs: List[InputPort] = [InputPort(name="trigger", type="signal", required=False)]
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
    }

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    @classmethod
    def get_field_schema(cls) -> Dict[str, FieldSchema]:
        return {
            "symbol": FieldSchema(name="symbol", type=FieldType.OBJECT, description="Current contract identity.", category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH, required=True, object_schema=[{"name":"symbol","type":"STRING","required":True},{"name":"exchange","type":"STRING","required":True}]),
            "side": FieldSchema(name="side", type=FieldType.ENUM, enum_values=["buy","sell"], default="buy", category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH),
            "order_type": FieldSchema(name="order_type", type=FieldType.ENUM, enum_values=["limit","market"], default="limit", category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH),
            "price": FieldSchema(name="price", type=FieldType.NUMBER, description="Proposed order price in the contract's quotation units.", category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH),
            "query_type": FieldSchema(name="query_type", type=FieldType.ENUM, enum_values=["new","close","total"], default="new", category=FieldCategory.PARAMETERS, expression_mode=ExpressionMode.BOTH),
        }
