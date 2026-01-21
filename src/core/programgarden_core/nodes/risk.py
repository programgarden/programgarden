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
)


class PositionSizingNode(BaseNode):
    """
    Position size calculation node

    Supports various position sizing methods: Kelly, fixed ratio, ATR-based
    """

    type: Literal["PositionSizingNode"] = "PositionSizingNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.PositionSizingNode.description"

    # === 바인딩 필드 (다른 노드에서 값 수신) ===
    symbols: Any = Field(
        default=None,
        description="투자할 종목 목록 (ConditionNode.passed_symbols 또는 WatchlistNode.symbols 바인딩)",
    )
    balance: Any = Field(
        default=None,
        description="예수금/매수가능금액 (AccountNode.balance 또는 RealAccountNode.balance 바인딩)",
    )
    price_data: Any = Field(
        default=None,
        description="종목별 현재가 데이터 (MarketDataNode.price 또는 RealMarketDataNode.price 바인딩)",
    )

    # PositionSizingNode specific config
    method: Literal["fixed_percent", "fixed_amount", "kelly", "atr_based"] = Field(
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
            name="symbols",
            type="symbol_list",
            description="i18n:ports.symbols",
        ),
        InputPort(
            name="balance",
            type="balance_data",
            description="i18n:ports.balance",
        ),
        InputPort(
            name="price_data",
            type="market_data",
            description="i18n:ports.price_data",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="quantity",
            type="dict",
            description="i18n:ports.quantity",
        ),
        OutputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.symbols",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            # === INPUTS: 바인딩 또는 직접 입력 ===
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="i18n:fields.PositionSizingNode.symbols",
                required=True,
                expression_mode=ExpressionMode.BOTH,  # 바인딩 또는 직접 입력
                category=FieldCategory.PARAMETERS,
                ui_component="symbol_editor",  # 종목 에디터 UI
                example_binding="{{ nodes.conditionNode.passed_symbols }}",
                bindable_sources=["ConditionNode.passed_symbols", "WatchlistNode.symbols"],
                expected_type="symbol_list",
            ),
            "balance": FieldSchema(
                name="balance",
                type=FieldType.NUMBER,  # 숫자 입력
                description="i18n:fields.PositionSizingNode.balance",
                required=True,
                expression_mode=ExpressionMode.BOTH,  # 바인딩 또는 직접 숫자 입력
                category=FieldCategory.PARAMETERS,
                placeholder="10000000",
                example_binding="{{ nodes.account.balance }}",
                bindable_sources=["AccountNode.balance", "RealAccountNode.balance"],
                expected_type="number",
            ),
            "price_data": FieldSchema(
                name="price_data",
                type=FieldType.OBJECT,
                description="i18n:fields.PositionSizingNode.price_data",
                required=False,
                expression_mode=ExpressionMode.BOTH,  # 바인딩 또는 직접 JSON 입력
                category=FieldCategory.PARAMETERS,
                example={"AAPL": 150.0, "NVDA": 450.0},  # 직접 입력 예시
                example_binding="{{ nodes.marketData.price }}",
                bindable_sources=["MarketDataNode.price", "RealMarketDataNode.price"],
                expected_type="market_data",
            ),
            # === PARAMETERS: 핵심 포지션 사이징 설정 ===
            "method": FieldSchema(
                name="method",
                type=FieldType.ENUM,
                description="i18n:fields.PositionSizingNode.method",
                default="fixed_percent",
                enum_values=["fixed_percent", "fixed_amount", "kelly", "atr_based"],
                enum_labels={
                    "fixed_percent": "i18n:enum.PositionSizingNode.method.fixed_percent",
                    "fixed_amount": "i18n:enum.PositionSizingNode.method.fixed_amount",
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