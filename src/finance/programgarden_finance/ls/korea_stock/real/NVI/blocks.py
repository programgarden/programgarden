"""(NXT) VI발동해제(NVI) 실시간 WebSocket 요청/응답 모델

EN:
    Pydantic models for the NVI (NXT Volatility Interruption) real-time WebSocket stream.
    Provides real-time notifications when a VI is triggered or released for
    NXT(Next Trading System)-listed stocks.

KO:
    NXT(넥스트거래소) VI(변동성완화장치) 발동/해제 데이터를 수신하기 위한
    WebSocket 요청/응답 모델입니다. VI 발동 시 기준가격, 발동가격, 구분 등
    9개 필드를 포함하며, 가격 필드는 int 타입입니다.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class NVIRealRequestHeader(BlockRealRequestHeader):
    pass


class NVIRealResponseHeader(BlockRealResponseHeader):
    pass


class NVIRealRequestBody(BaseModel):
    tr_cd: str = Field("NVI", description="거래 CD")
    tr_key: str = Field(..., max_length=10, description="'N' + 종목코드 6자리 + 공백 3자리 (예: 'N000880   ') 또는 전체종목 '0000000000'")

    @field_validator("tr_key", mode="before")
    def ensure_10_char_padding(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v)
        if len(s) < 10:
            return s.ljust(10)
        return s

    model_config = ConfigDict(validate_assignment=True)


class NVIRealRequest(BaseModel):
    """(NXT) VI발동해제(NVI) 실시간 등록/해제 요청

    EN:
        WebSocket subscription request for NXT VI (Volatility Interruption) events.
        Use tr_type='3' to subscribe, '4' to unsubscribe.
        Set tr_key='0000000000' to receive VI events for all NXT stocks.

    KO:
        NXT VI(변동성완화장치) 발동/해제 이벤트를 수신하기 위한 WebSocket 등록/해제 요청입니다.
        tr_type '3'으로 실시간 등록, '4'로 해제합니다.
        tr_key에 '0000000000'을 지정하면 전 종목 VI 이벤트를 수신합니다.
    """
    header: NVIRealRequestHeader = Field(
        NVIRealRequestHeader(token="", tr_type="3"),
        title="요청 헤더",
        description="NVI 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: NVIRealRequestBody = Field(
        NVIRealRequestBody(tr_cd="NVI", tr_key=""),
        title="요청 바디",
        description="NXT VI발동해제 실시간 등록에 필요한 종목코드 정보"
    )


class NVIRealResponseBody(BaseModel):
    """(NXT) VI발동해제(NVI) 실시간 응답 바디

    EN:
        Real-time NXT VI event data body containing 9 fields:
        VI type, reference prices (int), trigger price (int), stock code,
        time, exchange name, and exchange-specific short code.

    KO:
        NXT VI(변동성완화장치) 발동/해제 이벤트 데이터 바디입니다.
        VI 구분, 발동기준가격(int), 발동가격(int), 종목코드, 거래소별단축코드
        등 9개 필드를 포함합니다.
    """
    vi_gubun: str = Field(..., title="구분", description="VI 구분 (0:해제, 1:정적발동, 2:동적발동, 3:정적&동적)")
    """구분"""
    svi_recprice: int = Field(..., title="정적VI발동기준가격", description="정적 VI 발동 기준가격 (0이면 해당 없음)")
    """정적VI발동기준가격"""
    dvi_recprice: int = Field(..., title="동적VI발동기준가격", description="동적 VI 발동 기준가격 (0이면 해당 없음)")
    """동적VI발동기준가격"""
    vi_trgprice: int = Field(..., title="VI발동가격", description="VI 발동을 유발한 가격 (0이면 해제)")
    """VI발동가격"""
    shcode: str = Field(..., title="단축코드", description="NXT 종목 단축코드 9자리")
    """단축코드"""
    ref_shcode: str = Field(..., title="참조코드", description="참조코드 (미사용)")
    """참조코드"""
    time: str = Field(..., title="시간", description="VI 발동/해제 시간 (HHMMSS)")
    """시간"""
    exchname: str = Field(..., title="거래소명", description="거래소명 (예: 'NXT')")
    """거래소명"""
    ex_shcode: str = Field(..., title="거래소별단축코드", description="거래소별 단축코드 (예: 'N115450')")
    """거래소별단축코드"""


class NVIRealResponse(BaseModel):
    """(NXT) VI발동해제(NVI) 실시간 응답

    EN:
        Complete response model for NVI real-time NXT VI event data.
        Contains header (TR code) and body (VI event details).

    KO:
        NXT VI(변동성완화장치) 발동/해제 실시간 데이터의 전체 응답 모델입니다.
        header에 TR코드, body에 VI 이벤트 상세 데이터가 포함됩니다.
    """
    header: Optional[NVIRealResponseHeader]
    body: Optional[NVIRealResponseBody]

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
