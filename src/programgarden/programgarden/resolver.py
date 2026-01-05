"""
ProgramGarden - WorkflowResolver

JSON Definition → 실행 객체 변환
- Credential 바인딩
- 플러그인 레지스트리 기반 인스턴스화
- 에지 연결 검증
"""

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from pydantic import BaseModel


@dataclass
class ValidationResult:
    """워크플로우 검증 결과"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class ResolvedNode:
    """해결된 노드 (실행 준비 완료)"""

    def __init__(
        self,
        node_id: str,
        node_type: str,
        category: str,
        config: Dict[str, Any],
        plugin: Optional[Any] = None,
        plugin_params: Optional[Dict[str, Any]] = None,
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.category = category
        self.config = config
        self.plugin = plugin
        self.plugin_params = plugin_params or {}

        # 런타임 연결 (executor에서 설정)
        self.inputs: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}


class ResolvedEdge:
    """해결된 엣지 (연결 정보)"""

    def __init__(
        self,
        from_node_id: str,
        from_port: Optional[str],
        to_node_id: str,
        to_port: Optional[str],
    ):
        self.from_node_id = from_node_id
        self.from_port = from_port
        self.to_node_id = to_node_id
        self.to_port = to_port


class ResolvedWorkflow:
    """해결된 워크플로우 (실행 준비 완료)"""

    def __init__(
        self,
        workflow_id: str,
        version: str,
        nodes: Dict[str, ResolvedNode],
        edges: List[ResolvedEdge],
        execution_order: List[str],
    ):
        self.workflow_id = workflow_id
        self.version = version
        self.nodes = nodes
        self.edges = edges
        self.execution_order = execution_order


class WorkflowResolver:
    """
    워크플로우 리졸버

    Definition JSON을 실행 가능한 객체로 변환:
    1. 노드 타입 검증 및 인스턴스화
    2. 플러그인 로드 및 바인딩
    3. 엣지 연결 검증
    4. 실행 순서 계산 (토폴로지 정렬)
    """

    def __init__(self):
        # 지연 임포트로 순환 참조 방지
        pass

    def validate(self, definition: Dict[str, Any]) -> ValidationResult:
        """
        워크플로우 정의 검증

        Args:
            definition: 워크플로우 정의 (JSON dict)

        Returns:
            ValidationResult: 검증 결과
        """
        from programgarden_core import WorkflowDefinition, NodeTypeRegistry, PluginRegistry

        result = ValidationResult(is_valid=True)

        # 1. 기본 구조 검증
        try:
            workflow = WorkflowDefinition(**definition)
        except Exception as e:
            result.add_error(f"Definition 파싱 오류: {str(e)}")
            return result

        # 2. WorkflowDefinition 내장 검증
        structure_errors = workflow.validate_structure()
        for error in structure_errors:
            result.add_error(error)

        if not result.is_valid:
            return result

        # 3. 노드 타입 검증
        registry = NodeTypeRegistry()
        for node in workflow.nodes:
            node_type = node.get("type")
            if not registry.get(node_type):
                result.add_error(f"알 수 없는 노드 타입: {node_type}")

        # 4. 플러그인 검증 (플러그인 사용 노드)
        plugin_registry = PluginRegistry()
        plugin_node_types = {"ConditionNode", "NewOrderNode", "ModifyOrderNode", "CancelOrderNode"}

        for node in workflow.nodes:
            if node.get("type") in plugin_node_types:
                plugin_id = node.get("plugin")
                if not plugin_id:
                    result.add_error(f"노드 '{node.get('id')}'에 plugin이 지정되지 않았습니다")
                elif not plugin_registry.get(plugin_id):
                    result.add_warning(
                        f"플러그인 '{plugin_id}'가 레지스트리에 없습니다 (커뮤니티 로드 필요)"
                    )

        # 5. 엣지 연결 타입 호환성 검증
        # TODO: 입출력 포트 타입 매칭 검증

        return result

    def resolve(
        self,
        definition: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolvedWorkflow, ValidationResult]:
        """
        워크플로우 해결 (실행 객체 변환)

        Args:
            definition: 워크플로우 정의
            context: 실행 컨텍스트 (credential_id, symbols 등)

        Returns:
            (ResolvedWorkflow, ValidationResult)
        """
        from programgarden_core import WorkflowDefinition, NodeTypeRegistry, PluginRegistry

        # 검증
        validation = self.validate(definition)
        if not validation.is_valid:
            return None, validation

        workflow = WorkflowDefinition(**definition)
        context = context or {}

        # 노드 해결
        resolved_nodes: Dict[str, ResolvedNode] = {}
        node_registry = NodeTypeRegistry()
        plugin_registry = PluginRegistry()

        for node_def in workflow.nodes:
            node_id = node_def.get("id")
            node_type = node_def.get("type")
            category = node_def.get("category", "")

            # 설정 추출 (기본 필드 제외)
            config = {
                k: v for k, v in node_def.items()
                if k not in {"id", "type", "category", "position", "plugin", "params"}
            }

            # 플러그인 로드 (해당되는 경우)
            plugin = None
            plugin_params = {}
            if "plugin" in node_def:
                plugin_id = node_def.get("plugin")
                plugin = plugin_registry.get(plugin_id)
                plugin_params = node_def.get("params", {})

            resolved_node = ResolvedNode(
                node_id=node_id,
                node_type=node_type,
                category=category,
                config=config,
                plugin=plugin,
                plugin_params=plugin_params,
            )
            resolved_nodes[node_id] = resolved_node

        # 엣지 해결
        resolved_edges: List[ResolvedEdge] = []
        for edge in workflow.edges:
            resolved_edge = ResolvedEdge(
                from_node_id=edge.from_node_id,
                from_port=edge.from_output_name,
                to_node_id=edge.to_node_id,
                to_port=edge.to_input_name,
            )
            resolved_edges.append(resolved_edge)

        # 실행 순서 계산 (토폴로지 정렬)
        execution_order = self._topological_sort(resolved_nodes, resolved_edges)

        resolved_workflow = ResolvedWorkflow(
            workflow_id=workflow.id,
            version=workflow.version,
            nodes=resolved_nodes,
            edges=resolved_edges,
            execution_order=execution_order,
        )

        return resolved_workflow, validation

    def _topological_sort(
        self,
        nodes: Dict[str, ResolvedNode],
        edges: List[ResolvedEdge],
    ) -> List[str]:
        """
        토폴로지 정렬 (Kahn's algorithm)

        DAG의 노드를 의존성 순서대로 정렬
        """
        # 진입 차수 계산
        in_degree: Dict[str, int] = {node_id: 0 for node_id in nodes}
        adjacency: Dict[str, List[str]] = {node_id: [] for node_id in nodes}

        for edge in edges:
            if edge.to_node_id in in_degree:
                in_degree[edge.to_node_id] += 1
            if edge.from_node_id in adjacency:
                adjacency[edge.from_node_id].append(edge.to_node_id)

        # 진입 차수 0인 노드부터 시작
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            for neighbor in adjacency.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 순환 참조 체크
        if len(result) != len(nodes):
            # 순환 참조가 있으면 남은 노드 추가 (경고 발생)
            remaining = [n for n in nodes if n not in result]
            result.extend(remaining)

        return result
