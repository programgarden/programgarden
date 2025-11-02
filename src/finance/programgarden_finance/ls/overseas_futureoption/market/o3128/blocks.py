from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3128RequestHeader(BlockRequestHeader):
    pass


class O3128ResponseHeader(BlockResponseHeader):
    pass


class O3128InBlock(BaseModel):
    """
    o3128InBlock 입력 블록

    Attributes:
        mktgb (Literal["F", "O"]): 시장구분 (F:선물, O:옵션)
        shcode (str): 단축코드
        gubun (Literal["0", "1", "2"]): 주기구분 (0:일, 1:주, 2:월)
        qrycnt (int): 요청건수
        sdate (str): 시작일자 (YYYYMMDD)
        edate (str): 종료일자 (YYYYMMDD)
        cts_date (str): 연속일자 (YYYYMMDD)
    """
    mktgb: Literal["F", "O"] = Field(..., title="시장구분", description="F:선물, O:옵션")
    """시장구분 (F:선물, O:옵션)"""
    shcode: str = Field(..., title="단축코드", description="단축코드")
    """단축코드"""
    gubun: Literal["0", "1", "2"] = Field(..., title="주기구분", description="0:일,1:주,2:월")
    """주기구분 (0:일,1:주,2:월)"""
    qrycnt: int = Field(..., title="요청건수", description="요청건수")
    """요청건수"""
    sdate: str = Field(..., title="시작일자", description="시작일자 (YYYYMMDD)")
    """시작일자 (YYYYMMDD)"""
    edate: str = Field(..., title="종료일자", description="종료일자 (YYYYMMDD)")
    """종료일자 (YYYYMMDD)"""
    cts_date: str = Field("", title="연속일자", description="연속일자 (YYYYMMDD)")
    """연속일자 (YYYYMMDD)"""


class O3128Request(BaseModel):
    header: O3128RequestHeader = O3128RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3128",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["o3128InBlock"], O3128InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'o3128InBlock')"
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3128"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )


class O3128OutBlock(BaseModel):
    """
    o3128OutBlock 응답 기본 블록
    """
    shcode: str = Field(default="", title="단축코드", description="단축코드")
    """단축코드"""
    jisiga: float = Field(default=0.0, title="전일시가", description="전일시가")
    """전일시가"""
    jihigh: float = Field(default=0.0, title="전일고가", description="전일고가")
    """전일고가"""
    jilow: float = Field(default=0.0, title="전일저가", description="전일저가")
    """전일저가"""
    jiclose: float = Field(default=0.0, title="전일종가", description="전일종가")
    """전일종가"""
    jivolume: int = Field(default=0, title="전일거래량", description="전일거래량")
    """전일거래량"""
    disiga: float = Field(default=0.0, title="당일시가", description="당일시가")
    """당일시가"""
    dihigh: float = Field(default=0.0, title="당일고가", description="당일고가")
    """당일고가"""
    dilow: float = Field(default=0.0, title="당일저가", description="당일저가")
    """당일저가"""
    diclose: float = Field(default=0.0, title="당일종가", description="당일종가")
    """당일종가"""
    mk_stime: str = Field(default="", title="장시작시간", description="장시작시간 (HHMMSS)")
    """장시작시간 (HHMMSS)"""
    mk_etime: str = Field(default="", title="장마감시간", description="장마감시간 (HHMMSS)")
    """장마감시간 (HHMMSS)"""
    cts_date: str = Field(default="", title="연속일자", description="연속일자 (YYYYMMDD)")
    """연속일자 (YYYYMMDD)"""
    rec_count: int = Field(default=0, title="레코드카운트", description="레코드카운트")
    """레코드카운트"""


class O3128OutBlock1(BaseModel):
    """
    o3128OutBlock1 리스트 항목

    Attributes:
        date (str): 날짜 (YYYYMMDD)
        open (float): 시가
        high (float): 고가
        low (float): 저가
        close (float): 종가
        volume (int): 거래량
    """
    date: str = Field(default="", title="날짜", description="날짜 (YYYYMMDD)")
    """날짜 (YYYYMMDD)"""
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


class O3128Response(BaseModel):
    header: Optional[O3128ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: Optional[O3128OutBlock] = Field(
        None,
        title="기본 응답 블록",
        description="기본 응답 블록"
    )
    block1: List[O3128OutBlock1] = Field(
        ...,
        title="상세 리스트",
        description="상세 리스트 (여러 레코드)"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="HTTP 상태 코드"
    )
    rsp_cd: str = Field(..., title="응답코드", description="응답코드")
    rsp_msg: str = Field(..., title="응답메시지", description="응답메시지")
    error_msg: Optional[str] = Field(None, title="오류메시지", description="오류메시지 (있으면)")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
