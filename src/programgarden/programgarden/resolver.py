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
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.category = category
        self.config = config
        self.plugin = plugin
        self.fields = fields or {}

        # Runtime connections (set by executor)
        self.inputs: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}


class ResolvedEdge:
    """Resolved edge (execution order only)"""

    def __init__(
        self,
        from_node_id: str,
        to_node_id: str,
    ):
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id


class ResolvedWorkflow:
    """Resolved workflow (ready for execution)"""

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

        if not result.is_valid:
            return result

        # 3. Node type validation
        registry = NodeTypeRegistry()
        for node in workflow.nodes:
            node_type = node.get("type")
            if not registry.get(node_type):
                result.add_error(f"Unknown node type: {node_type}")

        # 4. Plugin validation (for plugin-using nodes)
        plugin_registry = PluginRegistry()
        plugin_node_types = {"ConditionNode", "NewOrderNode", "ModifyOrderNode", "CancelOrderNode"}

        for node in workflow.nodes:
            if node.get("type") in plugin_node_types:
                plugin_id = node.get("plugin")
                if not plugin_id:
                    result.add_error(f"Node '{node.get('id')}' does not have a plugin specified")
                elif not plugin_registry.get(plugin_id):
                    result.add_warning(
                        f"Plugin '{plugin_id}' not found in registry (community load required)"
                    )

        # 5. Edge connection type compatibility validation
        # TODO: Input/output port type matching validation

        return result

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

        for node_def in workflow.nodes:
            node_id = node_def.get("id")
            node_type = node_def.get("type")
            category = node_def.get("category", "")

            # Extract config (exclude base fields)
            config = {
                k: v for k, v in node_def.items()
                if k not in {"id", "type", "category", "position", "plugin", "fields"}
            }

            # Load plugin (if applicable)
            plugin = None
            fields = {}
            if "plugin" in node_def:
                plugin_id = node_def.get("plugin")
                plugin = plugin_registry.get(plugin_id)
                fields = node_def.get("fields", {})

            resolved_node = ResolvedNode(
                node_id=node_id,
                node_type=node_type,
                category=category,
                config=config,
                plugin=plugin,
                fields=fields,
            )
            resolved_nodes[node_id] = resolved_node

        # Resolve edges (execution order only)
        resolved_edges: List[ResolvedEdge] = []
        for edge in workflow.edges:
            resolved_edge = ResolvedEdge(
                from_node_id=edge.from_node_id,
                to_node_id=edge.to_node_id,
            )
            resolved_edges.append(resolved_edge)

        # Calculate execution order (topological sort)
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
        Topological sort (Kahn's algorithm)

        Sorts DAG nodes by dependency order
        """
        # Calculate in-degree
        in_degree: Dict[str, int] = {node_id: 0 for node_id in nodes}
        adjacency: Dict[str, List[str]] = {node_id: [] for node_id in nodes}

        for edge in edges:
            if edge.to_node_id in in_degree:
                in_degree[edge.to_node_id] += 1
            if edge.from_node_id in adjacency:
                adjacency[edge.from_node_id].append(edge.to_node_id)

        # Start with nodes having in-degree 0
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            for neighbor in adjacency.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for circular references
        if len(result) != len(nodes):
            # If circular reference exists, add remaining nodes (warning)
            remaining = [n for n in nodes if n not in result]
            result.extend(remaining)

        return result
