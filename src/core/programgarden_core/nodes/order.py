"""
ProgramGarden Core - Order Nodes

Order execution nodes:
- NewOrderNode: New order plugin execution
- ModifyOrderNode: Modify order plugin execution
- CancelOrderNode: Cancel order plugin execution
"""

from typing import Optional, List, Literal, Dict, Any, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    PluginNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class NewOrderNode(PluginNode):
    """
    New order plugin execution node

    Executes new order plugins such as MarketOrder, LimitOrder, ATRTrailingStop
    """

    type: Literal["NewOrderNode"] = "NewOrderNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.NewOrderNode.description"

    _inputs: List[InputPort] = [
        InputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.symbols",
        ),
        InputPort(
            name="quantity",
            type="dict",
            description="i18n:ports.quantity",
            required=False,
        ),
        InputPort(
            name="held_symbols",
            type="symbol_list",
            description="i18n:ports.held_symbols",
            required=False,
        ),
        InputPort(
            name="balance",
            type="balance_data",
            description="i18n:ports.balance",
            required=False,
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
            name="order_result",
            type="order_result",
            description="i18n:ports.order_result",
        ),
        OutputPort(
            name="order_id",
            type="string",
            description="i18n:ports.order_id",
        ),
        OutputPort(
            name="submitted_orders",
            type="order_list",
            description="i18n:ports.submitted_orders",
        ),
    ]


class ModifyOrderNode(PluginNode):
    """
    Modify order plugin execution node

    Executes modify order plugins such as TrackingPriceModifier, TurtleAdaptiveModify
    """

    type: Literal["ModifyOrderNode"] = "ModifyOrderNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.ModifyOrderNode.description"

    _inputs: List[InputPort] = [
        InputPort(
            name="target_orders",
            type="order_list",
            description="i18n:ports.target_orders",
        ),
        InputPort(
            name="price_data",
            type="market_data",
            description="i18n:ports.price_data",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="modify_result",
            type="order_result",
            description="i18n:ports.modify_result",
        ),
        OutputPort(
            name="modified_orders",
            type="order_list",
            description="i18n:ports.modified_orders",
        ),
    ]


class CancelOrderNode(PluginNode):
    """
    Cancel order plugin execution node

    Executes cancel order plugins such as PriceRangeCanceller, TimeStopCanceller
    """

    type: Literal["CancelOrderNode"] = "CancelOrderNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.CancelOrderNode.description"

    _inputs: List[InputPort] = [
        InputPort(
            name="target_orders",
            type="order_list",
            description="i18n:ports.target_orders",
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
            name="cancel_result",
            type="order_result",
            description="i18n:ports.cancel_result",
        ),
        OutputPort(
            name="cancelled_orders",
            type="order_list",
            description="i18n:ports.cancelled_orders",
        ),
    ]


class LiquidateNode(BaseNode):
    """
    Position liquidation node

    Emergency liquidation or full liquidation when risk limits are exceeded
    """

    type: Literal["LiquidateNode"] = "LiquidateNode"
    category: NodeCategory = NodeCategory.ORDER
    description: str = "i18n:nodes.LiquidateNode.description"

    # LiquidateNode specific config
    mode: Literal["all", "symbol", "losing", "profitable"] = Field(
        default="all",
        description="Liquidation mode (all, symbol: specific symbols, losing: losing positions, profitable: profitable positions)",
    )
    order_type: Literal["market", "limit"] = Field(
        default="market",
        description="Liquidation order type",
    )
    target_symbols: Optional[List[str]] = Field(
        default=None,
        description="Target symbols to liquidate (when mode='symbol')",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
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
            description="i18n:ports.result",
        ),
        OutputPort(
            name="liquidated_positions",
            type="position_list",
            description="청산된 포지션 목록",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 청산 설정 ===
            "mode": FieldSchema(
                name="mode",
                type=FieldType.ENUM,
                description="Liquidation mode",
                default="all",
                enum_values=["all", "symbol", "losing", "profitable"],
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            "target_symbols": FieldSchema(
                name="target_symbols",
                type=FieldType.ARRAY,
                description="Target symbols (when mode='symbol')",
                array_item_type=FieldType.STRING,
                required=False,
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 부가 설정 ===
            "order_type": FieldSchema(
                name="order_type",
                type=FieldType.ENUM,
                description="Order type for liquidation",
                default="market",
                enum_values=["market", "limit"],
                required=False,
                category=FieldCategory.SETTINGS,
            ),
        }
