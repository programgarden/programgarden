from abc import ABC, abstractmethod
from typing import Any, Generic, List, Literal, Optional, TypeVar, TypedDict

from programgarden_core.bases.base import SymbolInfoOverseasStock, SymbolInfoOverseasFutures


SymbolInfoType = TypeVar("SymbolInfoType", SymbolInfoOverseasStock, SymbolInfoOverseasFutures)


class BaseStrategyConditionResponseCommon(TypedDict):
    """전략 조건 응답의 공통 필드"""

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
    weight: Optional[int]
    """조건의 가중치는 0과 1사이의 값, 기본값은 0"""
    product: Literal["overseas_stock", "overseas_futures"]
    """응답이 속한 상품 유형"""


class BaseStrategyConditionResponseOverseasStockType(BaseStrategyConditionResponseCommon):
    """해외주식 조건 전략 응답 필드"""

    product: Literal["overseas_stock"]
    """응답이 속한 상품 유형"""


class BaseStrategyConditionResponseOverseasFuturesType(BaseStrategyConditionResponseCommon):
    """해외선물 조건 전략 응답 필드"""

    product: Literal["overseas_futures"]
    """응답이 속한 상품 유형"""
    position_side: Literal["long", "short", "flat"]
    """해외선물은 양방향 포지션을 지원하므로 롱/숏/포지션 없음(flat)으로 결과를 표현합니다."""


ResponseType = TypeVar(
    "ResponseType",
    BaseStrategyConditionResponseOverseasStockType,
    BaseStrategyConditionResponseOverseasFuturesType,
)


class BaseStrategyCondition(Generic[SymbolInfoType, ResponseType], ABC):
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
        self.symbol: Optional[SymbolInfoType] = None

    @abstractmethod
    async def execute(self) -> 'ResponseType':
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

    def _set_symbol(self, symbol: SymbolInfoType) -> None:
        """
        계산할 종목들을 선정합니다.
        선정된 종목들 위주로 조건 충족 여부를 확인해서 반환해줍니다.
        """
        self.symbol = symbol


class BaseStrategyConditionOverseasStock(
    BaseStrategyCondition[SymbolInfoOverseasStock, BaseStrategyConditionResponseOverseasStockType],
    ABC,
):
    """해외주식 조건 전략 기본 클래스"""
    product_type: Literal["overseas_stock"] = "overseas_stock"


class BaseStrategyConditionOverseasFutures(
    BaseStrategyCondition[SymbolInfoOverseasFutures, BaseStrategyConditionResponseOverseasFuturesType],
    ABC,
):
    """해외선물 조건 전략 기본 클래스"""

    product_type: Literal["overseas_futures"] = "overseas_futures"
