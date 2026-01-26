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
        OutputPort(name="ohlcv_data", type="ohlcv_data", description="i18n:ports.ohlcv_data"),
        OutputPort(name="data", type="market_data_full", description="i18n:ports.market_data_full"),
    ]

    # Symbols config field (optional - can also receive from input port)
    symbols: List[Dict[str, str]] = Field(
        default=[],
        description="Symbols to subscribe with exchange info. Format: [{exchange, symbol}, ...]. If empty, uses input port value.",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 브로커 연결 (필수) ===
            "connection": FieldSchema(
                name="connection",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.RealMarketDataNode.connection",
                description="i18n:fields.RealMarketDataNode.connection",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
                example_binding="{{ nodes.broker.connection }}",
                bindable_sources=["BrokerNode.connection"],
                expected_type="broker_connection",
                # ui_component 생략 → EXPRESSION_ONLY + OBJECT 타입에서 바인딩 입력 자동
            ),
            # === PARAMETERS: 종목 리스트 ===
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                display_name="i18n:fieldNames.RealMarketDataNode.symbols",
                description="i18n:fields.RealMarketDataNode.symbols",
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
                help_text="i18n:fields.RealMarketDataNode.symbols.help_text",
                # 테이블 컬럼 정의
                object_schema=[
                    {
                        "name": "exchange",
                        "type": "ENUM",
                        "label": "i18n:fields.RealMarketDataNode.symbols.exchange",
                        "required": True,
                        "expression_mode": "fixed_only",
                    },
                    {
                        "name": "symbol",
                        "type": "STRING",
                        "label": "i18n:fields.RealMarketDataNode.symbols.symbol",
                        "required": True,
                        "expression_mode": "fixed_only",
                        "placeholder": "AAPL",
                    },
                ],
                # 상품유형별 거래소 목록
                ui_options={
                    "exchanges_by_product": {
                        "overseas_stock": [
                            {"value": "NASDAQ", "label": "NASDAQ"},
                            {"value": "NYSE", "label": "NYSE"},
                            {"value": "AMEX", "label": "AMEX"},
                            {"value": "SEHK", "label": "홍콩거래소"},
                            {"value": "TSE", "label": "도쿄거래소"},
                            {"value": "SSE", "label": "상해거래소"},
                            {"value": "SZSE", "label": "심천거래소"},
                        ],
                        "overseas_futures": [
                            {"value": "CME", "label": "CME (시카고상업거래소)"},
                            {"value": "EUREX", "label": "EUREX (유럽선물거래소)"},
                            {"value": "SGX", "label": "SGX (싱가포르거래소)"},
                            {"value": "HKEX", "label": "HKEX (홍콩선물거래소)"},
                        ],
                    },
                    "default_product_type": "overseas_stock",
                },
            ),
            # === PARAMETERS: 필드 매핑 (접힌 상태) ===
            "exchange_field": FieldSchema(
                name="exchange_field",
                type=FieldType.STRING,
                display_name="i18n:fieldNames.RealMarketDataNode.exchange_field",
                description="i18n:fields.RealMarketDataNode.exchange_field",
                default="exchange",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="exchange",
                group="field_mapping",
                collapsed=True,
            ),
            "symbol_field": FieldSchema(
                name="symbol_field",
                type=FieldType.STRING,
                display_name="i18n:fieldNames.RealMarketDataNode.symbol_field",
                description="i18n:fields.RealMarketDataNode.symbol_field",
                default="symbol",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="symbol",
                group="field_mapping",
                collapsed=True,
            ),
            # === SETTINGS: 부가 설정 ===
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                display_name="i18n:fieldNames.RealMarketDataNode.stay_connected",
                description="i18n:fields.RealMarketDataNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                # ui_component 생략 → BOOLEAN 타입에서 checkbox 자동 추론
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
    
    # 상품 유형 선택 (해외주식/해외선물)
    product_type: str = Field(
        default="overseas_stock",
        description="상품 유형 선택 (해외주식/해외선물)"
    )
    
    # 해외주식 수수료/세금 설정 (손익 계산에 반영)
    commission_rate: float = Field(
        default=0.25,
        description="해외주식 매매 수수료율 (%). LS증권 기본 0.25%"
    )
    tax_rate: float = Field(
        default=0.0,
        description="해외주식 거래세율 (%). 미국 0%, 홍콩 0.1%, 일본 0%"
    )
    
    # 해외선물 수수료 설정 (계약당 고정 금액)
    futures_fee_per_contract: float = Field(
        default=7.5,
        description="해외선물 계약당 수수료 (USD, 편도). LS증권 기본 $7.5"
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
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 브로커 연결 (필수) ===
            "connection": FieldSchema(
                name="connection",
                type=FieldType.OBJECT,
                description="증권사 연결 정보입니다. BrokerNode(브로커 노드)를 먼저 추가하고, 그 노드의 connection 출력을 여기에 연결하세요.",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,  # 바인딩 필수
                category=FieldCategory.PARAMETERS,
                example={"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
                example_binding="{{ nodes.broker.connection }}",
                bindable_sources=["BrokerNode.connection"],
                expected_type="broker_connection",
                ui_component=UIComponent.BINDING_INPUT,
            ),
            # === PARAMETERS: 상품 유형 선택 ===
            "product_type": FieldSchema(
                name="product_type",
                type=FieldType.ENUM,
                description="i18n:fields.RealAccountNode.product_type",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                enum_labels={
                    "overseas_stock": "해외주식",
                    "overseas_futures": "해외선물"
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.SELECT,
            ),
            # === PARAMETERS: 해외주식 수수료/세금 (overseas_stock 선택 시만 표시) ===
            "commission_rate": FieldSchema(
                name="commission_rate",
                type=FieldType.NUMBER,
                description="i18n:fields.RealAccountNode.commission_rate",
                default=0.25,
                min_value=0,
                max_value=5,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,  # Fixed/Expression 토글 지원
                example=0.25,
                example_binding="{{ nodes.config.commission_rate }}",
                expected_type="float",
                visible_when={"product_type": "overseas_stock"},
                ui_component=UIComponent.NUMBER_INPUT,
            ),
            "tax_rate": FieldSchema(
                name="tax_rate",
                type=FieldType.NUMBER,
                description="i18n:fields.RealAccountNode.tax_rate",
                default=0.0,
                min_value=0,
                max_value=1,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,  # Fixed/Expression 토글 지원
                example=0.0,
                example_binding="{{ nodes.config.tax_rate }}",
                expected_type="float",
                visible_when={"product_type": "overseas_stock"},
                ui_component=UIComponent.NUMBER_INPUT,
            ),
            # === PARAMETERS: 해외선물 수수료 (overseas_futures 선택 시만 표시) ===
            "futures_fee_per_contract": FieldSchema(
                name="futures_fee_per_contract",
                type=FieldType.NUMBER,
                description="i18n:fields.RealAccountNode.futures_fee_per_contract",
                default=7.5,
                min_value=0,
                max_value=100,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,  # Fixed/Expression 토글 지원
                example_binding="{{ nodes.config.futures_fee }}",
                example=7.5,
                expected_type="float",
                visible_when={"product_type": "overseas_futures"},
                ui_component=UIComponent.NUMBER_INPUT,
            ),
            # === SETTINGS: 부가 설정 ===
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.RealAccountNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
            ),
            "sync_interval_sec": FieldSchema(
                name="sync_interval_sec",
                type=FieldType.INTEGER,
                description="i18n:fields.RealAccountNode.sync_interval_sec",
                default=60,
                min_value=10,
                max_value=3600,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=60,
                expected_type="int",
                ui_component=UIComponent.NUMBER_INPUT,
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
    
    # 상품 유형 선택 (해외주식/해외선물)
    product_type: str = Field(
        default="overseas_stock",
        description="i18n:fields.RealOrderEventNode.product_type"
    )
    
    # 이벤트 필터 - 해외주식 (특정 TR만 수신: all, AS0~AS4)
    event_filter: str = Field(
        default="all",
        description="i18n:fields.RealOrderEventNode.event_filter"
    )
    
    # 이벤트 필터 - 해외선물 (특정 TR만 수신: all, TC1~TC3)
    event_filter_futures: str = Field(
        default="all",
        description="i18n:fields.RealOrderEventNode.event_filter_futures"
    )
    
    # WebSocket 연결 유지 여부
    stay_connected: bool = Field(
        default=True,
        description="i18n:fields.RealOrderEventNode.stay_connected"
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
        ),
    ]
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
            # === PARAMETERS: 브로커 연결 (필수) ===
            "connection": FieldSchema(
                name="connection",
                type=FieldType.OBJECT,
                description="i18n:fields.RealOrderEventNode.connection",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
                example_binding="{{ nodes.broker.connection }}",
                bindable_sources=["BrokerNode.connection"],
                expected_type="broker_connection",
                ui_component=UIComponent.BINDING_INPUT,
            ),
            # === PARAMETERS: 상품 유형 선택 ===
            "product_type": FieldSchema(
                name="product_type",
                type=FieldType.ENUM,
                description="i18n:fields.RealOrderEventNode.product_type",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                enum_labels={
                    "overseas_stock": "i18n:enums.product_type.overseas_stock",
                    "overseas_futures": "i18n:enums.product_type.overseas_futures"
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.SELECT,
            ),
            # === PARAMETERS: 이벤트 필터 (해외주식) ===
            "event_filter": FieldSchema(
                name="event_filter",
                type=FieldType.ENUM,
                description="i18n:fields.RealOrderEventNode.event_filter",
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
                visible_when={"product_type": "overseas_stock"},
                ui_component=UIComponent.SELECT,
            ),
            # === PARAMETERS: 이벤트 필터 (해외선물) ===
            "event_filter_futures": FieldSchema(
                name="event_filter_futures",
                type=FieldType.ENUM,
                description="i18n:fields.RealOrderEventNode.event_filter_futures",
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
                visible_when={"product_type": "overseas_futures"},
                ui_component=UIComponent.SELECT,
            ),
            # === SETTINGS: 부가 설정 ===
            "stay_connected": FieldSchema(
                name="stay_connected",
                type=FieldType.BOOLEAN,
                description="i18n:fields.RealOrderEventNode.stay_connected",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
            ),
        }