"""
ProgramGarden Core - Field Binding 모델

노드 필드의 값 바인딩 시스템:
- FieldSchema: 필드 스키마 정의 (UI 렌더링용)
- FieldValue: 필드 값 (고정값, 바인딩, 표현식)
"""

from enum import Enum
from typing import Optional, Any, List, Dict, Union
from pydantic import BaseModel, ConfigDict, Field


class FieldType(str, Enum):
    """필드 데이터 타입"""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ENUM = "enum"
    ARRAY = "array"
    OBJECT = "object"
    KEY_VALUE_PAIRS = "key_value_pairs"  # 동적 키-값 쌍 (headers 등)
    CREDENTIAL = "credential"  # Credential 참조 (credentials 섹션에서 선택)


class FieldCategory(str, Enum):
    """필드 분류 (UI 렌더링용)"""

    PARAMETERS = "parameters"  # 핵심 설정 (method, url, headers, body 등)
    SETTINGS = "settings"      # 부가 설정 (timeout, retry, ssl 등)
    ADVANCED = "advanced"      # 고급 설정 (기본값으로 충분, 보통 숨김)


class ExpressionMode(str, Enum):
    """
    필드의 Expression 허용 모드
    
    클라이언트 UI 렌더링 가이드:
    - FIXED_ONLY: ui_component에 따른 입력 컴포넌트만 표시 (토글 없음)
    - EXPRESSION_ONLY: {{ }} 바인딩 에디터만 표시 (토글 없음)
    - BOTH: [Fixed | Expression] 토글 버튼 + 선택에 따른 입력
    """
    
    FIXED_ONLY = "fixed_only"          # 고정값만 가능 (토글 없음)
    EXPRESSION_ONLY = "expression_only"  # Expression만 가능 (바인딩 필수)
    BOTH = "both"                       # Fixed + Expression 둘 다 (토글 표시)


class UIComponent(str, Enum):
    """
    UI 컴포넌트 타입 (json_dynamic_widget 타입명과 동일)
    
    사용 가이드:
    - 기본 위젯: ui_component 생략 → FieldType에서 자동 추론
    - 세부 옵션: ui_options로 지정 (keyboardType, maxLines 등)
    - 커스텀 위젯: ui_component 명시 필수 (CUSTOM_* 접두사)
    
    FieldType → json_dynamic_widget 자동 매핑:
    - STRING → text_form_field
    - NUMBER/INTEGER → text_form_field (keyboardType: number 자동 적용)
    - BOOLEAN → checkbox
    - ENUM → dropdown_button_form_field
    - CREDENTIAL → custom_credential_select
    - KEY_VALUE_PAIRS → custom_key_value_editor
    """
    
    # === json_dynamic_widget 네이티브 타입 ===
    TEXT_FORM_FIELD = "text_form_field"
    CHECKBOX = "checkbox"
    DROPDOWN_BUTTON_FORM_FIELD = "dropdown_button_form_field"
    SLIDER = "slider"
    
    # === ProgramGarden 커스텀 위젯 ===
    CUSTOM_CREDENTIAL_SELECT = "custom_credential_select"
    CUSTOM_SYMBOL_EDITOR = "custom_symbol_editor"
    CUSTOM_EXPRESSION_TOGGLE = "custom_expression_toggle"
    CUSTOM_KEY_VALUE_EDITOR = "custom_key_value_editor"
    CUSTOM_OBJECT_ARRAY_TABLE = "custom_object_array_table"
    CUSTOM_CODE_EDITOR = "custom_code_editor"
    CUSTOM_CREATABLE_SELECT = "custom_creatable_select"
    CUSTOM_DATE_PICKER = "custom_date_picker"
    CUSTOM_TIME_PICKER = "custom_time_picker"
    CUSTOM_DATETIME_PICKER = "custom_datetime_picker"
    CUSTOM_PLUGIN_SELECT = "custom_plugin_select"
    CUSTOM_FIELD_MAPPING_EDITOR = "custom_field_mapping_editor"
    CUSTOM_ORDER_LIST_EDITOR = "custom_order_list_editor"
    
    @classmethod
    def get_default_widget_type(cls, field_type: "FieldType") -> str:
        """FieldType에 대한 기본 json_dynamic_widget 타입 반환"""
        mapping = {
            FieldType.STRING: "text_form_field",
            FieldType.NUMBER: "text_form_field",
            FieldType.INTEGER: "text_form_field",
            FieldType.BOOLEAN: "checkbox",
            FieldType.ENUM: "dropdown_button_form_field",
            FieldType.ARRAY: "text_form_field",
            FieldType.OBJECT: "text_form_field",
            FieldType.KEY_VALUE_PAIRS: "custom_key_value_editor",
            FieldType.CREDENTIAL: "custom_credential_select",
        }
        return mapping.get(field_type, "text_form_field")
    
    @classmethod
    def get_default_for_field_type(cls, field_type: "FieldType") -> "UIComponent":
        """FieldType에 대한 기본 UIComponent 반환"""
        mapping = {
            FieldType.STRING: cls.TEXT_FORM_FIELD,
            FieldType.NUMBER: cls.TEXT_FORM_FIELD,
            FieldType.INTEGER: cls.TEXT_FORM_FIELD,
            FieldType.BOOLEAN: cls.CHECKBOX,
            FieldType.ENUM: cls.DROPDOWN_BUTTON_FORM_FIELD,
            FieldType.ARRAY: cls.TEXT_FORM_FIELD,
            FieldType.OBJECT: cls.TEXT_FORM_FIELD,
            FieldType.KEY_VALUE_PAIRS: cls.CUSTOM_KEY_VALUE_EDITOR,
            FieldType.CREDENTIAL: cls.CUSTOM_CREDENTIAL_SELECT,
        }
        return mapping.get(field_type, cls.TEXT_FORM_FIELD)
    
    @classmethod
    def to_widget_type(cls, ui_component: Optional["UIComponent"], field_type: "FieldType") -> str:
        """UIComponent를 json_dynamic_widget 타입으로 변환"""
        if ui_component is None:
            return cls.get_default_widget_type(field_type)

        # UIComponent.value가 곧 json_dynamic_widget 타입명
        return ui_component.value


