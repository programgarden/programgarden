"""
ProgramGarden Core - Realtime Nodes

Realtime stream nodes:
- RealMarketDataNode: WebSocket market data stream
- RealAccountNode: Realtime account information
- RealOrderEventNode: Realtime order events
"""

from typing import Optional, List, Literal, Dict, TYPE_CHECKING, ClassVar
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
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.RealMarketDataNode.description"
    
    # CDN 기반 노드 아이콘 URL
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/realmarketdata.svg"

    # 브로커 연결 필드 (명시적 바인딩 필수)
    connection: Optional[Dict] = None  # BrokerNode의 connection 출력

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
                description="i18n:fields.RealMarketDataNode.symbols",
                default=[],
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
                bindable=True,
                expression_enabled=True,
                # 바인딩 가이드
                example=["AAPL", "TSLA", "NVDA"],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=[
                    "WatchlistNode.symbols",
                    "ScreenerNode.filtered_symbols",
                ],
                expected_type="list[str]",
            ),
            "fields": FieldSchema(
                name="fields",
                type=FieldType.ARRAY,
                description="i18n:fields.RealMarketDataNode.fields",
                default=["price", "volume"],
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                # 바인딩 불가 필드이지만 예시 제공
                example=["price", "volume", "bid", "ask"],
                expected_type="list[str]",
            ),
            # === SETTINGS: 부가 설정 ===
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.RealMarketDataNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                bindable=False,
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
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.RealAccountNode.description"
    
    # CDN 기반 노드 아이콘 URL
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/realaccount.svg"

    # 브로커 연결 필드 (명시적 바인딩 필수)
    connection: Optional[Dict] = None  # BrokerNode의 connection 출력

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
            # === SETTINGS: 부가 설정 ===
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.RealAccountNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                bindable=False,
            ),
            "sync_interval_sec": FieldSchema(
                name="sync_interval_sec",
                type=FieldType.INTEGER,
                description="i18n:fields.RealAccountNode.sync_interval_sec",
                default=60,
                min_value=10,
                max_value=3600,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=60,
                expected_type="int",
            ),
        }


class RealOrderEventNode(BaseNode):
    """
    Realtime order event node

    Receives realtime order fill/reject/cancel events
    """

    type: Literal["RealOrderEventNode"] = "RealOrderEventNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.RealOrderEventNode.description"
    
    # CDN 기반 노드 아이콘 URL
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/realorderevent.svg"

    # 브로커 연결 필드 (명시적 바인딩 필수)
    connection: Optional[Dict] = None  # BrokerNode의 connection 출력

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

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
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
        }