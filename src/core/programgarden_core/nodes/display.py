"""
ProgramGarden Core - Display Node

Visualization node:
- DisplayNode: Chart/table visualization
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
    
    # Node size for inline visualization
    width: int = Field(
        default=300,
        description="Node width in pixels",
        ge=200,
        le=800,
    )
    height: int = Field(
        default=200,
        description="Node height in pixels",
        ge=150,
        le=600,
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

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === INTERNAL: 자동 감지되는 내부 설정 (사용자에게 숨겨짐) ===
            # chart_type과 title은 데이터 형태에 따라 자동 결정됨
            # === SETTINGS: 부가 설정 ===
            "width": FieldSchema(
                name="width",
                type=FieldType.INTEGER,
                description="Node width (px)",
                default=300,
                min_value=200,
                max_value=800,
                category=FieldCategory.SETTINGS,
            ),
            "height": FieldSchema(
                name="height",
                type=FieldType.INTEGER,
                description="Node height (px)",
                default=200,
                min_value=150,
                max_value=600,
                category=FieldCategory.SETTINGS,
            ),
        }