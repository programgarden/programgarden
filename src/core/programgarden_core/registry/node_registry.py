"""
ProgramGarden Core - NodeTypeRegistry

Node type schema registry
AI can query "what node types are available?"
"""

from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel, Field

from programgarden_core.nodes.base import BaseNode, NodeCategory, InputPort, OutputPort
from programgarden_core.i18n import translate_schema, translate_category


class NodeTypeSchema(BaseModel):
    """Node type schema (for AI agents)"""

    node_type: str = Field(..., description="Node type name")
    category: str = Field(..., description="Node category")
    description: Optional[str] = Field(default=None, description="Node description")
    img_url: Optional[str] = Field(default=None, description="Node icon image URL")
    inputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Input port definitions",
    )
    outputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Output port definitions",
    )
    config_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration schema",
    )


class NodeTypeRegistry:
    """
    Node type registry

    Registry for registering and querying node types.
    Used by AI agents to query available node list.
    Supports both built-in nodes and external (community) nodes.
    """

    _instance: Optional["NodeTypeRegistry"] = None
    _registry: Dict[str, Type[BaseNode]] = {}
    _schemas: Dict[str, NodeTypeSchema] = {}
    _external_nodes: Dict[str, Dict[str, Any]] = {}  # 외부 노드 메타데이터

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
            StartNode, BrokerNode,
            RealMarketDataNode, RealAccountNode, RealOrderEventNode,
            MarketDataNode, AccountNode, HistoricalDataNode, SQLiteNode, PostgresNode, HTTPRequestNode,
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, SymbolQueryNode,
            ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode,
            ConditionNode, LogicNode, PerformanceConditionNode,
            PositionSizingNode, RiskGuardNode, RiskConditionNode, PortfolioNode,
            NewOrderNode, ModifyOrderNode, CancelOrderNode, LiquidateNode,
            DisplayNode,
            BacktestEngineNode,
            DeployNode, TradingHaltNode, JobControlNode,
            CustomPnLNode,
        )

        node_classes = [
            # Infra
            StartNode, BrokerNode,
            # Realtime
            RealMarketDataNode, RealAccountNode, RealOrderEventNode,
            # Data
            MarketDataNode, AccountNode, HistoricalDataNode, SQLiteNode, PostgresNode, HTTPRequestNode,
            # Symbol
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, SymbolQueryNode,
            # Trigger
            ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode,
            # Condition
            ConditionNode, LogicNode, PerformanceConditionNode,
            # Risk
            PositionSizingNode, RiskGuardNode, RiskConditionNode, PortfolioNode,
            # Order
            NewOrderNode, ModifyOrderNode, CancelOrderNode, LiquidateNode,
            # Event - 커뮤니티 노드(TelegramNode 등)로 대체됨
            # Display
            DisplayNode,
            # Backtest
            BacktestEngineNode,
            # Job
            DeployNode, TradingHaltNode, JobControlNode,
            # Calculation
            CustomPnLNode,
        ]

        for node_class in node_classes:
            self.register(node_class)

    def register_external(
        self,
        node_class: Type[BaseNode],
        source: str = "community",
        trust_level: str = "community",
    ) -> None:
        """
        외부 노드 타입 등록 (커뮤니티/사용자용)
        
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
        
        # 외부 노드 메타데이터 저장
        self._external_nodes[type_name] = {
            "source": source,
            "trust_level": trust_level,
        }

    def is_external(self, node_type: str) -> bool:
        """노드가 외부(커뮤니티) 노드인지 확인"""
        return node_type in self._external_nodes

    def get_external_info(self, node_type: str) -> Optional[Dict[str, Any]]:
        """외부 노드의 메타데이터 조회"""
        return self._external_nodes.get(node_type)

    def list_external_nodes(self, source: Optional[str] = None) -> List[str]:
        """외부 노드 목록 조회"""
        if source:
            return [
                name for name, info in self._external_nodes.items()
                if info["source"] == source
            ]
        return list(self._external_nodes.keys())

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
                "event": "https://cdn-icons-png.flaticon.com/512/3239/3239952.png",
                "display": "https://cdn-icons-png.flaticon.com/512/2920/2920349.png",
                "backtest": "https://cdn-icons-png.flaticon.com/512/2920/2920244.png",
                "job": "https://cdn-icons-png.flaticon.com/512/1087/1087815.png",
                "calculation": "https://cdn-icons-png.flaticon.com/512/897/897368.png",
            }
            cat_value = instance.category.value if hasattr(instance.category, 'value') else instance.category
            img_url = category_icons.get(cat_value, "https://cdn-icons-png.flaticon.com/512/2099/2099058.png")
        
        schema = NodeTypeSchema(
            node_type=type_name,
            category=instance.category.value if hasattr(instance.category, 'value') else instance.category,
            description=description,
            img_url=img_url,
            inputs=[inp.model_dump() for inp in instance.get_inputs()],
            outputs=[out.model_dump() for out in instance.get_outputs()],
            config_schema=self._extract_config_schema(node_class),
        )
        self._schemas[type_name] = schema

    def _extract_config_schema(self, node_class: Type[BaseNode]) -> Dict[str, Any]:
        """Extract config schema from node class
        
        Prioritizes _field_schema if available, falls back to Pydantic model_fields.
        Excludes fields with exclude=True (credential-injected fields).
        Includes category (PARAMETERS/SETTINGS) if available in _field_schema.
        """
        schema = {}
        model_fields = node_class.model_fields

        # BaseNode 필드 제외
        base_fields = {"id", "type", "category", "position", "config", "description"}
        # UI에서 숨길 필드 (내부용)
        hidden_fields = {"plugin_version"}  # community 플러그인은 버전 관리 불필요

        # _field_schema가 있으면 우선 사용 (get_field_schema에 정의된 필드만 UI에 표시)
        field_schema_dict = node_class.get_field_schema() if hasattr(node_class, 'get_field_schema') else {}
        
        # get_field_schema가 있으면 그 필드만 사용, 없으면 model_fields 전체 사용
        has_field_schema = bool(field_schema_dict)

        for field_name, field_info in model_fields.items():
            if field_name in base_fields:
                continue
            
            # UI에서 숨길 필드 제외
            if field_name in hidden_fields:
                continue
            
            # exclude=True인 필드는 스키마에서 제외 (credential에서 주입되는 필드)
            if field_info.exclude:
                continue
            
            # get_field_schema가 정의되어 있고, 해당 필드가 없으면 스키마에서 제외
            # (내부용 필드로 취급 - UI에 노출하지 않음)
            if has_field_schema and field_name not in field_schema_dict:
                continue

            # _field_schema에 정의가 있으면 사용
            if field_name in field_schema_dict:
                fs = field_schema_dict[field_name]
                field_schema = {
                    "type": fs.type.value if hasattr(fs.type, 'value') else str(fs.type),
                    "required": fs.required,
                }
                if fs.default is not None:
                    field_schema["default"] = fs.default
                if fs.description:
                    field_schema["description"] = fs.description
                if fs.enum_values:
                    field_schema["enum_values"] = fs.enum_values
                if fs.enum_labels:
                    field_schema["enum_labels"] = fs.enum_labels
                if fs.bindable is not None:
                    field_schema["bindable"] = fs.bindable
                if fs.expression_enabled is not None:
                    field_schema["expression_enabled"] = fs.expression_enabled
                # category 추가 (PARAMETERS/SETTINGS)
                if fs.category is not None:
                    field_schema["category"] = fs.category.value if hasattr(fs.category, 'value') else str(fs.category)
                # ui_component 추가 (symbol_editor 등)
                if hasattr(fs, 'ui_component') and fs.ui_component:
                    field_schema["ui_component"] = fs.ui_component
                # ui_hint 추가
                if hasattr(fs, 'ui_hint') and fs.ui_hint:
                    field_schema["ui_hint"] = fs.ui_hint
                # === 바인딩 가이드 필드 추가 ===
                if hasattr(fs, 'example') and fs.example is not None:
                    field_schema["example"] = fs.example
                if hasattr(fs, 'example_binding') and fs.example_binding:
                    field_schema["example_binding"] = fs.example_binding
                if hasattr(fs, 'bindable_sources') and fs.bindable_sources:
                    field_schema["bindable_sources"] = fs.bindable_sources
                if hasattr(fs, 'expected_type') and fs.expected_type:
                    field_schema["expected_type"] = fs.expected_type
                # === 조건부 표시 필드 추가 ===
                if hasattr(fs, 'visible_when') and fs.visible_when:
                    field_schema["visible_when"] = fs.visible_when
                if hasattr(fs, 'depends_on') and fs.depends_on:
                    field_schema["depends_on"] = fs.depends_on
            else:
                # Pydantic 필드에서 추출
                field_type = str(field_info.annotation) if field_info.annotation else "any"
                field_schema = {
                    "type": field_type,
                    "required": field_info.is_required(),
                }
                if field_info.default is not None:
                    field_schema["default"] = field_info.default
                if field_info.description:
                    field_schema["description"] = field_info.description

            schema[field_name] = field_schema

        return schema

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

    def list_schemas(self, category: Optional[str] = None, locale: Optional[str] = None) -> List[NodeTypeSchema]:
        """List registered node schemas (for AI agents) with optional locale translation"""
        schemas = [
            schema for schema in self._schemas.values()
            if not category or schema.category == category
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
