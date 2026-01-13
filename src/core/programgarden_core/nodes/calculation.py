"""
ProgramGarden Core - Calculation Node

Calculation node:
- CustomPnLNode: Custom P&L calculation for advanced use cases

Note: RealAccountNode already provides basic P&L calculation via StockAccountTracker.
Use CustomPnLNode only when you need:
- Custom commission rates
- Multi-account aggregation
- Benchmark comparison
- Virtual position tracking
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class CustomPnLNode(BaseNode):
    """
    Custom P&L calculation node (optional)

    For advanced use cases that require custom P&L logic:
    - Custom commission/tax rates
    - Multi-account position aggregation
    - Benchmark (SPY, etc.) relative returns
    - Virtual/paper position tracking

    Note: For basic P&L, use RealAccountNode.positions which already
    includes pnl_rate and pnl_amount from StockAccountTracker.
    """

    type: Literal["CustomPnLNode"] = "CustomPnLNode"
    category: NodeCategory = NodeCategory.ANALYSIS
    description: str = "Custom P&L calculation for advanced use cases"

    # CustomPnLNode specific config
    mode: Literal["realtime", "batch"] = Field(
        default="realtime",
        description="Calculation mode",
    )
    commission_rate: float = Field(
        default=0.0025,
        description="Custom commission rate (default 0.25%)",
    )
    include_commission: bool = Field(
        default=True,
        description="Include commission in calculation",
    )
    base_currency: str = Field(
        default="USD",
        description="Base currency",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="tick_data",
            type="tick_data",
            description="i18n:ports.tick_data",
        ),
        InputPort(
            name="positions",
            type="position_data",
            description="i18n:ports.positions",
        ),
        InputPort(
            name="trades",
            type="trade_list",
            description="i18n:ports.trades",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="daily_pnl",
            type="float",
            description="Daily P&L (%)",
        ),
        OutputPort(
            name="position_pnl",
            type="dict",
            description="Position P&L (%)",
        ),
        OutputPort(
            name="trade_count",
            type="int",
            description="Daily trade count",
        ),
        OutputPort(
            name="consecutive_losses",
            type="int",
            description="Consecutive loss count",
        ),
        OutputPort(
            name="summary",
            type="pnl_summary",
            description="i18n:ports.summary",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 계산 설정 ===
            "mode": FieldSchema(
                name="mode",
                type=FieldType.ENUM,
                description="Calculation mode. realtime: calculate on every tick. batch: calculate periodically.",
                default="realtime",
                enum_values=["realtime", "batch"],
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="realtime",
                expected_type="str",
            ),
            "base_currency": FieldSchema(
                name="base_currency",
                type=FieldType.STRING,
                description="Base currency for P&L calculation. All values will be converted to this currency.",
                default="USD",
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="USD",
                expected_type="str",
            ),
            # === SETTINGS: 수수료 설정 ===
            "commission_rate": FieldSchema(
                name="commission_rate",
                type=FieldType.NUMBER,
                description="Custom commission rate as decimal. e.g., 0.0025 = 0.25% per trade.",
                default=0.0025,
                min_value=0,
                max_value=0.1,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=0.0025,
                expected_type="float",
            ),
            "include_commission": FieldSchema(
                name="include_commission",
                type=FieldType.BOOLEAN,
                description="Include commission in P&L calculation. When true, P&L is reduced by commission.",
                default=True,
                category=FieldCategory.SETTINGS,
                bindable=False,
            ),
        }
