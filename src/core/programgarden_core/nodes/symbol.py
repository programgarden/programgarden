"""
ProgramGarden Core - Symbol 노드

종목 소스/필터 노드:
- WatchlistNode: 사용자 정의 관심종목 리스트
- MarketUniverseNode: 시장 전체 (NASDAQ100, S&P500 등)
- ScreenerNode: 조건부 종목 스크리닝
- SymbolFilterNode: 종목 리스트 필터/교집합/차집합
"""

from typing import Optional, List, Literal, Dict, Any, Union
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class WatchlistNode(BaseNode):
    """
    사용자 정의 관심종목 리스트 노드

    사용자가 직접 지정한 종목 리스트 출력
    """

    type: Literal["WatchlistNode"] = "WatchlistNode"
    category: NodeCategory = NodeCategory.SYMBOL

    # WatchlistNode 전용 설정
    # 템플릿 참조 허용 (예: "{{inputs.symbols}}")
    symbols: Union[List[str], str] = Field(
        default_factory=list,
        description="관심종목 코드 리스트 (예: ['AAPL', 'TSLA', 'NVDA']) 또는 템플릿 참조",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="종목 코드 리스트")
    ]


class MarketUniverseNode(BaseNode):
    """
    시장 전체 종목 노드

    특정 시장/지수의 구성 종목 리스트 출력
    """

    type: Literal["MarketUniverseNode"] = "MarketUniverseNode"
    category: NodeCategory = NodeCategory.SYMBOL

    # MarketUniverseNode 전용 설정
    universe: str = Field(
        default="NASDAQ100",
        description="시장/지수 (NASDAQ100, SP500, DOW30, RUSSELL2000 등)",
    )
    exchange: Optional[str] = Field(
        default=None, description="거래소 필터 (NYSE, NASDAQ, AMEX 등)"
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="BrokerNode 연결 (종목 조회용)",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="종목 코드 리스트")
    ]


class ScreenerNode(BaseNode):
    """
    조건부 종목 스크리닝 노드

    시가총액, 거래량, 섹터 등 조건에 따른 종목 필터링
    """

    type: Literal["ScreenerNode"] = "ScreenerNode"
    category: NodeCategory = NodeCategory.SYMBOL

    # ScreenerNode 전용 설정
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="스크리닝 조건 (예: {'market_cap_min': 10e9, 'volume_min': 1e6})",
    )
    universe: str = Field(
        default="ALL", description="스크리닝 대상 시장 (ALL, NASDAQ, NYSE 등)"
    )
    max_results: int = Field(default=100, description="최대 결과 개수")

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="BrokerNode 연결 (종목 조회용)",
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="스크리닝 실행 트리거",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="필터링된 종목 리스트")
    ]


class SymbolFilterNode(BaseNode):
    """
    종목 리스트 필터/집합 연산 노드

    여러 종목 리스트의 교집합/합집합/차집합 등 연산
    """

    type: Literal["SymbolFilterNode"] = "SymbolFilterNode"
    category: NodeCategory = NodeCategory.SYMBOL

    # SymbolFilterNode 전용 설정
    operation: Literal["union", "intersection", "difference", "exclude"] = Field(
        default="intersection",
        description="집합 연산 (union: 합집합, intersection: 교집합, difference: 차집합, exclude: 제외)",
    )
    exclude_symbols: List[str] = Field(
        default_factory=list, description="제외할 종목 리스트 (exclude 연산 시)"
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="input_a",
            type="symbol_list",
            description="첫 번째 종목 리스트",
        ),
        InputPort(
            name="input_b",
            type="symbol_list",
            description="두 번째 종목 리스트",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="연산 결과 종목 리스트")
    ]
