"""
ProgramGarden Core - Stock Symbol Query Node

해외주식 전체종목조회:
- OverseasStockSymbolQueryNode: 해외주식 전체 거래 가능 종목 조회 (g3190 API)
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


class OverseasStockSymbolQueryNode(BaseNode):
    """
    해외주식 전체종목조회 노드

    해외주식 전체 거래 가능 종목을 조회합니다.
    g3190 API (마스터상장종목조회) 사용.
    """

    type: Literal["OverseasStockSymbolQueryNode"] = "OverseasStockSymbolQueryNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasStockSymbolQueryNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    stock_exchange: Optional[str] = Field(
        default=None,
        description="Exchange for overseas_stock: NYSE(81), NASDAQ(82), AMEX(83), etc.",
    )
    country: str = Field(
        default="US",
        description="Country code for overseas_stock (US, HK, JP, CN, etc.)",
    )
    max_results: int = Field(
        default=500,
        description="Maximum number of symbols to retrieve per request",
    )

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Retrieve the full list of tradeable symbols on a US exchange (NYSE, NASDAQ, AMEX) or other LS-supported overseas market",
            "Bootstrap a universe for a screener or fundamental ranking workflow before splitting into per-symbol nodes",
            "Populate a WatchlistNode or ScreenerNode dynamically with current exchange master data",
        ],
        "when_not_to_use": [
            "For overseas futures symbol lookup — use OverseasFuturesSymbolQueryNode",
            "For Korean domestic stock symbols — use KoreaStockSymbolQueryNode",
            "When you already have a fixed watchlist — use WatchlistNode directly instead",
        ],
        "typical_scenarios": [
            "OverseasStockSymbolQueryNode → SplitNode → OverseasStockFundamentalNode (universe fundamental scan)",
            "OverseasStockSymbolQueryNode → ScreenerNode (filter by volume/price criteria)",
            "OverseasStockSymbolQueryNode → SplitNode → OverseasStockMarketDataNode (full exchange price snapshot)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Queries g3190 API (overseas stock master) — returns [{symbol, exchange, name, currency, ...}] list",
        "Filter by country (US, HK, JP, CN, VN, ID) and stock_exchange code (81=NYSE/AMEX, 82=NASDAQ, blank=all)",
        "max_results cap (100–10000) prevents runaway API calls on large exchanges; uses continuation-query under the hood",
        "Outputs `symbols` (list) and `count` (int) ports — wire symbols to SplitNode for per-item downstream processing",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Setting max_results=10000 for every workflow cycle in a scheduled strategy",
            "reason": "Fetching the entire exchange master on every cycle wastes API quota. The symbol list rarely changes.",
            "alternative": "Run OverseasStockSymbolQueryNode once in a setup workflow and cache results in SQLiteNode, or use WatchlistNode for a fixed universe.",
        },
        {
            "pattern": "Connecting the symbols output directly to an order node without filtering",
            "reason": "An unfiltered exchange universe can have thousands of symbols, each triggering an order — this will exhaust position limits and quota instantly.",
            "alternative": "Route symbols through ScreenerNode or SymbolFilterNode first to reduce the working set.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Query all NASDAQ symbols",
            "description": "Fetch all tradeable NASDAQ symbols and display the count.",
            "workflow_snippet": {
                "id": "overseas_stock_symbol_query_nasdaq",
                "name": "NASDAQ Symbol List",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "symbols", "type": "OverseasStockSymbolQueryNode", "country": "US", "stock_exchange": "82", "max_results": 500},
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
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "symbols port: [{symbol, exchange, name, currency, ...}, ...]. count port: integer total.",
        },
        {
            "title": "Symbol query feeding a fundamental screener",
            "description": "Fetch all US symbols and pipe them through SplitNode for per-symbol fundamental data fetch.",
            "workflow_snippet": {
                "id": "overseas_stock_symbol_query_screener",
                "name": "Symbol to Screener",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "symbols", "type": "OverseasStockSymbolQueryNode", "country": "US", "max_results": 100},
                    {"id": "split", "type": "SplitNode", "items": "{{ nodes.symbols.symbols }}"},
                    {"id": "fundamental", "type": "OverseasStockFundamentalNode", "symbol": "{{ nodes.split.item }}"},
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
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "Each symbol's fundamental data is fetched in turn; display shows a table of per/eps/market_cap per stock.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "No symbol input required — this node generates the universe. "
            "Set `country` (US/HK/JP/CN) and optionally `stock_exchange` (81=NYSE/AMEX, 82=NASDAQ) to narrow the scope. "
            "`max_results` caps the list size; default 500 is safe for most use cases."
        ),
        "output_consumption": (
            "The `symbols` port emits a list[dict] with fields: symbol, exchange, name, currency. "
            "Wire to SplitNode to iterate per-symbol. "
            "The `count` port emits the total number of symbols returned (int)."
        ),
        "common_combinations": [
            "OverseasStockSymbolQueryNode.symbols → SplitNode → OverseasStockFundamentalNode (universe scan)",
            "OverseasStockSymbolQueryNode.symbols → ScreenerNode (volume/price filter)",
            "OverseasStockSymbolQueryNode.symbols → SymbolFilterNode (exclude known symbols)",
        ],
        "pitfalls": [
            "The full exchange master can have thousands of symbols — always apply a screener or filter before passing to order nodes",
            "max_results is a hard cap, not a filter; the API may return fewer if the exchange has fewer listings",
            "country='US' with no stock_exchange set returns all US exchanges combined (NYSE + NASDAQ + AMEX)",
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
            "country": FieldSchema(
                name="country",
                type=FieldType.ENUM,
                description="국가 코드. US: 미국, HK: 홍콩, JP: 일본, CN: 중국",
                default="US",
                enum_values=["US", "HK", "JP", "CN", "VN", "ID"],
                enum_labels={
                    "US": "i18n:enums.country.US",
                    "HK": "i18n:enums.country.HK",
                    "JP": "i18n:enums.country.JP",
                    "CN": "i18n:enums.country.CN",
                    "VN": "i18n:enums.country.VN",
                    "ID": "i18n:enums.country.ID",
                },
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="US",
                expected_type="str",
            ),
            "stock_exchange": FieldSchema(
                name="stock_exchange",
                type=FieldType.ENUM,
                description="거래소 구분. NYSE/AMEX: 81, NASDAQ: 82, 전체: 빈값",
                enum_values=["", "81", "82"],
                enum_labels={
                    "": "i18n:enums.stock_exchange_code.all",
                    "81": "i18n:enums.stock_exchange_code.81",
                    "82": "i18n:enums.stock_exchange_code.82",
                },
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="82",
                expected_type="str",
            ),
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="최대 조회 건수. 연속 조회로 전체 데이터를 가져옵니다.",
                default=500,
                min_value=100,
                max_value=10000,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=500,
                expected_type="int",
            ),
        }
