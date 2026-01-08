"""
ProgramGarden Core - Field Binding 모델

노드 필드의 값 바인딩 시스템:
- FieldSchema: 필드 스키마 정의 (UI 렌더링용)
- FieldValue: 필드 값 (고정값, 바인딩, 표현식)
"""

from enum import Enum
from typing import Optional, Any, List, Dict, Union
from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """필드 데이터 타입"""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ENUM = "enum"
    ARRAY = "array"
    OBJECT = "object"


class FieldSchema(BaseModel):
    """
    노드 필드 스키마 (UI 렌더링 및 검증용)

    백엔드에서 정의하고, 클라이언트(Flutter)가 이를 기반으로
    동적 폼을 생성합니다.

    Example:
        FieldSchema(
            name="quantity",
            type=FieldType.INTEGER,
            description="주문 수량",
            required=True,
            bindable=True,
            expression_enabled=True,
        )
    """

    name: str = Field(..., description="필드 이름")
    type: FieldType = Field(..., description="필드 데이터 타입")
    description: Optional[str] = Field(default=None, description="필드 설명")

    # 필수/기본값
    required: bool = Field(default=False, description="필수 여부")
    default: Optional[Any] = Field(default=None, description="기본값")

    # 타입별 추가 옵션
    enum_values: Optional[List[str]] = Field(
        default=None, description="enum 타입의 선택 가능 값 목록"
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
    bindable: bool = Field(
        default=True, description="다른 노드 출력과 바인딩 가능 여부"
    )
    expression_enabled: bool = Field(
        default=False, description="{{ }} 표현식 사용 가능 여부"
    )

    # UI 힌트
    ui_component: Optional[str] = Field(
        default=None,
        description="UI 컴포넌트 힌트 (dropdown, slider, textarea 등)",
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

    class Config:
        use_enum_values = True


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
