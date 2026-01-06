"""
ProgramGarden Core - Condition Nodes

Condition evaluation nodes:
- ConditionNode: Condition plugin execution (RSI, MACD, etc.)
- LogicNode: Condition combination (and/or/xor/at_least/weighted)
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    PluginNode,
    NodeCategory,
    InputPort,
    OutputPort,
)
from programgarden_core.models.field_binding import FieldSchema, FieldType


class ConditionNode(PluginNode):
    """
    Condition plugin execution node

    Executes community plugins such as RSI, MACD, BollingerBands
    """

    type: Literal["ConditionNode"] = "ConditionNode"
    category: NodeCategory = NodeCategory.CONDITION
    description: str = "i18n:nodes.ConditionNode.description"

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
        InputPort(
            name="price_data",
            type="market_data",
            description="i18n:ports.price_data",
        ),
        InputPort(
            name="volume_data",
            type="market_data",
            description="i18n:ports.volume_data",
            required=False,
        ),
        InputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.symbols",
            required=False,
        ),
        InputPort(
            name="held_symbols",
            type="symbol_list",
            description="i18n:ports.held_symbols",
            required=False,
        ),
        InputPort(
            name="position_data",
            type="position_data",
            description="i18n:ports.positions",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="condition_result",
            description="i18n:ports.result",
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="i18n:ports.passed_symbols",
        ),
        OutputPort(
            name="failed_symbols",
            type="symbol_list",
            description="i18n:ports.failed_symbols",
        ),
        OutputPort(
            name="values",
            type="dict",
            description="i18n:ports.values",
        ),
    ]


class LogicNode(BaseNode):
    """
    Condition combination node

    Combines multiple condition results with logical operators
    """

    type: Literal["LogicNode"] = "LogicNode"
    category: NodeCategory = NodeCategory.CONDITION
    description: str = "i18n:nodes.LogicNode.description"

    # LogicNode specific config
    operator: Literal["all", "any", "not", "xor", "at_least", "at_most", "exactly", "weighted"] = Field(
        default="all",
        description="Logical operator (all=AND, any=OR, not, xor, at_least, at_most, exactly, weighted)",
    )
    threshold: Optional[int] = Field(
        default=None,
        description="Threshold value (for at_least, at_most, exactly operators)",
    )
    weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Weights (for weighted operator, weight per input ID)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="input",
            type="condition_result",
            description="i18n:ports.result",
            multiple=True,
            min_connections=2,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="condition_result",
            description="i18n:ports.result",
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="i18n:ports.passed_symbols",
        ),
    ]
    _field_schema: ClassVar[Dict[str, FieldSchema]] = {
        "operator": FieldSchema(
            name="operator",
            type=FieldType.ENUM,
            description="Logical operator",
            default="all",
            enum_values=["all", "any", "not", "xor", "at_least", "at_most", "exactly", "weighted"],
            required=True,
            bindable=False,
        ),
        "threshold": FieldSchema(
            name="threshold",
            type=FieldType.INTEGER,
            description="Threshold value (for at_least, at_most, exactly operators)",
            bindable=True,
            expression_enabled=True,
        ),
        "weights": FieldSchema(
            name="weights",
            type=FieldType.OBJECT,
            description="Weights (for weighted operator)",
            bindable=False,
        ),
    }
