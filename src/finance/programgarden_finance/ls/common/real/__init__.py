"""Common (broker-agnostic) real-time WebSocket Real class.

EN:
    Exposes the JIF (Market Status) TR through a dedicated Real class so
    any broker credential type can share a single WebSocket session for
    market-status updates.

KO:
    broker credential 타입과 무관한 JIF(장운영정보) 실시간 TR을 단일
    WebSocket 세션에서 구독할 수 있도록 제공하는 Real 클래스입니다.
"""

from programgarden_core.bases import BaseReal
from programgarden_core.korea_alias import require_korean_alias

from programgarden_finance.ls.real_base import RealRequestAbstract
from programgarden_finance.ls.token_manager import TokenManager

from .JIF import RealJIF
from .JIF.blocks import (
    JIFRealRequest,
    JIFRealRequestHeader,
    JIFRealRequestBody,
    JIFRealResponseHeader,
    JIFRealResponseBody,
    JIFRealResponse,
)


class Real(RealRequestAbstract, BaseReal):
    """LS Securities real-time Real class for broker-agnostic TRs.

    EN:
        Hosts the JIF (Market Status) subscription. Any broker's
        access_token works — only a single WebSocket session per
        ``token_manager`` is needed.

    KO:
        broker credential 타입과 무관하게 사용 가능한 실시간 TR을
        제공합니다. 현재는 JIF(장운영정보)만 포함하며, token_manager당
        단일 WebSocket 세션을 공유합니다.
    """

    def __init__(
        self,
        token_manager: TokenManager,
        reconnect: bool = True,
        recv_timeout: float = 5.0,
        ping_interval: float = 30.0,
        ping_timeout: float = 5.0,
        max_backoff: float = 60.0,
    ):
        super().__init__(
            reconnect=reconnect,
            recv_timeout=recv_timeout,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            max_backoff=max_backoff,
            token_manager=token_manager,
        )
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def JIF(self) -> RealJIF:
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealJIF(parent=self)

    장운영정보 = JIF
    장운영정보.__doc__ = "JIF 장운영정보 실시간 스트림을 요청합니다."


__all__ = [
    "Real",
    "RealJIF",
    "JIFRealRequest",
    "JIFRealRequestHeader",
    "JIFRealRequestBody",
    "JIFRealResponseHeader",
    "JIFRealResponseBody",
    "JIFRealResponse",
]
