"""
ProgramGarden Core - Order Nodes

순수 주문 실행 노드 (전략 로직은 ConditionNode에서 처리):
- NewOrderNode: 신규 주문 실행 (해외주식/해외선물)
- ModifyOrderNode: 정정 주문 실행
- CancelOrderNode: 취소 주문 실행
- LiquidateNode: 포지션 청산

모든 전략/조건 계산(RSI, 수량 결정 등)은 ConditionNode/PositionSizingNode에서 처리하고,
주문 노드는 결정된 값을 받아 증권사 API를 호출하는 역할만 담당합니다.
"""

from typing import Optional, List, Literal, Dict, Any, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


# =============================================================================
# 신규 주문 노드
# =============================================================================

class NewOrderNode(BaseNode):
    """
    신규 주문 실행 노드

    ConditionNode에서 계산된 매매 대상 종목과 PositionSizingNode에서 결정된
    수량을 받아 증권사 API로 실제 주문을 실행합니다.

    지원 상품:
    - overseas_stock: 해외주식 (미국 NYSE/NASDAQ)
    - overseas_futures: 해외선물옵션

    주문 흐름:
    1. ConditionNode → passed_symbols (매수/매도 대상 종목)
    2. PositionSizingNode → quantities (종목별 수량)
    3. NewOrderNode → 실제 주문 실행
    """

    type: Literal["NewOrderNode"] = "NewOrderNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.NewOrderNode.description"

    # === 상품 및 주문 유형 선택 ===
    product: Literal["overseas_stock", "overseas_futures"] = Field(
        default="overseas_stock",
        description="상품 유형 (overseas_stock: 해외주식, overseas_futures: 해외선물)",
    )
    side: Literal["buy", "sell"] = Field(
        default="buy",
        description="매매 구분 (buy: 매수, sell: 매도)",
    )
    order_type: Literal["market", "limit"] = Field(
        default="limit",
        description="주문 유형 (market: 시장가, limit: 지정가)",
    )

    # === 해외주식 전용 필드 ===
    market_code: Optional[Literal["NYSE", "NASDAQ"]] = Field(
        default=None,
        description="[해외주식] 시장 코드 (NYSE: 뉴욕, NASDAQ: 나스닥)",
    )
    price_type: Optional[Literal["limit", "market", "LOO", "LOC", "MOO", "MOC"]] = Field(
        default="limit",
        description="[해외주식] 호가 유형 (limit: 지정가, market: 시장가, LOO/LOC/MOO/MOC: 미국 특수주문)",
    )

    # === 해외선물 전용 필드 ===
    exchange_code: Optional[str] = Field(
        default=None,
        description="[해외선물] 거래소 코드 (예: CME, EUREX)",
    )
    expiry_month: Optional[str] = Field(
        default=None,
        description="[해외선물] 만기년월 (예: 202503)",
    )

    # === 바인딩 필드 (다른 노드에서 값 수신) ===
    symbols: Any = Field(
        default=None,
        description="주문 대상 종목 목록 (ConditionNode.passed_symbols 바인딩)",
    )
    quantities: Any = Field(
        default=None,
        description="종목별 주문 수량 (PositionSizingNode.quantities 바인딩)",
    )
    prices: Any = Field(
        default=None,
        description="종목별 주문 가격 (지정가 주문 시, RealMarketDataNode.price 바인딩)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.order_trigger",
        ),
        InputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.order_symbols",
        ),
        InputPort(
            name="quantities",
            type="dict",
            description="i18n:ports.order_quantities",
        ),
        InputPort(
            name="prices",
            type="dict",
            description="i18n:ports.order_prices",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="order_result",
            type="order_result",
            description="i18n:ports.order_result",
        ),
        OutputPort(
            name="order_ids",
            type="dict",
            description="i18n:ports.order_ids",
        ),
        OutputPort(
            name="submitted_orders",
            type="order_list",
            description="i18n:ports.submitted_orders",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent
        return {
            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 핵심 주문 설정
            # ═══════════════════════════════════════════════════════════════
            "product": FieldSchema(
                name="product",
                type=FieldType.ENUM,
                description="i18n:fields.NewOrderNode.product",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                enum_labels={
                    "overseas_stock": "해외주식 (미국 NYSE/NASDAQ)",
                    "overseas_futures": "해외선물옵션 (CME, EUREX 등)",
                },
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                example="overseas_stock",
                expected_type="str",
            ),
            "side": FieldSchema(
                name="side",
                type=FieldType.ENUM,
                description="i18n:fields.NewOrderNode.side",
                default="buy",
                enum_values=["buy", "sell"],
                enum_labels={
                    "buy": "매수 (Buy)",
                    "sell": "매도 (Sell)",
                },
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                example="buy",
                expected_type="str",
            ),
            "order_type": FieldSchema(
                name="order_type",
                type=FieldType.ENUM,
                description="i18n:fields.NewOrderNode.order_type",
                default="limit",
                enum_values=["market", "limit"],
                enum_labels={
                    "market": "시장가 (Market) - 즉시 체결",
                    "limit": "지정가 (Limit) - 가격 지정",
                },
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                example="limit",
                expected_type="str",
            ),

            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 해외주식 전용 설정
            # ═══════════════════════════════════════════════════════════════
            "market_code": FieldSchema(
                name="market_code",
                type=FieldType.ENUM,
                description="i18n:fields.NewOrderNode.market_code",
                enum_values=["NYSE", "NASDAQ"],
                enum_labels={
                    "NYSE": "뉴욕증권거래소 (NYSE)",
                    "NASDAQ": "나스닥 (NASDAQ)",
                },
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                visible_when={"product": "overseas_stock"},
                example="NASDAQ",
                expected_type="str",
            ),
            "price_type": FieldSchema(
                name="price_type",
                type=FieldType.ENUM,
                description="i18n:fields.NewOrderNode.price_type",
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
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                visible_when={"product": "overseas_stock"},
                example="limit",
                expected_type="str",
            ),

            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 해외선물 전용 설정
            # ═══════════════════════════════════════════════════════════════
            "exchange_code": FieldSchema(
                name="exchange_code",
                type=FieldType.STRING,
                description="i18n:fields.NewOrderNode.exchange_code",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.TEXT_INPUT,
                visible_when={"product": "overseas_futures"},
                placeholder="CME",
                example="CME",
                expected_type="str",
            ),
            "expiry_month": FieldSchema(
                name="expiry_month",
                type=FieldType.STRING,
                description="i18n:fields.NewOrderNode.expiry_month",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.TEXT_INPUT,
                visible_when={"product": "overseas_futures"},
                placeholder="202503",
                example="202503",
                expected_type="str",
            ),

            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 바인딩 필드 (다른 노드에서 데이터 수신)
            # ═══════════════════════════════════════════════════════════════
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.STRING,
                description="i18n:fields.NewOrderNode.symbols",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.condition.passed_symbols }}",
                example=["AAPL", "TSLA", "NVDA"],
                example_binding="{{ nodes.condition.passed_symbols }}",
                bindable_sources=[
                    "ConditionNode.passed_symbols",
                    "LogicNode.passed_symbols",
                    "WatchlistNode.symbols",
                ],
                expected_type="list[str]",
            ),
            "quantities": FieldSchema(
                name="quantities",
                type=FieldType.STRING,
                description="i18n:fields.NewOrderNode.quantities",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.sizing.quantities }}",
                example={"AAPL": 10, "TSLA": 5, "NVDA": 3},
                example_binding="{{ nodes.sizing.quantities }}",
                bindable_sources=[
                    "PositionSizingNode.quantities",
                ],
                expected_type="dict[str, int]",
            ),
            "prices": FieldSchema(
                name="prices",
                type=FieldType.STRING,
                description="i18n:fields.NewOrderNode.prices",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.realMarket.price }}",
                example={"AAPL": 150.50, "TSLA": 250.00, "NVDA": 500.00},
                example_binding="{{ nodes.realMarket.price }}",
                bindable_sources=[
                    "RealMarketDataNode.price",
                    "MarketDataNode.price",
                ],
                expected_type="dict[str, float]",
            ),
        }


