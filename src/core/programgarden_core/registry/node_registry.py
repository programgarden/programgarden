"""
ProgramGarden Core - NodeTypeRegistry

Node type schema registry
AI can query "what node types are available?"
"""

from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel, Field

from programgarden_core.nodes.base import BaseNode, NodeCategory, InputPort, OutputPort, ProductScope, BrokerProvider
from programgarden_core.i18n import translate_schema, translate_category


class NodeTypeSchema(BaseModel):
    """Node type schema (for AI agents and clients)"""

    node_type: str = Field(..., description="Node type name")
    display_name: str = Field(..., description="Node display name (i18n key or translated)")
    category: str = Field(..., description="Node category")
    description: Optional[str] = Field(default=None, description="Node description")
    img_url: Optional[str] = Field(default=None, description="Node icon image URL")
    product_scope: str = Field(default="all", description="Product scope: overseas_stock | overseas_futures | all")
    broker_provider: str = Field(default="all", description="Broker provider: ls-sec.co.kr | all")
    inputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Input port definitions with display_name",
    )
    outputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Output port definitions with display_name",
    )
    config_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="Simple field metadata for client form rendering. "
                    "Each field contains: type, display_name, description, required, "
                    "category (parameters/settings), expression_mode, etc.",
    )
    display_data_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Schema describing the data structure produced by Display nodes at runtime. "
                    "Properties with 'resolved_by' indicate dynamic field names determined by node settings.",
    )
    connection_rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Connection rules for this node (deny_direct_from, required_intermediate, etc.)",
    )
    rate_limit: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Node-level rate limit config (min_interval_sec, max_concurrent, etc.)",
    )

    # === AI chatbot metadata (English, loaded from _ai_metadata/{NodeType}.json) ===
    usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Granular usage guidance authored in English for the workflow-"
            "generation AI chatbot. Shape:\n"
            "- when_to_use: List[str] — concrete scenarios this node is for\n"
            "- when_not_to_use: List[str] — cases where a different node fits better\n"
            "- typical_scenarios: List[str] — 3–5 common workflow patterns"
        ),
    )
    features: Optional[List[str]] = Field(
        default=None,
        description=(
            "Bullet list of strengths / constraints in English. Example: "
            "'Auto-iterates over upstream array output', 'No credential required'."
        ),
    )
    anti_patterns: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description=(
            "Common misuses with alternatives (English). Each entry: "
            "- pattern: str — the misuse\n"
            "- reason: str — why it is wrong\n"
            "- alternative: str — the correct approach (another node / expression)"
        ),
    )
    examples: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description=(
            "Executable full workflow examples (2–3 per node) authored in "
            "English. Each entry: title / description / workflow_snippet "
            "(complete dict with nodes, edges, credentials, bindings) / "
            "expected_output. The workflow_snippet MUST pass "
            "WorkflowExecutor.validate()."
        ),
    )
    node_guide: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Text-oriented guide complementing examples (English). Shape:\n"
            "- input_handling: str — how inputs are supplied "
            "(direct / `{{ nodes.X.Y }}` / auto-iterate / credential)\n"
            "- output_consumption: str — output shape + how downstream nodes bind\n"
            "- common_combinations: List[str] — frequently paired node chains\n"
            "- pitfalls: List[str] — connection caveats and shape requirements"
        ),
    )


