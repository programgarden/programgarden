"""
ProgramGarden Core - Symbol Nodes

Symbol source/filter nodes:
- WatchlistNode: User-defined watchlist
- MarketUniverseNode: Market universe (NASDAQ100, S&P500, etc.)
- ScreenerNode: Conditional symbol screening
- SymbolFilterNode: Symbol list filter/intersection/difference
"""

from typing import Optional, List, Literal, Dict, Any, Union, ClassVar
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)
from programgarden_core.models.field_binding import FieldSchema, FieldType


class WatchlistNode(BaseNode):
    """
    User-defined watchlist node

    Outputs a list of symbols specified by the user
    """

    type: Literal["WatchlistNode"] = "WatchlistNode"
    category: NodeCategory = NodeCategory.SYMBOL
    description: str = "i18n:nodes.WatchlistNode.description"

    # WatchlistNode specific config
    # Template reference allowed (e.g., "{{inputs.symbols}}")
    symbols: Union[List[str], str] = Field(
        default_factory=list,
        description="List of symbol codes (e.g., ['AAPL', 'TSLA', 'NVDA']) or template reference",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols")
    ]
    _field_schema: ClassVar[Dict[str, FieldSchema]] = {
        "symbols": FieldSchema(
            name="symbols",
            type=FieldType.ARRAY,
            description="i18n:fields.WatchlistNode.symbols",
            required=True,
            array_item_type=FieldType.STRING,
            bindable=True,
            expression_enabled=True,
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
