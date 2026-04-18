"""
ProgramGarden Core - Korea Stock Account Node

국내주식 계좌 조회:
- KoreaStockAccountNode: 국내주식 계좌 잔고, 보유종목 조회 (REST API 1회성)
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
    KOREA_STOCK_BALANCE_FIELDS,
    POSITION_FIELDS,
    SYMBOL_LIST_FIELDS,
)


class KoreaStockAccountNode(BaseNode):
    """
    국내주식 REST API 1회성 계좌 조회 노드

    특정 시점의 국내주식 계좌 정보를 REST API로 조회합니다:
    - 보유종목 목록
    - 각 종목별 포지션 (수량, 평균단가, 평가금액, 손익률)
    - 예수금/총자산

    미체결 주문 조회는 KoreaStockOpenOrdersNode를 사용하세요.
    실시간 업데이트가 필요하면 KoreaStockRealAccountNode를 사용하세요.
    """

    type: Literal["KoreaStockAccountNode"] = "KoreaStockAccountNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.KoreaStockAccountNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Query Korea domestic stock account balance and held positions at a specific point in time (one-shot REST call)",
            "Check orderable cash before placing a new Korea stock order",
            "Feed held_symbols into downstream market-data or condition nodes for domestic portfolio strategies",
        ],
        "when_not_to_use": [
            "When you need live streaming updates — use KoreaStockRealAccountNode instead",
            "For open (unfilled) Korea stock orders — use KoreaStockOpenOrdersNode",
            "For overseas stock or futures accounts — use OverseasStockAccountNode or OverseasFuturesAccountNode",
        ],
        "typical_scenarios": [
            "Start → KoreaStockBrokerNode → KoreaStockAccountNode → TableDisplayNode (domestic account dashboard)",
            "Start → KoreaStockBrokerNode → KoreaStockAccountNode → IfNode (cash > threshold → order)",
            "KoreaStockAccountNode.held_symbols → KoreaStockMarketDataNode (mark-to-market on held positions)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns three ports: held_symbols (symbol list with KRX codes), balance (KRW cash/equity summary), positions (per-symbol P&L in KRW)",
        "is_tool_enabled=True — AI Agent can call this node as a tool to inspect Korea stock portfolio state",
        "Real trading only (KoreaStockBrokerNode does not support paper_trading mode); no mock data",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using KoreaStockAccountNode in a high-frequency realtime loop",
            "reason": "Each execution makes a REST call; at high frequency this hits LS API rate limits and returns stale data.",
            "alternative": "Use KoreaStockRealAccountNode for continuous streaming account state in realtime workflows.",
        },
        {
            "pattern": "Wiring KoreaStockAccountNode with an OverseasStockBrokerNode or OverseasFuturesBrokerNode upstream",
            "reason": "Product scope mismatch: domestic stock queries require the korea_stock credential type and session from KoreaStockBrokerNode.",
            "alternative": "Always pair KoreaStockAccountNode with KoreaStockBrokerNode.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Korea stock account balance dashboard",
            "description": "Query Korea domestic stock account and display positions in a table.",
            "workflow_snippet": {
                "id": "korea-stock-account-balance",
                "name": "Korea Stock Account Balance",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "account", "type": "KoreaStockAccountNode"},
                    {"id": "display", "type": "TableDisplayNode", "title": "KR Positions", "data": "{{ nodes.account.positions }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "display"},
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
            "expected_output": "positions port: list of {symbol, quantity, avg_price, pnl_rate} in KRW; balance port: {cash_krw, total_eval_krw, orderable_amount}; held_symbols: [{symbol}].",
        },
        {
            "title": "Cash check before Korea stock order",
            "description": "Read account balance and only place an order when orderable cash exceeds 1,000,000 KRW.",
            "workflow_snippet": {
                "id": "korea-stock-cash-check",
                "name": "Korea Stock Cash Check",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "account", "type": "KoreaStockAccountNode"},
                    {"id": "if_cash", "type": "IfNode", "left": "{{ nodes.account.balance.orderable_amount }}", "operator": ">=", "right": 1000000},
                    {"id": "order", "type": "KoreaStockNewOrderNode", "symbol": "005930", "side": "buy", "order_type": "limit", "quantity": 1, "price": 75000},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "if_cash"},
                    {"from": "if_cash", "to": "order", "from_port": "true"},
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
            "expected_output": "When orderable_amount >= 1,000,000 KRW: KoreaStockNewOrderNode places the buy order. Otherwise the order branch is skipped.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Accepts an optional trigger signal on the `trigger` port. Korea stock broker connection is auto-injected by the executor from the upstream KoreaStockBrokerNode.",
        "output_consumption": "Three ports: `held_symbols` (array, auto-iterates) feeds symbol-iterating nodes; `positions` (array, auto-iterates) feeds risk/display nodes; `balance` (object) feeds cash checks via IfNode.",
        "common_combinations": [
            "KoreaStockAccountNode.balance → IfNode (orderable cash guard before order)",
            "KoreaStockAccountNode.positions → PortfolioNode (KRW risk aggregation)",
            "KoreaStockAccountNode → TableDisplayNode (domestic account dashboard)",
        ],
        "pitfalls": [
            "KoreaStockBrokerNode does not support paper_trading mode — this node always queries the real account",
            "positions array auto-iterates downstream nodes; use AggregateNode if you need the full list as a single value",
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
        OutputPort(name="balance", type="balance_data", description="i18n:ports.balance", fields=KOREA_STOCK_BALANCE_FIELDS),
        OutputPort(name="positions", type="position_data", description="i18n:ports.positions", fields=POSITION_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        return {}
