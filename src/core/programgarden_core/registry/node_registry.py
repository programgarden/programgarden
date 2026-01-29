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
    """Node type schema (for AI agents)"""

    node_type: str = Field(..., description="Node type name")
    category: str = Field(..., description="Node category")
    description: Optional[str] = Field(default=None, description="Node description")
    img_url: Optional[str] = Field(default=None, description="Node icon image URL")
    product_scope: str = Field(default="all", description="Product scope: overseas_stock | overseas_futures | all")
    broker_provider: str = Field(default="all", description="Broker provider: ls-sec.co.kr | all")
    inputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Input port definitions",
    )
    outputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Output port definitions",
    )
    widget_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="json_dynamic_widget schema for Flutter form rendering (PARAMETERS fields)",
    )
    settings_widget_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="json_dynamic_widget schema for Settings tab (SETTINGS fields)",
    )
    display_data_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Schema describing the data structure produced by Display nodes at runtime. "
                    "Properties with 'resolved_by' indicate dynamic field names determined by node settings.",
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
            StartNode, ThrottleNode, SplitNode, AggregateNode,
            OverseasStockBrokerNode, OverseasFuturesBrokerNode,
            # Market - Stock (해외주식)
            OverseasStockMarketDataNode, OverseasStockHistoricalDataNode,
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
            # Data (상품 무관)
            SQLiteNode, HTTPRequestNode, FieldMappingNode,
            # Symbol (상품 무관)
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode,
            ScheduleNode, TradingHoursFilterNode,
            ConditionNode, LogicNode,
            PositionSizingNode, PortfolioNode,
            OverseasStockNewOrderNode, OverseasStockModifyOrderNode, OverseasStockCancelOrderNode,
            OverseasFuturesNewOrderNode, OverseasFuturesModifyOrderNode, OverseasFuturesCancelOrderNode,
            TableDisplayNode, LineChartNode, MultiLineChartNode,
            CandlestickChartNode, BarChartNode, SummaryDisplayNode,
            BacktestEngineNode, BenchmarkCompareNode,
        )

        node_classes = [
            # Infra
            StartNode, ThrottleNode, SplitNode, AggregateNode,
            # Broker (상품별 분리)
            OverseasStockBrokerNode, OverseasFuturesBrokerNode,
            # Market - Stock (해외주식)
            OverseasStockMarketDataNode, OverseasStockHistoricalDataNode,
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
            # Data (상품 무관)
            SQLiteNode, HTTPRequestNode, FieldMappingNode,
            # Symbol (상품 무관)
            WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode,
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
        
        # product_scope, broker_provider 추출
        product_scope = getattr(node_class, '_product_scope', ProductScope.ALL)
        broker_provider = getattr(node_class, '_broker_provider', BrokerProvider.ALL)
        product_scope_value = product_scope.value if hasattr(product_scope, 'value') else str(product_scope)
        broker_provider_value = broker_provider.value if hasattr(broker_provider, 'value') else str(broker_provider)

        widget_schema, settings_widget_schema = self._build_widget_schemas(node_class)

        # Display 노드의 런타임 데이터 스키마
        display_data_schema = getattr(node_class, '_display_data_schema', None)

        schema = NodeTypeSchema(
            node_type=type_name,
            category=instance.category.value if hasattr(instance.category, 'value') else instance.category,
            description=description,
            img_url=img_url,
            product_scope=product_scope_value,
            broker_provider=broker_provider_value,
            inputs=[inp.model_dump(exclude_none=True) for inp in instance.get_inputs()],
            outputs=[out.model_dump(exclude_none=True) for out in instance.get_outputs()],
            widget_schema=widget_schema,
            settings_widget_schema=settings_widget_schema,
            display_data_schema=display_data_schema,
        )
        self._schemas[type_name] = schema

    def _build_widget_schemas(self, node_class: Type[BaseNode]) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        노드의 설정 폼을 PARAMETERS/SETTINGS로 분리하여 json_dynamic_widget JSON으로 변환

        group 속성이 있는 필드는 그룹별로 card 위젯으로 래핑하여 중첩 배치합니다.

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

        # 그룹 없는 필드 / 그룹별 필드 분리 수집
        ungrouped_params = []
        ungrouped_settings = []
        grouped_params: Dict[str, list] = {}   # group_name -> [widget, ...]
        grouped_settings: Dict[str, list] = {}
        group_order_params: list = []  # 그룹 등장 순서 유지
        group_order_settings: list = []

        # 노드 타입명 추출 (i18n 키 생성용)
        node_type = node_class.__name__

        for name, fs in field_schemas.items():
            try:
                # 카테고리에 따라 다른 위젯 생성
                if fs.category == FieldCategory.SETTINGS:
                    widget = fs.to_simple_widget()
                    widget = self._add_i18n_label_to_settings_widget(widget, node_type, name)
                else:
                    widget = fs.to_json_dynamic_widget()

                widget["fieldKey"] = name
                widget["field_key_of_pydantic"] = name

                if "args" in widget:
                    widget["args"]["fieldKey"] = name

                if fs.visible_when:
                    widget = self._wrap_conditional(widget, fs.visible_when, name)

                # 카테고리 + 그룹에 따라 분리
                if fs.category == FieldCategory.SETTINGS:
                    if fs.group:
                        if fs.group not in grouped_settings:
                            grouped_settings[fs.group] = []
                            group_order_settings.append(fs.group)
                        grouped_settings[fs.group].append(widget)
                    else:
                        ungrouped_settings.append(widget)
                else:
                    if fs.group:
                        if fs.group not in grouped_params:
                            grouped_params[fs.group] = []
                            group_order_params.append(fs.group)
                        grouped_params[fs.group].append(widget)
                    else:
                        ungrouped_params.append(widget)

            except Exception as e:
                ungrouped_params.append({
                    "type": "text_form_field",
                    "fieldKey": name,
                    "args": {
                        "decoration": {"labelText": name, "helperText": f"(conversion error: {str(e)})"}
                    }
                })

        # 최종 children: ungrouped 먼저, 그다음 group card (등장 순서 유지)
        parameters_children = list(ungrouped_params)
        for group_name in group_order_params:
            parameters_children.append(
                self._build_group_card(node_type, group_name, grouped_params[group_name])
            )

        settings_children = list(ungrouped_settings)
        for group_name in group_order_settings:
            settings_children.append(
                self._build_group_card(node_type, group_name, grouped_settings[group_name])
            )

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

    def _build_group_card(
        self, node_type: str, group_name: str, children: list
    ) -> Dict[str, Any]:
        """
        그룹 필드를 card > padding > column 구조로 래핑

        Args:
            node_type: 노드 타입명 (i18n 키 생성용)
            group_name: 그룹 이름
            children: 그룹에 속한 위젯 리스트
        """
        title_widget = {
            "type": "text",
            "args": {
                "text": f"i18n:groups.{node_type}.{group_name}",
                "style": {"fontWeight": "w600", "fontSize": 13}
            }
        }

        return {
            "type": "card",
            "args": {
                "elevation": 0,
                "margin": {"top": 12, "bottom": 4},
                "child": {
                    "type": "padding",
                    "args": {
                        "padding": {"left": 12, "right": 12, "top": 8, "bottom": 8},
                        "child": {
                            "type": "column",
                            "args": {
                                "mainAxisSize": "min",
                                "children": [title_widget] + children
                            }
                        }
                    }
                }
            }
        }
    
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
