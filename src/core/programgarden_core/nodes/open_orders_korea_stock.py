"""
ProgramGarden Core - Korea Stock Open Orders Node

국내주식 미체결 주문 조회:
- KoreaStockOpenOrdersNode: 국내주식 미체결 주문 조회 (REST API 1회성)
"""

from typing import Any, List, Literal, Dict, ClassVar, TYPE_CHECKING

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


class KoreaStockOpenOrdersNode(BaseNode):
    """
    국내주식 미체결 주문 조회 노드

    REST API로 현재 미체결 주문 목록을 조회합니다:
    - 주문번호, 종목코드, 매매구분
    - 주문수량, 체결수량, 미체결수량
    - 주문가격, 주문시각

    미체결 주문을 수정하거나 취소할 때 활용합니다.
    """

    type: Literal["KoreaStockOpenOrdersNode"] = "KoreaStockOpenOrdersNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.KoreaStockOpenOrdersNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Retrieve the current list of unfilled Korea domestic stock orders to modify or cancel them",
            "Check open order count to prevent duplicate submissions in domestic stock strategies",
            "Feed order IDs into KoreaStockModifyOrderNode or KoreaStockCancelOrderNode",
        ],
        "when_not_to_use": [
            "For account balance or held positions — use KoreaStockAccountNode",
            "For real-time order event streaming — use KoreaStockRealOrderEventNode",
            "For overseas stock open orders — use OverseasStockOpenOrdersNode",
        ],
        "typical_scenarios": [
            "Start → KoreaStockBrokerNode → KoreaStockOpenOrdersNode → KoreaStockCancelOrderNode (cancel all open orders)",
            "Start → KoreaStockBrokerNode → KoreaStockOpenOrdersNode → IfNode (count == 0 → place new order)",
            "ScheduleNode → KoreaStockOpenOrdersNode → TableDisplayNode (end-of-day open-order snapshot)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns `open_orders` (list of unfilled domestic order dicts) and `count` (integer) ports",
        "is_tool_enabled=True — AI Agent can query pending Korea stock orders as a tool call",
        "Real trading only — KoreaStockBrokerNode does not support paper_trading mode",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Calling KoreaStockOpenOrdersNode at high frequency without throttling",
            "reason": "Each execution makes a REST API call; frequent calls hit LS API rate limits and return stale data.",
            "alternative": "Limit frequency with a ScheduleNode or ThrottleNode; for live event-driven order tracking use KoreaStockRealOrderEventNode.",
        },
        {
            "pattern": "Using KoreaStockOpenOrdersNode with a non-Korea broker upstream",
            "reason": "Product scope mismatch: only KoreaStockBrokerNode provides the domestic stock session required for this query.",
            "alternative": "Always wire KoreaStockBrokerNode → KoreaStockOpenOrdersNode via a main edge.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Display all open Korea stock orders",
            "description": "Query and display all outstanding domestic stock orders in a table.",
            "workflow_snippet": {
                "id": "korea-stock-open-orders-display",
                "name": "Korea Stock Open Orders Display",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "open_orders", "type": "KoreaStockOpenOrdersNode"},
                    {"id": "display", "type": "TableDisplayNode", "title": "KR Open Orders", "data": "{{ nodes.open_orders.open_orders }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "open_orders port: list of unfilled domestic order dicts (order_id, symbol, side, quantity, price, remaining_quantity); count port: integer.",
        },
        {
            "title": "Order dedup guard for Korea stock",
            "description": "Only place a new domestic stock order when there are no existing open orders.",
            "workflow_snippet": {
                "id": "korea-stock-order-dedup",
                "name": "Korea Stock Order Dedup Guard",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "open_orders", "type": "KoreaStockOpenOrdersNode"},
                    {"id": "if_no_orders", "type": "IfNode", "left": "{{ nodes.open_orders.count }}", "operator": "==", "right": 0},
                    {"id": "order", "type": "KoreaStockNewOrderNode", "symbol": "005930", "side": "buy", "order_type": "limit", "quantity": 1, "price": 75000},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "if_no_orders"},
                    {"from": "if_no_orders", "to": "order", "from_port": "true"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "When count == 0: KoreaStockNewOrderNode places the buy order. When count > 0: order branch is skipped.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Accepts an optional trigger signal. Korea stock broker connection is auto-injected by the executor from the upstream KoreaStockBrokerNode.",
        "output_consumption": "`open_orders` (list of dicts) auto-iterates downstream order-management nodes; `count` (integer) feeds IfNode comparisons for guard logic.",
        "common_combinations": [
            "KoreaStockOpenOrdersNode.open_orders → KoreaStockCancelOrderNode (bulk cancel)",
            "KoreaStockOpenOrdersNode.count → IfNode (duplicate-order guard)",
            "KoreaStockOpenOrdersNode → TableDisplayNode (open-order snapshot)",
        ],
        "pitfalls": [
            "Real trading only — KoreaStockBrokerNode does not expose a paper_trading mode for domestic stocks",
            "open_orders auto-iterates downstream nodes; use AggregateNode if you need the full list as a single value",
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
