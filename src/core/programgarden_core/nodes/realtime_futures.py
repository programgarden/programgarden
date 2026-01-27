"""
ProgramGarden Core - Futures Realtime Nodes

해외선물 실시간 노드:
- OverseasFuturesRealMarketDataNode: 해외선물 실시간 시세 (WebSocket)
- OverseasFuturesRealAccountNode: 해외선물 실시간 계좌 정보
- OverseasFuturesRealOrderEventNode: 해외선물 실시간 주문 이벤트
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


class OverseasFuturesRealMarketDataNode(BaseNode):
    """
    해외선물 실시간 시세 노드

    WebSocket을 통해 해외선물 실시간 시세(가격, 거래량, 호가)를 수신합니다.
    거래소: CME, EUREX, SGX, HKEX
    """

    type: Literal["OverseasFuturesRealMarketDataNode"] = "OverseasFuturesRealMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasFuturesRealMarketDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/realmarketdata_futures.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
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
                display_name="i18n:fieldNames.OverseasFuturesRealMarketDataNode.symbols",
                description="i18n:fields.OverseasFuturesRealMarketDataNode.symbols",
                default=[],
                array_item_type=FieldType.OBJECT,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example=[{"exchange": "CME", "symbol": "ESH26"}, {"exchange": "EUREX", "symbol": "FDXH26"}],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=[
                    "WatchlistNode.symbols",
                ],
                expected_type="list[{exchange: str, symbol: str}]",
                ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
                help_text="i18n:fields.OverseasFuturesRealMarketDataNode.symbols.help_text",
                object_schema=[
                    {"name": "exchange", "type": "ENUM", "label": "i18n:fields.OverseasFuturesRealMarketDataNode.symbols.exchange", "required": True, "expression_mode": "fixed_only"},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasFuturesRealMarketDataNode.symbols.symbol", "required": True, "expression_mode": "fixed_only", "placeholder": "ESH26"},
                ],
                ui_options={
                    "exchanges": [
                        {"value": "CME", "label": "CME (시카고상업거래소)"},
                        {"value": "EUREX", "label": "EUREX (유럽선물거래소)"},
                        {"value": "SGX", "label": "SGX (싱가포르거래소)"},
                        {"value": "HKEX", "label": "HKEX (홍콩선물거래소)"},
                    ],
                },
            ),
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                display_name="i18n:fieldNames.OverseasFuturesRealMarketDataNode.stay_connected",
                description="i18n:fields.OverseasFuturesRealMarketDataNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
        }


class OverseasFuturesRealAccountNode(BaseNode):
    """
    해외선물 실시간 계좌 정보 노드

    해외선물 보유종목, 잔고, 미체결, 실시간 손익을 제공합니다.
    계약당 수수료 설정으로 정확한 손익 계산을 지원합니다.
    """

    type: Literal["OverseasFuturesRealAccountNode"] = "OverseasFuturesRealAccountNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasFuturesRealAccountNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/realaccount_futures.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    stay_connected: bool = Field(
        default=True,
        description="Keep WebSocket connection alive between flow executions.",
    )
    sync_interval_sec: int = Field(
        default=60, description="REST API sync interval (seconds)"
    )
    futures_fee_per_contract: float = Field(
        default=7.5,
        description="해외선물 계약당 수수료 (USD, 편도). LS증권 기본 $7.5"
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
            "futures_fee_per_contract": FieldSchema(
                name="futures_fee_per_contract",
                type=FieldType.NUMBER,
                description="i18n:fields.OverseasFuturesRealAccountNode.futures_fee_per_contract",
                default=7.5,
                min_value=0,
                max_value=100,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example_binding="{{ nodes.config.futures_fee }}",
                example=7.5,
                expected_type="float",
            ),
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.OverseasFuturesRealAccountNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
            ),
            "sync_interval_sec": FieldSchema(
                name="sync_interval_sec",
                type=FieldType.INTEGER,
                description="i18n:fields.OverseasFuturesRealAccountNode.sync_interval_sec",
                default=60,
                min_value=10,
                max_value=3600,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=60,
                expected_type="int",
            ),
        }


class OverseasFuturesRealOrderEventNode(BaseNode):
    """
    해외선물 실시간 주문 이벤트 노드

    해외선물 주문 체결/거부/취소 이벤트를 실시간으로 수신합니다.
    이벤트 필터: all, TC1(주문접수), TC2(정정/취소), TC3(체결)
    """

    type: Literal["OverseasFuturesRealOrderEventNode"] = "OverseasFuturesRealOrderEventNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasFuturesRealOrderEventNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/realorderevent_futures.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    event_filter: str = Field(
        default="all",
        description="i18n:fields.OverseasFuturesRealOrderEventNode.event_filter"
    )
    stay_connected: bool = Field(
        default=True,
        description="i18n:fields.OverseasFuturesRealOrderEventNode.stay_connected"
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
                description="i18n:fields.OverseasFuturesRealOrderEventNode.event_filter",
                default="all",
                enum_values=["all", "TC1", "TC2", "TC3"],
                enum_labels={
                    "all": "i18n:enums.event_filter_futures.all",
                    "TC1": "i18n:enums.event_filter_futures.TC1",
                    "TC2": "i18n:enums.event_filter_futures.TC2",
                    "TC3": "i18n:enums.event_filter_futures.TC3"
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.OverseasFuturesRealOrderEventNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
            ),
        }
