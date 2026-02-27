"""국내주식 실시간(Real) WebSocket 통합 클래스

EN:
    Unified real-time WebSocket class for Korean domestic stocks.
    Manages 13 TR real-time streams: 8 market data (S3_, K3_, H1_, HA_, NH1, IJ_, DVI, NVI)
    and 5 order events (SC0, SC1, SC2, SC3, SC4).
    Uses singleton pattern per token_manager instance.

KO:
    국내주식 실시간 WebSocket 통합 클래스입니다.
    시세 8개(S3_, K3_, H1_, HA_, NH1, IJ_, DVI, NVI)와
    주문 5개(SC0, SC1, SC2, SC3, SC4) 총 13개 TR을 관리합니다.
    token_manager 인스턴스 단위 싱글톤 패턴을 사용합니다.
"""

from programgarden_core.bases import BaseReal
from programgarden_finance.ls.real_base import RealRequestAbstract
from programgarden_finance.ls.token_manager import TokenManager

# ─── 시세 TR imports ───
from .S3_ import RealS3_
from .S3_.blocks import (
    S3_RealRequest, S3_RealRequestHeader, S3_RealRequestBody,
    S3_RealResponseHeader, S3_RealResponseBody, S3_RealResponse,
)
from .K3_ import RealK3_
from .K3_.blocks import (
    K3_RealRequest, K3_RealRequestHeader, K3_RealRequestBody,
    K3_RealResponseHeader, K3_RealResponseBody, K3_RealResponse,
)
from .H1_ import RealH1_
from .H1_.blocks import (
    H1_RealRequest, H1_RealRequestHeader, H1_RealRequestBody,
    H1_RealResponseHeader, H1_RealResponseBody, H1_RealResponse,
)
from .HA_ import RealHA_
from .HA_.blocks import (
    HA_RealRequest, HA_RealRequestHeader, HA_RealRequestBody,
    HA_RealResponseHeader, HA_RealResponseBody, HA_RealResponse,
)
from .NH1 import RealNH1
from .NH1.blocks import (
    NH1RealRequest, NH1RealRequestHeader, NH1RealRequestBody,
    NH1RealResponseHeader, NH1RealResponseBody, NH1RealResponse,
)
from .IJ_ import RealIJ_
from .IJ_.blocks import (
    IJ_RealRequest, IJ_RealRequestHeader, IJ_RealRequestBody,
    IJ_RealResponseHeader, IJ_RealResponseBody, IJ_RealResponse,
)
from .DVI import RealDVI
from .DVI.blocks import (
    DVIRealRequest, DVIRealRequestHeader, DVIRealRequestBody,
    DVIRealResponseHeader, DVIRealResponseBody, DVIRealResponse,
)
from .NVI import RealNVI
from .NVI.blocks import (
    NVIRealRequest, NVIRealRequestHeader, NVIRealRequestBody,
    NVIRealResponseHeader, NVIRealResponseBody, NVIRealResponse,
)

# ─── 주문 TR imports ───
from .SC0 import RealSC0
from .SC0.blocks import (
    SC0RealRequest, SC0RealRequestHeader, SC0RealRequestBody,
    SC0RealResponseHeader, SC0RealResponseBody, SC0RealResponse,
)
from .SC1 import RealSC1
from .SC1.blocks import (
    SC1RealRequest, SC1RealRequestHeader, SC1RealRequestBody,
    SC1RealResponseHeader, SC1RealResponseBody, SC1RealResponse,
)
from .SC2 import RealSC2
from .SC2.blocks import (
    SC2RealRequest, SC2RealRequestHeader, SC2RealRequestBody,
    SC2RealResponseHeader, SC2RealResponseBody, SC2RealResponse,
)
from .SC3 import RealSC3
from .SC3.blocks import (
    SC3RealRequest, SC3RealRequestHeader, SC3RealRequestBody,
    SC3RealResponseHeader, SC3RealResponseBody, SC3RealResponse,
)
from .SC4 import RealSC4
from .SC4.blocks import (
    SC4RealRequest, SC4RealRequestHeader, SC4RealRequestBody,
    SC4RealResponseHeader, SC4RealResponseBody, SC4RealResponse,
)

