"""
ProgramGarden Core - NodeTypeRegistry

노드 타입 스키마 레지스트리
AI가 "어떤 노드 타입 있어?" 질의 가능
"""

from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel, Field

from programgarden_core.nodes.base import BaseNode, NodeCategory, InputPort, OutputPort


class NodeTypeSchema(BaseModel):
    """노드 타입 스키마 (AI 에이전트용)"""

    node_type: str = Field(..., description="노드 타입명")
    category: str = Field(..., description="노드 카테고리")
    description: Optional[str] = Field(default=None, description="노드 설명")
    inputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="입력 포트 정의",
    )
    outputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="출력 포트 정의",
    )
    config_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="설정 스키마",
    )


class NodeTypeRegistry:
    """
    노드 타입 레지스트리

    26개 노드 타입을 등록하고 조회하는 레지스트리.
    AI 에이전트가 사용 가능한 노드 목록을 조회할 때 사용.
    """

    _instance: Optional["NodeTypeRegistry"] = None
    _registry: Dict[str, Type[BaseNode]] = {}
    _schemas: Dict[str, NodeTypeSchema] = {}

    def __new__(cls) -> "NodeTypeRegistry":
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """내장 노드 타입 등록"""
        # 지연 임포트로 순환 참조 방지
        from programgarden_core.nodes import (
            StartNode, BrokerNode,
            RealMarketDataNode, RealAccountNode, RealOrderEventNode,
            MarketDataNode, AccountNode,
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode,
            ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode,
            ConditionNode, LogicNode,
            PositionSizingNode, RiskGuardNode,
            NewOrderNode, ModifyOrderNode, CancelOrderNode,
            EventHandlerNode, ErrorHandlerNode, AlertNode,
            DisplayNode,
            GroupNode,
        )

        node_classes = [
            # Infra
            StartNode, BrokerNode,
            # Realtime
            RealMarketDataNode, RealAccountNode, RealOrderEventNode,
            # Data
            MarketDataNode, AccountNode,
            # Symbol
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode,
            # Trigger
            ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode,
            # Condition
            ConditionNode, LogicNode,
            # Risk
            PositionSizingNode, RiskGuardNode,
            # Order
            NewOrderNode, ModifyOrderNode, CancelOrderNode,
            # Event
            EventHandlerNode, ErrorHandlerNode, AlertNode,
            # Display
            DisplayNode,
            # Group
            GroupNode,
        ]

        for node_class in node_classes:
            self.register(node_class)

    def register(self, node_class: Type[BaseNode]) -> None:
        """노드 타입 등록"""
        # 타입명 추출 (Literal에서)
        type_name = node_class.__name__

        self._registry[type_name] = node_class

        # 스키마 생성용 인스턴스 생성
        # PluginNode 상속 노드는 plugin 필드 기본값 필요
        init_kwargs: Dict[str, Any] = {"id": "__schema__", "type": type_name}
        
        # plugin 필드가 required인 경우 기본값 제공
        if "plugin" in node_class.model_fields:
            field_info = node_class.model_fields["plugin"]
            if field_info.is_required():
                init_kwargs["plugin"] = "__schema__"
        
        instance = node_class(**init_kwargs)
        schema = NodeTypeSchema(
            node_type=type_name,
            category=instance.category.value if hasattr(instance.category, 'value') else instance.category,
            description=node_class.__doc__,
            inputs=[inp.model_dump() for inp in instance.get_inputs()],
            outputs=[out.model_dump() for out in instance.get_outputs()],
            config_schema=self._extract_config_schema(node_class),
        )
        self._schemas[type_name] = schema

    def _extract_config_schema(self, node_class: Type[BaseNode]) -> Dict[str, Any]:
        """노드 클래스에서 설정 스키마 추출"""
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
        """노드 클래스 조회"""
        return self._registry.get(node_type)

    def get_schema(self, node_type: str) -> Optional[NodeTypeSchema]:
        """노드 스키마 조회"""
        return self._schemas.get(node_type)

    def list_types(self, category: Optional[str] = None) -> List[str]:
        """등록된 노드 타입 목록"""
        if category:
            return [
                name for name, schema in self._schemas.items()
                if schema.category == category
            ]
        return list(self._registry.keys())

    def list_schemas(self, category: Optional[str] = None) -> List[NodeTypeSchema]:
        """등록된 노드 스키마 목록 (AI 에이전트용)"""
        if category:
            return [
                schema for schema in self._schemas.values()
                if schema.category == category
            ]
        return list(self._schemas.values())

    def list_categories(self) -> List[Dict[str, Any]]:
        """카테고리 목록 (노드 수 포함)"""
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
        """노드 인스턴스 생성"""
        node_class = self.get(node_type)
        if not node_class:
            raise ValueError(f"Unknown node type: {node_type}")
        return node_class(**kwargs)
