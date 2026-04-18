"""
ProgramGarden Core - Futures Open Orders Node

해외선물 미체결 주문 조회:
- OverseasFuturesOpenOrdersNode: 해외선물 미체결 주문 조회 (REST API 1회성)
"""

from typing import Any, List, Literal, Dict, ClassVar, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    ProductScope,
    BrokerProvider,
    OPEN_ORDER_FIELDS,
)


class OverseasFuturesOpenOrdersNode(BaseNode):
    """
    해외선물 미체결 주문 조회 노드

    REST API로 현재 미체결 주문 목록을 조회합니다:
    - 주문번호, 종목코드, 매매구분
    - 주문수량, 체결수량, 미체결수량
    - 주문가격, 주문시각

    미체결 주문을 수정하거나 취소할 때 활용합니다.
    """

    type: Literal["OverseasFuturesOpenOrdersNode"] = "OverseasFuturesOpenOrdersNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasFuturesOpenOrdersNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Retrieve the current list of unfilled overseas futures orders to manage or cancel them",
            "Feed open order IDs into OverseasFuturesModifyOrderNode or OverseasFuturesCancelOrderNode",
            "Check open order count to avoid exceeding position or order limits in futures strategies",
        ],
        "when_not_to_use": [
            "For account balance or held positions — use OverseasFuturesAccountNode",
            "For real-time order event streaming — use OverseasFuturesRealOrderEventNode",
            "For overseas stock open orders — use OverseasStockOpenOrdersNode",
        ],
        "typical_scenarios": [
            "Start → OverseasFuturesBrokerNode → OverseasFuturesOpenOrdersNode → OverseasFuturesCancelOrderNode (cancel stale orders)",
            "Start → OverseasFuturesBrokerNode → OverseasFuturesOpenOrdersNode → IfNode (count > 0) → skip new order",
            "ScheduleNode → OverseasFuturesOpenOrdersNode → TableDisplayNode (daily open-order snapshot)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns `open_orders` (list of unfilled futures order dicts) and `count` (integer) ports",
        "is_tool_enabled=True — AI Agent can query pending futures orders as a tool call",
        "Works in both paper_trading and real trading modes via the upstream OverseasFuturesBrokerNode",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Querying futures open orders at tick frequency without throttling",
            "reason": "Each execution makes a REST API call; high frequency will hit rate limits and results will lag behind actual order state.",
            "alternative": "Limit query frequency with a ScheduleNode or ThrottleNode; for event-driven tracking use OverseasFuturesRealOrderEventNode.",
        },
        {
            "pattern": "Pairing OverseasFuturesOpenOrdersNode with OverseasStockBrokerNode",
            "reason": "Product scope mismatch: the stock broker session cannot serve futures order queries.",
            "alternative": "Always use OverseasFuturesBrokerNode upstream of OverseasFuturesOpenOrdersNode.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Display all open futures orders",
            "description": "Query and display all outstanding overseas futures orders in a table.",
            "workflow_snippet": {
                "id": "futures-open-orders-display",
                "name": "Open Futures Orders Display",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": True},
                    {"id": "open_orders", "type": "OverseasFuturesOpenOrdersNode"},
                    {"id": "display", "type": "TableDisplayNode", "title": "Open Futures Orders", "data": "{{ nodes.open_orders.open_orders }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "open_orders port: list of unfilled futures order dicts (order_id, symbol, side, quantity, price, remaining_quantity); count port: integer.",
        },
        {
            "title": "Guard against duplicate futures orders",
            "description": "Only place a new futures order when there are no existing open orders for the target contract.",
            "workflow_snippet": {
                "id": "futures-order-dedup-guard",
                "name": "Futures Order Dedup Guard",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": True},
                    {"id": "open_orders", "type": "OverseasFuturesOpenOrdersNode"},
                    {"id": "if_no_orders", "type": "IfNode", "left": "{{ nodes.open_orders.count }}", "operator": "==", "right": 0},
                    {"id": "order", "type": "OverseasFuturesNewOrderNode", "symbol": "ESH26", "exchange": "CME", "side": "buy", "order_type": "limit", "quantity": 1, "price": 5200.0},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "if_no_orders"},
                    {"from": "if_no_orders", "to": "order", "from_port": "true"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "When count == 0: NewOrderNode places the order. When count > 0: order branch is skipped to prevent duplication.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Accepts an optional trigger signal. Futures broker connection is auto-injected by the executor from the upstream OverseasFuturesBrokerNode.",
        "output_consumption": "`open_orders` (list of dicts) auto-iterates downstream order-management nodes; `count` (integer) feeds IfNode comparisons for guard logic.",
        "common_combinations": [
            "OverseasFuturesOpenOrdersNode.open_orders → OverseasFuturesCancelOrderNode (bulk cancel)",
            "OverseasFuturesOpenOrdersNode.count → IfNode (duplicate-order guard)",
            "OverseasFuturesOpenOrdersNode → TableDisplayNode (open-order snapshot)",
        ],
        "pitfalls": [
            "open_orders auto-iterates downstream nodes — use AggregateNode if you need the full list as a single value for batch operations",
            "Snapshot data; order state can change between the query and the downstream action — build retry logic for time-sensitive operations",
        ],
    }

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="open_orders", type="order_list", description="i18n:ports.open_orders", fields=OPEN_ORDER_FIELDS),
        OutputPort(name="count", type="number", description="i18n:ports.count"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        return {}
