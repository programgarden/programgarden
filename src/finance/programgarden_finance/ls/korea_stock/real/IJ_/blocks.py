"""업종지수(IJ_) 실시간 WebSocket 요청/응답 모델

EN:
    Pydantic models for the IJ_ (Sector Index) real-time WebSocket stream.
    Provides real-time sector/industry index data including KOSPI, KOSDAQ indices,
    with rising/falling stock counts and foreign/institutional net trading.

KO:
    업종지수의 실시간 데이터를 수신하기 위한 WebSocket 요청/응답 모델입니다.
    KOSPI, KOSDAQ 등 업종지수 값, 등락률, 거래량, 상승/하락종목수,
    외인/기관 순매수 등 25개 필드를 포함합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class IJ_RealRequestHeader(BlockRealRequestHeader):
    pass


class IJ_RealResponseHeader(BlockRealResponseHeader):
    pass


class IJ_RealRequestBody(BaseModel):
    tr_cd: str = Field("IJ_", description="거래 CD")
    tr_key: str = Field(..., max_length=8, description="업종코드 3자리 (예: '001'=KOSPI, '301'=KOSDAQ)")


class IJ_RealRequest(BaseModel):
    """업종지수(IJ_) 실시간 시세 등록/해제 요청

    EN:
        WebSocket subscription request for real-time sector index data.
        Use tr_type='3' to subscribe, '4' to unsubscribe.
        Supports KOSPI('001'), KOSDAQ('301'), and other sector codes.

    KO:
        업종지수의 실시간 데이터 수신을 위한 WebSocket 등록/해제 요청입니다.
        tr_type '3'으로 실시간 등록, '4'로 해제합니다.
        KOSPI('001'), KOSDAQ('301') 등 업종코드를 지정합니다.
    """
    header: IJ_RealRequestHeader = Field(
        IJ_RealRequestHeader(token="", tr_type="3"),
        title="요청 헤더",
        description="IJ_ 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: IJ_RealRequestBody = Field(
        IJ_RealRequestBody(tr_cd="IJ_", tr_key=""),
        title="요청 바디",
        description="업종지수 실시간 등록에 필요한 업종코드 정보"
    )


class IJ_RealResponseBody(BaseModel):
    """업종지수(IJ_) 실시간 응답 바디

    EN:
        Real-time sector index data body containing 25 fields:
        index value, change, rising/falling stock counts, open/high/low index,
        foreign/institutional net trading volume and amount.

    KO:
        업종지수의 실시간 데이터 바디입니다.
        지수값, 등락률, 상승/하락종목수, 시가/고가/저가 지수,
        외인/기관 순매수량 및 순매수금액 등 25개 필드를 포함합니다.
    """
    time: str = Field(..., title="시간", description="지수 산출 시간 (HHMMSS, 예: '090510')")
    """시간"""
    jisu: str = Field(..., title="지수", description="현재 업종지수 값 (예: '2638.79')")
    """지수"""
    sign: str = Field(..., title="전일대비구분", description="전일대비구분 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락)")
    """전일대비구분"""
    change: str = Field(..., title="전일비", description="전일대비 지수 변동폭 (예: '0.84')")
    """전일비"""
    drate: str = Field(..., title="등락율", description="전일대비 등락율 (%, 예: '0.03')")
    """등락율"""
    cvolume: str = Field(..., title="체결량", description="이번 체결의 거래량")
    """체결량"""
    volume: str = Field(..., title="거래량", description="당일 누적 거래량")
    """거래량"""
    value: str = Field(..., title="거래대금", description="당일 누적 거래대금 (백만원)")
    """거래대금"""
    upjo: str = Field(..., title="상한종목수", description="상한가 도달 종목 수")
    """상한종목수"""
    highjo: str = Field(..., title="상승종목수", description="전일대비 상승한 종목 수")
    """상승종목수"""
    unchgjo: str = Field(..., title="보합종목수", description="전일대비 변동 없는 종목 수")
    """보합종목수"""
    lowjo: str = Field(..., title="하락종목수", description="전일대비 하락한 종목 수")
    """하락종목수"""
    downjo: str = Field(..., title="하한종목수", description="하한가 도달 종목 수")
    """하한종목수"""
    upjrate: str = Field(..., title="상승종목비율", description="전체 대비 상승 종목 비율 (%, 예: '42.11')")
    """상승종목비율"""
    openjisu: str = Field(..., title="시가지수", description="당일 시가 지수")
    """시가지수"""
    opentime: str = Field(..., title="시가시간", description="시가지수 형성 시간 (HHMMSS)")
    """시가시간"""
    highjisu: str = Field(..., title="고가지수", description="당일 고가 지수")
    """고가지수"""
    hightime: str = Field(..., title="고가시간", description="고가지수 형성 시간 (HHMMSS)")
    """고가시간"""
    lowjisu: str = Field(..., title="저가지수", description="당일 저가 지수")
    """저가지수"""
    lowtime: str = Field(..., title="저가시간", description="저가지수 형성 시간 (HHMMSS)")
    """저가시간"""
    frgsvolume: str = Field(..., title="외인순매수수량", description="외국인 순매수 수량 (음수=순매도)")
    """외인순매수수량"""
    orgsvolume: str = Field(..., title="기관순매수수량", description="기관 순매수 수량 (음수=순매도)")
    """기관순매수수량"""
    frgsvalue: str = Field(..., title="외인순매수금액", description="외국인 순매수 금액 (백만원)")
    """외인순매수금액"""
    orgsvalue: str = Field(..., title="기관순매수금액", description="기관 순매수 금액 (백만원)")
    """기관순매수금액"""
    upcode: str = Field(..., title="업종코드", description="업종코드 3자리 (예: '001'=KOSPI)")
    """업종코드"""


class IJ_RealResponse(BaseModel):
    """업종지수(IJ_) 실시간 응답

    EN:
        Complete response model for IJ_ real-time sector index data.
        Contains header (TR code, sector code) and body (index details).

    KO:
        업종지수 실시간 데이터의 전체 응답 모델입니다.
        header에 TR코드와 업종코드, body에 지수 상세 데이터가 포함됩니다.
    """
    header: Optional[IJ_RealResponseHeader]
    body: Optional[IJ_RealResponseBody]

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
