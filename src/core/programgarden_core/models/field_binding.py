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
    UI 컴포넌트 타입 (전역 상수)
    
    expression_mode에 따른 UI 렌더링:
    - fixed_only: ui_component에 따른 입력 컴포넌트만 표시
    - expression_only: BINDING_INPUT ({{ }} 에디터)만 표시
    - both: [Fixed | Expression] 토글 + 선택에 따른 입력
    
    FieldType → UIComponent 기본 매핑:
    - ENUM → SELECT
    - CREDENTIAL → CREDENTIAL_SELECT  
    - NUMBER/INTEGER → NUMBER_INPUT
    - BOOLEAN → CHECKBOX
    - STRING → TEXT_INPUT
    - ARRAY[OBJECT] (직접 편집) → OBJECT_ARRAY_TABLE, SYMBOL_EDITOR 등
    - ARRAY (바인딩 전용) → BINDING_INPUT
    - OBJECT (바인딩 전용) → BINDING_INPUT
    """
    
    # === 기본 입력 컴포넌트 ===
    TEXT_INPUT = "text_input"              # 짧은 텍스트 입력
    TEXTAREA = "textarea"                  # 긴 텍스트 입력 (여러 줄)
    NUMBER_INPUT = "number_input"          # 숫자 입력 (스피너 포함)
    CHECKBOX = "checkbox"                  # 불리언 체크박스
    SELECT = "select"                      # 드롭다운 선택 (ENUM용)
    MULTI_SELECT = "multi_select"          # 다중 선택 (배열용)
    
    # === 특수 입력 컴포넌트 ===
    CREDENTIAL_SELECT = "credential_select"  # Credential 선택 드롭다운
    PLUGIN_SELECT = "plugin_select"          # 플러그인 선택 드롭다운 (ConditionNode 등)
    SYMBOL_EDITOR = "symbol_editor"          # 종목 편집기 (exchange + symbol 쌍, fx 토글로 바인딩 지원)
    OBJECT_ARRAY_TABLE = "object_array_table"  # 객체 배열 테이블 (object_schema 기반, 행 추가/삭제)
    KEY_VALUE_EDITOR = "key_value_editor"    # 키-값 쌍 편집기 (HTTP headers 등)
    FIELD_MAPPING_EDITOR = "field_mapping_editor"  # 필드 매핑 편집기 (from→to 변환 테이블)
    CODE_EDITOR = "code_editor"              # 코드/JSON 편집기
    
    # === 바인딩 전용 컴포넌트 ===
    BINDING_INPUT = "binding_input"          # 바인딩 입력 ({{ nodes.xxx.yyy }} 전용)
    
    # === 날짜/시간 컴포넌트 ===
    DATE_PICKER = "date_picker"              # 날짜 선택기
    TIME_PICKER = "time_picker"              # 시간 선택기
    DATETIME_PICKER = "datetime_picker"      # 날짜+시간 선택기
    
    # === 슬라이더/범위 ===
    SLIDER = "slider"                        # 슬라이더 (범위 값)
    RANGE_SLIDER = "range_slider"            # 범위 슬라이더 (min-max)
    
    @classmethod
    def get_default_for_field_type(cls, field_type: "FieldType") -> "UIComponent":
        """FieldType에 대한 기본 UIComponent 반환"""
        mapping = {
            FieldType.STRING: cls.TEXT_INPUT,
            FieldType.NUMBER: cls.NUMBER_INPUT,
            FieldType.INTEGER: cls.NUMBER_INPUT,
            FieldType.BOOLEAN: cls.CHECKBOX,
            FieldType.ENUM: cls.SELECT,
            FieldType.ARRAY: cls.TEXT_INPUT,  # 배열은 상황에 따라 다름
            FieldType.OBJECT: cls.BINDING_INPUT,  # 객체는 보통 바인딩
            FieldType.KEY_VALUE_PAIRS: cls.KEY_VALUE_EDITOR,
            FieldType.CREDENTIAL: cls.CREDENTIAL_SELECT,
        }
        return mapping.get(field_type, cls.TEXT_INPUT)


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

    model_config = ConfigDict(use_enum_values=True)


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