from programgarden_core.korea_alias import require_korean_alias


class Real(RealRequestAbstract, BaseReal):
    """국내주식 실시간(Real) WebSocket 통합 클래스

    EN:
        Manages WebSocket connections for Korean domestic stock real-time data.
        Provides access to 13 TR clients via property methods:
        - Market data: S3_(KOSPI체결), K3_(KOSDAQ체결), H1_(KOSPI호가),
          HA_(KOSDAQ호가), NH1(NXT호가), IJ_(업종지수), DVI(VI발동해제), NVI(NXT VI)
        - Order events: SC0(주문접수), SC1(주문체결), SC2(주문정정),
          SC3(주문취소), SC4(주문거부)

    KO:
        국내주식 실시간 데이터를 위한 WebSocket 연결을 관리합니다.
        13개 TR 클라이언트에 메서드로 접근합니다:
        - 시세: S3_(KOSPI체결), K3_(KOSDAQ체결), H1_(KOSPI호가잔량),
          HA_(KOSDAQ호가잔량), NH1(NXT호가잔량), IJ_(업종지수),
          DVI(시간외단일가VI발동해제), NVI(NXT VI발동해제)
        - 주문: SC0(주문접수), SC1(주문체결), SC2(주문정정),
          SC3(주문취소), SC4(주문거부)
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

    # ─── 시세 TR 메서드 (8개) ───

    @require_korean_alias
    def S3_(self) -> RealS3_:
        """KOSPI 체결(S3_) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the S3_ client for subscribing to real-time KOSPI trade execution data.
            Provides tick-by-tick trade data (price, volume, change) for KOSPI-listed stocks.

        KO:
            KOSPI 종목의 실시간 체결(틱) 데이터를 구독하기 위한 S3_ 클라이언트를 반환합니다.
            현재가, 거래량, 등락률 등 체결 데이터를 실시간으로 수신합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealS3_(parent=self)

    KOSPI체결 = S3_
    KOSPI체결.__doc__ = "KOSPI 종목의 실시간 체결 데이터를 구독합니다."

    @require_korean_alias
    def K3_(self) -> RealK3_:
        """KOSDAQ 체결(K3_) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the K3_ client for subscribing to real-time KOSDAQ trade execution data.

        KO:
            KOSDAQ 종목의 실시간 체결(틱) 데이터를 구독하기 위한 K3_ 클라이언트를 반환합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealK3_(parent=self)

    KOSDAQ체결 = K3_
    KOSDAQ체결.__doc__ = "KOSDAQ 종목의 실시간 체결 데이터를 구독합니다."

    @require_korean_alias
    def H1_(self) -> RealH1_:
        """KOSPI 호가잔량(H1_) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the H1_ client for subscribing to real-time KOSPI 10-level order book data.

        KO:
            KOSPI 종목의 실시간 10단계 호가잔량 데이터를 구독하기 위한 H1_ 클라이언트를 반환합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealH1_(parent=self)

    KOSPI호가잔량 = H1_
    KOSPI호가잔량.__doc__ = "KOSPI 종목의 실시간 호가잔량 데이터를 구독합니다."

    @require_korean_alias
    def HA_(self) -> RealHA_:
        """KOSDAQ 호가잔량(HA_) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the HA_ client for subscribing to real-time KOSDAQ 10-level order book data.

        KO:
            KOSDAQ 종목의 실시간 10단계 호가잔량 데이터를 구독하기 위한 HA_ 클라이언트를 반환합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealHA_(parent=self)

    KOSDAQ호가잔량 = HA_
    KOSDAQ호가잔량.__doc__ = "KOSDAQ 종목의 실시간 호가잔량 데이터를 구독합니다."

    @require_korean_alias
    def NH1(self) -> RealNH1:
        """(NXT) 호가잔량(NH1) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the NH1 client for subscribing to real-time NXT 10-level order book data.
            NXT (Next Trading System) is a separate exchange with its own stock codes.

        KO:
            NXT(넥스트거래소) 종목의 실시간 10단계 호가잔량 데이터를 구독하기 위한
            NH1 클라이언트를 반환합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealNH1(parent=self)

    NXT호가잔량 = NH1
    NXT호가잔량.__doc__ = "NXT(넥스트거래소) 종목의 실시간 호가잔량 데이터를 구독합니다."

    @require_korean_alias
    def IJ_(self) -> RealIJ_:
        """업종지수(IJ_) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the IJ_ client for subscribing to real-time sector index data.
            Supports KOSPI('001'), KOSDAQ('301'), and other sector indices.

        KO:
            업종지수의 실시간 데이터를 구독하기 위한 IJ_ 클라이언트를 반환합니다.
            KOSPI('001'), KOSDAQ('301') 등 업종코드를 지정하여 구독합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealIJ_(parent=self)

    업종지수 = IJ_
    업종지수.__doc__ = "업종지수의 실시간 데이터를 구독합니다."

    @require_korean_alias
    def DVI(self) -> RealDVI:
        """시간외단일가 VI발동해제(DVI) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the DVI client for subscribing to KRX Volatility Interruption events.
            VI (Volatility Interruption) triggers when price moves exceed thresholds.

        KO:
            KRX 시간외단일가 VI(변동성완화장치) 발동/해제 이벤트를 구독하기 위한
            DVI 클라이언트를 반환합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealDVI(parent=self)

    VI발동해제 = DVI
    VI발동해제.__doc__ = "시간외단일가 VI(변동성완화장치) 발동/해제 이벤트를 구독합니다."

    @require_korean_alias
    def NVI(self) -> RealNVI:
        """(NXT) VI발동해제(NVI) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the NVI client for subscribing to NXT Volatility Interruption events.

        KO:
            NXT(넥스트거래소) VI(변동성완화장치) 발동/해제 이벤트를 구독하기 위한
            NVI 클라이언트를 반환합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealNVI(parent=self)

    NXT_VI발동해제 = NVI
    NXT_VI발동해제.__doc__ = "NXT VI(변동성완화장치) 발동/해제 이벤트를 구독합니다."

    # ─── 주문 TR 메서드 (5개) ───

    @require_korean_alias
    def SC0(self) -> RealSC0:
        """주식주문접수(SC0) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the SC0 client for subscribing to stock order acceptance events.
            Notifies when a new order, modification, or cancellation is accepted.

        KO:
            주식주문접수 이벤트를 구독하기 위한 SC0 클라이언트를 반환합니다.
            신규주문, 정정, 취소 접수 시 실시간으로 알림을 수신합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealSC0(parent=self)

    주문접수 = SC0
    주문접수.__doc__ = "주식주문접수 이벤트를 실시간으로 수신합니다."

    @require_korean_alias
    def SC1(self) -> RealSC1:
        """주식주문체결(SC1) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the SC1 client for subscribing to stock order execution events.
            Notifies when an order is filled (executed) at the exchange.

        KO:
            주식주문체결 이벤트를 구독하기 위한 SC1 클라이언트를 반환합니다.
            거래소에서 주문이 체결될 때 실시간으로 알림을 수신합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealSC1(parent=self)

    주문체결 = SC1
    주문체결.__doc__ = "주식주문체결 이벤트를 실시간으로 수신합니다."

    @require_korean_alias
    def SC2(self) -> RealSC2:
        """주식주문정정(SC2) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the SC2 client for subscribing to stock order modification events.

        KO:
            주식주문정정 이벤트를 구독하기 위한 SC2 클라이언트를 반환합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealSC2(parent=self)

    주문정정 = SC2
    주문정정.__doc__ = "주식주문정정 이벤트를 실시간으로 수신합니다."

    @require_korean_alias
    def SC3(self) -> RealSC3:
        """주식주문취소(SC3) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the SC3 client for subscribing to stock order cancellation events.

        KO:
            주식주문취소 이벤트를 구독하기 위한 SC3 클라이언트를 반환합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealSC3(parent=self)

    주문취소 = SC3
    주문취소.__doc__ = "주식주문취소 이벤트를 실시간으로 수신합니다."

    @require_korean_alias
    def SC4(self) -> RealSC4:
        """주식주문거부(SC4) 실시간 클라이언트를 반환합니다.

        EN:
            Returns the SC4 client for subscribing to stock order rejection events.
            Notifies when an order is rejected by the exchange.

        KO:
            주식주문거부 이벤트를 구독하기 위한 SC4 클라이언트를 반환합니다.
            거래소에서 주문이 거부될 때 실시간으로 알림을 수신합니다.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return RealSC4(parent=self)

    주문거부 = SC4
    주문거부.__doc__ = "주식주문거부 이벤트를 실시간으로 수신합니다."


