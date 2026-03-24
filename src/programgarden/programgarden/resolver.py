"""
ProgramGarden - WorkflowResolver

JSON Definition → Execution object conversion
- Credential binding
- Plugin registry-based instantiation
- Edge connection validation
"""

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from pydantic import BaseModel


@dataclass
class ValidationResult:
    """Workflow validation result"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class ResolvedNode:
    """Resolved node (ready for execution)"""

    def __init__(
        self,
        node_id: str,
        node_type: str,
        category: str,
        config: Dict[str, Any],
        plugin: Optional[Any] = None,
        fields: Optional[Dict[str, Any]] = None,
        product_scope: str = "all",
        broker_provider: str = "all",
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.category = category
        self.config = config
        self.plugin = plugin
        self.fields = fields or {}
        self.product_scope = product_scope
        self.broker_provider = broker_provider

        # Runtime connections (set by executor)
        self.inputs: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}


class ResolvedEdge:
    """Resolved edge"""

    def __init__(
        self,
        from_node_id: str,
        to_node_id: str,
        edge_type: str = "main",
        from_port: str = None,
    ):
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id
        self.edge_type = edge_type
        self.from_port = from_port

    @property
    def is_dag_edge(self) -> bool:
        """DAG topological sort에 포함되는 엣지인지 여부"""
        return self.edge_type == "main"


class ResolvedWorkflow:
    """Resolved workflow (ready for execution)"""

    def __init__(
        self,
        workflow_id: str,
        version: str,
        nodes: Dict[str, ResolvedNode],
        edges: List[ResolvedEdge],
        execution_order: List[str],
        tool_edges: Optional[List[ResolvedEdge]] = None,
        ai_model_edges: Optional[List[ResolvedEdge]] = None,
    ):
        self.workflow_id = workflow_id
        self.version = version
        self.nodes = nodes
        self.edges = edges
        self.execution_order = execution_order
        self.tool_edges = tool_edges or []
        self.ai_model_edges = ai_model_edges or []

    def get_tool_node_ids(self, agent_node_id: str) -> List[str]:
        """특정 AIAgentNode에 tool 엣지로 연결된 노드 ID 목록"""
        return [e.from_node_id for e in self.tool_edges if e.to_node_id == agent_node_id]

    def get_ai_model_node_id(self, agent_node_id: str) -> Optional[str]:
        """특정 AIAgentNode에 ai_model 엣지로 연결된 LLMModelNode ID"""
        for e in self.ai_model_edges:
            if e.to_node_id == agent_node_id:
                return e.from_node_id
        return None


class WorkflowResolver:
    """
    Workflow resolver

    Converts Definition JSON to executable objects:
    1. Node type validation and instantiation
    2. Plugin loading and binding
    3. Edge connection validation
    4. Execution order calculation (topological sort)
    """

    def __init__(self):
        # Lazy import to prevent circular references
        pass

    def validate(self, definition: Dict[str, Any]) -> ValidationResult:
        """
        Validate workflow definition

        Args:
            definition: Workflow definition (JSON dict)

        Returns:
            ValidationResult: Validation result
        """
        from programgarden_core import WorkflowDefinition, NodeTypeRegistry, PluginRegistry

        result = ValidationResult(is_valid=True)

        # 1. Basic structure validation
        try:
            workflow = WorkflowDefinition(**definition)
        except Exception as e:
            result.add_error(f"Definition parsing error: {str(e)}")
            return result

        # 2. WorkflowDefinition built-in validation
        structure_errors = workflow.validate_structure()
        for error in structure_errors:
            result.add_error(error)

        # 3. Reserved node ID validation
        RESERVED_NODE_IDS = {"nodes", "input", "context"}
        for node in workflow.nodes:
            node_id = node.get("id")
            if node_id in RESERVED_NODE_IDS:
                result.add_error(
                    f"Node ID '{node_id}' is reserved. "
                    f"Cannot use: {', '.join(sorted(RESERVED_NODE_IDS))}"
                )

        # 4. Node type validation (including dynamic nodes)
        from programgarden_core.registry import DynamicNodeRegistry, is_dynamic_node_type
        registry = NodeTypeRegistry()
        dynamic_registry = DynamicNodeRegistry()

        for node in workflow.nodes:
            node_type = node.get("type")
            node_id = node.get("id")

            # 일반 노드 체크
            if registry.get(node_type):
                continue

            # 동적 노드 체크 (Dynamic_ prefix)
            if is_dynamic_node_type(node_type):
                if not dynamic_registry.get_schema(node_type):
                    result.add_error(
                        f"Dynamic node schema not registered: {node_type}. "
                        "Call register_dynamic_schemas() first."
                    )
                    continue

                # 동적 노드의 credential_id 사용 차단
                if node.get("credential_id"):
                    result.add_error(
                        f"Dynamic node '{node_id}' cannot use credential_id. "
                        "Credential access is blocked for dynamic nodes for security."
                    )
                continue

            # 둘 다 없으면 에러
            result.add_error(f"Unknown node type: {node_type}")

        # 4. Plugin validation (for plugin-using nodes)
        # 주문 노드는 orders 배열에 price가 포함되어 있어 plugin 선택사항
        plugin_registry = PluginRegistry()
        plugin_node_types = {"ConditionNode"}

        for node in workflow.nodes:
            if node.get("type") in plugin_node_types:
                plugin_id = node.get("plugin")
                if not plugin_id:
                    result.add_error(f"Node '{node.get('id')}' does not have a plugin specified")
                elif not plugin_registry.get(plugin_id):
                    result.add_warning(
                        f"Plugin '{plugin_id}' not found in registry (community load required)"
                    )

        # 5. 노드 연결 규칙 검증 (실시간 → 위험 노드 직결 차단)
        self._validate_connection_rules(workflow, registry, result)

        # 6. 노드-브로커 호환성 검증 (product_scope + broker_provider 자동 매칭)
        self._validate_node_broker_compatibility(workflow, registry, result)

        # 7. BrokerNode 중복 검증 (같은 product_scope는 1개만 허용)
        self._validate_broker_nodes(workflow, registry, result)

        # 8. 엣지 참조 검증 (존재하지 않는 노드 참조 차단)
        self._validate_edge_references(workflow, result)

        # 9. 표현식 바인딩 참조 검증 ({{ nodes.xxx }} → xxx가 실제 존재하는지)
        self._validate_expression_references(workflow, result)

        # 10. credential_id 참조 검증
        self._validate_credential_references(workflow, result)

        return result

    def _validate_connection_rules(
        self,
        workflow,
        registry,
        result: ValidationResult,
    ) -> None:
        """
        노드 연결 규칙 검증.

        각 main 엣지에 대해 타겟 노드의 _connection_rules를 확인하고,
        실시간 노드에서 위험 노드로의 직접 연결이 있으면 에러/경고를 추가.

        검증 대상: main 엣지만 (tool, ai_model 엣지는 데이터 흐름이 아님)
        """
        from programgarden_core.models.edge import EdgeType
        from programgarden_core.models.connection_rule import ConnectionSeverity

        # 노드 ID → 노드 타입 매핑
        node_id_to_type_map = {
            node.get("id"): node.get("type")
            for node in workflow.nodes
        }

        for edge in workflow.edges:
            # main 엣지만 검증 (tool/ai_model은 실행 순서 아님)
            if edge.edge_type != EdgeType.MAIN:
                continue

            target_node_type = node_id_to_type_map.get(edge.to_node_id)
            source_node_type = node_id_to_type_map.get(edge.from_node_id)

            if not target_node_type or not source_node_type:
                continue

            # 타겟 노드 클래스에서 connection_rules 확인
            target_node_class = registry.get(target_node_type)
            if not target_node_class:
                continue

            connection_rules = getattr(target_node_class, '_connection_rules', [])
            for rule in connection_rules:
                if source_node_type in rule.deny_direct_from:
                    violation_message = (
                        f"'{edge.from_node_id}' ({source_node_type}) → "
                        f"'{edge.to_node_id}' ({target_node_type}) "
                        f"직접 연결이 차단됩니다."
                    )
                    if rule.required_intermediate:
                        violation_message += (
                            f" '{rule.required_intermediate}'를 사이에 배치하세요."
                        )
                    if rule.reason:
                        violation_message += f" 이유: {rule.reason}"

                    if rule.severity == ConnectionSeverity.ERROR:
                        result.add_error(violation_message)
                    else:
                        result.add_warning(violation_message)

    @staticmethod
    def _is_broker_node(registry, node_type: str) -> bool:
        """BrokerNode 계열인지 스키마를 통해 확인 (connection 출력 포트가 있는 노드)"""
        schema = registry.get_schema(node_type)
        if not schema:
            return False
        outputs = schema.outputs or []
        return any(
            (o.get("type") if isinstance(o, dict) else getattr(o, "type", "")) == "broker_connection"
            for o in outputs
        )

    def _validate_edge_references(
        self,
        workflow,
        result: ValidationResult,
    ) -> None:
        """엣지가 참조하는 노드 ID가 실제 존재하는지 검증."""
        node_ids = {n.get("id") for n in workflow.nodes}

        for edge in workflow.edges:
            from_raw = getattr(edge, "from_node", "") or ""
            to_raw = getattr(edge, "to_node", "") or ""

            # dot notation 지원: "if1.true" → node_id = "if1"
            from_id = from_raw.split(".")[0] if from_raw else ""
            to_id = to_raw.split(".")[0] if to_raw else ""

            if from_id and from_id not in node_ids:
                result.add_error(
                    f"Edge 'from' references non-existent node '{from_id}'. "
                    f"Available nodes: [{', '.join(sorted(node_ids))}]"
                )
            if to_id and to_id not in node_ids:
                result.add_error(
                    f"Edge 'to' references non-existent node '{to_id}'. "
                    f"Available nodes: [{', '.join(sorted(node_ids))}]"
                )

    def _validate_expression_references(
        self,
        workflow,
        result: ValidationResult,
    ) -> None:
        """
        {{ nodes.xxx.yyy }} 표현식에서 참조하는 노드 ID가 실제 존재하는지 검증.
        AI 워크플로우 빌더가 잘못된 노드 참조를 사전에 감지할 수 있도록 함.
        """
        import re

        node_ids = {n.get("id") for n in workflow.nodes}
        # {{ nodes.xxx 또는 {{ nodes.xxx.yyy }} 패턴
        expr_pattern = re.compile(r"\{\{\s*nodes\.(\w+)")
        skip_keys = {"id", "type", "category", "position"}

        def find_refs(value, node_id: str, field_path: str):
            if isinstance(value, str):
                for match in expr_pattern.finditer(value):
                    ref_id = match.group(1)
                    if ref_id not in node_ids:
                        result.add_error(
                            f"Node '{node_id}' field '{field_path}' references "
                            f"non-existent node '{ref_id}'. "
                            f"Available nodes: [{', '.join(sorted(node_ids))}]"
                        )
            elif isinstance(value, dict):
                for k, v in value.items():
                    find_refs(v, node_id, f"{field_path}.{k}")
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    find_refs(v, node_id, f"{field_path}[{i}]")

        for node in workflow.nodes:
            node_id = node.get("id", "")
            for key, value in node.items():
                if key in skip_keys:
                    continue
                find_refs(value, node_id, key)

    def _validate_credential_references(
        self,
        workflow,
        result: ValidationResult,
    ) -> None:
        """노드의 credential_id가 credentials 목록에 정의되어 있는지 검증."""
        defined_creds = set()
        for cred in (workflow.credentials or []):
            cid = getattr(cred, "credential_id", None) or (cred.get("credential_id") if isinstance(cred, dict) else None)
            if cid:
                defined_creds.add(cid)

        for node in workflow.nodes:
            cred_id = node.get("credential_id")
            if cred_id and cred_id not in defined_creds:
                result.add_error(
                    f"Node '{node.get('id')}' credential_id '{cred_id}' "
                    f"is not defined in credentials. "
                    f"Defined credentials: [{', '.join(sorted(defined_creds)) if defined_creds else 'none'}]"
                )

    def _validate_broker_nodes(
        self,
        workflow,
        registry,
        result: ValidationResult,
    ) -> None:
        """
        같은 product_scope의 BrokerNode가 중복되지 않는지 검증.

        - OverseasStockBrokerNode는 1개만 허용
        - OverseasFuturesBrokerNode는 1개만 허용
        - 다른 product_scope끼리는 공존 가능 (overseas_stock + overseas_futures)
        """
        from programgarden_core.nodes.base import ProductScope

        broker_scopes: Dict[str, str] = {}  # {product_scope.value: node_id}

        for node in workflow.nodes:
            node_type = node.get("type")
            node_class = registry.get(node_type)
            if not node_class:
                continue

            # BrokerNode 계열인지 스키마로 확인
            if not self._is_broker_node(registry, node_type):
                continue

            node_id = node.get("id")
            scope = getattr(node_class, '_product_scope', ProductScope.ALL)

            if scope == ProductScope.ALL:
                continue

            scope_value = scope.value
            if scope_value in broker_scopes:
                product_label = "overseas_stock" if scope == ProductScope.STOCK else "overseas_futures"
                result.add_error(
                    f"Duplicate {product_label} broker node. "
                    f"Only one allowed: '{broker_scopes[scope_value]}' and '{node_id}'. Remove one."
                )
            else:
                broker_scopes[scope_value] = node_id

    def _validate_node_broker_compatibility(
        self,
        workflow,
        registry,
        result: ValidationResult,
    ) -> None:
        """
        노드의 (product_scope, broker_provider) 조합이
        워크플로우에 존재하는 BrokerNode와 호환되는지 검증.

        검증 규칙:
        1. product_scope 매칭: OverseasStockMarketDataNode → OverseasStockBrokerNode 필요
        2. broker_provider 매칭: LS증권 노드 → LS증권 브로커 필요
        3. ProductScope.ALL / BrokerProvider.ALL은 모든 것과 매칭 (범용 노드)
        """
        from programgarden_core.nodes.base import ProductScope, BrokerProvider

        # 1. 워크플로우의 BrokerNode에서 (product_scope, broker_provider) 쌍 수집
        available_brokers: Dict[str, str] = {}  # {product_scope.value: broker_provider.value}
        for node in workflow.nodes:
            node_type = node.get("type")
            node_class = registry.get(node_type)
            if not node_class:
                continue

            scope = getattr(node_class, '_product_scope', ProductScope.ALL)
            if scope == ProductScope.ALL:
                continue

            # BrokerNode 계열인지 스키마로 확인
            if self._is_broker_node(registry, node_type):
                provider = getattr(node_class, '_broker_provider', BrokerProvider.ALL)
                available_brokers[scope.value] = provider.value

        # 2. 각 노드의 (product_scope, broker_provider)가 매칭되는지 확인
        for node in workflow.nodes:
            node_type = node.get("type")
            node_class = registry.get(node_type)
            if not node_class:
                continue

            scope = getattr(node_class, '_product_scope', ProductScope.ALL)
            provider = getattr(node_class, '_broker_provider', BrokerProvider.ALL)

            # 범용 노드는 검증 불필요
            if scope == ProductScope.ALL:
                continue

            # BrokerNode 자체는 검증 대상 아님
            if self._is_broker_node(registry, node_type):
                continue

            # product_scope 매칭 확인
            if scope.value not in available_brokers:
                product_label = "overseas_stock" if scope == ProductScope.STOCK else "overseas_futures"
                broker_node = "OverseasStockBrokerNode" if scope == ProductScope.STOCK else "OverseasFuturesBrokerNode"
                result.add_error(
                    f"Node '{node.get('id')}' ({node_type}) requires {product_label} broker. "
                    f"Add {broker_node} to the workflow."
                )
                continue

            # broker_provider 매칭 확인 (ALL은 모든 것과 매칭)
            if provider != BrokerProvider.ALL:
                broker_provider_value = available_brokers[scope.value]
                if broker_provider_value != BrokerProvider.ALL.value and broker_provider_value != provider.value:
                    result.add_error(
                        f"Node '{node.get('id')}' ({node_type}) requires "
                        f"'{provider.value}' broker provider, but workflow has "
                        f"'{broker_provider_value}' broker configured."
                    )

    def resolve(
        self,
        definition: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolvedWorkflow, ValidationResult]:
        """
        Resolve workflow (convert to execution objects)

        Args:
            definition: Workflow definition
            context: Execution context (credential_id, symbols, etc.)

        Returns:
            (ResolvedWorkflow, ValidationResult)
        """
        from programgarden_core import WorkflowDefinition, NodeTypeRegistry, PluginRegistry

        # Validate
        validation = self.validate(definition)
        if not validation.is_valid:
            return None, validation

        workflow = WorkflowDefinition(**definition)
        context = context or {}

        # Resolve nodes
        resolved_nodes: Dict[str, ResolvedNode] = {}
        node_registry = NodeTypeRegistry()
        plugin_registry = PluginRegistry()

        from programgarden_core.registry import DynamicNodeRegistry, is_dynamic_node_type
        dynamic_registry = DynamicNodeRegistry()

        for node_def in workflow.nodes:
            node_id = node_def.get("id")
            node_type = node_def.get("type")
            category = node_def.get("category", "")

            # 동적 노드면 스키마에서 category 가져오기
            if is_dynamic_node_type(node_type):
                dynamic_schema = dynamic_registry.get_schema(node_type)
                if dynamic_schema and not category:
                    category = dynamic_schema.category

            # Plugin node types where fields should be extracted separately
            # 주문 노드는 plugin 선택사항 (orders에 price 포함)
            PLUGIN_NODE_TYPES = {"ConditionNode"}

            # Extract config (exclude base fields)
            # For plugin nodes, exclude "fields" from config (will be passed separately)
            # But keep "plugin" in config for plugin_id lookup
            if node_type in PLUGIN_NODE_TYPES:
                config = {
                    k: v for k, v in node_def.items()
                    if k not in {"id", "type", "category", "position", "fields"}  # "plugin" 유지
                }
            else:
                config = {
                    k: v for k, v in node_def.items()
                    if k not in {"id", "type", "category", "position", "plugin"}
                }

            # Load plugin (if applicable)
            plugin = None
            fields = {}
            if "plugin" in node_def:
                plugin_id = node_def.get("plugin")
                plugin = plugin_registry.get(plugin_id)
                fields = node_def.get("fields", {})

            # product_scope, broker_provider 추출
            # 동적 노드는 범용 (all)으로 처리
            node_class = node_registry.get(node_type)
            p_scope = "all"
            b_provider = "all"
            if node_class:
                p_scope = getattr(node_class, '_product_scope', None)
                p_scope = p_scope.value if p_scope else "all"
                b_provider = getattr(node_class, '_broker_provider', None)
                b_provider = b_provider.value if b_provider else "all"

            resolved_node = ResolvedNode(
                node_id=node_id,
                node_type=node_type,
                category=category,
                config=config,
                plugin=plugin,
                fields=fields,
                product_scope=p_scope,
                broker_provider=b_provider,
            )
            resolved_nodes[node_id] = resolved_node

        # Resolve edges - DAG/tool/ai_model 분리
        dag_edges: List[ResolvedEdge] = []
        tool_edges: List[ResolvedEdge] = []
        ai_model_edges: List[ResolvedEdge] = []

        for edge in workflow.edges:
            edge_type_str = edge.edge_type.value if hasattr(edge.edge_type, 'value') else str(edge.edge_type)
            resolved_edge = ResolvedEdge(
                from_node_id=edge.from_node_id,
                to_node_id=edge.to_node_id,
                edge_type=edge_type_str,
                from_port=getattr(edge, 'from_port', None),
            )
            if edge.is_dag_edge:
                dag_edges.append(resolved_edge)
            elif edge_type_str == "tool":
                tool_edges.append(resolved_edge)
            elif edge_type_str == "ai_model":
                ai_model_edges.append(resolved_edge)

        # Calculate execution order (topological sort) - DAG 엣지만 사용
        execution_order = self._topological_sort(resolved_nodes, dag_edges)

        resolved_workflow = ResolvedWorkflow(
            workflow_id=workflow.id,
            version=workflow.version,
            nodes=resolved_nodes,
            edges=dag_edges,
            execution_order=execution_order,
            tool_edges=tool_edges,
            ai_model_edges=ai_model_edges,
        )

        return resolved_workflow, validation

    def _topological_sort(
        self,
        nodes: Dict[str, ResolvedNode],
        edges: List[ResolvedEdge],
    ) -> List[str]:
        """
        Topological sort (DFS-based)

        Sorts DAG nodes by dependency order using depth-first search.
        Executes one path completely before moving to the next path.
        
        Algorithm: DFS pre-order traversal that respects dependency constraints.
        When visiting a node, first ensure all its dependencies are visited.
        """
        # Build adjacency list and reverse adjacency (dependencies)
        adjacency: Dict[str, List[str]] = {node_id: [] for node_id in nodes}
        dependencies: Dict[str, List[str]] = {node_id: [] for node_id in nodes}
        in_degree: Dict[str, int] = {node_id: 0 for node_id in nodes}

        for edge in edges:
            if edge.from_node_id in adjacency:
                adjacency[edge.from_node_id].append(edge.to_node_id)
            if edge.to_node_id in dependencies:
                dependencies[edge.to_node_id].append(edge.from_node_id)
            if edge.to_node_id in in_degree:
                in_degree[edge.to_node_id] += 1

        visited = set()
        result = []

        def visit(node_id: str) -> None:
            """Visit a node, ensuring all dependencies are visited first."""
            if node_id in visited:
                return
            # First, visit all dependencies (pre-requisites)
            for dep in dependencies.get(node_id, []):
                visit(dep)
            # Mark as visited and add to result
            if node_id not in visited:
                visited.add(node_id)
                result.append(node_id)
            # Then visit children in order (DFS into each path)
            for child in adjacency.get(node_id, []):
                visit(child)

        # Start from nodes with in-degree 0 (root nodes)
        start_nodes = [n for n, d in in_degree.items() if d == 0]
        for node_id in start_nodes:
            visit(node_id)

        # Check for circular references: add unvisited nodes
        for node_id in nodes:
            if node_id not in visited:
                visit(node_id)

        return result
