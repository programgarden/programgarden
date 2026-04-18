"""
ProgramGarden Core - Risk Nodes

Risk management nodes:
- PositionSizingNode: Position size calculation
"""

from typing import Optional, List, Literal, Dict, Any, TYPE_CHECKING, ClassVar
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    QUANTITY_FIELDS,
    SYMBOL_LIST_FIELDS,
)


class PositionSizingNode(BaseNode):
    """
    Position size calculation node (단일 종목)

    Item-based execution:
    - Input: symbol (단일 종목), balance, market_data (해당 종목 시세)
    - Output: order (해당 종목의 주문 정보 {symbol, exchange, quantity, price})

    Supports various position sizing methods: Kelly, fixed ratio, ATR-based
    """

    type: Literal["PositionSizingNode"] = "PositionSizingNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.PositionSizingNode.description"

    # === 바인딩 필드 (Item-based execution) ===
    symbol: Any = Field(
        default=None,
        description="단일 종목 {exchange, symbol} (SplitNode.item 또는 ConditionNode.result 바인딩)",
    )
    balance: Any = Field(
        default=None,
        description="예수금/매수가능금액 (AccountNode.balance 또는 RealAccountNode.balance 바인딩)",
    )
    market_data: Any = Field(
        default=None,
        description="해당 종목 시세 데이터 (MarketDataNode.value 바인딩)",
    )

    # PositionSizingNode specific config
    method: Literal["fixed_percent", "fixed_amount", "fixed_quantity", "kelly", "atr_based"] = Field(
        default="fixed_percent",
        description="Position sizing method",
    )
    max_percent: float = Field(
        default=10.0,
        description="Max position percentage of account (%)",
    )
    fixed_amount: Optional[float] = Field(
        default=None,
        description="Fixed amount (for fixed_amount method)",
    )
    fixed_quantity: Optional[int] = Field(
        default=1,
        description="Fixed quantity per symbol (for fixed_quantity method)",
    )
    kelly_fraction: float = Field(
        default=0.25,
        description="Kelly fraction adjustment (for kelly method, conservative 1/4)",
    )
    atr_risk_percent: float = Field(
        default=1.0,
        description="ATR-based risk percentage (for atr_based method)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="symbol",
            type="symbol",
            description="i18n:ports.symbol",
        ),
        InputPort(
            name="balance",
            type="balance_data",
            description="i18n:ports.balance",
        ),
        InputPort(
            name="market_data",
            type="market_data",
            description="i18n:ports.market_data",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="order",
            type="order",
            description="i18n:ports.order",
            fields=[
                {"name": "symbol", "type": "string", "description": "종목코드"},
                {"name": "exchange", "type": "string", "description": "거래소 코드"},
                {"name": "quantity", "type": "number", "description": "주문 수량"},
                {"name": "price", "type": "number", "description": "주문 가격"},
            ],
        ),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Compute per-symbol order size from balance + market data before handing off to NewOrderNode",
            "Switch sizing method (fixed percent / Kelly / ATR) without rewriting the pipeline",
            "Standardize risk exposure across different strategies (share the same PositionSizingNode config)",
        ],
        "when_not_to_use": [
            "Fixed-quantity simple tests — set `quantity` directly on NewOrderNode and skip sizing entirely",
            "Portfolio-level rebalancing — use PortfolioNode to compute allocations first, then size each leg",
            "Per-leg position-management signals (stop-loss / trailing) — that lives in ConditionNode with position-management plugins",
        ],
        "typical_scenarios": [
            "ConditionNode.result → SplitNode → PositionSizingNode(method='fixed_percent', max_percent=5) → NewOrderNode",
            "AccountNode.balance + MarketDataNode → PositionSizingNode(method='atr_based') → NewOrderNode",
            "ConditionNode + historical → PositionSizingNode(method='kelly', kelly_fraction=0.25) → order loop",
        ],
    }
    _features: ClassVar[List[str]] = [
        "5 sizing methods: fixed_percent / fixed_amount / fixed_quantity / kelly / atr_based",
        "Item-based execution — pair with SplitNode to size every candidate symbol independently",
        "`max_percent` caps the position regardless of method — defensive guardrail against outsized orders",
        "Outputs ready-to-consume order shape `{symbol, exchange, quantity, price}`",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "method='kelly' without a statistical edge estimate",
            "reason": "Kelly assumes you have a reliable win-rate / payout estimate; guessing leads to oversized bets.",
            "alternative": "Fall back to fixed_percent with a small max_percent (1–3 %) until you have historical edge data, then switch to Kelly with kelly_fraction=0.25 (quarter-Kelly) for safety.",
        },
        {
            "pattern": "Binding `symbol` as a raw string (e.g. 'AAPL')",
            "reason": "PositionSizingNode expects the symbol object `{exchange, symbol}` to determine the right broker and price lookups.",
            "alternative": "Bind `{{ nodes.split.item }}` or `{{ nodes.condition.passed_symbols[0] }}`, not the plain string.",
        },
        {
            "pattern": "Skipping `market_data` for ATR-based sizing",
            "reason": "ATR requires recent price history; without `market_data` the node falls back to a degenerate value.",
            "alternative": "Wire OverseasStockMarketDataNode.value into `market_data` before using method='atr_based'.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Fixed-percent sizing then place order",
            "description": "Condition finds oversold symbols; SplitNode per-symbol; PositionSizingNode caps each at 5% of balance; NewOrderNode places the trade.",
            "workflow_snippet": {
                "id": "sizing-fixed-percent",
                "name": "Fixed percent sizing",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
                    {
                        "id": "historical",
                        "type": "OverseasStockHistoricalDataNode",
                        "symbol": "{{ item }}",
                        "period": "1d",
                        "start_date": "20260301",
                        "end_date": "20260401",
                    },
                    {
                        "id": "rsi",
                        "type": "ConditionNode",
                        "plugin": "RSI",
                        "items": {
                            "from": "{{ item.time_series }}",
                            "extract": {
                                "symbol": "{{ item.symbol }}",
                                "exchange": "{{ item.exchange }}",
                                "date": "{{ row.date }}",
                                "close": "{{ row.close }}",
                            },
                        },
                        "fields": {"period": 14, "threshold": 30, "direction": "below"},
                    },
                    {"id": "split", "type": "SplitNode"},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "{{ nodes.split.item }}"},
                    {
                        "id": "size",
                        "type": "PositionSizingNode",
                        "method": "fixed_percent",
                        "max_percent": 5.0,
                        "symbol": "{{ nodes.split.item }}",
                        "balance": "{{ nodes.account.balance }}",
                        "market_data": "{{ nodes.market.value }}",
                    },
                    {
                        "id": "order",
                        "type": "OverseasStockNewOrderNode",
                        "symbol": "{{ nodes.size.order.symbol }}",
                        "exchange": "{{ nodes.size.order.exchange }}",
                        "quantity": "{{ nodes.size.order.quantity }}",
                        "price": "{{ nodes.size.order.price }}",
                        "side": "buy",
                    },
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "historical"},
                    {"from": "historical", "to": "rsi"},
                    {"from": "rsi", "to": "split"},
                    {"from": "split", "to": "market"},
                    {"from": "market", "to": "size"},
                    {"from": "account", "to": "size"},
                    {"from": "size", "to": "order"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "PositionSizingNode produces an order dict with quantity capped at 5% of balance; OrderNode consumes it and fires the buy.",
        },
        {
            "title": "ATR-based risk sizing",
            "description": "Risk 1% of account per trade, sized against the symbol's 14-day ATR.",
            "workflow_snippet": {
                "id": "sizing-atr",
                "name": "ATR-based sizing",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": {"symbol": "AAPL", "exchange": "NASDAQ"}},
                    {
                        "id": "size",
                        "type": "PositionSizingNode",
                        "method": "atr_based",
                        "atr_risk_percent": 1.0,
                        "max_percent": 10.0,
                        "symbol": {"symbol": "AAPL", "exchange": "NASDAQ"},
                        "balance": "{{ nodes.account.balance }}",
                        "market_data": "{{ nodes.market.value }}",
                    },
                    {"id": "display", "type": "SummaryDisplayNode", "title": "Sized order", "data": {"order": "{{ nodes.size.order }}"}},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "broker", "to": "market"},
                    {"from": "market", "to": "size"},
                    {"from": "account", "to": "size"},
                    {"from": "size", "to": "display"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "SummaryDisplay renders the order dict with quantity derived from 1% risk divided by current ATR; max_percent still caps total exposure at 10%.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "`symbol` is the object `{symbol, exchange}`. `balance` is scalar (AccountNode.balance). `market_data` is MarketDataNode.value (required for ATR).",
        "output_consumption": "`order` output is `{symbol, exchange, quantity, price}`. Feed into NewOrderNode by binding each subfield.",
        "common_combinations": [
            "SplitNode → PositionSizingNode → NewOrderNode (per-symbol sizing loop)",
            "ConditionNode → PositionSizingNode(kelly) → NewOrderNode",
            "AccountNode + MarketDataNode → PositionSizingNode(atr_based) → NewOrderNode",
        ],
        "pitfalls": [
            "`symbol` must be the object form, not a plain string",
            "method='kelly' needs kelly_fraction <= 1.0 (quarter-Kelly = 0.25 is a sane default)",
            "method='atr_based' needs `market_data` bound — otherwise the fallback produces a zero / tiny quantity",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === INPUTS: Item-based 바인딩 ===
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                description="i18n:fields.PositionSizingNode.symbol",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"exchange": "NASDAQ", "symbol": "AAPL"},
                example_binding="{{ nodes.condition.result }}",
                bindable_sources=[
                    "ConditionNode.result",
                    "SplitNode.item",
                ],
                expected_type="{exchange: str, symbol: str}",
                object_schema=[
                    {"name": "exchange", "type": "STRING", "label": "i18n:fields.PositionSizingNode.symbol.exchange", "required": True},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.PositionSizingNode.symbol.symbol", "required": True},
                ],
                help_text="i18n:fields.PositionSizingNode.symbol.help_text",
            ),
            "balance": FieldSchema(
                name="balance",
                type=FieldType.NUMBER,
                description="i18n:fields.PositionSizingNode.balance",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="10000000",
                example_binding="{{ nodes.account.balance }}",
                bindable_sources=["AccountNode.balance", "RealAccountNode.balance"],
                expected_type="number",
            ),
            "market_data": FieldSchema(
                name="market_data",
                type=FieldType.OBJECT,
                description="i18n:fields.PositionSizingNode.market_data",
                required=False,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"symbol": "AAPL", "exchange": "NASDAQ", "price": 150.0},
                example_binding="{{ nodes.marketdata.value }}",
                bindable_sources=[
                    "OverseasStockMarketDataNode.value",
                    "OverseasFuturesMarketDataNode.value",
                ],
                expected_type="{symbol: str, exchange: str, price: float, ...}",
                help_text="i18n:fields.PositionSizingNode.market_data.help_text",
            ),
            # === PARAMETERS: 핵심 포지션 사이징 설정 ===
            "method": FieldSchema(
                name="method",
                type=FieldType.ENUM,
                description="i18n:fields.PositionSizingNode.method",
                default="fixed_percent",
                enum_values=["fixed_percent", "fixed_amount", "fixed_quantity", "kelly", "atr_based"],
                enum_labels={
                    "fixed_percent": "i18n:enum.PositionSizingNode.method.fixed_percent",
                    "fixed_amount": "i18n:enum.PositionSizingNode.method.fixed_amount",
                    "fixed_quantity": "i18n:enum.PositionSizingNode.method.fixed_quantity",
                    "kelly": "i18n:enum.PositionSizingNode.method.kelly",
                    "atr_based": "i18n:enum.PositionSizingNode.method.atr_based",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
            ),
            # fixed_percent에서는 투자 비율, kelly/atr_based에서는 상한선
            # fixed_amount에서는 불필요 (금액 고정이므로 비율 제한 없음)
            "max_percent": FieldSchema(
                name="max_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.PositionSizingNode.max_percent",
                default=10.0,
                min_value=0.1,
                max_value=100.0,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                visible_when={"method": ["fixed_percent", "kelly", "atr_based"]},
            ),
            # fixed_amount 방식에서만 사용
            "fixed_amount": FieldSchema(
                name="fixed_amount",
                type=FieldType.NUMBER,
                description="i18n:fields.PositionSizingNode.fixed_amount",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                visible_when={"method": "fixed_amount"},
            ),
            # fixed_quantity 방식에서만 사용
            "fixed_quantity": FieldSchema(
                name="fixed_quantity",
                type=FieldType.INTEGER,
                description="i18n:fields.PositionSizingNode.fixed_quantity",
                default=1,
                min_value=1,
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                visible_when={"method": "fixed_quantity"},
            ),
            # === SETTINGS: 부가 설정 ===
            # kelly 방식에서만 사용
            "kelly_fraction": FieldSchema(
                name="kelly_fraction",
                type=FieldType.NUMBER,
                description="i18n:fields.PositionSizingNode.kelly_fraction",
                default=0.25,
                min_value=0.01,
                max_value=1.0,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.SETTINGS,
                visible_when={"method": "kelly"},
            ),
            # atr_based 방식에서만 사용
            "atr_risk_percent": FieldSchema(
                name="atr_risk_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.PositionSizingNode.atr_risk_percent",
                default=1.0,
                min_value=0.1,
                max_value=10.0,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.SETTINGS,
                visible_when={"method": "atr_based"},
            ),
        }