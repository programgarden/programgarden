"""Finance 패키지용 기본 컴포넌트 클래스들

EN:
    Base classes for finance package components (account, chart, market, order, real).

KO:
    Finance 패키지의 컴포넌트 베이스 클래스들 (계좌, 차트, 시세, 주문, 실시간)
"""

from abc import ABC
from ..korea_alias import EnforceKoreanAliasABCMeta


class BaseAccno(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """계좌 관련 기능을 제공하는 객체의 기본 클래스

    EN:
        Base class for account-related functionality.
        (e.g., balance inquiry, deposit inquiry, etc.)

    KO:
        계좌 관련 기능을 제공하는 객체의 기본 클래스입니다.
        (예: 잔고 조회, 예수금 조회 등)
    """
    pass


class BaseChart(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """차트 데이터 관련 기능을 제공하는 객체의 기본 클래스

    EN:
        Base class for chart data functionality.
        (e.g., minute bars, daily bars, etc.)

    KO:
        차트 데이터 관련 기능을 제공하는 객체의 기본 클래스입니다.
        (예: 분봉, 일봉 조회 등)
    """
    pass


class BaseMarket(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """시세 및 종목 정보 관련 기능을 제공하는 객체의 기본 클래스

    EN:
        Base class for market data and symbol information.
        (e.g., current price inquiry, order book inquiry, etc.)

    KO:
        시세 및 종목 정보 관련 기능을 제공하는 객체의 기본 클래스입니다.
        (예: 현재가 조회, 호가 조회 등)
    """
    pass


class BaseOrder(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """주문 관련 기능을 제공하는 객체의 기본 클래스

    EN:
        Base class for order-related functionality.
        (e.g., buy, sell, modify, cancel, etc.)

    KO:
        주문 관련 기능을 제공하는 객체의 기본 클래스입니다.
        (예: 매수, 매도, 정정, 취소 등)
    """
    pass


class BaseReal(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """실시간 데이터(WebSocket) 관련 기능을 제공하는 객체의 기본 클래스

    EN:
        Base class for real-time data functionality via WebSocket.

    KO:
        실시간 데이터(웹소켓 등) 관련 기능을 제공하는 객체의 기본 클래스입니다.
    """
    pass
