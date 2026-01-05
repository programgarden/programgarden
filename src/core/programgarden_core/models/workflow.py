"""
ProgramGarden Core - Workflow 모델

워크플로우 정의 (Definition Layer)
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from programgarden_core.models.edge import Edge


class InputType(str, Enum):
    """워크플로우 입력 타입"""

    CREDENTIAL = "credential"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SYMBOL_LIST = "symbol_list"
    OBJECT = "object"


class WorkflowInput(BaseModel):
    """워크플로우 입력 파라미터 정의"""

    type: InputType = Field(..., description="입력 타입")
    required: bool = Field(default=True, description="필수 여부")
    default: Optional[Any] = Field(default=None, description="기본값")
    description: Optional[str] = Field(default=None, description="설명")


class WorkflowDefinition(BaseModel):
    """
    워크플로우 정의 (Definition Layer)

    노드와 엣지로 구성된 DAG(Directed Acyclic Graph) 형태의 전략 정의.
    버전 관리되며 재사용 가능.

    Example:
        {
            "id": "strategy-rsi-bb",
            "version": "1.0.0",
            "name": "RSI + 볼린저밴드 매수전략",
            "nodes": [...],
            "edges": [...]
        }
    """

    id: str = Field(..., description="워크플로우 고유 ID")
    version: str = Field(default="1.0.0", description="버전 (semantic versioning)")
    name: str = Field(..., description="워크플로우 이름")
    description: Optional[str] = Field(default=None, description="워크플로우 설명")

    # 입력 파라미터 정의
    inputs: Dict[str, WorkflowInput] = Field(
        default_factory=dict,
        description="워크플로우 입력 파라미터 (credential_id, symbols 등)",
    )

    # 노드와 엣지
    nodes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="노드 정의 목록",
    )
    edges: List[Edge] = Field(
        default_factory=list,
        description="엣지(연결) 정의 목록",
    )

    # 메타데이터
    tags: List[str] = Field(
        default_factory=list,
        description="태그 목록 (검색용)",
    )
    author: Optional[str] = Field(default=None, description="작성자")
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="생성 시간",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="수정 시간",
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    def get_node_ids(self) -> List[str]:
        """모든 노드 ID 반환"""
        return [node.get("id") for node in self.nodes if node.get("id")]

    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """ID로 노드 조회"""
        for node in self.nodes:
            if node.get("id") == node_id:
                return node
        return None

    def get_edges_from_node(self, node_id: str) -> List[Edge]:
        """특정 노드에서 나가는 엣지 조회"""
        return [edge for edge in self.edges if edge.from_node_id == node_id]

    def get_edges_to_node(self, node_id: str) -> List[Edge]:
        """특정 노드로 들어오는 엣지 조회"""
        return [edge for edge in self.edges if edge.to_node_id == node_id]

    def get_start_nodes(self) -> List[Dict[str, Any]]:
        """시작 노드(입력 엣지 없는 노드) 조회"""
        nodes_with_input = {edge.to_node_id for edge in self.edges}
        return [
            node for node in self.nodes
            if node.get("id") not in nodes_with_input
        ]

    def validate_structure(self) -> List[str]:
        """
        워크플로우 구조 검증

        Returns:
            검증 오류 메시지 목록 (빈 리스트면 유효)
        """
        errors = []

        # 1. 노드 ID 중복 체크
        node_ids = self.get_node_ids()
        if len(node_ids) != len(set(node_ids)):
            errors.append("중복된 노드 ID가 있습니다")

        # 2. 엣지 참조 노드 존재 체크
        node_id_set = set(node_ids)
        for edge in self.edges:
            if edge.from_node_id not in node_id_set:
                errors.append(f"엣지의 출발 노드가 존재하지 않습니다: {edge.from_node_id}")
            if edge.to_node_id not in node_id_set:
                errors.append(f"엣지의 도착 노드가 존재하지 않습니다: {edge.to_node_id}")

        # 3. StartNode 존재 체크
        start_nodes = [n for n in self.nodes if n.get("type") == "StartNode"]
        if not start_nodes:
            errors.append("StartNode가 없습니다 (Definition당 1개 필수)")
        elif len(start_nodes) > 1:
            errors.append("StartNode가 여러 개입니다 (Definition당 1개만 허용)")

        # 4. 순환 참조 체크 (간단한 DFS)
        # TODO: 본격적인 DAG 검증 구현

        return errors
