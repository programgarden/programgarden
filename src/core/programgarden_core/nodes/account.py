"""
ProgramGarden Core - Account Nodes

계좌/자산/포지션 관련 노드 (1회성 REST API 조회):
- AccountNode: 계좌 잔고, 보유종목, 미체결 조회

실시간 계좌 정보는 realtime/RealAccountNode 참조
"""

from typing import List, Literal

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class AccountNode(BaseNode):
    """
    REST API 1회성 계좌 조회 노드

    특정 시점의 계좌 정보를 REST API로 조회합니다:
    - 보유종목 목록
    - 각 종목별 포지션 (수량, 평균단가, 평가금액, 손익률)
    - 예수금/총자산
    - 미체결 주문

    실시간으로 계속 업데이트가 필요한 경우 RealAccountNode를 사용하세요.
    """

    type: Literal["AccountNode"] = "AccountNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.AccountNode.description"

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="held_symbols", type="symbol_list", description="i18n:ports.held_symbols"
        ),
        OutputPort(
            name="balance",
            type="balance_data",
            description="i18n:ports.balance",
        ),
        OutputPort(
            name="open_orders", type="order_list", description="i18n:ports.open_orders"
        ),
        OutputPort(
            name="positions",
            type="position_data",
            description="i18n:ports.positions",
        ),
    ]
