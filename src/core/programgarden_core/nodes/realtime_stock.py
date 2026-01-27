"""
ProgramGarden Core - Stock Realtime Nodes

해외주식 실시간 노드:
- OverseasStockRealMarketDataNode: 해외주식 실시간 시세 (WebSocket)
- OverseasStockRealAccountNode: 해외주식 실시간 계좌 정보
- OverseasStockRealOrderEventNode: 해외주식 실시간 주문 이벤트
"""

from typing import Optional, List, Literal, Dict, ClassVar, TYPE_CHECKING
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
    BALANCE_FIELDS,
    POSITION_FIELDS,
    SYMBOL_LIST_FIELDS,
    PRICE_DATA_FIELDS,
)


class OverseasStockRealMarketDataNode(BaseNode):
    """
    해외주식 실시간 시세 노드

    WebSocket을 통해 해외주식 실시간 시세(가격, 거래량, 호가)를 수신합니다.
    거래소: NYSE, NASDAQ, AMEX
    """

    type: Literal["OverseasStockRealMarketDataNode"] = "OverseasStockRealMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasStockRealMarketDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/realmarketdata_stock.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    stay_connected: bool = Field(
        default=True,
        description="Keep WebSocket connection alive between flow executions.",
    )
    symbols: List[Dict[str, str]] = Field(
        default=[],
        description="Symbols to subscribe with exchange info. Format: [{exchange, symbol}, ...].",
    )

    _inputs: List[InputPort] = [
        InputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols"),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.subscribed_symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="ohlcv_data", type="ohlcv_data", description="i18n:ports.ohlcv_data"),
        OutputPort(name="data", type="market_data_full", description="i18n:ports.market_data_full"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                display_name="i18n:fieldNames.OverseasStockRealMarketDataNode.symbols",
                description="i18n:fields.OverseasStockRealMarketDataNode.symbols",
                default=[],
                array_item_type=FieldType.OBJECT,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example=[{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NASDAQ", "symbol": "TSLA"}],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=[
                    "WatchlistNode.symbols",
                    "ScreenerNode.symbols",
                    "MarketUniverseNode.symbols",
                ],
                expected_type="list[{exchange: str, symbol: str}]",
                ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
                help_text="i18n:fields.OverseasStockRealMarketDataNode.symbols.help_text",
                object_schema=[
                    {"name": "exchange", "type": "ENUM", "label": "i18n:fields.OverseasStockRealMarketDataNode.symbols.exchange", "required": True, "expression_mode": "fixed_only"},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasStockRealMarketDataNode.symbols.symbol", "required": True, "expression_mode": "fixed_only", "placeholder": "AAPL"},
                ],
                ui_options={
                    "exchanges": [
                        {"value": "NASDAQ", "label": "NASDAQ"},
                        {"value": "NYSE", "label": "NYSE"},
                        {"value": "AMEX", "label": "AMEX"},
                    ],
                },
            ),
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                display_name="i18n:fieldNames.OverseasStockRealMarketDataNode.stay_connected",
                description="i18n:fields.OverseasStockRealMarketDataNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
        }


class OverseasStockRealAccountNode(BaseNode):
    """
    해외주식 실시간 계좌 정보 노드

    해외주식 보유종목, 잔고, 미체결, 실시간 손익을 제공합니다.
    수수료율/세금율 설정으로 정확한 손익 계산을 지원합니다.
    """

    type: Literal["OverseasStockRealAccountNode"] = "OverseasStockRealAccountNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasStockRealAccountNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/realaccount_stock.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    stay_connected: bool = Field(
        default=True,
        description="Keep WebSocket connection alive between flow executions.",
    )
    sync_interval_sec: int = Field(
        default=60, description="REST API sync interval (seconds)"
    )
    commission_rate: float = Field(
        default=0.25,
        description="해외주식 매매 수수료율 (%). LS증권 기본 0.25%"
    )
    tax_rate: float = Field(
        default=0.0,
        description="해외주식 거래세율 (%). 미국 0%, 홍콩 0.1%, 일본 0%"
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="held_symbols", type="symbol_list", description="i18n:ports.held_symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="balance", type="balance_data", description="i18n:ports.balance", fields=BALANCE_FIELDS),
        OutputPort(name="open_orders", type="order_list", description="i18n:ports.open_orders"),
        OutputPort(name="positions", type="position_data", description="i18n:ports.positions", fields=POSITION_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "commission_rate": FieldSchema(
                name="commission_rate",
                type=FieldType.NUMBER,
                description="i18n:fields.OverseasStockRealAccountNode.commission_rate",
                default=0.25,
                min_value=0,
                max_value=5,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example=0.25,
                example_binding="{{ nodes.config.commission_rate }}",
                expected_type="float",
            ),
            "tax_rate": FieldSchema(
                name="tax_rate",
                type=FieldType.NUMBER,
                description="i18n:fields.OverseasStockRealAccountNode.tax_rate",
                default=0.0,
                min_value=0,
                max_value=1,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example=0.0,
                example_binding="{{ nodes.config.tax_rate }}",
                expected_type="float",
            ),
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.OverseasStockRealAccountNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
            ),
            "sync_interval_sec": FieldSchema(
                name="sync_interval_sec",
                type=FieldType.INTEGER,
                description="i18n:fields.OverseasStockRealAccountNode.sync_interval_sec",
                default=60,
                min_value=10,
                max_value=3600,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=60,
                expected_type="int",
            ),
        }


class OverseasStockRealOrderEventNode(BaseNode):
    """
    해외주식 실시간 주문 이벤트 노드

    해외주식 주문 체결/거부/취소 이벤트를 실시간으로 수신합니다.
    이벤트 필터: all, AS0(접수), AS1(체결), AS2(정정), AS3(취소확인), AS4(거부)
    """

    type: Literal["OverseasStockRealOrderEventNode"] = "OverseasStockRealOrderEventNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasStockRealOrderEventNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/realorderevent_stock.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    event_filter: str = Field(
        default="all",
        description="i18n:fields.OverseasStockRealOrderEventNode.event_filter"
    )
    stay_connected: bool = Field(
        default=True,
        description="i18n:fields.OverseasStockRealOrderEventNode.stay_connected"
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="accepted", type="order_event", description="i18n:ports.accepted"),
        OutputPort(name="filled", type="order_event", description="i18n:ports.filled"),
        OutputPort(name="modified", type="order_event", description="i18n:ports.modified"),
        OutputPort(name="cancelled", type="order_event", description="i18n:ports.cancelled"),
        OutputPort(name="rejected", type="order_event", description="i18n:ports.rejected"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "event_filter": FieldSchema(
                name="event_filter",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockRealOrderEventNode.event_filter",
                default="all",
                enum_values=["all", "AS0", "AS1", "AS2", "AS3", "AS4"],
                enum_labels={
                    "all": "i18n:enums.event_filter.all",
                    "AS0": "i18n:enums.event_filter.AS0",
                    "AS1": "i18n:enums.event_filter.AS1",
                    "AS2": "i18n:enums.event_filter.AS2",
                    "AS3": "i18n:enums.event_filter.AS3",
                    "AS4": "i18n:enums.event_filter.AS4"
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.OverseasStockRealOrderEventNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
            ),
        }
