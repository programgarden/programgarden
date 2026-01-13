"""
ProgramGarden Core - Symbol Nodes

Symbol source/filter nodes:
- WatchlistNode: User-defined watchlist
- MarketUniverseNode: Market universe (NASDAQ100, S&P500, etc.)
- ScreenerNode: Conditional symbol screening
- SymbolFilterNode: Symbol list filter/intersection/difference
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


class WatchlistNode(BaseNode):
    """
    User-defined watchlist node

    Outputs a list of symbols with exchange information.
    Each symbol entry contains exchange name (NYSE, NASDAQ, CME, etc.) and symbol code.
    
    Exchange names are automatically converted to API codes at execution time.
    - overseas_stock: NYSE/AMEX → 81, NASDAQ → 82
    - overseas_futures: CME, COMEX, etc. (string codes)
    
    Note: Broker information is managed by BrokerNode.
    WatchlistNode only stores symbols - broker/company info comes from connected BrokerNode.
    """

    type: Literal["WatchlistNode"] = "WatchlistNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.WatchlistNode.description"

    # 브로커 연결 필드 (명시적 바인딩 필수)
    connection: Optional[Dict] = None  # BrokerNode의 connection 출력

    # Symbol entries: [{exchange: "NASDAQ", symbol: "AAPL"}, ...]
    symbols: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of symbol entries with exchange and symbol code",
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
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="List of symbols with exchange info. Each entry has 'exchange' (NYSE, NASDAQ, CME, etc.) and 'symbol' (ticker code).",
                required=True,
                array_item_type=FieldType.OBJECT,
                bindable=True,
                expression_enabled=True,
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