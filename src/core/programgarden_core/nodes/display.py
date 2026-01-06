"""
ProgramGarden Core - Display Node

Visualization node:
- DisplayNode: Chart/table visualization
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class DisplayNode(BaseNode):
    """
    Chart/table visualization node

    Supports various visualizations: line, candlestick, bar, scatter, radar, heatmap, table
    """

    type: Literal["DisplayNode"] = "DisplayNode"
    category: NodeCategory = NodeCategory.DISPLAY
    description: str = "i18n:nodes.DisplayNode.description"

    # DisplayNode specific config
    chart_type: Literal[
        "line", "candlestick", "bar", "scatter", "radar", "heatmap", "table"
    ] = Field(
        default="line",
        description="Chart type",
    )
    title: Optional[str] = Field(
        default=None,
        description="Chart title",
    )
    x_label: Optional[str] = Field(
        default=None,
        description="X-axis label",
    )
    y_label: Optional[str] = Field(
        default=None,
        description="Y-axis label",
    )
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional chart options",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="data",
            type="any",
            description="i18n:ports.data",
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="rendered",
            type="signal",
            description="Render complete signal",
        ),
    ]
