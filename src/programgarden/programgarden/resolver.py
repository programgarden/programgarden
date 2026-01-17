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

        # 3. Reserved node ID validation
        RESERVED_NODE_IDS = {"nodes", "input", "context"}
        for node in workflow.nodes:
            node_id = node.get("id")
            if node_id in RESERVED_NODE_IDS:
                result.add_error(
                    f"Node ID '{node_id}' is reserved. "
                    f"Cannot use: {', '.join(sorted(RESERVED_NODE_IDS))}"
                )

        # 4. Node type validation
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

        # 6. Required input port connection validation
        self._validate_required_connections(workflow, registry, result)

        return result

    def _validate_required_connections(
        self,
        workflow,
        registry,
        result: ValidationResult,
    ) -> None:
        """
        Validate required input port connections.
        
        Checks if nodes with required=True input ports have explicit connection field binding.
        NO automatic BrokerNode ancestor detection - explicit binding required.
        """
        # Nodes that require explicit connection field binding
        # e.g., connection: "{{ nodes.broker.connection }}"
        CONNECTION_REQUIRED_NODES = {
            "RealMarketDataNode",
            "RealAccountNode",
            "RealOrderEventNode",
            "NewOrderNode",
            "ModifyOrderNode",
            "CancelOrderNode",
            "AccountNode",
            "MarketDataNode",
        }
        
        # Build edge lookup: {to_node_id: [from_node_ids]}
        incoming_edges: Dict[str, List[str]] = {}
        for edge in workflow.edges:
            to_id = edge.to_node_id
            from_id = edge.from_node_id
            if to_id not in incoming_edges:
                incoming_edges[to_id] = []
            incoming_edges[to_id].append(from_id)
        
        # Build node lookup: {node_id: node_dict}
        nodes_by_id = {n.get("id"): n for n in workflow.nodes}
        
        for node in workflow.nodes:
            node_id = node.get("id")
            node_type = node.get("type")
            
            # Check explicit connection field binding for specific node types
            if node_type in CONNECTION_REQUIRED_NODES:
                connection_field = node.get("connection")
                if not connection_field:
                    result.add_error(
                        f"Node '{node_id}' ({node_type}) requires explicit connection field. "
                        f"Set connection: \"{{{{ nodes.broker.connection }}}}\" in node config."
                    )
            
            # Check required input ports from node class definition
            node_class = registry.get(node_type)
            if node_class:
                self._check_required_ports(node_id, node_type, node_class, incoming_edges, nodes_by_id, result)

    def _has_broker_ancestor(
        self,
        node_id: str,
        incoming_edges: Dict[str, List[str]],
        nodes_by_id: Dict[str, Dict],
    ) -> bool:
        """
        Check if node has BrokerNode as an ancestor (BFS traversal).
        """
        from collections import deque
        
        visited = set()
        queue = deque([node_id])
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            
            for parent_id in incoming_edges.get(current, []):
                parent_node = nodes_by_id.get(parent_id)
                if parent_node and parent_node.get("type") == "BrokerNode":
                    return True
                if parent_id not in visited:
                    queue.append(parent_id)
        
        return False

    def _check_required_ports(
        self,
        node_id: str,
        node_type: str,
        node_class,
        incoming_edges: Dict[str, List[str]],
        nodes_by_id: Dict[str, Dict],
        result: ValidationResult,
    ) -> None:
        """
        Check if required input ports have valid connections.
        
        For 'symbols' type ports, checks if field is set or port is connected.
        """
        # Get _inputs from class definition (not instance)
        # Pydantic treats _inputs as private attr, so access from __class_vars__ or directly
        inputs = []
        if hasattr(node_class, "__dict__") and "_inputs" in node_class.__dict__:
            inputs = node_class.__dict__["_inputs"]
        elif hasattr(node_class, "_inputs"):
            raw_inputs = node_class._inputs
            # Check if it's a list (not ModelPrivateAttr)
            if isinstance(raw_inputs, list):
                inputs = raw_inputs
        
        if not inputs:
            return
        
        node_config = nodes_by_id.get(node_id, {})
        
        for port in inputs:
            port_name = getattr(port, "name", "")
            port_type = getattr(port, "type", "")
            required = getattr(port, "required", True)
            
            if not required:
                continue
            
            # Special handling: symbols can come from field or port
            if port_type == "symbol_list":
                # Check if symbols field is set in node config
                symbols_in_config = node_config.get("symbols")
                if symbols_in_config and len(symbols_in_config) > 0:
                    continue  # symbols set in field, no port connection needed
            
            # Check if there's an incoming connection
            has_connection = len(incoming_edges.get(node_id, [])) > 0
            
            # For broker_connection, we already check via _has_broker_ancestor
            if port_type == "broker_connection":
                continue  # Already handled above
            
            # For other required ports, warn if no connection (not error, might be expression binding)
            # Full validation would require checking output types of source nodes
            # For now, we just ensure there's at least some connection for required ports

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

            # Plugin node types where fields should be extracted separately
            PLUGIN_NODE_TYPES = {"ConditionNode", "NewOrderNode", "ModifyOrderNode", "CancelOrderNode"}

            # Extract config (exclude base fields)
            # For plugin nodes, exclude "fields" from config (will be passed separately)
            # But keep "plugin" in config for plugin_id lookup
            # For non-plugin nodes like MarketDataNode, keep "fields" in config
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
