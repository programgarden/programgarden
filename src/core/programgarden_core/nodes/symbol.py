"""
ProgramGarden Core - Symbol Nodes

Symbol source/filter nodes:
- WatchlistNode: User-defined watchlist
- MarketUniverseNode: Market universe (NASDAQ100, S&P500, etc.)
- ScreenerNode: Conditional symbol screening
- SymbolFilterNode: Symbol list filter/intersection/difference

SymbolQueryNode는 상품별 분리됨:
- symbol_stock.py → OverseasStockSymbolQueryNode
- symbol_futures.py → OverseasFuturesSymbolQueryNode
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar, Union, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    SYMBOL_LIST_FIELDS,
)
from programgarden_core.models.exchange import SymbolEntry, ProductType


class WatchlistNode(BaseNode):
    """
    User-defined watchlist node

    Outputs a list of symbols with exchange information.
    Each symbol entry contains exchange name (NYSE, NASDAQ, CME, etc.) and symbol code.
    
    Note: This node only defines symbols. 
    Broker connection and product type are handled by downstream nodes (RealMarketDataNode, etc.)
    """

    type: Literal["WatchlistNode"] = "WatchlistNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.WatchlistNode.description"

    # Symbol entries: [{exchange: "NASDAQ", symbol: "AAPL"}, ...]
    symbols: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of symbol entries with exchange and symbol code",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.symbols",
            fields=SYMBOL_LIST_FIELDS,
            example=[
                {"exchange": "NASDAQ", "symbol": "AAPL"},
                {"exchange": "NASDAQ", "symbol": "TSLA"},
                {"exchange": "NYSE", "symbol": "JPM"},
            ],
        ),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Define a static watchlist of symbols that seeds the rest of the workflow",
            "Provide a fixed set of symbols to iterate over with SplitNode for per-symbol processing",
            "Supply a curated set of equities or futures contracts to downstream market-data or order nodes",
        ],
        "when_not_to_use": [
            "When you need dynamic symbol discovery based on market conditions — use ScreenerNode or MarketUniverseNode instead",
            "When symbols change at runtime — bind a dynamic source instead of hardcoding in WatchlistNode",
        ],
        "typical_scenarios": [
            "WatchlistNode → SplitNode → OverseasStockMarketDataNode → ConditionNode (fetch quotes for each symbol)",
            "WatchlistNode → ExclusionListNode → SplitNode → OverseasStockNewOrderNode (filter then order)",
            "WatchlistNode → OverseasStockHistoricalDataNode (seed historical data pull for a fixed universe)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Stores a static list of {symbol, exchange} entries that can include any supported exchange (NASDAQ, NYSE, AMEX, CME, EUREX, SGX, HKEX)",
        "Outputs a symbol_list that is auto-iterated by downstream nodes when paired with SplitNode",
        "No broker connection required — runs as an independent data-source node",
        "Supports expression binding so the list can be populated from another node's symbols output at runtime",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using {'AAPL': {...}} dict-keyed format instead of [{symbol, exchange}] list",
            "reason": "ProgramGarden requires list[dict] with symbol and exchange keys. Dict-keyed symbols fail validation.",
            "alternative": "Use [{\"symbol\": \"AAPL\", \"exchange\": \"NASDAQ\"}] format.",
        },
        {
            "pattern": "Adding 200+ symbols directly to WatchlistNode without pagination or batching",
            "reason": "Large lists iterate one-by-one via SplitNode which may exceed rate limits on downstream API calls.",
            "alternative": "Add a ThrottleNode between SplitNode and market-data nodes to limit the request rate.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Fetch quotes for a fixed watchlist",
            "description": "WatchlistNode seeds three NASDAQ symbols; SplitNode iterates them; OverseasStockMarketDataNode fetches the current price for each.",
            "workflow_snippet": {
                "id": "watchlist_quotes",
                "name": "Watchlist Quote Fetch",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}, {"symbol": "NVDA", "exchange": "NASDAQ"}]},
                    {"id": "split", "type": "SplitNode", "items": "{{ nodes.watchlist.symbols }}"},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "{{ nodes.split.item }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.market.value }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "split"},
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
            "expected_output": "A table of current prices for AAPL, MSFT, and NVDA.",
        },
        {
            "title": "Watchlist with exclusion filter before ordering",
            "description": "WatchlistNode provides candidates; ExclusionListNode removes blacklisted symbols; remaining symbols go to an order node.",
            "workflow_snippet": {
                "id": "watchlist_exclusion_order",
                "name": "Watchlist Exclusion Order",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "TSLA", "exchange": "NASDAQ"}, {"symbol": "AMZN", "exchange": "NASDAQ"}]},
                    {"id": "exclusion", "type": "ExclusionListNode", "symbols": [{"symbol": "TSLA", "exchange": "NASDAQ", "reason": "high volatility"}], "input_symbols": "{{ nodes.watchlist.symbols }}"},
                    {"id": "split", "type": "SplitNode", "items": "{{ nodes.exclusion.filtered }}"},
                    {"id": "order", "type": "OverseasStockNewOrderNode", "symbol": "{{ nodes.split.item.symbol }}", "exchange": "{{ nodes.split.item.exchange }}", "order_type": "limit", "side": "buy", "quantity": 1, "price": 100.0},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "exclusion"},
                    {"from": "exclusion", "to": "split"},
                    {"from": "split", "to": "order"},
                    {"from": "broker", "to": "order"},
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
            "expected_output": "Limit buy orders placed for AAPL and AMZN; TSLA skipped by exclusion list.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "No runtime inputs required. The symbols field is configured statically in the node. Alternatively bind it to another node's symbols output via expression to make it dynamic.",
        "output_consumption": "Connect symbols to SplitNode.items for per-symbol iteration, or pass directly to ExclusionListNode.input_symbols, ScreenerNode.symbols, or SymbolFilterNode.input_a for list-level operations.",
        "common_combinations": [
            "WatchlistNode → SplitNode → OverseasStockMarketDataNode",
            "WatchlistNode → ExclusionListNode → SplitNode → NewOrderNode",
            "WatchlistNode → SymbolFilterNode (difference with account holdings) → SplitNode → NewOrderNode",
        ],
        "pitfalls": [
            "Do not use dict-keyed symbols. Always use list[dict] with symbol and exchange keys.",
            "WatchlistNode does not validate whether the exchange supports the given symbol — validation happens at execution time in the broker node.",
            "Mixing futures and equity symbols in one WatchlistNode is allowed but downstream nodes may only accept one product type.",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 핵심 설정 ===
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="관심종목 목록입니다. 각 항목에 거래소(exchange)와 종목코드(symbol)를 입력하세요.",
                required=True,
                array_item_type=FieldType.OBJECT,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
                ui_options={
                    "exchanges": [
                        {"value": "NASDAQ", "label": "NASDAQ"},
                        {"value": "NYSE", "label": "NYSE"},
                        {"value": "AMEX", "label": "AMEX"},
                        {"value": "CME", "label": "CME (시카고상업거래소)"},
                        {"value": "EUREX", "label": "EUREX (유럽선물거래소)"},
                        {"value": "SGX", "label": "SGX (싱가포르거래소)"},
                        {"value": "HKEX", "label": "HKEX (홍콩거래소)"},
                    ],
                },
                example=[{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NASDAQ", "symbol": "TSLA"}],
                example_binding="{{ nodes.universe.symbols }}",
                bindable_sources=["MarketUniverseNode.symbols", "ScreenerNode.symbols"],
                expected_type="list[dict]",
            ),
        }


class MarketUniverseNode(BaseNode):
    """
    대표지수 종목 노드 (Market Universe Node)
    
    ⚠️ 해외주식(overseas_stock) 전용 노드입니다. 해외선물은 지원하지 않습니다.
    
    S&P500, NASDAQ100 등 미국 대표 지수의 구성 종목을 자동으로 가져옵니다.
    pytickersymbols 라이브러리를 활용하여 최신 인덱스 구성종목을 조회합니다.
    Broker 연결 없이 독립적으로 실행됩니다.
    
    지원 인덱스 (LS증권 거래 가능):
    - NASDAQ100: 나스닥 100 (~101개)
    - SP500: S&P 500 (~503개)
    - SP100: S&P 100
    - DOW30: 다우존스 30
    """

    type: Literal["MarketUniverseNode"] = "MarketUniverseNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.MarketUniverseNode.description"

    # 인덱스 선택
    universe: str = Field(
        default="NASDAQ100",
        description="대표 지수 선택 (NASDAQ100, SP500, DOW30 등). 해외주식 전용.",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="종목 수"),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Automatically retrieve all constituents of a major US index (NASDAQ100, S&P500, S&P100, DOW30) as a trading universe",
            "Seed a screening or filtering pipeline with a broad index-membership list without manual symbol entry",
            "Run a systematic strategy over an entire index, then narrow down with ScreenerNode or SymbolFilterNode",
        ],
        "when_not_to_use": [
            "For overseas futures universes — this node covers US equities only",
            "When you need custom or non-index symbol lists — use WatchlistNode instead",
            "When the index needs real-time rebalancing — constituent data is sourced from pytickersymbols (snapshot, not live)",
        ],
        "typical_scenarios": [
            "MarketUniverseNode (NASDAQ100) → ScreenerNode (volume_min filter) → SplitNode → ConditionNode",
            "MarketUniverseNode (SP500) → SymbolFilterNode (difference with held symbols) → SplitNode → NewOrderNode",
            "MarketUniverseNode (DOW30) → SplitNode → OverseasStockHistoricalDataNode → ConditionNode (momentum)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns the complete constituent list for NASDAQ100, S&P500, S&P100, or DOW30 as a symbol_list with exchange metadata",
        "No broker connection required — uses pytickersymbols library, runs standalone",
        "Outputs count port alongside symbols so downstream aggregation can track universe size",
        "Supports all exchange types present in the chosen index (NASDAQ, NYSE) automatically",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using MarketUniverseNode for overseas futures (CME, HKEX) universes",
            "reason": "MarketUniverseNode only supports US equity indexes. Overseas futures have no constituent list.",
            "alternative": "Manually define futures symbols using WatchlistNode with the appropriate CME/HKEX exchange codes.",
        },
        {
            "pattern": "Passing the full SP500 (~503 symbols) directly to a market-data node without rate limiting",
            "reason": "503 sequential API calls will exceed broker rate limits and may result in errors.",
            "alternative": "Add a ThrottleNode after SplitNode to control request pacing.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Fetch NASDAQ100 universe and display count",
            "description": "MarketUniverseNode loads all NASDAQ100 constituents, TableDisplayNode shows the list and count.",
            "workflow_snippet": {
                "id": "nasdaq100_universe",
                "name": "NASDAQ100 Universe",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "universe", "type": "MarketUniverseNode", "universe": "NASDAQ100"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.universe.symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "universe"},
                    {"from": "universe", "to": "display"},
                ],
                "credentials": [],
            },
            "expected_output": "A table of ~101 NASDAQ100 constituent symbols with exchange metadata.",
        },
        {
            "title": "SP500 universe screened by minimum market cap",
            "description": "MarketUniverseNode fetches all S&P500 members; ScreenerNode keeps only those above $100B market cap.",
            "workflow_snippet": {
                "id": "sp500_screened",
                "name": "SP500 Large Cap Screen",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "universe", "type": "MarketUniverseNode", "universe": "SP500"},
                    {"id": "screener", "type": "ScreenerNode", "symbols": "{{ nodes.universe.symbols }}", "market_cap_min": 100000000000},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.screener.symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "universe"},
                    {"from": "universe", "to": "screener"},
                    {"from": "screener", "to": "display"},
                ],
                "credentials": [],
            },
            "expected_output": "A filtered list of S&P500 companies with market cap above $100B.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "No inputs required. Configure the universe field to one of NASDAQ100, SP500, SP100, or DOW30. The node fetches constituents at execution time from pytickersymbols.",
        "output_consumption": "Connect symbols to ScreenerNode.symbols for further filtering, or to SplitNode.items for per-symbol iteration. Use count for logging or conditional branching.",
        "common_combinations": [
            "MarketUniverseNode → ScreenerNode → SplitNode → OverseasStockMarketDataNode",
            "MarketUniverseNode → SymbolFilterNode (subtract held positions) → SplitNode → NewOrderNode",
            "MarketUniverseNode → ExclusionListNode → SplitNode → ConditionNode",
        ],
        "pitfalls": [
            "Constituent data comes from pytickersymbols which updates periodically — it may lag actual index changes by days.",
            "For large indexes (SP500), always add a ThrottleNode before downstream API calls.",
            "MarketUniverseNode does not support overseas futures — use WatchlistNode for CME/HKEX symbols.",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "universe": FieldSchema(
                name="universe",
                type=FieldType.ENUM,
                description="i18n:fields.MarketUniverseNode.universe",
                default="NASDAQ100",
                required=True,
                enum_values=["NASDAQ100", "SP500", "SP100", "DOW30"],
                enum_labels={
                    "NASDAQ100": "i18n:enums.universe.NASDAQ100",
                    "SP500": "i18n:enums.universe.SP500",
                    "SP100": "i18n:enums.universe.SP100",
                    "DOW30": "i18n:enums.universe.DOW30",
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="NASDAQ100",
                expected_type="str",
            ),
        }


class ScreenerNode(BaseNode):
    """
    조건으로 종목찾기 노드 (Screener Node)
    
    시가총액, 거래량, 섹터 등 조건을 설정하면
    해당 조건을 만족하는 종목만 골라냅니다.
    Yahoo Finance API를 활용합니다.
    """

    type: Literal["ScreenerNode"] = "ScreenerNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.ScreenerNode.description"

    # 입력 종목 리스트 (선택사항) - 바인딩 또는 직접 입력
    symbols: Optional[Union[List[Dict[str, str]], str]] = Field(
        default=None,
        description="필터링할 종목 리스트. 없으면 전체 시장에서 검색",
    )
    
    # 스크리닝 조건
    market_cap_min: Optional[float] = Field(
        default=None,
        description="최소 시가총액 (달러). 예: 10000000000 = 100억 달러",
    )
    market_cap_max: Optional[float] = Field(
        default=None,
        description="최대 시가총액 (달러)",
    )
    volume_min: Optional[int] = Field(
        default=None,
        description="최소 평균 거래량 (주). 예: 1000000 = 100만주",
    )
    sector: Optional[str] = Field(
        default=None,
        description="섹터 필터 (Technology, Healthcare, Finance 등)",
    )
    exchange: Optional[str] = Field(
        default=None,
        description="거래소 필터 (NASDAQ, NYSE, AMEX)",
    )
    max_results: int = Field(
        default=100, 
        description="최대 결과 수"
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="symbols",
            type="symbol_list",
            description="필터링할 종목 리스트 (선택사항). 없으면 전체 시장에서 검색",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="결과 종목 수"),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Filter a symbol universe by fundamental criteria such as market cap, average volume, or sector",
            "Narrow down a large index (e.g. SP500) to tradeable candidates before applying technical conditions",
            "Combine with MarketUniverseNode to build a quantitative screening pipeline sourced from Yahoo Finance",
        ],
        "when_not_to_use": [
            "For technical indicator-based filtering (RSI, MACD) — use ConditionNode with the appropriate plugin instead",
            "For set operations on existing symbol lists — use SymbolFilterNode (intersection/difference/union)",
            "When broker-specific fundamental data is preferred — ScreenerNode uses Yahoo Finance data which may differ",
        ],
        "typical_scenarios": [
            "MarketUniverseNode (NASDAQ100) → ScreenerNode (Technology sector, volume_min=1M) → SplitNode → OverseasStockMarketDataNode",
            "WatchlistNode → ScreenerNode (market_cap_min filter) → SymbolFilterNode → SplitNode → NewOrderNode",
            "ScreenerNode (standalone, no input) → SplitNode → OverseasStockHistoricalDataNode",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Filters symbols by market cap (min/max), minimum average volume, sector, and exchange; all filters are optional and combinable",
        "Can run without input symbols to screen the entire market, or accept a symbol_list input to narrow an existing universe",
        "Outputs a sorted (largest market cap first) symbol_list and a count port for downstream conditional logic",
        "Powered by Yahoo Finance API — no broker credential required",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using ScreenerNode alone for technical indicator criteria (RSI oversold, MACD crossover)",
            "reason": "ScreenerNode only supports fundamental/descriptive filters. Technical signals require historical price data and indicator computation.",
            "alternative": "Chain ScreenerNode (fundamental pre-filter) → SplitNode → OverseasStockHistoricalDataNode → ConditionNode (technical filter).",
        },
        {
            "pattern": "Setting max_results to 500 without downstream rate limiting",
            "reason": "500 symbols iterating through API calls will trigger rate limits.",
            "alternative": "Keep max_results to a manageable size (50–100) or add a ThrottleNode after SplitNode.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Screen NASDAQ100 for large-cap tech stocks",
            "description": "MarketUniverseNode loads NASDAQ100 constituents; ScreenerNode keeps only Technology sector symbols with market cap above $100B and volume above 1M.",
            "workflow_snippet": {
                "id": "screener_nasdaq_tech",
                "name": "NASDAQ100 Tech Screen",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "universe", "type": "MarketUniverseNode", "universe": "NASDAQ100"},
                    {"id": "screener", "type": "ScreenerNode", "symbols": "{{ nodes.universe.symbols }}", "sector": "Technology", "market_cap_min": 100000000000, "volume_min": 1000000, "max_results": 20},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.screener.symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "universe"},
                    {"from": "universe", "to": "screener"},
                    {"from": "screener", "to": "display"},
                ],
                "credentials": [],
            },
            "expected_output": "Up to 20 NASDAQ100 Technology stocks with market cap >$100B and average volume >1M shares.",
        },
        {
            "title": "Standalone screener without input universe",
            "description": "ScreenerNode runs without an upstream universe, screening the entire market for high-volume NASDAQ stocks.",
            "workflow_snippet": {
                "id": "screener_standalone",
                "name": "NASDAQ High Volume Screen",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "screener", "type": "ScreenerNode", "exchange": "NASDAQ", "volume_min": 5000000, "max_results": 50},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.screener.symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "screener"},
                    {"from": "screener", "to": "display"},
                ],
                "credentials": [],
            },
            "expected_output": "Up to 50 NASDAQ stocks with average daily volume above 5M shares.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "The symbols input is optional. When connected, ScreenerNode filters only those symbols. When empty, it screens the full market. All filter fields (market_cap_min, volume_min, sector, exchange) are independently optional.",
        "output_consumption": "Connect symbols to SplitNode.items for per-symbol iteration, or to SymbolFilterNode/ExclusionListNode for further set operations. Use count for logging or conditional branching with IfNode.",
        "common_combinations": [
            "MarketUniverseNode → ScreenerNode → SplitNode → OverseasStockMarketDataNode",
            "ScreenerNode → SymbolFilterNode (difference with held positions) → SplitNode → NewOrderNode",
            "ScreenerNode → SplitNode → OverseasStockHistoricalDataNode → ConditionNode (RSI/MACD)",
        ],
        "pitfalls": [
            "ScreenerNode relies on Yahoo Finance data which may have delays or inconsistencies with broker data.",
            "Setting no filters returns all symbols up to max_results — always set at least one filter for production strategies.",
            "The sector filter uses Yahoo Finance sector names; ensure exact match (e.g. 'Financial Services' not 'Finance').",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 입력 종목 리스트 (선택사항) ===
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="필터링할 종목 리스트입니다. 비워두면 전체 시장에서 검색합니다. 다른 노드의 symbols 출력을 연결하면 해당 종목들만 필터링합니다.",
                required=False,
                array_item_type=FieldType.OBJECT,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
                ui_options={
                    "exchanges": [
                        {"value": "NASDAQ", "label": "NASDAQ"},
                        {"value": "NYSE", "label": "NYSE"},
                        {"value": "AMEX", "label": "AMEX"},
                        {"value": "CME", "label": "CME (시카고상업거래소)"},
                        {"value": "EUREX", "label": "EUREX (유럽선물거래소)"},
                        {"value": "SGX", "label": "SGX (싱가포르거래소)"},
                        {"value": "HKEX", "label": "HKEX (홍콩거래소)"},
                    ],
                },
                example=[{"exchange": "NASDAQ", "symbol": "AAPL"}],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=["WatchlistNode.symbols", "MarketUniverseNode.symbols", "SymbolQueryNode.symbols"],
                expected_type="list[dict]",
            ),
            # === PARAMETERS: 시가총액 필터 ===
            "market_cap_min": FieldSchema(
                name="market_cap_min",
                type=FieldType.NUMBER,
                description="최소 시가총액을 입력하세요 (달러 단위). 예: 100억 달러 = 10000000000. 유동성 낮은 소형주를 제외하려면 설정하세요.",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=10000000000,
                placeholder="예: 10000000000 (100억 달러)",
                expected_type="float",
            ),
            "market_cap_max": FieldSchema(
                name="market_cap_max",
                type=FieldType.NUMBER,
                description="최대 시가총액을 입력하세요. 중소형주만 찾으려면 설정하세요.",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=50000000000,
                expected_type="float",
            ),
            # === PARAMETERS: 거래량 필터 ===
            "volume_min": FieldSchema(
                name="volume_min",
                type=FieldType.INTEGER,
                description="최소 평균 거래량 (주 단위). 예: 100만주 = 1000000. 거래량이 적은 종목은 주문 체결이 어려울 수 있습니다.",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=1000000,
                placeholder="예: 1000000 (100만주)",
                expected_type="int",
            ),
            # === PARAMETERS: 섹터/거래소 필터 ===
            "sector": FieldSchema(
                name="sector",
                type=FieldType.ENUM,
                description="특정 섹터만 찾으려면 선택하세요. 비워두면 전체 섹터.",
                required=False,
                enum_values=["", "Technology", "Healthcare", "Financial Services", "Consumer Cyclical", "Communication Services", "Industrials", "Consumer Defensive", "Energy", "Utilities", "Real Estate", "Basic Materials"],
                enum_labels={
                    "": "i18n:enums.sector.all",
                    "Technology": "i18n:enums.sector.Technology",
                    "Healthcare": "i18n:enums.sector.Healthcare",
                    "Financial Services": "i18n:enums.sector.Financial_Services",
                    "Consumer Cyclical": "i18n:enums.sector.Consumer_Cyclical",
                    "Communication Services": "i18n:enums.sector.Communication_Services",
                    "Industrials": "i18n:enums.sector.Industrials",
                    "Consumer Defensive": "i18n:enums.sector.Consumer_Defensive",
                    "Energy": "i18n:enums.sector.Energy",
                    "Utilities": "i18n:enums.sector.Utilities",
                    "Real Estate": "i18n:enums.sector.Real_Estate",
                    "Basic Materials": "i18n:enums.sector.Basic_Materials",
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="Technology",
                expected_type="str",
            ),
            "exchange": FieldSchema(
                name="exchange",
                type=FieldType.ENUM,
                description="특정 거래소 종목만 찾으려면 선택하세요. 비워두면 전체 거래소.",
                required=False,
                enum_values=["", "NASDAQ", "NYSE", "AMEX"],
                enum_labels={
                    "": "i18n:enums.stock_exchange.all",
                    "NASDAQ": "i18n:enums.stock_exchange.NASDAQ",
                    "NYSE": "i18n:enums.stock_exchange.NYSE",
                    "AMEX": "i18n:enums.stock_exchange.AMEX",
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="NASDAQ",
                expected_type="str",
            ),
            # === SETTINGS: 결과 제한 ===
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="최대 몇 개 종목을 가져올지 설정하세요. 시가총액 큰 순으로 정렬됩니다.",
                default=100,
                min_value=1,
                max_value=500,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=100,
                expected_type="int",
            ),
        }


class ExclusionListNode(BaseNode):
    """
    거래 제외 종목 노드 (Exclusion List Node)

    거래하지 않을 종목을 관리합니다.
    직접 입력하거나 다른 노드 출력을 연결하여 자동으로 제외할 수 있습니다.

    사용 예시:
    - 특정 종목을 수동으로 블랙리스트 지정
    - 보유 종목을 동적으로 연결하여 중복 매수 방지
    - input_symbols 연결 시 제외 적용된 결과를 직접 출력
    """

    type: Literal["ExclusionListNode"] = "ExclusionListNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.ExclusionListNode.description"

    # 1. 수동 입력: 사용자가 직접 종목을 지정
    symbols: List[Dict[str, str]] = Field(
        default_factory=list,
        description="제외할 종목 목록 [{exchange, symbol, reason?}, ...]",
    )

    # 2. 동적 입력: 다른 노드 출력을 바인딩하여 동적으로 제외 종목 추가
    dynamic_symbols: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="동적으로 추가할 제외 종목 (다른 노드 출력 바인딩)",
    )

    # 3. 필터 대상: 제외를 적용할 원본 종목 리스트 (선택)
    input_symbols: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="필터링할 원본 종목 리스트 (연결 시 제외 적용된 결과 출력)",
    )

    # 4. 기본 제외 사유 (수동 입력 종목에 개별 reason이 없을 때 사용)
    default_reason: str = Field(
        default="",
        description="기본 제외 사유 (개별 종목에 reason이 없을 때 적용)",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="excluded", type="symbol_list", description="i18n:outputs.ExclusionListNode.excluded", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="filtered", type="symbol_list", description="i18n:outputs.ExclusionListNode.filtered", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="i18n:outputs.ExclusionListNode.count"),
        OutputPort(name="reasons", type="object", description="i18n:outputs.ExclusionListNode.reasons"),
    ]

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Maintain a blacklist of symbols that must never be traded, and automatically block them in downstream order nodes",
            "Dynamically combine a static blacklist with runtime-derived symbols (e.g. currently held positions) to prevent duplicate buys",
            "Filter an incoming symbol universe to remove excluded symbols before passing to order logic",
        ],
        "when_not_to_use": [
            "For set intersection or union operations between two symbol lists — use SymbolFilterNode instead",
            "When you only need to subtract held positions without a persistent exclusion list — SymbolFilterNode with operation='difference' is simpler",
        ],
        "typical_scenarios": [
            "WatchlistNode → ExclusionListNode (static blacklist + dynamic held positions) → SplitNode → NewOrderNode",
            "MarketUniverseNode → ExclusionListNode → ScreenerNode → SplitNode → ConditionNode",
            "ExclusionListNode (standalone) exposed as AI Agent Tool for 'what symbols are excluded and why?' queries",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Merges static symbols (manual blacklist) with dynamic_symbols (runtime-bound) into a unified excluded list with per-symbol reason tracking",
        "When input_symbols is connected, outputs a filtered list (filtered port) with excluded symbols removed — ready for downstream order nodes",
        "Automatic order-block safety: downstream OverseasStockNewOrderNode and other order nodes check the exclusion list and abort if the target symbol is listed",
        "is_tool_enabled=True — AI Agent can query the exclusion list to explain which symbols are blocked and why",
        "Four output ports: excluded (full blacklist), filtered (input minus excluded), count (blacklist size), reasons (symbol→reason map)",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Bypassing ExclusionListNode and placing orders directly after WatchlistNode",
            "reason": "Without ExclusionListNode in the path, the automatic order-block safety does not activate and blacklisted symbols may be traded.",
            "alternative": "Always route the symbol list through ExclusionListNode before any order node when a blacklist is required.",
        },
        {
            "pattern": "Using ExclusionListNode for set intersection (keep symbols in both lists)",
            "reason": "ExclusionListNode only supports removal (difference), not intersection.",
            "alternative": "Use SymbolFilterNode with operation='intersection' for intersection logic.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Static blacklist blocks order placement",
            "description": "TSLA is statically blacklisted; ExclusionListNode filters it out from the watchlist; the remaining symbols proceed to the order node. TSLA order is automatically blocked.",
            "workflow_snippet": {
                "id": "exclusion_order_block",
                "name": "Exclusion List Order Block",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "TSLA", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}]},
                    {"id": "exclusion", "type": "ExclusionListNode", "symbols": [{"symbol": "TSLA", "exchange": "NASDAQ", "reason": "high volatility blacklist"}], "input_symbols": "{{ nodes.watchlist.symbols }}"},
                    {"id": "split", "type": "SplitNode", "items": "{{ nodes.exclusion.filtered }}"},
                    {"id": "order", "type": "OverseasStockNewOrderNode", "symbol": "{{ nodes.split.item.symbol }}", "exchange": "{{ nodes.split.item.exchange }}", "order_type": "limit", "side": "buy", "quantity": 1, "price": 150.0},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "exclusion"},
                    {"from": "exclusion", "to": "split"},
                    {"from": "split", "to": "order"},
                    {"from": "broker", "to": "order"},
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
            "expected_output": "Buy orders placed for AAPL and MSFT. TSLA order is blocked by the exclusion list.",
        },
        {
            "title": "Dynamic exclusion: skip already-held positions",
            "description": "Account node provides current holdings; ExclusionListNode merges them with a static blacklist to prevent duplicate purchases.",
            "workflow_snippet": {
                "id": "exclusion_dynamic_held",
                "name": "Exclusion Dynamic Held Positions",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "universe", "type": "MarketUniverseNode", "universe": "NASDAQ100"},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "exclusion", "type": "ExclusionListNode", "symbols": [{"symbol": "NVDA", "exchange": "NASDAQ", "reason": "manually excluded"}], "dynamic_symbols": "{{ nodes.account.held_symbols }}", "input_symbols": "{{ nodes.universe.symbols }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.exclusion.filtered }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "broker", "to": "universe"},
                    {"from": "universe", "to": "exclusion"},
                    {"from": "account", "to": "exclusion"},
                    {"from": "exclusion", "to": "display"},
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
            "expected_output": "NASDAQ100 symbols minus NVDA (static) and all currently held positions.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Three inputs: symbols (static blacklist, configured), dynamic_symbols (runtime-bound additional exclusions), input_symbols (universe to filter). Only symbols is required; the other two are optional.",
        "output_consumption": "Use filtered as the cleaned symbol list for downstream order or split nodes. Use excluded for audit display. Use reasons for AI Agent tool queries about why symbols are blocked.",
        "common_combinations": [
            "WatchlistNode/MarketUniverseNode → ExclusionListNode → SplitNode → NewOrderNode",
            "AccountNode.held_symbols → ExclusionListNode.dynamic_symbols (prevent duplicate buys)",
            "ExclusionListNode → SplitNode → OverseasStockMarketDataNode (price check only non-blacklisted)",
        ],
        "pitfalls": [
            "The automatic order-block only applies when the order node is downstream of ExclusionListNode in the DAG — bypassing it removes the protection.",
            "dynamic_symbols must be a list[dict] with symbol and exchange keys. Passing plain strings will fail.",
            "If input_symbols is not connected, the filtered port returns an empty list — connect input_symbols when you need the filtered output.",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="i18n:fields.ExclusionListNode.symbols",
                required=True,
                array_item_type=FieldType.OBJECT,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
                ui_options={
                    "exchanges": [
                        {"value": "NASDAQ", "label": "NASDAQ"},
                        {"value": "NYSE", "label": "NYSE"},
                        {"value": "AMEX", "label": "AMEX"},
                        {"value": "CME", "label": "CME (시카고상업거래소)"},
                        {"value": "EUREX", "label": "EUREX (유럽선물거래소)"},
                        {"value": "SGX", "label": "SGX (싱가포르거래소)"},
                        {"value": "HKEX", "label": "HKEX (홍콩거래소)"},
                    ],
                    "extra_fields": [
                        {"key": "reason", "label": "제외 사유", "type": "string", "required": False},
                    ],
                },
                example=[{"exchange": "NASDAQ", "symbol": "NVDA", "reason": "과열 우려"}],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=["WatchlistNode.symbols", "MarketUniverseNode.symbols", "ScreenerNode.symbols"],
                expected_type="list[dict]",
            ),
            "dynamic_symbols": FieldSchema(
                name="dynamic_symbols",
                type=FieldType.ARRAY,
                description="i18n:fields.ExclusionListNode.dynamic_symbols",
                required=False,
                array_item_type=FieldType.OBJECT,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example_binding="{{ nodes.account.held_symbols }}",
                bindable_sources=["AccountNode.held_symbols", "WatchlistNode.symbols", "ConditionNode.passed_symbols"],
                expected_type="list[dict]",
            ),
            "input_symbols": FieldSchema(
                name="input_symbols",
                type=FieldType.ARRAY,
                description="i18n:fields.ExclusionListNode.input_symbols",
                required=False,
                array_item_type=FieldType.OBJECT,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example_binding="{{ nodes.universe.symbols }}",
                bindable_sources=["MarketUniverseNode.symbols", "WatchlistNode.symbols", "ScreenerNode.symbols"],
                expected_type="list[dict]",
            ),
            "default_reason": FieldSchema(
                name="default_reason",
                type=FieldType.STRING,
                description="i18n:fields.ExclusionListNode.default_reason",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                example="보유 종목 중복 매수 방지",
                placeholder="예: 실적 부진, 리스크 과다",
                expected_type="str",
            ),
        }


class SymbolFilterNode(BaseNode):
    """
    종목 비교/필터 노드 (Symbol Filter Node)
    
    두 종목 리스트를 비교하여 교집합, 합집합, 차집합을 계산합니다.
    
    사용 예시:
    - 관심종목 - 보유종목 = 신규 매수 대상 (중복 매수 방지)
    - RSI과매도 ∩ MACD골든크로스 = 강력 매수 신호
    """

    type: Literal["SymbolFilterNode"] = "SymbolFilterNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.SymbolFilterNode.description"

    # 집합 연산 종류
    operation: Literal["difference", "intersection", "union"] = Field(
        default="difference",
        description="집합 연산 종류",
    )
    
    # input_a, input_b는 바인딩으로 받음
    input_a: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="첫 번째 종목 리스트 (필수)",
    )
    input_b: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="두 번째 종목 리스트 (선택)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="input_a",
            type="symbol_list",
            description="첫 번째 종목 리스트 (예: 관심종목)",
            required=True,
        ),
        InputPort(
            name="input_b",
            type="symbol_list",
            description="두 번째 종목 리스트 (예: 보유종목)",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="결과 종목 수"),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Compute the difference between two symbol lists to find new buy candidates (watchlist minus held positions)",
            "Compute the intersection of two signal lists to find symbols confirmed by multiple independent strategies",
            "Merge two symbol lists into a union for a combined trading universe",
        ],
        "when_not_to_use": [
            "When you need to remove symbols based on a persistent blacklist with reason tracking — use ExclusionListNode instead",
            "When filtering by fundamental criteria (market cap, sector) — use ScreenerNode instead",
            "When applying technical indicator conditions to a symbol list — use ConditionNode with the appropriate plugin",
        ],
        "typical_scenarios": [
            "WatchlistNode → SymbolFilterNode (difference: watchlist minus account holdings) → SplitNode → NewOrderNode",
            "ConditionNode.passed_symbols + ConditionNode.passed_symbols → SymbolFilterNode (intersection: both signals agree) → NewOrderNode",
            "MarketUniverseNode + WatchlistNode → SymbolFilterNode (union: combined universe) → ScreenerNode",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Supports three set operations — difference (A minus B), intersection (A AND B), and union (A OR B) — on any two symbol_list inputs",
        "Matching is done by (symbol, exchange) pair, so the same ticker on different exchanges is treated as distinct",
        "Outputs a symbol_list and a count for use in downstream conditional logic",
        "No broker connection required — pure list computation",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using SymbolFilterNode for blacklisting with reason tracking",
            "reason": "SymbolFilterNode performs pure set operations without reason metadata. It cannot store 'why' a symbol was removed.",
            "alternative": "Use ExclusionListNode which supports per-symbol reason fields and automatic order-block safety.",
        },
        {
            "pattern": "Connecting input_b from a node that may output an empty list without handling the empty case",
            "reason": "For difference with an empty input_b, all of input_a passes through. For intersection with empty input_b, no symbols pass through — this may silently halt order generation.",
            "alternative": "Add an IfNode checking count > 0 before passing the result to order nodes.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Subtract held positions from watchlist (buy only new)",
            "description": "WatchlistNode provides candidates; AccountNode provides current holdings; SymbolFilterNode (difference) returns only symbols not already held.",
            "workflow_snippet": {
                "id": "symbolfiler_difference",
                "name": "Watchlist Minus Holdings",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}, {"symbol": "NVDA", "exchange": "NASDAQ"}]},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "filter", "type": "SymbolFilterNode", "operation": "difference", "input_a": "{{ nodes.watchlist.symbols }}", "input_b": "{{ nodes.account.held_symbols }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.filter.symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "filter"},
                    {"from": "account", "to": "filter"},
                    {"from": "filter", "to": "display"},
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
            "expected_output": "Symbols in the watchlist that are not currently held in the account.",
        },
        {
            "title": "Intersection of two signal lists (confirm with two strategies)",
            "description": "Two ConditionNode outputs (RSI oversold, MACD golden cross) are intersected; only symbols signaled by both strategies proceed.",
            "workflow_snippet": {
                "id": "symbolfiler_intersection",
                "name": "Dual Signal Intersection",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}]},
                    {"id": "rsi_cond", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.watchlist.symbols }}"},
                    {"id": "macd_cond", "type": "ConditionNode", "plugin": "MACD", "data": "{{ nodes.watchlist.symbols }}"},
                    {"id": "filter", "type": "SymbolFilterNode", "operation": "intersection", "input_a": "{{ nodes.rsi_cond.passed_symbols }}", "input_b": "{{ nodes.macd_cond.passed_symbols }}"},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.filter.symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "rsi_cond"},
                    {"from": "watchlist", "to": "macd_cond"},
                    {"from": "rsi_cond", "to": "filter"},
                    {"from": "macd_cond", "to": "filter"},
                    {"from": "filter", "to": "display"},
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
            "expected_output": "Symbols that are simultaneously RSI-oversold and MACD-golden-cross.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "input_a is required; input_b is optional (union/intersection with empty input_b returns input_a unchanged for union, empty for intersection). Both must be list[dict] with symbol and exchange keys.",
        "output_consumption": "Connect symbols to SplitNode.items for per-symbol order/data-fetch iteration. Use count with IfNode to guard against empty results before ordering.",
        "common_combinations": [
            "WatchlistNode + AccountNode.held_symbols → SymbolFilterNode (difference) → SplitNode → NewOrderNode",
            "ConditionNode.passed_symbols + ConditionNode.passed_symbols → SymbolFilterNode (intersection) → SplitNode → NewOrderNode",
            "MarketUniverseNode + WatchlistNode → SymbolFilterNode (union) → ScreenerNode",
        ],
        "pitfalls": [
            "Matching is by (symbol, exchange) pair — AAPL:NASDAQ and AAPL:NYSE are treated as different symbols.",
            "An intersection with an empty input_b produces zero results and will silently skip all downstream order nodes.",
            "SymbolFilterNode does not track reasons for removal — use ExclusionListNode if audit trail is needed.",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "operation": FieldSchema(
                name="operation",
                type=FieldType.ENUM,
                description="어떤 비교를 할지 선택하세요.",
                default="difference",
                required=True,
                enum_values=["difference", "intersection", "union"],
                enum_labels={
                    "difference": "i18n:enums.symbol_operation.difference",
                    "intersection": "i18n:enums.symbol_operation.intersection",
                    "union": "i18n:enums.symbol_operation.union",
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="difference",
                expected_type="str",
            ),
            "input_a": FieldSchema(
                name="input_a",
                type=FieldType.ARRAY,
                description="첫 번째 종목 리스트입니다. WatchlistNode나 다른 노드의 symbols 출력을 연결하세요.",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=["WatchlistNode.symbols", "MarketUniverseNode.symbols", "ScreenerNode.symbols", "AccountNode.held_symbols"],
                expected_type="list[dict]",
            ),
            "input_b": FieldSchema(
                name="input_b",
                type=FieldType.ARRAY,
                description="두 번째 종목 리스트입니다. 비교할 대상을 연결하세요. 예: 보유종목(AccountNode.held_symbols)",
                required=False,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example_binding="{{ nodes.account.held_symbols }}",
                bindable_sources=["WatchlistNode.symbols", "AccountNode.held_symbols", "ConditionNode.passed_symbols"],
                expected_type="list[dict]",
            ),
        }