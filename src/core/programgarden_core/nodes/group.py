"""
ProgramGarden Core - Group 노드

서브플로우 노드:
- GroupNode: 재사용 가능한 서브플로우
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class GroupNode(BaseNode):
    """
    재사용 가능한 서브플로우 노드

    여러 노드를 그룹화하여 재사용 가능한 서브플로우로 만듦.
    $input.*, $output.* 인터페이스로 외부와 데이터 교환.
    무제한 중첩 허용.
    """

    type: Literal["GroupNode"] = "GroupNode"
    category: NodeCategory = NodeCategory.GROUP

    # GroupNode 전용 설정
    workflow_id: Optional[str] = Field(
        default=None,
        description="참조할 서브 워크플로우 ID (외부 정의 참조 시)",
    )
    inline_nodes: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="인라인 노드 정의 (그룹 내 직접 정의 시)",
    )
    inline_edges: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="인라인 엣지 정의 (그룹 내 직접 정의 시)",
    )
    input_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="입력 매핑 ($input.* → 내부 노드)",
    )
    output_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="출력 매핑 (내부 노드 → $output.*)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="$input",
            type="any",
            description="그룹 입력 (동적, input_mapping으로 정의)",
            multiple=True,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="$output",
            type="any",
            description="그룹 출력 (동적, output_mapping으로 정의)",
        ),
    ]