__all__ = [
    Real,

    # ─── 시세 TR ───
    S3_RealRequest, S3_RealRequestBody, S3_RealRequestHeader,
    S3_RealResponseBody, S3_RealResponseHeader, S3_RealResponse,
    K3_RealRequest, K3_RealRequestBody, K3_RealRequestHeader,
    K3_RealResponseBody, K3_RealResponseHeader, K3_RealResponse,
    H1_RealRequest, H1_RealRequestBody, H1_RealRequestHeader,
    H1_RealResponseBody, H1_RealResponseHeader, H1_RealResponse,
    HA_RealRequest, HA_RealRequestBody, HA_RealRequestHeader,
    HA_RealResponseBody, HA_RealResponseHeader, HA_RealResponse,
    NH1RealRequest, NH1RealRequestBody, NH1RealRequestHeader,
    NH1RealResponseBody, NH1RealResponseHeader, NH1RealResponse,
    IJ_RealRequest, IJ_RealRequestBody, IJ_RealRequestHeader,
    IJ_RealResponseBody, IJ_RealResponseHeader, IJ_RealResponse,
    DVIRealRequest, DVIRealRequestBody, DVIRealRequestHeader,
    DVIRealResponseBody, DVIRealResponseHeader, DVIRealResponse,
    NVIRealRequest, NVIRealRequestBody, NVIRealRequestHeader,
    NVIRealResponseBody, NVIRealResponseHeader, NVIRealResponse,

    # ─── 주문 TR ───
    SC0RealRequest, SC0RealRequestBody, SC0RealRequestHeader,
    SC0RealResponseBody, SC0RealResponseHeader, SC0RealResponse,
    SC1RealRequest, SC1RealRequestBody, SC1RealRequestHeader,
    SC1RealResponseBody, SC1RealResponseHeader, SC1RealResponse,
    SC2RealRequest, SC2RealRequestBody, SC2RealRequestHeader,
    SC2RealResponseBody, SC2RealResponseHeader, SC2RealResponse,
    SC3RealRequest, SC3RealRequestBody, SC3RealRequestHeader,
    SC3RealResponseBody, SC3RealResponseHeader, SC3RealResponse,
    SC4RealRequest, SC4RealRequestBody, SC4RealRequestHeader,
    SC4RealResponseBody, SC4RealResponseHeader, SC4RealResponse,

    # ─── 클라이언트 ───
    RealS3_, RealK3_, RealH1_, RealHA_,
    RealNH1, RealIJ_, RealDVI, RealNVI,
    RealSC0, RealSC1, RealSC2, RealSC3, RealSC4,
]
