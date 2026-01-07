"""
ProgramGarden Core - Realtime Nodes

Realtime stream nodes:
- RealMarketDataNode: WebSocket market data stream
- RealAccountNode: Realtime account information
- RealOrderEventNode: Realtime order events
"""

from typing import Optional, List, Literal
from pydantic import Field

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
        OutputPort(name="price", type="market_data", description="i18n:ports.price_data"),
        OutputPort(
            name="volume", type="market_data", description="i18n:ports.volume_data"
        ),
        OutputPort(name="bid", type="market_data", description="i18n:ports.bid"),
        OutputPort(name="ask", type="market_data", description="i18n:ports.ask"),
    ]


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
