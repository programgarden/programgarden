"""
ProgramGarden Core - Stock Open Orders Node

해외주식 미체결 주문 조회:
- OverseasStockOpenOrdersNode: 해외주식 미체결 주문 조회 (REST API 1회성)
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


class OverseasStockOpenOrdersNode(BaseNode):
    """
    해외주식 미체결 주문 조회 노드

    REST API로 현재 미체결 주문 목록을 조회합니다:
    - 주문번호, 종목코드, 매매구분
    - 주문수량, 체결수량, 미체결수량
    - 주문가격, 주문시각

    미체결 주문을 수정하거나 취소할 때 활용합니다.
    """

    type: Literal["OverseasStockOpenOrdersNode"] = "OverseasStockOpenOrdersNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasStockOpenOrdersNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Retrieve the current list of unfilled overseas stock orders before deciding to modify or cancel them",
            "Feed open order IDs into OverseasStockModifyOrderNode or OverseasStockCancelOrderNode",
            "Check open order count to avoid duplicate submissions in strategy logic",
        ],
        "when_not_to_use": [
            "For account balance or held positions — use OverseasStockAccountNode",
            "For real-time order event streaming — use OverseasStockRealOrderEventNode",
            "For overseas futures open orders — use OverseasFuturesOpenOrdersNode",
        ],
        "typical_scenarios": [
            "Start → OverseasStockBrokerNode → OverseasStockOpenOrdersNode → OverseasStockCancelOrderNode (cancel all open orders)",
            "Start → OverseasStockBrokerNode → OverseasStockOpenOrdersNode → IfNode (count > 0) → OverseasStockModifyOrderNode",
            "ScheduleNode → OverseasStockOpenOrdersNode → TableDisplayNode (daily open-order summary)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns `open_orders` (list of unfilled order dicts) and `count` (integer) ports",
        "is_tool_enabled=True — AI Agent can query pending orders as a tool call",
        "One-shot REST call: suitable for scheduled checks or pre-trade validation steps",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Querying open orders in a high-frequency loop without throttling",
            "reason": "Each execution makes a REST API call; hammering the endpoint leads to rate-limit errors and inaccurate data due to latency.",
            "alternative": "Use a ScheduleNode or ThrottleNode to limit query frequency; for live event-driven tracking use OverseasStockRealOrderEventNode.",
        },
        {
            "pattern": "Omitting the upstream OverseasStockBrokerNode",
            "reason": "Without the broker session the REST call has no authentication and will fail at runtime.",
            "alternative": "Always wire OverseasStockBrokerNode → OverseasStockOpenOrdersNode via a main edge.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Display all open stock orders",
            "description": "Query and display all outstanding overseas stock orders in a table.",
            "workflow_snippet": {
                "id": "stock-open-orders-display",
                "name": "Open Stock Orders Display",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "open_orders", "type": "OverseasStockOpenOrdersNode"},
                    {"id": "display", "type": "TableDisplayNode", "title": "Open Orders", "data": "{{ nodes.open_orders.open_orders }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "open_orders port: list of unfilled order dicts (order_id, symbol, side, quantity, price, remaining_quantity); count port: integer total.",
        },
        {
            "title": "Cancel all open orders when count > 0",
            "description": "Check for open orders and cancel each one if any exist.",
            "workflow_snippet": {
                "id": "stock-cancel-open-orders",
                "name": "Cancel All Open Stock Orders",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "open_orders", "type": "OverseasStockOpenOrdersNode"},
                    {"id": "if_has_orders", "type": "IfNode", "left": "{{ nodes.open_orders.count }}", "operator": ">", "right": 0},
                    {"id": "cancel", "type": "OverseasStockCancelOrderNode", "order_id": "{{ item.order_id }}", "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "if_has_orders"},
                    {"from": "if_has_orders", "to": "cancel", "from_port": "true"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "If count > 0: CancelOrderNode auto-iterates over open_orders list and cancels each. If count == 0: cancel branch is skipped.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Accepts an optional trigger signal. Broker connection is auto-injected by the executor — no explicit binding required.",
        "output_consumption": "`open_orders` (list of dicts) auto-iterates downstream order management nodes; `count` (integer) feeds IfNode comparisons.",
        "common_combinations": [
            "OverseasStockOpenOrdersNode.open_orders → OverseasStockCancelOrderNode (bulk cancel)",
            "OverseasStockOpenOrdersNode.count → IfNode (guard against duplicate orders)",
            "OverseasStockOpenOrdersNode → TableDisplayNode (open-order dashboard)",
        ],
        "pitfalls": [
            "open_orders list auto-iterates downstream nodes — use AggregateNode if you need the full list as a single value",
            "This is a snapshot query; for event-driven order tracking subscribe to OverseasStockRealOrderEventNode instead",
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
