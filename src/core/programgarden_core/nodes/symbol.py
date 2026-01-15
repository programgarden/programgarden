"""
ProgramGarden Core - Symbol Nodes

Symbol source/filter nodes:
- WatchlistNode: User-defined watchlist
- MarketUniverseNode: Market universe (NASDAQ100, S&P500, etc.)
- ScreenerNode: Conditional symbol screening
- SymbolFilterNode: Symbol list filter/intersection/difference
- SymbolQueryNode: 전체종목조회 - All tradable symbols from broker API (g3190 for stock, o3101 for futures)
"""

from typing import Optional, List, Literal, Dict, Any, Union, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)
from programgarden_core.models.exchange import SymbolEntry, ProductType


class SymbolQueryNode(BaseNode):
    """
    전체종목조회 노드 (Symbol Query Node)

    Queries all tradable symbols from broker API.
    - overseas_stock: Uses g3190 API (마스터상장종목조회)
    - overseas_futures: Uses o3101 API (해외선물마스터조회)
    
    Returns a list of all symbols available for trading on the selected exchange.
    """

    type: Literal["SymbolQueryNode"] = "SymbolQueryNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.SymbolQueryNode.description"

    # 브로커 연결 필드 (명시적 바인딩 필수)
    connection: Optional[Dict] = None  # BrokerNode의 connection 출력

    # 상품 유형 선택 (해외주식/해외선물)
    product_type: str = Field(
        default="overseas_stock",
        description="Product type: overseas_stock or overseas_futures",
    )

    # 거래소 선택 (해외주식)
    stock_exchange: Optional[str] = Field(
        default=None,
        description="Exchange for overseas_stock: NYSE(81), NASDAQ(82), AMEX(83), etc.",
    )
    
    # 국가 선택 (해외주식) - g3190 natcode
    country: str = Field(
        default="US",
        description="Country code for overseas_stock (US, HK, JP, CN, etc.)",
    )
    
    # 거래소 구분 (해외선물) - o3101 gubun
    futures_exchange: Optional[str] = Field(
        default=None,
        description="Exchange for overseas_futures: 1(all), 2(CME), 3(SGX), etc.",
    )
    
    # 월물 필터 (해외선물)
    futures_contract_month: Optional[str] = Field(
        default=None,
        description="Contract month filter for overseas_futures: F, 2026F, front, next",
    )
    
    # 최대 조회 건수
    max_results: int = Field(
        default=500,
        description="Maximum number of symbols to retrieve per request",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
            required=True,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols"),
        OutputPort(name="count", type="integer", description="Total symbol count"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 브로커 연결 (필수) ===
            "connection": FieldSchema(
                name="connection",
                type=FieldType.OBJECT,
                description="증권사 연결 정보입니다. BrokerNode를 먼저 추가하고, 그 노드의 connection 출력을 연결하세요.",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                example={"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
                example_binding="{{ nodes.broker.connection }}",
                bindable_sources=["BrokerNode.connection"],
                expected_type="broker_connection",
            ),
            # === PARAMETERS: 상품 유형 선택 ===
            "product_type": FieldSchema(
                name="product_type",
                type=FieldType.ENUM,
                description="상품 유형을 선택하세요. 해외주식 또는 해외선물.",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                enum_labels={"overseas_stock": "해외주식", "overseas_futures": "해외선물"},
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="overseas_stock",
                expected_type="str",
            ),
            # === PARAMETERS: 해외주식 설정 (overseas_stock 선택시만 표시) ===
            "country": FieldSchema(
                name="country",
                type=FieldType.ENUM,
                description="국가 코드. US: 미국, HK: 홍콩, JP: 일본, CN: 중국",
                default="US",
                enum_values=["US", "HK", "JP", "CN", "VN", "ID"],
                enum_labels={"US": "미국", "HK": "홍콩", "JP": "일본", "CN": "중국", "VN": "베트남", "ID": "인도네시아"},
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="US",
                expected_type="str",
                visible_when={"product_type": "overseas_stock"},
            ),
            "stock_exchange": FieldSchema(
                name="stock_exchange",
                type=FieldType.ENUM,
                description="거래소 구분. NYSE/AMEX: 81, NASDAQ: 82, 전체: 빈값",
                enum_values=["", "81", "82"],
                enum_labels={"": "전체", "81": "NYSE/AMEX", "82": "NASDAQ"},
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="82",
                expected_type="str",
                visible_when={"product_type": "overseas_stock"},
            ),
            # === PARAMETERS: 해외선물 설정 (overseas_futures 선택시만 표시) ===
            "futures_exchange": FieldSchema(
                name="futures_exchange",
                type=FieldType.ENUM,
                description="거래소 구분. 1: 전체, 2: CME, 3: SGX, 4: EUREX, 5: ICE, 6: HKEX, 7: OSE",
                enum_values=["1", "2", "3", "4", "5", "6", "7"],
                enum_labels={"1": "전체", "2": "CME", "3": "SGX", "4": "EUREX", "5": "ICE", "6": "HKEX", "7": "OSE"},
                default="1",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="1",
                expected_type="str",
                visible_when={"product_type": "overseas_futures"},
            ),
            "futures_contract_month": FieldSchema(
                name="futures_contract_month",
                type=FieldType.STRING,
                description="월물 필터. 예: 'F' (1월), '2026F' (2026년 1월), 'front' (근월물), 'next' (차월물). 월물코드: F=1월, G=2월, H=3월, J=4월, K=5월, M=6월, N=7월, Q=8월, U=9월, V=10월, X=11월, Z=12월",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="front",
                expected_type="str",
                placeholder="front, next, F, 2026F",
                visible_when={"product_type": "overseas_futures"},
            ),
            # === SETTINGS: 부가 설정 ===
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="최대 조회 건수. 연속 조회로 전체 데이터를 가져옵니다.",
                default=500,
                min_value=100,
                max_value=10000,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=500,
                expected_type="int",
            ),
        }


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
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols")
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 설정 ===
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="관심종목 목록입니다. 각 항목에 거래소(exchange)와 종목코드(symbol)를 입력하세요.",
                required=True,
                array_item_type=FieldType.OBJECT,
                bindable=False,
                expression_enabled=False,
                category=FieldCategory.PARAMETERS,
                ui_component="symbol_editor",
                example=[{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NASDAQ", "symbol": "TSLA"}],
                expected_type="list[dict]",
            ),
        }


class MarketUniverseNode(BaseNode):
    """
    Market universe node

    Outputs constituent symbols of a specific market/index
    """

    type: Literal["MarketUniverseNode"] = "MarketUniverseNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.MarketUniverseNode.description"

    # 브로커 연결 필드 (명시적 바인딩 필수)
    connection: Optional[Dict] = None  # BrokerNode의 connection 출력

    # MarketUniverseNode specific config
    universe: str = Field(
        default="NASDAQ100",
        description="Market/Index (NASDAQ100, SP500, DOW30, RUSSELL2000, etc.)",
    )
    exchange: Optional[str] = Field(
        default=None, description="Exchange filter (NYSE, NASDAQ, AMEX, etc.)"
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
            required=True,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols")
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 브로커 연결 (필수) ===
            "connection": FieldSchema(
                name="connection",
                type=FieldType.OBJECT,
                description="증권사 연결 정보입니다. BrokerNode(브로커 노드)를 먼저 추가하고, 그 노드의 connection 출력을 여기에 연결하세요.",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                example={"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
                example_binding="{{ nodes.broker.connection }}",
                bindable_sources=["BrokerNode.connection"],
                expected_type="broker_connection",
            ),
            # === PARAMETERS: 핵심 설정 ===
            "universe": FieldSchema(
                name="universe",
                type=FieldType.STRING,
                description="Market/Index to get constituents from. Options: NASDAQ100, SP500, DOW30, RUSSELL2000.",
                default="NASDAQ100",
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="NASDAQ100",
                expected_type="str",
            ),
            "exchange": FieldSchema(
                name="exchange",
                type=FieldType.STRING,
                description="Optional exchange filter. Options: NYSE, NASDAQ, AMEX. Leave empty for all exchanges.",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="NASDAQ",
                expected_type="str",
            ),
        }


class ScreenerNode(BaseNode):
    """
    Conditional symbol screening node

    Filters symbols based on market cap, volume, sector, etc.
    """

    type: Literal["ScreenerNode"] = "ScreenerNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.ScreenerNode.description"

    # 브로커 연결 필드 (명시적 바인딩 필수)
    connection: Optional[Dict] = None  # BrokerNode의 connection 출력

    # ScreenerNode specific config
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Screening conditions (e.g., {'market_cap_min': 10e9, 'volume_min': 1e6})",
    )
    universe: str = Field(
        default="ALL", description="Target market for screening (ALL, NASDAQ, NYSE, etc.)"
    )
    max_results: int = Field(default=100, description="Maximum number of results")

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols")
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 브로커 연결 (필수) ===
            "connection": FieldSchema(
                name="connection",
                type=FieldType.OBJECT,
                description="증권사 연결 정보입니다. BrokerNode(브로커 노드)를 먼저 추가하고, 그 노드의 connection 출력을 여기에 연결하세요.",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                example={"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
                example_binding="{{ nodes.broker.connection }}",
                bindable_sources=["BrokerNode.connection"],
                expected_type="broker_connection",
            ),
            # === PARAMETERS: 핵심 스크리닝 설정 ===
            "filters": FieldSchema(
                name="filters",
                type=FieldType.OBJECT,
                description="Screening conditions. Available filters: market_cap_min, market_cap_max, volume_min, volume_max, sector, pe_ratio_max, dividend_yield_min.",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example={"market_cap_min": 10000000000, "volume_min": 1000000},
                expected_type="dict[str, Any]",
            ),
            "universe": FieldSchema(
                name="universe",
                type=FieldType.STRING,
                description="Target market for screening. ALL: all markets. NASDAQ: NASDAQ only. NYSE: NYSE only.",
                default="ALL",
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="ALL",
                expected_type="str",
            ),
            # === SETTINGS: 부가 설정 ===
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="Maximum number of symbols to return. Results are sorted by market cap descending.",
                default=100,
                min_value=1,
                max_value=1000,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=100,
                expected_type="int",
            ),
        }


