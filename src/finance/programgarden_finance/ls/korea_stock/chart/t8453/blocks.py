from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8453RequestHeader(BlockRequestHeader):
    """T8453 요청용 Header"""
    pass


class T8453ResponseHeader(BlockResponseHeader):
    """T8453 응답용 Header"""
    pass


class T8453InBlock(BaseModel):
    """(통합)주식챠트(틱/N틱) API용 입력 블록"""
    shcode: str = Field(default="", description="단축코드")
    ncnt: int = Field(default=0, description="단위(n틱)")
    qrycnt: int = Field(default=0, description="요청건수(최대:500)")
    nday: str = Field(default="", description="조회영업일수(0:미사용1>=사용)")
    sdate: str = Field(default="", description="시작일자")
    stime: str = Field(default="", description="시작시간(현재미사용)")
    edate: str = Field(default="", description="종료일자")
    etime: str = Field(default="", description="종료시간(현재미사용)")
    cts_date: str = Field(default="", description="연속일자")
    cts_time: str = Field(default="", description="연속시간")
    comp_yn: str = Field(default="", description="압축여부(N:비압축)")


class T8453OutBlock(BaseModel):
    """(통합)주식챠트(틱/N틱) API용 출력 블록 - t8453OutBlock"""
    shcode: str = Field(default="", description="단축코드")
    jisiga: int = Field(default=0, description="전일시가")
    jihigh: int = Field(default=0, description="전일고가")
    jilow: int = Field(default=0, description="전일저가")
    jicloseㅍ: int = Field(default=0, description="전일종가")
    jivolume: int = Field(default=0, description="전일거래량")
    disiga: int = Field(default=0, description="당일시가")
    dihigh: int = Field(default=0, description="당일고가")
    dilow: int = Field(default=0, description="당일저가")
    diclose: int = Field(default=0, description="당일종가")
    highend: int = Field(default=0, description="상한가")
    lowend: int = Field(default=0, description="하한가")
    cts_date: str = Field(default="", description="연속일자")
    cts_time: str = Field(default="", description="연속시간")
    s_time: str = Field(default="", description="장시작시간(HHMMSS)")
    e_time: str = Field(default="", description="장종료시간(HHMMSS)")
    dshmin: str = Field(default="", description="동시호가처리시간(MM:분)")
    rec_count: int = Field(default=0, description="레코드카운트")
    nxt_fm_s_time: str = Field(default="", description="NXT프리마켓장시작시간(HHMMSS)")
    nxt_fm_e_time: str = Field(default="", description="NXT프리마켓장종료시간(HHMMSS)")
    nxt_fm_dshmin: str = Field(default="", description="NXT프리마켓동시호가처리시간(MM:분)")
    nxt_am_s_time: str = Field(default="", description="NXT에프터마켓장시작시간(HHMMSS)")
    nxt_am_e_time: str = Field(default="", description="NXT에프터마켓장종료시간(HHMMSS)")
    nxt_am_dshmin: str = Field(default="", description="NXT에프터마켓동시호가처리시간(MM:분)")


class T8453OutBlock1(BaseModel):
    """(통합)주식챠트(틱/N틱) API용 출력 블록 - t8453OutBlock1"""
    date: str = Field(default="", description="날짜")
    time: str = Field(default="", description="시간")
    open: int = Field(default=0, description="시가")
    high: int = Field(default=0, description="고가")
    low: int = Field(default=0, description="저가")
    close: int = Field(default=0, description="종가")
    jdiff_vol: int = Field(default=0, description="거래량")
    jongchk: int = Field(default=0, description="수정구분")
    rate: float = Field(default=0.0, description="수정비율")
    pricechk: int = Field(default=0, description="수정주가반영항목")


class T8453Request(BaseModel):
    """(통합)주식챠트(틱/N틱) API용 요청 모델"""
    header: T8453RequestHeader = T8453RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8453",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T8453Response(BaseModel):
    """(통합)주식챠트(틱/N틱) API용 응답 모델"""
    header: Optional[T8453ResponseHeader] = None
    cont_block: Optional[T8453OutBlock] = None
    block: list[T8453OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T8453RequestHeader",
    "T8453ResponseHeader",
    "T8453InBlock",
    "T8453OutBlock",
    "T8453OutBlock1",
    "T8453Request",
    "T8453Response",
]
