"""
ProgramGarden Core - Realtime Nodes

Realtime stream nodes:
- RealMarketDataNode: WebSocket market data stream
- RealAccountNode: Realtime account information
- RealOrderEventNode: Realtime order events
"""

from typing import Optional, List, Literal, Dict, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class RealMarketDataNode(BaseNode):
    """
    Realtime market data stream node

    Receives realtime market data (price, volume, bid/ask) via WebSocket
    """

    type: Literal["RealMarketDataNode"] = "RealMarketDataNode"
    category: NodeCategory = NodeCategory.REALTIME
    description: str = "i18n:nodes.RealMarketDataNode.description"

    # RealMarketDataNode specific config
    stay_connected: bool = Field(
        default=True,
        description="Keep WebSocket connection alive between flow executions. "
        "If True, maintains realtime stream until explicit stop(). "
        "If False, disconnects after single data fetch.",
    )
    fields: List[str] = Field(
        default=["price", "volume"],
        description="Fields to receive (price, volume, bid, ask, etc.)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
        ),
        InputPort(
            name="symbols", type="symbol_list", description="i18n:ports.symbols"
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.subscribed_symbols"),
        OutputPort(name="price", type="market_data", description="i18n:ports.price_data"),
        OutputPort(
            name="volume", type="market_data", description="i18n:ports.volume_data"
        ),
        OutputPort(name="bid", type="market_data", description="i18n:ports.bid"),
        OutputPort(name="ask", type="market_data", description="i18n:ports.ask"),
        OutputPort(name="data", type="market_data_full", description="i18n:ports.market_data_full"),
    ]

    # Symbols config field (optional - can also receive from input port)
    symbols: List[str] = Field(
        default=[],
        description="Symbols to subscribe. If empty, uses input port value.",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 설정 ===
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="Symbols to subscribe (e.g., AAPL, TSLA). If empty, uses input port.",
                default=[],
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
            ),
            "fields": FieldSchema(
                name="fields",
                type=FieldType.ARRAY,
                description="Fields to receive (price, volume, bid, ask)",
                default=["price", "volume"],
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 부가 설정 ===
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="Keep WebSocket connection alive",
                default=True,
                category=FieldCategory.SETTINGS,
            ),
        }


class RealAccountNode(BaseNode):
    """
    Realtime account information node

    Provides holdings, balance, open orders, and realtime P&L.
    Uses StockAccountTracker internally for realtime return calculation.

    - Syncs with broker data via REST API every sync_interval_sec
    - Recalculates returns immediately on WebSocket tick
    - Automatically refreshes token before reconnection attempts
    """

    type: Literal["RealAccountNode"] = "RealAccountNode"
    category: NodeCategory = NodeCategory.REALTIME
    description: str = "i18n:nodes.RealAccountNode.description"

    # RealAccountNode specific config
    stay_connected: bool = Field(
        default=True,
        description="Keep WebSocket connection alive between flow executions. "
        "If True with ScheduleNode: stays alive during schedule wait. "
        "If True without ScheduleNode: stays alive until explicit stop(). "
        "If False: disconnects after each flow execution.",
    )
    sync_interval_sec: int = Field(
        default=60, description="REST API sync interval (seconds)"
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="held_symbols", type="symbol_list", description="i18n:ports.held_symbols"
        ),
        OutputPort(
            name="balance",
            type="balance_data",
            description="i18n:ports.balance",
        ),
        OutputPort(
            name="open_orders", type="order_list", description="i18n:ports.open_orders"
        ),
        OutputPort(
            name="positions",
            type="position_data",
            description="i18n:ports.positions",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === SETTINGS: 모두 부가 설정 ===
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="Keep WebSocket connection alive",
                default=True,
                category=FieldCategory.SETTINGS,
            ),
            "sync_interval_sec": FieldSchema(
                name="sync_interval_sec",
                type=FieldType.INTEGER,
                description="REST API sync interval (seconds)",
                default=60,
                min_value=10,
                max_value=3600,
                category=FieldCategory.SETTINGS,
            ),
        }


class RealOrderEventNode(BaseNode):
    """
    Realtime order event node

    Receives realtime order fill/reject/cancel events
    """

    type: Literal["RealOrderEventNode"] = "RealOrderEventNode"
    category: NodeCategory = NodeCategory.REALTIME
    description: str = "i18n:nodes.RealOrderEventNode.description"

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="filled", type="order_event", description="i18n:ports.filled"),
        OutputPort(name="rejected", type="order_event", description="i18n:ports.rejected"),
        OutputPort(name="cancelled", type="order_event", description="i18n:ports.cancelled"),
    ]