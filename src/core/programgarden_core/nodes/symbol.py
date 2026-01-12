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
    category: NodeCategory = NodeCategory.SYMBOL
    description: str = "i18n:nodes.WatchlistNode.description"

    # Product type: overseas_stock or overseas_futures
    # Auto-detected from BrokerNode if connected, otherwise set manually for exchange list display
    product: Optional[str] = Field(
        default=None,
        description="Product type (overseas_stock, overseas_futures). Auto-detected from BrokerNode. Only used for exchange list display in UI.",
    )

    # Symbol entries: [{exchange: "NASDAQ", symbol: "AAPL"}, ...]
    symbols: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of symbol entries with exchange and symbol code",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="broker",
            type="broker_connection",
            description="i18n:ports.broker_connection",
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
            # === PARAMETERS: 핵심 설정 ===
            # product, broker는 BrokerNode에서 자동 감지되므로 UI에 노출하지 않음
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="i18n:fields.WatchlistNode.symbols",
                required=True,
                array_item_type=FieldType.OBJECT,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                ui_component="symbol_editor",
            ),
        }


class MarketUniverseNode(BaseNode):
    """
    Market universe node

    Outputs constituent symbols of a specific market/index
    """

    type: Literal["MarketUniverseNode"] = "MarketUniverseNode"
    category: NodeCategory = NodeCategory.SYMBOL
    description: str = "i18n:nodes.MarketUniverseNode.description"

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
            # === PARAMETERS: 핵심 설정 ===
            "universe": FieldSchema(
                name="universe",
                type=FieldType.STRING,
                description="Market/Index (NASDAQ100, SP500, DOW30, etc.)",
                default="NASDAQ100",
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            "exchange": FieldSchema(
                name="exchange",
                type=FieldType.STRING,
                description="Exchange filter (NYSE, NASDAQ, etc.)",
                required=False,
                category=FieldCategory.PARAMETERS,
            ),
        }


class ScreenerNode(BaseNode):
    """
    Conditional symbol screening node

    Filters symbols based on market cap, volume, sector, etc.
    """

    type: Literal["ScreenerNode"] = "ScreenerNode"
    category: NodeCategory = NodeCategory.SYMBOL
    description: str = "i18n:nodes.ScreenerNode.description"

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
            # === PARAMETERS: 핵심 스크리닝 설정 ===
            "filters": FieldSchema(
                name="filters",
                type=FieldType.OBJECT,
                description="Screening conditions",
                required=False,
                category=FieldCategory.PARAMETERS,
            ),
            "universe": FieldSchema(
                name="universe",
                type=FieldType.STRING,
                description="Target market (ALL, NASDAQ, NYSE, etc.)",
                default="ALL",
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 부가 설정 ===
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="Maximum number of results",
                default=100,
                min_value=1,
                max_value=1000,
                category=FieldCategory.SETTINGS,
            ),
        }


class SymbolFilterNode(BaseNode):
    """
    Symbol list filter/set operation node

    Performs intersection/union/difference operations on multiple symbol lists
    """

    type: Literal["SymbolFilterNode"] = "SymbolFilterNode"
    category: NodeCategory = NodeCategory.SYMBOL
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
                description="Set operation",
                default="intersection",
                enum_values=["union", "intersection", "difference", "exclude"],
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            "exclude_symbols": FieldSchema(
                name="exclude_symbols",
                type=FieldType.ARRAY,
                description="Symbols to exclude",
                array_item_type=FieldType.STRING,
                required=False,
                category=FieldCategory.PARAMETERS,
            ),
        }