"""
ProgramGarden Core - Risk Nodes

Risk management nodes:
- PositionSizingNode: Position size calculation
- RiskGuardNode: Daily loss limit, max position constraints
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
    category: NodeCategory = NodeCategory.RISK
    description: str = "i18n:nodes.PositionSizingNode.description"

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
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 포지션 사이징 설정 ===
            "method": FieldSchema(
                name="method",
                type=FieldType.ENUM,
                description="Position sizing method",
                default="fixed_percent",
                enum_values=["fixed_percent", "fixed_amount", "kelly", "atr_based"],
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            "max_percent": FieldSchema(
                name="max_percent",
                type=FieldType.NUMBER,
                description="Max position % of account",
                default=10.0,
                min_value=0.1,
                max_value=100.0,
                category=FieldCategory.PARAMETERS,
            ),
            "fixed_amount": FieldSchema(
                name="fixed_amount",
                type=FieldType.NUMBER,
                description="Fixed amount (for fixed_amount)",
                required=False,
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 부가 설정 ===
            "kelly_fraction": FieldSchema(
                name="kelly_fraction",
                type=FieldType.NUMBER,
                description="Kelly fraction (0.25 = 1/4 Kelly)",
                default=0.25,
                min_value=0.01,
                max_value=1.0,
                category=FieldCategory.SETTINGS,
            ),
            "atr_risk_percent": FieldSchema(
                name="atr_risk_percent",
                type=FieldType.NUMBER,
                description="ATR risk %",
                default=1.0,
                min_value=0.1,
                max_value=10.0,
                category=FieldCategory.SETTINGS,
            ),
        }


class RiskGuardNode(BaseNode):
    """
    Risk guard node

    Risk management for daily loss limit, max positions, consecutive losses
    """

    type: Literal["RiskGuardNode"] = "RiskGuardNode"
    category: NodeCategory = NodeCategory.RISK
    description: str = "i18n:nodes.RiskGuardNode.description"

    # RiskGuardNode specific config
    max_daily_loss: Optional[float] = Field(
        default=None,
        description="Max daily loss amount (negative, e.g., -500)",
    )
    max_daily_loss_percent: Optional[float] = Field(
        default=None,
        description="Max daily loss percentage (%, e.g., -5)",
    )
    max_positions: Optional[int] = Field(
        default=None,
        description="Max concurrent positions",
    )
    max_position_per_symbol: Optional[float] = Field(
        default=None,
        description="Max position percentage per symbol (%)",
    )
    max_consecutive_losses: Optional[int] = Field(
        default=None,
        description="Max consecutive losses (count)",
    )
    cooldown_after_loss_minutes: Optional[int] = Field(
        default=None,
        description="Cooldown period after loss (minutes)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.symbols",
        ),
        InputPort(
            name="account_state",
            type="account_data",
            description="i18n:ports.account_state",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="approved_symbols",
            type="symbol_list",
            description="i18n:ports.approved_symbols",
        ),
        OutputPort(
            name="blocked_symbols",
            type="symbol_list",
            description="i18n:ports.blocked_symbols",
        ),
        OutputPort(
            name="blocked_reason",
            type="string",
            description="i18n:ports.blocked_reason",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 리스크 한도 설정 ===
            "max_daily_loss": FieldSchema(
                name="max_daily_loss",
                type=FieldType.NUMBER,
                description="Max daily loss amount (e.g., -500)",
                required=False,
                category=FieldCategory.PARAMETERS,
            ),
            "max_daily_loss_percent": FieldSchema(
                name="max_daily_loss_percent",
                type=FieldType.NUMBER,
                description="Max daily loss % (e.g., -5)",
                required=False,
                category=FieldCategory.PARAMETERS,
            ),
            "max_positions": FieldSchema(
                name="max_positions",
                type=FieldType.INTEGER,
                description="Max concurrent positions",
                required=False,
                min_value=1,
                category=FieldCategory.PARAMETERS,
            ),
            "max_position_per_symbol": FieldSchema(
                name="max_position_per_symbol",
                type=FieldType.NUMBER,
                description="Max position % per symbol",
                required=False,
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 부가 설정 ===
            "max_consecutive_losses": FieldSchema(
                name="max_consecutive_losses",
                type=FieldType.INTEGER,
                description="Max consecutive losses",
                required=False,
                min_value=1,
                category=FieldCategory.SETTINGS,
            ),
            "cooldown_after_loss_minutes": FieldSchema(
                name="cooldown_after_loss_minutes",
                type=FieldType.INTEGER,
                description="Cooldown after loss (minutes)",
                required=False,
                min_value=1,
                category=FieldCategory.SETTINGS,
            ),
        }


class RiskConditionNode(BaseNode):
    """
    Risk condition evaluation node

    Evaluates risk conditions based on realtime P&L, trade count, etc.
    """

    type: Literal["RiskConditionNode"] = "RiskConditionNode"
    category: NodeCategory = NodeCategory.RISK
    description: str = "i18n:nodes.RiskConditionNode.description"

    # RiskConditionNode specific config
    rule: Literal["daily_pnl", "position_pnl", "daily_trade_count", "consecutive_losses"] = Field(
        default="daily_pnl",
        description="Risk rule to evaluate",
    )
    threshold: float = Field(
        default=-500.0,
        description="Threshold value",
    )
    operator: Literal["<=", "<", ">=", ">", "==", "!="] = Field(
        default="<=",
        description="Comparison operator",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="value",
            type="float",
            description="Value to evaluate",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="bool",
            description="i18n:ports.result",
        ),
        OutputPort(
            name="current_value",
            type="float",
            description="i18n:ports.current_value",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 모두 핵심 조건 설정 ===
            "rule": FieldSchema(
                name="rule",
                type=FieldType.ENUM,
                description="Risk rule to evaluate",
                default="daily_pnl",
                enum_values=["daily_pnl", "position_pnl", "daily_trade_count", "consecutive_losses"],
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            "threshold": FieldSchema(
                name="threshold",
                type=FieldType.NUMBER,
                description="Threshold value",
                default=-500.0,
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            "operator": FieldSchema(
                name="operator",
                type=FieldType.ENUM,
                description="Comparison operator",
                default="<=",
                enum_values=["<=", "<", ">=", ">", "==", "!="],
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
        }