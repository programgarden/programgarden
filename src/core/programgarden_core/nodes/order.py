"""
ProgramGarden Core - Order Nodes

상품별 주문 노드 (해외주식 3개 + 해외선물 3개 + 국내주식 3개 = 총 9개):
- OverseasStockNewOrderNode, OverseasStockModifyOrderNode, OverseasStockCancelOrderNode (해외주식)
- OverseasFuturesNewOrderNode, OverseasFuturesModifyOrderNode, OverseasFuturesCancelOrderNode (해외선물)
- KoreaStockNewOrderNode, KoreaStockModifyOrderNode, KoreaStockCancelOrderNode (국내주식)

입력 구조:
- NewOrder: orders 배열 [{symbol, exchange, quantity, price}, ...]
- Modify/Cancel: original_order_id, symbol, exchange 단일 필드
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar, TYPE_CHECKING
import logging
from pydantic import Field, model_validator

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    ProductScope,
    BrokerProvider,
    ORDER_LIST_FIELDS,
    ORDER_RESULT_FIELDS,
    SYMBOL_LIST_FIELDS,
    RetryableError,
)
from programgarden_core.models.resilience import (
    ResilienceConfig,
    RetryConfig,
    FallbackConfig,
    FallbackMode,
)
from programgarden_core.models.connection_rule import (
    ConnectionRule,
    ConnectionSeverity,
    RateLimitConfig,
    REALTIME_SOURCE_NODE_TYPES,
)


# =============================================================================
# 베이스 클래스
# =============================================================================

class BaseOrderNode(BaseNode):
    """
    주문 노드 공통 베이스 클래스 (단일 주문)

    Item-based execution:
    - Input: order (단일 주문 {symbol, exchange, quantity, price})
    - Output: result (해당 주문의 결과)

    주문 노드는 중복 주문 위험으로 인해 기본적으로 재시도가 비활성화됩니다.
    네트워크 에러(주문이 서버에 도달하기 전 실패)만 재시도 허용.
    """

    category: NodeCategory = NodeCategory.ORDER

    # 실시간 노드에서 직접 연결 차단 (ThrottleNode 경유 필수)
    _connection_rules: ClassVar[List[ConnectionRule]] = [
        ConnectionRule(
            deny_direct_from=REALTIME_SOURCE_NODE_TYPES,
            required_intermediate="ThrottleNode",
            severity=ConnectionSeverity.ERROR,
            reason="i18n:connection_rules.realtime_to_order.reason",
            suggestion="i18n:connection_rules.realtime_to_order.suggestion",
        ),
    ]

    # 런타임 rate limit: 최소 5초 간격, 동시 실행 1개 (중복 주문 방지)
    _rate_limit: ClassVar[Optional[RateLimitConfig]] = RateLimitConfig(
        min_interval_sec=5,
        max_concurrent=1,
        on_throttle="skip",
    )

    # 브로커 연결 (필수)
    connection: Optional[Dict] = Field(
        default=None,
        description="브로커 연결 정보 (BrokerNode.connection 바인딩)",
    )

    # 공통 주문 설정
    side: Literal["buy", "sell"] = Field(
        default="buy",
        description="매매 구분 (buy: 매수, sell: 매도)",
    )
    order_type: Literal["market", "limit"] = Field(
        default="limit",
        description="주문 유형 (market: 시장가, limit: 지정가)",
    )

    # 단일 주문 입력 (Item-based execution)
    order: Any = Field(
        default=None,
        description="단일 주문 {symbol, exchange, quantity, price}",
    )

    # Resilience: 주문 노드는 기본적으로 재시도 비활성화 (중복 주문 위험)
    resilience: ResilienceConfig = Field(
        default_factory=lambda: ResilienceConfig(
            retry=RetryConfig(
                enabled=False,
                retry_on=[RetryableError.NETWORK_ERROR],  # 네트워크 에러만 허용
            ),
            fallback=FallbackConfig(mode=FallbackMode.ERROR),
        ),
        description="재시도 및 실패 처리 설정 (주문 노드는 기본 비활성화)",
    )

    @model_validator(mode="after")
    def _clamp_order_retry(self) -> "BaseOrderNode":
        """주문 노드의 retry 횟수를 3 이하로 강제 (M-1: 중복 주문 위험 방지)."""
        _MAX_ORDER_RETRIES = 3
        if self.resilience.retry.enabled and self.resilience.retry.max_retries > _MAX_ORDER_RETRIES:
            logging.getLogger("programgarden_core.order").warning(
                f"주문 노드 max_retries={self.resilience.retry.max_retries} → "
                f"{_MAX_ORDER_RETRIES}으로 제한 (중복 주문 위험 방지)"
            )
            self.resilience.retry.max_retries = _MAX_ORDER_RETRIES
        return self

    def is_retryable_error(self, error: Exception) -> Optional[RetryableError]:
        """
        주문 에러가 재시도 가능한지 판단.

        주문 노드는 네트워크 에러(연결 실패)만 재시도 허용.
        주문이 서버에 도달했는지 확인 불가한 경우 재시도 금지.

        Args:
            error: 발생한 예외

        Returns:
            RetryableError 유형, 또는 None (재시도 불가)
        """
        error_str = str(error).lower()

        # 네트워크 연결 실패 (주문이 서버에 도달하기 전 실패)만 재시도 허용
        if "connection refused" in error_str or "connection reset" in error_str:
            return RetryableError.NETWORK_ERROR

        # 그 외 모든 에러는 재시도 불가 (중복 주문 방지)
        return None

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.order_trigger",
        ),
        InputPort(
            name="order",
            type="order",
            description="i18n:ports.order_input",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="order_result",
            description="i18n:ports.order_result",
            fields=ORDER_RESULT_FIELDS,
            example=[
                {
                    "order_id": "250414-00123",
                    "exchange": "NASDAQ",
                    "symbol": "AAPL",
                    "side": "buy",
                    "quantity": 10,
                    "price": 187.45,
                    "status": "accepted",
                },
            ],
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            "rate_limit_interval": FieldSchema(
                name="rate_limit_interval",
                type=FieldType.NUMBER,
                description="i18n:fields.BaseOrderNode.rate_limit_interval",
                default=5,
                min=1,
                max=300,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=5,
            ),
            "rate_limit_action": FieldSchema(
                name="rate_limit_action",
                type=FieldType.ENUM,
                description="i18n:fields.BaseOrderNode.rate_limit_action",
                default="skip",
                enum_values=["skip", "error"],
                enum_labels={
                    "skip": "i18n:enums.rate_limit_action.skip",
                    "error": "i18n:enums.rate_limit_action.error",
                },
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="skip",
            ),
        }


class BaseModifyOrderNode(BaseNode):
    """
    정정/취소 주문 노드 공통 베이스 클래스

    주문 노드는 중복 처리 위험으로 인해 기본적으로 재시도가 비활성화됩니다.
    """

    category: NodeCategory = NodeCategory.ORDER

    # 실시간 노드에서 직접 연결 차단 (ThrottleNode 경유 필수)
    _connection_rules: ClassVar[List[ConnectionRule]] = [
        ConnectionRule(
            deny_direct_from=REALTIME_SOURCE_NODE_TYPES,
            required_intermediate="ThrottleNode",
            severity=ConnectionSeverity.ERROR,
            reason="i18n:connection_rules.realtime_to_order.reason",
            suggestion="i18n:connection_rules.realtime_to_order.suggestion",
        ),
    ]

    # 런타임 rate limit: 최소 5초 간격, 동시 실행 1개 (중복 정정/취소 방지)
    _rate_limit: ClassVar[Optional[RateLimitConfig]] = RateLimitConfig(
        min_interval_sec=5,
        max_concurrent=1,
        on_throttle="skip",
    )

    # 브로커 연결 (필수)
    connection: Optional[Dict] = Field(
        default=None,
        description="브로커 연결 정보 (BrokerNode.connection 바인딩)",
    )

    # 정정/취소 대상
    original_order_id: Any = Field(
        default=None,
        description="정정/취소할 원주문번호",
    )
    symbol: Any = Field(
        default=None,
        description="종목 코드",
    )
    exchange: Any = Field(
        default=None,
        description="거래소 코드",
    )

    # Resilience: 정정/취소 노드도 기본적으로 재시도 비활성화
    resilience: ResilienceConfig = Field(
        default_factory=lambda: ResilienceConfig(
            retry=RetryConfig(
                enabled=False,
                retry_on=[RetryableError.NETWORK_ERROR],
            ),
            fallback=FallbackConfig(mode=FallbackMode.ERROR),
        ),
        description="재시도 및 실패 처리 설정 (정정/취소 노드는 기본 비활성화)",
    )

    @model_validator(mode="after")
    def _clamp_order_retry(self) -> "BaseModifyOrderNode":
        """정정/취소 노드의 retry 횟수를 3 이하로 강제 (M-1)."""
        _MAX_ORDER_RETRIES = 3
        if self.resilience.retry.enabled and self.resilience.retry.max_retries > _MAX_ORDER_RETRIES:
            logging.getLogger("programgarden_core.order").warning(
                f"정정/취소 노드 max_retries={self.resilience.retry.max_retries} → "
                f"{_MAX_ORDER_RETRIES}으로 제한 (중복 처리 위험 방지)"
            )
            self.resilience.retry.max_retries = _MAX_ORDER_RETRIES
        return self

    def is_retryable_error(self, error: Exception) -> Optional[RetryableError]:
        """정정/취소 에러가 재시도 가능한지 판단."""
        error_str = str(error).lower()

        if "connection refused" in error_str or "connection reset" in error_str:
            return RetryableError.NETWORK_ERROR

        return None

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            "rate_limit_interval": FieldSchema(
                name="rate_limit_interval",
                type=FieldType.NUMBER,
                description="i18n:fields.BaseOrderNode.rate_limit_interval",
                default=5,
                min=1,
                max=300,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=5,
            ),
            "rate_limit_action": FieldSchema(
                name="rate_limit_action",
                type=FieldType.ENUM,
                description="i18n:fields.BaseOrderNode.rate_limit_action",
                default="skip",
                enum_values=["skip", "error"],
                enum_labels={
                    "skip": "i18n:enums.rate_limit_action.skip",
                    "error": "i18n:enums.rate_limit_action.error",
                },
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="skip",
            ),
        }


# =============================================================================
# 해외주식 주문 노드
# =============================================================================

class OverseasStockNewOrderNode(BaseOrderNode):
    """
    해외주식 신규주문 노드

    미국 주식(NYSE, NASDAQ, AMEX) 신규주문을 실행합니다.
    orders 필드에 주문할 종목 목록을 바인딩하세요.

    API: COSAT00301 (해외주식 신규주문)
    """

    type: Literal["OverseasStockNewOrderNode"] = "OverseasStockNewOrderNode"
    description: str = "i18n:nodes.OverseasStockNewOrderNode.description"

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Place a new buy or sell order for a US-listed stock (NYSE, NASDAQ, AMEX)",
            "Execute a signal-driven order after a ConditionNode or PositionSizingNode resolves the target symbol and quantity",
            "Auto-iterate over an array of signals to place multiple orders in sequence",
        ],
        "when_not_to_use": [
            "For overseas futures orders — use OverseasFuturesNewOrderNode",
            "For Korean domestic stocks — use KoreaStockNewOrderNode",
            "When no upstream OverseasStockBrokerNode is present — connection auto-injection will fail",
            "In paper-trading mode without setting paper_trading=false on the broker node — real orders require a live session",
        ],
        "typical_scenarios": [
            "ConditionNode.result → PositionSizingNode → OverseasStockNewOrderNode (signal-driven buy)",
            "OverseasStockAccountNode.held_symbols → ConditionNode (stop-loss) → OverseasStockNewOrderNode (sell)",
            "ScreenerNode.symbols → SplitNode → PositionSizingNode → OverseasStockNewOrderNode (basket order)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Executes a single limit or market order per node execution; use auto-iterate for batch orders from an upstream array",
        "Built-in rate-limit guard: minimum 5-second interval, max 1 concurrent execution to prevent accidental duplicate orders",
        "Supports extended price_type options: LOO, LOC, MOO, MOC for open/close auction orders",
        "is_tool_enabled=True — AI Agent can call this node as a tool to place orders autonomously",
        "retry is disabled by default (resilience.retry.enabled=False); only pure network-connection failures may be retried, never a submitted order",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Hard-coding quantity as a fixed integer instead of routing through PositionSizingNode",
            "reason": "Fixed quantities ignore available cash, volatility, and risk limits, leading to oversized or undersized positions.",
            "alternative": "Connect PositionSizingNode upstream and bind `order` to `{{ nodes.positionSizing.order }}` to get a risk-adjusted quantity.",
        },
        {
            "pattern": "Enabling retry on order nodes (resilience.retry.enabled=True) without understanding idempotency",
            "reason": "If the order reached the exchange before the network error, retrying will place a duplicate order. The default is disabled for this reason.",
            "alternative": "Leave retry disabled. If you need retry, only enable it for RetryableError.NETWORK_ERROR and verify server-side idempotency keys.",
        },
        {
            "pattern": "Connecting a realtime node (e.g. OverseasStockRealMarketDataNode) directly to OverseasStockNewOrderNode without ThrottleNode",
            "reason": "Every tick would trigger an order attempt; rate-limit rules block this and raise a connection error at validation time.",
            "alternative": "Insert a ThrottleNode between the realtime source and the order node to control firing rate.",
        },
        {
            "pattern": "Using a dict-keyed positions object {symbol: {...}} from a RealAccountNode output as order input",
            "reason": "All position outputs in ProgramGarden are list[dict] with `symbol`/`exchange` keys. Dict-keyed access will fail at runtime.",
            "alternative": "Bind `{{ item.symbol }}` when auto-iterating over the positions list, or use FieldMappingNode to reshape data.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Signal-driven buy order via PositionSizingNode",
            "description": "RSI oversold signal triggers PositionSizingNode to compute the order size, then OverseasStockNewOrderNode places the buy.",
            "workflow_snippet": {
                "id": "overseas_stock_new_order_rsi_buy",
                "name": "RSI Buy Order",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "fields": ["price"]},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "period": "1d", "count": 20},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.ohlcv }}", "period": 14, "oversold_threshold": 30},
                    {"id": "sizing", "type": "PositionSizingNode", "method": "fixed_percent", "max_percent": 5, "balance": "{{ nodes.account.balance }}", "price": "{{ nodes.market.price }}", "symbol": {"symbol": "AAPL", "exchange": "NASDAQ"}},
                    {"id": "order", "type": "OverseasStockNewOrderNode", "side": "buy", "order_type": "limit", "order": "{{ nodes.sizing.order }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "broker", "to": "market"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "sizing"},
                    {"from": "account", "to": "sizing"},
                    {"from": "market", "to": "sizing"},
                    {"from": "sizing", "to": "order"},
                    {"from": "broker", "to": "order"},
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
            "expected_output": "result port: {order_id, symbol, exchange, side, quantity, price, status} — the accepted order confirmation from LS Securities.",
        },
        {
            "title": "Basket sell order — auto-iterate over positions array",
            "description": "Fetch held positions and auto-iterate to place a sell order for every position above a profit threshold.",
            "workflow_snippet": {
                "id": "overseas_stock_basket_sell",
                "name": "Basket Sell",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "order", "type": "OverseasStockNewOrderNode", "side": "sell", "order_type": "market", "order": "{{ item }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "order"},
                    {"from": "broker", "to": "order"},
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
            "expected_output": "result port emitted once per position: {order_id, symbol, exchange, side, quantity, status}.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `order` field must be a dict with keys {symbol, exchange, quantity, price?}. "
            "Bind it from PositionSizingNode.order for risk-adjusted sizing. "
            "The `side` field ('buy'/'sell') and `order_type` ('limit'/'market') are fixed at node config time — not per-order. "
            "The `price_type` field adds special auction types (LOO/LOC/MOO/MOC); for regular hours use 'limit' or 'market'. "
            "The broker connection is auto-injected via DAG traversal — no explicit connection binding is needed."
        ),
        "output_consumption": (
            "The `result` port emits a single order-confirmation dict: {order_id, symbol, exchange, side, quantity, price, status}. "
            "Pass order_id downstream to ModifyOrderNode or CancelOrderNode if you need to amend the order. "
            "Wire to TableDisplayNode to log order history."
        ),
        "common_combinations": [
            "PositionSizingNode.order → OverseasStockNewOrderNode (standard signal-driven order)",
            "OverseasStockNewOrderNode.result.order_id → OverseasStockCancelOrderNode (order lifecycle management)",
            "ConditionNode.result → OverseasStockNewOrderNode (direct condition-triggered order without sizing)",
            "OverseasStockNewOrderNode.result → TableDisplayNode (order audit log)",
        ],
        "pitfalls": [
            "price_type='LOO'/'MOO' require a market order sent before open — submitting them during regular hours may be rejected by the exchange",
            "The rate-limit guard (min 5s interval) will skip duplicate executions silently if on_throttle='skip'; set on_throttle='error' during testing to surface issues",
            "paper_trading=True on the broker node will NOT route to a real order API — always set paper_trading=False for live trading",
            "Retry is disabled by default on all order nodes to prevent duplicate orders — do not enable unless you understand the idempotency implications",
        ],
    }

    # 해외주식 전용 필드
    price_type: Literal["limit", "market", "LOO", "LOC", "MOO", "MOC"] = Field(
        default="limit",
        description="호가 유형 (limit, market, LOO, LOC, MOO, MOC)",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        )
        return {
            **super().get_field_schema(),
            "side": FieldSchema(
                name="side",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockNewOrderNode.side",
                default="buy",
                enum_values=["buy", "sell"],
                enum_labels={
                    "buy": "i18n:enums.side.buy",
                    "sell": "i18n:enums.side.sell",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
                example="buy",
            ),
            "order_type": FieldSchema(
                name="order_type",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockNewOrderNode.order_type",
                default="limit",
                enum_values=["market", "limit"],
                enum_labels={
                    "market": "i18n:enums.order_type.market",
                    "limit": "i18n:enums.order_type.limit",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
                example="limit",
            ),
            "price_type": FieldSchema(
                name="price_type",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockNewOrderNode.price_type",
                default="limit",
                enum_values=["limit", "market", "LOO", "LOC", "MOO", "MOC"],
                enum_labels={
                    "limit": "i18n:enums.price_type.limit",
                    "market": "i18n:enums.price_type.market",
                    "LOO": "i18n:enums.price_type.LOO",
                    "LOC": "i18n:enums.price_type.LOC",
                    "MOO": "i18n:enums.price_type.MOO",
                    "MOC": "i18n:enums.price_type.MOC",
                },
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
                example="limit",
            ),
            "order": FieldSchema(
                name="order",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.OverseasStockNewOrderNode.order",
                description="i18n:fields.OverseasStockNewOrderNode.order",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 10, "price": 150.0},
                example_binding="{{ nodes.positionSizing.order }}",
                bindable_sources=[
                    "PositionSizingNode.order",
                ],
                object_schema=[
                    {"name": "symbol", "type": "STRING", "required": True,
                     "label": "i18n:fields.order.symbol"},
                    {"name": "exchange", "type": "STRING", "required": True,
                     "label": "i18n:fields.order.exchange"},
                    {"name": "quantity", "type": "INTEGER", "required": True,
                     "label": "i18n:fields.order.quantity"},
                    {"name": "price", "type": "NUMBER", "required": False,
                     "label": "i18n:fields.order.price"},
                ],
                expected_type="{symbol: str, exchange: str, quantity: int, price?: float}",
                help_text="i18n:fields.OverseasStockNewOrderNode.order.help_text",
            ),
        }


class OverseasStockModifyOrderNode(BaseModifyOrderNode):
    """
    해외주식 정정주문 노드

    기존 미체결 주문의 가격이나 수량을 정정합니다.

    API: COSAT00302 (해외주식 정정주문)
    """

    type: Literal["OverseasStockModifyOrderNode"] = "OverseasStockModifyOrderNode"
    description: str = "i18n:nodes.OverseasStockModifyOrderNode.description"

    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Change the price or quantity of an existing unfilled overseas stock order",
            "Chase a moving price by repricing a limit order without cancelling and resubmitting",
            "Partially reduce an open order's quantity to lower exposure",
        ],
        "when_not_to_use": [
            "When the order has already been fully filled — modification will be rejected by the exchange",
            "When you want to fully cancel an order — use OverseasStockCancelOrderNode instead",
            "For futures orders — use OverseasFuturesModifyOrderNode",
        ],
        "typical_scenarios": [
            "OverseasStockOpenOrdersNode.orders → OverseasStockModifyOrderNode (reprice all open orders)",
            "OverseasStockRealOrderEventNode (partial fill event) → OverseasStockModifyOrderNode (adjust remaining quantity)",
            "IfNode (price moved away) → OverseasStockModifyOrderNode (reprice limit order)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Modifies price and/or quantity of a single open order identified by original_order_id + symbol + exchange",
        "Retry disabled by default (same safety rationale as new-order nodes — a duplicate modify can cause unintended fills)",
        "Rate-limited to 1 concurrent execution with 5-second minimum interval to prevent rapid repeated modifications",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Hard-coding original_order_id as a static string",
            "reason": "Order IDs are generated at runtime by the broker; a static ID becomes stale instantly and will fail.",
            "alternative": "Bind original_order_id from OverseasStockOpenOrdersNode.orders[].order_id or OverseasStockNewOrderNode.result.order_id.",
        },
        {
            "pattern": "Enabling retry on modify nodes without idempotency guarantees",
            "reason": "A successful modify that returns a transient error on response will be retried, potentially applying the price change twice.",
            "alternative": "Leave resilience.retry.enabled=False (default). Query OverseasStockOpenOrdersNode after a failure to confirm the current state.",
        },
        {
            "pattern": "Connecting a realtime data node directly to OverseasStockModifyOrderNode without ThrottleNode",
            "reason": "Every tick would fire a modify request, hitting rate limits immediately and causing order rejections.",
            "alternative": "Insert a ThrottleNode between the realtime source and the modify node.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Reprice an open limit order from open-orders list",
            "description": "Fetch all open orders and modify the price of the first one to a new target price.",
            "workflow_snippet": {
                "id": "overseas_stock_modify_order_reprice",
                "name": "Reprice Open Order",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "open_orders", "type": "OverseasStockOpenOrdersNode"},
                    {"id": "modify", "type": "OverseasStockModifyOrderNode",
                     "original_order_id": "{{ item.order_id }}",
                     "symbol": "{{ item.symbol }}",
                     "exchange": "{{ item.exchange }}",
                     "new_price": 185.0},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "modify"},
                    {"from": "broker", "to": "modify"},
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
            "expected_output": "modify_result port: {order_id, symbol, exchange, status, new_price}; modified_order_id port: the updated order ID string.",
        },
        {
            "title": "Adjust order quantity on partial fill event",
            "description": "Listen for a partial fill via RealOrderEventNode and reduce the remaining open quantity.",
            "workflow_snippet": {
                "id": "overseas_stock_modify_order_partial_fill",
                "name": "Partial Fill Quantity Adjust",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "real_event", "type": "OverseasStockRealOrderEventNode"},
                    {"id": "throttle", "type": "ThrottleNode", "interval_sec": 10},
                    {"id": "modify", "type": "OverseasStockModifyOrderNode",
                     "original_order_id": "{{ nodes.real_event.order_id }}",
                     "symbol": "{{ nodes.real_event.symbol }}",
                     "exchange": "{{ nodes.real_event.exchange }}",
                     "new_quantity": 5},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "real_event"},
                    {"from": "real_event", "to": "throttle"},
                    {"from": "throttle", "to": "modify"},
                    {"from": "broker", "to": "modify"},
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
            "expected_output": "modify_result port emitted with updated quantity; modified_order_id port contains the new order ID.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "Requires three fields: `original_order_id` (string, the order to modify), `symbol` (ticker string), and `exchange` ('NYSE'/'NASDAQ'/'AMEX'). "
            "Optionally provide `new_price` (float) and/or `new_quantity` (int) — omitting a field keeps the original value. "
            "Bind original_order_id from upstream OpenOrdersNode or from a NewOrderNode result. "
            "The broker connection is auto-injected via DAG traversal."
        ),
        "output_consumption": (
            "Two ports: `modify_result` (full order confirmation dict) and `modified_order_id` (string). "
            "Pass modified_order_id to a subsequent CancelOrderNode if you need to cancel after a failed modify."
        ),
        "common_combinations": [
            "OverseasStockOpenOrdersNode → OverseasStockModifyOrderNode (reprice all open orders)",
            "OverseasStockRealOrderEventNode → ThrottleNode → OverseasStockModifyOrderNode (event-driven reprice)",
            "OverseasStockModifyOrderNode.modified_order_id → OverseasStockCancelOrderNode (cancel if modify fails)",
        ],
        "pitfalls": [
            "Cannot modify a fully filled order — query OpenOrdersNode first to verify the order is still open",
            "Omitting both new_price and new_quantity makes the call a no-op (the broker may return an error)",
            "The 5-second rate-limit guard applies — rapid sequential modifications will be silently skipped",
        ],
    }

    # 해외주식 전용 필드
    price_type: Literal["limit", "market"] = Field(
        default="limit",
        description="호가 유형",
    )

    # 정정 대상
    new_quantity: Optional[int] = Field(
        default=None,
        description="정정할 수량 (변경하지 않으면 기존 수량 유지)",
    )
    new_price: Optional[float] = Field(
        default=None,
        description="정정할 가격 (변경하지 않으면 기존 가격 유지)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.modify_trigger",
        ),
        InputPort(
            name="original_order_id",
            type="string",
            description="i18n:ports.original_order_id",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="modify_result",
            type="order_result",
            description="i18n:ports.modify_result",
            fields=ORDER_RESULT_FIELDS,
        ),
        OutputPort(
            name="modified_order_id",
            type="string",
            description="i18n:ports.modified_order_id",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            **super().get_field_schema(),
            "price_type": FieldSchema(
                name="price_type",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockModifyOrderNode.price_type",
                default="limit",
                enum_values=["limit", "market"],
                enum_labels={
                    "limit": "i18n:enums.order_type.limit",
                    "market": "i18n:enums.order_type.market",
                },
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
            "original_order_id": FieldSchema(
                name="original_order_id",
                type=FieldType.STRING,
                description="i18n:fields.OverseasStockModifyOrderNode.original_order_id",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.selected_order.order_id }}",
                example="ORD20260127001",
                example_binding="{{ nodes.account.selected_order.order_id }}",
                bindable_sources=[
                    "RealAccountNode.open_orders[].order_id",
                    "OverseasStockNewOrderNode.order_result.order_id",
                ],
                expected_type="str",
            ),
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.STRING,
                description="i18n:fields.OverseasStockModifyOrderNode.symbol",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="AAPL",
                example="AAPL",
                expected_type="str",
            ),
            "exchange": FieldSchema(
                name="exchange",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockModifyOrderNode.exchange",
                enum_values=["NYSE", "NASDAQ", "AMEX"],
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
            "new_quantity": FieldSchema(
                name="new_quantity",
                type=FieldType.INTEGER,
                description="i18n:fields.OverseasStockModifyOrderNode.new_quantity",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="10",
                expected_type="int",
            ),
            "new_price": FieldSchema(
                name="new_price",
                type=FieldType.NUMBER,
                description="i18n:fields.OverseasStockModifyOrderNode.new_price",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                visible_when={"price_type": "limit"},
                placeholder="155.50",
                expected_type="float",
            ),
        }


class OverseasStockCancelOrderNode(BaseModifyOrderNode):
    """
    해외주식 취소주문 노드

    기존 미체결 주문을 취소합니다.

    API: COSAT00303 (해외주식 취소주문)
    """

    type: Literal["OverseasStockCancelOrderNode"] = "OverseasStockCancelOrderNode"
    description: str = "i18n:nodes.OverseasStockCancelOrderNode.description"

    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Cancel an existing unfilled or partially-filled overseas stock order",
            "Implement a time-based expiry: cancel open orders that have not filled within N minutes",
            "Cancel all open orders on a stop-loss trigger before placing new protective orders",
        ],
        "when_not_to_use": [
            "When the order is already fully filled — the cancel will be rejected by the broker",
            "For modify (price/quantity change) — use OverseasStockModifyOrderNode instead",
            "For futures orders — use OverseasFuturesCancelOrderNode",
        ],
        "typical_scenarios": [
            "ScheduleNode (end-of-day) → OverseasStockOpenOrdersNode → OverseasStockCancelOrderNode (cancel-all EOD)",
            "OverseasStockRealOrderEventNode (timeout/no-fill) → OverseasStockCancelOrderNode (stale order cleanup)",
            "IfNode (stop-loss triggered) → OverseasStockCancelOrderNode then OverseasStockNewOrderNode (cancel then replace)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Cancels a single open order identified by original_order_id + symbol + exchange; auto-iterate to cancel multiple",
        "Retry disabled by default — a duplicate cancel on an already-cancelled order returns an error from the broker",
        "Rate-limited to 1 concurrent execution with 5-second minimum interval",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Hard-coding original_order_id as a static string",
            "reason": "Order IDs are runtime-generated; a stale static ID will always fail or cancel the wrong order.",
            "alternative": "Bind from OverseasStockOpenOrdersNode.orders[].order_id or OverseasStockNewOrderNode.result.order_id.",
        },
        {
            "pattern": "Enabling retry on cancel nodes",
            "reason": "If the cancel succeeded but the response was lost in transit, retrying will hit 'order not found' and may raise an unhandled error.",
            "alternative": "Leave resilience.retry.enabled=False. Use fallback.mode='skip' if you want the workflow to continue past a stale cancel.",
        },
        {
            "pattern": "Connecting a realtime data node directly to cancel without ThrottleNode",
            "reason": "Each tick would fire a cancel request and exhaust rate limits immediately.",
            "alternative": "Use ThrottleNode or IfNode to gate the cancel trigger.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Cancel all open orders at end-of-day",
            "description": "Fetch all open orders and auto-iterate to cancel each one before market close.",
            "workflow_snippet": {
                "id": "overseas_stock_cancel_all_eod",
                "name": "Cancel All Open Orders EOD",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "open_orders", "type": "OverseasStockOpenOrdersNode"},
                    {"id": "cancel", "type": "OverseasStockCancelOrderNode",
                     "original_order_id": "{{ item.order_id }}",
                     "symbol": "{{ item.symbol }}",
                     "exchange": "{{ item.exchange }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "cancel"},
                    {"from": "broker", "to": "cancel"},
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
            "expected_output": "cancel_result port: {order_id, symbol, exchange, status='cancelled'}; cancelled_order_id port: string.",
        },
        {
            "title": "Cancel a specific order then place a replacement",
            "description": "Stop-loss triggers: cancel the original buy order and place a market sell to exit the position.",
            "workflow_snippet": {
                "id": "overseas_stock_cancel_and_replace",
                "name": "Cancel and Replace Order",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "open_orders", "type": "OverseasStockOpenOrdersNode"},
                    {"id": "cancel", "type": "OverseasStockCancelOrderNode",
                     "original_order_id": "{{ nodes.open_orders.orders[0].order_id }}",
                     "symbol": "AAPL",
                     "exchange": "NASDAQ"},
                    {"id": "sell", "type": "OverseasStockNewOrderNode",
                     "side": "sell",
                     "order_type": "market",
                     "order": {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 10}},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "cancel"},
                    {"from": "cancel", "to": "sell"},
                    {"from": "broker", "to": "cancel"},
                    {"from": "broker", "to": "sell"},
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
            "expected_output": "cancel_result with status='cancelled', then sell result with status='accepted' market order.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "Requires three fields: `original_order_id` (the order to cancel), `symbol` (ticker string), `exchange` ('NYSE'/'NASDAQ'/'AMEX'). "
            "Bind original_order_id from OverseasStockOpenOrdersNode.orders[].order_id or from a prior NewOrderNode.result.order_id. "
            "The broker connection is auto-injected via DAG traversal."
        ),
        "output_consumption": (
            "Two ports: `cancel_result` (full cancellation confirmation dict) and `cancelled_order_id` (string). "
            "Wire cancel_result to TableDisplayNode for audit logging, or use cancelled_order_id in downstream logic."
        ),
        "common_combinations": [
            "OverseasStockOpenOrdersNode → OverseasStockCancelOrderNode (cancel all open orders)",
            "OverseasStockCancelOrderNode → OverseasStockNewOrderNode (cancel then replace pattern)",
            "ScheduleNode → OverseasStockOpenOrdersNode → OverseasStockCancelOrderNode (EOD cleanup)",
        ],
        "pitfalls": [
            "Cancelling an already-filled order returns a broker error; check order status via OpenOrdersNode before cancelling",
            "fallback.mode='error' (default) will halt the workflow on a failed cancel — set to 'skip' for best-effort cancel-all patterns",
            "The 5-second rate-limit guard means large cancel batches take at minimum 5s per order",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.cancel_trigger",
        ),
        InputPort(
            name="original_order_id",
            type="string",
            description="i18n:ports.original_order_id",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="cancel_result",
            type="order_result",
            description="i18n:ports.cancel_result",
            fields=ORDER_RESULT_FIELDS,
        ),
        OutputPort(
            name="cancelled_order_id",
            type="string",
            description="i18n:ports.cancelled_order_id",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            **super().get_field_schema(),
            "original_order_id": FieldSchema(
                name="original_order_id",
                type=FieldType.STRING,
                description="i18n:fields.OverseasStockCancelOrderNode.original_order_id",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.selected_order.order_id }}",
                example="ORD20260127001",
                example_binding="{{ nodes.account.selected_order.order_id }}",
                bindable_sources=[
                    "RealAccountNode.open_orders[].order_id",
                    "OverseasStockNewOrderNode.order_result.order_id",
                ],
                expected_type="str",
            ),
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.STRING,
                description="i18n:fields.OverseasStockCancelOrderNode.symbol",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="AAPL",
                example="AAPL",
                expected_type="str",
            ),
            "exchange": FieldSchema(
                name="exchange",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockCancelOrderNode.exchange",
                enum_values=["NYSE", "NASDAQ", "AMEX"],
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
        }


# =============================================================================
# 해외선물 주문 노드
# =============================================================================

class OverseasFuturesNewOrderNode(BaseOrderNode):
    """
    해외선물 신규주문 노드

    해외선물(CME, EUREX, SGX, HKEX 등) 신규주문을 실행합니다.
    orders 필드에 주문할 종목 목록을 바인딩하세요.

    API: CIDBT00100 (해외선물 신규주문)
    """

    type: Literal["OverseasFuturesNewOrderNode"] = "OverseasFuturesNewOrderNode"
    description: str = "i18n:nodes.OverseasFuturesNewOrderNode.description"

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Place a new buy or sell order for an overseas futures contract (CME, EUREX, SGX, HKEX)",
            "Execute trend-following or hedging strategies using futures instruments",
            "Open or close futures positions programmatically, including expiry-month specification",
        ],
        "when_not_to_use": [
            "For US/HK/JP stocks — use OverseasStockNewOrderNode instead",
            "For Korean domestic stocks — use KoreaStockNewOrderNode",
            "When OverseasFuturesBrokerNode is not in the DAG — connection injection will fail",
        ],
        "typical_scenarios": [
            "ConditionNode → PositionSizingNode → OverseasFuturesNewOrderNode (systematic entry)",
            "OverseasFuturesAccountNode.positions → ConditionNode → OverseasFuturesNewOrderNode (add-to-position)",
            "ScheduleNode → OverseasFuturesNewOrderNode (time-triggered futures rollover)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Supports expiry_month field (YYYYMM format) to target a specific contract month; defaults to front-month if omitted",
        "Covers CME, EUREX, SGX, HKEX futures through OverseasFuturesBrokerNode — requires a separate futures credential",
        "is_tool_enabled=True — AI Agent can call this node as a tool to place futures orders",
        "Retry disabled by default to prevent duplicate futures contract positions",
        "Rate-limited to 1 concurrent execution with 5-second minimum interval",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Hard-coding quantity as a fixed integer without PositionSizingNode",
            "reason": "Futures contracts have multipliers and margin requirements; a fixed-lot approach ignores account equity and volatility.",
            "alternative": "Use PositionSizingNode with method='fixed_percent' or 'atr_based' and bind its output to the order field.",
        },
        {
            "pattern": "Using an OverseasStockBrokerNode for futures orders",
            "reason": "Overseas futures require a separate credential type (broker_ls_overseas_futureoption) and a different API endpoint.",
            "alternative": "Add OverseasFuturesBrokerNode with a futures-specific credential_id to the DAG.",
        },
        {
            "pattern": "Enabling retry on futures order nodes",
            "reason": "A duplicate futures order can double your position, which is especially dangerous with leverage.",
            "alternative": "Leave retry disabled (default). Query OverseasFuturesOpenOrdersNode or account after a failure to verify order state.",
        },
        {
            "pattern": "Using dict-keyed position data from account outputs as order input",
            "reason": "All position data in ProgramGarden is list[dict] with `symbol`/`exchange` keys — not symbol-keyed dicts.",
            "alternative": "Bind `{{ item }}` or `{{ item.symbol }}` when auto-iterating over positions list.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Place a CME NQ futures buy order",
            "description": "Trend signal triggers a buy order for one NASDAQ-100 Mini futures contract on CME.",
            "workflow_snippet": {
                "id": "overseas_futures_new_order_nq_buy",
                "name": "NQ Futures Buy",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": False},
                    {"id": "order", "type": "OverseasFuturesNewOrderNode",
                     "side": "buy",
                     "order_type": "limit",
                     "expiry_month": "202506",
                     "order": {"symbol": "NQM25", "exchange": "CME", "quantity": 1, "price": 21000.0}},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "order"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futureoption",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "result port: {order_id, symbol, exchange, side, quantity, price, status='accepted'}.",
        },
        {
            "title": "HKEX mini-futures basket order via auto-iterate",
            "description": "Place orders for multiple HKEX futures contracts by auto-iterating over a signals array.",
            "workflow_snippet": {
                "id": "overseas_futures_new_order_hkex_basket",
                "name": "HKEX Futures Basket",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasFuturesAccountNode"},
                    {"id": "sizing", "type": "PositionSizingNode",
                     "method": "fixed_percent",
                     "max_percent": 10,
                     "balance": "{{ nodes.account.balance }}",
                     "price": 20000.0,
                     "symbol": {"symbol": "MHIc1", "exchange": "HKEX"}},
                    {"id": "order", "type": "OverseasFuturesNewOrderNode",
                     "side": "buy",
                     "order_type": "limit",
                     "order": "{{ nodes.sizing.order }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "sizing"},
                    {"from": "sizing", "to": "order"},
                    {"from": "broker", "to": "order"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futureoption",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "result port: {order_id, symbol='MHIc1', exchange='HKEX', side='buy', quantity, price, status}.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `order` field must be a dict with keys {symbol, exchange, quantity, price?}. "
            "The `expiry_month` field (YYYYMM string) selects the contract month; omit for the default front-month. "
            "The `side` field ('buy'/'sell') selects direction; `order_type` ('limit'/'market') sets execution type. "
            "Requires OverseasFuturesBrokerNode upstream with a `broker_ls_overseas_futureoption` credential. "
            "The broker connection is auto-injected via DAG traversal."
        ),
        "output_consumption": (
            "The `result` port emits a single order-confirmation dict: {order_id, symbol, exchange, side, quantity, price, status}. "
            "Pass order_id to OverseasFuturesModifyOrderNode or OverseasFuturesCancelOrderNode for lifecycle management."
        ),
        "common_combinations": [
            "PositionSizingNode.order → OverseasFuturesNewOrderNode (risk-sized futures entry)",
            "OverseasFuturesNewOrderNode.result.order_id → OverseasFuturesCancelOrderNode (order lifecycle)",
            "OverseasFuturesAccountNode.balance → PositionSizingNode → OverseasFuturesNewOrderNode",
            "OverseasFuturesNewOrderNode.result → TableDisplayNode (order audit log)",
        ],
        "pitfalls": [
            "Futures require a separate futures-specific broker credential (broker_ls_overseas_futureoption) — not the stock credential",
            "Leverage in futures means a fixed-lot mistake is more costly than in equities — always use PositionSizingNode",
            "Retry is disabled by default to prevent duplicate positions — do not enable without server-side idempotency confirmation",
            "paper_trading must be False on OverseasFuturesBrokerNode for real order execution",
        ],
    }

    # 해외선물 전용 필드
    expiry_month: Optional[str] = Field(
        default=None,
        description="만기년월 (예: 202503)",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        )
        return {
            **super().get_field_schema(),
            "side": FieldSchema(
                name="side",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasFuturesNewOrderNode.side",
                default="buy",
                enum_values=["buy", "sell"],
                enum_labels={
                    "buy": "i18n:enums.side.buy",
                    "sell": "i18n:enums.side.sell",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
                example="buy",
            ),
            "order_type": FieldSchema(
                name="order_type",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasFuturesNewOrderNode.order_type",
                default="limit",
                enum_values=["market", "limit"],
                enum_labels={
                    "market": "i18n:enums.order_type.market",
                    "limit": "i18n:enums.order_type.limit",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
                example="limit",
            ),
            "expiry_month": FieldSchema(
                name="expiry_month",
                type=FieldType.STRING,
                description="i18n:fields.OverseasFuturesNewOrderNode.expiry_month",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="202503",
                example="202503",
                expected_type="str",
            ),
            "order": FieldSchema(
                name="order",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.OverseasFuturesNewOrderNode.order",
                description="i18n:fields.OverseasFuturesNewOrderNode.order",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"symbol": "NQH25", "exchange": "CME", "quantity": 1, "price": 21000.0},
                example_binding="{{ nodes.positionSizing.order }}",
                bindable_sources=[
                    "PositionSizingNode.order",
                ],
                object_schema=[
                    {"name": "symbol", "type": "STRING", "required": True,
                     "label": "i18n:fields.order.symbol"},
                    {"name": "exchange", "type": "STRING", "required": True,
                     "label": "i18n:fields.order.exchange"},
                    {"name": "quantity", "type": "INTEGER", "required": True,
                     "label": "i18n:fields.order.quantity"},
                    {"name": "price", "type": "NUMBER", "required": False,
                     "label": "i18n:fields.order.price"},
                ],
                expected_type="{symbol: str, exchange: str, quantity: int, price?: float}",
                help_text="i18n:fields.OverseasFuturesNewOrderNode.order.help_text",
            ),
        }


class OverseasFuturesModifyOrderNode(BaseModifyOrderNode):
    """
    해외선물 정정주문 노드

    기존 미체결 주문의 가격이나 수량을 정정합니다.

    API: CIDBT00200 (해외선물 정정주문)
    """

    type: Literal["OverseasFuturesModifyOrderNode"] = "OverseasFuturesModifyOrderNode"
    description: str = "i18n:nodes.OverseasFuturesModifyOrderNode.description"

    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Change the price or quantity of an existing unfilled overseas futures order",
            "Chase price with a limit order reprice to improve fill probability in a trending market",
            "Partially scale out of an open futures order by reducing quantity before full execution",
        ],
        "when_not_to_use": [
            "When the futures order has already been fully filled — modification will be rejected",
            "To fully cancel the order — use OverseasFuturesCancelOrderNode instead",
            "For stock orders — use OverseasStockModifyOrderNode",
        ],
        "typical_scenarios": [
            "OverseasFuturesOpenOrdersNode → OverseasFuturesModifyOrderNode (reprice all open futures orders)",
            "OverseasFuturesRealOrderEventNode → ThrottleNode → OverseasFuturesModifyOrderNode (event-driven reprice)",
            "IfNode (market moved away) → OverseasFuturesModifyOrderNode (aggressive reprice to market)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Modifies price and/or quantity of a single open futures order by original_order_id + symbol + exchange",
        "Supports the same exchanges as OverseasFuturesNewOrderNode (CME, EUREX, SGX, HKEX)",
        "Retry disabled by default — duplicate modify on a futures order can create unexpected position delta",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Hard-coding original_order_id as a static string",
            "reason": "Futures order IDs are runtime-generated; a static ID will fail or target the wrong order.",
            "alternative": "Bind from OverseasFuturesOpenOrdersNode.orders[].order_id or OverseasFuturesNewOrderNode.result.order_id.",
        },
        {
            "pattern": "Enabling retry on futures modify nodes",
            "reason": "A successful modify with a lost acknowledgement will apply the price change twice if retried.",
            "alternative": "Leave resilience.retry.enabled=False. Query OpenOrdersNode to verify state after a suspected failure.",
        },
        {
            "pattern": "Connecting realtime futures data directly to modify without ThrottleNode",
            "reason": "Each tick fires a modify attempt, saturating the rate limit and causing cascading rejections.",
            "alternative": "Insert ThrottleNode between realtime source and modify node.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Reprice an open futures limit order",
            "description": "Fetch all open futures orders and reprice the first one to a better limit price.",
            "workflow_snippet": {
                "id": "overseas_futures_modify_order_reprice",
                "name": "Reprice Open Futures Order",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": False},
                    {"id": "open_orders", "type": "OverseasFuturesOpenOrdersNode"},
                    {"id": "modify", "type": "OverseasFuturesModifyOrderNode",
                     "original_order_id": "{{ item.order_id }}",
                     "symbol": "{{ item.symbol }}",
                     "exchange": "{{ item.exchange }}",
                     "new_price": 21050.0},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "modify"},
                    {"from": "broker", "to": "modify"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futureoption",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "modify_result port: {order_id, symbol, exchange, new_price, status}; modified_order_id port: updated order ID string.",
        },
        {
            "title": "Reduce quantity on partial fill event",
            "description": "Listen for partial fill event on a futures order and reduce the remaining quantity.",
            "workflow_snippet": {
                "id": "overseas_futures_modify_order_partial",
                "name": "Futures Partial Fill Adjust",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": False},
                    {"id": "real_event", "type": "OverseasFuturesRealOrderEventNode"},
                    {"id": "throttle", "type": "ThrottleNode", "interval_sec": 10},
                    {"id": "modify", "type": "OverseasFuturesModifyOrderNode",
                     "original_order_id": "{{ nodes.real_event.order_id }}",
                     "symbol": "{{ nodes.real_event.symbol }}",
                     "exchange": "{{ nodes.real_event.exchange }}",
                     "new_quantity": 1},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "real_event"},
                    {"from": "real_event", "to": "throttle"},
                    {"from": "throttle", "to": "modify"},
                    {"from": "broker", "to": "modify"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futureoption",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "modify_result port with updated quantity; modified_order_id contains the new order ID.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "Requires three fields: `original_order_id` (string), `symbol` (futures contract code e.g. 'NQM25'), `exchange` ('CME'/'EUREX'/'SGX'/'HKEX'). "
            "Provide `new_price` (float) and/or `new_quantity` (int) — at least one must be specified. "
            "Bind original_order_id from OverseasFuturesOpenOrdersNode or a prior NewOrderNode result. "
            "Requires OverseasFuturesBrokerNode upstream (auto-injected by executor)."
        ),
        "output_consumption": (
            "Two ports: `modify_result` (order confirmation dict) and `modified_order_id` (string). "
            "Chain modified_order_id into CancelOrderNode for subsequent lifecycle steps."
        ),
        "common_combinations": [
            "OverseasFuturesOpenOrdersNode → OverseasFuturesModifyOrderNode (reprice all open futures)",
            "OverseasFuturesRealOrderEventNode → ThrottleNode → OverseasFuturesModifyOrderNode (event-driven reprice)",
            "OverseasFuturesModifyOrderNode.modified_order_id → OverseasFuturesCancelOrderNode (cancel after failed modify)",
        ],
        "pitfalls": [
            "Cannot modify a fully filled futures order — verify order status first via OpenOrdersNode",
            "Omitting both new_price and new_quantity sends a no-op that the broker may reject with an error",
            "Futures contract codes include expiry month (e.g. NQM25) — make sure symbol matches the exact open order",
        ],
    }

    # 정정 대상
    new_quantity: Optional[int] = Field(
        default=None,
        description="정정할 수량",
    )
    new_price: Optional[float] = Field(
        default=None,
        description="정정할 가격",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.modify_trigger",
        ),
        InputPort(
            name="original_order_id",
            type="string",
            description="i18n:ports.original_order_id",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="modify_result",
            type="order_result",
            description="i18n:ports.modify_result",
            fields=ORDER_RESULT_FIELDS,
        ),
        OutputPort(
            name="modified_order_id",
            type="string",
            description="i18n:ports.modified_order_id",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            **super().get_field_schema(),
            "original_order_id": FieldSchema(
                name="original_order_id",
                type=FieldType.STRING,
                description="i18n:fields.OverseasFuturesModifyOrderNode.original_order_id",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.selected_order.order_id }}",
                example="ORD20260127001",
                example_binding="{{ nodes.account.selected_order.order_id }}",
                bindable_sources=[
                    "RealAccountNode.open_orders[].order_id",
                    "OverseasFuturesNewOrderNode.order_result.order_id",
                ],
                expected_type="str",
            ),
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.STRING,
                description="i18n:fields.OverseasFuturesModifyOrderNode.symbol",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="NQH25",
                example="NQH25",
                expected_type="str",
            ),
            "exchange": FieldSchema(
                name="exchange",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasFuturesModifyOrderNode.exchange",
                enum_values=["CME", "EUREX", "SGX", "HKEX"],
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
            "new_quantity": FieldSchema(
                name="new_quantity",
                type=FieldType.INTEGER,
                description="i18n:fields.OverseasFuturesModifyOrderNode.new_quantity",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="1",
                expected_type="int",
            ),
            "new_price": FieldSchema(
                name="new_price",
                type=FieldType.NUMBER,
                description="i18n:fields.OverseasFuturesModifyOrderNode.new_price",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="21000.0",
                expected_type="float",
            ),
        }


class OverseasFuturesCancelOrderNode(BaseModifyOrderNode):
    """
    해외선물 취소주문 노드

    기존 미체결 주문을 취소합니다.

    API: CIDBT00300 (해외선물 취소주문)
    """

    type: Literal["OverseasFuturesCancelOrderNode"] = "OverseasFuturesCancelOrderNode"
    description: str = "i18n:nodes.OverseasFuturesCancelOrderNode.description"

    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Cancel an existing unfilled or partially-filled overseas futures order",
            "Implement end-of-session cleanup: cancel all open futures orders before rollover",
            "Cancel protective limit orders when a hedging condition is no longer active",
        ],
        "when_not_to_use": [
            "When the futures order is already fully filled — cancel will be rejected by the exchange",
            "To modify price/quantity — use OverseasFuturesModifyOrderNode instead",
            "For stock orders — use OverseasStockCancelOrderNode",
        ],
        "typical_scenarios": [
            "ScheduleNode (session end) → OverseasFuturesOpenOrdersNode → OverseasFuturesCancelOrderNode (cancel-all)",
            "OverseasFuturesRealOrderEventNode (timeout) → OverseasFuturesCancelOrderNode (stale order cleanup)",
            "IfNode (position closed) → OverseasFuturesCancelOrderNode (cancel protective stop)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Cancels a single open futures order by original_order_id + symbol + exchange; auto-iterate for batch cancellation",
        "Retry disabled by default — a duplicate cancel returns a broker error if the order was already cancelled",
        "Rate-limited to 1 concurrent execution with 5-second minimum interval",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Hard-coding original_order_id as a static string",
            "reason": "Futures order IDs are runtime-generated; a static ID will fail or cancel the wrong contract.",
            "alternative": "Bind from OverseasFuturesOpenOrdersNode.orders[].order_id or OverseasFuturesNewOrderNode.result.order_id.",
        },
        {
            "pattern": "Enabling retry on cancel nodes",
            "reason": "A successful cancel that returns a transient network error will be retried and hit 'order not found', potentially crashing the workflow.",
            "alternative": "Leave retry disabled. Set fallback.mode='skip' if best-effort cancel is acceptable.",
        },
        {
            "pattern": "Connecting realtime futures data directly to cancel without ThrottleNode",
            "reason": "Every tick fires a cancel attempt, exhausting rate limits and generating spurious rejections.",
            "alternative": "Use ThrottleNode or IfNode to gate the cancel trigger.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Cancel all open futures orders at session end",
            "description": "Fetch all open futures orders and auto-iterate to cancel each one before market close.",
            "workflow_snippet": {
                "id": "overseas_futures_cancel_all_eod",
                "name": "Cancel All Futures Orders",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": False},
                    {"id": "open_orders", "type": "OverseasFuturesOpenOrdersNode"},
                    {"id": "cancel", "type": "OverseasFuturesCancelOrderNode",
                     "original_order_id": "{{ item.order_id }}",
                     "symbol": "{{ item.symbol }}",
                     "exchange": "{{ item.exchange }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "cancel"},
                    {"from": "broker", "to": "cancel"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futureoption",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "cancel_result port: {order_id, symbol, exchange, status='cancelled'}; cancelled_order_id port: string.",
        },
        {
            "title": "Cancel a specific futures order and replace with new price",
            "description": "Cancel an existing limit order and immediately place a new one at a revised price.",
            "workflow_snippet": {
                "id": "overseas_futures_cancel_and_replace",
                "name": "Futures Cancel and Replace",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures_cred", "paper_trading": False},
                    {"id": "open_orders", "type": "OverseasFuturesOpenOrdersNode"},
                    {"id": "cancel", "type": "OverseasFuturesCancelOrderNode",
                     "original_order_id": "{{ nodes.open_orders.orders[0].order_id }}",
                     "symbol": "NQM25",
                     "exchange": "CME"},
                    {"id": "new_order", "type": "OverseasFuturesNewOrderNode",
                     "side": "buy",
                     "order_type": "limit",
                     "order": {"symbol": "NQM25", "exchange": "CME", "quantity": 1, "price": 21100.0}},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "cancel"},
                    {"from": "cancel", "to": "new_order"},
                    {"from": "broker", "to": "cancel"},
                    {"from": "broker", "to": "new_order"},
                ],
                "credentials": [
                    {
                        "credential_id": "futures_cred",
                        "type": "broker_ls_overseas_futureoption",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "cancel_result with status='cancelled', then new order result with status='accepted'.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "Requires three fields: `original_order_id` (the futures order to cancel), `symbol` (contract code e.g. 'NQM25'), `exchange` ('CME'/'EUREX'/'SGX'/'HKEX'). "
            "Bind original_order_id from OverseasFuturesOpenOrdersNode.orders[].order_id or from a prior NewOrderNode result. "
            "The broker connection is auto-injected via DAG traversal from OverseasFuturesBrokerNode."
        ),
        "output_consumption": (
            "Two ports: `cancel_result` (cancellation confirmation dict) and `cancelled_order_id` (string). "
            "Chain cancel_result to TableDisplayNode for audit logging, or sequence cancelled_order_id into a new order node."
        ),
        "common_combinations": [
            "OverseasFuturesOpenOrdersNode → OverseasFuturesCancelOrderNode (cancel all open futures)",
            "OverseasFuturesCancelOrderNode → OverseasFuturesNewOrderNode (cancel then replace pattern)",
            "ScheduleNode → OverseasFuturesOpenOrdersNode → OverseasFuturesCancelOrderNode (session-end cleanup)",
        ],
        "pitfalls": [
            "Cancelling an already-filled futures order returns a broker error — check order status first via OpenOrdersNode",
            "fallback.mode='error' (default) halts workflow on cancel failure — use 'skip' for best-effort cancel-all loops",
            "The 5-second rate-limit guard means a 10-order cancel batch takes at least 50 seconds",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.cancel_trigger",
        ),
        InputPort(
            name="original_order_id",
            type="string",
            description="i18n:ports.original_order_id",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="cancel_result",
            type="order_result",
            description="i18n:ports.cancel_result",
            fields=ORDER_RESULT_FIELDS,
        ),
        OutputPort(
            name="cancelled_order_id",
            type="string",
            description="i18n:ports.cancelled_order_id",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            **super().get_field_schema(),
            "original_order_id": FieldSchema(
                name="original_order_id",
                type=FieldType.STRING,
                description="i18n:fields.OverseasFuturesCancelOrderNode.original_order_id",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.selected_order.order_id }}",
                example="ORD20260127001",
                example_binding="{{ nodes.account.selected_order.order_id }}",
                bindable_sources=[
                    "RealAccountNode.open_orders[].order_id",
                    "OverseasFuturesNewOrderNode.order_result.order_id",
                ],
                expected_type="str",
            ),
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.STRING,
                description="i18n:fields.OverseasFuturesCancelOrderNode.symbol",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="NQH25",
                example="NQH25",
                expected_type="str",
            ),
            "exchange": FieldSchema(
                name="exchange",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasFuturesCancelOrderNode.exchange",
                enum_values=["CME", "EUREX", "SGX", "HKEX"],
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
        }


# =============================================================================
# 국내주식 주문 노드
# =============================================================================

class KoreaStockNewOrderNode(BaseOrderNode):
    """
    국내주식 신규주문 노드

    국내주식(KOSPI, KOSDAQ) 신규주문을 실행합니다.
    order 필드에 주문할 종목을 바인딩하세요.

    API: CSPAT00601 (국내주식 신규주문)
    """

    type: Literal["KoreaStockNewOrderNode"] = "KoreaStockNewOrderNode"
    description: str = "i18n:nodes.KoreaStockNewOrderNode.description"

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Place a new buy or sell order for a Korean domestic stock (KOSPI or KOSDAQ)",
            "Execute a signal-driven entry after a ConditionNode or PositionSizingNode resolves the target symbol and quantity",
            "Place orders in KRW-denominated quantities for KOSPI/KOSDAQ listed stocks",
        ],
        "when_not_to_use": [
            "For overseas (US/HK/JP) stocks — use OverseasStockNewOrderNode",
            "For overseas futures — use OverseasFuturesNewOrderNode",
            "In paper-trading mode — KoreaStockNewOrderNode is real-market only (paper_trading=False is enforced at the Pydantic level)",
        ],
        "typical_scenarios": [
            "KoreaStockAccountNode → ConditionNode → PositionSizingNode → KoreaStockNewOrderNode (RSI-based buy)",
            "KoreaStockHistoricalDataNode → ConditionNode → KoreaStockNewOrderNode (breakout entry)",
            "ScheduleNode → KoreaStockAccountNode → KoreaStockNewOrderNode (time-triggered rebalance)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Supports price_type options: 'limit' (지정가), 'market' (시장가), 'conditional_limit' (조건부지정가)",
        "KRW-denominated: symbol is a 6-digit Korean stock code (e.g. '005930' for Samsung Electronics); no exchange field required",
        "is_tool_enabled=True — AI Agent can call this node as a tool to place Korean stock orders",
        "Real-market only — paper_trading mode is not supported for Korean domestic stocks; KoreaStockBrokerNode enforces this",
        "Retry disabled by default to prevent duplicate KRW-denominated orders",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Setting paper_trading=True on KoreaStockBrokerNode",
            "reason": "Korean domestic stocks do not support paper trading mode through LS Securities. The broker node will raise a validation error.",
            "alternative": "Use only real-market credentials. For testing logic, use an OverseasStockBrokerNode in paper mode instead.",
        },
        {
            "pattern": "Hard-coding quantity as a fixed integer without PositionSizingNode",
            "reason": "Fixed KRW quantities ignore available balance and risk limits, leading to oversized or undersized positions.",
            "alternative": "Connect PositionSizingNode and bind `order` to `{{ nodes.positionSizing.order }}` for risk-adjusted quantity.",
        },
        {
            "pattern": "Using exchange field in the order dict for Korean stocks",
            "reason": "Korean stocks do not use an exchange field — the symbol (6-digit code) uniquely identifies KOSPI/KOSDAQ listing.",
            "alternative": "Use order dict with only {symbol, quantity, price?} keys for KoreaStockNewOrderNode.",
        },
        {
            "pattern": "Enabling retry on Korea stock order nodes",
            "reason": "A duplicate order can result in a double position in KRW-denominated Korean stocks.",
            "alternative": "Leave resilience.retry.enabled=False (default). Verify order state via KoreaStockOpenOrdersNode after failures.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "RSI-driven buy order for Samsung Electronics",
            "description": "RSI oversold signal on daily data triggers a buy order for Samsung stock via PositionSizingNode.",
            "workflow_snippet": {
                "id": "korea_stock_new_order_rsi_buy",
                "name": "Korea Stock RSI Buy",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "kr_broker_cred"},
                    {"id": "account", "type": "KoreaStockAccountNode"},
                    {"id": "historical", "type": "KoreaStockHistoricalDataNode",
                     "symbols": [{"symbol": "005930", "exchange": "KOSPI"}],
                     "period": "1d", "count": 20},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI",
                     "data": "{{ nodes.historical.ohlcv }}", "period": 14, "oversold_threshold": 30},
                    {"id": "sizing", "type": "PositionSizingNode",
                     "method": "fixed_percent", "max_percent": 5,
                     "balance": "{{ nodes.account.balance }}",
                     "price": 70000,
                     "symbol": {"symbol": "005930", "exchange": "KOSPI"}},
                    {"id": "order", "type": "KoreaStockNewOrderNode",
                     "side": "buy", "order_type": "limit",
                     "order": "{{ nodes.sizing.order }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "sizing"},
                    {"from": "account", "to": "sizing"},
                    {"from": "sizing", "to": "order"},
                    {"from": "broker", "to": "order"},
                ],
                "credentials": [
                    {
                        "credential_id": "kr_broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "result port: {order_id, symbol='005930', side='buy', quantity, price, status='accepted'}.",
        },
        {
            "title": "Market sell order for all held Korean stocks",
            "description": "Fetch account positions and auto-iterate to place a market sell for every held stock.",
            "workflow_snippet": {
                "id": "korea_stock_basket_sell",
                "name": "Korea Stock Basket Sell",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "kr_broker_cred"},
                    {"id": "account", "type": "KoreaStockAccountNode"},
                    {"id": "order", "type": "KoreaStockNewOrderNode",
                     "side": "sell", "order_type": "market",
                     "order": "{{ item }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "order"},
                    {"from": "broker", "to": "order"},
                ],
                "credentials": [
                    {
                        "credential_id": "kr_broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "result port emitted once per position: {order_id, symbol, side='sell', quantity, status}.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `order` field must be a dict with keys {symbol, quantity, price?} — no exchange field for Korean stocks. "
            "symbol is the 6-digit KRX code (e.g. '005930' for Samsung). "
            "price is KRW-denominated (integer or float). "
            "The `price_type` field selects order sub-type: 'limit' (default), 'market', or 'conditional_limit'. "
            "For market orders, omit price or set to 0. "
            "Requires KoreaStockBrokerNode upstream (auto-injected by executor)."
        ),
        "output_consumption": (
            "The `result` port emits: {order_id, symbol, side, quantity, price, status}. "
            "Pass order_id to KoreaStockModifyOrderNode or KoreaStockCancelOrderNode for lifecycle management."
        ),
        "common_combinations": [
            "PositionSizingNode.order → KoreaStockNewOrderNode (risk-adjusted KRW order)",
            "KoreaStockNewOrderNode.result.order_id → KoreaStockCancelOrderNode (order lifecycle)",
            "KoreaStockAccountNode.balance → PositionSizingNode → KoreaStockNewOrderNode",
            "KoreaStockNewOrderNode.result → TableDisplayNode (audit log)",
        ],
        "pitfalls": [
            "Paper trading is NOT supported for Korean domestic stocks — do not set paper_trading=True on KoreaStockBrokerNode",
            "Korean stock order quantities are in shares (not KRW) — verify you are passing share count, not monetary amount",
            "Retry is disabled by default — do not enable without server-side idempotency confirmation from LS Securities",
            "conditional_limit price_type requires a limit price even though it may execute as market under certain conditions",
        ],
    }

    # 국내주식 전용 필드
    price_type: Literal["limit", "market", "conditional_limit"] = Field(
        default="limit",
        description="호가 유형 (limit: 지정가, market: 시장가, conditional_limit: 조건부지정가)",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        )
        return {
            **super().get_field_schema(),
            "side": FieldSchema(
                name="side",
                type=FieldType.ENUM,
                description="i18n:fields.KoreaStockNewOrderNode.side",
                default="buy",
                enum_values=["buy", "sell"],
                enum_labels={
                    "buy": "i18n:enums.side.buy",
                    "sell": "i18n:enums.side.sell",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
            "order_type": FieldSchema(
                name="order_type",
                type=FieldType.ENUM,
                description="i18n:fields.KoreaStockNewOrderNode.order_type",
                default="limit",
                enum_values=["market", "limit"],
                enum_labels={
                    "market": "i18n:enums.order_type.market",
                    "limit": "i18n:enums.order_type.limit",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
            "price_type": FieldSchema(
                name="price_type",
                type=FieldType.ENUM,
                description="i18n:fields.KoreaStockNewOrderNode.price_type",
                default="limit",
                enum_values=["limit", "market", "conditional_limit"],
                enum_labels={
                    "limit": "i18n:enums.kr_price_type.limit",
                    "market": "i18n:enums.kr_price_type.market",
                    "conditional_limit": "i18n:enums.kr_price_type.conditional_limit",
                },
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
            "order": FieldSchema(
                name="order",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.KoreaStockNewOrderNode.order",
                description="i18n:fields.KoreaStockNewOrderNode.order",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"symbol": "005930", "quantity": 10, "price": 70000},
                example_binding="{{ nodes.positionSizing.order }}",
                bindable_sources=[
                    "PositionSizingNode.order",
                ],
                object_schema=[
                    {"name": "symbol", "type": "STRING", "required": True,
                     "label": "i18n:fields.order.symbol"},
                    {"name": "quantity", "type": "INTEGER", "required": True,
                     "label": "i18n:fields.order.quantity"},
                    {"name": "price", "type": "NUMBER", "required": False,
                     "label": "i18n:fields.order.price"},
                ],
                expected_type="{symbol: str, quantity: int, price?: float}",
                help_text="i18n:fields.KoreaStockNewOrderNode.order.help_text",
            ),
        }


class KoreaStockModifyOrderNode(BaseModifyOrderNode):
    """
    국내주식 정정주문 노드

    기존 미체결 주문의 가격이나 수량을 정정합니다.

    API: CSPAT00701 (국내주식 정정주문)
    """

    type: Literal["KoreaStockModifyOrderNode"] = "KoreaStockModifyOrderNode"
    description: str = "i18n:nodes.KoreaStockModifyOrderNode.description"

    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Change the price or quantity of an existing unfilled Korean stock order (KOSPI/KOSDAQ)",
            "Chase a moving price on a KRW-denominated limit order without cancelling and resubmitting",
            "Partially reduce the open quantity of a Korean stock order to lower exposure",
        ],
        "when_not_to_use": [
            "When the order is already fully filled — modification will be rejected by the exchange",
            "To fully cancel the order — use KoreaStockCancelOrderNode instead",
            "For overseas stock orders — use OverseasStockModifyOrderNode",
        ],
        "typical_scenarios": [
            "KoreaStockOpenOrdersNode.orders → KoreaStockModifyOrderNode (reprice all open KR orders)",
            "KoreaStockRealOrderEventNode (partial fill) → ThrottleNode → KoreaStockModifyOrderNode (adjust remaining)",
            "IfNode (market moved) → KoreaStockModifyOrderNode (chase with new limit price)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Modifies price and/or quantity of a single open Korean stock order by original_order_id + symbol",
        "No exchange field required — Korean stock symbol (6-digit code) uniquely identifies the instrument",
        "Retry disabled by default to prevent double-modification risk in KRW-denominated orders",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Hard-coding original_order_id as a static string",
            "reason": "Korean stock order IDs are runtime-generated; a stale static ID will fail or modify the wrong order.",
            "alternative": "Bind from KoreaStockOpenOrdersNode.orders[].order_id or KoreaStockNewOrderNode.result.order_id.",
        },
        {
            "pattern": "Enabling retry on modify nodes",
            "reason": "A successful modify with a lost acknowledgement will apply the price change twice if retried.",
            "alternative": "Leave resilience.retry.enabled=False. Query KoreaStockOpenOrdersNode to verify state after failure.",
        },
        {
            "pattern": "Connecting realtime Korean data directly to modify without ThrottleNode",
            "reason": "Each tick fires a modify request, exhausting rate limits and causing rejection cascades.",
            "alternative": "Insert ThrottleNode between the realtime source and the modify node.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Reprice an open Korean stock limit order",
            "description": "Fetch all open Korean stock orders and reprice the first one to a new KRW price.",
            "workflow_snippet": {
                "id": "korea_stock_modify_order_reprice",
                "name": "Korea Stock Reprice",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "kr_broker_cred"},
                    {"id": "open_orders", "type": "KoreaStockOpenOrdersNode"},
                    {"id": "modify", "type": "KoreaStockModifyOrderNode",
                     "original_order_id": "{{ item.order_id }}",
                     "symbol": "{{ item.symbol }}",
                     "new_price": 69500},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "modify"},
                    {"from": "broker", "to": "modify"},
                ],
                "credentials": [
                    {
                        "credential_id": "kr_broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "modify_result port: {order_id, symbol, new_price, status}; modified_order_id port: string.",
        },
        {
            "title": "Reduce quantity on partial fill event",
            "description": "React to a partial fill via RealOrderEventNode and reduce the remaining quantity.",
            "workflow_snippet": {
                "id": "korea_stock_modify_order_partial",
                "name": "Korea Stock Partial Fill Adjust",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "kr_broker_cred"},
                    {"id": "real_event", "type": "KoreaStockRealOrderEventNode"},
                    {"id": "throttle", "type": "ThrottleNode", "interval_sec": 10},
                    {"id": "modify", "type": "KoreaStockModifyOrderNode",
                     "original_order_id": "{{ nodes.real_event.order_id }}",
                     "symbol": "{{ nodes.real_event.symbol }}",
                     "new_quantity": 5},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "real_event"},
                    {"from": "real_event", "to": "throttle"},
                    {"from": "throttle", "to": "modify"},
                    {"from": "broker", "to": "modify"},
                ],
                "credentials": [
                    {
                        "credential_id": "kr_broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "modify_result with updated quantity; modified_order_id port contains the new order ID.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "Requires two mandatory fields: `original_order_id` (string) and `symbol` (6-digit KRX code). "
            "No exchange field — Korean stock symbols uniquely identify instruments. "
            "Optionally provide `new_price` (KRW int/float) and/or `new_quantity` (int). "
            "Bind original_order_id from KoreaStockOpenOrdersNode or a prior NewOrderNode result. "
            "Requires KoreaStockBrokerNode upstream (auto-injected by executor)."
        ),
        "output_consumption": (
            "Two ports: `modify_result` (order confirmation dict) and `modified_order_id` (string). "
            "Chain modified_order_id into KoreaStockCancelOrderNode for subsequent lifecycle steps."
        ),
        "common_combinations": [
            "KoreaStockOpenOrdersNode → KoreaStockModifyOrderNode (reprice all open KR orders)",
            "KoreaStockRealOrderEventNode → ThrottleNode → KoreaStockModifyOrderNode (event-driven reprice)",
            "KoreaStockModifyOrderNode.modified_order_id → KoreaStockCancelOrderNode (cancel after failed modify)",
        ],
        "pitfalls": [
            "Cannot modify a fully filled Korean stock order — verify status via KoreaStockOpenOrdersNode first",
            "KRW prices must be valid tick sizes for the stock; invalid tick sizes will be rejected by KRX",
            "Paper trading is NOT supported for Korean stocks — the broker node enforces real-market mode only",
        ],
    }

    # 정정 대상
    new_quantity: Optional[int] = Field(
        default=None,
        description="정정할 수량 (변경하지 않으면 기존 수량 유지)",
    )
    new_price: Optional[float] = Field(
        default=None,
        description="정정할 가격 (변경하지 않으면 기존 가격 유지)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.modify_trigger",
        ),
        InputPort(
            name="original_order_id",
            type="string",
            description="i18n:ports.original_order_id",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="modify_result",
            type="order_result",
            description="i18n:ports.modify_result",
            fields=ORDER_RESULT_FIELDS,
        ),
        OutputPort(
            name="modified_order_id",
            type="string",
            description="i18n:ports.modified_order_id",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            **super().get_field_schema(),
            "original_order_id": FieldSchema(
                name="original_order_id",
                type=FieldType.STRING,
                description="i18n:fields.KoreaStockModifyOrderNode.original_order_id",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.selected_order.order_id }}",
                example="ORD20260127001",
                example_binding="{{ nodes.account.selected_order.order_id }}",
                bindable_sources=[
                    "RealAccountNode.open_orders[].order_id",
                    "KoreaStockNewOrderNode.order_result.order_id",
                ],
                expected_type="str",
            ),
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.STRING,
                description="i18n:fields.KoreaStockModifyOrderNode.symbol",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="005930",
                example="005930",
                expected_type="str",
            ),
            "new_quantity": FieldSchema(
                name="new_quantity",
                type=FieldType.INTEGER,
                description="i18n:fields.KoreaStockModifyOrderNode.new_quantity",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="10",
                expected_type="int",
            ),
            "new_price": FieldSchema(
                name="new_price",
                type=FieldType.NUMBER,
                description="i18n:fields.KoreaStockModifyOrderNode.new_price",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="70000",
                expected_type="float",
            ),
        }


class KoreaStockCancelOrderNode(BaseModifyOrderNode):
    """
    국내주식 취소주문 노드

    기존 미체결 주문을 취소합니다.

    API: CSPAT00801 (국내주식 취소주문)
    """

    type: Literal["KoreaStockCancelOrderNode"] = "KoreaStockCancelOrderNode"
    description: str = "i18n:nodes.KoreaStockCancelOrderNode.description"

    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Cancel an existing unfilled or partially-filled Korean domestic stock order (KOSPI/KOSDAQ)",
            "Implement end-of-day cleanup by cancelling all remaining open Korean stock orders",
            "Cancel a stale limit order that has not filled within a defined time window",
        ],
        "when_not_to_use": [
            "When the order is already fully filled — cancel will be rejected by KRX",
            "To change price or quantity — use KoreaStockModifyOrderNode instead",
            "For overseas stock orders — use OverseasStockCancelOrderNode",
        ],
        "typical_scenarios": [
            "ScheduleNode (end-of-day) → KoreaStockOpenOrdersNode → KoreaStockCancelOrderNode (cancel-all)",
            "KoreaStockRealOrderEventNode (timeout) → KoreaStockCancelOrderNode (stale order cleanup)",
            "IfNode (stop-loss triggered) → KoreaStockCancelOrderNode → KoreaStockNewOrderNode (cancel then exit)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Cancels a single open Korean stock order by original_order_id + symbol; auto-iterate for batch cancellation",
        "No exchange field required — Korean stock symbols uniquely identify KOSPI/KOSDAQ instruments",
        "Retry disabled by default — a duplicate cancel returns an error if the order was already cancelled",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Hard-coding original_order_id as a static string",
            "reason": "Korean stock order IDs are runtime-generated; a stale static ID will always fail.",
            "alternative": "Bind from KoreaStockOpenOrdersNode.orders[].order_id or KoreaStockNewOrderNode.result.order_id.",
        },
        {
            "pattern": "Enabling retry on Korean stock cancel nodes",
            "reason": "A successful cancel that returns a transient error will be retried and hit 'order not found'.",
            "alternative": "Leave retry disabled. Use fallback.mode='skip' if best-effort cancel is acceptable.",
        },
        {
            "pattern": "Connecting realtime Korean data directly to cancel without ThrottleNode",
            "reason": "Every tick would fire a cancel request, exhausting the rate limit and generating spurious rejections.",
            "alternative": "Use ThrottleNode or IfNode to gate the cancel trigger.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Cancel all open Korean stock orders at end of day",
            "description": "Fetch all open Korean stock orders and auto-iterate to cancel each one before market close.",
            "workflow_snippet": {
                "id": "korea_stock_cancel_all_eod",
                "name": "Korea Stock Cancel All EOD",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "kr_broker_cred"},
                    {"id": "open_orders", "type": "KoreaStockOpenOrdersNode"},
                    {"id": "cancel", "type": "KoreaStockCancelOrderNode",
                     "original_order_id": "{{ item.order_id }}",
                     "symbol": "{{ item.symbol }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "cancel"},
                    {"from": "broker", "to": "cancel"},
                ],
                "credentials": [
                    {
                        "credential_id": "kr_broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "cancel_result port: {order_id, symbol, status='cancelled'}; cancelled_order_id port: string.",
        },
        {
            "title": "Cancel a specific order and place exit market order",
            "description": "Stop-loss condition triggers: cancel the open limit buy and immediately place a market sell to exit.",
            "workflow_snippet": {
                "id": "korea_stock_cancel_and_exit",
                "name": "Korea Stock Cancel and Exit",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "kr_broker_cred"},
                    {"id": "open_orders", "type": "KoreaStockOpenOrdersNode"},
                    {"id": "cancel", "type": "KoreaStockCancelOrderNode",
                     "original_order_id": "{{ nodes.open_orders.orders[0].order_id }}",
                     "symbol": "005930"},
                    {"id": "sell", "type": "KoreaStockNewOrderNode",
                     "side": "sell",
                     "order_type": "market",
                     "order": {"symbol": "005930", "quantity": 10}},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "open_orders"},
                    {"from": "open_orders", "to": "cancel"},
                    {"from": "cancel", "to": "sell"},
                    {"from": "broker", "to": "cancel"},
                    {"from": "broker", "to": "sell"},
                ],
                "credentials": [
                    {
                        "credential_id": "kr_broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "cancel_result with status='cancelled', then sell result with status='accepted' market order.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "Requires two mandatory fields: `original_order_id` (string) and `symbol` (6-digit KRX code). "
            "No exchange field for Korean stocks. "
            "Bind original_order_id from KoreaStockOpenOrdersNode.orders[].order_id or from a prior NewOrderNode result. "
            "Requires KoreaStockBrokerNode upstream (auto-injected by executor)."
        ),
        "output_consumption": (
            "Two ports: `cancel_result` (cancellation confirmation dict) and `cancelled_order_id` (string). "
            "Chain cancel_result to TableDisplayNode for audit logging, or sequence into a new order node."
        ),
        "common_combinations": [
            "KoreaStockOpenOrdersNode → KoreaStockCancelOrderNode (cancel all open KR orders)",
            "KoreaStockCancelOrderNode → KoreaStockNewOrderNode (cancel then replace pattern)",
            "ScheduleNode → KoreaStockOpenOrdersNode → KoreaStockCancelOrderNode (EOD cleanup)",
        ],
        "pitfalls": [
            "Cancelling an already-filled Korean stock order returns a KRX error — check status via OpenOrdersNode first",
            "Paper trading is NOT supported for Korean domestic stocks — do not configure KoreaStockBrokerNode in paper mode",
            "fallback.mode='error' (default) halts workflow on cancel failure — use 'skip' for best-effort cancel-all loops",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.cancel_trigger",
        ),
        InputPort(
            name="original_order_id",
            type="string",
            description="i18n:ports.original_order_id",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="cancel_result",
            type="order_result",
            description="i18n:ports.cancel_result",
            fields=ORDER_RESULT_FIELDS,
        ),
        OutputPort(
            name="cancelled_order_id",
            type="string",
            description="i18n:ports.cancelled_order_id",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            **super().get_field_schema(),
            "original_order_id": FieldSchema(
                name="original_order_id",
                type=FieldType.STRING,
                description="i18n:fields.KoreaStockCancelOrderNode.original_order_id",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.selected_order.order_id }}",
                example="ORD20260127001",
                example_binding="{{ nodes.account.selected_order.order_id }}",
                bindable_sources=[
                    "RealAccountNode.open_orders[].order_id",
                    "KoreaStockNewOrderNode.order_result.order_id",
                ],
                expected_type="str",
            ),
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.STRING,
                description="i18n:fields.KoreaStockCancelOrderNode.symbol",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="005930",
                example="005930",
                expected_type="str",
            ),
        }
