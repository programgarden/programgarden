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
    JSON = "json"  # JSON 문자열 직접 입력 (fallback.default_value 등)
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
    CUSTOM_RESILIENCE_EDITOR = "custom_resilience_editor"

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

    def get_display_name(self, node_type: str) -> str:
        """
        필드의 표시 이름을 반환합니다.

        우선순위:
        1. display_name이 직접 지정되어 있으면 반환
        2. i18n 키 형식으로 반환 (i18n:fieldNames.{NodeType}.{field_name})
        3. 필드명을 Title Case로 변환하여 반환 (폴백)

        Args:
            node_type: 노드 타입명 (예: "OverseasStockBrokerNode")

        Returns:
            str: 표시할 필드명 또는 i18n 키
        """
        if self.display_name:
            return self.display_name

        # i18n 키 형식으로 반환 (클라이언트에서 해석)
        return f"i18n:fieldNames.{node_type}.{self.name}"

    def to_config_dict(self, node_type: str) -> Dict[str, Any]:
        """
        FieldSchema를 config_schema 형식의 딕셔너리로 변환합니다.

        클라이언트에서 동적 폼을 생성하기 위한 단순한 JSON 형식입니다.
        json_dynamic_widget 형식이 아닌, 필드 메타데이터만 제공합니다.

        Args:
            node_type: 노드 타입명 (예: "OverseasStockBrokerNode")

        Returns:
            dict: config_schema 필드 형식

        Example:
            >>> fs = FieldSchema(name="provider", type=FieldType.ENUM, ...)
            >>> config = fs.to_config_dict("OverseasStockBrokerNode")
            >>> # {"type": "enum", "display_name": "i18n:...", ...}
        """
        config: Dict[str, Any] = {
            "type": self.type.value if hasattr(self.type, 'value') else str(self.type),
            "display_name": self.get_display_name(node_type),
            "required": self.required,
            "category": self.category.value if hasattr(self.category, 'value') else str(self.category),
            "expression_mode": self.expression_mode.value if hasattr(self.expression_mode, 'value') else str(self.expression_mode),
        }

        # 선택적 필드들
        if self.description:
            config["description"] = self.description

        if self.default is not None:
            config["default"] = self.default

        # ENUM 타입 전용
        if self.enum_values:
            config["enum_values"] = self.enum_values
        if self.enum_labels:
            config["enum_labels"] = self.enum_labels

        # 숫자 타입 전용
        if self.min_value is not None:
            config["min_value"] = self.min_value
        if self.max_value is not None:
            config["max_value"] = self.max_value

        # 배열 타입 전용
        if self.array_item_type:
            config["array_item_type"] = self.array_item_type.value if hasattr(self.array_item_type, 'value') else str(self.array_item_type)

        # 객체/배열의 중첩 필드 (object_schema -> sub_fields로 이름 변경)
        if self.object_schema:
            config["sub_fields"] = self.object_schema

        # 바인딩 가이드
        if self.example is not None:
            config["example"] = self.example
        if self.example_binding:
            config["example_binding"] = self.example_binding
        if self.bindable_sources:
            config["bindable_sources"] = self.bindable_sources
        if self.expected_type:
            config["expected_type"] = self.expected_type

        # UI 힌트
        if self.ui_component:
            config["ui_component"] = self.ui_component.value if hasattr(self.ui_component, 'value') else str(self.ui_component)
        if self.ui_options:
            config["ui_options"] = self.ui_options
        if self.placeholder:
            config["placeholder"] = self.placeholder
        if self.help_text:
            config["help_text"] = self.help_text

        # 그룹핑
        if self.group:
            config["group"] = self.group

        # 조건부 표시
        if self.visible_when:
            config["visible_when"] = self.visible_when

        # CREDENTIAL 타입 전용
        if self.credential_types:
            config["credential_types"] = self.credential_types

        return config


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