# =============================================================================
# 정정 주문 노드
# =============================================================================

class ModifyOrderNode(BaseNode):
    """
    정정 주문 실행 노드

    기존 미체결 주문의 가격이나 수량을 정정합니다.
    정정할 주문 정보는 RealAccountNode.open_orders에서 바인딩합니다.
    """

    type: Literal["ModifyOrderNode"] = "ModifyOrderNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.ModifyOrderNode.description"

    # === 상품 유형 선택 ===
    product: Literal["overseas_stock", "overseas_futures"] = Field(
        default="overseas_stock",
        description="상품 유형 (overseas_stock: 해외주식, overseas_futures: 해외선물)",
    )

    # === 해외주식 전용 필드 ===
    market_code: Optional[Literal["NYSE", "NASDAQ"]] = Field(
        default=None,
        description="[해외주식] 시장 코드",
    )
    price_type: Optional[Literal["limit", "market"]] = Field(
        default="limit",
        description="[해외주식] 호가 유형",
    )

    # === 해외선물 전용 필드 ===
    exchange_code: Optional[str] = Field(
        default=None,
        description="[해외선물] 거래소 코드 (예: CME, EUREX)",
    )
    expiry_month: Optional[str] = Field(
        default=None,
        description="[해외선물] 만기년월 (예: 202503)",
    )

    # === 바인딩 필드 ===
    original_order_id: Any = Field(
        default=None,
        description="정정할 원주문번호",
    )
    symbol: Any = Field(
        default=None,
        description="종목 코드",
    )
    new_quantity: Any = Field(
        default=None,
        description="정정할 수량 (변경하지 않으면 기존 수량 유지)",
    )
    new_price: Any = Field(
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
        InputPort(
            name="symbol",
            type="string",
            description="i18n:ports.symbol",
        ),
        InputPort(
            name="new_quantity",
            type="number",
            description="i18n:ports.new_quantity",
            required=False,
        ),
        InputPort(
            name="new_price",
            type="number",
            description="i18n:ports.new_price",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="modify_result",
            type="order_result",
            description="i18n:ports.modify_result",
        ),
        OutputPort(
            name="modified_order_id",
            type="string",
            description="i18n:ports.modified_order_id",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent
        return {
            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 상품 유형 선택
            # ═══════════════════════════════════════════════════════════════
            "product": FieldSchema(
                name="product",
                type=FieldType.ENUM,
                description="i18n:fields.ModifyOrderNode.product",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                enum_labels={
                    "overseas_stock": "해외주식 (미국 NYSE/NASDAQ)",
                    "overseas_futures": "해외선물옵션",
                },
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                example="overseas_stock",
                expected_type="str",
            ),
            "market_code": FieldSchema(
                name="market_code",
                type=FieldType.ENUM,
                description="i18n:fields.ModifyOrderNode.market_code",
                enum_values=["NYSE", "NASDAQ"],
                enum_labels={
                    "NYSE": "뉴욕증권거래소 (NYSE)",
                    "NASDAQ": "나스닥 (NASDAQ)",
                },
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                visible_when={"product": "overseas_stock"},
                example="NASDAQ",
                expected_type="str",
            ),
            "price_type": FieldSchema(
                name="price_type",
                type=FieldType.ENUM,
                description="i18n:fields.ModifyOrderNode.price_type",
                default="limit",
                enum_values=["limit", "market"],
                enum_labels={
                    "limit": "지정가 (Limit)",
                    "market": "시장가 (Market)",
                },
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                visible_when={"product": "overseas_stock"},
                example="limit",
                expected_type="str",
            ),

            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 해외선물 전용 설정
            # ═══════════════════════════════════════════════════════════════
            "exchange_code": FieldSchema(
                name="exchange_code",
                type=FieldType.STRING,
                description="i18n:fields.ModifyOrderNode.exchange_code",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.TEXT_INPUT,
                visible_when={"product": "overseas_futures"},
                placeholder="CME",
                example="CME",
                expected_type="str",
            ),
            "expiry_month": FieldSchema(
                name="expiry_month",
                type=FieldType.STRING,
                description="i18n:fields.ModifyOrderNode.expiry_month",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.TEXT_INPUT,
                visible_when={"product": "overseas_futures"},
                placeholder="202503",
                example="202503",
                expected_type="str",
            ),

            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 정정 대상 정보 (바인딩)
            # ═══════════════════════════════════════════════════════════════
            "original_order_id": FieldSchema(
                name="original_order_id",
                type=FieldType.STRING,
                description="i18n:fields.ModifyOrderNode.original_order_id",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.selected_order.order_id }}",
                example="ORD20260113001",
                example_binding="{{ nodes.account.selected_order.order_id }}",
                bindable_sources=[
                    "RealAccountNode.open_orders[].order_id",
                    "NewOrderNode.order_ids",
                ],
                expected_type="str",
            ),
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.STRING,
                description="i18n:fields.ModifyOrderNode.symbol",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.selected_order.symbol }}",
                example="AAPL",
                example_binding="{{ nodes.account.selected_order.symbol }}",
                bindable_sources=[
                    "RealAccountNode.open_orders[].symbol",
                ],
                expected_type="str",
            ),
            "new_quantity": FieldSchema(
                name="new_quantity",
                type=FieldType.NUMBER,
                description="i18n:fields.ModifyOrderNode.new_quantity",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="10",
                example=10,
                expected_type="int",
            ),
            "new_price": FieldSchema(
                name="new_price",
                type=FieldType.NUMBER,
                description="i18n:fields.ModifyOrderNode.new_price",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="155.50",
                example=155.50,
                example_binding="{{ nodes.realMarket.price.AAPL }}",
                bindable_sources=[
                    "RealMarketDataNode.price",
                ],
                expected_type="float",
            ),
        }


