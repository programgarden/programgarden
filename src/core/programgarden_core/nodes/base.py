"""
ProgramGarden Core - 노드 베이스 클래스

모든 노드의 기반이 되는 BaseNode와 공통 타입 정의
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Literal, ClassVar
from pydantic import BaseModel, Field

from programgarden_core.models.field_binding import FieldSchema, FieldType


class NodeCategory(str, Enum):
    """노드 카테고리 (14개)"""

    INFRA = "infra"
    REALTIME = "realtime"
    DATA = "data"
    SYMBOL = "symbol"
    TRIGGER = "trigger"
    CONDITION = "condition"
    RISK = "risk"
    ORDER = "order"
    EVENT = "event"
    DISPLAY = "display"
    GROUP = "group"
    BACKTEST = "backtest"
    JOB = "job"
    CALCULATION = "calculation"


class Position(BaseModel):
    """Flutter UI용 노드 위치"""

    x: float = 0.0
    y: float = 0.0


class InputPort(BaseModel):
    """입력 포트 정의"""

    name: str
    type: str
    description: Optional[str] = None
    required: bool = True
    multiple: bool = False  # 여러 엣지 연결 가능 여부
    min_connections: Optional[int] = None  # 최소 연결 수


class OutputPort(BaseModel):
    """출력 포트 정의"""

    name: str
    type: str
    description: Optional[str] = None


class BaseNode(BaseModel):
    """
    모든 노드의 베이스 클래스

    Attributes:
        id: 노드 고유 ID (워크플로우 내에서 유일)
        type: 노드 타입 (클래스명)
        category: 노드 카테고리
        position: Flutter UI용 위치 (선택적)
        config: 노드별 설정
        description: 노드 설명
    """

    id: str = Field(..., description="노드 고유 ID")
    type: str = Field(..., description="노드 타입")
    category: NodeCategory = Field(..., description="노드 카테고리")
    position: Optional[Position] = Field(
        default=None, description="Flutter UI용 노드 위치"
    )
    config: Dict[str, Any] = Field(default_factory=dict, description="노드 설정")
    description: Optional[str] = Field(default=None, description="노드 설명")

    # 메타 정보 (서브클래스에서 오버라이드)
    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = []
    _field_schema: ClassVar[Dict[str, FieldSchema]] = {}

    class Config:
        use_enum_values = True
        extra = "allow"  # 플러그인별 추가 필드 허용

    def get_inputs(self) -> List[InputPort]:
        """입력 포트 목록 반환"""
        return self._inputs

    def get_outputs(self) -> List[OutputPort]:
        """출력 포트 목록 반환"""
        return self._outputs

    def validate_config(self) -> bool:
        """설정 유효성 검증 (서브클래스에서 오버라이드)"""
        return True

    @classmethod
    def get_field_schema(cls) -> Dict[str, FieldSchema]:
        """노드의 설정 가능한 필드 스키마 반환"""
        return cls._field_schema


class PluginNode(BaseNode):
    """
    플러그인을 사용하는 노드의 베이스 클래스

    ConditionNode, NewOrderNode, ModifyOrderNode, CancelOrderNode 등이 상속
    """

    plugin: str = Field(..., description="플러그인 ID (예: RSI, MarketOrder)")
    plugin_version: Optional[str] = Field(
        default=None, description="플러그인 버전 (예: 1.2.0)"
    )
    fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="플러그인 필드 (고정값, 바인딩, 표현식 지원)",
    )

    def get_plugin_ref(self) -> str:
        """플러그인 참조 문자열 반환 (예: RSI@1.2.0)"""
        if self.plugin_version:
            return f"{self.plugin}@{self.plugin_version}"
        return self.plugin

    def has_expressions(self) -> bool:
        """표현식이 포함된 필드가 있는지 확인"""
        from programgarden_core.models.field_binding import is_expression
        return any(is_expression(v) for v in self.fields.values())
