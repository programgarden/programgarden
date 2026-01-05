"""
ProgramGarden Core - Risk 노드

리스크 관리 노드:
- PositionSizingNode: 포지션 크기 계산
- RiskGuardNode: 일일손실한도, 최대포지션 제한
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class PositionSizingNode(BaseNode):
    """
    포지션 크기 계산 노드

    켈리 공식, 고정비율, ATR 기반 등 다양한 포지션 사이징 방법 지원
    """

    type: Literal["PositionSizingNode"] = "PositionSizingNode"
    category: NodeCategory = NodeCategory.RISK

    # PositionSizingNode 전용 설정
    method: Literal["fixed_percent", "fixed_amount", "kelly", "atr_based"] = Field(
        default="fixed_percent",
        description="포지션 사이징 방법",
    )
    max_percent: float = Field(
        default=10.0,
        description="계좌 대비 최대 포지션 비율 (%)",
    )
    fixed_amount: Optional[float] = Field(
        default=None,
        description="고정 금액 (fixed_amount 방법용)",
    )
    kelly_fraction: float = Field(
        default=0.25,
        description="켈리 비율 조정값 (kelly 방법용, 보수적으로 1/4 적용)",
    )
    atr_risk_percent: float = Field(
        default=1.0,
        description="ATR 기반 리스크 비율 (atr_based 방법용)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="symbols",
            type="symbol_list",
            description="포지션 계산 대상 종목",
        ),
        InputPort(
            name="balance",
            type="balance_data",
            description="계좌 잔고 정보",
        ),
        InputPort(
            name="price_data",
            type="market_data",
            description="현재가 정보",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="quantity",
            type="dict",
            description="종목별 주문 수량",
        ),
        OutputPort(
            name="symbols",
            type="symbol_list",
            description="포지션 계산된 종목 리스트",
        ),
    ]


class RiskGuardNode(BaseNode):
    """
    리스크 가드 노드

    일일손실한도, 최대포지션, 연속손실 제한 등 리스크 관리
    """

    type: Literal["RiskGuardNode"] = "RiskGuardNode"
    category: NodeCategory = NodeCategory.RISK

    # RiskGuardNode 전용 설정
    max_daily_loss: Optional[float] = Field(
        default=None,
        description="일일 최대 손실액 (음수, 예: -500)",
    )
    max_daily_loss_percent: Optional[float] = Field(
        default=None,
        description="일일 최대 손실률 (%, 예: -5)",
    )
    max_positions: Optional[int] = Field(
        default=None,
        description="최대 동시 포지션 수",
    )
    max_position_per_symbol: Optional[float] = Field(
        default=None,
        description="종목당 최대 포지션 비율 (%)",
    )
    max_consecutive_losses: Optional[int] = Field(
        default=None,
        description="연속 손실 제한 (횟수)",
    )
    cooldown_after_loss_minutes: Optional[int] = Field(
        default=None,
        description="손실 후 대기 시간 (분)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="symbols",
            type="symbol_list",
            description="진입 요청 종목 리스트",
        ),
        InputPort(
            name="account_state",
            type="account_data",
            description="계좌 상태 정보",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="approved_symbols",
            type="symbol_list",
            description="리스크 체크 통과한 종목 리스트",
        ),
        OutputPort(
            name="blocked_symbols",
            type="symbol_list",
            description="리스크 체크 실패한 종목 리스트",
        ),
        OutputPort(
            name="blocked_reason",
            type="string",
            description="차단 사유",
        ),
    ]