# =============================================================================
# 취소 주문 노드
# =============================================================================

class CancelOrderNode(BaseNode):
    """
    취소 주문 실행 노드

    기존 미체결 주문을 취소합니다.
    취소할 주문 정보는 RealAccountNode.open_orders에서 바인딩합니다.
    """

    type: Literal["CancelOrderNode"] = "CancelOrderNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.CancelOrderNode.description"

    # === 상품 유형 선택 ===
    product: Literal["overseas_stock", "overseas_futures"] = Field(
        default="overseas_stock",
        description="상품 유형",
    )

    # === 해외주식 전용 필드 ===
    market_code: Optional[Literal["NYSE", "NASDAQ"]] = Field(
        default=None,
        description="[해외주식] 시장 코드",
    )

    # === 해외선물 전용 필드 ===
    exchange_code: Optional[str] = Field(
        default=None,
        description="[해외선물] 거래소 코드 (예: CME, EUREX)",
    )
    expiry_month: Optional[str] = Field(
        default=None,
        description="[해외선물] 만기년월 (예: 202503)",
    )

    # === 바인딩 필드 ===
    original_order_id: Any = Field(
        default=None,
        description="취소할 원주문번호",
    )
    symbol: Any = Field(
        default=None,
        description="종목 코드",
    )

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
        InputPort(
            name="symbol",
            type="string",
            description="i18n:ports.symbol",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="cancel_result",
            type="order_result",
            description="i18n:ports.cancel_result",
        ),
        OutputPort(
            name="cancelled_order_id",
            type="string",
            description="i18n:ports.cancelled_order_id",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent
        return {
            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 상품 유형 선택
            # ═══════════════════════════════════════════════════════════════
            "product": FieldSchema(
                name="product",
                type=FieldType.ENUM,
                description="i18n:fields.CancelOrderNode.product",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                enum_labels={
                    "overseas_stock": "해외주식 (미국 NYSE/NASDAQ)",
                    "overseas_futures": "해외선물옵션",
                },
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                example="overseas_stock",
                expected_type="str",
            ),
            "market_code": FieldSchema(
                name="market_code",
                type=FieldType.ENUM,
                description="i18n:fields.CancelOrderNode.market_code",
                enum_values=["NYSE", "NASDAQ"],
                enum_labels={
                    "NYSE": "뉴욕증권거래소 (NYSE)",
                    "NASDAQ": "나스닥 (NASDAQ)",
                },
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                visible_when={"product": "overseas_stock"},
                example="NASDAQ",
                expected_type="str",
            ),

            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 해외선물 전용 설정
            # ═══════════════════════════════════════════════════════════════
            "exchange_code": FieldSchema(
                name="exchange_code",
                type=FieldType.STRING,
                description="i18n:fields.CancelOrderNode.exchange_code",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.TEXT_INPUT,
                visible_when={"product": "overseas_futures"},
                placeholder="CME",
                example="CME",
                expected_type="str",
            ),
            "expiry_month": FieldSchema(
                name="expiry_month",
                type=FieldType.STRING,
                description="i18n:fields.CancelOrderNode.expiry_month",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.TEXT_INPUT,
                visible_when={"product": "overseas_futures"},
                placeholder="202503",
                example="202503",
                expected_type="str",
            ),

            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 취소 대상 정보 (바인딩)
            # ═══════════════════════════════════════════════════════════════
            "original_order_id": FieldSchema(
                name="original_order_id",
                type=FieldType.STRING,
                description="i18n:fields.CancelOrderNode.original_order_id",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.selected_order.order_id }}",
                example="ORD20260113001",
                example_binding="{{ nodes.account.selected_order.order_id }}",
                bindable_sources=[
                    "RealAccountNode.open_orders[].order_id",
                    "NewOrderNode.order_ids",
                ],
                expected_type="str",
            ),
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.STRING,
                description="i18n:fields.CancelOrderNode.symbol",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.selected_order.symbol }}",
                example="AAPL",
                example_binding="{{ nodes.account.selected_order.symbol }}",
                bindable_sources=[
                    "RealAccountNode.open_orders[].symbol",
                ],
                expected_type="str",
            ),
        }


