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
    widget_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="json_dynamic_widget schema for Flutter form rendering (PARAMETERS fields)",
    )
    settings_widget_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="json_dynamic_widget schema for Settings tab (SETTINGS fields)",
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
            StartNode, BrokerNode, ThrottleNode,
            RealMarketDataNode, RealAccountNode, RealOrderEventNode,
            MarketDataNode, AccountNode, HistoricalDataNode, SQLiteNode, PostgresNode, HTTPRequestNode, FieldMappingNode,
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, SymbolQueryNode,
            ScheduleNode, TradingHoursFilterNode,
            ConditionNode, LogicNode,
            PositionSizingNode, PortfolioNode,
            StockNewOrderNode, StockModifyOrderNode, StockCancelOrderNode,
            FuturesNewOrderNode, FuturesModifyOrderNode, FuturesCancelOrderNode,
            DisplayNode,
            BacktestEngineNode, BenchmarkCompareNode,
        )

        node_classes = [
            # Infra
            StartNode, BrokerNode, ThrottleNode,
            # Realtime
            RealMarketDataNode, RealAccountNode, RealOrderEventNode,
            # Data
            MarketDataNode, AccountNode, HistoricalDataNode, SQLiteNode, PostgresNode, HTTPRequestNode, FieldMappingNode,
            # Symbol
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, SymbolQueryNode,
            # Trigger
            ScheduleNode, TradingHoursFilterNode,
            # Condition
            ConditionNode, LogicNode,
            # Risk
            PositionSizingNode, PortfolioNode,
            # Order (해외주식)
            StockNewOrderNode, StockModifyOrderNode, StockCancelOrderNode,
            # Order (해외선물)
            FuturesNewOrderNode, FuturesModifyOrderNode, FuturesCancelOrderNode,
            # messaging - 커뮤니티 노드(TelegramNode 등)에서 등록
            # Display
            DisplayNode,
            # Backtest/Analysis
            BacktestEngineNode, BenchmarkCompareNode,
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
                "messaging": "https://cdn-icons-png.flaticon.com/512/3239/3239952.png",
                "display": "https://cdn-icons-png.flaticon.com/512/2920/2920349.png",
                "backtest": "https://cdn-icons-png.flaticon.com/512/2920/2920244.png",
                "job": "https://cdn-icons-png.flaticon.com/512/1087/1087815.png",
            }
            cat_value = instance.category.value if hasattr(instance.category, 'value') else instance.category
            img_url = category_icons.get(cat_value, "https://cdn-icons-png.flaticon.com/512/2099/2099058.png")
        
        widget_schema, settings_widget_schema = self._build_widget_schemas(node_class)
        schema = NodeTypeSchema(
            node_type=type_name,
            category=instance.category.value if hasattr(instance.category, 'value') else instance.category,
            description=description,
            img_url=img_url,
            inputs=[inp.model_dump() for inp in instance.get_inputs()],
            outputs=[out.model_dump() for out in instance.get_outputs()],
            config_schema=self._extract_config_schema(node_class),
            widget_schema=widget_schema,
            settings_widget_schema=settings_widget_schema,
        )
        self._schemas[type_name] = schema

    def _build_widget_schemas(self, node_class: Type[BaseNode]) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        노드의 설정 폼을 PARAMETERS/SETTINGS로 분리하여 json_dynamic_widget JSON으로 변환
        
        Args:
            node_class: 노드 클래스
            
        Returns:
            tuple: (widget_schema, settings_widget_schema)
            - widget_schema: PARAMETERS 카테고리 필드들 (메인 폼)
            - settings_widget_schema: SETTINGS 카테고리 필드들 (설정 탭)
        """
        from programgarden_core.models.field_binding import FieldCategory
        
        if not hasattr(node_class, 'get_field_schema'):
            return None, None
        
        field_schemas = node_class.get_field_schema()
        if not field_schemas:
            return None, None
        
        parameters_children = []
        settings_children = []
        
        # 노드 타입명 추출 (i18n 키 생성용)
        node_type = node_class.__name__
        
        for name, fs in field_schemas.items():
            try:
                # 카테고리에 따라 다른 위젯 생성
                if fs.category == FieldCategory.SETTINGS:
                    # SETTINGS: 토글 없이 직접 위젯 생성
                    widget = fs.to_simple_widget()
                    # SETTINGS 위젯에 i18n labelText 추가
                    widget = self._add_i18n_label_to_settings_widget(widget, node_type, name)
                else:
                    # PARAMETERS: 기존 토글 위젯
                    widget = fs.to_json_dynamic_widget()
                
                widget["fieldKey"] = name  # Pydantic 모델 필드명 (Flutter 코드 생성기 호환)
                widget["field_key_of_pydantic"] = name  # i18n 번역 및 테스트용
                
                # fieldKey를 args 안에도 추가 (json_dynamic_widget 빌더가 args에서 읽음)
                if "args" in widget:
                    widget["args"]["fieldKey"] = name
                
                # visible_when 조건부 표시: json_dynamic_widget의 conditional 위젯으로 감싸기
                if fs.visible_when:
                    widget = self._wrap_conditional(widget, fs.visible_when, name)
                
                # 카테고리에 따라 분리
                if fs.category == FieldCategory.SETTINGS:
                    settings_children.append(widget)
                else:
                    # PARAMETERS 또는 None (기본값)
                    parameters_children.append(widget)
                    
            except Exception as e:
                # 변환 실패 시 기본 텍스트 필드로 폴백 (PARAMETERS에 추가)
                parameters_children.append({
                    "type": "text_form_field",
                    "fieldKey": name,
                    "args": {
                        "decoration": {"labelText": name, "helperText": f"(conversion error: {str(e)})"}
                    }
                })
        
        # 각 스키마 생성 (children이 없으면 None)
        widget_schema = {
            "type": "column",
            "args": {"children": parameters_children}
        } if parameters_children else None
        
        settings_widget_schema = {
            "type": "column",
            "args": {"children": settings_children}
        } if settings_children else None
        
        return widget_schema, settings_widget_schema
    
    def _add_i18n_label_to_settings_widget(
        self, widget: Dict[str, Any], node_type: str, field_name: str
    ) -> Dict[str, Any]:
        """
        SETTINGS 위젯에 i18n labelText 추가
        
        checkbox는 decoration이 없으므로 labelText를 args에 직접 추가하고,
        다른 위젯은 decoration.labelText에 i18n 키를 설정합니다.
        
        Args:
            widget: 위젯 딕셔너리
            node_type: 노드 타입명 (예: "RealAccountNode")
            field_name: 필드명 (예: "stay_connected")
            
        Returns:
            i18n labelText가 추가된 위젯
        """
        i18n_label_key = f"i18n:fieldNames.{node_type}.{field_name}"
        
        if "args" not in widget:
            widget["args"] = {}
        
        if widget.get("type") == "checkbox":
            # checkbox는 labelText를 args에 직접 추가
            widget["args"]["labelText"] = i18n_label_key
        else:
            # 다른 위젯은 decoration.labelText에 추가
            if "decoration" not in widget["args"]:
                widget["args"]["decoration"] = {}
            widget["args"]["decoration"]["labelText"] = i18n_label_key
        
        return widget
    
    def _wrap_conditional(self, widget: Dict[str, Any], visible_when: Dict[str, Any], field_key: str) -> Dict[str, Any]:
        """
        visible_when 조건을 json_dynamic_widget의 conditional 위젯으로 감싸기
        
        json_dynamic_widget 표준 conditional 형식:
        {
            "type": "conditional",
            "listen": ["field_name"],  // 이 변수가 변경되면 위젯 리빌드
            "args": {
                "conditional": {"values": {"field_name": "expected_value"}},
                "onTrue": { /* 조건 만족 시 표시할 위젯 */ }
            }
        }
        
        Args:
            widget: 원본 위젯
            visible_when: 조건 딕셔너리 (예: {"product_type": "overseas_stock"})
            field_key: 필드 키 (Pydantic 모델 필드명)
            
        Returns:
            conditional 위젯으로 감싼 구조
        """
        # listen 배열: visible_when의 모든 키를 감시
        listen_fields = list(visible_when.keys())
        
        # conditional values 구성
        # 배열 값은 첫 번째 값만 사용 (json_dynamic_widget 제한)
        conditional_values = {}
        for field, value in visible_when.items():
            if isinstance(value, list):
                # 배열인 경우 첫 번째 값 사용
                conditional_values[field] = value[0] if value else None
            else:
                conditional_values[field] = value
        
        return {
            "type": "conditional",
            "listen": listen_fields,
            "fieldKey": field_key,  # Flutter 코드 생성기 호환
            "args": {
                "conditional": {"values": conditional_values},
                "onTrue": widget
            }
        }

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
                # === display_name (UI 라벨) ===
                if hasattr(fs, 'display_name') and fs.display_name:
                    field_schema["display_name"] = fs.display_name
                if fs.enum_values:
                    field_schema["enum_values"] = fs.enum_values
                if fs.enum_labels:
                    field_schema["enum_labels"] = fs.enum_labels
                # === expression_mode ===
                if hasattr(fs, 'expression_mode') and fs.expression_mode:
                    field_schema["expression_mode"] = fs.expression_mode.value if hasattr(fs.expression_mode, 'value') else str(fs.expression_mode)
                # category 추가 (PARAMETERS/SETTINGS)
                if fs.category is not None:
                    field_schema["category"] = fs.category.value if hasattr(fs.category, 'value') else str(fs.category)
                # ui_component 추가 (symbol_editor 등)
                if hasattr(fs, 'ui_component') and fs.ui_component:
                    field_schema["ui_component"] = fs.ui_component.value if hasattr(fs.ui_component, 'value') else str(fs.ui_component)
                # ui_options 추가 (ui_component 세부 설정)
                if hasattr(fs, 'ui_options') and fs.ui_options:
                    field_schema["ui_options"] = fs.ui_options
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
                # === 필드 그룹 (UI에서 그룹핑용) ===
                if hasattr(fs, 'group') and fs.group:
                    field_schema["group"] = fs.group
                # === 배열 항목 스키마 (condition_list 등) ===
                if hasattr(fs, 'object_schema') and fs.object_schema:
                    field_schema["object_schema"] = fs.object_schema
                # === 부모-자식 관계 (계층적 UI 표시용) ===
                if hasattr(fs, 'child_of') and fs.child_of:
                    field_schema["child_of"] = fs.child_of
                # === placeholder 추가 ===
                if hasattr(fs, 'placeholder') and fs.placeholder:
                    field_schema["placeholder"] = fs.placeholder
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
