from abc import ABC, abstractmethod
from ..korea_alias import EnforceKoreanAliasABCMeta, require_korean_alias
from .components import BaseAccno, BaseChart, BaseMarket, BaseOrder, BaseReal


class BaseOverseasStock(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """
    해외 주식 관련 기능을 제공하는 객체의 기본 클래스입니다.
    (예: 잔고, 차트, 시세, 주문 등)
    """
    
    @abstractmethod
    @require_korean_alias
    def accno(self) -> BaseAccno:
        """계좌 관련 객체를 반환합니다."""
        pass

    @abstractmethod
    @require_korean_alias
    def chart(self) -> BaseChart:
        """차트 관련 객체를 반환합니다."""
        pass

    @abstractmethod
    @require_korean_alias
    def market(self) -> BaseMarket:
        """시세 관련 객체를 반환합니다."""
        pass

    @abstractmethod
    @require_korean_alias
    def order(self) -> BaseOrder:
        """주문 관련 객체를 반환합니다."""
        pass

    @abstractmethod
    @require_korean_alias
    def real(self) -> BaseReal:
        """실시간 데이터 관련 객체를 반환합니다."""
        pass

    계좌 = accno
    차트 = chart
    시세 = market
    주문 = order
    실시간 = real


class BaseOverseasFutureoption(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """
    해외 선물/옵션 관련 기능을 제공하는 객체의 기본 클래스입니다.
    (예: 잔고, 차트, 시세, 주문 등)
    """
    
    @abstractmethod
    @require_korean_alias
    def accno(self) -> BaseAccno:
        """계좌 관련 객체를 반환합니다."""
        pass

    @abstractmethod
    @require_korean_alias
    def chart(self) -> BaseChart:
        """차트 관련 객체를 반환합니다."""
        pass

    @abstractmethod
    @require_korean_alias
    def market(self) -> BaseMarket:
        """시세 관련 객체를 반환합니다."""
        pass

    @abstractmethod
    @require_korean_alias
    def order(self) -> BaseOrder:
        """주문 관련 객체를 반환합니다."""
        pass

    @abstractmethod
    @require_korean_alias
    def real(self) -> BaseReal:
        """실시간 데이터 관련 객체를 반환합니다."""
        pass

    계좌 = accno
    차트 = chart
    시세 = market
    주문 = order
    실시간 = real