class SymbolFilterNode(BaseNode):
    """
    Symbol list filter/set operation node

    Performs intersection/union/difference operations on multiple symbol lists
    """

    type: Literal["SymbolFilterNode"] = "SymbolFilterNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.SymbolFilterNode.description"

    # SymbolFilterNode specific config
    operation: Literal["union", "intersection", "difference", "exclude"] = Field(
        default="intersection",
        description="Set operation (union, intersection, difference, exclude)",
    )
    exclude_symbols: List[str] = Field(
        default_factory=list, description="Symbols to exclude (for exclude operation)"
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="input_a",
            type="symbol_list",
            description="First symbol list",
        ),
        InputPort(
            name="input_b",
            type="symbol_list",
            description="Second symbol list",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols")
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 모두 핵심 설정 ===
            "operation": FieldSchema(
                name="operation",
                type=FieldType.ENUM,
                description="Set operation on symbol lists. union: combine all. intersection: common symbols only. difference: in A but not B. exclude: remove specified symbols.",
                default="intersection",
                enum_values=["union", "intersection", "difference", "exclude"],
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="intersection",
                expected_type="str",
            ),
            "exclude_symbols": FieldSchema(
                name="exclude_symbols",
                type=FieldType.ARRAY,
                description="Symbols to exclude when operation='exclude'. List specific tickers to remove from result.",
                array_item_type=FieldType.STRING,
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=True,
                expression_enabled=True,
                example=["AAPL", "MSFT"],
                example_binding="{{ nodes.blacklist.symbols }}",
                expected_type="list[str]",
            ),
        }