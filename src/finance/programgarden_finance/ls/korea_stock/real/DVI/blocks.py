"""시간외단일가 VI발동해제(DVI) 실시간 WebSocket 요청/응답 모델

EN:
    Pydantic models for the DVI (KRX Volatility Interruption) real-time WebSocket stream.
    Provides real-time notifications when a VI (Volatility Interruption) is triggered
    or released for KRX-listed stocks during after-hours single-price trading.

KO:
    KRX 시간외단일가 VI(변동성완화장치) 발동/해제 데이터를 수신하기 위한
    WebSocket 요청/응답 모델입니다. VI 발동 시 기준가격, 발동가격, 구분
    (정적/동적/정적&동적) 등 8개 필드를 포함합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class DVIRealRequestHeader(BlockRealRequestHeader):
    pass


class DVIRealResponseHeader(BlockRealResponseHeader):
    pass


class DVIRealRequestBody(BaseModel):
    tr_cd: str = Field("DVI", description="거래 CD")
    tr_key: str = Field(..., max_length=6, description="종목 단축코드 6자리 (예: '086520') 또는 전체종목 '000000'")


class DVIRealRequest(BaseModel):
    """시간외단일가 VI발동해제(DVI) 실시간 등록/해제 요청

    EN:
        WebSocket subscription request for KRX VI (Volatility Interruption) events.
        Use tr_type='3' to subscribe, '4' to unsubscribe.
        Set tr_key='000000' to receive VI events for all stocks.

    KO:
        KRX VI(변동성완화장치) 발동/해제 이벤트를 수신하기 위한 WebSocket 등록/해제 요청입니다.
        tr_type '3'으로 실시간 등록, '4'로 해제합니다.
        tr_key에 '000000'을 지정하면 전 종목 VI 이벤트를 수신합니다.
    """
    header: DVIRealRequestHeader = Field(
        DVIRealRequestHeader(token="", tr_type="3"),
        title="요청 헤더",
        description="DVI 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: DVIRealRequestBody = Field(
        DVIRealRequestBody(tr_cd="DVI", tr_key=""),
        title="요청 바디",
        description="VI발동해제 실시간 등록에 필요한 종목코드 정보"
    )


class DVIRealResponseBody(BaseModel):
    """시간외단일가 VI발동해제(DVI) 실시간 응답 바디

    EN:
        Real-time KRX VI event data body containing 8 fields:
        VI type (trigger/release), reference prices, trigger price,
        stock code, time, and exchange name.

    KO:
        KRX VI(변동성완화장치) 발동/해제 이벤트 데이터 바디입니다.
        VI 구분(발동/해제), 발동기준가격, 발동가격, 종목코드 등 8개 필드를 포함합니다.
    """
    vi_gubun: str = Field(..., title="구분", description="VI 구분 (0:해제, 1:정적발동, 2:동적발동, 3:정적&동적)")
    """구분"""
    svi_recprice: str = Field(..., title="정적VI발동기준가격", description="정적 VI 발동 기준가격 (0이면 해당 없음)")
    """정적VI발동기준가격"""
    dvi_recprice: str = Field(..., title="동적VI발동기준가격", description="동적 VI 발동 기준가격 (0이면 해당 없음)")
    """동적VI발동기준가격"""
    vi_trgprice: str = Field(..., title="VI발동가격", description="VI 발동을 유발한 가격 (0이면 해제)")
    """VI발동가격"""
    shcode: str = Field(..., title="단축코드", description="VI가 발동/해제된 종목 단축코드 6자리 (KEY)")
    """단축코드"""
    ref_shcode: str = Field(..., title="참조코드", description="참조코드 (미사용)")
    """참조코드"""
    time: str = Field(..., title="시간", description="VI 발동/해제 시간 (HHMMSS, 예: '092415')")
    """시간"""
    exchname: str = Field(..., title="거래소명", description="거래소명 (예: 'KRX')")
    """거래소명"""


class DVIRealResponse(BaseModel):
    """시간외단일가 VI발동해제(DVI) 실시간 응답

    EN:
        Complete response model for DVI real-time VI event data.
        Contains header (TR code, stock code) and body (VI event details).

    KO:
        KRX VI(변동성완화장치) 발동/해제 실시간 데이터의 전체 응답 모델입니다.
        header에 TR코드와 종목코드, body에 VI 이벤트 상세 데이터가 포함됩니다.
    """
    header: Optional[DVIRealResponseHeader]
    body: Optional[DVIRealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드")
    """응답 코드"""
    rsp_msg: str = Field(..., title="응답 메시지")
    """응답 메시지"""
    error_msg: Optional[str] = Field(None, title="오류 메시지")
    """오류 메시지 (있으면)"""
    _raw_data: Optional[Response] = PrivateAttr(default=None)
    """private으로 BaseModel의 직렬화에 포함시키지 않는다"""

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
