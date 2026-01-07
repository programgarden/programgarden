"""
ProgramGarden Core - NodeTypeRegistry

Node type schema registry
AI can query "what node types are available?"
"""

from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel, Field

from programgarden_core.nodes.base import BaseNode, NodeCategory, InputPort, OutputPort
from programgarden_core.i18n import translate_schema


class NodeTypeSchema(BaseModel):
    """Node type schema (for AI agents)"""

    node_type: str = Field(..., description="Node type name")
    category: str = Field(..., description="Node category")
    description: Optional[str] = Field(default=None, description="Node description")
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

    Registry for registering and querying 37 node types.
    Used by AI agents to query available node list.
    """

    _instance: Optional["NodeTypeRegistry"] = None
    _registry: Dict[str, Type[BaseNode]] = {}
    _schemas: Dict[str, NodeTypeSchema] = {}

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
            MarketDataNode, AccountNode, HistoricalDataNode, SQLiteNode, PostgresNode,
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode,
            ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode,
            ConditionNode, LogicNode, PerformanceConditionNode,
            PositionSizingNode, RiskGuardNode, RiskConditionNode,
            NewOrderNode, ModifyOrderNode, CancelOrderNode, LiquidateNode,
            EventHandlerNode, ErrorHandlerNode, AlertNode,
            DisplayNode,
            GroupNode,
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
            MarketDataNode, AccountNode, HistoricalDataNode, SQLiteNode, PostgresNode,
            # Symbol
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode,
            # Trigger
            ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode,
            # Condition
            ConditionNode, LogicNode, PerformanceConditionNode,
            # Risk
            PositionSizingNode, RiskGuardNode, RiskConditionNode,
            # Order
            NewOrderNode, ModifyOrderNode, CancelOrderNode, LiquidateNode,
            # Event
            EventHandlerNode, ErrorHandlerNode, AlertNode,
            # Display
            DisplayNode,
            # Group
            GroupNode,
            # Backtest
            BacktestEngineNode,
            # Job
            DeployNode, TradingHaltNode, JobControlNode,
            # Calculation
            CustomPnLNode,
        ]

        for node_class in node_classes:
            self.register(node_class)

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
        
        schema = NodeTypeSchema(
            node_type=type_name,
            category=instance.category.value if hasattr(instance.category, 'value') else instance.category,
            description=description,
            inputs=[inp.model_dump() for inp in instance.get_inputs()],
            outputs=[out.model_dump() for out in instance.get_outputs()],
            config_schema=self._extract_config_schema(node_class),
        )
        self._schemas[type_name] = schema

    def _extract_config_schema(self, node_class: Type[BaseNode]) -> Dict[str, Any]:
        """Extract config schema from node class"""
        schema = {}
        model_fields = node_class.model_fields

        # BaseNode 필드 제외
        base_fields = {"id", "type", "category", "position", "config", "description"}
        # PluginNode 필드 (해당되는 경우)
        plugin_fields = {"plugin", "plugin_version", "params"}

        for field_name, field_info in model_fields.items():
            if field_name in base_fields:
                continue

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

    def list_categories(self) -> List[Dict[str, Any]]:
        """List categories (with node count)"""
        category_counts: Dict[str, int] = {}
        for schema in self._schemas.values():
            cat = schema.category
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return [
            {
                "category": cat,
                "count": count,
                "description": NodeCategory(cat).name if cat in [e.value for e in NodeCategory] else cat,
            }
            for cat, count in sorted(category_counts.items())
        ]

    def create_node(self, node_type: str, **kwargs) -> BaseNode:
        """Create node instance"""
        node_class = self.get(node_type)
        if not node_class:
            raise ValueError(f"Unknown node type: {node_type}")
        return node_class(**kwargs)
