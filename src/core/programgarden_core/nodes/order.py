"""
ProgramGarden Core - Order Nodes

상품별 주문 노드 (해외주식 3개 + 해외선물 3개 = 총 6개):
- OverseasStockNewOrderNode, OverseasStockModifyOrderNode, OverseasStockCancelOrderNode (해외주식)
- OverseasFuturesNewOrderNode, OverseasFuturesModifyOrderNode, OverseasFuturesCancelOrderNode (해외선물)

입력 구조:
- NewOrder: orders 배열 [{symbol, exchange, quantity, price}, ...]
- Modify/Cancel: original_order_id, symbol, exchange 단일 필드
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar, TYPE_CHECKING
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
    ORDER_LIST_FIELDS,
    ORDER_RESULT_FIELDS,
    SYMBOL_LIST_FIELDS,
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
    """

    category: NodeCategory = NodeCategory.ORDER

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
        ),
    ]


class BaseModifyOrderNode(BaseNode):
    """
    정정/취소 주문 노드 공통 베이스 클래스
    """

    category: NodeCategory = NodeCategory.ORDER

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

    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

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
            "side": FieldSchema(
                name="side",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockNewOrderNode.side",
                default="buy",
                enum_values=["buy", "sell"],
                enum_labels={
                    "buy": "매수 (Buy)",
                    "sell": "매도 (Sell)",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
            "order_type": FieldSchema(
                name="order_type",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockNewOrderNode.order_type",
                default="limit",
                enum_values=["market", "limit"],
                enum_labels={
                    "market": "시장가 (Market)",
                    "limit": "지정가 (Limit)",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
            "price_type": FieldSchema(
                name="price_type",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockNewOrderNode.price_type",
                default="limit",
                enum_values=["limit", "market", "LOO", "LOC", "MOO", "MOC"],
                enum_labels={
                    "limit": "지정가 (Limit)",
                    "market": "시장가 (Market)",
                    "LOO": "시초가 지정가 (Limit On Open)",
                    "LOC": "종가 지정가 (Limit On Close)",
                    "MOO": "시초가 시장가 (Market On Open)",
                    "MOC": "종가 시장가 (Market On Close)",
                },
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
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
            "price_type": FieldSchema(
                name="price_type",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasStockModifyOrderNode.price_type",
                default="limit",
                enum_values=["limit", "market"],
                enum_labels={
                    "limit": "지정가 (Limit)",
                    "market": "시장가 (Market)",
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

    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

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
            "side": FieldSchema(
                name="side",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasFuturesNewOrderNode.side",
                default="buy",
                enum_values=["buy", "sell"],
                enum_labels={
                    "buy": "매수 (Buy)",
                    "sell": "매도 (Sell)",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
            ),
            "order_type": FieldSchema(
                name="order_type",
                type=FieldType.ENUM,
                description="i18n:fields.OverseasFuturesNewOrderNode.order_type",
                default="limit",
                enum_values=["market", "limit"],
                enum_labels={
                    "market": "시장가 (Market)",
                    "limit": "지정가 (Limit)",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                expected_type="str",
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
