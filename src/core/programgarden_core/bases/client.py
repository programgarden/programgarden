"""Finance 패키지용 클라이언트 베이스 클래스

EN:
    Base class for broker client implementations.

KO:
    증권사 클라이언트 구현을 위한 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import Any

from ..korea_alias import EnforceKoreanAliasABCMeta, require_korean_alias
from .products import BaseOverseasStock, BaseOverseasFutureoption


class BaseClient(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """공통 브로커 클라이언트 인터페이스

    EN:
        Common broker client interface that all broker implementations must follow.

    KO:
        모든 브로커 구현체가 따라야 하는 공통 클라이언트 인터페이스입니다.
    """

    @abstractmethod
    def is_logged_in(self) -> bool:
        """세션이 인증되었는지 반환

        EN:
            Return whether session is authenticated.

        KO:
            세션이 인증되었는지 여부를 반환합니다.
        """

    @abstractmethod
    @require_korean_alias
    def login(self, **kwargs: Any) -> bool:
        """동기 로그인 수행

        EN:
            Perform synchronous login.

        KO:
            동기 방식으로 로그인을 수행합니다.
        """

    @abstractmethod
    @require_korean_alias
    async def async_login(self, **kwargs: Any) -> bool:
        """비동기 로그인 수행

        EN:
            Perform asynchronous login.

        KO:
            비동기 방식으로 로그인을 수행합니다.
        """

    @abstractmethod
    @require_korean_alias
    def overseas_stock(self) -> BaseOverseasStock:
        """해외주식 파사드 반환

        EN:
            Return overseas stock facade.

        KO:
            해외주식 기능을 제공하는 파사드 객체를 반환합니다.
        """

    @abstractmethod
    @require_korean_alias
    def overseas_futureoption(self) -> BaseOverseasFutureoption:
        """해외선물/옵션 파사드 반환

        EN:
            Return overseas futures/options facade.

        KO:
            해외선물/옵션 기능을 제공하는 파사드 객체를 반환합니다.
        """

    로그인 = login
    비동기로그인 = async_login
    해외주식 = overseas_stock
    해외선물 = overseas_futureoption
