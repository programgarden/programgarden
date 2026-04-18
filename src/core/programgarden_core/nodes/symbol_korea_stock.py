"""
ProgramGarden Core - Korea Stock Symbol Query Node

국내주식 전체종목조회:
- KoreaStockSymbolQueryNode: KOSPI/KOSDAQ 전체 거래 가능 종목 조회 (t9945 API)
"""

from typing import Any, Optional, List, Literal, Dict, ClassVar, TYPE_CHECKING
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
    SYMBOL_LIST_FIELDS,
)


class KoreaStockSymbolQueryNode(BaseNode):
    """
    국내주식 전체종목조회 노드

    KOSPI/KOSDAQ 전체 거래 가능 종목을 조회합니다.
    t9945 API (마스터상장종목조회) 사용.
    """

    type: Literal["KoreaStockSymbolQueryNode"] = "KoreaStockSymbolQueryNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.KoreaStockSymbolQueryNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    market: str = Field(
        default="all",
        description="Market type: all, KOSPI, KOSDAQ",
    )

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Retrieve the full list of tradeable domestic stocks from KOSPI, KOSDAQ, or both markets",
            "Bootstrap a domestic stock universe for a screener or fundamental ranking workflow",
            "Discover all listed symbols before applying ScreenerNode or SymbolFilterNode filters",
        ],
        "when_not_to_use": [
            "For overseas stock symbol lookup — use OverseasStockSymbolQueryNode",
            "For overseas futures symbol lookup — use OverseasFuturesSymbolQueryNode",
            "When you already have a fixed watchlist of domestic stocks — use WatchlistNode or SplitNode items directly",
        ],
        "typical_scenarios": [
            "KoreaStockSymbolQueryNode → SplitNode → KoreaStockFundamentalNode (full KOSPI fundamental scan)",
            "KoreaStockSymbolQueryNode → ScreenerNode (filter by volume, market cap, sector)",
            "KoreaStockSymbolQueryNode → SplitNode → KoreaStockMarketDataNode (KRX price snapshot)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Queries t9945 API (domestic stock master) — returns [{symbol, name, market, sector, currency}, ...] list",
        "Filter by market: 'all' (KOSPI + KOSDAQ), 'KOSPI', or 'KOSDAQ'",
        "Symbol format in output is 6-digit KRX code without exchange field — compatible with all KoreaStock nodes",
        "Outputs `symbols` (list) and `count` (int) ports — wire symbols to SplitNode for per-item processing",
        "Real-trading only — KoreaStock product does not support paper trading",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Connecting the symbols output directly to a KoreaStockNewOrderNode without any filter",
            "reason": "The full KRX master contains thousands of stocks including illiquid and ST-listed names — ordering all of them would be catastrophic.",
            "alternative": "Route symbols through ScreenerNode or SymbolFilterNode first to reduce to a quality working set.",
        },
        {
            "pattern": "Running this node on every execution cycle of a realtime strategy",
            "reason": "The exchange master rarely changes intraday — fetching it on every cycle wastes API quota unnecessarily.",
            "alternative": "Run once at strategy startup and cache the symbol list in SQLiteNode for reuse.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "List all KOSPI symbols",
            "description": "Fetch all KOSPI-listed stocks and display the count and symbol list.",
            "workflow_snippet": {
                "id": "korea_stock_symbol_query_kospi",
                "name": "KOSPI Symbol List",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "symbols", "type": "KoreaStockSymbolQueryNode", "market": "KOSPI"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.symbols.symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "symbols"},
                    {"from": "symbols", "to": "display"},
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
            "expected_output": "symbols port: [{symbol, name, market, sector, currency}, ...]. count port: integer total.",
        },
        {
            "title": "Symbol query feeding a domestic fundamental screener",
            "description": "Fetch KOSDAQ symbols and pipe them through SplitNode for per-symbol fundamental fetch.",
            "workflow_snippet": {
                "id": "korea_stock_symbol_query_fundamental",
                "name": "KOSDAQ Fundamental Scan",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "symbols", "type": "KoreaStockSymbolQueryNode", "market": "KOSDAQ"},
                    {"id": "split", "type": "SplitNode", "items": "{{ nodes.symbols.symbols }}"},
                    {"id": "fundamental", "type": "KoreaStockFundamentalNode", "symbol": "{{ nodes.split.item }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.fundamental.value }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "symbols"},
                    {"from": "symbols", "to": "split"},
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
            "expected_output": "Each KOSDAQ stock's fundamental data is fetched in turn; display shows per/pbr/market_cap per stock.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "No symbol input required — this node generates the domestic universe. "
            "Set `market` to 'KOSPI', 'KOSDAQ', or 'all' (default) to scope the results."
        ),
        "output_consumption": (
            "The `symbols` port emits list[dict] with fields: symbol (6-digit), name, market, sector, currency. "
            "Wire to SplitNode for per-symbol downstream processing. "
            "The `count` port emits the total number of listed stocks returned."
        ),
        "common_combinations": [
            "KoreaStockSymbolQueryNode.symbols → SplitNode → KoreaStockFundamentalNode (universe fundamental scan)",
            "KoreaStockSymbolQueryNode.symbols → ScreenerNode (market cap / volume filter)",
            "KoreaStockSymbolQueryNode.symbols → SymbolFilterNode (exclude regulated or illiquid stocks)",
        ],
        "pitfalls": [
            "The full KRX master has thousands of stocks — always filter before passing to order nodes",
            "market='all' returns both KOSPI and KOSDAQ combined — use 'KOSPI' or 'KOSDAQ' to narrow",
            "KoreaStock does not support paper trading — uses a live LS Securities session",
        ],
    }

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="Total symbol count"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "market": FieldSchema(
                name="market",
                type=FieldType.ENUM,
                description="i18n:fields.KoreaStockSymbolQueryNode.market",
                default="all",
                enum_values=["all", "KOSPI", "KOSDAQ"],
                enum_labels={
                    "all": "i18n:enums.kr_market.all",
                    "KOSPI": "i18n:enums.kr_market.KOSPI",
                    "KOSDAQ": "i18n:enums.kr_market.KOSDAQ",
                },
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="all",
                expected_type="str",
            ),
        }
