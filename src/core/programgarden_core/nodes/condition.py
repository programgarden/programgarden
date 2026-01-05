"""
ProgramGarden Core - Condition 노드

조건 평가 노드:
- ConditionNode: 조건 플러그인 실행 (RSI, MACD 등)
- LogicNode: 조건 조합 (and/or/xor/at_least/weighted)
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    PluginNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class ConditionNode(PluginNode):
    """
    조건 플러그인 실행 노드

    RSI, MACD, BollingerBands 등 커뮤니티 플러그인 실행
    """

    type: Literal["ConditionNode"] = "ConditionNode"
    category: NodeCategory = NodeCategory.CONDITION

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="조건 평가 트리거"),
        InputPort(
            name="price_data",
            type="market_data",
            description="가격 데이터 (RealMarketDataNode에서)",
        ),
        InputPort(
            name="volume_data",
            type="market_data",
            description="거래량 데이터",
            required=False,
        ),
        InputPort(
            name="symbols",
            type="symbol_list",
            description="평가 대상 종목 리스트",
            required=False,
        ),
        InputPort(
            name="held_symbols",
            type="symbol_list",
            description="보유 종목 리스트 (익절/손절용)",
            required=False,
        ),
        InputPort(
            name="position_data",
            type="position_data",
            description="포지션 데이터 (수익률 기반 조건용)",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="condition_result",
            description="조건 평가 결과 (True/False)",
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="조건을 통과한 종목 리스트",
        ),
        OutputPort(
            name="failed_symbols",
            type="symbol_list",
            description="조건을 통과하지 못한 종목 리스트",
        ),
        OutputPort(
            name="values",
            type="dict",
            description="조건 평가에 사용된 값 (예: RSI 값)",
        ),
    ]


class LogicNode(BaseNode):
    """
    조건 조합 노드

    여러 조건의 결과를 논리 연산으로 조합
    """

    type: Literal["LogicNode"] = "LogicNode"
    category: NodeCategory = NodeCategory.CONDITION

    # LogicNode 전용 설정
    operator: Literal["all", "any", "not", "xor", "at_least", "at_most", "exactly", "weighted"] = Field(
        default="all",
        description="논리 연산자 (all=AND, any=OR, not, xor, at_least, at_most, exactly, weighted)",
    )
    threshold: Optional[int] = Field(
        default=None,
        description="임계값 (at_least, at_most, exactly 연산자용)",
    )
    weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="가중치 (weighted 연산자용, 입력 ID별 가중치)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="input",
            type="condition_result",
            description="조건 결과 입력 (여러 개 연결 가능)",
            multiple=True,
            min_connections=2,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="condition_result",
            description="조합된 조건 결과",
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="조건을 통과한 종목 리스트",
        ),
    ]
