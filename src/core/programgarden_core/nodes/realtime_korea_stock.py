"""
ProgramGarden Core - Korea Stock Realtime Nodes

국내주식 실시간 노드:
- KoreaStockRealMarketDataNode: 국내주식 실시간 시세 (WebSocket)
- KoreaStockRealAccountNode: 국내주식 실시간 계좌 정보
- KoreaStockRealOrderEventNode: 국내주식 실시간 주문 이벤트
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
    KOREA_STOCK_REAL_BALANCE_FIELDS,
    MARKET_DATA_FULL_FIELDS,
    OHLCV_DATA_FIELDS,
    ORDER_EVENT_FIELDS,
    ORDER_LIST_FIELDS,
    POSITION_FIELDS,
    SYMBOL_LIST_FIELDS,
)


class KoreaStockRealMarketDataNode(BaseNode):
    """
    국내주식 실시간 시세 노드

    WebSocket을 통해 국내주식 실시간 시세(가격, 거래량, 호가)를 수신합니다.
    거래소: KRX (KOSPI, KOSDAQ)
    """

    type: Literal["KoreaStockRealMarketDataNode"] = "KoreaStockRealMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.KoreaStockRealMarketDataNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    stay_connected: bool = Field(
        default=True,
        description="Keep WebSocket connection alive between flow executions.",
    )
    # 단일 종목 (Item-based execution) - 국내주식은 exchange 불필요
    symbol: Optional[Dict[str, str]] = Field(
        default=None,
        description="Single symbol entry with symbol code (6-digit)",
    )

    _inputs: List[InputPort] = [
        InputPort(name="symbol", type="symbol", description="i18n:ports.symbol"),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="ohlcv_data", type="ohlcv_data", description="i18n:ports.ohlcv_data", fields=OHLCV_DATA_FIELDS),
        OutputPort(name="data", type="market_data_full", description="i18n:ports.market_data_full", fields=MARKET_DATA_FULL_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.KoreaStockRealMarketDataNode.symbol",
                description="i18n:fields.KoreaStockRealMarketDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"symbol": "005930"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{symbol: str}",
                help_text="i18n:fields.KoreaStockRealMarketDataNode.symbol.help_text",
                object_schema=[
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.KoreaStockRealMarketDataNode.symbol.symbol", "required": True},
                ],
            ),
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                display_name="i18n:fieldNames.KoreaStockRealMarketDataNode.stay_connected",
                description="i18n:fields.KoreaStockRealMarketDataNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
        }


class KoreaStockRealAccountNode(BaseNode):
    """
    국내주식 실시간 계좌 정보 노드

    국내주식 보유종목, 잔고, 미체결, 실시간 손익을 제공합니다.
    수수료율 설정으로 정확한 손익 계산을 지원합니다.
    세율은 market(KOSPI/KOSDAQ)에 따라 자동 결정됩니다.
    """

    type: Literal["KoreaStockRealAccountNode"] = "KoreaStockRealAccountNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.KoreaStockRealAccountNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    stay_connected: bool = Field(
        default=True,
        description="Keep WebSocket connection alive between flow executions.",
    )
    sync_interval_sec: int = Field(
        default=60, description="REST API sync interval (seconds)"
    )
    commission_rate: float = Field(
        default=0.015,
        description="국내주식 매매 수수료율 (%). LS증권 기본 0.015%"
    )
    market: str = Field(
        default="KOSPI",
        description="시장 구분 (KOSPI/KOSDAQ). 세율 자동 결정에 사용",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="held_symbols", type="symbol_list", description="i18n:ports.held_symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="balance", type="balance_data", description="i18n:ports.balance", fields=KOREA_STOCK_REAL_BALANCE_FIELDS),
        OutputPort(name="open_orders", type="order_list", description="i18n:ports.open_orders", fields=ORDER_LIST_FIELDS),
        OutputPort(name="positions", type="position_data", description="i18n:ports.positions", fields=POSITION_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "commission_rate": FieldSchema(
                name="commission_rate",
                type=FieldType.NUMBER,
                description="i18n:fields.KoreaStockRealAccountNode.commission_rate",
                default=0.015,
                min_value=0,
                max_value=5,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example=0.015,
                example_binding="{{ nodes.config.commission_rate }}",
                expected_type="float",
            ),
            "market": FieldSchema(
                name="market",
                type=FieldType.ENUM,
                description="i18n:fields.KoreaStockRealAccountNode.market",
                default="KOSPI",
                enum_values=["KOSPI", "KOSDAQ"],
                enum_labels={
                    "KOSPI": "i18n:enums.kr_market.KOSPI",
                    "KOSDAQ": "i18n:enums.kr_market.KOSDAQ",
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.KoreaStockRealAccountNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
            ),
            "sync_interval_sec": FieldSchema(
                name="sync_interval_sec",
                type=FieldType.INTEGER,
                description="i18n:fields.KoreaStockRealAccountNode.sync_interval_sec",
                default=60,
                min_value=10,
                max_value=3600,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=60,
                expected_type="int",
            ),
        }


class KoreaStockRealOrderEventNode(BaseNode):
    """
    국내주식 실시간 주문 이벤트 노드

    국내주식 주문 체결/거부/취소 이벤트를 실시간으로 수신합니다.
    이벤트 필터: all, SC0(접수), SC1(체결), SC2(정정), SC3(취소확인), SC4(거부)
    """

    type: Literal["KoreaStockRealOrderEventNode"] = "KoreaStockRealOrderEventNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.KoreaStockRealOrderEventNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    event_filter: str = Field(
        default="all",
        description="i18n:fields.KoreaStockRealOrderEventNode.event_filter"
    )
    stay_connected: bool = Field(
        default=True,
        description="i18n:fields.KoreaStockRealOrderEventNode.stay_connected"
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="accepted", type="order_event", description="i18n:ports.accepted", fields=ORDER_EVENT_FIELDS),
        OutputPort(name="filled", type="order_event", description="i18n:ports.filled", fields=ORDER_EVENT_FIELDS),
        OutputPort(name="modified", type="order_event", description="i18n:ports.modified", fields=ORDER_EVENT_FIELDS),
        OutputPort(name="cancelled", type="order_event", description="i18n:ports.cancelled", fields=ORDER_EVENT_FIELDS),
        OutputPort(name="rejected", type="order_event", description="i18n:ports.rejected", fields=ORDER_EVENT_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "event_filter": FieldSchema(
                name="event_filter",
                type=FieldType.ENUM,
                description="i18n:fields.KoreaStockRealOrderEventNode.event_filter",
                default="all",
                enum_values=["all", "SC0", "SC1", "SC2", "SC3", "SC4"],
                enum_labels={
                    "all": "i18n:enums.event_filter.all",
                    "SC0": "i18n:enums.event_filter.SC0",
                    "SC1": "i18n:enums.event_filter.SC1",
                    "SC2": "i18n:enums.event_filter.SC2",
                    "SC3": "i18n:enums.event_filter.SC3",
                    "SC4": "i18n:enums.event_filter.SC4",
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.KoreaStockRealOrderEventNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
            ),
        }
