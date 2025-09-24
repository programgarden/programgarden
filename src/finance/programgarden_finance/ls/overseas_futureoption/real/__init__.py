from programgarden_finance.ls.real_base import RealRequestAbstract
from programgarden_finance.ls.token_manager import TokenManager
from .OVC import RealOVC
from .OVC.blocks import (
    OVCRealRequest,
    OVCRealRequestHeader,
    OVCRealRequestBody,
    OVCRealResponseBody,
    OVCRealResponseHeader,
    OVCRealResponse,
)
from .OVH import RealOVH
from .OVH.blocks import (
    OVHRealRequest,
    OVHRealRequestHeader,
    OVHRealRequestBody,
    OVHRealResponseBody,
    OVHRealResponseHeader,
    OVHRealResponse,
)
from .WOC import RealWOC
from .WOC.blocks import (
    WOCRealRequest,
    WOCRealRequestHeader,
    WOCRealRequestBody,
    WOCRealResponseBody,
    WOCRealResponseHeader,
    WOCRealResponse,
)
from .WOH import RealWOH
from .WOH.blocks import (
    WOHRealRequest,
    WOHRealRequestHeader,
    WOHRealRequestBody,
    WOHRealResponseBody,
    WOHRealResponseHeader,
    WOHRealResponse,
)
from .TC1 import RealTC1
from .TC1.blocks import (
    TC1RealRequest,
    TC1RealRequestHeader,
    TC1RealRequestBody,
    TC1RealResponseBody,
    TC1RealResponseHeader,
    TC1RealResponse,
)
from .TC2.client import RealTC2
from .TC2.blocks import (
    TC2RealRequest,
    TC2RealRequestHeader,
    TC2RealRequestBody,
    TC2RealResponseBody,
    TC2RealResponseHeader,
    TC2RealResponse,
)
from .TC3.client import RealTC3
from .TC3.blocks import (
    TC3RealRequest,
    TC3RealRequestHeader,
    TC3RealRequestBody,
    TC3RealResponseBody,
    TC3RealResponseHeader,
    TC3RealResponse,
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
    def OVC(self) -> RealOVC:
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealOVC(
            parent=self
        )

    해외선물체결 = OVC
    해외선물체결.__doc__ = "해외 선물 체결(틱)을 요청합니다."

    @require_korean_alias
    def OVH(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealOVH(
            parent=self
        )

    해외선물호가 = OVH
    해외선물호가.__doc__ = "해외 선물 호가(틱)을 요청합니다."

    @require_korean_alias
    def WOC(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealWOC(
            parent=self
        )

    해외옵션체결 = WOC
    해외옵션체결.__doc__ = "해외 옵션 체결(틱)을 요청합니다."

    @require_korean_alias
    def WOH(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealWOH(
            parent=self
        )

    해외옵션호가 = WOH
    해외옵션호가.__doc__ = "해외 옵션 호가(틱)을 요청합니다."

    @require_korean_alias
    def TC1(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealTC1(
            parent=self
        )

    해외선물주문접수 = TC1
    해외선물주문접수.__doc__ = "해외 선물 주문 접수를 요청합니다."

    @require_korean_alias
    def TC2(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealTC2(
            parent=self
        )

    해외선물주문응답 = TC2
    해외선물주문응답.__doc__ = "해외 선물 주문 응답을 요청합니다."

    @require_korean_alias
    def TC3(self):
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        return RealTC3(
            parent=self
        )

    해외선물주문체결 = TC3
    해외선물주문체결.__doc__ = "해외 선물 주문 체결을 요청합니다."


__all__ = [
    Real,

    OVCRealRequest,
    OVCRealRequestBody,
    OVCRealRequestHeader,
    OVCRealResponseBody,
    OVCRealResponseHeader,
    OVCRealResponse,

    OVHRealRequest,
    OVHRealRequestBody,
    OVHRealRequestHeader,
    OVHRealResponseBody,
    OVHRealResponseHeader,
    OVHRealResponse,

    WOCRealRequest,
    WOCRealRequestBody,
    WOCRealRequestHeader,
    WOCRealResponseBody,
    WOCRealResponseHeader,
    WOCRealResponse,

    WOHRealRequest,
    WOHRealRequestBody,
    WOHRealRequestHeader,
    WOHRealResponseBody,
    WOHRealResponseHeader,
    WOHRealResponse,

    TC1RealRequest,
    TC1RealRequestBody,
    TC1RealRequestHeader,
    TC1RealResponseBody,
    TC1RealResponseHeader,
    TC1RealResponse,

    TC2RealRequest,
    TC2RealRequestBody,
    TC2RealRequestHeader,
    TC2RealResponseBody,
    TC2RealResponseHeader,
    TC2RealResponse,

    TC3RealRequest,
    TC3RealRequestBody,
    TC3RealRequestHeader,
    TC3RealResponseBody,
    TC3RealResponseHeader,
    TC3RealResponse,

    RealOVC,
    RealOVH,
    RealWOC,
    RealWOH,
    RealTC1,
    RealTC2,
    RealTC3,
]
