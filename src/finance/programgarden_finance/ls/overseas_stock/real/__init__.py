from programgarden_finance.ls.real_base import RealRequestAbstract
from programgarden_finance.ls.token_manager import TokenManager
from .GSC import RealGSC
from .GSC.blocks import (
    GSCRealRequest,
    GSCRealRequestHeader,
    GSCRealRequestBody,
    GSCRealResponseBody,
    GSCRealResponseHeader,
    GSCRealResponse
)
from .GSH import RealGSH
from .GSH.blocks import (
    GSHRealRequest,
    GSHRealRequestHeader,
    GSHRealRequestBody,
    GSHRealResponseBody,
    GSHRealResponseHeader,
    GSHRealResponse
)
from .AS0 import RealAS0
from .AS0.blocks import (
    AS0RealRequest,
    AS0RealRequestHeader,
    AS0RealRequestBody,
    AS0RealResponseHeader,
    AS0RealResponseBody,
    AS0RealResponse,
)
from .AS1 import RealAS1
from .AS1.blocks import (
    AS1RealRequest,
    AS1RealRequestHeader,
    AS1RealRequestBody,
    AS1RealResponseHeader,
    AS1RealResponseBody,
    AS1RealResponse,
)
from .AS2.client import RealAS2
from .AS2.blocks import (
    AS2RealRequest,
    AS2RealRequestHeader,
    AS2RealRequestBody,
    AS2RealResponseHeader,
    AS2RealResponseBody,
    AS2RealResponse,
)
from .AS3.client import RealAS3
from .AS3.blocks import (
    AS3RealRequest,
    AS3RealRequestHeader,
    AS3RealRequestBody,
    AS3RealResponseHeader,
    AS3RealResponseBody,
    AS3RealResponse,
)
from .AS4.client import RealAS4
from .AS4.blocks import (
    AS4RealRequest,
    AS4RealRequestHeader,
    AS4RealRequestBody,
    AS4RealResponseHeader,
    AS4RealResponseBody,
    AS4RealResponse,
)


from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias

EnforceKoreanAliasAndBaseMeta = type(
    "EnforceKoreanAliasAndBaseMeta",
    (EnforceKoreanAliasMeta, RealRequestAbstract.__class__),
    {}
)


class Real(RealRequestAbstract, metaclass=EnforceKoreanAliasAndBaseMeta):
    """
    LS증권 OpenAPI 실시간 클래스
    """

    def __init__(
        self,
        token_manager: TokenManager,
        reconnect=True,
        recv_timeout=5.0,
        ping_interval=30.0,
        ping_timeout=5.0,
        max_backoff=60.0
    ):
        super().__init__(
            reconnect=reconnect,
            recv_timeout=recv_timeout,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            max_backoff=max_backoff,
            token_manager=token_manager
        )
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def GSC(self) -> RealGSC:
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealGSC(
            parent=self
        )

    해외주식체결 = GSC
    해외주식체결.__doc__ = "해외 주식 체결(틱)을 요청합니다."

    @require_korean_alias
    def GSH(self) -> RealGSH:
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealGSH(
            parent=self
        )

    해외주식호가 = GSH
    해외주식호가.__doc__ = "해외 주식 호가를 요청합니다."

    @require_korean_alias
    def AS0(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealAS0(
            parent=self
        )

    해외주식주문접수_미국 = AS0
    해외주식주문접수_미국.__doc__ = "해외 주식 주문 접수를 요청합니다."

    @require_korean_alias
    def AS1(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealAS1(
            parent=self
        )

    해외주식주문체결_미국 = AS1
    해외주식주문체결_미국.__doc__ = "해외 주식 주문 체결을 요청합니다."

    @require_korean_alias
    def AS2(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealAS2(
            parent=self
        )

    해외주식주문정정_미국 = AS2
    해외주식주문정정_미국.__doc__ = "해외 주식 주문 정정을 요청합니다."

    @require_korean_alias
    def AS3(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealAS3(
            parent=self
        )

    해외주식주문취소_미국 = AS3
    해외주식주문취소_미국.__doc__ = "해외 주식 주문 취소를 요청합니다."

    @require_korean_alias
    def AS4(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealAS4(
            parent=self
        )

    해외주식주문거부_미국 = AS4
    해외주식주문거부_미국.__doc__ = "해외 주식 주문 거부를 요청합니다."


__all__ = [
    Real,

    GSCRealRequest,
    GSCRealRequestBody,
    GSCRealRequestHeader,
    GSCRealResponseBody,
    GSCRealResponseHeader,
    GSCRealResponse,

    GSHRealRequest,
    GSHRealRequestBody,
    GSHRealRequestHeader,
    GSHRealResponseBody,
    GSHRealResponseHeader,
    GSHRealResponse,

    AS0RealRequest,
    AS0RealRequestBody,
    AS0RealRequestHeader,
    AS0RealResponseBody,
    AS0RealResponseHeader,
    AS0RealResponse,

    AS1RealRequest,
    AS1RealRequestBody,
    AS1RealRequestHeader,
    AS1RealResponseBody,
    AS1RealResponseHeader,
    AS1RealResponse,

    AS2RealRequest,
    AS2RealRequestBody,
    AS2RealRequestHeader,
    AS2RealResponseBody,
    AS2RealResponseHeader,
    AS2RealResponse,

    AS3RealRequest,
    AS3RealRequestBody,
    AS3RealRequestHeader,
    AS3RealResponseBody,
    AS3RealResponseHeader,
    AS3RealResponse,

    AS4RealRequest,
    AS4RealRequestBody,
    AS4RealRequestHeader,
    AS4RealResponseBody,
    AS4RealResponseHeader,
    AS4RealResponse,

    RealGSC,
    RealGSH,
    RealAS0,
    RealAS1,
    RealAS2,
    RealAS3,
    RealAS4,
]
