"""
ProgramGarden Core - Futures Market Data Node

해외선물 시세 조회:
- OverseasFuturesMarketDataNode: 해외선물 REST API 시세 조회 (CME, EUREX, SGX, HKEX)

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


class OverseasFuturesMarketDataNode(BaseNode):
    """
    해외선물 REST API 시세 조회 노드 (단일 종목)

    SplitNode와 함께 사용하여 개별 종목의 시세를 조회합니다.
    거래소: CME, EUREX, SGX, HKEX

    Item-based execution:
    - Input: symbol (단일 종목 {exchange, symbol})
    - Output: value (해당 종목의 시세 데이터)
    """

    type: Literal["OverseasFuturesMarketDataNode"] = "OverseasFuturesMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasFuturesMarketDataNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
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
            "Fetch the latest quote (price, volume, open interest) for a single overseas futures contract (CME, EUREX, SGX, HKEX)",
            "Use after a SplitNode to query each futures contract's current price in a per-item iteration loop",
            "Feed live futures pricing into PositionSizingNode or ConditionNode for signal evaluation",
        ],
        "when_not_to_use": [
            "For US stock price data — use OverseasStockMarketDataNode",
            "For Korean domestic stocks — use KoreaStockMarketDataNode",
            "When you need tick-level streaming — use OverseasFuturesRealMarketDataNode (WebSocket) instead",
            "When querying OHLCV history — use OverseasFuturesHistoricalDataNode",
        ],
        "typical_scenarios": [
            "OverseasFuturesSymbolQueryNode → SplitNode → OverseasFuturesMarketDataNode → ConditionNode (futures screening)",
            "SplitNode.item → OverseasFuturesMarketDataNode → PositionSizingNode (contract price for sizing)",
            "WatchlistNode → SplitNode → OverseasFuturesMarketDataNode → TableDisplayNode (futures monitor)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns a single futures contract's snapshot: current_price, volume, open_interest, change_percent, bid, ask",
        "Item-based execution: pair with SplitNode to query multiple contracts in sequence",
        "is_tool_enabled=True — AI Agent can call this node to look up live futures prices autonomously",
        "Supported exchanges: CME, EUREX, SGX, HKEX — symbol format includes contract month code (e.g., ESH26)",
        "Broker connection is auto-injected via DAG traversal from OverseasFuturesBrokerNode",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using {\"ESH26\": {...}} dict-keyed format for the symbol field",
            "reason": "ProgramGarden requires {symbol, exchange} format. Dict-keyed symbols fail validation.",
            "alternative": "Use {\"symbol\": \"ESH26\", \"exchange\": \"CME\"} format.",
        },
        {
            "pattern": "Passing a list of contracts directly to the symbol field",
            "reason": "The symbol field expects a single {exchange, symbol} dict. Lists cause a runtime type error.",
            "alternative": "Use SplitNode upstream to iterate over the contract list one at a time.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Fetch current price for E-mini S&P 500 futures",
            "description": "Broker connects, then OverseasFuturesMarketDataNode fetches the latest quote for the ESH26 contract.",
            "workflow_snippet": {
                "id": "overseas_futures_market_data_basic",
                "name": "Futures Quote Fetch",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "ESH26", "exchange": "CME"}]},
                    {"id": "market", "type": "OverseasFuturesMarketDataNode", "symbol": "{{ nodes.split.item }}"},
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
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "value port: {symbol, exchange, current_price, volume, open_interest, change_percent, bid, ask}.",
        },
        {
            "title": "Multi-contract scan — compare HKEX futures prices",
            "description": "Fetch prices for multiple HKEX mini-futures contracts and display them in a table.",
            "workflow_snippet": {
                "id": "overseas_futures_market_data_multi",
                "name": "HKEX Futures Scan",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "MHIH26", "exchange": "HKEX"}, {"symbol": "MHIK26", "exchange": "HKEX"}]},
                    {"id": "market", "type": "OverseasFuturesMarketDataNode", "symbol": "{{ nodes.split.item }}"},
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
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "market.value emitted once per contract with price/volume data for each HKEX mini-futures contract.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `symbol` field takes a single {exchange, symbol} dict. "
            "Exchange values: CME, EUREX, SGX, HKEX. Symbol includes contract month code (e.g., ESH26 for March 2026). "
            "Broker connection auto-injected from OverseasFuturesBrokerNode."
        ),
        "output_consumption": (
            "The `value` port emits: {symbol, exchange, current_price, volume, open_interest, change_percent, bid, ask}. "
            "Access individual fields via `{{ nodes.market.value.current_price }}`."
        ),
        "common_combinations": [
            "SplitNode.item → OverseasFuturesMarketDataNode → ConditionNode (per-contract signal)",
            "OverseasFuturesMarketDataNode.value.current_price → PositionSizingNode.price",
            "OverseasFuturesMarketDataNode.value → TableDisplayNode (futures monitor)",
        ],
        "pitfalls": [
            "Symbol must include contract month code (e.g., ESH26 not ES) — check OverseasFuturesSymbolQueryNode for valid codes",
            "Use OverseasFuturesBrokerNode (not OverseasStockBrokerNode) as the upstream broker",
            "REST polling returns a snapshot; for tick-level streaming use OverseasFuturesRealMarketDataNode",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(name="symbol", type="symbol", description="i18n:ports.symbol"),
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="market_data", description="i18n:ports.market_data_value", fields=PRICE_DATA_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.OverseasFuturesMarketDataNode.symbol",
                description="i18n:fields.OverseasFuturesMarketDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"exchange": "CME", "symbol": "ESH26"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{exchange: str, symbol: str}",
                help_text="i18n:fields.OverseasFuturesMarketDataNode.symbol.help_text",
                object_schema=[
                    {"name": "exchange", "type": "STRING", "label": "i18n:fields.OverseasFuturesMarketDataNode.symbol.exchange", "required": True},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasFuturesMarketDataNode.symbol.symbol", "required": True},
                ],
            ),
        }
