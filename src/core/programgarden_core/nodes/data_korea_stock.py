"""
ProgramGarden Core - Korea Stock Market Data Node

국내주식 시세 조회:
- KoreaStockMarketDataNode: 국내주식 REST API 시세 조회 (KRX)

Item-based execution:
- Input: 단일 symbol (SplitNode에서 분리된 아이템)
- Output: 단일 value (해당 종목의 시세)
"""

from typing import Any, List, Literal, Dict, ClassVar, Optional, TYPE_CHECKING
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
    KOREA_STOCK_PRICE_DATA_FIELDS,
)


class KoreaStockMarketDataNode(BaseNode):
    """
    국내주식 REST API 시세 조회 노드 (단일 종목)

    SplitNode와 함께 사용하여 개별 종목의 시세를 조회합니다.
    거래소: KRX (KOSPI, KOSDAQ)

    Item-based execution:
    - Input: symbol (단일 종목 {symbol})
    - Output: value (해당 종목의 시세 데이터)
    """

    type: Literal["KoreaStockMarketDataNode"] = "KoreaStockMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.KoreaStockMarketDataNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    # 단일 종목 (Item-based execution) - 국내주식은 exchange 불필요
    symbol: Optional[Dict[str, str]] = Field(
        default=None,
        description="Single symbol entry with symbol code (6-digit)",
    )

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Fetch the latest quote (price, volume, change) for a single Korean domestic stock (KOSPI or KOSDAQ) via REST API",
            "Use after a SplitNode to query each symbol's current price in a per-item iteration loop",
            "Feed live KRX pricing into PositionSizingNode or ConditionNode for domestic stock signal evaluation",
        ],
        "when_not_to_use": [
            "For US or overseas stock price data — use OverseasStockMarketDataNode",
            "For overseas futures — use OverseasFuturesMarketDataNode",
            "When you need tick-level streaming data — use KoreaStockRealMarketDataNode (WebSocket) instead",
            "For historical OHLCV series — use KoreaStockHistoricalDataNode",
        ],
        "typical_scenarios": [
            "KoreaStockSymbolQueryNode → SplitNode → KoreaStockMarketDataNode → ConditionNode (domestic price filter)",
            "SplitNode.item → KoreaStockMarketDataNode → PositionSizingNode (domestic stock price for sizing)",
            "SplitNode.item → KoreaStockMarketDataNode → TableDisplayNode (KRX price monitor)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns a single domestic stock's snapshot: current_price, volume, change_percent, bid, ask, per, eps, 52w_high, 52w_low",
        "Symbol format is a 6-digit KRX code (e.g., '005930') — no exchange field required (domestic market only)",
        "Item-based execution: pair with SplitNode to query multiple domestic stocks in sequence",
        "is_tool_enabled=True — AI Agent can call this node to look up KRX stock prices autonomously",
        "Real-trading only — KoreaStock product does not support paper trading (paper_trading=False enforced)",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Including an exchange field in the symbol dict (e.g., {symbol: '005930', exchange: 'KRX'})",
            "reason": "Korean domestic stocks only require the 6-digit symbol code. The exchange field is ignored and may cause confusion.",
            "alternative": "Use {\"symbol\": \"005930\"} without an exchange field.",
        },
        {
            "pattern": "Passing a list of symbols directly to the symbol field",
            "reason": "The symbol field expects a single {symbol} dict. Passing a list causes a runtime type error.",
            "alternative": "Use SplitNode upstream to iterate over the symbol list one at a time.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Fetch current price for Samsung Electronics",
            "description": "Connect broker, then fetch the latest quote for 005930 (Samsung) via KoreaStockMarketDataNode.",
            "workflow_snippet": {
                "id": "korea_stock_market_data_basic",
                "name": "KRX Quote Fetch",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "005930"}, {"symbol": "000660"}]},
                    {"id": "market", "type": "KoreaStockMarketDataNode", "symbol": "{{ nodes.split.item }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.market.value }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "split"},
                    {"from": "split", "to": "market"},
                    {"from": "broker", "to": "market"},
                    {"from": "market", "to": "display"},
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
            "expected_output": "value port: {symbol, current_price, volume, change_percent, bid, ask, per, eps} per domestic stock.",
        },
        {
            "title": "Price lookup for domestic PositionSizingNode",
            "description": "Fetch current price of a KOSPI stock and feed it into PositionSizingNode for order sizing.",
            "workflow_snippet": {
                "id": "korea_stock_market_data_sizing",
                "name": "KRX Price to Sizing",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "account", "type": "KoreaStockAccountNode"},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "005930"}]},
                    {"id": "market", "type": "KoreaStockMarketDataNode", "symbol": "{{ nodes.split.item }}"},
                    {"id": "sizing", "type": "PositionSizingNode", "method": "fixed_percent", "max_percent": 5, "balance": "{{ nodes.account.balance }}", "price": "{{ nodes.market.value.current_price }}", "symbol": "{{ nodes.split.item }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "broker", "to": "split"},
                    {"from": "split", "to": "market"},
                    {"from": "broker", "to": "market"},
                    {"from": "market", "to": "sizing"},
                    {"from": "account", "to": "sizing"},
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
            "expected_output": "market.value.current_price is fed into PositionSizingNode to compute risk-adjusted domestic stock order quantity.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `symbol` field takes a single dict with only `symbol` key (6-digit KRX code, e.g., {\"symbol\": \"005930\"}). "
            "No exchange field is needed — Korean domestic market is implied. "
            "Broker connection is auto-injected from KoreaStockBrokerNode."
        ),
        "output_consumption": (
            "The `value` port emits: {symbol, current_price, volume, change_percent, bid, ask, per, eps, 52w_high, 52w_low}. "
            "Access via `{{ nodes.market.value.current_price }}`."
        ),
        "common_combinations": [
            "SplitNode.item → KoreaStockMarketDataNode → ConditionNode (domestic price-based signal)",
            "KoreaStockMarketDataNode.value.current_price → PositionSizingNode.price",
            "KoreaStockMarketDataNode.value → TableDisplayNode (KRX price monitor)",
        ],
        "pitfalls": [
            "KoreaStock does not support paper trading — KoreaStockBrokerNode always uses a live session",
            "Symbol must be a 6-digit KRX code without exchange field — do not include exchange key",
            "REST polling returns a snapshot; for tick-level streaming use KoreaStockRealMarketDataNode",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(name="symbol", type="symbol", description="i18n:ports.symbol"),
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="market_data", description="i18n:ports.market_data_value", fields=KOREA_STOCK_PRICE_DATA_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.KoreaStockMarketDataNode.symbol",
                description="i18n:fields.KoreaStockMarketDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"symbol": "005930"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{symbol: str}",
                help_text="i18n:fields.KoreaStockMarketDataNode.symbol.help_text",
                object_schema=[
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.KoreaStockMarketDataNode.symbol.symbol", "required": True},
                ],
            ),
        }
