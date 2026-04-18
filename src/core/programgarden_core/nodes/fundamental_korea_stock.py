"""
ProgramGarden Core - Korea Stock Fundamental Node

국내주식 종목정보(펀더멘털) 조회:
- KoreaStockFundamentalNode: t1102 API 기반 종목정보 조회

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
    KOREA_STOCK_FUNDAMENTAL_FIELDS,
)


class KoreaStockFundamentalNode(BaseNode):
    """
    국내주식 종목정보(펀더멘털) 조회 노드 (단일 종목)

    PER, EPS, PBR, 시가총액, 상장주식수, 52주 고/저가, 업종 등
    종목의 기본적 분석 데이터를 조회합니다.
    거래소: KRX (KOSPI, KOSDAQ)

    Item-based execution:
    - Input: symbol (단일 종목 {symbol})
    - Output: value (해당 종목의 펀더멘털 데이터)
    """

    type: Literal["KoreaStockFundamentalNode"] = "KoreaStockFundamentalNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.KoreaStockFundamentalNode.description"
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
            "Retrieve fundamental valuation data (PER, EPS, PBR, market cap, 52w high/low, sector) for a Korean domestic stock (KOSPI/KOSDAQ)",
            "Screen or rank domestic stocks by fundamental criteria — pair with ConditionNode or FieldMappingNode for filtering",
            "Provide an AI Agent with KRX stock fundamental context for investment thesis or sector analysis",
        ],
        "when_not_to_use": [
            "For overseas stock fundamentals (US, HK, JP) — use OverseasStockFundamentalNode",
            "When you only need real-time price/volume data — use KoreaStockMarketDataNode",
            "For earnings announcements or financial statements — fundamental data is updated daily, not event-driven",
        ],
        "typical_scenarios": [
            "KoreaStockSymbolQueryNode → SplitNode → KoreaStockFundamentalNode → FieldMappingNode (KRX fundamental table)",
            "SplitNode.item → KoreaStockFundamentalNode → ConditionNode (filter KOSPI stocks by PER < 10)",
            "KoreaStockFundamentalNode → AIAgentNode (domestic fundamental analysis tool for LLM)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns per, pbr, eps, market_cap, shares_outstanding, 52w_high, 52w_low, sector, industry, dividend_yield fields",
        "Symbol format: 6-digit KRX code (e.g., '005930') without exchange field — domestic market implied",
        "Item-based execution: pair with SplitNode to fetch fundamentals for each domestic stock",
        "is_tool_enabled=True — AI Agent can call this node for KRX fundamental analysis autonomously",
        "Data sourced from LS Securities t1102 API — updated daily, not real-time",
        "Real-trading only — KoreaStock product does not support paper trading",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using PER/EPS values for intraday trading decisions",
            "reason": "Fundamental data is updated once daily. Using it to trigger intraday trades creates stale-data risk.",
            "alternative": "Combine KoreaStockMarketDataNode (current price) with KoreaStockFundamentalNode (daily fundamentals) for hybrid screening workflows.",
        },
        {
            "pattern": "Including exchange field in symbol dict",
            "reason": "Korean domestic stocks do not require an exchange field — only the 6-digit symbol code is needed.",
            "alternative": "Use {\"symbol\": \"005930\"} without exchange key.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Fetch fundamental data for Samsung Electronics",
            "description": "Query PER, PBR, EPS, and market cap for 005930 and display the result.",
            "workflow_snippet": {
                "id": "korea_stock_fundamental_basic",
                "name": "KRX Fundamental Fetch",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "005930"}, {"symbol": "000660"}]},
                    {"id": "fundamental", "type": "KoreaStockFundamentalNode", "symbol": "{{ nodes.split.item }}"},
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
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "value port: {symbol, per, pbr, eps, market_cap, shares_outstanding, 52w_high, 52w_low, sector, dividend_yield}.",
        },
        {
            "title": "Domestic value screening — low PBR filter",
            "description": "Query fundamentals for a KOSPI universe and filter by PBR below 1.0 to find undervalued stocks.",
            "workflow_snippet": {
                "id": "korea_stock_fundamental_screen",
                "name": "KRX PBR Screening",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "005930"}, {"symbol": "005380"}, {"symbol": "051910"}]},
                    {"id": "fundamental", "type": "KoreaStockFundamentalNode", "symbol": "{{ nodes.split.item }}"},
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
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "fundamental.value emitted per symbol; downstream ConditionNode can filter by pbr < 1.0.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `symbol` field takes a single dict with only `symbol` key (6-digit KRX code, e.g., {\"symbol\": \"005930\"}). "
            "No exchange field needed — domestic market is implied. Broker connection is auto-injected from KoreaStockBrokerNode."
        ),
        "output_consumption": (
            "The `value` port emits: {symbol, per, pbr, eps, market_cap, shares_outstanding, 52w_high, 52w_low, sector, industry, dividend_yield}. "
            "Access via `{{ nodes.fundamental.value.per }}`."
        ),
        "common_combinations": [
            "SplitNode.item → KoreaStockFundamentalNode → FieldMappingNode (reshape for display)",
            "KoreaStockFundamentalNode.value → AIAgentNode (KRX fundamental analysis tool)",
            "KoreaStockFundamentalNode.value → TableDisplayNode (fundamental table)",
        ],
        "pitfalls": [
            "Fundamental data is daily — do not use for intraday signal generation",
            "PER may be null or negative for loss-making companies — add null-check in downstream ConditionNode",
            "KoreaStock does not support paper trading — always uses a live LS Securities session",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(name="symbol", type="symbol", description="i18n:ports.symbol"),
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="fundamental_data", description="i18n:ports.fundamental_data_value", fields=KOREA_STOCK_FUNDAMENTAL_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.KoreaStockFundamentalNode.symbol",
                description="i18n:fields.KoreaStockFundamentalNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"symbol": "005930"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{symbol: str}",
                help_text="i18n:fields.KoreaStockFundamentalNode.symbol.help_text",
                object_schema=[
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.KoreaStockFundamentalNode.symbol.symbol", "required": True},
                ],
            ),
        }
