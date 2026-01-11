"""
ProgramGarden Core - Edge 모델

노드 간 연결(엣지) 정의 - 실행 순서만 표현
데이터 바인딩은 노드 config에서 {{ nodeId.field }} 표현식으로 처리
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Edge(BaseModel):
    """
    노드 간 연결 정의 (실행 순서)

    엣지는 노드 간 실행 순서만 표현합니다.
    데이터 바인딩은 노드 config에서 {{ }} 표현식으로 처리합니다.

    Examples:
        엣지 (실행 순서):
        - {"from": "start", "to": "broker"}
        - {"from": "broker", "to": "watchlist"}
        - {"from": "watchlist", "to": "marketData"}

        데이터 바인딩 (노드 config):
        - "symbols": "{{ watchlist.symbols }}"
        - "price": "{{ marketData.price }}"
    """
    
    model_config = ConfigDict(populate_by_name=True)

    from_node: str = Field(
        ...,
        alias="from",
        description="출발 노드 ID",
    )
    to_node: str = Field(
        ...,
        alias="to",
        description="도착 노드 ID",
    )
    
    description: Optional[str] = Field(
        default=None,
        description="연결 설명",
    )

    @model_validator(mode='before')
    @classmethod
    def extract_node_ids(cls, values: dict) -> dict:
        """
        from/to 값에서 노드 ID만 추출 (하위호환성)
        
        "nodeA.portX" → "nodeA"
        "nodeA" → "nodeA"
        """
        if isinstance(values, dict):
            from_val = values.get('from') or values.get('from_node')
            to_val = values.get('to') or values.get('to_node')
            
            if from_val:
                values['from'] = from_val.split('.')[0]
            if to_val:
                values['to'] = to_val.split('.')[0]
        
        return values

    # 하위호환성을 위한 property (기존 코드가 참조하는 경우)
    @property
    def from_node_id(self) -> str:
        """출발 노드 ID (하위호환)"""
        return self.from_node

    @property
    def to_node_id(self) -> str:
        """도착 노드 ID (하위호환)"""
        return self.to_node
