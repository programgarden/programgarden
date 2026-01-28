"""
ProgramGarden Core - Risk Nodes

Risk management nodes:
- PositionSizingNode: Position size calculation
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
    QUANTITY_FIELDS,
    SYMBOL_LIST_FIELDS,
)


class PositionSizingNode(BaseNode):
    """
    Position size calculation node (단일 종목)

    Item-based execution:
    - Input: symbol (단일 종목), balance, market_data (해당 종목 시세)
    - Output: order (해당 종목의 주문 정보 {symbol, exchange, quantity, price})

    Supports various position sizing methods: Kelly, fixed ratio, ATR-based
    """

    type: Literal["PositionSizingNode"] = "PositionSizingNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.PositionSizingNode.description"

    # === 바인딩 필드 (Item-based execution) ===
    symbol: Any = Field(
        default=None,
        description="단일 종목 {exchange, symbol} (SplitNode.item 또는 ConditionNode.result 바인딩)",
    )
    balance: Any = Field(
        default=None,
        description="예수금/매수가능금액 (AccountNode.balance 또는 RealAccountNode.balance 바인딩)",
    )
    market_data: Any = Field(
        default=None,
        description="해당 종목 시세 데이터 (MarketDataNode.value 바인딩)",
    )

    # PositionSizingNode specific config
    method: Literal["fixed_percent", "fixed_amount", "fixed_quantity", "kelly", "atr_based"] = Field(
        default="fixed_percent",
        description="Position sizing method",
    )
    max_percent: float = Field(
        default=10.0,
        description="Max position percentage of account (%)",
    )
    fixed_amount: Optional[float] = Field(
        default=None,
        description="Fixed amount (for fixed_amount method)",
    )
    fixed_quantity: Optional[int] = Field(
        default=1,
        description="Fixed quantity per symbol (for fixed_quantity method)",
    )
    kelly_fraction: float = Field(
        default=0.25,
        description="Kelly fraction adjustment (for kelly method, conservative 1/4)",
    )
    atr_risk_percent: float = Field(
        default=1.0,
        description="ATR-based risk percentage (for atr_based method)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="symbol",
            type="symbol",
            description="i18n:ports.symbol",
        ),
        InputPort(
            name="balance",
            type="balance_data",
            description="i18n:ports.balance",
        ),
        InputPort(
            name="market_data",
            type="market_data",
            description="i18n:ports.market_data",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="order",
            type="order",
            description="i18n:ports.order",
            fields=[
                {"name": "symbol", "type": "string", "description": "종목코드"},
                {"name": "exchange", "type": "string", "description": "거래소 코드"},
                {"name": "quantity", "type": "number", "description": "주문 수량"},
                {"name": "price", "type": "number", "description": "주문 가격"},
            ],
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === INPUTS: Item-based 바인딩 ===
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                description="i18n:fields.PositionSizingNode.symbol",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"exchange": "NASDAQ", "symbol": "AAPL"},
                example_binding="{{ nodes.condition.result }}",
                bindable_sources=[
                    "ConditionNode.result",
                    "SplitNode.item",
                ],
                expected_type="{exchange: str, symbol: str}",
                object_schema=[
                    {"name": "exchange", "type": "STRING", "label": "i18n:fields.PositionSizingNode.symbol.exchange", "required": True},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.PositionSizingNode.symbol.symbol", "required": True},
                ],
                help_text="i18n:fields.PositionSizingNode.symbol.help_text",
            ),
            "balance": FieldSchema(
                name="balance",
                type=FieldType.NUMBER,
                description="i18n:fields.PositionSizingNode.balance",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="10000000",
                example_binding="{{ nodes.account.balance }}",
                bindable_sources=["AccountNode.balance", "RealAccountNode.balance"],
                expected_type="number",
            ),
            "market_data": FieldSchema(
                name="market_data",
                type=FieldType.OBJECT,
                description="i18n:fields.PositionSizingNode.market_data",
                required=False,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"symbol": "AAPL", "exchange": "NASDAQ", "price": 150.0},
                example_binding="{{ nodes.marketdata.value }}",
                bindable_sources=[
                    "OverseasStockMarketDataNode.value",
                    "OverseasFuturesMarketDataNode.value",
                ],
                expected_type="{symbol: str, exchange: str, price: float, ...}",
                help_text="i18n:fields.PositionSizingNode.market_data.help_text",
            ),
            # === PARAMETERS: 핵심 포지션 사이징 설정 ===
            "method": FieldSchema(
                name="method",
                type=FieldType.ENUM,
                description="i18n:fields.PositionSizingNode.method",
                default="fixed_percent",
                enum_values=["fixed_percent", "fixed_amount", "fixed_quantity", "kelly", "atr_based"],
                enum_labels={
                    "fixed_percent": "i18n:enum.PositionSizingNode.method.fixed_percent",
                    "fixed_amount": "i18n:enum.PositionSizingNode.method.fixed_amount",
                    "fixed_quantity": "i18n:enum.PositionSizingNode.method.fixed_quantity",
                    "kelly": "i18n:enum.PositionSizingNode.method.kelly",
                    "atr_based": "i18n:enum.PositionSizingNode.method.atr_based",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
            ),
            # fixed_percent에서는 투자 비율, kelly/atr_based에서는 상한선
            # fixed_amount에서는 불필요 (금액 고정이므로 비율 제한 없음)
            "max_percent": FieldSchema(
                name="max_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.PositionSizingNode.max_percent",
                default=10.0,
                min_value=0.1,
                max_value=100.0,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                visible_when={"method": ["fixed_percent", "kelly", "atr_based"]},
            ),
            # fixed_amount 방식에서만 사용
            "fixed_amount": FieldSchema(
                name="fixed_amount",
                type=FieldType.NUMBER,
                description="i18n:fields.PositionSizingNode.fixed_amount",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                visible_when={"method": "fixed_amount"},
            ),
            # fixed_quantity 방식에서만 사용
            "fixed_quantity": FieldSchema(
                name="fixed_quantity",
                type=FieldType.INTEGER,
                description="i18n:fields.PositionSizingNode.fixed_quantity",
                default=1,
                min_value=1,
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                visible_when={"method": "fixed_quantity"},
            ),
            # === SETTINGS: 부가 설정 ===
            # kelly 방식에서만 사용
            "kelly_fraction": FieldSchema(
                name="kelly_fraction",
                type=FieldType.NUMBER,
                description="i18n:fields.PositionSizingNode.kelly_fraction",
                default=0.25,
                min_value=0.01,
                max_value=1.0,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.SETTINGS,
                visible_when={"method": "kelly"},
            ),
            # atr_based 방식에서만 사용
            "atr_risk_percent": FieldSchema(
                name="atr_risk_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.PositionSizingNode.atr_risk_percent",
                default=1.0,
                min_value=0.1,
                max_value=10.0,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.SETTINGS,
                visible_when={"method": "atr_based"},
            ),
        }