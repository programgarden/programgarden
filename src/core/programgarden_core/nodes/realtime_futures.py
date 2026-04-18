"""
ProgramGarden Core - Futures Realtime Nodes

해외선물 실시간 노드:
- OverseasFuturesRealMarketDataNode: 해외선물 실시간 시세 (WebSocket)
- OverseasFuturesRealAccountNode: 해외선물 실시간 계좌 정보
- OverseasFuturesRealOrderEventNode: 해외선물 실시간 주문 이벤트
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
    OVERSEAS_FUTURES_REAL_BALANCE_FIELDS,
    MARKET_DATA_FULL_FIELDS,
    OHLCV_DATA_FIELDS,
    ORDER_EVENT_FIELDS,
    ORDER_LIST_FIELDS,
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
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Stream real-time overseas futures tick data (price, volume, open interest) via WebSocket for live intraday futures strategies",
            "Feed live futures prices into ConditionNode for continuous signal evaluation on CME, EUREX, SGX, or HKEX contracts",
            "Use stay_connected=True to maintain the WebSocket subscription across workflow execution cycles",
        ],
        "when_not_to_use": [
            "For US stock real-time data — use OverseasStockRealMarketDataNode",
            "For Korean domestic stock real-time — use KoreaStockRealMarketDataNode",
            "When polling historical bars is sufficient — use OverseasFuturesHistoricalDataNode to avoid WebSocket overhead",
            "Directly connected to an order or AI node without ThrottleNode — every tick would trigger downstream execution",
        ],
        "typical_scenarios": [
            "OverseasFuturesRealMarketDataNode → ThrottleNode → ConditionNode → OverseasFuturesNewOrderNode (futures tick strategy)",
            "OverseasFuturesRealMarketDataNode → ThrottleNode → AIAgentNode (periodic AI analysis on live futures)",
            "OverseasFuturesRealMarketDataNode → CandlestickChartNode (live futures chart display)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Streams real-time trade events from LS Securities WebSocket — ohlcv_data port emits aggregated candles; data port emits raw tick dicts",
        "stay_connected=True keeps the WebSocket subscription live between cycles (recommended for realtime strategies)",
        "Supports CME, EUREX, SGX, HKEX contracts — symbol must include contract month code (e.g., ESH26)",
        "Item-based execution: one subscription per node; use multiple nodes to watch multiple contracts",
        "Automatically re-subscribes after WebSocket reconnection events",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Wiring OverseasFuturesRealMarketDataNode directly to OverseasFuturesNewOrderNode without ThrottleNode",
            "reason": "Every incoming tick triggers an order attempt. The executor's rate-limit guard raises a connection error at validation time.",
            "alternative": "Insert ThrottleNode between the realtime source and any order or AI node.",
        },
        {
            "pattern": "Setting stay_connected=False in a long-running futures strategy",
            "reason": "stay_connected=False closes the WebSocket after each cycle, causing reconnection overhead and potential missed ticks.",
            "alternative": "Leave stay_connected=True (default) for continuous realtime strategies.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "E-mini S&P live tick stream with ThrottleNode",
            "description": "Subscribe to ESH26 ticks, throttle to 60 seconds, evaluate a MACD condition.",
            "workflow_snippet": {
                "id": "overseas_futures_real_market_data_throttle",
                "name": "Futures Live Tick Strategy",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "ESH26", "exchange": "CME"}]},
                    {"id": "real", "type": "OverseasFuturesRealMarketDataNode", "symbol": "{{ nodes.split.item }}", "stay_connected": True},
                    {"id": "throttle", "type": "ThrottleNode", "interval_seconds": 60},
                    {"id": "condition", "type": "ConditionNode", "plugin": "MACD", "data": "{{ nodes.real.ohlcv_data }}"},
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
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "ohlcv_data port: {symbol, exchange, open, high, low, close, volume} aggregated candle. Throttled to once per 60 seconds downstream.",
        },
        {
            "title": "HKEX mini-futures live chart",
            "description": "Stream MHIH26 ticks and render a live candlestick chart.",
            "workflow_snippet": {
                "id": "overseas_futures_real_market_data_chart",
                "name": "HKEX Live Chart",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "MHIH26", "exchange": "HKEX"}]},
                    {"id": "real", "type": "OverseasFuturesRealMarketDataNode", "symbol": "{{ nodes.split.item }}", "stay_connected": True},
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
                        "type": "broker_ls_overseas_futures",
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
            "The `symbol` field takes a single {exchange, symbol} dict. Bind to `{{ nodes.split.item }}`. "
            "Supported exchanges: CME, EUREX, SGX, HKEX. Symbol must include contract month (e.g., ESH26). "
            "Use OverseasFuturesBrokerNode as the upstream broker."
        ),
        "output_consumption": (
            "The `ohlcv_data` port emits aggregated candle dicts: {symbol, exchange, open, high, low, close, volume}. "
            "The `data` port emits the raw full tick dict. "
            "ALWAYS insert ThrottleNode before any order or AI node downstream."
        ),
        "common_combinations": [
            "OverseasFuturesRealMarketDataNode → ThrottleNode → ConditionNode → OverseasFuturesNewOrderNode (live futures trading)",
            "OverseasFuturesRealMarketDataNode → CandlestickChartNode (live chart)",
            "OverseasFuturesRealMarketDataNode → ThrottleNode → AIAgentNode (periodic live analysis)",
        ],
        "pitfalls": [
            "Never connect directly to an order or AI node — always insert ThrottleNode to prevent every-tick execution",
            "Contract symbols expire quarterly — update symbol (e.g., ESH26 → ESM26) at roll date",
            "stay_connected=False will reconnect on every cycle — use True for realtime strategies",
        ],
    }

    stay_connected: bool = Field(
        default=True,
        description="Keep WebSocket connection alive between flow executions.",
    )
    # 단일 종목 (Item-based execution)
    symbol: Optional[Dict[str, str]] = Field(
        default=None,
        description="Single symbol entry with exchange and symbol code",
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
                display_name="i18n:fieldNames.OverseasFuturesRealMarketDataNode.symbol",
                description="i18n:fields.OverseasFuturesRealMarketDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"exchange": "CME", "symbol": "ESH26"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{exchange: str, symbol: str}",
                help_text="i18n:fields.OverseasFuturesRealMarketDataNode.symbol.help_text",
                object_schema=[
                    {"name": "exchange", "type": "STRING", "label": "i18n:fields.OverseasFuturesRealMarketDataNode.symbol.exchange", "required": True},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasFuturesRealMarketDataNode.symbol.symbol", "required": True},
                ],
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
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Maintain a continuously updated view of overseas futures held positions, balance, and open orders via WebSocket",
            "Feed live futures position data into realtime risk management or trailing stop logic",
            "Prefer over OverseasFuturesAccountNode when the workflow is a long-running realtime loop",
        ],
        "when_not_to_use": [
            "For one-shot scheduled queries — use the lighter OverseasFuturesAccountNode (REST, no WebSocket overhead)",
            "For overseas stock realtime account — use OverseasStockRealAccountNode",
            "For Korea stock realtime account — use KoreaStockRealAccountNode",
        ],
        "typical_scenarios": [
            "Start → OverseasFuturesBrokerNode → OverseasFuturesRealAccountNode → ThrottleNode → ConditionNode (realtime margin guard)",
            "OverseasFuturesRealAccountNode.positions → PortfolioNode (live risk aggregation)",
            "OverseasFuturesRealAccountNode.held_symbols → OverseasFuturesRealMarketDataNode (live mark-to-market)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Provides four output ports: held_symbols, balance (with margin details), open_orders, and positions updated via WebSocket",
        "Configurable futures_fee_per_contract for accurate per-contract net P&L calculation",
        "stay_connected=True keeps the subscription alive; sync_interval_sec controls REST REST-sync cadence",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Connecting OverseasFuturesRealAccountNode directly to order nodes without ThrottleNode",
            "reason": "Each WebSocket tick triggers downstream execution; without throttling order nodes can fire at tick frequency, creating unintended positions.",
            "alternative": "Insert ThrottleNode (interval_sec=5, mode=latest) between RealAccountNode and any order or condition node.",
        },
        {
            "pattern": "Using futures_fee_per_contract=0 in production",
            "reason": "Setting fee to zero overstates P&L and can lead to incorrect risk calculations and premature strategy triggers.",
            "alternative": "Set futures_fee_per_contract to match your LS account plan (default $7.5/contract one-way).",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Realtime futures account monitor",
            "description": "Subscribe to live overseas futures account updates and display positions every 10 seconds.",
            "workflow_snippet": {
                "id": "futures-real-account-display",
                "name": "Realtime Futures Account Monitor",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": True},
                    {"id": "real_account", "type": "OverseasFuturesRealAccountNode", "stay_connected": True, "futures_fee_per_contract": 7.5},
                    {"id": "throttle", "type": "ThrottleNode", "mode": "latest", "interval_sec": 10, "pass_first": True},
                    {"id": "display", "type": "TableDisplayNode", "title": "Live Futures Positions", "data": "{{ nodes.throttle.data }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "real_account"},
                    {"from": "real_account", "to": "throttle"},
                    {"from": "throttle", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "Throttled every 10s: positions list with live net P&L, balance with margin details and orderable margin.",
        },
        {
            "title": "Realtime margin guard with auto-liquidation",
            "description": "Monitor futures margin in realtime and liquidate position when margin falls below safety threshold.",
            "workflow_snippet": {
                "id": "futures-margin-guard",
                "name": "Futures Margin Guard",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": True},
                    {"id": "real_account", "type": "OverseasFuturesRealAccountNode", "stay_connected": True},
                    {"id": "throttle", "type": "ThrottleNode", "mode": "latest", "interval_sec": 5, "pass_first": True},
                    {"id": "condition", "type": "ConditionNode", "plugin": "StopLoss", "data": "{{ nodes.throttle.data }}"},
                    {"id": "order", "type": "OverseasFuturesNewOrderNode", "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}", "side": "sell", "order_type": "market", "quantity": "{{ item.quantity }}"},
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
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "When StopLoss signals a stop: NewOrderNode fires a market sell to liquidate the position.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "No input ports. Broker connection is auto-injected from the upstream OverseasFuturesBrokerNode. Set futures_fee_per_contract to match your actual account plan.",
        "output_consumption": "Four ports: held_symbols (array), balance (object with margin fields), open_orders (array), positions (array). All array ports auto-iterate; insert ThrottleNode before strategy logic.",
        "common_combinations": [
            "OverseasFuturesRealAccountNode → ThrottleNode → ConditionNode (realtime strategy gate)",
            "OverseasFuturesRealAccountNode.positions → PortfolioNode (risk aggregation)",
            "OverseasFuturesRealAccountNode.held_symbols → SplitNode → OverseasFuturesRealMarketDataNode",
        ],
        "pitfalls": [
            "Without ThrottleNode every WebSocket tick triggers the full downstream DAG — always throttle before expensive operations",
            "futures_fee_per_contract must reflect your real account rate; an incorrect value distorts P&L and risk signals",
        ],
    }

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
        OutputPort(name="balance", type="balance_data", description="i18n:ports.balance", fields=OVERSEAS_FUTURES_REAL_BALANCE_FIELDS),
        OutputPort(name="open_orders", type="order_list", description="i18n:ports.open_orders", fields=ORDER_LIST_FIELDS),
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
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "React immediately to futures fill events (TC3) to update P&L tracking or trigger follow-up orders",
            "Monitor futures order acceptance (TC1) or modification/cancellation confirmations (TC2)",
            "Build event-driven futures strategies that respond to order state changes without polling",
        ],
        "when_not_to_use": [
            "For a snapshot of current open orders — use OverseasFuturesOpenOrdersNode (REST)",
            "For overseas stock order events — use OverseasStockRealOrderEventNode",
            "For Korea domestic stock order events — use KoreaStockRealOrderEventNode",
        ],
        "typical_scenarios": [
            "OverseasFuturesRealOrderEventNode.filled → FieldMappingNode → TableDisplayNode (futures fill log)",
            "OverseasFuturesRealOrderEventNode.rejected → TelegramNode (rejection alert)",
            "OverseasFuturesRealOrderEventNode.filled → ConditionNode (verify fill then place hedge leg)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Emits five event ports: accepted, filled, modified, cancelled, rejected — each fires on the corresponding TC event code",
        "event_filter supports TC1 (acceptance), TC2 (modify/cancel), TC3 (fill), or 'all' for all event types",
        "Runs persistently with stay_connected=True; events arrive via WebSocket push without polling",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Placing a new order directly on the `filled` port without symbol validation",
            "reason": "All futures fills for any contract fire on the `filled` port; unconditional new orders create an unintended chain for every fill.",
            "alternative": "Add a ConditionNode or IfNode that checks `item.symbol == target_contract` before placing any follow-up order.",
        },
        {
            "pattern": "Using OverseasFuturesRealOrderEventNode with an OverseasStockBrokerNode upstream",
            "reason": "Product scope mismatch: the stock broker WebSocket stream does not carry futures TC events.",
            "alternative": "Always wire OverseasFuturesBrokerNode → OverseasFuturesRealOrderEventNode via a main edge.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Futures fill event display",
            "description": "Subscribe to futures fill events and log each confirmed trade.",
            "workflow_snippet": {
                "id": "futures-real-order-event-display",
                "name": "Futures Fill Event Display",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": True},
                    {"id": "order_event", "type": "OverseasFuturesRealOrderEventNode", "event_filter": "TC3", "stay_connected": True},
                    {"id": "display", "type": "TableDisplayNode", "title": "Futures Fill Events", "data": "{{ nodes.order_event.filled }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "order_event"},
                    {"from": "order_event", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "On each TC3 fill: filled port emits {order_id, symbol, exchange, side, quantity, price, fill_time}; TableDisplayNode logs the event.",
        },
        {
            "title": "Futures rejection alert via Telegram",
            "description": "Send a Telegram alert whenever an overseas futures order is rejected.",
            "workflow_snippet": {
                "id": "futures-order-rejection-alert",
                "name": "Futures Order Rejection Alert",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": True},
                    {"id": "order_event", "type": "OverseasFuturesRealOrderEventNode", "event_filter": "all", "stay_connected": True},
                    {"id": "telegram", "type": "TelegramNode", "credential_id": "tg_cred", "message": "Futures order rejected: {{ nodes.order_event.rejected.symbol }} {{ nodes.order_event.rejected.order_id }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "order_event"},
                    {"from": "order_event", "to": "telegram"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futures",
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
            "expected_output": "On each rejected event: TelegramNode sends the rejection message with symbol and order_id.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "No input ports. Broker connection is auto-injected from the upstream OverseasFuturesBrokerNode. Set event_filter to a specific TC code or 'all'.",
        "output_consumption": "Five ports (accepted, filled, modified, cancelled, rejected) each fire independently on the corresponding broker event. Wire each port to its own downstream chain.",
        "common_combinations": [
            "OverseasFuturesRealOrderEventNode.filled → FieldMappingNode → TableDisplayNode",
            "OverseasFuturesRealOrderEventNode.rejected → TelegramNode (alert)",
            "OverseasFuturesRealOrderEventNode.filled → ConditionNode (hedge trigger)",
        ],
        "pitfalls": [
            "All five ports are independent; wiring multiple ports to the same heavy downstream chain may cause concurrent executions per event",
            "event_filter='all' receives all TC codes; scope to TC3 when only fill confirmation is needed to reduce noise",
        ],
    }

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