class FieldSchema(BaseModel):
    """
    노드 필드 스키마 (UI 렌더링 및 검증용)

    백엔드에서 정의하고, 클라이언트(React/Flutter 등)가 이를 기반으로
    동적 폼을 생성합니다.

    Example:
        # 고정값만 가능 (설정 필드)
        FieldSchema(
            name="method",
            type=FieldType.ENUM,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        
        # 바인딩 필수 (연결 필드)
        FieldSchema(
            name="connection",
            type=FieldType.OBJECT,
            expression_mode=ExpressionMode.EXPRESSION_ONLY,
        )
        
        # Fixed/Expression 둘 다 가능 (기본값)
        FieldSchema(
            name="symbols",
            type=FieldType.ARRAY,
            expression_mode=ExpressionMode.BOTH,
        )
    """

    name: str = Field(..., description="필드 이름")
    type: FieldType = Field(..., description="필드 데이터 타입")
    display_name: Optional[str] = Field(
        default=None, 
        description="필드 라벨 (UI 표시용). i18n 키 또는 직접 값. 없으면 필드명을 Title Case로 변환"
    )
    description: Optional[str] = Field(default=None, description="필드 설명")
    category: FieldCategory = Field(
        default=FieldCategory.PARAMETERS,
        description="필드 분류 (parameters: 핵심, settings: 부가)"
    )

    # 필수/기본값
    required: bool = Field(default=False, description="필수 여부")
    default: Optional[Any] = Field(default=None, description="기본값")

    # 타입별 추가 옵션
    enum_values: Optional[List[str]] = Field(
        default=None, description="enum 타입의 선택 가능 값 목록"
    )
    enum_labels: Optional[Dict[str, str]] = Field(
        default=None, description="enum 값에 대한 라벨 (예: {'overseas_stock': '해외주식'})"
    )
    min_value: Optional[float] = Field(
        default=None, description="number/integer의 최솟값"
    )
    max_value: Optional[float] = Field(
        default=None, description="number/integer의 최댓값"
    )
    array_item_type: Optional[FieldType] = Field(
        default=None, description="array 타입의 요소 타입"
    )

    # 바인딩 옵션
    expression_mode: ExpressionMode = Field(
        default=ExpressionMode.BOTH,
        description="Fixed/Expression 허용 모드. fixed_only: 고정값만, expression_only: 바인딩 필수, both: 토글 표시"
    )
    
    # === 바인딩 가이드 ===
    example: Optional[Any] = Field(
        default=None,
        description="예시 값 (기대하는 데이터 형태)",
    )
    example_binding: Optional[str] = Field(
        default=None,
        description="바인딩 표현식 예시 ({{ nodes.xxx.yyy }})",
    )
    bindable_sources: Optional[List[str]] = Field(
        default=None,
        description="바인딩 가능한 소스 노드와 포트 목록",
    )
    expected_type: Optional[str] = Field(
        default=None,
        description="기대하는 데이터 타입 (검증용, 예: dict[str, float], list[str])",
    )

    # UI 힌트
    ui_component: Optional[UIComponent] = Field(
        default=None,
        description="UI 컴포넌트 타입. None이면 FieldType에 따른 기본 컴포넌트 사용. 모든 컴포넌트는 바인딩 지원.",
    )
    ui_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="UI 컴포넌트 세부 옵션 (예: code_editor의 language, creatable_select의 file_extension 등)",
    )
    placeholder: Optional[str] = Field(
        default=None, description="입력 필드 placeholder"
    )
    group: Optional[str] = Field(
        default=None, description="필드 그룹 (UI에서 그룹핑용)"
    )

    # 조건부 필드 상태 (계층적 노드 연결용)
    disabled_when: Optional[str] = Field(
        default=None,
        description="조건부 비활성화 표현식 (예: 'has_incoming_portfolio_edge')",
    )
    read_only_when: Optional[str] = Field(
        default=None,
        description="조건부 읽기전용 표현식 (예: 'is_child_node')",
    )
    override_source: Optional[str] = Field(
        default=None,
        description="값이 다른 곳에서 계산되는 경우 출처 표시 (예: 'parent.allocation * parent.total_capital')",
    )
    ui_hint: Optional[str] = Field(
        default=None,
        description="UI 표시 힌트 (inherited, calculated, locked, warning 등)",
    )

    # 조건부 표시 (특정 필드 값에 따라 필드 표시/숨김)
    visible_when: Optional[Dict[str, Any]] = Field(
        default=None,
        description="조건부 표시 조건 (예: {'product': 'overseas_stock'}는 product 필드가 'overseas_stock'일 때만 표시)",
    )
    
    # chart_type별 필드 조건부 표시 (DisplayNode용)
    depends_on: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="다른 필드 값에 따른 조건부 표시 (예: {'chart_type': ['line', 'bar']})",
    )
    
    # 배열/객체 타입의 항목 스키마 (condition_list, key_value_editor 등)
    object_schema: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="테이블 컬럼 정의 (예: [{name: 'key', type: 'STRING'}, {name: 'value', type: 'STRING'}])",
    )
    
    # 부모-자식 필드 관계 (계층적 UI 렌더링용)
    child_of: Optional[str] = Field(
        default=None,
        description="부모 필드명. 지정 시 부모 필드 아래 들여쓰기되어 표시됨 (예: 'data')",
    )
    
    # 고급 옵션 (기본 숨김)
    collapsed: bool = Field(
        default=False,
        description="기본적으로 접혀있는 필드 (고급 옵션)",
    )
    help_text: Optional[str] = Field(
        default=None,
        description="추가 도움말 텍스트",
    )
    
    # Credential 타입 필터 (CREDENTIAL_SELECT 전용)
    credential_types: Optional[List[str]] = Field(
        default=None,
        description="CREDENTIAL_SELECT에서 표시할 credential 타입 목록 (예: ['broker_ls', 'telegram'])",
    )

    model_config = ConfigDict(use_enum_values=True)
    
    def to_simple_widget(self) -> Dict[str, Any]:
        """
        SETTINGS 카테고리용 단순 위젯 생성 (토글 없음)
        
        expression_mode를 무시하고 ui_component에 따른 위젯만 생성합니다.
        settings 필드는 고정값만 사용하므로 Fixed/Expression 토글이 불필요합니다.
        
        Returns:
            dict: json_dynamic_widget 호환 JSON 구조 (토글 없음)
        """
        ui_comp = self.ui_component
        if ui_comp is None:
            ui_comp = UIComponent.get_default_for_field_type(self.type)
        
        label = self.display_name or self.name.replace("_", " ").title()
        decoration: Dict[str, Any] = {"labelText": label}
        if self.placeholder:
            decoration["hintText"] = self.placeholder
        
        widget = self._map_ui_component_to_widget(ui_comp, decoration)
        # description이 있으면 args.helperText로 전달 (to_json_dynamic_widget의 FIXED_ONLY와 동일)
        if self.description:
            widget["args"]["helperText"] = self.description
        return widget

    def to_json_dynamic_widget(self) -> Dict[str, Any]:
        """
        FieldSchema를 json_dynamic_widget JSON 형태로 변환
        
        Flutter 클라이언트에서 json_dynamic_widget 패키지로 동적 폼을 렌더링하기 위한
        JSON 구조를 생성합니다.
        
        Returns:
            dict: json_dynamic_widget 호환 JSON 구조
            
        Example:
            >>> fs = FieldSchema(name="provider", type=FieldType.ENUM, ...)
            >>> widget = fs.to_json_dynamic_widget()
            >>> # {"type": "dropdown_button_form_field", "args": {...}}
        """
        # UI 컴포넌트 결정 (명시적 지정 > 타입 기반 기본값)
        ui_comp = self.ui_component
        if ui_comp is None:
            ui_comp = UIComponent.get_default_for_field_type(self.type)
        
        # 표시 이름 결정 (display_name > name의 Title Case)
        label = self.display_name or self.name.replace("_", " ").title()
        
        # 기본 decoration 구성 (helperText는 args에서 관리)
        decoration: Dict[str, Any] = {"labelText": label}
        if self.placeholder:
            decoration["hintText"] = self.placeholder

        # FIXED_ONLY: 토글 없이 직접 위젯만 렌더링 (expression 전환이 불가하므로 토글 불필요)
        if self.expression_mode == ExpressionMode.FIXED_ONLY:
            widget = self._map_ui_component_to_widget(ui_comp, decoration)
            # description이 있으면 args.helperText로 전달 (Flutter에서 자유롭게 렌더링)
            if self.description:
                widget["args"]["helperText"] = self.description
            return widget

        # 자체 토글을 포함하는 커스텀 위젯들은 직접 렌더링 (expression_toggle 래핑 생략)
        # 이 위젯들은 내부에서 자체적으로 Fixed/Expression 토글을 처리함
        self_toggle_widgets = {
            UIComponent.CUSTOM_SYMBOL_EDITOR,
        }
        if ui_comp in self_toggle_widgets:
            return self._map_ui_component_to_widget(ui_comp, decoration)

        # expression_mode에 따른 처리
        # EXPRESSION_ONLY: 토글 없이 expression 입력만 표시
        if self.expression_mode == ExpressionMode.EXPRESSION_ONLY:
            return self._build_expression_only_widget(decoration)

        # BOTH 모드: Fixed/Expression 토글 위젯 (전환 가능)
        return self._build_toggle_widget(ui_comp, decoration)
    
    def _map_ui_component_to_widget(
        self, 
        ui_comp: "UIComponent", 
        decoration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """UIComponent를 json_dynamic_widget 타입으로 매핑
        
        ui_options가 있으면 해당 옵션을 적용합니다.
        FieldType에 따른 기본 옵션도 자동 적용됩니다.
        """
        ui_opts = self.ui_options or {}

        # === TEXT_FORM_FIELD ===
        if ui_comp == UIComponent.TEXT_FORM_FIELD:
            args: Dict[str, Any] = {"decoration": decoration}
            if self.default is not None:
                args["initialValue"] = str(self.default)
            # NUMBER/INTEGER 타입은 keyboardType: number 자동 적용
            if self.type in (FieldType.NUMBER, FieldType.INTEGER):
                args["keyboardType"] = ui_opts.get("keyboardType", "number")
            if ui_opts.get("maxLines"):
                args["maxLines"] = ui_opts["maxLines"]
            if ui_opts.get("keyboardType") and self.type not in (FieldType.NUMBER, FieldType.INTEGER):
                args["keyboardType"] = ui_opts["keyboardType"]
            return {"type": "text_form_field", "args": args}

        # === CHECKBOX ===
        if ui_comp == UIComponent.CHECKBOX:
            label = self.display_name or self.name.replace("_", " ").title()
            args: Dict[str, Any] = {
                "value": self.default if isinstance(self.default, bool) else False,
                "labelText": label,
            }
            return {"type": "checkbox", "args": args}

        # === DROPDOWN ===
        if ui_comp == UIComponent.DROPDOWN_BUTTON_FORM_FIELD:
            items = self.enum_values or []
            args: Dict[str, Any] = {
                "decoration": decoration,
                "items": items,
            }
            if self.default is not None:
                args["value"] = self.default
            if self.enum_labels:
                args["itemLabels"] = self.enum_labels
            if ui_opts.get("multiple"):
                args["multiple"] = True
            return {"type": "dropdown_button_form_field", "args": args}

        # === CREDENTIAL_SELECT ===
        if ui_comp == UIComponent.CUSTOM_CREDENTIAL_SELECT:
            args: Dict[str, Any] = {
                "decoration": decoration,
                "items": [],
            }
            if self.credential_types:
                from .credential import BUILTIN_CREDENTIAL_SCHEMAS
                credential_type_infos = []
                for type_id in self.credential_types:
                    schema = BUILTIN_CREDENTIAL_SCHEMAS.get(type_id)
                    credential_type_infos.append({
                        "type_id": type_id,
                        "name": schema.name if schema else type_id,
                    })
                args["credentialTypes"] = credential_type_infos
            return {"type": "custom_credential_select", "args": args}

        # === PLUGIN_SELECT ===
        if ui_comp == UIComponent.CUSTOM_PLUGIN_SELECT:
            return {
                "type": "custom_plugin_select",
                "args": {"decoration": decoration},
            }

        # === SYMBOL_EDITOR ===
        if ui_comp == UIComponent.CUSTOM_SYMBOL_EDITOR:
            args: Dict[str, Any] = {
                "decoration": decoration,
                "expressionMode": self.expression_mode.value if hasattr(self.expression_mode, 'value') else str(self.expression_mode),
            }
            if self.object_schema:
                args["objectSchema"] = self.object_schema
            if self.ui_options:
                args["uiOptions"] = self.ui_options
            if self.example_binding:
                args["expressionHint"] = self.example_binding
            return {"type": "custom_symbol_editor", "args": args}

        # === KEY_VALUE_EDITOR ===
        if ui_comp == UIComponent.CUSTOM_KEY_VALUE_EDITOR:
            return {
                "type": "custom_key_value_editor",
                "args": {
                    "decoration": decoration,
                    "objectSchema": self.object_schema,
                },
            }

        # === ORDER_LIST_EDITOR ===
        if ui_comp == UIComponent.CUSTOM_ORDER_LIST_EDITOR:
            args_dict: Dict[str, Any] = {
                "decoration": decoration,
                "objectSchema": self.object_schema,
            }
            if self.example_binding:
                args_dict["exampleBinding"] = self.example_binding
            if self.bindable_sources:
                args_dict["bindableSources"] = self.bindable_sources
            return {
                "type": "custom_order_list_editor",
                "args": args_dict,
            }

        # === OBJECT_ARRAY_TABLE ===
        if ui_comp == UIComponent.CUSTOM_OBJECT_ARRAY_TABLE:
            return {
                "type": "custom_object_array_table",
                "args": {
                    "decoration": decoration,
                    "objectSchema": self.object_schema,
                },
            }

        # === CODE_EDITOR ===
        if ui_comp == UIComponent.CUSTOM_CODE_EDITOR:
            return {
                "type": "custom_code_editor",
                "args": {
                    "decoration": decoration,
                    "language": ui_opts.get("language", "sql"),
                },
            }

        # === CREATABLE_SELECT ===
        if ui_comp == UIComponent.CUSTOM_CREATABLE_SELECT:
            return {
                "type": "custom_creatable_select",
                "args": {
                    "decoration": decoration,
                    "source": ui_opts.get("source"),
                    "fileExtension": ui_opts.get("file_extension"),
                    "createLabel": ui_opts.get("create_label"),
                    "deletable": ui_opts.get("deletable", False),
                },
            }

        # === DATE_PICKER ===
        if ui_comp == UIComponent.CUSTOM_DATE_PICKER:
            args: Dict[str, Any] = {
                "fieldKey": self.name,
                "decoration": decoration,
            }
            if self.default:
                args["initialValue"] = self.default
            if ui_opts.get("firstDate"):
                args["firstDate"] = ui_opts["firstDate"]
            if ui_opts.get("lastDate"):
                args["lastDate"] = ui_opts["lastDate"]
            if ui_opts.get("dateFormat"):
                args["dateFormat"] = ui_opts["dateFormat"]
            return {
                "type": "custom_date_picker",
                "args": args,
            }

        # === TIME_PICKER ===
        if ui_comp == UIComponent.CUSTOM_TIME_PICKER:
            return {
                "type": "custom_time_picker",
                "args": {"decoration": decoration},
            }

        # === DATETIME_PICKER ===
        if ui_comp == UIComponent.CUSTOM_DATETIME_PICKER:
            return {
                "type": "custom_datetime_picker",
                "args": {"decoration": decoration},
            }

        # === FIELD_MAPPING_EDITOR ===
        if ui_comp == UIComponent.CUSTOM_FIELD_MAPPING_EDITOR:
            return {
                "type": "custom_field_mapping_editor",
                "args": {
                    "decoration": decoration,
                    "objectSchema": self.object_schema,
                },
            }

        # === SLIDER ===
        if ui_comp == UIComponent.SLIDER:
            args: Dict[str, Any] = {
                "min": float(self.min_value or 0),
                "max": float(self.max_value or 100),
                "value": float(self.default or 0),
            }
            if ui_opts.get("range"):
                args["range"] = True
            return {"type": "slider", "args": args}

        # === 기본값: TEXT_FORM_FIELD ===
        args: Dict[str, Any] = {"decoration": decoration}
        if self.default is not None:
            args["initialValue"] = str(self.default)
        if self.type in (FieldType.NUMBER, FieldType.INTEGER):
            args["keyboardType"] = ui_opts.get("keyboardType", "number")
        if ui_opts.get("maxLines"):
            args["maxLines"] = ui_opts["maxLines"]
        if ui_opts.get("keyboardType") and self.type not in (FieldType.NUMBER, FieldType.INTEGER):
            args["keyboardType"] = ui_opts["keyboardType"]
        return {"type": "text_form_field", "args": args}
    
    def _build_expression_only_widget(
        self,
        decoration: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        EXPRESSION_ONLY 전용 위젯 생성 (토글 없는 단순 expression 입력)

        {{ nodes.xxx.yyy }} 형태의 바인딩 표현식만 입력받는 텍스트 필드입니다.
        custom_expression_toggle 없이 직접 text_form_field를 반환합니다.
        """
        expr_decoration = decoration.copy()
        if self.example_binding:
            expr_decoration["hintText"] = self.example_binding

        args: Dict[str, Any] = {
            "fieldKey": self.name,
            "decoration": expr_decoration,
        }

        # helperText: help_text > description 순으로 적용
        if self.help_text:
            args["helperText"] = self.help_text
        elif self.description:
            args["helperText"] = self.description

        return {"type": "text_form_field", "args": args}

    def _build_toggle_widget(
        self,
        ui_comp: "UIComponent",
        decoration: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        custom_expression_toggle 위젯 생성 (BOTH 모드 전용)

        Fixed/Expression 토글 버튼과 함께 선택에 따른 입력 위젯을 렌더링합니다.

        Args:
            ui_comp: UI 컴포넌트 타입
            decoration: 라벨, 설명 등 장식 정보

        Returns:
            dict: custom_expression_toggle 위젯 JSON
        """
        # Fixed 위젯 (ui_component에 따른 입력)
        fixed_widget = self._build_fixed_widget(ui_comp, decoration.copy())

        # Expression 위젯 (바인딩 입력)
        expression_widget = self._build_expression_field(decoration.copy())

        args: Dict[str, Any] = {
            "fieldKey": self.name,
            "label": decoration.get("labelText", self.name),
            "defaultMode": "fixed",
            "expressionHint": self.example_binding,
            "fixedWidget": fixed_widget,
            "expressionWidget": expression_widget,
        }

        # helperText 분리: fixed/expression 모드별로 다른 설명 표시
        if self.description:
            args["fixedHelperText"] = self.description
        if self.help_text:
            args["expressionHelperText"] = self.help_text
        elif self.example_binding:
            args["expressionHelperText"] = f"예: {self.example_binding}"

        return {
            "type": "custom_expression_toggle",
            "args": args
        }
    
    def _build_fixed_widget(
        self,
        ui_comp: "UIComponent",
        decoration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fixed 모드용 위젯 생성 (BOTH 모드의 토글에서 사용)
        
        기존 _map_ui_component_to_widget과 동일하지만 토글 내부용으로 사용됩니다.
        """
        return self._map_ui_component_to_widget(ui_comp, decoration)
    
    def _build_expression_field(
        self,
        decoration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Expression 모드용 바인딩 입력 필드 생성
        
        {{ nodes.xxx.yyy }} 형태의 바인딩 표현식을 입력받는 텍스트 필드입니다.
        """
        if self.example_binding:
            decoration["hintText"] = self.example_binding
        
        return {
            "type": "text_form_field",
            "args": {
                "fieldKey": self.name,
                "decoration": decoration,
            }
        }


class FieldValueType(str, Enum):
    """필드 값 유형"""

    FIXED = "fixed"  # 고정값
    BINDING = "binding"  # 다른 노드 출력과 바인딩
    EXPRESSION = "expression"  # Jinja2 스타일 표현식


def parse_field_value(value: Any) -> tuple[FieldValueType, Any, Optional[str]]:
    """
    필드 값을 파싱하여 타입과 실제 값을 반환

    Args:
        value: 필드 값 (고정값, 표현식 문자열 등)

    Returns:
        (value_type, parsed_value, source)
        - fixed: (FIXED, value, None)
        - expression: (EXPRESSION, "{{ expr }}", None)

    Examples:
        parse_field_value(10) → (FIXED, 10, None)
        parse_field_value("buy") → (FIXED, "buy", None)
        parse_field_value("{{ price * 0.99 }}") → (EXPRESSION, "{{ price * 0.99 }}", None)
    """
    import re

    # None은 그대로
    if value is None:
        return FieldValueType.FIXED, None, None

    # 문자열이 아닌 경우 고정값
    if not isinstance(value, str):
        return FieldValueType.FIXED, value, None

    # 표현식 패턴 체크: {{ ... }}
    expression_pattern = re.compile(r'\{\{.*?\}\}')
    if expression_pattern.search(value):
        return FieldValueType.EXPRESSION, value, None

    # 일반 문자열은 고정값
    return FieldValueType.FIXED, value, None


def is_expression(value: Any) -> bool:
    """값이 표현식인지 확인"""
    if not isinstance(value, str):
        return False
    import re
    return bool(re.search(r'\{\{.*?\}\}', value))


class FieldsDict(dict):
    """
    노드의 fields 딕셔너리

    JSON에서 파싱된 fields를 감싸며, 표현식 평가 메서드 제공
    """

    def get_field_type(self, key: str) -> FieldValueType:
        """필드의 값 타입 반환"""
        value = self.get(key)
        value_type, _, _ = parse_field_value(value)
        return value_type

    def has_expressions(self) -> bool:
        """표현식이 포함된 필드가 있는지 확인"""
        return any(is_expression(v) for v in self.values())

    def get_expression_fields(self) -> List[str]:
        """표현식이 포함된 필드 이름 목록"""
        return [k for k, v in self.items() if is_expression(v)]

    def get_fixed_fields(self) -> Dict[str, Any]:
        """고정값 필드만 반환"""
        return {k: v for k, v in self.items() if not is_expression(v)}
