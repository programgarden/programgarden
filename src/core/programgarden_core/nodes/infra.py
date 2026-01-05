"""
ProgramGarden Core - Infra 노드

인프라/연결 관련 노드:
- StartNode: 워크플로우 진입점
- BrokerNode: 증권사 연결
"""

from typing import Optional, List, Literal
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class StartNode(BaseNode):
    """
    워크플로우 진입점

    Definition당 1개 필수. 워크플로우 실행의 시작점.
    """

    type: Literal["StartNode"] = "StartNode"
    category: NodeCategory = NodeCategory.INFRA

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="start", type="signal", description="워크플로우 시작 신호")
    ]


class BrokerNode(BaseNode):
    """
    증권사 연결 노드

    OpenAPI 연결을 위한 증권사 설정.
    credential_id로 실제 인증 정보 참조.
    """

    type: Literal["BrokerNode"] = "BrokerNode"
    category: NodeCategory = NodeCategory.INFRA

    # BrokerNode 전용 설정
    provider: str = Field(
        default="ls-sec.co.kr", description="증권사 제공자 (현재 LS증권만 지원)"
    )
    product: Literal["overseas_stock", "overseas_futures"] = Field(
        default="overseas_stock", description="상품 유형"
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(
            name="connection",
            type="broker_connection",
            description="증권사 연결 객체",
        )
    ]
