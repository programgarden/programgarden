from abc import ABC
from ..korea_alias import EnforceKoreanAliasABCMeta


class BaseAccno(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """
    계좌 관련 기능을 제공하는 객체의 기본 클래스입니다.
    (예: 잔고 조회, 예수금 조회 등)
    """
    pass

class BaseChart(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """
    차트 데이터 관련 기능을 제공하는 객체의 기본 클래스입니다.
    (예: 분봉, 일봉 조회 등)
    """
    pass

class BaseMarket(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """
    시세 및 종목 정보 관련 기능을 제공하는 객체의 기본 클래스입니다.
    (예: 현재가 조회, 호가 조회 등)
    """
    pass

class BaseOrder(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """
    주문 관련 기능을 제공하는 객체의 기본 클래스입니다.
    (예: 매수, 매도, 정정, 취소 등)
    """
    pass

class BaseReal(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """
    실시간 데이터(웹소켓 등) 관련 기능을 제공하는 객체의 기본 클래스입니다.
    """
    pass
