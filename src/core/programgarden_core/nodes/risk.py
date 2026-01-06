"""
ProgramGarden Core - Risk Nodes

Risk management nodes:
- PositionSizingNode: Position size calculation
- RiskGuardNode: Daily loss limit, max position constraints
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field

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
