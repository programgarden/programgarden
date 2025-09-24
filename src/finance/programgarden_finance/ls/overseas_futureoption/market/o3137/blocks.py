from typing import List, Optional, Literal

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3137RequestHeader(BlockRequestHeader):
    pass


class O3137ResponseHeader(BlockResponseHeader):
    pass


class O3137InBlock(BaseModel):
    """
    o3137InBlock 입력 블록

    Attributes:
        mktgb (Literal["F", "O"]): 시장구분 ex) F(선물), O(옵션)
        shcode (str): 단축코드
        ncnt (int): N분주기
        qrycnt (int): 조회갯수
        cts_seq (str): 연속순번
        cts_daygb (str): 연속당일구분
    """
    mktgb: Literal["F", "O"] = Field(..., title="시장구분", description="ex) F(선물), O(옵션)")
    """시장구분 (ex: F, O)"""
    shcode: str = Field(..., title="단축코드", description="단축코드 (예: ADM23)")
    """단축코드"""
    ncnt: int = Field(..., title="N분주기", description="N분주기 (예: 0(30초), 1(1분), 30(30분))")
    """N분주기"""
    qrycnt: int = Field(..., le=500, title="조회갯수", description="조회갯수")
    """조회갯수"""
    cts_seq: str = Field("", title="연속시간", description="연속시간 또는 연속시퀀스 (빈값 또는 문자열)")
    """연속시간/시퀀스"""
    cts_daygb: str = Field("", title="연속당일구분", description="연속당일구분 (예: 당일구분)")
    """연속당일구분"""


class O3137Request(BaseModel):
    header: O3137RequestHeader = O3137RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3137",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["o3137InBlock"], O3137InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'o3137InBlock')"
    )
    """입력 블록, o3137InBlock 데이터 블록을 포함하는 딕셔너리 형태"""
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3137"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3137OutBlock(BaseModel):
    """
    o3137OutBlock 응답 기본 블록
    """
    shcode: str = Field(default="", title="단축코드", description="단축코드")
    """단축코드"""
    rec_count: int = Field(default=0, title="레코드카운트", description="레코드카운트")
    """레코드카운트"""
    cts_seq: str = Field(default="", title="연속시간", description="연속시간 (연속 조회용)")
    """연속시간"""
    cts_daygb: str = Field(default="", title="연속당일구분", description="연속당일구분")
    """연속당일구분"""


class O3137OutBlock1(BaseModel):
    """
    o3137OutBlock1 리스트 항목

    Attributes:
        date (str): 날짜 (YYYYMMDD)
        time (str): 시간 (HHMMSS)
        open (float): 시가
        high (float): 고가
        low (float): 저가
        close (float): 종가
        volume (int): 거래량
    """
    date: str = Field(default="", title="날짜", description="날짜 (YYYYMMDD)")
    """날짜 (YYYYMMDD)"""
    time: str = Field(default="", title="시간", description="시간 (HHMMSS)")
    """시간 (HHMMSS)"""
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


class O3137Response(BaseModel):
    header: Optional[O3137ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    """응답 헤더 데이터 블록"""
    block: Optional[O3137OutBlock] = Field(
        None,
        title="기본 응답 블록",
        description="기본 응답 블록"
    )
    """기본 응답 블록"""
    block1: List[O3137OutBlock1] = Field(
        ...,
        title="상세 리스트",
        description="상세 리스트 (여러 레코드)"
    )
    """상세 리스트 (여러 레코드)"""
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
