"""
ProgramGarden Core - Stock Account Node

해외주식 계좌 조회:
- OverseasStockAccountNode: 해외주식 계좌 잔고, 보유종목 조회 (REST API 1회성)
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
    OVERSEAS_STOCK_BALANCE_FIELDS,
    POSITION_FIELDS,
    SYMBOL_LIST_FIELDS,
)


class OverseasStockAccountNode(BaseNode):
    """
    해외주식 REST API 1회성 계좌 조회 노드

    특정 시점의 해외주식 계좌 정보를 REST API로 조회합니다:
    - 보유종목 목록
    - 각 종목별 포지션 (수량, 평균단가, 평가금액, 손익률)
    - 예수금/총자산

    미체결 주문 조회는 OverseasStockOpenOrdersNode를 사용하세요.
    실시간 업데이트가 필요하면 OverseasStockRealAccountNode를 사용하세요.
    """

    type: Literal["OverseasStockAccountNode"] = "OverseasStockAccountNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasStockAccountNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Query the overseas stock account balance and held positions at a specific point in time (one-shot REST call)",
            "Feed held_symbols into downstream market-data or condition nodes for portfolio-level strategies",
            "Check orderable cash balance before placing new orders",
        ],
        "when_not_to_use": [
            "When you need live streaming updates — use OverseasStockRealAccountNode instead",
            "For open (unfilled) order lists — use OverseasStockOpenOrdersNode",
            "For overseas futures accounts — use OverseasFuturesAccountNode",
        ],
        "typical_scenarios": [
            "Start → OverseasStockBrokerNode → OverseasStockAccountNode → TableDisplayNode (balance dashboard)",
            "Start → OverseasStockBrokerNode → OverseasStockAccountNode → ConditionNode (check orderable cash > threshold)",
            "OverseasStockAccountNode.held_symbols → OverseasStockMarketDataNode (auto-iterate mark-to-market)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns three ports: held_symbols (symbol list), balance (cash/equity summary), positions (per-symbol P&L)",
        "is_tool_enabled=True — AI Agent can call this node as a tool to inspect portfolio state",
        "One-shot REST call: safe to use in scheduled or on-demand workflows without WebSocket overhead",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using OverseasStockAccountNode inside a realtime loop expecting tick-level freshness",
            "reason": "Each execution makes a fresh REST call; high-frequency calling will hit API rate limits and lag behind tick data.",
            "alternative": "Use OverseasStockRealAccountNode which maintains a WebSocket subscription and updates state incrementally.",
        },
        {
            "pattern": "Wiring OverseasStockAccountNode without an upstream OverseasStockBrokerNode",
            "reason": "The node requires an active LS-Sec session; without the broker in the DAG the executor cannot inject the connection and the call fails.",
            "alternative": "Always place OverseasStockBrokerNode upstream and connect it via a main edge before AccountNode.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Account balance dashboard",
            "description": "Read overseas stock account state and display positions and balance in a table.",
            "workflow_snippet": {
                "id": "overseas-stock-account-balance",
                "name": "Overseas Stock Account Balance",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "display", "type": "TableDisplayNode", "title": "Positions", "data": "{{ nodes.account.positions }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "display"},
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
            "expected_output": "positions port: list of {symbol, exchange, quantity, avg_price, pnl_rate}; balance port: {cash_krw, total_eval_krw, orderable_amount}; held_symbols: [{symbol, exchange}].",
        },
        {
            "title": "Portfolio mark-to-market via held_symbols auto-iterate",
            "description": "Fetch account positions then auto-iterate market data for every held symbol to compute live mark-to-market.",
            "workflow_snippet": {
                "id": "overseas-stock-account-mtm",
                "name": "Account + Mark-to-Market",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "{{ item }}"},
                    {"id": "display", "type": "TableDisplayNode", "title": "Live Prices", "data": "{{ nodes.market.data }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "market"},
                    {"from": "market", "to": "display"},
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
            "expected_output": "For each held symbol the MarketDataNode emits current price/volume; TableDisplayNode shows live mark-to-market data.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Accepts an optional trigger signal on the `trigger` input port. No explicit binding needed — the broker connection is auto-injected by the executor via DAG traversal.",
        "output_consumption": "Three ports: `held_symbols` (array of {symbol, exchange}) feeds symbol-iterating nodes; `positions` (array of position dicts) feeds condition/display nodes; `balance` (single object) feeds orderable-cash checks.",
        "common_combinations": [
            "OverseasStockAccountNode.held_symbols → OverseasStockMarketDataNode (mark-to-market)",
            "OverseasStockAccountNode.balance → IfNode (orderable cash threshold)",
            "OverseasStockAccountNode.positions → ConditionNode with PortfolioPlugin (drawdown check)",
            "OverseasStockAccountNode.positions → FieldMappingNode → TableDisplayNode",
        ],
        "pitfalls": [
            "Each call is a fresh REST round-trip; do not place inside a high-frequency realtime loop",
            "held_symbols and positions arrays auto-iterate downstream nodes — wrap in AggregateNode first if you need them as a single batch",
        ],
    }

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="held_symbols",
            type="symbol_list",
            description="i18n:ports.held_symbols",
            fields=SYMBOL_LIST_FIELDS,
            example=[
                {"exchange": "NASDAQ", "symbol": "AAPL"},
                {"exchange": "NASDAQ", "symbol": "TSLA"},
            ],
        ),
        OutputPort(
            name="balance",
            type="balance_data",
            description="i18n:ports.balance",
            fields=OVERSEAS_STOCK_BALANCE_FIELDS,
            example={
                "total_pnl_rate": 7.42,
                "cash_krw": 5_000_000,
                "stock_eval_krw": 12_500_000,
                "total_eval_krw": 17_500_000,
                "total_pnl_krw": 1_210_000,
                "orderable_amount": 3_500.50,
                "foreign_cash": 3_800.10,
                "exchange_rate": 1380.25,
            },
        ),
        OutputPort(
            name="positions",
            type="position_data",
            description="i18n:ports.positions",
            fields=POSITION_FIELDS,
            example=[
                {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 10, "avg_price": 175.20, "pnl_rate": 6.99},
                {"symbol": "TSLA", "exchange": "NASDAQ", "quantity": 5, "avg_price": 240.00, "pnl_rate": -2.50},
            ],
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        return {}