class NodeTypeRegistry:
    """
    Node type registry

    Registry for registering and querying node types.
    Used by AI agents to query available node list.
    Supports both built-in nodes and community nodes.
    """

    _instance: Optional["NodeTypeRegistry"] = None
    _registry: Dict[str, Type[BaseNode]] = {}
    _schemas: Dict[str, NodeTypeSchema] = {}
    _community_nodes: Dict[str, Dict[str, Any]] = {}  # 커뮤니티 노드 메타데이터

    def __new__(cls) -> "NodeTypeRegistry":
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Register built-in node types"""
        # 지연 임포트로 순환 참조 방지
        from programgarden_core.nodes import (
            StartNode, ThrottleNode, SplitNode, AggregateNode, IfNode,
            OverseasStockBrokerNode, OverseasFuturesBrokerNode,
            # Market - Stock (해외주식)
            OverseasStockMarketDataNode, OverseasStockFundamentalNode,
            OverseasStockHistoricalDataNode,
            OverseasStockRealMarketDataNode,
            OverseasStockSymbolQueryNode,
            # Market - Futures (해외선물)
            OverseasFuturesMarketDataNode, OverseasFuturesHistoricalDataNode,
            OverseasFuturesRealMarketDataNode,
            OverseasFuturesSymbolQueryNode,
            # Account - Stock (해외주식)
            OverseasStockAccountNode, OverseasStockRealAccountNode, OverseasStockRealOrderEventNode,
            # Account - Futures (해외선물)
            OverseasFuturesAccountNode, OverseasFuturesRealAccountNode, OverseasFuturesRealOrderEventNode,
            # Open Orders (미체결 조회)
            OverseasStockOpenOrdersNode, OverseasFuturesOpenOrdersNode,
            # Korea Stock (국내주식)
            KoreaStockBrokerNode,
            KoreaStockAccountNode, KoreaStockOpenOrdersNode,
            KoreaStockMarketDataNode, KoreaStockFundamentalNode,
            KoreaStockHistoricalDataNode, KoreaStockSymbolQueryNode,
            KoreaStockRealMarketDataNode, KoreaStockRealAccountNode, KoreaStockRealOrderEventNode,
            KoreaStockNewOrderNode, KoreaStockModifyOrderNode, KoreaStockCancelOrderNode,
            # Data (상품 무관)
            SQLiteNode, HTTPRequestNode, FieldMappingNode,
            # Market External (credential 불필요)
            CurrencyRateNode,
            # Market Status (JIF 장운영정보 — credential agnostic)
            MarketStatusNode,
            # Symbol (상품 무관)
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, ExclusionListNode,
            ScheduleNode, TradingHoursFilterNode,
            ConditionNode, LogicNode,
            PositionSizingNode, PortfolioNode,
            OverseasStockNewOrderNode, OverseasStockModifyOrderNode, OverseasStockCancelOrderNode,
            OverseasFuturesNewOrderNode, OverseasFuturesModifyOrderNode, OverseasFuturesCancelOrderNode,
            TableDisplayNode, LineChartNode, MultiLineChartNode,
            CandlestickChartNode, BarChartNode, SummaryDisplayNode,
            BacktestEngineNode, BenchmarkCompareNode,
            # AI (에이전트, LLM 연결)
            LLMModelNode, AIAgentNode,
        )

        node_classes = [
            # Infra
            StartNode, ThrottleNode, SplitNode, AggregateNode, IfNode,
            # Broker (상품별 분리)
            OverseasStockBrokerNode, OverseasFuturesBrokerNode,
            # Market - Stock (해외주식)
            OverseasStockMarketDataNode, OverseasStockFundamentalNode,
            OverseasStockHistoricalDataNode,
            OverseasStockRealMarketDataNode,
            OverseasStockSymbolQueryNode,
            # Market - Futures (해외선물)
            OverseasFuturesMarketDataNode, OverseasFuturesHistoricalDataNode,
            OverseasFuturesRealMarketDataNode,
            OverseasFuturesSymbolQueryNode,
            # Account - Stock (해외주식)
            OverseasStockAccountNode, OverseasStockRealAccountNode, OverseasStockRealOrderEventNode,
            # Account - Futures (해외선물)
            OverseasFuturesAccountNode, OverseasFuturesRealAccountNode, OverseasFuturesRealOrderEventNode,
            # Open Orders (미체결 조회)
            OverseasStockOpenOrdersNode, OverseasFuturesOpenOrdersNode,
            # Korea Stock (국내주식)
            KoreaStockBrokerNode,
            KoreaStockAccountNode, KoreaStockOpenOrdersNode,
            KoreaStockMarketDataNode, KoreaStockFundamentalNode,
            KoreaStockHistoricalDataNode, KoreaStockSymbolQueryNode,
            KoreaStockRealMarketDataNode, KoreaStockRealAccountNode, KoreaStockRealOrderEventNode,
            KoreaStockNewOrderNode, KoreaStockModifyOrderNode, KoreaStockCancelOrderNode,
            # Data (상품 무관)
            SQLiteNode, HTTPRequestNode, FieldMappingNode,
            # Market External (credential 불필요)
            CurrencyRateNode,
            # Market Status (JIF 장운영정보 — credential agnostic)
            MarketStatusNode,
            # Symbol (상품 무관)
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, ExclusionListNode,
            # Trigger
            ScheduleNode, TradingHoursFilterNode,
            # Condition
            ConditionNode, LogicNode,
            # Risk
            PositionSizingNode, PortfolioNode,
            # Order (해외주식)
            OverseasStockNewOrderNode, OverseasStockModifyOrderNode, OverseasStockCancelOrderNode,
            # Order (해외선물)
            OverseasFuturesNewOrderNode, OverseasFuturesModifyOrderNode, OverseasFuturesCancelOrderNode,
            # messaging - 커뮤니티 노드(TelegramNode 등)에서 등록
            # Display (6개)
            TableDisplayNode, LineChartNode, MultiLineChartNode,
            CandlestickChartNode, BarChartNode, SummaryDisplayNode,
            # Backtest/Analysis
            BacktestEngineNode, BenchmarkCompareNode,
            # AI (에이전트, LLM 연결)
            LLMModelNode, AIAgentNode,
        ]

        for node_class in node_classes:
            self.register(node_class)

    def register_community(
        self,
        node_class: Type[BaseNode],
        source: str = "community",
        trust_level: str = "community",
    ) -> None:
        """
        커뮤니티 노드 타입 등록

        Args:
            node_class: 노드 클래스 (BaseNode 또는 BaseNotificationNode 상속)
            source: 노드 출처 ("community", "user")
            trust_level: 신뢰 레벨 ("core", "verified", "community")

        Raises:
            ValueError: 노드 타입 이름이 이미 존재하는 경우
        """
        type_name = node_class.__name__

        # 중복 체크 (내장 노드와 충돌 방지)
        if type_name in self._registry:
            raise ValueError(f"Node type '{type_name}' already exists in registry")

        # 일반 등록 수행
        self.register(node_class)

        # 커뮤니티 노드 메타데이터 저장
        self._community_nodes[type_name] = {
            "source": source,
            "trust_level": trust_level,
        }

    def is_community(self, node_type: str) -> bool:
        """노드가 커뮤니티 노드인지 확인"""
        return node_type in self._community_nodes

    def get_community_info(self, node_type: str) -> Optional[Dict[str, Any]]:
        """커뮤니티 노드의 메타데이터 조회"""
        return self._community_nodes.get(node_type)

    def list_community_nodes(self, source: Optional[str] = None) -> List[str]:
        """커뮤니티 노드 목록 조회"""
        if source:
            return [
                name for name, info in self._community_nodes.items()
                if info["source"] == source
            ]
        return list(self._community_nodes.keys())

    def register(self, node_class: Type[BaseNode]) -> None:
        """Register node type"""
        import typing
        from typing import get_origin, get_args
        
        # 타입명 추출 (Literal에서)
        type_name = node_class.__name__

        self._registry[type_name] = node_class

        # 스키마 생성용 인스턴스 생성
        # 모든 필수 필드에 대해 기본값 제공
        init_kwargs: Dict[str, Any] = {"id": "__schema__", "type": type_name}
        
        # 모든 필수 필드에 임시 기본값 제공
        for field_name, field_info in node_class.model_fields.items():
            if field_name in {"id", "type", "category", "position", "config", "description"}:
                continue
            if field_info.is_required():
                # 타입에 따른 기본값 제공
                annotation = field_info.annotation
                origin = get_origin(annotation)
                args = get_args(annotation)
                
                # Literal 타입 처리 - 첫 번째 값 사용
                if origin is typing.Literal:
                    init_kwargs[field_name] = args[0] if args else "__schema__"
                elif annotation == str:
                    init_kwargs[field_name] = "__schema__"
                elif annotation == int:
                    init_kwargs[field_name] = 0
                elif annotation == float:
                    init_kwargs[field_name] = 0.0
                elif annotation == bool:
                    init_kwargs[field_name] = False
                elif origin is list:
                    init_kwargs[field_name] = []
                elif origin is dict or annotation is dict:
                    init_kwargs[field_name] = {}
                else:
                    init_kwargs[field_name] = "__schema__"
        
        instance = node_class(**init_kwargs)
        
        # Use instance.description if available (for i18n), otherwise use docstring
        description = instance.description if hasattr(instance, 'description') and instance.description else node_class.__doc__
        
        # Get img_url from class variable, fallback to default placeholder
        img_url = getattr(node_class, '_img_url', None)
        if not img_url:
            # 카테고리별 기본 아이콘
            category_icons = {
                "infra": "https://cdn-icons-png.flaticon.com/512/2099/2099058.png",
                "realtime": "https://cdn-icons-png.flaticon.com/512/2972/2972531.png",
                "data": "https://cdn-icons-png.flaticon.com/512/2906/2906274.png",
                "account": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                "symbol": "https://cdn-icons-png.flaticon.com/512/3135/3135706.png",
                "trigger": "https://cdn-icons-png.flaticon.com/512/2972/2972185.png",
                "condition": "https://cdn-icons-png.flaticon.com/512/1828/1828643.png",
                "risk": "https://cdn-icons-png.flaticon.com/512/2345/2345338.png",
                "order": "https://cdn-icons-png.flaticon.com/512/3144/3144456.png",
                "messaging": "https://cdn-icons-png.flaticon.com/512/3239/3239952.png",
                "display": "https://cdn-icons-png.flaticon.com/512/2920/2920349.png",
                "backtest": "https://cdn-icons-png.flaticon.com/512/2920/2920244.png",
                "job": "https://cdn-icons-png.flaticon.com/512/1087/1087815.png",
                "ai": "https://cdn-icons-png.flaticon.com/512/4712/4712139.png",
            }
            cat_value = instance.category.value if hasattr(instance.category, 'value') else instance.category
            img_url = category_icons.get(cat_value, "https://cdn-icons-png.flaticon.com/512/2099/2099058.png")
        
        # product_scope, broker_provider 추출
        product_scope = getattr(node_class, '_product_scope', ProductScope.ALL)
        broker_provider = getattr(node_class, '_broker_provider', BrokerProvider.ALL)
        product_scope_value = product_scope.value if hasattr(product_scope, 'value') else str(product_scope)
        broker_provider_value = broker_provider.value if hasattr(broker_provider, 'value') else str(broker_provider)

        config_schema = self._build_config_schema(node_class, type_name)

        # Display 노드의 런타임 데이터 스키마
        display_data_schema = getattr(node_class, '_display_data_schema', None)

        # 연결 규칙 직렬화 (_connection_rules ClassVar → dict 리스트)
        connection_rules_raw = getattr(node_class, '_connection_rules', [])
        serialized_connection_rules = [
            rule.model_dump() for rule in connection_rules_raw
        ]

        # Rate limit 직렬화 (_rate_limit ClassVar → dict)
        rate_limit_config = getattr(node_class, '_rate_limit', None)
        serialized_rate_limit = rate_limit_config.model_dump() if rate_limit_config else None

        # 입출력 포트 직렬화 시 display_name 자동 추가
        inputs = self._serialize_ports(instance.get_inputs(), type_name)
        outputs = self._serialize_ports(instance.get_outputs(), type_name)

        # display_name: i18n 키 (기본값), locale 전달 시 번역됨
        display_name = f"i18n:nodes.{type_name}.name"

        # AI-facing metadata — each field is a flat ClassVar on the class,
        # mirroring the existing `_img_url` / `_connection_rules` / `_rate_limit`
        # pattern. English only. Missing attribute → None.
        schema = NodeTypeSchema(
            node_type=type_name,
            display_name=display_name,
            category=instance.category.value if hasattr(instance.category, 'value') else instance.category,
            description=description,
            img_url=img_url,
            product_scope=product_scope_value,
            broker_provider=broker_provider_value,
            inputs=inputs,
            outputs=outputs,
            config_schema=config_schema,
            display_data_schema=display_data_schema,
            connection_rules=serialized_connection_rules,
            rate_limit=serialized_rate_limit,
            usage=getattr(node_class, "_usage", None),
            features=getattr(node_class, "_features", None),
            anti_patterns=getattr(node_class, "_anti_patterns", None),
            examples=getattr(node_class, "_examples", None),
            node_guide=getattr(node_class, "_node_guide", None),
        )
        self._schemas[type_name] = schema

    def _serialize_ports(self, ports: List, node_type: str) -> List[Dict[str, Any]]:
        """
        포트 목록을 직렬화하면서 display_name을 자동 추가합니다.

        display_name 우선순위:
        1. 포트에 직접 설정된 display_name
        2. i18n 키 형식: portNames.{port_name} (공통 포트)

        Args:
            ports: InputPort 또는 OutputPort 목록
            node_type: 노드 타입명

        Returns:
            직렬화된 포트 딕셔너리 목록
        """
        result = []
        for port in ports:
            port_dict = port.model_dump(exclude_none=True)

            # display_name이 없으면 i18n 키 생성 (기존 ports.xxx 형식 사용)
            if not port_dict.get("display_name"):
                port_dict["display_name"] = f"i18n:ports.{port.name}"

            result.append(port_dict)

        return result

    def _build_config_schema(self, node_class: Type[BaseNode], node_type: str) -> Dict[str, Any]:
        """
        노드의 필드 스키마를 단순한 config_schema 형식으로 변환합니다.

        json_dynamic_widget 형식이 아닌, 필드별 메타데이터만 제공합니다.
        클라이언트에서 UI 컴포넌트 결정 및 폼 렌더링에 활용합니다.

        Args:
            node_class: 노드 클래스
            node_type: 노드 타입명 (예: "OverseasStockBrokerNode")

        Returns:
            dict: {field_name: field_config, ...} 형식의 config_schema
        """
        if not hasattr(node_class, 'get_field_schema'):
            return {}

        field_schemas = node_class.get_field_schema()
        if not field_schemas:
            return {}

        config_schema: Dict[str, Any] = {}

        for name, fs in field_schemas.items():
            try:
                config_schema[name] = fs.to_config_dict(node_type)
            except Exception as e:
                # 변환 실패 시 최소 정보만 제공
                config_schema[name] = {
                    "type": "string",
                    "display_name": name.replace("_", " ").title(),
                    "required": False,
                    "category": "parameters",
                    "expression_mode": "both",
                    "error": str(e),
                }

        return config_schema

    def get(self, node_type: str) -> Optional[Type[BaseNode]]:
        """Query node class"""
        return self._registry.get(node_type)

    def get_schema(self, node_type: str, locale: Optional[str] = None) -> Optional[NodeTypeSchema]:
        """Query node schema with optional locale translation"""
        schema = self._schemas.get(node_type)
        if schema and locale:
            # Translate schema to requested locale
            schema_dict = schema.model_dump()
            translated = translate_schema(schema_dict, locale=locale)
            return NodeTypeSchema(**translated)
        return schema

    def list_types(self, category: Optional[str] = None) -> List[str]:
        """List registered node types"""
        if category:
            return [
                name for name, schema in self._schemas.items()
                if schema.category == category
            ]
        return list(self._registry.keys())

    def list_schemas(self, category: Optional[str] = None, locale: Optional[str] = None, product_scope: Optional[str] = None) -> List[NodeTypeSchema]:
        """List registered node schemas (for AI agents) with optional locale translation and product_scope filter"""
        schemas = [
            schema for schema in self._schemas.values()
            if (not category or schema.category == category)
            and (not product_scope or schema.product_scope == product_scope or schema.product_scope == "all")
        ]
        
        if locale:
            # Translate all schemas
            translated_schemas = []
            for schema in schemas:
                schema_dict = schema.model_dump()
                translated = translate_schema(schema_dict, locale=locale)
                translated_schemas.append(NodeTypeSchema(**translated))
            return translated_schemas
        
        return schemas

    def list_categories(self, locale: Optional[str] = None) -> List[Dict[str, Any]]:
        """List categories with node count and optional locale translation"""
        category_counts: Dict[str, int] = {}
        for schema in self._schemas.values():
            cat = schema.category
            category_counts[cat] = category_counts.get(cat, 0) + 1

        result = []
        for cat, count in sorted(category_counts.items()):
            if locale:
                cat_info = translate_category(cat, locale)
                cat_info["count"] = count
            else:
                cat_info = {
                    "id": cat,
                    "name": NodeCategory(cat).name if cat in [e.value for e in NodeCategory] else cat,
                    "description": "",
                    "count": count,
                }
            result.append(cat_info)
        
        return result

    def create_node(self, node_type: str, **kwargs) -> BaseNode:
        """Create node instance"""
        node_class = self.get(node_type)
        if not node_class:
            raise ValueError(f"Unknown node type: {node_type}")
        return node_class(**kwargs)
