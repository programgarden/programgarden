"""
ProgramGarden Core - Display 노드

시각화 노드:
- DisplayNode: 차트/테이블 시각화
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
    차트/테이블 시각화 노드

    line, candlestick, bar, scatter, radar, heatmap, table 등 다양한 시각화 지원
    """

    type: Literal["DisplayNode"] = "DisplayNode"
    category: NodeCategory = NodeCategory.DISPLAY

    # DisplayNode 전용 설정
    chart_type: Literal[
        "line", "candlestick", "bar", "scatter", "radar", "heatmap", "table"
    ] = Field(
        default="line",
        description="차트 유형",
    )
    title: Optional[str] = Field(
        default=None,
        description="차트 제목",
    )
    x_label: Optional[str] = Field(
        default=None,
        description="X축 레이블",
    )
    y_label: Optional[str] = Field(
        default=None,
        description="Y축 레이블",
    )
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="차트별 추가 옵션",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="data",
            type="any",
            description="시각화할 데이터",
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="시각화 업데이트 트리거",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="rendered",
            type="signal",
            description="렌더링 완료 신호",
        ),
    ]
