"""
ProgramGarden Core - Workflow 모델

워크플로우 정의 (Definition Layer)
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from enum import Enum

from programgarden_core.models.edge import Edge
from programgarden_core.models.resource import ResourceLimits


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


class CredentialReference(BaseModel):
    """
    워크플로우 내 Credential 참조
    
    JSON 공유 시 data의 키만 포함하고 값은 비워둠.
    Python 개발자가 직접 사용 시 data에 값을 채워 실행 가능.
    
    Example (공유용):
        {
            "id": "broker-cred",
            "type": "broker_ls",
            "name": "LS증권 API",
            "data": {"appkey": "", "appsecret": ""}
        }
    
    Example (실행용):
        {
            "id": "broker-cred",
            "type": "broker_ls", 
            "name": "LS증권 API",
            "data": {"appkey": "실제값", "appsecret": "실제값"}
        }
    """
    
    id: str = Field(..., description="Credential 고유 ID")
    type: str = Field(..., description="Credential 타입 (broker_ls, telegram 등)")
    name: Optional[str] = Field(default=None, description="표시 이름")
    description: Optional[str] = Field(default=None, description="설명")
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Credential 데이터 (공유 시 값 비움, 실행 시 값 채움)"
    )


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

    # 리소스 제한 (선택사항, 미설정 시 자동 감지)
    resource_limits: Optional[ResourceLimits] = Field(
        default=None,
        description="리소스 제한 설정 (CPU, RAM, 워커 수 등). None이면 시스템 기반 자동 감지",
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

    # Credential 참조 (워크플로우에서 사용하는 인증 정보)
    credentials: List[CredentialReference] = Field(
        default_factory=list,
        description="워크플로우에서 사용하는 Credential 목록",
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

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )

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

        # 4. 순환 참조 체크 (DAG 검증)
        cycle = self._detect_cycle()
        if cycle:
            cycle_path = " → ".join(cycle)
            errors.append(f"순환 참조가 있습니다: {cycle_path}")

        return errors

    def _detect_cycle(self) -> Optional[List[str]]:
        """
        DFS 기반 순환 참조 탐지 (3-color 알고리즘)

        Returns:
            순환 경로 리스트 (없으면 None)
            예: ["node-a", "node-b", "node-c", "node-a"]
        """
        # 인접 리스트 구성
        adjacency: Dict[str, List[str]] = {
            node.get("id"): [] for node in self.nodes if node.get("id")
        }
        for edge in self.edges:
            from_id = edge.from_node_id
            to_id = edge.to_node_id
            if from_id in adjacency:
                adjacency[from_id].append(to_id)

        # 방문 상태: 0=WHITE(미방문), 1=GRAY(방문중), 2=BLACK(완료)
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {node_id: WHITE for node_id in adjacency}
        parent: Dict[str, Optional[str]] = {node_id: None for node_id in adjacency}

        def dfs(node_id: str) -> Optional[List[str]]:
            """DFS 탐색, 순환 발견 시 경로 반환"""
            color[node_id] = GRAY

            for neighbor in adjacency.get(node_id, []):
                if neighbor not in color:
                    # 존재하지 않는 노드 참조 (다른 검증에서 처리)
                    continue

                if color[neighbor] == GRAY:
                    # 순환 발견! 경로 구성
                    cycle = [neighbor]
                    current = node_id
                    while current != neighbor:
                        cycle.append(current)
                        current = parent.get(current)
                        if current is None:
                            break
                    cycle.append(neighbor)
                    return list(reversed(cycle))

                if color[neighbor] == WHITE:
                    parent[neighbor] = node_id
                    result = dfs(neighbor)
                    if result:
                        return result

            color[node_id] = BLACK
            return None

        # 모든 노드에서 DFS 시작 (연결되지 않은 컴포넌트 처리)
        for node_id in adjacency:
            if color[node_id] == WHITE:
                result = dfs(node_id)
                if result:
                    return result

        return None
