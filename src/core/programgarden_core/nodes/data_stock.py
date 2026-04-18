"""
ProgramGarden Core - Stock Market Data Node

해외주식 시세 조회:
- OverseasStockMarketDataNode: 해외주식 REST API 시세 조회 (NYSE, NASDAQ, AMEX)

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
    PRICE_DATA_FIELDS,
)


class OverseasStockMarketDataNode(BaseNode):
    """
    해외주식 REST API 시세 조회 노드 (단일 종목)

    SplitNode와 함께 사용하여 개별 종목의 시세를 조회합니다.
    거래소: NYSE, NASDAQ, AMEX

    Item-based execution:
    - Input: symbol (단일 종목 {exchange, symbol})
    - Output: value (해당 종목의 시세 데이터)
    """

    type: Literal["OverseasStockMarketDataNode"] = "OverseasStockMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasStockMarketDataNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    # 단일 종목 (Item-based execution)
    symbol: Optional[Dict[str, str]] = Field(
        default=None,
        description="Single symbol entry with exchange and symbol code",
    )

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Fetch the latest quote (price, volume, change) for a single US-listed stock (NYSE, NASDAQ, AMEX) via REST API",
            "Use after a SplitNode to query each symbol's current price in a per-item iteration loop",
            "Feed live pricing into PositionSizingNode or ConditionNode without needing a WebSocket connection",
        ],
        "when_not_to_use": [
            "For overseas futures price data — use OverseasFuturesMarketDataNode",
            "For Korean domestic stocks — use KoreaStockMarketDataNode",
            "When you need tick-level streaming data — use OverseasStockRealMarketDataNode (WebSocket) instead",
            "When querying historical OHLCV series — use OverseasStockHistoricalDataNode",
        ],
        "typical_scenarios": [
            "WatchlistNode → SplitNode → OverseasStockMarketDataNode → ConditionNode (price-based filter)",
            "OverseasStockSymbolQueryNode → SplitNode → OverseasStockMarketDataNode → FieldMappingNode",
            "SplitNode.item → OverseasStockMarketDataNode → PositionSizingNode (price input for sizing)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns a single symbol's snapshot: current_price, volume, change_percent, bid, ask, per, eps, 52w_high, 52w_low",
        "Item-based execution: receives one {exchange, symbol} dict per call and emits one value dict — pair with SplitNode for multi-symbol queries",
        "is_tool_enabled=True — AI Agent can call this node to look up live prices autonomously",
        "Broker connection is auto-injected via DAG traversal — no explicit binding needed",
        "REST-based polling; for continuous streaming use OverseasStockRealMarketDataNode",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Passing a list of symbols directly to the symbol field instead of using SplitNode",
            "reason": "The symbol field expects a single {exchange, symbol} dict. Passing a list will cause a runtime type error.",
            "alternative": "Place a SplitNode upstream to iterate over the list; each item is then passed one at a time to OverseasStockMarketDataNode.",
        },
        {
            "pattern": "Using {\"AAPL\": {...}} dict-keyed format for the symbol field",
            "reason": "ProgramGarden requires {symbol, exchange} format for all symbol inputs. Dict-keyed symbols will fail validation.",
            "alternative": "Use {\"symbol\": \"AAPL\", \"exchange\": \"NASDAQ\"} format.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Fetch current price for a single stock",
            "description": "Broker connects, then OverseasStockMarketDataNode fetches the latest quote for AAPL passed via SplitNode.",
            "workflow_snippet": {
                "id": "overseas_stock_market_data_basic",
                "name": "Stock Quote Fetch",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}]},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "{{ nodes.split.item }}"},
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
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "value port: {symbol, exchange, current_price, volume, change_percent, bid, ask, per, eps} for each symbol.",
        },
        {
            "title": "Price lookup feeding PositionSizingNode",
            "description": "Fetch current price for a watchlist symbol and pass it to PositionSizingNode for risk-adjusted order sizing.",
            "workflow_snippet": {
                "id": "overseas_stock_market_data_sizing",
                "name": "Price to Sizing",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "NVDA", "exchange": "NASDAQ"}]},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "{{ nodes.split.item }}"},
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
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "market.value.current_price fed into PositionSizingNode to compute risk-adjusted order quantity.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `symbol` field takes a single {exchange, symbol} dict — always bind it to `{{ nodes.split.item }}` "
            "when iterating over a list. Exchange codes: NASDAQ, NYSE, AMEX. "
            "The node auto-receives the broker connection via DAG traversal from OverseasStockBrokerNode."
        ),
        "output_consumption": (
            "The `value` port emits a flat dict with fields: symbol, exchange, current_price, volume, change_percent, "
            "bid, ask, per, eps, 52w_high, 52w_low. Access individual fields via `{{ nodes.market.value.current_price }}`."
        ),
        "common_combinations": [
            "SplitNode.item → OverseasStockMarketDataNode (per-symbol price fetch in iteration)",
            "OverseasStockMarketDataNode.value → ConditionNode (price-based signal trigger)",
            "OverseasStockMarketDataNode.value.current_price → PositionSizingNode.price",
            "OverseasStockMarketDataNode.value → TableDisplayNode (price monitoring display)",
        ],
        "pitfalls": [
            "The symbol field must be a single dict — not a list. Use SplitNode for multi-symbol scenarios",
            "REST polling returns a snapshot at call time; for tick-level streaming use OverseasStockRealMarketDataNode",
            "OverseasStockBrokerNode must be upstream via a main edge for connection auto-injection to work",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(name="symbol", type="symbol", description="i18n:ports.symbol"),
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="value",
            type="market_data",
            description="i18n:ports.market_data_value",
            fields=PRICE_DATA_FIELDS,
            example={
                "exchange": "NASDAQ",
                "symbol": "AAPL",
                "current_price": 187.45,
                "volume": 12_345_678,
                "change_percent": -1.23,
                "per": 28.5,
                "eps": 6.57,
            },
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.OverseasStockMarketDataNode.symbol",
                description="i18n:fields.OverseasStockMarketDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"exchange": "NASDAQ", "symbol": "AAPL"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{exchange: str, symbol: str}",
                help_text="i18n:fields.OverseasStockMarketDataNode.symbol.help_text",
                object_schema=[
                    {"name": "exchange", "type": "STRING", "label": "i18n:fields.OverseasStockMarketDataNode.symbol.exchange", "required": True},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasStockMarketDataNode.symbol.symbol", "required": True},
                ],
            ),
        }
