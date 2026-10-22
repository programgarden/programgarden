"""
ProgramGarden Core - Edge 모델

노드 간 연결(엣지) 정의
- main: 실행 순서 (DAG topological sort에 포함)
- tool: AI Agent의 Tool로 등록 (DAG 순서에서 제외, 필요 시 호출)
- ai_model: LLM 연결 제공 (DAG 순서에서 제외)

데이터 바인딩은 노드 config에서 {{ nodeId.field }} 표현식으로 처리
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EdgeType(str, Enum):
    """엣지 타입"""
    MAIN = "main"          # 기존: 실행 순서 (DAG 포함)
    TOOL = "tool"          # AI Agent의 Tool로 등록 (DAG 제외)
    AI_MODEL = "ai_model"  # LLM 연결 제공 (DAG 제외)


class Edge(BaseModel):
    """
    노드 간 연결 정의

    엣지 타입별 역할:
    - main (기본): 실행 순서 정의, DAG topological sort에 포함
    - tool: AI Agent의 Tool로 등록, DAG 순서에서 제외 (Agent가 필요 시 호출)
    - ai_model: LLM 연결 제공, DAG 순서에서 제외

    Examples:
        main 엣지 (실행 순서):
        - {"from": "schedule", "to": "broker"}
        - {"from": "broker", "to": "ai-trader"}

        tool 엣지 (AI Tool 등록):
        - {"from": "market", "to": "ai-trader", "type": "tool"}

        ai_model 엣지 (LLM 연결):
        - {"from": "llm", "to": "ai-trader", "type": "ai_model"}

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
    from_port: Optional[str] = Field(
        default=None,
        description="출발 포트 (예: IfNode의 true/false)",
    )
    edge_type: EdgeType = Field(
        default=EdgeType.MAIN,
        alias="type",
        description="엣지 타입 (main: 실행 순서, tool: AI Tool, ai_model: LLM 연결)",
    )

    description: Optional[str] = Field(
        default=None,
        description="연결 설명",
    )

    @property
    def is_dag_edge(self) -> bool:
        """DAG topological sort에 포함되는 엣지인지 여부"""
        return self.edge_type == EdgeType.MAIN

    @model_validator(mode='before')
    @classmethod
    def extract_node_ids(cls, values: dict) -> dict:
        """
        from/to 값에서 노드 ID만 추출하고 포트 정보를 보존

        "nodeA.portX" → from="nodeA", from_port="portX"
        "nodeA" → from="nodeA"
        """
        if isinstance(values, dict):
            from_val = values.get('from') or values.get('from_node')
            to_val = values.get('to') or values.get('to_node')

            if from_val:
                from_str = str(from_val)
                if '.' in from_str:
                    parts = from_str.split('.', 1)
                    values['from'] = parts[0]
                    if not values.get('from_port'):
                        values['from_port'] = parts[1]
                else:
                    values['from'] = from_str
            if to_val:
                values['to'] = str(to_val).split('.')[0]

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
