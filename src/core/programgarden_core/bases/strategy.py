from abc import ABC, abstractmethod
from typing import Any, List, Optional, TypedDict

from programgarden_core.bases.base import SymbolInfo


class BaseStrategyConditionResponseType(TypedDict):
    """기본 응답 데이터"""

    condition_id: Optional[str]
    """조건 ID"""
    success: bool
    """조건 통과한 종목이 1개라도 있으면 True로 처리합니다."""
    symbol: str
    """종목 코드"""
    exchcd: str
    """거래소 코드"""
    data: Any
    """조건 통과한 종목에 대한 추가 데이터"""
    weight: Optional[int] = 0
    """조건의 가중치는 0과 1사이의 값, 기본값은 0"""


class BaseStrategyCondition(ABC):
    """
    종목추출 전략의 조건 타입을 정의하는 추상 클래스입니다.
    """

    id: str
    """전략의 고유 ID"""
    description: str
    """전략에 대한 설명"""
    securities: List[str]
    """사용 가능한 증권사/거래소들"""

    @abstractmethod
    def __init__(self, **kwargs):
        self.symbol: Optional[SymbolInfo] = None

    @abstractmethod
    async def execute(self) -> 'BaseStrategyConditionResponseType':
        """
        전략을 실행하는 메서드입니다.
        구체적인 전략 클래스에서 구현해야 합니다.
        """
        pass

    def _set_system_id(self, system_id: Optional[str]) -> None:
        """
        시스템 고유 ID를 설정합니다.
        """
        self.system_id = system_id

    def _set_symbol(self, symbol: SymbolInfo) -> None:
        """
        계산할 종목들을 선정합니다.
        선정된 종목들 위주로 조건 충족 여부를 확인해서 반환해줍니다.
        """
        self.symbol = symbol