# =============================================================================
# 청산 노드
# =============================================================================

class LiquidateNode(BaseNode):
    """
    포지션 청산 노드

    리스크 한도 초과 시 긴급 청산 또는 전량 청산을 실행합니다.
    """

    type: Literal["LiquidateNode"] = "LiquidateNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.LiquidateNode.description"

    # === 상품 유형 선택 ===
    product: Literal["overseas_stock", "overseas_futures"] = Field(
        default="overseas_stock",
        description="상품 유형",
    )

    # === 해외주식 전용 필드 ===
    market_code: Optional[Literal["NYSE", "NASDAQ"]] = Field(
        default=None,
        description="[해외주식] 시장 코드",
    )

    # === 해외선물 전용 필드 ===
    exchange_code: Optional[str] = Field(
        default=None,
        description="[해외선물] 거래소 코드 (예: CME, EUREX)",
    )
    expiry_month: Optional[str] = Field(
        default=None,
        description="[해외선물] 만기년월 (예: 202503)",
    )

    # === 청산 설정 ===
    mode: Literal["all", "symbol", "losing", "profitable"] = Field(
        default="all",
        description="청산 모드 (all: 전체, symbol: 특정 종목, losing: 손실 포지션, profitable: 수익 포지션)",
    )
    order_type: Literal["market", "limit"] = Field(
        default="market",
        description="청산 주문 유형",
    )

    # === 바인딩 필드 ===
    target_symbols: Optional[List[str]] = Field(
        default=None,
        description="청산 대상 종목 (mode='symbol' 시)",
    )
    positions: Any = Field(
        default=None,
        description="포지션 데이터 바인딩",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.liquidate_trigger",
        ),
        InputPort(
            name="positions",
            type="position_data",
            description="i18n:ports.positions",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="liquidation_result",
            description="i18n:ports.liquidation_result",
        ),
        OutputPort(
            name="liquidated_positions",
            type="position_list",
            description="i18n:ports.liquidated_positions",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent
        return {
            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 상품 및 청산 설정
            # ═══════════════════════════════════════════════════════════════
            "product": FieldSchema(
                name="product",
                type=FieldType.ENUM,
                description="i18n:fields.LiquidateNode.product",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                enum_labels={
                    "overseas_stock": "해외주식 (미국 NYSE/NASDAQ)",
                    "overseas_futures": "해외선물옵션",
                },
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                example="overseas_stock",
                expected_type="str",
            ),

            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 해외주식 전용 설정
            # ═══════════════════════════════════════════════════════════════
            "market_code": FieldSchema(
                name="market_code",
                type=FieldType.ENUM,
                description="i18n:fields.LiquidateNode.market_code",
                enum_values=["NYSE", "NASDAQ"],
                enum_labels={
                    "NYSE": "뉴욕증권거래소 (NYSE)",
                    "NASDAQ": "나스닥 (NASDAQ)",
                },
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                visible_when={"product": "overseas_stock"},
                example="NASDAQ",
                expected_type="str",
            ),

            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 해외선물 전용 설정
            # ═══════════════════════════════════════════════════════════════
            "exchange_code": FieldSchema(
                name="exchange_code",
                type=FieldType.STRING,
                description="i18n:fields.LiquidateNode.exchange_code",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.TEXT_INPUT,
                visible_when={"product": "overseas_futures"},
                placeholder="CME",
                example="CME",
                expected_type="str",
            ),
            "expiry_month": FieldSchema(
                name="expiry_month",
                type=FieldType.STRING,
                description="i18n:fields.LiquidateNode.expiry_month",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.TEXT_INPUT,
                visible_when={"product": "overseas_futures"},
                placeholder="202503",
                example="202503",
                expected_type="str",
            ),

            "mode": FieldSchema(
                name="mode",
                type=FieldType.ENUM,
                description="i18n:fields.LiquidateNode.mode",
                default="all",
                enum_values=["all", "symbol", "losing", "profitable"],
                enum_labels={
                    "all": "전체 청산",
                    "symbol": "특정 종목만 청산",
                    "losing": "손실 포지션만 청산",
                    "profitable": "수익 포지션만 청산",
                },
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
                example="all",
                expected_type="str",
            ),
            "order_type": FieldSchema(
                name="order_type",
                type=FieldType.ENUM,
                description="i18n:fields.LiquidateNode.order_type",
                default="market",
                enum_values=["market", "limit"],
                enum_labels={
                    "market": "시장가 (즉시 체결)",
                    "limit": "지정가",
                },
                required=False,
                bindable=False,
                category=FieldCategory.SETTINGS,
                ui_component=UIComponent.SELECT,
                example="market",
                expected_type="str",
            ),

            # ═══════════════════════════════════════════════════════════════
            # PARAMETERS: 바인딩 필드
            # ═══════════════════════════════════════════════════════════════
            "target_symbols": FieldSchema(
                name="target_symbols",
                type=FieldType.ARRAY,
                description="i18n:fields.LiquidateNode.target_symbols",
                array_item_type=FieldType.STRING,
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                visible_when={"mode": "symbol"},
                placeholder="{{ nodes.riskGuard.exceeded_symbols }}",
                example=["AAPL", "TSLA"],
                example_binding="{{ nodes.riskGuard.exceeded_symbols }}",
                bindable_sources=[
                    "RiskGuardNode.exceeded_symbols",
                    "ConditionNode.passed_symbols",
                ],
                expected_type="list[str]",
            ),
            "positions": FieldSchema(
                name="positions",
                type=FieldType.STRING,
                description="i18n:fields.LiquidateNode.positions",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.positions }}",
                example=[{"symbol": "AAPL", "qty": 10, "avg_price": 150.0}],
                example_binding="{{ nodes.account.positions }}",
                bindable_sources=[
                    "RealAccountNode.positions",
                    "AccountNode.positions",
                ],
                expected_type="list[dict]",
            ),
        }
