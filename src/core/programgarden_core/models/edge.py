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

    지원 형식:
        1. {"from": "broker.connection", "to": "realAccount"}
        2. {"source": "broker", "sourceHandle": "connection", "target": "realAccount"}
        
    Examples:
        - {"from": "broker.connection", "to": "realAccount"}
        - {"from": "rsi.passed_symbols", "to": "order.symbols"}
        - {"from": "schedule.trigger", "to": "tradingHours"}
        - {"source": "start", "sourceHandle": "trigger", "target": "schedule"}
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
    
    # 대안 필드 (source/target 스타일)
    source: Optional[str] = Field(
        default=None,
        description="출발 노드 ID (sourceHandle과 함께 사용)",
    )
    sourceHandle: Optional[str] = Field(
        default=None,
        description="출발 출력 포트 이름",
    )
    target: Optional[str] = Field(
        default=None,
        description="도착 노드 ID (targetHandle과 함께 사용)",
    )
    targetHandle: Optional[str] = Field(
        default=None,
        description="도착 입력 포트 이름",
    )
    
    description: Optional[str] = Field(
        default=None,
        description="연결 설명",
    )

    class Config:
        populate_by_name = True  # alias 사용 허용
    
    @model_validator(mode='after')
    def normalize_fields(self) -> 'Edge':
        """source/target 스타일을 from/to로 정규화"""
        # source/target → from/to 변환
        if self.source and not self.from_port:
            if self.sourceHandle:
                self.from_port = f"{self.source}.{self.sourceHandle}"
            else:
                self.from_port = self.source
        
        if self.target and not self.to_port:
            if self.targetHandle:
                self.to_port = f"{self.target}.{self.targetHandle}"
            else:
                self.to_port = self.target
        
        # 필수 필드 검증
        if not self.from_port:
            raise ValueError("'from' 또는 'source' 필드가 필요합니다")
        if not self.to_port:
            raise ValueError("'to' 또는 'target' 필드가 필요합니다")
        
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
