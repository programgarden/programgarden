"""
ProgramGarden Core - Futures Account Node

해외선물 계좌 조회:
- OverseasFuturesAccountNode: 해외선물 계좌 잔고, 보유종목 조회 (REST API 1회성)
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
    OVERSEAS_FUTURES_BALANCE_FIELDS,
    POSITION_FIELDS,
    SYMBOL_LIST_FIELDS,
)


class OverseasFuturesAccountNode(BaseNode):
    """
    해외선물 REST API 1회성 계좌 조회 노드

    특정 시점의 해외선물 계좌 정보를 REST API로 조회합니다:
    - 보유종목 목록
    - 각 종목별 포지션 (수량, 평균단가, 평가금액, 손익률)
    - 예수금/총자산

    미체결 주문 조회는 OverseasFuturesOpenOrdersNode를 사용하세요.
    실시간 업데이트가 필요하면 OverseasFuturesRealAccountNode를 사용하세요.
    """

    type: Literal["OverseasFuturesAccountNode"] = "OverseasFuturesAccountNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasFuturesAccountNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Query overseas futures account balance and current positions at a specific point in time (one-shot REST call)",
            "Check available margin before placing a new futures order",
            "Feed held_symbols into market-data or condition nodes for futures portfolio strategies",
        ],
        "when_not_to_use": [
            "When you need live streaming updates — use OverseasFuturesRealAccountNode instead",
            "For open (unfilled) futures orders — use OverseasFuturesOpenOrdersNode",
            "For overseas stock accounts — use OverseasStockAccountNode",
        ],
        "typical_scenarios": [
            "Start → OverseasFuturesBrokerNode → OverseasFuturesAccountNode → TableDisplayNode (margin dashboard)",
            "Start → OverseasFuturesBrokerNode → OverseasFuturesAccountNode → IfNode (margin > threshold → order)",
            "OverseasFuturesAccountNode.positions → ConditionNode with PortfolioPlugin (risk check)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns three ports: held_symbols (symbol list), balance (margin/equity summary), positions (per-contract P&L)",
        "is_tool_enabled=True — AI Agent can call this node as a tool to inspect futures portfolio state",
        "One-shot REST call; supports paper_trading mode via OverseasFuturesBrokerNode",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using OverseasFuturesAccountNode in a high-frequency realtime loop",
            "reason": "Each execution makes a REST call; at tick frequency this will hit rate limits and the data will be stale relative to WebSocket updates.",
            "alternative": "Use OverseasFuturesRealAccountNode for live streaming account state in realtime workflows.",
        },
        {
            "pattern": "Wiring OverseasFuturesAccountNode with an OverseasStockBrokerNode upstream",
            "reason": "Product scope mismatch: the stock broker connection cannot serve futures account queries and the executor will fail to inject the correct session.",
            "alternative": "Always pair OverseasFuturesAccountNode with OverseasFuturesBrokerNode.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Futures account balance dashboard",
            "description": "Query overseas futures account state and display positions and margin in a table.",
            "workflow_snippet": {
                "id": "futures-account-balance",
                "name": "Overseas Futures Account Balance",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": True},
                    {"id": "account", "type": "OverseasFuturesAccountNode"},
                    {"id": "display", "type": "TableDisplayNode", "title": "Futures Positions", "data": "{{ nodes.account.positions }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "display"},
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
            "expected_output": "positions port: list of {symbol, exchange, quantity, avg_price, pnl_rate}; balance port: {margin_balance, total_eval, orderable_margin}.",
        },
        {
            "title": "Margin check before futures order",
            "description": "Read account margin and place a new order only when available margin exceeds the threshold.",
            "workflow_snippet": {
                "id": "futures-account-margin-check",
                "name": "Futures Margin Check",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": True},
                    {"id": "account", "type": "OverseasFuturesAccountNode"},
                    {"id": "if_margin", "type": "IfNode", "left": "{{ nodes.account.balance.orderable_margin }}", "operator": ">=", "right": 10000},
                    {"id": "order", "type": "OverseasFuturesNewOrderNode", "symbol": "ESH26", "exchange": "CME", "side": "buy", "order_type": "limit", "quantity": 1, "price": 5200.0},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "if_margin"},
                    {"from": "if_margin", "to": "order", "from_port": "true"},
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
            "expected_output": "When orderable_margin >= 10000: NewOrderNode places a buy limit order. Otherwise the order branch is skipped.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Accepts an optional trigger signal on the `trigger` port. The futures broker connection is auto-injected by the executor from the upstream OverseasFuturesBrokerNode.",
        "output_consumption": "Three ports: `held_symbols` (array, auto-iterates) feeds symbol-iterating market nodes; `positions` (array, auto-iterates) feeds risk/display nodes; `balance` (object) feeds margin checks via IfNode.",
        "common_combinations": [
            "OverseasFuturesAccountNode.balance → IfNode (margin guard before order)",
            "OverseasFuturesAccountNode.positions → PortfolioNode (risk aggregation)",
            "OverseasFuturesAccountNode → TableDisplayNode (account dashboard)",
        ],
        "pitfalls": [
            "Each execution is a fresh REST call — do not use in tight loops; prefer OverseasFuturesRealAccountNode for realtime use cases",
            "positions array auto-iterates downstream nodes; use AggregateNode if you need the full array as a single value",
        ],
    }

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="held_symbols", type="symbol_list", description="i18n:ports.held_symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="balance", type="balance_data", description="i18n:ports.balance", fields=OVERSEAS_FUTURES_BALANCE_FIELDS),
        OutputPort(name="positions", type="position_data", description="i18n:ports.positions", fields=POSITION_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        return {}
