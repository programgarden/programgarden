"""ProgramGarden WorkflowResolver — structured-error validation.

Converts a JSON workflow definition into executable objects after running
a battery of structural / topological / registry checks. Every emitted
diagnostic is a `programgarden_core.ErrorInfo` so AI chatbots can do
deterministic self-correction without parsing free-form strings.
"""

from typing import Optional, List, Dict, Any, Set, Tuple

from programgarden_core import (
    ErrorCode,
    ErrorInfo,
    ErrorLocation,
    ValidationLimits,
    ValidationResult,
    build_error,
    suggest_close_match,
)


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

    def validate(
        self,
        definition: Dict[str, Any],
        *,
        limits: Optional[ValidationLimits] = None,
        suppress_recommendations: Optional[List[str]] = None,
        expand_cascade: bool = False,
        validate_dynamic_injection: bool = False,
    ) -> ValidationResult:
        """Validate a workflow definition and return a structured result.

        Args:
            definition: The workflow JSON dict.
            limits: Output volume caps (default: ValidationLimits()).
            suppress_recommendations: rule_id list to skip when building
                `static_recommendations`.
            expand_cascade: When True, skip cascade suppression (debugging).
            validate_dynamic_injection: When True, emit DYNAMIC_NODE_CLASS_NOT_INJECTED
                for Dynamic_* nodes that have a registered schema but no injected
                runtime class. Call right before `execute()` to catch missing
                inject_node_classes() calls.
        """
        from programgarden_core import WorkflowDefinition, NodeTypeRegistry, PluginRegistry
        from programgarden.validation_recommender import (
            finalize_result,
            run_static_recommendation_rules,
        )

        result = ValidationResult()

        # 1. Definition parsing (Pydantic schema check)
        try:
            workflow = WorkflowDefinition(**definition)
        except Exception as e:
            result.add(
                build_error(
                    ErrorCode.DEFINITION_PARSE_ERROR,
                    f"Workflow definition failed schema validation: {e}",
                    suggestion="Inspect the offending field path and align it with WorkflowDefinition.",
                    details={"raw_exception": str(e)},
                )
            )
            # Even on parse failure run finalize so summary/limits stay populated.
            finalize_result(result, limits=limits, expand_cascade=expand_cascade)
            return result

        # 2. Structural invariants (duplicates, edge refs, StartNode, cycles)
        for info in workflow.validate_structure():
            result.add(info)

        # 3. Reserved node ids
        RESERVED_NODE_IDS = {"nodes", "input", "context"}
        for node in workflow.nodes:
            node_id = node.get("id")
            if node_id in RESERVED_NODE_IDS:
                result.add(
                    build_error(
                        ErrorCode.RESERVED_NODE_ID,
                        f"Node id '{node_id}' is reserved and cannot be used",
                        location=ErrorLocation(node_id=node_id),
                        available_values=sorted(RESERVED_NODE_IDS),
                        suggestion="Rename the node to anything outside the reserved id set.",
                    )
                )

        # 4. Node type validation (regular + dynamic registry)
        from programgarden_core.registry import DynamicNodeRegistry, is_dynamic_node_type
        registry = NodeTypeRegistry()
        dynamic_registry = DynamicNodeRegistry()
        known_types: List[str] = sorted(registry.list_types() + dynamic_registry.list_schema_types())

        for node in workflow.nodes:
            node_type = node.get("type")
            node_id = node.get("id")

            if registry.get(node_type):
                continue

            if is_dynamic_node_type(node_type):
                if not dynamic_registry.get_schema(node_type):
                    result.add(
                        build_error(
                            ErrorCode.UNKNOWN_DYNAMIC_NODE_SCHEMA,
                            f"Dynamic node schema '{node_type}' is not registered",
                            location=ErrorLocation(node_id=node_id, node_type=node_type),
                            suggestion="Call executor.register_dynamic_schemas([...]) before validate().",
                        )
                    )
                    continue

                if node.get("credential_id"):
                    result.add(
                        build_error(
                            ErrorCode.DYNAMIC_NODE_CREDENTIAL_FORBIDDEN,
                            f"Dynamic node '{node_id}' cannot reference a credential_id",
                            location=ErrorLocation(
                                node_id=node_id,
                                node_type=node_type,
                                credential_id=node.get("credential_id"),
                            ),
                            suggestion="Remove credential_id from the dynamic node — credential access is blocked for security.",
                        )
                    )

                if validate_dynamic_injection and not dynamic_registry.get_node_class(node_type):
                    result.add(
                        build_error(
                            ErrorCode.DYNAMIC_NODE_CLASS_NOT_INJECTED,
                            f"Dynamic node '{node_type}' has a registered schema but no injected runtime class",
                            location=ErrorLocation(node_id=node_id, node_type=node_type),
                            suggestion="Call executor.inject_node_classes({...}) before execute(). Otherwise the node returns runtime errors as downstream data.",
                        )
                    )
                continue

            result.add(
                build_error(
                    ErrorCode.UNKNOWN_NODE_TYPE,
                    f"Unknown node type '{node_type}'",
                    location=ErrorLocation(node_id=node_id, node_type=node_type),
                    available_values=suggest_close_match(node_type or "", known_types),
                    suggestion="Pick a node type from the registered list, or register a Dynamic_ schema first.",
                )
            )

        # 5. Plugin validation (ConditionNode etc.)
        plugin_registry = PluginRegistry()
        plugin_node_types = {"ConditionNode"}
        all_plugin_ids: List[str] = sorted(
            {getattr(s, "id", "") for s in plugin_registry.list_plugins() if getattr(s, "id", "")}
        )

        for node in workflow.nodes:
            if node.get("type") in plugin_node_types:
                plugin_id = node.get("plugin")
                if not plugin_id:
                    result.add(
                        build_error(
                            ErrorCode.MISSING_PLUGIN,
                            f"Node '{node.get('id')}' must specify a 'plugin' id",
                            location=ErrorLocation(node_id=node.get("id"), node_type=node.get("type")),
                            suggestion="Set the 'plugin' field to a registered plugin id (e.g. 'RSI').",
                        )
                    )
                elif not plugin_registry.get(plugin_id):
                    result.add(
                        build_error(
                            ErrorCode.UNKNOWN_PLUGIN,
                            f"Plugin '{plugin_id}' is not registered (is programgarden-community installed?)",
                            location=ErrorLocation(
                                node_id=node.get("id"),
                                node_type=node.get("type"),
                                plugin_id=plugin_id,
                            ),
                            available_values=suggest_close_match(plugin_id, all_plugin_ids),
                            suggestion="Install programgarden-community or register the plugin manually.",
                        )
                    )
                else:
                    # Plugin exists — verify the data binding shape matches the
                    # plugin's contract. Mirrors the runtime branch in
                    # executor (_execute_condition_node): position-management
                    # plugins read `positions`, indicator plugins iterate
                    # `items {from, extract}`. Without this static check the
                    # wrong shape (legacy `data`/`params`) passes validate()
                    # and only fails at dry_run, so the AI build self-correct
                    # loop never sees it.
                    plugin_schema = plugin_registry.get_schema(plugin_id)
                    required_data = (
                        plugin_schema.required_data if plugin_schema else ["data"]
                    )
                    is_positions_based = (
                        "positions" in required_data and "data" not in required_data
                    )
                    if is_positions_based:
                        if not node.get("positions"):
                            result.add(
                                build_error(
                                    ErrorCode.MISSING_REQUIRED_FIELD,
                                    f"ConditionNode '{node.get('id')}' uses position "
                                    f"plugin '{plugin_id}' but has no 'positions' binding",
                                    location=ErrorLocation(
                                        node_id=node.get("id"),
                                        node_type=node.get("type"),
                                        plugin_id=plugin_id,
                                        field_path="positions",
                                    ),
                                    suggestion=(
                                        "Position-management plugins (StopLoss / "
                                        "ProfitTarget / TrailingStop) read holdings from "
                                        "'positions'. Bind it to an account node's "
                                        "positions output, e.g. positions: "
                                        "'{{ nodes.account.positions }}'. The 'data' / "
                                        "'params' fields are not used here."
                                    ),
                                )
                            )
                    else:
                        items = node.get("items")
                        if (
                            not isinstance(items, dict)
                            or not items.get("from")
                            or not items.get("extract")
                        ):
                            result.add(
                                build_error(
                                    ErrorCode.MISSING_REQUIRED_FIELD,
                                    f"ConditionNode '{node.get('id')}' uses indicator "
                                    f"plugin '{plugin_id}' but has no valid 'items' "
                                    f"binding (items.from + items.extract)",
                                    location=ErrorLocation(
                                        node_id=node.get("id"),
                                        node_type=node.get("type"),
                                        plugin_id=plugin_id,
                                        field_path="items",
                                    ),
                                    suggestion=(
                                        "Indicator plugins iterate OHLCV through 'items'. "
                                        "Add items with 'from' (the source array) and "
                                        "'extract' (per-row field map), e.g. items: "
                                        "{from: '{{ item.time_series }}', extract: "
                                        "{symbol, exchange, date, close}}. The legacy "
                                        "'data' / 'params' fields are not used."
                                    ),
                                )
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

        # 11. Static recommendations (topology analysis)
        for rec in run_static_recommendation_rules(
            workflow,
            registry,
            suppress=suppress_recommendations,
        ):
            result.add_static_recommendation(rec)

        # 12. Inline error -> recommendation augmentation
        self._attach_inline_recommendations(result, workflow)

        # 13. Post-processing: cascade suppression + capping + summary
        finalize_result(result, limits=limits, expand_cascade=expand_cascade)

        return result

    def _attach_inline_recommendations(self, result: ValidationResult, workflow) -> None:
        """Augment specific ErrorInfo entries with related Recommendation hints.

        Plan §Phase 2.11: for a small set of error codes there's a natural
        improvement worth attaching directly to the error object (rather
        than the workflow-level channel) so the chatbot sees a fix path
        alongside the diagnosis.
        """
        from programgarden.validation_recommender import (
            make_expression_port_typo_rec,
            make_broker_product_mismatch_rec,
        )

        node_ids = [n.get("id") for n in workflow.nodes if isinstance(n, dict) and n.get("id")]

        for info in result.errors:
            code = info.code.value if hasattr(info.code, "value") else info.code
            if code == ErrorCode.INVALID_EXPRESSION_REF.value:
                ref_id = None
                expr = info.location.expression or ""
                # extract `{{ nodes.X.Y }}` -> X
                import re as _re
                m = _re.search(r"nodes\.(\w+)", expr)
                if m:
                    ref_id = m.group(1)
                if ref_id:
                    info.recommendations.append(
                        make_expression_port_typo_rec(
                            ref_id=ref_id,
                            candidates=node_ids,
                            location=info.location,
                        )
                    )
            elif code == ErrorCode.INCOMPATIBLE_BROKER_PROVIDER.value:
                required = info.details.get("required_provider")
                if required and info.location.node_id and info.location.node_type:
                    info.recommendations.append(
                        make_broker_product_mismatch_rec(
                            node_id=info.location.node_id,
                            node_type=info.location.node_type,
                            required_provider=required,
                        )
                    )

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

        from programgarden_core import ErrorSeverity
        from programgarden_core.i18n.translator import t as _i18n_t

        def _resolve_i18n(value):
            if isinstance(value, str) and value.startswith("i18n:"):
                return _i18n_t(value[len("i18n:"):], locale="en")
            return value

        for idx, edge in enumerate(workflow.edges):
            if edge.edge_type != EdgeType.MAIN:
                continue

            target_node_type = node_id_to_type_map.get(edge.to_node_id)
            source_node_type = node_id_to_type_map.get(edge.from_node_id)

            if not target_node_type or not source_node_type:
                continue

            target_node_class = registry.get(target_node_type)
            if not target_node_class:
                continue

            connection_rules = getattr(target_node_class, '_connection_rules', [])
            for rule in connection_rules:
                if source_node_type in rule.deny_direct_from:
                    resolved_reason = _resolve_i18n(rule.reason)
                    resolved_rule_suggestion = _resolve_i18n(getattr(rule, "suggestion", None))

                    message_parts = [
                        f"Direct connection blocked: '{edge.from_node_id}' "
                        f"({source_node_type}) -> '{edge.to_node_id}' ({target_node_type})"
                    ]
                    if resolved_reason:
                        message_parts.append(resolved_reason)

                    # Prefer the rule's own i18n suggestion; otherwise synthesise
                    # one from required_intermediate.
                    suggestion: Optional[str] = resolved_rule_suggestion
                    if not suggestion and rule.required_intermediate:
                        suggestion = (
                            f"Insert a {rule.required_intermediate} node between source and target."
                        )

                    severity = (
                        ErrorSeverity.ERROR
                        if rule.severity == ConnectionSeverity.ERROR
                        else ErrorSeverity.WARNING
                    )
                    result.add(
                        build_error(
                            ErrorCode.CONNECTION_RULE_VIOLATION,
                            ". ".join(message_parts),
                            location=ErrorLocation(
                                node_id=edge.to_node_id,
                                node_type=target_node_type,
                                edge_index=idx,
                                edge_from=edge.from_node_id,
                                edge_to=edge.to_node_id,
                            ),
                            suggestion=suggestion,
                            severity=severity,
                            details={
                                "source_node_id": edge.from_node_id,
                                "source_node_type": source_node_type,
                                "target_node_type": target_node_type,
                                "required_intermediate": rule.required_intermediate,
                                "reason": resolved_reason,
                            },
                        )
                    )

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
        """Verify each edge's from/to references an existing node.

        Also catches `from_port` typos for nodes that declare multiple
        output ports (`IfNode.true/false` etc.) via INVALID_EDGE_PORT,
        and validates ai_model/tool edge type semantics for AI Agent flows.
        """
        from programgarden_core import NodeTypeRegistry
        from programgarden_core.models.edge import EdgeType

        node_ids = {n.get("id") for n in workflow.nodes}
        node_type_by_id = {n.get("id"): n.get("type") for n in workflow.nodes}
        registry = NodeTypeRegistry()

        for idx, edge in enumerate(workflow.edges):
            from_raw = getattr(edge, "from_node", "") or ""
            to_raw = getattr(edge, "to_node", "") or ""

            from_id = from_raw.split(".")[0] if from_raw else ""
            to_id = to_raw.split(".")[0] if to_raw else ""

            if from_id and from_id not in node_ids:
                result.add(
                    build_error(
                        ErrorCode.INVALID_EDGE_REF,
                        f"Edge 'from' references non-existent node '{from_id}'",
                        location=ErrorLocation(
                            edge_index=idx,
                            edge_from=from_raw,
                            edge_to=to_raw,
                        ),
                        available_values=sorted(nid for nid in node_ids if nid),
                        suggestion="Update edge.from to reference an existing node id.",
                    )
                )
            if to_id and to_id not in node_ids:
                result.add(
                    build_error(
                        ErrorCode.INVALID_EDGE_REF,
                        f"Edge 'to' references non-existent node '{to_id}'",
                        location=ErrorLocation(
                            edge_index=idx,
                            edge_from=from_raw,
                            edge_to=to_raw,
                        ),
                        available_values=sorted(nid for nid in node_ids if nid),
                        suggestion="Update edge.to to reference an existing node id.",
                    )
                )

            # INVALID_EDGE_PORT — explicit from_port that doesn't exist on source
            from_port = getattr(edge, "from_port", None)
            if from_id and from_id in node_ids and from_port:
                source_type = node_type_by_id.get(from_id)
                schema = registry.get_schema(source_type) if source_type else None
                if schema:
                    output_names: List[str] = []
                    for out in (schema.outputs or []):
                        if isinstance(out, dict):
                            name = out.get("name")
                        else:
                            name = getattr(out, "name", None)
                        if name:
                            output_names.append(name)
                    if output_names and from_port not in output_names:
                        result.add(
                            build_error(
                                ErrorCode.INVALID_EDGE_PORT,
                                f"Edge from_port '{from_port}' is not an output of node '{from_id}' ({source_type})",
                                location=ErrorLocation(
                                    node_id=from_id,
                                    node_type=source_type,
                                    edge_index=idx,
                                    edge_from=from_raw,
                                    edge_to=to_raw,
                                    output_port=from_port,
                                ),
                                available_values=suggest_close_match(from_port, output_names) or sorted(output_names),
                                suggestion="Pick an output port that exists on the source node.",
                            )
                        )

            # AI edge semantic validation: ai_model / tool edges have strict source/target shape.
            edge_type = getattr(edge, "edge_type", None)
            edge_type_str = edge_type.value if hasattr(edge_type, "value") else str(edge_type) if edge_type else "main"

            if edge_type_str == EdgeType.AI_MODEL.value:
                source_type = node_type_by_id.get(from_id)
                target_type = node_type_by_id.get(to_id)
                if from_id and source_type and source_type != "LLMModelNode":
                    result.add(
                        build_error(
                            ErrorCode.INVALID_AI_MODEL_EDGE,
                            f"ai_model edge source must be LLMModelNode, got '{source_type}'",
                            location=ErrorLocation(
                                node_id=from_id,
                                node_type=source_type,
                                edge_index=idx,
                                edge_from=from_raw,
                                edge_to=to_raw,
                            ),
                            suggestion="Connect an LLMModelNode as the ai_model edge source.",
                        )
                    )
                if to_id and target_type and target_type != "AIAgentNode":
                    result.add(
                        build_error(
                            ErrorCode.INVALID_AI_MODEL_EDGE,
                            f"ai_model edge target must be AIAgentNode, got '{target_type}'",
                            location=ErrorLocation(
                                node_id=to_id,
                                node_type=target_type,
                                edge_index=idx,
                                edge_from=from_raw,
                                edge_to=to_raw,
                            ),
                            suggestion="ai_model edges feed an AIAgentNode. Use edge_type='main' for other targets.",
                        )
                    )

            elif edge_type_str == EdgeType.TOOL.value:
                source_type = node_type_by_id.get(from_id)
                target_type = node_type_by_id.get(to_id)
                if from_id and source_type:
                    source_cls = registry.get(source_type)
                    is_tool = bool(source_cls and source_cls.is_tool_enabled()) if source_cls else False
                    if not is_tool:
                        result.add(
                            build_error(
                                ErrorCode.INVALID_TOOL_EDGE,
                                f"tool edge source '{source_type}' is not tool-enabled (is_tool_enabled() returns False)",
                                location=ErrorLocation(
                                    node_id=from_id,
                                    node_type=source_type,
                                    edge_index=idx,
                                    edge_from=from_raw,
                                    edge_to=to_raw,
                                ),
                                suggestion="Only tool-enabled nodes (MarketDataNode, AccountNode, ConditionNode etc.) can be registered as AI Agent tools.",
                            )
                        )
                if to_id and target_type and target_type != "AIAgentNode":
                    result.add(
                        build_error(
                            ErrorCode.INVALID_TOOL_EDGE,
                            f"tool edge target must be AIAgentNode, got '{target_type}'",
                            location=ErrorLocation(
                                node_id=to_id,
                                node_type=target_type,
                                edge_index=idx,
                                edge_from=from_raw,
                                edge_to=to_raw,
                            ),
                            suggestion="tool edges register a node as an AI Agent tool. The target must be an AIAgentNode.",
                        )
                    )

    def _validate_expression_references(
        self,
        workflow,
        result: ValidationResult,
    ) -> None:
        """
        {{ nodes.<id>(.<port>)? }} 표현식의 노드 ID + 출력 포트 존재 여부를 검증한다.

        - node id 가 정의되지 않은 경우: INVALID_EXPRESSION_REF
        - port 가 존재하지 않는 경우 (메서드 호출 / chain method 제외): INVALID_EXPRESSION_REF
        """
        import re
        from programgarden_core import NodeTypeRegistry
        from programgarden_core.registry import DynamicNodeRegistry

        node_ids = {n.get("id") for n in workflow.nodes}
        node_type_by_id = {n.get("id"): n.get("type") for n in workflow.nodes}
        registry = NodeTypeRegistry()
        dynamic_registry = DynamicNodeRegistry()

        # NodeOutputProxy 체이닝 메서드 — port 가 아닌 호출. nodes.X.<method>(...) 일 때 검증 스킵.
        chain_methods = {
            "all", "first", "last", "count",
            "filter", "map", "pluck", "flatten",
            "sum", "avg", "mean", "median", "min", "max",
            "stdev", "variance",
            "unique", "sort_by", "sort", "limit", "offset",
            "head", "tail",
        }

        def _port_names_for(node_type: str) -> Optional[List[str]]:
            if not node_type:
                return None
            schema = registry.get_schema(node_type)
            if schema:
                names: Set[str] = set()
                for out in (schema.outputs or []):
                    if isinstance(out, dict):
                        nm = out.get("name")
                    else:
                        nm = getattr(out, "name", None)
                    if nm:
                        names.add(nm)
                names.discard("")
                return sorted(names) if names else None
            dyn_schema = dynamic_registry.get_schema(node_type)
            if dyn_schema:
                return [o.get("name") for o in (dyn_schema.outputs or []) if o.get("name")]
            return None

        def _extract_field_names(outputs: Any, port_name: str) -> Optional[List[str]]:
            """Walk an outputs list (list of dicts or OutputPort instances)
            and return the field names declared on the matching port, or
            None if the port has no `fields` schema. Returning None signals
            "skip nested validation" — only validate when schema declares
            fields, otherwise leave the port shape open."""
            for out in (outputs or []):
                if isinstance(out, dict):
                    nm = out.get("name")
                    fields = out.get("fields")
                else:
                    nm = getattr(out, "name", None)
                    fields = getattr(out, "fields", None)
                if nm != port_name:
                    continue
                if not fields:
                    return None
                names: Set[str] = set()
                for f in fields:
                    if isinstance(f, dict):
                        fn = f.get("name")
                    else:
                        fn = getattr(f, "name", None)
                    if fn:
                        names.add(fn)
                return sorted(names) if names else None
            return None

        def _field_names_for(node_type: str, port_name: str) -> Optional[List[str]]:
            """Resolve declared field names for an output port.

            Mirrors `_port_names_for`: check the static NodeTypeRegistry
            first, then fall back to DynamicNodeRegistry so user-injected
            Dynamic_* nodes get the same nested-field typo gate as
            built-in nodes when their schema declares `fields`."""
            if not node_type or not port_name:
                return None
            schema = registry.get_schema(node_type)
            if schema:
                return _extract_field_names(schema.outputs, port_name)
            dyn_schema = dynamic_registry.get_schema(node_type)
            if dyn_schema:
                return _extract_field_names(dyn_schema.outputs, port_name)
            return None

        # ── Phase 2: cross-port TYPE compatibility ──────────────────────────
        # Field *existence* is handled above. This adds a conservative type
        # check: a binding that is the WHOLE value of a numeric/boolean-typed
        # consuming field must not read an output sub-field of a *different*
        # concrete scalar type (e.g. feeding a `string` symbol into a `number`
        # balance field). Only strong scalar classes are compared; object /
        # array / enum / json / `any` and string-consuming fields (freely
        # coercible) are left open to keep false-rejects at zero.
        _SCALAR_CLASS = {
            "number": "num", "integer": "num", "int": "num",
            "float": "num", "decimal": "num",
            "string": "str", "str": "str",
            "boolean": "bool", "bool": "bool",
        }

        def _scalar_class(type_str: Any) -> Optional[str]:
            if not type_str:
                return None
            return _SCALAR_CLASS.get(str(type_str).strip().lower())

        def _extract_field_type(outputs: Any, port_name: str, field_name: str) -> Optional[str]:
            for out in (outputs or []):
                if isinstance(out, dict):
                    nm = out.get("name")
                    fields = out.get("fields")
                else:
                    nm = getattr(out, "name", None)
                    fields = getattr(out, "fields", None)
                if nm != port_name:
                    continue
                for f in (fields or []):
                    if isinstance(f, dict):
                        fn, ft = f.get("name"), f.get("type")
                    else:
                        fn, ft = getattr(f, "name", None), getattr(f, "type", None)
                    if fn == field_name:
                        return ft
            return None

        def _output_field_type(node_type: str, port_name: str, field_name: str) -> Optional[str]:
            if not node_type:
                return None
            schema = registry.get_schema(node_type)
            if schema:
                return _extract_field_type(schema.outputs, port_name, field_name)
            dyn_schema = dynamic_registry.get_schema(node_type)
            if dyn_schema:
                return _extract_field_type(dyn_schema.outputs, port_name, field_name)
            return None

        def _consuming_scalar_class(node_type: str, field_key: str) -> Optional[str]:
            """Strong scalar class expected by a consuming node's top-level
            config field, or None when the field is open/structured (skip).

            `expected_type == 'any'` (e.g. IfNode.left/right) is explicitly open
            and must never be type-checked; struct-shaped `expected_type`
            (``{...}``) is object-like → skip; a concrete scalar `expected_type`
            wins, otherwise fall back to the FieldType enum.
            """
            node_class = registry.get(node_type) if node_type else None
            if node_class is None:
                return None
            try:
                fs = node_class.get_field_schema()
            except Exception:
                return None
            sch = fs.get(field_key) if isinstance(fs, dict) else None
            if sch is None:
                return None
            expected = getattr(sch, "expected_type", None)
            if expected is not None:
                exp_s = str(expected).strip().lower()
                if exp_s in ("any", ""):
                    return None
                cls = _scalar_class(exp_s)
                # Concrete scalar expected_type → use it; struct/other → skip.
                return cls
            ftype = getattr(sch, "type", None)
            ftype = getattr(ftype, "value", ftype)
            return _scalar_class(ftype)

        # Whole-value single-expression matcher (no surrounding text / arithmetic).
        _whole_expr = re.compile(r"^\s*\{\{\s*nodes\.[\w.]+\s*\}\}\s*$")

        # nodes.<id>(.<attr>)* — capture the full dotted path so nested
        # field typos (e.g. {{ nodes.account.balance.orderabl_amount }})
        # are also caught when OutputPort.fields declares the shape.
        expr_pattern = re.compile(r"\{\{\s*nodes\.(\w+)((?:\.\w+)*)\s*(\()?")
        skip_keys = {"id", "type", "category", "position"}

        def find_refs(value, node_id: str, field_path: str):
            if isinstance(value, str):
                for match in expr_pattern.finditer(value):
                    ref_id = match.group(1)
                    path_str = match.group(2) or ""
                    is_call = match.group(3) == "("
                    attrs = [a for a in path_str.split(".") if a]

                    if ref_id not in node_ids:
                        result.add(
                            build_error(
                                ErrorCode.INVALID_EXPRESSION_REF,
                                f"Expression references non-existent node '{ref_id}'",
                                location=ErrorLocation(
                                    node_id=node_id,
                                    field_path=field_path,
                                    expression=value,
                                ),
                                available_values=suggest_close_match(ref_id, sorted(nid for nid in node_ids if nid))
                                or sorted(nid for nid in node_ids if nid),
                                suggestion="Update the expression to reference an existing node id.",
                            )
                        )
                        continue

                    if not attrs:
                        continue

                    # The trailing `(` binds to the last attr. So when the
                    # path is single-attr and ends with `(`, that attr is a
                    # method call (e.g. nodes.x.first()) and we skip both
                    # port and nested checks.
                    attr = attrs[0]
                    is_port_method = is_call and len(attrs) == 1
                    if attr in chain_methods or is_port_method:
                        continue

                    source_type = node_type_by_id.get(ref_id)
                    ports = _port_names_for(source_type)
                    if ports is not None and attr not in ports:
                        result.add(
                            build_error(
                                ErrorCode.INVALID_EXPRESSION_REF,
                                f"Expression port '{attr}' is not an output of node '{ref_id}' ({source_type})",
                                location=ErrorLocation(
                                    node_id=node_id,
                                    node_type=node_type_by_id.get(node_id),
                                    field_path=field_path,
                                    expression=value,
                                    output_port=attr,
                                ),
                                available_values=suggest_close_match(attr, ports) or sorted(ports),
                                suggestion="Pick an output port that exists on the source node (or use a chaining method like .filter()/.first()).",
                            )
                        )
                        continue

                    # Nested field validation: only when the port has a
                    # declared `fields` schema. Skip when the trailing attr
                    # is a method (e.g. nodes.x.port.something()).
                    if len(attrs) < 2:
                        continue
                    is_nested_method = is_call and len(attrs) == 2
                    if is_nested_method:
                        continue
                    nested = attrs[1]
                    field_names = _field_names_for(source_type, attr)
                    field_exists = (
                        field_names is None
                        or nested in field_names
                        # Underscore-prefixed keys are reserved for internal
                        # metadata (e.g. _partial_failure on balance dicts).
                        # Treat them as known so consumers can branch on them
                        # without forcing every metadata addition to update
                        # BALANCE_FIELDS in lockstep.
                        or nested.startswith("_")
                    )
                    if not field_exists:
                        result.add(
                            build_error(
                                ErrorCode.INVALID_EXPRESSION_REF,
                                f"Expression field '{nested}' is not a declared field of "
                                f"port '{attr}' on node '{ref_id}' ({source_type})",
                                location=ErrorLocation(
                                    node_id=node_id,
                                    node_type=node_type_by_id.get(node_id),
                                    field_path=field_path,
                                    expression=value,
                                    output_port=attr,
                                ),
                                available_values=suggest_close_match(nested, field_names) or sorted(field_names),
                                suggestion=(
                                    f"Pick a field that exists on '{attr}' "
                                    "(see OutputPort.fields in the node schema)."
                                ),
                            )
                        )
                        continue

                    # ── Phase 2: type compatibility on the valid-field path ──
                    # Only when this binding is the WHOLE value of a TOP-LEVEL
                    # config field and the field shape is known. Nested consumer
                    # paths (field_path with '.'/'[' → object-typed parent) and
                    # interpolated strings are intentionally skipped (ceiling).
                    if (
                        field_names is not None
                        and not is_call
                        and len(attrs) == 2
                        and "." not in field_path
                        and "[" not in field_path
                        and _whole_expr.match(value)
                    ):
                        consumer_type = node_type_by_id.get(node_id)
                        cin = _consuming_scalar_class(consumer_type, field_path)
                        if cin in ("num", "bool"):
                            out_type = _output_field_type(source_type, attr, nested)
                            cout = _scalar_class(out_type)
                            if cout is not None and cout != cin:
                                result.add(
                                    build_error(
                                        ErrorCode.INVALID_FIELD_TYPE,
                                        f"Field '{field_path}' on node '{node_id}' "
                                        f"({consumer_type}) expects a {cin} value, but "
                                        f"the expression reads '{attr}.{nested}' from "
                                        f"'{ref_id}' ({source_type}) which is declared "
                                        f"{out_type}.",
                                        location=ErrorLocation(
                                            node_id=node_id,
                                            node_type=consumer_type,
                                            field_path=field_path,
                                            expression=value,
                                            output_port=attr,
                                        ),
                                        suggestion=(
                                            f"'{field_path}' 필드에는 {cin} 타입 값이 필요합니다. "
                                            f"'{ref_id}' 노드의 '{attr}.{nested}' 출력은 타입이 달라 "
                                            f"맞지 않습니다 — 타입이 호환되는 출력 필드로 바꾸세요."
                                        ),
                                        details={
                                            "consumer_field": field_path,
                                            "consumer_class": cin,
                                            "ref_node_id": ref_id,
                                            "ref_port": attr,
                                            "ref_field": nested,
                                            "ref_field_type": out_type,
                                        },
                                    )
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
                result.add(
                    build_error(
                        ErrorCode.UNKNOWN_CREDENTIAL,
                        f"Node '{node.get('id')}' references undefined credential '{cred_id}'",
                        location=ErrorLocation(
                            node_id=node.get("id"),
                            node_type=node.get("type"),
                            credential_id=cred_id,
                        ),
                        available_values=sorted(defined_creds) if defined_creds else None,
                        suggestion="Add a matching credential entry under definition.credentials[] or fix the credential_id.",
                    )
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
                result.add(
                    build_error(
                        ErrorCode.DUPLICATE_BROKER_NODE,
                        f"Duplicate {product_label} broker node: '{broker_scopes[scope_value]}' and '{node_id}'",
                        location=ErrorLocation(node_id=node_id, node_type=node_type),
                        suggestion="Keep only one broker node per product scope.",
                        details={
                            "product_scope": scope_value,
                            "existing": broker_scopes[scope_value],
                            "duplicate": node_id,
                        },
                    )
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

            # product_scope match
            if scope.value not in available_brokers:
                product_label = "overseas_stock" if scope == ProductScope.STOCK else "overseas_futures"
                broker_node = "OverseasStockBrokerNode" if scope == ProductScope.STOCK else "OverseasFuturesBrokerNode"
                result.add(
                    build_error(
                        ErrorCode.MISSING_REQUIRED_BROKER,
                        f"Node '{node.get('id')}' ({node_type}) requires a {product_label} broker",
                        location=ErrorLocation(node_id=node.get("id"), node_type=node_type),
                        suggestion=f"Add {broker_node} to the workflow.",
                        details={"product_scope": scope.value, "expected_broker_node": broker_node},
                    )
                )
                continue

            # broker_provider match (ALL matches anything)
            if provider != BrokerProvider.ALL:
                broker_provider_value = available_brokers[scope.value]
                if broker_provider_value != BrokerProvider.ALL.value and broker_provider_value != provider.value:
                    result.add(
                        build_error(
                            ErrorCode.INCOMPATIBLE_BROKER_PROVIDER,
                            (
                                f"Node '{node.get('id')}' ({node_type}) requires "
                                f"broker provider '{provider.value}', but the workflow has "
                                f"'{broker_provider_value}' configured"
                            ),
                            location=ErrorLocation(node_id=node.get("id"), node_type=node_type),
                            available_values=[provider.value, BrokerProvider.ALL.value],
                            suggestion="Switch the broker node to one that matches this node's provider.",
                            details={
                                "required_provider": provider.value,
                                "configured_provider": broker_provider_value,
                                "product_scope": scope.value,
                            },
                        )
                    )

    def resolve(
        self,
        definition: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        *,
        validate_dynamic_injection: bool = False,
    ) -> Tuple[ResolvedWorkflow, ValidationResult]:
        """
        Resolve workflow (convert to execution objects)

        Args:
            definition: Workflow definition
            context: Execution context (credential_id, symbols, etc.)
            validate_dynamic_injection: When True, validate() emits
                DYNAMIC_NODE_CLASS_NOT_INJECTED for Dynamic_* nodes whose
                class has not been injected. Pass True from execute()/
                restore() so missing inject_node_classes() is blocked
                before GenericNodeExecutor silently surfaces the error
                as downstream data.

        Returns:
            (ResolvedWorkflow, ValidationResult)
        """
        from programgarden_core import WorkflowDefinition, NodeTypeRegistry, PluginRegistry

        # Validate
        validation = self.validate(
            definition,
            validate_dynamic_injection=validate_dynamic_injection,
        )
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
