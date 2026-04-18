"""
ProgramGarden Core - Stock Fundamental Node

해외주식 종목정보(펀더멘털) 조회:
- OverseasStockFundamentalNode: g3104 API 기반 종목정보 조회

Item-based execution:
- Input: 단일 symbol (SplitNode에서 분리된 아이템)
- Output: 단일 value (해당 종목의 펀더멘털 데이터)
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
    FUNDAMENTAL_DATA_FIELDS,
)


class OverseasStockFundamentalNode(BaseNode):
    """
    해외주식 종목정보(펀더멘털) 조회 노드 (단일 종목)

    PER, EPS, 시가총액, 발행주식수, 52주 고/저가, 업종 등
    종목의 기본적 분석 데이터를 조회합니다.
    거래소: NYSE, NASDAQ, AMEX

    Item-based execution:
    - Input: symbol (단일 종목 {exchange, symbol})
    - Output: value (해당 종목의 펀더멘털 데이터)
    """

    type: Literal["OverseasStockFundamentalNode"] = "OverseasStockFundamentalNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasStockFundamentalNode.description"
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
            "Retrieve fundamental valuation data (PER, EPS, PBR, market cap, 52w high/low, sector) for a US-listed stock",
            "Screen or rank stocks by fundamental criteria — pair with ConditionNode or FieldMappingNode for filtering",
            "Give an AI Agent context about a stock's valuation alongside price data for investment thesis generation",
        ],
        "when_not_to_use": [
            "For Korean domestic stock fundamentals — use KoreaStockFundamentalNode",
            "When you only need price/volume data — use OverseasStockMarketDataNode",
            "For real-time earnings or news events — fundamental data is updated daily, not tick-by-tick",
        ],
        "typical_scenarios": [
            "SplitNode.item → OverseasStockFundamentalNode → ConditionNode (filter by PER < 20)",
            "OverseasStockSymbolQueryNode → SplitNode → OverseasStockFundamentalNode → FieldMappingNode (build fundamental table)",
            "OverseasStockFundamentalNode → AIAgentNode (fundamental analysis tool for LLM)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns per, pbr, eps, market_cap, shares_outstanding, 52w_high, 52w_low, sector, industry fields",
        "Item-based execution: pair with SplitNode to fetch fundamentals for each symbol in a universe",
        "is_tool_enabled=True — AI Agent can call this node to analyze stock valuation autonomously",
        "Broker connection is auto-injected via DAG traversal from OverseasStockBrokerNode",
        "Data sourced from LS Securities g3104 API — updated daily, not real-time",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Treating PER/EPS fields as real-time — comparing against intraday price moves",
            "reason": "Fundamental data is updated daily. Using it for intraday decisions creates stale-data risk.",
            "alternative": "Combine OverseasStockMarketDataNode (current price) with OverseasStockFundamentalNode (daily fundamentals) for hybrid screening.",
        },
        {
            "pattern": "Passing a list of symbols directly to the symbol field",
            "reason": "The symbol field expects a single {exchange, symbol} dict. Lists cause a runtime type error.",
            "alternative": "Use SplitNode upstream so each item is passed one at a time.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Fetch fundamentals for a single stock",
            "description": "Query PER, EPS, market cap for AAPL and display the result.",
            "workflow_snippet": {
                "id": "overseas_stock_fundamental_basic",
                "name": "Stock Fundamentals",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
                    {"id": "fundamental", "type": "OverseasStockFundamentalNode", "symbol": "{{ nodes.split.item }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.fundamental.value }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "split"},
                    {"from": "split", "to": "fundamental"},
                    {"from": "broker", "to": "fundamental"},
                    {"from": "fundamental", "to": "display"},
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
            "expected_output": "value port: {symbol, exchange, per, pbr, eps, market_cap, shares_outstanding, 52w_high, 52w_low, sector, industry}.",
        },
        {
            "title": "Fundamental screening — filter low-PER stocks",
            "description": "Query fundamentals for a watchlist and filter to stocks with PER under 20 using ConditionNode.",
            "workflow_snippet": {
                "id": "overseas_stock_fundamental_screen",
                "name": "PER Screening",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}]},
                    {"id": "fundamental", "type": "OverseasStockFundamentalNode", "symbol": "{{ nodes.split.item }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.fundamental.value }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "split"},
                    {"from": "split", "to": "fundamental"},
                    {"from": "broker", "to": "fundamental"},
                    {"from": "fundamental", "to": "display"},
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
            "expected_output": "fundamental.value emitted per symbol; downstream ConditionNode can filter by per < 20.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `symbol` field takes a single {exchange, symbol} dict. Bind to `{{ nodes.split.item }}` when iterating. "
            "Supported exchanges: NYSE, NASDAQ, AMEX. Broker connection is auto-injected."
        ),
        "output_consumption": (
            "The `value` port emits: {symbol, exchange, per, pbr, eps, market_cap, shares_outstanding, 52w_high, 52w_low, sector, industry}. "
            "Access individual fields via `{{ nodes.fundamental.value.per }}`."
        ),
        "common_combinations": [
            "SplitNode.item → OverseasStockFundamentalNode → FieldMappingNode (reshape for display)",
            "OverseasStockFundamentalNode.value → AIAgentNode (fundamental analysis tool)",
            "OverseasStockFundamentalNode.value → TableDisplayNode (fundamental table display)",
        ],
        "pitfalls": [
            "Fundamental data is updated daily — do not use it as a real-time signal",
            "PER may be null for pre-earnings or non-profitable companies — add null-check in ConditionNode logic",
            "The symbol field expects a single dict; use SplitNode for multi-symbol fundamental queries",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(name="symbol", type="symbol", description="i18n:ports.symbol"),
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="fundamental_data", description="i18n:ports.fundamental_data_value", fields=FUNDAMENTAL_DATA_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.OverseasStockFundamentalNode.symbol",
                description="i18n:fields.OverseasStockFundamentalNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"exchange": "NASDAQ", "symbol": "AAPL"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{exchange: str, symbol: str}",
                help_text="i18n:fields.OverseasStockFundamentalNode.symbol.help_text",
                object_schema=[
                    {"name": "exchange", "type": "STRING", "label": "i18n:fields.OverseasStockFundamentalNode.symbol.exchange", "required": True},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasStockFundamentalNode.symbol.symbol", "required": True},
                ],
            ),
        }
