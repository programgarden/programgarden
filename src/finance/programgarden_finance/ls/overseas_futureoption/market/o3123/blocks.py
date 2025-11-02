from typing import List, Optional, Literal

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3123RequestHeader(BlockRequestHeader):
    pass


class O3123ResponseHeader(BlockResponseHeader):
    pass


class O3123InBlock(BaseModel):
    """
    o3123InBlock 입력 블록

    Attributes:
        mktgb (str): 시장구분
        shcode (str): 단축코드
        ncnt (int): N분주기
        readcnt (int): 조회갯수
        cts_date (str): 연속일자
        cts_time (str): 연속시간
    """
    mktgb: str = Field(..., title="시장구분", description="ex) F(선물), O(옵션)")
    """시장구분 (ex: F, O)"""
    shcode: str = Field(..., title="단축코드", description="단축코드 (예: ADU13)")
    """단축코드"""
    ncnt: int = Field(..., title="N분주기", description="N분주기 (예: 0(30초), 1(1분), 30(30분))")
    """N분주기"""
    readcnt: int = Field(..., le=500, title="조회갯수", description="조회갯수")
    """조회갯수"""
    cts_date: str = Field("", title="연속일자", description="연속일자 (YYYYMMDD)")
    """연속일자 (YYYYMMDD)"""
    cts_time: str = Field("", title="연속시간", description="연속시간 (HHMMSS)")
    """연속시간 (HHMMSS)"""


class O3123Request(BaseModel):
    header: O3123RequestHeader = O3123RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3123",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["o3123InBlock"], O3123InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'o3123InBlock')"
    )
    """입력 블록, o3123InBlock 데이터 블록을 포함하는 딕셔너리 형태"""
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3123"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3123OutBlock(BaseModel):
    """
    o3123OutBlock 응답 기본 블록
    """
    shcode: str = Field(default="", title="단축코드", description="단축코드")
    """단축코드"""
    timediff: int = Field(default=0, title="시차", description="시차")
    """시차"""
    readcnt: int = Field(default=0, title="조회갯수", description="조회갯수")
    """조회갯수"""
    cts_date: str = Field(default="", title="연속일자", description="연속일자 (YYYYMMDD)")
    """연속일자 (YYYYMMDD)"""
    cts_time: str = Field(default="", title="연속시간", description="연속시간 (HHMMSS)")
    """연속시간 (HHMMSS)"""


class O3123OutBlock1(BaseModel):
    """
    o3123OutBlock1 리스트 항목

    Attributes:
        date (str): 날짜 (YYYYMMDD)
        time (str): 현지시간 (HHMMSS)
        open (float): 시가
        high (float): 고가
        low (float): 저가
        close (float): 종가
        volume (int): 거래량
    """
    date: str = Field(default="", title="날짜", description="날짜 (YYYYMMDD)")
    """날짜 (YYYYMMDD)"""
    time: str = Field(default="", title="현지시간", description="현지시간 (HHMMSS)")
    """현지시간 (HHMMSS)"""
    open: float = Field(default=0.0, title="시가", description="시가")
    """시가"""
    high: float = Field(default=0.0, title="고가", description="고가")
    """고가"""
    low: float = Field(default=0.0, title="저가", description="저가")
    """저가"""
    close: float = Field(default=0.0, title="종가", description="종가")
    """종가"""
    volume: int = Field(default=0, title="거래량", description="거래량")
    """거래량"""


class O3123Response(BaseModel):
    header: Optional[O3123ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    """응답 헤더 데이터 블록"""
    block: Optional[O3123OutBlock] = Field(
        None,
        title="기본 응답 블록",
        description="기본 응답 블록"
    )
    """기본 응답 블록"""
    block1: List[O3123OutBlock1] = Field(
        ...,
        title="상세 리스트",
        description="상세 리스트 (여러 레코드)"
    )
    """상세 리스트 (여러 레코드)"""
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="HTTP 상태 코드"
    )
    """HTTP 상태 코드"""
    rsp_cd: str = Field(..., title="응답코드", description="응답코드")
    """응답코드"""
    rsp_msg: str = Field(..., title="응답메시지", description="응답메시지")
    """응답메시지"""
    error_msg: Optional[str] = Field(None, title="오류메시지", description="오류메시지 (있으면)")
    """오류메시지 (있으면)"""

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
