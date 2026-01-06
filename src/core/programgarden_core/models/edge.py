"""
ProgramGarden Core - Edge 모델

노드 간 연결(엣지) 정의
"""

from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class Edge(BaseModel):
    """
    노드 간 연결 정의

    from_node.output → to_node.input 형태로 데이터 흐름 표현

    Examples:
        - {"from": "broker.connection", "to": "realAccount"}
        - {"from": "rsi.passed_symbols", "to": "order.symbols"}
        - {"from": "schedule.trigger", "to": "tradingHours"}
        - {"from": "start", "to": "broker"}  # 포트 생략 시 기본 포트 사용
    """

    from_port: Optional[str] = Field(
        default=None,
        alias="from",
        description="출발 포트 (node_id.output_name 또는 node_id)",
    )
    to_port: Optional[str] = Field(
        default=None,
        alias="to",
        description="도착 포트 (node_id.input_name 또는 node_id)",
    )
    
    description: Optional[str] = Field(
        default=None,
        description="연결 설명",
    )

    class Config:
        populate_by_name = True  # alias 사용 허용
    
    @model_validator(mode='after')
    def validate_required_fields(self) -> 'Edge':
        """필수 필드 검증"""
        if not self.from_port:
            raise ValueError("'from' 필드가 필요합니다")
        if not self.to_port:
            raise ValueError("'to' 필드가 필요합니다")
        return self

    @property
    def from_node_id(self) -> str:
        """출발 노드 ID 추출"""
        return self.from_port.split(".")[0]

    @property
    def from_output_name(self) -> Optional[str]:
        """출발 출력 포트 이름 추출"""
        parts = self.from_port.split(".")
        return parts[1] if len(parts) > 1 else None

    @property
    def to_node_id(self) -> str:
        """도착 노드 ID 추출"""
        return self.to_port.split(".")[0]

    @property
    def to_input_name(self) -> Optional[str]:
        """도착 입력 포트 이름 추출"""
        parts = self.to_port.split(".")
        return parts[1] if len(parts) > 1 else None

    @field_validator("from_port", "to_port", mode='before')
    @classmethod
    def validate_port_format(cls, v: Optional[str]) -> Optional[str]:
        """포트 형식 검증 (node_id 또는 node_id.port_name)"""
        if v is None:
            return v
        if not v:
            raise ValueError("포트는 빈 문자열일 수 없습니다")
        parts = v.split(".")
        if len(parts) > 2:
            raise ValueError(f"잘못된 포트 형식: {v} (node_id.port_name 형식이어야 합니다)")
        return v
