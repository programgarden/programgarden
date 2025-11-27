from abc import ABC, abstractmethod
from typing import Any

from ..korea_alias import EnforceKoreanAliasABCMeta, require_korean_alias
from .products import BaseOverseasStock, BaseOverseasFutureoption


class BaseClient(ABC, metaclass=EnforceKoreanAliasABCMeta):
    """Common broker client interface."""

    @abstractmethod
    def is_logged_in(self) -> bool:
        """Return whether session is authenticated."""

    @abstractmethod
    @require_korean_alias
    def login(self, **kwargs: Any) -> bool:
        """Perform synchronous login."""

    @abstractmethod
    @require_korean_alias
    async def async_login(self, **kwargs: Any) -> bool:
        """Perform asynchronous login."""

    @abstractmethod
    @require_korean_alias
    def overseas_stock(self) -> BaseOverseasStock:
        """Return overseas stock facade."""

    @abstractmethod
    @require_korean_alias
    def overseas_futureoption(self) -> BaseOverseasFutureoption:
        """Return overseas futures/options facade."""

    로그인 = login
    비동기로그인 = async_login
    해외주식 = overseas_stock
    해외선물 = overseas_futureoption
