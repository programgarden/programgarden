"""KOSDAQ 체결(K3_) 실시간 WebSocket 요청/응답 모델

EN:
    Pydantic models for the K3_ (KOSDAQ Trade Execution) real-time WebSocket stream.
    Provides real-time tick-by-tick trade data for KOSDAQ-listed stocks.
    Field structure is identical to S3_ (KOSPI).

KO:
    KOSDAQ 종목의 실시간 체결(틱) 데이터를 수신하기 위한 WebSocket 요청/응답 모델입니다.
    필드 구조는 S3_(KOSPI 체결)와 동일하며, KOSDAQ 종목에 대한 데이터를 수신합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class K3_RealRequestHeader(BlockRealRequestHeader):
    pass


class K3_RealResponseHeader(BlockRealResponseHeader):
    pass


class K3_RealRequestBody(BaseModel):
    tr_cd: str = Field("K3_", description="거래 CD")
    tr_key: str = Field(..., max_length=8, description="KOSDAQ 종목 단축코드 6자리 또는 8자리 (예: '122870')")


class K3_RealRequest(BaseModel):
    """KOSDAQ 체결(K3_) 실시간 시세 등록/해제 요청

    EN:
        WebSocket subscription request for KOSDAQ real-time trade execution data.
        Use tr_type='3' to subscribe, '4' to unsubscribe.

    KO:
        KOSDAQ 종목의 실시간 체결 데이터 수신을 위한 WebSocket 등록/해제 요청입니다.
        tr_type '3'으로 실시간 등록, '4'로 해제합니다.
    """
    header: K3_RealRequestHeader = Field(
        K3_RealRequestHeader(token="", tr_type="3"),
        title="요청 헤더",
        description="K3_ 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: K3_RealRequestBody = Field(
        K3_RealRequestBody(tr_cd="K3_", tr_key=""),
        title="요청 바디",
        description="KOSDAQ 체결 실시간 등록에 필요한 종목코드 정보"
    )


class K3_RealResponseBody(BaseModel):
    """KOSDAQ 체결(K3_) 실시간 응답 바디

    EN:
        Real-time KOSDAQ trade execution data body containing 27 fields.
        Field structure is identical to S3_ (KOSPI Trade Execution).

    KO:
        KOSDAQ 종목의 실시간 체결 데이터 바디입니다.
        필드 구조는 S3_(KOSPI 체결)와 동일한 27개 필드를 포함합니다.
    """
    chetime: str = Field(..., title="체결시간", description="체결시간 (HHMMSS, 예: '104904')")
    """체결시간"""
    sign: str = Field(..., title="전일대비구분", description="전일대비구분 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락)")
    """전일대비구분"""
    change: str = Field(..., title="전일대비", description="전일대비 가격 변동폭")
    """전일대비"""
    drate: str = Field(..., title="등락율", description="전일대비 등락율 (%, 예: '29.68')")
    """등락율"""
    price: str = Field(..., title="현재가", description="현재 체결가격")
    """현재가"""
    opentime: str = Field(..., title="시가시간", description="시가 형성 시간 (HHMMSS)")
    """시가시간"""
    open: str = Field(..., title="시가", description="당일 시가")
    """시가"""
    hightime: str = Field(..., title="고가시간", description="고가 형성 시간 (HHMMSS)")
    """고가시간"""
    high: str = Field(..., title="고가", description="당일 고가")
    """고가"""
    lowtime: str = Field(..., title="저가시간", description="저가 형성 시간 (HHMMSS)")
    """저가시간"""
    low: str = Field(..., title="저가", description="당일 저가")
    """저가"""
    cgubun: str = Field(..., title="체결구분", description="체결구분 ('+':매수체결, '-':매도체결)")
    """체결구분"""
    cvolume: str = Field(..., title="체결량", description="이번 체결의 체결수량")
    """체결량"""
    volume: str = Field(..., title="누적거래량", description="당일 누적 거래량")
    """누적거래량"""
    value: str = Field(..., title="누적거래대금", description="당일 누적 거래대금 (백만원)")
    """누적거래대금"""
    mdvolume: str = Field(..., title="매도누적체결량", description="당일 매도 누적 체결수량")
    """매도누적체결량"""
    mdchecnt: str = Field(..., title="매도누적체결건수", description="당일 매도 누적 체결 건수")
    """매도누적체결건수"""
    msvolume: str = Field(..., title="매수누적체결량", description="당일 매수 누적 체결수량")
    """매수누적체결량"""
    mschecnt: str = Field(..., title="매수누적체결건수", description="당일 매수 누적 체결 건수")
    """매수누적체결건수"""
    cpower: str = Field(..., title="체결강도", description="체결강도 (매수체결량/매도체결량*100, 예: '44.30')")
    """체결강도"""
    w_avrg: str = Field(..., title="가중평균가", description="거래량 가중 평균가격")
    """가중평균가"""
    offerho: str = Field(..., title="매도호가", description="매도 최우선호가 (매도1호가)")
    """매도호가"""
    bidho: str = Field(..., title="매수호가", description="매수 최우선호가 (매수1호가)")
    """매수호가"""
    status: str = Field(..., title="장정보", description="장 상태 정보 ('00':장중)")
    """장정보"""
    jnilvolume: str = Field(..., title="전일동시간대거래량", description="전일 동시간대까지의 누적 거래량")
    """전일동시간대거래량"""
    shcode: str = Field(..., title="단축코드", description="종목 단축코드 6자리 (예: '122870')")
    """단축코드"""
    exchname: str = Field(..., title="거래소명", description="거래소명 (예: 'KRX')")
    """거래소명"""


class K3_RealResponse(BaseModel):
    """KOSDAQ 체결(K3_) 실시간 응답

    EN:
        Complete response model for K3_ real-time KOSDAQ trade execution data.

    KO:
        KOSDAQ 체결 실시간 데이터의 전체 응답 모델입니다.
    """
    header: Optional[K3_RealResponseHeader]
    body: Optional[K3_RealResponseBody]

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
