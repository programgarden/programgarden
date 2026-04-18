"""
ProgramGarden Core - Korea Stock Realtime Nodes

국내주식 실시간 노드:
- KoreaStockRealMarketDataNode: 국내주식 실시간 시세 (WebSocket)
- KoreaStockRealAccountNode: 국내주식 실시간 계좌 정보
- KoreaStockRealOrderEventNode: 국내주식 실시간 주문 이벤트
"""

from typing import Any, Optional, List, Literal, Dict, ClassVar, TYPE_CHECKING
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

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Stream real-time Korean domestic stock tick data (KOSPI/KOSDAQ) via WebSocket for live intraday strategies",
            "Feed live KRX price updates into ConditionNode for continuous signal evaluation without REST polling",
            "Use stay_connected=True to maintain the WebSocket subscription across workflow execution cycles",
        ],
        "when_not_to_use": [
            "For overseas stock real-time data — use OverseasStockRealMarketDataNode",
            "For overseas futures real-time — use OverseasFuturesRealMarketDataNode",
            "When daily polling is sufficient — use KoreaStockMarketDataNode or KoreaStockHistoricalDataNode",
            "Directly connected to an order or AI node without ThrottleNode — every tick would trigger downstream execution",
        ],
        "typical_scenarios": [
            "KoreaStockRealMarketDataNode → ThrottleNode → ConditionNode → KoreaStockNewOrderNode (domestic tick strategy)",
            "KoreaStockRealMarketDataNode → ThrottleNode → AIAgentNode (periodic live analysis on KRX data)",
            "KoreaStockRealMarketDataNode → CandlestickChartNode (live domestic stock chart)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Streams real-time trade events from LS Securities WebSocket for KRX stocks — ohlcv_data port emits aggregated candles; data port emits raw tick dicts",
        "stay_connected=True keeps the WebSocket subscription live between cycles (recommended for realtime strategies)",
        "Symbol format: 6-digit KRX code (e.g., '005930') without exchange field — domestic market implied",
        "Item-based execution: one subscription per node; use multiple nodes to watch multiple domestic stocks",
        "Real-trading only — KoreaStock product does not support paper trading",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Wiring KoreaStockRealMarketDataNode directly to KoreaStockNewOrderNode without ThrottleNode",
            "reason": "Every incoming tick triggers an order attempt. The executor's rate-limit guard raises a connection error at validation time.",
            "alternative": "Insert ThrottleNode between the realtime source and any order or AI node to control the firing rate.",
        },
        {
            "pattern": "Using exchange field in the symbol dict (e.g., {symbol: '005930', exchange: 'KRX'})",
            "reason": "KoreaStock nodes only accept a 6-digit symbol code without exchange. The exchange field causes a schema validation error.",
            "alternative": "Use {\"symbol\": \"005930\"} without exchange field.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Samsung Electronics live tick stream with ThrottleNode",
            "description": "Subscribe to 005930 ticks via WebSocket, throttle to 60 seconds, then evaluate RSI condition.",
            "workflow_snippet": {
                "id": "korea_stock_real_market_data_throttle",
                "name": "KRX Live Tick Strategy",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "005930"}]},
                    {"id": "real", "type": "KoreaStockRealMarketDataNode", "symbol": "{{ nodes.split.item }}", "stay_connected": True},
                    {"id": "throttle", "type": "ThrottleNode", "interval_seconds": 60},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.real.ohlcv_data }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "split"},
                    {"from": "split", "to": "real"},
                    {"from": "broker", "to": "real"},
                    {"from": "real", "to": "throttle"},
                    {"from": "throttle", "to": "condition"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "ohlcv_data port: {symbol, open, high, low, close, volume} aggregated candle per tick batch. Throttled to once per 60 seconds downstream.",
        },
        {
            "title": "Live candlestick chart for KOSDAQ stock",
            "description": "Stream real-time ticks for a KOSDAQ stock and render a live candlestick chart.",
            "workflow_snippet": {
                "id": "korea_stock_real_market_data_chart",
                "name": "KRX Live Chart",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "247540"}]},
                    {"id": "real", "type": "KoreaStockRealMarketDataNode", "symbol": "{{ nodes.split.item }}", "stay_connected": True},
                    {"id": "chart", "type": "CandlestickChartNode", "data": "{{ nodes.real.ohlcv_data }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "split"},
                    {"from": "split", "to": "real"},
                    {"from": "broker", "to": "real"},
                    {"from": "real", "to": "chart"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "ohlcv_data rendered as live candlestick chart in CandlestickChartNode, updating on each tick.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `symbol` field takes a single dict with only `symbol` key (6-digit KRX code, e.g., {\"symbol\": \"005930\"}). "
            "No exchange field. Set stay_connected=True (default) for continuous realtime strategies. "
            "Use KoreaStockBrokerNode as the upstream broker."
        ),
        "output_consumption": (
            "The `ohlcv_data` port emits aggregated candle dicts: {symbol, open, high, low, close, volume}. "
            "The `data` port emits the raw full tick dict including bid/ask. "
            "ALWAYS insert ThrottleNode before any order or AI node downstream."
        ),
        "common_combinations": [
            "KoreaStockRealMarketDataNode → ThrottleNode → ConditionNode → KoreaStockNewOrderNode (live domestic trading)",
            "KoreaStockRealMarketDataNode → CandlestickChartNode (live KRX chart)",
            "KoreaStockRealMarketDataNode → ThrottleNode → AIAgentNode (periodic live analysis)",
        ],
        "pitfalls": [
            "Never connect directly to an order or AI node — always insert ThrottleNode to prevent every-tick execution",
            "KoreaStock does not support paper trading — all strategies use a live LS Securities session",
            "Symbol field must not include exchange key — use {\"symbol\": \"005930\"} only",
        ],
    }

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

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Maintain a continuously updated view of Korea domestic stock held positions, balance, and open orders via WebSocket",
            "Feed live domestic position data into realtime trailing stop or risk management nodes",
            "Prefer over KoreaStockAccountNode when the workflow is a long-running realtime loop",
        ],
        "when_not_to_use": [
            "For one-shot scheduled queries — use the lighter KoreaStockAccountNode (REST, no WebSocket overhead)",
            "For overseas stock realtime account — use OverseasStockRealAccountNode",
            "For overseas futures realtime account — use OverseasFuturesRealAccountNode",
        ],
        "typical_scenarios": [
            "Start → KoreaStockBrokerNode → KoreaStockRealAccountNode → ThrottleNode → ConditionNode (realtime stop-loss)",
            "KoreaStockRealAccountNode.positions → PortfolioNode (live KRW risk aggregation)",
            "KoreaStockRealAccountNode.held_symbols → KoreaStockRealMarketDataNode (realtime mark-to-market)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Provides four output ports: held_symbols, balance (KRW), open_orders, and positions updated via WebSocket",
        "market field (KOSPI/KOSDAQ) drives automatic tax rate selection for accurate net P&L calculation",
        "stay_connected=True keeps the subscription alive; commission_rate configurable to match your LS account plan",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Connecting KoreaStockRealAccountNode directly to order nodes without ThrottleNode",
            "reason": "Each WebSocket tick triggers the full downstream DAG; at tick frequency order nodes can fire multiple times per second creating unintended trades.",
            "alternative": "Insert ThrottleNode (interval_sec=5, mode=latest) between KoreaStockRealAccountNode and any order or condition node.",
        },
        {
            "pattern": "Setting commission_rate=0 in production for Korea stocks",
            "reason": "Zero commission overstates P&L and can lead to incorrect risk signals and premature strategy triggers.",
            "alternative": "Set commission_rate to match your LS account plan (default 0.015% for Korea stocks).",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Realtime Korea stock account monitor",
            "description": "Subscribe to live Korea stock account updates and display positions every 10 seconds.",
            "workflow_snippet": {
                "id": "korea-stock-real-account-display",
                "name": "Realtime Korea Stock Account Monitor",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "real_account", "type": "KoreaStockRealAccountNode", "stay_connected": True, "commission_rate": 0.015, "market": "KOSPI"},
                    {"id": "throttle", "type": "ThrottleNode", "mode": "latest", "interval_sec": 10, "pass_first": True},
                    {"id": "display", "type": "TableDisplayNode", "title": "Live KR Positions", "data": "{{ nodes.throttle.data }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "real_account"},
                    {"from": "real_account", "to": "throttle"},
                    {"from": "throttle", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "Throttled every 10s: positions list with live KRW P&L, balance with cash and orderable amount.",
        },
        {
            "title": "Realtime trailing stop for Korea stocks",
            "description": "Monitor live positions and trigger a stop-loss sell when drawdown exceeds threshold.",
            "workflow_snippet": {
                "id": "korea-stock-real-trailing-stop",
                "name": "Korea Stock Realtime Trailing Stop",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "real_account", "type": "KoreaStockRealAccountNode", "stay_connected": True, "market": "KOSPI"},
                    {"id": "throttle", "type": "ThrottleNode", "mode": "latest", "interval_sec": 5, "pass_first": True},
                    {"id": "condition", "type": "ConditionNode", "plugin": "StopLoss", "data": "{{ nodes.throttle.data }}"},
                    {"id": "order", "type": "KoreaStockNewOrderNode", "symbol": "{{ item.symbol }}", "side": "sell", "order_type": "market", "quantity": "{{ item.quantity }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "real_account"},
                    {"from": "real_account", "to": "throttle"},
                    {"from": "throttle", "to": "condition"},
                    {"from": "condition", "to": "order"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "When StopLoss signals a stop: KoreaStockNewOrderNode fires a market sell for each affected domestic position.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "No input ports. Korea stock broker connection is auto-injected from the upstream KoreaStockBrokerNode. Set market=KOSPI or KOSDAQ for correct tax rate; set commission_rate to match your account plan.",
        "output_consumption": "Four ports: held_symbols (array), balance (KRW object), open_orders (array), positions (array). All array ports auto-iterate; insert ThrottleNode before strategy logic to control frequency.",
        "common_combinations": [
            "KoreaStockRealAccountNode → ThrottleNode → ConditionNode (realtime strategy gate)",
            "KoreaStockRealAccountNode.positions → PortfolioNode (KRW risk aggregation)",
            "KoreaStockRealAccountNode.held_symbols → SplitNode → KoreaStockRealMarketDataNode",
        ],
        "pitfalls": [
            "Without ThrottleNode every WebSocket tick triggers the full downstream DAG — always throttle before expensive nodes",
            "market must match the stocks you hold (KOSPI vs KOSDAQ) as it affects transaction tax rate and P&L accuracy",
        ],
    }

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

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "React immediately to Korea stock fill events (SC1) to update P&L tracking or trigger follow-up orders",
            "Monitor order acceptance (SC0) or rejection (SC4) for domestic stock error recovery",
            "Build event-driven domestic stock strategies that respond to order state transitions without polling",
        ],
        "when_not_to_use": [
            "For a one-shot snapshot of current open orders — use KoreaStockOpenOrdersNode (REST)",
            "For overseas stock order events — use OverseasStockRealOrderEventNode",
            "For overseas futures order events — use OverseasFuturesRealOrderEventNode",
        ],
        "typical_scenarios": [
            "KoreaStockRealOrderEventNode.filled → FieldMappingNode → TableDisplayNode (domestic fill log)",
            "KoreaStockRealOrderEventNode.rejected → TelegramNode (rejection alert)",
            "KoreaStockRealOrderEventNode.filled → ConditionNode (verify fill then adjust hedge)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Emits five event ports: accepted, filled, modified, cancelled, rejected — each fires on the corresponding SC event code",
        "event_filter supports SC0–SC4 individually or 'all' for every Korea stock order event type",
        "Runs persistently with stay_connected=True; events arrive via WebSocket push without polling",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Placing a new order directly on the `filled` port without symbol validation",
            "reason": "All fills for any domestic order fire on the `filled` port; unconditional new orders chain indefinitely.",
            "alternative": "Add a ConditionNode or IfNode that checks `item.symbol == target_symbol` before any follow-up order.",
        },
        {
            "pattern": "Using KoreaStockRealOrderEventNode with a non-Korea broker upstream",
            "reason": "SC event codes are specific to the Korea stock WebSocket stream; an overseas broker cannot provide them.",
            "alternative": "Always wire KoreaStockBrokerNode → KoreaStockRealOrderEventNode via a main edge.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Korea stock fill event display",
            "description": "Subscribe to SC1 fill events and log each confirmed domestic trade.",
            "workflow_snippet": {
                "id": "korea-stock-real-order-event-display",
                "name": "Korea Stock Fill Event Display",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "order_event", "type": "KoreaStockRealOrderEventNode", "event_filter": "SC1", "stay_connected": True},
                    {"id": "display", "type": "TableDisplayNode", "title": "KR Fill Events", "data": "{{ nodes.order_event.filled }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "order_event"},
                    {"from": "order_event", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "On each SC1 fill: filled port emits {order_id, symbol, side, quantity, price, fill_time}; TableDisplayNode logs each trade.",
        },
        {
            "title": "Korea stock rejection alert via Telegram",
            "description": "Send a Telegram notification whenever a domestic stock order is rejected.",
            "workflow_snippet": {
                "id": "korea-stock-order-rejection-alert",
                "name": "Korea Stock Order Rejection Alert",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "order_event", "type": "KoreaStockRealOrderEventNode", "event_filter": "SC4", "stay_connected": True},
                    {"id": "telegram", "type": "TelegramNode", "credential_id": "tg_cred", "message": "KR order rejected: {{ nodes.order_event.rejected.symbol }} {{ nodes.order_event.rejected.order_id }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "order_event"},
                    {"from": "order_event", "to": "telegram"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    },
                    {
                        "credential_id": "tg_cred",
                        "type": "telegram_bot",
                        "data": [
                            {"key": "bot_token", "value": "", "type": "password", "label": "Bot Token"},
                            {"key": "chat_id", "value": "", "type": "text", "label": "Chat ID"},
                        ],
                    },
                ],
            },
            "expected_output": "On each SC4 rejection event: TelegramNode sends the rejection alert with symbol and order_id.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "No input ports. Korea stock broker connection is auto-injected from the upstream KoreaStockBrokerNode. Set event_filter to a specific SC code or 'all'.",
        "output_consumption": "Five ports (accepted, filled, modified, cancelled, rejected) each fire independently on the corresponding broker event. Wire each port to its own downstream node chain as needed.",
        "common_combinations": [
            "KoreaStockRealOrderEventNode.filled → FieldMappingNode → TableDisplayNode",
            "KoreaStockRealOrderEventNode.rejected → TelegramNode (alert)",
            "KoreaStockRealOrderEventNode.filled → ConditionNode (P&L check → hedge)",
        ],
        "pitfalls": [
            "All five ports fire independently; avoid wiring all ports to the same heavy downstream node without filtering",
            "Real trading only — KoreaStockBrokerNode does not support paper_trading mode; no mock order events are generated",
        ],
    }

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
