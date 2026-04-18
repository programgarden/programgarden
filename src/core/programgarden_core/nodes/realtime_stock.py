"""
ProgramGarden Core - Stock Realtime Nodes

해외주식 실시간 노드:
- OverseasStockRealMarketDataNode: 해외주식 실시간 시세 (WebSocket)
- OverseasStockRealAccountNode: 해외주식 실시간 계좌 정보
- OverseasStockRealOrderEventNode: 해외주식 실시간 주문 이벤트
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
    OVERSEAS_STOCK_REAL_BALANCE_FIELDS,
    MARKET_DATA_FULL_FIELDS,
    OHLCV_DATA_FIELDS,
    ORDER_EVENT_FIELDS,
    ORDER_LIST_FIELDS,
    POSITION_FIELDS,
    SYMBOL_LIST_FIELDS,
    PRICE_DATA_FIELDS,
)


class OverseasStockRealMarketDataNode(BaseNode):
    """
    해외주식 실시간 시세 노드

    WebSocket을 통해 해외주식 실시간 체결 데이터(가격, 거래량)를 수신합니다.
    GSC(체결) TR을 사용하며, 호가(GSH) 데이터는 포함되지 않습니다.
    거래소: NYSE, NASDAQ, AMEX
    """

    type: Literal["OverseasStockRealMarketDataNode"] = "OverseasStockRealMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasStockRealMarketDataNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Stream real-time US stock tick data (GSC trade events) via WebSocket for live intraday strategies",
            "Feed live price updates into ConditionNode for continuous signal evaluation without polling REST endpoints",
            "Use stay_connected=True to maintain the WebSocket subscription across multiple workflow execution cycles",
        ],
        "when_not_to_use": [
            "For overseas futures real-time data — use OverseasFuturesRealMarketDataNode",
            "For Korean domestic real-time stock data — use KoreaStockRealMarketDataNode",
            "When polling historical bars is sufficient — use OverseasStockHistoricalDataNode to avoid WebSocket overhead",
            "Directly connected to an order or AI node without ThrottleNode — every tick will trigger downstream execution",
        ],
        "typical_scenarios": [
            "OverseasStockRealMarketDataNode → ThrottleNode → ConditionNode → OverseasStockNewOrderNode (tick-driven strategy)",
            "OverseasStockRealMarketDataNode → ThrottleNode → AIAgentNode (periodic AI analysis on live data)",
            "OverseasStockRealMarketDataNode → CandlestickChartNode (live chart display)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Streams GSC (trade/tick) events from LS Securities WebSocket — ohlcv_data port emits aggregated candles; data port emits raw tick dicts",
        "stay_connected=True keeps the WebSocket subscription live between cycles (recommended for realtime strategies)",
        "Item-based execution: one subscription per node; use multiple nodes or SplitNode to watch several symbols",
        "Automatically re-subscribes after WebSocket reconnection events",
        "Does NOT include order book (bid/ask levels) — only trade (GSC) events; ask/bid from GSH are in the data port",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Wiring OverseasStockRealMarketDataNode directly to OverseasStockNewOrderNode without ThrottleNode",
            "reason": "Every incoming tick triggers an order attempt. The executor's rate-limit guard will raise a connection error at validation time.",
            "alternative": "Insert ThrottleNode between the realtime source and any order or AI node to control the firing rate.",
        },
        {
            "pattern": "Setting stay_connected=False in a long-running realtime strategy",
            "reason": "With stay_connected=False, the WebSocket is closed after each cycle, causing reconnection overhead on every execution.",
            "alternative": "Leave stay_connected=True (default) for continuous realtime strategies.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Live tick stream with ThrottleNode and condition check",
            "description": "Subscribe to AAPL ticks via WebSocket, throttle to 60-second intervals, then evaluate a price condition.",
            "workflow_snippet": {
                "id": "overseas_stock_real_market_data_throttle",
                "name": "Live Tick Strategy",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
                    {"id": "real", "type": "OverseasStockRealMarketDataNode", "symbol": "{{ nodes.split.item }}", "stay_connected": True},
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
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "ohlcv_data port: {symbol, exchange, open, high, low, close, volume} aggregated candle per tick batch. Throttled to once per 60 seconds downstream.",
        },
        {
            "title": "Live candlestick chart display",
            "description": "Stream real-time MSFT ticks and render a live candlestick chart.",
            "workflow_snippet": {
                "id": "overseas_stock_real_market_data_chart",
                "name": "Live Chart",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "MSFT", "exchange": "NASDAQ"}]},
                    {"id": "real", "type": "OverseasStockRealMarketDataNode", "symbol": "{{ nodes.split.item }}", "stay_connected": True},
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
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "ohlcv_data is rendered in CandlestickChartNode as a live chart that updates on each tick.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `symbol` field takes a single {exchange, symbol} dict — bind to `{{ nodes.split.item }}` when setting up per-symbol subscriptions. "
            "Supported exchanges: NASDAQ, NYSE, AMEX. "
            "Set stay_connected=True (default) to avoid reconnection overhead on every cycle."
        ),
        "output_consumption": (
            "The `ohlcv_data` port emits aggregated candle dicts: {symbol, exchange, open, high, low, close, volume}. "
            "The `data` port emits the raw full tick dict including bid/ask fields. "
            "ALWAYS insert ThrottleNode before any order or AI node downstream."
        ),
        "common_combinations": [
            "OverseasStockRealMarketDataNode → ThrottleNode → ConditionNode → OverseasStockNewOrderNode (live trading)",
            "OverseasStockRealMarketDataNode → CandlestickChartNode (live chart)",
            "OverseasStockRealMarketDataNode → ThrottleNode → AIAgentNode (periodic live analysis)",
        ],
        "pitfalls": [
            "Never connect directly to an order or AI node — always insert ThrottleNode to prevent every-tick execution",
            "stay_connected=False will reconnect on every cycle — use True for realtime strategies",
            "GSC events are trade events only; full order book depth is not available via this node",
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
                display_name="i18n:fieldNames.OverseasStockRealMarketDataNode.symbol",
                description="i18n:fields.OverseasStockRealMarketDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"exchange": "NASDAQ", "symbol": "AAPL"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{exchange: str, symbol: str}",
                help_text="i18n:fields.OverseasStockRealMarketDataNode.symbol.help_text",
                object_schema=[
                    {"name": "exchange", "type": "STRING", "label": "i18n:fields.OverseasStockRealMarketDataNode.symbol.exchange", "required": True},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasStockRealMarketDataNode.symbol.symbol", "required": True},
                ],
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
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Maintain a continuously updated view of overseas stock held positions, balance, and open orders via WebSocket",
            "Feed live position data into realtime strategy nodes for trailing stop or risk management",
            "Prefer over OverseasStockAccountNode when the workflow is a long-running realtime loop",
        ],
        "when_not_to_use": [
            "For one-shot scheduled queries — use the lighter OverseasStockAccountNode (REST, no WebSocket overhead)",
            "For overseas futures realtime account — use OverseasFuturesRealAccountNode",
            "For Korea stock realtime account — use KoreaStockRealAccountNode",
        ],
        "typical_scenarios": [
            "Start → OverseasStockBrokerNode → OverseasStockRealAccountNode → ThrottleNode → ConditionNode (realtime trailing stop)",
            "OverseasStockRealAccountNode.positions → PortfolioNode (live risk aggregation)",
            "OverseasStockRealAccountNode.held_symbols → OverseasStockRealMarketDataNode (realtime mark-to-market)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Provides four output ports: held_symbols, balance (with real-time P&L), open_orders, and positions updated via WebSocket",
        "Configurable commission_rate and tax_rate for accurate net P&L calculation per position",
        "stay_connected=True keeps the WebSocket alive across execution cycles; sync_interval_sec controls REST REST-sync frequency",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Connecting OverseasStockRealAccountNode directly to heavy compute nodes without ThrottleNode",
            "reason": "Each WebSocket tick triggers downstream execution; without throttling the condition/order nodes run at tick frequency and can exhaust API limits.",
            "alternative": "Insert a ThrottleNode (e.g., interval_sec=5, mode=latest) between RealAccountNode and any downstream logic node.",
        },
        {
            "pattern": "Using the positions port to drive per-symbol ordering without auto-iterate awareness",
            "reason": "positions is an array; downstream order nodes auto-iterate per item, which can create duplicate orders for every position on each tick.",
            "alternative": "Filter positions via FieldMappingNode or ConditionNode first; ensure only the target position triggers the order path.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Realtime account monitor with throttle",
            "description": "Subscribe to live overseas stock account updates and display balance every 10 seconds.",
            "workflow_snippet": {
                "id": "stock-real-account-display",
                "name": "Realtime Stock Account Monitor",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "real_account", "type": "OverseasStockRealAccountNode", "stay_connected": True, "commission_rate": 0.25},
                    {"id": "throttle", "type": "ThrottleNode", "mode": "latest", "interval_sec": 10, "pass_first": True},
                    {"id": "display", "type": "TableDisplayNode", "title": "Live Positions", "data": "{{ nodes.throttle.data }}"},
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
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "Throttled every 10s: positions list with live P&L, balance with total equity and orderable cash.",
        },
        {
            "title": "Realtime trailing stop using live positions",
            "description": "Feed live positions into a ConditionNode to trigger a stop-loss order when drawdown exceeds threshold.",
            "workflow_snippet": {
                "id": "stock-real-account-trailing-stop",
                "name": "Realtime Trailing Stop",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "real_account", "type": "OverseasStockRealAccountNode", "stay_connected": True},
                    {"id": "throttle", "type": "ThrottleNode", "mode": "latest", "interval_sec": 5, "pass_first": True},
                    {"id": "condition", "type": "ConditionNode", "plugin": "StopLoss", "data": "{{ nodes.throttle.data }}"},
                    {"id": "order", "type": "OverseasStockNewOrderNode", "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}", "side": "sell", "order_type": "market", "quantity": "{{ item.quantity }}"},
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
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "When StopLoss plugin signals a stop, NewOrderNode fires a market sell for each affected position.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "No input ports. Broker connection is auto-injected by the executor from the upstream OverseasStockBrokerNode. Configure commission_rate and tax_rate to match your LS account plan.",
        "output_consumption": "Four ports: held_symbols (array), balance (object), open_orders (array), positions (array). All array ports auto-iterate downstream; insert ThrottleNode before strategy logic to control frequency.",
        "common_combinations": [
            "OverseasStockRealAccountNode → ThrottleNode → ConditionNode (realtime strategy gate)",
            "OverseasStockRealAccountNode.positions → PortfolioNode (risk aggregation)",
            "OverseasStockRealAccountNode.held_symbols → SplitNode → OverseasStockRealMarketDataNode",
        ],
        "pitfalls": [
            "Without ThrottleNode every WebSocket tick triggers the full downstream DAG — always throttle before heavy nodes",
            "commission_rate and tax_rate default to LS standard rates; verify these match your actual account settings for accurate P&L",
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
        OutputPort(name="balance", type="balance_data", description="i18n:ports.balance", fields=OVERSEAS_STOCK_REAL_BALANCE_FIELDS),
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
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "React immediately to fill events (AS1) to update internal P&L tracking or trigger follow-up orders",
            "Monitor order acceptance (AS0) or rejection (AS4) to handle broker error recovery logic",
            "Build event-driven workflows that respond to order state transitions without polling",
        ],
        "when_not_to_use": [
            "For a one-shot snapshot of current open orders — use OverseasStockOpenOrdersNode (REST)",
            "For overseas futures order events — use OverseasFuturesRealOrderEventNode",
            "For Korea domestic stock order events — use KoreaStockRealOrderEventNode",
        ],
        "typical_scenarios": [
            "OverseasStockRealOrderEventNode.filled → FieldMappingNode → TableDisplayNode (fill confirmation log)",
            "OverseasStockRealOrderEventNode.rejected → TelegramNode (rejection alert)",
            "OverseasStockRealOrderEventNode.filled → ConditionNode (verify fill then place hedge)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Emits five event ports: accepted, filled, modified, cancelled, rejected — each fires independently on its corresponding broker event",
        "event_filter field lets you subscribe to a specific AS code (AS0–AS4) or all events at once",
        "Runs persistently with stay_connected=True; no polling — events arrive via WebSocket push",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Placing an order node directly on the `filled` port without checking symbol match",
            "reason": "All fills for any order fire on the `filled` port; wiring a new order directly can create an unintended chain of orders for every fill.",
            "alternative": "Add a ConditionNode or IfNode on the filled port that checks `item.symbol == target_symbol` before placing the follow-up order.",
        },
        {
            "pattern": "Using OverseasStockRealOrderEventNode without an upstream broker in the DAG",
            "reason": "The node subscribes to the account-level WebSocket stream which requires an authenticated LS session from the broker node.",
            "alternative": "Always wire OverseasStockBrokerNode → OverseasStockRealOrderEventNode via a main edge.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Fill event display",
            "description": "Subscribe to fill events and display each confirmed trade in a table.",
            "workflow_snippet": {
                "id": "stock-real-order-event-display",
                "name": "Stock Fill Event Display",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "order_event", "type": "OverseasStockRealOrderEventNode", "event_filter": "AS1", "stay_connected": True},
                    {"id": "display", "type": "TableDisplayNode", "title": "Fill Events", "data": "{{ nodes.order_event.filled }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "order_event"},
                    {"from": "order_event", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "On each fill: filled port emits {order_id, symbol, exchange, side, quantity, price, fill_time}; TableDisplayNode logs the event.",
        },
        {
            "title": "Rejection alert via Telegram",
            "description": "Send a Telegram notification whenever an overseas stock order is rejected.",
            "workflow_snippet": {
                "id": "stock-order-rejection-alert",
                "name": "Stock Order Rejection Alert",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "order_event", "type": "OverseasStockRealOrderEventNode", "event_filter": "AS4", "stay_connected": True},
                    {"id": "telegram", "type": "TelegramNode", "credential_id": "tg_cred", "message": "Order rejected: {{ nodes.order_event.rejected.symbol }} {{ nodes.order_event.rejected.order_id }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "order_event"},
                    {"from": "order_event", "to": "telegram"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
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
            "expected_output": "On each AS4 rejection event: TelegramNode sends the order rejection message with symbol and order_id.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "No input ports. Broker connection is auto-injected by the executor. Set event_filter to a specific AS code to receive only one event type, or 'all' for every transition.",
        "output_consumption": "Five ports (accepted, filled, modified, cancelled, rejected) each fire independently when the corresponding broker event arrives. Wire each port to its own downstream node chain as needed.",
        "common_combinations": [
            "OverseasStockRealOrderEventNode.filled → FieldMappingNode → TableDisplayNode",
            "OverseasStockRealOrderEventNode.rejected → TelegramNode (alert)",
            "OverseasStockRealOrderEventNode.filled → ConditionNode (PnL check) → follow-up order",
        ],
        "pitfalls": [
            "All five ports are independent — connecting multiple ports to the same heavy downstream chain may cause concurrent executions per fill",
            "event_filter='all' is the default but can produce noise; scope to a specific AS code when only one event type is relevant",
        ],
    }

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
