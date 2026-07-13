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
    ) -> ValidationResult:
        """Validate a workflow definition and return a structured result.

        Args:
            definition: The workflow JSON dict.
            limits: Output volume caps (default: ValidationLimits()).
            suppress_recommendations: rule_id list to skip when building
                `static_recommendations`.
            expand_cascade: When True, skip cascade suppression (debugging).
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

        # 4. Node type validation (registry)
        registry = NodeTypeRegistry()
        known_types: List[str] = sorted(registry.list_types())

        for node in workflow.nodes:
            node_type = node.get("type")
            node_id = node.get("id")

            if registry.get(node_type):
                continue

            result.add(
                build_error(
                    ErrorCode.UNKNOWN_NODE_TYPE,
                    f"Unknown node type '{node_type}'",
                    location=ErrorLocation(node_id=node_id, node_type=node_type),
                    available_values=suggest_close_match(node_type or "", known_types),
                    suggestion="Pick a node type from the registered list.",
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

        # 10.5 CodeNode 정적 검증 (compile/screen 사전검증 + credential 봉쇄)
        self._validate_code_nodes(workflow, result)

        # 10.6 SplitNode 소스 검증 (분리할 배열이 실제로 배선됐는지)
        self._validate_split_nodes(workflow, registry, result)

        # 10.7 AIAgentNode ai_model 엣지 필수 검증 (LLM 없이는 애초에 동작 불가)
        self._validate_ai_agent_nodes(workflow, result)

        # 10.8 Display 노드 columns 키가 상류 출력 스키마에 실재하는지 (없는 키는 표에 '-' 만 찍힌다)
        self._validate_display_columns(workflow, registry, result)

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

        node_ids = {n.get("id") for n in workflow.nodes}
        node_type_by_id = {n.get("id"): n.get("type") for n in workflow.nodes}
        registry = NodeTypeRegistry()

        # CodeNode declares its output ports per-instance (config `outputs`), not
        # in the static registry schema. Build an id→ports map so the typo guard
        # validates {{ nodes.<code_id>.<port> }} against the instance's ports.
        code_node_ports_by_id: Dict[str, List[str]] = {}
        for n in workflow.nodes:
            if n.get("type") == "CodeNode":
                outs = n.get("outputs") or []
                names = [o.get("name") for o in outs if isinstance(o, dict) and o.get("name")]
                code_node_ports_by_id[n.get("id")] = names or ["result"]

        # NodeOutputProxy 체이닝 메서드 — port 가 아닌 호출. nodes.X.<method>(...) 일 때 검증 스킵.
        chain_methods = {
            "all", "first", "last", "count",
            "filter", "map", "pluck", "flatten",
            "sum", "avg", "mean", "median", "min", "max",
            "stdev", "variance",
            "unique", "sort_by", "sort", "limit", "offset",
            "head", "tail",
        }

        def _port_names_for(node_type: str, ref_id: Optional[str] = None) -> Optional[List[str]]:
            # CodeNode: use the per-instance declared ports (or ['result']).
            if ref_id is not None and ref_id in code_node_ports_by_id:
                return code_node_ports_by_id[ref_id]
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
            """Resolve declared field names for an output port from the
            static NodeTypeRegistry schema (when the port declares `fields`)."""
            if not node_type or not port_name:
                return None
            schema = registry.get_schema(node_type)
            if schema:
                return _extract_field_names(schema.outputs, port_name)
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
                    ports = _port_names_for(source_type, ref_id)
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

    # Credential-like binding keywords that must never feed a CodeNode input
    # (Layer 3 seal). Exact-token match against the binding path components.
    _CODE_NODE_CRED_KEYWORDS = frozenset({
        "appkey", "appsecret", "secret", "secretkey", "password", "passwd",
        "token", "credential", "credentials", "apikey", "api_key", "privatekey",
    })

    def _iter_binding_exprs(self, value):
        """Yield the inner text of every {{ ... }} expression found in a
        (possibly nested) config value."""
        import re
        _pat = re.compile(r"\{\{\s*(.+?)\s*\}\}")
        if isinstance(value, str):
            for m in _pat.finditer(value):
                yield m.group(1)
        elif isinstance(value, dict):
            for v in value.values():
                yield from self._iter_binding_exprs(v)
        elif isinstance(value, list):
            for v in value:
                yield from self._iter_binding_exprs(v)

    def _validate_code_nodes(self, workflow, result: ValidationResult) -> None:
        """Static CodeNode validation (before any execution):

        1. `credential_id` is forbidden (CodeNode has no credential access).
        2. Compile/screen pre-check → CODE_NODE_SYNTAX_ERROR / CODE_NODE_FORBIDDEN
           / CODE_NODE_NO_EXECUTE (line/offset), so the chatbot self-corrects
           statically instead of learning at runtime.
        3. Binding seal (Layer 3): `data`/`params` must not reference a
           credential-like source (e.g. {{ nodes.broker.appkey }}).
        """
        import re
        from programgarden_core.code_node import compile_code_node

        for node in workflow.nodes:
            if node.get("type") != "CodeNode":
                continue
            node_id = node.get("id")

            # 1. credential_id ban
            if node.get("credential_id"):
                result.add(
                    build_error(
                        ErrorCode.CODE_NODE_FORBIDDEN,
                        f"CodeNode '{node_id}' must not reference a credential_id.",
                        location=ErrorLocation(
                            node_id=node_id, node_type="CodeNode",
                            credential_id=node.get("credential_id"),
                        ),
                        suggestion="Remove credential_id — CodeNode has no credential or broker access by design.",
                    )
                )

            # 2. compile / screen pre-check
            screen = compile_code_node(node.get("code", "") or "", node_id or "code", screen=True)
            if not screen.ok:
                try:
                    code_enum = ErrorCode(screen.error_code)
                except ValueError:
                    code_enum = ErrorCode.CODE_NODE_SYNTAX_ERROR
                result.add(
                    build_error(
                        code_enum,
                        screen.message or "CodeNode failed static validation.",
                        location=ErrorLocation(
                            node_id=node_id, node_type="CodeNode", field_path="code",
                        ),
                        suggestion=screen.suggestion,
                        details=screen.details or {},
                    )
                )

            # 3. credential-like binding seal on data/params
            for field_key in ("data", "params"):
                for expr in self._iter_binding_exprs(node.get(field_key)):
                    tokens = {t for t in re.split(r"[^A-Za-z0-9_]+", expr.lower()) if t}
                    hit = tokens & self._CODE_NODE_CRED_KEYWORDS
                    if hit:
                        result.add(
                            build_error(
                                ErrorCode.CODE_NODE_FORBIDDEN,
                                f"CodeNode '{node_id}' input '{field_key}' references a "
                                f"credential-like binding ('{expr}').",
                                location=ErrorLocation(
                                    node_id=node_id, node_type="CodeNode",
                                    field_path=field_key, expression="{{ " + expr + " }}",
                                ),
                                suggestion="Do not feed credentials/secrets into CodeNode — it has no credential access; pass only computed data.",
                                details={"credential_tokens": sorted(hit)},
                            )
                        )

    # SplitNode 는 실 엔진에서 두 조건이 **모두** 충족돼야만 동작한다(6변형 dry_run
    # 프로브로 확정, executor._execute_split_branch / _execute_main_flow):
    #   (1) 짝 AggregateNode 가 그래프상 도달 가능해야 한다. 없으면 _execute_split_branch
    #       가 aggregate_id=None 에서 즉시 return → branch 자체가 실행 안 됨(노드 pending
    #       유지, 하류 item 전부 공백). engine._find_split_aggregate_pairs 참조.
    #   (2) split 로 들어오는 상류 노드가 리스트를 출력해야 한다. 엔진은 분리 대상 배열을
    #       **오직 상류 노드 출력**(포트 symbols/values/array/data/items)에서만 읽는다.
    #       config `array` 필드는 **어느 경로에서도 읽히지 않는다**(SplitNodeExecutor.execute
    #       의 config.get("array") 는 죽은 코드 — 실행 엔진이 그 executor 를 거치지 않고
    #       상류 출력에서 배열을 직접 가져와 item 을 set). 따라서 `array`/`items` 를 config
    #       리터럴로 넣는 저작 패턴은 검증만 통과하고 런타임엔 0개를 낸다.
    # 둘 중 하나라도 빠지면 하류 `{{ nodes.<split>.item }}` 이 조용히 비어 count:0 쓰레기
    # 결과가 된다(단일 심볼에 SplitNode 를 잘못 붙이는 것이 전형적 저작 결함). 정적으로
    # 잡아 AI self-correct 루프가 dry_run 전에 보게 한다.
    # 오탐(최대 리스크) 최소화: (2)는 상류 중 하나라도 리스트를 낼 "가능성"이 있으면 통과.
    #   가능성 = (a) 상류가 CodeNode(동적 출력), (b) 상류 스키마 미상(커뮤니티/제네릭),
    #            (c) 상류 출력 포트 타입 중 하나라도 확정 스칼라/시그널이 아님.
    #            모든 상류가 확정 스칼라일 때만 flag.
    _SPLIT_SCALAR_OUTPUT_TYPES = frozenset({
        "signal", "boolean", "integer", "number", "float", "string",
        "broker_connection",
    })

    def _validate_split_nodes(self, workflow, registry, result: ValidationResult) -> None:
        """SplitNode 가 실 엔진에서 동작 가능하게 배선됐는지 정적 검증(오탐 보수적).

        엔진 동작(프로브 확정): SplitNode 는 (1) 짝 AggregateNode 가 도달 가능하고
        (2) 상류가 리스트를 출력해야만 branch 를 실행한다. config `array` 는 안 읽힌다.
        """
        split_nodes = [
            n for n in workflow.nodes
            if isinstance(n, dict) and n.get("type") == "SplitNode"
        ]
        if not split_nodes:
            return
        node_type_by_id = {
            n.get("id"): n.get("type") for n in workflow.nodes if isinstance(n, dict)
        }
        aggregate_ids: Set[str] = {
            n.get("id") for n in workflow.nodes
            if isinstance(n, dict) and n.get("type") == "AggregateNode"
        }
        # adjacency(from_id -> [to_id]) + incoming(to_id -> [from_id])
        adjacency: Dict[str, List[str]] = {}
        incoming: Dict[str, List[str]] = {}
        for edge in workflow.edges:
            to_raw = getattr(edge, "to_node", "") or ""
            from_raw = getattr(edge, "from_node", "") or ""
            to_id = to_raw.split(".")[0] if to_raw else ""
            from_id = from_raw.split(".")[0] if from_raw else ""
            if to_id:
                incoming.setdefault(to_id, []).append(from_id)
            if from_id and to_id:
                adjacency.setdefault(from_id, []).append(to_id)

        def _reaches_aggregate(start: Optional[str]) -> bool:
            # 엔진 _find_split_aggregate_pairs 와 동일하게 그래프 도달성으로 짝을 판정.
            if not start:
                return False
            seen: Set[str] = set()
            queue: List[str] = [start]
            while queue:
                cur = queue.pop(0)
                if cur in seen:
                    continue
                seen.add(cur)
                for nxt in adjacency.get(cur, []):
                    if nxt in aggregate_ids:
                        return True
                    queue.append(nxt)
            return False

        def _may_produce_list(src_type: Optional[str]) -> bool:
            # 동적/미상 출력은 리스트 가능 → 보수적으로 통과.
            if not src_type or src_type == "CodeNode":
                return True
            schema = registry.get_schema(src_type)
            if schema is None:
                return True
            ports = list(schema.outputs or [])
            if not ports:
                return True  # 출력 미선언 → 알 수 없음 → 통과
            for out in ports:
                ptype = out.get("type") if isinstance(out, dict) else getattr(out, "type", None)
                if ptype not in self._SPLIT_SCALAR_OUTPUT_TYPES:
                    return True  # 배열/오브젝트 등 비스칼라 포트 존재 → 가능성 있음
            return False  # 모든 포트가 확정 스칼라 → 리스트 생산 불가

        for node in split_nodes:
            sid = node.get("id")
            # (1) 짝 AggregateNode 도달성 — 없으면 엔진이 branch 를 실행조차 안 한다.
            if not _reaches_aggregate(sid):
                result.add(
                    build_error(
                        ErrorCode.MISSING_REQUIRED_FIELD,
                        (
                            f"SplitNode '{sid}' has no reachable AggregateNode. The engine "
                            f"only runs a SplitNode's per-item branch when a paired "
                            f"AggregateNode is reachable from it — without one the branch "
                            f"never executes (the node stays pending) and every downstream "
                            f"`{{{{ nodes.{sid}.item }}}}` resolves empty (silent count:0)."
                        ),
                        location=ErrorLocation(node_id=sid, node_type="SplitNode", field_path=None),
                        suggestion=(
                            "Add an AggregateNode downstream of this split's branch (so it is "
                            "reachable from the SplitNode), which recollects the per-item "
                            "results. If you only ever have a single value, DELETE the "
                            "SplitNode and bind that value directly on the downstream node."
                        ),
                    )
                )
                continue
            # (2) 상류 리스트 소스 — config `array` 는 엔진이 안 읽으므로 소스로 인정 안 함.
            srcs = incoming.get(sid, [])
            if srcs and any(_may_produce_list(node_type_by_id.get(s)) for s in srcs):
                continue
            result.add(
                build_error(
                    ErrorCode.MISSING_REQUIRED_FIELD,
                    (
                        f"SplitNode '{sid}' has no upstream node that outputs a list. The "
                        f"engine reads the array to split ONLY from an upstream node's list "
                        f"output (ports symbols/values/array/data/items) — the `array` "
                        f"config field is NOT read at runtime. It will emit zero items and "
                        f"every downstream `{{{{ nodes.{sid}.item }}}}` resolves empty "
                        f"(silent count:0 result)."
                    ),
                    location=ErrorLocation(node_id=sid, node_type="SplitNode", field_path="array"),
                    suggestion=(
                        "Connect an edge from an upstream node that OUTPUTS a list "
                        "(WatchlistNode/MarketUniverseNode → symbols, AccountNode → "
                        "positions, ConditionNode → values, or a CodeNode returning a list). "
                        "Do NOT put the list in an `array`/`items` config field — the engine "
                        "ignores it. For a single known symbol, DELETE SplitNode and bind "
                        "that symbol directly on the downstream node."
                    ),
                )
            )

    def _validate_ai_agent_nodes(self, workflow, result: ValidationResult) -> None:
        """AIAgentNode 는 ai_model 엣지로 LLMModelNode 가 연결돼야 한다.

        LLM 이 없으면 이 노드는 **애초에 동작 불가**(런타임에 raise)이므로 오탐 위험이
        0이다. static validate 에서 잡아 챗봇이 저장 전에 고치게 한다 — deep_validate 는
        인프라 오류 시 검증을 건너뛰고 '성공'으로 저장할 수 있어 못 믿는다(soft-skip).
        ai_model 엣지의 source/target **형태** 오류는 _validate_edge_references 가
        (INVALID_AI_MODEL_EDGE) 별도로 잡으므로, 여기선 '연결 자체가 없는' 구멍만 본다.
        """
        from programgarden_core.models.edge import EdgeType

        agent_ids = [
            n.get("id")
            for n in workflow.nodes
            if isinstance(n, dict) and n.get("type") == "AIAgentNode"
        ]
        if not agent_ids:
            return
        # ai_model 엣지가 타깃으로 삼는 AIAgentNode id 집합
        ai_model_targets: Set[str] = set()
        for edge in workflow.edges:
            edge_type = getattr(edge, "edge_type", None)
            et = (
                edge_type.value if hasattr(edge_type, "value")
                else (str(edge_type) if edge_type else "main")
            )
            if et != EdgeType.AI_MODEL.value:
                continue
            to_raw = getattr(edge, "to_node", "") or ""
            to_id = to_raw.split(".")[0] if to_raw else ""
            if to_id:
                ai_model_targets.add(to_id)

        for aid in agent_ids:
            if aid in ai_model_targets:
                continue
            result.add(
                build_error(
                    ErrorCode.MISSING_REQUIRED_FIELD,
                    f"AIAgentNode '{aid}' has no LLM model connected — it cannot run without "
                    f"one. Connect an LLMModelNode to '{aid}' via an \"ai_model\" edge.",
                    location=ErrorLocation(node_id=aid, node_type="AIAgentNode", field_path="ai_model"),
                    suggestion=(
                        "Add an LLMModelNode and wire it with an ai_model edge, e.g. "
                        f'{{"from": "<llm_node_id>", "to": "{aid}", "edge_type": "ai_model"}}.'
                    ),
                )
            )

    def _validate_display_columns(self, workflow, registry, result: ValidationResult) -> None:
        """Display 노드의 `columns` 키가 상류 출력 스키마에 실재하는지 검증한다.

        `columns` 는 `{{ }}` 바인딩이 아니라 **평범한 문자열 목록**이라 표현식 검증
        (`_validate_expression_references`)의 사정권 밖이었다. 그래서 상류가 내보내지 않는
        이름을 적어도 아무도 막지 않았고, 표는 그 칸에 조용히 `-` 만 찍은 채 워크플로우는
        `completed / errors=0` 으로 보고했다.
        (실측 2026-07-13: 챗봇이 `current_price`/`change_percent` 로 저작 → 시세 노드는
        `price`/`change_pct` 를 내보냄 → 사용자가 요청한 '현재가'가 표에서 사라졌다.)

        🔴 **오탐 0 원칙 — 검증된 포트에만 건다.**
        `fields` 를 선언했다는 것만으로는 부족하다. 라이브러리 곳곳의 선언이 런타임보다
        **불완전**하다(예: `ScreenerNode.symbols` 런타임은 price/market_cap/volume/sector 를
        담는데 `SYMBOL_LIST_FIELDS` 는 exchange/symbol 둘만 선언). 그런 포트에 이 가드를 걸면
        **정상 워크플로우를 대량 오탐**한다(동봉 예제 7건이 실제로 걸렸다).

        그래서 `tests/test_output_schema_contract.py` 로 **선언 == 런타임** 이 증명된 포트만
        여기 등록한다. 다른 포트의 선언을 바로잡을 때마다 계약 검사에 추가하고 이 목록을 넓힌다.
        """
        import re as _re

        # (node_type, port) — 계약 검사로 선언 == 런타임 이 증명된 포트만.
        VERIFIED_PORTS = {
            ("OverseasStockMarketDataNode", "value"),
            ("OverseasStockMarketDataNode", "values"),
            ("OverseasFuturesMarketDataNode", "value"),
            ("OverseasFuturesMarketDataNode", "values"),
            ("KoreaStockMarketDataNode", "value"),
            ("KoreaStockMarketDataNode", "values"),
        }

        DISPLAY_TYPES = {"TableDisplayNode", "ChartDisplayNode"}
        nodes_by_id = {
            n.get("id"): n for n in workflow.nodes
            if isinstance(n, dict) and n.get("id")
        }

        for node in workflow.nodes:
            if not isinstance(node, dict) or node.get("type") not in DISPLAY_TYPES:
                continue
            columns = node.get("columns")
            data_expr = node.get("data")
            if not columns or not isinstance(columns, list) or not isinstance(data_expr, str):
                continue

            m = _re.search(r"nodes\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)", data_expr)
            if not m:
                continue
            src_id, port = m.group(1), m.group(2)
            src_node = nodes_by_id.get(src_id)
            if not src_node:
                continue  # 노드 부재는 _validate_expression_references 가 잡는다
            if (src_node.get("type"), port) not in VERIFIED_PORTS:
                continue  # 선언이 런타임과 일치한다고 증명되지 않은 포트 → 검사하지 않는다

            schema = registry.get_schema(src_node.get("type"))
            if not schema:
                continue
            declared: Set[str] = set()
            for out in (getattr(schema, "outputs", None) or []):
                nm = out.get("name") if isinstance(out, dict) else getattr(out, "name", None)
                if nm != port:
                    continue
                fields = out.get("fields") if isinstance(out, dict) else getattr(out, "fields", None)
                for f in (fields or []):
                    fn = f.get("name") if isinstance(f, dict) else getattr(f, "name", None)
                    if fn:
                        declared.add(fn)
                break
            if not declared:
                continue  # 출력 모양이 열려 있음 → 검사 근거 없음 (오탐 방지)

            for col in columns:
                key = col.get("key") if isinstance(col, dict) else col
                if not isinstance(key, str) or not key or key in declared:
                    continue
                result.add(
                    build_error(
                        ErrorCode.INVALID_EXPRESSION_REF,
                        f"{node.get('type')} '{node.get('id')}' lists column '{key}', but node "
                        f"'{src_id}' does not output a field with that name on port '{port}'. "
                        f"The column would render as '-' while the workflow still reports success.",
                        location=ErrorLocation(
                            node_id=node.get("id"),
                            node_type=node.get("type"),
                            field_path="columns",
                        ),
                        suggestion=(
                            f"Use one of the fields '{src_id}.{port}' actually outputs: "
                            f"{', '.join(sorted(declared))}."
                        ),
                    )
                )

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
